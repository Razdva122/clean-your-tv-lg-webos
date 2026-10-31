"""Windowed cytv wizard. Run with python -m cytv.gui."""
import html
from pathlib import Path
import shutil
import sys
import threading

from PySide6.QtCore import QObject, Signal, QUrl, QTimer, Qt
from PySide6.QtGui import QDesktopServices, QIcon, QFontDatabase, QFont, QPixmap
from PySide6.QtWidgets import (QApplication, QFileDialog, QFrame, QHBoxLayout,
                              QLabel, QLineEdit, QMainWindow, QMessageBox, QProgressBar,
                              QPushButton, QTextBrowser, QVBoxLayout, QWidget, QButtonGroup, QDialog)

from cytv import __version__, cli, diagnostics, i18n
from cytv.i18n import translate as tr
from cytv.desktop import Channel
from cytv.gui_style import STYLE, TVPreview, Select, EditionOption, BrandSignature

MAINTENANCE_ACTIONS = (
    ('Check TV status', 'status'),
    ('Check connection and create a diagnostic report', 'doctor'),
    ('Return to LG Home', 'restore'),
    ('Uninstall Clean Your TV', 'uninstall'),
    ('Home button diagnostics', 'home-diagnostics'),
    ('Enable updates for all TV components (root required)', 'enable-system-updates'),
    ('Clear WAM caches (root required)', 'clean-wam-cache'),
)


class Events(QObject):
    event = Signal(str, object)


