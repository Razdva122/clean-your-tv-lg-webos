import unittest
import io
from unittest.mock import patch

from cytv.terminal import Console


class TerminalTests(unittest.TestCase):
    def test_issue_draft_browser_requires_opt_in_and_leaves_a_link_if_unavailable(self):
        from urllib.parse import parse_qs, urlparse

        draft = {'title': '[cytv] Установка / 電視 & Home', 'body': 'My own observation'}
        for answer in ('', 'q', 'y'):
            with self.subTest(answer=answer):
                lines = []
                ui = Console(lines.append, interactive=True)
                with patch('cytv.terminal.webbrowser.open', return_value=False) as browser:
                    ui.issue(draft, ask=lambda _: answer)
                self.assertIn(draft['title'], lines)
                self.assertIn(draft['body'], lines)
                link = next(line for line in lines if line.startswith('https://github.com/'))
                self.assertEqual(parse_qs(urlparse(link).query),
                                 {'template': ['cytv.yml'], 'title': [draft['title']]})
                if answer == 'y':
                    browser.assert_called_once_with(link)
                    self.assertIn('Could not open the browser', '\n'.join(lines))
                else:
                    browser.assert_not_called()

    def test_failed_noninteractive_console_prepares_a_draft_without_a_diagnostic(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import Mock
        from cytv import cli, i18n

        self.addCleanup(i18n.set_language, i18n.resolved_language())

        lines = []
        connect = Mock(side_effect=OSError('PRIVATE TRANSPORT'))
        ask = Mock(side_effect=AssertionError('Unexpected prompt'))
        ui = Console(lines.append, interactive=True)
        with TemporaryDirectory() as directory, \
             patch('cytv.diagnostics.create_report', side_effect=OSError('PRIVATE REPORT PATH')), \
             patch('cytv.terminal.webbrowser.open') as browser:
            code = cli.main(['status', '--host', '192.0.2.55', '--edition', 'root',
                             '--non-interactive', '--language', 'en', '--data-dir', directory],
                            connect=connect, ask=ask, write=ui)
            self.assertEqual(list(Path(directory).glob('reports/*.json')), [])
        self.assertEqual(code, 1)
        output = '\n'.join(lines)
        self.assertIn('template=cytv.yml', output)
        self.assertIn('Reason: unknown', output)
        self.assertIn('Include the visible error', output)
        self.assertNotIn('PRIVATE', output)
        connect.assert_called_once()
        ask.assert_not_called()
        browser.assert_not_called()

    def test_json_result_requires_no_input_and_retains_the_exit_code(self):
        import json
        from tempfile import TemporaryDirectory
        from unittest.mock import Mock
        from cytv import cli, i18n

        self.addCleanup(i18n.set_language, i18n.language_choice())
        ask = Mock(side_effect=AssertionError('Unexpected prompt'))
        lines = []
        with TemporaryDirectory() as directory:
            code = cli.main(['status', '--result-json', '--language', 'en', '--data-dir', directory],
                            ask=ask, secret=ask, write=lines.append)
        self.assertEqual(code, 2)
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])['outcome']['state'], 'owner-input-required')
        self.assertEqual(json.loads(lines[0])['exit_code'], code)
        ask.assert_not_called()

    def test_argument_errors_use_red_stderr(self):
        from cytv.cli import LanguageParser
        output = io.StringIO()
        with patch('cytv.cli.sys.stderr', output), patch('cytv.cli.supports_ansi', return_value=True), \
             patch.dict('os.environ', {}, clear=True), self.assertRaises(SystemExit):
            LanguageParser(prog='cytv').parse_args(['--unknown'])
        self.assertIn('\x1b[31m', output.getvalue())

    def test_errors_are_red_only_when_color_is_supported(self):
        for color in (True, False):
            lines = []
            ui = Console(lines.append, width=42, interactive=color, color=color)
            ui.error('Could not complete this step', heading=True)
            ui.error('Failure details <not markup>')
            output = '\n'.join(lines)
            self.assertIn('Failure details', output)
            self.assertEqual('\x1b[31m' in output, color)
            self.assertEqual('\x1b[31m' in lines[-1], color)

    def test_plain_output_has_hierarchy_and_wraps_to_small_terminal(self):
        lines = []
        ui = Console(lines.append, width=42, interactive=False)
        ui.step(2, 'Choose your edition')
        ui.option('1', 'No-root', 'For a TV without root. Uses LG Developer Mode.')
        self.assertIn('STEP 2 / 6', '\n'.join(lines))
        self.assertIn('[1] No-root', '\n'.join(lines))
        self.assertNotIn('\x1b', '\n'.join(lines))
        self.assertTrue(all(len(line) <= 42 for text in lines for line in text.splitlines()))
        self.assertTrue(ui.prompt('Edition [1]: ').startswith('\n  > '))

    def test_real_terminal_starts_new_step_without_erasing_scrollback(self):
        lines = []
        ui = Console(lines.append, width=72, interactive=True, color=True)
        ui.step(2, 'Choose your edition')
        self.assertIn('\x1b[2J\x1b[H', '\n'.join(lines))
        self.assertNotIn('\x1b[3J', '\n'.join(lines))
        self.assertTrue(lines[0].startswith('\n\n'))
        self.assertIn('\x1b[1m', '\n'.join(lines))


if __name__ == '__main__':
    unittest.main()
