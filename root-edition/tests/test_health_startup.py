"""Exercise cold health initialization and the real activation/readiness contract."""
import contextlib
import io
import os
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
import device_adapter as d
import emergency_trial as emergency
import guardian_device as guardian
import persistent_health as health
import test_persistent_recovery as fixture


class Observer:
    pid=123
    def __init__(self,fd,payload):
        self.fd=os.dup(fd);self.stopped=False
        os.write(self.fd,payload)
    def poll(self):return 0 if self.stopped else None
    def kill(self):
        self.stopped=True;os.close(self.fd)
    def wait(self):return 0


@unittest.skipUnless(os.name=='posix','TV process/pipe contract requires POSIX')
class StartupHealthTests(unittest.TestCase):
    def setUp(self):
        self.case=fixture.IntegrationTests('test_exit_disables_intent_before_real_routing_restore')
        self.case.setUp();self.addCleanup(self.case.tearDown)
        journal=d.safe_json(self.case.root/'profile-trial.json');journal['deadline']=time.monotonic()+60;d.save(journal)
        self.stack=contextlib.ExitStack();self.addCleanup(self.stack.close)
        for value in (patch('intent_runtime.boot_identity',return_value='boot-a'),
                      patch.object(d,'FAILSAFE',self.case.root/'failsafe'),
                      patch.object(health,'ROOT',self.case.root/'health')):
            self.stack.enter_context(value)

    def supervisor(self,tx,stop,ready,errors,payload=b'READY\nPING\n'):
        def run():
            try:emergency.supervise(tx)
            except Exception as error:errors.append(error)
        self.stack.enter_context(patch.object(emergency.subprocess,'Popen',side_effect=lambda args,**kw:Observer(kw['pass_fds'][0],payload)))
        self.stack.enter_context(patch.object(emergency,'save_ready',side_effect=lambda *args:ready.set()))
        self.stack.enter_context(patch.object(emergency,'completed',side_effect=lambda _:stop.is_set()))
        self.stack.enter_context(patch.object(emergency,'recover',return_value=True))
        self.stack.enter_context(patch.object(health,'require_guardian'))
        return threading.Thread(target=run,name='cold-supervisor')

    def cold_activation(self,restart=False):
        if restart:
            expected=self.case.c.boot(self.case.intent,'boot-b','new-attempt',False)['intent']
        else:
            self.case.c.exit(self.case.intent);expected=self.case.store.read()
        stop=threading.Event();ready=threading.Event();errors=[];threads=[]
        original=d.require_home;first=[True]
        def presence(**kw):
            if threading.current_thread().name=='cold-supervisor' and first[0]:
                first[0]=False;time.sleep(3)
            return original(**kw)
        def start(before_publish):
            self.case.create_route('route-b')
            journal=d.safe_json(self.case.root/'profile-trial.json');journal['deadline']=time.monotonic()+60;d.save(journal)
            before_publish('route-b')
            thread=self.supervisor('route-b',stop,ready,errors);threads.append(thread);thread.start()
            if not ready.wait(8):raise RuntimeError('No validated startup readiness')
            return {'transaction':'route-b'}
        failure=None;result=None
        with patch.object(emergency,'start',side_effect=start),patch.object(d,'require_home',side_effect=presence), \
             patch('provision.verify',return_value={'integrity_verified':True}),patch('helper_bridge.require_idle'), \
             patch('intent_runtime.boot_identity',return_value='boot-b' if restart else 'boot-a'), \
             patch.object(d,'active_guardian',return_value=True),patch.object(d,'native_input_enable',return_value='unavailable'), \
             contextlib.redirect_stderr(io.StringIO()):
            try:result=self.case.c.restart(expected) if restart else self.case.c.enable(expected,'boot-a','new-attempt')
            except Exception as error:failure=error
            finally:
                stop.set()
                for thread in threads:thread.join(10)
        self.assertIsNone(failure,'Parent revoked activation before first cold heartbeat: '+repr(failure))
        self.assertEqual(errors,[])
        self.assertEqual(result['intent']['phase'],'active')
        self.assertTrue(self.case.store.read()['enabled'])
        self.assertGreaterEqual(health.load('route-b')['sequence'],1)

    def test_cold_first_validation_does_not_revoke_activation(self):
        self.cold_activation()

    def test_cold_first_validation_does_not_revoke_boot_restart(self):
        self.cold_activation(restart=True)

    def test_bound_ready_follows_validated_heartbeat(self):
        stop=threading.Event();ready=threading.Event();entered=threading.Event();release=threading.Event();errors=[]
        original=health.publish
        def publish(*args):
            entered.set()
            if not release.wait(3):raise RuntimeError('test heartbeat held')
            return original(*args)
        thread=self.supervisor('route-a',stop,ready,errors)
        with patch.object(health,'publish',side_effect=publish):
            thread.start()
            try:
                self.assertTrue(entered.wait(3))
                self.assertFalse(ready.is_set(),'READY must not precede the first validated heartbeat')
                release.set();self.assertTrue(ready.wait(3))
                self.assertGreaterEqual(health.load('route-a')['sequence'],1)
            finally:release.set();stop.set();thread.join(5)
        self.assertEqual(errors,[])

    def test_guardian_initial_validation_precedes_first_pulse(self):
        pulse=health.path('route-a').with_suffix('.guard')
        def authorized(tx):
            self.assertFalse(pulse.exists(),'Pulse falsely claimed readiness before cold validation')
            return False
        def watch(*args,**kw):
            self.assertIsNone(kw['continuation']())
            return 'test-end'
        with patch.object(guardian,'watch',side_effect=watch),patch.object(health,'authorized',side_effect=authorized), \
             patch('shutdown_state.monitor',return_value=Mock()):
            self.assertEqual(guardian.run('route-a'),'test-end')
        self.assertTrue(pulse.exists())

    def test_parent_waits_within_trial_budget_instead_of_three_seconds(self):
        now=[0.0];supervisor=Mock(pid=123);supervisor.poll.return_value=None
        child=Mock(pid=456);child.poll.return_value=None
        journal=d.safe_json(self.case.root/'profile-trial.json');journal['deadline']=60
        def read(path):
            if str(path).endswith('profile-trial.json'):return journal
            return ({'transaction':'route-a','pid':123,'start_ticks':'123','observer_pid':789,'observer_start_ticks':'789'}
                    if now[0]>=4 else {})
        with patch.object(emergency.bounded,'begin',side_effect=lambda spawn:spawn('route-a')), \
             patch.object(emergency.bounded,'spawn',return_value=child),patch.object(emergency.subprocess,'Popen',return_value=supervisor), \
             patch.object(d,'safe_json',side_effect=read),patch.object(d,'process_start',side_effect=lambda pid:str(pid)), \
             patch.object(emergency.time,'monotonic',side_effect=lambda:now[0]), \
             patch.object(emergency.time,'sleep',side_effect=lambda seconds:now.__setitem__(0,now[0]+seconds)):
            try:result=emergency.start()
            except RuntimeError as error:self.fail('Readiness was rejected inside the original trial budget: '+str(error))
        self.assertEqual(result.pid,456)
        self.assertGreaterEqual(now[0],4)
        self.assertLess(now[0],40)

    def test_failsafe_before_input_readiness_never_publishes_ready(self):
        d.FAILSAFE.touch();stop=threading.Event();ready=threading.Event();errors=[]
        thread=self.supervisor('route-a',stop,ready,errors)
        with contextlib.redirect_stderr(io.StringIO()):thread.start();thread.join(3)
        self.assertFalse(thread.is_alive());self.assertFalse(ready.is_set())
        self.assertEqual([getattr(error,'reason',None) for error in errors],['failsafe-present'])
        self.assertFalse(health.path('route-a').exists())

    def test_input_loss_before_first_heartbeat_cannot_publish_ready(self):
        stop=threading.Event();ready=threading.Event();errors=[]
        thread=self.supervisor('route-a',stop,ready,errors,b'READY\nLOST\n')
        thread.start();thread.join(3)
        self.assertFalse(thread.is_alive());self.assertFalse(ready.is_set());self.assertEqual(errors,[])
        self.assertFalse(health.path('route-a').exists())
        emergency.recover.assert_called_once_with('route-a','input_lost')

    def test_missing_guardian_pulse_stops_before_input_and_preserves_reserve(self):
        journal=d.safe_json(self.case.root/'profile-trial.json');journal['deadline']=60;d.save(journal)
        now=[0.0]
        with patch.object(emergency.time,'monotonic',side_effect=lambda:now[0]), \
             patch.object(emergency.time,'sleep',side_effect=lambda seconds:now.__setitem__(0,now[0]+seconds)), \
             patch.object(health,'require_guardian',side_effect=FileNotFoundError()), \
             patch.object(emergency.subprocess,'Popen') as observer,patch.object(emergency,'recover',return_value=True):
            with self.assertRaisesRegex(RuntimeError,'guarded startup deadline'):emergency.supervise('route-a')
        observer.assert_not_called()
        self.assertGreaterEqual(now[0],40);self.assertLess(now[0],40.01)
        self.assertFalse((self.case.root/'escape-ready.json').exists())

    def test_corrupt_or_exhausted_startup_deadline_is_never_admission(self):
        for deadline in (float('nan'),float('inf'),True,20,19,91,'60',None):
            with self.subTest(deadline=deadline),patch.object(emergency.time,'monotonic',return_value=0), \
                 patch.object(d,'safe_json',return_value={'transaction':'route-a','state':'pending','deadline':deadline}):
                with self.assertRaises(ValueError):emergency.startup_deadline('route-a')

    def test_slow_first_heartbeat_after_priming_still_cannot_publish_ready(self):
        journal=d.safe_json(self.case.root/'profile-trial.json');journal['deadline']=60;d.save(journal)
        now=[0.0];original=health.publish
        def slow_publish(*args):
            original(*args);now[0]+=3
        with patch.object(emergency.time,'monotonic',side_effect=lambda:now[0]), \
             patch.object(health,'require_guardian'),patch.object(health,'publish',side_effect=slow_publish), \
             patch.object(emergency.subprocess,'Popen',side_effect=lambda args,**kw:Observer(kw['pass_fds'][0],b'READY\nPING\n')), \
             patch.object(emergency,'save_ready') as ready,patch.object(emergency,'recover',return_value=True):
            with self.assertRaisesRegex(RuntimeError,'watchdog deadline'):emergency.supervise('route-a')
        ready.assert_not_called()
