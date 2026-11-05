"""The developer entry point validates locally before any SSH effect."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location('c1_setup', ROOT/'setup_gate.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class SetupTests(unittest.TestCase):
    def test_unreviewed_install_never_connects(self):
        run = Mock()
        with patch('setup.ssh_options', return_value=['test-tv']), \
                patch('deploy.verify_bundle', side_effect=ValueError('not experimental')):
            with self.assertRaises(ValueError):
                setup.execute('install', 'test-tv', ROOT, run=run)
        run.assert_not_called()

    def test_recovery_uses_retained_driver_and_explicit_backend(self):
        run = Mock()
        with patch('setup.ssh_options', return_value=['test-tv']):
            setup.execute('restore', 'test-tv', run=run)
        argv = run.call_args.args[0]
        self.assertEqual(argv[:2], ['ssh', 'test-tv'])
        self.assertIn('/var/lib/clean-your-tv-root/deploy.py restore --experimental-c1-gate', argv[-1])
        self.assertIn('unset PYTHONHOME PYTHONPATH', argv[-1])

    def test_unsupported_mode_never_connects(self):
        run = Mock()
        with self.assertRaises(ValueError):
            setup.execute('update', 'test-tv', run=run)
        run.assert_not_called()
