"""SSAP pairing and fresh inventory, with icons embedded as local data URLs."""
import base64
import json
from pathlib import Path
import ssl
import time
import urllib.parse
import urllib.request

from .state import private_write
from .transport import NoRedirect
from .errors import UserError, TVConnectionError, TVNotReady


def connection_closed(error):
    frame = error.rcvd
    if frame and frame.code == 1008 and frame.reason == 'Try Again Later (EWS)':
        return TVNotReady()
    return TVConnectionError('TV remote-control connection closed. Keep the TV on and check its pairing request.',
                             close_code=frame.code if frame else None)


def tv_context(compatible=False):
    # Same LG self-signed local control endpoint used by the existing lgtv.py.
    context = ssl.create_default_context()
    context.check_hostname, context.verify_mode = False, ssl.CERT_NONE
    if compatible:
        # Older TVs offer static RSA with AES-GCM instead of ECDHE/DHE.
        # Keep the default suites first, TLS 1.2 minimum and security level.
        suites = ':'.join(cipher['name'] for cipher in context.get_ciphers())
        context.set_ciphers(suites + ':AES128-GCM-SHA256:AES256-GCM-SHA384')
    return context


def fetch_icon(url):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(),
                                       urllib.request.HTTPSHandler(context=tv_context()))
    with opener.open(url, timeout=5) as response:
        data = response.read(256 * 1024 + 1)
    if not data or len(data) > 256 * 1024:
        raise ValueError('Invalid icon size')
    return data


def include_tuner(launchpoints, installed):
    """Supplement launch points only with the tuner the TV reports installed."""
    if not isinstance(launchpoints, list) or len(launchpoints) > 300 or not isinstance(installed, list) or len(installed) > 300:
        return launchpoints
    for app in installed:
        if (isinstance(app, dict) and app.get('id') == 'com.webos.app.livetv'
                and isinstance(app.get('title'), str) and 0 < len(app['title']) <= 256):
            return [dict(app, hidden=False)] + [a for a in launchpoints
                                               if not isinstance(a, dict) or a.get('id') != app['id']][:299]
    return launchpoints


class Inventory:
    def __init__(self, host, fallback, fetch=fetch_icon):
        self.host, self.fallback, self.fetch = host, fallback, fetch

    def icon(self, app):
        data, kind = self.fallback, 'png'
        for key in ('extraLargeIcon', 'largeIcon', 'mediumLargeIcon', 'icon', 'miniicon', 'favicon'):
            try:
                candidate = app.get(key, '')
                if not isinstance(candidate, str):
                    continue
                url = urllib.parse.urlsplit(candidate)
                if url.scheme not in ('http', 'https') or url.hostname != self.host or url.username or url.password:
                    continue
                if url.port not in (None, 80, 443, 3000, 3001):
                    continue
                data = self.fetch(url.geturl())
                if data.startswith(b'\xff\xd8'):
                    kind = 'jpeg'
                elif data[:4] == b'RIFF' and data[8:12] == b'WEBP':
                    kind = 'webp'
                elif not data.startswith(b'\x89PNG\r\n\x1a\n'):
                    data = self.fallback
                    continue
                break
            except (OSError, ValueError):
                continue
        return 'data:image/' + kind + ';base64,' + base64.b64encode(data).decode()

    def build(self, launchpoints, inputs):
        if not isinstance(launchpoints, list) or not isinstance(inputs, list) or len(launchpoints) > 300 or len(inputs) > 100:
            raise ValueError('Unexpected TV inventory')
        apps, seen = [], set()
        for app in launchpoints:
            if not isinstance(app, dict) or app.get('hidden'):
                continue
            appid, title = app.get('id'), app.get('title')
            if not isinstance(appid, str) or not 0 < len(appid) <= 256 or not isinstance(title, str) or len(title) > 256:
                raise ValueError('Invalid TV application metadata')
            if appid in seen:
                continue
            seen.add(appid)
            apps.append({'id': appid, 'title': title, 'icon': self.icon(app),
                         'iconColor': str(app.get('iconColor') or app.get('bgColor') or '')[:64]})
        devices = []
        for device in inputs:
            if not isinstance(device, dict) or not isinstance(device.get('appId'), str):
                continue
            label = device.get('label') or device.get('id') or device['appId']
            devices.append({'appId': device['appId'][:256], 'label': str(label)[:256]})
        return {'apps': apps, 'inputs': devices}


