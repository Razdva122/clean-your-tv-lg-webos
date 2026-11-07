"""Host checks must keep the project interpreter instead of losing its dependencies."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class PythonSelectionTests(unittest.TestCase):
    def run_profile(self, project_python=True, override=False, active=False):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'scripts').mkdir()
            shutil.copy(ROOT / 'scripts/test.sh', root / 'scripts/test.sh')
            tools = root / 'tools'
            tools.mkdir()
            log = root / 'interpreter'

            def interpreter(path, name):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('#!/bin/sh\nprintf "%s\\n" "' + name + '" "$PYTHON" "$CYTV_PYTHON" > "$PYTHON_SELECTION_LOG"\n')
                path.chmod(0o755)

            interpreter(tools / 'python3', 'system')
            if project_python:
                interpreter(root / '.venv-cytv/bin/python3', 'project')
            if active:
                interpreter(root / 'active/bin/python3', 'active')
            interpreter(tools / 'explicit-python', 'explicit')
            env = {key: value for key, value in os.environ.items()
                   if key not in ('PYTHON', 'CYTV_PYTHON', 'VIRTUAL_ENV')}
            env.update(PATH=str(tools) + os.pathsep + env['PATH'], PYTHON_SELECTION_LOG=str(log))
            if override:
                env['PYTHON'] = str(tools / 'explicit-python')
            if active:
                env['VIRTUAL_ENV'] = str(root / 'active')
            subprocess.run(['bash', str(root / 'scripts/test.sh'), 'android'],
                           env=env, check=True, capture_output=True)
            return log.read_text().splitlines()

    def test_uses_project_environment_without_shell_activation(self):
        selected, python, android_python = self.run_profile()
        self.assertEqual(selected, 'project')
        self.assertTrue(python.endswith('/.venv-cytv/bin/python3'))
        self.assertEqual(android_python, python)

    def test_explicit_interpreter_takes_precedence(self):
        selected, python, android_python = self.run_profile(override=True, active=True)
        self.assertEqual(selected, 'explicit')
        self.assertTrue(python.endswith('/tools/explicit-python'))
        self.assertEqual(android_python, python)

    def test_active_environment_precedes_project_environment(self):
        selected, python, android_python = self.run_profile(active=True)
        self.assertEqual(selected, 'active')
        self.assertTrue(python.endswith('/active/bin/python3'))
        self.assertEqual(android_python, python)

    def test_ci_without_local_environment_uses_path(self):
        selected, python, android_python = self.run_profile(project_python=False)
        self.assertEqual(selected, 'system')
        self.assertEqual(python, 'python3')
        self.assertEqual(android_python, python)

    @unittest.skipIf(os.name == 'nt', 'POSIX executable fixture')
    def test_node_preview_uses_explicit_python_without_adjacent_python3(self):
        with tempfile.TemporaryDirectory() as temporary:
            tools = Path(temporary)
            selected = tools / 'selected-python'
            selected.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$PYTHON_SELECTION_LOG"\n')
            selected.chmod(0o755)
            poison = tools / 'python3'
            poison.write_text('#!/bin/sh\nexit 99\n')
            poison.chmod(0o755)
            log = tools / 'arguments'
            result = subprocess.run(['node', '-e', "require('./tests/themes/browser.cjs').stage('python-selection')"],
                                    cwd=ROOT, capture_output=True, text=True,
                                    env={**os.environ, 'PYTHON': str(selected),
                                         'PYTHON_SELECTION_LOG': str(log),
                                         'PATH': str(tools) + os.pathsep + os.environ['PATH']})
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(log.read_text().splitlines()[:2], ['scripts/preview.py', '--build'])
