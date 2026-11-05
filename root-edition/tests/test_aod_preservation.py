"""Root activation must preserve unrelated profile and Settings destinations."""
import copy
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'runtime'))
import bounded_profile_trial as trial
import device_adapter as adapter
import profile_recovery as recovery
import transport
from profile_plan import CANDIDATE, STOCK, snapshot


class AodTests(unittest.TestCase):
    def test_activation_and_recovery_preserve_full_maps(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root/'candidate'
            profiles = {'defaultApps': {'categories': {'home': STOCK, 'aod': 'aod.original',
                        'vendor': 'vendor.original'}, 'extra': {'keep': True}},
                        'idleApp': {'support': True, 'appId': STOCK, 'extra': ['keep']}}
            defaults = {'home': STOCK, 'aod': 'aod.original', 'vendor': {'keep': True}}
            original_defaults = copy.deepcopy(defaults)
            original_profiles = copy.deepcopy(profiles)
            writes = []

            def effective():
                result = copy.deepcopy(profiles)
                if target.exists():
                    for name, value in json.loads(target.read_text()).items():
                        # Profile properties merge; categories is replaced as a unit.
                        result[name].update(value)
                return result

            def call(uri, payload, **kwargs):
                if uri.endswith('/getProfiles'):
                    return {'returnValue': True, 'profiles': effective()}
                if uri.endswith('/getSystemSettings'):
                    return {'returnValue': True, 'settings': {'defaultApps': copy.deepcopy(defaults)}}
                if uri.endswith('/setDefaultApp'):
                    writes.append('destructive')
                    defaults.clear(); defaults['home'] = payload['appId']
                elif uri.endswith('/setSystemSettings'):
                    writes.append(copy.deepcopy(payload))
                    defaults.clear(); defaults.update(payload['settings']['defaultApps'])
                elif uri.endswith('/getAppInfo'):
                    return {'returnValue': True, 'appInfo': {'id': CANDIDATE,
                            'type': 'web', 'version': '1.0.0', 'appCategory': ['home']}}
                elif not uri.endswith('/debug/rescan'):
                    self.fail('Unexpected RPC: '+uri)
                return {'returnValue': True}

            class Child:
                pid = 123
                def poll(self): return None

            def spawn(tx):
                journal = adapter.safe_json(root/'profile-trial.json')
                ready = root/'profile-guardian-ready.json'
                ready.write_text(json.dumps({'transaction': tx, 'pid': 123,
                                             'deadline': journal['deadline']}))
                ready.chmod(0o600)
                return Child()

            with patch.object(adapter, 'STATE', root), patch.object(adapter, 'TARGET', target), \
                    patch.object(adapter, 'EXPECTED_UID', os.geteuid()), \
                    patch.object(adapter, 'home_present', return_value=True), \
                    patch.object(adapter, 'sam_transport', return_value=transport), \
                    patch.object(transport, 'call', side_effect=call), \
                    patch('provision.verify', return_value={}), \
                    patch('helper_bridge.require_idle', return_value={}):
                result = trial.begin(spawn)
                expected = copy.deepcopy(original_profiles)
                expected['defaultApps']['categories']['home'] = CANDIDATE
                expected['idleApp']['appId'] = CANDIDATE
                self.assertEqual(result['effective']['profiles'], expected)
                self.assertEqual(defaults, dict(original_defaults, home=CANDIDATE))
                self.assertEqual(profiles, original_profiles)
                active = adapter.safe_json(root/'profile-trial.json')
                self.assertEqual(active['version'], 2)
                self.assertEqual(active['payload_sha256'], hashlib.sha256(target.read_bytes()).hexdigest())
                # An interrupted restore must keep the dynamic payload recoverable.
                with patch.object(adapter, 'read', side_effect=TimeoutError('lost reply')):
                    self.assertEqual(adapter.restore_once(result['transaction']), 'recovering')
                self.assertFalse(target.exists())
                self.assertEqual(adapter.safe_json(root/'profile-trial.json')['version'], 2)
                self.assertEqual(adapter.restore_once(result['transaction']), 'restored')
                self.assertEqual(defaults, original_defaults)
                terminal = adapter.safe_json(root/'profile-trial.json')
                self.assertEqual(terminal['version'], 1)
                self.assertEqual(terminal['payload_sha256'], recovery.DIGEST)
                self.assertEqual(terminal['completed_payload_sha256'], active['payload_sha256'])
                # This is the exact fixed-digest/version predicate of the retained v1 reader.
                self.assertIs(terminal['armed'], True)
                self.assertEqual(terminal['state'], 'restored')
                self.assertEqual(terminal['baseline'], snapshot(
                    {'returnValue': True, 'profiles': original_profiles}, STOCK))
                recovery.validate(terminal)
                # A subsequent trial accepts and archives the terminal record.
                result = trial.begin(spawn)
                self.assertEqual(adapter.restore_once(result['transaction']), 'restored')
            self.assertNotIn('destructive', writes)

    def test_transport_rejects_invalid_map_without_writing(self):
        for defaults in (None, [], {'home': None}, {'home': ''}):
            with self.subTest(defaults=defaults), patch.object(transport, 'call',
                    return_value={'returnValue': True, 'settings': {'defaultApps': defaults}}) as call:
                with self.assertRaises(ValueError): transport.write(CANDIDATE)
                self.assertEqual(call.call_count, 1)
                self.assertTrue(call.call_args.args[0].endswith('/getSystemSettings'))

    def test_settings_readback_must_preserve_unrelated_destinations(self):
        before = {'home': STOCK, 'aod': 'aod.original'}
        after = {'home': CANDIDATE}
        with patch.object(transport, 'call', side_effect=[
                {'returnValue': True, 'settings': {'defaultApps': before}},
                {'returnValue': True},
                {'returnValue': True, 'settings': {'defaultApps': after}}]):
            with self.assertRaisesRegex(RuntimeError, 'readback mismatch'):
                transport.write(CANDIDATE)

    def test_legacy_pending_journal_still_recovers(self):
        from test_root_runtime_profile_recovery import Model
        from test_root_runtime_profile_plan import response
        journal = recovery.prepare(response(), STOCK)
        journal.update(version=1, payload_sha256=recovery.DIGEST)
        model = Model()
        self.assertEqual(recovery.recover(journal, model.remove, model.refresh,
            model.read, model.write, model.save), 'restored')
        self.assertEqual(journal['version'], 1)
        self.assertNotIn('completed_payload_sha256', journal)

    def test_changed_dynamic_payload_is_rejected_before_removal(self):
        from test_root_runtime_profile_recovery import Model
        from test_root_runtime_profile_plan import response
        journal = recovery.prepare(response(), STOCK)
        journal['baseline']['profiles']['defaultApps']['categories']['aod'] = 'changed'
        model = Model()
        with self.assertRaises(ValueError):
            recovery.recover(journal, model.remove, model.refresh,
                             model.read, model.write, model.save)
        self.assertEqual(model.events, [])

    def test_transport_invalid_destination_has_no_effect(self):
        with patch.object(transport, 'call') as call:
            with self.assertRaises(ValueError): transport.write('foreign.home')
            call.assert_not_called()

    def test_lost_write_reply_is_not_retried(self):
        before = {'home': STOCK, 'aod': 'aod.original'}
        reply = {'returnValue': True, 'settings': {'defaultApps': before}}
        with patch.object(transport, 'call', side_effect=[reply, TimeoutError('lost')]) as call:
            with self.assertRaises(TimeoutError): transport.write(CANDIDATE)
            self.assertEqual(call.call_count, 2)
            self.assertEqual(before, {'home': STOCK, 'aod': 'aod.original'})


if __name__ == '__main__': unittest.main()
