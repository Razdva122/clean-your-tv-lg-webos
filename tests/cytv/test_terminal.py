import unittest
import io
from unittest.mock import patch

from cytv.terminal import Console


class TerminalTests(unittest.TestCase):
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
