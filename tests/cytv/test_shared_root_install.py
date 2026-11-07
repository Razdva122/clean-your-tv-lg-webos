"""The SSH client consumes the same durable records as the TV entry point."""
import os
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock
from cytv.operations import Installer
from cytv import state


class SharedRootInstallTests(unittest.TestCase):
    def fixture(self, event):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        root=Path(temp.name);store=state.Store(root/'host');profile=state.target('tv.local','root')
        remote=MagicMock();remote.run.return_value=json.dumps(event)
        installer=Installer(remote,store,profile,root,{},lambda *_:None)
        installer._selected_python='/usr/bin/python3';installer._coordinator_code='/tmp/trusted-current-code'
        return installer,remote,store,profile

    def test_status_command_keeps_selected_private_python_and_posix_driver_arguments(self):
        import shlex
        installer,remote,store,profile=self.fixture({'operation':'a'*32,'state':'recovery_required'})
        installer._selected_python='/var/lib/clean-your-tv-python/4a71641c8d5536175e404a961624e8656eba30e97b5026f6bd7dc31e4bbeaaea/bin/python3.13'
        installer._coordinator_code="/tmp/space and ' quote"
        installer.product_action('status','a'*32)
        self.assertEqual(shlex.split(remote.run.call_args.args[0]),[
            'env','-u','PYTHONHOME','-u','PYTHONPATH','PYTHONDONTWRITEBYTECODE=1','PYTHONNOUSERSITE=1',
            '/var/lib/clean-your-tv-python/4a71641c8d5536175e404a961624e8656eba30e97b5026f6bd7dc31e4bbeaaea/bin/python3.13','-B',
            "/tmp/space and ' quote/install_driver.py",'status','--operation','a'*32])
        self.assertEqual(remote.run.call_count,1)

    def test_failed_status_records_host_boundary_without_replaying_or_retiring_pending(self):
        from cytv.errors import TVCommandError
        from cytv.diagnostics import create_report
        from unittest.mock import patch
        for boundary in ('coordinator-stage', 'python-select', 'driver'):
            with self.subTest(boundary=boundary):
                installer,remote,store,profile=self.fixture({})
                store.begin(profile,'install',stage='coordinator-submitted',product_operation='a'*32)
                original=store.pending(profile)
                error=TVCommandError(127)
                stage=patch.object(installer,'coordinator_code',side_effect=error) if boundary=='coordinator-stage' else patch.object(installer,'coordinator_code',return_value='/tmp/private-stage')
                python=patch.object(installer,'_python',side_effect=error) if boundary=='python-select' else patch.object(installer,'_python',return_value='/usr/bin/python3')
                remote.run.side_effect=error
                with stage,python,self.assertRaises(TVCommandError) as caught:
                    installer.product_action('status','a'*32)
                report=json.loads(create_report(store,'status',profile,'status',caught.exception).read_text())
                self.assertEqual(report['ssh_command'],{'exit_status':127,'root_action':'status','root_boundary':boundary})
                self.assertEqual(store.pending(profile),original)
                self.assertLessEqual(remote.run.call_count,1)
                remote.luna.assert_not_called()
                self.assertNotIn('private-stage',json.dumps(report))

    def test_tv_origin_is_inspected_with_current_code_without_reinstall_or_profile_reset(self):
        event={'operation':None,'stage':'inspect','state':'installed','code':'inspected',
               'installation':{'state':'installed','reason':'verified_components','can_install':False,'can_maintain':True}}
        installer,remote,store,profile=self.fixture(event)
        self.assertTrue(installer.root_installation()['can_maintain'])
        command=remote.run.call_args.args[0]
        self.assertIn('/tmp/trusted-current-code/install_driver.py inspect',command)
        self.assertNotIn('/var/lib/clean-your-tv-root/deploy.py',command)
        self.assertIsNone(store.pending(profile));remote.luna.assert_not_called();remote.upload.assert_not_called()

    def test_pending_device_operation_stays_status_only_when_packages_are_absent(self):
        identifier='a'*32
        event={'operation':identifier,'stage':'package-remove-submitting','state':'pending','code':'operation_pending'}
        installer,remote,store,profile=self.fixture(event)
        store.begin(profile,'uninstall',full_project=True,product_operation=identifier)
        installer.installed_apps=MagicMock(return_value=[])
        installer.verify_absent=MagicMock()
        result=installer.status()
        self.assertEqual(result['device']['product'],event);self.assertIsNotNone(result['pending'])
        self.assertIn(' status --operation '+identifier,remote.run.call_args.args[0])
        remote.luna.assert_not_called();installer.verify_absent.assert_not_called()

    def test_verified_setup_offers_separate_explicit_activation(self):
        identifier='a'*32
        event={'operation':identifier,'stage':'complete','state':'complete','code':'verified','current':True,'result':{'installed':'com.cleanyourtv.root.preview','verified':True,'home_changed':False,'baseline_sha':'a'*64}}
        installer,remote,store,profile=self.fixture(event)
        store.begin(profile,'install',product_operation=identifier,requires_updater=True)
        installer.root_action=MagicMock(return_value={'result':{'journal_exists':False,'intent':None,'effective':{'sam_home':'com.webos.app.home','profiles':{'defaultApps':{'categories':{'home':'com.webos.app.home'}},'idleApp':{'appId':'com.webos.app.home','support':True}}},'recovery':{'integrity_verified':True}}})
        installer.verify_root_updater=MagicMock()
        result=installer.status()
        self.assertTrue(result['can_resume_root_setup']);self.assertIsNotNone(store.pending(profile))
        remote.luna.assert_not_called()
        self.assertFalse(any(' enable' in call.args[0] for call in remote.run.call_args_list))

    def test_desktop_import_does_not_load_device_only_posix_modules(self):
        project=Path(__file__).resolve().parents[2]
        code="""import builtins,sys
sys.path.insert(0,sys.argv[1])
original=builtins.__import__
def importing(name,*args,**kwargs):
 if name in ('fcntl','termios'):raise ImportError('device-only module is unavailable')
 return original(name,*args,**kwargs)
builtins.__import__=importing
import cytv.operations
"""
        result=subprocess.run([sys.executable,'-I','-B','-c',code,str(project)],cwd=tempfile.gettempdir(),capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

class ActualCrossClientTests(unittest.TestCase):
    def setUp(self):
        project=Path(__file__).resolve().parents[2]
        sys.path.insert(0,str(project/'root-edition'));sys.path.insert(0,str(project/'root-edition/tests'))
    def fixture(self):
        sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'root-edition/tests'))
        from install_fixture import CurrentInstallation
        return CurrentInstallation()

    def host(self, fixture):
        import shlex
        from install_driver import Coordinator
        from install_device import LocalDevice
        class Transport:
            def run(self,command,**kwargs):
                words=shlex.split(command)
                if 'CYTV_UPDATER_VERIFIED' in command:
                    proof=LocalDevice().readback()
                    if proof['baseline_sha']!=words[-1]:raise AssertionError('different baseline')
                    return 'CYTV_UPDATER_VERIFIED'
                index=next(i for i,w in enumerate(words) if w.endswith('/install_driver.py'));action=words[index+1]
                device=LocalDevice();driver=Coordinator(device,fixture.owner)
                if action=='inspect':
                    inspected=device.inspect();return json.dumps({'operation':None,'state':inspected['state'],'code':'inspected','stage':'inspect','installation':inspected})
                identifier=words[words.index('--operation')+1]
                if action=='install':return json.dumps(driver.install(identifier,fixture.payload))
                if action=='status':
                    event=driver.status(identifier)
                    if '--verify-current' in words:event=dict(event,current=device.validate_completion(event['action'],event.get('lease')))
                    return json.dumps(event)
                raise AssertionError('unexpected transport action')
            def luna(self,uri,payload,**kwargs):
                if uri!='com.cleanyourtv.root.updater.service/status' or kwargs.get('app_id')!='com.cleanyourtv.root.preview':raise AssertionError('unexpected maintenance bus mutation')
                from updater.core import Manager
                return {'returnValue':True,'result':Manager(fixture.up_store,None).status()}
            def upload(self,*args,**kwargs):raise AssertionError('maintenance reset/upload')
        store=state.Store(fixture.base/'host-client');profile=state.target('tv.local','root')
        host=Installer(Transport(),store,profile,fixture.payload,{},lambda *_:None)
        host._selected_python='/usr/bin/python3';host._coordinator_code=str(fixture.payload/'root-updater')
        return host

    @unittest.skipUnless(os.name=='posix','Requires POSIX device filesystem/process fixture')
    def test_tv_to_cytv_uses_real_complete_receipts_and_preserves_profile_off(self):
        from install_driver import Coordinator
        from install_device import LocalDevice
        with self.fixture() as fixture:
            self.assertEqual(LocalDevice().inspect()['state'],'installed')
            self.assertEqual(Coordinator(LocalDevice(),fixture.owner).install('a'*32,fixture.payload)['state'],'complete')
            host=self.host(fixture)
            self.assertTrue(host.root_installation()['can_maintain'])
            host.verify_root_updater(fixture.up_store.read('current')['sha256'])
            self.assertEqual(host.product_action('install','b'*32,str(fixture.payload))['state'],'complete')
            fixture.assert_preserved(self)

    @unittest.skipUnless(os.name=='posix','Requires POSIX device filesystem/process fixture')
    def test_cytv_to_tv_uses_real_complete_receipts_without_resubmission(self):
        from install_driver import Coordinator
        from install_device import LocalDevice
        with self.fixture() as fixture:
            host=self.host(fixture)
            self.assertEqual(host.product_action('install','c'*32,str(fixture.payload))['state'],'complete')
            self.assertEqual(LocalDevice().inspect()['state'],'installed')
            self.assertEqual(Coordinator(LocalDevice(),fixture.owner).install('d'*32,fixture.payload)['state'],'complete')
            fixture.assert_preserved(self)

    @unittest.skipUnless(os.name=='posix','Requires POSIX device filesystem/process fixture')
    def test_component_deletion_and_newer_operation_invalidate_historical_completion(self):
        from install_driver import Coordinator
        from install_device import LocalDevice
        import shutil
        with self.fixture() as fixture:
            driver=Coordinator(LocalDevice(),fixture.owner);event=driver.install('a'*32,fixture.payload)
            self.assertTrue(LocalDevice().validate_completion('install',event['lease']))
            newer=driver.install('b'*32,fixture.payload)
            self.assertFalse(LocalDevice().validate_completion('install',event['lease']))
            shutil.rmtree(fixture.installed/'usr/palm/applications/com.cleanyourtv.root.updater')
            self.assertFalse(LocalDevice().validate_completion('install',newer['lease']))
            self.assertEqual(LocalDevice().inspect()['state'],'recovery_required')

