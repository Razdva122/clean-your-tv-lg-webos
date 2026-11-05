"""A failed enable can be reviewed without installing either package again."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock
from cytv import operations, state
from cytv.recovery import recover
from cytv.terminal import Console


class ActivationRecoveryTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.store = state.Store(tmp.name); self.profile = state.target('tv.local', 'root')
        self.remote = MagicMock()
        self.remote.run.return_value = 'CYTV_ACTIVATION_RECOVERABLE'
        self.installer = operations.Installer(self.remote, self.store, self.profile, Path(tmp.name), {}, lambda *_: None)
        self.installer._selected_python = '/usr/bin/python3'
        self.store.begin(self.profile, 'activate-root', stage='enable', requires_updater=True,
                         updates_ready=True, baseline_sha='a'*64, release_sha='b'*64, bundle_sha='c'*64,
                         product_operation='d'*32)
        self.device = {'recovery': {'integrity_verified': True}, 'journal_exists': True,
            'journal': {'state': 'restored'}, 'intent': {'enabled': False, 'phase': 'disabled'},
            'guardian_active': False, 'effective': {'sam_home': 'com.webos.app.home', 'profiles': {
                'defaultApps': {'categories': {'home': 'com.webos.app.home'}},
                'idleApp': {'appId': 'com.webos.app.home'}}}}
        self.installer.root_files_match = MagicMock(return_value=True)
        self.installer.verify_root_updater = MagicMock()
        self.installer.product_action = MagicMock(return_value={'operation': 'd'*32, 'state': 'complete',
            'current': True, 'result': {'baseline_sha': 'a'*64, 'home_changed': False, 'verified': True}})

    def eligible(self):
        return self.installer.can_resume_root_setup(self.store.pending(self.profile), self.device)

    def test_restored_activation_can_be_reviewed_without_enabling(self):
        before = self.store.pending(self.profile)
        self.assertTrue(self.eligible())
        self.assertEqual(self.store.pending(self.profile), before)
        self.assertFalse(any(' enable' in call.args[0] for call in self.remote.run.call_args_list))

    def test_ambiguous_or_changed_evidence_never_authorizes_activation(self):
        original = copy.deepcopy(self.device)
        for field, value in (('guardian_active', True), ('journal', {'state': 'pending'}),
                             ('journal', None), ('journal', []),
                             ('intent', {'enabled': False, 'phase': 'recovering'}),
                             ('recovery', {'integrity_verified': False})):
            with self.subTest(field=field):
                self.device = dict(original, **{field: value})
                self.assertFalse(self.eligible())
        self.device = original
        for changes in ({'stage': 'unknown'}, {'baseline_sha': ''}, {'updates_ready': False},
                        {'requires_updater': False}, {'home_backend': 'c1-native-gate'}):
            pending = dict(self.store.pending(self.profile), **changes)
            with self.subTest(changes=changes):
                self.assertFalse(self.installer.can_resume_root_setup(pending, self.device))
        for event in ({'state': 'pending', 'current': True}, {'state': 'complete', 'current': False},
                      {'state': 'complete', 'current': True, 'result': {'baseline_sha': 'e'*64}}):
            self.installer.product_action.return_value = event
            self.assertFalse(self.eligible())

    def test_blocked_device_or_file_or_updater_check_keeps_receipt(self):
        before = self.store.pending(self.profile)
        self.remote.run.return_value = ''
        self.assertFalse(self.eligible())
        self.remote.run.return_value = 'CYTV_ACTIVATION_RECOVERABLE'
        self.installer.root_files_match.return_value = False
        self.assertFalse(self.eligible())
        self.installer.root_files_match.return_value = True
        self.installer.verify_root_updater.side_effect = RuntimeError('not verified')
        self.assertFalse(self.eligible())
        self.assertEqual(self.store.pending(self.profile), before)

    def test_declining_and_confirming_recovery_preserve_original_evidence(self):
        self.installer.root_action = MagicMock(return_value={'returnValue': True, 'result': self.device})
        run = self.remote.run
        run.side_effect = lambda cmd, **kw: ('{"stage":"installed-recovery-only"}' if 'deploy.json' in cmd
                                            else 'CYTV_ACTIVATION_RECOVERABLE')
        original = self.store.pending(self.profile)
        answers = iter(('y', ''))
        recover(self.installer, lambda _: next(answers), Console(lambda *_: None))
        self.assertEqual(self.store.pending(self.profile), original)
        self.installer.root_action.assert_called_with('status')
        self.assertEqual(list(self.store.device_dir(self.profile).glob('recovery-*.json')), [])
        # The real activation orchestration is exercised separately in test_operations.
        self.installer.activate_root = MagicMock(side_effect=lambda: self.store.finish(self.profile))
        answers = iter(('y', 'y'))
        recover(self.installer, lambda _: next(answers), Console(lambda *_: None))
        saved = list(self.store.device_dir(self.profile).glob('recovery-*.json'))
        self.assertEqual(len(saved), 1)
        self.assertEqual(json.loads(saved[0].read_text())['previous'], original)
        self.assertIsNone(self.store.pending(self.profile))
        self.remote.upload.assert_not_called()

    def test_confirmation_rechecks_before_changing_receipt(self):
        self.installer.status = MagicMock(return_value={'can_resume_root_setup': False})
        before = self.store.pending(self.profile)
        with self.assertRaises(RuntimeError): self.installer.resume_root_setup()
        self.assertEqual(self.store.pending(self.profile), before)

    def test_busy_proof_after_confirmation_keeps_original_receipt_without_enabling(self):
        self.installer.root_action = MagicMock(return_value={'returnValue': True, 'result': self.device})
        blocked = [False]
        self.remote.run.side_effect = lambda cmd, **kw: ('{"stage":"installed-recovery-only"}' if 'deploy.json' in cmd
            else '' if blocked[0] else 'CYTV_ACTIVATION_RECOVERABLE')
        before = self.store.pending(self.profile)
        def answer(prompt):
            if 'Finish Root setup?' in prompt: blocked[0] = True
            return 'y'
        with self.assertRaises(RuntimeError): recover(self.installer, answer, Console(lambda *_: None))
        self.assertEqual(self.store.pending(self.profile), before)
        self.assertEqual(list(self.store.device_dir(self.profile).glob('recovery-*.json')), [])
        self.assertFalse(any(call.args[0].endswith(' enable') for call in self.remote.run.call_args_list))
