"""Shard routing must neither lose tests nor turn discovery failures green."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / 'scripts/test-shard.py'


class CIShards(unittest.TestCase):
    def run_shard(self, directory, shard, *args):
        return subprocess.run([sys.executable, str(RUNNER), '--shard', shard,
                               '-s', str(directory), *args], cwd=ROOT,
                              text=True, capture_output=True)

    def test_partition_executes_each_case_once_and_keeps_class_fixtures(self):
        self.assertTrue(RUNNER.exists(), 'A unittest shard runner is required')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log = root / 'executed'
            (root / 'test_cases.py').write_text(
                'import unittest\nfrom pathlib import Path\n'
                f'LOG = Path({str(log)!r})\n'
                'class Cases(unittest.TestCase):\n'
                ' @classmethod\n def setUpClass(cls): cls.ready = True\n'
                ' @classmethod\n def tearDownClass(cls): cls.ready = False\n' +
                ''.join(f' def test_{i}(self):\n  self.assertTrue(self.ready)\n'
                        f'  with LOG.open("a") as stream: stream.write("{i}\\n")\n'
                        for i in range(9)))
            inventories = []
            for index in range(1, 5):
                listed = self.run_shard(root, f'{index}/4', '--list')
                self.assertEqual(listed.returncode, 0, listed.stderr)
                inventories.extend(json.loads(listed.stdout))
                result = self.run_shard(root, f'{index}/4')
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(sorted(log.read_text().splitlines()), list(map(str, range(9))))
            self.assertEqual(sorted(inventories), [f'test_cases.Cases.test_{i}' for i in range(9)])
            whole = self.run_shard(root, '1/1', '--list')
            self.assertEqual(json.loads(whole.stdout), sorted(inventories))

    def test_failures_and_import_errors_are_not_hidden_by_partition(self):
        self.assertTrue(RUNNER.exists(), 'A unittest shard runner is required')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            case = root / 'test_failure.py'
            case.write_text('import unittest\nclass Cases(unittest.TestCase):\n'
                            ' def test_failure(self): self.fail("real failure")\n')
            result = self.run_shard(root, '1/1')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('real failure', result.stderr)
            case.write_text('raise ImportError("broken discovery")\n')
            for index in range(1, 5):
                result = self.run_shard(root, f'{index}/4')
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('broken discovery', result.stderr)

    def test_bad_shards_fail_before_tests_run(self):
        with tempfile.TemporaryDirectory() as directory:
            for value in ('0/4', '5/4', '1/0', 'x/4', '1', '01/4', '1/999999999999999999999'):
                result = subprocess.run(['bash', str(ROOT / 'scripts/test.sh'), '--shard', value, 'ui'],
                                        cwd=ROOT, text=True, capture_output=True)
                self.assertEqual(result.returncode, 2, (value, result.stderr))
                self.assertIn('Invalid shard', result.stderr)

    def test_empty_partition_succeeds_but_empty_discovery_fails(self):
        self.assertTrue(RUNNER.exists(), 'A unittest shard runner is required')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertNotEqual(self.run_shard(root, '1/4').returncode, 0)
            (root / 'test_one.py').write_text('import unittest\nclass Cases(unittest.TestCase):\n'
                                             ' def test_ok(self): pass\n')
            self.assertEqual(self.run_shard(root, '4/4').returncode, 0)


if __name__ == '__main__':
    unittest.main()
