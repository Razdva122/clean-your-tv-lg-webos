"""Fixed System-only replacement: original evidence is preserved across faults."""
from contextlib import contextmanager
import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest

if os.name!='posix':raise unittest.SkipTest('TV System replacement requires POSIX locks')

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'root-edition'))
from updater.store import Store
from installation import Ownership

class Tests(unittest.TestCase):
    def setUp(self):
        try:self.module=importlib.import_module('cytv.system_updater_replace')
        except ModuleNotFoundError:self.fail('System-only replacement coordinator is missing')
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base=Path(os.path.realpath(self.tmp.name));self.store=Store(self.base/'installation',uid=os.getuid());self.ownership=Ownership(self.store)
        self.calls=[]
    def test_replacement_never_uses_root_package_removal(self):
        self.assertTrue(hasattr(self.module,'SCRIPT'))
        namespace={'__name__':'replacement_test'};exec(self.module.support_source(),namespace);exec(self.module.SCRIPT,namespace)
        self.assertEqual(namespace['APP'],'com.cleanyourtv.system.updater')
        self.assertNotIn('com.cleanyourtv.root.preview',namespace['remove_system'].__code__.co_consts)
    def test_wrong_bundle_is_rejected_before_remote_replacement(self):
        bundle=self.base/'bundle';bundle.mkdir();(bundle/'bundle.json').write_text(json.dumps({'schema':1,'supervisor':1,'files':{'system-updater.ipk':'0'*64,'setup-system-updater.py':'1'*64}}))
        (bundle/'system-updater.ipk').write_bytes(b'wrong');(bundle/'setup-system-updater.py').write_bytes(b'wrong')
        with self.assertRaises(ValueError):self.module.program(bundle)


    def test_real_built_target_reaches_device_preflight(self):
        import importlib.util
        from unittest.mock import patch
        def load(name):
            spec=importlib.util.spec_from_file_location('replacement_admission_'+name,ROOT/'system-updater'/(name+'.py'))
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
        setup=load('setup');build=load('build');bundle=self.base/'actual-system-bundle';build.build(bundle)
        namespace={'__name__':'replacement_admission'}
        exec(self.module.support_source(),namespace);exec(self.module.SCRIPT,namespace)
        class DevicePreflightReached(Exception):pass
        def device_preflight(*args):raise DevicePreflightReached()
        with patch.dict(namespace,{'old_proof':device_preflight}):
            with self.assertRaises(DevicePreflightReached):
                namespace['replace'](bundle,setup,None,None,self.store,self.ownership,None,None,None)
        self.assertIsNone(self.store.read('system-replacement'))
        self.assertIsNone(self.ownership.status())