class SSAP:
    def __init__(self, host, directory, progress=print):
        self.host, self.directory, self.progress = host, Path(directory), progress
        self.counter, self.ws, self.key = 0, None, None

    def __enter__(self):
        from websockets.sync.client import connect
        from websockets.exceptions import ConnectionClosed
        from lgtv import PERMISSIONS
        keyfile = self.directory / 'ssap.json'
        saved = json.loads(keyfile.read_text()) if keyfile.exists() else {}
        payload = {'forcePairing': False, 'pairingType': 'PROMPT',
                   'manifest': {'manifestVersion': 1, 'appVersion': '1.1', 'permissions': PERMISSIONS}}
        if saved.get('key'):
            payload['client-key'] = saved['key']
        try:
            self.ws = connect(f'wss://{self.host}:3001', ssl=tv_context(), open_timeout=10,
                              max_size=8 * 1024 * 1024, proxy=None)
        except ssl.SSLError:
            # Retry only the TLS connection, before sending any pairing data.
            self.ws = connect(f'wss://{self.host}:3001', ssl=tv_context(compatible=True),
                              open_timeout=10, max_size=8 * 1024 * 1024, proxy=None)
        try:
            self.progress('Checking TV remote-control access…' if saved.get('key') else 'Accept the remote-control pairing request on the TV if shown…')
            self.ws.send(json.dumps({'id': 'register_0', 'type': 'register', 'payload': payload}))
            deadline = time.monotonic() + 65
            while time.monotonic() < deadline:
                reply = json.loads(self.ws.recv(timeout=max(0.1, deadline - time.monotonic())))
                if reply.get('type') == 'error':
                    raise UserError('TV pairing was rejected. Check the on-screen request and local network access.')
                if reply.get('type') == 'registered':
                    key = reply.get('payload', {}).get('client-key')
                    if not isinstance(key, str) or not 0 < len(key) <= 1024:
                        raise ValueError('Invalid TV pairing response')
                    self.key = key
                    private_write(keyfile, json.dumps({'key': key}).encode())
                    return self
            raise TVConnectionError('Timed out waiting for the TV pairing request. Keep the TV on and accept it with the remote.',
                                    reason_code='pairing-timeout')
        except ConnectionClosed as exc:
            self.ws.close()
            raise connection_closed(exc) from exc
        except TimeoutError as exc:
            self.ws.close()
            raise TVConnectionError('Timed out waiting for the TV pairing request. Keep the TV on and accept it with the remote.',
                                    reason_code='pairing-timeout') from exc
        except BaseException:
            self.ws.close()
            raise

    def __exit__(self, *args):
        self.ws.close()

    def call(self, uri):
        from websockets.exceptions import ConnectionClosed
        self.counter += 1
        request = 'cytv_' + str(self.counter)
        try:
            self.ws.send(json.dumps({'id': request, 'type': 'request', 'uri': uri, 'payload': {}}))
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                reply = json.loads(self.ws.recv(timeout=max(0.1, deadline - time.monotonic())))
                if reply.get('id') != request:
                    continue
                payload = reply.get('payload', {})
                if reply.get('type') == 'error' or not isinstance(payload, dict) or payload.get('returnValue') is False:
                    raise UserError('TV permission was denied. Check pairing and run cytv doctor.')
                return payload
            raise UserError('Reading TV applications timed out. Keep the TV on and check the connection.')
        except ConnectionClosed as exc:
            raise connection_closed(exc) from exc
        except TimeoutError as exc:
            raise UserError('Reading TV applications timed out. Keep the TV on and check the connection.') from exc

    def inventory(self, fallback):
        points = self.call('ssap://com.webos.applicationManager/listLaunchPoints').get('launchPoints')
        inputs = self.call('ssap://tv/getExternalInputList').get('devices')
        # listLaunchPoints can omit the installed broadcast tuner entirely.
        # Unsupported optional discovery must not break the normal inventory.
        try:
            installed = self.call('ssap://com.webos.applicationManager/listApps')
        except (UserError, json.JSONDecodeError, AttributeError):
            # The wire parser assumes an object; optional malformed JSON or a
            # non-object reply must not discard the successful baseline reads.
            installed = None
        if isinstance(installed, dict) and installed.get('returnValue') is not False:
            points = include_tuner(points, installed.get('apps'))
        return Inventory(self.host, fallback).build(points, inputs)
