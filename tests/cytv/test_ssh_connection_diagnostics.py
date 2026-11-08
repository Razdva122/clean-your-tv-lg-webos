"""Socket evidence crosses the normal export/history boundary without addresses."""
import errno
import json
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from paramiko.ssh_exception import NoValidConnectionsError
from cytv import cli, diagnostics, state
from cytv.failure_help import for_error


class SSHConnectionDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = state.Store(self.tmp.name)
        self.profile = state.target('192.0.2.55', 'root')

    def report(self, error=None, action='install', phase='ssh-connect'):
        path = diagnostics.create_report(self.store, action, self.profile, phase, error)
        text = path.read_text()
        self.assertNotIn('PRIVATE', text)
        self.assertNotIn('192.0.2.55', text)
        return json.loads(text)

    def test_typed_socket_causes_survive_current_and_previous_attempt_export(self):
        cases = [(PermissionError(errno.EACCES, 'PRIVATE'), 'access-denied'),
                 (PermissionError(errno.EPERM, 'PRIVATE'), 'access-denied'),
                 (ConnectionRefusedError(errno.ECONNREFUSED, 'PRIVATE'), 'refused'),
                 (TimeoutError('PRIVATE'), 'timeout'),
                 (OSError(errno.ETIMEDOUT, 'PRIVATE'), 'timeout'),
                 (OSError(errno.EHOSTUNREACH, 'PRIVATE'), 'host-unreachable'),
                 (OSError(errno.ENETUNREACH, 'PRIVATE'), 'network-unreachable'),
                 (socket.gaierror(socket.EAI_NONAME, 'PRIVATE'), 'name-resolution'),
                 (OSError(errno.EIO, 'PRIVATE'), 'unknown')]
        for cause, category in cases:
            for wrapped in (False, True):
                error = NoValidConnectionsError({('PRIVATE-HOST', 22): cause}) if wrapped else cause
                with self.subTest(category=category, wrapped=wrapped):
                    report = self.report(error)
                    expected = {'protocol': 'ssh', 'causes': [category]}
                    self.assertEqual(report.get('connection'), expected)
                    self.assertEqual(report['previous_attempt_failure'].get('connection'), expected)

    def test_mixed_causes_are_bounded_unique_and_do_not_claim_a_single_cause(self):
        error = NoValidConnectionsError({('PRIVATE-A', 22): OSError(errno.EACCES, 'PRIVATE'),
                                        ('PRIVATE-B', 22): OSError(errno.ECONNREFUSED, 'PRIVATE'),
                                        ('PRIVATE-C', 22): OSError(errno.ECONNREFUSED, 'PRIVATE')})
        report = self.report(error)
        self.assertEqual(report.get('connection'), {'protocol': 'ssh', 'causes': ['access-denied', 'refused']})
        self.assertEqual(report['reason_code'], 'ssh-unreachable')
        self.assertEqual(for_error(error, 'ssh-connect', self.profile)['code'], 'ssh-unreachable')

    def test_original_and_observation_history_keep_separate_socket_causes(self):
        self.store.begin(self.profile, 'install')
        original = self.report(OSError(errno.EHOSTUNREACH, 'PRIVATE'))
        expected = {'protocol': 'ssh', 'causes': ['host-unreachable']}
        self.assertEqual(original['first_failure'].get('connection'), expected)
        self.store = state.Store(self.tmp.name)
        later = self.report(TimeoutError('PRIVATE'), action='doctor')
        self.assertEqual(later['first_failure'].get('connection'), expected)
        self.assertEqual(later['observation_failure'].get('connection'), {'protocol': 'ssh', 'causes': ['timeout']})

    def test_reexport_filters_untrusted_and_malformed_categories(self):
        for causes, expected in [(['refused', 'PRIVATE', {'private': 'PRIVATE'}, 'refused', True], ['refused']),
                                 ('PRIVATE', []), ({'PRIVATE': 'refused'}, []), (None, [])]:
            result = diagnostics.context.failure_summary({'connection': {
                'protocol': 'ssh', 'causes': causes, 'address': 'PRIVATE', 'errors': 'PRIVATE'}})
            self.assertEqual(result.get('connection'), {'protocol': 'ssh', 'causes': expected})
            self.assertNotIn('PRIVATE', json.dumps(result))

    def test_no_socket_evidence_for_key_file_authentication_other_phases_or_success(self):
        errors = [PermissionError(errno.EACCES, 'PRIVATE', '/PRIVATE/key.pem'),
                  type('AuthenticationException', (Exception,), {})('PRIVATE'), None]
        for error in errors:
            self.assertNotIn('connection', self.report(error))
        self.assertNotIn('connection', self.report(OSError(errno.EHOSTUNREACH, 'PRIVATE'), phase='install-root'))

    def test_doctor_failure_reaches_normal_report_without_device_work_or_retry(self):
        connect = Mock(side_effect=NoValidConnectionsError({
            ('PRIVATE-HOST', 22): OSError(errno.EHOSTUNREACH, 'PRIVATE')}))
        with patch('cytv.cli.package.verify_payload', return_value={}), patch('cytv.cli.Installer') as installer:
            code = cli.main(['doctor', '--report', '--host', '192.0.2.55', '--edition', 'root',
                             '--data-dir', self.tmp.name, '--language', 'en', '--yes'],
                            write=lambda _: None, connect=connect)
        self.assertEqual(code, 1)
        connect.assert_called_once()
        installer.assert_not_called()
        report = json.loads(next(Path(self.tmp.name).glob('reports/*.json')).read_text())
        self.assertEqual(report['connection'], {'protocol': 'ssh', 'causes': ['host-unreachable']})
        self.assertEqual(report['observation_failure']['connection'], report['connection'])
        self.assertEqual(report['checks']['ssh'], 'fail')
        self.assertEqual(report['checks']['root-user'], 'pending')
        self.assertNotIn('PRIVATE', json.dumps(report))
        self.assertNotIn('192.0.2.55', json.dumps(report))

    def test_windows_native_errno_constants_preserve_wsa_categories(self):
        # CPython exposes these WSA values as errno's socket constants on Windows.
        native = {'ECONNREFUSED': 10061, 'ETIMEDOUT': 10060,
                  'EHOSTUNREACH': 10065, 'ENETUNREACH': 10051}
        with patch.multiple(errno, **native):
            for number, category in [(10061, 'refused'), (10060, 'timeout'),
                                     (10065, 'host-unreachable'), (10051, 'network-unreachable')]:
                for wrapped in (False, True):
                    cause = OSError(number, 'PRIVATE')
                    error = NoValidConnectionsError({('PRIVATE-HOST', 22): cause}) if wrapped else cause
                    with self.subTest(number=number, wrapped=wrapped):
                        report = self.report(error)
                        self.assertEqual(report.get('connection'), {'protocol': 'ssh', 'causes': [category]})
