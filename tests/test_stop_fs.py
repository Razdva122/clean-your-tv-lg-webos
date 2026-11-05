"""Compile and exercise the fixed-domain C adapter; no device or dependencies."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CASES = (
    'empty', 'publish', 'unbound', 'mismatch-owner', 'mismatch-group', 'mismatch-producer',
    'repair', 'publisher-no-repair', 'directory-replace', 'directory-symlink',
    'invalid-symlink', 'invalid-fifo', 'invalid-hardlink', 'invalid-unknown',
    'invalid-mode', 'invalid-special', 'invalid-oversize', 'invalid-partial', 'invalid-start', 'invalid-id',
    'fifo-race', 'remove-race', 'record-race', 'directory-race', 'collision',
    'full', 'overflow', 'concurrent', 'concurrent-partial', 'retained-fd', 'file-sync-fail', 'dir-sync-fail',
    'publish-replace', 'publish-corrupt', 'publish-mode', 'cut-create', 'cut-write',
    'cut-file-sync', 'cut-dir-sync', 'bad-nonce',
)


class StopFsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='cytv-stop-fs-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.base = Path(cls.temp.name)
        cls.fixture = cls.base / 'fixture'
        cls.binary = cls.base / 'stop-fs-test'
        cls.flags = ['-std=c11', '-Wall', '-Wextra', '-Werror', '-g']
        if os.environ.get('CYTV_STOP_TEST_SANITIZE') == '1':
            cls.flags += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
        command = [os.environ.get('CC', 'cc'), *cls.flags,
                   '-I', str(ROOT / 'native/app'), '-DCYTV_STOP_TEST_BUILD',
                   '-DCYTV_STOP_TEST_PATH="' + str(cls.fixture / 'inbox') + '"',
                   str(ROOT / 'native/app/stop-fs.c'), str(ROOT / 'tests/stop_fs_test.c'),
                   '-o', str(cls.binary)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)

    def setUp(self):
        shutil.rmtree(self.fixture, ignore_errors=True)
        (self.fixture / 'inbox').mkdir(parents=True)

    def test_path_override_requires_explicit_test_build(self):
        result = subprocess.run(
            [os.environ.get('CC', 'cc'), *self.flags,
             '-DCYTV_STOP_TEST_PATH="/tmp/not-a-production-path"', '-c',
             str(ROOT / 'native/app/stop-fs.c'), '-o', str(self.base / 'invalid.o')],
            capture_output=True, text=True, timeout=60)
        self.assertNotEqual(result.returncode, 0, 'production path must not be overridable')


def test_case(name):
    def run(self):
        result = subprocess.run([str(self.binary), name], capture_output=True,
                                text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), 'PASS')
    return run


for case in CASES:
    setattr(StopFsTests, 'test_' + case.replace('-', '_'), test_case(case))


if __name__ == '__main__':
    unittest.main()
