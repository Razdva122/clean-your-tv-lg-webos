"""Run the TV shell probe against a local /proc fixture; never contact a TV."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from cytv.operations import Installer, HELPER_STATE
from cytv.errors import UserError


class HelperPreflightTests(unittest.TestCase):
    def probe(self, pid=None, processes=None, symlink=False, grep_error=False, legacy_grep=False):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        state = root / 'state'
        state.mkdir()
        proc = root / 'proc'
        proc.mkdir()
        if symlink:
            (state / 'controller.pid').symlink_to(root / 'missing')
        elif pid is not None:
            (state / 'controller.pid').write_text(pid)
        for number, args in (processes or {}).items():
            directory = proc / str(number)
            directory.mkdir()
            (directory / 'cmdline').write_bytes(args)
        class Remote:
            def run(_, command):
                if 'CYTV_NODE_READY' in command: return 'CYTV_NODE_READY'
                if command == 'uname -m': return 'armv7l'
                if command.startswith('LC_ALL=C od '):
                    return '127 69 76 70 1 1 1 0 0 0 0 0 0 0 0 0 2 0 40 0'
                if 'CYTV_ROOT_STATE' in command: return ''
                script = command.replace(HELPER_STATE, state.as_posix()).replace('/proc/', proc.as_posix() + '/')
                if legacy_grep:
                    # BusyBox 1.20.2 grep.c uses strstr for -F, ignoring -x.
                    # Include the real SSH shell command in the proc fixture.
                    own = proc / '999'
                    own.mkdir(exist_ok=True)
                    (own / 'cmdline').write_bytes(b'sh\0-c\0' + script.encode() + b'\0')
                    script = 'grep() { if [ "$1" = -Fx ]; then shift; command grep -F "$@"; else command grep "$@"; fi; }\n' + script
                if grep_error:
                    script = 'grep() { return 2; }\n' + script
                return subprocess.check_output(['sh', '-c', script], text=True)
        self.messages = []
        return Installer(Remote(), None, {'edition': 'no-root'}, '.', {}, self.messages.append)

    def test_dead_or_reused_pid_does_not_prevent_install(self):
        for processes in ({}, {123: b'unrelated\0'}):
            with self.subTest(processes=processes):
                self.probe('123', processes).preflight(install=True)
                self.assertTrue(any('stale' in message.lower() for message in self.messages))
                self.assertEqual((Path(self.tmp.name) / 'state/controller.pid').read_text(), '123')

    def test_live_controller_and_orphan_worker_block_before_install(self):
        for args in (b'com.local.nativehome\0',
                     b'node\0/media/developer/apps/usr/palm/applications/com.local.nativehome/native.js\0',
                     b'/media/developer/apps/usr/palm/applications/com.local.nativehome/relay\0'):
            with self.subTest(args=args):
                with self.assertRaisesRegex(UserError, 'running.*Installation has not started'):
                    self.probe(None, {123: args}).preflight(install=True)

    def test_invalid_or_symlink_pid_stays_blocked_without_deletion(self):
        for pid, symlink in (('../bad', False), (None, True)):
            with self.subTest(pid=pid):
                with self.assertRaisesRegex(UserError, 'could not be verified.*Installation has not started'):
                    self.probe(pid, symlink=symlink).preflight(install=True)
                self.assertTrue((Path(self.tmp.name) / 'state/controller.pid').is_symlink() or
                                (Path(self.tmp.name) / 'state/controller.pid').exists())

    def test_idle_tv_can_install(self):
        self.probe().preflight(install=True)

    def test_legacy_grep_does_not_match_ssh_probe_or_service(self):
        for processes in ({}, {123: b'node\0/usr/bin/run-js-service\0com.local.nativehome.service\0'}):
            with self.subTest(processes=processes):
                installer = self.probe(processes=processes, legacy_grep=True)
                self.assertEqual(installer.helper_state(), 'stopped')

    def test_legacy_grep_still_blocks_controller_and_relay(self):
        for args in (b'com.local.nativehome\0',
                     b'node\0/media/developer/apps/usr/palm/applications/com.local.nativehome/native.js\0',
                     b'/media/developer/apps/usr/palm/applications/com.local.nativehome/relay\0'):
            with self.subTest(args=args):
                self.assertEqual(self.probe(processes={123: args}, legacy_grep=True).helper_state(), 'running')

    def test_process_patterns_are_literal_whole_arguments(self):
        for args in (b'comXlocalXnativehome\0', b'com.local.nativehome.service\0',
                     b'/media/developer/apps/usr/palm/applications/com.local.nativehome/nativeXjs\0',
                     b'/media/developer/apps/usr/palm/applications/com.local.nativehome/relay-cleanup\0'):
            with self.subTest(args=args):
                self.assertEqual(self.probe(processes={123: args}).helper_state(), 'stopped')

    def test_empty_target_cmdline_or_missing_proc_is_uncertain(self):
        installer = self.probe('123', {123: b''})
        self.assertEqual(installer.helper_state(), 'uncertain')
        installer = self.probe()
        (Path(self.tmp.name) / 'proc').rmdir()
        self.assertEqual(installer.helper_state(), 'uncertain')

    def test_failed_process_matching_does_not_allow_replacement(self):
        installer = self.probe(None, {123: b'com.local.nativehome\0'}, grep_error=True)
        with self.assertRaisesRegex(UserError, 'could not be verified'):
            installer.preflight(install=True)
