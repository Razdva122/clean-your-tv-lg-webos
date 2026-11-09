import os
import io
from contextlib import redirect_stderr,redirect_stdout
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from updater.store import Store
from installation import Ownership, Busy
import install_driver

class Device:
    def __init__(self, fail=None): self.calls=[]; self.fail=fail; self.installed=False
    def call(self, name):
        self.calls.append(name)
        if name == self.fail: raise RuntimeError('private diagnostic')
    def preflight(self, payload, options): self.call('preflight')
    def inspect(self):
        self.call('inspect')
        return {'state':'installed' if self.installed else 'fresh'}
    def deploy(self, payload, options): self.call('deploy')
    def updater(self, payload, options): self.call('updater'); self.installed=True
    def supervisor(self, payload, options): self.call('supervisor')
    def readback(self): self.call('readback'); return {'verified':True}
    def require_selected_runtime(self, payload): self.call('runtime-contract')
    def restore(self): self.call('restore')
    def remove(self, checkpoint):
        checkpoint('remove-submitting'); self.call('remove'); checkpoint('remove-terminal')
        return {'removed':True}

class CoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.store=Store(Path(self.tmp.name).resolve()/'state',uid=os.getuid())
        self.owner=Ownership(self.store); self.device=Device()
        self.driver=install_driver.Coordinator(self.device,self.owner,read=lambda path:None); self.identifier='a'*32
    def test_order_and_no_activation(self):
        result=self.driver.install(self.identifier,'/verified',prepare_supervisor=True)
        self.assertEqual(self.device.calls,['preflight','inspect','deploy','updater','supervisor','readback'])
        self.assertEqual(result['state'],'complete'); self.assertTrue(self.owner.status()['terminal'])
        self.assertFalse(result['home_changed'])
    def test_failure_at_every_boundary_retains_ownership_and_never_replays(self):
        for boundary in ('deploy','updater','supervisor','readback'):
            with self.subTest(boundary=boundary), tempfile.TemporaryDirectory() as tmp:
                owner=Ownership(Store(Path(tmp).resolve()/'state',uid=os.getuid()))
                device=Device(boundary); driver=install_driver.Coordinator(device,owner,read=lambda path:None)
                result=driver.install(self.identifier,'/verified',prepare_supervisor=True)
                self.assertEqual(result['state'],'recovery_required'); self.assertFalse(owner.status()['terminal'])
                calls=list(device.calls)
                self.assertEqual(driver.install(self.identifier,'/verified',prepare_supervisor=True),result)
                self.assertEqual(device.calls,calls)
                with self.assertRaises(Busy): driver.install('b'*32,'/verified')
                self.assertNotIn('private diagnostic',str(result))
    def test_initial_worker_failure_survives_status_without_private_command(self):
        import subprocess
        def deploy(payload, options):
            raise subprocess.CalledProcessError(127, ['PRIVATE-COMMAND'], output=b'PRIVATE-OUTPUT', stderr=b'PRIVATE-ERROR')
        self.device.deploy=deploy
        result=self.driver.install(self.identifier,'/verified')
        self.assertEqual(result.get('failure'), {'exception_type':'CalledProcessError','exit_status':127})
        self.assertEqual(self.driver.status(self.identifier)['failure'],result['failure'])
        self.assertNotIn('PRIVATE',str(result))
        self.assertEqual(self.driver.install(self.identifier,'/verified'),result)

    def test_broken_private_log_does_not_replace_original_worker_failure(self):
        import subprocess
        def fail_deploy(payload, options):
            raise subprocess.CalledProcessError(127, ['PRIVATE-COMMAND'])
        def fail_log(error):
            raise OSError('PRIVATE-LOG')
        self.device.deploy=fail_deploy; self.device.log=fail_log
        result=self.driver.install(self.identifier,'/verified')
        self.assertEqual(result['state'],'recovery_required')
        self.assertEqual(result['failure'],{'exception_type':'CalledProcessError','exit_status':127})

    def test_same_contract_handoff_maintains_without_submission(self):
        self.device.installed=True
        self.assertEqual(self.driver.install(self.identifier,'/verified')['state'],'complete')
        self.assertEqual(self.device.calls,['preflight','inspect','runtime-contract','readback'])
    def test_installed_runtime_mismatch_is_not_success_and_never_replays(self):
        from install_device import InstallerRuntimeMismatch
        self.device.installed=True
        def reject(payload):
            self.device.call('runtime-contract')
            raise InstallerRuntimeMismatch()
        self.device.require_selected_runtime=reject
        result=self.driver.install(self.identifier,'/verified',prepare_supervisor=True)
        self.assertEqual(result['state'],'recovery_required')
        self.assertEqual(result['code'],'installer-runtime-mismatch')
        self.assertEqual(self.device.calls,['preflight','inspect','runtime-contract'])
        self.assertFalse(self.owner.status()['terminal'])
        self.assertEqual(self.driver.install(self.identifier,'/verified'),result)
        self.assertEqual(self.device.calls,['preflight','inspect','runtime-contract'])

    def test_retained_state_is_never_overwritten(self):
        self.device.inspect=lambda:{'state':'recovery_required'}
        result=self.driver.install(self.identifier,'/verified')
        self.assertEqual(result['code'],'installation_requires_recovery')
        self.assertEqual(self.device.calls,['preflight']); self.assertFalse(self.owner.status()['terminal'])
    def test_removal_holds_lease_and_retains_uncertain_submission(self):
        def remove(checkpoint):
            checkpoint('remove-submitting')
            with self.assertRaises(Busy):
                with Ownership(self.store).operation('deploy','deploy.json'): pass
            raise RuntimeError('lost terminal')
        self.device.remove=remove
        result=self.driver.remove(self.identifier)
        self.assertEqual(result['state'],'recovery_required')
        self.assertEqual(self.owner.status()['stage'],'remove-submitting')
        self.assertEqual(self.driver.remove(self.identifier),result)
    def test_status_and_restore_remain_available(self):
        self.device.fail='deploy'; self.driver.install(self.identifier,'/verified')
        self.assertEqual(self.driver.status(self.identifier)['state'],'recovery_required')
        self.driver.restore(); self.assertEqual(self.device.calls[-1],'restore')
        self.assertFalse(self.owner.status()['terminal'])
    def test_invalid_identifier_and_options_do_not_mutate(self):
        for identifier in ('../operation','A'*32,'a'*31,None):
            with self.assertRaises(ValueError): self.driver.install(identifier,'/verified')
        with self.assertRaises(ValueError): self.driver.install(self.identifier,'/verified',migrate=1)
        self.assertEqual(self.device.calls,[]); self.assertIsNone(self.owner.status())

class ActivationTests(unittest.TestCase):
    def test_pending_product_blocks_direct_root_activation_but_terminal_allows(self):
        import importlib.util
        path=Path(__file__).resolve().parents[1]/'runtime/update_guard.py'
        spec=importlib.util.spec_from_file_location('product_update_guard',path)
        guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve()/'root';root.mkdir(mode=0o700)
            ownership=Ownership(Store(root.parent/'clean-your-tv-installation',uid=os.getuid()))
            with ownership.operation('product','product.json') as record:
                with self.assertRaises(guard.ProductPending):
                    with guard.control(root,os.getuid()): pass
            with self.assertRaises(guard.ProductPending):
                with guard.control(root,os.getuid()): pass
            with ownership.operation('product','product.json',resume=record['id']) as record:
                ownership.stage(record,'complete',terminal=True)
            with guard.control(root,os.getuid()): pass

    def test_direct_activation_serializes_with_product_ownership(self):
        import importlib.util
        path=Path(__file__).resolve().parents[1]/'runtime/update_guard.py'
        spec=importlib.util.spec_from_file_location('product_update_guard_race',path)
        guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve()/'root';root.mkdir(mode=0o700)
            ownership=Ownership(Store(root.parent/'clean-your-tv-installation',uid=os.getuid()))
            with guard.control(root,os.getuid()):
                with self.assertRaises(Busy):
                    with ownership.operation('product','product.json'): pass