class HistoricalCompletionTests(unittest.TestCase):
    fixture=SharedRootInstallTests.fixture
    def test_historical_complete_without_current_proof_cannot_offer_or_perform_activation(self):
        event={'operation':'a'*32,'state':'complete','stage':'complete','code':'verified','current':False,'result':{'baseline_sha':'b'*64}}
        installer,remote,store,profile=self.fixture(event)
        store.begin(profile,'install',product_operation='a'*32,requires_updater=True)
        installer.root_action=MagicMock()
        self.assertFalse(installer.status()['can_resume_root_setup'])
        from unittest.mock import patch
        with patch('cytv.root_install_recovery.recovery_python',return_value='/usr/bin/python3'),self.assertRaisesRegex(RuntimeError,'continuation'):
            installer.resume_root_setup()
        installer.root_action.assert_not_called();remote.luna.assert_not_called()
        self.assertIsNotNone(store.pending(profile))

    def test_activation_revalidates_after_user_confirmation(self):
        event={'operation':'a'*32,'state':'complete','stage':'complete','code':'verified','current':False,'result':{}}
        installer,remote,store,profile=self.fixture(event)
        store.begin(profile,'activate-root',product_operation='a'*32)
        installer.root_action=MagicMock()
        with self.assertRaisesRegex(RuntimeError,'continuation'):installer.activate_root()
        installer.root_action.assert_not_called();remote.luna.assert_not_called()