class FlowFixture:
    """Shared replacement fixture; version variants explicitly inherit FlowTests."""
    def setUp(self):
        from cytv import system_updater_replace as module
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.base=Path(os.path.realpath(self.tmp.name))
        self.ns={'__name__':'replacement_flow'};exec(module.support_source(),self.ns);exec(module.SCRIPT,self.ns)
        self.bundle=self.base/'bundle';self.bundle.mkdir(mode=0o700);self.system=self.base/'system';self.installed=self.base/'sdk';self.installed.mkdir()
        self.root=self.base/'root';self.root.mkdir();self.root_marker=self.root/'root-code';self.root_marker.write_bytes(b'Root remains exact');self.profile=self.root/'user-profile';self.profile.write_bytes(b'personal layout')
        self.home=self.root/'persistent-intent.json';self.home.write_text('{"enabled":false,"phase":"disabled"}');self.home.chmod(0o600)
        self.override=self.root/'owned-override.json';self.ns.update(HOME_OVERRIDE=self.override,HOME_FILES=(self.home,self.override))
        self.calls=[];self.fault=None;self.removals=0
        self.refreshes=[]
        stock='com.webos.app.home'
        self.runtime_status={'intent':{'enabled':False,'phase':'disabled'},'effective':{'sam_home':stock,
                             'profiles':{'defaultApps':{'categories':{'home':stock}},'idleApp':{'appId':stock,'support':True}}}}
        self.store=Store(self.base/'installation',uid=os.getuid());self.ownership=Ownership(self.store)
        self.meta=self.make_bundle(self.bundle)
        self.make_system(self.system,self.bundle)
        self.appdir=self.installed/'usr/palm/applications'/self.ns['APP'];self.appdir.mkdir(parents=True);(self.appdir/'version').write_text('1.1.0')
        env=self
        class Device:
            def __init__(self,store,code=None):self.store=store;self.code=code;self.uid=os.getuid();self.root_updater=env.root/'updater'
            def integrity(self,**kw):env.ns['original_code'](Path(self.store.root))
            def require_components(self):
                if not env.appdir.is_dir():raise ValueError('System removed')
            def _root_integrity(self):
                if env.root_marker.read_bytes()!=b'Root remains exact':raise ValueError('Root proof changed')
            def installed(self,app):raise ValueError('Foreign application')
            def runtime(self,mode):
                env.assertEqual(mode,'status')
                return env.runtime_status
            def owner_identity(self,app):
                if app!=env.ns['APP']:raise ValueError('Foreign owner')
                return {'id':app,'version':(env.appdir/'version').read_text()}
        class Manager:
            def __init__(self):self.store=Store(env.system,uid=os.getuid());self.io=Device(self.store,code=env.system/'code')
            def _load(self):return self.store.read('transaction')
            def _profile(self,tx):return self.store.read(tx['profile'])
        self.manager=Manager()
        self.cleanup=types.SimpleNamespace(operate=self.cleanup_action,stop=lambda code:None)
        self.setup=types.SimpleNamespace(verify_bundle=self.verify_bundle,package_files=lambda raw:{k:v.encode() for k,v in json.loads(raw).items()},safe=lambda p:Path(p).read_bytes(),snapshot=self.snapshot,verify_baseline=self.verify_baseline,installed_data=lambda p,*args:Path(p).read_bytes(),infrastructure_readback=lambda item,raw:None,INSTALLED=self.installed,provision=self.provision,resume=self.resume)
    def make_bundle(self,path,version='1.2.9'):
        import hashlib
        data={name:b'' for name in ['installation.py','package_identity.py','system_updater/core.py','system_updater/device.py','system_updater/support/store.py']}
        data['setup-system-updater.py']=b'# trusted setup';data['system-updater.ipk']=json.dumps({'usr/palm/applications/'+self.ns['APP']+'/appinfo.json':json.dumps({'id':self.ns['APP'],'version':version})}).encode()
        for name,raw in data.items():
            p=path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);p.chmod(0o600)
        meta={'schema':1,'supervisor':1,'health_lock_wait_seconds':10,'files':{n:hashlib.sha256(b).hexdigest() for n,b in data.items()}};(path/'bundle.json').write_text(json.dumps(meta));(path/'bundle.json').chmod(0o600);return meta
    def make_system(self,state,bundle):
        import shutil,hashlib
        state.mkdir(mode=0o700,exist_ok=True);store=Store(state,uid=os.getuid());(state/'code').mkdir(exist_ok=True)
        meta=json.loads((bundle/'bundle.json').read_text());code={n:h for n,h in meta['files'].items() if n not in ('system-updater.ipk','setup-system-updater.py')}
        for name in code:
            target=state/'code'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(bundle/name,target);target.chmod(0o600)
        raw=(bundle/'system-updater.ipk').read_bytes();sha=hashlib.sha256(raw).hexdigest();(state/'cache').mkdir(exist_ok=True);(state/'cache'/(sha+'.ipk')).write_bytes(raw);(state/'cache'/(sha+'.ipk')).chmod(0o600)
        store.write('bootstrap-bundle',{'schema':1,'bundle':meta,'package':{'sha256':sha,'size':len(raw)}});store.write('infrastructure',{'schema':1,'code':code});store.write('registration',{'files':{}})
    def verify_bundle(self,bundle,*,historical_manifest=None):
        import hashlib
        meta=json.loads((Path(bundle)/'bundle.json').read_bytes() if historical_manifest is None else historical_manifest)
        for n,h in meta['files'].items():
            if hashlib.sha256((Path(bundle)/n).read_bytes()).hexdigest()!=h:raise ValueError('Bundle changed')
        return meta
    def snapshot(self,bundle,edition,output):
        import hashlib
        self.calls.append('capture');output=Path(output);output.mkdir();(output/'cache').mkdir()
        raw=json.dumps({str(self.root_marker.relative_to(self.installed)):'unused'}) if self.root_marker.is_relative_to(self.installed) else json.dumps({'../root/root-code':'Root remains exact'})
        # A fixed test boundary maps actual baseline data to the Root marker.
        raw=json.dumps({'root-marker':'Root remains exact'}).encode();sha=hashlib.sha256(raw).hexdigest();(output/'cache'/sha).write_bytes(raw)
        value={'components':[{'name':'root','kind':'ipk','sha256':sha,'size':len(raw)}]};(output/'baseline.json').write_text(json.dumps(value));(output/'baseline.json').chmod(0o600)
        self.setup.installed_data=lambda path,*args:self.root_marker.read_bytes()
        if self.fault=='capture':raise KeyboardInterrupt('captured partial private staging')
    def verify_baseline(self,baseline,bundle):
        import hashlib
        value=json.loads((Path(baseline)/'baseline.json').read_text())
        for c in value['components']:
            raw=(Path(baseline)/'cache'/c['sha256']).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=c['sha256']:raise ValueError('Baseline changed')
        return value
    def cleanup_action(self,action,**kw):
        self.calls.append(action);state=Path(kw['state'])
        if action=='status':return {'present':True,'ownership_verified':True,'bootstrap_complete':True,'edition':'root','disabled':False}
        if action=='disable':
            Store(state,uid=os.getuid()).write('cytv-removal',{'phase':'disabled','archive':kw['destination']})
            if self.fault=='disable':raise KeyboardInterrupt('disable interrupted')
            return {'disabled':True}
        state.rename(kw['destination'])
        if self.fault=='archive':raise KeyboardInterrupt('archive committed before response')
        return {'removed':True}
    def remove(self,app,**kw):
        import shutil
        self.assertEqual(app,self.ns['APP']);self.removals+=1;self.calls.append('sdk-remove');shutil.rmtree(self.appdir)
        if self.fault=='remove':raise KeyboardInterrupt('submission outcome unknown')
        return {'completed':True,'event':{'details':{'packageId':app}}}
    def provision(self,bundle,baseline,refresh=None):
        self.refreshes.append(refresh)
        self.calls.append('provision');self.make_system(self.system,bundle)
        files = self.setup.package_files(self.setup.safe(Path(bundle)/'system-updater.ipk'))
        info = json.loads(files['usr/palm/applications/'+self.ns['APP']+'/appinfo.json'])
        self.appdir.mkdir(parents=True, exist_ok=True)
        (self.appdir/'version').write_text(info['version'])
        if self.fault=='provision':raise KeyboardInterrupt('new bootstrap in progress')
        return {'installed':True}
    def resume(self,bundle,refresh=None):
        self.refreshes.append(refresh)
        self.calls.append('resume');self.verify_bundle(bundle);return {'installed':True}
    def run_replacement(self,bundle=None,source_sha='a'*64,**options):
        return self.ns['replace'](bundle or self.bundle,self.setup,self.cleanup,self.manager,self.store,self.ownership,self.remove,lambda t,a:t.get('completed') is True and t['event']['details']['packageId']==a,lambda owner:None,system=self.system,source_sha=source_sha,**options)

