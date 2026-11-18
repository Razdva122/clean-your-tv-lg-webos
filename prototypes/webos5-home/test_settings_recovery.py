"""Host-only tests. The settings file models a separate process's durable DB."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import settings_recovery as recovery


class SettingsRecoveryTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        self.defaults = self.root / 'default-apps.json'
        self.journal = self.root / 'home-journal.json'

    def write(self, value):
        self.defaults.write_text(json.dumps(value))

    def read(self):
        return json.loads(self.defaults.read_text())

    def test_process_loss_after_write_restores_both_stock_styles(self):
        for stock in ('com.webos.app.home', 'com.webos.app.fullhome'):
            with self.subTest(stock=stock):
                self.write({'home': stock, 'music': 'original'})
                launcher = subprocess.run(
                    [sys.executable, '-c', """
import json, os, sys
from pathlib import Path
from settings_recovery import enable
settings, journal = map(Path, sys.argv[1:])
def write(record):
    settings.write_text(json.dumps(record))
    os._exit(23)
enable(journal, lambda: json.loads(settings.read_text()), write, explicit=True)
""", str(self.defaults), str(self.journal)], cwd=Path(__file__).parent, check=False)
                self.assertEqual(launcher.returncode, 23)
                self.assertEqual(self.read()['home'], 'com.cleanyourtv.root.preview')
                self.write(dict(self.read(), music='changed'))
                self.assertEqual(recovery.restore(self.journal, self.read, self.write), 'restored')
                self.assertEqual(self.read(), {'home': stock, 'music': 'changed'})
                self.assertEqual(recovery.restore(self.journal, self.read, self.write), 'restored')

    def test_stop_vetoes_enable_until_a_new_explicit_attempt(self):
        self.write({'home': 'com.webos.app.home'})
        recovery.enable(self.journal, self.read, self.write, explicit=True)
        recovery.restore(self.journal, self.read, self.write)
        with self.assertRaisesRegex(ValueError, 'explicit Enable'):
            recovery.enable(self.journal, self.read, self.write)
        self.assertEqual(self.read()['home'], 'com.webos.app.home')
        recovery.enable(self.journal, self.read, self.write, explicit=True)
        self.assertEqual(self.read()['home'], 'com.cleanyourtv.root.preview')

    def test_foreign_choice_survives_restore(self):
        self.write({'home': 'com.webos.app.home'})
        recovery.enable(self.journal, self.read, self.write, explicit=True)
        self.write({'home': 'org.example.home'})
        with self.assertRaisesRegex(ValueError, 'changed'):
            recovery.restore(self.journal, self.read, self.write)
        self.assertEqual(self.read()['home'], 'org.example.home')
        self.assertTrue(self.journal.exists())

    def test_missing_stock_override_never_grants_a_write(self):
        self.write({'music': 'keep'})
        with self.assertRaisesRegex(ValueError, 'stock'):
            recovery.enable(self.journal, self.read, self.write, explicit=True)
        self.assertEqual(self.read(), {'music': 'keep'})
        self.assertFalse(self.journal.exists())

    def test_restore_reconciles_a_lost_ack_without_repeating_the_write(self):
        self.write({'home': 'com.webos.app.fullhome'})
        recovery.enable(self.journal, self.read, self.write, explicit=True)
        calls = []

        def write_without_ack(record):
            calls.append(record)
            self.write(record)
            raise TimeoutError('no reply')

        self.assertEqual(recovery.restore(self.journal, self.read, write_without_ack), 'restored')
        self.assertEqual(recovery.restore(self.journal, self.read, write_without_ack), 'restored')
        self.assertEqual(calls, [{'home': 'com.webos.app.fullhome'}])


if __name__ == '__main__':
    unittest.main()
