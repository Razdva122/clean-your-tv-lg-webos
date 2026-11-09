import os
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installation import Ownership, Busy
from updater.store import Store
from install_driver import Coordinator


class Device:
    def __init__(self): self.calls = []; self.fail = None
    def clean_remove(self, record, save):
        for stage in ('original-writers-fenced', 'controls-restored', 'package-removal', 'private-cleanup'):
            if stage not in record['done']:
                save(stage)
                self.calls.append(stage)
                if stage == self.fail: raise OSError('PRIVATE')
                record['done'].append(stage)
                save(stage)
        return {'removed':True, 'applications_services_startup_removed':True, 'private_cleanup_verified':True}
    def verify_clean(self, record): self.calls.append('verify'); return True


class CoordinatorCleanRemoval(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.owner = Ownership(Store(Path(self.tmp.name).resolve()/'installation', uid=os.getuid()))
        self.device = Device(); self.id = 'a'*32
        self.driver = Coordinator(self.device, self.owner, read=lambda path:None)

    def original(self):
        with self.owner.operation('product', 'product-'+self.id+'.json') as lease:
            self.owner.stage(lease, 'root-updater')
            original = dict(operation=self.id, action='install', stage='root-updater', state='recovery_required',
                            lease=lease['id'], candidate_sha256='b'*64, failure={'exit_status':127})
            self.owner.store.write('request-'+self.id, original)
        return original

    def test_partial_install_uses_original_lease_and_preserves_first_failure(self):
        original = self.original()
        result = self.driver.clean_remove(self.id)
        self.assertEqual(result['stage'], 'verified-clean')
        self.assertEqual(result['original']['request'], original)
        self.assertEqual(result['lease'], original['lease'])
        self.assertEqual(self.owner.store.read('request-'+self.id), original)
        with self.assertRaises(Busy):
            with self.owner.operation('product', 'product-'+self.id+'.json', resume=original['lease']): pass

    def test_retry_keeps_first_and_latest_failure_separate(self):
        first=RuntimeError('PRIVATE first');first.luna={'call':'apps-dev','reason':'permission-denied','error_code':-1}
        last=TimeoutError('PRIVATE last');last.luna={'call':'home-settings','reason':'timeout'}
        def failed(record,save):
            save('original-writers-fenced');raise first
        self.device.clean_remove=failed
        one=self.driver.clean_remove(self.id)
        def retried(record,save):
            save('original-writers-fenced');raise last
        self.device.clean_remove=retried
        two=self.driver.clean_remove(self.id)
        self.assertEqual(two['failure'],one['failure'])
        self.assertEqual(two.get('last_failure'),{'exception_type':'TimeoutError',
            'stage':'original-writers-fenced','luna':{'call':'home-settings','reason':'timeout'}})
        self.assertEqual(two['failure']['luna']['call'],'apps-dev')
        self.assertNotIn('PRIVATE',str(two))

    def test_cleanup_context_rethrows_same_error_and_worker_filters_untrusted_steps(self):
        from clean_removal import cleanup_step
        from install_driver import failure_summary
        error=RuntimeError('PRIVATE')
        with self.assertRaises(RuntimeError) as caught:
            with cleanup_step('home-readback'):
                raise error
        self.assertIs(caught.exception,error)
        self.assertEqual(failure_summary(error),{'exception_type':'RuntimeError','cleanup_step':'home-readback'})
        for unsafe in ('PRIVATE',{'path':'PRIVATE'},['PRIVATE'],True,None):
            error.cleanup_step=unsafe
            self.assertEqual(failure_summary(error),{'exception_type':'RuntimeError'})

    def test_before_first_lease_late_original_worker_cannot_acquire(self):
        result = self.driver.clean_remove(self.id)
        with self.assertRaises(Busy):
            with self.owner.operation('product', 'product-'+self.id+'.json'): pass
        self.assertEqual(result['original']['request'], None)

    def test_clean_native_install_handoff_uses_new_lease_and_never_replays(self):
        first=self.driver.clean_remove(self.id)
        calls=[]
        self.device.preflight=lambda payload,options,product:calls.append(('preflight',product))
        self.device.prepare_clean_install=lambda record:calls.append(('handoff',record['operation']))
        self.device.native_deploy=lambda payload:{'returnValue':True,'installed':'com.cleanyourtv.root.preview','home_changed':False}
        identifier='b'*32
        result=self.driver.native_install(identifier,'/verified')
        self.assertEqual(result['state'],'complete')
        self.assertEqual(result['clean_predecessor'],first['operation'])
        self.assertNotEqual(result['lease'],first['lease'])
        self.assertEqual(calls,[('preflight',False),('handoff',self.id)])
        self.assertEqual(self.driver.native_install(identifier,'/verified'),result)
        self.assertEqual(len(calls),2)

    def test_private_cleanup_interruption_resumes_without_package_replay(self):
        self.original(); self.device.fail = 'private-cleanup'
        first = self.driver.clean_remove(self.id)
        self.assertEqual(first['stage'], 'private-cleanup')
        self.assertEqual(first['reason'], 'private-cleanup-incomplete')
        self.device.fail = None
        result = self.driver.clean_remove(self.id)
        self.assertEqual(result['stage'], 'verified-clean')
        self.assertEqual(self.device.calls.count('package-removal'), 1)
        self.driver.clean_remove(self.id)
        self.assertEqual(self.device.calls.count('package-removal'), 1)

    def test_other_live_ownership_lock_blocks_before_any_effect(self):
        self.original()
        with self.owner.operation('product', 'product-'+self.id+'.json', resume=self.owner.status()['id']):
            with self.assertRaises(Busy): self.driver.clean_remove(self.id)
        self.assertEqual(self.device.calls, [])

    def test_verified_removal_fresh_install_then_new_removal_keeps_old_fence(self):
        first=self.driver.clean_remove(self.id)
        new='b'*32
        self.device.prepare_clean_install=lambda record:self.device.calls.append('handoff')
        result=self.driver._run(new,'install',lambda checkpoint:{'verified':True})
        self.assertEqual(result['state'],'complete')
        self.assertNotEqual(result['lease'],first['lease'])
        self.assertEqual(self.device.calls.count('handoff'),1)
        before=list(self.device.calls)
        old=self.driver._run(self.id,'install',lambda checkpoint:self.fail('old worker executed'))
        self.assertEqual(old['code'],'clean_removal_requested')
        self.assertEqual(self.device.calls,before)
        second=self.driver.clean_remove(new)
        self.assertEqual(second['stage'],'verified-clean')
        self.assertNotEqual(second['lease'],first['lease'])

    def test_old_clean_remove_and_workers_cannot_reclaim_no_root_successor(self):
        original=self.driver.clean_remove(self.id)
        successor=dict(schema=1,id='f'*32,owner='no-root',journal='no-root-'+'e'*32+'.json',stage='reserved',terminal=False)
        self.owner.store.write('operation',successor)
        before=list(self.device.calls)
        for expected in (None,original['lease']):
            with self.subTest(expected=expected),self.assertRaises(Busy):
                self.driver.clean_remove(self.id,intent=original['removal'],expected_lease=expected)
        with self.assertRaises(Busy):
            with self.owner.operation('product','product-'+self.id+'.json',resume=original['lease']):pass
        self.assertEqual(self.device.calls,before)
        self.assertEqual(self.owner.status(),successor)

    def test_completed_removal_rotates_fence_and_old_retry_cannot_sweep_new_apps(self):
        first=self.driver.clean_remove(self.id)
        self.assertNotEqual(first['lease'],self.owner.status()['id'])
        self.assertEqual(first['final_fence'],self.owner.status()['id'])
        before=list(self.device.calls)
        self.device.clean_remove=lambda *args:self.fail('completed goal swept a new installation')
        self.device.verify_clean=lambda record:(_ for _ in ()).throw(ValueError('project_apps_remain'))
        with self.assertRaisesRegex(ValueError,'project_apps_remain'):self.driver.clean_remove(self.id)
        self.assertEqual(before,self.device.calls)

    def test_new_explicit_remove_selects_new_goal_after_completed_fence(self):
        first=self.driver.clean_remove(self.id)
        new='d'*32
        target=self.driver.removal_target(new)
        self.assertEqual(target['target_operation'],new)
        self.assertIsNone(target['target_removal'])
        second=self.driver.clean_remove(new,intent='e'*32,expected_lease=target['target_lease'])
        self.assertEqual(second['stage'],'verified-clean')
        self.assertNotEqual(second['final_fence'],first['final_fence'])
        self.assertEqual(self.owner.store.read('clean-removal-'+self.id),first)

    def test_explicit_new_root_removal_can_retire_bound_no_root_successor(self):
        first=self.driver.clean_remove(self.id)
        binding=dict(schema=1,protocol='no-root-root-handoff-v1',operation='e'*32,lease='f'*32,plan_sha256='0'*64)
        self.owner.store.write('no-root-'+binding['operation'],binding)
        self.owner.store.write('operation',dict(schema=1,id=binding['lease'],owner='no-root',journal='no-root-'+binding['operation']+'.json',stage='reserved',terminal=False))
        second=self.driver.clean_remove('d'*32,intent='9'*32,expected_lease='f'*32)
        self.assertEqual(second['stage'],'verified-clean')
        self.assertNotEqual(second['final_fence'],first['final_fence'])

    def test_inspect_and_restore_verified_removal_preserve_fences_and_old_request(self):
        original=self.original();self.driver.clean_remove(self.id)
        self.device.inspect=lambda:{'state':'recovery_required','can_install':False,'can_maintain':False}
        self.device.restore=lambda:self.fail('removed driver executed')
        before=self.owner.status().copy()
        result=self.driver.inspect()
        self.assertTrue(result.get('clean_removal_verified'))
        self.assertTrue(result['can_install']);self.assertFalse(result['can_maintain'])
        self.assertTrue(self.driver.restore()['already_removed'])
        self.assertEqual(self.owner.status(),before)
        self.assertEqual(self.owner.store.read('request-'+self.id),original)

    def test_clean_inspection_refuses_incomplete_or_drifted_proof(self):
        self.driver.clean_remove(self.id)
        self.device.inspect=lambda:{'state':'recovery_required','can_install':False,'can_maintain':False}
        original=self.owner.store.read('clean-removal-'+self.id)
        for key,value in [('lease','f'*32),('current',False),('stage','private-cleanup')]:
            with self.subTest(key=key):
                record=dict(original);record[key]=value
                self.owner.store.write('clean-removal-'+self.id,record)
                with self.assertRaises((Busy,ValueError)):self.driver.inspect()
        self.owner.store.write('clean-removal-'+self.id,original)
        self.device.verify_clean=lambda record:False
        with self.assertRaises((Busy,ValueError)):self.driver.inspect()

    def test_clean_inspection_respects_original_global_mutex(self):
        self.driver.clean_remove(self.id)
        lease=self.owner.status()
        with self.owner.operation('clean-removal',lease['journal'],resume=lease['id']):
            with self.assertRaises(Busy):self.driver.inspect()

    def test_inspect_reports_only_fixed_stale_support_restart_reason(self):
        import install_driver,install_device,io,json
        from contextlib import redirect_stdout
        for error,restart in ((ValueError('support_stage_remains'),True),(ValueError('live_original_worker'),True),
                              (ValueError('support_stage_remains private details'),False),(RuntimeError('support_stage_remains'),False)):
            with self.subTest(error=type(error).__name__,restart=restart):
                output=io.StringIO()
                with patch.object(sys,'argv',['install_driver','inspect']),patch.object(Coordinator,'inspect',side_effect=error),patch.object(install_device.LocalDevice,'log'),redirect_stdout(output):
                    install_driver.main()
                result=json.loads(output.getvalue())
                self.assertEqual(result.get('reason'), 'restart-required' if restart else None)
                self.assertEqual(result['state'],'recovery_required')

    def test_inspect_reports_only_fixed_project_apps_cleanup_reason(self):
        import install_driver,install_device,io,json
        from contextlib import redirect_stdout
        for error,reason in ((ValueError('project_apps_remain'),'project-apps-remain'),
                             (ValueError('project_apps_remain PRIVATE'),None),
                             (RuntimeError('project_apps_remain'),None)):
            with self.subTest(error=repr(error)):
                output=io.StringIO()
                with patch.object(sys,'argv',['install_driver','inspect']),patch.object(Coordinator,'inspect',side_effect=error),patch.object(install_device.LocalDevice,'log'),redirect_stdout(output):
                    install_driver.main()
                result=json.loads(output.getvalue())
                self.assertEqual(result.get('reason'),reason)
                self.assertEqual(result['state'],'recovery_required')
                self.assertIs(result['home_changed'],False)
                self.assertNotIn('PRIVATE',output.getvalue())

    def test_reinstalled_apps_keep_the_verified_removal_fence(self):
        self.original();self.driver.clean_remove(self.id)
        lease=self.owner.status().copy()
        record=self.owner.store.read('clean-removal-'+self.id).copy()
        def changed(record):raise ValueError('project_apps_remain')
        self.device.verify_clean=changed
        with self.assertRaisesRegex(ValueError,'project_apps_remain'):self.driver.inspect()
        self.assertEqual(self.owner.status(),lease)
        self.assertEqual(self.owner.store.read('clean-removal-'+self.id),record)

    def test_pending_removal_cannot_handoff_to_new_install(self):
        self.device.fail='private-cleanup';self.driver.clean_remove(self.id)
        with self.assertRaises(Busy):self.driver._run('b'*32,'install',lambda checkpoint:self.fail('executed'))

    def test_parent_never_rewrites_receipt_after_tail_retirement_started(self):
        def tail(record):
            self.device.cleanup_tail_started=True
            final=dict(record,stage='verified-clean',state='complete',current=True)
            self.owner.store.write('clean-removal-'+self.id,final)
            raise OSError('parent interpreter stopped reading its retired runtime')
        self.device.finish_clean_tail=tail
        reply=self.driver.clean_remove(self.id)
        self.assertFalse(reply['current'])
        persisted=self.owner.store.read('clean-removal-'+self.id)
        self.assertEqual(persisted['stage'],'verified-clean')
        self.assertTrue(persisted['current'])

    def test_final_tv_audit_keeps_first_failure_and_hashes_without_private_nested_data(self):
        original=self.original()
        original.update(config={'ssap':'PRIVATE_SECRET'},raw_error='PRIVATE_SECRET')
        self.owner.store.write('request-'+self.id,original)
        self.driver.read=lambda path:{'phase':'recovery-required','error':'PRIVATE_SECRET','profile':{'key':'PRIVATE_SECRET'}}
        result=self.driver.clean_remove(self.id)
        self.assertEqual(result['stage'],'verified-clean')
        self.assertTrue(result['audit_compacted'])
        self.assertNotIn('PRIVATE_SECRET',str(result))
        self.assertEqual(result['original']['request']['failure'],{'exit_status':127})
        self.assertEqual(len(result['original_digests']['request']),64)
        self.assertNotIn('PRIVATE_SECRET',str(self.owner.store.read('request-'+self.id)))


class ConfinedCleanup(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()/'owned';self.root.mkdir(mode=0o700)

    def test_changed_owned_preferences_are_deleted_but_lock_inode_stays(self):
        from clean_removal import retire_tree
        (self.root/'state').mkdir();(self.root/'state/key.json').write_text('changed private key')
        (self.root/'provision.lock').touch();inode=(self.root/'provision.lock').stat().st_ino
        self.assertEqual(retire_tree(self.root,{'state'},{'provision.lock'},os.getuid()),2)
        self.assertEqual((self.root/'provision.lock').stat().st_ino,inode)
        self.assertEqual(retire_tree(self.root,{'state'},{'provision.lock'},os.getuid()),0)

    def test_symlink_and_unclassified_data_prevent_all_deletions(self):
        from clean_removal import retire_tree
        foreign=self.root.parent/'foreign';foreign.write_text('keep')
        (self.root/'config.json').write_text('private')
        (self.root/'code').symlink_to(foreign)
        retire_tree(self.root,{'config.json','code'},uid=os.getuid())
        self.assertFalse((self.root/'code').exists());self.assertEqual(foreign.read_text(),'keep')
        (self.root/'config.json').write_text('private')
        (self.root/'unknown').write_text('do not classify by prefix')
        with self.assertRaises(ValueError):retire_tree(self.root,{'config.json'},uid=os.getuid())
        self.assertTrue((self.root/'config.json').exists())

    def test_interrupted_cleanup_never_recreates_deleted_private_bytes(self):
        from clean_removal import retire_tree
        for name in ('key.json','code.py'):(self.root/name).write_text('private')
        real=os.unlink;calls=[]
        def interrupted(name,**kwargs):
            calls.append(name)
            if name=='key.json':raise OSError('storage failure')
            return real(name,**kwargs)
        with patch('clean_removal.os.unlink',side_effect=interrupted):
            with self.assertRaises(OSError):retire_tree(self.root,{'key.json','code.py'},uid=os.getuid())
        self.assertEqual(calls,['code.py','key.json']);self.assertFalse((self.root/'code.py').exists())
        self.assertEqual(retire_tree(self.root,{'key.json','code.py'},uid=os.getuid()),1)

    def test_partial_registration_restore_checks_foreign_bytes_before_any_write(self):
        import clean_removal
        base=self.root.parent/'bus';app='com.cleanyourtv.root.updater';files={}
        for folder,suffix in (('services.d','.service'),('roles.d','.service.json'),('client-permissions.d','.service.json'),('api-permissions.d','.api.json')):
            (base/folder).mkdir(parents=True)
            path=base/folder/(app+'.service'+suffix);path.write_text('installed')
            files[str(path)]={'original':'original','installed':'installed'}
        Store(self.root,uid=os.getuid()).write('registration',{'files':files})
        victim=Path(sorted(files)[-1]);victim.write_text('foreign')
        with self.assertRaisesRegex(ValueError,'ownership_conflict'):
            clean_removal.restore_registrations(self.root,app,base,os.getuid())
        self.assertEqual(victim.read_text(),'foreign')
        self.assertTrue(all(Path(name).read_text()=='installed' for name in files if name!=str(victim)))
        victim.write_text('original')
        clean_removal.restore_registrations(self.root,app,base,os.getuid())
        self.assertTrue(all(Path(name).read_text()=='original' for name in files))

    def test_compositor_stock_subprocess_protocol_returns_fresh_proof(self):
        from install_device import LocalDevice
        payload=self.root/'support';(payload/'root-updater').mkdir(parents=True)
        proof={'mode':'stock-compositor','target':{'dev':45851,'ino':5647,'size':50684},'target_sha256':'a'*64}
        (payload/'root-updater/clean_removal.py').write_text('def compositor_stock(payload):\n    return '+repr(proof)+'\n')
        device=LocalDevice();device.payload=payload
        self.assertEqual(device.compositor_stock({'operation':'c'*32}),proof)

    def test_native_deploy_child_keeps_mutex_and_ignores_only_its_parent_lease(self):
        from install_device import LocalDevice
        payload=self.root/'support';root=payload/'root';root.mkdir(parents=True)
        owner=Ownership(Store(self.root/'installation',uid=os.getuid()))
        (root/'deploy.py').write_text('''import fcntl,json,os
def checked_file(root,name):return b'{"routing":"compositor-keyfilter-v1"}'
def experimental_admission(routing,owned_operation=None):
    assert routing=='compositor-keyfilter-v1'
    path=os.path.dirname(os.path.dirname(__file__))+'/../installation/ownership.lock'
    inherited=int(open(os.path.dirname(__file__)+'/lease-fd').read())
    assert os.fstat(inherited).st_ino==os.stat(path).st_ino
    fd=os.open(path,os.O_RDWR)
    try:
        try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:pass
        else:raise AssertionError('child lost original mutex')
    finally:os.close(fd)
    return owned_operation
def install(bundle,experimental_c1_gate=False,_experimental_admission=None):
    assert experimental_c1_gate is True
    return {'returnValue':True,'observed_lease':_experimental_admission}
''')
        device=LocalDevice();device.ownership=owner
        with owner.operation('product','product-'+'c'*32+'.json') as lease:
            device.operation=lease
            (root/'lease-fd').write_text(str(owner.fd))
            result=device.native_deploy(payload)
            self.assertEqual(result,{'returnValue':True,'observed_lease':lease['id']})

    def test_current_native_restore_selects_only_verified_new_bundle_executable(self):
        import hashlib
        import clean_removal
        from unittest.mock import Mock
        payload=self.root/'bundle';(payload/'runtime').mkdir(parents=True)
        native=payload/'runtime/c1-home-gate';native.write_bytes(b'current native');native.chmod(0o600)
        backend=Mock();backend.STATE=self.root/'old';backend.selection.return_value={'routing':'mount-v1','native_sha256':'0'*64}
        cli=Mock();cli.gate_backend.return_value=backend
        def restore(mode):
            self.assertEqual(mode,'restore');self.assertEqual(backend.binary(backend.STATE,os.getuid()),native)
            return 'restored'
        cli.main.side_effect=restore
        with patch.dict(sys.modules,{'cli':cli}),patch('deploy.verify_bundle',return_value={'files':{'runtime/c1-home-gate':hashlib.sha256(native.read_bytes()).hexdigest()}}),patch('deploy.checked_file',return_value=native.read_bytes()):
            before=list(sys.path)
            try:self.assertEqual(clean_removal.runtime_restore(payload,os.getuid())['result'],'restored')
            finally:sys.path[:]=before
        self.assertEqual(native.stat().st_mode&0o777,0o700)


class PackageRemoval(unittest.TestCase):
    def test_old_unknown_is_separate_from_new_remove_terminal(self):
        import clean_removal
        from unittest.mock import Mock
        app=clean_removal.APPS[0];present={app};calls=[]
        device=Mock();device.apps.side_effect=lambda:set(present)
        def absent(identity,terminal=None):self.assertNotIn(identity,present)
        device.absent.side_effect=absent
        def remove(identity,timeout):
            calls.append(identity);present.remove(identity)
            return {'completed':True,'event':{'id':identity,'details':{'packageId':identity,'state':'removed'}}}
        record={'packages':{},'original':{'outcome':'unknown'}}
        with patch('observed_install.remove',side_effect=remove):
            clean_removal.remove_packages(device,record,lambda stage:None)
            clean_removal.remove_packages(device,record,lambda stage:None)
        self.assertEqual(calls,[app]);self.assertEqual(record['original']['outcome'],'unknown')

    def test_retry_skips_absent_package_after_connection_loss(self):
        import clean_removal
        from unittest.mock import Mock
        app=clean_removal.APPS[0];device=Mock();device.apps.return_value={app}
        record={'packages':{}}
        with patch('observed_install.remove',side_effect=OSError('lost')) as remove:
            with self.assertRaises(OSError):clean_removal.remove_packages(device,record,lambda stage:None)
            device.apps.return_value=set()
            clean_removal.remove_packages(device,record,lambda stage:None)
        self.assertEqual(remove.call_count,1)


class PartialDeviceRemoval(unittest.TestCase):
    def lockdown_retry_fixture(self, metadata=True):
        import copy,json,types,install_device
        from cytv.system_updater_remove import SCRIPT
        fixture=self.fixture();driver,identifier,root,updater,payload,calls,present=fixture
        base=install_device.BUS;system=install_device.SUPERVISOR;system.mkdir(mode=0o700)
        app='com.cleanyourtv.root.updater';service=app+'.service'
        paths={key:base/folder/(service+suffix) for key,folder,suffix in (
            ('service','services.d','.service'),('role','roles.d','.service.json'),
            ('client','client-permissions.d','.service.json'),('api','api-permissions.d','.api.json'))}
        installed_api=json.dumps({'fixture.api':[service+'/status',service+'/install']})
        disabled_api=json.dumps({'fixture.api':[service+'/status']})
        registration={'files':{}}
        for key,path in paths.items():
            path.parent.mkdir(parents=True,exist_ok=True)
            original='{"sdk":[]}' if key=='api' else 'SDK '+key
            installed=installed_api if key=='api' else 'private '+key
            path.write_text(installed);path.chmod(0o600)
            registration['files'][str(path)]={'original':original,'installed':installed,
                                             'mode':0o600,'uid':os.getuid(),'gid':os.getgid()}
            if not metadata:
                for name in ('mode','uid','gid'):registration['files'][str(path)].pop(name)
        disabled=copy.deepcopy(registration);disabled['files'][str(paths['api'])]['installed']=disabled_api
        original_raw=json.dumps(registration);disabled_raw=json.dumps(disabled)
        receipt=updater/'registration.json';receipt.write_text(disabled_raw);receipt.chmod(0o600)
        paths['api'].write_text(disabled_api)
        legacy={'schema':1,'files':{str(paths['api']):{'original':installed_api,'disabled':disabled_api,'mode':0o600},
                                   str(receipt):{'original':original_raw,'disabled':disabled_raw,'mode':0o600}}}
        Store(system,uid=os.getuid()).write('legacy-lockdown',legacy)
        module=types.ModuleType('cleanup_system_updater');exec(SCRIPT,module.__dict__);module.ROOT_UPDATER=updater
        patcher=patch.dict(sys.modules,{'cleanup_system_updater':module});patcher.start();self.addCleanup(patcher.stop)
        return fixture,module,system,paths,legacy

    def test_restore_subprocess_failure_names_boundary_and_retains_inverse(self):
        import subprocess, deploy
        driver,identifier,root,updater,payload,calls,present=self.fixture()
        original=driver.ownership.store.read('request-'+identifier)
        inverse='{"fixture":"PRIVATE routing inverse"}'
        (root/'profile-trial.json').write_text(inverse)
        error=subprocess.CalledProcessError(1,['PRIVATE command'],output=b'PRIVATE output',stderr=b'PRIVATE stderr')
        with patch.object(deploy,'command',side_effect=error),patch.object(driver.device,'log'):
            result=driver.clean_remove(identifier)
        self.assertEqual(result['last_failure'],{'exception_type':'CalledProcessError','exit_status':1,
            'stage':'original-writers-fenced','cleanup_step':'runtime-restore'})
        self.assertEqual(result['state'],'recovery_required')
        self.assertFalse(result['current'])
        self.assertEqual(driver.ownership.store.read('request-'+identifier),original)
        self.assertEqual((root/'profile-trial.json').read_text(),inverse)
        self.assertEqual(driver.ownership.store.read('routing-backup-'+identifier)['profile-trial.json'],inverse)
        self.assertFalse(any(call.startswith(('remove-','cleanup-')) for call in calls))
        self.assertNotIn('PRIVATE',str(result['last_failure']))

    def test_legacy_permissions_failure_does_not_blame_runtime_restore_on_retry(self):
        import subprocess, deploy
        driver,identifier,root,updater,payload,calls,present=self.fixture()
        with patch.object(deploy,'command',side_effect=subprocess.CalledProcessError(1,['PRIVATE'])),patch.object(driver.device,'log'):
            first=driver.clean_remove(identifier)
        cleanup=driver.device.cleanup
        def fail(name,*args):
            if name=='legacy_permissions':raise subprocess.CalledProcessError(7,['PRIVATE'])
            return cleanup(name,*args)
        with patch.object(driver.device,'cleanup',side_effect=fail),patch.object(driver.device,'log'):
            second=driver.clean_remove(identifier)
        self.assertEqual(second['failure'],first['failure'])
        self.assertEqual(second['last_failure']['cleanup_step'],'legacy-permissions')
        self.assertEqual(second['last_failure']['exit_status'],7)
        self.assertTrue(root.exists());self.assertTrue(updater.exists())
        self.assertFalse(any(call.startswith('remove-') for call in calls))

    def test_lockdown_retry_keeps_authenticated_terminal_sdk_api_after_interruption(self):
        import json
        fixture,module,system,paths,legacy=self.lockdown_retry_fixture(metadata=False)
        driver,identifier,root,updater,payload,calls,present=fixture
        present.add('com.gathin.tvhome');rpc=driver.device.rpc;failed=[False]
        def interrupted(method,data):
            if method=='com.gathin.tvhome.renewal/disable':
                if not failed[0]:failed[0]=True;raise RuntimeError('interrupted after registration restoration')
                return {'returnValue':True,'state':{'enabled':False}}
            return rpc(method,data)
        driver.device.rpc=interrupted
        first=driver.clean_remove(identifier)
        self.assertEqual(first['state'],'recovery_required')
        sdk=json.loads(legacy['files'][str(updater/'registration.json')]['original'])['files'][str(paths['api'])]['original']
        self.assertEqual(paths['api'].read_text(),sdk)
        writes=[];write=module.write
        def observed(path,*args,**kwargs):writes.append(path);return write(path,*args,**kwargs)
        with patch.object(module,'write',side_effect=observed):retry=driver.clean_remove(identifier)
        self.assertEqual(retry['stage'],'restart-required',retry)
        self.assertNotIn(paths['api'],writes,'Never republish the intermediate private API on Retry')

    def test_lockdown_terminal_api_requires_complete_exact_lineage_before_writes(self):
        import json
        for damage in ('foreign-api','receipt','installed-link','disabled-snapshot','metadata','missing-receipt'):
            with self.subTest(damage=damage):
                fixture,module,system,paths,legacy=self.lockdown_retry_fixture()
                driver,identifier,root,updater,payload,calls,present=fixture
                receipt=updater/'registration.json';proof=legacy['files'][str(receipt)]
                original=json.loads(proof['original']);api=paths['api']
                api.write_text(original['files'][str(api)]['original']);receipt.write_text(proof['original'])
                if damage=='foreign-api':api.write_text('foreign')
                elif damage=='receipt':receipt.write_text('{"files":{}}')
                elif damage=='installed-link':
                    original['files'][str(api)]['installed']='unlinked';proof['original']=json.dumps(original);receipt.write_text(proof['original'])
                elif damage=='disabled-snapshot':proof['disabled']=json.dumps(original)
                elif damage=='metadata':api.chmod(0o644)
                elif damage=='missing-receipt':legacy['files'].pop(str(receipt))
                Store(system,uid=os.getuid()).write('legacy-lockdown',legacy)
                before={path:path.read_bytes() for path in (*paths.values(),receipt)}
                with patch.object(module,'write',side_effect=AssertionError('Unverified lineage wrote registration')):
                    result=driver.clean_remove(identifier)
                self.assertEqual(result['state'],'recovery_required')
                self.assertEqual(before,{path:path.read_bytes() for path in before})

    def test_terminal_sdk_api_with_metadata_is_scoped_to_explicit_clean_removal(self):
        import json
        fixture,module,system,paths,legacy=self.lockdown_retry_fixture()
        driver,identifier,root,updater,payload,calls,present=fixture
        receipt=updater/'registration.json';proof=legacy['files'][str(receipt)]
        original=json.loads(proof['original']);api=paths['api']
        api.write_text(original['files'][str(api)]['original']);receipt.write_text(proof['original'])
        before=api.stat()
        with self.assertRaisesRegex(ValueError,'Legacy lockdown file changed'):module.lockdown(system,api.parents[1])
        from clean_removal import validate_restored_root_api
        entries=module.lockdown(system,api.parents[1],check=lambda files:validate_restored_root_api(files,api.parents[1],updater,os.getuid()))
        self.assertNotIn(str(api),entries)
        self.assertEqual((before.st_ino,before.st_mode,before.st_uid,before.st_gid),
                         (api.stat().st_ino,api.stat().st_mode,api.stat().st_uid,api.stat().st_gid))

    def test_known_completed_root_and_system_receipts_are_retired_with_inverse_preserved(self):
        import install_device
        driver,identifier,root,updater,payload,calls,present=self.fixture()
        driver.device.ownership=driver.ownership
        system=install_device.SUPERVISOR;system.mkdir(mode=0o700)
        names=[root/'completed-profile-12345678-1234-4abc-8def-123456789abc.json',
               root/('system-rollback-anchor-'+'a'*32+'.json'),
               system/'current-root.json',system/'installer-accepted.json']
        for path in names:path.write_text('{"fixture":"owned receipt"}')
        original='{"fixture":"original Home inverse"}'
        (root/'profile-trial.json').write_text(original)
        record={'operation':identifier,'staging_hashes':[]}
        driver.device.preserve_routing_inverse(record)
        driver.device.retire_clean_private(record)
        self.assertTrue(all(not path.exists() for path in names))
        self.assertEqual(driver.ownership.store.read('routing-backup-'+identifier),{'profile-trial.json':original})

    def test_receipt_name_near_matches_and_wrong_component_are_not_retired(self):
        uuid='12345678-1234-4abc-8def-123456789abc'
        for component,name in [('root','completed-profile-'+'a'*32+'.json'),
                               ('root','completed-profile-'+uuid+'.json.bak'),
                               ('root','system-rollback-anchor-'+'a'*31+'.json'),
                               ('root','system-rollback-anchor-'+'A'*32+'.json'),
                               ('root','current-root.json'),('updater','installer-accepted.json'),
                               ('updater','completed-profile-'+uuid+'.json')]:
            with self.subTest(component=component,name=name):
                driver,identifier,root,updater,payload,calls,present=self.fixture()
                driver.device.ownership=driver.ownership
                path=(root if component=='root' else updater)/name;path.write_text('preserve')
                with self.assertRaisesRegex(ValueError,'unclassified_private_member'):
                    driver.device.retire_clean_private({'operation':identifier,'staging_hashes':[]})
                self.assertEqual(path.read_text(),'preserve')

    def test_known_receipts_in_authenticated_archives_use_same_classification(self):
        import install_device
        driver,identifier,root,updater,payload,calls,present=self.fixture()
        driver.device.ownership=driver.ownership
        archives=[]
        for index,component in enumerate((root,updater,install_device.SUPERVISOR)):
            archive=component.parent/(component.name+'.archive-'+'a'*32)
            store=Store(archive,uid=os.getuid());archives.append(archive)
            if index==0:
                store.write('deploy',{'app':install_device.APP,'stage':'install-submitting'})
                store.write('profile-trial',{'fixture':'original archive inverse'})
                names=['completed-profile-12345678-1234-4abc-8def-123456789abc.json',
                       'system-rollback-anchor-'+'a'*32+'.json']
            else:
                store.write('cytv-removal',{'archive':str(archive),'phase':'disabling'})
                names=['current-root.json','current-no-root.json','installer-accepted.json'] if index==2 else []
            names.append('profile-'+'b'*32+'.json')
            for name in names:(archive/name).write_text('{"fixture":"owned receipt"}')
        driver.device.retire_clean_private({'operation':identifier,'staging_hashes':[]})
        self.assertTrue(all(not archive.exists() for archive in archives))
        self.assertEqual(driver.store.read('archive-backup-'+identifier+'-0'),
                         {'profile-trial':{'fixture':'original archive inverse'}})

    def test_known_receipt_with_foreign_owner_is_not_retired(self):
        driver,identifier,root,updater,payload,calls,present=self.fixture()
        driver.device.ownership=driver.ownership
        path=root/'completed-profile-12345678-1234-4abc-8def-123456789abc.json';path.write_text('preserve')
        actual=os.stat
        def foreign(name,*args,**kwargs):
            info=actual(name,*args,**kwargs)
            if name==path.name and 'dir_fd' in kwargs:
                fields=list(info);fields[4]=os.getuid()+1;return os.stat_result(fields)
            return info
        with patch('clean_removal.os.stat',side_effect=foreign):
            with self.assertRaisesRegex(ValueError,'unsafe_private_member'):
                driver.device.retire_clean_private({'operation':identifier,'staging_hashes':[]})
        self.assertEqual(path.read_text(),'preserve')

    def test_known_completed_receipt_hardlink_is_still_refused(self):
        driver,identifier,root,updater,payload,calls,present=self.fixture()
        driver.device.ownership=driver.ownership
        path=root/'completed-profile-12345678-1234-4abc-8def-123456789abc.json';path.write_text('preserve')
        other=root.parent/'foreign-copy';os.link(path,other)
        with self.assertRaisesRegex(ValueError,'unsafe_private_member'):
            driver.device.retire_clean_private({'operation':identifier,'staging_hashes':[]})
        self.assertEqual(path.read_text(),'preserve');self.assertEqual(other.read_text(),'preserve')

    def fixture(self, unknown=False, missing_profiles=False):
        import install_device, clean_removal, deploy, startup_hook
        from contextlib import ExitStack
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        base=Path(tmp.name).resolve();root=base/'root';root.mkdir(mode=0o700)
        updater=base/'root-updater';updater.mkdir(mode=0o700)
        supervisor=base/'system';installed=base/'apps';bus=base/'bus';bus.mkdir()
        init=base/'init';init.mkdir();proc=base/'proc';proc.mkdir()
        payload=base/'support';(payload/'root/runtime').mkdir(parents=True);(payload/'root-updater').mkdir()
        (payload/'root/runtime/cli.py').write_text('current source')
        (payload/'root-updater/bundle.json').write_text('{"files":{"install_driver.py":"fixture","package.json":"fixture","services.json":"fixture"}}')
        (root/'state').mkdir();(root/'state/ssap.json').write_text('changed key')
        (root/'runtime').mkdir();(root/'runtime/cli.py').write_text('old executable')
        (root/'updater').mkdir();(root/'updater/store.py').write_text('old support')
        (updater/'code').mkdir();(updater/'code/run-updater.py').write_text('old executable')
        Store(root,uid=os.getuid()).write('deploy',{'version':1,'app':install_device.APP,'stage':'install-submitting' if unknown else 'install-observed'})
        Store(updater,uid=os.getuid()).write('bootstrap',{'phase':'prepared'})
        present={install_device.APP};calls=[]
        class Model(install_device.LocalDevice):
            def rpc(self,method,data):
                calls.append(method)
                if method.endswith('/status'):return {'returnValue':True,'status':{'apps':[]}}
                if method=='com.palm.activitymanager/list':return {'returnValue':True,'activities':[]}
                if method.endswith('/getAllInputStatus'):return {'returnValue':True,'devices':[]}
                if method.endswith('/getSystemSettings'):return {'returnValue':True,'settings':{'defaultApps':{'home':'third.party.home'}}}
                if method.endswith('/getProfiles'):
                    if missing_profiles:return {'returnValue':False,'errorCode':-1}
                    return {'returnValue':True,'profiles':{'defaultApps':{'categories':{'home':'third.party.home'}},'idleApp':{'appId':'third.party.home'}}}
                raise AssertionError(method)
            def apps(self):return set(present)
            def cleanup(self,name,*args):calls.append('cleanup-'+name);return True
            # This OS model stops at Python readback; actual Node/FD handoff is
            # exercised separately for native and managed Python in test_cleanup_tail.
            def finish_clean_tail(self,record):return None
        device=Model();device.payload=payload
        device.shared_cleanup=lambda action,record,**kwargs:{'schema':1,'present':[],'blocked':[],'root_present':[]}
        device.current_boot="11111111-1111-1111-1111-111111111111"
        device.boot_id=lambda:device.current_boot+':session-'+device.current_boot[0]*32
        owner=Ownership(Store(base/'installation',uid=os.getuid()))
        identifier='c'*32
        with owner.operation('product','product-'+identifier+'.json') as lease:
            original={'operation':identifier,'action':'install','stage':'root-deploy','state':'recovery_required','lease':lease['id']}
            owner.store.write('request-'+identifier,original)
        stack=ExitStack();self.addCleanup(stack.close)
        # Discovery also loads runtime/provision.py under the same short name.
        # Production runs coordinator support in its own interpreter; bind that
        # actual source only for this fixture, restoring the runtime module after.
        spec=importlib.util.spec_from_file_location('coordinator_provision_fixture',Path(__file__).resolve().parents[1]/'provision.py')
        provision=importlib.util.module_from_spec(spec);spec.loader.exec_module(provision)
        stack.enter_context(patch.dict(sys.modules,{'provision':provision}))
        temporary=base/'tmp';temporary.mkdir()
        for key,value in {'ROOT':root,'UPDATER':updater,'SUPERVISOR':supervisor,'INSTALLED':installed,'BUS':bus,'INIT':init,'PROC':proc,'TEMP':temporary}.items():stack.enter_context(patch.object(install_device,key,value))
        from installation import _optional_record
        stack.enter_context(patch.object(install_device,'read_journal',side_effect=lambda p:_optional_record(install_device.checked_store(p.parent,os.getuid()),p.name)))
        stack.enter_context(patch.object(startup_hook,'STATE',root));stack.enter_context(patch.object(startup_hook,'HOOK',init/'50-clean-your-tv-root'))
        def current_restore(args):
            calls.append('current-restore');self.assertEqual(args[1:4],['-I','-B','-c'])
            self.assertIn(repr(str(payload/'root-updater')),args[4])
            self.assertIn(repr(str(payload/'root')),args[4])
            return {'returnValue':True,'result':'absent'}
        stack.enter_context(patch.object(deploy,'command',side_effect=current_restore))
        def remove(app,timeout):
            calls.append('remove-'+app);present.remove(app)
            return {'completed':True,'event':{'details':{'state':'removed'}}}
        stack.enter_context(patch('observed_install.remove',side_effect=remove))
        def read(path):
            actual={'deploy':root/'deploy.json','root-bootstrap':updater/'bootstrap.json'}
            import installation
            key=next(k for k,(known,_,_) in installation.JOURNALS.items() if known==path)
            p=actual.get(key)
            return json.loads(p.read_text()) if p and p.exists() else None
        import json
        return Coordinator(device,owner,read),identifier,root,updater,payload,calls,present

    def test_final_activity_checks_preserve_foreign_prefix_but_refuse_known_services(self):
        from clean_removal import APPS
        driver,identifier,*_=self.fixture();rpc=driver.device.rpc
        foreign=[{'name':'com.cleanyourtv.recoveryprobe.boot','activityId':42,'callback':{'method':'luna://com.cleanyourtv.recoveryprobe.service/boot'}},
                 {'name':'foreign','activityId':43,'callback':{'method':'luna://com.cleanyourtv.root.preview.service.foreign/boot'}}]
        activities=list(foreign);cancelled=[]
        def actual(method,data):
            if method=='com.palm.activitymanager/list':return {'returnValue':True,'activities':activities}
            if method=='com.palm.activitymanager/cancel':cancelled.append(data);return {'returnValue':True}
            return rpc(method,data)
        driver.device.rpc=actual
        driver.clean_remove(identifier);driver.device.current_boot='22222222-2222-2222-2222-222222222222'
        result=driver.clean_remove(identifier)
        self.assertEqual(result['stage'],'verified-clean',result)
        self.assertEqual(cancelled,[]);self.assertEqual(activities,foreign)
        for app in APPS:
            callback='luna://'+app+('.renewal/' if app=='com.gathin.tvhome' else '.service/')+'unexpected'
            activities[:]=[{'name':'unexpected','activityId':7,'callback':{'method':callback}}]
            with self.subTest(app=app),self.assertRaisesRegex(ValueError,'owned_activity_remains'):
                driver.device.verify_clean(result)
        activities[:]=[{'name':'com.cleanyourtv.root.preview.service.recovery','callback':{'method':'luna://foreign.service/boot'}}]
        with self.assertRaisesRegex(ValueError,'owned_activity_remains'):driver.device.verify_clean(result)

    def test_boot_reader_authenticates_current_runtime_and_requires_session_identity(self):
        import deploy,install_device
        from install_fixture import CurrentInstallation
        with CurrentInstallation() as fixture:
            device=install_device.LocalDevice();device.payload=fixture.payload
            value='11111111-1111-1111-1111-111111111111:session-'+'a'*32
            with patch.object(deploy,'command',return_value={'returnValue':True,'boot':value}) as command:
                self.assertEqual(device.boot_id(),value)
                args=command.call_args.args[0]
                self.assertEqual(args[1:4],['-I','-B','-c'])
                self.assertIn(repr(str(fixture.payload/'root/runtime')),args[4])
                self.assertIn('boot_identity()',args[4])
                self.assertNotIn(str(fixture.root/'runtime'),args[4])
                (fixture.payload/'root/runtime/intent_runtime.py').write_text('changed current code')
                with self.assertRaises(ValueError):device.boot_id()
                self.assertEqual(command.call_count,1)

    def test_malformed_boot_baseline_refuses_without_sampling_or_cleanup(self):
        driver,identifier,*_=self.fixture();driver.clean_remove(identifier)
        name='clean-removal-'+identifier;record=driver.ownership.store.read(name)
        record['cleanup_boot_id']='invalid';driver.ownership.store.write(name,record)
        with patch.object(driver.device,'boot_id',side_effect=AssertionError('must not create marker')):
            result=driver.clean_remove(identifier)
        self.assertNotEqual(result['stage'],'verified-clean')
        self.assertEqual(result['cleanup_boot_id'],'invalid')

    def test_durable_restart_fact_does_not_recreate_retired_boot_marker(self):
        driver,identifier,*_=self.fixture();driver.clean_remove(identifier)
        driver.device.current_boot='22222222-2222-2222-2222-222222222222'
        self.assertEqual(driver.clean_remove(identifier)['stage'],'verified-clean')
        driver.device.payload=None
        with patch.object(driver.device,'boot_id',side_effect=AssertionError('must not create marker')):
            self.assertEqual(driver.clean_remove(identifier)['stage'],'verified-clean')

    def test_legacy_baseline_reseeds_and_clears_unusable_verified_fact(self):
        driver,identifier,*_=self.fixture()
        first=driver.clean_remove(identifier)
        store=driver.ownership.store
        name='clean-removal-'+identifier
        record=store.read(name);record['cleanup_boot_id']=driver.device.current_boot
        record['cleanup_verified_boot_id']='22222222-2222-2222-2222-222222222222:session-'+'b'*32
        store.write(name,record)
        result=driver.clean_remove(identifier)
        self.assertEqual(result['stage'],'restart-required')
        saved=store.read(name)
        self.assertIn(':session-',saved['cleanup_boot_id'])
        self.assertNotIn('cleanup_verified_boot_id',saved)

    def test_real_partial_trees_clean_without_finishing_install_or_changing_foreign_home(self):
        driver,identifier,root,updater,payload,calls,present=self.fixture()
        self.assertEqual(driver.clean_remove(identifier)['stage'],'restart-required')
        driver.device.current_boot='22222222-2222-2222-2222-222222222222'
        result=driver.clean_remove(identifier)
        self.assertEqual(result['stage'],'verified-clean',result)
        self.assertEqual(set(p.name for p in root.iterdir()),{'deploy.json','provision.lock'})
        self.assertEqual(set(p.name for p in updater.iterdir()),{'bootstrap.json','daemon.lock','worker.lock'})
        self.assertEqual(list(payload.iterdir()),[])
        self.assertEqual(calls.count('remove-com.cleanyourtv.root.preview'),1)
        self.assertLess(calls.index('current-restore'),calls.index('remove-com.cleanyourtv.root.preview'))
        self.assertFalse(any('setDefault' in name or 'launch' in name for name in calls))
        driver.device.payload=None
        self.assertEqual(driver.clean_remove(identifier)['stage'],'verified-clean')
        self.assertEqual(calls.count('remove-com.cleanyourtv.root.preview'),1)

    def optional_startup_restart(self, app, service, outcome, interrupted=False):
        driver,identifier,root,updater,payload,calls,present=self.fixture()
        present.add(app)
        rpc=driver.device.rpc;disabled=[];remaining={'owned':True}
        foreign={'name':'foreign.job','activityId':9,'callback':{'method':'luna://org.foreign/tick'}}
        own={'name':'com.local.nativehome.boot','activityId':7,
             'callback':{'method':'luna://com.local.nativehome.service/tick'}}
        def actual(method,data):
            if method==service+'/disable':
                disabled.append(method)
                if isinstance(outcome,Exception):raise outcome
                return outcome
            if method=='com.palm.activitymanager/list':
                return {'returnValue':True,'activities':[foreign]+([own] if remaining['owned'] else [])}
            if method=='com.palm.activitymanager/cancel':
                self.assertEqual(data,{'activityId':7});remaining['owned']=False
                return {'returnValue':True}
            return rpc(method,data)
        driver.device.rpc=actual
        shared=driver.device.shared_cleanup;actions=[]
        def cleanup(action,record,**kwargs):
            actions.append(action);return shared(action,record,**kwargs)
        driver.device.shared_cleanup=cleanup
        if interrupted:
            with patch.object(driver.device,'remove_owned_registrations',side_effect=OSError('interrupted readback')):
                paused=driver.clean_remove(identifier)
            self.assertIn('controls-restored',paused['done'])
            self.assertFalse(any(name.startswith('remove-') for name in calls))
        first=driver.clean_remove(identifier)
        self.assertEqual(first['stage'],'restart-required',first)
        self.assertEqual(first['cleanup_startup_unavailable'],[service])
        self.assertIs(first['result']['removed'],False)
        self.assertIs(first['result']['verified_clean'],False)
        self.assertFalse(any(name.startswith('remove-') for name in calls))
        self.assertTrue((root/'state/ssap.json').exists())
        self.assertFalse(remaining['owned']);self.assertIn('stop',actions)
        self.assertEqual(driver.clean_remove(identifier)['stage'],'restart-required')
        driver.device.current_boot='22222222-2222-2222-2222-222222222222'
        final=driver.clean_remove(identifier)
        self.assertEqual(final['stage'],'verified-clean',final)
        self.assertIs(final['result']['verified_clean'],True)
        self.assertEqual(disabled,[service+'/disable'])
        self.assertFalse((root/'state/ssap.json').exists())
        self.assertEqual(actual('com.palm.activitymanager/list',{})['activities'],[foreign])

    def test_unconfirmed_legacy_startup_moves_boot_before_package_and_file_cleanup(self):
        for app,service,reply in (
                ('com.gathin.tvhome','com.gathin.tvhome.renewal',
                 {'returnValue':True,'state':{'enabled':False,'error':'cancel-unconfirmed'}}),
                ('com.local.nativehome','com.local.nativehome.service',
                 {'returnValue':True,'cancel':{'returnValue':False}})):
            with self.subTest(service=service):self.optional_startup_restart(app,service,reply)

    def test_unavailable_optional_startup_moves_boot_before_package_and_file_cleanup(self):
        for error in (RuntimeError('Bus operation rejected'),TimeoutError('Bus response timed out')):
            with self.subTest(error=error):
                self.optional_startup_restart('com.gathin.tvhome','com.gathin.tvhome.renewal',error)

    def test_optional_startup_boot_checkpoint_survives_interrupted_registration_readback(self):
        self.optional_startup_restart('com.gathin.tvhome','com.gathin.tvhome.renewal',
            {'returnValue':True,'state':{'enabled':False,'error':'cancel-unconfirmed'}},interrupted=True)

    def test_optional_fallback_does_not_hide_other_errors_or_owned_activity_refusal(self):
        for activity_refusal in (False,True):
            with self.subTest(activity_refusal=activity_refusal):
                driver,identifier,root,updater,payload,calls,present=self.fixture()
                present.add('com.gathin.tvhome');rpc=driver.device.rpc
                def actual(method,data):
                    if method=='com.gathin.tvhome.renewal/disable':
                        if not activity_refusal:raise RuntimeError('unrelated current failure')
                        return {'returnValue':True,'state':{'enabled':False,'error':'cancel-unconfirmed'}}
                    if activity_refusal and method=='com.palm.activitymanager/list':
                        return {'returnValue':True,'activities':[{'name':'com.gathin.tvhome.renewal.hourly',
                            'activityId':7,'callback':{'method':'luna://com.gathin.tvhome.renewal/tick'}}]}
                    if method=='com.palm.activitymanager/cancel':raise RuntimeError('Bus operation rejected')
                    return rpc(method,data)
                driver.device.rpc=actual
                result=driver.clean_remove(identifier)
                self.assertEqual(result['state'],'recovery_required',result)
                self.assertNotEqual(result['stage'],'restart-required')
                self.assertNotEqual(result['stage'],'verified-clean')
                self.assertFalse(any(name.startswith('remove-') for name in calls))
                self.assertTrue((root/'state/ssap.json').exists())

    def test_unknown_old_outcome_does_not_prevent_owned_file_cleanup(self):
        driver,identifier,root,updater,payload,calls,present=self.fixture(unknown=True)
        present.clear()
        result=driver.clean_remove(identifier)
        self.assertEqual(result['stage'],'restart-required')
        self.assertEqual(result['state'],'recovery_required')
        self.assertFalse((root/'state/ssap.json').exists())
        self.assertFalse(any(name.startswith('remove-') for name in calls))

    def test_stale_submitted_receipt_does_not_prevent_retry_cleanup(self):
        driver,identifier,root,updater,payload,calls,present=self.fixture()
        from unittest.mock import patch
        with patch.object(driver.device,'retire_clean_private',side_effect=OSError('interrupted')):
            first=driver.clean_remove(identifier)
        self.assertIn('package-removal',first['done'])
        first['packages']['com.cleanyourtv.root.preview']={'state':'submitted'}
        driver.store.write('clean-removal-'+identifier,first)
        result=driver.clean_remove(identifier)
        self.assertEqual(result['state'],'recovery_required')
        self.assertEqual(result['stage'],'restart-required')
        self.assertFalse((root/'state/ssap.json').exists())
        self.assertEqual(calls.count('remove-com.cleanyourtv.root.preview'),1)

    def test_live_owner_inverse_records_preserved_without_product_secrets(self):
        driver,identifier,root,updater,payload,calls,present=self.fixture()
        (root/'system-permissions.json').write_text('{"original":"foreign permission"}')
        (updater/'registration.json').write_text('{"original":"foreign registration"}')
        driver.device.ownership=driver.ownership
        driver.device.preserve_routing_inverse({'operation':identifier})
        saved=driver.ownership.store.read('routing-backup-'+identifier)
        self.assertIn('system-permissions.json',saved)
        self.assertIn('root-updater/registration.json',saved)
        self.assertNotIn('ssap',str(saved))

    def test_helper_missing_from_sam_with_live_process_requires_full_boot(self):
        import install_device
        driver,identifier,root,updater,payload,calls,present=self.fixture()
        process=install_device.PROC/'12345';process.mkdir()
        (process/'cmdline').write_bytes(str(install_device.INSTALLED/'usr/palm/applications/com.local.nativehome/relay').encode()+b'\0')
        result=driver.clean_remove(identifier)
        self.assertEqual(result['stage'],'restart-required')
        self.assertFalse(result['current'])
        self.assertTrue((root/'state/ssap.json').exists())
        self.assertTrue(any(name.startswith('remove-') for name in calls))

    def test_retained_inert_system_temp_does_not_block_clean_readback(self):
        import install_device
        driver,identifier,root,updater,payload,calls,present=self.fixture()
        driver.clean_remove(identifier)
        driver.device.current_boot='22222222-2222-2222-2222-222222222222'
        record=driver.clean_remove(identifier)
        stage=install_device.TEMP/('cytv-system-updater-'+'a'*32);stage.mkdir(mode=0o700)
        (stage/'diagnostic.txt').write_text('preserve unknown temporary data')
        info=stage.stat()
        record['retained_temporary_stages']=[dict(path=str(stage),dev=info.st_dev,ino=info.st_ino)]
        self.assertTrue(driver.device.verify_clean(record))
        self.assertTrue((stage/'diagnostic.txt').exists())
        record['retained_temporary_stages'][0]['ino']+=1
        with self.assertRaisesRegex(ValueError,'support_stage_remains'):driver.device.verify_clean(record)

    def test_clean_readback_exempts_only_executing_checked_coordinator_stage(self):
        import install_device
        driver,identifier,root,updater,payload,calls,present=self.fixture()
        self.assertEqual(driver.clean_remove(identifier)['stage'],'restart-required')
        driver.device.current_boot='22222222-2222-2222-2222-222222222222'
        record=driver.clean_remove(identifier)
        stage=install_device.TEMP/('cytv-coordinator-'+'a'*32);stage.mkdir()
        (stage/'install_device.py').write_bytes(b'current support')
        with patch.object(install_device,'__file__',str(stage/'install_device.py')), patch('coordinator_inventory.BUNDLED_FILES',('install_device.py',)):
            self.assertTrue(driver.device.verify_clean(record))
            other=install_device.TEMP/('cytv-coordinator-'+'b'*32);other.mkdir()
            (other/'install_device.py').write_bytes(b'current support')
            self.assertTrue(driver.device.verify_clean(record))
            (other/'foreign').write_bytes(b'unknown support')
            with self.assertRaisesRegex(ValueError,'support_stage_remains'):driver.device.verify_clean(record)
            (other/'foreign').unlink()
            (other/'install_device.py').write_bytes(b'stale support')
            with self.assertRaisesRegex(ValueError,'support_stage_remains'):driver.device.verify_clean(record)
            (other/'install_device.py').unlink()
            (other/'install_device.py').symlink_to(stage/'install_device.py')
            with self.assertRaisesRegex(ValueError,'support_stage_remains'):driver.device.verify_clean(record)

    def test_readonly_clean_proof_runs_current_shared_cleanup_without_payload(self):
        import install_device,json,hashlib,subprocess
        from cytv.no_root_cleanup import PRIVATE_CLEANUP_PROGRAM
        driver,identifier,root,updater,payload,calls,present=self.fixture()
        driver.clean_remove(identifier)
        driver.device.current_boot='22222222-2222-2222-2222-222222222222'
        driver.clean_remove(identifier)
        base=root.parent
        for name in ('developer','bus-private','varlib','profiles'):(base/name).mkdir()
        source=PRIVATE_CLEANUP_PROGRAM.replace('/media/developer',str(base/'developer')).replace('/var/luna-service2-dev',str(base/'bus-private'))
        source=source.replace('/var/lib',str(base/'varlib')).replace('/var/webos-profile',str(base/'profiles')).replace('/proc/sys/kernel/random/boot_id',str(base/'boot'))
        (base/'boot').write_text('22222222-2222-2222-2222-222222222222')
        if os.getuid()!=0:source=source.replace('if(uid!==0||','if(false||')
        stage=install_device.TEMP/('cytv-coordinator-'+'a'*32);stage.mkdir()
        script=stage/'cleanup_no_root_private.js';script.write_text(source)
        (stage/'bundle.json').write_text(json.dumps({'files':{script.name:hashlib.sha256(script.read_bytes()).hexdigest()}}))
        del driver.device.shared_cleanup
        driver.device.payload=None
        run=subprocess.run
        def actual(args,**kwargs):return run([os.environ.get('NODE8','node'),*args[1:]],**kwargs)
        with patch.object(install_device,'__file__',str(stage/'install_device.py')),patch('coordinator_inventory.BUNDLED_FILES',(script.name,)),patch('install_device.subprocess.run',side_effect=actual):
            self.assertTrue(driver.inspect()['clean_removal_verified'])
            self.assertTrue(driver.restore()['already_removed'])
            script.write_text(source+'\n// changed current support')
            with self.assertRaisesRegex(ValueError,'current_cleanup_support_changed'):driver.inspect()

    def test_clean_process_proof_allows_only_exact_current_readonly_status(self):
        import install_device
        driver,identifier,root,updater,payload,calls,present=self.fixture()
        driver.clean_remove(identifier)
        driver.device.current_boot='22222222-2222-2222-2222-222222222222'
        record=driver.clean_remove(identifier)
        stage=install_device.TEMP/('cytv-coordinator-'+'a'*32);stage.mkdir()
        for name in ('install_device.py','install_driver.py'):(stage/name).write_bytes(b'current support')
        process=install_device.PROC/'12345';process.mkdir()
        args=[sys.executable,'-B',str(stage/'install_driver.py'),'status','--operation','d'*32]
        command=process/'cmdline';command.write_bytes(b'\0'.join(arg.encode() for arg in args)+b'\0')
        with patch.object(install_device,'__file__',str(stage/'install_device.py')),patch('coordinator_inventory.BUNDLED_FILES',('install_device.py','install_driver.py')):
            self.assertTrue(driver.device.verify_clean(record))
            for tail in (['--resume'],['--worker'],['--payload',str(payload)]):
                command.write_bytes(b'\0'.join(arg.encode() for arg in args+tail)+b'\0')
                with self.assertRaisesRegex(ValueError,'live_original_worker'):driver.device.verify_clean(record)
            command.write_bytes(b'\0'.join(arg.encode() for arg in args)+b'\0')
            other=install_device.TEMP/('cytv-coordinator-'+'b'*32);other.mkdir()
            for name in ('install_device.py','install_driver.py'):(other/name).write_bytes(b'stale support')
            command.write_bytes(b'\0'.join(arg.replace(str(stage),str(other)).encode() for arg in args)+b'\0')
            with self.assertRaisesRegex(ValueError,'live_original_worker'):driver.device.clean_quiescent(record,all_processes=True)

    def test_clean_readback_accepts_only_exact_current_product_upload(self):
        import install_device,json,shutil,hashlib
        driver,identifier,root,updater,payload,calls,present=self.fixture()
        driver.clean_remove(identifier)
        driver.device.current_boot='22222222-2222-2222-2222-222222222222'
        record=driver.clean_remove(identifier)
        snapshot=payload.parent/'current-snapshot';snapshot.mkdir()
        for component in ('root','root-updater'):
            folder=snapshot/component;folder.mkdir()
            (folder/'current.py').write_bytes(b'current bytes')
            (folder/'bundle.json').write_text(json.dumps({'files':{'current.py':hashlib.sha256(b'current bytes').hexdigest()}}))
        stage=install_device.TEMP/('cytv-product-'+'a'*32)
        shutil.copytree(snapshot,stage)
        (snapshot/'worker.log').write_bytes(b'private worker log')
        driver.device.payload=snapshot
        self.assertTrue(driver.device.verify_clean(record))
        (stage/'foreign').mkdir()
        with self.assertRaisesRegex(ValueError,'support_stage_remains'):driver.device.verify_clean(record)
        (stage/'foreign').rmdir()
        (stage/'root/current.py').write_bytes(b'changed bytes')
        with self.assertRaisesRegex(ValueError,'support_stage_remains'):driver.device.verify_clean(record)

    def test_interrupted_fence_archive_resumes_only_original_inodes(self):
        import install_device
        driver,identifier,root,updater,payload,calls,present=self.fixture()
        driver.clean_remove(identifier)
        driver.device.current_boot='22222222-2222-2222-2222-222222222222'
        clean=driver.clean_remove(identifier)
        original=driver.ownership.store.read('request-'+identifier)
        rename=os.rename
        def interrupted(source,target,**kwargs):
            if source==updater.name:raise OSError('interrupted archive')
            return rename(source,target,**kwargs)
        with patch.object(install_device.os,'rename',side_effect=interrupted):
            failed=driver._run('d'*32,'install',lambda checkpoint:self.fail('install effects began'))
        self.assertEqual(failed['stage'],'reserved')
        self.assertEqual(failed['state'],'recovery_required')
        self.assertFalse(root.exists());self.assertTrue(updater.exists())
        driver.ownership.store.write('submission-'+'d'*32,dict(operation='d'*32,action='install'))
        driver.device.verify_resume=lambda payload,submission:dict(migrate=False,prepare_supervisor=False)
        def resume(payload,options,stage,checkpoint):
            self.assertFalse(root.exists());self.assertFalse(updater.exists())
            return {'verified':True}
        driver.device.resume_install=resume
        completed=driver.resume('d'*32,payload)
        self.assertEqual(completed['state'],'complete',completed)
        self.assertEqual(driver.ownership.store.read('request-'+identifier),original)
        driver.device.prepare_clean_install(clean)

    def test_interrupted_fence_archive_rejects_replaced_archived_directory(self):
        import install_device
        driver,identifier,root,updater,payload,calls,present=self.fixture()
        driver.clean_remove(identifier)
        driver.device.current_boot='22222222-2222-2222-2222-222222222222'
        clean=driver.clean_remove(identifier)
        rename=os.rename
        def interrupted(source,target,**kwargs):
            if source==updater.name:raise OSError('interrupted archive')
            return rename(source,target,**kwargs)
        with patch.object(install_device.os,'rename',side_effect=interrupted):
            driver._run('d'*32,'install',lambda checkpoint:self.fail('effects'))
        archive=Path(driver.ownership.store.root)/('component-fences-'+identifier)
        (archive/root.name).rename(archive/'replaced')
        (archive/root.name).mkdir()
        with self.assertRaisesRegex(ValueError,'component_fence_conflict'):driver.device.prepare_clean_install(clean)
        self.assertTrue(updater.exists())

    def test_fresh_install_moves_minimal_fences_without_replacing_lock_inodes(self):
        driver,identifier,root,updater,payload,calls,present=self.fixture()
        self.assertEqual(driver.clean_remove(identifier)['stage'],'restart-required')
        driver.device.current_boot='22222222-2222-2222-2222-222222222222'
        first=driver.clean_remove(identifier);self.assertEqual(first['stage'],'verified-clean')
        inodes={path:path.stat().st_ino for path in (root/'provision.lock',updater/'worker.lock')}
        original=driver.owner if hasattr(driver,'owner') else driver.ownership
        before=original.store.read('request-'+identifier)
        second=driver._run('d'*32,'install',lambda checkpoint:{'verified':True})
        self.assertEqual(second['state'],'complete',second)
        self.assertFalse(root.exists());self.assertFalse(updater.exists())
        archived=Path(original.store.root)/('component-fences-'+identifier)
        for path,inode in inodes.items():self.assertEqual((archived/path.parent.name/path.name).stat().st_ino,inode)
        self.assertEqual(original.store.read('request-'+identifier),before)

    def test_catalog_fallback_sweeps_unregistered_residue_without_redundant_removal(self):
        import types,install_device
        driver,identifier,root,updater,payload,calls,present=self.fixture()
        original=driver.device.rpc
        def rpc(method,data):
            if method=='com.webos.applicationManager/dev/listApps':raise RuntimeError('Bus operation rejected')
            if method=='com.webos.applicationManager/listApps':return {'returnValue':True,'apps':[{'id':app} for app in present]}
            return original(method,data)
        driver.device.rpc=rpc
        driver.device.apps=types.MethodType(install_device.LocalDevice.apps,driver.device)
        # SDK can leave an empty package directory after unregistering it.
        # The existing confined sweeper handles it without a new package request.
        leftover=driver.device.package_paths('com.local.nativehome')[1]
        leftover.mkdir(parents=True)
        shared=driver.device.shared_cleanup
        def sweep(action,record,**kwargs):
            if action=='root-package' and kwargs.get('app')=='com.local.nativehome' and leftover.exists():leftover.rmdir()
            return shared(action,record,**kwargs)
        driver.device.shared_cleanup=sweep
        self.assertNotIn('com.local.nativehome',driver.device.apps())
        self.assertEqual(driver.clean_remove(identifier)['stage'],'restart-required')
        driver.device.current_boot='22222222-2222-2222-2222-222222222222'
        self.assertEqual(driver.clean_remove(identifier)['stage'],'verified-clean')
        self.assertNotIn('remove-com.local.nativehome',calls)
        self.assertFalse(leftover.exists())

    def test_catalog_timeout_can_fall_back_but_malformed_catalog_cannot_claim_absence(self):
        import types,install_device
        for failure in (TimeoutError('Bus response timed out'),None):
            driver,identifier,root,updater,payload,calls,present=self.fixture()
            original=driver.device.rpc
            def rpc(method,data):
                if method=='com.webos.applicationManager/dev/listApps':
                    if failure:raise failure
                    return {'returnValue':True,'apps':[{'id':None}]}
                if method=='com.webos.applicationManager/listApps':return {'returnValue':True,'apps':[]}
                return original(method,data)
            driver.device.rpc=rpc
            driver.device.apps=types.MethodType(install_device.LocalDevice.apps,driver.device)
            if failure:self.assertEqual(driver.device.apps(),set())
            else:
                with patch.object(driver.device,'log'):result=driver.clean_remove(identifier)
                self.assertEqual(result['last_failure']['luna'],{'call':'apps-dev','reason':'malformed-reply'})
                self.assertEqual(result['stage'],'original-writers-fenced')
                self.assertFalse(any(name.startswith('remove-') for name in calls))

    def test_malformed_rpc_envelope_cannot_be_hidden_by_valid_fallback(self):
        import types,install_device
        from updater.luna import context
        driver,identifier,root,updater,payload,calls,present=self.fixture()
        original=driver.device.rpc
        def rpc(method,data):
            if method=='com.webos.applicationManager/dev/listApps':
                raise context(RuntimeError('Bus operation rejected'),method,'malformed-reply')
            if method=='com.webos.applicationManager/listApps':return {'returnValue':True,'apps':[]}
            return original(method,data)
        driver.device.rpc=rpc
        driver.device.apps=types.MethodType(install_device.LocalDevice.apps,driver.device)
        with patch.object(driver.device,'log'):result=driver.clean_remove(identifier)
        self.assertEqual(result['stage'],'original-writers-fenced')
        self.assertEqual(result.get('last_failure',{}).get('luna'),{'call':'apps-dev','reason':'malformed-reply'})
        self.assertFalse(any(name.startswith('remove-') for name in calls))

    def test_both_catalog_reads_denied_block_before_package_removal(self):
        import types,install_device
        driver,identifier,root,updater,payload,calls,present=self.fixture()
        def refused(method,data):
            from updater.luna import context
            raise context(RuntimeError('Bus operation rejected'),method,'negative-reply',{'errorCode':-1})
        driver.device.rpc=refused
        driver.device.apps=types.MethodType(install_device.LocalDevice.apps,driver.device)
        with patch.object(driver.device,'log'):result=driver.clean_remove(identifier)
        self.assertEqual(result['stage'],'original-writers-fenced')
        self.assertEqual(result['last_failure']['luna'],{'call':'apps','reason':'negative-reply','error_code':-1})
        self.assertFalse(any(name.startswith('remove-') for name in calls))
        self.assertTrue((root/'state/ssap.json').exists())

    def profileless_fixture(self, reply=None, home='com.webos.app.home'):
        from updater.luna import context
        driver,identifier,root,updater,payload,calls,present=self.fixture()
        # Old incomplete provisioning is not a trusted pre-activation stage.
        Store(root,uid=os.getuid()).write('deploy',{'version':1,'app':'com.cleanyourtv.root.preview','stage':'installed-recovery-only'})
        original=driver.device.rpc
        missing={'returnValue':False,'errorCode':-1,'errorText':'Service does not exist: com.webos.service.systemprofile.'}
        response=missing if reply is None else reply
        def rpc(method,data):
            if method.endswith('/getSystemSettings'):
                return {'returnValue':True,'settings':{'defaultApps':{'home':home}}}
            if method.endswith('/getProfiles'):
                if isinstance(response,Exception):raise response
                raise context(RuntimeError('Bus operation rejected'),method,'negative-reply',response)
            return original(method,data)
        driver.device.rpc=rpc
        return driver,identifier,root,updater,payload,calls,present

    def test_webos5_stock_home_can_remove_from_an_old_fenced_attempt(self):
        driver,identifier,root,updater,payload,calls,present=self.profileless_fixture()
        # Model the published remover's failed attempt, before new support exists.
        from updater.luna import context
        method='com.webos.service.systemprofile/getProfiles'
        old_error=context(RuntimeError('Bus operation rejected'),method,'negative-reply',
            {'returnValue':False,'errorCode':-1,'errorText':'Service does not exist: com.webos.service.systemprofile.'})
        with patch.object(driver.device,'log'),patch('clean_removal.routes',side_effect=old_error):
            first=driver.clean_remove(identifier)
        # The old checkpoint predates the new eligibility observation.
        first.pop('profileless_cleanup_eligible',None)
        driver.ownership.store.write('clean-removal-'+identifier,first)
        self.assertEqual(first['stage'],'original-writers-fenced')
        self.assertFalse(first['routing_never_applied'])
        self.assertEqual(first['last_failure']['luna'],{'call':'home-profiles','reason':'service-missing','error_code':-1})
        self.assertEqual(driver.clean_remove(identifier)['stage'],'restart-required')
        driver.device.current_boot='22222222-2222-2222-2222-222222222222'
        result=driver.clean_remove(identifier)
        self.assertEqual(result['stage'],'verified-clean',result)
        self.assertEqual(result['routes'],{'mode':'stock-settings','home':'com.webos.app.home'})
        self.assertEqual(result['original']['request']['state'],'recovery_required')
        self.assertFalse(present)
        self.assertFalse(any('setSystem' in name or 'setDefault' in name for name in calls))

    def test_webos5_saved_inverse_and_previous_profiles_prevent_backend_downgrade(self):
        for proof in ('backup','profiles','override','refused'):
            with self.subTest(proof=proof):
                driver,identifier,root,updater,payload,calls,present=self.profileless_fixture()
                driver.device.ownership=driver.ownership
                if proof=='backup':
                    # The live journal may already have been consumed by an old
                    # restoration; its original inverse must still block fallback.
                    driver.ownership.store.write('routing-backup-'+identifier,{'profile-trial.json':'{}'})
                if proof=='override':
                    exists=os.path.lexists
                    guard=patch('install_device.os.path.lexists',side_effect=lambda path:
                        str(path)=='/var/webos-profile/override/clean-your-tv-root.json' or exists(path))
                else:
                    from contextlib import nullcontext
                    guard=nullcontext()
                # Seed a fenced checkpoint without performing a TV-side restore.
                with patch.object(driver.device,'clean_remove',side_effect=RuntimeError('old failure')),patch.object(driver.device,'log'):
                    record=driver.clean_remove(identifier)
                if proof=='profiles':record['routes']=['com.webos.app.home']*3
                if proof=='refused':record['profileless_cleanup_eligible']=False
                driver.ownership.store.write('clean-removal-'+identifier,record)
                with guard,patch.object(driver.device,'log'):result=driver.clean_remove(identifier)
                self.assertEqual(result['stage'],'original-writers-fenced')
                self.assertFalse(any(name.startswith('remove-') for name in calls))
                self.assertTrue((root/'state/ssap.json').exists())

    def test_webos5_post_restart_home_drift_preserves_removal_fence(self):
        driver,identifier,root,updater,payload,calls,present=self.profileless_fixture()
        self.assertEqual(driver.clean_remove(identifier)['stage'],'restart-required')
        driver.device.current_boot='22222222-2222-2222-2222-222222222222'
        rpc=driver.device.rpc
        def changed(method,data):
            if method.endswith('/getSystemSettings'):
                return {'returnValue':True,'settings':{'defaultApps':{'home':'third.party.home'}}}
            return rpc(method,data)
        driver.device.rpc=changed
        with patch.object(driver.device,'log'):result=driver.clean_remove(identifier)
        self.assertEqual(result['state'],'recovery_required')
        self.assertNotEqual(result['stage'],'verified-clean')
        self.assertFalse(result.get('current',False))
        self.assertFalse(driver.ownership.status()['terminal'])

    def test_webos5_cleanup_does_not_hide_other_profile_failures(self):
        replies=[TimeoutError('Bus response timed out'),RuntimeError('Bus operation rejected'),
            {'returnValue':False,'errorCode':-1,'errorText':'Permission denied'},
            {'returnValue':False,'errorCode':-1,'errorText':'Service does not exist: another.service.'},
            {'returnValue':False,'errorCode':True,'errorText':'Service does not exist: com.webos.service.systemprofile.'},
            {'returnValue':False,'errorCode':-1,'errorText':'Service does not exist: com.webos.service.systemprofile. extra'}]
        for reply in replies:
            with self.subTest(reply=reply):
                driver,identifier,root,updater,payload,calls,present=self.profileless_fixture(reply)
                with patch.object(driver.device,'log'):result=driver.clean_remove(identifier)
                self.assertEqual(result['stage'],'original-writers-fenced')
                self.assertTrue((root/'state/ssap.json').exists())
                self.assertFalse(any(name.startswith('remove-') for name in calls))

    def test_webos5_profileless_cleanup_requires_stock_home_and_no_routing_evidence(self):
        for marker in ('profile-trial.json','persistent-intent.json','persistent-binding.json',
                       'profile-candidate.stage','home-backend.json','c1-gate','c1-keyfilter'):
            with self.subTest(marker=marker):
                driver,identifier,root,updater,payload,calls,present=self.profileless_fixture()
                (root/marker).write_text('{}')
                with patch.object(driver.device,'log'):result=driver.clean_remove(identifier)
                self.assertEqual(result['stage'],'original-writers-fenced')
                self.assertTrue((root/marker).exists())
                self.assertFalse(any(name.startswith('remove-') for name in calls))
        for home in ('third.party.home','com.gathin.tvhome','',None):
            with self.subTest(home=home):
                driver,identifier,root,updater,payload,calls,present=self.profileless_fixture(home=home)
                with patch.object(driver.device,'log'):result=driver.clean_remove(identifier)
                self.assertEqual(result['stage'],'original-writers-fenced')
                self.assertFalse(any(name.startswith('remove-') for name in calls))

    def test_never_activated_removal_needs_no_home_apis_even_after_old_failed_attempt(self):
        from updater.luna import context
        driver,identifier,root,updater,payload,calls,present=self.fixture()
        error=context(RuntimeError('Bus operation rejected'),
            'com.webos.settingsservice/getSystemSettings','negative-reply',{'returnValue':False})
        with patch.object(driver.device,'log'),patch('clean_removal.routes',side_effect=error):
            first=driver.clean_remove(identifier)
        self.assertEqual(first['stage'],'original-writers-fenced')
        first.pop('profileless_cleanup_eligible',None)
        driver.store.write('clean-removal-'+identifier,first)
        original=driver.device.rpc
        def unavailable(method,data):
            if method.endswith(('/getSystemSettings','/getProfiles')):
                self.fail('Untouched Home must not require a firmware Home API')
            return original(method,data)
        driver.device.rpc=unavailable
        self.assertEqual(driver.clean_remove(identifier)['stage'],'restart-required')
        self.assertEqual(driver.clean_remove(identifier)['stage'],'restart-required')
        driver.device.current_boot='22222222-2222-2222-2222-222222222222'
        final=driver.clean_remove(identifier)
        self.assertEqual(final['stage'],'verified-clean',final)
        self.assertEqual(final['routes'],{'mode':'never-applied'})
        self.assertFalse(present)
        self.assertEqual(final['original']['request']['state'],'recovery_required')

    def test_pre_journal_compositor_failure_can_explicitly_remove_with_fresh_stock_proof(self):
        driver,identifier,root,updater,payload,calls,present=self.fixture()
        (root/'deploy.json').unlink()
        (payload/'root/runtime/c1_keyfilter.py').write_text('current verified support')
        proof={'mode':'stock-compositor','target':{'dev':45851,'ino':5647,'size':50684},'target_sha256':'a'*64}
        original=driver.device.rpc
        def unavailable(method,data):
            if method.endswith(('/getSystemSettings','/getProfiles')):
                raise RuntimeError('Unavailable Home setting')
            return original(method,data)
        driver.device.rpc=unavailable
        with patch.object(driver.device,'compositor_stock',return_value=proof,create=True) as observe:
            self.assertEqual(driver.clean_remove(identifier)['stage'],'restart-required')
            driver.device.current_boot='22222222-2222-2222-2222-222222222222'
            final=driver.clean_remove(identifier)
        self.assertEqual(final['stage'],'verified-clean',final)
        self.assertEqual(final['routes'],proof)
        self.assertFalse(final['routing_never_applied'])
        self.assertGreater(observe.call_count,1)
        self.assertFalse(present)

    def test_compositor_retry_keeps_new_routing_evidence_before_cleanup(self):
        driver,identifier,root,updater,payload,calls,present=self.fixture()
        (root/'deploy.json').unlink()
        (payload/'root/runtime/c1_keyfilter.py').write_text('current verified support')
        proof={'mode':'stock-compositor','target':{'dev':45851,'ino':5647,'size':50684},'target_sha256':'a'*64}
        with patch.object(driver.device,'compositor_stock',return_value=proof,create=True):
            self.assertEqual(driver.clean_remove(identifier)['stage'],'restart-required')
            marker=root/'persistent-intent.json';marker.write_text('{}')
            driver.device.current_boot='22222222-2222-2222-2222-222222222222'
            with patch.object(driver.device,'log'):final=driver.clean_remove(identifier)
        self.assertEqual(final['state'],'recovery_required')
        self.assertEqual(marker.read_text(),'{}')

    def test_never_applied_restart_preserves_new_routing_marker_before_cleanup(self):
        driver,identifier,root,updater,payload,calls,present=self.fixture()
        self.assertEqual(driver.clean_remove(identifier)['stage'],'restart-required')
        marker=root/'persistent-intent.json';marker.write_text('{}')
        driver.device.current_boot='22222222-2222-2222-2222-222222222222'
        original=driver.device.rpc
        def unavailable(method,data):
            if method.endswith(('/getSystemSettings','/getProfiles')):raise RuntimeError('Home API unavailable')
            return original(method,data)
        driver.device.rpc=unavailable
        with patch.object(driver.device,'log'):result=driver.clean_remove(identifier)
        self.assertEqual(result['state'],'recovery_required')
        self.assertNotEqual(result['stage'],'verified-clean')
        self.assertEqual(marker.read_text(),'{}')

    def test_old_pre_activation_readback_upgrades_only_with_fresh_no_effect_proof(self):
        driver,identifier,root,updater,payload,calls,present=self.fixture()
        self.assertEqual(driver.clean_remove(identifier)['stage'],'restart-required')
        record=driver.store.read('clean-removal-'+identifier)
        record['routes']=['third.party.home']*3
        driver.store.write('clean-removal-'+identifier,record)
        driver.device.current_boot='22222222-2222-2222-2222-222222222222'
        final=driver.clean_remove(identifier)
        self.assertEqual(final['stage'],'verified-clean',final)
        self.assertEqual(final['routes'],{'mode':'never-applied'})

    def test_never_applied_proof_rechecks_live_and_preserved_routing_evidence(self):
        import clean_removal
        for source in ('live','backup','phase','eligibility'):
            with self.subTest(source=source):
                driver,identifier,root,updater,payload,calls,present=self.fixture()
                self.assertEqual(driver.clean_remove(identifier)['stage'],'restart-required')
                record=driver.store.read('clean-removal-'+identifier)
                if source=='live':(root/'persistent-intent.json').write_text('{}')
                if source=='backup':driver.store.write('routing-backup-'+identifier,{'profile-trial.json':'{}'})
                if source=='phase':record['fenced_components']['deploy']['stage']='installed-recovery-only'
                if source=='eligibility':record['profileless_cleanup_eligible']=False
                with patch.object(driver.device,'rpc',side_effect=RuntimeError('Home API unavailable')):
                    with self.assertRaises(RuntimeError):clean_removal.routes(driver.device,record)

    def test_never_activated_partial_can_clean_when_profile_interface_unavailable(self):
        driver,identifier,root,updater,payload,calls,present=self.fixture(missing_profiles=True)
        self.assertEqual(driver.clean_remove(identifier)['stage'],'restart-required')
        driver.device.current_boot='22222222-2222-2222-2222-222222222222'
        result=driver.clean_remove(identifier)
        self.assertEqual(result['stage'],'verified-clean',result)
        self.assertEqual(result['routes'],{'mode':'never-applied'})
        self.assertTrue(result['routing_never_applied'])
        self.assertFalse(any('setSystem' in name or 'setProfiles' in name for name in calls))

    def test_possible_old_activation_cannot_claim_missing_profile_interface_is_clean(self):
        driver,identifier,root,updater,payload,calls,present=self.fixture(missing_profiles=True)
        Store(root,uid=os.getuid()).write('deploy',{'version':1,'app':'com.cleanyourtv.root.preview','stage':'installed-recovery-only'})
        result=driver.clean_remove(identifier)
        self.assertEqual(result['stage'],'original-writers-fenced')
        self.assertFalse(result['routing_never_applied'])
        self.assertTrue((root/'state/ssap.json').exists())
        self.assertFalse(any(name.startswith('remove-') for name in calls))


class ActivityInventoryCompatibility(unittest.TestCase):
    def test_missing_or_timed_out_list_uses_checked_get_activity_info(self):
        import clean_removal
        from unittest.mock import Mock
        for reason in ('timeout','service-missing','method-missing','negative-reply'):
            with self.subTest(reason=reason):
                error=TimeoutError('private') if reason=='timeout' else RuntimeError('private')
                error.luna={'call':'activities-list','reason':reason}
                rows=[{'name':'foreign','callback':{'method':'luna://foreign/keep'}}]
                device=Mock();device.rpc.side_effect=[error,{'returnValue':True,'activities':rows}]
                self.assertEqual(clean_removal.activities(device),rows)
                self.assertEqual([c.args[0] for c in device.rpc.call_args_list],
                    ['com.palm.activitymanager/list','com.palm.activitymanager/getActivityInfo'])

    def test_malformed_or_unsafe_inventory_does_not_get_another_chance(self):
        import clean_removal
        from unittest.mock import Mock
        for reply in ({'returnValue':True}, {'returnValue':True,'activities':{}},
                      {'returnValue':True,'activities':[None]},
                      {'returnValue':True,'activities':[{'callback':None}]},
                      {'returnValue':False,'activities':[]}):
            device=Mock();device.rpc.return_value=reply
            with self.subTest(reply=reply),self.assertRaises(ValueError):clean_removal.activities(device)
            self.assertEqual(device.rpc.call_count,1)
        for reason in ('permission-denied','oversized-reply','malformed-reply','client-start-failed'):
            device=Mock();error=RuntimeError('private');error.luna={'reason':reason}
            device.rpc.side_effect=error
            with self.subTest(reason=reason),self.assertRaises(RuntimeError):clean_removal.activities(device)
            self.assertEqual(device.rpc.call_count,1)


if __name__ == '__main__': unittest.main()
