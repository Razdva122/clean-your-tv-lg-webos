import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

class LanguageTests(unittest.TestCase):
    def language(self):
        self.assertIsNotNone(importlib.util.find_spec('cytv.i18n'), 'installer language support is missing')
        from cytv import i18n
        self.addCleanup(i18n.set_language, 'en')
        return i18n

    def test_czech_selection_locale_detection_and_persistence(self):
        lang = self.language()
        self.assertEqual(lang.LANGUAGES.get('cs'), 'Čeština')
        for tag in ('cs', 'cs-CZ', 'cs_CZ.UTF-8'):
            self.assertEqual(lang.resolve_language(tag), 'cs')
        self.assertEqual(lang.resolve_language('auto', ['xx', 'cs-CZ']), 'cs')
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(lang.configure('cs', directory), 'cs')
            self.assertEqual(lang.configure(None, directory), 'cs')
            self.assertEqual(json.loads((Path(directory) / 'settings.json').read_text())['language'], 'cs')

    def test_czech_catalog_renders_values_and_preserves_default_no(self):
        lang = self.language()
        self.assertTrue(all('cs' in values for values in lang.MESSAGES.values()))
        lang.set_language('cs')
        self.assertEqual(lang.translate('Connect to your TV'), 'Připojení k televizoru')
        self.assertEqual(lang.translate('Read 17 applications.'), 'Načteno 17 aplikací.')
        self.assertEqual(lang.translate('Run cytv status.'), 'Spusťte cytv status.')
        self.assertIn('Enter / n = ne', lang.translate('y = yes   /   Enter / n = no   /   q = quit'))
        from cytv.desktop import Channel
        events = []
        channel = Channel(lambda *event: events.append(event))
        channel.answer('n')
        self.assertEqual(channel.ask('Install this edition? [y/N]: '), 'n')
        self.assertEqual((events[-1][1].kind, events[-1][1].default), ('confirm', 'n'))
        from cytv.cli import main
        with tempfile.TemporaryDirectory() as directory:
            lines = []
            self.assertEqual(main(['--language', 'cs', '--data-dir', directory, '--no-discovery'],
                                  ask=lambda _: 'q', write=lines.append), 130)
            self.assertIn('Zrušeno', '\n'.join(lines))

    def test_home_observation_prompt_and_desktop_title_translate_in_all_locales(self):
        from cytv.desktop import Prompt
        lang = self.language()
        prompt = 'Home button result [3]: '
        title = Prompt(prompt).title
        for code in set(lang.LANGUAGES) - {'en','auto'}:
            with self.subTest(language=code):
                lang.set_language(code)
                self.assertNotEqual(lang.translate(prompt).strip(), prompt.strip())
                self.assertNotEqual(lang.translate(title), title)

    def test_desktop_typed_credentials_survive_all_localized_labels(self):
        from cytv.desktop import Channel
        from cytv.transport import CredentialPrompt
        lang = self.language()
        for code in set(lang.LANGUAGES) - {'auto'}:
            lang.set_language(code)
            for kind, label in [('key','SSH key passphrase: '), ('root','Root SSH password (hidden): '),
                                ('developer','Developer Mode passphrase: ')]:
                events = []
                channel = Channel(lambda *event: events.append(event))
                channel.answer('private fixture')
                channel.secret(CredentialPrompt(lang.translate(label), kind))
                with self.subTest(language=code, credential=kind):
                    self.assertEqual(events[-1][1].credential_type, kind)

    def test_fixed_failure_guidance_translates_in_every_installer_locale(self):
        from cytv.failure_help import GUIDES
        from cytv.checks import LABELS
        lang=self.language()
        messages={text for guide in GUIDES.values() for text in guide[:3]}
        messages.update(LABELS[key] for key in ('home-settings','home-profiles'))
        for code in set(lang.LANGUAGES)-{'en','auto'}:
            lang.set_language(code)
            for message in messages:
                with self.subTest(language=code,text=message):self.assertNotEqual(lang.translate(message),message)

    def test_connection_actions_and_macos_instructions_translate_with_app_name(self):
        lang = self.language()
        message = 'In System Settings → Privacy & Security → Local Network, allow {app}. macOS may show an older copy’s name. Fully quit cytv and reopen it after changing access.'
        for code in set(lang.LANGUAGES) - {'en', 'auto'}:
            lang.set_language(code)
            for text in ('Check connection again', 'Change connection', 'Open System Settings', message):
                self.assertNotEqual(lang.translate(text), text)
            self.assertIn('cytv 8.app', lang.translate(message).format(app='cytv 8.app'))

    def test_recovery_choices_plans_and_pending_auth_advice_translate_completely(self):
        import ast
        import re
        lang = self.language()
        source = Path(__file__).resolve().parents[2] / 'cytv/recovery.py'
        messages = set()
        for node in ast.walk(ast.parse(source.read_text(encoding='utf-8'))):
            if not isinstance(node, ast.Call): continue
            name = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, 'attr', '')
            values = node.args[2:4] if name == 'plan' else node.args[1:2] if name == 'option' else []
            messages.update(value.value for value in values if isinstance(value, ast.Constant) and isinstance(value.value, str))
        messages.update(('Recovery action [0]: ', 'Recovery action', 'Keep the original saved TV connection and recovery data; do not replace or edit the connection to bypass recovery.'))
        for code in set(lang.LANGUAGES) - {'en', 'auto'}:
            lang.set_language(code)
            for message in messages:
                for sentence in ([message.strip()] if message.strip() in lang.MESSAGES else re.split(r'(?<=[.!?]) +', message.strip())):
                    with self.subTest(language=code, text=sentence):
                        self.assertNotEqual(lang.translate(sentence), sentence)

    def test_locale_variants_and_unsupported_fallback(self):
        lang = self.language()
        for value, expected in [('pt_PT.UTF-8', 'pt-BR'), ('de_AT', 'de'), ('ru-RU', 'ru'), ('zh_CN', 'zh-Hans'), ('C', 'en')]:
            self.assertEqual(lang.resolve_language(value), expected)
        self.assertEqual(lang.resolve_language('auto', ['xx_XX', 'fr_CA']), 'fr')

    def test_chinese_script_precedes_region_and_posix_tags(self):
        lang = self.language()
        for value, expected in [
            ('zh', 'zh-Hans'), ('zh_CN.UTF-8', 'zh-Hans'),
            ('zh-SG', 'zh-Hans'), ('zh-TW', 'zh-Hant'),
            ('zh_HK.UTF-8', 'zh-Hant'), ('zh-MO', 'zh-Hant'),
            ('zh-Hans-TW', 'zh-Hans'), ('zh_Hant_CN.UTF-8', 'zh-Hant'),
        ]:
            with self.subTest(value=value):
                self.assertEqual(lang.resolve_language(value), expected)
        self.assertEqual(lang.resolve_language('auto', ['xx', 'zh-Hant-HK']), 'zh-Hant')

    def test_chinese_selection_and_rendering_keep_identifiers(self):
        lang = self.language()
        for code, title in [('zh-Hans', '连接到电视'), ('zh-Hant', '連線至電視')]:
            with tempfile.TemporaryDirectory() as directory:
                self.assertEqual(lang.configure(code, directory), code)
                self.assertEqual(lang.configure(None, directory), code)
            self.assertEqual(lang.translate('Connect to your TV'), title)
            self.assertIn('17', lang.translate('Read 17 applications.'))
            self.assertIn('cytv status', lang.translate('Run cytv status.'))

    def test_chinese_cli_cancel_and_desktop_confirm_semantics(self):
        self.language()
        from cytv.cli import main
        from cytv.desktop import Channel
        from cytv import i18n
        for code in ('zh-Hans', 'zh-Hant'):
            with tempfile.TemporaryDirectory() as directory:
                lines = []
                self.assertEqual(main(['--language', code, '--data-dir', directory, '--no-discovery'],
                                      ask=lambda _: 'q', write=lines.append), 130)
                self.assertIn('取消', '\n'.join(lines))
            i18n.set_language(code)
            events = []
            channel = Channel(lambda *event: events.append(event))
            channel.answer('n')
            self.assertEqual(channel.ask('Connect and remember this TV? [Y/n]: '), 'n')
            prompt = events[-1][1]
            self.assertEqual((prompt.kind, prompt.default), ('confirm', 'y'))

    def test_selection_is_persisted_and_auto_is_not_frozen(self):
        lang = self.language()
        with tempfile.TemporaryDirectory() as directory:
            lang.configure('ru', directory)
            self.assertEqual(lang.configure(None, directory), 'ru')
            lang.configure('auto', directory)
            self.assertEqual(json.loads((Path(directory) / 'settings.json').read_text())['language'], 'auto')
            self.assertEqual(lang.resolve_language('auto', ['ko_KR']), 'ko')

    def test_terminal_translation_keeps_values_and_desktop_semantics(self):
        lang = self.language()
        from cytv.terminal import Console
        from cytv.desktop import Channel
        lang.set_language('ru')
        lines = []
        Console(lines.append).heading('Connect to your TV')
        self.assertIn('Подключение', '\n'.join(lines))
        self.assertEqual(lang.translate('Read 17 applications.'), 'Прочитано приложений: 17.')
        events = []
        channel = Channel(lambda *event: events.append(event))
        channel.answer('n')
        self.assertEqual(channel.ask('Connect and remember this TV? [Y/n]: '), 'n')
        prompt = events[-1][1]
        self.assertEqual((prompt.kind, prompt.default), ('confirm', 'y'))

    def test_cli_language_help_and_cancel(self):
        lang = self.language()
        from cytv.cli import main
        with tempfile.TemporaryDirectory() as directory:
            lines = []
            code = main(['--language', 'ru', '--data-dir', directory, '--no-discovery'], ask=lambda _: 'q', write=lines.append)
            self.assertEqual(code, 130)
            self.assertIn('Отменено', '\n'.join(lines))

    def test_failed_preference_save_keeps_active_language_and_cli_reports_error(self):
        lang = self.language()
        from unittest.mock import patch
        from cytv.cli import main
        lang.set_language('en')
        with tempfile.TemporaryDirectory() as directory, patch('cytv.state.private_write', side_effect=OSError('readonly')):
            with self.assertRaises(OSError):
                lang.configure('ru', directory)
            self.assertEqual(lang.language_choice(), 'en')
            lines = []
            self.assertEqual(main(['--language', 'ru', '--data-dir', directory, '--version'], write=lines.append), 2)
            self.assertIn('языка', '\n'.join(lines))

    def test_help_is_translated_and_patterns_do_not_consume_english_instructions(self):
        lang = self.language()
        from cytv.cli import main
        from contextlib import redirect_stdout
        import io
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()) as output:
            with self.assertRaises(SystemExit) as result:
                main(['--language', 'ru', '--data-dir', directory, '--help'])
            self.assertEqual(result.exception.code, 0)
        self.assertNotIn('Print installer version', output.getvalue())
        self.assertIn('версию', output.getvalue())
        lang.set_language('ru')
        self.assertNotIn('search again', lang.translate('Enter a number from 0 to 4, r to search again, or q to quit.'))

    def test_catalogs_keep_interpolation_fields_for_every_language(self):
        lang = self.language()
        from string import Formatter
        for source, translations in lang.MESSAGES.items():
            fields = {name for _, name, _, _ in Formatter().parse(source) if name}
            self.assertEqual(set(translations), set(lang.LANGUAGES) - {'en', 'auto'})
            for code, value in translations.items():
                with self.subTest(source=source, language=code):
                    self.assertTrue(value.strip())
                    self.assertEqual({name for _, name, _, _ in Formatter().parse(value) if name}, fields)

    def test_catalog_rows_have_unique_canonical_messages(self):
        from collections import Counter
        from cytv.translations import ROWS
        keys = Counter(row.split('|')[0] for row in ROWS.splitlines() if row.strip())
        self.assertEqual([key for key, count in keys.items() if count > 1], [])

    def test_bounded_cleanup_details_translate_in_every_locale(self):
        from cytv.recovery_ui import REMOVAL_STAGES, REMOVAL_BLOCKERS
        lang = self.language()
        messages = set(REMOVAL_STAGES.values()) | set(REMOVAL_BLOCKERS.values())
        for code in set(lang.LANGUAGES) - {'en','auto'}:
            lang.set_language(code)
            for message in messages - {''}:
                with self.subTest(language=code, message=message):
                    self.assertIn(message, lang.MESSAGES)
                    self.assertNotEqual(lang.translate(message), message)

    def test_short_desktop_password_titles_are_translated_without_changing_identifiers(self):
        lang = self.language()
        from cytv.desktop import Prompt
        lang.set_language('ru')
        prompt = Prompt('SSH key passphrase: ', secret=True)
        self.assertEqual(lang.translate(prompt.title), 'Кодовая фраза SSH-ключа')
        self.assertEqual(prompt.kind, 'secret')

    def test_all_static_installer_messages_have_complete_translations(self):
        import ast
        import re
        lang = self.language()
        for path in (Path(__file__).resolve().parents[2] / 'cytv').glob('*.py'):
            if path.stem in ('translations', 'i18n'):
                continue
            for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
                if not isinstance(node, ast.Call) or not node.args:
                    continue
                name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ''
                if name not in ('write', 'progress', 'heading', 'error', 'text', 'confirm', 'UserError', 'ExistingRoot', 'TVNotReady'):
                    continue
                arg = node.args[0]
                if not isinstance(arg, ast.Constant) or not isinstance(arg.value, str) or len(arg.value) < 9:
                    continue
                source = arg.value.replace(' | ', ' / ')
                if source in lang.MESSAGES:
                    continue
                for sentence in re.split(r'(?<=[.!?]) +', source):
                    if not any(c.isalpha() for c in sentence):
                        continue
                    for code in set(lang.LANGUAGES) - {'en', 'auto'}:
                        lang.set_language(code)
                        with self.subTest(file=path.name, line=node.lineno, language=code, text=sentence):
                            self.assertNotEqual(lang.translate(sentence), sentence)

    def test_neutral_edition_guidance_is_translated_in_every_language(self):
        lang = self.language()
        messages = (
            'No-root and Root are equal options for different TV setups.',
            'This installer does not obtain root.',
            'Enter = current choice   /   q = quit',
        )
        for code in set(lang.LANGUAGES) - {'en', 'auto'}:
            lang.set_language(code)
            for message in messages:
                with self.subTest(language=code, message=message):
                    self.assertNotEqual(lang.translate(message), message)

    def test_package_removal_progress_preserves_app_id_in_every_language(self):
        lang = self.language()
        message = 'Removing com.cleanyourtv.root.updater…'
        for code in set(lang.LANGUAGES) - {'en', 'auto'}:
            lang.set_language(code)
            self.assertNotEqual(lang.translate(message), message)
            self.assertIn('com.cleanyourtv.root.updater', lang.translate(message))
