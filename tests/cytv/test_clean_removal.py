import json
from pathlib import Path
import tempfile
import unittest

from cytv.state import Store, target
from cytv.recovery_state import assess, removal_summary


class RemovalIntentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(self.tmp.name)
        self.profile = target('tv.local', 'root')

    def test_request_preserves_nested_unknown_and_first_failure(self):
        self.store.begin(self.profile, 'install', product_operation='a'*32,
                         previous={'action': 'install', 'stage': 'pending'},
                         failure={'reason': 'unknown', 'private': 'SECRET'})
        original = self.store.pending(self.profile)
        raw = (self.store.device_dir(self.profile)/'operation.json').read_bytes()
        intent = self.store.request_clean_removal(self.profile)
        self.assertEqual(intent['previous'], original)
        self.assertEqual(intent['product_operation'], 'a'*32)
        self.assertEqual(intent['stage'], 'requested')
        self.assertEqual(self.store.request_clean_removal(self.profile), intent)
        self.assertEqual((self.store.device_dir(self.profile)/intent['original_receipt']).read_bytes(), raw)
        projection = removal_summary(intent)
        self.assertNotIn('SECRET', str(projection))
        self.assertEqual(assess(self.profile, intent)['actions'], ['continue-removal', 'retain-evidence'])

    def test_359_unknown_does_not_guess_original_submission(self):
        self.profile = target('tv.local', 'no-root')
        self.store.begin(self.profile, 'install', components={}, stage='pending')
        original = self.store.pending(self.profile)
        intent = self.store.request_clean_removal(self.profile)
        self.assertEqual(intent['previous'], original)
        self.assertNotIn('unsubmitted', str(intent))
        self.assertEqual(removal_summary(intent)['state'], 'cleanup-in-progress')

    def test_new_explicit_remove_after_completion_gets_new_goal_and_retains_history(self):
        intent = self.store.request_clean_removal(self.profile)
        self.store.checkpoint(self.profile, stage='verified-clean', result={'removed': True,'verified_clean':True})
        self.store.finish_clean_removal(self.profile)
        self.assertIsNone(self.store.pending(self.profile))
        again = self.store.request_clean_removal(self.profile)
        self.assertNotEqual(again['removal_operation'], intent['removal_operation'])
        self.assertEqual(again['stage'], 'requested')
        self.assertEqual(self.store.request_clean_removal(self.profile),again)
        histories=list(self.store.device_dir(self.profile).glob('clean-removal-history-*.json'))
        self.assertEqual(len(histories),1)
        self.assertEqual(json.loads(histories[0].read_text())['removal_operation'],intent['removal_operation'])

    def test_intent_persists_before_connection_or_support_staging(self):
        intent = self.store.request_clean_removal(self.profile)
        self.assertEqual(self.store.pending(self.profile), intent)
        self.assertEqual(removal_summary(intent), {
            'state':'cleanup-in-progress', 'stage':'requested',
            'reason':'removal-requested', 'original_outcome':'unknown'})

    def test_new_install_has_new_removal_generation_after_old_clean_result(self):
        first=self.store.request_clean_removal(self.profile)
        self.store.checkpoint(self.profile,stage='verified-clean',result={'removed':True,'verified_clean':True})
        self.store.finish_clean_removal(self.profile)
        self.store.begin(self.profile,'install')
        self.store.finish(self.profile)
        second=self.store.request_clean_removal(self.profile)
        self.assertNotEqual(first['removal_operation'],second['removal_operation'])
        self.assertEqual(second['stage'],'requested')

    def test_progress_stage_alone_cannot_finish_removal(self):
        from cytv.errors import UserError
        self.store.request_clean_removal(self.profile)
        self.store.checkpoint(self.profile,stage='verified-clean',result={'removed':True,'verified_clean':False})
        with self.assertRaises(UserError):self.store.finish_clean_removal(self.profile)


if __name__ == '__main__':
    unittest.main()
