"""User journeys retain the chosen goal through safe maintenance transitions."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from cytv import cli, state
from cytv.errors import ExistingRoot, UserError
from tests.cytv.test_clean_removal_cli import Capture


class MaintenanceFlowTests(unittest.TestCase):
    def test_unverified_helper_state_stops_before_pairing_without_clearing_state(self):
        with tempfile.TemporaryDirectory() as tmp, patch('cytv.cli.package.verify_payload',return_value={}), \
             patch('cytv.cli.payload_dir',return_value=Path(tmp)), patch('cytv.cli.Installer') as cls, patch('cytv.tv.SSAP') as ssap:
            installer=cls.return_value;installer.version_summary.return_value=[]
            installer.preflight.side_effect=UserError('Helper unknown',reason_code='helper-state-unverified')
            result=cli.main(['install','--host','192.0.2.50','--edition','no-root','--yes','--language','en','--data-dir',tmp],
                            ask=Mock(side_effect=AssertionError('No blind retry')),write=lambda _:None,connect=lambda *a:Mock())
            self.assertEqual(result,2);ssap.assert_not_called();installer.install.assert_not_called()

    def test_helper_can_be_stopped_and_rechecked_before_pairing_without_restarting_setup(self):
        for answer in ('y','n'):
            with self.subTest(answer=answer), tempfile.TemporaryDirectory() as tmp, \
                 patch('cytv.cli.package.verify_payload',return_value={}), \
                 patch('cytv.cli.payload_dir',return_value=Path(tmp)), \
                 patch('cytv.cli.Installer') as cls, patch('cytv.tv.SSAP') as ssap:
                events=[];installer=cls.return_value
                def preflight(**kwargs):
                    events.append('preflight')
                    if len(events)==1:raise UserError('Helper active',reason_code='helper-running')
                installer.preflight.side_effect=preflight
                installer.version_summary.return_value=[]
                ssap.side_effect=lambda *args:events.append('pair') or Mock(__enter__=Mock(return_value=Mock(inventory=Mock(return_value={'apps':[]}))),__exit__=Mock(return_value=False))
                (Path(tmp)/'fallback.png').write_bytes(b'icon')
                result=cli.main(['install','--host','192.0.2.50','--edition','no-root','--yes','--language','en','--data-dir',tmp],
                                ask=lambda _:answer,write=lambda _:None,connect=lambda *a:Mock())
                self.assertEqual(result,0)
                self.assertEqual(events,['preflight','preflight','pair'] if answer=='y' else ['preflight'])
                self.assertEqual(installer.install.call_count,1 if answer=='y' else 0)

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
                                ask=lambda _:answer,write=write,connect=lambda *a:Mock())
                self.assertEqual(result,0)
                installer.uninstall_project.assert_not_called()
                self.assertEqual(installer.root_inventory.call_count,1 if answer=='y' else 0)
                self.assertEqual(installer.install.call_count,1 if answer=='y' else 0)
                if answer=='y':self.assertEqual(installer.install.call_args.kwargs,{'reinstall':'installed'})
                ssap.assert_not_called()

    def test_explicit_recovery_key_does_not_replace_saved_target_or_host_pin(self):
        with tempfile.TemporaryDirectory() as tmp,patch('cytv.cli.package.verify_payload',return_value={}),patch('cytv.cli.Installer'):
            store=state.Store(tmp);profile=state.target('192.0.2.50','root',2222,identity='/old/key')
            store.save(profile);directory=store.device_dir(profile)
            (directory/'known_hosts').write_bytes(b'original pin');store.request_clean_removal(profile)
            pending=store.pending(profile);connections=[]
            def connect(selected,*args,**kwargs):
                connections.append((dict(selected),kwargs));raise UserError('Stop before TV work')
            result=cli.main(['uninstall','--host',profile['host'],'--edition','root','--port','2222','--identity',str(Path(tmp)/'new-key'),
                             '--language','en','--data-dir',tmp],connect=connect,write=lambda _:None)
            self.assertNotEqual(result,0)
            self.assertEqual(connections[0][0]['identity'],str((Path(tmp)/'new-key').resolve()))
            self.assertFalse(connections[0][1]['persist'])
            self.assertEqual(store.pending(profile)['removal_operation'],pending['removal_operation'])
            self.assertEqual((directory/'known_hosts').read_bytes(),b'original pin')
            self.assertEqual(store.profiles(),[profile])