class LocalRemovalTests(unittest.TestCase):
    def test_runtime_validation_failure_precedes_updater_disabling(self):
        result, owner, calls, _, _ = self.run_device(fail='validate-root-driver')
        self.assertEqual(result['state'], 'recovery_required')
        self.assertFalse(any(call.startswith('cleanup-') for call in calls), calls)
        self.assertNotIn('root-remove', calls)

    def run_device(self, fail=None, apps=None, busy=None, resume_after=False):
        from unittest.mock import patch
        import install_device
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        base=Path(temp.name).resolve();root=base/'root';root.mkdir()
        owner=Ownership(Store(base/'ownership',uid=os.getuid()))
        errors=[];owner.fixture_errors=errors
        calls=[];present=set(apps if apps is not None else (install_device.APP,'com.cleanyourtv.root.updater','com.cleanyourtv.updater','com.local.nativehome','com.gathin.tvhome','com.cleanyourtv.system.updater'))
        class Model(install_device.LocalDevice):
            def log(self,error):errors.append(type(error).__name__+': '+str(error))
            def verify_resume(self,payload,submission):return {'migrate':False,'prepare_supervisor':False}
            def root_journal(self):return {'stage':'installed-recovery-only'}
            def archive_proof(self,path):return False
            def legacy_status(self):return self.rpc('com.cleanyourtv.updater.service/status',{})
            def validate_root_driver(self): self.boundary('validate-root-driver')
            def boundary(self,name):
                self.assert_lease()
                calls.append(name)
                if name==fail: raise RuntimeError('private boundary failure')
            def assert_lease(self):
                if owner.status()['terminal']: raise AssertionError('lease released early')
                try:
                    with Ownership(owner.store).operation('foreign','transaction.json'): pass
                except Busy: pass
                else: raise AssertionError('foreign mutation entered removal')
            def apps(self): return set(present)
            def rpc(self,method,payload):
                self.boundary(method)
                if method.endswith('/status'):
                    return {'returnValue':True,'status':{'apps':[]},'result':{'transaction':None}}
                if method.endswith('/getAllInputStatus'): return {'devices':[]}
                return {'returnValue':True}
            def cleanup(self,name,*args):
                self.boundary('cleanup-'+name+'-'+(args[0] if args else ''))
                if name=='root_archive':
                    value=busy.pop(0) if busy and len(busy)>1 else (busy[0] if busy else False)
                    if isinstance(value,Exception): raise value
                    return {'busy':value}
                return {'disabled':True,'removed':True,'archive':'saved-'+name}
            def absent(self,app,terminal=None):
                self.boundary('absent-'+app)
                if app in present: raise ValueError('package remains')
            def verify_removed(self):
                self.boundary('verify-removed')
                if present: raise ValueError('packages remain')
        device=Model()
        def root_remove():
            device.boundary('root-remove');present.discard(install_device.APP)
            return {'removed':install_device.APP,'state_retained':str(root)}
        def package_remove(app,timeout):
            device.boundary('remove-'+app);present.discard(app)
            return {'completed':True,'event':{'id':app,'statusValue':31,'details':{'packageId':app,'state':'removed'}}}
        elapsed=[0]
        def sleep(seconds):elapsed[0]+=seconds
        with patch.object(install_device,'ROOT',root),patch.object(install_device,'SUPERVISOR',base/'supervisor'),patch('deploy.uninstall',root_remove),patch('observed_install.remove',package_remove),patch('time.monotonic',lambda:elapsed[0]),patch('time.sleep',sleep):
            driver=install_driver.Coordinator(device,owner,read=lambda p:None)
            result=driver.remove('a'*32)
            if resume_after:
                fail=None
                owner.store.write('submission-'+'a'*32,{'action':'remove','candidate_sha256':'0'*64})
                result=driver.resume('a'*32,'/verified')
        return result,owner,calls,present,elapsed

    def test_complete_sequence_retains_exact_terminals_and_global_ownership(self):
        result,owner,calls,present,_=self.run_device()
        self.assertEqual(result['state'],'complete');self.assertFalse(present)
        self.assertTrue(owner.status()['terminal'])
        self.assertLess(calls.index('cleanup-system_updater-disable'),calls.index('root-remove'))
        self.assertLess(calls.index('cleanup-root_updater-disable'),calls.index('root-remove'))
        self.assertLess(calls.index('root-remove'),calls.index('remove-com.cleanyourtv.root.updater'))
        self.assertLess(calls.index('cleanup-app_permissions-'),calls.index('cleanup-root_updater-finalize'))
        record=owner.store.read('removal-'+owner.status()['id'])
        for app,value in record['removals'].items():
            self.assertEqual(value['state'],'terminal')
            self.assertEqual(value['evidence']['event']['details']['packageId'],app)

    def test_every_effect_boundary_failure_keeps_reservation(self):
        _,_,boundaries,_,_=self.run_device()
        for boundary in boundaries:
            with self.subTest(boundary=boundary):
                result,owner,calls,_,_=self.run_device(fail=boundary)
                self.assertEqual(result['state'],'recovery_required')
                self.assertFalse(owner.status()['terminal'])
                self.assertEqual(calls[-1],boundary)

    def test_leftover_updater_does_not_resubmit_absent_root(self):
        result,_,calls,_,_=self.run_device(apps={'com.cleanyourtv.root.updater'})
        self.assertEqual(result['state'],'complete');self.assertNotIn('root-remove',calls)
        self.assertEqual([c for c in calls if c.startswith('remove-')],['remove-com.cleanyourtv.root.updater'])

    def test_root_exit_wait_and_failure_keep_ownership(self):
        for busy,success in (([False],True),([True,True,False],True),([True],False),([RuntimeError('private')],False)):
            with self.subTest(busy=busy):
                result,owner,_,_,elapsed=self.run_device(apps=set(),busy=busy)
                self.assertEqual(result['state'],'complete' if success else 'recovery_required')
                self.assertEqual(owner.status()['terminal'],success)
                self.assertLessEqual(elapsed[0],60)

class CurrentByteReadbackTests(unittest.TestCase):
    def fixture(self):
        import hashlib,json
        from cytv import package
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        base=Path(temp.name).resolve();root=base/'root';root.mkdir()
        updater=base/'updater';store=Store(updater,uid=os.getuid());(updater/'cache').mkdir()
        app='com.cleanyourtv.root.preview';prefix='usr/palm/applications/'+app+'/'
        files={prefix+'appinfo.json':json.dumps({'id':app,'version':'1.0.0','type':'web','main':'index.html'}).encode(),
               prefix+'index.html':b'current UI',prefix+'apps.js':b'personalized inventory',prefix+'config.js':b'personalized preferences',
               prefix+'startup.sh':b'#!/bin/sh\nexit 0\n','usr/palm/packages/'+app+'/packageinfo.json':json.dumps({'id':app,'app':app,'version':'1.0.0','services':[]}).encode()}
        raw=package.ipk(app,'1.0.0',files,executable=(prefix+'startup.sh',))
        parts=package.read_ar(raw);parts['data.tar.gz']=package.tgz(files,executable=(prefix+'startup.sh',),directories=False)
        parts['control.tar.gz']=package.tgz({'control':('Package: '+app+'\nVersion: 1.0.0\n').encode()},directories=False)
        raw=package.ar(parts)
        descriptor={'local':True,'version':'1.0.0','size':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        (updater/'cache'/(descriptor['sha256']+'.ipk')).write_bytes(raw);store.write('current',descriptor)
        installed=base/'installed'
        for name,data in files.items():
            target=installed/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);target.chmod(0o755 if name.endswith('startup.sh') else 0o644)
        return root,updater,installed,store,files

    def test_exact_byte_readback_leaves_profile_and_off_latch(self):
        from unittest.mock import patch
        import install_device
        root,updater,installed,store,files=self.fixture()
        marker=root/'emergency-off';marker.write_bytes(b'off')
        before={name:(installed/name).read_bytes() for name in files}
        with patch('updater.device.Device.integrity',return_value={}):
            result=install_device.current_root(root,updater,installed,uid=os.getuid())
            self.assertTrue(result['local']);self.assertEqual(marker.read_bytes(),b'off')
            self.assertEqual({n:(installed/n).read_bytes() for n in files},before)
        startup=next(n for n in files if n.endswith('startup.sh'))
        self.assertEqual((installed/startup).stat().st_mode & 0o777,0o755)

    def test_sdk_mode_drift_is_data_but_changed_bytes_refuse_current_contract(self):
        from unittest.mock import patch
        import install_device
        root,updater,installed,_,files=self.fixture()
        for path in installed.rglob('*'):path.chmod(0o777)
        with patch('updater.device.Device.integrity',return_value={}):
            self.assertTrue(install_device.current_root(root,updater,installed,uid=os.getuid())['local'])
            startup=installed/next(n for n in files if n.endswith('startup.sh'));startup.write_bytes(b'changed')
            with self.assertRaises(ValueError):install_device.current_root(root,updater,installed,uid=os.getuid())

    def test_invalid_saved_profile_is_recovery_and_never_rewritten(self):
        from unittest.mock import patch
        import install_device
        root,updater,installed,store,_=self.fixture()
        profile={'schema':2,'private':'retained'}
        store.write('profile-'+'a'*32,profile)
        tx={'phase':'complete','homeResumePhase':'complete','profile':'profile-'+'a'*32,'profileDigest':'0'*64}
        store.write('transaction',tx)
        with patch('updater.device.Device.integrity',return_value={}),self.assertRaises(ValueError):
            install_device.current_root(root,updater,installed,uid=os.getuid())
        self.assertEqual(store.read('profile-'+'a'*32),profile)

    def test_unknown_legacy_updater_receipt_requires_migration(self):
        import install_device
        _,updater,installed,_,_=self.fixture()
        with self.assertRaisesRegex(ValueError,'migration'):
            install_device.current_updater(updater,installed,uid=os.getuid())

