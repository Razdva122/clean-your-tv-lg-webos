"""Preflight errors retain safe facts, including the failing space boundary."""
import json
import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from cytv.checks import CheckList
from cytv.operations import Installer

from cytv import diagnostics, python_runtime as runtime, state
from cytv.errors import UserError


class PreflightTests(unittest.TestCase):
    def test_low_space_survives_selection_and_is_exported_without_remote_text(self):
        class Remote:
            def run(self, command, **kwargs):
                if 'CYTV_SYSTEM_PYTHON' in command:
                    return ''
                return 'CYTV_TARGET_ERROR space 27648 327680 424296'
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(UserError) as caught:
                runtime.select_python(Remote(), directory, lambda _: None, provision=True)
            error = caught.exception
            self.assertIn('27 MiB', str(error))
            self.assertIn('320 MiB', str(error))
            self.assertIn('Session Storage', str(error))
            self.assertIn('free space yourself', str(error))
            self.assertIn('may sign you out or lose unsaved work', str(error))
            self.assertIn('docs/WAM-CLEANUP.md', str(error))
            report = json.loads(diagnostics.create_report(state.Store(directory), 'install', None, 'preflight', error).read_text())
            self.assertEqual(report['python_runtime'], {'reason': 'space', 'available_kib': 27648,
                'required_kib': 327680, 'wam_session_kib': 424296})

    def test_display_does_not_round_a_space_deficit_away(self):
        from cytv.errors import PythonPreflightError
        self.assertIn('319.9 MiB', str(PythonPreflightError('space', 327679, 327680)))

    def test_specific_failures_and_untrusted_output(self):
        for reply, reason in [('CYTV_TARGET_ERROR abi', 'abi'),
                              ('CYTV_TARGET_ERROR ownership', 'ownership'),
                              ('CYTV_TARGET_ERROR space-query', 'space-query'),
                              ('CYTV_TARGET_ERROR space 1 327680 -1', 'space'),
                              ('CYTV_TARGET_ERROR space 1 327680 private-secret', 'unknown'),
                              ('private-secret', 'unknown')]:
            with self.subTest(reply=reply), patch.object(runtime, '_run', return_value=reply):
                with self.assertRaises(UserError) as caught:
                    runtime._preflight(None)
                self.assertEqual(caught.exception.reason, reason)
                self.assertNotIn('private-secret', str(caught.exception))

    @unittest.skipUnless(os.name == 'posix', 'Requires POSIX shell')
    def test_space_check_runs_at_boundary_and_reuses_existing_slot(self):
        with tempfile.TemporaryDirectory() as directory:
            for available, existing, expected in [(327679, False, 'space'), (327680, False, 'READY'),
                                                   (0, True, 'READY'), ('bad', False, 'space-query'), ('9223372036854775808', False, 'space-query')]:
                slot = directory + '/slot'
                if existing: os.mkdir(slot)
                prefix = 'set -eu\nbase=/var/lib\nslot=' + slot + '\n'
                prefix += 'df() { printf "header\\nfixture 1 1 %s 1 /var\\n" "$CYTV_AVAILABLE"; }\n'
                prefix += 'ancestors() { return 1; }\n'
                result = subprocess.run(['/bin/sh', '-c', prefix + runtime._space_script(327680)],
                    env=dict(os.environ, CYTV_AVAILABLE=str(available)), capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(expected, result.stdout)
                if existing: os.rmdir(slot)

    @unittest.skipUnless(os.name == 'posix', 'Requires POSIX shell')
    def test_failed_measurements_never_become_success_or_definite_wam_size(self):
        for command, expected in [
            ('df() { printf "fixture 1 1 999999 1 /var\\n"; return 1; }', 'space-query'),
            ('df() { printf "fixture 1 1 1 1 /var\\n"; }', 'space 1 327680 -1')]:
            prefix = 'set -eu\nbase=/var/lib\nslot=\n' + command + '\n'
            prefix += 'ancestors() { return 0; }\nsafe_mode() { return 0; }\n'
            prefix += 'du() { printf "999999 ignored\\n"; return 1; }\n'
            prefix += 'readlink() { printf "/bin/du"; }\n'
            result = subprocess.run(['/bin/sh', '-c', prefix + runtime._space_script(327680)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(expected, result.stdout)

    def test_staging_recheck_reports_changed_space_before_upload(self):
        with patch.object(runtime, '_run', return_value='CYTV_TARGET_ERROR space 1024 250000 -1'):
            with self.assertRaises(UserError) as caught:
                runtime._check_space(None, 250000)
            self.assertIn('1 MiB', str(caught.exception))
            self.assertEqual(caught.exception.required_kib, 250000)


class RootPythonResultTests(unittest.TestCase):
    python_probes = ('python3', 'python-json', 'python-fcntl', 'python-version')

    class Remote:
        def __init__(self, *, node=True, abi=True):
            self.node = node
            self.abi = abi
            self.commands = []

        def run(self, command, **kwargs):
            self.commands.append(command)
            if 'CYTV_ROOT_READY' in command:
                missing = ('/usr/bin/python3' in command or '/verified/python' in command
                           or ('/usr/bin/node' in command and not self.node))
                return 'CYTV_ROOT_MISSING' if missing else 'CYTV_ROOT_READY'
            if 'CYTV_TARGET_READY' in command:
                return 'CYTV_TARGET_READY' if self.abi else 'CYTV_TARGET_ERROR abi'
            return ''

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.store = state.Store(os.path.realpath(temporary.name))
        self.events = []
        self.progress = []
        self.checks = CheckList(self.events.append)
        self.profile = {'edition': 'root', 'host': '192.0.2.10'}

    def installer(self, remote):
        self.checks.prepare('root', 'install')
        return Installer(remote, self.store, self.profile, '.', {}, progress=self.progress.append, checks=self.checks)

    def report(self, installer, error):
        path = diagnostics.create_report(self.store, 'install', self.profile, 'preflight', error,
                                         installer.tv_info, checks=self.checks.results)
        return json.loads(path.read_text())

    def test_missing_python_is_one_result_and_node_blocks_provisioning(self):
        remote = self.Remote(node=False)
        installer = self.installer(remote)
        with self.assertRaises(UserError) as caught:
            installer.preflight(install=True)
        self.assertIn('node-version', str(caught.exception))
        self.assertIn('TV Python 3.9+', str(caught.exception))
        self.assertNotIn('CYTV_TARGET_READY', '\n'.join(remote.commands))
        rows = {event['id']: event for event in self.events}
        self.assertEqual(rows['python-runtime']['status'], 'fail')
        self.assertTrue(rows.keys().isdisjoint(self.python_probes))
        report = self.report(installer, caught.exception)
        self.assertNotIn('python-runtime', report['checks'])
        for name in self.python_probes:
            self.assertEqual(report['checks'][name], 'fail')
            self.assertEqual(report['tv']['root_requirements'][name], 'fail')

    def test_cache_invalidated_after_preparation_is_still_a_host_cache_failure(self):
        remote = self.Remote()
        installer = self.installer(remote)
        cache = self.store.root / 'python-cache'
        cache.mkdir(mode=0o700)
        archive = cache / (runtime.SHA256 + '.tar.gz')
        archive.write_bytes(b'invalid')
        with patch.object(runtime, 'prime_cache', return_value=archive):
            with self.assertRaises(UserError) as caught:
                installer.preflight(install=True)
        self.assertIn('The TV passed the checks to prepare private Python.', self.progress)
        self.assertIn('Remove its pinned archive', str(caught.exception))
        self.assertEqual(self.report(installer, caught.exception)['python_cache'], {'reason': 'cache-invalid'})
        self.assertEqual(self.checks.results['python-runtime']['status'], 'fail')
        self.assertEqual(archive.read_bytes(), b'invalid')

    def test_cache_read_failure_points_to_local_data_folder(self):
        installer = self.installer(self.Remote())
        archive = self.store.root / 'python-cache' / (runtime.SHA256 + '.tar.gz')
        with patch.object(runtime, 'prime_cache', return_value=archive):
            with self.assertRaises(UserError) as caught:
                installer.preflight(install=True)
        self.assertIn('Check write access to the application data folder', str(caught.exception))
        self.assertEqual(self.report(installer, caught.exception)['python_cache'], {'reason': 'cache-access'})

    def test_incompatible_tv_stops_before_cache_access(self):
        remote = self.Remote(abi=False)
        installer = self.installer(remote)
        with self.assertRaisesRegex(UserError, 'The TV ABI check failed') as caught:
            installer.preflight(install=True)
        self.assertNotIn('The TV passed the checks to prepare private Python.', self.progress)
        self.assertFalse((self.store.root / 'python-cache').exists())
        self.assertEqual(self.report(installer, caught.exception)['python_runtime'], {'reason': 'abi'})
        self.assertEqual(self.checks.results['python-runtime']['status'], 'fail')

    def test_python_failing_root_probes_is_never_selected_for_activation(self):
        remote = self.Remote()
        installer = self.installer(remote)
        with patch.object(installer, '_select_python', return_value='/verified/python'):
            with self.assertRaisesRegex(UserError, 'Private Python installation could not be verified'):
                installer.preflight(install=True)
        self.assertNotEqual(installer._selected_python, '/verified/python')
        self.assertFalse(any('CYTV_EXISTING_ROOT' in command for command in remote.commands))
