"""Recovery decisions never replace device-side mutation guards."""
import tempfile
import unittest
from unittest.mock import Mock
from cytv import state
from cytv.errors import UserError
from cytv.terminal import Console


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.store = state.Store(tmp.name)
        self.profile = state.target('192.0.2.10', 'no-root')
        self.store.begin(self.profile, 'install')
        self.installer = Mock(store=self.store, profile=self.profile)
        self.installer.status.return_value = {'device': {'apps': []}}
        self.installer.remote.luna.return_value = {'returnValue': True, 'status': {'apps': []}}
        self.output = []

    def run_recovery(self, answers, non_interactive=False):
        from cytv.recovery import recover
        values = iter(answers)
        return recover(self.installer, lambda _: next(values), Console(self.output.append), non_interactive)

    def test_default_no_never_inspects_or_mutates(self):
        before = self.store.pending(self.profile)
        self.run_recovery([''])
        self.installer.status.assert_not_called()
        self.installer.uninstall.assert_not_called()
        self.assertEqual(before, self.store.pending(self.profile))

    def test_noninteractive_cannot_approve_recovery(self):
        with self.assertRaises(UserError): self.run_recovery([], True)
        self.installer.status.assert_not_called()

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
            self.installer.status.return_value = {'device': {'apps': [{'id': 'com.gathin.tvhome'}]}}
            with self.assertRaises(UserError): self.run_recovery(['y'])
            self.installer.uninstall.assert_not_called()
            self.installer.restore.assert_not_called()

    def test_root_resume_requires_second_default_no_confirmation(self):
        self.profile = state.target('192.0.2.10', 'root')
        self.store.begin(self.profile, 'install')
        self.installer.profile = self.profile
        self.installer.status.return_value = {'can_resume_root_setup': True}
        self.run_recovery(['y', ''])
        self.installer.resume_root_setup.assert_not_called()
        self.run_recovery(['y', 'y'])
        self.installer.resume_root_setup.assert_called_once_with()
        self.installer.uninstall.assert_not_called()
        self.installer.remote.luna.assert_not_called()

    def test_unknown_root_never_removes_or_activates(self):
        self.profile = state.target('192.0.2.10', 'root')
        self.store.begin(self.profile, 'install')
        self.installer.profile = self.profile
        self.installer.status.return_value = {}
        with self.assertRaises(UserError): self.run_recovery(['y'])
        self.installer.uninstall.assert_not_called()
        self.installer.resume_root_setup.assert_not_called()

    def test_orphan_root_operation_is_blocked_even_without_host_receipt(self):
        self.profile = state.target('192.0.2.10', 'root')
        self.installer.profile = self.profile
        self.installer.status.return_value = {'pending': None, 'active_operation': 'private-operation',
                                             'device': {'product': {'state': 'running'}}}
        with self.assertRaises(UserError): self.run_recovery(['y'])
        self.installer.uninstall.assert_not_called()
        self.installer.resume_root_setup.assert_not_called()

    def test_incomplete_or_unknown_root_state_without_receipt_blocks(self):
        self.profile = state.target('192.0.2.10', 'root')
        self.installer.profile = self.profile
        for stage in ('incomplete-state', 'installing', None):
            self.installer.status.return_value = {'deployment_stage': stage}
            with self.subTest(stage=stage), self.assertRaises(UserError): self.run_recovery(['y'])

    def test_verified_root_removal_can_finish_inspection_without_reinstall(self):
        self.profile = state.target('192.0.2.10', 'root')
        self.installer.profile = self.profile
        self.installer.status.return_value = {'reconciled': 'product-removal-verified',
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
