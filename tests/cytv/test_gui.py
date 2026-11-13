"""Offline widget checks; never connect to a TV."""
import os
import sys
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
import time
import unittest
from unittest.mock import patch
from pathlib import Path
try:
    from PySide6.QtWidgets import QApplication, QPushButton, QLineEdit, QComboBox, QRadioButton, QDialog, QLabel, QScrollArea, QCheckBox
    from cytv.gui import Wizard
    from cytv.desktop import Prompt
    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, 'Desktop build dependencies are optional for CLI tests')
class GuiTests(unittest.TestCase):
    def test_debloat_restoration_defaults_to_skip_without_cancelling_removal(self):
        from cytv import debloat, i18n
        from cytv.desktop import Channel

        i18n.set_language('en')
        wizard = Wizard()
        self.addCleanup(wizard.close)
        wizard.command = 'uninstall'
        wizard.operation_title = 'Uninstall Clean Your TV'
        wizard.channel = Channel(wizard.receive)
        wizard.channel.console.step(1, 'Debloat restoration preview')
        wizard.channel.console('Sponsored tiles — Off → On')
        wizard.show_prompt(Prompt(debloat.RESTORE_PROMPT + ' [y/N]: '))
        self.assertIn('Sponsored tiles — Off → On', wizard.content.toPlainText())
        buttons = {button.text(): button for button in wizard.form.findChildren(QPushButton)}
        self.assertTrue(buttons[debloat.SKIP_RESTORE].isDefault())
        buttons[debloat.SKIP_RESTORE].click()
        self.assertEqual(wizard.channel.answers.get_nowait(), 'n')

    def test_final_customization_prefills_existing_name_validates_and_submits(self):
        import json
        from cytv import i18n
        from cytv.desktop import Channel
        from cytv.install_settings import PROMPT
        w=Wizard();self.addCleanup(w.close)
        i18n.set_language('en')
        w.channel=Channel(lambda *_:None)
        w.selected_profile = {'edition': 'root'}
        w.receive('installation-settings', {'tv_name':'Existing'})
        w.show_prompt(Prompt(PROMPT))
        entry=w.form.findChild(QLineEdit,'tvName')
        self.assertEqual(entry.placeholderText(),'Existing')
        self.assertEqual(entry.text(), '')
        submit=next(button for button in w.form.findChildren(QPushButton) if button.text()=='Continue')
        submit.click()
        self.assertNotIn('tv_name', json.loads(w.channel.answers.get_nowait()))
        w.show_prompt(Prompt(PROMPT))
        entry = w.form.findChild(QLineEdit, 'tvName')
        submit = next(button for button in w.form.findChildren(QPushButton) if button.text() == 'Continue')
        entry.setText('x'*49);submit.click()
        self.assertTrue(w.channel.answers.empty())
        self.assertTrue(w.form.findChild(QLabel,'tvNameError').text())
        entry.setText('Aashiyaan');submit.click()
        self.assertEqual(json.loads(w.channel.answers.get_nowait())['tv_name'],'Aashiyaan')

    def test_debloat_group_selection_and_results(self):
        import json
        from PySide6.QtGui import QColor, QPalette
        from cytv import debloat, i18n
        from cytv.desktop import Channel
        from cytv.gui_style import ToggleSwitch
        w = Wizard()
        self.addCleanup(w.close)
        i18n.set_language('en')
        palette = w.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor('white'))
        w.setPalette(palette)
        w.channel = Channel(lambda *_: None)
        w.receive('step', (5, debloat.TITLE, True))
        w.show_prompt(Prompt(debloat.SELECT))
        w.resize(900, 680)
        w.show()
        self.app.processEvents()
        self.assertTrue(w.reading.isHidden())
        for name in w.step_names:
            self.assertGreaterEqual(name.height(), name.heightForWidth(name.width()), name.text())
        scroll = w.form.findChild(QScrollArea, 'debloatSelection')
        self.assertLessEqual(scroll.widget().width(), scroll.viewport().width())
        self.assertLess(scroll.viewport().grab().toImage().pixelColor(1, 1).lightness(), 100)
        toggles = w.form.findChildren(ToggleSwitch)
        self.assertEqual(len(toggles), 14)
        self.assertTrue(all(toggle.isChecked() for toggle in toggles))
        section = w.form.findChild(ToggleSwitch, 'debloatGroup-homePromotion')
        section.click()
        field = w.form.findChild(ToggleSwitch, 'debloat-contentRecommendation')
        self.assertFalse(field.isChecked())
        section.click()
        self.assertTrue(field.isChecked())
        field.click()
        self.assertEqual(section.accessibleDescription(), 'Some selected')
        next(b for b in w.form.findChildren(QPushButton) if b.text() == 'Continue').click()
        self.assertEqual(json.loads(w.channel.answers.get_nowait()),
                         [key for key in debloat.SETTINGS if key != 'contentRecommendation'])
        w.receive('debloat-results', {'homePromotion': 'unverified', 'aiNudge': 'firmware-blocked'})
        w.show_prompt(Prompt(debloat.REVIEW))
        self.assertFalse(w.reading.isHidden())
        self.assertIn('The result could not be verified.', w.content.toPlainText())
        self.assertIn('This TV firmware blocks changing this setting in No-root.', w.content.toPlainText())
        self.app.processEvents()
        icon = w.content.document().find('✓')
        label = w.content.document().find('Turn off sponsored tiles')
        icon.setPosition(icon.selectionStart())
        label.setPosition(label.selectionStart())
        self.assertLess(w.content.cursorRect(label).left() - w.content.cursorRect(icon).left(), 56)
        next(b for b in w.form.findChildren(QPushButton) if b.text() == debloat.CONTINUE).click()
        self.assertEqual(w.channel.answers.get_nowait(), '1')

    def test_setup_explanations_do_not_overlap_at_minimum_window_size(self):
        from cytv import i18n, install_settings as settings
        w = Wizard()
        self.addCleanup(w.close)
        i18n.set_language('ru')
        self.addCleanup(i18n.set_language, 'en')
        w.resize(900, 680)
        w.selected_profile = {'edition': 'root'}
        w.show_prompt(Prompt(settings.PROMPT))
        w.show()
        self.app.processEvents()
        scroll = w.form.findChild(QScrollArea, 'installationSettings')
        self.assertIsNotNone(scroll)
        self.assertLessEqual(scroll.widget().width(), scroll.viewport().width())
        items = [scroll.widget().layout().itemAt(i).widget() for i in range(scroll.widget().layout().count())
                 if scroll.widget().layout().itemAt(i).widget() is not None]
        for first, second in zip(items, items[1:]):
            self.assertLess(first.geometry().bottom(), second.geometry().top())

    def test_setup_form_filters_mode_and_disables_weather_for_ribbon(self):
        import json
        from cytv.gui_style import ThemeCard, ToggleSwitch
        from cytv.desktop import Channel
        from cytv import install_settings as settings
        for profile, specific, absent in [
            ({'edition': 'root'}, 'block_updates', 'renewal'),
            ({'edition': 'no-root'}, 'renewal', 'block_updates'),
            ({'edition': 'no-root', 'connection': 'root-ssh'}, None, 'renewal')
        ]:
            w = Wizard()
            self.addCleanup(w.close)
            w.channel = Channel(lambda *_: None)
            w.selected_profile = profile
            w.receive('installation-settings', {specific: False} if specific else {})
            w.show_prompt(Prompt(settings.PROMPT))
            cards = w.form.findChildren(ThemeCard)
            self.assertEqual([card.key for card in cards], ['classic', 'liquid-glass', 'ribbon'])
            self.assertTrue(all(not card.preview.isNull() for card in cards))
            weather = w.form.findChild(ToggleSwitch, 'weather')
            weather.setChecked(True)
            cards[2].click()
            self.assertFalse(weather.isEnabled())
            self.assertFalse(weather.isChecked())
            self.assertIsNone(w.form.findChild(ToggleSwitch, absent))
            if specific:
                toggle = w.form.findChild(ToggleSwitch, specific)
                self.assertFalse(toggle.isTristate())
                toggle.click()
            next(b for b in w.form.findChildren(QPushButton) if b.text() == 'Continue').click()
            answer = json.loads(w.channel.answers.get_nowait())
            self.assertEqual(answer['theme'], 'ribbon')
            self.assertFalse(answer['weather'])
            if specific:
                self.assertTrue(answer[specific])

    def test_setup_switch_preserves_current_value_and_allows_explicit_off(self):
        import json
        from cytv.gui_style import ToggleSwitch
        from cytv.desktop import Channel
        from cytv import install_settings as settings
        for change in (False, True):
            w = Wizard()
            self.addCleanup(w.close)
            w.channel = Channel(lambda *_:None)
            w.selected_profile = {'edition':'root'}
            w.receive('installation-settings', {'block_updates':True})
            w.show_prompt(Prompt(settings.PROMPT))
            toggle = w.form.findChild(ToggleSwitch, 'block_updates')
            self.assertTrue(toggle.isChecked())
            if change: toggle.click()
            next(b for b in w.form.findChildren(QPushButton) if b.text()=='Continue').click()
            value = json.loads(w.channel.answers.get_nowait())
            if change: self.assertIs(value['block_updates'],False)
            else: self.assertNotIn('block_updates',value)

    def test_theme_cards_and_switch_work_from_keyboard(self):
        from PySide6.QtTest import QTest
        from PySide6.QtCore import Qt
        from cytv.gui_style import ThemeCard, ToggleSwitch
        from cytv import install_settings as settings
        w=Wizard();self.addCleanup(w.close)
        w.selected_profile={'edition':'no-root','connection':'root-ssh'}
        w.show_prompt(Prompt(settings.PROMPT));w.show();self.app.processEvents()
        cards=w.form.findChildren(ThemeCard)
        cards[0].setFocus()
        QTest.keyClick(cards[0],Qt.Key.Key_Right)
        self.assertTrue(cards[1].isChecked())
        switch=w.form.findChild(ToggleSwitch,'weather')
        switch.setFocus();QTest.keyClick(switch,Qt.Key.Key_Space)
        self.assertTrue(switch.isChecked())

    def test_unreadable_mode_state_cannot_be_submitted_as_off(self):
        import json
        from cytv.gui_style import ToggleSwitch
        from cytv.desktop import Channel
        from cytv import install_settings as settings
        w=Wizard();self.addCleanup(w.close)
        w.channel=Channel(lambda *_:None);w.selected_profile={'edition':'root'}
        w.show_prompt(Prompt(settings.PROMPT))
        self.assertFalse(w.form.findChild(ToggleSwitch,'block_updates').isEnabled())
        next(b for b in w.form.findChildren(QPushButton) if b.text()=='Continue').click()
        self.assertNotIn('block_updates',json.loads(w.channel.answers.get_nowait()))

    def test_default_wizard_runs_update_gate_before_payload_or_tv_changes(self):
        from cytv import installer_update as update
        w=Wizard()
        self.addCleanup(w.close)
        with patch('cytv.cli.choose_profile',return_value={'host':'192.0.2.1','edition':'root','port':22}), patch.object(update,'latest',return_value='0.15.0'), patch('cytv.package.verify_payload') as payload, patch('cytv.gui.QDesktopServices.openUrl',return_value=True):
            w.start('install')
            deadline=time.monotonic()+3
            while not w.pending and time.monotonic()<deadline:
                self.app.processEvents()
                time.sleep(.01)
            self.assertIsNotNone(w.pending)
            self.assertEqual(w.pending.label,update.PROMPT)
            next(b for b in w.form.findChildren(QPushButton) if b.text()==update.DOWNLOAD).click()
            w.worker.join(timeout=3)
            self.assertFalse(w.worker.is_alive())
            self.app.processEvents()
            payload.assert_not_called()
            self.assertIn('Installation has not started.',w.content.toPlainText())

    def test_installer_update_has_two_direct_actions_and_no_implicit_install(self):
        from cytv.desktop import Channel
        from cytv import installer_update as update
        for action, answer in [('Open GitHub and download the latest version', '1'), ('No, install this version', '2')]:
            w=Wizard()
            self.addCleanup(w.close)
            w.channel=Channel(lambda *_:None)
            with patch('cytv.gui.QDesktopServices.openUrl',return_value=True) as browser:
                w.show_prompt(Prompt(update.PROMPT,[('1',update.DOWNLOAD,''),('2',update.CONTINUE,'')]))
                self.assertFalse(w.form.findChildren(QComboBox))
                buttons=w.form.findChildren(QPushButton)
                self.assertFalse(any(b.isDefault() for b in buttons if b.text()==update.CONTINUE))
                next(b for b in buttons if b.text()==action).click()
                self.assertEqual(w.channel.answers.get_nowait(),answer)
                self.assertEqual(browser.called,answer=='1')

    def test_runtime_alternatives_are_visible_direct_actions_with_separate_cancel(self):
        from cytv import i18n
        from cytv.desktop import Channel
        from cytv.root_runtime import NOTICE, NO_ROOT_TITLE, NO_ROOT_DETAIL, BETA_TITLE
        for language in ('en', 'ru', 'de'):
            for choice, action in (('1', 'Install No-root'), ('2', 'Try Root Beta'), ('0', 'Cancel')):
                with self.subTest(language=language, choice=choice):
                    w=Wizard()
                    self.addCleanup(w.close)
                    i18n.set_language(language)
                    w.channel=Channel(lambda *_:None)
                    w.show_prompt(Prompt('Alternative edition [0]: ',[
                        ('1',NO_ROOT_TITLE,NO_ROOT_DETAIL),('2',BETA_TITLE,NOTICE),('0','Cancel','')]))
                    self.assertFalse(w.form.findChildren(QComboBox),'Alternatives must be visible without opening a list')
                    buttons=w.form.findChildren(QPushButton)
                    self.assertFalse(any(button.text()==i18n.translate('Continue') for button in buttons))
                    selected=next(button for button in buttons if button.text()==i18n.translate(action))
                    cancel=next(button for button in buttons if button.text()==i18n.translate('Cancel'))
                    self.assertTrue(cancel.isDefault())
                    self.assertTrue(all(not button.isDefault() for button in buttons if button!=cancel))
                    self.assertTrue(any(label.wordWrap() and label.text()==i18n.translate(NOTICE)
                                        for label in w.form.findChildren(QLabel)))
                    selected.click()
                    self.assertEqual(w.channel.answers.get_nowait(),choice)

    def test_runtime_alternative_without_beta_does_not_offer_beta_action(self):
        w=Wizard()
        self.addCleanup(w.close)
        w.show_prompt(Prompt('Alternative edition [0]: ',[
            ('1','Install No-root using existing root SSH','Uses Home and Home Helper. Developer Mode is not installed.'),
            ('0','Cancel','')]))
        self.assertFalse(w.form.findChildren(QComboBox))
        self.assertEqual(len(w.form.findChildren(QPushButton)),2)

    def test_beta_confirmation_names_the_action_and_cancel(self):
        from cytv.desktop import Channel
        for choice, action in (('y','Try Root Beta'),('n','Cancel')):
            w=Wizard()
            self.addCleanup(w.close)
            w.channel=Channel(lambda *_:None)
            w.show_prompt(Prompt('Install experimental Root Beta? [y/N]: '))
            button=next(button for button in w.form.findChildren(QPushButton) if button.text()==action)
            button.click()
            self.assertEqual(w.channel.answers.get_nowait(),choice)

    def test_runtime_choices_keep_full_descriptions_visible_in_all_languages(self):
        from cytv import i18n
        from cytv.root_runtime import NOTICE, NO_ROOT_TITLE, NO_ROOT_DETAIL, BETA_TITLE
        for language in set(i18n.LANGUAGES)-{'auto'}:
            with self.subTest(language=language):
                w=Wizard()
                self.addCleanup(w.close)
                i18n.set_language(language)
                w.preview.hide()
                w.resize(900,680)
                w.show_prompt(Prompt('Alternative edition [0]: ',[
                    ('1',NO_ROOT_TITLE,NO_ROOT_DETAIL),('2',BETA_TITLE,NOTICE),('0','Cancel','')]))
                w.show()
                for _ in range(3): self.app.processEvents()
                scroll=w.form.findChild(QScrollArea,'runtimeChoices')
                descriptions=[label for label in w.form.findChildren(QLabel) if label.objectName() in ('choiceDetail','promptTitle') and label.isVisible()]
                self.assertEqual(len(descriptions),4)
                for label in descriptions:
                    self.assertGreaterEqual(label.height(),label.heightForWidth(label.width()))
                    self.assertTrue(label.parentWidget().rect().contains(label.geometry()))
                    scroll.ensureWidgetVisible(label)
                    self.app.processEvents()
                    self.assertTrue(scroll.viewport().rect().contains(label.mapTo(scroll.viewport(),label.rect().bottomRight())))
                    for sibling in label.parentWidget().findChildren(QPushButton):
                        self.assertFalse(label.geometry().intersects(sibling.geometry()),'Choice text must not hide behind its action')
                for button in w.form.findChildren(QPushButton):
                    if button.parentWidget()!=w.form:
                        scroll.ensureWidgetVisible(button)
                        self.app.processEvents()
                    self.assertTrue(w.rect().contains(button.mapTo(w,button.rect().bottomRight())))
                w.close()

    def test_edition_switch_replaces_failed_root_checks_with_new_checks(self):
        w=Wizard()
        self.addCleanup(w.close)
        w.receive('check',{'id':'node-version','label':'TV Node.js 8+','status':'fail','detail':''})
        w.receive('selected-profile',{'host':'192.0.2.10','port':22,'edition':'no-root','connection':'root-ssh'})
        w.receive('check',{'id':'helper-node','label':'TV Node.js 0.10.15+','status':'pass','detail':''})
        self.assertNotIn('node-version',w.check_results)
        self.assertEqual(w.check_results['helper-node']['status'],'pass')
        self.assertNotIn('TV Node.js 8+',w.check_panel.toPlainText())

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

    def test_short_cleanup_result_shows_error_in_one_scrolling_area(self):
        from PySide6.QtCore import QPoint, QPointF, Qt
        from PySide6.QtGui import QWheelEvent
        from PySide6.QtTest import QTest

        w = Wizard()
        self.addCleanup(w.close)
        w.resize(900, 680)
        w.show()
        w.preview.hide()
        w.content.clear()
        w.command = 'uninstall'
        w.receive('recovery', {'host': '192.0.2.10', 'edition': 'no-root', 'port': 9922})
        w.receive('recovery-plan', {'state': 'blocked', 'disposition': 'clean-removal',
                                    'summary': 'Removal is still in progress.', 'actions': ['continue-removal'],
                                    'removal': {'stage': 'private-cleanup', 'reason': 'private-cleanup-incomplete'}})
        w.receive('check', {'id': 'ssh', 'label': 'SSH connection and sign-in', 'status': 'pass', 'detail': ''})
        for index in range(16):
            w.receive('text', f'Cleanup progress {index}')
        w.receive('error-heading', 'Could not complete this step')
        error = 'Some Clean Your TV files or settings remain. Choose Try again.'
        w.receive('error', error)
        report = Path(self.directory.name) / 'diagnostic.json'
        report.touch()
        w.receive('report', str(report))
        w.receive('text', 'Review the report.')
        w.receive('done', 2)
        self.app.processEvents()

        actions = {button.text(): button for button in w.form.findChildren(QPushButton)}
        self.assertEqual(actions['Save diagnostic report…'].y(), actions['Back to start'].y())
        heading = w.content.cursorRect(w.content.document().find('Could not complete this step'))
        message = w.content.cursorRect(w.content.document().find(error))
        self.assertTrue(w.content.viewport().rect().contains(heading.united(message)))
        reading = w.findChild(QScrollArea, 'wizardReading')
        self.assertIsNotNone(reading)
        for panel in (w.content, w.check_panel, w.details):
            self.assertTrue(reading.isAncestorOf(panel))
            self.assertFalse(panel.verticalScrollBar().isVisible())
        visible_error = w.content.viewport().mapTo(reading.viewport(), message.bottomLeft())
        self.assertTrue(reading.viewport().rect().contains(visible_error),
                        (visible_error, reading.viewport().rect(), message,
                         reading.verticalScrollBar().value(), w.content.toPlainText()))
        w.details_toggle.click()
        self.app.processEvents()
        self.assertGreater(reading.verticalScrollBar().maximum(), 0)
        self.assertGreater(reading.verticalScrollBar().value(), 0)
        self.assertFalse(w.details.isHidden())
        self.assertIn('Cleanup progress 0', w.details.toPlainText())
        self.assertEqual(w.details.verticalScrollBar().maximum(), 0)
        reading.verticalScrollBar().setValue(0)
        viewport = w.content.viewport()
        point = message.center()
        wheel = QWheelEvent(QPointF(point), QPointF(viewport.mapToGlobal(point)), QPoint(), QPoint(0, -120),
                            Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False)
        self.app.sendEvent(viewport, wheel)
        self.assertGreater(reading.verticalScrollBar().value(), 0)
        for panel in (w.content, w.check_panel, w.details):
            with self.subTest(panel=panel.accessibleName()):
                panel.setFocus()
                reading.verticalScrollBar().setValue(0)
                QTest.keyClick(panel, Qt.Key.Key_PageDown)
                self.assertGreater(reading.verticalScrollBar().value(), 0)
        for button in (w.cancel, w.details_toggle, *w.form.findChildren(QPushButton)):
            self.assertFalse(reading.isAncestorOf(button))
            position = button.mapTo(w, button.rect().bottomRight())
            self.assertTrue(w.rect().contains(position), button.text())
        w.details_toggle.click()
        self.app.processEvents()
        self.assertEqual(reading.verticalScrollBar().value(), 0)

    def test_live_progress_stays_visible_above_tall_checks(self):
        w = Wizard()
        self.addCleanup(w.close)
        w.resize(900, 680)
        w.show()
        w.preview.hide()
        w.content.clear()
        w.running = True
        self.addCleanup(setattr, w, 'running', False)
        for index in range(20):
            w.receive('check', {'id': str(index), 'label': f'TV check {index}',
                                'status': 'pass', 'detail': 'Completed'})
        self.app.processEvents()
        self.assertGreater(w.check_panel.height(), w.reading.viewport().height())
        self.assertEqual(w.reading.verticalScrollBar().value(), 0)

        for index in range(20):
            w.receive('text', f'Cleanup progress {index}')
            self.app.processEvents()
        w.receive('text', 'Checking the current cleanup state.')
        self.app.processEvents()
        cursor = w.content.document().find('Checking the current cleanup state.')
        position = w.content.viewport().mapTo(w.reading.viewport(), w.content.cursorRect(cursor).center())
        self.assertTrue(w.reading.viewport().rect().contains(position), position)
        w.reading.verticalScrollBar().setValue(0)
        w.receive('text', 'Cleanup is still running.')
        self.app.processEvents()
        self.assertEqual(w.reading.verticalScrollBar().value(), 0)

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

    def test_diagnostics_runs_explicit_multiline_command_on_selected_ssh_and_copies_output(self):
        from PySide6.QtWidgets import QPlainTextEdit
        from unittest.mock import Mock
        from cytv import cli, state
        from cytv.transport import CommandResult

        for edition, connection, username in (('root', None, 'root'),
                                              ('no-root', None, 'prisoner'),
                                              ('no-root', 'root-ssh', 'root')):
            with self.subTest(edition=edition, connection=connection):
                profile = state.target('192.0.2.10', edition, connection=connection)
                store = state.Store(Path(self.directory.name) / username / edition)
                store.save(profile)
                remote = Mock()
                remote.run_command.return_value = CommandResult('  <out>\n', 'error\n', 42, False)
                connect = Mock(return_value=remote)
                w = Wizard(run=lambda args, **kwargs: cli.main(
                    [*args, '--data-dir', str(store.root)], connect=connect, **kwargs))
                self.addCleanup(w.close)
                self.addCleanup(lambda window=w: window.submit(None) if window.running and window.pending else None)
                w.resize(900, 680)
                w.show()
                w.diagnostics_toggle.click()
                next(b for b in w.form.findChildren(QPushButton) if b.text() == 'Run SSH command').click()
                self.pump(lambda: w.findChild(QPlainTextEdit, 'sshCommandInput') is not None)
                editor = w.findChild(QPlainTextEdit, 'sshCommandInput')
                self.assertIn(f'{username}@192.0.2.10:{profile["port"]}', w.subtitle.text())
                run = next(b for b in w.form.findChildren(QPushButton) if b.text() == 'Run')
                self.assertFalse(run.isEnabled())
                self.app.processEvents()
                self.assertTrue(editor.isVisible())
                self.assertTrue(w.form.rect().contains(run.geometry()))
                command = "printf '<out>'\nprintf 'error' >&2\nexit 42"
                editor.setPlainText(command)
                remote.run_command.assert_not_called()
                run.click()
                self.pump(lambda: not w.running)
                connect.assert_called_once()
                self.assertEqual(connect.call_args.args[0], profile)
                remote.run_command.assert_called_once_with(command)
                remote.close.assert_called_once_with()
                output = w.findChild(QPlainTextEdit, 'sshCommandOutput')
                self.assertTrue(output.isReadOnly())
                next(b for b in w.form.findChildren(QPushButton) if b.text() == 'Copy output').click()
                copied = self.app.clipboard().text()
                self.assertEqual(copied, output.toPlainText())
                self.assertIn('stdout\n  <out>', copied)
                self.assertIn('stderr\nerror', copied)
                self.assertIn('Exit code: 42', copied)
                w.close()

    def test_maintenance_is_disclosed_and_resets_on_home(self):
        w = Wizard()
        self.addCleanup(w.close)
        w.show()
        self.app.processEvents()
        setup = next(button for button in w.form.findChildren(QPushButton) if button.isDefault())
        wallpaper = w.wallpapers_button
        maintenance = w.maintenance_toggle
        position = lambda button: button.mapTo(w.form, button.rect().topLeft())
        self.assertLess(position(setup).y() + setup.height(), position(wallpaper).y())
        self.assertEqual(position(wallpaper).y(), position(maintenance).y())
        self.assertGreater(setup.width(), wallpaper.width())
        self.assertGreaterEqual(maintenance.height(), 44)
        self.assertTrue(w.maintenance.isHidden())
        w.maintenance_toggle.click()
        self.assertFalse(w.maintenance.isHidden())
        self.assertTrue(w.content.isHidden(), 'Expanded maintenance replaces setup instructions so controls have room')
        w.resize(900, 680)
        self.app.processEvents()
        self.assertTrue(w.preview.isHidden())
        for control in (*w.maintenance.findChildren(QComboBox), *w.maintenance.findChildren(QPushButton)):
            self.assertTrue(w.maintenance.rect().contains(control.geometry()), 'Maintenance controls fit the smallest window')
        w.home()
        self.assertTrue(w.maintenance.isHidden())
        self.assertFalse(w.preview.isHidden())
        self.assertFalse(w.content.isHidden())
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
                ('recover', 'Review recovery options'),
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
                self.assertFalse(w.content.isHidden(), 'Operation instructions must be visible after expanded maintenance')
                self.assertEqual(calls[0][0], command)
                self.assertEqual('--report' in calls[0], command == 'doctor')
                actual_title, actual_badge = w.title.text(), w.badge.text()
                w.submit(None)
                self.pump(lambda: not w.running)
                self.assertEqual(actual_title, title)
                self.assertEqual(actual_badge, 'Maintenance action')
                self.assertTrue(w.steps.isHidden())
                w.close()

    def test_rollback_maintenance_retains_default_no_and_pending_guards(self):
        from unittest.mock import Mock
        from cytv import cli, state

        store = state.Store(self.directory.name)
        profile = state.target('192.0.2.10', 'root')
        store.save(profile)
        for command, option, method in (
                ('recover-root-rollback', False, 'recover_root_rollback'),
                ('recover-system-rollback', False, 'recover_system_rollback'),
                ('recover-system-rollback', True, 'recover_system_rollback')):
            for outcome in ('declined', 'confirmed', 'pending'):
                with self.subTest(command=command, new_attempt=option, outcome=outcome), \
                        patch('cytv.cli.Installer') as installer:
                    connect = Mock()
                    args = []

                    def runner(argv, **kwargs):
                        args.extend(argv)
                        return cli.main(argv, connect=connect, **kwargs)

                    w = Wizard(run=runner)
                    self.addCleanup(w.close)
                    w.maintenance_toggle.click()
                    choices = w.maintenance.findChild(QComboBox)
                    self.assertGreaterEqual(choices.findData(command), 0)
                    choices.setCurrentIndex(choices.findData(command))
                    rearm = w.maintenance.findChild(QCheckBox)
                    self.assertEqual(rearm.isHidden(), command != 'recover-system-rollback')
                    self.assertFalse(rearm.isChecked())
                    if option:
                        rearm.click()
                    if outcome == 'pending':
                        store.begin(profile, 'install')
                        self.addCleanup(store.device_dir(profile).joinpath('operation.json').unlink, missing_ok=True)
                    w.maintenance.findChild(QPushButton).click()
                    if outcome != 'pending':
                        self.pump(lambda: w.pending is not None)
                        self.assertEqual((w.pending.kind, w.pending.default), ('confirm', 'n'))
                        self.assertFalse(connect.called)
                        w.submit('y' if outcome == 'confirmed' else 'n')
                    self.pump(lambda: not w.running)
                    self.assertEqual('--new-recovery-attempt' in args, option)
                    self.assertNotIn('--yes', args)
                    recover = getattr(installer.return_value, method)
                    if outcome == 'confirmed':
                        recover.assert_called_once_with(**({'new_attempt': True} if option else {}))
                        connect.assert_called_once()
                    else:
                        recover.assert_not_called()
                        connect.assert_not_called()
                    installer.return_value.install.assert_not_called()
                    w.close()
                    if outcome == 'pending':
                        store.device_dir(profile).joinpath('operation.json').unlink()

    def test_debloat_maintenance_uses_setup_selection_and_saves_report(self):
        from unittest.mock import Mock
        from cytv import cli, debloat, state
        from cytv.gui_style import ToggleSwitch

        store = state.Store(self.directory.name)
        profile = state.target('192.0.2.10', 'root')
        store.save(profile)
        remote = Mock(root=True)
        remote.luna.side_effect = [
            {'returnValue': False},
            {'returnValue': True, 'settings': {'homePromotion': 'on'}},
            {'returnValue': True},
            {'returnValue': True, 'settings': {'homePromotion': 'off'}},
        ]
        w = Wizard(run=lambda argv, **kwargs: cli.main(argv, connect=lambda *_: remote, **kwargs))
        self.addCleanup(w.close)
        with patch('cytv.cli.Installer') as installer, patch('cytv.cli.package.verify_payload') as payload:
            w.maintenance_toggle.click()
            choices = w.maintenance.findChild(QComboBox)
            self.assertGreaterEqual(choices.findData('debloat'), 0)
            choices.setCurrentIndex(choices.findData('debloat'))
            w.maintenance.findChild(QPushButton).click()
            self.pump(lambda: w.pending is not None)
            self.assertEqual(w.pending.label, debloat.SELECT)
            self.assertTrue(w.steps.isHidden())
            toggles = w.form.findChildren(ToggleSwitch)
            self.assertTrue(toggles)
            self.assertTrue(all(not toggle.isChecked() for toggle in toggles))
            apply = next(b for b in w.form.findChildren(QPushButton) if b.text() == 'Apply selected settings')
            self.assertFalse(apply.isEnabled())
            group = w.form.findChild(ToggleSwitch, 'debloatGroup-homePromotion')
            group.click()
            self.assertTrue(apply.isEnabled())
            group.click()
            self.assertFalse(apply.isEnabled())
            w.form.findChild(ToggleSwitch, 'debloat-homePromotion').click()
            apply.click()
            self.pump(lambda: w.pending is not None)
            self.assertEqual(w.pending.label, debloat.REVIEW)
            self.assertIn('Successfully applied and verified', w.content.toPlainText())
            next(b for b in w.form.findChildren(QPushButton) if b.text() == 'Continue').click()
            self.pump(lambda: not w.running)
            self.assertIsNotNone(w.report)
            self.assertTrue(any(b.text() == 'Save diagnostic report…' for b in w.form.findChildren(QPushButton)))
            installer.assert_not_called()
            payload.assert_not_called()
            remote.upload.assert_not_called()

    def test_failed_home_interface_is_visible_before_passed_prerequisites(self):
        w=Wizard();self.addCleanup(w.close)
        for key,label,status in [('ssh','SSH connection and sign-in','pass'),('home-profiles','Root Home profile interface','fail')]:
            w.receive('check',{'id':key,'label':label,'status':status,'detail':''})
        text=w.check_panel.toPlainText()
        self.assertLess(text.index('Root Home profile interface'),text.index('SSH connection and sign-in'))

    def test_failure_help_preserves_missing_report_warning_and_does_not_retry(self):
        calls=[]
        w=Wizard(run=lambda *a,**k:calls.append(a));self.addCleanup(w.close)
        help={'code':'ssh-unreachable','title':'Check the TV connection','detail':'SSH was not verified.',
              'next_step':'Review the selected TV address and SSH port.','pending':False,'can_edit_connection':True}
        w.receive('failure-help',help);w.receive('done',1)
        self.assertEqual(w.title.text(),'Check the TV connection')
        self.assertIn('could not be created',w.subtitle.text())
        self.assertEqual(calls,[])
        w.home();self.assertIsNone(w.failure_help)

    def test_network_failure_actions_recheck_without_install_and_preserve_recovery(self):
        import errno
        from cytv.failure_help import for_error
        profile = {'host': '192.0.2.10', 'port': 22, 'edition': 'root'}
        calls = []
        w = Wizard(run=lambda args, **kw: calls.append(args) or 0)
        self.addCleanup(w.close)
        w.show()
        w.command = 'install'
        w.receive('selected-profile', profile)
        w.receive('check', {'id': 'ssh', 'label': 'SSH connection and sign-in', 'status': 'fail', 'detail': ''})
        w.receive('failure-help', for_error(PermissionError(errno.EACCES, 'PRIVATE'), 'ssh-connect', profile))
        with patch('cytv.gui.sys.platform', 'darwin'):
            w.receive('done', 1)
        self.app.processEvents()
        self.assertIn('blocked', w.subtitle.text())
        self.assertIn('Local Network', w.content.toPlainText())
        self.assertIn('older', w.content.toPlainText())
        self.assertTrue(w.check_panel.isHidden())
        buttons = {b.text(): b for b in w.form.findChildren(QPushButton)}
        self.assertTrue(buttons['Check connection again'].isDefault())
        with patch('cytv.gui.subprocess.Popen') as launch:
            buttons['Open System Settings'].click()
            launch.assert_called_once_with(['open', '-b', 'com.apple.systempreferences'])
        buttons['Check connection again'].click()
        self.pump(lambda: not w.running)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], 'doctor')
        self.assertIn('--report', calls[0])
        self.assertEqual(calls[0][calls[0].index('--host') + 1], '192.0.2.10')
        w.home()
        self.assertIsNone(w.selected_profile)
        w.receive('selected-profile', profile)
        w.receive('failure-help', for_error(PermissionError(errno.EACCES, 'PRIVATE'), 'ssh-connect', profile,
                                          {'action': 'install', 'stage': 'coordinator-submitted'}))
        w.receive('done', 1)
        labels = [b.text() for b in w.form.findChildren(QPushButton)]
        self.assertNotIn('Check connection again', labels)
        self.assertNotIn('Change connection', labels)

    def test_macos_timeout_keeps_network_checklist_with_optional_permission_advice(self):
        from cytv.failure_help import for_error
        w = Wizard(); self.addCleanup(w.close)
        w.receive('selected-profile', {'host': '192.0.2.10', 'port': 22, 'edition': 'root'})
        w.receive('failure-help', for_error(TimeoutError(), 'ssh-connect', {'edition': 'root'}))
        with patch('cytv.gui.sys.platform', 'darwin'):
            w.receive('done', 1)
        text = w.content.toPlainText()
        self.assertIn('Keep the TV on', text)
        self.assertIn('SSH port', text)
        self.assertIn('VPN', text)
        self.assertIn('System Settings', text)

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS permission layout uses native macOS font metrics')
    def test_russian_macos_permission_help_and_actions_fit_small_window(self):
        import errno
        from cytv import i18n
        from cytv.failure_help import for_error
        w = Wizard(); self.addCleanup(w.close)
        i18n.set_language('ru')
        w.home(); w.resize(900, 680); w.show(); w.preview.hide()
        w.receive('selected-profile', {'host': '192.0.2.10', 'port': 22, 'edition': 'root'})
        w.receive('text', 'Connecting to the TV…')
        w.receive('check', {'id': 'ssh', 'label': 'SSH connection and sign-in', 'status': 'fail', 'detail': ''})
        report = Path(self.directory.name) / 'report.json'; report.write_text('{}')
        w.receive('report', report)
        w.receive('failure-help', for_error(PermissionError(errno.EACCES, 'PRIVATE'), 'ssh-connect', {'edition': 'root'}))
        with patch('cytv.gui.sys.platform', 'darwin'), patch('cytv.gui.sys.executable', '/Applications/cytv 8.app/Contents/MacOS/cytv'):
            w.receive('done', 1)
        self.app.processEvents()
        self.assertIn('cytv 8.app', w.content.toPlainText())
        self.assertEqual(w.content.verticalScrollBar().maximum(), 0)
        for button in w.form.findChildren(QPushButton):
            self.assertTrue(w.rect().contains(button.mapTo(w, button.rect().bottomRight())))
            self.assertGreaterEqual(button.height(), 44)

    def test_edited_connection_is_validated_and_checked_without_installation(self):
        calls = []
        w = Wizard(run=lambda args, **kw: calls.append(args) or 0)
        self.addCleanup(w.close)
        w.edit_connection({'host': '192.0.2.10', 'port': 22, 'edition': 'root', 'root_variant': 'node012-beta'})
        entries = w.form.findChildren(QLineEdit)
        check = next(b for b in w.form.findChildren(QPushButton) if b.text() == 'Check connection again')
        entries[0].setText('https://invalid')
        check.click()
        self.assertIn('Invalid TV address', w.subtitle.text())
        self.assertEqual(calls, [])
        entries[0].setText('192.0.2.20')
        entries[1].setText('2222')
        check.click()
        self.pump(lambda: not w.running)
        args = calls[0]
        self.assertEqual(args[0], 'doctor')
        self.assertEqual(args[args.index('--host') + 1], '192.0.2.20')
        self.assertEqual(args[args.index('--port') + 1], '2222')
        self.assertEqual(args[args.index('--root-variant') + 1], 'node012-beta')
        w.edit_connection({'host': '192.0.2.10', 'port': 22, 'edition': 'root', 'root_variant': 'node012-beta'})
        edition = next(c for c in w.form.findChildren(QComboBox) if c is not w.language)
        edition.setCurrentIndex(1)
        next(b for b in w.form.findChildren(QPushButton) if b.text() == 'Check connection again').click()
        self.pump(lambda: not w.running)
        self.assertNotIn('--root-variant', calls[1])
        self.assertEqual(calls[1][calls[1].index('--edition') + 1], 'no-root')

    def test_setup_result_requires_all_three_distinct_checks(self):
        w = Wizard(); self.addCleanup(w.close)
        w.command = 'install'
        w.receive('check', {'id':'ssh','label':'SSH connection and sign-in','status':'pass','detail':''})
        for key, label, status in [('packages','Installed packages','pass'),
                ('startup','Startup readback','pass'),
                ('home-button','Home button — your observation','unknown')]:
            w.receive('check', {'id':key,'label':label,'status':status,'detail':''})
        w.receive('done',0)
        self.assertEqual(w.title.text(), 'Review TV checks')
        text = w.check_panel.toPlainText()
        self.assertLess(text.index('Installed packages'), text.index('SSH connection and sign-in'))
        w.receive('check', {'id':'home-button','label':'Home button — your observation','status':'fail','detail':''})
        w.receive('done',0)
        self.assertEqual(w.title.text(), 'Review TV checks')
        w.receive('check', {'id':'home-button','label':'Home button — your observation','status':'pass','detail':''})
        w.receive('done',0)
        self.assertEqual(w.title.text(), 'Home button confirmed by you')

    def test_steps_follow_events_without_marking_failed_install_complete(self):
        w = Wizard()
        w.receive('step', (3, 'Prepare the TV connection', True))
        self.assertEqual([row.property('state') for row in w.step_rows],
                         ['complete', 'complete', 'current', 'upcoming', 'upcoming', 'upcoming'])
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
