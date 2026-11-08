import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cytv.tv import Inventory, SSAP
from cytv.errors import TVNotReady, TVConnectionError


class InventoryTests(unittest.TestCase):
    def test_icon_diagnostics_count_causes_without_retaining_metadata(self):
        png = b'\x89PNG\r\n\x1a\noriginal'
        fetched = []
        def fetch(url):
            fetched.append(url)
            if '/failed' in url: raise OSError('PRIVATE error and address')
            return b'not-an-image' if '/invalid' in url else png
        inventory = Inventory('192.0.2.10', b'fallback', fetch)
        urls = [None, ['PRIVATE'], 'https://PRIVATE/icon',
                'http://192.0.2.10/failed?PRIVATE', 'http://192.0.2.10/invalid',
                'http://192.0.2.10/good', 'http://192.0.2.10/good']
        apps = [dict(id='PRIVATE-' + str(i), title='PRIVATE', icon=url)
                for i, url in enumerate(urls)]
        apps[-1]['largeIcon'] = 'http://192.0.2.10/failed'
        result = inventory.build(apps, [])
        self.assertEqual(len(result['apps']), 7)
        self.assertEqual(len(fetched), 5)
        self.assertEqual(getattr(inventory, 'icon_diagnostics', None), {
            'schema': 1, 'status': 'complete', 'apps': 7, 'embedded': 2,
            'fallback': 5, 'missing_uri': 1, 'rejected_uri': 2,
            'fetch_failed': 2, 'invalid_image': 1})
        self.assertNotIn('PRIVATE', json.dumps(inventory.icon_diagnostics))

    def test_ssap_retains_icon_diagnostics_on_inventory_failure(self):
        session = object.__new__(SSAP)
        session.host = '192.0.2.10'
        def call(uri):
            if uri.endswith('/listLaunchPoints'): return {'launchPoints': [{'id': 'PRIVATE', 'title': 'PRIVATE'}]}
            if uri.endswith('/getExternalInputList'): return {'devices': []}
            return {'apps': []}
        session.call = call
        self.assertEqual(len(session.inventory(b'fallback')['apps']), 1)
        self.assertEqual(getattr(session, 'icon_diagnostics', {}).get('fallback'), 1)
        def unavailable(uri): raise TVConnectionError('PRIVATE')
        session.call = unavailable
        with self.assertRaises(TVConnectionError): session.inventory(b'fallback')
        self.assertEqual(session.icon_diagnostics, {'schema': 1, 'status': 'unavailable'})

    def test_fresh_inventory_uses_local_fallback_and_never_fetches_foreign_urls(self):
        requests = []
        inventory = Inventory('192.0.2.10', b'fallback-png', lambda url: requests.append(url) or b'png')
        result = inventory.build([
            {'id': 'youtube', 'title': 'YouTube', 'icon': 'http://192.0.2.10:3000/icon.png'},
            {'id': 'foreign', 'title': 'Foreign', 'icon': 'http://example.com/icon.png'},
            {'id': 'hidden', 'title': 'Hidden', 'hidden': True},
            {'id': 'no-icon', 'title': 'No icon'},
        ], [{'appId': 'com.webos.app.hdmi1', 'id': 'HDMI_1'}])
        self.assertEqual(requests, ['http://192.0.2.10:3000/icon.png'])
        self.assertEqual([a['id'] for a in result['apps']], ['youtube', 'foreign', 'no-icon'])
        self.assertEqual(result['apps'][1]['icon'], 'data:image/png;base64,ZmFsbGJhY2stcG5n')
        self.assertEqual(result['inputs'], [{'appId': 'com.webos.app.hdmi1', 'label': 'HDMI_1'}])

    def test_supplementary_inventory_size_is_bounded(self):
        from cytv.tv import include_tuner
        ordinary = {'id': 'video', 'title': 'Video'}
        tv = {'id': 'com.webos.app.livetv', 'title': 'TV'}
        self.assertEqual(include_tuner([ordinary], [tv] + [None] * 299)[0]['id'], tv['id'])
        self.assertEqual(include_tuner([ordinary], [tv] + [None] * 300), [ordinary])

    def test_ssap_supplements_only_the_discovered_tuner(self):
        from cytv.errors import UserError
        tv = {'id': 'com.webos.app.livetv', 'title': 'Телетрансляция', 'visible': False, 'hidden': True}
        ordinary = {'id': 'video', 'title': 'Video'}
        for extra in ([tv, {'id': 'private-system', 'title': 'System', 'visible': False}], [], None, [None, {}]):
            with self.subTest(extra=extra):
                session = object.__new__(SSAP)
                session.host = '192.0.2.10'
                calls = []
                def call(uri):
                    calls.append(uri)
                    if uri.endswith('/listLaunchPoints'): return {'launchPoints': [ordinary]}
                    if uri.endswith('/getExternalInputList'): return {'devices': []}
                    if extra is None: raise UserError('unavailable')
                    return {'apps': extra}
                session.call = call
                apps = session.inventory(b'fallback')['apps']
                expected = [tv['id'], ordinary['id']] if extra and tv in extra else [ordinary['id']]
                self.assertEqual([a['id'] for a in apps], expected)
                if tv['id'] in expected: self.assertEqual(apps[0]['title'], tv['title'])
                self.assertIn('ssap://com.webos.applicationManager/listApps', calls)

    def test_optional_malformed_wire_preserves_baseline_inventory(self):
        cases = [('wire', '{broken'), ('wire', 'null'), ('wire', '[]'),
                 ('payload', None), ('payload', [])]
        for kind, value in cases:
            with self.subTest(kind=kind, value=value):
                class Socket:
                    def send(self, raw): self.request = json.loads(raw)
                    def recv(self, timeout):
                        uri = self.request['uri']
                        if uri.endswith('/listLaunchPoints'): payload = {'launchPoints': [{'id': 'video', 'title': 'Video'}]}
                        elif uri.endswith('/getExternalInputList'): payload = {'devices': [{'appId': 'com.webos.app.hdmi1', 'id': 'HDMI_1'}]}
                        elif kind == 'wire': return value
                        else: payload = value
                        return json.dumps({'id': self.request['id'], 'payload': payload})
                session = object.__new__(SSAP)
                session.host, session.counter, session.ws = '192.0.2.10', 0, Socket()
                inventory = session.inventory(b'fallback')
                self.assertEqual([a['id'] for a in inventory['apps']], ['video'])
                self.assertEqual(inventory['inputs'], [{'appId': 'com.webos.app.hdmi1', 'label': 'HDMI_1'}])

    def test_ssap_rejects_error_instead_of_empty_success(self):
        session = object.__new__(SSAP)
        session.counter = 0
        class Socket:
            def send(self, data):
                self.request = json.loads(data)
            def recv(self, timeout):
                return json.dumps({'id': self.request['id'], 'type': 'error', 'error': 'denied'})
        session.ws = Socket()
        with self.assertRaisesRegex(RuntimeError, 'permission'):
            session.call('ssap://com.webos.applicationManager/listLaunchPoints')

    def test_standby_close_before_register_is_actionable_and_closes_socket(self):
        from websockets.exceptions import ConnectionClosedError
        from websockets.frames import Close
        class Socket:
            closed = False
            def send(self, data):
                raise ConnectionClosedError(Close(1008, 'Try Again Later (EWS)'), Close(1008, 'Try Again Later (EWS)'), True)
            def close(self): self.closed = True
        socket = Socket()
        with tempfile.TemporaryDirectory() as tmp, \
             patch('websockets.sync.client.connect', return_value=socket), \
             self.assertRaises(TVNotReady) as caught:
            with SSAP('192.0.2.10', tmp, lambda _: None):
                self.fail('Sleeping TV must not register')
        self.assertTrue(socket.closed)
        self.assertEqual(caught.exception.close_code, 1008)
        self.assertEqual(caught.exception.reason_code, 'tv-not-ready')
        self.assertIn('remote', str(caught.exception))

    def test_pairing_timeout_and_other_policy_closes_do_not_become_standby_retry(self):
        from websockets.exceptions import ConnectionClosedError
        from websockets.frames import Close
        class Socket:
            def send(self, data): pass
            def recv(self, timeout): raise TimeoutError
            def close(self): self.closed = True
        socket = Socket()
        with tempfile.TemporaryDirectory() as tmp, patch('websockets.sync.client.connect', return_value=socket), \
             self.assertRaisesRegex(TVConnectionError, 'pairing request'):
            with SSAP('192.0.2.10', tmp, lambda _: None): pass
        self.assertTrue(socket.closed)
        class Denied(Socket):
            def send(self, data):
                raise ConnectionClosedError(Close(1008, 'PRIVATE-REMOTE-TEXT'), Close(1008, ''), True)
        with tempfile.TemporaryDirectory() as tmp, patch('websockets.sync.client.connect', return_value=Denied()), \
             self.assertRaises(TVConnectionError) as caught:
            with SSAP('192.0.2.10', tmp, lambda _: None): pass
        self.assertNotIsInstance(caught.exception, TVNotReady)
        self.assertNotIn('PRIVATE-REMOTE-TEXT', str(caught.exception))



