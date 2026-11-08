"""Diagnostic history is evidence only; it never authorizes recovery."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from cytv import cli, diagnostics, state
from cytv.errors import UserError, TVCommandError


class ContextTests(unittest.TestCase):
    def test_root_inventory_summary_excludes_untrusted_details(self):
        report=self.report('install','read-inventory',UserError('PRIVATE'),tv_info={'root_inventory':{
            'applications':'read','inputs':'unavailable','raw':'PRIVATE'}})
        self.assertEqual(report['tv'].get('root_inventory'),{'applications':'read','inputs':'unavailable'})
        self.assertNotIn('PRIVATE',json.dumps(report))
        unknown=diagnostics.context.tv_summary({'root_inventory':{
            'applications':'PRIVATE','inputs':{'devices':'PRIVATE'}}})
        self.assertEqual(unknown.get('root_inventory'),{'applications':'unknown','inputs':'unknown'})
        self.assertNotIn('PRIVATE',json.dumps(unknown))

    def test_root_inventory_failures_revalidate_all_fields(self):
        report=self.report('install','read-inventory',UserError('PRIVATE'),tv_info={
            'root_inventory_failures':{
                'applications':{'reason':'permission-denied','error_code':-1,'raw':'PRIVATE'},
                'inputs':{'reason':'PRIVATE','error_code':True,'path':'PRIVATE'},
                'PRIVATE':{'reason':'timeout'}}})
        self.assertEqual(report['tv'].get('root_inventory_failures'),{
            'applications':{'reason':'permission-denied','error_code':-1},
            'inputs':{'reason':'unknown'}})
        self.assertNotIn('PRIVATE',json.dumps(report))
        for code in (True,2**31,-2**31-1,1.5,'PRIVATE',{},None):
            value=diagnostics.context.tv_summary({'root_inventory_failures':{
                'applications':{'reason':'negative-reply','error_code':code}}})
            self.assertEqual(value.get('root_inventory_failures'),{
                'applications':{'reason':'negative-reply'}})

    def test_worker_failures_export_current_call_but_strip_untrusted_fields(self):
        from cytv.diagnostic_context import product_summary
        product={'failure':{'exception_type':'RuntimeError',
            'luna':{'call':'apps-dev','reason':'permission-denied','error_code':-1,'error_text':'PRIVATE'}},
            'last_failure':{'exception_type':'TimeoutError','stage':'original-writers-fenced',
                'luna':{'call':'home-settings','reason':'timeout','error_code':True,'raw':'PRIVATE'}}}
        report=self.report('uninstall','uninstall',status={'device':{'product':product}})
        value=report['status']['product']
        self.assertEqual(value['failure'],{'exception_type':'RuntimeError',
            'luna':{'call':'apps-dev','reason':'permission-denied','error_code':-1}})
        self.assertEqual(value.get('last_failure'),{'exception_type':'TimeoutError','stage':'original-writers-fenced',
            'luna':{'call':'home-settings','reason':'timeout'}})
        self.assertNotIn('PRIVATE',json.dumps(report))
        unknown=product_summary({'last_failure':{'exception_type':'PRIVATE','stage':'PRIVATE',
            'luna':{'call':'PRIVATE','reason':'PRIVATE','error_code':'PRIVATE'}}})
        self.assertNotIn('PRIVATE',json.dumps(unknown))

    def test_cleanup_step_survives_export_and_history_with_allowlist(self):
        self.store.begin(self.profile,'install')
        original=self.report('install','activate-root',TVCommandError(1))['first_failure']
        self.store.request_clean_removal(self.profile)
        product={'last_failure':{'exception_type':'CalledProcessError','exit_status':1,
            'stage':'original-writers-fenced','cleanup_step':'runtime-restore','stderr':'PRIVATE'}}
        report=self.report('recover','recover',UserError('PRIVATE',reason_code='cleanup-check-failed'),
            status={'device':{'product':product}})
        expected=report['status']['product']['last_failure']
        self.assertEqual(expected.get('cleanup_step'),'runtime-restore')
        self.assertEqual(report['observation_failure']['status']['product']['last_failure'],expected)
        later=self.report('doctor','doctor-complete')
        self.assertEqual(later['first_failure'],original)
        history_store=state.Store(Path(self.tmp.name)/'history')
        history_store.begin(self.profile,'uninstall')
        diagnostics.create_report(history_store,'uninstall',self.profile,'uninstall',UserError('PRIVATE'),
            status={'device':{'product':product}})
        saved=json.loads(diagnostics.create_report(history_store,'doctor',self.profile,'doctor-complete').read_text())
        self.assertEqual(saved['first_failure']['status']['product']['last_failure'],expected)
        product['last_failure']['cleanup_step']='PRIVATE'
        unsafe=self.report('status','status',status={'device':{'product':product}})
        self.assertEqual(unsafe['status']['product']['last_failure']['cleanup_step'],'unknown')
        self.assertNotIn('PRIVATE',json.dumps([report,later,unsafe]))

    def test_removal_reports_keep_fixed_failure_codes_without_private_messages(self):
        for reason in ('root-worker-busy', 'root-access-required', 'removal-failed',
                       'cleanup-check-failed', 'connection-interrupted'):
            with self.subTest(reason=reason):
                report = self.report('uninstall', 'uninstall',
                                     UserError('PRIVATE-MESSAGE', reason_code=reason))
                self.assertEqual(report['reason_code'], reason)
                self.assertNotIn('PRIVATE-MESSAGE', json.dumps(report))

    def test_clean_removal_keeps_original_failure_after_success_and_exports_current_proof(self):
        self.store.begin(self.profile,'install')
        first=self.report('install','install-helper',TVCommandError(127))
        self.store.request_clean_removal(self.profile)
        self.store.checkpoint(self.profile,stage='verified-clean',removal_reason='removal-verified',
                              result={'removed':True,'verified_clean':True})
        self.store.finish_clean_removal(self.profile)
        later=self.report('uninstall','uninstall',status={'removed':True,'verified_clean':True})
        self.assertEqual(later['first_failure'],first['first_failure'])
        self.assertEqual(later['status'],{'removed':True,'verified_clean':True})
        self.assertIsNone(later['pending'])

    def test_clean_removal_unknown_original_does_not_become_new_ssh_failure(self):
        self.store.begin(self.profile,'install')
        original=self.store.pending(self.profile)
        self.store.request_clean_removal(self.profile)
        later=self.report('uninstall','ssh-connect',TVCommandError(255))
        self.assertIsNone(later['first_failure'])
        self.assertEqual(later['ssh_command']['exit_status'],255)
        self.assertEqual(self.store.pending(self.profile)['previous'],original)

    def test_clean_removal_original_receipt_lineage_is_bounded_and_projected(self):
        self.store.begin(self.profile,'install')
        first=self.report('install','install-helper',TVCommandError(127))
        intent=self.store.request_clean_removal(self.profile)
        intent.pop('previous')
        path=self.store.device_dir(self.profile)/'operation.json'
        state.private_write(path,json.dumps(intent).encode())
        later=self.report('uninstall','ssh-connect',TVCommandError(255))
        self.assertEqual(later['first_failure'],first['first_failure'])
        self.assertNotIn(intent['diagnostic_id'],json.dumps(later))
        intent['original_receipt']='../PRIVATE.json'
        state.private_write(path,json.dumps(intent).encode())
        blocked=self.report('uninstall','ssh-connect',TVCommandError(255))
        self.assertEqual(blocked['failure_history'],'unavailable')
        self.assertIsNone(blocked['first_failure'])

    def test_truncated_original_lineage_does_not_guess_the_first_failure(self):
        self.store.begin(self.profile,'install')
        self.report('install','install-helper',TVCommandError(127))
        original=self.store.pending(self.profile)
        for _ in range(17):original={'action':'install','previous':original}
        state.private_write(self.store.device_dir(self.profile)/'operation.json',json.dumps(original).encode())
        self.store.request_clean_removal(self.profile)
        later=self.report('uninstall','ssh-connect',TVCommandError(255))
        self.assertIsNone(later['first_failure'])
        self.assertEqual(later['failure_history'],'unavailable')

    def test_intermediate_removal_failure_does_not_fill_unknown_original_cause(self):
        from paramiko import AuthenticationException
        self.store.begin(self.profile,'install')
        original=self.store.pending(self.profile)
        self.store.finish(self.profile)  # Model the retained historical wrapper shape.
        self.store.begin(self.profile,'uninstall',previous=original)
        intermediate=self.report('uninstall','uninstall',TVCommandError(127))
        self.store.request_clean_removal(self.profile)
        later=self.report('uninstall','ssh-connect',AuthenticationException('PRIVATE CURRENT'))
        self.assertIsNone(later['first_failure'])
        self.assertEqual(later['failure_history'],'not-recorded')
        self.assertEqual(later['intermediate_failures'],[intermediate['first_failure']])
        self.assertEqual(later['reason_code'],'ssh-authentication')
        self.assertNotIn('PRIVATE',json.dumps(later))

    def test_repeated_original_diagnostic_id_keeps_known_original_cause(self):
        from paramiko import AuthenticationException
        self.store.begin(self.profile,'install')
        first=self.report('install','install-helper',TVCommandError(127))
        original=self.store.pending(self.profile)
        self.store.checkpoint(self.profile,action='uninstall',previous=original)
        self.assertEqual(self.store.pending(self.profile)['diagnostic_id'],original['diagnostic_id'])
        self.store.request_clean_removal(self.profile)
        later=self.report('uninstall','ssh-connect',AuthenticationException('PRIVATE CURRENT'))
        self.assertEqual(later['first_failure'],first['first_failure'])
        self.assertEqual(later['failure_history'],'recorded')
        self.assertFalse(later.get('intermediate_failures'))

    def test_recovery_proof_categories_are_fixed_and_do_not_export_admission_material(self):
        from cytv.diagnostic_context import status_summary
        value=status_summary({'device':{'product':{'resume_reason':'original-snapshot-unverified','operation':'PRIVATE'}},
            'cancellation':{'state':'blocked','reason':'stock-routing-unverified','proof_sha256':'PRIVATE','candidate_sha256':'PRIVATE'}})
        self.assertEqual(value['product']['resume_reason'],'original-snapshot-unverified')
        self.assertEqual(value['cancellation'],{'state':'blocked','reason':'stock-routing-unverified'})
        self.assertNotIn('PRIVATE',json.dumps(value))
        self.assertEqual(status_summary({'cancellation':{'state':'PRIVATE','reason':'PRIVATE'}})['cancellation'],
                         {'state':'unknown','reason':'unknown'})
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
        root_profile=state.target('192.0.2.55','root')
        (self.store.device_dir(root_profile)/'known_hosts').write_bytes(b'original pin')
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
