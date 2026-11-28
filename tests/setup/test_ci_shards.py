"""Shard routing must neither lose tests nor turn discovery failures green."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / 'scripts/test-shard.py'


class CIShards(unittest.TestCase):
    def test_profile_consumes_timing_directory_without_exporting_it_to_nested_tests(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'scripts').mkdir()
            shutil.copy(ROOT / 'scripts/test.sh', root / 'scripts/test.sh')
            python = root / 'python'
            log = root / 'calls'
            python.write_text('#!/bin/sh\nprintf "%s\\n" "${CI_TEST_TIMINGS_DIR-unset}" "$@" > "$TIMING_CALLS"\n')
            python.chmod(0o755)
            timings = root / 'timing reports'
            # Shard 3 has no serial Homebrew block; isolate the Python invocation.
            result = subprocess.run(['bash', str(root / 'scripts/test.sh'), '--shard', '3/4', 'installer'],
                                    env={**os.environ, 'PYTHON': str(python), 'TIMING_CALLS': str(log),
                                         'CI_TEST_TIMINGS_DIR': str(timings)}, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(log.read_text().splitlines(),
                             ['unset', 'scripts/test-shard.py', '--shard', '3/4', '-s',
                              'tests/cytv', '--timings', str(timings / 'cytv.json')])

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

    def test_parallel_intel_workers_overlap_and_propagate_each_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'scripts').mkdir()
            for script in ('test-shard.py', 'ci_test_timing.py'):
                shutil.copy(ROOT / 'scripts' / script, root / 'scripts')
            suite = root / 'tests/cytv'
            suite.mkdir(parents=True)
            (suite / 'test_workers.py').write_text(textwrap.dedent("""
                import os, time, unittest
                from pathlib import Path

                class Workers(unittest.TestCase):
                    def meet(self, name, peer):
                        shared = Path(os.environ['MEETING'])
                        (shared / name).write_text(str(Path.cwd()))
                        end = time.monotonic() + 5
                        while not (shared / peer).exists() and time.monotonic() < end:
                            time.sleep(.01)
                        self.assertNotEqual(str(Path.cwd()), (shared / peer).read_text())
                        self.assertEqual(Path('node_modules/installed').read_text(), 'yes')
                        self.assertNotEqual(name, os.environ['FAIL_WORKER'])

                    def test_a(self):
                        self.meet('a', 'b')

                    def test_b(self):
                        self.meet('b', 'a')
                """))
            # Exercise the documented relative interpreter and timing path in both checkouts.
            interpreter = root / '.venv-cytv/bin/python'
            interpreter.parent.mkdir(parents=True)
            interpreter.write_text('#!/usr/bin/env bash\nexec "$FIXTURE_PYTHON" "$@"\n')
            interpreter.chmod(0o755)
            (root / 'node_modules').mkdir()
            (root / 'node_modules/installed').write_text('yes')
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
            subprocess.run(['git', 'add', 'scripts', 'tests'], cwd=root, check=True)
            subprocess.run(['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                            'commit', '--no-gpg-sign', '-qm', 'fixture'], cwd=root, check=True)
            for failing_worker in ('', 'a', 'b'):
                with self.subTest(failing_worker=failing_worker):
                    timings = root / ('timings-' + failing_worker)
                    result = subprocess.run(
                        ['bash', str(ROOT / 'scripts/test-intel-installer.sh'), timings.name],
                        cwd=root, env={**os.environ, 'PYTHON': '.venv-cytv/bin/python',
                                       'FIXTURE_PYTHON': sys.executable,
                                       'FAIL_WORKER': failing_worker, 'MEETING': str(root),
                                       'GITHUB_STEP_SUMMARY': ''}, text=True, capture_output=True)
                    self.assertEqual(result.returncode, int(bool(failing_worker)), result.stderr)
                    reports = [json.loads(path.read_text()) for path in sorted(timings.glob('*.json'))]
                    self.assertEqual([report['shard'] for report in reports], ['1/2', '2/2'])
                    for report, worker in zip(reports, 'ab'):
                        self.assertEqual(report['successful'], worker != failing_worker)
                        self.assertEqual([row['id'] for row in report['tests']],
                                         [f'test_workers.Workers.test_{worker}'])
                        (root / worker).unlink()
                    worktrees = subprocess.check_output(['git', 'worktree', 'list', '--porcelain'],
                                                       cwd=root, text=True)
                    self.assertEqual(worktrees.count('worktree '), 1)

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

    def test_timing_report_preserves_duplicates_skips_failures_and_shared_fixtures(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'test_timed.py').write_text(
                'import time, unittest\n'
                'def setUpModule(): time.sleep(.02)\n'
                'def tearDownModule(): time.sleep(.02)\n'
                'class Cases(unittest.TestCase):\n'
                ' @classmethod\n def setUpClass(cls): time.sleep(.02)\n'
                ' @classmethod\n def tearDownClass(cls): time.sleep(.02)\n'
                ' def test_ok(self): time.sleep(.02)\n'
                ' @unittest.skip("fixture condition")\n def test_skip(self): pass\n'
                ' def test_fail(self): self.fail("real failure")\n'
                'def load_tests(loader, tests, pattern):\n'
                ' return unittest.TestSuite([tests, Cases("test_ok")])\n')
            report = root / 'timings.json'
            result = self.run_shard(root, '1/1', '--timings', str(report))
            self.assertEqual(result.returncode, 1, result.stderr)
            data = json.loads(report.read_text())
            self.assertEqual(data['tests_run'], 4)
            self.assertFalse(data['successful'])
            self.assertEqual([row['id'] for row in data['tests']].count('test_timed.Cases.test_ok'), 2)
            self.assertEqual(data['skips'], [{'id': 'test_timed.Cases.test_skip', 'reason': 'fixture condition'}])
            for phase in ('setUpModule', 'tearDownModule', 'setUpClass', 'tearDownClass'):
                self.assertGreaterEqual(sum(row['seconds'] for row in data['fixtures']
                                            if row['phase'] == phase), .015)
            self.assertIn('real failure', result.stderr)
            self.assertIn('Slowest tests', result.stderr)

    def test_timing_report_survives_shared_fixture_errors_and_skips(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'test_fixtures.py').write_text(
                'import unittest\n'
                'class Broken(unittest.TestCase):\n'
                ' @classmethod\n def setUpClass(cls): raise RuntimeError("fixture failed")\n'
                ' def test_never_runs(self): pass\n'
                'class Skipped(unittest.TestCase):\n'
                ' @classmethod\n def setUpClass(cls): raise unittest.SkipTest("fixture unavailable")\n'
                ' def test_never_runs(self): pass\n')
            report = root / 'timings.json'
            result = self.run_shard(root, '1/1', '--timings', str(report))
            self.assertEqual(result.returncode, 1, result.stderr)
            data = json.loads(report.read_text())
            self.assertFalse(data['successful'])
            self.assertEqual(data['tests_run'], 0)
            self.assertEqual(len(data['skips']), 1)
            self.assertEqual(data['skips'][0]['reason'], 'fixture unavailable')
            self.assertIn('fixture failed', result.stderr)


if __name__ == '__main__':
    unittest.main()
