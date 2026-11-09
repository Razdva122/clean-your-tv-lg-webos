"""Issue #422: real journals and routing, simulated firmware/process boundaries."""
import copy
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'runtime'))
import boot_gate
import boot_gate as continuation
import device_adapter as d
import intent_runtime as runtime
import persistent_health as health
import test_wake_lifecycle as lifecycle


class ContinuationTests(unittest.TestCase):
    create_route = lifecycle.WakeLifecycleTests.create_route
    read = lifecycle.WakeLifecycleTests.read
    write = lifecycle.WakeLifecycleTests.write
    call = lifecycle.WakeLifecycleTests.call
    tearDown = lifecycle.WakeLifecycleTests.tearDown
    new_startup = lifecycle.WakeLifecycleTests.new_startup

    def setUp(self):
        lifecycle.WakeLifecycleTests.setUp(self)
        for name, value in [
            ('profile-guardian-ready.json', dict(transaction='route-a',pid=98765,start_ticks='111')),
            ('escape-ready.json', dict(transaction='route-a',pid=98766,start_ticks='112',observer_pid=98767,observer_start_ticks='113'))
        ]:
            path = self.root/name; path.write_text(json.dumps(value)); path.chmod(0o600)
        self.new_startup()
        self.expected = copy.deepcopy(self.read())
        self.original = d.safe_json(self.root/'profile-trial.json')
        self.original_file = self.target.read_bytes()
        self.original_inode = self.target.stat().st_ino
        self.steps = []

    def spawn(self, transaction):
        self.steps.append('observer')
        self.assertNotEqual(transaction, 'route-a')
        self.assertTrue(continuation.waiting(transaction))
        self.assertEqual(self.read(), self.expected)
        self.assertEqual(self.target.stat().st_ino, self.original_inode)
        health.guardian_ping(transaction)
        class Child:
            def poll(self): return None
        return Child()

    def gate(self, **kwargs):
        self.steps.append('gate')
        self.assertEqual(self.steps[0], 'observer', 'Input protection must precede gate waiting')
        self.assertEqual(self.read(), self.expected)
        self.assertLessEqual(kwargs['timeout'], 35)
        return True

    def dispatch(self, gate=None, spawn=None):
        fresh = health.require_fresh
        def pulse(transaction):
            if not continuation.waiting(transaction): health.publish(transaction, 1)
            return fresh(transaction)
        from unittest.mock import Mock
        with patch.object(continuation,'arm_bootstrap',return_value=Mock()), patch('provision.verify', return_value={}), \
                patch('helper_bridge.require_idle', return_value={}), \
                patch('emergency_trial.spawn_guarded', side_effect=spawn or self.spawn), \
                patch.object(boot_gate, 'wait', side_effect=gate or self.gate), \
                patch.object(health, 'require_fresh', side_effect=pulse), \
                patch.object(d, 'active_guardian', return_value=True):
            return runtime.boot()

    def test_retained_route_never_becomes_stock_during_normal_boot(self):
        result = self.dispatch()
        self.assertEqual(result['intent']['phase'], 'active')
        self.assertEqual(self.read(), self.expected)
        self.assertEqual(self.target.read_bytes(), self.original_file)
        self.assertEqual(self.target.stat().st_ino, self.original_inode)
        self.assertEqual(self.launches, [])
        route = d.safe_json(self.root/'profile-trial.json')
        self.assertEqual(route['baseline'], self.original['baseline'])
        self.assertEqual(route['candidate_identity'], self.original['candidate_identity'])
        self.assertNotEqual(route['transaction'], 'route-a')
        self.assertFalse((self.root/continuation.NAME).exists())

    def test_gate_failure_restores_original_baseline_and_disables(self):
        with self.assertRaisesRegex(RuntimeError, 'Normal startup'):
            self.dispatch(gate=lambda **kwargs:False)
        self.assertEqual(self.store.read()['phase'], 'disabled')
        self.assertEqual(self.read(), self.baseline)
        self.assertFalse((self.root/continuation.NAME).exists())

    def test_observer_failure_restores_original_baseline_and_disables(self):
        def fail(transaction): raise RuntimeError('input failed')
        with self.assertRaisesRegex(RuntimeError, 'input failed'):
            self.dispatch(spawn=fail)
        self.assertEqual(self.store.read()['phase'], 'disabled')
        self.assertEqual(self.read(), self.baseline)

    def test_escape_during_gate_cannot_be_reenabled(self):
        def gate(**kwargs):
            from persistent_recovery import bound_exit
            transaction = self.c.read_binding()['transaction']
            self.assertTrue(bound_exit(transaction, reason='escape'))
            return True
        with self.assertRaises(ValueError): self.dispatch(gate=gate)
        self.assertEqual(self.store.read()['phase'], 'disabled')
        self.assertEqual(self.read(), self.baseline)

    def test_live_predecessor_refuses_continuation(self):
        with patch.object(d, 'process_start', return_value='111'):
            self.assertFalse(continuation.eligible(self.c,self.intent,runtime.boot_identity()))
        self.assertEqual(self.read(), self.expected)

    def test_conflicting_profile_refuses_continuation(self):
        self.target.write_bytes(b'foreign')
        self.assertFalse(continuation.eligible(self.c,self.intent,runtime.boot_identity()))
        self.assertEqual(self.target.read_bytes(), b'foreign')

    def test_stale_old_health_cannot_authorize_new_transaction(self):
        def gate(**kwargs):
            with self.assertRaises(health.HealthContextError): health.publish('route-a', 2)
            self.assertEqual(self.read(), self.expected)
            return True
        self.dispatch(gate=gate)

    def test_interrupted_durable_prefixes_recover_after_dispatcher_restart(self):
        # Reconstruct the fixture for every crash boundary; recovery is real and
        # must use the original baseline even across a torn binding.
        for boundary in ('record','intent','route','binding'):
            with self.subTest(boundary=boundary):
                case = ContinuationTests('test_live_predecessor_refuses_continuation')
                case.setUp()
                try:
                    target, name = {
                        'record': (continuation,'save'),
                        'intent': (case.c,'event'),
                        'route': (d,'save'),
                        'binding': (case.c,'write_binding')
                    }[boundary]
                    original = getattr(target,name)
                    def crash(*args, **kwargs):
                        original(*args,**kwargs)
                        raise RuntimeError('simulated process death')
                    from unittest.mock import Mock
                    with patch.object(continuation,'arm_bootstrap',return_value=Mock()), patch('provision.verify',return_value={}), \
                            patch('helper_bridge.require_idle',return_value={}), \
                            patch.object(target,name,side_effect=crash):
                        with self.assertRaisesRegex(RuntimeError,'simulated process death'):
                            continuation.prepare(case.c,case.intent,runtime.boot_identity())
                    self.assertTrue((case.root/continuation.NAME).exists())
                    self.assertEqual(runtime.boot(), 'restored')
                    self.assertEqual(case.store.read()['phase'], 'disabled')
                    self.assertEqual(case.read(), case.baseline)
                    self.assertFalse((case.root/continuation.NAME).exists())
                finally: case.tearDown()

    def test_failsafe_cannot_publish_persistent_health_during_guarded_wait(self):
        def gate(**kwargs):
            transaction = self.c.read_binding()['transaction']
            d.FAILSAFE.touch()
            self.assertTrue(continuation.waiting(transaction))
            with self.assertRaises(health.HealthContextError): health.publish(transaction,1)
            return False
        with self.assertRaises(RuntimeError): self.dispatch(gate=gate)
        self.assertTrue(d.FAILSAFE.exists(), 'Recovery must never clear failsafe')
        self.assertEqual(self.store.read()['phase'],'disabled')
        self.assertEqual(self.read(),self.baseline)

    def test_missing_predecessor_evidence_refuses_adoption(self):
        (self.root/'escape-ready.json').unlink()
        self.assertFalse(continuation.eligible(self.c,self.intent,runtime.boot_identity()))
        self.assertEqual(self.read(),self.expected)

    def test_recovering_record_cannot_replace_saved_ownership(self):
        from unittest.mock import Mock
        with patch.object(continuation,'arm_bootstrap',return_value=Mock()), \
                patch('provision.verify',return_value={}),patch('helper_bridge.require_idle',return_value={}):
            value, _ = continuation.prepare(self.c,self.intent,runtime.boot_identity())
        route = dict(value['route'],state='recovering')
        route['candidate_identity'] = dict(route['candidate_identity'],inode=route['candidate_identity']['inode']+1)
        d.save(route)
        with self.assertRaisesRegex(ValueError,'recovery authority changed'):
            self.c.exit(self.store.read(),reason='fault')
        self.assertEqual(self.target.read_bytes(),self.original_file)
        self.assertFalse(self.store.read()['enabled'])

    def test_bootstrap_parent_eof_and_deadline_restore_without_another_callback(self):
        import time
        for expiry in (False,True):
            with self.subTest(expiry=expiry):
                read_fd,write_fd = os.pipe()
                try:
                    if not expiry: os.close(write_fd);write_fd=None
                    recovered = []
                    result = continuation.watch_bootstrap(read_fd,
                        time.monotonic()+(-1 if expiry else 1),lambda:recovered.append(True))
                    self.assertEqual(result,'recovered')
                    self.assertEqual(recovered,[True])
                finally:
                    os.close(read_fd)
                    if write_fd is not None: os.close(write_fd)

    def test_bootstrap_disarm_requires_explicit_protection_transfer(self):
        import time
        read_fd,write_fd = os.pipe()
        try:
            os.write(write_fd,b'ARMED\n')
            result = continuation.watch_bootstrap(read_fd,time.monotonic()+1,
                lambda:self.fail('Transferred protection must not recover'))
            self.assertEqual(result,'armed')
        finally: os.close(read_fd);os.close(write_fd)

    def test_recovery_only_supervisor_keeps_watchdog_and_never_publishes_health(self):
        import emergency_trial as emergency
        from unittest.mock import Mock
        from test_health_startup import Observer
        with patch.object(continuation,'arm_bootstrap',return_value=Mock()), \
                patch('provision.verify',return_value={}),patch('helper_bridge.require_idle',return_value={}):
            value,_ = continuation.prepare(self.c,self.intent,runtime.boot_identity())
        transaction = value['route']['transaction']
        health.guardian_ping(transaction)
        d.FAILSAFE.touch()
        def ready(*args):
            self.assertTrue(continuation.waiting(transaction))
            self.assertFalse(health.path(transaction).exists())
        with patch.object(emergency.subprocess,'Popen',side_effect=lambda args,**kw:
                 Observer(kw['pass_fds'][0],b'READY\nPING\nESCAPE\n')), \
                patch.object(emergency,'save_ready',side_effect=ready):
            emergency.supervise(transaction)
        self.assertFalse(health.path(transaction).exists())
        self.assertEqual(self.store.read()['phase'],'disabled')
        self.assertEqual(self.read(),self.baseline)
        self.assertTrue(d.FAILSAFE.exists())

    def test_real_bootstrap_process_recovers_each_unprotected_prefix_on_parent_eof(self):
        import subprocess
        import time
        from unittest.mock import Mock
        original_popen = subprocess.Popen
        for boundary in ('before-record','record','intent','route','binding'):
            with self.subTest(boundary=boundary):
                case = ContinuationTests('test_live_predecessor_refuses_continuation')
                case.setUp(); monitor = None
                try:
                    with patch.object(continuation,'arm_bootstrap',return_value=Mock()), \
                            patch('provision.verify',return_value={}),patch('helper_bridge.require_idle',return_value={}):
                        value,_ = continuation.prepare(case.c,case.intent,runtime.boot_identity())
                    case.store._save(value['prior']); d.save(value['old_route'])
                    case.c.write_binding(value['previous']); continuation.remove()
                    (case.root/'host-home').write_text(d.CANDIDATE)
                    # A real child executes bootstrap + Coordinator recovery.
                    # Substitute only firmware/package boundaries in that child.
                    code = '''
import copy, os, sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import device_adapter as d
import boot_gate
root=Path(sys.argv[2]);d.STATE=root;d.TARGET=root/'profile';d.EXPECTED_UID=os.geteuid()
d.home_present=lambda **kw:True
d.native_input_disable=lambda:None
class Transport:
 def call(self,*args,**kwargs):return {'returnValue':True}
 def write(self,target):(root/'host-home').write_text(target)
d.sam_transport=lambda:Transport()
def read():
 j=d.safe_json(root/'profile-trial.json');value=copy.deepcopy(j['baseline'])
 value['sam_home']=(root/'host-home').read_text()
 if d.TARGET.exists():
  value['profiles']['defaultApps']['categories']['home']=d.CANDIDATE
  value['profiles']['idleApp']['appId']=d.CANDIDATE
 return value
d.read=read
boot_gate.bootstrap(int(sys.argv[3]),int(sys.argv[4]))
'''
                    def process(args, **kwargs):
                        return original_popen([sys.executable,'-c',code,
                            str(Path(continuation.__file__).parent),str(case.root),*args[-2:]],**kwargs)
                    with patch('subprocess.Popen',side_effect=process): monitor=continuation.arm_bootstrap(value)
                    self.assertIsNone(monitor.process.poll())
                    steps=[lambda:continuation.save(value),
                           lambda:case.c.event(value['prior'],'resume',boot=value['intent']['boot'],token=value['intent']['token']),
                           lambda:d.save(value['route']),
                           lambda:case.c.write_binding(value['binding'])]
                    count={'before-record':0,'record':1,'intent':2,'route':3,'binding':4}[boundary]
                    for step in steps[:count]:step()
                    monitor.close()  # OS EOF is identical to an abruptly dead parent.
                    self.assertEqual(monitor.process.wait(timeout=10),0)
                    self.assertEqual(case.store.read()['phase'],'disabled')
                    self.assertFalse(case.target.exists())
                    self.assertEqual((case.root/'host-home').read_text(),d.STOCK)
                    self.assertFalse((case.root/continuation.NAME).exists())
                finally:
                    if monitor is not None:
                        monitor.close()
                        if monitor.process.poll() is None:monitor.process.wait(timeout=10)
                    case.tearDown()

    def test_missing_normal_marker_and_persistent_failsafe_have_bounded_recovery(self):
        real_wait = boot_gate.wait
        elapsed = [0.0]
        (boot_gate.ROOT/'normal.json').unlink();d.FAILSAFE.touch()
        def gate(**kwargs):
            def observe():
                transaction=self.c.read_binding()['transaction']
                self.assertTrue(continuation.waiting(transaction))
                self.assertFalse(health.path(transaction).exists())
                self.assertEqual(self.read(),self.expected)
                return False,True
            return real_wait(observe=observe,timeout=kwargs['timeout'],
                clock=lambda:elapsed[0],sleep=lambda delay:elapsed.__setitem__(0,elapsed[0]+delay))
        with self.assertRaises(RuntimeError): self.dispatch(gate=gate)
        self.assertGreater(elapsed[0],0)
        self.assertLessEqual(elapsed[0],35)
        self.assertTrue(d.FAILSAFE.exists())
        self.assertEqual(self.store.read()['phase'],'disabled')
        self.assertEqual(self.read(),self.baseline)

    def test_slow_guard_startup_consumes_original_budget_instead_of_extending_it(self):
        now=[0.0]
        original=now[0]
        def spawn(transaction):
            now[0]+=30
            return self.spawn(transaction)
        def gate(**kwargs):
            self.assertLessEqual(kwargs['timeout'],10)
            self.assertEqual(d.safe_json(self.root/'profile-trial.json')['deadline'],original+60)
            return True
        with patch.object(continuation.time,'monotonic',side_effect=lambda:now[0]):
            self.dispatch(gate=gate,spawn=spawn)
