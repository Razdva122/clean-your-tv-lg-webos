"""Readiness-only recovery uses real journals and genuine manager health receipts."""
import copy
from contextlib import contextmanager
import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import types
from unittest.mock import patch

if os.name != 'posix':
    raise unittest.SkipTest('TV rollback recovery requires POSIX locks and filesystem semantics')

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/system_updates'))
fixture_spec=importlib.util.spec_from_file_location('_rollback_recovery_core_fixture',ROOT/'tests/system_updates/test_core.py')
core_fixture=importlib.util.module_from_spec(fixture_spec);fixture_spec.loader.exec_module(core_fixture)
RootIO,profile,Store=core_fixture.RootIO,core_fixture.profile,core_fixture.Store
from system_updater.core import Manager
import hashlib,tarfile
fixture=ROOT/'tests/system_updates/fixtures/public-1.3.0-supervisor.tar.gz'
provenance=json.loads(fixture.with_suffix('.provenance.json').read_text())
assert hashlib.sha256(fixture.read_bytes()).hexdigest()==provenance['sha256']
with tarfile.open(fixture) as archive:
    original_core=archive.extractfile('supervisor/system_updater/core.py').read()
    original_device=archive.extractfile('supervisor/system_updater/device.py').read()
    original_identity=archive.extractfile('supervisor/package_identity.py').read()
assert hashlib.sha256(original_core).hexdigest()==provenance['files']['supervisor/system_updater/core.py']
original_namespace={'__name__':'system_updater.original_recovery_core','__package__':'system_updater'}
exec(compile(original_core,'<verified original supervisor core>','exec'),original_namespace)
Manager=original_namespace['Manager']
assert hashlib.sha256(original_identity).hexdigest()==provenance['files']['supervisor/package_identity.py']
OriginalIdentity=types.ModuleType('package_identity')
exec(compile(original_identity,'<verified original supervisor package identity>','exec'),OriginalIdentity.__dict__)
assert hashlib.sha256(original_device).hexdigest()==provenance['files']['supervisor/system_updater/device.py']
original_namespace={'__name__':'system_updater.original_recovery_device','__package__':'system_updater','__file__':str(ROOT/'system-updater/device.py')}
with patch.dict(sys.modules,{'package_identity':OriginalIdentity}):
    exec(compile(original_device,'<verified original supervisor device>','exec'),original_namespace)
OriginalDevice=original_namespace['Device']
from installation import Ownership, Busy

class RecoveryIO(RootIO):
    legacy_states=[]
    root_updater=Path('/unused-root-updater')
    def _root_integrity(self):pass
    def integrity(self,**kw):return {'schema':1,'code':{'original':'a'*64}}
    def require_components(self):pass
    def _verify_release(self,value,edition):return value
    def install(self,c,submitted,terminal,intent):
        self.calls.append('install:'+c['name']);intent();submitted({'application':c.get('application'),'component':c['name'],'sha256':c['sha256']})
        for old in self.current['components']:
            if old['name']==c['name']:old['version']=c['version']
        terminal({'success':True,'sha256':c['sha256'],'event':{'id':c.get('application'),'statusValue':30,'details':{'packageId':c.get('application'),'client':'com.webos.lunasend-99','ipkFile':'/var/lib/clean-your-tv-installer/cytv-root-install-test/package.ipk'}}})
    def close_launcher(self):self.calls.append('close')

