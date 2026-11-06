"""Bounded presentation only; these values never authorize cleanup."""
import unittest


class RecoveryPresentationTests(unittest.TestCase):
    def test_known_cleanup_phase_and_blocker_have_plain_instructions(self):
        from cytv.recovery_ui import removal_details
        self.assertEqual(removal_details({'disposition':'clean-removal','removal':{
            'stage':'private-cleanup','reason':'removal-terminal-unknown'}}), {
                'stage_text':'Removing private setup data…',
                'blocker_text':'A package removal result is unknown. It will not be repeated.'})

    def test_unknown_codes_do_not_become_private_main_ui_text_or_completion(self):
        from cytv.recovery_ui import removal_details
        details = removal_details({'disposition':'clean-removal','removal':{
            'stage':'PRIVATE-PATH','reason':'PRIVATE-ERROR','original_outcome':'PRIVATE'}})
        self.assertEqual(details, {'stage_text':'Verifying removal…',
                                 'blocker_text':'Removal is not verified. Recovery data was kept.'})
        self.assertNotIn('PRIVATE', str(details))
        self.assertEqual(removal_details({'disposition':'clean-removal','removal':{
            'stage':['PRIVATE'], 'reason':{'PRIVATE':True}}}), details)
        self.assertEqual(removal_details({'disposition':'home-off','removal':{}}), {})

    def test_persisted_verified_stage_is_presented_as_current_check(self):
        from cytv.recovery_ui import removal_details
        self.assertEqual(removal_details({'disposition':'clean-removal','removal':{
            'stage':'verified-clean','reason':'removal-verified'}}),
            {'stage_text':'Verifying removal…','blocker_text':''})