class LegacySyncTunerTests(unittest.TestCase):
    def test_optional_disconnect_preserves_baseline_listing(self):
        import asyncio, contextlib, io, runpy
        from unittest.mock import AsyncMock
        from websockets.exceptions import ConnectionClosedError
        module = runpy.run_path(str(Path(__file__).resolve().parents[2] / 'sync-apps.py'))
        async def call(ws, uri):
            if uri.endswith('/listLaunchPoints'): return {'launchPoints': [{'id': 'video', 'title': 'Video'}]}
            if uri.endswith('/getExternalInputList'): return {'devices': []}
            raise ConnectionClosedError(None, None)
        out = io.StringIO()
        with patch('lgtv.session', new=AsyncMock(return_value=AsyncMock())), patch('lgtv.call', new=call), contextlib.redirect_stdout(out):
            asyncio.run(module['main']('192.0.2.10', True))
        self.assertIn('Video', out.getvalue())

    def test_optional_malformed_wire_preserves_baseline_listing(self):
        import asyncio, contextlib, io, runpy
        from unittest.mock import AsyncMock
        module = runpy.run_path(str(Path(__file__).resolve().parents[2] / 'sync-apps.py'))
        cases = [('wire', '{broken'), ('wire', 'null'), ('wire', '[]'),
                 ('payload', None), ('payload', [])]
        for kind, value in cases:
            with self.subTest(kind=kind, value=value):
                class Socket:
                    async def send(self, raw): self.request = json.loads(raw)
                    async def recv(self):
                        uri = self.request['uri']
                        if uri.endswith('/listLaunchPoints'): payload = {'launchPoints': [{'id': 'video', 'title': 'Video'}]}
                        elif uri.endswith('/getExternalInputList'): payload = {'devices': []}
                        elif kind == 'wire': return value
                        else: payload = value
                        return json.dumps({'id': self.request['id'], 'payload': payload})
                    async def close(self): pass
                out = io.StringIO()
                with patch('lgtv.session', new=AsyncMock(return_value=Socket())), contextlib.redirect_stdout(out):
                    asyncio.run(module['main']('192.0.2.10', True))
                self.assertIn('Video', out.getvalue())

    def test_discovered_tuner_survives_unavailable_icon(self):
        import asyncio, contextlib, io, runpy
        from unittest.mock import AsyncMock
        module = runpy.run_path(str(Path(__file__).resolve().parents[2] / 'sync-apps.py'))
        async def call(ws, uri):
            if uri.endswith('/listLaunchPoints'): return {'launchPoints': []}
            if uri.endswith('/getExternalInputList'): return {'devices': []}
            return {'returnValue': True, 'apps': [{'id': 'com.webos.app.livetv', 'title': 'TV', 'visible': False}]}
        with tempfile.TemporaryDirectory() as directory:
            module['main'].__globals__['APP_DIR'] = directory
            (Path(directory) / 'brand-v2-icon.png').write_bytes(b'fallback')
            with patch('lgtv.session', new=AsyncMock(return_value=AsyncMock())), patch('lgtv.call', new=call), patch('urllib.request.urlopen', side_effect=OSError('no icon')), contextlib.redirect_stdout(io.StringIO()):
                asyncio.run(module['main']('192.0.2.10', False))
            script = (Path(directory) / 'apps.js').read_text()
            data = json.loads(script.split('window.TV_APPS = ', 1)[1].rstrip(';\n'))
            self.assertEqual([a['id'] for a in data['apps']], ['com.webos.app.livetv'])


