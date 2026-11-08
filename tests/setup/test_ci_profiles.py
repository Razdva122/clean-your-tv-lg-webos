"""Exercise the selected shell profile and the release-only workflow boundary."""
from collections import Counter
import fnmatch
import os
import re
import shutil
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
                                'PROFILE_LOG': str(log), 'PYTHON': 'python3', 'CYTV_PYTHON': 'python3'})
            commands = log.read_text()
            self.assertNotIn('-browser.cjs', commands)
            self.assertIn('npm run lint:compat', commands)
            self.assertIn('npm run test:compat', commands)
            self.assertIn('root-edition/ui/test-', commands)
            for unrelated in ('native/', 'root-edition/tests/', 'root-edition/service/',
                              'tests/cytv', 'test-python-runtime', 'python3 ', 'cc '):
                self.assertNotIn(unrelated, commands)

    def test_tv_runtime_keeps_all_device_checks_without_ui(self):
        # Compare executed commands, not a second hand-maintained safety allowlist.
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            for executable in ('npm', 'node', 'python3', 'cc'):
                command = temp / executable
                command.write_text('#!/bin/sh\nprintf "%s\\n" "$(basename "$0") $*" >> "$PROFILE_LOG"\n')
                command.chmod(0o755)
            compiler = temp / 'cc'
            compiler.write_text(compiler.read_text() +
                                'while [ "$#" -gt 0 ]; do\n'
                                '  if [ "$1" = -o ]; then shift; printf "#!/bin/sh\\nexit 0\\n" > "$1"; chmod +x "$1"; fi\n'
                                '  shift\ndone\n')
            checkout = temp / 'checkout'
            (checkout / 'scripts').mkdir(parents=True)
            shutil.copy(ROOT / 'scripts/test.sh', checkout / 'scripts/test.sh')
            for name in ('root-edition', 'native', 'launcher', 'renewal-service',
                         'updater-service', 'updater-app', 'tests'):
                (checkout / name).symlink_to(ROOT / name, target_is_directory=True)
            traces = {}
            profiles = ['ui', 'tv', 'tv-runtime', 'tv tv-runtime', '']
            profiles += [f'--shard {index}/{count}' for count in (1, 2, 3, 4)
                         for index in range(1, count + 1)]
            for profile in profiles:
                log = temp / (profile.replace(' ', '-').replace('/', '-') or 'full')
                subprocess.run(['bash', str(checkout / 'scripts/test.sh'), *profile.split()],
                               cwd=ROOT, check=True, capture_output=True,
                               env={**os.environ, 'PATH': str(temp) + os.pathsep + os.environ['PATH'],
                                    'PROFILE_LOG': str(log), 'PYTHON': 'python3', 'CYTV_PYTHON': 'python3'})
                traces[profile] = log.read_text().splitlines()
            # Union of shard commands equals the original full profile. Only the
            # three large Python discoveries become partitioned runner calls.
            large_suites = ('root-edition/tests', 'tests/setup', 'tests/cytv')
            original = Counter(traces[''])
            for directory in large_suites:
                self.assertEqual(original.pop(f'python3 -m unittest discover -s {directory}'), 1)
            for count in (1, 2, 3, 4):
                sharded = Counter()
                for index in range(1, count + 1):
                    commands = traces[f'--shard {index}/{count}']
                    for directory in large_suites:
                        command = f'python3 scripts/test-shard.py --shard {index}/{count} -s {directory}'
                        self.assertEqual(commands.count(command), 1)
                    sharded.update(command for command in commands if 'scripts/test-shard.py' not in command)
                self.assertEqual(sharded, original, f'{count} shards must retain each serial command exactly once')
            # Serial groups must leave shard 1, with each dependency-coherent
            # block kept together in its own isolated checkout.
            for command in ('node tests/helper-compat.cjs',
                            'node homebrew/tests/ui.cjs'):
                self.assertIn(command, traces['--shard 2/4'])
                self.assertNotIn(command, traces['--shard 1/4'])
            for command in ('python3 tests/root-node-compat.py', 'python3 tests/root-node-compat.py --beta'):
                self.assertIn(command, traces['--shard 3/4'])
                self.assertNotIn(command, traces['--shard 2/4'])
            self.assertIn('python3 -m unittest discover -s tests/system_updates', traces['--shard 4/4'])
            self.assertNotIn('python3 -m unittest discover -s tests/system_updates', traces['--shard 1/4'])
            self.assertIn('node tests/root-decoder-ui.cjs', traces['--shard 2/4'])
            self.assertNotIn('node tests/root-decoder-ui.cjs', traces['--shard 1/4'])
            self.assertEqual(traces['tv'], traces['ui'] + traces['tv-runtime'])
            self.assertEqual(traces['tv'], traces['tv tv-runtime'])
            self.assertNotIn('npm run test:themes', traces['tv-runtime'])
            for required in ('node tests/helper-compat.cjs', 'node tests/home-control.cjs',
                             'node --test tests/controller-resume-home.cjs tests/controller-watchdog.cjs',
                             'python3 tests/root-node-compat.py',
                             'python3 -m unittest discover -s root-edition/tests',
                             'python3 -m unittest discover -s tests/system_updates'):
                self.assertIn(required, traces['tv-runtime'])

    def test_runtime_missing_selection_never_invokes_empty_full_suite(self):
        workflow = (ROOT / '.github/workflows/tests.yml').read_text()
        self.assertIn('TV_RUNTIME: ${{ needs.scope.outputs.tv_runtime }}', workflow)
        for name in ('Prepare pinned Node', 'Verify real webOS-style file ownership'):
            condition = workflow[workflow.index('      - name: ' + name):].splitlines()[1]
            self.assertIn("runner.os == 'Linux'", condition)
            self.assertIn("contains(format(' {0} ', steps.evidence.outputs.missing), ' tv-runtime ')", condition)
        ownership = workflow[workflow.index('      - name: Verify real webOS-style file ownership'):].splitlines()[1]
        self.assertIn('matrix.shard == 1', ownership)
        step = workflow.split('      - name: Test affected runtime components', 1)[1].split('      - name:', 1)[0]
        script = step.split('        run: |\n', 1)[1]
        script = '\n'.join(line[10:] for line in script.splitlines())
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            (temp / 'scripts').mkdir()
            runner = temp / 'scripts/test.sh'
            runner.write_text('#!/bin/sh\nprintf "%s" "$*" > selected\n')
            runner.chmod(0o755)
            for missing, expected in [('tv-runtime', '--shard 2/4 tv-runtime'),
                                      ('installer setup', '--shard 2/4 installer setup'), ('', None)]:
                (temp / 'selected').unlink(missing_ok=True)
                subprocess.run(['bash', '-e', '-c', script], cwd=temp,
                               env={**os.environ, 'MISSING': missing, 'SHARD': '2/4'}, check=True)
                actual = (temp / 'selected').read_text() if (temp / 'selected').exists() else None
                self.assertEqual(actual, expected)
        direct = (ROOT / '.github/workflows/tv-candidate.yml').read_text()
        self.assertIn("TV_REQUIRED: ${{ steps.safety_scope.outputs.tv == 'true' || steps.safety_scope.outputs.tv_runtime == 'true' }}", direct)

    def test_metadata_checks_remain_fresh_when_setup_is_reused(self):
        workflow = (ROOT / '.github/workflows/tests.yml').read_text()
        step = workflow.split('      - name: Validate current release metadata independently of runtime reuse', 1)[1].split('      - name:', 1)[0]
        script = step.split('        run: |\n', 1)[1].split("          python - <<'PYTHON'", 1)[0]
        script = '\n'.join(line[10:] for line in script.splitlines())
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            executable = temp / 'python'
            executable.write_text('#!/bin/sh\nprintf "%s" "$*" > "$METADATA_LOG"\n')
            executable.chmod(0o755)
            log = temp / 'commands'
            for shard, setup, expected in [('1', 'false', True), ('1', 'true', False), ('2', 'false', False)]:
                log.unlink(missing_ok=True)
                subprocess.run(['bash', '-e', '-c', script], check=True,
                               env={**os.environ, 'PATH': str(temp) + os.pathsep + os.environ['PATH'],
                                    'METADATA_LOG': str(log), 'SHARD_INDEX': shard, 'RUN_SETUP': setup})
                self.assertEqual(log.exists(), expected)
        self.assertIn('validate_shape', step)

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