class Wizard(QMainWindow):
    def __init__(self, run=cli.main):
        super().__init__()
        i18n.configure()
        self.run = run
        self.running = False
        self.pending = None
        self.preparation = []
        self.collect_preparation = False
        self.report = None
        self.recovery_profile = None
        self.worker = None
        self.setWindowTitle('Clean Your TV')
        self.resize(1060, 820)
        self.setMinimumSize(900, 680)
        self.apply_language_font()
        self.current_step = 0
        self.command = 'install'
        self.events = Events()
        self.events.event.connect(self.receive)
        body = QWidget()
        self.setCentralWidget(body)
        shell = QHBoxLayout(body)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        sidebar = QWidget()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(248)
        rail = QVBoxLayout(sidebar)
        rail.setContentsMargins(20, 24, 20, 26)
        rail.setSpacing(8)
        self.brand = BrandSignature(cli.payload_dir() / 'brand-stacked.svg')
        rail.addWidget(self.brand)
        rail.addSpacing(12)
        self.rail_title = QLabel()
        self.rail_title.setObjectName('railTitle')
        self.rail_title.setWordWrap(True)
        rail.addWidget(self.rail_title)
        rail.addSpacing(12)
        self.steps = QWidget()
        step_layout = QVBoxLayout(self.steps)
        step_layout.setContentsMargins(0, 0, 0, 0)
        step_layout.setSpacing(12)
        self.step_rows = []
        self.step_names = []
        self.step_numbers = []
        for number in range(1, 5):
            row = QFrame()
            row.setObjectName('step')
            line = QHBoxLayout(row)
            line.setContentsMargins(10, 12, 10, 12)
            line.setSpacing(12)
            marker = QLabel(str(number))
            marker.setObjectName('stepNumber')
            marker.setFixedSize(32, 32)
            marker.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name = QLabel()
            name.setObjectName('stepName')
            name.setWordWrap(True)
            line.addWidget(marker)
            line.addWidget(name, 1)
            self.step_rows.append(row)
            self.step_names.append(name)
            self.step_numbers.append(marker)
            step_layout.addWidget(row)
        rail.addWidget(self.steps)
        rail.addStretch()
        self.rail_note = QLabel()
        self.rail_note.setObjectName('railNote')
        self.rail_note.setWordWrap(True)
        rail.addWidget(self.rail_note)
        rail.addSpacing(20)
        version = QLabel('cytv ' + __version__)
        version.setObjectName('version')
        rail.addWidget(version)
        shell.addWidget(sidebar)
        main = QWidget()
        layout = QVBoxLayout(main)
        layout.setContentsMargins(40, 30, 40, 24)
        layout.setSpacing(12)
        header = QHBoxLayout()
        self.badge = QLabel()
        self.badge.setObjectName('badge')
        header.addWidget(self.badge)
        header.addStretch()
        self.language = Select()
        self.language.setObjectName('language')
        self.language.setAccessibleName(tr('Language'))
        for code, name in i18n.LANGUAGES.items():
            self.language.addItem(tr(name) if code == 'auto' else name, code)
        self.language.setCurrentIndex(list(i18n.LANGUAGES).index(i18n.language_choice()))
        self.language.currentIndexChanged.connect(self.change_language)
        header.addWidget(self.language)
        layout.addLayout(header)
        layout.addSpacing(18)
        self.title = QLabel()
        self.title.setObjectName('title')
        self.title.setWordWrap(True)
        layout.addWidget(self.title)
        self.subtitle = QLabel()
        self.subtitle.setObjectName('subtitle')
        self.subtitle.setWordWrap(True)
        layout.addWidget(self.subtitle)
        self.preview = TVPreview()
        layout.addWidget(self.preview)
        self.content = QTextBrowser()
        self.content.setOpenExternalLinks(False)
        self.content.setOpenLinks(False)
        self.content.anchorClicked.connect(lambda url: self.show_reference(url.path()) if url.scheme() == 'guide' else None)
        self.content.setFrameShape(QFrame.Shape.NoFrame)
        self.content.document().setDefaultStyleSheet(
            'p { margin-top: 6px; margin-bottom: 12px; line-height: 140%; } '
            'h3 { color: #f3ede3; font-size: 16px; margin-top: 12px; margin-bottom: 10px; }')
        layout.addWidget(self.content, 1)
        self.check_results = {}
        self.check_panel = QTextBrowser()
        self.check_panel.setAccessibleName(tr('TV checks'))
        self.check_panel.setOpenLinks(False)
        self.check_panel.setFrameShape(QFrame.Shape.NoFrame)
        self.check_panel.setMinimumHeight(150)
        self.check_panel.hide()
        layout.addWidget(self.check_panel, 2)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(5)
        self.progress.hide()
        layout.addWidget(self.progress)
        self.form = QWidget()
        self.form.setObjectName('form')
        self.form_layout = QVBoxLayout(self.form)
        self.form_layout.setContentsMargins(16, 16, 16, 16)
        self.form_layout.setSpacing(10)
        layout.addWidget(self.form)
        self.details_toggle = QPushButton()
        self.details_toggle.setCheckable(True)
        self.details_toggle.setObjectName('detailsToggle')
        self.details_toggle.setMinimumHeight(36)
        self.details_toggle.toggled.connect(self.toggle_details)
        layout.addWidget(self.details_toggle)
        self.details = QTextBrowser()
        self.details.setOpenExternalLinks(False)
        self.details.setMaximumHeight(150)
        self.details.setAccessibleName(tr('Details'))
        layout.addWidget(self.details)
        footer = QHBoxLayout()
        footer.addStretch()
        self.cancel = QPushButton(tr('Close'))
        self.cancel.setObjectName('close')
        self.cancel.clicked.connect(self.close)
        footer.addWidget(self.cancel)
        layout.addLayout(footer)
        shell.addWidget(main, 1)
        self.home()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'preview'):
            self.preview.setFixedHeight(144 if self.height() < 760 else 206)

    def apply_language_font(self):
        family = {'zh-Hans': 'Noto Sans SC', 'zh-Hant': 'Noto Sans TC'}.get(i18n.resolved_language())
        # Keep the existing typography for other languages and use the script's
        # packaged outlines ahead of system CJK fallback for Chinese.
        style = STYLE.replace('font-family: ', 'font-family: "' + family + '", ', 1) if family else STYLE
        self.setStyleSheet(style)

    def change_language(self):
        if self.running:
            return
        previous = i18n.language_choice()
        try:
            i18n.configure(self.language.currentData())
        except OSError:
            self.language.blockSignals(True)
            self.language.setCurrentIndex(list(i18n.LANGUAGES).index(previous))
            self.language.blockSignals(False)
            self.error_dialog('Could not save language preference', 'Check write access to the application data folder and try again.')
            return
        self.apply_language_font()
        self.language.setAccessibleName(tr('Language'))
        self.language.setItemText(0, tr('Auto'))
        self.cancel.setText(tr('Close'))
        self.home()

    def clear_form(self):
        while self.form_layout.count():
            item = self.form_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

    def button(self, label, callback, default=False):
        button = QPushButton(tr(label))
        button.setMinimumHeight(44)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setDefault(default)
        button.setProperty('primary', default)
        button.clicked.connect(callback)
        self.form_layout.addWidget(button)
        return button

    def update_steps(self, number=0, result=None):
        self.current_step = number
        for index, row in enumerate(self.step_rows, 1):
            state = 'complete' if index < number else 'current' if index == number else 'upcoming'
            if result == 0:
                state = 'complete'
            elif index == number and result is not None:
                state = 'error' if result != 130 else 'upcoming'
            row.setProperty('state', state)
            self.step_numbers[index - 1].setText('✓' if state == 'complete' else '!' if state == 'error' else str(index))
            row.style().unpolish(row)
            row.style().polish(row)
            for label in (self.step_numbers[index - 1], self.step_names[index - 1]):
                label.style().unpolish(label)
                label.style().polish(label)
            row.update()

    def set_error_state(self, failed):
        for widget in (self.title, self.badge):
            widget.setProperty('state', 'error' if failed else '')
            widget.style().unpolish(widget)
            widget.style().polish(widget)

    def error_dialog(self, title, message):
        dialog = QMessageBox(QMessageBox.Icon.Warning, tr(title), tr(message), parent=self)
        dialog.setStyleSheet('QLabel { color: #ff6b6b; }')
        dialog.exec()

    def reset_checks(self):
        self.check_results.clear()
        self.check_panel.clear()
        self.check_panel.hide()
        self.content.setMaximumHeight(16777215)

    def home(self):
        self.reset_checks()
        self.recovery_profile = None
        self.preparation = []
        self.collect_preparation = False
        self.reset_details()
        self.clear_form()
        self.preview.show()
        self.subtitle.show()
        self.steps.show()
        self.progress.hide()
        self.update_steps()
        self.set_error_state(False)
        self.badge.setText(tr('Before you begin'))
        self.rail_title.setText(tr('Set up my TV'))
        self.rail_note.setText(tr('Keep your TV on and watch for a pairing request.'))
        for label, title in zip(self.step_names, ('Connect to your TV', 'Choose your edition', 'Prepare the TV connection', 'Review and install')):
            label.setText(tr(title))
        self.title.setText(tr('Make your TV feel like yours'))
        self.subtitle.setText(tr('Install Root or No-root. We will help you choose.'))
        self.content.setHtml('<h3>' + html.escape(tr('Before you begin')) + '</h3><p>' + html.escape(tr('Turn on your LG webOS TV and connect it to the same home network as this computer.')) + '</p><p>' + html.escape(tr('cytv will look for your TV automatically. Keep the remote nearby to approve pairing on the TV.')) + '</p>')
        self.button('Set up my TV', lambda: self.start('install'), True)
        self.maintenance_toggle = self.button('Maintenance action', self.toggle_maintenance)
        self.maintenance_toggle.setObjectName('maintenanceToggle')
        self.maintenance_toggle.setCheckable(True)
        self.maintenance_toggle.setText(tr('Maintenance action') + '  ▸')
        self.maintenance = QWidget()
        maintenance_layout = QVBoxLayout(self.maintenance)
        maintenance_layout.setContentsMargins(0, 0, 0, 0)
        maintenance_layout.setSpacing(10)
        actions = Select()
        actions.setAccessibleName(tr('Maintenance action'))
        for label, command in MAINTENANCE_ACTIONS:
            actions.addItem(tr(label), command)
        help_text = QLabel(tr('Check TV status shows what is installed. Return to LG Home restores the standard screen. Uninstall Clean Your TV removes the CYTV apps.'))
        help_text.setWordWrap(True)
        maintenance_layout.addWidget(help_text)
        maintenance_layout.addWidget(actions)
        execute = QPushButton(tr('Run selected maintenance action'))
        execute.setMinimumHeight(44)
        execute.clicked.connect(lambda: self.start(actions.currentData()))
        maintenance_layout.addWidget(execute)
        self.form_layout.addWidget(self.maintenance)
        self.maintenance.hide()

    def toggle_maintenance(self):
        expanded = self.maintenance_toggle.isChecked()
        self.maintenance.setVisible(expanded)
        self.maintenance_toggle.setText(tr('Maintenance action') + ('  ▾' if expanded else '  ▸'))

    def toggle_details(self, expanded):
        self.details.setVisible(expanded)
        self.details_toggle.setText(tr('Details') + ('  ▾' if expanded else '  ▸'))

    def reset_details(self):
        self.details.clear()
        self.details_toggle.setChecked(False)
        self.toggle_details(False)
        self.details_toggle.hide()

    def guide_path(self, name):
        if name not in ('sign-in', 'dev-mode', 'key-server'):
            return None
        for directory in (cli.payload_dir() / 'setup-guide',
                          Path(__file__).resolve().parents[1] / 'android/app/src/main/assets/ui/guide'):
            path = directory / (name + '.png')
            if path.is_file():
                return path
        return None

    def show_reference(self, name):
        path = self.guide_path(name)
        if path is None:
            return
        dialog = QDialog(self)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.setWindowTitle(tr('Example from LG'))
        layout = QVBoxLayout(dialog)
        picture = QLabel()
        picture.setAccessibleName(tr('Example from LG'))
        picture.setPixmap(QPixmap(str(path)).scaled(760, 430, Qt.AspectRatioMode.KeepAspectRatio,
                                                   Qt.TransformationMode.SmoothTransformation))
        picture.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(picture)
        caption = QLabel(tr('Example from LG. The screen may look different on your TV. Use the code shown on your own TV.'))
        caption.setWordWrap(True)
        layout.addWidget(caption)
        close = QPushButton(tr('Close'))
        close.clicked.connect(dialog.close)
        layout.addWidget(close)
        dialog.open()

    def instruction_card(self, title, messages, image=None):
        paragraphs = ''.join('<p style="margin-top: 4px; margin-bottom: 0; line-height: 125%">' + html.escape(tr(text)).replace('\n', '<br>') + '</p>' for text in messages)
        path = self.guide_path(image)
        if path is not None:
            picture = QPixmap(str(path))
            width = 240
            height = round(width * picture.height() / max(1, picture.width()))
            paragraphs = ('<table width="100%" cellpadding="6"><tr><td valign="top" width="250">'
                          '<a href="guide:' + image + '"><img src="' + QUrl.fromLocalFile(str(path)).toString() +
                          f'" width="{width}" height="{height}" alt="' + html.escape(tr('Example from LG')) + '"></a><p style="font-size: 13px">' +
                          html.escape(tr('Example from LG')) + ' · <a style="color: #d6c5ae" href="guide:' + image + '">' +
                          html.escape(tr('Enlarge')) + '</a></p></td><td valign="top">' + paragraphs + '</td></tr></table>')
        return ('<table width="100%" cellspacing="0" cellpadding="12" '
                'style="background-color: #272521; border: 1px solid #51483e"><tr><td>'
                '<h3 style="color: #f3ede3; margin-top: 0; margin-bottom: 6px">' + html.escape(tr(title)) + '</h3>' + paragraphs + '</td></tr></table>')

    def show_preparation(self, index, prompt):
        if index == len(self.preparation):
            self.preparation = []
            self.content.setHtml(self.review_content)
            self.title.setText(self.review_title)
            self.badge.setText(tr('Step 4 of 4'))
            self.update_steps(4)
            self.show_prompt(prompt)
            return
        self.clear_form()
        self.title.setText(tr('Prepare the TV connection'))
        self.badge.setText(tr('Step 3 of 4') + f' · {index + 1} / {len(self.preparation)}')
        self.update_steps(3)
        title, messages = self.preparation[index]
        image = {'1. Developer Mode': 'sign-in', '2. Dev Mode Status': 'dev-mode',
                 '3. Key Server': 'key-server'}.get(title)
        self.content.setHtml(self.instruction_card(title, messages, image))
        if index:
            self.button('Back', lambda: self.show_preparation(index - 1, prompt))
        self.button('Continue', lambda: self.show_preparation(index + 1, prompt), True).setFocus()

    def start(self, command, profile=None):
        if self.running:
            return
        self.running = True
        self.reset_checks()
        self.set_error_state(False)
        self.command = command
        self.operation_title = next((label for label, key in MAINTENANCE_ACTIONS if key == command), 'Set up my TV')
        self.preview.hide()
        self.subtitle.show()
        self.steps.setVisible(command == 'install')
        self.update_steps(1)
        self.badge.setText(tr('Connecting to your TV' if command == 'install' else 'Maintenance action'))
        self.rail_title.setText(tr(self.operation_title))
        self.language.setEnabled(False)
        self.report = None
        self.recovery_profile = None
        self.pending = None
        self.preparation = []
        self.collect_preparation = False
        self.reset_details()
        self.content.clear()
        self.clear_form()
        self.title.setText(tr('Connecting to your TV' if command == 'install' else self.operation_title))
        self.subtitle.setText(tr('Keep your TV on and watch for a pairing request.'))
        self.cancel.setText(tr('Cancel'))
        self.cancel.setEnabled(False)
        self.progress.show()
        self.channel = Channel(self.events.event.emit)
        def work():
            try:
                args = [command, '--report'] if command == 'doctor' else [command]
                if profile:
                    args += ['--host', profile['host'], '--edition', profile['edition'],
                             '--port', str(profile['port']), '--no-discovery']
                args += ['--language', i18n.language_choice()]
                code = self.run(args, ask=self.channel.ask, secret=self.channel.secret, write=self.channel.console)
            except Exception:
                # Startup/storage errors outside cli.main's handler must stay visible,
                # without exposing exception text that could contain credentials.
                self.events.event.emit('error-heading', 'Could not start this operation')
                self.events.event.emit('error', 'Check that your user account can write to its application data folder. You can report this problem using Open an issue below.')
                code = 1
            self.events.event.emit('done', code)
        self.worker = threading.Thread(target=work, name='cytv-install', daemon=False)
        self.worker.start()

    def receive(self, kind, value):
        if kind == 'check':
            self.check_panel.setAccessibleName(tr('TV checks'))
            self.content.setMaximumHeight(140)
            self.check_results[value['id']] = dict(value)
            from .checks import STATUS
            colors = {'pass': '#90cfad', 'fail': '#ff8580', 'unknown': '#e8c17d',
                      'running': '#eddbc2', 'pending': '#c0b5a5'}
            rows = []
            for result in self.check_results.values():
                status = result['status']
                label, detail = html.escape(tr(result['label'])), html.escape(tr(result['detail']))
                marker = {'pass': '✓', 'fail': '!', 'unknown': '?', 'running': '…', 'pending': '·'}[status]
                rows.append(f'<tr><td style="color:{colors[status]};padding:5px">{marker}</td>'
                            f'<td style="padding:5px">{label}' + (f'<br><small>{detail}</small>' if detail else '') + '</td>'
                            f'<td style="color:{colors[status]};padding:5px">{html.escape(tr(STATUS[status]))}</td></tr>')
            self.check_panel.setHtml('<h3>' + html.escape(tr('TV checks')) + '</h3><table width="100%">' + ''.join(rows) + '</table>')
            self.check_panel.show()
        elif kind == 'step':
            number, title, clear = value
            self.collect_preparation = number == 3
            if self.collect_preparation:
                self.preparation = []
            self.details.append(html.escape(tr(title)))
            if self.command == 'install':
                self.title.setText(tr(title))
                self.subtitle.hide()
                self.badge.setText(tr(f'Step {number} of 4'))
                self.update_steps(number)
            else:
                self.title.setText(tr(self.operation_title))
                self.subtitle.setText(tr(title))
                self.subtitle.show()
                self.badge.setText(tr('Maintenance action'))
            self.content.clear()
        elif kind in ('text', 'heading', 'error', 'error-heading'):
            text = tr(value)
            tag = 'h3' if kind in ('heading', 'error-heading') else 'p'
            color = '#ff6b6b' if kind.startswith('error') else '#f3ede3' if kind == 'heading' else '#c0b5a5'
            style = f' style="color: {color}"'
            markup = f'<{tag}{style}>' + html.escape(text).replace('\n', '<br>') + f'</{tag}>'
            self.content.append(markup)
            self.details.append(markup)
            self.details_toggle.show()
            if self.collect_preparation:
                if kind == 'heading':
                    self.preparation.append((value, []))
                elif kind == 'text' and self.preparation:
                    self.preparation[-1][1].append(value)
        elif kind == 'report':
            path = Path(value)
            if path.is_file():
                self.report = path
        elif kind == 'recovery':
            self.recovery_profile = dict(value)
        elif kind == 'prompt':
            self.show_prompt(value)
        elif kind == 'done':
            self.running = False
            self.set_error_state(value not in (0, 130))
            self.language.setEnabled(True)
            self.pending = None
            self.progress.hide()
            self.cancel.setText(tr('Close'))
            self.cancel.setEnabled(True)
            self.clear_form()
            self.title.setText(tr('Finished' if value == 0 else 'Cancelled' if value == 130 else 'Let’s resolve this'))
            self.subtitle.show()
            self.subtitle.setText(tr('Read the result below before continuing.'))
            self.rail_note.setText(tr('Read the result below before continuing.'))
            self.badge.setText(self.title.text())
            if self.command == 'install':
                self.update_steps(self.current_step, value)
            self.content.moveCursor(self.content.textCursor().MoveOperation.End)
            failed = value not in (0, 130)
            recover = value == 0 and self.recovery_profile is not None
            if recover:
                profile = dict(self.recovery_profile)
                self.title.setText(tr('Recovery available'))
                self.badge.setText(self.title.text())
                self.subtitle.setText(tr('Restore LG Home, finish removal and reinstall. You will review each step before changes.'))
                self.button('Recover and reinstall', lambda: self.start('install', profile), True)
            if self.report:
                self.button('Save diagnostic report…', self.save_report, failed)
                if failed:
                    self.subtitle.setText(tr('Save the report from this failed attempt and attach it to your issue. Recovery data has been kept.'))
            elif failed:
                self.subtitle.setText(tr('A diagnostic report could not be created. Include the visible error when opening an issue.'))
            if failed:
                self.button('Open an issue', lambda: QDesktopServices.openUrl(QUrl(diagnostics.ISSUE_URL)))
            self.button('Back to start', self.home, not recover and not (failed and self.report))
            failed_checks = [result for result in self.check_results.values() if result['status'] in ('fail', 'unknown')]
            if failed and failed_checks:
                self.subtitle.setText(tr('Failed') + ': ' + ', '.join(tr(result['label']) for result in failed_checks) + '\n' + self.subtitle.text())

    def show_prompt(self, prompt):
        self.check_panel.hide()
        self.content.setMaximumHeight(16777215)
        self.pending = prompt
        self.progress.hide()
        self.cancel.setEnabled(True)
        self.clear_form()
        self.details_toggle.setChecked(False)
        if (self.preparation and self.preparation[0][0] == '1. Developer Mode'
                and prompt.label.startswith('Connect to check installed versions?')):
            self.review_title = self.title.text()
            self.review_content = self.content.toHtml()
            self.show_preparation(0, prompt)
            return
        if prompt.secret:
            developer = prompt.label.startswith('Developer Mode')
            title = 'Developer Mode code (Passphrase)' if developer else prompt.title
            self.title.setText(tr(title))
            self.subtitle.hide()
            if developer:
                cards = [self.instruction_card('Where to find the code', [
                    'Enter Passphrase: the six characters shown in Developer Mode on the TV. Match uppercase and lowercase letters.'], 'key-server'),
                    self.instruction_card('Important', [
                    'Use the code from the TV, not your LG account password. If no code is visible, turn on Key Server.'])]
            else:
                help_text = ('Enter the passphrase that unlocks your private SSH key file.' if prompt.label.startswith('SSH key')
                             else 'Enter your existing TV root SSH password. This was set when SSH access was configured.')
                cards = [self.instruction_card(title, [help_text])]
            self.content.setHtml('<p style="margin-bottom: 16px"></p>'.join(cards))
        label = QLabel(tr('Connection check' if self.command != 'install' and prompt.label.startswith('Edition [') else 'Developer Mode code (Passphrase)' if prompt.secret and prompt.label.startswith('Developer Mode') else prompt.title))
        label.setWordWrap(True)
        label.setObjectName('promptTitle')
        self.form_layout.addWidget(label)
        if prompt.kind == 'confirm':
            trust_prompt = prompt.label.startswith('Connect and remember this TV?')
            label = ('Recover and reinstall' if prompt.label.startswith('Finish removal before installing again?')
                     else 'Connect and remember' if trust_prompt else 'Continue')
            yes = self.button(label, lambda: self.submit('y'), prompt.default == 'y')
            no = self.button('No, go back / cancel this operation', lambda: self.submit('n'), prompt.default == 'n')
            (yes if prompt.default == 'y' else no).setFocus()
            if trust_prompt:
                self.button('Connection details', lambda: self.submit('?'))
        elif prompt.kind == 'choice' and prompt.label.startswith('Edition'):
            options = QWidget()
            row = QHBoxLayout(options)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(12)
            group = QButtonGroup(options)
            for key, name, detail in prompt.options:
                card = EditionOption(tr(name), tr(detail), key)
                group.addButton(card)
                row.addWidget(card, 1)
                if key == prompt.default:
                    card.setChecked(True)
            self.form_layout.addWidget(options)
            proceed = self.button('Continue', lambda: self.submit(group.checkedButton().key), True)
            proceed.setEnabled(group.checkedButton() is not None)
            group.buttonToggled.connect(lambda: proceed.setEnabled(group.checkedButton() is not None))
            if group.checkedButton():
                group.checkedButton().setFocus()
        elif prompt.kind == 'choice':
            choices = Select()
            choices.setAccessibleName(tr(prompt.title))
            for key, name, detail in prompt.options:
                choices.addItem(tr(name) + (' — ' + tr(detail) if detail else ''), key)
                if key == prompt.default:
                    choices.setCurrentIndex(choices.count() - 1)
            self.form_layout.addWidget(choices)
            self.button('Continue', lambda: self.submit(choices.currentData()), True)
            choices.setFocus()
            if prompt.label.startswith('TV number'):
                # Saved-TV menus also use this label; retry is offered only for discovery.
                if any(name == 'Enter an IP address manually' for _, name, _ in prompt.options):
                    self.button('Search again', lambda: self.submit('r'))
        elif prompt.kind == 'ready':
            self.button('TV is on — check again', lambda: self.submit(''), True).setFocus()
        else:
            entry = QLineEdit()
            entry.setAccessibleName(label.text())
            label.setBuddy(entry)
            if prompt.secret:
                entry.setEchoMode(QLineEdit.EchoMode.Password)
            elif 'IP address' in prompt.label:
                entry.setPlaceholderText(tr('For example, 192.168.1.50'))
            self.form_layout.addWidget(entry)
            def submit_entry():
                value = entry.text()
                entry.clear()
                self.submit(value)
            entry.returnPressed.connect(submit_entry)
            self.button('Continue', submit_entry, True)
            if prompt.kind == 'file':
                def choose_file():
                    filename, _ = QFileDialog.getOpenFileName(self, tr('Choose your existing SSH private key'))
                    if filename:
                        entry.setText(filename)
                self.button('Choose key file…', choose_file)
            if 'IP address' in prompt.label:
                self.button('Search again', lambda: self.submit('r'))
                self.button('Help finding my TV', lambda: self.submit('?'))
            entry.setFocus()

    def submit(self, value):
        if not self.pending:
            return
        if self.pending.secret:
            self.content.clear()
            self.title.setText(tr('Connecting to your TV'))
        self.pending = None
        if self.check_results:
            self.content.setMaximumHeight(140)
            self.check_panel.show()
        self.clear_form()
        self.cancel.setEnabled(False)
        self.progress.show()
        self.channel.answer(value)

    def save_report(self):
        filename, _ = QFileDialog.getSaveFileName(self, tr('Save diagnostic report'), self.report.name, 'JSON (*.json)')
        if filename:
            try:
                if Path(filename).resolve() != self.report.resolve():
                    shutil.copyfile(self.report, filename)
            except OSError:
                self.error_dialog('Could not save report', 'Choose another folder and try again.')

    def closeEvent(self, event):
        if self.running:
            event.ignore()
            if self.pending:
                self.submit(None)
            else:
                QMessageBox.information(self, tr('Operation in progress'), tr('Please wait for this step to finish. This keeps installation and recovery data consistent.'))
        else:
            event.accept()


def main():
    app = QApplication(sys.argv[:1])
    for font in (cli.payload_dir() / 'fonts').glob('*.ttf'):
        QFontDatabase.addApplicationFont(str(font))
    QFont.insertSubstitutions(app.font().family(), ['Noto Sans', 'Noto Sans Devanagari', 'Noto Sans KR'])
    app.setApplicationName('Clean Your TV')
    app.setOrganizationName('CleanYourTV')
    app.setWindowIcon(QIcon(str(cli.payload_dir() / 'installer.png')))
    app.setStyle('Fusion')
    window = Wizard()
    window.show()
    if '--smoke-test' in sys.argv:
        QTimer.singleShot(200, app.quit)
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