class NativeIconQualityTests(unittest.TestCase):
    def test_largest_native_url_precedes_small_and_unreachable_variants_fall_back(self):
        import base64
        calls = []
        png = b'\x89PNG\r\n\x1a\noriginal'
        def fetch(url):
            calls.append(url)
            if url.endswith('extra.png'):
                raise OSError('unavailable')
            return png
        source = {'extraLargeIcon': 'http://192.0.2.10/extra.png',
                  'largeIcon': 'http://192.0.2.10/large.png',
                  'icon': 'http://192.0.2.10/small.png'}
        value = Inventory('192.0.2.10', b'fallback', fetch).icon(source)
        self.assertEqual(calls, ['http://192.0.2.10/extra.png', 'http://192.0.2.10/large.png'])
        self.assertEqual(base64.b64decode(value.split(',')[1]), png)

    def test_optional_native_icon_metadata_with_wrong_type_falls_back(self):
        png = b'\x89PNG\r\n\x1a\noriginal'
        for value in (None, 123, {}, []):
            with self.subTest(value=value):
                result = Inventory('192.0.2.10', b'fallback', lambda _: png).icon({
                    'extraLargeIcon': value, 'icon': 'http://192.0.2.10/icon.png'})
                self.assertTrue(result.startswith('data:image/png;base64,'))


if __name__ == '__main__':
    unittest.main()