class WorkerDurabilityTests(unittest.TestCase):
    def test_process_death_after_submission_returns_status_without_replay(self):
        import subprocess
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        root=Path(temp.name).resolve();state=root/'ownership';marker=root/'submissions'
        code='''import os,sys
sys.path.insert(0,sys.argv[1])
from install_driver import Coordinator
from installation import Ownership
from updater.store import Store
class Device:
 def preflight(self,*args):pass
 def inspect(self):return {'state':'fresh'}
 def deploy(self,*args):
  with open(sys.argv[3],'a') as out:out.write('submitted\\n');out.flush();os.fsync(out.fileno())
  os._exit(23)
Coordinator(Device(),Ownership(Store(sys.argv[2],uid=os.getuid())),read=lambda p:None).install('a'*32,'/verified')
'''
        result=subprocess.run([sys.executable,'-c',code,str(Path(__file__).resolve().parents[1]),str(state),str(marker)])
        self.assertEqual(result.returncode,23)
        owner=Ownership(Store(state,uid=os.getuid()));device=Device()
        driver=install_driver.Coordinator(device,owner,read=lambda p:None)
        self.assertEqual(driver.status('a'*32)['state'],'pending')
        self.assertEqual(driver.install('a'*32,'/verified')['state'],'pending')
        self.assertEqual(device.calls,[]);self.assertEqual(marker.read_text(),'submitted\n')
        self.assertFalse(owner.status()['terminal'])

    def submission_fixture(self):
        import json
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        root=Path(temp.name).resolve();payload=root/'payload';payload.mkdir()
        inventories={}
        for name in ('root','root-updater'):
            bundle=payload/name;bundle.mkdir();(bundle/'install_driver.py').write_bytes(b'verified worker v1')
            import hashlib
            manifest={'files':{'install_driver.py':hashlib.sha256(b'verified worker v1').hexdigest()}}
            (bundle/'bundle.json').write_text(json.dumps(manifest));inventories[name]=manifest
        owner=Ownership(Store(root/'ownership',uid=os.getuid()))
        return root,payload,inventories,owner

    def test_detached_snapshot_survives_package_replacement_and_lost_reply(self):
        from unittest.mock import patch
        import install_device
        root,payload,inventories,owner=self.submission_fixture()
        with patch('install_driver._verified_payload',return_value=inventories),patch('install_driver.root_review_binding',return_value={'identity':{},'code':{}}),patch.object(install_device.LocalDevice,'preflight'),patch('subprocess.Popen') as spawn:
            record=install_driver.submit('a'*32,payload,ownership=owner)
            self.assertEqual(record['state'],'pending');self.assertTrue(spawn.call_args.kwargs['start_new_session'])
            (payload/'root-updater/install_driver.py').write_bytes(b'replaced installer v2')
            snapshot=Path(owner.store.root)/('request-'+'a'*32)/'root-updater/install_driver.py'
            self.assertEqual(snapshot.read_bytes(),b'verified worker v1')
            self.assertEqual(install_driver.submit('a'*32,payload,ownership=owner)['state'],'pending')
            self.assertEqual(spawn.call_count,1)

    def test_submission_parent_wait_is_bounded_and_only_tracks_exact_parent(self):
        with patch('os.getppid',side_effect=[42,42,1]),patch('time.monotonic',side_effect=[0,0.1,0.2]),patch('time.sleep') as sleep:
            install_driver.wait_submission_parent(42)
            self.assertEqual(sleep.call_count,2)
        with patch('os.getppid',return_value=42),patch('time.monotonic',side_effect=[0,1,3]),patch('time.sleep') as sleep:
            install_driver.wait_submission_parent(42)
            self.assertEqual(sleep.call_count,1)

    def test_temporary_upload_preserved_with_durable_matching_snapshot(self):
        import shutil
        import install_device
        _,payload,inventories,owner=self.submission_fixture()
        stage=Path('/tmp').resolve()/('cytv-product-'+__import__('uuid').uuid4().hex)
        shutil.copytree(payload,stage);self.addCleanup(shutil.rmtree,stage,True)
        synced=set();fsync=os.fsync
        def sync(fd):
            import stat
            info=os.fstat(fd)
            if stat.S_ISDIR(info.st_mode):synced.add((info.st_dev,info.st_ino))
            return fsync(fd)
        def spawn(*args,**kwargs):
            snapshot=Path(owner.store.root)/('request-'+'a'*32)
            directories=[Path(owner.store.root),snapshot,*[p for p in snapshot.rglob('*') if p.is_dir()]]
            self.assertTrue({(p.stat().st_dev,p.stat().st_ino) for p in directories}<=synced)
            saved=owner.store.read('submission-'+'a'*32)
            self.assertTrue(saved['staging'])
            self.assertTrue((stage/'root/install_driver.py').is_file())
            device=install_device.LocalDevice();device.ownership=owner;device.payload=snapshot
            self.assertTrue(device.current_product_stage(stage))
            (stage/'foreign').write_bytes(b'unknown')
            self.assertFalse(device.current_product_stage(stage))
            (stage/'foreign').unlink()
            (stage/'root/install_driver.py').write_bytes(b'changed')
            self.assertFalse(device.current_product_stage(stage))
        with patch('install_driver._verified_payload',return_value=inventories),patch('install_driver.root_review_binding',return_value={'identity':{},'code':{}}),patch.object(install_device.LocalDevice,'preflight'),patch('subprocess.Popen',side_effect=spawn),patch('os.fsync',side_effect=sync):
            self.assertEqual(install_driver.submit('a'*32,stage,ownership=owner)['state'],'pending')

    def test_failed_spawn_is_retained_and_cannot_be_resubmitted(self):
        from unittest.mock import patch
        import install_device
        _,payload,inventories,owner=self.submission_fixture()
        with patch('install_driver._verified_payload',return_value=inventories),patch('install_driver.root_review_binding',return_value={'identity':{},'code':{}}),patch.object(install_device.LocalDevice,'preflight'),patch('subprocess.Popen',side_effect=OSError('private')) as spawn:
            self.assertEqual(install_driver.submit('a'*32,payload,ownership=owner)['state'],'recovery_required')
            self.assertEqual(install_driver.submit('a'*32,payload,ownership=owner)['state'],'recovery_required')
            self.assertEqual(spawn.call_count,1)

    def test_changed_reviewed_candidate_never_stages_or_spawns(self):
        from unittest.mock import patch
        _,payload,inventories,owner=self.submission_fixture()
        with patch('install_driver._verified_payload',return_value=inventories),patch('install_driver.root_review_binding',return_value={'identity':{},'code':{}}),patch('subprocess.Popen') as spawn:
            with self.assertRaisesRegex(ValueError,'candidate_changed'):
                install_driver.submit('a'*32,payload,candidate='0'*64,ownership=owner)
            spawn.assert_not_called()
            self.assertIsNone(owner.store.read('submission-'+'a'*32))

