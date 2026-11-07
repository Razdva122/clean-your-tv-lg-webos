"""Bounded presentation only; these values never authorize cleanup."""
import unittest


class RecoveryPresentationTests(unittest.TestCase):
    def test_known_cleanup_phase_and_blocker_have_plain_instructions(self):
        from cytv.recovery_ui import removal_details
        self.assertEqual(removal_details({'disposition':'clean-removal','removal':{
            'stage':'private-cleanup','reason':'removal-terminal-unknown'}}), {
                'stage_text':'Removing private setup data…',
                'blocker_text':'Removal could not be confirmed. Check the connection and try again.'})

    def test_unknown_codes_do_not_become_private_main_ui_text_or_completion(self):
        from cytv.recovery_ui import removal_details
        details = removal_details({'disposition':'clean-removal','removal':{
            'stage':'PRIVATE-PATH','reason':'PRIVATE-ERROR','original_outcome':'PRIVATE'}})
        self.assertEqual(details, {'stage_text':'Verifying removal…',
                                 'blocker_text':'Removal could not be confirmed. Check the connection and try again.'})
        self.assertNotIn('PRIVATE', str(details))
        self.assertEqual(removal_details({'disposition':'clean-removal','removal':{
            'stage':['PRIVATE'], 'reason':{'PRIVATE':True}}}), details)
        self.assertEqual(removal_details({'disposition':'home-off','removal':{}}), {})

    def test_persisted_verified_stage_is_presented_as_current_check(self):
        from cytv.recovery_ui import removal_details
        self.assertEqual(removal_details({'disposition':'clean-removal','removal':{
            'stage':'verified-clean','reason':'removal-verified'}}),
            {'stage_text':'Verifying removal…','blocker_text':''})

    def test_current_connection_or_auth_help_overrides_only_restart_presentation(self):
        from cytv.recovery_ui import removal_details, removal_restart_required
        plan={'disposition':'clean-removal','restart_required':True,'removal':{'stage':'restart-required','reason':'restart-required'}}
        for code,next_step in [('ssh-unreachable','Connection to the TV was interrupted. Check the connection and try again.'),('ssh-auth-root','Use the existing Root SSH key.'),('ssh-access-denied','Check app network access.'),('ssh-refused','Check the SSH port.'),('ssh-timeout','Connection to the TV was interrupted. Check the connection and try again.')]:
            with self.subTest(code=code):
                detail=removal_details(plan,{'code':code,'next_step':next_step})
                self.assertEqual(detail['blocker_text'],next_step)
                self.assertNotIn('Restart',detail['stage_text'])
                self.assertTrue(removal_restart_required(plan),'current connection advice cannot authorize completion')
