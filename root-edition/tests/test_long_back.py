import sys, unittest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
from emergency_gesture import LongBack
class Tests(unittest.TestCase):
 def test_hold_fires_once_without_repeats(self):
  p=LongBack();p.event(1,412,1,100)
  self.assertFalse(p.tick(1299));self.assertTrue(p.tick(1300));self.assertFalse(p.tick(1500))
  p.event(1,412,0,1600);p.event(1,412,1,2000);self.assertTrue(p.tick(3200))
 def test_short_press_and_orphan_repeat_do_not_exit(self):
  p=LongBack();p.event(1,412,1,100);p.event(1,412,0,200);self.assertFalse(p.tick(2000))
  p.event(1,412,2,3000);self.assertFalse(p.tick(5000))


class PreferenceTests(unittest.TestCase):
    def setUp(self):
        import cli
        self.command = lambda operation: cli.execute('long-back', operation)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        for name, value in [('STATE', self.root), ('EXPECTED_UID', os.getuid())]:
            setting = patch.object(cli.d, name, value)
            setting.start()
            self.addCleanup(setting.stop)
        selector = patch.object(cli, 'gate_backend', return_value=None)
        selector.start()
        self.addCleanup(selector.stop)

    def test_existing_installation_defaults_on_and_changes_survive_readback(self):
        self.assertEqual(self.command('status'), {'longBackOpensHome': True})
        self.assertEqual(list(self.root.iterdir()), [])
        for operation, enabled in [('off', False), ('on', True)]:
            expected = {'longBackOpensHome': enabled}
            self.assertEqual(self.command(operation), expected)
            self.assertEqual(self.command('status'), expected)
        self.assertEqual((self.root/'long-back.json').stat().st_mode & 0o777, 0o600)

    def test_failed_write_preserves_previous_setting(self):
        self.command('off')
        with patch.object(os, 'replace', side_effect=OSError('full disk')), self.assertRaises(OSError):
            self.command('on')
        self.assertEqual(self.command('status'), {'longBackOpensHome': False})

    def test_switching_off_and_on_invalidates_only_the_original_hold(self):
        import device_adapter as d
        self.command('off')
        self.command('on')
        _, original = d.long_back_preference()
        self.command('on')
        self.assertEqual(d.long_back_preference(), (True, original))
        self.command('off')
        self.command('on')
        self.assertNotEqual(d.long_back_preference()[1], original)