class ReservationRaceTests(unittest.TestCase):
    def test_completed_concurrent_request_does_not_leave_new_reserved_lease(self):
        from contextlib import contextmanager
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        store=Store(Path(temp.name).resolve()/'ownership',uid=os.getuid());owner=Ownership(store)
        original=owner.operation
        completed={'operation':'a'*32,'action':'install','stage':'complete','state':'complete','code':'verified','home_changed':False,'result':{'verified':True}}
        @contextmanager
        def racing(*args,**kwargs):
            store.write('request-'+'a'*32,completed)
            with original(*args,**kwargs) as record: yield record
        owner.operation=racing
        result=install_driver.Coordinator(Device(),owner,read=lambda path:None).install('a'*32,'/verified')
        self.assertEqual(result,completed)
        self.assertIsNone(owner.status())

class RealHandoffTests(unittest.TestCase):
    def test_current_protocol_through_local_inspection_and_maintenance(self):
        from install_fixture import CurrentInstallation
        import install_device
        with CurrentInstallation() as fixture:
            device=install_device.LocalDevice()
            self.assertEqual(device.inspect()['state'],'installed')
            result=install_driver.Coordinator(device,fixture.owner).install('c'*32,fixture.payload)
            self.assertEqual(result['state'],'complete')
            fixture.assert_preserved(self)

