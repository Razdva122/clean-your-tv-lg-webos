"""Actual C1 bundles/receipts; only the remote device and activation boundary fake."""
import hashlib
import json
from pathlib import Path
import shlex
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock
from cytv import package, state
from cytv.errors import UserError
from cytv import root_gate

BACKEND='c1-native-gate'
NOTICE='C1 Beta: native Home control selected automatically. Power recovery and TV controls are still being tested.'

class Remote:
    def __init__(self):self.calls=[];self.uploads={}
    def run(self,command):
        self.calls.append(command)
        if command.startswith('LC_ALL=C df -Pk '):
            return 'Filesystem 1024-blocks Used Available Capacity Mounted on\n/dev/test 10000000 0 10000000 0% /shared'
    def upload(self,path,data,mode=0o600):self.calls.append(('upload',path,mode));self.uploads[path]=data

class RootGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();self.payload=self.root/'payload';self.payload.mkdir()
        self.variant='root-c1';self.folder=self.payload/self.variant;self.folder.mkdir()
        self.inventory={'apps':[{'id':'com.example.app','name':'Example'}],'inputs':[]}
        app='usr/palm/applications/'+package.ROOT_APP+'/'
        self.ipk=package.ROOT_APP+'_1.2.3_all.ipk'
        files={app+'appinfo.json':json.dumps({'id':package.ROOT_APP,'version':'1.2.3','resolution':'1920x1080'}).encode(),app+'index.html':b'<html>Home</html>'}
        raw=package.ipk(package.ROOT_APP,'1.2.3',files)
        binary=b'fixture: host checks bytes/hash, deployment owns ELF admission'
        release={'application_id':package.ROOT_APP,'version':'1.2.3','home_backend':BACKEND,'experimental':True,'native_sha256':hashlib.sha256(binary).hexdigest(),'files':{n:hashlib.sha256(b).hexdigest() for n,b in files.items()}}
        data={self.ipk:raw,'release.json':json.dumps(release).encode(),'SHA256SUMS':(hashlib.sha256(raw).hexdigest()+'  '+self.ipk+'\n').encode(),'runtime/c1-home-gate':binary,'runtime/c1_gate.py':b'"""fixture"""\n','deploy.py':b'"""fixture"""\n'}
        for name,raw in data.items():p=self.folder/name;p.parent.mkdir(exist_ok=True);p.write_bytes(raw)
        self.refresh()
        self.remote=Remote();self.store=state.Store(self.root/'host');self.profile=state.target('fixture.local','root')
        self.progress=[];self.actions=[]
        self.installer=SimpleNamespace(payload=self.payload,manifest=self.manifest,tv_info={'graphics_resolution':'1920x1080'},store=self.store,profile=self.profile,remote=self.remote,progress=self.progress.append,outcome=SimpleNamespace(packages_verified=Mock()),root_action=self.action,activate_root=self.activate)
        self.installer.product_action=Mock(side_effect=AssertionError('normal coordinator used'))
        self.installer.upload_product=Mock(side_effect=AssertionError('normal product uploaded'))
        self.installer.verify_root_updater=Mock(side_effect=AssertionError('normal updater used'))
        self.failure=None
    def refresh(self):
        files={p.relative_to(self.folder).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in self.folder.rglob('*') if p.is_file() and p.name!='bundle.json'}
        (self.folder/'bundle.json').write_text(json.dumps({'package':self.ipk,'files':files}))
        self.manifest={'root_backends':{BACKEND:{'experimental':True,'hardware_validated':False,'graphics':{'1920x1080':'root-c1','1280x720':'root-c1-720p'}}},'files':{self.variant+'/'+p.relative_to(self.folder).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in self.folder.rglob('*') if p.is_file()}}
        if hasattr(self,'installer'):self.installer.manifest=self.manifest

    def test_generic_admission_cannot_install_legacy_mount_payload(self):
        self.installer.tv_info['home_backend_schema']=3
        with self.assertRaises(UserError):
            root_gate.install(self.installer,self.inventory)
        self.assertIsNone(self.store.pending(self.profile))
        self.assertEqual(self.remote.uploads,{})

    def test_runtime_variant_cannot_cross_normal_and_beta_payloads(self):
        path = self.folder/'release.json'
        original = json.loads(path.read_bytes())
        for profile_variant, release_variant in ((None, 'node012-beta'), ('node012-beta', None)):
            with self.subTest(profile=profile_variant, release=release_variant):
                self.profile.pop('root_variant', None)
                if profile_variant:
                    self.profile['root_variant'] = profile_variant
                release = dict(original)
                if release_variant:
                    release['runtime_variant'] = release_variant
                path.write_text(json.dumps(release))
                self.refresh()
                with self.assertRaises(UserError):
                    root_gate.install(self.installer,self.inventory)
                self.assertEqual(self.remote.uploads,{})
                self.assertIsNone(self.store.pending(self.profile))
    def test_verified_clean_handoff_uses_current_coordinator_without_old_driver_replay(self):
        self.installer._native_clean_install=True
        self.installer.upload_product=Mock(return_value='/tmp/cytv-product-'+'a'*32)
        self.installer.product_action=Mock(return_value={'state':'complete','result':{'returnValue':True,'installed':package.ROOT_APP,'home_changed':False}})
        result=root_gate.install(self.installer,self.inventory)
        self.assertTrue(result['home_changed'])
        self.assertEqual(self.installer.product_action.call_args.args[0],'native-install')
        self.assertNotIn('install',self.actions)

    def action(self,action,**kwargs):
        self.actions.append((action,kwargs))
        if self.failure==action:raise RuntimeError('interrupted '+action)
        if action=='install':
            self.assertTrue(kwargs['experimental']);stage=kwargs['bundle']
            manifest=json.loads(self.remote.uploads[stage+'/bundle.json'])
            raw=self.remote.uploads[stage+'/'+manifest['package']]
            contents=package.data_files(raw)
            self.assertIn(b'com.example.app',contents['usr/palm/applications/'+package.ROOT_APP+'/apps.js'])
            self.assertFalse(any('root-updater' in p for p in self.remote.uploads))
            return {'returnValue':True,'installed':package.ROOT_APP,'home_changed':False}
        if action=='status':return {'returnValue':True,'result':{'backend':BACKEND,'recovery':{'integrity_verified':self.failure!='integrity'},'effective':{'returnValue':True,'backend':BACKEND,'profiles':None,'stock_verified':self.failure!='stock-proof','mounted':False,'healthy':False,'guardian_pid':0}}}
        raise AssertionError(action)
    def activate(self):
        pending=self.store.pending(self.profile);self.assertEqual(pending['action'],'activate-root');self.assertEqual(pending['home_backend'],BACKEND);self.assertFalse(pending['requires_updater'])
        if self.failure=='activation':raise RuntimeError('activation interrupted')
        self.store.finish(self.profile)
        return True
    def test_intended_flow_personalizes_and_uses_only_native_component(self):
        result=root_gate.install(self.installer,self.inventory,False,None)
        self.assertEqual([a for a,_ in self.actions],['install','status']);self.assertTrue(result['home_changed']);self.assertFalse(result['updates_ready']);self.assertTrue(result['beta']);self.assertEqual(result['backend'],BACKEND)
        self.assertIsNone(self.store.pending(self.profile));self.installer.outcome.packages_verified.assert_called_once()
        self.assertIn(NOTICE,self.progress)
        marker=json.loads((self.store.device_dir(self.profile)/'installation.json').read_text());self.assertEqual(marker['home_backend'],BACKEND)
    def test_migrate_reinstall_and_unknown_resolution_refuse_before_effects(self):
        for migrate,reinstall in [(True,None),(False,'installed'),(False,'removed')]:
            with self.subTest(migrate=migrate,reinstall=reinstall),self.assertRaises(UserError):root_gate.install(self.installer,self.inventory,migrate,reinstall)
        self.installer.tv_info['graphics_resolution']='unknown'
        with self.assertRaises(UserError):root_gate.install(self.installer,self.inventory,False,None)
        self.assertEqual(self.remote.calls,[]);self.assertEqual(self.actions,[]);self.assertIsNone(self.store.pending(self.profile))
    def test_corrupt_payload_refuses_before_upload_or_pending(self):
        (self.folder/'runtime/c1-home-gate').write_bytes(b'changed')
        with self.assertRaises(UserError):root_gate.install(self.installer,self.inventory,False,None)
        self.assertEqual(self.remote.calls,[]);self.assertIsNone(self.store.pending(self.profile))
    def test_backend_flags_native_hash_and_graphics_are_strict(self):
        release_path=self.folder/'release.json';original=json.loads(release_path.read_text())
        for field,value in [('home_backend','system-profile'),('experimental',False),('native_sha256','0'*64),('application_id','com.other.app')]:
            release_path.write_text(json.dumps(dict(original,**{field:value})));self.refresh()
            with self.subTest(field=field),self.assertRaises(UserError):root_gate.install(self.installer,self.inventory,False,None)
            self.assertEqual(self.remote.calls,[]);self.assertIsNone(self.store.pending(self.profile))
        release_path.write_text(json.dumps(original));self.refresh();self.manifest['root_backends'][BACKEND]['experimental']=1
        with self.assertRaises(UserError):root_gate.install(self.installer,self.inventory,False,None)
    def test_unsafe_manifest_path_or_symlink_refuses_before_effects(self):
        manifest=json.loads((self.folder/'bundle.json').read_text());manifest['files']['../outside']='0'*64
        (self.folder/'bundle.json').write_text(json.dumps(manifest));self.manifest['files'][self.variant+'/bundle.json']=hashlib.sha256((self.folder/'bundle.json').read_bytes()).hexdigest()
        with self.assertRaises(UserError):root_gate.install(self.installer,self.inventory,False,None)
        self.assertEqual(self.remote.calls,[]);self.assertIsNone(self.store.pending(self.profile))
    def test_failures_retain_exact_pending_and_never_retry_or_fall_back(self):
        for failure in ['install','integrity','activation']:
            self.failure=failure
            with self.subTest(failure=failure),self.assertRaises((RuntimeError,UserError)):root_gate.install(self.installer,self.inventory,False,None)
            pending=self.store.pending(self.profile);self.assertEqual(pending['home_backend'],BACKEND);self.assertFalse(pending['requires_updater']);self.assertNotIn('product_operation',pending)
            self.installer.product_action.assert_not_called();self.installer.upload_product.assert_not_called();self.installer.verify_root_updater.assert_not_called()
            self.store.finish(self.profile)
    def test_prior_pending_refuses_even_when_bundle_is_valid(self):
        self.store.begin(self.profile,'install',stage='uncertain');before=self.store.pending(self.profile)
        with self.assertRaises(UserError):root_gate.install(self.installer,self.inventory,False,None)
        self.assertEqual(self.store.pending(self.profile),before);self.assertEqual(self.remote.calls,[])
    def test_bad_install_readback_never_activates(self):
        self.installer.root_action=Mock(return_value={'returnValue':True,'installed':package.ROOT_APP,'home_changed':True});self.installer.activate_root=Mock()
        with self.assertRaises(UserError):root_gate.install(self.installer,self.inventory,False,None)
        self.installer.activate_root.assert_not_called();self.assertIsNotNone(self.store.pending(self.profile))
    def test_720p_native_variant_selected_explicitly(self):
        contents=package.data_files((self.folder/self.ipk).read_bytes());app='usr/palm/applications/'+package.ROOT_APP+'/appinfo.json';info=json.loads(contents[app]);info['resolution']='1280x720';contents[app]=json.dumps(info).encode();(self.folder/self.ipk).write_bytes(package.ipk(package.ROOT_APP,'1.2.3',contents));release_path=self.folder/'release.json';release=json.loads(release_path.read_text());release['files']={name:hashlib.sha256(raw).hexdigest() for name,raw in contents.items()};release_path.write_text(json.dumps(release));self.variant='root-c1-720p';self.folder.rename(self.payload/self.variant);self.folder=self.payload/self.variant;self.refresh();self.installer.tv_info['graphics_resolution']='1280x720'
        result=root_gate.install(self.installer,self.inventory,False,None);self.assertEqual(result['backend'],BACKEND)

    def test_activation_launch_result_does_not_fabricate_duplicate_request(self):
        self.installer.activate_root=lambda:False
        result=root_gate.install(self.installer,self.inventory,False,None)
        self.assertIs(result['launch_requested'],False)
    def test_invalid_stock_proof_blocks_before_packages_verified_or_activation(self):
        self.failure='stock-proof';self.installer.activate_root=Mock()
        with self.assertRaises(UserError):root_gate.install(self.installer,self.inventory,False,None)
        self.installer.outcome.packages_verified.assert_not_called();self.installer.activate_root.assert_not_called();self.assertIsNotNone(self.store.pending(self.profile))
    def test_package_readback_identity_is_verified_before_upload(self):
        path=self.folder/self.ipk;contents=package.data_files(path.read_bytes());app='usr/palm/applications/'+package.ROOT_APP+'/appinfo.json';info=json.loads(contents[app]);info['id']='com.wrong.app';contents[app]=json.dumps(info).encode();path.write_bytes(package.ipk(package.ROOT_APP,'1.2.3',contents));self.refresh()
        with self.assertRaises(UserError):root_gate.install(self.installer,self.inventory,False,None)
        self.assertEqual(self.remote.calls,[]);self.assertIsNone(self.store.pending(self.profile))
    def removal_fixture(self):
        self.installer.verify_project_startup_removed=Mock()
        self.installer.installed_apps=Mock(return_value=[{'id':package.ROOT_APP}])
        self.installer.status=Mock(return_value={'deployment_stage':'uninstalled-state-retained'})
        def uninstall(full_project=False):
            self.assertIs(full_project,False);self.installer.installed_apps.return_value=[]
            return {'removed':package.ROOT_APP,'state_retained':'/var/lib/clean-your-tv-root'}
        self.installer.uninstall=Mock(side_effect=uninstall)
    def test_lone_native_root_full_removal_verifies_stock_and_absence(self):
        self.removal_fixture();result=root_gate.remove_project(self.installer)
        self.assertTrue(result['removed']);self.assertTrue(result['applications_services_startup_removed']);self.installer.uninstall.assert_called_once_with(full_project=False)
    def test_other_project_apps_refuse_full_removal_before_any_mutation(self):
        self.removal_fixture()
        for app in root_gate.PROJECT_APPS-{package.ROOT_APP}:
            self.installer.installed_apps.return_value=[{'id':package.ROOT_APP},{'id':app}]
            with self.subTest(app=app),self.assertRaises(UserError):root_gate.remove_project(self.installer)
        self.installer.uninstall.assert_not_called();self.assertEqual(self.actions,[]);self.assertEqual(self.remote.calls,[])
    def test_uncertain_prior_removal_never_resubmits(self):
        self.removal_fixture();self.store.begin(self.profile,'uninstall',stage='uncertain')
        with self.assertRaises(UserError):root_gate.remove_project(self.installer)
        self.installer.status.assert_called_once();self.installer.uninstall.assert_not_called();self.assertIsNotNone(self.store.pending(self.profile))
    def test_terminal_prior_removal_is_status_only_even_after_recovery_rollback(self):
        self.removal_fixture();self.store.begin(self.profile,'uninstall',stage='removing');self.installer.installed_apps.return_value=[]
        def status():
            self.store.finish(self.profile);return {'deployment_stage':'uninstalled-state-retained'}
        self.installer.status.side_effect=status;self.failure='integrity'
        result=root_gate.remove_project(self.installer);self.assertTrue(result['removed']);self.installer.uninstall.assert_not_called()
    def test_removal_postcheck_cannot_claim_stock_when_proof_is_missing(self):
        self.removal_fixture();self.failure='stock-proof'
        with self.assertRaises(UserError):root_gate.remove_project(self.installer)
        self.installer.uninstall.assert_called_once()
    def test_orphan_startup_hook_blocks_full_removal_success_with_empty_inventory(self):
        self.removal_fixture()
        self.installer.verify_project_startup_removed.side_effect=UserError('Project startup or service registrations remain. Removal is not complete.')
        with self.assertRaises(UserError):root_gate.remove_project(self.installer)
        self.assertEqual(self.installer.installed_apps.return_value,[])
        self.installer.verify_project_startup_removed.assert_called_once()
if __name__=='__main__':unittest.main()
