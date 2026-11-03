"""Recovery reports distinguish journals without exporting private recovery data."""
import json
import tempfile
import unittest
from unittest.mock import Mock
from cytv import diagnostics, state
from cytv.desktop import DesktopConsole
from cytv.errors import TVRejected
from cytv.failure_help import for_error
from cytv.recovery import recover


class RecoveryStateTests(unittest.TestCase):
    def test_reports_explain_next_step_and_keep_original_journal_private(self):
        cases = [
            ({'action': 'uninstall', 'stage': 'pending'}, 'removal-not-submitted', 'review-recovery'),
            ({'action': 'uninstall', 'stage': 'pending', 'removals': {}}, 'removal-not-submitted', 'review-recovery'),
            ({'action': 'uninstall', 'stage': 'pending', 'previous': {'action': 'install', 'secret': 'PRIVATE'}}, 'inherited-operation', 'retain-evidence'),
            ({'action': 'install', 'stage': 'pending', 'expected': {'secret': 'PRIVATE'}}, 'interrupted-install', 'retain-evidence'),
            ({'action': 'uninstall', 'stage': 'removing', 'removals': {'com.gathin.tvhome': 'submitted'}}, 'removal-started', 'retain-evidence'),
            ({'action': 'uninstall', 'stage': 'pending', 'unexpected': 'PRIVATE'}, 'unknown-journal', 'retain-evidence'),
            ({'action': 'uninstall', 'stage': 'pending', 'removals': {'PRIVATE-APP': 'PRIVATE'}}, 'unknown-journal', 'retain-evidence'),
            ({'action': 'uninstall', 'stage': 'pending', 'removals': []}, 'unknown-journal', 'retain-evidence'),
        ]
        for journal, category, next_action in cases:
            with self.subTest(category=category), tempfile.TemporaryDirectory() as tmp:
                store = state.Store(tmp); profile = state.target('192.0.2.10', 'no-root')
                path = store.device_dir(profile) / 'operation.json'
                path.write_text(json.dumps(journal))
                before = path.read_bytes()
                report = diagnostics.create_report(store, 'recover', profile, 'recover')
                data = json.loads(report.read_text())
                self.assertIn('recovery', data)
                self.assertEqual(data['recovery']['category'], category)
                self.assertEqual(data['recovery']['next_action'], next_action)
                self.assertNotIn('PRIVATE', report.read_text())
                self.assertNotIn('192.0.2.10', report.read_text())
                self.assertEqual(path.read_bytes(), before)

    def test_report_includes_only_known_package_removal_states(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = state.Store(tmp); profile = state.target('192.0.2.10', 'no-root')
            store.begin(profile, 'uninstall', stage='removing', removals={
                'com.gathin.tvhome': 'submitted', 'com.local.nativehome': 'terminal', 'PRIVATE-APP': 'PRIVATE'})
            data = json.loads(diagnostics.create_report(store, 'recover', profile, 'recover').read_text())
            self.assertIn('recovery', data)
            self.assertEqual(data['recovery']['removals'], {'home': 'submitted', 'helper': 'terminal'})
            self.assertEqual(data['recovery']['category'], 'unknown-journal')
            self.assertNotIn('PRIVATE', json.dumps(data))

    def test_root_never_inherits_no_root_recovery_permission(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = state.Store(tmp); profile = state.target('192.0.2.10', 'root')
            store.begin(profile, 'uninstall')
            data = json.loads(diagnostics.create_report(store, 'recover', profile, 'recover').read_text())
            self.assertIn('recovery', data)
            self.assertEqual(data['recovery']['category'], 'other-edition')
            self.assertEqual(data['recovery']['next_action'], 'retain-evidence')

    def test_package_status_refusal_is_explained_without_copying_remote_text(self):
        error = TVRejected('PRIVATE', {'returnValue': False, 'errorCode': -1}, 'com.webos.appInstallService/status')
        guide = for_error(error, 'recover', {'edition': 'no-root'}, {'action': 'install', 'stage': 'pending'})
        self.assertEqual(guide['code'], 'recovery-status-rejected')
        self.assertFalse(guide['can_edit_connection'])
        self.assertNotIn('PRIVATE', str(guide))
        self.assertEqual(for_error(error, 'ssh-connect', {'edition': 'no-root'}, {'action': 'install'})['code'], 'pending-operation')

    def test_failed_recovery_plan_contains_the_specific_blocker_and_preserves_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = state.Store(tmp); profile = state.target('192.0.2.10', 'no-root')
            store.begin(profile, 'install')
            before = store.pending(profile)
            installer = Mock(store=store, profile=profile)
            installer.status.return_value = {'device': {'apps': []}}
            installer.remote.luna.side_effect = TVRejected('PRIVATE', {'returnValue': False, 'errorCode': -1}, 'com.webos.appInstallService/status')
            events = []
            with self.assertRaises(TVRejected):
                recover(installer, lambda _: 'y', DesktopConsole(lambda k,v: events.append((k,v))))
            blocked = [v for k,v in events if k == 'recovery-plan' and v['state'] == 'blocked'][-1]
            self.assertIn('package status', blocked['summary'].lower())
            self.assertNotIn('PRIVATE', str(events))
            self.assertEqual(store.pending(profile), before)
            installer.uninstall.assert_not_called()
