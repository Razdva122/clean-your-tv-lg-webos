"""Exercise the selected shell profile and the release-only workflow boundary."""
import fnmatch
import os
import re
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CIProfiles(unittest.TestCase):
    def test_ui_profile_never_invokes_device_or_installer_tests(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            log = temp / 'commands'
            for executable in ('npm', 'node', 'python3', 'cc'):
                command = temp / executable
                command.write_text('#!/bin/sh\nprintf "%s\\n" "$(basename "$0") $*" >> "$PROFILE_LOG"\n')
                command.chmod(0o755)
            subprocess.run(['bash', str(ROOT / 'scripts/test.sh'), 'ui'], cwd=ROOT, check=True,
                           env={**os.environ, 'PATH': str(temp) + os.pathsep + os.environ['PATH'],
                                'PROFILE_LOG': str(log)})
            commands = log.read_text()
            self.assertNotIn('-browser.cjs', commands)
            self.assertIn('npm run lint:compat', commands)
            self.assertIn('npm run test:compat', commands)
            self.assertIn('root-edition/ui/test-', commands)
            for unrelated in ('native/', 'root-edition/tests/', 'root-edition/service/',
                              'tests/cytv', 'test-python-runtime', 'python3 ', 'cc '):
                self.assertNotIn(unrelated, commands)

    def test_required_statuses_include_parallel_browser_failures(self):
        workflow = (ROOT / '.github/workflows/tests.yml').read_text()
        summary = re.search(r'^  tests:\n(.*?)(?=^  [^ ]|\Z)', workflow, re.M | re.S).group(1)
        self.assertIn('needs: [scope, runtime, browser, optional-python]', summary)
        browser = re.search(r'^  browser:\n(.*?)(?=^  [^ ]|\Z)', workflow, re.M | re.S).group(1)
        self.assertIn('BROWSER_CHANNEL=chromium node tests/tv-dev-ui.cjs', browser)
        self.assertIn('if: always()', summary)
        script = summary.split('        run: |\n', 1)[1]
        script = '\n'.join(line[10:] for line in script.splitlines())
        complete = dict(os.environ, SCOPE='success', RUNTIME='success', BROWSER='success',
                        PYTHON='success', BROWSER_REQUIRED='true', PYTHON_REQUIRED='true')
        def status(**updates):
            return subprocess.run(['bash', '-e', '-c', script], env={**complete, **updates}, capture_output=True).returncode
        self.assertEqual(status(), 0)
        for dependency in ('SCOPE', 'RUNTIME', 'BROWSER', 'PYTHON'):
            for state in ('failure', 'skipped', 'cancelled'):
                with self.subTest(dependency=dependency, state=state):
                    self.assertNotEqual(status(**{dependency: state}), 0)
        self.assertEqual(status(BROWSER='skipped', PYTHON='skipped', BROWSER_REQUIRED='false', PYTHON_REQUIRED='false'), 0)
        for dependency in ('BROWSER', 'PYTHON'):
            for state in ('failure', 'cancelled', 'unknown', ''):
                with self.subTest(optional=dependency, state=state):
                    self.assertNotEqual(status(BROWSER_REQUIRED='false', PYTHON_REQUIRED='false', **{dependency: state}), 0)

    def test_full_release_marker_fails_for_every_incomplete_dependency(self):
        workflow = (ROOT / '.github/workflows/tests.yml').read_text()
        marker = workflow.split('  full-release:', 1)[1]
        self.assertIn('needs: [tests, browser, optional-python]', marker)
        self.assertIn('if: always() && inputs.full_suite', marker)
        script = marker.split('        run: |\n', 1)[1]
        script = '\n'.join(line[10:] for line in script.splitlines())
        complete = dict(os.environ, TESTS='success', BROWSER='success', PYTHON='success', SOURCE='a' * 40)
        self.assertEqual(subprocess.run(['bash', '-e', '-c', script], env=complete, capture_output=True).returncode, 0)
        for dependency in ('TESTS', 'BROWSER', 'PYTHON'):
            for state in ('failure', 'skipped', 'cancelled'):
                with self.subTest(dependency=dependency, state=state):
                    self.assertNotEqual(subprocess.run(['bash', '-e', '-c', script],
                        env={**complete, dependency: state}, capture_output=True).returncode, 0)
        self.assertNotEqual(subprocess.run(['bash', '-e', '-c', script],
            env={**complete, 'SOURCE': ''}, capture_output=True).returncode, 0)

    def test_desktop_freeze_is_scoped_to_runtime_and_packaging_inputs(self):
        workflow = (ROOT / '.github/workflows/cytv-runtime.yml').read_text()
        paths = [line.strip()[3:-1] for line in workflow.splitlines() if line.startswith("      - '")]
        for name in ('cytv/runtime_check.py', 'cytv/requirements.txt', 'cytv/desktop_entry.py',
                     'scripts/desktop_packaging.py'):
            self.assertTrue(any(fnmatch.fnmatchcase(name, pattern) for pattern in paths), name)
        self.assertFalse(any(fnmatch.fnmatchcase('cytv/transport.py', pattern) for pattern in paths))

    def test_direct_tv_artifacts_require_affected_safety_before_build_and_upload(self):
        workflow = (ROOT / '.github/workflows/tv-candidate.yml').read_text()
        self.assertIn('fetch-depth: 0', workflow)
        self.assertIn('CI_QUICK_SUITE: true', workflow)
        self.assertIn('run: python scripts/ci-scope.py', workflow)
        safety = workflow.index('      - name: Verify affected TV safety')
        self.assertLess(safety, workflow.index('      - name: Build and inspect'))
        self.assertLess(safety, workflow.index('      - uses: actions/upload-artifact'))
        step = workflow[safety:].split('      - name: Build', 1)[0]
        script = step.split('        run: |\n', 1)[1]
        script = '\n'.join(line[10:] for line in script.splitlines())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'scripts').mkdir()
            runner = root / 'scripts/test.sh'
            runner.write_text('#!/bin/sh\nprintf "%s" "$*" > selected\n')
            runner.chmod(0o755)
            for required, expected in (('true', 'tv'), ('false', 'ui')):
                subprocess.run(['bash', '-e', '-c', script], cwd=root, check=True,
                               env={**os.environ, 'TV_REQUIRED': required})
                self.assertEqual((root / 'selected').read_text(), expected)
            for missing in ('', 'unknown'):
                with self.subTest(missing=missing):
                    self.assertNotEqual(subprocess.run(['bash', '-e', '-c', script], cwd=root,
                        env={**os.environ, 'TV_REQUIRED': missing}).returncode, 0)
        self.assertIn("if: steps.safety_scope.outputs.tv == 'true'", workflow)
        self.assertIn('4e1578efc2a2cc67651413a05ccc4c5d43f6b4329c599901c556f24d93cd0508', workflow)

    def test_metadata_pushes_never_start_or_cancel_frozen_builds(self):
        candidate = (ROOT / '.github/workflows/cytv.yml').read_text()
        self.assertNotIn('  push:', candidate)
        self.assertIn('  cancel-in-progress: false', candidate)
        preview = (ROOT / '.github/workflows/preview-pages.yml').read_text()
        self.assertNotIn('scripts/test.sh preview', preview)
