"""Offline widget checks; never connect to a TV."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
import time
import unittest
from unittest.mock import patch
from pathlib import Path
try:
    from PySide6.QtWidgets import QApplication, QPushButton, QLineEdit, QComboBox, QRadioButton, QDialog
    from cytv.gui import Wizard
    from cytv.desktop import Prompt
    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, 'Desktop build dependencies are optional for CLI tests')
class GuiTests(unittest.TestCase):
    def test_check_results_survive_error_steps_and_reset_at_home(self):
        w = Wizard()
        self.addCleanup(w.close)
        self.assertTrue(hasattr(w, 'check_panel'), 'Checks need a persistent visible panel')
        for name, status in [('ssh', 'pass'), ('python3', 'fail'), ('TV Node.js 8+', 'fail'), ('pairing', 'pending')]:
            w.receive('check', {'id': name, 'label': name, 'status': status, 'detail': '<private>'})
        w.receive('step', (4, 'Installing', True))
        w.receive('done', 2)
        self.assertFalse(w.check_panel.isHidden())
        text = w.check_panel.toPlainText()
        self.assertIn('Passed', text)
        self.assertIn('Failed', text)
        self.assertIn('Not checked', text)
        self.assertIn('Node.js 8+', w.subtitle.text(), 'Failed requirement must be visible without scrolling')
        self.assertIn('&lt;private&gt;', w.check_panel.toHtml())
        w.home()
        self.assertTrue(w.check_panel.isHidden())
        self.assertEqual(w.check_panel.toPlainText(), '')

    def test_error_text_is_red_and_escaped_without_coloring_progress(self):
        w = Wizard()
        self.addCleanup(w.close)
        w.content.clear()
        w.receive('text', 'Normal progress')
        w.receive('error-heading', 'Could not complete this step')
        w.receive('error', 'Failure <details>')
        markup = w.content.toHtml().lower()
        self.assertIn('#ff6b6b', markup)
        self.assertIn('failure &lt;details&gt;', markup)
        self.assertIn('Normal progress', w.content.toPlainText())
        w.receive('done', 2)
        self.assertEqual(w.title.property('state'), 'error')
        w.home()
        self.assertEqual(w.title.property('state'), '')

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from cytv import i18n
        self.addCleanup(i18n.set_language, 'en')
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        prefs = patch('cytv.state.default_dir', return_value=Path(self.directory.name))
        prefs.start()
        self.addCleanup(prefs.stop)
        languages = patch('cytv.i18n.system_languages', return_value=['en'])
        languages.start()
        self.addCleanup(languages.stop)

    def test_maintenance_is_disclosed_and_resets_on_home(self):
        w = Wizard()
        w.show()
        self.assertTrue(w.maintenance.isHidden())
        w.maintenance_toggle.click()
        self.assertFalse(w.maintenance.isHidden())
        w.home()
        self.assertTrue(w.maintenance.isHidden())
        self.assertFalse(w.maintenance_toggle.isChecked())
        w.close()

    def test_select_popup_has_no_light_bands(self):
        from cytv.gui_style import Select, STYLE
        self.app.setStyle('Fusion')
        select = Select()
        self.addCleanup(select.close)
        select.setStyleSheet(STYLE)
        select.addItems(['Automatic', 'English', 'Русский'])
        select.show()
        for _ in range(2):
            select.showPopup()
            self.app.processEvents()
            image = select.view().window().grab().toImage()
            for y in (2, image.height() - 3):
                self.assertLess(image.pixelColor(image.width() // 2, y).lightness(), 80)
            select.hidePopup()

    def test_maintenance_buttons_dispatch_selected_command_and_keep_action_visible(self):
        for index, (command, title) in enumerate([
                ('status', 'Check TV status'),
                ('doctor', 'Check connection and create a diagnostic report'),
                ('restore', 'Return to LG Home'),
                ('uninstall', 'Uninstall Clean Your TV'),
                ('home-diagnostics', 'Home button diagnostics'),
                ('enable-system-updates', 'Enable updates for all TV components (root required)'),
                ('clean-wam-cache', 'Clear WAM caches (root required)')]):
            with self.subTest(command=command):
                calls = []
                def runner(argv, **kwargs):
                    calls.append(argv)
                    kwargs['write'].step(2, 'Choose how you normally connect to this TV.')
                    kwargs['ask']('TV IP address: ')
                    return 0
                w = Wizard(run=runner)
                self.addCleanup(w.close)
                w.maintenance_toggle.click()
                w.maintenance.findChild(QComboBox).setCurrentIndex(index)
                w.maintenance.findChild(QPushButton).click()
                self.pump(lambda: w.pending is not None)
                self.assertEqual(calls[0][0], command)
                self.assertEqual('--report' in calls[0], command == 'doctor')
                actual_title, actual_badge = w.title.text(), w.badge.text()
                w.submit(None)
                self.pump(lambda: not w.running)
                self.assertEqual(actual_title, title)
                self.assertEqual(actual_badge, 'Maintenance action')
                self.assertTrue(w.steps.isHidden())
                w.close()

    def test_steps_follow_events_without_marking_failed_install_complete(self):
        w = Wizard()
        w.receive('step', (3, 'Prepare the TV connection', True))
        self.assertEqual([row.property('state') for row in w.step_rows],
                         ['complete', 'complete', 'current', 'upcoming'])
        w.receive('done', 1)
        self.assertEqual(w.step_rows[2].property('state'), 'error')
        self.assertEqual(w.step_rows[3].property('state'), 'upcoming')
        w.home()
        self.assertTrue(all(row.property('state') == 'upcoming' for row in w.step_rows))
        w.close()

    def test_edition_cards_keep_default_and_submit_selected_machine_key(self):
        w = Wizard()
        from cytv.desktop import Channel
        w.channel = Channel(lambda *args: None)
        w.show_prompt(Prompt('Edition [2]: ', [('1', 'No-root', 'For a TV without root. Uses LG Developer Mode.'),
                                               ('2', 'Root', 'For an already rooted TV with existing SSH access.')]))
        cards = w.form.findChildren(QRadioButton)
        self.assertEqual(len(cards), 2)
        self.assertTrue(cards[1].isChecked())
        cards[0].click()
        next(b for b in w.form.findChildren(QPushButton) if b.isDefault()).click()
        self.assertEqual(w.channel.answers.get_nowait(), '1')
        w.close()

    def test_language_selection_rerenders_and_persists_all_locales(self):
        from cytv import i18n
        w = Wizard()
        for code in i18n.LANGUAGES:
            w.language.setCurrentIndex(list(i18n.LANGUAGES).index(code))
            self.assertEqual(i18n.language_choice(), code)
            self.assertEqual(i18n.configure(), i18n.resolve_language(code))
            if code not in ('en', 'auto'):
                self.assertNotEqual(w.title.text(), 'Make your TV feel like yours')
        w.close()

    def test_chinese_fonts_follow_startup_and_language_changes(self):
        from PySide6.QtGui import QFontDatabase, QTextLayout
        from cytv import i18n
        from cytv.gui_style import STYLE
        fonts = Path(__file__).resolve().parents[2] / 'launcher/fonts'
        for name in ('SC', 'TC'):
            self.assertGreaterEqual(QFontDatabase.addApplicationFont(str(fonts / ('NotoSans%s.ttf' % name))), 0)
        i18n.configure('zh-Hant')
        w = Wizard()
        self.addCleanup(w.close)
        w.show()
        self.app.processEvents()

        def rendered_family():
            layout = QTextLayout('中文', w.title.font())
            layout.beginLayout()
            layout.createLine()
            layout.endLayout()
            return {run.rawFont().familyName() for run in layout.glyphRuns()}

        self.assertEqual(rendered_family(), {'Noto Sans TC'})
        for code, family in [('zh-Hans', 'Noto Sans SC'), ('zh-Hant', 'Noto Sans TC')]:
            w.language.setCurrentIndex(list(i18n.LANGUAGES).index(code))
            self.app.processEvents()
            self.assertEqual(rendered_family(), {family})
        w.language.setCurrentIndex(list(i18n.LANGUAGES).index('en'))
        self.assertEqual(w.styleSheet(), STYLE)
        w.close()
        i18n.configure('auto')
        with patch('cytv.i18n.system_languages', return_value=['zh-TW']):
            w = Wizard()
        self.addCleanup(w.close)
        w.show()
        self.app.processEvents()
        self.assertEqual(rendered_family(), {'Noto Sans TC'})

    def test_translated_secret_and_confirmation_keep_semantics(self):
        from cytv import i18n
        w = Wizard()
        w.language.setCurrentIndex(list(i18n.LANGUAGES).index('ru'))
        w.show_prompt(Prompt('Connect and remember this TV? [Y/n]: '))
        self.assertTrue(any(b.isDefault() and 'Подключиться' in b.text() for b in w.form.findChildren(QPushButton)))
        w.show_prompt(Prompt('SSH key passphrase: ', secret=True))
        self.assertEqual(w.form.findChild(QLineEdit).echoMode(), QLineEdit.EchoMode.Password)
        w.close()

    def test_secret_prompt_separates_current_guidance_from_collapsed_history(self):
        w = Wizard()
        self.addCleanup(w.close)
        w.show()
        w.receive('text', 'Earlier setup instruction')
        w.show_prompt(Prompt('Developer Mode passphrase: ', secret=True))
        self.app.processEvents()
        self.assertNotIn('Earlier setup instruction', w.content.toPlainText())
        self.assertIn('six characters', w.content.toPlainText())
        self.assertIn('Key Server', w.content.toPlainText())
        self.assertIn('Earlier setup instruction', w.details.toPlainText())
        self.assertTrue(w.details.isHidden())
        w.details_toggle.click()
        self.assertFalse(w.details.isHidden())
        self.assertEqual(w.form.findChild(QLineEdit).echoMode(), QLineEdit.EchoMode.Password)

    def test_preparation_pages_do_not_answer_connection_confirmation(self):
        from cytv.desktop import Channel
        w = Wizard()
        self.addCleanup(w.close)
        w.channel = Channel(lambda *args: None)
        w.receive('step', (3, 'Prepare the TV connection', True))
        for heading, text in [('1. Developer Mode', 'Install the app'),
                              ('2. Dev Mode Status', 'Restart the TV'),
                              ('3. Key Server', 'Leave the app open')]:
            w.receive('heading', heading)
            w.receive('text', text)
        w.receive('step', (4, 'Review and install', False))
        w.receive('text', 'TV: 192.0.2.10')
        prompt = Prompt('Connect to check installed versions? [Y/n]: ')
        w.show_prompt(prompt)
        self.assertIn('Install the app', w.content.toPlainText())
        self.assertNotIn('Restart the TV', w.content.toPlainText())
        self.assertTrue(w.channel.answers.empty())
        def click_default():
            next(b for b in w.form.findChildren(QPushButton) if b.isDefault()).click()
        click_default()
        self.assertIn('Restart the TV', w.content.toPlainText())
        next(b for b in w.form.findChildren(QPushButton) if b.text() == 'Back').click()
        self.assertIn('Install the app', w.content.toPlainText())
        for _ in range(3):
            click_default()
        self.assertIn('TV: 192.0.2.10', w.content.toPlainText())
        self.assertTrue(w.channel.answers.empty())
        self.assertEqual(w.pending, prompt)
        click_default()
        self.assertEqual(w.channel.answers.get_nowait(), 'y')

    def test_example_viewer_keeps_dark_theme_and_does_not_answer_password_prompt(self):
        from cytv.desktop import Channel
        w = Wizard()
        self.addCleanup(w.close)
        w.channel = Channel(lambda *args: None)
        prompt = Prompt('Developer Mode passphrase: ', secret=True)
        w.show_prompt(prompt)
        w.show_reference('key-server')
        self.app.processEvents()
        viewer = w.findChild(QDialog)
        self.assertTrue(viewer.isVisible())
        self.assertTrue(viewer.isModal())
        self.assertLess(viewer.grab().toImage().pixelColor(2, 2).lightness(), 80)
        viewer.reject()
        self.assertEqual(w.pending, prompt)
        self.assertTrue(w.channel.answers.empty())

    def test_failed_language_save_keeps_visible_and_active_selection(self):
        from cytv import i18n
        w = Wizard()
        old_index = w.language.currentIndex()
        old_title = w.title.text()
        with patch('cytv.state.private_write', side_effect=OSError('read only')), patch.object(w, 'error_dialog'):
            w.language.setCurrentIndex(list(i18n.LANGUAGES).index('ru'))
        self.assertEqual(w.language.currentIndex(), old_index)
        self.assertEqual(i18n.language_choice(), 'auto')
        self.assertEqual(i18n.resolved_language(), 'en')
        self.assertEqual(w.title.text(), old_title)
        w.close()

    def pump(self, predicate):
        deadline = time.monotonic() + 3
        while not predicate() and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.005)
        self.assertTrue(predicate())

    def test_worker_prompt_and_completion(self):
        answers = []
        def runner(argv, ask, secret, write):
            write.step(2, 'Choose your edition')
            write.option(1, 'No-root')
            write.option(2, 'Root')
            answers.append(ask('Edition [2]: '))
            answers.append(secret('Password: '))
            write.heading('Root is ready')
            return 0
        w = Wizard(run=runner)
        w.start('install')
        self.pump(lambda: w.pending is not None)
        cards = w.form.findChildren(QRadioButton)
        self.assertTrue(cards[1].isChecked())
        next(b for b in w.form.findChildren(QPushButton) if b.isDefault()).click()
        self.pump(lambda: w.pending is not None)
        self.assertEqual(w.form.findChild(QLineEdit).echoMode(), QLineEdit.EchoMode.Password)
        w.submit('private-password')
        self.pump(lambda: not w.running)
        self.assertEqual(answers, ['2', 'private-password'])
        self.assertNotIn('private-password', w.content.toPlainText())
        self.assertIn('Root is ready', w.content.toPlainText())
        w.close()

    def test_close_cancels_prompt_without_killing_worker(self):
        def runner(argv, ask, secret, write):
            try:
                ask('TV IP address: ')
            except EOFError:
                write('Cancelled. No TV changes were made.')
                return 130
        w = Wizard(run=runner)
        w.start('install')
        self.pump(lambda: w.pending is not None)
        w.close()
        self.pump(lambda: not w.running)
        self.assertEqual(w.title.text(), 'Cancelled')
        w.close()

    def test_real_cli_cancel_never_connects(self):
        from cytv.cli import main
        with tempfile.TemporaryDirectory() as directory:
            def runner(argv, **kwargs):
                return main(argv + ['--data-dir', directory], search=lambda: [], **kwargs)
            w = Wizard(run=runner)
            w.start('install')
            self.pump(lambda: w.pending is not None)
            w.submit(None)
            self.pump(lambda: not w.running)
            self.assertEqual(w.title.text(), 'Cancelled')
            w.close()

    def test_destructive_confirm_focuses_no(self):
        w = Wizard()
        w.show_prompt(Prompt('Continue [y/N]: '))
        buttons = w.form.findChildren(QPushButton)
        defaults = [b.text() for b in buttons if b.isDefault()]
        self.assertEqual(defaults, ['No, go back / cancel this operation'])
        w.close()
