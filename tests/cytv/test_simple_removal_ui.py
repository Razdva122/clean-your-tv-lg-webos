"""Real Qt workers/widgets for the simple same-goal removal presentation."""
import json
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

    def prepare_root_restore(self, *, restore_result='restored'):
        from tests.cytv.clean_removal_fixture import prepare

        prepare(self.fixture)
        remote = self.fixture.remote
        remote.installed = [{'id': 'com.cleanyourtv.root.preview', 'version': '1.2.2'}]
        original_run = remote.run
        clean_requested = False

        def run(command, **kwargs):
            nonlocal clean_requested
            if 'deploy.py restore' in command:
                remote.calls.append(('run', command))
                return json.dumps({'returnValue': True, 'result': restore_result})
            if 'install_driver.py clean-remove' in command:
                if not clean_requested:
                    clean_requested = True
                    pending = self.fixture.store.pending(self.fixture.profile)
                    return json.dumps({'operation': pending['product_operation'], 'state': 'recovery_required',
                        'stage': 'original-writers-fenced', 'reason': 'controls-unverified',
                        'cleanup_error': 'cleanup-check-failed',
                        'last_failure': {'stage': 'original-writers-fenced', 'cleanup_step': 'runtime-restore'}})
                remote.installed = []
            return original_run(command, **kwargs)

        remote.run = run

    def start_uninstall_and_restore(self):
        w = self.fixture.window()
        w.start('uninstall', self.fixture.profile)
        self.fixture.pump(lambda: w.pending is not None)
        w.submit('y')
        self.fixture.pump(lambda: not w.running)
        restore = self.fixture.button(w, 'Return to LG Home')
        self.assertIsNotNone(restore, w.details.toPlainText())
        restore.click()
        self.fixture.pump(lambda: w.pending is not None or not w.running)
        self.assertIsNotNone(w.pending, w.content.toPlainText())
        return w

    def package_removals(self):
        return [call[2]['id'] for call in self.fixture.remote.calls
                if call[0] == 'luna' and call[1].endswith('/dev/remove')]

    def test_verified_restore_offers_continuation_of_the_confirmed_uninstall(self):
        self.prepare_root_restore()
        w = self.start_uninstall_and_restore()
        store, profile = self.fixture.store, self.fixture.profile
        operation = store.pending(profile)['removal_operation']
        w.submit('y')
        self.fixture.pump(lambda: not w.running)
        self.assertEqual(w.title.text(), 'LG Home is restored.')
        self.assertEqual(w.rail_title.text(), 'Uninstall Clean Your TV')
        self.assertEqual(self.package_removals(), [])
        self.assertEqual(len(self.fixture.remote.installed), 1)
        self.assertEqual(self.fixture.device_removals, [])

        continuation = self.fixture.button(w, 'Continue removal')
        self.assertIsNotNone(continuation)
        continuation.click()
        self.fixture.pump(lambda: not w.running or w.pending is not None)
        self.assertIsNone(w.pending)
        self.assertEqual(w.title.text(), 'Clean Your TV removal is verified.', w.content.toPlainText())
        self.assertEqual(self.fixture.device_removals, ['d'*32])
        self.assertEqual(self.fixture.remote.installed, [])
        self.assertEqual(self.fixture.connections, [profile] * 3)
        receipt = json.loads((store.device_dir(profile) / 'clean-removal.json').read_bytes())
        self.assertEqual(receipt['removal_operation'], operation)
        self.assertIsNone(store.pending(profile))

    def test_standalone_restore_keeps_apps_even_with_an_existing_removal_request(self):
        self.fixture.remote.installed = [{'id': 'com.gathin.tvhome'}, {'id': 'com.local.nativehome'}]
        store, profile = self.fixture.store, self.fixture.profile
        for kind in ('none', 'legacy', 'confirmed'):
            with self.subTest(kind=kind):
                store.finish(profile)
                if kind == 'legacy':
                    store.begin(profile, 'uninstall', stage='controls-restored')
                elif kind == 'confirmed':
                    store.request_clean_removal(profile)
                original = store.pending(profile)
                w = self.fixture.window()
                start = len(self.fixture.remote.calls)
                self.fixture.check(w, 'restore')
                self.assertIn(('luna', 'com.webos.applicationManager/launch', {'id': 'com.webos.app.home'}),
                              self.fixture.remote.calls[start:])
                self.assertEqual(self.package_removals(), [])
                self.assertEqual(len(self.fixture.remote.installed), 2)
                self.assertIsNone(self.fixture.button(w, 'Continue removal'))
                self.assertEqual(store.pending(profile), original)
                w.close()

    def test_cancel_before_uninstall_consent_keeps_apps_and_creates_no_request(self):
        self.fixture.remote.installed = [{'id': 'com.gathin.tvhome'}, {'id': 'com.local.nativehome'}]
        store, profile = self.fixture.store, self.fixture.profile
        store.finish(profile)
        w = self.fixture.window()
        w.start('uninstall', profile)
        self.fixture.pump(lambda: w.pending is not None)
        w.submit(None)
        self.fixture.pump(lambda: not w.running)
        self.assertIsNone(store.pending(profile))
        self.assertEqual(self.fixture.connections, [])
        self.assertEqual(self.package_removals(), [])
        self.assertIsNone(self.fixture.button(w, 'Return to LG Home'))
        self.assertIsNone(self.fixture.button(w, 'Continue removal'))

    def test_unverified_or_cancelled_restore_never_offers_to_continue_removal(self):
        from cytv.state import target

        for response in ('n', 'y'):
            with self.subTest(response=response):
                self.fixture.store.finish(target('192.0.2.10', 'root'))
                self.prepare_root_restore(restore_result='absent')
                w = self.start_uninstall_and_restore()
                w.submit(response)
                self.fixture.pump(lambda: not w.running)
                self.assertNotEqual(w.title.text(), 'LG Home is restored.')
                self.assertIsNone(self.fixture.button(w, 'Continue removal'))
                self.assertEqual(self.fixture.device_removals, [])
                self.assertEqual(len(self.fixture.remote.installed), 1)
                w.close()

    def test_stale_restore_result_cannot_start_a_new_removal(self):
        self.prepare_root_restore()
        w = self.start_uninstall_and_restore()
        w.submit('y')
        self.fixture.pump(lambda: not w.running)
        store, profile = self.fixture.store, self.fixture.profile
        store.finish(profile)
        replacement = store.request_clean_removal(profile)
        connections = self.fixture.connections.copy()

        self.fixture.button(w, 'Continue removal').click()
        self.fixture.pump(lambda: not w.running or w.pending is not None)
        self.assertIsNone(w.pending)
        self.assertEqual(self.fixture.connections, connections)
        self.assertEqual(self.fixture.device_removals, [])
        self.assertEqual(store.pending(profile), replacement)

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
        self.assertEqual(attempts[-1][0],'recover')
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
        self.assertEqual(w.title.text(),'Check the TV connection to continue removal')
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

    def test_incomplete_final_cleanup_is_neutral_and_offers_review(self):
        def runner(argv, **kwargs):
            write=kwargs['write'];write.recovery(self.fixture.profile)
            write.recovery_plan({'state':'blocked','disposition':'clean-removal',
                'summary':'Removal is not finished yet.','next_step':'Try again',
                'reason':'private-cleanup-incomplete','actions':['continue-removal'],
                'removal':{'stage':'private-cleanup','reason':'private-cleanup-incomplete'}})
            return 1
        w=self.fixture.window();w.run=runner;w.start('uninstall',self.fixture.profile)
        self.fixture.pump(lambda:not w.running)
        self.assertEqual(w.title.text(),'Finish Clean Your TV cleanup')
        self.assertNotEqual(w.title.property('state'),'error')
        self.assertIsNone(self.fixture.button(w,'Try again'))
        self.assertIsNotNone(self.fixture.button(w, 'Review recovery options'))
        self.assertIn('Review recovery options before continuing.', w.subtitle.text())

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
                self.assertIn('Review recovery options before continuing.', w.subtitle.text())
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
