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

    def test_removal_connection_help_keeps_target_locked_and_retries_removal(self):
        from PySide6.QtWidgets import QLineEdit, QComboBox
        attempts=[]
        def runner(argv,**kwargs):
            attempts.append(argv)
            write=kwargs['write'];write.recovery(self.fixture.profile)
            write.failure_help({'code':'ssh-timeout','title':'The TV did not respond','detail':'Connection timed out.',
                                'next_step':'Keep the TV awake.','pending':True,'can_edit_connection':False})
            write.recovery_plan({'state':'waiting','disposition':'clean-removal','summary':'Removal is not finished yet.',
                                 'next_step':'Try again','actions':['continue-removal'],'reason':'connection-interrupted'})
            return 1
        w=self.fixture.window();w.run=runner;w.start('uninstall',self.fixture.profile)
        self.fixture.pump(lambda:not w.running)
        button=self.fixture.button(w,'Connection details');self.assertIsNotNone(button);button.click()
        fields=w.findChildren(QLineEdit)
        self.assertTrue(fields);self.assertTrue(all(field.isReadOnly() for field in fields))
        self.assertTrue(all(not field.isEnabled() for field in w.findChildren(QComboBox) if field.accessibleName()=='Edition'))
        self.fixture.button(w,'Try again').click();self.fixture.pump(lambda:not w.running)
        self.assertEqual(attempts[0],attempts[1])

    def test_removal_connection_help_can_select_an_existing_root_signin_key(self):
        from unittest.mock import patch
        profile=dict(self.fixture.profile,edition='root',port=2222)
        attempts=[]
        def runner(argv,**kwargs):
            attempts.append(argv);write=kwargs['write'];write.recovery(profile)
            write.failure_help({'code':'ssh-key-file','title':'Check the local SSH key','detail':'Key unavailable.',
                                'next_step':'Choose an existing key.','pending':True,'can_edit_connection':False})
            write.recovery_plan({'state':'waiting','disposition':'clean-removal','summary':'Removal is not finished yet.',
                                 'next_step':'Try again','actions':['continue-removal']})
            return 1
        w=self.fixture.window();w.run=runner;w.start('uninstall',profile)
        self.fixture.pump(lambda:not w.running)
        self.fixture.button(w,'Connection details').click()
        with patch('cytv.gui.QFileDialog.getOpenFileName',return_value=('/existing/key','')):
            self.fixture.button(w,'Choose key file…').click()
        self.fixture.pump(lambda:not w.running)
        self.assertEqual(attempts[-1][attempts[-1].index('--identity')+1],'/existing/key')
        self.assertEqual(attempts[-1][0],'uninstall')
        self.assertEqual(attempts[-1][attempts[-1].index('--host')+1],profile['host'])
        self.assertEqual(attempts[-1][attempts[-1].index('--port')+1],'2222')

    def test_actual_cli_connection_loss_after_restart_wait_keeps_same_goal_and_plain_retry(self):
        self.fixture.store.request_clean_removal(self.fixture.profile)
        self.fixture.store.checkpoint(self.fixture.profile,stage='restart-required',removal_reason='restart-required')
        original=self.fixture.store.pending(self.fixture.profile)['removal_operation']
        def connect(profile,*args,**kwargs):raise TimeoutError('current connection lost')
        self.fixture.connect=connect
        w=self.fixture.window();w.start('uninstall',self.fixture.profile)
        self.fixture.pump(lambda:not w.running)
        self.assertEqual(w.title.text(),'Removal is not finished yet.')
        self.assertIn('Connection to the TV was interrupted. Check the connection and try again.',w.subtitle.text())
        self.assertNotIn('disconnect it from power',w.subtitle.text())
        self.assertIsNotNone(self.fixture.button(w,'Try again'))
        self.assertEqual(self.fixture.store.pending(self.fixture.profile)['removal_operation'],original)
        self.assertEqual(self.fixture.store.pending(self.fixture.profile)['stage'],'restart-required')

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
        self.assertEqual(len(attempts), 3)
        self.fixture.button(w, 'Try again').click()
        self.fixture.pump(lambda: not w.running or w.pending is not None)
        self.assertIsNone(w.pending, 'Same-goal retry must not ask for removal approval again')
        self.assertEqual(attempts, [self.fixture.profile]*6)
        self.assertEqual(self.fixture.store.pending(self.fixture.profile)['removal_operation'], intent['removal_operation'])
        self.assertEqual(self.fixture.remote.calls, [])

    def test_restart_required_overrides_stale_complete_flags(self):
        variants = ({'restart_required':True},
                    {'removal':{'stage':'restart-required'}},
                    {'restart_required':False,'removal':{'stage':'restart-required'}},
                    {'restart_required':False,'removal':{'stage':'package-removal','reason':'restart-required'}},
                    {'restart_required':False,'reason':'restart-required'})
        for variant in variants:
            with self.subTest(variant=variant):
                def runner(argv, **kwargs):
                    kwargs['write'].recovery_plan({'state':'complete','disposition':'clean-removal',
                        'removed':True,'verified_clean':True,
                        'summary':'Clean Your TV removal is verified.','next_step':'Try again',**variant})
                    return 0
                w = self.fixture.window()
                w.run = runner
                w.start('uninstall', self.fixture.profile)
                self.fixture.pump(lambda: not w.running)
                self.assertEqual(w.title.text(), 'Restart the TV to finish removal')
                self.assertIn('disconnect it from power', w.subtitle.text())
                w.close()

    def test_malformed_removal_data_stays_neutral_without_widget_crash(self):
        for malformed in ('PRIVATE', ['PRIVATE'], True, 1, {'stage':['PRIVATE'],'reason':{'PRIVATE':1}}):
            with self.subTest(removal=malformed):
                def runner(argv, **kwargs):
                    kwargs['write'].recovery_plan({'state':'waiting','disposition':'clean-removal',
                        'removed':False,'verified_clean':False,'removal':malformed,
                        'summary':'Removal is not finished yet.','next_step':'Try again'})
                    return 0
                w = self.fixture.window()
                w.run = runner
                w.start('uninstall', self.fixture.profile)
                self.fixture.pump(lambda: not w.running)
                self.assertEqual(w.title.text(), 'Removal is not finished yet.')
                self.assertIn('Check the connection and try again.', w.subtitle.text())
                self.assertNotIn('PRIVATE', w.subtitle.text())
                w.close()

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