class FlowTests(FlowFixture, unittest.TestCase):
    def test_other_target_versions_are_rejected_before_device_changes(self):
        for version in ('1.2.1','1.2.2','1.2.3','1.2.4','1.2.5','1.2.6','1.2.7','1.2.8','1.2.12'):
            with self.subTest(version=version):
                self.make_bundle(self.bundle,version=version)
                with self.assertRaisesRegex(ValueError,'supported System Updater bundle'):
                    self.run_replacement()
                self.assertEqual(self.calls,[]);self.assertEqual(self.removals,0)
                self.assertIsNone(self.store.read('system-replacement'))
                self.assertIsNone(self.ownership.status())
    def test_success_captures_first_and_removes_only_supervisor(self):
        result=self.run_replacement();self.assertTrue(result['installed']);self.assertEqual(result['version'],'1.2.9');self.assertTrue(result['profile_storage_untouched']);self.assertEqual(self.removals,1)
        self.assertLess(self.calls.index('capture'),self.calls.index('disable'));self.assertLess(self.calls.index('sdk-remove'),self.calls.index('archive'))
        self.assertEqual(self.profile.read_bytes(),b'personal layout');self.assertEqual(self.home.read_text(),'{"enabled":false,"phase":"disabled"}')
        self.assertTrue(self.ownership.status()['terminal']);self.assertTrue(Path(result['archive']).is_dir())
    def test_unknown_removal_never_replays(self):
        self.fault='remove'
        with self.assertRaises(KeyboardInterrupt):self.run_replacement()
        self.fault=None
        with self.assertRaisesRegex(ValueError,'unknown'):self.run_replacement()
        self.assertEqual(self.removals,1)
    def test_resume_after_archive_response_loss_preserves_old_state(self):
        self.fault='archive'
        with self.assertRaises(KeyboardInterrupt):self.run_replacement()
        self.fault=None;self.assertTrue(self.run_replacement()['installed']);self.assertEqual(self.removals,1)
    def test_resume_partial_new_provision_uses_existing_resume(self):
        self.fault='provision'
        with self.assertRaises(KeyboardInterrupt):self.run_replacement()
        self.fault=None;self.assertTrue(self.run_replacement()['installed']);self.assertEqual(self.calls.count('provision'),1);self.assertEqual(self.calls.count('resume'),1)
    def test_same_bundle_required_after_interruption(self):
        self.fault='disable'
        with self.assertRaises(KeyboardInterrupt):self.run_replacement()
        self.fault=None
        with self.assertRaisesRegex(ValueError,'same verified'):self.run_replacement(source_sha='b'*64)
        (self.bundle/'bundle.json').write_text(json.dumps({**self.meta,'notes':'different bundle'}))
        with self.assertRaisesRegex(ValueError,'same verified'):self.run_replacement()
        self.assertEqual(self.removals,0)
    def test_changed_root_bytes_stops_before_disable(self):
        self.root_marker.write_bytes(b'changed')
        with self.assertRaises(ValueError):self.run_replacement()
        self.assertNotIn('disable',self.calls);self.assertEqual(self.removals,0)
    def test_foreign_retained_lease_is_not_bypassed(self):
        self.store.write('operation',{'schema':1,'id':'b'*32,'owner':'root-update','journal':'transaction.json','stage':'verifying','terminal':False})
        with self.assertRaises(RuntimeError):self.run_replacement()
        self.assertEqual(self.removals,0)

    def test_stale_self_consistent_bundle_without_fixed_marker_is_rejected(self):
        meta=json.loads((self.bundle/'bundle.json').read_text());meta.pop('health_lock_wait_seconds');(self.bundle/'bundle.json').write_text(json.dumps(meta))
        with self.assertRaises(ValueError):self.run_replacement()
        self.assertEqual(self.removals,0);self.assertNotIn('disable',self.calls)
    def test_damaged_archive_blocks_resumed_provision_before_effects(self):
        self.fault='provision'
        with self.assertRaises(KeyboardInterrupt):self.run_replacement()
        self.fault=None;job=self.store.read('system-replacement');archive=Path(job['archive']);(archive/'registration.json').write_text('{"changed":true}')
        before=self.calls.count('resume')
        with self.assertRaises(ValueError):self.run_replacement()
        self.assertEqual(self.calls.count('resume'),before)
    def test_corrupt_journal_archive_and_stage_are_rejected(self):
        self.fault='disable'
        with self.assertRaises(KeyboardInterrupt):self.run_replacement()
        self.fault=None;job=self.store.read('system-replacement');job['archive']='/foreign/archive';self.store.write('system-replacement',job)
        with self.assertRaises(ValueError):self.run_replacement()
        self.assertEqual(self.removals,0)
    def test_completed_repeat_does_not_remove_or_provision_again(self):
        self.run_replacement();before=(self.removals,self.calls.count('provision'))
        self.assertTrue(self.run_replacement()['installed']);self.assertEqual((self.removals,self.calls.count('provision')),before)

    def test_capture_and_disable_interruptions_resume_without_root_changes(self):
        self.fault='capture'
        with self.assertRaises(KeyboardInterrupt):self.run_replacement()
        self.assertNotIn('disable',self.calls);self.fault='disable'
        with self.assertRaises(KeyboardInterrupt):self.run_replacement()
        self.fault=None;self.assertTrue(self.run_replacement()['installed']);self.assertEqual(self.removals,1)
        self.assertEqual(self.profile.read_bytes(),b'personal layout')
    def test_existing_legacy_restore_snapshot_blocks_before_disable(self):
        root_updater=self.root/'updater';root_updater.mkdir();(root_updater/'transaction.json').write_text('{"phase":"complete"}')
        with self.assertRaisesRegex(ValueError,'legacy Root backup'):self.run_replacement()
        self.assertNotIn('disable',self.calls);self.assertEqual(self.removals,0)
    def test_changed_original_system_registration_refuses_resumed_removal(self):
        self.fault='disable'
        with self.assertRaises(KeyboardInterrupt):self.run_replacement()
        self.fault=None;Store(self.system,uid=os.getuid()).write('registration',{'changed':True})
        with self.assertRaises(ValueError):self.run_replacement()
        self.assertEqual(self.removals,0)