class ExplicitRecoveryTests(unittest.TestCase):
    def test_final_worker_rechecks_request_binding_after_acquiring_original_lease(self):
        from contextlib import contextmanager
        from install_fixture import CurrentInstallation
        from install_device import LocalDevice
        from unittest.mock import patch
        with CurrentInstallation() as fixture:
            device=LocalDevice();driver=install_driver.Coordinator(device,fixture.owner)
            with redirect_stderr(io.StringIO()),patch.object(device,'readback',side_effect=ValueError('interruption')):
                driver.install('a'*32,fixture.payload)
            snapshot=fixture.snapshot('a'*32);self.bind_candidate(fixture,'a'*32,snapshot)
            name='request-'+'a'*32
            original_record=fixture.owner.store.read(name)
            original_lease=fixture.owner.status()
            original=fixture.owner.operation
            for key,value in (('lease','e'*32),('operation','e'*32),('action','remove'),('candidate_sha256','e'*64)):
                with self.subTest(field=key):
                    fixture.owner.store.write('operation',original_lease)
                    fixture.owner.store.write(name,original_record)
                    changed_record={**original_record,key:value}
                    @contextmanager
                    def changed(*args,**kwargs):
                        with original(*args,**kwargs) as lease:
                            fixture.owner.store.write(name,changed_record)
                            yield lease
                    with patch.object(fixture.owner,'operation',side_effect=changed), \
                         patch.object(device,'readback',wraps=device.readback) as readback:
                        with self.assertRaises(ValueError):driver.resume('a'*32,snapshot,final_readback_only=True)
                        readback.assert_not_called()
                    self.assertEqual(fixture.owner.store.read(name),changed_record)
                    self.assertEqual(fixture.owner.status(),original_lease)
                    self.assertFalse(fixture.owner.status()['terminal'])

    def test_final_worker_rechecks_snapshot_after_acquiring_original_lease(self):
        from contextlib import contextmanager
        from install_fixture import CurrentInstallation
        from install_device import LocalDevice
        from unittest.mock import patch
        with CurrentInstallation() as fixture:
            device=LocalDevice();driver=install_driver.Coordinator(device,fixture.owner)
            with redirect_stderr(io.StringIO()),patch.object(device,'readback',side_effect=ValueError('interruption')):
                driver.install('a'*32,fixture.payload)
            snapshot=fixture.snapshot('a'*32);self.bind_candidate(fixture,'a'*32,snapshot)
            original=fixture.owner.operation
            @contextmanager
            def changed(*args,**kwargs):
                with original(*args,**kwargs) as lease:
                    (snapshot/'root-updater/install_driver.py').write_bytes(b'changed while waiting')
                    yield lease
            with patch.object(fixture.owner,'operation',side_effect=changed),self.assertRaises(ValueError):
                driver.resume('a'*32,snapshot,final_readback_only=True)
            self.assertFalse(fixture.owner.status()['terminal'])

    def test_host_orchestration_reaches_original_filesystem_coordinator_without_package_replay(self):
        import json,shlex
        from install_fixture import CurrentInstallation
        from install_device import LocalDevice
        from unittest.mock import patch
        from cytv import operations,state
        from cytv.root_install_recovery import RECOVERY_ENTRY
        with CurrentInstallation() as fixture:
            device=LocalDevice();driver=install_driver.Coordinator(device,fixture.owner)
            with redirect_stderr(io.StringIO()),patch.object(device,'readback',side_effect=ValueError('interruption')):
                failed=driver.install('a'*32,fixture.payload)
            snapshot=fixture.snapshot('a'*32);self.bind_candidate(fixture,'a'*32,snapshot)
            host=state.Store(fixture.base/'host');profile=state.target('fixture.local','root')
            host.begin(profile,'install',stage='coordinator-submitted',requires_updater=True,
                       product_operation='a'*32,recovery_protocol='root-final-readback-v1')
            original=host.pending(profile);calls=[];uploads={};test=self
            class Remote:
                def upload(self,path,data,mode=0o600):uploads[path]=data
                def luna(self,uri,payload,**kwargs):
                    test.assertEqual(uri,operations.UPDATER_APP+'.service/status')
                    return {'returnValue':True,'result':None}
                def run(self,command,**kwargs):
                    calls.append(command);words=shlex.split(command)
                    if '/usr/bin/node' in words:return '/usr/bin/python3'
                    if command.startswith(('umask ','mkdir ')):return ''
                    if RECOVERY_ENTRY in words:
                        test.assertIn('-I',words)
                        action=words[words.index(RECOVERY_ENTRY)+3]
                        if action=='status':
                            event=driver.status('a'*32)
                            return json.dumps(dict(event,**install_driver.continuation_status('a'*32,fixture.owner.store,device),
                                current=device.validate_completion('install',event.get('lease')) if event['state']=='complete' else False))
                        test.assertEqual(action,'install');test.assertIn('--final-readback-only',words)
                        test.assertNotIn('--payload',words)
                        return json.dumps(driver.resume('a'*32,snapshot,final_readback_only=True))
                    if 'CYTV_UPDATER_VERIFIED' in command:
                        test.assertEqual(words[-1],device.readback()['baseline_sha'])
                        return 'CYTV_UPDATER_VERIFIED'
                    if '/var/lib/clean-your-tv-root/deploy.py status' in command:
                        return json.dumps({'returnValue':True,'result':{'recovery':{'integrity_verified':True},'guardian_active':False,
                            'intent':{'enabled':False,'phase':'disabled'},'effective':{'sam_home':'com.webos.app.home',
                            'profiles':{'defaultApps':{'categories':{'home':'com.webos.app.home'}},'idleApp':{'appId':'com.webos.app.home'}}}}})
                    raise AssertionError(command)
            installer=operations.Installer(Remote(),host,profile,fixture.payload,{})
            reviewed=installer.observe_recovery()
            self.assertIn('continue-product',reviewed['assessment']['actions'])
            self.assertEqual(host.pending(profile),original)
            with patch.object(device,'resume_install',side_effect=AssertionError('general replay path')):
                result=installer.continue_root_product(original)
            self.assertTrue(result['can_resume_root_setup'])
            self.assertEqual(host.pending(profile)['baseline_sha'],device.readback()['baseline_sha'])
            self.assertEqual(driver.status('a'*32)['lease'],failed['lease'])
            self.assertTrue(fixture.owner.status()['terminal']);fixture.assert_preserved(self)
            self.assertEqual(sum('--resume' in call for call in calls),1)
            self.assertTrue(any(path.endswith('/install_driver.py') for path in uploads))

    def test_terminal_record_with_unfinished_lease_spawns_only_current_trusted_worker(self):
        from install_fixture import CurrentInstallation
        from install_device import LocalDevice
        from unittest.mock import patch
        with CurrentInstallation() as fixture:
            device=LocalDevice();driver=install_driver.Coordinator(device,fixture.owner)
            driver.install('a'*32,fixture.payload);snapshot=fixture.snapshot('a'*32)
            fixture.retain('a'*32,'complete');self.bind_candidate(fixture,'a'*32,snapshot)
            record=fixture.owner.store.read('request-'+'a'*32);record['state']='complete'
            fixture.owner.store.write('request-'+'a'*32,record)
            with patch('subprocess.Popen') as spawn:
                result=install_driver.resume_submit('a'*32,fixture.owner,action='install',final_readback_only=True)
            self.assertEqual(result['state'],'pending')
            self.assertEqual(spawn.call_count,1)
            args=spawn.call_args.args[0]
            self.assertEqual(args[2],str(Path(install_driver.__file__).resolve()))
            self.assertIn('--final-readback-only',args)
            self.assertEqual(args[args.index('--payload')+1],str(snapshot))

    def bind_candidate(self,fixture,identifier,snapshot):
        submission=fixture.owner.store.read('submission-'+identifier)
        candidate=install_driver.candidate_digest(snapshot,install_driver._verified_payload(snapshot,False))
        submission['candidate_sha256']=candidate;fixture.owner.store.write('submission-'+identifier,submission)
        record=fixture.owner.store.read('request-'+identifier);record['candidate_sha256']=candidate
        fixture.owner.store.write('request-'+identifier,record)

    def test_host_final_readback_continuation_is_rechecked_under_original_lease(self):
        from install_fixture import CurrentInstallation
        from install_device import LocalDevice
        from unittest.mock import patch
        with CurrentInstallation() as fixture:
            device=LocalDevice();driver=install_driver.Coordinator(device,fixture.owner)
            with redirect_stderr(io.StringIO()),patch.object(device,'readback',side_effect=ValueError('interruption')):
                failed=driver.install('a'*32,fixture.payload)
            snapshot=fixture.snapshot('a'*32)
            self.bind_candidate(fixture,'a'*32,snapshot)
            proof=install_driver.continuation_status('a'*32,fixture.owner.store,device)
            self.assertTrue(proof['can_resume'])
            with patch.object(device,'resume_install',side_effect=AssertionError('general replay path')):
                completed=driver.resume('a'*32,snapshot,final_readback_only=True)
            self.assertEqual(completed['lease'],failed['lease'])
            self.assertEqual(completed['result']['baseline_sha'],device.readback()['baseline_sha'])
            fixture.assert_preserved(self)

    def test_final_readback_refusal_reports_snapshot_and_stage_without_writes(self):
        from install_fixture import CurrentInstallation
        from install_device import LocalDevice
        from unittest.mock import patch
        with CurrentInstallation() as fixture:
            device=LocalDevice();driver=install_driver.Coordinator(device,fixture.owner)
            with redirect_stderr(io.StringIO()),patch.object(device,'readback',side_effect=ValueError('interruption')):
                driver.install('a'*32,fixture.payload)
            snapshot=fixture.snapshot('a'*32)
            self.bind_candidate(fixture,'a'*32,snapshot)
            record=fixture.owner.store.read('request-'+'a'*32)
            record['stage']='root-deploy';fixture.owner.store.write('request-'+'a'*32,record)
            before=(fixture.state/('request-'+'a'*32+'.json')).read_bytes()
            self.assertEqual(install_driver.continuation_status('a'*32,fixture.owner.store,device)['resume_reason'],'package-terminal-unverified')
            with self.assertRaises(ValueError):driver.resume('a'*32,snapshot,final_readback_only=True)
            self.assertEqual((fixture.state/('request-'+'a'*32+'.json')).read_bytes(),before)
            (snapshot/'root-updater/install_driver.py').write_bytes(b'changed')
            self.assertEqual(install_driver.continuation_status('a'*32,fixture.owner.store,device)['resume_reason'],'original-snapshot-unverified')

    def test_final_readback_rejects_candidate_drift_and_live_child(self):
        from install_fixture import CurrentInstallation
        from install_device import LocalDevice
        from unittest.mock import patch
        import install_device
        with CurrentInstallation() as fixture:
            device=LocalDevice();driver=install_driver.Coordinator(device,fixture.owner)
            with redirect_stderr(io.StringIO()),patch.object(device,'readback',side_effect=ValueError('interruption')):
                driver.install('a'*32,fixture.payload)
            snapshot=fixture.snapshot('a'*32);self.bind_candidate(fixture,'a'*32,snapshot)
            processes=fixture.base/'processes';(processes/'999999').mkdir(parents=True)
            (processes/'999999'/'cmdline').write_bytes(str(snapshot/'root/provision.py').encode()+b'\0finalize\0')
            with patch.object(install_device,'PROC',processes):
                self.assertEqual(install_driver.continuation_status('a'*32,fixture.owner.store,device)['resume_reason'],'worker-not-quiescent')
                with self.assertRaises(ValueError):driver.resume('a'*32,snapshot,final_readback_only=True)
            record=fixture.owner.store.read('request-'+'a'*32);record['candidate_sha256']='f'*64
            fixture.owner.store.write('request-'+'a'*32,record)
            self.assertEqual(install_driver.continuation_status('a'*32,fixture.owner.store,device)['resume_reason'],'original-snapshot-unverified')

    def test_terminal_then_readback_failure_resumes_original_request_without_submission(self):
        from install_fixture import CurrentInstallation
        from install_device import LocalDevice
        from unittest.mock import patch
        with CurrentInstallation() as fixture:
            device=LocalDevice();driver=install_driver.Coordinator(device,fixture.owner)
            original=device.readback
            errors=io.StringIO()
            with redirect_stderr(errors),patch.object(device,'readback',side_effect=ValueError('transient readback')):
                failed=driver.install('a'*32,fixture.payload)
            self.assertIn('transient readback',errors.getvalue())
            lease=fixture.owner.status()['id'];snapshot=fixture.snapshot('a'*32)
            self.assertEqual(failed['state'],'recovery_required')
            self.assertEqual(driver.install('a'*32,fixture.payload),failed)
            completed=driver.resume('a'*32,snapshot)
            self.assertEqual(completed['state'],'complete');self.assertEqual(completed['lease'],lease)
            self.assertTrue(fixture.owner.status()['terminal']);fixture.assert_preserved(self)

    def test_completed_terminal_request_can_fail_and_resume_without_changing_lease(self):
        from install_fixture import CurrentInstallation
        from install_device import LocalDevice
        from unittest.mock import patch
        with CurrentInstallation() as fixture:
            device=LocalDevice();driver=install_driver.Coordinator(device,fixture.owner)
            complete=driver.install('a'*32,fixture.payload);snapshot=fixture.snapshot('a'*32)
            errors=io.StringIO()
            with redirect_stderr(errors),patch.object(device,'readback',side_effect=ValueError('fresh readback failed')):
                failed=driver.resume('a'*32,snapshot)
            self.assertIn('fresh readback failed',errors.getvalue())
            self.assertEqual(failed['state'],'recovery_required')
            self.assertEqual(fixture.owner.status()['id'],complete['lease']);self.assertTrue(fixture.owner.status()['terminal'])
            self.assertEqual(driver.status('a'*32)['state'],'complete')
            self.assertEqual(driver.resume('a'*32,snapshot)['state'],'complete')
            self.assertEqual(fixture.owner.status()['id'],complete['lease'])
            driver.install('b'*32,fixture.payload)
            with self.assertRaises(Busy):driver.resume('a'*32,snapshot)

    def test_request_completion_before_ownership_completion_is_reconciled(self):
        from install_fixture import CurrentInstallation
        from install_device import LocalDevice
        from unittest.mock import patch
        with CurrentInstallation() as fixture:
            device=LocalDevice();driver=install_driver.Coordinator(device,fixture.owner)
            original=fixture.owner.stage
            def crash(record,stage,terminal=False):
                if terminal:raise OSError('crash before ownership completion')
                return original(record,stage,terminal)
            errors=io.StringIO()
            with redirect_stderr(errors),patch.object(fixture.owner,'stage',side_effect=crash):driver.install('a'*32,fixture.payload)
            self.assertIn('crash before ownership completion',errors.getvalue())
            record=driver.status('a'*32);record.update(state='complete',stage='complete',code='verified')
            fixture.owner.store.write('request-'+'a'*32,record)
            self.assertFalse(fixture.owner.status()['terminal'])
            self.assertEqual(driver.resume('a'*32,fixture.snapshot('a'*32))['state'],'complete')
            self.assertTrue(fixture.owner.status()['terminal'])

    def test_explicit_pre_submission_continuation_is_bounded_and_unknown_submission_is_not_replayed(self):
        from install_device import LocalDevice
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        owner=Ownership(Store(Path(temp.name).resolve()/'state',uid=os.getuid()))
        class BeforeSubmission(Device):
            resume_install=LocalDevice.resume_install
            def verify_resume(self,*args):return {'migrate':False,'prepare_supervisor':False}
            def absent(self,*args):pass
        device=BeforeSubmission('deploy');driver=install_driver.Coordinator(device,owner,read=lambda p:None)
        driver.install('a'*32,'/verified');owner.store.write('submission-'+'a'*32,{'action':'install','candidate_sha256':'0'*64})
        device.fail=None
        self.assertEqual(driver.resume('a'*32,'/verified')['state'],'complete')
        model=LocalRemovalTests();self.addCleanup(model.doCleanups)
        result,owner,calls,_,_=model.run_device(fail='remove-com.cleanyourtv.root.updater',resume_after=True)
        self.assertEqual(result['state'],'recovery_required');self.assertFalse(owner.status()['terminal'])
        self.assertEqual(calls.count('remove-com.cleanyourtv.root.updater'),1)

    def test_package_terminal_and_final_readback_continuation_do_not_resubmit(self):
        model=LocalRemovalTests();self.addCleanup(model.doCleanups)
        for boundary in ('absent-com.cleanyourtv.root.updater','verify-removed'):
            with self.subTest(boundary=boundary):
                result,owner,calls,_,_=model.run_device(fail=boundary,resume_after=True)
                self.assertEqual(result['state'],'complete',owner.fixture_errors);self.assertTrue(owner.status()['terminal'])
                self.assertEqual(calls.count('remove-com.cleanyourtv.root.updater'),1)

    def test_retained_legacy_status_emits_fixed_authorized_luna_identity(self):
        from unittest.mock import patch
        from test_observed_install import Fake
        from install_device import LocalDevice
        client=Fake(99);client.send({'returnValue':True,'result':{'transaction':None}})
        try:
            with patch('updater.luna.subprocess.Popen',return_value=client) as start:
                self.assertEqual(LocalDevice.legacy_status()['result']['transaction'],None)
            args=start.call_args.args[0]
            self.assertEqual(args[:7],['/usr/bin/luna-send','-a','com.gathin.tvhome','-m','com.gathin.tvhome-cytv','-n','1'])
            self.assertEqual(args[-2],'luna://com.cleanyourtv.updater.service/status')
        finally:client.close()

