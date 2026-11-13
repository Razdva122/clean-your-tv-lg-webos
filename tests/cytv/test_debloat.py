import json
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from cytv import debloat, diagnostics
from cytv.state import Store


class DebloatTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        profile = {'host': 'tv.local', 'edition': 'root', 'port': 22}
        self.installer = SimpleNamespace(profile=profile, store=Store(self.tmp.name))
        self.record = self.installer.store.device_dir(profile) / 'debloat.json'

    def test_results_explain_write_rejection_only_on_matching_no_root_firmware(self):
        from cytv.desktop import DesktopConsole

        self.installer.profile['edition'] = 'no-root'
        self.installer.remote = SimpleNamespace(
            root=False, run=lambda command, **kwargs: '"off"' if 'livePlus' in command else 'null')
        self.installer.tv_info = {'modelName': '55UK7500PSA', 'firmwareVersion': '05.50.70'}
        for firmware, reply, expected in (
            ('05.50.70', {'returnValue': False}, 'firmware-blocked'),
            ('05.50.70', TimeoutError(), 'failed'),
            ('05.50.71', {'returnValue': False}, 'failed'),
        ):
            with self.subTest(firmware=firmware, reply=reply), patch.object(debloat, 'SSAP') as connect:
                self.installer.tv_info['firmwareVersion'] = firmware
                connect.return_value.__enter__.return_value.call.side_effect = [reply]
                writer = Mock()
                events = {}
                answers = iter(['["homePromotion", "livePlus"]', '1'])
                debloat.run(self.installer, lambda _: next(answers), DesktopConsole(writer), diagnostic=events)
                writer.assert_any_call('debloat-results', {'homePromotion': expected, 'livePlus': 'already'})
                self.assertEqual(events['homePromotion'],
                                 'write-unavailable' if isinstance(reply, Exception) else 'write-rejected')

    def test_result_states_and_journal_precedes_write(self):
        values = {'homePromotion': 'off', 'screenSaverAd': 'on', 'lmt': 'off'}
        writes = []

        def luna(uri, payload, **kwargs):
            if uri.endswith('/getSystemSettings'):
                key, = payload['keys']
                return {'returnValue': True, 'settings': {key: values.get(key)}}
            (key, wanted), = payload['settings'].items()
            writes.append(key)
            entries = json.loads(self.record.read_text())['settings']
            if key in values:
                self.assertEqual(entries[key]['original'], values[key])
            else:
                self.assertNotIn(key, entries)
            if key == 'lmt':
                return {'returnValue': False}
            if key in values:
                values[key] = wanted
            return {'returnValue': True}

        self.installer.remote = SimpleNamespace(root=True, luna=luna)
        result = debloat.apply(self.installer, ['homePromotion', 'screenSaverAd', 'livePlus', 'lmt'])
        self.assertEqual(result, {'homePromotion': 'already', 'screenSaverAd': 'verified',
                                  'livePlus': 'unverified', 'lmt': 'failed'})
        self.assertEqual(writes, ['screenSaverAd', 'livePlus', 'lmt'])
        self.assertEqual(values['screenSaverAd'], 'off')

    def test_no_root_with_root_ssh_writes_and_verifies_through_luna(self):
        self.installer.profile.update(edition='no-root', connection='root-ssh')
        self.installer.remote = SimpleNamespace(root=True)
        with patch.object(self.installer.remote, 'luna', create=True) as luna, patch.object(debloat, 'SSAP') as connect:
            luna.side_effect = [
                {'returnValue': True, 'settings': {'livePromotion': 'on'}},
                {'returnValue': True},
                {'returnValue': True, 'settings': {'livePromotion': 'off'}},
            ]
            self.assertEqual(debloat.apply(self.installer, ['livePromotion']), {'livePromotion': 'verified'})
            connect.assert_not_called()
            self.assertEqual(luna.call_count, 3)
            self.assertEqual(luna.call_args_list[1].args, (
                debloat.SERVICE + 'setSystemSettings', {'category': 'option', 'settings': {'livePromotion': 'off'}}))

    def test_no_root_reads_files_and_sends_only_selected_key_over_ssap(self):
        replies = iter(['null', '"off"'])
        self.installer.profile['edition'] = 'no-root'
        self.installer.profile['port'] = 9922
        self.installer.remote = SimpleNamespace(root=False, run=lambda *a, **kw: next(replies))
        with patch.object(debloat, 'SSAP') as connect:
            ssap = connect.return_value.__enter__.return_value
            ssap.call.return_value = {'returnValue': True}
            self.assertEqual(debloat.apply(self.installer, ['aiNudge']), {'aiNudge': 'verified'})
            ssap.call.assert_called_once_with('ssap://settings/setSystemSettings',
                                              {'category': 'general', 'settings': {'aiNudge': 'off'}},
                                              timeout=8)
        path = self.installer.store.device_dir(self.installer.profile) / 'debloat.json'
        self.assertFalse(path.exists())

    def test_live_plus_falls_back_to_ssap_read_and_skips_already_correct_value(self):
        self.installer.profile.update(edition='no-root', port=9922)
        self.installer.remote = SimpleNamespace(root=False, run=lambda *a, **kw: 'null')
        with patch.object(debloat, 'SSAP') as connect:
            ssap = connect.return_value.__enter__.return_value
            ssap.call.return_value = {'returnValue': True, 'settings': {'livePlus': 'off'}}
            self.assertEqual(debloat.apply(self.installer, ['livePlus']), {'livePlus': 'already'})
            ssap.call.assert_called_once_with('ssap://settings/getSystemSettings',
                                              {'category': 'option', 'keys': ['livePlus']},
                                              timeout=5)

    def test_no_root_permission_denial_does_not_stop_following_setting(self):
        from cytv.errors import UserError

        self.installer.profile.update(edition='no-root', port=9922)
        self.installer.remote = SimpleNamespace(root=False, run=lambda *a, **kw: 'null')
        with patch.object(debloat, 'SSAP') as connect:
            ssap = connect.return_value.__enter__.return_value
            ssap.call.side_effect = [UserError('TV permission was denied.'), {'returnValue': True}]
            self.assertEqual(debloat.apply(self.installer, ['aiNudge', 'sportsAlarm']),
                             {'aiNudge': 'failed', 'sportsAlarm': 'unverified'})
            self.assertEqual(ssap.call.call_count, 2)

    def test_failed_settings_pairing_is_reported_for_each_blocked_write(self):
        self.installer.profile.update(edition='no-root', port=9922)
        self.installer.remote = SimpleNamespace(
            root=False, run=lambda command, **kwargs: '"off"' if 'livePlus' in command else 'null')
        events = {}
        with patch('websockets.sync.client.connect') as connect:
            socket = connect.return_value
            socket.recv.return_value = json.dumps({'type': 'error', 'error': 'private-pairing-details'})
            result = debloat.apply(self.installer, ['livePlus', 'lmt', 'aiNudge'], diagnostic=events)
        self.assertEqual(result, {'livePlus': 'already', 'lmt': 'failed', 'aiNudge': 'failed'})
        self.assertEqual(events, {'livePlus': 'already', 'lmt': 'pairing-rejected', 'aiNudge': 'pairing-rejected'})
        socket.send.assert_called_once()

    def test_write_rejection_and_readback_failures_are_distinct_in_install_report(self):
        self.installer.profile.update(edition='no-root', port=9922)
        self.installer.remote = SimpleNamespace(
            root=False, run=lambda command, **kwargs: 'null' if 'sportsAlarm' in command else '"on"')
        socket = Mock()
        socket.recv.side_effect = [
            json.dumps({'type': 'registered', 'payload': {'client-key': 'private-settings-key'}}),
            json.dumps({'id': 'cytv_1', 'type': 'error', 'error': 'private-response'}),
            json.dumps({'id': 'cytv_2', 'payload': {'returnValue': True}}),
            json.dumps({'id': 'cytv_3', 'payload': {'returnValue': True}}),
        ]
        events = {}
        with patch('websockets.sync.client.connect', return_value=socket), patch.object(debloat.time, 'sleep'):
            result = debloat.apply(self.installer, ['homePromotion', 'aiNudge', 'sportsAlarm'], diagnostic=events)
        self.assertEqual(result, {'homePromotion': 'failed', 'aiNudge': 'failed', 'sportsAlarm': 'unverified'})
        path = diagnostics.create_report(self.installer.store, 'install', self.installer.profile, 'install-complete',
                                         tv_info={'debloat': {**events, 'private-key': 'verified', 'livePlus': 'private-value'}})
        report = path.read_text()
        self.assertEqual(json.loads(report)['debloat'], {
            'homePromotion': 'write-rejected', 'aiNudge': 'verify-mismatch', 'sportsAlarm': 'verify-unavailable',
        })
        self.assertNotIn('private-', report)

    def test_restore_requires_consent_and_keeps_unverified_entries(self):
        from cytv.terminal import Console

        entries = {
            'homePromotion': {'original': 'on', 'target': 'off'},
            'screenSaverAd': {'original': 'on', 'target': 'off'},
            'livePlus': {'original': 'on', 'target': 'off'},
            'sportsAlarm': {'original': 'on', 'target': 'off'},
        }
        self.record.write_text(json.dumps({'schema': 1, 'settings': entries}))
        values = {'homePromotion': 'off', 'screenSaverAd': 'on', 'sportsAlarm': 'off'}
        writes = []

        def luna(uri, payload, **kwargs):
            if uri.endswith('/getSystemSettings'):
                key, = payload['keys']
                return {'returnValue': True, 'settings': {key: values.get(key)}}
            (key, wanted), = payload['settings'].items()
            writes.append((key, wanted))
            if key == 'sportsAlarm':
                return {'returnValue': False}
            values[key] = wanted
            return {'returnValue': True}

        self.installer.remote = SimpleNamespace(root=True, luna=luna)
        output = []
        console = Console(output.append)
        debloat.offer_restore(self.installer.remote, self.installer.store, self.installer.profile, lambda _: '', console)
        self.assertEqual(writes, [])
        self.assertEqual(json.loads(self.record.read_text())['settings'], entries)

        debloat.offer_restore(self.installer.remote, self.installer.store, self.installer.profile, lambda _: 'y', console)
        self.assertEqual(writes, [('homePromotion', 'on'), ('sportsAlarm', 'on')])
        self.assertEqual(json.loads(self.record.read_text())['settings'],
                         {key: entries[key] for key in ('livePlus', 'sportsAlarm')})
        self.assertIn('Restored and verified', ' '.join(output))
        self.assertIn('Could not read the current value', ' '.join(output))

    def test_restore_uses_ssap_for_saved_developer_mode_profile(self):
        self.installer.profile.update(edition='no-root', port=9922)
        record = self.installer.store.device_dir(self.installer.profile) / 'debloat.json'
        record.write_text(json.dumps({'schema': 1, 'settings': {
            'livePlus': {'original': 'on', 'target': 'off'},
        }}))
        self.installer.remote = SimpleNamespace(root=False, run=lambda *a, **kw: 'null')
        with patch.object(debloat, 'SSAP') as connect:
            ssap = connect.return_value.__enter__.return_value
            ssap.call.side_effect = [
                {'returnValue': True, 'settings': {'livePlus': 'off'}},
                {'returnValue': True},
                {'returnValue': True, 'settings': {'livePlus': 'on'}},
            ]
            from cytv.terminal import Console
            debloat.offer_restore(self.installer.remote, self.installer.store, self.installer.profile, lambda _: 'y', Console(lambda _: None))
            self.assertEqual(ssap.call.call_args_list[1].args, (
                'ssap://settings/setSystemSettings', {'category': 'option', 'settings': {'livePlus': 'on'}}))
        self.assertEqual(json.loads(record.read_text())['settings'], {})