class SelfUpdatingBaselineTests(FlowFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.make_bundle(self.bundle,version='1.2.11')
        (self.appdir/'version').write_text('1.2.10')

    def test_preceding_supervisor_replacement_preserves_product_and_settings(self):
        result=self.run_replacement()
        self.assertEqual(result['version'],'1.2.11')
        self.assertEqual(self.removals,1)
        self.assertEqual(self.profile.read_bytes(),b'personal layout')
        self.assertEqual(self.root_marker.read_bytes(),b'Root remains exact')

    def test_old_broken_transition_is_not_newly_admitted(self):
        (self.appdir/'version').write_text('1.2.9')
        with self.assertRaisesRegex(ValueError,'not supported'):
            self.run_replacement()
        self.assertEqual(self.removals,0)

    def test_active_home_blocks_baseline_replacement(self):
        self.runtime_status['intent']={'enabled':True,'phase':'active'}
        with self.assertRaises(ValueError):self.run_replacement()
        self.assertEqual(self.removals,0)


class StockHomeFlowTests(FlowFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.make_bundle(self.bundle, version='1.2.10')
        (self.appdir/'version').write_text('1.2.9')

    def test_unverified_stock_home_refuses_before_reservation(self):
        for check in ('intent', 'override', 'sam', 'profile', 'idle', 'idle-support'):
            with self.subTest(check=check):
                self.doCleanups()
                self.setUp()
                effective=self.runtime_status['effective']
                if check=='intent':self.runtime_status['intent']={'enabled':True,'phase':'active'}
                if check=='override':self.override.write_text('retained override')
                if check=='sam':effective['sam_home']='com.cleanyourtv.root.preview'
                if check=='profile':effective['profiles']['defaultApps']['categories']['home']='unknown'
                if check=='idle':effective['profiles']['idleApp']['appId']='unknown'
                if check=='idle-support':effective['profiles']['idleApp']['support']=False
                with self.assertRaisesRegex(ValueError, 'Return to LG Home'):
                    self.run_replacement()
                self.assertIsNone(self.ownership.status())
                self.assertIsNone(self.store.read('system-replacement'))
                self.assertNotIn('disable',self.calls)
                self.assertEqual(self.removals,0)

    def test_stock_home_replacement_and_resume_forward_scan_only_callback(self):
        self.runtime_status['intent']=None
        def refresh():
            pass
        self.fault='provision'
        with self.assertRaises(KeyboardInterrupt):
            self.run_replacement(refresh=refresh)
        self.fault=None
        self.assertEqual(self.run_replacement(refresh=refresh)['version'],'1.2.10')
        self.assertEqual(self.refreshes,[refresh,refresh])
        self.assertEqual(self.removals,1)


class Retained111FlowTests(FlowTests):
    """Run interruption/integrity coverage against the retained public owner."""
    def setUp(self):
        super().setUp()
        (self.appdir/'version').write_text('1.1.1')

    def check_terminal_profile_archive(self,phase):
        saved=Store(self.system,uid=os.getuid());profile='profile-'+'c'*32
        saved.write(profile,{'layout':{'apps':['synthetic']}})
        saved.write('transaction',{'edition':'root','phase':phase,'homeResumePhase':phase,'profile':profile})
        original_profile=(self.system/(profile+'.json')).read_bytes()
        original_transaction=(self.system/'transaction.json').read_bytes()
        result=self.run_replacement();archive=Path(result['archive'])
        self.assertEqual((archive/(profile+'.json')).read_bytes(),original_profile)
        self.assertEqual((archive/'transaction.json').read_bytes(),original_transaction)
        self.assertEqual(self.profile.read_bytes(),b'personal layout')
        self.assertEqual((self.appdir/'version').read_text(),'1.2.9')

    def test_completed_transaction_profile_is_archived_unchanged(self):
        self.check_terminal_profile_archive('complete')

    def test_rolled_back_transaction_profile_is_archived_unchanged(self):
        self.check_terminal_profile_archive('rolled-back')

    def test_unfinished_home_resume_refuses_before_reservation(self):
        Store(self.system,uid=os.getuid()).write('transaction',{'edition':'root','phase':'complete','homeResumePhase':'pending'})
        with self.assertRaisesRegex(ValueError,'existing System recovery'):
            self.run_replacement()
        self.assertEqual(self.calls,[]);self.assertEqual(self.removals,0)
        self.assertIsNone(self.store.read('system-replacement'))
        self.assertIsNone(self.ownership.status())

    def test_unrecognized_owners_refuse_before_reservation(self):
        for version in ('1.0.0','1.1.2','1.1.10','1.2.1','1.2.2','1.2.3','1.2.4','1.2.5','1.2.6','1.2.7','1.2.8','1.2.9','2.0.0','unknown'):
            with self.subTest(version=version):
                (self.appdir/'version').write_text(version)
                with self.assertRaisesRegex(ValueError,'System Updater'):
                    self.run_replacement()
                self.assertEqual(self.calls,[]);self.assertEqual(self.removals,0)
                self.assertIsNone(self.store.read('system-replacement'))
                self.assertIsNone(self.ownership.status())

class HistoricalReplacementTests(FlowFixture, unittest.TestCase):
    def historical(self):
        import shutil
        self.run_replacement()
        job=self.store.read('system-replacement');root=Path(self.store.root)/('system-replacement-'+job['id'])
        historical_bundle=root/'bundle'
        raw=json.loads((historical_bundle/'system-updater.ipk').read_bytes())
        key='usr/palm/applications/'+self.ns['APP']+'/appinfo.json'
        raw[key]=json.dumps({'id':self.ns['APP'],'version':'1.1.1'})
        (historical_bundle/'system-updater.ipk').write_text(json.dumps(raw))
        meta=json.loads((historical_bundle/'bundle.json').read_bytes())
        meta['files']['system-updater.ipk']=self.ns['digest']((historical_bundle/'system-updater.ipk').read_bytes())
        (historical_bundle/'bundle.json').write_text(json.dumps(meta))
        job['bundle_sha256']=self.ns['digest']((historical_bundle/'bundle.json').read_bytes())
        job['source_sha256']='d'*64;self.store.write('system-replacement',job)
        shutil.rmtree(self.system);self.make_system(self.system,historical_bundle)
        (self.appdir/'version').write_text('1.1.1')
        self.store.write('operation',{'schema':1,'id':'e'*32,'owner':'system-update','journal':'transaction.json','stage':'complete','terminal':True})
        self.calls=[];self.removals=0
        return job,root
    def test_completed_historical_owner_can_start_new_verified_replacement(self):
        old,root=self.historical();raw=(Path(self.store.root)/'system-replacement.json').read_bytes()
        self.assertTrue(self.run_replacement()['installed'])
        self.assertEqual((root/'completed-replacement.json').read_bytes(),raw)
        self.assertNotEqual(self.store.read('system-replacement')['id'],old['id'])
        self.assertTrue(Path(old['archive']).is_dir());self.assertEqual(self.removals,1)
    def test_published_supervisor_can_migrate_after_completed_replacement(self):
        self.run_replacement()
        old = self.store.read('system-replacement')
        root = Path(self.store.root) / ('system-replacement-' + old['id'])
        bundle = self.bundle.parent / 'new-bundle'
        self.make_bundle(bundle, version='1.2.10')
        result = self.run_replacement(bundle)
        self.assertEqual(result['version'], '1.2.10')
        self.assertTrue(result['root_unchanged'])
        self.assertTrue(result['home_unchanged'])
        self.assertTrue(result['profile_storage_untouched'])
        self.assertTrue((root / 'completed-replacement.json').is_file())

    def fresh_root_bootstrap(self):
        import shutil
        historical, root = self.historical()
        shutil.rmtree(historical['archive'])
        shutil.rmtree(self.system)
        self.make_system(self.system, self.bundle)
        (self.appdir/'version').write_text('1.2.9')
        raw = (self.bundle/'system-updater.ipk').read_bytes()
        files = self.setup.package_files(raw)
        for name, data in files.items():
            path = self.installed/name
            path.write_bytes(data)
        self.setup.installed_data = lambda path, *args: Path(path).read_bytes()
        active = Store(self.system, uid=os.getuid())
        binding = active.read('bootstrap-bundle')
        active.write('installed-package', {'schema': 1, 'package': dict(binding['package'], version='1.2.9', local=True),
                     'files': {name: self.ns['digest'](raw) for name, raw in files.items()}})
        active.write('installed-terminal', {'completed': True, 'event': {'id': self.ns['APP'], 'statusValue': 30,
                     'details': {'packageId': self.ns['APP'], 'client': 'com.webos.lunasend-123',
                                 'ipkFile': '/var/lib/clean-your-tv-installer/cytv-root-install-test/package.ipk'}}})
        active.write('bootstrap', {'phase': 'complete', 'edition': 'root', 'hardware_validated': False})
        active.write('baseline', {'edition': 'root'})
        self.store.write('operation', {'schema': 1, 'id': 'f'*32, 'owner': 'system-bootstrap',
                         'journal': 'bootstrap.json', 'stage': 'complete', 'terminal': True})
        bundle = self.bundle.parent/'new-bundle'
        self.make_bundle(bundle, version='1.2.10')
        return historical, root, active, bundle

    def test_completed_pre_engine_bundle_can_retire_after_fresh_bootstrap(self):
        import runpy
        from cytv.package import ipk

        history, root, _, _ = self.fresh_root_bootstrap()
        bundle = root / 'bundle'
        # File inventory used by the published System Updater 1.2.10 bundle.
        names = """
            startup_hook.py package_data.py package_identity.py startup_guard.py
            installation.py python_boot.js python_binding.py infrastructure-paths.json
            system_updater/__init__.py system_updater/support/__init__.py
            system_updater/core.py system_updater/device.py system_updater/cli.py
            system_updater/policy.js system_updater/release-public.pem
            system_updater/ca-bundle.crt system_updater/ca-LICENSE.txt
            system_updater/support/store.py system_updater/support/package.py
            system_updater/support/profile.py system_updater/support/luna.py
            observed_install.py installer_status.py service.js run-system-updater.py
            services.json package.json setup-system-updater.py
        """.split()
        app = self.ns['APP']
        files = {name: name.encode() for name in names}
        files['system-updater.ipk'] = ipk(app, '1.2.10', {
            f'usr/palm/applications/{app}/appinfo.json':
                json.dumps({'id': app, 'version': '1.2.10'}).encode()
        })
        for name, data in files.items():
            path = bundle / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        manifest = {
            'schema': 1, 'supervisor': 1, 'health_lock_wait_seconds': 10,
            'files': {name: self.ns['digest'](raw) for name, raw in files.items()}
        }
        manifest_path = bundle / 'bundle.json'
        manifest_path.write_text(json.dumps(manifest))
        history['bundle_sha256'] = self.ns['digest'](manifest_path.read_bytes())
        (self.appdir / 'version').write_text('1.2.10')

        setup = runpy.run_path(str(ROOT / 'system-updater/setup.py'))
        for name in ('verify_bundle', 'package_files', 'safe'):
            setattr(self.setup, name, setup[name])

        def verify_history():
            return self.ns['completed_evidence'](
                history, self.setup, self.manager, self.store, self.system,
                lambda receipt, _: receipt.get('completed') is True, fresh=True)

        with self.assertRaisesRegex(ValueError, 'Unexpected supervisor bundle inventory'):
            self.setup.verify_bundle(bundle)
        self.assertEqual(verify_history(), root / 'completed-replacement.json')

        manifest['files'].pop('service.js')
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'Historical replacement bundle changed'):
            verify_history()
        history['bundle_sha256'] = self.ns['digest'](manifest_path.read_bytes())
        with self.assertRaisesRegex(ValueError, 'Unexpected supervisor bundle inventory'):
            verify_history()

        manifest['files']['service.js'] = self.ns['digest'](files['service.js'])
        manifest_path.write_text(json.dumps(manifest))
        history['bundle_sha256'] = self.ns['digest'](manifest_path.read_bytes())
        (bundle / 'service.js').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'Supervisor bundle hash mismatch'):
            verify_history()

    def test_same_replacement_bundle_is_eligible_after_fresh_published_bootstrap(self):
        history, root, _, bundle = self.fresh_root_bootstrap()
        self.make_bundle(root/'bundle', version='1.2.10')
        history['bundle_sha256'] = self.ns['digest']((root/'bundle/bundle.json').read_bytes())
        self.assertEqual(history['bundle_sha256'], self.ns['digest']((bundle/'bundle.json').read_bytes()))
        self.store.write('system-replacement', history)
        result = self.run_replacement(bundle, source_sha='b'*64)
        self.assertEqual(result['version'], '1.2.10')
        self.assertTrue(result['home_unchanged'])
        self.assertEqual(self.removals, 1)
        self.assertTrue((root/'completed-replacement.json').exists())

    def test_fresh_verified_root_bootstrap_retires_history_with_missing_archive(self):
        from unittest.mock import patch
        for point in ('reservation', 'active-journal'):
            with self.subTest(point=point):
                self.doCleanups()
                self.setUp()
                historical, root, active, bundle = self.fresh_root_bootstrap()
                old = (Path(self.store.root)/'system-replacement.json').read_bytes()
                write = Store.write

                def interrupt(store, name, value):
                    result = write(store, name, value)
                    if ((point == 'reservation' and name == 'operation' and value['stage'] == 'reserved')
                            or (point == 'active-journal' and name == 'system-replacement' and value['stage'] == 'capture')):
                        raise KeyboardInterrupt('reservation written before response')
                    return result

                with patch.object(Store, 'write', new=interrupt):
                    with self.assertRaises(KeyboardInterrupt):
                        self.run_replacement(bundle)
                self.assertEqual(self.removals, 0)
                self.assertEqual(self.ownership.status()['stage'], 'reserved')
                if point == 'reservation':
                    self.assertEqual((Path(self.store.root)/'system-replacement.json').read_bytes(), old)
                    self.assertFalse((root/'completed-replacement.json').exists())
                else:
                    self.assertEqual((root/'completed-replacement.json').read_bytes(), old)
                    self.assertEqual(self.store.read('system-replacement')['stage'], 'capture')
                with self.assertRaises(ValueError):
                    self.run_replacement(bundle, source_sha='9'*64)
                terminal = active.read('installed-terminal')
                changed = dict(terminal, event=dict(terminal['event'], details=dict(terminal['event']['details'], client='com.webos.lunasend-124')))
                active.write('installed-terminal', changed)
                with self.assertRaises(ValueError):
                    self.run_replacement(bundle)
                self.assertEqual(self.removals, 0)
                active.write('installed-terminal', terminal)
                self.assertEqual(self.run_replacement(bundle)['version'], '1.2.10')
                self.assertEqual((root/'completed-replacement.json').read_bytes(), old)
                self.assertFalse(Path(historical['archive']).exists())
                self.assertEqual(self.removals, 1)

    def test_fresh_bootstrap_rejects_incomplete_or_damaged_evidence_before_mutation(self):
        for damage in ('bootstrap', 'terminal', 'binding', 'package', 'payload', 'owner', 'archive', 'still-live'):
            with self.subTest(damage=damage):
                self.doCleanups()
                self.setUp()
                historical, root, active, bundle = self.fresh_root_bootstrap()
                if damage == 'bootstrap':
                    active.write('bootstrap', {'phase': 'accepted-supervisor', 'edition': 'root'})
                elif damage == 'terminal':
                    active.write('installed-terminal', {'completed': False})
                elif damage == 'binding':
                    active.write('bootstrap-bundle', dict(active.read('bootstrap-bundle'), schema=2))
                elif damage == 'package':
                    pin = active.read('bootstrap-bundle')['package']['sha256']
                    (self.system/'cache'/(pin+'.ipk')).write_bytes(b'wrong package')
                elif damage == 'payload':
                    (self.appdir/'appinfo.json').write_bytes(b'wrong SDK payload')
                elif damage == 'owner':
                    self.store.write('operation', dict(self.ownership.status(), owner='system-update'))
                elif damage == 'archive':
                    Path(historical['archive']).mkdir()
                else:
                    self.make_system(self.system, root/'bundle')
                    (self.appdir/'version').write_text('1.1.1')
                with self.assertRaises((ValueError, OSError)):
                    self.run_replacement(bundle)
                self.assertEqual(self.removals, 0)
                self.assertNotIn('disable', self.calls)
                self.assertFalse((root/'completed-replacement.json').exists())

    def test_historical_proof_damage_never_retires_or_disables(self):
        for damage in ('archive','bundle','baseline','owner','foreign-active','foreign-aborted','collision','unfinished','source-only'):
            with self.subTest(damage=damage):
                self.doCleanups();self.setUp();old,root=self.historical()
                if damage=='archive':(Path(old['archive'])/'registration.json').write_text('{}')
                elif damage=='bundle':(root/'bundle/bundle.json').write_text('{}')
                elif damage=='baseline':(root/'baseline/baseline.json').write_text('{}')
                elif damage=='owner':(self.appdir/'version').write_text('1.1.2')
                elif damage=='foreign-active':
                    op=self.store.read('operation');op['terminal']=False;self.store.write('operation',op)
                elif damage=='foreign-aborted':
                    op=self.store.read('operation');op['stage']='aborted';self.store.write('operation',op)
                elif damage=='collision':(root/'completed-replacement.json').write_text('{}')
                elif damage=='unfinished':old['stage']='verify';self.store.write('system-replacement',old)
                else:old['bundle_sha256']=self.ns['digest']((self.bundle/'bundle.json').read_bytes());self.store.write('system-replacement',old)
                before=(Path(self.store.root)/'system-replacement.json').read_bytes()
                with self.assertRaises((ValueError,RuntimeError,KeyError)):self.run_replacement()
                self.assertEqual((Path(self.store.root)/'system-replacement.json').read_bytes(),before)
                self.assertEqual((root/'completed-replacement.json').exists(),damage=='collision');self.assertNotIn('disable',self.calls)
    def test_interruption_before_and_after_atomic_retirement_is_resumable(self):
        from unittest.mock import patch
        for when in ('before','after'):
            with self.subTest(when=when):
                self.doCleanups();self.setUp();old,root=self.historical()
                rename=self.ns['os'].rename
                def interrupted(source,target):
                    if Path(target).name=='completed-replacement.json':
                        if when=='after':rename(source,target)
                        raise KeyboardInterrupt('retirement response lost')
                    return rename(source,target)
                with patch.object(self.ns['os'],'rename',side_effect=interrupted):
                    with self.assertRaises(KeyboardInterrupt):self.run_replacement()
                self.assertEqual(self.removals,0)
                self.assertTrue(self.run_replacement()['installed']);self.assertEqual(self.removals,1)
                self.assertTrue((root/'completed-replacement.json').is_file())

    def test_retirement_startup_rejects_changed_coordinator_source(self):
        from unittest.mock import patch
        old,root=self.historical();rename=self.ns['os'].rename
        def interrupted(source,target):
            rename(source,target)
            if Path(target).name=='completed-replacement.json':raise KeyboardInterrupt('archive committed before new active journal')
        with patch.object(self.ns['os'],'rename',side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt):self.run_replacement()
        with self.assertRaises(ValueError):self.run_replacement(source_sha='f'*64)
        self.assertEqual(self.removals,0)
        self.assertTrue(self.run_replacement()['installed'])

    def test_plan_pending_and_active_write_interruptions_pin_source_and_resume(self):
        from unittest.mock import patch
        for point in ('plan-after','pending-after','active-before','active-after'):
            with self.subTest(point=point):
                self.doCleanups();self.setUp();old,root=self.historical()
                lease=self.store.read('operation');write=Store.write
                def interrupted(store,name,value):
                    hit=(point=='plan-after' and name=='next-replacement' or point=='pending-after' and name=='pending-replacement'
                         or point.startswith('active-') and name=='system-replacement' and value.get('stage')=='capture')
                    if hit and point=='active-before':raise KeyboardInterrupt('before active journal')
                    result=write(store,name,value)
                    if hit:raise KeyboardInterrupt('durable write before response')
                    return result
                with patch.object(Store,'write',new=interrupted):
                    with self.assertRaises(KeyboardInterrupt):self.run_replacement()
                self.assertTrue((Path(self.store.root)/'system-replacement.json').is_file())
                self.assertEqual(self.removals,0)
                if point=='plan-after':self.assertEqual(self.store.read('operation'),lease)
                with self.assertRaises(ValueError):self.run_replacement(source_sha='f'*64)
                self.assertEqual(self.removals,0)
                self.assertTrue(self.run_replacement()['installed']);self.assertEqual(self.removals,1)