class ComponentTerminalRecoveryTests(unittest.TestCase):
    def test_bootstrap_keeps_cleanup_helpers_in_authenticated_stage_only(self):
        import hashlib,json,shutil
        from install_fixture import CurrentInstallation
        from updater import bootstrap,device as updater_device,store as updater_store
        from unittest.mock import patch
        installer_only={'cancel_install.py','cancel_provision.py','clean_removal.py','cleanup_tail.js','cleanup_no_root_private.js'}
        with CurrentInstallation() as fixture:
            bundle=fixture.payload/'root-updater';manifest=bootstrap.verify_bundle(bundle)
            self.assertTrue(installer_only <= set(manifest['files']))
            descriptor=fixture.up_store.read('current');proof=(fixture.root/'recovery-provision.json').read_bytes()
            root_manifest=json.loads((fixture.payload/'root/bundle.json').read_text())
            raw=(fixture.payload/'root'/root_manifest['package']).read_bytes()
            shutil.rmtree(fixture.updater)
            real_store=updater_store.Store
            class FixtureStore(real_store):
                def __init__(self,root,uid=0):super().__init__(root,uid=os.getuid())
            def atomic(path,raw,mode=0o600):
                path.write_bytes(raw.encode() if isinstance(raw,str) else raw);path.chmod(mode)
            with patch.object(bootstrap,'STATE',fixture.updater),patch.object(bootstrap,'safe_bytes',fixture.device_module.safe_bytes),patch.object(bootstrap,'atomic',atomic),patch.object(bootstrap,'preflight',return_value=(manifest,root_manifest,descriptor,proof,raw)),patch.object(updater_store,'Store',FixtureStore),patch.object(updater_device.Device,'integrity'),patch.object(updater_device.Device,'routing_status',return_value={'active':False,'safe':True}),patch('observed_install.install',return_value=self.terminal('com.cleanyourtv.root.updater')),patch.object(bootstrap,'finish_registration',return_value={'installed':True}):
                self.assertTrue(bootstrap.apply(bundle,fixture.payload/'root')['installed'])
            saved=FixtureStore(fixture.updater)
            code=saved.read('infrastructure')['code']
            self.assertEqual(set(code),set(manifest['files'])-installer_only-{'root-updater.ipk','setup-updater.py'})
            self.assertFalse(any((fixture.updater/'code'/name).exists() for name in installer_only))
            self.assertEqual(saved.read('bootstrap-bundle')['bundle'],manifest)
            for name in installer_only:
                self.assertEqual(hashlib.sha256((bundle/name).read_bytes()).hexdigest(),manifest['files'][name])

    @staticmethod
    def terminal(app):
        return {'completed':True,'event':{'id':app,'statusValue':30,'returnValue':True,'details':{'packageId':app,'client':'com.webos.lunasend-99','ipkFile':'/var/lib/clean-your-tv-installer/cytv-root-install-fixture/package.ipk'}}}

    def test_root_terminal_continues_provisioning_without_reinstall_or_reapplying_ready_registration(self):
        from install_fixture import CurrentInstallation
        from install_device import LocalDevice
        from unittest.mock import patch
        import deploy
        with CurrentInstallation() as fixture:
            driver=install_driver.Coordinator(LocalDevice(),fixture.owner)
            driver.install('a'*32,fixture.payload);snapshot=fixture.snapshot('a'*32)
            fixture.retain('a'*32)
            fixture.root_store.write('install-terminal',self.terminal('com.cleanyourtv.root.preview'))
            fixture.root_store.write('deploy',{'app':'com.cleanyourtv.root.preview','stage':'provision-finalize-starting'})
            with patch.object(deploy,'command',return_value={'returnValue':True}) as command:
                result=driver.resume('a'*32,snapshot)
            self.assertEqual(result['state'],'complete')
            self.assertEqual([call.args[0][-1] for call in command.call_args_list],['refresh','finalize'])
            fixture.assert_preserved(self)

    def test_updater_resume_requires_original_full_bundle_before_submission(self):
        import hashlib,json,shutil
        from install_fixture import CurrentInstallation,altered_bootstrap_bundle
        from updater import bootstrap,device as updater_device,store as updater_store
        from unittest.mock import patch
        with CurrentInstallation() as fixture:
            original=fixture.payload/'root-updater'
            manifest=bootstrap.verify_bundle(original)
            binding={'schema':1,'bundle':manifest,'package':{'sha256':manifest['files']['root-updater.ipk'],'size':(original/'root-updater.ipk').stat().st_size}}
            fixture.up_store.write('bootstrap-bundle',binding)
            fixture.up_store.write('bootstrap',{'phase':'installing-updater'})
            for folder,name in (('applications','com.cleanyourtv.root.updater'),('packages','com.cleanyourtv.root.updater'),('services','com.cleanyourtv.root.updater.service')):
                shutil.rmtree(fixture.installed/'usr/palm'/folder/name)
            real_store=updater_store.Store;real_device=updater_device.Device
            class FixtureStore(real_store):
                def __init__(self,root,uid=0):super().__init__(root,uid=os.getuid())
            class FixtureDevice(real_device):
                def __init__(self,store,code=None,**kwargs):super().__init__(store,code,root_state=fixture.root,installed=fixture.installed)
            alternatives=[altered_bootstrap_bundle(original,fixture.base/('alternate-'+str(code)),'root-updater.ipk',code=code) for code in (False,True)]
            before=fixture.up_store.read('bootstrap')
            with patch.object(bootstrap,'STATE',fixture.updater),patch.object(bootstrap,'INSTALLED',fixture.installed),patch.object(bootstrap,'HOOK',fixture.base/'absent-hook'),patch.object(bootstrap,'safe_bytes',fixture.device_module.safe_bytes),patch.object(updater_store,'Store',FixtureStore),patch.object(updater_device,'Device',FixtureDevice),patch.object(FixtureDevice,'routing_status',return_value={'active':False,'safe':True}),patch('observed_install.install',return_value=self.terminal('com.cleanyourtv.root.updater')) as install,patch.object(bootstrap,'finish_registration',return_value={'installed':True}) as finish:
                for alternate in alternatives:
                    bootstrap.verify_bundle(alternate) # Actual valid manifest, not a mocked rejection.
                    with self.assertRaisesRegex(ValueError,'original bootstrap bundle'):bootstrap.resume(alternate)
                    self.assertEqual(fixture.up_store.read('bootstrap'),before)
                    install.assert_not_called();finish.assert_not_called()
                (fixture.updater/'bootstrap-bundle.json').unlink()
                with self.assertRaisesRegex(ValueError,'original bootstrap bundle'):bootstrap.resume(original)
                install.assert_not_called();finish.assert_not_called()
                fixture.up_store.write('bootstrap-bundle',binding)
                self.assertTrue(bootstrap.resume(original)['installed'])
                self.assertEqual(Path(install.call_args.args[1]).read_bytes(),(original/'root-updater.ipk').read_bytes())
                self.assertEqual(fixture.up_store.read('bootstrap-bundle'),binding)

    def test_updater_terminal_and_interrupted_registration_resume_exact_owned_writes(self):
        from install_fixture import CurrentInstallation
        from updater import bootstrap,device as updater_device,store as updater_store
        from unittest.mock import patch
        with CurrentInstallation() as fixture:
            provision=fixture.provision
            uid=os.getuid();real_store=updater_store.Store;real_device=updater_device.Device
            class FixtureStore(real_store):
                def __init__(self,root,uid=0):super().__init__(root,uid=os.getuid())
            class FixtureDevice(real_device):
                def __init__(self,store,code=None,**kwargs):super().__init__(store,code,root_state=fixture.root,installed=fixture.installed)
            base=fixture.base/'ls2';hook=fixture.base/'hooks/51-updater';hook.parent.mkdir()
            service=bootstrap.SERVICE
            originals={'service':('[D-BUS Service]\nName='+service+'\nExec=/usr/bin/run-js-service -n /media/developer/apps/usr/palm/services/'+service+'\n').encode(),
                       'role':('{"appId":"'+service+'"}').encode(),'client':b'{}','api':b'{}'}
            for key,folder,suffix in (('service','services.d','.service'),('role','roles.d','.service.json'),('client','client-permissions.d','.service.json'),('api','api-permissions.d','.api.json')):
                target=base/folder/(service+suffix);target.parent.mkdir(parents=True);target.write_bytes(originals[key])
            def atomic(path,raw,mode=0o600):
                if isinstance(raw,str):raw=raw.encode()
                path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw);path.chmod(mode)
            manifest=bootstrap.verify_bundle(fixture.payload/'root-updater')
            fixture.up_store.write('bootstrap-bundle',{'schema':1,'bundle':manifest,'package':{'sha256':manifest['files']['root-updater.ipk'],'size':(fixture.payload/'root-updater/root-updater.ipk').stat().st_size}})
            fixture.up_store.write('bootstrap',{'phase':'provisioning'})
            fixture.up_store.write('installed-terminal',self.terminal('com.cleanyourtv.root.updater'))
            with patch.object(bootstrap,'STATE',fixture.updater),patch.object(bootstrap,'ROOT_STATE',fixture.root),patch.object(bootstrap,'INSTALLED',fixture.installed),patch.object(bootstrap,'BASE',base),patch.object(bootstrap,'HOOK',hook),patch.object(bootstrap,'safe_bytes',fixture.device_module.safe_bytes),patch.object(bootstrap,'atomic',atomic),patch.object(updater_store,'Store',FixtureStore),patch.object(updater_device,'Device',FixtureDevice),patch('startup_hook.install_link'),patch.object(provision,'refresh',side_effect=[RuntimeError('transient scanner failure'),None]),patch.dict(sys.modules),patch.object(sys,'path',[str(fixture.payload/'root-updater')]+sys.path):
                sys.modules.pop('cancel_provision',None)
                self.assertFalse((fixture.updater/'code/cancel_provision.py').exists())
                from installation import device_operation
                read=lambda path: fixture.up_store.read('bootstrap') if path.parent==fixture.updater and path.name=='bootstrap.json' else None
                with self.assertRaisesRegex(RuntimeError,'transient'):
                    with device_operation('root-bootstrap',ownership=fixture.owner,read=read):bootstrap.resume(fixture.payload/'root-updater')
                self.assertEqual(Path(sys.modules['cancel_provision'].__file__).resolve(),(fixture.payload/'root-updater/cancel_provision.py').resolve())
                pending=fixture.owner.status()['id']
                self.assertFalse(fixture.owner.status()['terminal'])
                saved=fixture.up_store.read('registration')
                with device_operation('root-bootstrap',recovery=True,ownership=fixture.owner,read=read) as lease:
                    self.assertEqual(lease['id'],pending)
                    self.assertTrue(bootstrap.resume(fixture.payload/'root-updater')['installed'])
                self.assertTrue(fixture.owner.status()['terminal'])
                self.assertEqual(fixture.up_store.read('registration'),saved)
                self.assertEqual(fixture.up_store.read('bootstrap')['phase'],'complete')
                (fixture.updater/'installed-terminal.json').unlink()
                fixture.up_store.write('bootstrap',{'phase':'accepted-updater'})
                with self.assertRaisesRegex(ValueError,'outcome unknown'):
                    with device_operation('root-bootstrap',recovery=True,ownership=fixture.owner,read=read):bootstrap.resume(fixture.payload/'root-updater')
                self.assertFalse(fixture.owner.status()['terminal'])
            fixture.assert_preserved(self)

