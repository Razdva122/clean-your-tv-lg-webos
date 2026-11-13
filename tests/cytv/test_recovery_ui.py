"""Bounded presentation only; these values never authorize cleanup."""
import unittest


class RecoveryPresentationTests(unittest.TestCase):
    def test_removal_action_classifies_only_fixed_evidence(self):
        from cytv.recovery_ui import removal_action
        plan = {'disposition':'clean-removal'}
        check = ('check', 'unverified', True)
        retry = ('retry-removal', 'transient', False)
        restart = ('retry-removal', 'restart', True)
        access = ('connect-root', 'access', True)
        complete = ('none', 'complete', False)
        terminal = {'state':'complete', 'removed':True, 'verified_clean':True}
        cases = [
            (terminal, None, complete),
            ({'state':'complete','removed':True}, None, check),
            ({'state':'complete','removed':True,'verified_clean':1}, None, check),
            ({'state':'ready','removed':True,'verified_clean':True}, None, check),
            ({'removal':{'stage':'verified-clean','reason':'removal-verified'}}, None, check),
            ({'actions':['connect-root']}, None, access),
            ({'reason':'root-access-required'}, None, access),
            ({'removal':{'stage':'restart-required'}}, None, restart),
            (dict(terminal, restart_required=True), None, restart),
            (dict(terminal, restart_required=True), {'code':'ssh-auth-root'}, check),
            (terminal, {'code':'ssh-timeout'}, retry),
            ({'reason':'root-access-required'}, {'code':'ssh-timeout'}, retry),
            ({'reason':'root-access-required'}, {'code':'ssh-auth-root'}, check),
            ({'restart_required':True}, {'code':'ssh-timeout'}, retry),
            ({'restart_required':True}, {'code':'ssh-identity'}, check),
            ({'restart_required':True}, {'code':'ssh-access-denied'}, check),
            ({'restart_required':True}, {'code':'ssh-refused'}, check),
            ({'restart_required':True}, {'code':'ssh-unreachable'}, check),
            ({'restart_required':True}, {'code':'ssh-unreachable','transient_connection':True}, retry),
            ({'reason':'cleanup-check-failed','removal':{'stage':'restart-required'}}, None, check),
            ({'reason':'removal-failed','removal':{'stage':'restart-required'}}, None, check),
            ({'reason':'root-worker-busy','removal':{'stage':'restart-required'}}, None, retry),
            ({'reason':'connection-interrupted','removal':{'stage':'restart-required'}}, None, retry),
            ({'reason':'connection-interrupted','actions':['connect-root']}, None, access),
            ({'reason':'removal-failed','removal':{'reason':'connection-interrupted'}}, None, check),
            ({'reason':'connection-interrupted'}, {'code':'recovery-status-rejected'}, check),
            ({'reason':'root-worker-busy','removal':{'reason':'controls-unverified'}}, None, retry),
            ({'reason':'PRIVATE','removal':{'reason':'original-writer-active'}}, None, retry),
            ({'reason':'removal-requested'}, {'code':'PRIVATE'}, check),
            ({'reason':'removal-requested'}, ['PRIVATE'], check),
            ({'reason':'removal-requested'}, {'code':['PRIVATE']}, check),
            ({'actions':'connect-root','removal':['PRIVATE'],'reason':['PRIVATE']}, None, check),
        ]
        cases += [({'reason':reason}, None, retry)
                  for reason in ('connection-interrupted', 'root-worker-busy', 'original-writer-active',
                                 'removal-requested')]
        cases += [({'reason':reason}, None, check)
                  for reason in (None, 'PRIVATE', 'cleanup-check-failed', 'private-cleanup-incomplete',
                                 'ownership-conflict', 'controls-unverified', 'removal-terminal-unknown',
                                 'removal-failed', 'removal-recheck-required')]
        for fields, failure, (action, condition, change) in cases:
            with self.subTest(fields=fields, failure=failure):
                self.assertEqual(removal_action(dict(plan, **fields), failure),
                                 {'action':action, 'condition':condition, 'requires_change':change})
        for malformed in (None, [], 'PRIVATE', {}, {'disposition':'home-off', **terminal}):
            with self.subTest(plan=malformed):
                self.assertEqual(removal_action(malformed),
                                 {'action':'check', 'condition':'unverified', 'requires_change':True})

    def test_precomputed_completion_needs_current_verified_removal(self):
        from cytv.recovery_ui import projected_removal_action
        value = {'state':'blocked','disposition':'clean-removal','removed':False,'verified_clean':False,
                 'removal_action':{'action':'none','condition':'complete','requires_change':False}}
        self.assertEqual(projected_removal_action(value),
                         {'action':'check','condition':'unverified','requires_change':True})

    def test_connection_pending_cleanup_and_package_refusal_have_distinct_results(self):
        from cytv.recovery_ui import removal_title, removal_waiting
        def plan(reason):
            return {'disposition':'clean-removal','reason':reason,'removal':{'stage':'private-cleanup','reason':reason}}
        self.assertEqual(removal_title(plan('connection-interrupted')), 'Check the TV connection to continue removal')
        self.assertEqual(removal_title(plan('private-cleanup-incomplete')), 'Finish Clean Your TV cleanup')
        self.assertEqual(removal_title(plan('removal-failed')), 'The TV could not remove a package')
        self.assertTrue(removal_waiting(plan('private-cleanup-incomplete')))
        self.assertFalse(removal_waiting(plan('removal-failed')))
        self.assertFalse(removal_waiting(plan('private-cleanup-incomplete'),{'code':'ssh-timeout'}))

    def test_protected_files_in_final_cleanup_are_shown_as_partial_removal(self):
        from cytv.recovery_ui import removal_details, removal_title
        plan = {'disposition': 'clean-removal', 'removal': {
            'stage': 'private-cleanup', 'reason': 'root-access-required'}}
        self.assertEqual(removal_title(plan), 'Cleanup is incomplete.')
        self.assertIn('Root access', removal_details(plan)['blocker_text'])
        plan['removal']['stage'] = 'requested'
        self.assertEqual(removal_title(plan), 'Removal is not finished yet.')

    def test_known_cleanup_phase_and_blocker_have_plain_instructions(self):
        from cytv.recovery_ui import removal_details
        self.assertEqual(removal_details({'disposition':'clean-removal','removal':{
            'stage':'private-cleanup','reason':'removal-terminal-unknown'}}), {
                'stage_text':'Removing private setup data…',
                'blocker_text':'The TV package result could not be verified. Review recovery options before continuing.'})

    def test_unknown_codes_do_not_become_private_main_ui_text_or_completion(self):
        from cytv.recovery_ui import removal_details
        details = removal_details({'disposition':'clean-removal','removal':{
            'stage':'PRIVATE-PATH','reason':'PRIVATE-ERROR','original_outcome':'PRIVATE'}})
        self.assertEqual(details, {'stage_text':'Verifying removal…',
                                 'blocker_text':'Removal could not be verified. Review recovery options before continuing.'})
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