class BoundaryTests(unittest.TestCase):
    def test_real_device_installed_rejects_own_system_app(self):
        name='replacement_original_protocol'
        package=types.ModuleType(name);package.__path__=[str(ROOT/'system-updater')]
        support=types.ModuleType(name+'.support');support.__path__=[str(ROOT/'root-edition/updater')]
        sys.modules[name]=package;sys.modules[name+'.support']=support
        self.addCleanup(lambda:[sys.modules.pop(k,None) for k in list(sys.modules) if k==name or k.startswith(name+'.')])
        device=importlib.import_module(name+'.device').Device
        with self.assertRaisesRegex(ValueError,'Foreign application'):
            device.installed(object(),'com.cleanyourtv.system.updater')

    def test_original_cleanup_validators_disable_and_archive_only_supervisor(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('replacement_removal_fixture',ROOT/'tests/system_updates/test_remove.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve();args=module.RemovalTests().fixture(root)
            personal=root/'root-profile';personal.write_bytes(b'keep me')
            self.assertTrue(module.namespace['operate']('status',**args)['ownership_verified'])
            disabled=module.namespace['operate']('disable',**args);self.assertTrue(disabled['disabled'])
            self.assertTrue(module.namespace['operate']('archive',**args)['removed'])
            self.assertEqual(personal.read_bytes(),b'keep me');self.assertTrue(Path(disabled['archive']).is_dir())
    def test_real_snapshot_preflight_and_replacement_readback_use_original_root_receipts(self):
        import importlib.util,functools
        from unittest.mock import patch
        sys.path.insert(0,str(ROOT/'root-edition/tests'))
        from install_fixture import CurrentInstallation
        def load(name):
            spec=importlib.util.spec_from_file_location('replacement_real_'+name,ROOT/'system-updater'/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
        from cytv.system_updater_replace import SCRIPT,support_source
        scope={'__name__':'replacement_boundary'};exec(support_source(),scope);exec(SCRIPT,scope)
        with CurrentInstallation() as fixture:
            setup=load('setup');build=load('build');bundle=fixture.base/'new-system-bundle';build.build(bundle)
            roots={'runtime':fixture.root/'runtime','updater':fixture.updater/'code','service':fixture.root/'service'}
            baseline=setup.snapshot(bundle,'root',fixture.base/'baseline',installed=fixture.installed,**roots)
            destination=setup.infrastructure_destination
            with patch.object(setup,'INSTALLED',fixture.installed),patch.object(setup,'ROOT_UPDATER_TRANSACTION',fixture.updater/'transaction.json'),patch.object(setup,'infrastructure_destination',side_effect=functools.partial(destination,**roots)):
                from cytv.system_updater_replace import program
                compile(program(bundle),'<verified replacement program>','exec')
                setup.preflight(bundle,baseline,state=fixture.base/'absent-system',installed=fixture.installed,base=fixture.base/'bus',hook=fixture.base/'absent-hook')
                scope['baseline_readback'](setup,baseline,bundle)
                marker=fixture.installed/'usr/palm/applications/com.cleanyourtv.root.preview/index.html';marker.write_bytes(b'changed bytes')
                with self.assertRaises(ValueError):scope['baseline_readback'](setup,baseline,bundle)
    def test_installer_uses_untouched_root_python_and_no_host_pending_on_refusal(self):
        from cytv import operations,state
        from cytv.errors import UserError
        from unittest.mock import MagicMock,patch
        with tempfile.TemporaryDirectory() as temporary:
            store=state.Store(Path(temporary)/'host');profile=state.target('192.0.2.10','root');remote=MagicMock();remote.root=True
            installer=operations.Installer(remote,store,profile,Path(temporary),{})
            with patch('cytv.system_updater_replace.program',return_value='trusted script'),patch.object(installer,'_python',return_value='/usr/bin/python3') as python:
                remote.run.side_effect=RuntimeError('preflight rejected before changes')
                with self.assertRaises(UserError):installer.replace_system_updater()
                self.assertIsNone(store.pending(profile));python.assert_called_once_with(operations.ROOT_STATE)
                remote.run.side_effect=None
                remote.run.return_value=json.dumps({'reason':'stock-home-required'})
                with self.assertRaisesRegex(UserError,'Return to LG Home'):
                    installer.replace_system_updater()
                self.assertIsNone(store.pending(profile))
                remote.run.return_value=json.dumps({'installed':True,'version':'1.2.9','root_unchanged':True,'home_unchanged':True,'profile_storage_untouched':True})
                self.assertTrue(installer.replace_system_updater()['installed']);self.assertIsNone(store.pending(profile))
                remote.run.return_value=json.dumps({'installed':True,'version':'1.2.1','root_unchanged':True,'home_unchanged':True,'profile_storage_untouched':True})
                with self.assertRaises(UserError):installer.replace_system_updater()
                self.assertIsNone(store.pending(profile))
            remote.upload.assert_not_called()


class ProcessTests(unittest.TestCase):
    def setUp(self):
        from cytv.system_updater_replace import SCRIPT,support_source
        self.ns={'__name__':'replacement_process_test'};exec(support_source(),self.ns);exec(SCRIPT,self.ns)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(os.path.realpath(self.tmp.name));self.proc=self.root/'proc';self.proc.mkdir();self.code=self.root/'system/code';self.code.mkdir(parents=True)
        self.node=self.root/'node';self.node.write_bytes(b'controlled Node fixture');self.node.chmod(0o755)
    def process(self,pid,title=None,cwd=None):
        path=self.proc/str(pid);path.mkdir();(path/'cmdline').write_bytes((title or self.ns['SERVICE']).encode()+b'\0')
        (path/'exe').symlink_to(self.node);(path/'cwd').symlink_to(cwd or self.code);(path/'stat').write_text(str(pid)+' (node) S '+'0 '*18+'12345')
    def find(self):return self.ns['rewritten_service'](self.code,self.proc,self.node,os.getuid())
    def test_rewritten_service_matches_uid_exe_cwd_and_start_time(self):
        self.process(101);self.assertEqual(self.find(),[(101,'12345')]);self.process(102,title='unrelated.node');self.assertEqual(self.find(),[(101,'12345')])
    def test_multiple_or_foreign_cwd_service_titles_are_refused(self):
        self.process(101);self.process(102)
        with self.assertRaisesRegex(ValueError,'Multiple'):self.find()
        import shutil;shutil.rmtree(self.proc/'102');(self.proc/'101/cwd').unlink();(self.proc/'101/cwd').symlink_to(self.root)
        with self.assertRaisesRegex(ValueError,'Ambiguous'):self.find()
    def test_rewritten_service_wrong_executable_is_not_killed(self):
        self.process(101);(self.proc/'101/exe').unlink();(self.proc/'101/exe').symlink_to(self.root/'other-node')
        with self.assertRaises(ValueError):self.find()
    def test_stop_rechecks_pid_identity_and_never_kills_unrelated_nodes(self):
        from unittest.mock import patch
        registration=self.code.parent/'registration.json';registration.write_bytes(b'protected registration');registration.chmod(0o600)
        cleanup=types.SimpleNamespace(stop=lambda code:None)
        with patch.dict(self.ns,{'rewritten_service':lambda *args:[(101,'12345')]}),patch.object(self.ns['os'],'kill') as kill:
            calls=iter([[(101,'12345')],[(101,'changed')]])
            self.ns['rewritten_service']=lambda *args:next(calls)
            with self.assertRaisesRegex(ValueError,'identity changed'):self.ns['stop_old_service'](self.code,cleanup,self.ns['digest'](registration.read_bytes()),self.proc)
            kill.assert_not_called()

if __name__=='__main__':unittest.main()
