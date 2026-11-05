"""Real host filesystem/process tests; compile-time isolated paths only."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CASES = ('acquire', 'contention', 'missing-lock', 'missing-journal', 'root-mode',
         'journal-mode', 'lock-mode', 'lock-link', 'lock-fifo', 'lock-hardlink',
         'owner', 'group', 'inode', 'unbound', 'adopt-unlocked', 'adopt-other',
         'adopt-readonly', 'adopt-cloexec', 'adopt-shared', 'adopt-shared-other', 'wrong-fd', 'lifecycle', 'nested',
         'wrong-pid', 'replacement', 'exec-inherit', 'exec-unrelated', 'stop-independent',
         'fork-discard', 'root-replace', 'journal-replace')

class PrivateIoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='cytv-private-io-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.base = Path(cls.temp.name)
        cls.fixture = cls.base / 'fixture'
        cls.binary = cls.base / 'lease-test'
        cls.flags = ['-std=c11', '-Wall', '-Wextra', '-Werror', '-g']
        if os.environ.get('CYTV_PRIVATE_TEST_SANITIZE') == '1':
            cls.flags += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
        command = [os.environ.get('CC', 'cc'), *cls.flags,
                   '-I', str(ROOT / 'native/app'), '-DCYTV_PRIVATE_TEST_BUILD',
                   '-DCYTV_PRIVATE_TEST_ROOT="' + str(cls.fixture / 'private') + '"',
                   '-DCYTV_STOP_TEST_BUILD',
                   '-DCYTV_STOP_TEST_PATH="' + str(cls.fixture / 'stop') + '"',
                   str(ROOT / 'native/app/private-lease.c'),
                   str(ROOT / 'native/app/stop-fs.c'),
                   str(ROOT / 'tests/private_lease_test.c'), '-o', str(cls.binary)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)

    def setUp(self):
        shutil.rmtree(self.fixture, ignore_errors=True)
        (self.fixture / 'private').mkdir(parents=True)

    def test_override_requires_test_build(self):
        result = subprocess.run([os.environ.get('CC', 'cc'), *self.flags,
            '-DCYTV_PRIVATE_TEST_ROOT="/tmp/not-production"', '-c',
            str(ROOT / 'native/app/private-lease.c'), '-o', str(self.base/'invalid.o')],
            capture_output=True, text=True, timeout=60)
        self.assertNotEqual(result.returncode, 0)


def case_test(name):
    def run(self):
        result = subprocess.run([str(self.binary), name], capture_output=True,
                                text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), 'PASS')
    return run

for case in CASES:
    setattr(PrivateIoTests, 'test_' + case.replace('-', '_'), case_test(case))

if __name__ == '__main__':
    unittest.main()