class Tests(unittest.TestCase):
    def setUp(self):
        # Freeze the original supervisor's selector for this test only. Current
        # Root lifecycle changes must neither fail provenance nor replace the
        # historical selector via imports inside OriginalDevice/recovery.
        self.enterContext(patch.dict(sys.modules,{'package_identity':OriginalIdentity}))
        try:self.module=importlib.import_module('cytv.system_rollback_recovery')
        except ModuleNotFoundError:self.fail('explicit rollback-readiness recovery is missing')
        import types
        namespace={};exec(self.module.SCRIPT,namespace);self.module=types.SimpleNamespace(**namespace)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=Store(os.path.realpath(self.tmp.name)+'/system',uid=os.getuid())
        self.ownership=Ownership(Store(os.path.realpath(self.tmp.name)+'/installation',uid=os.getuid()))
        self.io=RecoveryIO();self.manager=Manager(self.store,self.io)
        self.manager.install('root','v1.1.0',profile());self.advance('verifying');self.manager.healthy('root',self.manager.status()['id'],'1.1.0');self.advance('complete');self.manager.rollback();self.advance('verifying-rollback');self.io.time+=121;self.advance('recovery-required')
        tx=self.store.read('transaction');self.ownership.store.write('operation',{'schema':1,'id':'e'*32,'owner':'system-update','journal':'transaction.json','stage':'recovery-required','terminal':False})
        self.original=copy.deepcopy(tx);self.locked=False;self.health=True;self.interrupt=False
    def advance(self,phase):
        for _ in range(30):
            tx=self.manager.run()
            if tx['phase']==phase:return tx
        self.fail(tx)
    @contextmanager
    def mutation(self):
        current=self.ownership.status()
        with self.ownership.operation('system-update','transaction.json',resume=current['id']) as record:
            self.locked=True
            try:yield record
            finally:self.locked=False
    def launch(self):
        self.assertFalse(self.locked,'old Root one-shot health must run outside global ownership lock')
        self.io.calls.append('close-relaunch')
        if self.interrupt:raise KeyboardInterrupt('lost SSH')
        if self.health:self.manager.healthy('root',self.original['id'],'1.0.0')
    def sleep(self,seconds):self.io.time+=seconds
    def recover(self,new_attempt=False):
        return self.module.recover(self.manager,self.io,self.store,self.ownership,self.mutation,self.launch,self.sleep,new_attempt=new_attempt)
    def test_real_health_completes_original_manager_without_installing(self):
        calls=len([c for c in self.io.calls if c.startswith('install:')]);result=self.recover()
        self.assertEqual(result['phase'],'rolled-back');self.assertEqual(result['homeResumePhase'],'rolled-back')
        self.assertEqual(self.store.read('current-root'),self.original['prior']);self.assertTrue(self.ownership.status()['terminal'])
        self.assertEqual(len([c for c in self.io.calls if c.startswith('install:')]),calls)
        self.assertEqual(self.store.read('transaction')['components'],self.original['components'])
        audit=self.store.read('readiness-recovery-'+self.original['id']);self.assertEqual(audit['state'],'complete');self.assertEqual(audit['original'],self.original)
    def test_unknown_installer_and_wrong_terminal_binding_refused(self):
        for change in ('unknown','wrong-app'):
            tx=copy.deepcopy(self.original)
            if change=='unknown':tx['components'][0]['rollbackEvidence']['terminal']=None
            else:tx['components'][0]['rollbackEvidence']['terminal']['event']['id']='foreign'
            self.store.write('transaction',tx)
            with self.assertRaises(ValueError):self.recover()
            self.assertEqual(self.store.read('transaction'),tx)
    def test_wrong_cause_and_profile_damage_refused(self):
        tx=copy.deepcopy(self.original);tx['error']='Rollback failed; no retry permitted';self.store.write('transaction',tx)
        with self.assertRaises(ValueError):self.recover()
        tx=self.original;self.store.write('transaction',tx);(Path(self.store.root)/(tx['profile']+'.json')).write_text('{"invalid":true}')
        with self.assertRaises(ValueError):self.recover()
    def test_foreign_lease_and_changed_installed_bytes_refused(self):
        record=self.ownership.status();record['owner']='deploy';self.ownership.store.write('operation',record)
        with self.assertRaises((ValueError,Busy)):self.recover()
        record['owner']='system-update';self.ownership.store.write('operation',record)
        self.io.verify_installed=lambda c:False
        with self.assertRaises(ValueError):self.recover()
    def test_no_health_retains_timeout_and_never_publishes_prior(self):
        before=self.store.read('current-root');self.health=False;result=self.recover()
        self.assertEqual(result['phase'],'recovery-required');self.assertEqual(self.store.read('current-root'),before)
        self.assertFalse(self.ownership.status()['terminal'])
        with self.assertRaises(ValueError):self.recover()
    def test_interruption_reuses_original_attempt_deadline(self):
        self.interrupt=True
        with self.assertRaises(KeyboardInterrupt):self.recover()
        original_deadline=self.store.read('transaction')['deadline'];audit=self.store.read('readiness-recovery-'+self.original['id'])
        self.interrupt=False;result=self.recover();self.assertEqual(result['phase'],'rolled-back')
        self.assertEqual(result['deadline'],original_deadline);self.assertEqual(self.store.read('readiness-recovery-'+self.original['id'])['id'],audit['id'])
    def test_concurrent_worker_is_refused_without_writes(self):
        import fcntl
        lock=Path(self.store.root)/'daemon.lock'
        with lock.open('a') as stream:
            fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises((ValueError,BlockingIOError)):self.recover()
        self.assertEqual(self.store.read('transaction'),self.original)

    def test_stale_health_refused_before_any_rearm_or_audit(self):
        self.store.write('healthy-rollback-'+self.original['id'],{'transaction':self.original['id'],'version':'1.0.0','at':self.original['launched']})
        with self.assertRaises(ValueError):self.recover()
        self.assertEqual(self.store.read('transaction'),self.original)
        self.assertIsNone(self.store.read('readiness-recovery-'+self.original['id']))
    def test_completed_repeat_is_read_only_and_never_relaunches(self):
        self.recover();before=self.store.read('transaction');lease=self.ownership.status();calls=list(self.io.calls)
        result=self.recover();self.assertEqual(result,before);self.assertEqual(self.ownership.status(),lease);self.assertEqual(self.io.calls.count('close-relaunch'),calls.count('close-relaunch'));self.assertEqual(self.io.calls.count('finish'),calls.count('finish'))
    def test_corrupt_armed_deadline_cannot_extend_attempt(self):
        self.interrupt=True
        with self.assertRaises(KeyboardInterrupt):self.recover()
        name='readiness-recovery-'+self.original['id'];audit=self.store.read(name);audit['armed']['deadline']+=100;self.store.write(name,audit)
        self.interrupt=False
        with self.assertRaises(ValueError):self.recover()
    def test_expired_interrupted_attempt_does_not_relaunch(self):
        self.interrupt=True
        with self.assertRaises(KeyboardInterrupt):self.recover()
        self.io.time+=121;calls=list(self.io.calls);self.interrupt=False
        result=self.recover();self.assertEqual(result['phase'],'recovery-required');self.assertEqual(self.io.calls.count('close-relaunch'),calls.count('close-relaunch'))
    def test_clock_reversal_cannot_extend_health_wait(self):
        self.health=False
        def backwards(seconds):self.io.time-=1
        self.sleep=backwards
        import signal
        old=signal.signal(signal.SIGALRM,lambda *args:(_ for _ in ()).throw(AssertionError('clock reversal left recovery unbounded')))
        signal.alarm(2)
        try:result=self.recover();self.assertEqual(result['phase'],'recovery-required')
        finally:signal.alarm(0);signal.signal(signal.SIGALRM,old)
    def test_source_loader_ignores_ambient_module_and_bytecode(self):
        self.assertTrue(hasattr(self.module,'load_sources'),'verified source-only loader missing')
        import hashlib,py_compile
        code=Path(os.path.realpath(self.tmp.name))/'code';code.mkdir();source=code/'recovery_fixture.py';source.write_text('value="poison"')
        py_compile.compile(str(source),cfile=str(code/'recovery_fixture.pyc'))
        source.write_text('value="verified"');source.chmod(0o600)
        finder=self.module.load_sources(code,{'recovery_fixture.py':hashlib.sha256(source.read_bytes()).hexdigest()})
        self.addCleanup(lambda:sys.meta_path.remove(finder));self.addCleanup(lambda:sys.modules.pop('recovery_fixture',None))
        self.assertEqual(importlib.import_module('recovery_fixture').value,'verified')

    def test_prepared_audit_interruption_resumes_exact_first_window(self):
        write=self.store.write
        def interrupted(name,value):
            write(name,value)
            if name.startswith('readiness-recovery-') and value.get('state')=='prepared':raise KeyboardInterrupt('audit durable before rearm')
        self.store.write=interrupted
        with self.assertRaises(KeyboardInterrupt):self.recover()
        audit=self.store.read('readiness-recovery-'+self.original['id']);self.assertEqual(self.store.read('transaction'),self.original)
        self.store.write=write;result=self.recover();self.assertEqual(result['deadline'],audit['armed']['deadline'])
    def test_completion_before_audit_finalization_resumes_without_relaunch(self):
        write=self.store.write
        def interrupted(name,value):
            if name.startswith('readiness-recovery-') and value.get('state')=='complete':raise KeyboardInterrupt('completion durable, audit pending')
            write(name,value)
        self.store.write=interrupted
        with self.assertRaises(KeyboardInterrupt):self.recover()
        self.assertEqual(self.store.read('transaction')['phase'],'rolled-back');calls=self.io.calls.count('close-relaunch')
        self.store.write=write;result=self.recover();self.assertEqual(result['phase'],'rolled-back');self.assertEqual(self.io.calls.count('close-relaunch'),calls)
    def test_healthy_ownership_exit_contention_is_retried(self):
        mutation=self.mutation;entries=[]
        @contextmanager
        def contended():
            entries.append(1)
            if len(entries)==2:raise Busy()
            with mutation() as record:yield record
        self.mutation=contended;self.assertEqual(self.recover()['phase'],'rolled-back');self.assertEqual(len(entries),3)
    def test_terminal_foreign_lease_is_not_reserved_or_changed(self):
        record=self.ownership.status();record.update(owner='deploy',terminal=True);self.ownership.store.write('operation',record)
        with self.assertRaises(ValueError):self.recover()
        self.assertEqual(self.ownership.status(),record);self.assertEqual(self.store.read('transaction'),self.original)
    def test_loaded_ambient_supervisor_module_is_refused(self):
        import types,hashlib
        code=Path(os.path.realpath(self.tmp.name))/'code';code.mkdir();source=code/'recovery_fixture.py';source.write_text('value="verified"');source.chmod(0o600)
        sys.modules['recovery_fixture']=types.ModuleType('recovery_fixture');self.addCleanup(lambda:sys.modules.pop('recovery_fixture',None))
        with self.assertRaises(ValueError):self.module.load_sources(code,{'recovery_fixture.py':hashlib.sha256(source.read_bytes()).hexdigest()})

    def test_received_health_before_interruption_resumes_without_relaunch(self):
        launch=self.launch
        def interrupted():launch();raise KeyboardInterrupt('health received before SSH loss')
        self.launch=interrupted
        with self.assertRaises(KeyboardInterrupt):self.recover()
        calls=self.io.calls.count('close-relaunch');self.launch=launch
        self.assertEqual(self.recover()['phase'],'rolled-back');self.assertEqual(self.io.calls.count('close-relaunch'),calls)

    def test_original_owner_observation_defers_only_authenticated_transition(self):
        Device=OriginalDevice
        from package_identity import TransitionUnknown
        import types
        observed=[]
        def observe(owner):
            observed.append(owner)
            if owner!='com.cleanyourtv.system.updater' and self.store.read('transaction')['phase']=='recovery-required':raise TransitionUnknown('Private transaction requires recovery')
            return {'id':owner}
        self.io.owner_identity=observe;self.io.store=self.store
        self.io.components_present=types.MethodType(Device.components_present,self.io)
        self.io.require_components=types.MethodType(Device.require_components,self.io)
        self.assertEqual(self.recover()['phase'],'rolled-back')
        self.assertTrue({'com.cleanyourtv.system.updater','com.cleanyourtv.root.preview','com.cleanyourtv.root.updater'}<=set(observed))
    def test_original_owner_missing_or_corrupt_proof_dominates_transition(self):
        Device=OriginalDevice
        from package_identity import TransitionUnknown
        import types
        self.io.store=self.store
        self.io.components_present=types.MethodType(Device.components_present,self.io)
        self.io.require_components=types.MethodType(Device.require_components,self.io)
        for failure in [FileNotFoundError('removed supervisor'),ValueError('corrupt original receipt')]:
            def observe(owner):
                if owner=='com.cleanyourtv.system.updater':raise failure
                raise TransitionUnknown('Private transaction requires recovery')
            self.io.owner_identity=observe
            with self.assertRaises(ValueError):self.recover()
            self.assertEqual(self.store.read('transaction'),self.original)
    def test_preflight_never_calls_mutating_legacy_lockdown(self):
        self.io.check_legacy=lambda:self.fail('legacy lockdown is a write before verified rearm')
        self.assertEqual(self.recover()['phase'],'rolled-back')
    def test_root_recovery_proof_damage_rejected_before_audit(self):
        def damaged():raise ValueError('Root recovery receipt mismatch')
        self.io._root_integrity=damaged
        with self.assertRaises(ValueError):self.recover()
        self.assertEqual(self.store.read('transaction'),self.original);self.assertIsNone(self.store.read('readiness-recovery-'+self.original['id']))

    def test_restart_uses_tv_close_by_app_id_then_original_launch_outside_ownership(self):
        self.assertTrue(hasattr(self.module,'restart_launcher'),'TV restart boundary missing')
        calls=[]
        def rpc(uri,payload):
            self.assertFalse(self.locked);calls.append((uri,payload))
            self.assertEqual(uri,'luna://com.webos.applicationManager/closeByAppId')
            self.assertEqual(payload,{'id':'com.cleanyourtv.root.preview'})
            return {'returnValue':True}
        def launch(edition):
            self.assertFalse(self.locked);calls.append(('launch',edition))
            self.manager.healthy('root',self.original['id'],'1.0.0')
            return {'returnValue':True}
        self.io.rpc=rpc;self.io.launch=launch;self.launch=lambda:self.module.restart_launcher(self.io)
        self.assertEqual(self.recover()['phase'],'rolled-back')
        self.assertEqual(calls,[('luna://com.webos.applicationManager/closeByAppId',{'id':'com.cleanyourtv.root.preview'}),('launch','root')])
    def test_restart_close_failure_never_launches_or_fabricates_health(self):
        self.assertTrue(hasattr(self.module,'restart_launcher'),'TV restart boundary missing')
        calls=[];self.io.rpc=lambda *args: {'returnValue':False,'errorText':'close failed'}
        self.io.launch=lambda edition:calls.append(edition)
        with self.assertRaises(ValueError):self.module.restart_launcher(self.io)
        self.assertEqual(calls,[]);self.assertIsNone(self.store.read('healthy-rollback-'+self.original['id']))
    def test_restart_launch_failure_is_not_success(self):
        self.assertTrue(hasattr(self.module,'restart_launcher'),'TV restart boundary missing')
        self.io.rpc=lambda *args: {'returnValue':True}
        self.io.launch=lambda edition: {'returnValue':False,'errorText':'launch failed'}
        with self.assertRaises(ValueError):self.module.restart_launcher(self.io)
        self.assertIsNone(self.store.read('healthy-rollback-'+self.original['id']))
    def test_launcher_error_retains_audited_failure_without_new_deadline(self):
        def failed():raise ValueError('Root launcher close unconfirmed')
        self.launch=failed
        with self.assertRaises(ValueError):self.recover()
        audit=self.store.read('readiness-recovery-'+self.original['id']);tx=self.store.read('transaction')
        self.assertEqual(audit['state'],'failed');self.assertEqual(audit['failure'],'launcher-error')
        self.assertEqual(tx['phase'],'verifying-rollback');self.assertEqual(tx['deadline'],audit['armed']['deadline'])
        self.assertFalse(self.ownership.status()['terminal']);self.assertIsNone(self.store.read('healthy-rollback-'+self.original['id']))

    def expire_attempt(self):
        self.interrupt=True
        with self.assertRaises(KeyboardInterrupt):self.recover()
        self.interrupt=False;self.io.time+=121
        return self.store.read('readiness-recovery-'+self.original['id'])
    def test_explicit_new_attempt_archives_expired_audit_and_uses_real_health(self):
        old=self.expire_attempt();result=self.recover(new_attempt=True)
        new=self.store.read('readiness-recovery-'+self.original['id'])
        self.assertEqual(result['phase'],'rolled-back');self.assertNotEqual(new['id'],old['id'])
        history=self.store.read('readiness-recovery-history-'+old['id'])
        self.assertEqual(history['audit'],old);self.assertEqual(history['sha256'],self.module.digest(self.module.encode(old)))
        self.assertEqual(new['previous']['name'],'readiness-recovery-history-'+old['id']);self.assertEqual(new['previous']['sha256'],history['sha256'])
        self.assertEqual(result['deadline'],new['armed']['launched']+120)
    def test_new_flag_does_not_replace_unexpired_or_completed_attempt(self):
        self.interrupt=True
        with self.assertRaises(KeyboardInterrupt):self.recover()
        old=self.store.read('readiness-recovery-'+self.original['id']);self.interrupt=False
        result=self.recover(new_attempt=True);self.assertEqual(result['deadline'],old['armed']['deadline'])
        complete=self.store.read('readiness-recovery-'+self.original['id']);self.recover(new_attempt=True)
        self.assertEqual(self.store.read('readiness-recovery-'+self.original['id']),complete)
        self.assertEqual(list(Path(self.store.root).glob('readiness-recovery-history-*')),[])
    def test_failed_launcher_requires_expiry_even_with_new_flag(self):
        launch=self.launch;self.launch=lambda:(_ for _ in ()).throw(ValueError('close rejected'))
        with self.assertRaises(ValueError):self.recover()
        old=self.store.read('readiness-recovery-'+self.original['id']);self.launch=launch
        with self.assertRaises(ValueError):self.recover(new_attempt=True)
        self.assertEqual(self.store.read('transaction')['deadline'],old['armed']['deadline'])
        self.io.time+=121;self.assertEqual(self.recover(new_attempt=True)['phase'],'rolled-back')
    def test_new_attempt_refuses_existing_health_or_archive_conflict(self):
        old=self.expire_attempt();self.store.write('healthy-rollback-'+self.original['id'],{'transaction':self.original['id'],'version':'1.0.0','at':old['armed']['launched']})
        with self.assertRaises(ValueError):self.recover(new_attempt=True)
        self.assertEqual(self.store.read('readiness-recovery-'+self.original['id']),old)
        (Path(self.store.root)/('healthy-rollback-'+self.original['id']+'.json')).unlink()
        name='readiness-recovery-history-'+old['id'];self.store.write(name,{'foreign':'evidence'})
        with self.assertRaises(ValueError):self.recover(new_attempt=True)
        self.assertEqual(self.store.read(name),{'foreign':'evidence'})
        self.assertEqual(self.store.read('readiness-recovery-'+self.original['id']),old)
    def test_archive_before_pointer_interruption_retains_identical_history(self):
        old=self.expire_attempt();name='readiness-recovery-'+self.original['id'];write=self.store.write
        def interrupt(key,value):
            if key==name and value['id']!=old['id']:raise KeyboardInterrupt('history durable, pointer unchanged')
            write(key,value)
        self.store.write=interrupt
        with self.assertRaises(KeyboardInterrupt):self.recover(new_attempt=True)
        self.assertEqual(self.store.read(name),old);history=self.store.read('readiness-recovery-history-'+old['id'])
        self.store.write=write;self.assertEqual(self.recover(new_attempt=True)['phase'],'rolled-back')
        self.assertEqual(self.store.read('readiness-recovery-history-'+old['id']),history)
    def test_new_prepared_interruption_resumes_same_persisted_window(self):
        old=self.expire_attempt();name='readiness-recovery-'+self.original['id'];write=self.store.write
        def interrupt(key,value):
            write(key,value)
            if key==name and value['id']!=old['id'] and value['state']=='prepared':raise KeyboardInterrupt('new pointer durable, old journal')
        self.store.write=interrupt
        with self.assertRaises(KeyboardInterrupt):self.recover(new_attempt=True)
        prepared=self.store.read(name);self.store.write=write
        result=self.recover(new_attempt=True);self.assertEqual(result['deadline'],prepared['armed']['deadline'])
        self.assertEqual(self.store.read(name)['id'],prepared['id'])
    def test_expired_new_prepared_attempt_can_be_explicitly_archived(self):
        old=self.expire_attempt();name='readiness-recovery-'+self.original['id'];write=self.store.write
        def interrupt(key,value):
            write(key,value)
            if key==name and value['id']!=old['id'] and value['state']=='prepared':raise KeyboardInterrupt('prepared only')
        self.store.write=interrupt
        with self.assertRaises(KeyboardInterrupt):self.recover(new_attempt=True)
        prepared=self.store.read(name);self.store.write=write;self.io.time+=121
        self.assertEqual(self.recover(new_attempt=True)['phase'],'rolled-back')
        self.assertEqual(self.store.read('readiness-recovery-history-'+prepared['id'])['audit'],prepared)
    def test_new_attempt_api_requires_literal_boolean(self):
        from cytv.system_rollback_recovery import program
        for value in ['true',1,None]:
            with self.assertRaises(ValueError):program(new_attempt=value)
        self.assertIn('entry(new_attempt=True)',program(new_attempt=True))

    def test_advancing_clock_keeps_persisted_armed_record_exact(self):
        def ticking():self.io.time+=.001;return self.io.time
        self.io.now=ticking
        self.assertEqual(self.recover()['phase'],'rolled-back')
        audit=self.store.read('readiness-recovery-'+self.original['id'])
        self.assertEqual(audit['armed']['updated'],audit['armed']['launched'])
        self.assertEqual(self.recover()['phase'],'rolled-back')
    def test_existing_real_clock_updated_delta_is_preserved_in_archive(self):
        old=self.expire_attempt();old['armed']['updated']+=.01
        name='readiness-recovery-'+self.original['id'];self.store.write(name,old)
        tx=self.store.read('transaction');tx['updated']=old['armed']['updated'];self.store.write('transaction',tx)
        self.assertEqual(self.recover(new_attempt=True)['phase'],'rolled-back')
        self.assertEqual(self.store.read('readiness-recovery-history-'+old['id'])['audit'],old)
    def test_clock_reversal_between_observations_cannot_persist_invalid_armed_time(self):
        deadline=self.original['deadline'];values=iter([deadline+1,deadline-1])
        self.io.now=lambda:next(values,deadline+1)
        try:self.recover()
        except ValueError:pass
        audit=self.store.read('readiness-recovery-'+self.original['id'])
        self.assertGreaterEqual(audit['armed']['launched'],deadline)
    def test_restart_reports_which_bus_stage_was_rejected(self):
        def rejected(*args):raise ValueError('Bus operation rejected')
        self.io.rpc=rejected
        with self.assertRaisesRegex(ValueError,'Root closeByAppId rejected'):self.module.restart_launcher(self.io)
        self.io.rpc=lambda *args:{'returnValue':True};self.io.launch=rejected
        with self.assertRaisesRegex(ValueError,'Root launcher relaunch rejected'):self.module.restart_launcher(self.io)

if __name__=='__main__':unittest.main()
