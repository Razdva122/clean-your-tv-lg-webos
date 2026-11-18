"""User journeys retain the chosen goal through safe maintenance transitions."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from cytv import cli, state
from cytv.errors import ExistingRoot, UserError
from tests.cytv.test_clean_removal_cli import Capture


class MaintenanceFlowTests(unittest.TestCase):
    def test_no_root_checks_routing_and_helper_after_pairing_and_on_retry(self):
        from tests.cytv.test_operations import OperationTests, Remote

        for scenario, expected, after_pairing in (
            ('unverified-helper', 2, ['routing', 'helper']),
            ('cancel-retry', 130, ['routing', 'helper', 'retry']),
            ('accept-retry', 0, ['routing', 'helper', 'retry', 'routing', 'helper']),
            ('conflict-after-pairing', 2, ['routing']),
            ('conflict-on-retry', 2, ['routing', 'helper', 'retry', 'routing']),
        ):
            with self.subTest(scenario=scenario):
                fixture = OperationTests()
                fixture.setUp()
                self.addCleanup(fixture.doCleanups)
                (fixture.payload / 'fallback.png').write_bytes(b'icon')
                events = []
                routing_conflict = False
                helper = 'CYTV_HELPER_UNCERTAIN' if scenario == 'unverified-helper' else 'CYTV_HELPER_ACTIVE'

                class TV(Remote):
                    def close(self):
                        pass

                    def run(self, command, data=None, timeout=30):
                        if 'CYTV_ROOT_STATE' in command:
                            events.append('routing')
                            return 'CYTV_ROOT_STATE' if routing_conflict else ''
                        if 'CYTV_HELPER_IDLE' in command:
                            events.append('helper')
                            return helper
                        return super().run(command, data, timeout)

                def inventory(*args, **kwargs):
                    nonlocal routing_conflict
                    events.append('pair')
                    routing_conflict = scenario == 'conflict-after-pairing'
                    return fixture.inventory

                def ask(prompt):
                    nonlocal routing_conflict, helper
                    if 'Home button result' in prompt:
                        return '4'
                    self.assertIn('Try stopping Helper again?', prompt)
                    events.append('retry')
                    routing_conflict = scenario == 'conflict-on-retry'
                    helper = 'CYTV_HELPER_IDLE'
                    return 'n' if scenario == 'cancel-retry' else 'y'

                remote = TV()
                output = []
                with patch('cytv.cli.package.verify_payload', return_value=fixture.manifest), \
                     patch('cytv.tv.SSAP') as ssap, \
                     patch('cytv.operations.Installer.stop_helper_for_install', return_value='running') as stop:
                    tv = ssap.return_value.__enter__.return_value
                    tv.inventory.side_effect = inventory
                    tv.key = 'test-key'
                    code = cli.main(['install', '--host', '192.0.2.50', '--edition', 'no-root', '--yes',
                                     '--language', 'en', '--data-dir', str(fixture.store.root)],
                                    ask=ask, connect=lambda *_: remote, write=output.append,
                                    payload_root=fixture.payload)
                self.assertEqual(code, expected, '\n'.join(output))
                expected_events = ['routing', 'pair', *after_pairing]
                self.assertEqual(events[:len(expected_events)], expected_events)
                self.assertEqual(stop.call_count, int('retry' in after_pairing))
                self.assertEqual(remote.calls.count(('run', 'uname -m')), 1)
                self.assertEqual(sum('CYTV_NODE_READY' in entry[1] for entry in remote.calls), 1)
                if code:
                    self.assertEqual(events, expected_events)
                    self.assertFalse(remote.uploads)
                    self.assertFalse(remote.observers)
                    self.assertFalse(remote.installed)
                    self.assertIsNone(fixture.store.pending(state.target('192.0.2.50', 'no-root')))
                else:
                    self.assertTrue(remote.uploads)

    def test_no_root_staging_requires_original_root_ssh_handoff(self):
        from cytv.operations import Installer
        from cytv.root_runtime import FRESH_PROBE
        from tests.cytv.test_operations import Remote

        stamp = dict(operation='a'*32, removal='b'*32, lease='c'*32)
        changed = dict(stamp, lease='d'*32)
        for initial, current in ((None, stamp), (stamp, None), (stamp, changed), (stamp, stamp)):
            with self.subTest(initial=initial, current=current):
                handoff = initial

                class TV(Remote):
                    def run(self, command, **kwargs):
                        if command == FRESH_PROBE:
                            return 'CYTV_RETAINED_ROOT' if handoff else 'CYTV_FRESH_ROOT'
                        return super().run(command, **kwargs)

                profile = state.target('192.0.2.50', 'no-root', connection='root-ssh')
                installer = Installer(TV(), None, profile, '.', {})
                with patch('cytv.root_no_root_handoff.probe', side_effect=lambda _: handoff) as probe, \
                     patch.object(installer, 'helper_state', return_value='stopped') as helper:
                    installer.preflight(install=True, defer_helper=True)
                    handoff = current
                    if initial == current:
                        installer.prepare_install_helper(True)
                        helper.assert_called_once()
                    else:
                        with self.assertRaisesRegex(UserError, 'Previous Root installation needs recovery'):
                            installer.prepare_install_helper(True)
                        helper.assert_not_called()
                    if initial is None:
                        probe.assert_not_called()
                    self.assertEqual(installer._root_handoff, initial)

    def test_legacy_root_updater_offers_confirmed_reinstallation_with_fresh_inventory(self):
        for answer in ('y','n'):
            with self.subTest(answer=answer), tempfile.TemporaryDirectory() as tmp, \
                 patch('cytv.cli.package.verify_payload',return_value={}), \
                 patch('cytv.cli.payload_dir',return_value=Path(tmp)), \
                 patch('cytv.cli.Installer') as cls, patch('cytv.tv.SSAP') as ssap:
                store=state.Store(tmp);profile=state.target('192.0.2.50','root')
                installer=cls.return_value;installer.store=store;installer.profile=profile
                installer.preflight.side_effect=ExistingRoot('Existing Root')
                installer.status.return_value={'deployment_stage':'installed-recovery-only',
                                              'device':{'result':{'recovery':{'integrity_verified':True}}}}
                installer.has_root_updater.return_value=True
                (Path(tmp)/'fallback.png').write_bytes(b'icon')
                installer.root_inventory.return_value={'apps':[{'id':'video','title':'Video'}],'inputs':[]}
                write=Capture()
                result=cli.main(['install','--host',profile['host'],'--edition','root','--yes','--language','en','--data-dir',tmp],
                                ask=lambda prompt:'n' if any(text in prompt for text in ('Customize Clean Your TV?', 'Apply optional Debloat settings?')) else answer,write=write,connect=lambda *a:Mock())
                self.assertEqual(result,0)
                installer.uninstall_project.assert_not_called()
                self.assertEqual(installer.root_inventory.call_count,1 if answer=='y' else 0)
                self.assertEqual(installer.install.call_count,1 if answer=='y' else 0)
                if answer=='y':self.assertEqual(installer.install.call_args.kwargs,{'reinstall':'installed'})
                ssap.assert_not_called()

    def test_explicit_recovery_key_does_not_replace_saved_target_or_host_pin(self):
        for command in ('uninstall', 'recover'):
            with tempfile.TemporaryDirectory() as tmp,patch('cytv.cli.package.verify_payload',return_value={}),patch('cytv.cli.Installer'):
                store=state.Store(tmp);profile=state.target('192.0.2.50','root',2222,identity='/old/key')
                store.save(profile);directory=store.device_dir(profile)
                (directory/'known_hosts').write_bytes(b'original pin');store.request_clean_removal(profile)
                pending=store.pending(profile);connections=[]
                def connect(selected,*args,**kwargs):
                    connections.append((dict(selected),kwargs));raise UserError('Stop before TV work')
                result=cli.main([command,'--host',profile['host'],'--edition','root','--port','2222','--identity',str(Path(tmp)/'new-key'),
                                 '--language','en','--data-dir',tmp],connect=connect,ask=lambda _:'y',write=lambda _:None)
                self.assertNotEqual(result,0)
                self.assertEqual(connections[0][0]['identity'],str((Path(tmp)/'new-key').resolve()))
                self.assertFalse(connections[0][1]['persist'])
                self.assertEqual(store.pending(profile)['removal_operation'],pending['removal_operation'])
                self.assertEqual((directory/'known_hosts').read_bytes(),b'original pin')
                self.assertEqual(store.profiles(),[profile])
