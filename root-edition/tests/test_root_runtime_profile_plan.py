import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"runtime"))
import copy
import unittest
from profile_plan import snapshot, plan, restored, STOCK, CANDIDATE


def response(home=STOCK, idle=STOCK):
    return {'returnValue': True, 'profiles': {
        'defaultApps': {'categories': {'home': home, 'aod': 'aod.original'}},
        'idleApp': {'support': True, 'appId': idle}}}


class ProfilePlanTests(unittest.TestCase):
    def test_plan_changes_only_two_profile_destinations(self):
        raw = response()
        before = copy.deepcopy(raw)
        p = plan(raw, STOCK)
        self.assertEqual(raw, before)
        self.assertEqual(p['candidate_profile'], {
            'defaultApps': {'categories': {'home': CANDIDATE, 'aod': 'aod.original'}},
            'idleApp': {'appId': CANDIDATE, 'support': True}})
        self.assertFalse(p['ready_to_deploy'])

    def test_sam_restore_alone_is_not_complete(self):
        baseline = snapshot(response(), STOCK)
        self.assertFalse(restored(baseline, response(idle=CANDIDATE), STOCK))

    def test_profile_home_restore_alone_is_not_complete(self):
        baseline = snapshot(response(), STOCK)
        self.assertFalse(restored(baseline, response(), CANDIDATE))

    def test_profile_default_must_also_match(self):
        self.assertFalse(restored(snapshot(response(), STOCK), response(home=CANDIDATE), STOCK))

    def test_failed_read_is_not_restored(self):
        self.assertFalse(restored(snapshot(response(), STOCK), {'returnValue': False}, STOCK))

    def test_missing_and_malformed_fields_refuse_plan(self):
        for raw in ({}, {'returnValue': True, 'profiles': []}, response(idle=''), response(home=None)):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                plan(raw, STOCK)

    def test_disabled_idle_or_nonstock_baseline_refused(self):
        disabled = response()
        disabled['profiles']['idleApp']['support'] = False
        for raw, sam in ((disabled, STOCK), (response(idle='other.app'), STOCK),
                         (response(), 'other.app'), (response(), None)):
            with self.subTest(raw=raw, sam=sam), self.assertRaises(ValueError):
                plan(raw, sam)

    def test_support_and_unrelated_profile_changes_prevent_success(self):
        before = snapshot(response(), STOCK)
        for change in ('support', 'aod'):
            raw = response()
            if change == 'support': raw['profiles']['idleApp']['support'] = False
            else: raw['profiles']['defaultApps']['categories']['aod'] = 'changed'
            self.assertFalse(restored(before, raw, STOCK))

    def test_complete_readback_is_restored(self):
        self.assertTrue(restored(snapshot(response(), STOCK), response(), STOCK))


if __name__ == '__main__': unittest.main()
