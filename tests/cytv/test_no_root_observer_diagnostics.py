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
