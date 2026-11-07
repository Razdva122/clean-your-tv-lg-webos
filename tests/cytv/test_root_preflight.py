"""Run the actual Root requirement probes in a local shell, without a TV."""
import json
import os
import shutil
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest

from cytv import cli, diagnostics, state
from cytv.errors import UserError, TVCommandError
from cytv.operations import Installer
from cytv.transport import SSH


REQUIREMENTS = ('root-user', 'python3', 'luna-send', 'apps-directory',
                'luna-services-directory', 'python-json', 'python-fcntl', 'python-version', 'node-version')


class RootPreflightTests(unittest.TestCase):
    def test_failed_ssh_command_reports_exit_status_without_remote_text(self):
        class Channel:
            def recv_ready(self): return False
            def recv_stderr_ready(self): return True if not getattr(self, 'read', False) else False
            def recv_stderr(self, limit):
                self.read = True
                return b'PRIVATE-REMOTE-ERROR'
            def exit_status_ready(self): return True
            def recv_exit_status(self): return 127

        with self.assertRaises(UserError) as caught:
            list(SSH(None).chunks(Channel(), 5))
        self.assertEqual(getattr(caught.exception, 'exit_status', None), 127)
        with tempfile.TemporaryDirectory() as tmp:
            report = diagnostics.create_report(state.Store(tmp), 'doctor', None, 'doctor', caught.exception)
            self.assertEqual(json.loads(report.read_text())['ssh_command'], {'exit_status': 127})
            self.assertNotIn('PRIVATE-', report.read_text() + str(caught.exception))

    def remote(self, root, failed=()):
        paths = {name: root / name for name in
                 ('python3', 'luna-send', 'apps-directory', 'luna-services-directory', 'node')}
        for name, path in paths.items():
            if name in failed:
                continue
            if name.endswith('directory'):
                path.mkdir()
            else:
                script = '#!/bin/sh\n'
                if name == 'python3':
                    for module in ('json', 'fcntl'):
                        if 'python-' + module in failed:
                            script += 'case "$*" in *' + module + '*) echo PRIVATE-IMPORT-ERROR >&2; exit 1;; esac\n'
                    if 'python-version' in failed:
                        script += 'case "$*" in *version_info*) exec ' + shlex.quote(sys.executable) + ' -c ' + shlex.quote('import sys; sys.version_info=(3,8,10); exec(sys.argv[1])') + ' "$2";; esac\n'
                    script += 'exec ' + shlex.quote(sys.executable) + ' "$@"\n'
                if name == 'node':
                    if 'node-version' in failed:
                        script += 'exec ' + shlex.quote(shutil.which('node')) + ' -e ' + shlex.quote("Object.defineProperty(process.versions,'node',{value:'0.12.0'});") + '"$2"\n'
                    else:
                        script += 'exec ' + shlex.quote(shutil.which('node')) + ' "$@"\n'
                path.write_text(script)
                path.chmod(0o700)
        replacements = dict(zip(('/usr/bin/python3', '/usr/bin/luna-send',
                                 '/media/developer/apps', '/var/luna-service2-dev', '/usr/bin/node'), paths.values()))

        class Remote:
            def run(self, command, **kwargs):
                for original, path in replacements.items():
                    command = command.replace(original, shlex.quote(str(path)))
                uid = '1000' if 'root-user' in failed else '0'
                return subprocess.check_output(['sh', '-c',
                    'id() { echo ' + uid + '; }; ' + command], text=True)

            def close(self):
                pass

        return Remote()

    @unittest.skipUnless(os.name == 'posix', 'TV shell probes require POSIX Python with fcntl')
    def test_each_missing_requirement_is_named_and_all_checks_are_reported(self):
        for failed in REQUIREMENTS:
            with self.subTest(failed=failed), tempfile.TemporaryDirectory() as tmp:
                info = {}
                remote = self.remote(Path(tmp), (failed,))
                installer = Installer(remote, None, {'edition': 'root'}, '.', {}, tv_info=info)
                with self.assertRaisesRegex(UserError, failed):
                    installer.preflight()
                expected = dict.fromkeys(REQUIREMENTS, 'pass')
                expected[failed] = 'fail'
                if failed == 'python3':
                    expected.update({'python-json': 'fail', 'python-fcntl': 'fail', 'python-version': 'fail'})
                self.assertEqual(info['root_requirements'], expected)

    @unittest.skipUnless(os.name == 'posix', 'TV shell probes require POSIX Python with fcntl')
    def test_successful_checks_are_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            info = {}
            Installer(self.remote(Path(tmp)), None, {'edition': 'root'}, '.', {},
                      tv_info=info).preflight()
            self.assertEqual(info['root_requirements'], dict.fromkeys(REQUIREMENTS, 'pass'))
            self.assertEqual(info.get('node_version_status'), 'read')
            self.assertEqual(info.get('node_version'),
                             subprocess.check_output([shutil.which('node'), '--version'], text=True).strip()[1:])

    @unittest.skipUnless(os.name == 'posix', 'TV shell probes require POSIX Python with fcntl')
    def test_cli_report_identifies_requirements_without_private_remote_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            remote = self.remote(root, ('python-fcntl', 'luna-services-directory'))
            output = []
            code = cli.main(['doctor', '--language', 'en', '--host', '192.0.2.55',
                             '--edition', 'root', '--data-dir', str(root / 'state')],
                            write=output.append, connect=lambda *args: remote)
            self.assertEqual(code, 2)
            report = next((root / 'state/reports').glob('*.json'))
            checks = json.loads(report.read_text())['tv']['root_requirements']
            self.assertEqual(checks['python-fcntl'], 'fail')
            self.assertEqual(checks['luna-services-directory'], 'fail')
            self.assertIn('python-fcntl', '\n'.join(output))
            self.assertNotIn('PRIVATE-', report.read_text() + '\n'.join(output))

    def test_report_filters_untrusted_requirement_names_and_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            info = {'root_requirements': {'root-user': 'pass', 'python3': 'PRIVATE-VALUE',
                                         'PRIVATE-NAME': 'fail'}}
            report = diagnostics.create_report(state.Store(tmp), 'doctor', None, 'doctor', tv_info=info)
            self.assertEqual(json.loads(report.read_text())['tv']['root_requirements'],
                             {'root-user': 'pass', 'python3': 'unknown'})
            self.assertNotIn('PRIVATE-', report.read_text())

    def test_unknown_reply_blocks_install_without_exposing_remote_text(self):
        class Remote:
            def run(self, command): return 'PRIVATE-UNEXPECTED-RESPONSE'

        info = {}
        with self.assertRaises(UserError) as caught:
            Installer(Remote(), None, {'edition': 'root'}, '.', {}, tv_info=info).preflight(install=True)
        self.assertEqual(info['root_requirements'], dict.fromkeys(REQUIREMENTS, 'unknown'))
        self.assertNotIn('PRIVATE-', str(caught.exception))

    def test_interrupted_probe_preserves_partial_results_and_stops(self):
        class Remote:
            calls = 0
            def run(self, command):
                self.calls += 1
                if self.calls == 2:
                    raise TVCommandError(127)
                return 'CYTV_ROOT_READY'

        info, remote = {}, Remote()
        with self.assertRaises(TVCommandError):
            installer=Installer(remote, None, {'edition': 'root'}, '.', {}, tv_info=info)
            installer._selected_python='/usr/bin/python3'
            installer.preflight(install=True)
        self.assertEqual(remote.calls, 2)
        self.assertEqual(info['root_requirements'],
                         dict(dict.fromkeys(REQUIREMENTS, 'unknown'), **{'root-user': 'pass'}))

    def test_command_status_is_numeric_and_bounded(self):
        for value in ('PRIVATE-STATUS', True, -2, 256):
            with self.subTest(value=value):
                self.assertIsNone(TVCommandError(value).exit_status)
        for value in (-1, 1, 127, 255):
            self.assertEqual(TVCommandError(value).exit_status, value)


if __name__ == '__main__':
    unittest.main()
