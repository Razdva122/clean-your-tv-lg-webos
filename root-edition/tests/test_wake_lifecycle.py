"""Cross-component #171 boundaries; simulated firmware is not TV acceptance."""
import json
import shutil
import sys
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

    def dispatch(self):
        def start(before_publish):
            self.assertEqual(self.read(), self.baseline)  # Restore precedes rearm.
            self.create_route('route-b'); before_publish('route-b')
            health.publish('route-b', 1); health.guardian_ping('route-b')
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

    def test_same_session_power_edge_presents_without_rearming_or_retargeting_eim(self):
        power = shutdown_state.PowerState('route-a', self.session)
        power.event(dict(returnValue=True, subscribed=True, state='Active'))
        power.event(dict(returnValue=True, state='Active Standby'))
        token = power.event(dict(returnValue=True, state='Active'))
        self.assertIsNotNone(token)
        # A user-selected native input must not be overwritten to force first screen.
        self.last = {'type': 'HDMI_1', 'appId': 'com.webos.app.hdmi1'}
        with patch.object(d, 'active_guardian', return_value=True):
            self.assertEqual(runtime.present_wake('route-a', self.session,
                lambda: power.revision != token), 'launch-requested')
        self.assertEqual(self.launches, [d.CANDIDATE])
        self.assertEqual(self.store.read(), self.intent)
        self.assertEqual(self.last['type'], 'HDMI_1')
        self.assertEqual(d._native_read()['phase'], 'active')

    def assert_startup_fallback(self, cold):
        self.new_startup(cold=cold)
        result = self.dispatch()
        self.assertEqual(result['presentation'], 'launch-requested')
        self.assertEqual(result['intent']['phase'], 'active')
        self.assertEqual(self.launches, [d.CANDIDATE])
        self.assertEqual(self.c.read_binding()['transaction'], 'route-b')
        self.assertEqual(d._native_read()['phase'], 'active')
        # Duplicate callbacks must not replay the fallback or native mutation.
        self.assertEqual(self.dispatch(), 'guarded-intent-trial')
        self.assertEqual(self.launches, [d.CANDIDATE])
        self.assertEqual(sum(name == 'addDevice' for name, _ in self.calls), 1)

    def test_new_session_with_reused_kernel_uses_guarded_startup_fallback(self):
        self.assert_startup_fallback(cold=False)

    def test_cold_boot_uses_guarded_startup_fallback(self):
        self.assert_startup_fallback(cold=True)

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
