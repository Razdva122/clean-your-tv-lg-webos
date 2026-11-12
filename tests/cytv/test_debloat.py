import json
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from cytv import debloat
from cytv.state import Store


class DebloatTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        profile = {'host': 'tv.local', 'edition': 'root', 'port': 22}
        self.installer = SimpleNamespace(profile=profile, store=Store(self.tmp.name))
        self.record = self.installer.store.device_dir(profile) / 'debloat.json'

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
