"""Command dispatch follows the advisory policy without changing backend authority."""
import unittest
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
