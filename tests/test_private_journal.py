"""Bounded journal tests against actual host files and process cuts."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[1]
CASES = ('read', 'append', 'utf8-boundaries', 'append-invalid-utf8', 'no-read', 'missing', 'invalid-mode', 'invalid-hardlink',
         'invalid-symlink', 'invalid-fifo', 'invalid-gap', 'invalid-unknown',
         'invalid-oversize', 'invalid-nul', 'invalid-utf8', 'invalid-empty',
         'full', 'full-bytes', 'overflow', 'limit', 'append-oversize', 'wrong-seq', 'collision',
         'cache-mutation', 'read-fifo-race', 'read-replace', 'read-dir-replace',
         'read-file-sync-fail', 'read-dir-sync-fail', 'append-file-sync-fail',
         'append-dir-sync-fail', 'append-corrupt', 'append-replace',
         'lifecycle-read', 'lifecycle-append', 'cut-create', 'cut-write',
         'cut-file-sync', 'cut-dir-sync')
class PrivateJournalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='cytv-journal-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.base = Path(cls.temp.name)
        cls.fixture = cls.base / 'fixture'
        cls.binary = cls.base / 'journal-test'
        flags = ['-std=c11', '-Wall', '-Wextra', '-Werror', '-g']
        if os.environ.get('CYTV_PRIVATE_TEST_SANITIZE') == '1':
            flags += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
        command = [os.environ.get('CC', 'cc'), *flags, '-I', str(ROOT/'native/app'),
                   '-DCYTV_PRIVATE_TEST_BUILD',
                   '-DCYTV_PRIVATE_TEST_ROOT="'+str(cls.fixture/'private')+'"',
                   str(ROOT/'native/app/private-lease.c'), str(ROOT/'native/app/private-io.c'),
                   str(ROOT/'tests/private_journal_test.c'), '-o', str(cls.binary)]
        r = subprocess.run(command, capture_output=True, text=True, timeout=60)
        if r.returncode:
            raise AssertionError(r.stdout+r.stderr)
    def setUp(self):
        shutil.rmtree(self.fixture, ignore_errors=True)
        (self.fixture/'private').mkdir(parents=True)
def case_test(name):
    def run(self):
        r = subprocess.run([str(self.binary), name], capture_output=True, text=True, timeout=15)
        self.assertEqual(r.returncode, 0, r.stdout+r.stderr)
        self.assertEqual(r.stdout.strip(), 'PASS')
    return run
for case in CASES:
    setattr(PrivateJournalTests, 'test_'+case.replace('-', '_'), case_test(case))
if __name__ == '__main__':
    unittest.main()
