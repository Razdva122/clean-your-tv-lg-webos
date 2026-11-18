"""Recovery decisions never replace device-side mutation guards."""
import tempfile
import unittest
from unittest.mock import Mock
from cytv import state
from cytv.errors import UserError
from cytv.terminal import Console


class RecoveryTests(unittest.TestCase):
    def test_saved_restart_request_is_not_a_current_restart_instruction(self):
        from cytv.desktop import DesktopConsole
        from cytv.recovery import removal_plan
        from cytv.recovery_ui import removal_restart_required, removal_details
        self.store.request_clean_removal(self.profile)
        self.store.checkpoint(self.profile, stage='restart-required', removal_reason='restart-required')
        original = self.store.pending(self.profile)
        for connecting in (True, False):
            events = []
            write = DesktopConsole(lambda *event: events.append(event))
            removal_plan(write, self.store, self.profile, connecting=connecting)
            result = next(value for kind, value in events if kind == 'recovery-plan')
            self.assertFalse(removal_restart_required(result))
            self.assertNotIn('Restart the TV', str(removal_details(result)))
            self.assertNotIn('Restart the TV', result['summary'] + result['next_step'])
            self.assertEqual(self.store.pending(self.profile), original)

    def test_recovery_review_does_not_repeat_saved_restart_before_continuation(self):
        from cytv.desktop import DesktopConsole
        from cytv.recovery import recover
        from cytv.recovery_ui import removal_restart_required
        self.store.request_clean_removal(self.profile)
        self.store.checkpoint(self.profile, stage='restart-required', removal_reason='restart-required')
        original = self.store.pending(self.profile)
        events = []
        write = DesktopConsole(lambda *event: events.append(event))
        answers = iter(['y', 'n'])
        recover(self.installer, lambda _: next(answers), write)
        plans = [value for kind, value in events if kind == 'recovery-plan']
        self.assertTrue(plans)
        self.assertTrue(all(not removal_restart_required(value) for value in plans))
        self.assertNotIn('Restart the TV', str(events))
        self.assertEqual(self.store.pending(self.profile), original)

    def test_current_cleanup_restart_reply_still_requests_a_restart(self):
        from cytv.desktop import DesktopConsole
        from cytv.recovery import remove_before_reinstall
        from cytv.recovery_ui import removal_restart_required, removal_details
        self.store.request_clean_removal(self.profile)
        def current_cleanup():
            self.store.checkpoint(self.profile, stage='restart-required', removal_reason='restart-required')
            return {'removed':False, 'verified_clean':False, 'restart_required':True}
        self.installer.uninstall_project.side_effect = current_cleanup
        events = []
        remove_before_reinstall(self.installer, lambda _: 'y', DesktopConsole(lambda *event: events.append(event)))
        result = [value for kind, value in events if kind == 'recovery-plan'][-1]
        self.assertTrue(removal_restart_required(result))
        self.assertIn('Restart the TV', removal_details(result)['blocker_text'])
        self.assertFalse(result['verified_clean'])
        self.assertIsNotNone(self.store.pending(self.profile))

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.store = state.Store(tmp.name)
        self.profile = state.target('192.0.2.10', 'no-root')
        self.store.begin(self.profile, 'install')
        self.installer = Mock(store=self.store, profile=self.profile)
        self.installer.observe_recovery.return_value = {'device': {'apps': []}}
        self.installer.remote.luna.return_value = {'returnValue': True, 'status': {'apps': []}}
        self.output = []

    def run_recovery(self, answers, non_interactive=False):
        from cytv.recovery import recover
        values = iter(answers)
        return recover(self.installer, lambda _: next(values), Console(self.output.append), non_interactive)

    def test_continue_removal_cannot_publish_completion_without_both_proofs_or_during_restart(self):
        self.store.request_clean_removal(self.profile)
        for result in ({'verified_clean':True}, {'verified_clean':True,'removed':False},
                       {'verified_clean':True,'removed':1}, {'verified_clean':1,'removed':True},
                       {'verified_clean':True,'removed':True,'restart_required':True}):
            with self.subTest(result=result):
                restart=result.get('restart_required') is True
                self.store.checkpoint(self.profile,stage='restart-required' if restart else 'private-cleanup',
                                      removal_reason='restart-required' if restart else 'private-cleanup-incomplete')
                self.installer.continue_clean_removal.return_value=result
                plans=[]
                write=Console(self.output.append)
                write.recovery_plan=plans.append
                from cytv.recovery import recover
                answers=iter(['y','y'])
                with self.assertRaises(UserError):recover(self.installer,lambda _:next(answers),write)
                self.assertIsNotNone(self.store.pending(self.profile))
                self.assertIs(plans[-1]['removed'],False)
                self.assertIs(plans[-1]['verified_clean'],False)
                self.assertEqual(plans[-1]['restart_required'],restart)
                self.assertNotEqual(plans[-1]['state'],'complete')

    def test_default_no_never_inspects_or_mutates(self):
        before = self.store.pending(self.profile)
        self.run_recovery([''])
        self.installer.observe_recovery.assert_not_called()
        self.installer.uninstall.assert_not_called()
        self.assertEqual(before, self.store.pending(self.profile))

    def test_noninteractive_cannot_approve_recovery(self):
        with self.assertRaises(UserError): self.run_recovery([], True)
        self.installer.observe_recovery.assert_not_called()

    def test_declining_removal_preserves_journal(self):
        before = self.store.pending(self.profile)
        self.run_recovery(['y', ''])
        self.installer.uninstall.assert_not_called()
        self.assertEqual(before, self.store.pending(self.profile))

    def test_removal_stops_before_reinstallation(self):
        self.installer.uninstall.side_effect = lambda: self.store.finish(self.profile)
        self.run_recovery(['y', 'y'])
        self.installer.uninstall.assert_called_once_with()
        self.installer.install.assert_not_called()
        self.assertIsNone(self.store.pending(self.profile))

    def test_denied_busy_malformed_and_false_idle_block_all_changes(self):
        for reply in ({}, {'returnValue': False, 'status': {'apps': []}},
                      {'returnValue': True, 'status': {'apps': ['busy']}},
                      {'returnValue': True, 'status': None}):
            with self.subTest(reply=reply):
                self.installer.remote.luna.return_value = reply
                with self.assertRaises(UserError): self.run_recovery(['y'])
                self.installer.uninstall.assert_not_called()
        self.installer.remote.luna.side_effect = TimeoutError
        with self.assertRaises(TimeoutError): self.run_recovery(['y'])
        self.installer.uninstall.assert_not_called()

    def test_unknown_removal_receipt_blocks_before_restore(self):
        for stage in ('submitted', 'done', 'terminal'):
            self.store.checkpoint(self.profile, action='uninstall', removals={'com.gathin.tvhome': stage})
            self.installer.observe_recovery.return_value = {'device': {'apps': [{'id': 'com.gathin.tvhome'}]}}
            with self.assertRaises(UserError): self.run_recovery(['y'])
            self.installer.uninstall.assert_not_called()
            self.installer.restore.assert_not_called()

    def test_root_resume_requires_second_default_no_confirmation(self):
        self.profile = state.target('192.0.2.10', 'root')
        self.store.begin(self.profile, 'install')
        self.installer.profile = self.profile
        self.installer.observe_recovery.return_value = {'can_resume_root_setup': True, 'device': {'result': {}}}
        self.run_recovery(['y', ''])
        self.installer.resume_root_setup.assert_not_called()
        self.run_recovery(['y', '1', 'y'])
        self.installer.resume_root_setup.assert_called_once_with(expected_pending=self.store.pending(self.profile))
        self.installer.uninstall.assert_not_called()
        self.installer.remote.luna.assert_not_called()

    def test_unknown_root_never_removes_or_activates(self):
        self.profile = state.target('192.0.2.10', 'root')
        self.store.begin(self.profile, 'install')
        self.installer.profile = self.profile
        self.installer.observe_recovery.return_value = {}
        with self.assertRaises(UserError): self.run_recovery(['y'])
        self.installer.uninstall.assert_not_called()
        self.installer.resume_root_setup.assert_not_called()

    def test_orphan_root_operation_is_blocked_even_without_host_receipt(self):
        self.profile = state.target('192.0.2.10', 'root')
        self.installer.profile = self.profile
        self.installer.observe_recovery.return_value = {'pending': None, 'active_operation': 'private-operation',
                                             'device': {'product': {'state': 'running'}}}
        with self.assertRaises(UserError): self.run_recovery(['y'])
        self.installer.uninstall.assert_not_called()
        self.installer.resume_root_setup.assert_not_called()

    def test_incomplete_or_unknown_root_state_without_receipt_blocks(self):
        self.profile = state.target('192.0.2.10', 'root')
        self.installer.profile = self.profile
        for stage in ('incomplete-state', 'installing', None):
            self.installer.observe_recovery.return_value = {'deployment_stage': stage}
            with self.subTest(stage=stage), self.assertRaises(UserError): self.run_recovery(['y'])

    def test_verified_root_removal_can_finish_inspection_without_reinstall(self):
        self.profile = state.target('192.0.2.10', 'root')
        self.installer.profile = self.profile
        self.installer.observe_recovery.return_value = {'reconciled': 'product-removal-verified',
            'device': {'product': {'state': 'complete', 'current': True}}}
        self.run_recovery(['y'])
        self.installer.install.assert_not_called()
        self.installer.uninstall.assert_not_called()

    def test_unknown_no_root_stage_and_removal_entries_block(self):
        for fields in ({'action': 'uninstall', 'stage': 'unknown'},
                       {'removals': {'other.app': 'done'}}):
            self.store.checkpoint(self.profile, action='install', stage='pending', removals={})
            self.store.checkpoint(self.profile, **fields)
            with self.assertRaises(UserError): self.run_recovery(['y'])
            self.installer.uninstall.assert_not_called()

    def test_inherited_receipt_is_retained_without_offering_removal(self):
        self.store.checkpoint(self.profile, previous={'action': 'install'})
        before = self.store.pending(self.profile)
        with self.assertRaises(UserError): self.run_recovery(['y'])
        self.assertEqual(self.store.pending(self.profile), before)
        self.installer.uninstall.assert_not_called()
        self.installer.remote.luna.assert_not_called()
