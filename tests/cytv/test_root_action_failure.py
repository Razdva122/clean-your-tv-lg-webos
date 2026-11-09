"""Explain only fresh, allowlisted activation refusals without remote prose."""
import unittest

from cytv.errors import TVCommandError, UserError


REASONS = ('transaction-mismatch', 'binding-restored', 'generation-mismatch',
           'token-mismatch', 'boot-mismatch', 'phase-inactive', 'failsafe-present')


class RootActivationFailureTests(unittest.TestCase):
    def apply(self, error, log):
        from cytv.root_action_failure import apply_activation_reason
        apply_activation_reason(error, {'root_diagnostics': {'health_log': log}})
        return error

    def test_fresh_refusals_reach_fixed_guidance_and_report_allowlist(self):
        from cytv.failure_help import for_error, report_summary
        from cytv.diagnostic_context import REASONS as REPORT_REASONS
        for reason in REASONS:
            with self.subTest(reason=reason):
                error = self.apply(TVCommandError(1), {'status': 'read', 'scope': 'since-enable',
                    'health_refusal': reason, 'secret': 'PRIVATE'})
                code = 'root-activation-' + reason
                self.assertEqual(error.reason_code, code)
                self.assertEqual(error.exit_status, 1)
                guide = for_error(error, 'activate-root', {'edition': 'root'}, {'action': 'activate-root'})
                self.assertEqual(guide['code'], code)
                self.assertIn(code, REPORT_REASONS)
                self.assertEqual(report_summary(guide)['code'], code)
                self.assertFalse(guide['can_edit_connection'])
                self.assertNotIn('PRIVATE', str(guide))
                self.assertIn('recovery', guide['next_step'].lower())
                resumed = for_error(error, 'recover', {'edition': 'root'}, {'action': 'activate-root'})
                self.assertEqual(resumed['code'], code)

    def test_history_missing_or_hostile_observations_never_identify_current_cause(self):
        for log in ({}, {'status': 'read', 'scope': 'historical-tail', 'health_refusal': 'boot-mismatch'},
                    {'status': 'unsafe', 'scope': 'since-enable', 'health_refusal': 'boot-mismatch'},
                    {'status': 'read', 'scope': 'since-enable', 'health_refusal': 'generic'},
                    {'status': 'read', 'scope': 'since-enable', 'health_refusal': {'secret': 'PRIVATE'}},
                    {'status': 'read', 'scope': 'since-enable', 'health_refusal': 'PRIVATE'}):
            with self.subTest(log=log):
                self.assertEqual(self.apply(TVCommandError(1), log).reason_code, 'user-error')
        from cytv.root_action_failure import apply_activation_reason
        for value in (None, [], {'root_diagnostics': None}, {'root_diagnostics': {'health_log': []}}):
            error = TVCommandError(1)
            apply_activation_reason(error, value)
            self.assertEqual(error.reason_code, 'user-error')

    def test_connection_storage_and_other_failures_keep_their_original_reason(self):
        log = {'status': 'read', 'scope': 'since-enable', 'health_refusal': 'boot-mismatch'}
        for error in (TVCommandError(1, storage_full=True),
                      UserError('PRIVATE', reason_code='connection-interrupted'),
                      TimeoutError('PRIVATE'), UserError('PRIVATE')):
            before = getattr(error, 'reason_code', None)
            self.apply(error, log)
            self.assertEqual(getattr(error, 'reason_code', None), before)

    def test_specific_activation_guidance_is_limited_to_root_activation_phase(self):
        from cytv.failure_help import for_error
        error = self.apply(TVCommandError(1), {'status': 'read', 'scope': 'since-enable',
                                              'health_refusal': 'boot-mismatch'})
        for phase, edition in (('doctor', 'root'), ('activate-root', 'no-root')):
            guide = for_error(error, phase, {'edition': edition}, {'action': 'activate-root'})
            self.assertEqual(guide['code'], 'pending-operation')
