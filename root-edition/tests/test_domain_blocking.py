import importlib.util
import os
from contextlib import nullcontext
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'runtime'))
spec = importlib.util.spec_from_file_location('blocking_runtime', ROOT/'runtime/cli.py')
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


class DomainBlockingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.hosts = self.root/'hosts'
        self.original = b'127.0.0.1 localhost\r\n# custom\n192.0.2.1 kitchen'
        self.hosts.write_bytes(self.original)
        self.table = self.root/'domain-blocking.hosts'
        self.mountinfo = self.root/'mountinfo'
        self.mountinfo.write_text('')
        self.blocker = runtime.DomainBlocker(self.root, self.hosts, self.mountinfo)
        self.uid = patch.object(runtime.d, 'EXPECTED_UID', os.getuid())
        self.uid.start()
        self.addCleanup(self.uid.stop)

    def test_default_status_and_old_removal_have_no_side_effects(self):
        self.assertEqual(self.blocker.apply('status'), 'off')
        self.assertEqual(self.blocker.apply('off'), 'off')
        self.assertEqual(self.blocker.apply('boot'), 'off')
        self.assertFalse(self.table.exists())

    def test_bind_failure_retains_explicit_choice_and_off_restores_original(self):
        with patch.object(self.blocker, 'mount', side_effect=OSError):
            with self.assertRaises(OSError):
                self.blocker.apply('on')
        self.assertEqual(self.blocker.apply('status'), 'pending')
        result = self.table.read_bytes()
        self.assertTrue(result.startswith(self.original + b'\n'))
        for name in runtime.BLOCKED_HOSTS:
            self.assertIn(b'0.0.0.0 ' + name.encode() + b'\n', result)
            self.assertIn(b':: ' + name.encode() + b'\n', result)
        self.assertEqual(self.blocker.apply('off'), 'off')
        self.assertEqual(self.hosts.read_bytes(), self.original)

    def test_foreign_mount_and_conflicting_host_mapping_are_preserved(self):
        self.mountinfo.write_text('9 1 0:8 /third-party ' + str(self.hosts) + ' rw - tmpfs tmpfs rw\n')
        for operation in ('status', 'on', 'off'):
            self.assertEqual(self.blocker.apply(operation), 'external')
        self.mountinfo.write_text('')
        self.hosts.write_bytes(b'192.0.2.3 Ad.LgAppsTV.COM.\n')
        with self.assertRaises(ValueError):
            self.blocker.apply('on')
        self.assertFalse(self.table.exists())

    def test_reboot_rebuilds_from_current_configuration_without_overwriting_drift(self):
        with patch.object(self.blocker, 'mount', side_effect=OSError):
            with self.assertRaises(OSError):
                self.blocker.apply('on')
            self.hosts.write_bytes(b'127.0.0.1 localhost\n# new firmware defaults\n')
            with self.assertRaises(OSError):
                self.blocker.apply('boot')
        self.assertTrue(self.table.read_bytes().startswith(self.hosts.read_bytes()))
        self.table.chmod(0o644)
        self.table.write_bytes(b'foreign configuration')
        for operation in ('boot', 'off', 'on'):
            with self.assertRaises(ValueError):
                self.blocker.apply(operation)
        self.assertEqual(self.table.read_bytes(), b'foreign configuration')

    def test_indirect_source_or_target_is_refused(self):
        self.table.symlink_to(self.hosts)
        with self.assertRaises((OSError, ValueError)):
            self.blocker.apply('on')
        self.assertEqual(self.hosts.read_bytes(), self.original)

    def test_foreign_layer_never_gets_unmounted_by_off_or_boot(self):
        with patch.object(self.blocker, 'mount', side_effect=OSError):
            with self.assertRaises(OSError):
                self.blocker.apply('on')
        row = '9 1 0:8 /third-party ' + str(self.hosts) + ' rw - tmpfs tmpfs rw\n'
        self.mountinfo.write_text(row + row)
        with patch.object(self.blocker, 'mount') as mount:
            self.assertEqual(self.blocker.apply('off'), 'external')
            self.assertTrue(self.table.exists())
            self.mountinfo.write_text(row)
            self.assertEqual(self.blocker.apply('boot'), 'displaced')
            self.assertEqual(self.blocker.apply('off'), 'external')
            self.assertFalse(self.table.exists())
            mount.assert_not_called()

    def test_boot_replays_only_an_opt_in_on_confirmed_normal_startup(self):
        import boot_gate
        import update_guard
        with (patch.object(runtime.d, 'STATE', self.root),
              patch.object(runtime.os, 'geteuid', return_value=0),
              patch.object(update_guard, 'control', return_value=nullcontext()),
              patch.object(runtime, 'execute', return_value='restored'),
              patch.object(runtime, 'domain_blocking') as control,
              patch.object(boot_gate, 'observation') as observe):
            self.assertEqual(runtime.main('boot'), 'restored')
            observe.assert_not_called()
            self.table.touch()
            observe.return_value = (True, True)
            self.assertEqual(runtime.main('boot'), 'restored')
            control.assert_not_called()
            observe.return_value = (True, False)
            control.side_effect = OSError('No mount support')
            self.assertEqual(runtime.main('boot'), 'restored')
            control.assert_called_once_with('boot', self.root)

    def test_recovery_requires_own_table_to_be_released(self):
        self.table.touch()
        with (patch.object(runtime.os.path, 'samefile', return_value=True),
              patch.object(runtime.DomainBlocker, 'apply', return_value='external')):
            with self.assertRaises(ValueError):
                runtime.domain_blocking('off', self.root, required=True)
        self.table.unlink()
        self.assertEqual(runtime.domain_blocking('off', self.root, required=True), 'off')
