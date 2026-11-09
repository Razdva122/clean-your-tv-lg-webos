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
    from PySide6.QtWidgets import QApplication, QPushButton, QLineEdit, QComboBox, QRadioButton, QDialog, QLabel, QScrollArea
    from cytv.gui import Wizard
    from cytv.desktop import Prompt
    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, 'Desktop build dependencies are optional for CLI tests')
class GuiTests(unittest.TestCase):
    def test_tv_name_prompt_prefills_home_and_submits_custom_name(self):
        w=Wizard();self.addCleanup(w.close)
        from cytv.desktop import Channel
        w.channel=Channel(lambda *_:None)
        w.show_prompt(Prompt('TV name [Home]: '))
        entry=w.form.findChildren(QLineEdit)[0]
        self.assertEqual(entry.text(),'Home')
        self.assertEqual(entry.maxLength(),48)
        entry.setText('Aashiyaan')
        next(button for button in w.form.findChildren(QPushButton) if button.text()=='Continue').click()
        self.assertEqual(w.channel.answers.get_nowait(),'Aashiyaan')

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
