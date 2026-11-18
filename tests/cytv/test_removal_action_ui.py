"""Command dispatch follows the advisory policy without changing backend authority."""
import unittest
from unittest.mock import patch
from tests.cytv import test_desktop_recovery as desktop_fixture


@unittest.skipUnless(desktop_fixture.HAS_QT, 'Qt is optional for console-only tests')
class RemovalActionUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        desktop_fixture.DesktopRecoveryTests.setUpClass()

    def setUp(self):
        self.fixture = desktop_fixture.DesktopRecoveryTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_deterministic_failure_reviews_recovery_instead_of_repeating_uninstall(self):
        for reason in ('cleanup-check-failed', 'private-cleanup-incomplete', 'ownership-conflict', 'unknown'):
            with self.subTest(reason=reason):
                calls = []
                def runner(argv, **kwargs):
                    calls.append(argv)
                    write = kwargs['write']
                    write.recovery(self.fixture.profile)
                    write.recovery_plan({'state': 'blocked', 'disposition': 'clean-removal',
                        'summary': 'Removal is not finished yet.', 'next_step': 'Review recovery options',
                        'reason': reason, 'actions': ['continue-removal'],
                        'removal_action': {'action': 'check', 'condition': 'unverified', 'requires_change': True}})
                    return 1
                window = self.fixture.window()
                window.run = runner
                window.start('uninstall', self.fixture.profile)
                self.fixture.pump(lambda: not window.running)
                self.assertIsNone(self.fixture.button(window, 'Try again'))
                review = self.fixture.button(window, 'Review recovery options')
                self.assertIsNotNone(review)
                review.click()
                self.fixture.pump(lambda: not window.running)
                self.assertEqual([argv[0] for argv in calls], ['uninstall', 'recover'])
                self.assertNotIn('--yes', calls[-1])
                window.close()

    def test_unverified_controls_and_package_results_have_distinct_guidance(self):
        from cytv.errors import UserError
        from cytv.recovery import removal_plan

        self.fixture.store.request_clean_removal(self.fixture.profile)
        for stage, reason, title, instruction in (
                ('original-writers-fenced', 'controls-unverified',
                 'TV controls could not be verified.',
                 'Restore LG Home before continuing removal.'),
                ('package-removal', 'removal-terminal-unknown',
                 'The TV package result could not be verified.',
                 'Review recovery options before trying to remove packages again.'),
                ('requested', 'unknown',
                 'Removal is not finished yet.',
                 'Removal could not be verified. Review recovery options before continuing.')):
            with self.subTest(reason=reason):
                self.fixture.store.checkpoint(self.fixture.profile, stage=stage, removal_reason=reason)
                calls = []
                def runner(argv, **kwargs):
                    calls.append(argv)
                    if argv[0] == 'uninstall':
                        removal_plan(kwargs['write'], self.fixture.store, self.fixture.profile,
                                     error=UserError('PRIVATE', reason_code=reason), phase='uninstall')
                    return 2
                window = self.fixture.window()
                window.run = runner
                window.start('uninstall', self.fixture.profile)
                self.fixture.pump(lambda: not window.running)
                self.assertEqual(window.title.text(), title)
                self.assertIn(instruction, window.subtitle.text())
                self.assertNotIn('PRIVATE', window.subtitle.text())
                restore = self.fixture.button(window, 'Return to LG Home')
                if reason == 'controls-unverified':
                    self.assertIsNotNone(restore)
                    self.assertTrue(restore.isDefault())
                else:
                    self.assertIsNone(restore)
                self.assertIsNone(self.fixture.button(window, 'Try again'))
                self.fixture.button(window, 'Review recovery options').click()
                self.fixture.pump(lambda: not window.running)
                self.assertEqual([argv[0] for argv in calls], ['uninstall', 'recover'])
                self.assertNotIn('--yes', calls[-1])
                window.close()

    def removal_window(self, *, failure=None, reason='root-access-required'):
        from cytv.recovery import removal_plan
        from cytv import cli

        fixture = self.fixture
        fixture.store.request_clean_removal(fixture.profile)
        fixture.store.checkpoint(fixture.profile, stage='private-cleanup', removal_reason=reason)
        window = fixture.window()
        calls = []

        def runner(argv, **kwargs):
            calls.append(argv)
            if len(calls) == 1:
                if failure:
                    kwargs['write'].failure_help(failure)
                removal_plan(kwargs['write'], fixture.store, fixture.profile, failure=failure,
                             evidence={'stock':'routing-verified', 'packages':'absent', 'cleanup':'pending'})
                return 2
            def connect(profile, directory, secret, trust, *, persist=True):
                self.assertFalse(persist)
                self.assertFalse(trust('replacement fingerprint', True))
                return fixture.connect(profile)
            return cli.main(argv + ['--data-dir', str(fixture.root)], payload_root=fixture.payload,
                            connect=connect, **kwargs)

        window.run = runner
        window.start('uninstall', fixture.profile)
        fixture.pump(lambda: not window.running)
        return window, calls

    def save_root_connection(self, host=None, port=2222):
        from paramiko import RSAKey
        from cytv.state import target

        profile = target(host or self.fixture.profile['host'], 'root', port,
                         self.fixture.root / 'root.key', root_variant='node012-beta')
        self.fixture.store.save(profile)
        path = self.fixture.store.device_path(profile) / 'known_hosts'
        key = RSAKey.generate(1024)
        path.write_text(f"[{profile['host']}]:{port} {key.get_name()} {key.get_base64()}\n")
        return profile, path

    def test_verified_access_requirement_uses_the_saved_root_connection(self):
        profile, _ = self.save_root_connection()
        self.save_root_connection(host='192.0.2.12')
        window, calls = self.removal_window()
        self.assertIn('Root access', window.subtitle.text())
        self.assertIn('Clean Your TV packages are absent.', window.subtitle.text())
        self.assertIn('Final cleanup remains to be verified.', window.subtitle.text())
        self.fixture.button(window, 'Connect using Root').click()
        self.fixture.pump(lambda: window.pending is not None)
        self.assertEqual(window.pending.title, 'Restore LG Home and remove this edition?')
        self.assertEqual(self.fixture.connections, [])
        self.assertIn('--removal-pin', calls[-1])

        with (patch('cytv.root_runtime.select_payload', return_value=(self.fixture.payload, self.fixture.manifest)),
              patch('cytv.operations.Installer.continue_clean_removal',
                    return_value={'verified_clean':True, 'removed':True}) as remove):
            window.submit('y')
            self.fixture.pump(lambda: not window.running)
        self.assertEqual(self.fixture.connections, [profile])
        remove.assert_called_once()
        self.assertEqual(window.title.text(), 'Clean Your TV removal is verified.')

    def test_missing_or_ambiguous_root_connection_leaves_cleanup_incomplete(self):
        for situation in ('other-tv', 'unpinned', 'multiple'):
            with self.subTest(situation=situation):
                if situation == 'other-tv':
                    self.save_root_connection(host='192.0.2.12')
                elif situation == 'unpinned':
                    _, pin = self.save_root_connection()
                    pin.unlink()
                else:
                    self.save_root_connection()
                    self.save_root_connection(port=3333)
                window, calls = self.removal_window()
                self.assertIsNone(self.fixture.button(window, 'Connect using Root'))
                self.assertIsNotNone(self.fixture.button(window, 'Review recovery options'))
                self.assertIn('Without existing Root access, cleanup remains incomplete.', window.subtitle.text())
                self.assertEqual(len(calls), 1)

    def test_changed_saved_root_pin_stops_before_sign_in(self):
        profile, pin = self.save_root_connection()
        window, _ = self.removal_window()
        pin.write_text('replacement')
        self.fixture.button(window, 'Connect using Root').click()
        self.fixture.pump(lambda: window.pending is not None)
        window.submit('y')
        self.fixture.pump(lambda: not window.running)
        self.assertEqual(self.fixture.connections, [])
        self.assertIsNone(self.fixture.store.pending(profile))

    def test_retryable_connection_interruption_does_not_offer_root(self):
        self.save_root_connection()
        window, _ = self.removal_window(failure={'code':'ssh-timeout', 'title':'Connection timed out',
                                                'next_step':'Retry the connection.', 'detail':'The connection was interrupted.'})
        self.assertIsNotNone(self.fixture.button(window, 'Try again'))
        self.assertIsNone(self.fixture.button(window, 'Connect using Root'))
        self.assertNotIn('Root access', window.subtitle.text())
        self.assertEqual(self.fixture.connections, [])

    def test_existing_root_access_review_keeps_custom_connection(self):
        from PySide6.QtWidgets import QLineEdit
        profile = dict(self.fixture.profile, edition='root', port=2222, root_variant='node012-beta')
        calls = []
        def runner(argv, **kwargs):
            calls.append(argv)
            kwargs['write'].recovery(profile)
            kwargs['write'].recovery_plan({'state':'blocked','disposition':'clean-removal',
                'summary':'Removal is not finished yet.','next_step':'Review recovery options',
                'reason':'root-access-required','actions':['continue-removal'],
                'removal_action':{'action':'connect-root','condition':'access','requires_change':True}})
            return 1
        window = self.fixture.window()
        window.run = runner
        window.start('uninstall', profile)
        self.fixture.pump(lambda: not window.running)
        self.assertIsNone(self.fixture.button(window, 'Connect using Root'))
        self.fixture.button(window, 'Connection details').click()
        self.assertTrue(all(field.isReadOnly() for field in window.findChildren(QLineEdit)))
        self.fixture.button(window, 'Review recovery options').click()
        self.fixture.pump(lambda: not window.running)
        self.assertEqual(calls[-1][0], 'recover')
        self.assertEqual(calls[-1][calls[-1].index('--port') + 1], '2222')
        self.assertEqual(calls[-1][calls[-1].index('--root-variant') + 1], 'node012-beta')
        self.assertNotIn('--yes', calls[-1])
