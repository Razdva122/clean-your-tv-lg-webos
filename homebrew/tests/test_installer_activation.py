"""Exercise the TV install worker, durable receipt and guarded activation without a TV."""
from contextlib import ExitStack
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2] / 'root-edition'
sys.path.insert(0, str(ROOT))
from installation import Ownership, TV_APPROVAL, TV_INSTALLER, setup_activation_token, cancel_setup_activation
from install_driver import Coordinator
from updater.store import Store


class SetupActivationTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.base = Path(self.stack.enter_context(tempfile.TemporaryDirectory())).resolve()
        self.root = self.base / 'clean-your-tv-root'
        self.root.mkdir(mode=0o700)
        self.store = Store(self.base / 'clean-your-tv-installation', uid=os.getuid())
        self.owner = Ownership(self.store)
        self.operation = 'a' * 32
        self.candidate = 'b' * 64
        token = setup_activation_token(self.store)
        self.approval = dict(issuer=TV_INSTALLER, operation=self.operation, candidate_sha256=self.candidate, token=token)
        self.store.write(TV_APPROVAL, self.approval)
        self.store.write('submission-' + self.operation, dict(
            operation=self.operation, stage='submitted', action='install',
            candidate_sha256=self.candidate, tv_activation=TV_INSTALLER, tv_activation_token=token))
        self.stack.enter_context(patch.object(sys, 'path', [str(ROOT / 'runtime'), *sys.path]))
        spec = importlib.util.spec_from_file_location('setup_activation_cli', ROOT / 'runtime/cli.py')
        self.cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.cli)
        for name, value in [('STATE', self.root), ('EXPECTED_UID', os.getuid()), ('FAILSAFE', self.base / 'failsafe')]:
            self.stack.enter_context(patch.object(self.cli.d, name, value))
        self.stack.enter_context(patch.object(self.cli.os, 'geteuid', return_value=0))
        self.stack.enter_context(patch.object(self.cli.os, 'getppid', return_value=os.getpid()))
        self.stack.enter_context(patch('installation.Ownership', side_effect=lambda store=None: self.owner))
        self.stack.enter_context(patch('helper_bridge.STATE', self.base/'helper'))
        self.active = False
        self.launch = self.stack.enter_context(patch.object(self.cli, 'luna'))
        self.stack.enter_context(patch.object(self.cli, 'execute', side_effect=self.status))
        from intent_runtime import enable
        self.real_enable = enable
        self.enable = self.stack.enter_context(patch('intent_runtime.enable', side_effect=self.enable_home))
        self.lifecycle = Mock()
        self.lifecycle.store.read.side_effect = lambda: self.status('status')['intent']
        self.lifecycle.exit.side_effect = lambda **kwargs: setattr(self, 'active', False)
        self.stack.enter_context(patch('intent_runtime.coordinator', return_value=self.lifecycle))
        self.device = Mock()
        self.device.inspect.return_value = {'state':'fresh'}
        self.device.readback.return_value = {'verified':True}
        self.device.prepare_setup_activation.return_value = self.dispatch
        self.device.setup_activation_active.side_effect = lambda identifier: self.active
        self.device.setup_worker_live.return_value = False
        self.driver = Coordinator(self.device, self.owner, read=lambda path: None)
        self.before_dispatch = lambda: None

    def status(self, mode):
        self.assertEqual(mode, 'status')
        app = self.cli.d.CANDIDATE if self.active else 'com.webos.app.home'
        return {'recovery': {'integrity_verified': True}, 'guardian_active': self.active,
                'intent': {'phase': 'active' if self.active else 'disabled',
                           'enabled': self.active, 'token': self.operation},
                'effective': {'sam_home': app, 'profiles': {'idleApp': {'appId': app},
                              'defaultApps': {'categories': {'home': app}}}}}

    def enable_home(self, *, setup_operation, admission):
        self.assertEqual(setup_operation, self.operation)
        with admission():
            self.assertEqual(self.store.read('activation-' + self.operation)['state'], 'claimed')
            self.active = True

    def dispatch(self):
        self.before_dispatch()
        self.cli.main('setup-enable', self.operation)

    def install(self):
        record = self.driver.install(self.operation, '/verified', activate_after_install=True)
        self.assertEqual(record['state'], 'complete')
        self.assertTrue(self.owner.status()['terminal'])
        return self.driver.activation_status(dict(record, current=True), True)['activation']

    def test_original_worker_enables_once_after_product_unlock_and_reads_route(self):
        self.assertEqual(self.install(), {'state':'active','launch_requested':True,'completed':True})
        self.launch.assert_called_once_with('luna://com.webos.applicationManager/launch',
                                           {'id':self.cli.d.CANDIDATE, 'params':{'cytvPostInstall':self.operation}})
        self.install()
        with self.assertRaises(ValueError):
            self.dispatch()
        self.enable.assert_called_once()
        self.active = False
        self.assertEqual(self.install(), {'state':'finished', 'launch_requested':True, 'completed':True})
        self.enable.assert_called_once()

    def test_restore_between_install_and_enable_revokes_approval(self):
        self.before_dispatch = self.driver.restore
        self.assertEqual(self.install()['state'], 'cancelled')
        self.device.restore.assert_called_once()
        self.enable.assert_not_called()
        self.launch.assert_not_called()

    def test_restore_between_preflight_and_claim_cannot_publish_intent(self):
        def cancelled(**kwargs):
            cancel_setup_activation(self.store)
            self.enable_home(**kwargs)
        self.enable.side_effect = cancelled
        self.assertEqual(self.install()['state'], 'cancelled')
        self.assertFalse(self.active)
        self.launch.assert_not_called()

    def test_emergency_or_failsafe_does_not_rearm(self):
        self.cli.d.FAILSAFE.touch()
        self.assertEqual(self.install()['state'], 'unverified')
        self.enable.assert_not_called()
        self.cli.d.FAILSAFE.unlink()
        self.install()
        self.enable.assert_not_called()

    def test_active_helper_emergency_latch_prevents_auto_activation(self):
        helper = self.base / 'helper'
        helper.mkdir()
        (helper/'blocked').touch()
        self.assertEqual(self.install()['state'], 'unverified')
        self.assertTrue((helper/'blocked').is_file())
        self.enable.assert_not_called()

    def test_unacknowledged_launch_can_only_reconcile_its_matching_route(self):
        class WorkerDeath(BaseException): pass
        self.launch.side_effect = WorkerDeath()
        with self.assertRaises(WorkerDeath):
            self.install()
        self.assertEqual(self.install(), {'state':'active', 'launch_requested':False, 'completed':False})
        self.active = False
        self.assertEqual(self.install(), {'state':'unverified', 'launch_requested':False,'completed':False})
        self.enable.assert_called_once()
        self.launch.assert_called_once()

    def test_identical_replacement_generation_cannot_consume_old_approval(self):
        def replace():
            with self.owner.operation('product', 'product-' + 'f'*32 + '.json') as lease:
                self.owner.stage(lease, 'complete', terminal=True)
        self.before_dispatch = replace
        self.assertEqual(self.install(), {'state':'superseded','launch_requested':False,'completed':False})
        self.enable.assert_not_called()

    def test_live_claim_cannot_publish_a_transient_route_as_finished(self):
        def in_flight(*args):
            self.device.setup_worker_live.return_value = True
            record = self.driver.status(self.operation)
            observed = self.driver.activation_status(dict(record, current=True), True)
            self.assertEqual(observed['activation'], {'state':'pending','completed':False,'launch_requested':False})
            self.device.setup_activation_active.assert_not_called()
        self.launch.side_effect = in_flight
        self.assertEqual(self.install()['state'], 'active')

    def test_prior_completion_survives_boot_rotation_missing_readback_and_replacement(self):
        self.assertEqual(self.install()['state'], 'active')
        record = self.driver.status(self.operation)
        self.device.setup_activation_active.side_effect = None
        self.device.setup_activation_active.return_value = False
        self.assertEqual(self.driver.activation_status(dict(record, current=True), True)['activation']['state'], 'finished')
        result = self.driver.activation_status(dict(record, current=False), True)['activation']
        self.assertEqual(result, {'state':'finished', 'completed':True, 'launch_requested':True})
        with self.owner.operation('product', 'product-' + 'f'*32 + '.json') as lease:
            self.owner.stage(lease, 'complete', terminal=True)
        result = self.driver.activation_status(dict(record, current=False), True)['activation']
        self.assertEqual(result, {'state':'superseded', 'completed':True, 'launch_requested':True})
        self.enable.assert_called_once()

    def test_restore_discards_a_damaged_token_without_parsing_it(self):
        path = Path(self.store.root)/'homebrew-activation-token.json'
        path.write_bytes(b'corrupt')
        self.driver.restore()
        self.device.restore.assert_called_once()
        self.assertFalse(path.exists())
        self.assertIsNone(self.store.read(TV_APPROVAL))
        self.assertEqual(self.install()['state'], 'cancelled')
        self.enable.assert_not_called()

    def test_claimed_worker_death_reopens_read_only(self):
        class WorkerDeath(BaseException): pass
        def die_after_claim(**kwargs):
            with kwargs['admission']():
                raise WorkerDeath()
        self.enable.side_effect = die_after_claim
        with self.assertRaises(WorkerDeath):
            self.install()
        self.assertEqual(self.install(), {'state':'unverified','launch_requested':False,'completed':False})
        with self.assertRaises(ValueError):
            self.dispatch()
        self.enable.assert_called_once()

    def test_real_runtime_claim_precedes_trial_and_first_hardware_effect(self):
        from persistent_store import Store as IntentStore
        class LostWorker(BaseException): pass
        def first_effect(**kwargs):
            intent = IntentStore(self.root).read()
            self.assertEqual((intent['phase'], intent['generation'], intent['token']),
                             ('trial', 1, self.operation))
            self.assertFalse(intent['enabled'])
            self.assertEqual(self.store.read('activation-' + self.operation)['state'], 'claimed')
            raise LostWorker()
        self.enable.side_effect = self.real_enable
        with patch('provision.verify'), patch('helper_bridge.require_idle'), \
             patch('intent_runtime.boot_identity', return_value='test-boot'), \
             patch.object(self.cli.d, 'require_home'), patch('emergency_trial.start', side_effect=first_effect) as start:
            with self.assertRaises(LostWorker):
                self.install()
            self.assertEqual(self.install()['state'], 'unverified')
            start.assert_called_once()
            self.launch.assert_not_called()

    def test_launch_failure_preserves_packages_and_restores_owned_attempt(self):
        self.launch.side_effect = RuntimeError('TV launch failed')
        self.assertEqual(self.install(), {'state':'unverified','launch_requested':False,'completed':False})
        self.assertEqual(self.lifecycle.exit.call_args.kwargs['expected']['token'], self.operation)
        self.assertEqual(self.lifecycle.exit.call_args.kwargs['reason'], 'fault')
        self.assertFalse(self.active)

    def test_concurrent_off_after_claim_wins_before_open(self):
        def stopped(**kwargs):
            self.enable_home(**kwargs)
            cancel_setup_activation(self.store)
            self.active = False
        self.enable.side_effect = stopped
        self.assertEqual(self.install()['state'], 'cancelled')
        self.assertFalse(self.active)
        self.launch.assert_not_called()


if __name__ == '__main__':
    unittest.main()
