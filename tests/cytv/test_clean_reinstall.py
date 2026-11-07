"""Regression for verified clean removal followed by normal Root installation."""
import unittest
from unittest.mock import Mock
from tests.cytv import test_operations
from cytv.errors import ExistingRoot

CLEAN={'state':'fresh','reason':'verified_removal','can_install':True,
       'can_maintain':False,'clean_removal_verified':True}

class CleanReinstallTests(unittest.TestCase):
    setUp=test_operations.OperationTests.setUp
    installer=test_operations.OperationTests.installer
    root_bundle=test_operations.OperationTests.root_bundle

    def fixture(self):
        self.root_bundle();remote=test_operations.Remote();run=remote.run
        remote.run=lambda command,**kw: 'CYTV_EXISTING_ROOT' if 'CYTV_EXISTING_ROOT' in command else ('{"stage":"cancellation-admitted"}' if 'deploy.json' in command else run(command,**kw))
        inst=self.installer(remote,'root');inst.root_installation=Mock(return_value=dict(CLEAN))
        return inst,remote

    def test_blocked_shared_inspection_has_fixed_error_not_key_error(self):
        inst,remote=self.fixture()
        del inst.root_installation
        inst.product_action=Mock(return_value={'state':'recovery_required','stage':'blocked'})
        from cytv.errors import UserError
        with self.assertRaises(UserError) as caught:inst.root_installation()
        self.assertEqual(caught.exception.reason_code,'root-operation-unconfirmed')

    def test_reinstalled_project_apps_explain_cleanup_without_retired_execution(self):
        inst,remote=self.fixture();del inst.root_installation
        inst.product_action=Mock(return_value={'state':'recovery_required','stage':'blocked','reason':'project-apps-remain'})
        inst.root_action=Mock(side_effect=AssertionError('retired driver'))
        from cytv.errors import UserError
        for operation in (inst.root_installation,inst.status,lambda:inst.preflight(install=True),inst.restore_device):
            with self.subTest(operation=operation),self.assertRaises(UserError) as caught:operation()
            self.assertEqual(caught.exception.reason_code,'project-apps-remain')
            self.assertIn('Uninstall Clean Your TV',str(caught.exception))
            self.assertIn('No-root Home and Helper',str(caught.exception))
            self.assertIn('back up',str(caught.exception))
            self.assertIsNone(self.store.pending(inst.profile))
        inst.root_action.assert_not_called()

    def test_stale_support_requests_restart_without_retired_restore(self):
        inst,remote=self.fixture();del inst.root_installation
        inst.product_action=Mock(return_value={'state':'recovery_required','stage':'blocked','reason':'restart-required'})
        inst.root_action=Mock(side_effect=AssertionError('retired driver'))
        from cytv.errors import UserError
        for operation in (lambda:inst.preflight(install=True),inst.restore_device):
            with self.subTest(operation=operation),self.assertRaises(UserError) as caught:operation()
            self.assertEqual(caught.exception.reason_code,'restart-required')
        inst.root_action.assert_not_called()

    def test_preflight_accepts_only_current_verified_clean_removal(self):
        inst,remote=self.fixture();inst.preflight(install=True,home_interfaces=True)
        self.assertIsNone(self.store.pending(inst.profile))
        inst.root_installation.return_value=dict(CLEAN,clean_removal_verified=False)
        with self.assertRaises(ExistingRoot):inst.preflight(install=True,home_interfaces=True)

    def test_native_beta_keeps_fresh_only_guard_before_effects(self):
        inst,remote=self.fixture();inst.tv_info['home_backend']='c1-native-gate'
        with self.assertRaises(ExistingRoot):inst.preflight(install=True)
        self.assertIsNone(self.store.pending(inst.profile))

    def test_unverified_clean_restore_keeps_existing_recovery_path(self):
        inst,remote=self.fixture()
        inst.root_installation.return_value=dict(CLEAN,clean_removal_verified=False)
        inst.root_action=Mock(return_value={'restored':True})
        self.assertEqual(inst.restore_device(),{'restored':True})
        inst.root_action.assert_called_once_with('restore')

    def test_status_and_restore_do_not_execute_retired_driver(self):
        inst,remote=self.fixture();inst.root_action=Mock(side_effect=AssertionError('retired driver'))
        self.assertEqual(inst.status()['deployment_stage'],'verified-clean')
        self.assertTrue(inst.restore_device()['already_removed'])
        inst.root_action.assert_not_called()

class RootInventoryTests(unittest.TestCase):
    def fixture(self, result):
        import tempfile,json
        from pathlib import Path
        from cytv.operations import Installer
        from cytv.state import Store,target
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        remote=Mock();remote.run.return_value=json.dumps(result)
        inst=Installer(remote,Store(t.name),target('192.0.2.10','root'),Path(t.name),{})
        inst.coordinator_code=Mock(return_value='/tmp/cytv-coordinator-'+'a'*32)
        return inst,remote

    def test_root_reads_current_fixed_catalog_and_inputs_without_ssap(self):
        app={'id':'video','title':'Video','icon':'','iconColor':'red','hidden':False}
        inst,remote=self.fixture([[app,dict(app,title='duplicate'),dict(app,id='hidden',hidden=True)],{'returnValue':True,'devices':[{'appId':'hdmi','label':'HDMI'}]}])
        result=inst.root_inventory(b'fallback')
        self.assertEqual(len(result['apps']),1)
        self.assertTrue(result['apps'][0]['icon'].startswith('data:image/png;base64,'))
        self.assertEqual(result['inputs'],[{'appId':'hdmi','label':'HDMI'}]);self.assertNotIn('iconColor',result['apps'][0])
        self.assertEqual(remote.run.call_args.args[0],'/usr/bin/node')
        self.assertIn(b'/app-inventory.js',remote.run.call_args.kwargs['data'])
        self.assertIsNone(inst.store.pending(inst.profile))

    def test_invalid_or_empty_root_catalog_stops_before_install(self):
        for result in [[],[[],{'returnValue':True,'devices':[]}],[[{'id':None,'title':'bad'}],{'returnValue':True,'devices':[]}],[[],{'returnValue':False}]]:
            inst,remote=self.fixture(result)
            with self.subTest(result=result),self.assertRaises((ValueError,RuntimeError)):inst.root_inventory(b'fallback')
            self.assertIsNone(inst.store.pending(inst.profile))

class RootInventoryCLITests(unittest.TestCase):
    def test_root_install_uses_ssh_catalog_without_ssap_pairing(self):
        import tempfile
        from tests.cytv.test_cli import CLITests
        from unittest.mock import patch,MagicMock
        from pathlib import Path
        inventory={'apps':[{'id':'video','title':'Video'}],'inputs':[]}
        with tempfile.TemporaryDirectory() as tmp,patch('cytv.cli.payload_dir',return_value=Path(tmp)),patch('cytv.cli.Installer') as cls,patch('cytv.cli.package.verify_payload',return_value={}),patch('cytv.tv.SSAP') as ssap:
            (Path(tmp)/'fallback.png').write_bytes(b'fallback')
            cls.return_value.root_inventory.return_value=inventory
            code,output,_=CLITests.run_cli(self,['install','--host','192.0.2.10','--edition','root','--data-dir',tmp,'--yes'],remote=MagicMock())
            self.assertEqual(code,0,output);ssap.assert_not_called()
            cls.return_value.install.assert_called_once_with(inventory,None,False)

if __name__=='__main__':unittest.main()
