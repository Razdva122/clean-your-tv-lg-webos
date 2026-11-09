"""Replacement uses verified full removal, then the selected installer payload."""
import unittest
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

from cytv import operations
from cytv.errors import ExistingRoot, UserError
from tests.cytv import test_operations as fixture
from cytv import cli, state


class RootReinstallationFlowTests(unittest.TestCase):
    def run_install(self, pending=False, approve=True, non_interactive=False):
        with tempfile.TemporaryDirectory() as tmp, patch('cytv.cli.Installer') as cls, \
                patch('cytv.cli.package.verify_payload', return_value={}):
            (Path(tmp) / 'fallback.png').write_bytes(b'fallback')
            profile = state.target('192.0.2.10', 'root')
            store = state.Store(tmp)
            if pending:
                store.save(profile)
                (store.device_dir(profile) / 'known_hosts').write_bytes(b'original pin')
                store.begin(profile, 'activate-root', stage='enable')
            inst = cls.return_value
            inst.preflight.side_effect = ExistingRoot('existing')
            inst.status.return_value = {'deployment_stage': 'installed-recovery-only',
                                       'device': {'result': {'recovery': {'integrity_verified': True}}}}
            inst.version_summary.return_value = []
            inst.root_inventory.return_value = {'apps': [{'id': 'video', 'title': 'Video'}], 'inputs': []}
            inst.install.return_value = {'home_changed': True, 'updates_ready': True}
            inst.has_root_updater.return_value = True
            questions, output = [], []
            def ask(question):
                questions.append(str(question))
                return ('y' if approve else 'n') if 'Reinstall Root?' in question else 'n'
            code = cli.main(['install', '--host', profile['host'], '--edition', 'root',
                             '--data-dir', tmp, '--yes', '--language', 'en'] +
                            (['--non-interactive'] if non_interactive else []),
                            ask=ask, write=output.append, connect=lambda *_: MagicMock(), payload_root=Path(tmp))
            return code, inst, questions, output

    def test_existing_updater_reinstalls_in_the_same_confirmed_setup(self):
        code, inst, questions, output = self.run_install()
        self.assertEqual(code, 0, str(output))
        self.assertTrue(any('Reinstall Root?' in q for q in questions), questions)
        self.assertEqual(inst.install.call_args.kwargs, {'reinstall': 'installed'})
        inst.uninstall_project.assert_not_called()  # The real install validates its replacement first.

    def test_pending_activation_offers_reinstallation_instead_of_old_runtime_retry(self):
        code, inst, questions, output = self.run_install(pending=True)
        self.assertEqual(code, 0, str(output))
        self.assertTrue(any('Reinstall Root?' in q for q in questions), questions)
        self.assertEqual(inst.install.call_args.kwargs, {'reinstall': 'installed'})
        inst.observe_recovery.assert_not_called()
        inst.resume_root_setup.assert_not_called()

    def test_declining_reinstallation_leaves_the_tv_unchanged(self):
        code, inst, _, output = self.run_install(approve=False)
        self.assertEqual(code, 0, str(output))
        inst.install.assert_not_called()
        inst.uninstall_project.assert_not_called()

    def test_yes_does_not_approve_noninteractive_replacement(self):
        code, inst, _, _ = self.run_install(non_interactive=True)
        self.assertEqual(code, 2)
        inst.install.assert_not_called()
        inst.uninstall_project.assert_not_called()


