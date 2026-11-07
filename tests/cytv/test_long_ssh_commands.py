"""Exercise bounded SSH exec requests with a real local shell and binary stdin."""
import hashlib
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import unittest

from cytv.errors import TVCommandError
from cytv.transport import SSH


class LocalChannel:
    def __init__(self, command):
        if len(command.encode()) > 4096:
            raise EOFError('SSH server rejected oversized exec request')
        self.command, self.input, self.closed = command, b'', False

    def sendall(self, data):
        self.input += data

    def shutdown_write(self):
        shell = Path('/bin/sh')
        if sys.platform == 'win32':
            git = shutil.which('git')
            if git is None:
                raise RuntimeError('Git for Windows is required for the local POSIX shell fixture')
            # Both Git/bin/git.exe and Git/cmd/git.exe belong to this installation.
            # Do not use a PATH bash.exe, which may be the Windows WSL launcher.
            shell = Path(git).resolve().parent.parent / 'bin' / 'sh.exe'
        result = subprocess.run([str(shell), '-c', self.command], input=self.input,
                                capture_output=True, timeout=10)
        self.stdout, self.stderr, self.status = result.stdout, result.stderr, result.returncode

    def recv_ready(self): return bool(self.stdout)
    def recv_stderr_ready(self): return bool(self.stderr)
    def exit_status_ready(self): return True
    def recv_exit_status(self): return self.status
    def recv(self, size):
        result, self.stdout = self.stdout[:size], self.stdout[size:]
        return result
    def recv_stderr(self, size):
        result, self.stderr = self.stderr[:size], self.stderr[size:]
        return result
    def close(self): self.closed = True


class LongSSHCommands(unittest.TestCase):
    def remote(self):
        remote = SSH(None)
        def channel(command):
            remote.last_channel = LocalChannel(command)
            return remote.last_channel
        remote.channel = channel
        return remote

    def test_long_command_preserves_binary_input_and_empty_stdin(self):
        code = 'import sys,hashlib;print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest())'
        command = shlex.join([Path(sys.executable).as_posix(), '-c', code]) + '\n# ' + 'padding' * 5000
        for data in (None, b'', bytes(range(256)) * 10000 + b'\nPRIVATE\x00\xff'):
            with self.subTest(data_size=len(data or b'')):
                remote = self.remote()
                self.assertEqual(remote.run(command, data=data).strip(), hashlib.sha256(data or b'').hexdigest())
                self.assertTrue(remote.last_channel.closed)

    def test_long_command_preserves_exit_and_storage_error_category(self):
        remote = self.remote()
        with self.assertRaises(TVCommandError) as caught:
            remote.run('printf "No space left on device: PRIVATE" >&2; exit 9\n# ' + 'x' * 40000)
        self.assertEqual(caught.exception.reason_code, 'tv-storage-full')
        self.assertNotIn('PRIVATE', str(caught.exception))
        self.assertTrue(remote.last_channel.closed)

    def test_long_command_preserves_trailing_newline_in_shell_source(self):
        remote = self.remote()
        command = '# ' + 'padding' * 5000 + '\nprintf preserved\\\n'
        self.assertEqual(remote.run(command), 'preserved')

    def test_short_command_keeps_original_exec_request(self):
        remote = self.remote()
        self.assertEqual(remote.run('printf short'), 'short')
        self.assertEqual(remote.last_channel.command, 'printf short')
