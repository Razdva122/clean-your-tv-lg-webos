"""Exercise denied-service recovery using real Node/filesystem I/O, never a TV."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from cytv.errors import TVRejected, UserError
from cytv.operations import Installer, HELPER, HELPER_STATE


@unittest.skipIf(os.name == 'nt', 'The TV program uses POSIX ownership and permissions')
class HelperStopTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / HELPER
        self.directory = self.root / 'state'
        self.directory.mkdir(parents=True, mode=0o770)
        self.directory.chmod(0o770)
        self.calls = []
        self.error = TVRejected('denied', {'returnValue': False, 'errorCode': -1},
                                'com.local.nativehome.service/disable')
        self.stuck = False
        outer = self

        class Remote:
            def luna(self, uri, payload):
                outer.calls.append(uri)
                if uri.endswith('/dev/listApps'):
                    return {'apps': [{'id': HELPER}]}
                if uri.endswith('/disable'):
                    raise outer.error
                return {'returnValue': True}

            def run(self, command, data=None, timeout=30):
                outer.calls.append(command)
                if command == '/usr/bin/node':
                    code = data.decode().replace(HELPER_STATE, str(outer.directory))
                    code = code.replace(HELPER_STATE.rsplit('/', 1)[0], str(outer.root))
                    result = subprocess.run([os.environ.get('NODE010', 'node')], input=code, text=True,
                                            capture_output=True, check=True)
                    return result.stdout
                if 'CYTV_HELPER_IDLE' in command:
                    stopped = (outer.directory / 'blocked').exists() and (outer.directory / 'control.json').exists()
                    return 'CYTV_HELPER_ACTIVE' if outer.stuck or not stopped else 'CYTV_HELPER_IDLE'
                raise AssertionError(command)

        self.installer = Installer(Remote(), None, {'edition': 'no-root'}, '.', {}, lambda *_: None)

    def test_denied_disable_latches_stop_before_confirming_processes_gone(self):
        (self.directory / 'home-control.json').write_text('{"enabled":true}')
        (self.directory / 'watchdog').write_text('retained')
        self.installer.stop_helper()
        self.assertEqual((self.directory / 'blocked').read_text(), 'stopped')
        self.assertTrue((self.directory / 'blocked').stat().st_mode & 0o020,
                        'a controller with another UID in the shared group must be able to rewrite the stop latch')
        self.assertEqual((self.directory / 'blocked').stat().st_gid, self.directory.stat().st_gid)
        self.assertEqual(json.loads((self.directory / 'control.json').read_text()), {'cmd': 'stop'})
        self.assertEqual((self.directory / 'home-control.json').read_text(), '{"enabled":true}')
        self.assertEqual((self.directory / 'watchdog').read_text(), 'retained')
        self.assertLess(self.calls.index('/usr/bin/node'), next(i for i, c in enumerate(self.calls) if 'CYTV_HELPER_IDLE' in c))

    def test_existing_stop_latch_is_preserved(self):
        (self.directory / 'blocked').write_text('existing emergency stop')
        self.installer.stop_helper()
        self.assertEqual((self.directory / 'blocked').read_text(), 'existing emergency stop')

    def test_unknown_outcome_and_other_rejection_never_trigger_fallback(self):
        for error in [UserError('timeout'), TVRejected('other', {'errorCode': -101}),
                      TVRejected('other', {'errorCode': -1})]:
            with self.subTest(error=error):
                self.error = error
                with self.assertRaises(UserError):
                    self.installer.stop_helper()
                self.assertFalse((self.directory / 'blocked').exists())
                self.assertFalse((self.directory / 'control.json').exists())

    def test_unsafe_state_or_stop_files_fail_without_touching_symlink_target(self):
        target = Path(self.tmp.name) / 'private'
        target.write_text('untouched')
        for name in ['blocked', 'control.json']:
            with self.subTest(name=name):
                link = self.directory / name
                link.symlink_to(target)
                with self.assertRaises((RuntimeError, subprocess.CalledProcessError)):
                    self.installer.stop_helper()
                self.assertEqual(target.read_text(), 'untouched')
                link.unlink()

    def test_running_or_orphaned_worker_never_confirms_stop(self):
        self.stuck = True
        with patch('cytv.operations.time.sleep'), self.assertRaises(UserError):
            self.installer.stop_helper()
        self.assertTrue((self.directory / 'blocked').exists())

    def test_root_keeps_original_failure_instead_of_using_no_root_fallback(self):
        self.installer.profile['edition'] = 'root'
        with self.assertRaises(TVRejected):
            self.installer.stop_helper()
        self.assertFalse((self.directory / 'blocked').exists())

    def test_world_writable_state_and_symlinked_state_are_refused(self):
        self.directory.chmod(0o777)
        with self.assertRaises(subprocess.CalledProcessError):
            self.installer.stop_helper()
        self.assertFalse((self.directory / 'blocked').exists())
        self.directory.chmod(0o770)
        real = self.root / 'real-state'
        self.directory.rename(real)
        self.directory.symlink_to(real, target_is_directory=True)
        with self.assertRaises(subprocess.CalledProcessError):
            self.installer.stop_helper()
        self.assertEqual(list(real.iterdir()), [])
