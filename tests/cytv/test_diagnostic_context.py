"""Diagnostic history is evidence only; it never authorizes recovery."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from cytv import cli, diagnostics, state
from cytv.errors import UserError, TVCommandError


class ContextTests(unittest.TestCase):
    def test_recovery_observation_failure_is_separate_from_original_failure(self):
        from paramiko import AuthenticationException
        self.store.begin(self.profile, 'install')
        first = self.report('install', 'install-helper', TVCommandError(127))
        self.store = state.Store(self.tmp.name)
        later = self.report('recover', 'ssh-connect', AuthenticationException('PRIVATE'), status={
            'assessment': {'state': 'PRIVATE', 'reason': 'PRIVATE', 'actions': ['PRIVATE', 'check']}})
        self.assertEqual(later['first_failure'], first['first_failure'])
        self.assertEqual(later['observation_failure']['guidance']['code'], 'ssh-auth-no-root')
        self.assertEqual(later['recovery']['reason'], 'terminal-evidence-missing')
        self.assertEqual(later['status']['assessment'], {
            'state': 'blocked', 'reason': 'observation-unverified', 'actions': ['check']})
        self.assertNotIn('PRIVATE', json.dumps(later))

    def test_package_failure_detail_survives_recovery_error_without_changing_pending(self):
        from cytv.errors import TVRejected
        self.store.begin(self.profile, 'install')
        journal = self.store.device_dir(self.profile) / 'operation.json'
        before = journal.read_bytes()
        error = TVRejected('Install rejected', {'statusValue': 24, 'details': {
            'state': 'install failed', 'errorCode': -1, 'reason': 'FAILED_IPKG_INSTALL'}},
            'com.webos.appInstallService/dev/install')
        self.report('install', 'install-helper', error)
        self.store = state.Store(self.tmp.name)
        later = self.report('uninstall', 'uninstall', TVRejected('Status rejected',
            {'returnValue': False, 'errorCode': -1}, 'com.webos.appInstallService/status'))
        self.assertEqual(later['luna']['operation'], 'package-status')
        self.assertEqual(later['first_failure']['luna']['state'], 'install failed')
        self.assertEqual(later['first_failure']['luna']['reason'], 'FAILED_IPKG_INSTALL')
        self.assertEqual(journal.read_bytes(), before)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = state.Store(self.tmp.name)
        self.profile = state.target('192.0.2.55', 'no-root')

    def report(self, action, phase, error=None, **kwargs):
        path = diagnostics.create_report(self.store, action, self.profile, phase, error, **kwargs)
        return json.loads(path.read_text())

    def test_primary_failure_survives_new_process_status_and_doctor(self):
        self.store.begin(self.profile, 'install')
        before = (self.store.device_dir(self.profile) / 'operation.json').read_bytes()
        first = self.report('install', 'install-helper', TVCommandError(127))
        self.store = state.Store(self.tmp.name)
        later = self.report('status', 'status', TVCommandError(1))
        doctor = self.report('doctor', 'doctor-complete', status={'device': {'helper_state': 'stopped'}})
        self.assertEqual(first['first_failure']['ssh_command']['exit_status'], 127)
        self.assertEqual(later['first_failure'], first['first_failure'])
        self.assertEqual(doctor['first_failure'], first['first_failure'])
        self.assertEqual(later['ssh_command']['exit_status'], 1)
        self.assertEqual((self.store.device_dir(self.profile) / 'operation.json').read_bytes(), before)

    def test_new_operation_and_other_tv_do_not_inherit_old_error(self):
        self.store.begin(self.profile, 'install')
        self.report('install', 'install-helper', TVCommandError(127))
        self.store.finish(self.profile)
        self.store.begin(self.profile, 'install')
        value = self.report('status', 'status', TVCommandError(1))
        self.assertIsNone(value['first_failure'])
        other = state.target('192.0.2.56', 'no-root')
        path = diagnostics.create_report(self.store, 'doctor', other, 'doctor-complete')
        self.assertIsNone(json.loads(path.read_text())['first_failure'])

    def test_legacy_receipt_never_claims_followup_as_primary(self):
        receipt = self.store.device_dir(self.profile) / 'operation.json'
        receipt.write_text('{"action":"install","stage":"pending"}')
        before = receipt.read_bytes()
        value = self.report('status', 'status', TVCommandError(127))
        self.assertIsNone(value['first_failure'])
        self.assertEqual(value['failure_history'], 'not-recorded')
        self.assertEqual(receipt.read_bytes(), before)

    def test_preflight_failure_is_explicitly_previous_attempt_not_pending_cause(self):
        first = self.report('install', 'inspect-installation', TVCommandError(127))
        self.store = state.Store(self.tmp.name)
        later = self.report('doctor', 'doctor-complete')
        self.assertIsNone(later['first_failure'])
        self.assertEqual(later['previous_attempt_failure']['ssh_command']['exit_status'], 127)
        self.assertNotIn('192.0.2.55', json.dumps(later))

    def test_checks_status_and_reason_are_allowlisted(self):
        checks = {'ssh': {'status': 'pass', 'detail': 'PRIVATE-KEY'},
                  'helper-idle': {'status': 'unknown'}, 'PRIVATE-CHECK': {'status': 'fail'}}
        status = {'device': {'apps': [{'id': 'com.gathin.tvhome', 'version': '1.6.1'},
                                    {'id': 'private.app', 'version': 'PRIVATE-VERSION'}],
                             'helper_state': 'stopped', 'private': 'PRIVATE'},
                  'pending': {'product_operation': 'PRIVATE-UUID'}, 'can_resume_root_setup': False}
        value = self.report('doctor', 'doctor-complete', checks=checks, status=status)
        self.assertEqual(value['checks'], {'ssh': 'pass', 'helper-idle': 'unknown'})
        self.assertEqual(value['status']['components'], {'home': '1.6.1'})
        self.assertEqual(value['status']['helper_state'], 'stopped')
        self.assertNotIn('PRIVATE', json.dumps(value))
        error = UserError('PRIVATE-MESSAGE', reason_code='helper-running')
        self.assertEqual(self.report('install', 'preflight', error)['reason_code'], 'helper-running')

    def test_doctor_report_includes_existing_status_result_and_checks(self):
        with patch('cytv.cli.Installer') as cls:
            cls.return_value.status.return_value = {'device': {'helper_state': 'running', 'apps': [
                {'id': 'com.local.nativehome', 'version': '0.6.21'}]}, 'can_resume_root_setup': False}
            remote = MagicMock()
            code = cli.main(['doctor', '--report', '--host', '192.0.2.55', '--edition', 'no-root',
                             '--data-dir', self.tmp.name], write=lambda _: None, connect=lambda *args: remote)
        self.assertEqual(code, 0)
        value = json.loads(next(Path(self.tmp.name).glob('reports/*.json')).read_text())
        self.assertEqual(value['checks']['ssh'], 'pass')
        self.assertEqual(value['status']['components'], {'helper': '0.6.21'})
        self.assertEqual(value['status']['helper_state'], 'running')

    def test_new_receipt_has_private_correlation_and_cannot_override_it(self):
        self.store.begin(self.profile, 'install', diagnostic_id='PRIVATE')
        saved = self.store.pending(self.profile)
        self.assertRegex(saved['diagnostic_id'], r'^[a-f0-9]{32}$')
        identifier = saved['diagnostic_id']
        self.store.checkpoint(self.profile, stage='submitted', diagnostic_id='PRIVATE')
        self.assertEqual(self.store.pending(self.profile)['diagnostic_id'], identifier)
        self.assertNotIn(identifier, json.dumps(self.report('status', 'status')))
    def test_original_rejection_detail_and_version_survive_reexport(self):
        from cytv.errors import TVRejected
        self.store.begin(self.profile, 'install')
        first = self.report('install', 'install-helper', TVRejected('PRIVATE',
            {'returnValue': False, 'errorCode': -1, 'errorText': 'PRIVATE'},
            'com.webos.appInstallService/dev/install'))
        self.store = state.Store(self.tmp.name)
        later = self.report('doctor', 'doctor-complete')
        self.assertEqual(later['first_failure']['luna']['operation'], 'package-install')
        self.assertEqual(later['first_failure']['luna']['error_code'], -1)
        self.assertIn('cytv_version', later['first_failure'])
        self.assertNotIn('PRIVATE', json.dumps(later))

    def test_hostile_history_cannot_export_text_or_change_receipt(self):
        self.store.begin(self.profile, 'install')
        identifier = self.store.pending(self.profile)['diagnostic_id']
        self.report('install', 'install-helper', TVCommandError(127))
        path = self.store.device_dir(self.profile) / 'diagnostic-failures' / (identifier + '.json')
        path.write_text(json.dumps({'reason_code': 'PRIVATE-KEY', 'action': 'PRIVATE',
            'ssh_command': {'exit_status': 'PRIVATE'}, 'status': {'product': {'code': 'PRIVATE'}},
            'checks': {'ssh': 'PRIVATE'}, 'trace': 'PRIVATE', 'private': 'PRIVATE'}))
        value = self.report('doctor', 'doctor-complete')
        self.assertNotIn('PRIVATE', json.dumps(value))
        self.assertEqual(value['first_failure']['reason_code'], 'unknown')

    def test_history_write_failure_does_not_hide_current_error_report(self):
        self.store.begin(self.profile, 'install')
        with patch('cytv.diagnostic_context.os.open', side_effect=OSError('PRIVATE-DISK')):
            # Only history writing fails; final private report writing uses mkstemp too.
            with patch('cytv.diagnostics.private_write') as save:
                path = diagnostics.create_report(self.store, 'install', self.profile,
                                                 'install-helper', TVCommandError(127))
                value = json.loads(save.call_args.args[1])
        self.assertEqual(value['ssh_command']['exit_status'], 127)
        self.assertEqual(value['failure_history'], 'unavailable')

    def test_context_keeps_receipt_snapshot_after_lock_is_released(self):
        from cytv.diagnostic_context import operation_context
        with operation_context(self.store, self.profile):
            self.store.begin(self.profile, 'install')
        original = self.store.pending(self.profile)
        other = state.Store(self.tmp.name)
        other.finish(self.profile)
        other.begin(self.profile, 'uninstall')
        value = self.report('install', 'install-helper', TVCommandError(127))
        self.assertEqual(value['pending']['action'], original['action'])
        self.assertEqual(value['first_failure']['ssh_command']['exit_status'], 127)
        self.assertEqual(other.pending(self.profile)['action'], 'uninstall')

    def test_metadata_is_bounded_best_effort_and_redacted(self):
        from cytv.diagnostic_context import collect_metadata
        remote = MagicMock()
        remote.luna.return_value = {'returnValue': True, 'modelName': 'OLED55C3RLA',
            'sdkVersion': '11.2.0', 'firmwareVersion': '43.21.71', 'serialNumber': 'PRIVATE'}
        info = {}
        collect_metadata(remote, info)
        self.assertEqual(info, {'modelName': 'OLED55C3RLA', 'sdkVersion': '11.2.0',
                                'firmwareVersion': '43.21.71'})
        self.assertLessEqual(remote.luna.call_args.kwargs['timeout'], 5)
        remote.luna.side_effect = TimeoutError('PRIVATE')
        collect_metadata(remote, {})
        value = self.report('doctor', 'doctor-complete', tv_info={
            'modelName': {'serial': 'PRIVATE'}, 'sdkVersion': 'PRIVATE', 'firmwareVersion': '192.0.2.55'})
        self.assertNotIn('PRIVATE', json.dumps(value))
        self.assertNotIn('192.0.2.55', json.dumps(value))

    def test_symlink_or_corrupt_history_is_unavailable_and_preserved(self):
        self.store.begin(self.profile, 'install')
        self.report('install', 'install-helper', TVCommandError(127))
        identifier = self.store.pending(self.profile)['diagnostic_id']
        path = self.store.device_dir(self.profile) / 'diagnostic-failures' / (identifier + '.json')
        for contents in ('{', '[]'):
            path.write_text(contents)
            value = self.report('doctor', 'doctor-complete')
            self.assertEqual(value['failure_history'], 'unavailable')
            self.assertEqual(path.read_text(), contents)
        path.unlink()
        secret = Path(self.tmp.name) / 'private.json'
        secret.write_text('{"reason_code":"PRIVATE"}')
        path.symlink_to(secret)
        value = self.report('doctor', 'doctor-complete')
        self.assertEqual(value['failure_history'], 'unavailable')
        self.assertNotIn('PRIVATE', json.dumps(value))

    def test_successful_export_failure_does_not_fail_doctor(self):
        with patch('cytv.cli.Installer') as cls, patch('cytv.diagnostics.private_write', side_effect=OSError('PRIVATE')):
            cls.return_value.status.return_value = {'device': {'helper_state': 'stopped'}}
            code = cli.main(['doctor', '--report', '--host', '192.0.2.55', '--edition', 'no-root',
                             '--data-dir', self.tmp.name], write=lambda _: None, connect=lambda *args: MagicMock())
        self.assertEqual(code, 0)

    def test_secondary_failure_never_becomes_missing_original(self):
        self.store.begin(self.profile, 'install')
        self.store = state.Store(self.tmp.name)
        value = self.report('doctor', 'doctor', TVCommandError(127))
        self.assertIsNone(value['first_failure'])
        self.assertEqual(value['failure_history'], 'not-recorded')

    def test_verified_success_clears_only_previous_attempt_pointer(self):
        from cytv.diagnostic_context import clear_previous_attempt
        self.report('install', 'preflight', TVCommandError(127))
        reports = list((Path(self.tmp.name) / 'reports').glob('*.json'))
        clear_previous_attempt(self.store, self.profile)
        self.assertNotIn('previous_attempt_failure', self.report('doctor', 'doctor-complete'))
        self.assertTrue(all(path.exists() for path in reports))

    def test_primary_retains_safe_helper_runtime_and_status_observations(self):
        self.store.begin(self.profile, 'install')
        info = {'helper_state': 'running', 'kernel_arch': 'aarch64', 'userland_abi': 'arm32',
                'arm32_supported': True, 'root_requirements': {'node-version': 'fail', 'PRIVATE': 'pass'}}
        first = self.report('install', 'preflight', UserError('PRIVATE', reason_code='helper-running'),
                            tv_info=info, status={'device': {'helper_state': 'running', 'apps': [
                                {'id': 'com.local.nativehome', 'version': '0.6.21'}]}})
        self.store = state.Store(self.tmp.name)
        later = self.report('doctor', 'doctor-complete')
        original = later['first_failure']
        self.assertEqual(original['tv']['helper_state'], 'running')
        self.assertEqual(original['tv']['userland_abi'], 'arm32')
        self.assertIs(original['tv']['arm32_supported'], True)
        self.assertEqual(original['tv']['root_requirements'], {'node-version': 'fail'})
        self.assertEqual(original['status']['components'], {'helper': '0.6.21'})
        self.assertEqual(original['status']['helper_state'], 'running')
        self.assertNotIn('PRIVATE', json.dumps(later))

    def test_model_field_rejects_an_address(self):
        value = self.report('doctor', 'doctor-complete', tv_info={'modelName': '192.0.2.55'})
        self.assertNotIn('192.0.2.55', json.dumps(value))

    def test_real_cli_failure_then_new_cli_status_keeps_original_error(self):
        def installer(remote, store, profile, *args, **kwargs):
            instance = MagicMock()
            instance.version_summary.return_value = []
            def fail(*args, **kwargs):
                store.begin(profile, 'install')
                raise TVCommandError(127)
            instance.install.side_effect = fail
            return instance
        with patch('cytv.cli.Installer', side_effect=installer), patch('cytv.cli.package.verify_payload', return_value={}):
            code = cli.main(['install', '--migrate-home', '--yes', '--host', '192.0.2.55',
                             '--edition', 'root', '--data-dir', self.tmp.name],
                            write=lambda _: None, connect=lambda *args: MagicMock())
        self.assertEqual(code, 2)
        def fail_status(*args):
            raise TVCommandError(1)
        code = cli.main(['status', '--host', '192.0.2.55', '--edition', 'root',
                         '--data-dir', self.tmp.name], write=lambda _: None, connect=fail_status)
        self.assertEqual(code, 2)
        values = [json.loads(path.read_text()) for path in Path(self.tmp.name).glob('reports/*.json')]
        later = next(value for value in values if value['action'] == 'status')
        self.assertEqual(later['ssh_command']['exit_status'], 1)
        self.assertEqual(later['first_failure']['ssh_command']['exit_status'], 127)

    def test_root_worker_categories_reach_primary_host_report(self):
        from cytv.operations import Installer
        remote = MagicMock()
        remote.run.return_value = json.dumps({'operation': 'a'*32, 'state': 'recovery_required',
            'stage': 'root-deploy', 'code': 'installation_requires_recovery',
            'failure': {'exception_type': 'CalledProcessError', 'exit_status': 127,
                        'command': 'PRIVATE', 'stderr': 'PRIVATE'}})
        self.store.begin(self.profile, 'install')
        installer = Installer(remote, self.store, self.profile, '.', {})
        installer._python = lambda: '/usr/bin/python3'
        with self.assertRaises(UserError) as caught:
            installer.await_product('install', 'a'*32, '/verified')
        value = self.report('install', 'install-root', caught.exception,
                            status=installer.tv_info['status'])
        self.assertEqual(value['first_failure']['status']['product']['failure'],
                         {'exception_type': 'CalledProcessError', 'exit_status': 127})
        self.assertNotIn('PRIVATE', json.dumps(value))

    def test_hostile_worker_categories_are_revalidated(self):
        value = self.report('status', 'status', status={'device': {'product': {'state': 'recovery_required',
            'failure': {'exception_type': 'PRIVATE', 'exit_status': True, 'errno': 'PRIVATE',
                        'command': 'PRIVATE'}}}})
        self.assertEqual(value['status']['product']['failure'], {'exception_type': 'unknown'})
        self.assertNotIn('PRIVATE', json.dumps(value))


if __name__ == '__main__':
    unittest.main()