class ChildOwnershipRecoveryTests(unittest.TestCase):
    def test_live_provision_child_blocks_continuation_even_after_worker_lease_released(self):
        import subprocess
        from unittest.mock import patch
        from install_fixture import CurrentInstallation
        from install_device import LocalDevice
        import deploy
        executable=sys.executable
        with CurrentInstallation() as fixture:
            provision=fixture.provision
            driver=install_driver.Coordinator(LocalDevice(),fixture.owner)
            driver.install('a'*32,fixture.payload);snapshot=fixture.snapshot('a'*32)
            fixture.retain('a'*32)
            fixture.root_store.write('install-terminal',ComponentTerminalRecoveryTests.terminal('com.cleanyourtv.root.preview'))
            fixture.root_store.write('deploy',{'app':'com.cleanyourtv.root.preview','stage':'provision-finalize-starting'})
            code="import fcntl,sys;f=open(sys.argv[1],'a');fcntl.flock(f,fcntl.LOCK_EX);print('locked',flush=True);sys.stdin.read()"
            child=subprocess.Popen([executable,'-c',code,str(fixture.root/'provision.lock')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
            try:
                self.assertEqual(child.stdout.readline().strip(),'locked')
                def command(args):
                    with patch.object(provision,'STATE',fixture.root),patch.object(provision.os,'geteuid',return_value=0),patch.object(sys,'argv',['provision',args[-1]]):provision.main()
                    return {'returnValue':True}
                errors=io.StringIO()
                with redirect_stderr(errors),patch.object(deploy,'command',side_effect=command),patch.object(provision,'refresh') as refresh:
                    result=driver.resume('a'*32,snapshot)
                self.assertIn('BlockingIOError',errors.getvalue())
                self.assertEqual(result['state'],'recovery_required');self.assertFalse(fixture.owner.status()['terminal'])
                refresh.assert_not_called();self.assertIsNone(child.poll())
            finally:
                child.stdin.close();child.wait(timeout=5);child.stdout.close()

    def test_changed_snapshot_root_code_is_rejected_before_any_continuation(self):
        from install_fixture import CurrentInstallation
        from install_device import LocalDevice
        from cytv import package
        import hashlib,json,io,tarfile
        with CurrentInstallation() as fixture:
            driver=install_driver.Coordinator(LocalDevice(),fixture.owner)
            original=driver.install('a'*32,fixture.payload);snapshot=fixture.snapshot('a'*32)
            manifest=json.loads((snapshot/'root/bundle.json').read_text());path=snapshot/'root'/manifest['package'];parts=package.read_ar(path.read_bytes());files=package.data_files(path.read_bytes())
            files['usr/palm/applications/com.cleanyourtv.root.preview/index.html']=b'unreviewed replacement'
            with tarfile.open(fileobj=io.BytesIO(parts['data.tar.gz']),mode='r:gz') as archive:executable={m.name for m in archive if m.isfile() and m.mode&0o111}
            parts['data.tar.gz']=package.tgz(files,executable,directories=False);path.write_bytes(package.ar(parts))
            manifest['files'][manifest['package']]=hashlib.sha256(path.read_bytes()).hexdigest();(snapshot/'root/bundle.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'root_code_changed'):driver.resume('a'*32,snapshot)
            self.assertEqual(fixture.owner.status()['id'],original['lease']);self.assertTrue(fixture.owner.status()['terminal'])

class ReservationCheckpointRecoveryTests(unittest.TestCase):
    def test_affined_lease_before_first_checkpoint_can_continue_original_request_only(self):
        from install_device import LocalDevice
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        owner=Ownership(Store(Path(temp.name).resolve()/'ownership',uid=os.getuid()))
        class BeforeSubmission(Device):
            resume_install=LocalDevice.resume_install
            def verify_resume(self,*args):return {'migrate':False,'prepare_supervisor':False}
            def absent(self,*args):pass
        device=BeforeSubmission();driver=install_driver.Coordinator(device,owner,read=lambda p:None)
        with owner.operation('product','product-'+'a'*32+'.json') as lease:identifier=lease['id']
        owner.store.write('submission-'+'a'*32,{'operation':'a'*32,'action':'install','candidate_sha256':'0'*64})
        result=driver.resume('a'*32,'/verified')
        self.assertEqual(result['state'],'complete');self.assertEqual(owner.status()['id'],identifier)
        self.assertEqual(device.calls.count('deploy'),1)
        self.assertEqual(driver.install('a'*32,'/verified'),result)

    def test_busy_duplicate_before_checkpoint_does_not_poison_original_request(self):
        from install_fixture import CurrentInstallation
        from install_device import LocalDevice
        from unittest.mock import patch
        with CurrentInstallation() as fixture:
            identifier='a'*32;snapshot=fixture.snapshot(identifier)
            with fixture.owner.operation('product','product-'+identifier+'.json') as lease:
                lease_id=lease['id'];output=io.StringIO();errors=io.StringIO()
                with patch.object(sys,'argv',['install_driver','install','--operation',identifier,'--payload',str(snapshot),'--worker','--resume']),redirect_stdout(output),redirect_stderr(errors):
                    install_driver.main()
                self.assertIn('installation_operation_retained',errors.getvalue())
                self.assertIsNone(fixture.owner.store.read('request-'+identifier))
            completed=install_driver.Coordinator(LocalDevice(),fixture.owner).resume(identifier,snapshot)
            self.assertEqual(completed['state'],'complete');self.assertEqual(completed['lease'],lease_id)

class SavedRemovalTerminalTests(unittest.TestCase):
    def test_saved_terminal_requires_actual_error_free_bound_reply_not_absence(self):
        from installation import terminal_removal
        app='com.cleanyourtv.root.preview'
        for value in ({},None,{'completed':True},{'completed':True,'event':{'details':{}}},
          {'completed':True,'event':{'id':'other','details':{'state':'removed'}}},
          {'completed':True,'event':{'details':{'state':'removed','errorCode':1}}}):
            with self.subTest(value=value):self.assertFalse(terminal_removal(value,app))
        self.assertTrue(terminal_removal({'completed':True,'event':{'details':{'state':'removed'}}},app))


class ProductABITests(unittest.TestCase):
    def test_real_current_adapter_rejects_unsupported_os_machine_and_elf_before_setup(self):
        from unittest.mock import patch
        from install_fixture import CurrentInstallation
        import install_device
        with CurrentInstallation() as fixture:
            device=install_device.LocalDevice()
            self.assertEqual(device.inspect()['state'],'installed')
            for kernel in ('armv7l','armv8l','aarch64'):
                with self.subTest(supported_kernel=kernel),patch.object(install_device.platform,'machine',return_value=kernel):
                    install_device.require_product_abi()
                    self.assertEqual(device.inspect()['state'],'installed')
            options={'migrate':False,'prepare_supervisor':False}
            for attribute,value in (('platform','darwin'),('machine','x86_64'),('machine','armv6l')):
                target=install_device.sys if attribute=='platform' else install_device.platform
                context=patch.object(target,attribute,value) if attribute=='platform' else patch.object(target,attribute,return_value=value)
                with self.subTest(attribute=attribute,value=value),context:
                    self.assertEqual(device.inspect()['state'],'unsupported')
                    with self.assertRaisesRegex(RuntimeError,'unsupported_product_abi'):
                        device.preflight(fixture.payload,options)
                    # Cleanup payload validation does not gain install prerequisites.
                    device.preflight(fixture.payload,options,product=False)
            original=install_device.safe_bytes
            for index,value in ((4,2),(5,2),(18,62),(37,4),(39,4)):
                elf=bytearray(40);elf[:6]=b'\x7fELF\x01\x01';elf[18]=40;elf[39]=5;elf[index]=value
                with self.subTest(elf=index),patch.object(install_device,'safe_bytes',side_effect=lambda path,*a,**kw: bytes(elf) if path==Path('/bin/sh').resolve() else original(path,*a,**kw)):
                    self.assertEqual(device.inspect()['state'],'unsupported')
                    with self.assertRaisesRegex(RuntimeError,'unsupported_product_abi'):
                        device.preflight(fixture.payload,options)
            fixture.assert_preserved(self)


@unittest.skipUnless(os.name == 'posix', 'TV file metadata requires POSIX')
class SelectedRuntimeContractTests(unittest.TestCase):
    def setUp(self):
        import hashlib
        import deploy
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.root=Path(self.folder.name).resolve();self.installed=self.root/'installed';self.payload=self.root/'payload'
        self.files={}
        self.names=(*deploy.SUPPORT_FILES,'runtime/emergency_trial.py','runtime/persistent_health.py')
        for name in self.names:
            raw=('selected '+name).encode();self.files[name]=hashlib.sha256(raw).hexdigest()
            for target in (self.installed/name,self.payload/'root'/name):
                target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);target.chmod(0o600)
        # Model an independently validated old receipt; only the desired bundle
        # verifier is replaced at this boundary, actual fixed-path reads run.
        (self.installed/'bundle.json').write_text('{"old_self_consistent_receipt":true}')
        self.manifest={'files':self.files}

    def require(self):
        import install_device
        with patch.object(install_device,'ROOT',self.installed),patch('deploy.verify_bundle',return_value=self.manifest):
            return install_device.LocalDevice().require_selected_runtime(self.payload)

    def test_each_selected_runtime_and_support_member_must_match_actual_bytes(self):
        import install_device
        self.assertIsNone(self.require())
        for name in self.names:
            with self.subTest(name=name):
                path=self.installed/name;old=path.read_bytes();path.write_bytes(b'self-consistent old runtime')
                with self.assertRaises(install_device.InstallerRuntimeMismatch) as caught:self.require()
                self.assertEqual(caught.exception.reason_code,'installer-runtime-mismatch')
                self.assertEqual(path.read_bytes(),b'self-consistent old runtime')
                path.write_bytes(old)
        self.assertIsNone(self.require())

    def test_missing_or_indirect_runtime_is_refused_without_repair(self):
        import install_device
        path=self.installed/'runtime/emergency_trial.py';raw=path.read_bytes();path.unlink()
        with self.assertRaises(install_device.InstallerRuntimeMismatch):self.require()
        self.assertFalse(path.exists())
        foreign=self.root/'foreign';foreign.write_bytes(raw);foreign.chmod(0o600)
        path.symlink_to(foreign)
        with self.assertRaises(install_device.InstallerRuntimeMismatch):self.require()
        self.assertTrue(path.is_symlink());self.assertEqual(foreign.read_bytes(),raw)

    def test_unverified_selected_bundle_is_not_treated_as_an_old_runtime(self):
        import install_device
        with patch.object(install_device,'ROOT',self.installed),patch('deploy.verify_bundle',side_effect=ValueError('bundle integrity mismatch')):
            with self.assertRaises(ValueError) as caught:install_device.LocalDevice().require_selected_runtime(self.payload)
        self.assertNotIsInstance(caught.exception,install_device.InstallerRuntimeMismatch)
