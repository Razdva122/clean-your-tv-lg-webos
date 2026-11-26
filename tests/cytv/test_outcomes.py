"""Package, startup and physical-button evidence are never interchangeable."""
import unittest
from cytv.checks import CheckList
from cytv.terminal import Console


class OutcomeTests(unittest.TestCase):
    def setUp(self):
        from cytv.outcomes import SetupOutcome
        self.info, self.events, self.text = {}, [], []
        self.checks = CheckList(self.events.append)
        self.outcome = SetupOutcome(self.checks, self.info)
        self.outcome.begin()
        self.write = Console(self.text.append)

    def test_package_and_launch_ack_do_not_prove_runtime_or_home(self):
        self.outcome.packages_verified()
        self.outcome.launch_accepted()
        self.assertEqual(self.checks.results['packages']['status'], 'pass')
        self.assertEqual(self.checks.results['startup']['status'], 'unknown')
        self.assertEqual(self.checks.results['home-button']['status'], 'unknown')
        self.assertEqual(self.info['setup_outcome']['launch_request'], 'accepted')

    def test_process_observation_cannot_confirm_home(self):
        self.outcome.startup_observed('process-observed')
        self.assertEqual(self.checks.results['startup']['status'], 'pass')
        self.assertEqual(self.info['setup_outcome']['home_button'], 'not-tested')

    def test_home_review_separates_destinations_and_next_steps(self):
        for answer, result, destination, status, next_step in (
                ('1', 'confirmed-by-user', 'cytv-home', 'pass', 'Continue using Clean Your TV Home.'),
                ('2', 'not-working', 'lg-home', 'fail', 'Check Home control status'),
                ('3', 'not-working', 'no-visible-response', 'fail', 'Keep the current setup'),
                ('', 'not-tested', None, 'unknown', 'has not been checked')):
            with self.subTest(answer=answer):
                self.outcome.begin()
                self.outcome.review_home(lambda _: answer, self.write)
                observed = self.info['setup_outcome']
                self.assertEqual(observed['home_button'], result)
                self.assertEqual(observed.get('home_destination'), destination)
                self.assertEqual(self.checks.results['home-button']['status'], status)
                self.assertIn(next_step, self.checks.results['home-button']['detail'])

    def test_existing_observation_does_not_prompt_for_another_press(self):
        self.outcome.review_home(lambda _: '2', self.write)
        self.text.clear()
        self.outcome.review_home(lambda _: self.fail('must reuse the reported result'), self.write)
        self.assertEqual(self.info['setup_outcome']['home_destination'], 'lg-home')
        self.assertEqual(self.text, [])

    def test_noninteractive_and_cancellation_leave_home_untested(self):
        def cancelled(_): raise EOFError
        self.outcome.review_home(cancelled, self.write)
        self.outcome.review_home(lambda _: self.fail('must not ask'), self.write, non_interactive=True)
        self.assertEqual(self.info['setup_outcome']['home_button'], 'not-tested')

    def test_new_attempt_discards_old_owner_observation(self):
        self.outcome.review_home(lambda _: '1', self.write)
        self.info['helper_startup'] = {'state': 'ready'}
        self.outcome.begin()
        self.assertNotIn('helper_startup', self.info)
        self.assertEqual(self.info['setup_outcome']['home_button'], 'not-tested')

    def test_export_revalidates_hostile_and_extra_fields(self):
        from cytv.diagnostic_context import tv_summary
        self.info['setup_outcome']={'packages':'verified','launch_request':'accepted',
            'startup': 'PRIVATE-IP-192.0.2.10', 'home_button': True,
            'home_destination': 'PRIVATE', 'secret':'PRIVATE'}
        exported=tv_summary(self.info)['setup_outcome']
        self.assertEqual(exported, {'packages':'verified','launch_request':'accepted',
                                  'startup':'unknown','home_button':'unknown'})
        self.assertNotIn('PRIVATE', str(exported))
        observed = self.info['setup_outcome']
        observed.update(home_button='confirmed-by-user', home_destination='lg-home')
        self.assertNotIn('home_destination', tv_summary(self.info)['setup_outcome'])

    def test_stop_cancelled_activation_does_not_request_home_test_or_claim_startup(self):
        self.outcome.packages_verified()
        self.outcome.cancelled_by_stop()
        self.outcome.review_home(lambda _:self.fail('must not ask to test a stopped Helper'),self.write)
        self.assertEqual(self.info['setup_outcome']['launch_request'],'not-requested')
        self.assertEqual(self.info['setup_outcome']['startup'],'stopped-during-setup')
        self.assertEqual(self.checks.results['startup']['status'],'unknown')
        self.assertEqual(self.info['setup_outcome']['home_button'],'not-tested')
