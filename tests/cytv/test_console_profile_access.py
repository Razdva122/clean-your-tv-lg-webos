"""Exercise a denied saved profile through the actual console entrypoint."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from cytv import state
from tests.cytv.test_console_encoding import COMMAND, ROOT


@contextmanager
def deny_profile_read(path):
    if os.name != 'nt':
        path.chmod(0)
        try:
            yield
        finally:
            path.chmod(0o600)
        return

    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateFileW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                  ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel.CloseHandle.restype = wintypes.BOOL
    generic_read, exclusive, open_existing, normal = 0x80000000, 0, 3, 0x80
    handle = kernel.CreateFileW(str(path), generic_read, exclusive, None, open_existing, normal, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        yield
    finally:
        if not kernel.CloseHandle(handle):
            raise ctypes.WinError(ctypes.get_last_error())


class ConsoleProfileAccessTests(unittest.TestCase):
    @unittest.skipIf(os.name != 'nt' and os.geteuid() == 0,
                     'POSIX mode bits do not deny access to root')
    def test_denied_profile_exports_unobserved_report_and_preserves_identity(self):
        with tempfile.TemporaryDirectory(prefix='cytv-private-') as tmp:
            store = state.Store(tmp)
            host = '127.0.0.1'
            selected = state.target(host, 'root', 1, Path(tmp) / 'private-ssh-key')
            store.save(selected)
            store.begin(selected, 'activate-root', stage='enable')
            directory = store.device_dir(selected)
            profile = directory / 'profile.json'
            (directory / 'known_hosts').write_bytes(b'private original pin')
            original = {path: path.read_bytes() for path in directory.iterdir()}
            with deny_profile_read(profile):
                with self.assertRaises(PermissionError):
                    profile.read_bytes()
                result = subprocess.run([*COMMAND, 'status', '--non-interactive',
                                         '--host', host, '--edition', 'root', '--port', '1',
                                         '--language', 'en', '--data-dir', tmp], cwd=ROOT,
                                        stdin=subprocess.DEVNULL, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 2, (result.stdout, result.stderr))
            self.assertIn(b'saved TV connections could not be read', b' '.join(result.stdout.split()))
            path, = (Path(tmp) / 'reports').glob('*.json')
            text = path.read_text()
            report = json.loads(text)
            self.assertEqual(report['frontend'], 'console')
            self.assertEqual(report['phase'], 'select-tv')
            self.assertEqual(report['local_recovery'], {'reason': 'profile-access', 'location': 'profile'})
            self.assertNotIn('recovery', report)
            self.assertIsNone(report['pending'])
            self.assertEqual(report['tv'], {})
            self.assertEqual(report['checks'], {})
            self.assertFalse(list(Path(tmp).glob('session-*.lock')))
            self.assertEqual({file: file.read_bytes() for file in directory.iterdir()}, original)
            for private in (host, 'private-ssh-key', 'private original pin', Path(tmp).name):
                self.assertNotIn(private, text)
