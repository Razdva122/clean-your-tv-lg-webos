"""User journeys after failed setup; only TV IO is simulated."""
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from cytv import cli, operations, state
from cytv.desktop import DesktopConsole
from cytv.errors import UserError, TVRejected
from cytv.recovery import recover, removal_plan
from cytv.terminal import Console


class FailureJourneys(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.store = state.Store(temp.name)
        self.profile = state.target('192.0.2.10', 'root')
        self.store.save(self.profile)
        (self.store.device_dir(self.profile) / 'known_hosts').write_bytes(b'original pin')
        self.store.begin(self.profile, 'install', product_operation='a'*32)
        self.events = []
        self.write = DesktopConsole(lambda kind, value: self.events.append((kind, value)))

    def test_root_failure_offers_original_connection_recovery(self):
        before = self.store.pending(self.profile)
        cli.explain_failure(self.write, self.store, self.profile, 'install-root', UserError('Unconfirmed'))
        self.assertIn(('recovery', self.profile), self.events)
        self.assertEqual(self.store.pending(self.profile), before)

    def test_cancelled_pending_install_exports_report_and_recovery(self):
        before = self.store.pending(self.profile)
        with patch('cytv.cli.package.verify_payload', return_value={}):
            code = cli.main(['install', '--host', self.profile['host'], '--edition', 'root', '--yes',
                             '--language', 'en', '--data-dir', str(self.store.root)],
                            write=self.write, connect=Mock(side_effect=EOFError),
                            payload_root=self.store.root, ask=lambda _: 'y')
        self.assertEqual(code, 130)
        self.assertEqual(self.store.pending(self.profile), before)
        self.assertIn(('recovery', self.profile), self.events)
        reports = [Path(value) for kind, value in self.events if kind == 'report']
        self.assertEqual(len(reports), 1)
        self.assertTrue(json.loads(reports[0].read_text())['pending'])

    def test_cancel_before_changes_does_not_offer_recovery_or_report(self):
        self.store.finish(self.profile)
        with patch('cytv.cli.package.verify_payload', return_value={}):
            code = cli.main(['install', '--host', self.profile['host'], '--edition', 'root', '--yes',
                             '--language', 'en', '--data-dir', str(self.store.root)],
                            write=self.write, connect=Mock(side_effect=EOFError), payload_root=self.store.root)
        self.assertEqual(code, 130)
        self.assertFalse(any(kind in ('recovery', 'report') for kind, _ in self.events))

    def test_cancelled_cleanup_authentication_is_not_retried_as_network_loss(self):
        pending = self.store.request_clean_removal(self.profile)
        connect = Mock(side_effect=EOFError)
        with patch('cytv.cli.sleep'), patch('cytv.cli.package.verify_payload', return_value={}):
            code = cli.main(['uninstall', '--yes', '--host', self.profile['host'], '--edition', 'root',
                             '--language', 'en', '--data-dir', str(self.store.root)],
                            write=self.write, connect=connect, payload_root=self.store.root)
        self.assertEqual(code, 130)
        self.assertEqual(connect.call_count, 1)
        self.assertEqual(self.store.pending(self.profile), pending)

    def test_root_blocker_is_saved_and_offers_access_handoff(self):
        profile = state.target(self.profile['host'], 'no-root')
        pending = self.store.request_clean_removal(profile)
        installer = operations.Installer(Mock(), self.store, profile, self.store.root, {}, self.write)
        with patch('cytv.no_root_cleanup._device', return_value={
                'schema':1, 'root_present':['Root state'], 'present':[], 'blocked':[]}):
            with self.assertRaises(UserError):
                installer.continue_clean_removal(pending)
        removal_plan(self.write, self.store, profile)
        plan = [value for kind, value in self.events if kind == 'recovery-plan'][-1]
        self.assertEqual(plan['reason'], 'root-access-required')
        self.assertIn('connect-root', plan['actions'])
        self.assertEqual(plan['removal']['reason'], 'root-access-required')

    def test_no_root_failed_observation_offers_confirmed_full_removal(self):
        profile = state.target(self.profile['host'], 'no-root')
        self.store.begin(profile, 'install', recovery_protocol='no-root-original-stream-v1', observer_operation='b'*32)
        before = self.store.pending(profile)
        installer = Mock(store=self.store, profile=profile)
        installer.observe_recovery.return_value = {'device':{'observer':{'operation':'b'*32}},
            'no_root_ready':False, 'no_root_reason':'original-vendor-failure'}
        def remove():
            self.store.request_clean_removal(profile)
            return {'removed':False, 'verified_clean':False, 'restart_required':True}
        installer.uninstall_project.side_effect = remove
        answers = iter(['y', 'y'])
        recover(installer, lambda _: next(answers), self.write)
        pending = self.store.pending(profile)
        self.assertEqual(pending['recovery_protocol'], 'clean-removal-v1')
        self.assertEqual(pending['previous'], before)
        installer.continue_no_root.assert_not_called()

    def test_declining_fallback_keeps_original_failed_install(self):
        profile = state.target(self.profile['host'], 'no-root')
        self.store.begin(profile, 'install', recovery_protocol='no-root-original-stream-v1', observer_operation='b'*32)
        before = self.store.pending(profile)
        installer = Mock(store=self.store, profile=profile)
        installer.observe_recovery.return_value = {'device':{'observer':{'operation':'b'*32}}, 'no_root_ready':False}
        answers = iter(['y', 'n'])
        recover(installer, lambda _: next(answers), self.write)
        self.assertEqual(self.store.pending(profile), before)
        installer.uninstall_project.assert_not_called()


class ActivationCompensation(unittest.TestCase):
    def setUp(self):
        # These tests start after runtime admission; its actual byte reader has
        # separate coverage in test_root_runtime_contract and reinstallation.
        gate = patch('cytv.root_runtime_contract.verify')
        gate.start()
        self.addCleanup(gate.stop)

    def test_status_cannot_discard_pending_lg_home_compensation_on_either_backend(self):
        from tests.cytv.test_operations import Remote
        from tests.cytv.test_root_gate_operations import NativeOperationsTests
        for native in (False, True):
            with self.subTest(native=native):
                fixture = self.fixture()
                installer = fixture.installer
                extra = {'home_backend':'c1-native-gate','home_token':'a'*32} if native else {}
                fixture.store.checkpoint(fixture.profile, stage='launch', activation_restore_pending=True,
                                         activation_restore='unverified', **extra)
                before = fixture.store.pending(fixture.profile)
                active = NativeOperationsTests().active() if native else Remote().active
                installer.root_action = lambda _: {'result':active}
                fixture.remote.run.return_value = '{"stage":"installed-recovery-only"}'
                result = installer.status()
                self.assertEqual(fixture.store.pending(fixture.profile), before)
                self.assertIsNone(result['reconciled'])
                self.assertIsNone(result['reconciliation'])
                self.assertFalse(result['can_resume_root_setup'])

    def test_c1_launch_failure_compensates_with_stock_proof_or_keeps_retry_marker(self):
        from tests.cytv.test_root_gate_activation import NativeActivationTests
        proof = NativeActivationTests()
        proof.setUp()
        for restore_fails in (False, True):
            with self.subTest(restore_fails=restore_fails):
                fixture = self.fixture()
                installer = fixture.installer
                fixture.store.checkpoint(fixture.profile, stage='stop-helper', home_backend='c1-native-gate')
                actions = []
                enabled = False
                restored = False
                def root_action(action):
                    nonlocal enabled, restored
                    actions.append(action)
                    if action == 'enable':
                        enabled = True
                    if action == 'restore':
                        if restore_fails:
                            raise UserError('Restore failed')
                        restored = True
                    return proof.active if enabled and not restored else proof.stock
                installer.root_action = root_action
                failure = TVRejected('Launch refused', {'returnValue':False}, 'com.webos.applicationManager/launch')
                def luna(uri, payload, **kwargs):
                    if uri.endswith('/getForegroundAppInfo'):
                        return {'returnValue':True,'appId':'com.webos.app.livetv'}
                    raise failure
                fixture.remote.luna.side_effect = luna
                with self.assertRaises(TVRejected) as caught:
                    installer.activate_root()
                self.assertIs(caught.exception, failure)
                self.assertEqual(actions.count('enable'), 1)
                self.assertEqual(actions.count('restore'), 1)
                pending = fixture.store.pending(fixture.profile)
                self.assertEqual(pending['activation_restore_pending'], restore_fails)
                self.assertEqual(pending['activation_restore'], 'unverified' if restore_fails else 'verified')

    def fixture(self):
        from tests.cytv.test_activation_recovery import ActivationRecoveryTests
        fixture = ActivationRecoveryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.installer.stop_root_helper_for_activation = lambda: None
        return fixture

    def test_failed_restore_keeps_original_error_and_durable_next_action(self):
        fixture = self.fixture()
        installer = fixture.installer
        failure = TVRejected('PRIVATE FIRST', {'returnValue':False}, 'com.webos.applicationManager/launch')
        fixture.remote.luna.side_effect = failure
        from tests.cytv.test_operations import Remote
        def root_action(action):
            if action == 'restore':
                raise UserError('PRIVATE SECOND')
            return {'result':Remote().active}
        installer.root_action = root_action
        with self.assertRaises(TVRejected) as caught:
            installer.activate_root()
        self.assertIs(caught.exception, failure)
        pending = fixture.store.pending(fixture.profile)
        self.assertTrue(pending['activation_restore_pending'])
        self.assertEqual(pending['activation_restore'], 'unverified')
        self.assertNotIn('PRIVATE', json.dumps(pending))

    def test_lost_restore_ack_reconnects_and_checks_inactive_without_repeating_restore(self):
        fixture = self.fixture()
        installer = fixture.installer
        from tests.cytv.test_operations import Remote
        restored = []
        def root_action(action):
            if action == 'restore':
                restored.append(True)
                raise UserError('Lost response', reason_code='connection-interrupted')
            return {'result':fixture.device if restored else Remote().active}
        installer.root_action = root_action
        installer.reconnect = Mock(return_value=fixture.remote)
        self.assertTrue(installer.recover_failed_activation())
        self.assertEqual(len(restored), 1)
        self.assertEqual(installer.reconnect.call_count, 1)
        self.assertFalse(fixture.store.pending(fixture.profile)['activation_restore_pending'])

    def test_failed_launch_restores_and_verifies_lg_home_preserving_original_error(self):
        from tests.cytv.test_activation_recovery import ActivationRecoveryTests
        fixture = ActivationRecoveryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        installer = fixture.installer
        installer.stop_root_helper_for_activation = lambda: None
        failure = TVRejected('Launch refused', {'returnValue':False, 'errorCode':-1},
                             'com.webos.applicationManager/launch')
        fixture.remote.luna.side_effect = failure
        actions = []
        def root_action(action):
            actions.append(action)
            from tests.cytv.test_operations import Remote
            return {'returnValue':True, 'result':fixture.device if 'restore' in actions else Remote().active}
        installer.root_action = root_action
        with self.assertRaises(TVRejected) as caught:
            installer.activate_root()
        self.assertIs(caught.exception, failure)
        self.assertIn('restore', actions)
        pending = fixture.store.pending(fixture.profile)
        self.assertEqual(pending['stage'], 'launch')
        self.assertEqual(pending['activation_restore'], 'verified')
        self.assertFalse(pending['activation_restore_pending'])
        from cytv.diagnostics import create_report
        report = json.loads(create_report(fixture.store, 'install', fixture.profile, 'launch-root', failure).read_text())
        self.assertEqual(report['activation_recovery'], {'lg_home':'verified', 'retry_required':False})
        self.assertEqual(report['luna']['operation'], 'application-launch')


class RemovalContinuation(unittest.TestCase):
    @unittest.skipIf(os.name == 'nt' or not shutil.which('node'), 'POSIX TV filesystem model requires Node')
    def test_uncertain_cleanup_carrier_is_not_reinstalled_when_inventory_lags(self):
        from tests.cytv.test_no_root_simple_removal import SimpleRemoval
        fixture = SimpleRemoval()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.carrier_payload()
        directory = fixture.root/'bus/roles.d'
        directory.mkdir()
        (directory/'com.local.nativehome.service.json').write_text('{}')
        directory.chmod(0o555)
        self.addCleanup(directory.chmod, 0o755)
        luna = fixture.remote.luna
        def delayed_install(uri, payload, **kwargs):
            if uri.endswith('/dev/install'):
                fixture.remote.calls.append((uri, payload))
                raise UserError('Lost carrier reply', reason_code='connection-interrupted')
            return luna(uri, payload, **kwargs)
        fixture.remote.luna = delayed_install
        fixture.installer.reconnect = lambda: fixture.remote
        with patch('cytv.operations.sleep'), self.assertRaises(UserError) as caught:
            fixture.remove()
        self.assertEqual(sum(uri.endswith('/dev/install') for uri, _ in fixture.remote.calls), 1)
        self.assertEqual(caught.exception.reason_code, 'root-access-required')
        self.assertEqual(fixture.store.pending(fixture.profile)['removal_reason'], 'root-access-required')

    def test_busy_root_worker_waits_and_rechecks_same_removal_goal(self):
        from tests.cytv.test_full_uninstall import FullUninstallTests
        fixture = FullUninstallTests()
        self.addCleanup(fixture.doCleanups)
        installer, remote, store, profile, calls, device = fixture.fixture()
        run = remote.run.side_effect
        busy = [True]
        def run_busy(command, **kwargs):
            if busy and '/install_driver.py clean-remove ' in command:
                busy.pop()
                raise UserError('Busy', reason_code='root-worker-busy')
            return run(command, **kwargs)
        remote.run.side_effect = run_busy
        installer.reconnect = Mock(return_value=remote)
        with patch('cytv.operations.sleep'):
            self.assertTrue(installer.uninstall(full_project=True)['verified_clean'])
        installer.reconnect.assert_not_called()
        record = json.loads((store.device_dir(profile)/'clean-removal.json').read_text())
        self.assertEqual(record['removal_target_operation'], 'b'*32)

    def test_failed_root_cleanup_keeps_related_no_root_goal_unfinished(self):
        from tests.cytv.test_full_uninstall import FullUninstallTests
        fixture = FullUninstallTests()
        self.addCleanup(fixture.doCleanups)
        installer, remote, store, profile, calls, device = fixture.fixture('package-failed')
        source = state.target(profile['host'], 'no-root')
        store.save(source)
        store.request_clean_removal(source)
        store.checkpoint(source, removal_reason='root-access-required')
        before = store.pending(source)
        with self.assertRaises(UserError):
            installer.uninstall(full_project=True)
        self.assertEqual(store.pending(source), before)

    def test_transport_retries_stop_after_three_without_finishing_or_losing_original_history(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        store = state.Store(temp.name)
        profile = state.target('192.0.2.10', 'no-root')
        store.begin(profile, 'install')
        original = store.pending(profile)
        pending = store.request_clean_removal(profile)
        remote = Mock()
        remote.run.side_effect = UserError('PRIVATE NETWORK', reason_code='connection-interrupted')
        installer = operations.Installer(remote, store, profile, temp.name, {}, lambda _:None)
        installer.reconnect = Mock(return_value=remote)
        with patch('cytv.operations.sleep'), self.assertRaises(UserError):
            installer.continue_clean_removal(pending)
        self.assertEqual(remote.run.call_count, 3)
        self.assertEqual(installer.reconnect.call_count, 2)
        self.assertEqual(store.pending(profile)['previous'], original)
        self.assertEqual(store.pending(profile)['removal_operation'], pending['removal_operation'])
        self.assertFalse((store.device_dir(profile)/'clean-removal.json').exists())

    def test_cli_retries_initial_transport_loss_then_keeps_normal_removal_result(self):
        from tests.cytv.test_desktop_recovery import DesktopRecoveryTests
        fixture = DesktopRecoveryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.store.request_clean_removal(fixture.profile)
        original = fixture.store.pending(fixture.profile)['removal_operation']
        attempts = []
        def connect(*args, **kwargs):
            attempts.append(args[0])
            if len(attempts) < 3:
                raise TimeoutError('PRIVATE NETWORK')
            return fixture.remote
        with patch('cytv.cli.sleep'), patch.object(operations.Installer, '_continue_clean_removal',
                return_value={'removed':False,'verified_clean':False,'restart_required':True}):
            code = cli.main(['uninstall','--yes','--host',fixture.profile['host'],'--edition','no-root',
                             '--port',str(fixture.profile['port']),'--data-dir',str(fixture.root)],
                            payload_root=fixture.payload, connect=connect, write=lambda _:None)
        self.assertEqual(code, 0)
        self.assertEqual(len(attempts), 3)
        self.assertEqual(fixture.store.pending(fixture.profile)['removal_operation'], original)

    def test_verified_root_cleanup_finishes_same_tv_blocked_no_root_goal(self):
        from tests.cytv.test_full_uninstall import FullUninstallTests
        fixture = FullUninstallTests()
        self.addCleanup(fixture.doCleanups)
        installer, remote, store, profile, calls, device = fixture.fixture()
        source = state.target(profile['host'], 'no-root', 9923)
        foreign = state.target('other.local', 'no-root')
        for item in (source, foreign):
            store.save(item)
            store.begin(item, 'install')
            store.request_clean_removal(item)
            store.checkpoint(item, removal_reason='root-access-required')
        original = store.pending(source)
        self.assertTrue(installer.uninstall(full_project=True)['verified_clean'])
        self.assertIsNone(store.pending(source))
        record = json.loads((store.device_dir(source)/'clean-removal.json').read_text())
        self.assertEqual(record['removal_operation'], original['removal_operation'])
        self.assertEqual(record['previous'], original['previous'])
        self.assertIsNotNone(store.pending(foreign))

    @unittest.skipIf(os.name == 'nt' or not shutil.which('node'), 'POSIX TV filesystem model requires Node')
    def test_lost_remove_response_reconnects_and_finishes_without_duplicate_package_request(self):
        from tests.cytv.test_no_root_simple_removal import SimpleRemoval
        fixture = SimpleRemoval()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        app = 'com.gathin.tvhome'
        fixture.remote.apps.add(app)
        fixture.own_file('apps/usr/palm/applications/'+app+'/appinfo.json', json.dumps({'id':app}))
        luna = fixture.remote.luna
        fixture.remote.cut = app
        def lost_reply(*args, **kwargs):
            try:
                return luna(*args, **kwargs)
            except UserError as error:
                raise UserError('Connection interrupted', reason_code='connection-interrupted') from error
        fixture.remote.luna = lost_reply
        connections = []
        fixture.installer.reconnect = lambda: (connections.append(True) or fixture.remote)
        with patch('cytv.operations.sleep'):
            first = fixture.remove()
        self.assertTrue(first['restart_required'])
        self.assertEqual(len(connections), 1)
        self.assertEqual(sum(uri.endswith('/dev/remove') for uri, _ in fixture.remote.calls), 1)
        goal = fixture.store.pending(fixture.profile)['removal_operation']
        fixture.reboot()
        self.assertTrue(fixture.remove()['verified_clean'])
        record = json.loads((fixture.store.device_dir(fixture.profile)/'clean-removal.json').read_text())
        self.assertEqual(record['removal_operation'], goal)


class RecoveryWidgets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tests.cytv.test_desktop_recovery import DesktopRecoveryTests, HAS_QT
        if not HAS_QT:
            raise unittest.SkipTest('Qt optional')
        DesktopRecoveryTests.setUpClass()

    def setUp(self):
        from tests.cytv.test_desktop_recovery import DesktopRecoveryTests
        self.fixture = DesktopRecoveryTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_root_failure_and_cancel_both_offer_recovery(self):
        self.fixture.prepare_root_recovery('install')
        for code in (2, 130):
            with self.subTest(code=code):
                w = self.fixture.window()
                w.command = 'install'
                cli.explain_failure(DesktopConsole(w.receive), self.fixture.store,
                                    self.fixture.profile, 'install-root', UserError('Unconfirmed'))
                w.receive('done', code)
                self.assertIsNotNone(self.fixture.button(w, 'Review recovery options'))

    def test_root_blocker_shows_real_reason_and_connect_root_action(self):
        w = self.fixture.window()
        with patch('cytv.no_root_cleanup._device', return_value={
                'schema':1, 'root_present':['Root state'], 'present':[], 'blocked':[]}):
            w.start('uninstall')
            self.fixture.pump(lambda: w.pending is not None)
            w.submit('y')
            self.fixture.pump(lambda: not w.running)
        self.assertIn('Root access', w.subtitle.text())
        button = self.fixture.button(w, 'Connect using Root')
        self.assertIsNotNone(button)
        with patch.object(w, 'start') as start:
            button.click()
        self.assertEqual(start.call_args.args[0], 'uninstall')
        self.assertEqual(start.call_args.args[1], state.target(self.fixture.profile['host'], 'root'))
