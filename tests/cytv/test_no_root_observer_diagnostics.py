"""Observer failures remain actionable without exporting remote text or retrying work."""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from cytv import diagnostics, no_root_observer as observer, state
from cytv.errors import TVCommandError, UserError


class ObserverDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = state.Store(self.tmp.name)
        self.profile = state.target('test-tv', 'no-root')
        self.store.begin(self.profile, 'install', recovery_protocol='no-root-original-stream-v1')
        self.journal = self.store.device_dir(self.profile) / 'operation.json'
        self.before = self.journal.read_bytes()
        self.plan = {'operation': 'a' * 32}

    def failure(self, reply, command='status'):
        calls = []
        def run(*args, **kwargs):
            calls.append((args, kwargs))
            if isinstance(reply, BaseException):
                raise reply
            return reply
        with self.assertRaises(UserError) as caught:
            observer.invoke(SimpleNamespace(run=run), self.plan, command)
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.journal.read_bytes(), self.before)
        return caught.exception

    def report(self, error, action='install'):
        path = diagnostics.create_report(self.store, action, self.profile,
                                         'install-packages' if action == 'install' else action, error)
        text = path.read_text()
        self.assertNotIn('PRIVATE', text)
        self.assertNotIn('a' * 32, text)
        self.assertEqual(self.journal.read_bytes(), self.before)
        return json.loads(text)

    def test_command_failure_and_later_observation_keep_distinct_evidence(self):
        original = TVCommandError(127)
        error = self.failure(original, 'prepare')
        self.assertIs(error, original)
        first = self.report(error)
        self.assertEqual(first['reason_code'], 'ssh-command-failed')
        self.assertEqual(first['ssh_command'], {'exit_status': 127})
        self.assertEqual(first['no_root_observer'], {'command': 'prepare', 'failure': 'command-failed'})
        self.store = state.Store(self.tmp.name)  # A subsequent installer process.
        later = self.report(self.failure('PRIVATE-NOT-JSON'), 'recover')
        self.assertEqual(later['first_failure'], first['first_failure'])
        self.assertEqual(later['first_failure']['no_root_observer'], first['no_root_observer'])
        self.assertEqual(later['observation_failure']['no_root_observer'],
                         {'command': 'status', 'failure': 'invalid-json'})
        self.assertEqual(later['recovery']['state'], 'blocked')

    def test_reply_and_transport_failures_have_safe_distinct_categories(self):
        cases = [
            ('PRIVATE-NOT-JSON', 'invalid-json'),
            ('[]', 'invalid-reply'),
            ('{}', 'foreign-operation'),
            ('{"operation":"PRIVATE-OTHER"}', 'foreign-operation'),
            (TimeoutError('PRIVATE-ADDRESS'), 'timeout'),
            (OSError('PRIVATE-PATH'), 'transport-error'),
            (RuntimeError('PRIVATE-REMOTE-TEXT'), 'transport-error'),
            (UserError('TV SSH connection closed. Run cytv status before retrying.',
                       reason_code='connection-interrupted'), 'connection-interrupted'),
        ]
        for reply, expected in cases:
            with self.subTest(expected=expected):
                report = self.report(self.failure(reply), 'recover')
                self.assertEqual(report['no_root_observer'], {'command': 'status', 'failure': expected})
                self.assertNotIn('ssh_command', report)

    def test_actual_ssh_deadline_is_reported_as_timeout(self):
        from cytv.transport import SSH
        def run(*args, **kwargs):
            with patch('cytv.transport.time.monotonic', side_effect=[0, 2]):
                return b''.join(SSH.__new__(SSH).chunks(SimpleNamespace(), 1)).decode()
        with self.assertRaises(UserError) as caught:
            observer.invoke(SimpleNamespace(run=run), self.plan, 'prepare')
        report = self.report(caught.exception)
        self.assertEqual(report['reason_code'], 'operation-timeout')
        self.assertEqual(report['no_root_observer'], {'command': 'prepare', 'failure': 'timeout'})

    def test_known_storage_and_connection_errors_keep_their_guidance(self):
        for original in (TVCommandError(1, storage_full=True),
                         UserError('TV SSH connection closed. Run cytv status before retrying.',
                                   reason_code='connection-interrupted')):
            with self.subTest(reason=original.reason_code):
                error = self.failure(original)
                self.assertIs(error, original)
                self.assertEqual(error.reason_code, original.reason_code)
        report = self.report(self.failure(TVCommandError(1, storage_full=True)), 'recover')
        self.assertEqual(report['guidance']['code'], 'tv-storage-full')
        self.assertEqual(report['ssh_command']['exit_status'], 1)

    def test_invalid_status_is_identified_without_admitting_continuation(self):
        remote = SimpleNamespace(run=lambda *args, **kwargs: json.dumps(self.plan))
        with self.assertRaises(UserError) as caught:
            observer.snapshot(SimpleNamespace(remote=remote), {'plan': self.plan})
        report = self.report(caught.exception, 'recover')
        self.assertEqual(report['no_root_observer'], {'command': 'status', 'failure': 'invalid-status'})
        self.assertEqual(report['recovery']['actions'], ['check', 'retain-evidence'])

    def test_current_and_retained_metadata_are_revalidated(self):
        error = self.failure(TVCommandError(1))
        error.no_root_observer = {'command': 'PRIVATE-COMMAND', 'failure': {'PRIVATE': True},
                                  'stdout': 'PRIVATE-KEY', 'exit_status': True}
        report = self.report(error)
        self.assertEqual(report['no_root_observer'], {'command': 'unknown', 'failure': 'unknown'})
        record = diagnostics.context.failure_summary({
            'no_root_observer': {'command': ['PRIVATE'], 'failure': 'PRIVATE-PATH', 'raw': 'PRIVATE-KEY'}})
        self.assertEqual(record['no_root_observer'], {'command': 'unknown', 'failure': 'unknown'})
        self.assertNotIn('PRIVATE', json.dumps(record))

    def test_error_envelope_is_never_accepted_as_an_observation(self):
        reply = json.dumps({'operation': 'a' * 32, 'observer_error': {
            'exception_name': 'TypeError', 'exception_code': 'EINVAL',
            'observer_reason': 'PRIVATE-PATH', 'stack': 'PRIVATE-KEY'}})
        first = self.report(self.failure(reply, 'prepare'))
        expected = {'command': 'prepare', 'failure': 'observer-error',
                    'exception_name': 'TypeError', 'exception_code': 'EINVAL',
                    'observer_reason': 'unknown'}
        self.assertEqual(first['no_root_observer'], expected)
        self.store = state.Store(self.tmp.name)
        later = self.report(self.failure(reply), 'recover')
        self.assertEqual(later['first_failure']['no_root_observer'], expected)
        self.assertEqual(later['observation_failure']['no_root_observer']['failure'], 'observer-error')
        self.assertEqual(later['recovery']['state'], 'blocked')
        self.assertEqual(later['recovery']['actions'], ['check', 'retain-evidence'])
        for invalid in (None, [], 'PRIVATE-KEY'):
            error = self.failure(json.dumps({'operation': 'a' * 32, 'observer_error': invalid}))
            self.assertEqual(error.no_root_observer['failure'], 'invalid-reply')
        foreign = self.failure(json.dumps({'operation': 'PRIVATE', 'observer_error': {}}))
        self.assertEqual(foreign.no_root_observer['failure'], 'foreign-operation')

    def test_runtime_details_are_revalidated_in_retained_history(self):
        self.report(self.failure(TVCommandError(1), 'prepare'))
        record = self.store.device_dir(self.profile) / 'diagnostic-failures'
        path = next(record.glob('*.json'))
        saved = json.loads(path.read_text())
        saved['no_root_observer'] = {
            'command': 'prepare', 'failure': 'observer-error',
            'exception_name': ['PRIVATE'], 'exception_code': {'PRIVATE': True},
            'observer_reason': 'unsafe-directory', 'message': 'PRIVATE-KEY',
            'filesystem_operation': ['PRIVATE'], 'storage_area': 'private-storage'}
        path.write_text(json.dumps(saved))
        self.store = state.Store(self.tmp.name)
        later = self.report(self.failure('PRIVATE-NOT-JSON'), 'recover')
        self.assertEqual(later['first_failure']['no_root_observer'], {
            'command': 'prepare', 'failure': 'observer-error',
            'exception_name': 'unknown', 'exception_code': 'unknown',
            'observer_reason': 'unsafe-directory',
            'filesystem_operation': 'unknown', 'storage_area': 'private-storage'})

    def test_filesystem_details_survive_export_and_history_without_raw_paths(self):
        reply = json.dumps({'operation': 'a' * 32, 'observer_error': {
            'exception_name': 'Error', 'exception_code': 'EACCES', 'observer_reason': 'unknown',
            'filesystem_operation': 'mkdir', 'storage_area': 'public-staging',
            'path': '/PRIVATE/path', 'message': 'PRIVATE-KEY'}})
        first = self.report(self.failure(reply, 'storage-check'))
        self.assertEqual(first['no_root_observer']['filesystem_operation'], 'mkdir')
        self.assertEqual(first['no_root_observer']['storage_area'], 'public-staging')
        self.store = state.Store(self.tmp.name)
        later = self.report(self.failure('PRIVATE-NOT-JSON'), 'recover')
        self.assertEqual(later['first_failure']['no_root_observer'], first['no_root_observer'])
        record = diagnostics.context.failure_summary({'no_root_observer': {
            'command': 'storage-check', 'failure': 'observer-error',
            'filesystem_operation': {'PRIVATE': True}, 'storage_area': '/PRIVATE/path'}})
        self.assertEqual(record['no_root_observer']['filesystem_operation'], 'unknown')
        self.assertEqual(record['no_root_observer']['storage_area'], 'unknown')
        self.assertNotIn('PRIVATE', json.dumps(record))

    @unittest.skipIf(os.name == 'nt' or not shutil.which('node') or os.getuid() == 0,
                     'Requires POSIX shell, Node and an unprivileged user')
    def test_real_storage_refusal_identifies_staging_without_pending_or_package_requests(self):
        calls = []
        def run(command, **kwargs):
            calls.append(command)
            command = command.replace('/usr/bin/node', shlex.quote(runtime))
            result = subprocess.run(['sh', '-c', command], capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            return result.stdout.decode()
        directory = '/private/tmp' if Path('/private/tmp').exists() else None
        with tempfile.TemporaryDirectory(dir=directory) as tmp:
            root = Path(tmp).resolve()
            root.chmod(0o755)
            public = root / 'public'
            public.mkdir(mode=0o555)
            private = root / 'private'
            store = state.Store(root / 'host')
            installer = SimpleNamespace(remote=SimpleNamespace(run=run), store=store, profile=self.profile)
            runtimes = [shutil.which('node')] + [os.environ[name] for name in
                       ('NODE010', 'NODE01025', 'NODE012') if os.environ.get(name)]
            for runtime in runtimes:
                with self.subTest(runtime=runtime), patch.object(observer, 'ROOT', str(private)), \
                        patch.object(observer, 'PUBLIC_ROOT', str(public)):
                    calls.clear()
                    with self.assertRaises(UserError) as caught:
                        observer.begin(installer, 'install', {'helper.ipk': b'helper', 'launcher.ipk': b'home'},
                                       dict(zip(observer.APPS, ['1', '2'])), {}, {})
                    details = caught.exception.no_root_observer
                    self.assertEqual(details['command'], 'storage-check')
                    self.assertEqual(details['exception_code'], 'EACCES')
                    self.assertEqual(details['filesystem_operation'], 'mkdir')
                    self.assertEqual(details['storage_area'], 'public-staging')
                    self.assertIsNone(store.pending(self.profile))
                    self.assertEqual(len(calls), 2)  # Read-only selection, then the single storage check.
                    self.assertEqual(list(public.iterdir()), [])
                    self.assertEqual(list(private.iterdir()), [])

    @unittest.skipIf(os.name == 'nt' or not shutil.which('node'), 'Requires POSIX shell and Node')
    def test_wrapper_classifies_only_fixed_filesystem_categories_on_supported_runtimes(self):
        cases = [
            ('mkdir', '/tmp/.cytv-installer/PRIVATE/probe', 'mkdir', 'private-storage'),
            ('open', '/tmp/.cytv-installer', 'open', 'private-storage'),
            ('link', '/media/developer/temp/PRIVATE/probe', 'link', 'public-staging'),
            ('lstat', '/media/developer/temp', 'lstat', 'public-staging'),
            ('open', '/tmp', 'open', 'storage-parent'),
            ('open', '/tmp/', 'open', 'storage-parent'),
            ('lstat', '/media/developer', 'lstat', 'storage-parent'),
            ('lstat', '/', 'lstat', 'storage-parent'),
            ('open', '/tmp/.cytv-installer-PRIVATE/probe', 'open', 'unknown'),
            ('open', '/tmp/.cytv-installer/../PRIVATE', 'open', 'unknown'),
            ('open', 'PRIVATE/relative', 'open', 'unknown'),
            ('fsync', None, 'fsync', 'unknown'),
            ('PRIVATE-SYSCALL', {'PRIVATE': True}, 'unknown', 'unknown'),
        ]
        runtimes = [shutil.which('node')] + [os.environ[name] for name in
                   ('NODE010', 'NODE01025', 'NODE012') if os.environ.get(name)]
        for runtime in runtimes:
            def run(command, **kwargs):
                command = command.replace('/usr/bin/node', shlex.quote(runtime))
                result = subprocess.run(['sh', '-c', command], capture_output=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                self.assertNotIn(b'PRIVATE', result.stdout)
                self.assertNotIn(b'PRIVATE', result.stderr)
                return result.stdout.decode()
            for root_ssh in (False, True):
                root_cases = cases if not root_ssh else [
                    ('open', '/tmp/.cytv-installer-root/PRIVATE', 'open', 'private-storage'),
                    ('mkdir', '/var/lib/clean-your-tv-installer/PRIVATE', 'mkdir', 'public-staging'),
                    ('lstat', '/var/lib', 'lstat', 'storage-parent'),
                    ('open', '/tmp/.cytv-installer/PRIVATE', 'open', 'unknown'),
                ]
                for syscall, path, operation, area in root_cases:
                    with self.subTest(runtime=runtime, root_ssh=root_ssh, syscall=syscall, path=path):
                        program = ("var e=new Error('PRIVATE-MESSAGE');e.code='EACCES';e.syscall=" +
                                   json.dumps(syscall) + ';e.path=' + json.dumps(path) + ';throw e;')
                        plan = dict(self.plan, **({'connection': 'root-ssh'} if root_ssh else {}))
                        with patch.object(observer, 'ROOT_PROGRAM' if root_ssh else 'PROGRAM', program):
                            with self.assertRaises(UserError) as caught:
                                observer.invoke(SimpleNamespace(run=run, root=root_ssh), plan, 'storage-check')
                        report = self.report(caught.exception)
                        self.assertEqual(report['no_root_observer']['filesystem_operation'], operation)
                        self.assertEqual(report['no_root_observer']['storage_area'], area)

    @unittest.skipIf(os.name == 'nt' or not shutil.which('node'), 'Requires POSIX shell and Node')
    def test_real_prepare_and_status_preserve_source_and_refuse_unsafe_state(self):
        calls = []
        def run(command, **kwargs):
            calls.append(command)
            command = command.replace('/usr/bin/node', shlex.quote(shutil.which('node')))
            result = subprocess.run(['sh', '-c', command], capture_output=True, timeout=10)
            if result.returncode:
                raise TVCommandError(result.returncode)
            return result.stdout.decode()
        directory = '/private/tmp' if Path('/private/tmp').exists() else None
        with tempfile.TemporaryDirectory(dir=directory) as tmp:
            root = Path(tmp).resolve()
            root.chmod(0o755)
            public = root / 'public'
            public.mkdir(mode=0o755)
            private = root / 'private'
            remote = SimpleNamespace(run=run)
            with patch.object(observer, 'ROOT', str(private)), patch.object(observer, 'PUBLIC_ROOT', str(public)):
                plan = observer.make_plan('a' * 32, 'b' * 32, 'install',
                                          {'helper.ipk': b'helper', 'launcher.ipk': b'home'},
                                          dict(zip(observer.APPS, ['1', '2'])), public_root=str(public))
                observer.invoke(remote, plan, 'prepare')
                before = {p: p.read_bytes() for p in private.rglob('*') if p.is_file()}
                self.assertEqual((private / 'operations' / ('a' * 32) / 'observer.js').read_text(), observer.PROGRAM)
                result = observer.snapshot(SimpleNamespace(remote=remote), {'plan': plan})
                self.assertEqual(result['reservation'], 'active')
                self.assertEqual([slot['submission'] for slot in result['slots']], ['prepared', 'prepared'])
                private.chmod(0o755)
                with self.assertRaises(UserError) as caught:
                    observer.snapshot(SimpleNamespace(remote=remote), {'plan': plan})
                self.assertEqual(caught.exception.no_root_observer['observer_reason'], 'nonprivate-directory')
                self.assertEqual(len(calls), 3)  # No repair, extra probe or package retry.
                self.assertEqual({p: p.read_bytes() for p in private.rglob('*') if p.is_file()}, before)

    @unittest.skipIf(os.name == 'nt' or not shutil.which('node'), 'Requires POSIX shell and Node')
    def test_real_node_failures_are_bounded_and_keep_storage_guidance(self):
        def run(command, **kwargs):
            command = command.replace('/usr/bin/node', shlex.quote(shutil.which('node')))
            result = subprocess.run(['sh', '-c', command], capture_output=True, timeout=10)
            if result.returncode:
                raise TVCommandError(result.returncode)
            self.assertNotIn(b'PRIVATE', result.stdout)
            self.assertNotIn(b'PRIVATE', result.stderr)
            return result.stdout.decode()
        # The real observer refuses this incomplete plan before touching the filesystem.
        with self.assertRaises(UserError) as caught:
            observer.invoke(SimpleNamespace(run=run), self.plan, 'prepare')
        self.assertEqual(caught.exception.no_root_observer, {
            'command': 'prepare', 'failure': 'observer-error',
            'exception_name': 'Error', 'exception_code': 'unknown', 'observer_reason': 'invalid-plan',
            'filesystem_operation': 'unknown', 'storage_area': 'unknown'})
        for code in ('ENOSPC', 'EDQUOT', 'EACCES', 'PRIVATE-CODE'):
            program = "var e=new Error('PRIVATE-PATH');e.code=" + json.dumps(code) + ";throw e;"
            with self.subTest(code=code), patch.object(observer, 'PROGRAM', program):
                with self.assertRaises(UserError) as caught:
                    observer.invoke(SimpleNamespace(run=run), self.plan, 'status')
                report = self.report(caught.exception, 'recover')
                self.assertEqual(report['no_root_observer']['exception_code'],
                                 'unknown' if code == 'PRIVATE-CODE' else code)
                self.assertNotIn('ssh_command', report)  # No invented nonzero SSH status.
                if code in ('ENOSPC', 'EDQUOT'):
                    self.assertEqual(report['guidance']['code'], 'tv-storage-full')
                    self.assertEqual(report['reason_code'], 'tv-storage-full')

    @unittest.skipIf(os.name == 'nt' or not shutil.which('node'), 'Requires POSIX shell and Node')
    def test_launch_needs_no_env_options_and_clears_node_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = Path(tmp) / 'env'
            env.write_text('#!/bin/sh\nexit 64\n')  # A TV env without -u support.
            env.chmod(0o700)
            environment = dict(os.environ, PATH=tmp + os.pathsep + os.environ.get('PATH', ''),
                               NODE_OPTIONS='--require PRIVATE-MODULE', NODE_PATH='PRIVATE-PATH')
            def run(command, **kwargs):
                command = command.replace('/usr/bin/node', shlex.quote(shutil.which('node')))
                result = subprocess.run(['sh', '-c', command], env=environment,
                                        capture_output=True, timeout=10)
                if result.returncode:
                    raise TVCommandError(result.returncode)
                return result.stdout.decode()
            program = "process.stdout.write(JSON.stringify({operation:JSON.parse(process.argv[process.argv.length-1]).plan.operation,options:process.env.NODE_OPTIONS,path:process.env.NODE_PATH}));"
            with patch.object(observer, 'PROGRAM', program):
                result = observer.invoke(SimpleNamespace(run=run), self.plan, 'status')
            self.assertEqual(result, self.plan)


if __name__ == '__main__':
    unittest.main()
