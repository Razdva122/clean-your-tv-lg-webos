"""Cross-component #171 boundaries; simulated firmware is not TV acceptance."""
import json
import shutil
import sys
import subprocess
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
import boot_gate
import device_adapter as d
import intent_runtime as runtime
import persistent_health as health
from persistent_recovery import bound_exit
import shutdown_state
import test_persistent_recovery as recovery
import test_native_input as native_tests


class WakeLifecycleTests(unittest.TestCase):
    create_route = recovery.IntegrationTests.create_route
    read = recovery.IntegrationTests.read
    write = recovery.IntegrationTests.write
    tearDown = recovery.IntegrationTests.tearDown

    def setUp(self):
        recovery.IntegrationTests.setUp(self)
        self.last = {'type': 'DTV', 'appId': 'com.webos.app.livetv'}
        self.devices = []; self.calls = []; self.fault_hook = None; self.startup = 'on'
        self.launches = []
        self.foreground = 'com.webos.app.livetv'
        for target, name, value in (
                (health, 'ROOT', self.root/'health'),
                (boot_gate, 'ROOT', self.root/'session'),
                (d, 'PROC', self.root/'proc'),
                (d, 'FAILSAFE', self.root/'failsafe')):
            p = patch.object(target, name, value); p.start(); self.addCleanup(p.stop)
        kernel = d.PROC/'sys/kernel/random/boot_id'
        kernel.parent.mkdir(parents=True); kernel.write_text('kernel-a')
        self.session = runtime.boot_identity()
        self.intent = dict(self.intent, boot=self.session)
        self.store.path.write_text(json.dumps(self.intent))
        health.publish('route-a', 1); health.guardian_ping('route-a')
        self.assertEqual(d.native_input_enable(), 'active')

    def call(self, uri, payload, timeout=5):
        if uri.endswith('/getBootStatus'):
            return dict(returnValue=True, bootTarget='hardware', powerStatus='active',
                        bootStatus='normal', firstAppLaunched=True, firstAppId='')
        if uri.endswith('/getForegroundAppInfo'):
            return dict(returnValue=True, appId=self.foreground)
        if uri.endswith('/launch'):
            self.launches.append(payload['id']); return dict(returnValue=True)
        return native_tests.NativeInputTests.call(self, uri, payload, timeout)

    def new_startup(self, cold=False):
        shutil.rmtree(boot_gate.ROOT)
        if cold:
            (d.PROC/'sys/kernel/random/boot_id').write_text('kernel-b')
        self.assertNotEqual(runtime.boot_identity(), self.session)
        boot_gate.mark()

    def dispatch(self, guardian=True, stale_binding=False):
        def start(before_publish):
            self.assertEqual(self.read(), self.baseline)  # Restore precedes rearm.
            self.create_route('route-b'); before_publish('route-b')
            health.publish('route-b', 1)
            if guardian:
                health.guardian_ping('route-b')
            if stale_binding:
                binding = self.c.read_binding()
                binding['token'] = 'stale-token'
                self.c.binding.write_text(json.dumps(binding))
            return {'transaction': 'route-b'}
        # Only physical process/input startup and the firmware gate timing are
        # substituted. Store, binding, routing, health, EIM receipts and dispatcher
        # execute their real implementations.
        wait = boot_gate.wait
        with patch('emergency_trial.start', side_effect=start), \
                patch.object(d, 'active_guardian', return_value=True), \
                patch.object(boot_gate, 'wait', side_effect=lambda: wait(timeout=0)):
            return runtime.boot()

    def assert_stays_off(self):
        self.assertEqual(self.store.read()['phase'], 'disabled')
        self.assertFalse(self.store.read()['enabled'])
        self.assertEqual(self.read(), self.baseline)
        self.assertEqual(self.devices, [])
        self.assertEqual(self.last, {'type': 'DTV', 'appId': 'com.webos.app.livetv'})
        self.assertEqual(d._native_read()['phase'], 'disabled')
        self.new_startup()
        self.assertEqual(self.dispatch(), 'restored')
        self.assertEqual(self.store.read()['phase'], 'disabled')
        self.assertEqual(self.launches, [])
        self.assertEqual(self.devices, [])

    def test_same_session_power_cycle_never_launches_or_retargets_eim(self):
        # Exercise actual monitor wiring and duplicate ON with an owned child.
        self.last = {'type': 'HDMI_1', 'appId': 'com.webos.app.hdmi1'}
        frames = ''.join(json.dumps(dict(returnValue=True, state=state,
            **({'subscribed': True} if index == 0 else {})))
            for index, state in enumerate(('Active', 'Active Standby', 'Active', 'Active')))
        real_popen = subprocess.Popen
        def child(*args, **kwargs):
            return real_popen([sys.executable, '-c',
                'import sys;print('+repr(frames)+',flush=True);sys.stdin.read()'], **kwargs)
        with patch.object(shutdown_state.subprocess, 'Popen', side_effect=child), \
                patch.object(shutdown_state, 'query', return_value=False), \
                patch.object(shutdown_state.PowerReason, 'poll', return_value=False), \
                patch.object(d, 'active_guardian', return_value=True):
            monitor = shutdown_state.monitor('route-a')
            try:
                deadline = time.monotonic()+2
                while time.monotonic() < deadline:
                    try:
                        snapshot = json.loads(health.path('route-a').with_suffix('.wake').read_text())
                    except (FileNotFoundError, ValueError):
                        snapshot = {}
                    if snapshot.get('wake_count') == 1:
                        break
                    time.sleep(.01)
                self.assertEqual(snapshot.get('wake_count'), 1)
            finally:
                monitor.close()
        self.assertEqual(self.launches, [])
        self.assertEqual(self.store.read(), self.intent)
        self.assertEqual(self.last['type'], 'HDMI_1')
        self.assertEqual(d._native_read()['phase'], 'active')

    def assert_guarded_startup(self, cold):
        self.new_startup(cold=cold)
        result = self.dispatch()
        self.assertEqual(result['intent']['phase'], 'active')
        self.assertEqual(self.launches, [])
        self.assertEqual(self.c.read_binding()['transaction'], 'route-b')
        self.assertEqual(d._native_read()['phase'], 'active')
        # Duplicate callbacks must not replay the fallback or native mutation.
        self.assertEqual(self.dispatch(), 'guarded-intent-trial')
        self.assertEqual(self.launches, [])
        self.assertEqual(sum(name == 'addDevice' for name, _ in self.calls), 1)

    def test_new_session_with_reused_kernel_rearms_without_launch(self):
        self.assert_guarded_startup(cold=False)

    def test_cold_boot_rearms_without_launch(self):
        self.assert_guarded_startup(cold=True)

    def test_boot_rearm_without_guardian_health_fails_without_launch(self):
        self.new_startup()
        with self.assertRaises(FileNotFoundError):
            self.dispatch(guardian=False)
        self.assertFalse(self.store.read()['enabled'])
        self.assertEqual(self.store.read()['phase'], 'recovering')
        self.assertEqual(self.launches, [])

    def test_boot_rearm_with_stale_binding_fails_without_launch(self):
        self.new_startup()
        with self.assertRaises(ValueError):
            self.dispatch(stale_binding=True)
        self.assertFalse(self.store.read()['enabled'])
        self.assertEqual(self.store.read()['phase'], 'recovering')
        self.assertEqual(self.launches, [])

    def test_unproved_observer_exit_stays_off_after_new_startup(self):
        with patch.object(shutdown_state, 'query', return_value=False):
            self.assertTrue(bound_exit('route-a', reason='observer_exit'))
        self.assert_stays_off()

    def test_explicit_off_stays_off_after_new_startup(self):
        self.c.exit(self.intent)
        self.assert_stays_off()

    def test_emergency_beats_positive_shutdown_proof_and_stays_off(self):
        shutdown_state.record('route-a')
        self.assertTrue(bound_exit('route-a', reason='escape'))
        self.assert_stays_off()

    def test_failsafe_stays_off_after_later_normal_startup(self):
        self.new_startup(); d.FAILSAFE.touch()
        self.assertEqual(self.dispatch(), 'restored')
        d.FAILSAFE.unlink()
        self.assert_stays_off()

    def test_absent_normal_marker_cannot_rearm_despite_cleared_failsafe(self):
        self.new_startup(); (boot_gate.ROOT/'normal.json').unlink()
        self.assertEqual(self.dispatch(), 'restored')
        self.assert_stays_off()

    def test_package_loss_cleans_owned_native_input_and_stays_off(self):
        with patch.object(d, 'home_present', return_value=False):
            self.assertTrue(bound_exit('route-a', reason='observer_exit'))
        self.assert_stays_off()

    def test_guarded_boot_with_protected_source_withdraws_native_priority_without_launch(self):
        self.foreground = 'youtube.leanback.v4'
        self.new_startup()
        result = self.dispatch()
        self.assertEqual(result['intent']['phase'], 'active')
        self.assertEqual(self.last, {'type':'DTV','appId':'com.webos.app.livetv'})
        self.assertEqual(self.launches, [])
