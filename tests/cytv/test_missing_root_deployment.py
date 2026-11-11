"""Missing native deployment evidence never unlocks another installation."""
import json
import tempfile
import unittest
from unittest.mock import MagicMock

from cytv import diagnostics, state
from cytv.desktop import DesktopConsole
from cytv.errors import UserError
from cytv.operations import Installer
from cytv.recovery import recover
from cytv.recovery_state import assess, assessment_summary


class MissingDeploymentTests(unittest.TestCase):
    def fixture(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        store = state.Store(folder.name)
        profile = state.target('192.0.2.10', 'root')
        store.begin(profile, 'install', home_backend='c1-native-gate', stage='setup', requires_updater=False)
        remote = MagicMock()
        remote.run.return_value = '{"stage":"absent"}'
        installer = Installer(remote, store, profile, '.', {})
        installer.verify_absent = MagicMock(side_effect=AssertionError('absence cannot settle this receipt'))
        return installer, store, profile, remote

    def test_status_export_names_missing_evidence_without_settling_receipt(self):
        installer, store, profile, remote = self.fixture()
        before = (store.device_dir(profile) / 'operation.json').read_bytes()
        result = installer.status()
        report = json.loads(diagnostics.create_report(store, 'status', profile, 'status', status=result).read_text())
        self.assertEqual(report['recovery']['reason'], 'root-deployment-missing')
        self.assertEqual(report['recovery']['state'], 'blocked')
        self.assertEqual(report['recovery']['actions'], ['continue-removal', 'retain-evidence'])
        self.assertFalse(report['status']['can_resume_root_setup'])
        self.assertEqual(report['status']['deployment_stage'], 'absent')
        self.assertEqual(assessment_summary(report['recovery'])['reason'], 'root-deployment-missing')
        self.assertEqual((store.device_dir(profile) / 'operation.json').read_bytes(), before)
        installer.verify_absent.assert_not_called()
        remote.upload.assert_not_called()
        remote.luna.assert_not_called()
        self.assertNotIn('192.0.2.10', json.dumps(report))

    def test_classification_does_not_override_other_recovery_protocols(self):
        installer, store, profile, remote = self.fixture()
        pending = store.pending(profile)
        observation = {'device': {'deployment_stage': 'absent'}, 'can_resume_root_setup': False}
        for change, observed in [
            ({'stage':'upload'}, observation),
            ({'action':'activate-root'}, observation),
            ({'home_backend':'other'}, observation),
            ({'product_operation':'a'*32}, observation),
            ({'previous':{}}, observation),
            ({}, {'device':{'deployment_stage':'incomplete-state'}, 'can_resume_root_setup':False}),
            ({}, {'device':{'deployment_stage':'absent'}}),
            ({}, dict(observation, active_operation='PRIVATE')),
        ]:
            with self.subTest(change=change, observed=observed):
                self.assertNotEqual(assess(profile, dict(pending, **change), observed)['reason'], 'root-deployment-missing')
        for stage in ('setup', 'verify'):
            value = assess(profile, dict(pending, stage=stage), observation)
            self.assertEqual(value['reason'], 'root-deployment-missing')
            self.assertEqual(value['actions'], ['continue-removal', 'retain-evidence'])

    def test_recovery_decline_keeps_receipt_and_never_dispatches_removal(self):
        installer, store, profile, remote = self.fixture()
        before = store.pending(profile)
        events = []
        prompts = []
        def decline(prompt):
            prompts.append(prompt)
            return 'n'
        recover(installer, decline, DesktopConsole(lambda key, value:events.append((key, value))),
                initial_observation=installer.status())
        self.assertEqual(len(prompts), 1)
        self.assertIn('Remove remaining Clean Your TV packages?', prompts[0])
        self.assertEqual(store.pending(profile), before)
        remote.upload.assert_not_called()
        remote.luna.assert_not_called()

    def test_confirmed_removal_reuses_full_cleanup_and_archives_original_failure(self):
        import shutil
        from tests.cytv.test_full_uninstall import FullUninstallTests
        for outcome in ('complete', 'package-failed'):
            with self.subTest(outcome=outcome):
                installer, remote, store, profile, calls, device = FullUninstallTests.fixture(self, outcome)
                shutil.copytree(installer.payload/'root', installer.payload/'root-c1')
                installer.native_root_present = MagicMock(return_value=False)
                store.begin(profile, 'install', home_backend='c1-native-gate', stage='setup', requires_updater=False)
                original = store.pending(profile)
                diagnostics.create_report(store, 'install', profile, 'install-root', UserError('PRIVATE'))
                observed = {'device':{'deployment_stage':'absent'}, 'can_resume_root_setup':False}
                events = []
                prompts = []
                def confirm(prompt):
                    prompts.append(prompt)
                    return 'y'
                def run_recovery():
                    recover(installer, confirm, DesktopConsole(lambda key, value:events.append((key, value))),
                            initial_observation=observed)
                if outcome == 'complete':
                    run_recovery()
                    self.assertIsNone(store.pending(profile))
                    receipt = json.loads((store.device_dir(profile)/'clean-removal.json').read_text())
                    self.assertEqual(receipt['previous'], original)
                    plans = [value for key, value in events if key == 'recovery-plan']
                    self.assertTrue(plans[-1]['verified_clean'])
                else:
                    with self.assertRaises(UserError):run_recovery()
                    pending = store.pending(profile)
                    self.assertEqual(pending['previous'], original)
                    self.assertEqual(pending['removal_reason'], 'removal-failed')
                self.assertEqual(len(prompts), 1)
                self.assertEqual([action for action, _ in calls], ['clean-target', 'clean-remove'])
                remote.luna.assert_not_called()
                report = json.loads(diagnostics.create_report(store, 'recover', profile, 'recover').read_text())
                self.assertEqual(report['first_failure']['phase'], 'install-root')
                self.assertNotIn('PRIVATE', json.dumps(report))

    def test_cli_status_presents_the_blocker_and_keeps_original_failure(self):
        from unittest.mock import patch
        from cytv import cli
        installer, store, profile, remote = self.fixture()
        store.save(profile)
        (store.device_dir(profile)/'known_hosts').write_bytes(b'original pin')
        original_error = UserError('PRIVATE', reason_code='ssh-command-failed')
        diagnostics.create_report(store, 'install', profile, 'install-root', original_error)
        before = store.pending(profile)
        events = []
        with patch('cytv.cli.Installer', return_value=installer), patch('cytv.cli.package.verify_payload', return_value={}):
            code = cli.main(['status', '--host', profile['host'], '--edition', 'root', '--language', 'en',
                             '--data-dir', str(store.root)], connect=lambda *_:remote,
                            write=DesktopConsole(lambda key, value:events.append((key, value))))
        self.assertEqual(code, 0, str(events))
        plans = [value for key, value in events if key == 'recovery-plan']
        self.assertTrue(plans, 'status must show the blocked plan instead of only raw JSON')
        self.assertEqual(plans[-1]['reason'], 'root-deployment-missing')
        self.assertTrue(any(key == 'recovery' for key, _ in events), 'desktop needs the saved recovery profile')
        self.assertEqual(store.pending(profile), before)
        reports = [json.loads(path.read_text()) for path in (store.root/'reports').glob('*.json')]
        latest = next(value for value in reports if value['action'] == 'status')
        self.assertEqual(latest['first_failure']['phase'], 'install-root')
        self.assertEqual(latest['recovery']['reason'], 'root-deployment-missing')
        self.assertNotIn('PRIVATE', json.dumps(latest))
