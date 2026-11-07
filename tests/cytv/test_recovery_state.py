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
    def test_observer_diagnostics_export_only_fixed_facts(self):
        from cytv.diagnostic_context import status_summary
        result=status_summary({'device':{'observer':{'operation':'PRIVATE','plan_sha256':'PRIVATE','reservation':'active',
            'slots':[{'submission':'claimed-possibly-submitted','terminal':'failure','readback':'not-checked','reason':None,
                      'reply':{'errorText':'PRIVATE'},'path':'PRIVATE'},
                     {'submission':'PRIVATE','terminal':'PRIVATE','readback':'PRIVATE','reason':'PRIVATE'}]}}})
        self.assertEqual(result.get('observer',{}).get('reservation'),'active')
        self.assertEqual(result['observer']['slots'][0]['terminal'],'failure')
        self.assertNotIn('PRIVATE',json.dumps(result))
    def test_cancellation_advice_requires_matching_raw_operation_and_never_exports_proof(self):
        from cytv.recovery_state import assess
        pending={'action':'install','product_operation':'a'*32}
        observed={'device':{},'cancellation':{'operation':'a'*32,'state':'admissible','home_changed':False,
            'candidate_sha256':'b'*64,'proof_sha256':'c'*64,'code_sha256':'d'*64}}
        value=assess({'edition':'root'},pending,observed)
        self.assertEqual(value['actions'],['cancel-install','retain-evidence'])
        observed['device']={'product':{'operation':'e'*32}}
        self.assertEqual(assess({'edition':'root'},pending,observed)['reason'],'foreign-operation')
        observed['device']={}
        observed['cancellation']['operation']='e'*32
        self.assertNotIn('cancel-install',assess({'edition':'root'},pending,observed)['actions'])
    def test_assessment_is_conservative_and_never_exports_receipts(self):
        from cytv.recovery_state import assess
        root = {'edition': 'root'}
        nr = {'edition': 'no-root'}
        cases = [
            (nr, None, {}, 'idle', 'no-pending-operation', []),
            (nr, {'action': 'uninstall', 'stage': 'pending'}, {}, 'pre-submission', 'removal-not-submitted', ['check', 'retain-evidence']),
            (nr, {'action': 'install', 'stage': 'pending'}, {'device': {'apps': []}}, 'blocked', 'terminal-evidence-missing', ['check', 'retain-evidence']),
            (nr, {'action': 'install', 'stage': 'pending', 'previous': {'secret': 'PRIVATE'}}, {}, 'blocked', 'inherited-operation', ['retain-evidence']),
            (root, {'action': 'unknown', 'stage': 'corrupt'}, {}, 'blocked', 'unsupported-receipt', ['retain-evidence']),
            (root, None, {'active_operation': 'PRIVATE'}, 'blocked', 'foreign-operation', ['check', 'retain-evidence']),
            (root, {'action': 'install', 'stage': 'submitted', 'product_operation': 'a'*32},
             {'device': {'product': {'state': 'pending', 'operation': 'a'*32}}}, 'waiting', 'operation-live', ['check', 'retain-evidence']),
            (root, {'action': 'activate-root', 'stage': 'enable'},
             {'can_resume_root_setup': True, 'device': {'result': {}}}, 'setup-ready', 'packages-verified', ['continue-setup', 'finish-home-off', 'retain-evidence']),
            (root, {'action': 'activate-root', 'stage': 'enable'},
             {'can_resume_root_setup': True}, 'blocked', 'observation-unverified', ['check', 'retain-evidence']),
            (root, {'action': 'uninstall', 'product_operation': 'a'*32},
             {'reconciliation': 'product-removal-verified', 'device': {'product': {'operation': 'a'*32, 'state': 'complete', 'current': True}}},
             'terminal-verified', 'removal-verified', ['reconcile', 'retain-evidence']),
        ]
        for profile, pending, observed, state_code, reason, actions in cases:
            with self.subTest(reason=reason):
                before = json.dumps([profile, pending, observed], sort_keys=True)
                result = assess(profile, pending, observed)
                self.assertEqual(result, {'state': state_code, 'reason': reason, 'actions': actions})
                self.assertNotIn('PRIVATE', json.dumps(result))
                self.assertEqual(json.dumps([profile, pending, observed], sort_keys=True), before)

    def test_pending_does_not_hide_current_connection_blocker(self):
        from paramiko import AuthenticationException
        from cytv.errors import UserError, DeveloperKeyError
        pending = {'action': 'install', 'stage': 'pending'}
        for error, edition, code in ((AuthenticationException('PRIVATE'), 'root', 'ssh-auth-root'),
                                     (TimeoutError('PRIVATE'), 'no-root', 'ssh-timeout'),
                                     (UserError('PRIVATE', reason_code='ssh-trust-record'), 'root', 'ssh-identity'),
                                     (DeveloperKeyError('PRIVATE', 'key-unlock'), 'no-root', 'developer-key-unlock')):
            guide = for_error(error, 'ssh-connect', {'edition': edition}, pending)
            self.assertEqual(guide['code'], code)
            self.assertTrue(guide['pending'])
            self.assertFalse(guide['can_edit_connection'])
            self.assertNotIn('PRIVATE', str(guide))
            self.assertIn('original saved', guide['next_step'])

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
            installer.observe_recovery.return_value = {'device': {'apps': []}}
            installer.remote.luna.side_effect = TVRejected('PRIVATE', {'returnValue': False, 'errorCode': -1}, 'com.webos.appInstallService/status')
            events = []
            with self.assertRaises(TVRejected):
                recover(installer, lambda _: 'y', DesktopConsole(lambda k,v: events.append((k,v))))
            blocked = [v for k,v in events if k == 'recovery-plan' and v['state'] == 'blocked'][-1]
            self.assertIn('package status', blocked['summary'].lower())
            self.assertNotIn('PRIVATE', str(events))
            self.assertEqual(store.pending(profile), before)
            installer.uninstall.assert_not_called()