class RootReinstallationTests(unittest.TestCase):
    setUp = fixture.OperationTests.setUp
    installer = fixture.OperationTests.installer
    root_bundle = fixture.OperationTests.root_bundle

    def test_self_consistent_old_runtime_requires_explicit_reinstallation(self):
        self.root_bundle()
        remote = fixture.Remote()
        original = remote.run
        remote.run = lambda command, **kw: ('CYTV_EXISTING_ROOT' if 'CYTV_EXISTING_ROOT' in command
                                           else original(command, **kw))
        inst = self.installer(remote, 'root')
        inst.root_installation = Mock(return_value={'state': 'installed', 'can_maintain': True})
        with self.assertRaises(ExistingRoot):
            inst.preflight(install=True, home_interfaces=True)
        self.assertIsNone(self.store.pending(inst.profile))

    def test_reinstall_cleans_complete_project_before_delivering_new_runtime(self):
        self.root_bundle()
        inst = self.installer(fixture.Remote(), 'root')
        inst.has_root_updater = Mock(return_value=True)
        order = []
        def remove():
            order.append('remove')
            return {'removed': True, 'verified_clean': True, 'restart_required': False}
        inst.uninstall_project = Mock(side_effect=remove)
        original = inst.await_product
        def deliver(*args, **kw):
            order.append('install')
            return original(*args, **kw)
        inst.await_product = deliver
        inst.root_archive = Mock(side_effect=AssertionError('No retained driver or archive needed'))
        result = inst.install(self.inventory, reinstall='installed')
        self.assertTrue(result['home_changed'])
        self.assertEqual(order, ['remove', 'install'])
        self.assertIsNone(self.store.pending(inst.profile))

    def test_failed_activation_can_be_explicitly_replaced_without_binding_resume(self):
        self.root_bundle()
        inst = self.installer(fixture.Remote(), 'root')
        self.store.begin(inst.profile, 'activate-root', stage='enable')
        original = self.store.pending(inst.profile)
        def remove():
            self.assertEqual(self.store.pending(inst.profile), original)
            self.store.finish(inst.profile)
            return {'removed': True, 'verified_clean': True}
        inst.uninstall_project = Mock(side_effect=remove)
        inst.can_resume_root_activation = Mock(side_effect=AssertionError('Old binding is not retry authority'))
        self.assertTrue(inst.install(self.inventory, reinstall='installed')['home_changed'])
        inst.uninstall_project.assert_called_once()

    def test_selected_runtime_mismatch_never_enables_or_stops_helper(self):
        self.root_bundle()
        remote = fixture.Remote()
        original = remote.run
        def run(command, data=None, **kw):
            if data and b'CYTV_SELECTED_RUNTIME_VERIFIED' in data:
                return 'CYTV_SELECTED_RUNTIME_MISMATCH'
            return original(command, data=data, **kw)
        remote.run = run
        inst = self.installer(remote, 'root')
        self.store.begin(inst.profile, 'activate-root', stage='enable')
        before = self.store.pending(inst.profile)
        inst.root_action = Mock(side_effect=AssertionError('Old runtime must not execute'))
        inst.stop_root_helper_for_activation = Mock()
        with self.assertRaises(UserError) as caught:
            inst.activate_root()
        self.assertEqual(caught.exception.reason_code, 'installer-runtime-mismatch')
        self.assertEqual(self.store.pending(inst.profile), before)
        inst.stop_root_helper_for_activation.assert_not_called()

    def test_worker_runtime_mismatch_keeps_specific_reason(self):
        inst = self.installer(fixture.Remote(), 'root')
        inst.product_action = Mock(return_value={'state': 'recovery_required',
                                                'code': 'installer-runtime-mismatch'})
        with self.assertRaises(UserError) as caught:
            inst.await_product('install', 'a' * 32, '/tmp/selected')
        self.assertEqual(caught.exception.reason_code, 'installer-runtime-mismatch')
        inst.product_action.assert_called_once()

    def test_verified_cleanup_recreates_retired_support_before_inspection(self):
        self.root_bundle()
        remote = fixture.Remote()
        inst = self.installer(remote, 'root')
        old_stage = inst.coordinator_code()
        inst._recovery_code = '/tmp/retired-recovery'
        inst._selected_python = '/retired/python'
        inst.uninstall_project = Mock(return_value={'removed': True, 'verified_clean': True})
        inst.prepare_root_reinstall()
        # Full removal retires these files. Simulate the execution boundary,
        # then exercise staging and inspection rather than only cache values.
        original = remote.run
        def run(command, **kw):
            if old_stage + '/install_driver.py' in command:
                self.fail('Retired coordinator was executed')
            return original(command, **kw)
        remote.run = run
        self.assertNotIn('_recovery_code', vars(inst))
        self.assertNotIn('_selected_python', vars(inst))
        self.assertEqual(inst.root_installation()['state'], 'fresh')
        self.assertNotEqual(inst.coordinator_code(), old_stage)

    def test_replacement_permission_does_not_ignore_another_saved_operation(self):
        with tempfile.TemporaryDirectory() as tmp:
            from cytv.root_runtime import require_idle
            store = state.Store(tmp)
            profile = state.target('192.0.2.10', 'root')
            other = state.target(profile['host'], 'no-root')
            store.save(profile); store.save(other)
            store.begin(profile, 'activate-root', stage='enable')
            pending = store.pending(profile)
            require_idle(store, profile, replacing=pending)
            store.begin(other, 'install')
            with self.assertRaises(UserError):
                require_idle(store, profile, replacing=pending)

    def test_incomplete_removal_never_submits_replacement(self):
        self.root_bundle()
        for result in ({'removed': True}, {'removed': True, 'verified_clean': False},
                       {'removed': True, 'verified_clean': True, 'restart_required': True}):
            with self.subTest(result=result):
                inst = self.installer(fixture.Remote(), 'root')
                inst.uninstall_project = Mock(return_value=result)
                inst.await_product = Mock(side_effect=AssertionError('Replacement must wait'))
                with self.assertRaises(UserError):
                    inst.install(self.inventory, reinstall='installed')
                inst.uninstall_project.assert_called_once()
                inst.await_product.assert_not_called()


if __name__ == '__main__':
    unittest.main()
