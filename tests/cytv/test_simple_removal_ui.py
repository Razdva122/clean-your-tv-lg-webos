"""Real Qt workers/widgets for the simple same-goal removal presentation."""
import unittest

from tests.cytv import test_desktop_recovery as desktop_fixture


@unittest.skipUnless(desktop_fixture.HAS_QT, 'Qt is optional for console-only tests')
class SimpleRemovalUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        desktop_fixture.DesktopRecoveryTests.setUpClass()

    def setUp(self):
        self.fixture = desktop_fixture.DesktopRecoveryTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_connection_loss_try_again_runs_same_uninstall_target(self):
        attempts = []
        profile = self.fixture.profile
        def runner(argv, **kwargs):
            attempts.append(argv)
            write = kwargs['write']
            write.recovery(profile)
            write.recovery_plan({'state':'waiting','disposition':'clean-removal',
                'summary':'Removal is not finished yet.','next_step':'Try again',
                'actions':['continue-removal'], 'reason':'connection-interrupted',
                'removal':{'stage':'package-removal','reason':'connection-interrupted'}})
            return 1
        w = self.fixture.window()
        w.run = runner
        w.start('uninstall', profile)
        self.fixture.pump(lambda: not w.running)
        self.assertIn('Connection to the TV was interrupted. Check the connection and try again.', w.subtitle.text())
        self.assertIsNone(self.fixture.button(w, 'Review recovery options'))
        self.fixture.button(w, 'Try again').click()
        self.fixture.pump(lambda: not w.running)
        self.assertEqual(len(attempts), 2)
        self.assertTrue(all(args[0] == 'uninstall' for args in attempts))
        self.assertEqual(attempts[0], attempts[1])
        self.assertNotIn('--yes', attempts[1])

    def test_restart_required_is_neutral_and_explains_full_power_restart(self):
        def runner(argv, **kwargs):
            write = kwargs['write']
            write.recovery(self.fixture.profile)
            write.recovery_plan({'state':'waiting','disposition':'clean-removal',
                'summary':'Removal is not finished yet.','next_step':'Try again',
                'removed':False,'verified_clean':False,'restart_required':True,
                'actions':['continue-removal'], 'removal':{'stage':'restart-required','reason':'restart-required'}})
            return 0
        w = self.fixture.window()
        w.run = runner
        w.start('uninstall', self.fixture.profile)
        self.fixture.pump(lambda: not w.running)
        self.assertEqual(w.title.text(), 'Restart the TV to finish removal')
        self.assertIn('disconnect it from power, reconnect it, then choose Try again', w.subtitle.text())
        self.assertIn('Standby is not a full restart.', w.subtitle.text())
        self.assertIsNotNone(self.fixture.button(w, 'Try again'))

    def test_actual_cli_retry_reuses_approved_goal_without_second_confirmation(self):
        attempts = []
        def connect(profile, *args, **kwargs):
            attempts.append(dict(profile))
            raise TimeoutError('simulated connection loss')
        self.fixture.connect = connect
        w = self.fixture.window()
        w.start('uninstall', self.fixture.profile)
        self.fixture.pump(lambda: w.pending is not None)
        w.submit('y')
        self.fixture.pump(lambda: not w.running)
        intent = self.fixture.store.pending(self.fixture.profile)
        self.assertEqual(len(attempts), 1)
        self.fixture.button(w, 'Try again').click()
        self.fixture.pump(lambda: not w.running or w.pending is not None)
        self.assertIsNone(w.pending, 'Same-goal retry must not ask for removal approval again')
        self.assertEqual(attempts, [self.fixture.profile, self.fixture.profile])
        self.assertEqual(self.fixture.store.pending(self.fixture.profile)['removal_operation'], intent['removal_operation'])
        self.assertEqual(self.fixture.remote.calls, [])

    def test_restart_required_overrides_stale_complete_flags(self):
        def runner(argv, **kwargs):
            kwargs['write'].recovery_plan({'state':'complete','disposition':'clean-removal',
                'removed':True,'verified_clean':True,'restart_required':True,
                'summary':'Clean Your TV removal is verified.','next_step':'Try again'})
            return 0
        w = self.fixture.window()
        w.run = runner
        w.start('uninstall', self.fixture.profile)
        self.fixture.pump(lambda: not w.running)
        self.assertEqual(w.title.text(), 'Restart the TV to finish removal')

    def test_explicit_remove_needs_removed_and_verified_clean(self):
        for removed in (None,False,True):
            with self.subTest(removed=removed):
                def runner(argv, **kwargs):
                    kwargs['write'].recovery_plan({'state':'complete','disposition':'clean-removal',
                        'summary':'Clean Your TV removal is verified.','next_step':'Other TV apps stay installed.',
                        'removed':removed,'verified_clean':True})
                    return 0
                w = self.fixture.window()
                w.run = runner
                w.start('uninstall', self.fixture.profile)
                self.fixture.pump(lambda: not w.running)
                self.assertEqual(w.title.text(), 'Clean Your TV removal is verified.' if removed is True else 'Removal is not finished yet.')
