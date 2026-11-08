import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cytv import cli, diagnostics, state


class DiagnosticTests(unittest.TestCase):
    def test_icon_counts_are_allowlisted_again_before_report_and_history_export(self):
        counts = {'schema': 'PRIVATE', 'status': 'complete', 'apps': 7, 'embedded': 2,
                  'fallback': 5, 'missing_uri': 1, 'rejected_uri': 2,
                  'fetch_failed': 2, 'invalid_image': 1, 'PRIVATE': 'PRIVATE'}
        with tempfile.TemporaryDirectory() as tmp:
            path = diagnostics.create_report(state.Store(tmp), 'install', None, 'read-inventory',
                                             tv_info={'icon_inventory': counts})
            report = json.loads(path.read_text())
            expected = dict(counts, schema=1)
            del expected['PRIVATE']
            self.assertEqual(report['tv'].get('icon_inventory'), expected)
            from cytv.diagnostic_context import failure_summary, tv_summary
            self.assertEqual(failure_summary(report)['tv']['icon_inventory'], expected)
            self.assertNotIn('PRIVATE', path.read_text())
            for value in (-1, 1801, True, 'PRIVATE', {}, []):
                with self.subTest(value=value):
                    safe = tv_summary({'icon_inventory': {'status': 'PRIVATE', 'apps': value}})
                    self.assertEqual(safe['icon_inventory'], {'schema': 1, 'status': 'unavailable'})

    def test_ssh_report_exports_cause_without_wrapped_addresses_or_error_text(self):
        import errno
        from paramiko.ssh_exception import NoValidConnectionsError
        with tempfile.TemporaryDirectory() as tmp:
            for number, code in [(errno.EACCES, 'ssh-access-denied'),
                                 (errno.ECONNREFUSED, 'ssh-refused'), (errno.ETIMEDOUT, 'ssh-timeout')]:
                error = NoValidConnectionsError({('PRIVATE-HOST', 22): OSError(number, 'PRIVATE-TEXT')})
                path = diagnostics.create_report(state.Store(tmp), 'install', None, 'ssh-connect', error)
                report = json.loads(path.read_text())
                self.assertEqual(report['reason_code'], code)
                self.assertEqual(report['guidance']['code'], code)
                self.assertNotIn('PRIVATE', path.read_text())

    def test_package_failure_states_and_fixed_reasons_survive_report_export(self):
        from cytv.transport import terminal_reply
        from cytv.errors import TVRejected
        for method, terminal, remote_state in (
            ('install', 'installed', 'install failed'),
            ('remove', 'removed', 'remove failed'),
        ):
            for reason in ('FAILED_INTERNAL_ERROR', 'FAILED_CREATE_TMP',
                           'FAILED_NOT_ENOUGH_TEMP_SPACE', 'FAILED_NOT_ENOUGH_INSTALL_SPACE',
                           'FAILED_PACKAGEFILE_NOT_FOUND', 'FAILED_PACKAGEFILE_CORRUPT',
                           'FAILED_VERIFY', 'FAILED_IPKG_INSTALL', 'FAILED_INSTALL'):
                with self.subTest(method=method, reason=reason), tempfile.TemporaryDirectory() as tmp:
                    with self.assertRaises(TVRejected) as caught:
                        terminal_reply({'statusValue': 24, 'details': {
                            'state': remote_state, 'errorCode': -1, 'reason': reason,
                            'ipkFile': 'PRIVATE-PATH'}}, terminal,
                            uri='com.webos.appInstallService/dev/' + method)
                    path = diagnostics.create_report(state.Store(tmp), method, None,
                                                     method + '-helper', caught.exception)
                    luna = json.loads(path.read_text())['luna']
                    self.assertEqual(luna['state'], remote_state)
                    self.assertEqual(luna['reason'], reason)
                    self.assertEqual(luna['details_error_code'], -1)
                    self.assertNotIn('PRIVATE', path.read_text())

    def test_package_reason_is_revalidated_before_export(self):
        from cytv.errors import TVRejected
        for reason in ('PRIVATE-KEY', 'FAILED_VERIFY PRIVATE-PATH',
                       {'reason': 'PRIVATE-KEY'}, ['PRIVATE'], None, True):
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as tmp:
                error = TVRejected('PRIVATE-MESSAGE', {'details': {
                    'state': 'install failed', 'reason': reason}})
                self.assertEqual(error.luna.get('reason'), 'unknown')
                error.luna['reason'] = reason
                path = diagnostics.create_report(state.Store(tmp), 'install', None,
                                                 'install-helper', error)
                self.assertEqual(json.loads(path.read_text())['luna']['reason'], 'unknown')
                self.assertNotIn('PRIVATE', path.read_text())

    def test_passive_root_status_exports_fixed_categories_only(self):
        value={'schema':1,'status':'read','operation':'consistent-not-admission',
               'worker':'exception-recorded','python':'private-bytes-match-unexecuted','private':'PRIVATE-PASSWORD'}
        result=diagnostics.context.product_summary({'state':'recovery_required','passive':value})
        self.assertEqual(result['passive'],{k:v for k,v in value.items() if k!='private'})
        value['python']={'secret':'PRIVATE-PATH'}
        self.assertEqual(diagnostics.context.product_summary({'passive':value})['passive']['python'],'unknown')
        self.assertNotIn('PRIVATE',json.dumps(diagnostics.context.product_summary({'passive':value})))

    def test_helper_state_rejects_unknown_or_structured_remote_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            for value in ('PRIVATE-PROCESS', {'process': 'PRIVATE-PATH'}, None, True):
                path = diagnostics.create_report(state.Store(tmp), 'install', None, 'preflight',
                                                 tv_info={'helper_state': value})
                self.assertEqual(json.loads(path.read_text())['tv'].get('helper_state'), 'unknown')
                self.assertNotIn('PRIVATE-', path.read_text())

    def test_python_cache_reason_is_revalidated_before_export(self):
        from cytv.errors import PythonCacheError
        with tempfile.TemporaryDirectory() as tmp:
            error = PythonCacheError('network')
            error.reason = 'PRIVATE-URL-AND-PATH'
            path = diagnostics.create_report(state.Store(tmp), 'install', None, 'preflight', error)
            self.assertEqual(json.loads(path.read_text())['python_cache'], {'reason': 'unknown'})
            self.assertNotIn('PRIVATE', path.read_text())

    def test_root_command_context_is_allowlisted_again_at_export(self):
        from cytv.errors import TVCommandError
        with tempfile.TemporaryDirectory() as tmp:
            error=TVCommandError(127)
            error.root_action='PRIVATE-ACTION';error.root_boundary={'private':'PRIVATE-PATH'}
            text=diagnostics.create_report(state.Store(tmp),'status',None,'status',error).read_text()
            self.assertEqual(json.loads(text)['ssh_command'],{'exit_status':127})
            self.assertNotIn('PRIVATE-',text)

    def test_restore_rejections_identify_only_allowlisted_operations(self):
        from cytv.transport import terminal_reply
        from cytv.errors import TVRejected
        for uri, operation in (
            ('com.local.nativehome.service/disable', 'helper-disable'),
            ('com.webos.service.eim/deleteDevice', 'eim-delete-device'),
            ('com.webos.applicationManager/launch', 'application-launch'),
            ('PRIVATE-SERVICE/PRIVATE-METHOD', 'luna-call'),
        ):
            with self.subTest(uri=uri), tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(TVRejected) as caught:
                    terminal_reply({'returnValue': False, 'errorCode': -101,
                                    'errorText': 'PRIVATE-REMOTE-TEXT'}, uri=uri)
                path = diagnostics.create_report(state.Store(tmp), 'restore', None, 'restore', caught.exception)
                self.assertEqual(json.loads(path.read_text())['luna']['operation'], operation)
                self.assertNotIn('PRIVATE-', path.read_text())

    def test_package_rejection_preserves_safe_metadata_from_luna_to_report(self):
        from cytv.transport import SSH
        from cytv.errors import TVRejected
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp:
            ssh=object.__new__(SSH);ssh.root=False
            channel=SimpleNamespace(close=lambda:None)
            ssh.channel=lambda command:channel
            ssh.chunks=lambda connection,timeout:[json.dumps({
                'returnValue':False,'errorCode':-1,'errorText':'PRIVATE-KEY 192.0.2.55',
                'statusValue':30,'details':{'errorCode':'-17','state':'FAILED',
                'ipkFile':'/private/staging','packageId':'private.app'}}).encode()]
            with self.assertRaises(TVRejected) as caught:
                ssh.luna('com.webos.appInstallService/dev/install',{},terminal='installed')
            path=diagnostics.create_report(state.Store(tmp),'install',None,'install-helper',caught.exception)
            self.assertEqual(json.loads(path.read_text())['luna'],{
                'operation':'package-install','error_code':-1,'details_error_code':-17,
                'status_value':30,'state':'failed','return_value':False})
            for secret in ('PRIVATE-KEY','192.0.2.55','/private/staging','private.app'):
                self.assertNotIn(secret,path.read_text())
                self.assertNotIn(secret,str(caught.exception))

    def test_luna_rejection_metadata_rejects_non_numeric_codes_and_unknown_states(self):
        from cytv.transport import terminal_reply
        from cytv.errors import TVRejected
        with tempfile.TemporaryDirectory() as tmp:
            for code in (True, 1.5, 2**40, '-999999999999', 'PRIVATE-CODE', {'key':'PRIVATE'}):
                with self.subTest(code=code):
                    with self.assertRaises(TVRejected) as caught:
                        terminal_reply({'returnValue':False,'errorCode':code,'statusValue':code,
                            'details':{'state':'PRIVATE-STATE','errorCode':code}},uri='PRIVATE-URI')
                    path=diagnostics.create_report(state.Store(tmp),'install',None,'install-helper',caught.exception)
                    value=json.loads(path.read_text())['luna']
                    self.assertEqual(value,{'operation':'luna-call','error_code':None,
                        'details_error_code':None,'status_value':None,'state':'unknown','return_value':False})
                    self.assertNotIn('PRIVATE',path.read_text())

    def test_failed_package_state_without_error_code_still_exports_reason(self):
        from cytv.transport import terminal_reply
        from cytv.errors import TVRejected
        with self.assertRaises(TVRejected) as caught:
            terminal_reply({'details':{'state':'FAILED'}},'removed',uri='com.webos.appInstallService/dev/remove')
        with tempfile.TemporaryDirectory() as tmp:
            path=diagnostics.create_report(state.Store(tmp),'remove',None,'remove-home',caught.exception)
            value=json.loads(path.read_text())['luna']
            self.assertEqual(value['operation'],'package-remove')
            self.assertEqual(value['state'],'failed')
            self.assertIsNone(value['return_value'])

    def test_project_apps_cleanup_reason_survives_without_remote_text(self):
        from cytv.errors import UserError
        with tempfile.TemporaryDirectory() as tmp:
            report=diagnostics.create_report(state.Store(tmp),'status',None,'status',
                UserError('PRIVATE',reason_code='project-apps-remain'))
            value=json.loads(report.read_text())
            self.assertEqual(value['reason_code'],'project-apps-remain')
            self.assertNotIn('PRIVATE',report.read_text())

    def test_developer_key_reason_is_allowlisted_without_credentials_or_exception_text(self):
        from cytv.errors import DeveloperKeyError
        with tempfile.TemporaryDirectory() as tmp:
            for reason in ('response-format', 'key-unlock', 'PRIVATE-REASON'):
                error = DeveloperKeyError('PRIVATE-MESSAGE', reason)
                path = diagnostics.create_report(state.Store(tmp), 'install', None, 'ssh-connect', error)
                report = json.loads(path.read_text())
                self.assertEqual(report['connection'], {'protocol': 'developer-key',
                    'reason_code': reason if reason != 'PRIVATE-REASON' else 'unknown'})
                self.assertNotIn('PRIVATE-', path.read_text())

    def setUp(self):
        from cytv import i18n
        i18n.set_language('en')
        self.addCleanup(i18n.set_language, 'en')
        language = patch('cytv.i18n.system_languages', return_value=['en'])
        language.start()
        self.addCleanup(language.stop)

    def test_ssap_protocol_metadata_is_allowlisted_without_remote_reason_text(self):
        from cytv.errors import TVConnectionError
        with tempfile.TemporaryDirectory() as tmp:
            error=TVConnectionError('Installer-owned message', close_code=1008, reason_code='PRIVATE-REMOTE-REASON')
            path=diagnostics.create_report(state.Store(tmp), 'install', None, 'pair-tv', error)
            value=json.loads(path.read_text())
            self.assertEqual(value['connection'], {'protocol':'ssap','close_code':1008,'reason_code':'connection-closed'})
            self.assertNotIn('PRIVATE-REMOTE-REASON', path.read_text())

    def test_report_includes_only_allowlisted_tv_architecture_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = state.Store(tmp)
            info = {'kernel_arch': 'aarch64', 'userland_abi': 'arm32',
                    'arm32_supported': True, 'raw_elf': 'PRIVATE-ELF', 'host': '192.0.2.55'}
            path = diagnostics.create_report(store, 'install', None, 'preflight', tv_info=info)
            self.assertEqual(json.loads(path.read_text())['tv'], {
                'kernel_arch': 'aarch64', 'userland_abi': 'arm32', 'arm32_supported': True})
            info.update(kernel_arch='PRIVATE-KERNEL', userland_abi='PRIVATE-ABI', arm32_supported='SECRET')
            path = diagnostics.create_report(store, 'install', None, 'preflight', tv_info=info)
            self.assertEqual(json.loads(path.read_text())['tv'], {
                'kernel_arch': 'unknown', 'userland_abi': 'unknown'})
            for private in ('PRIVATE-', '192.0.2.55', 'SECRET'):
                self.assertNotIn(private, path.read_text())

    def test_report_excludes_exception_text_addresses_keys_and_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = state.Store(tmp)
            profile = state.target('192.0.2.55', 'root', identity='/private/secret-personal-key')
            store.begin(profile, 'install')
            store.checkpoint(profile, expected={'private.app.name': 'privatehash'}, eim_registered='unknown')
            try:
                raise RuntimeError('password=ULTRASECRET 192.0.2.55 client-key=PAIRINGKEY private.app.name')
            except RuntimeError as error:
                report = diagnostics.create_report(store, 'install', profile, 'ssh-connect', error)
            raw = report.read_text()
            value = json.loads(raw)
            for private in ('ULTRASECRET', '192.0.2.55', 'PAIRINGKEY', 'private.app.name', 'secret-personal-key'):
                self.assertNotIn(private, raw)
            self.assertEqual(value['phase'], 'ssh-connect')
            self.assertEqual(value['pending'], {'action': 'install', 'stage': 'pending'})
            self.assertTrue(value['trace'])
            self.assertEqual(value['edition'], 'root')

    def test_cli_architecture_failure_preserves_probe_results_in_report(self):
        class Remote:
            def run(self, command, **kwargs):
                if 'CYTV_NODE_VERSION' in command: return 'CYTV_NODE_MISSING'
                if command == 'uname -m': return 'aarch64'
                if command == 'LC_ALL=C od -An -v -t u1 -N 20 /bin/sh':
                    return '127 69 76 70 2 1 1 0 0 0 0 0 0 0 0 0 2 0 183 0'
                raise AssertionError('Unexpected command')
            def close(self): pass
        with tempfile.TemporaryDirectory() as tmp:
            code = cli.main(['doctor', '--host', '192.0.2.55', '--edition', 'no-root',
                             '--data-dir', tmp], write=lambda _: None, connect=lambda *args: Remote())
            self.assertEqual(code, 2)
            reports = list(Path(tmp).glob('reports/*.json'))
            self.assertEqual(len(reports), 1)
            self.assertEqual(json.loads(reports[0].read_text())['tv'], {
                'node_version_status': 'missing',
                'kernel_arch': 'aarch64', 'userland_abi': 'arm64', 'arm32_supported': False})

    def test_cli_failure_provides_issue_link_report_and_requested_debug_details(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = []
            def fail(*args):
                raise OSError('PRIVATE TRANSPORT DATA')
            code = cli.main(['status', '--host', '192.0.2.55', '--edition', 'root', '--data-dir', tmp],
                            write=output.append, connect=fail)
            text = '\n'.join(output)
            self.assertEqual(code, 1)
            self.assertIn('https://github.com/Razdva122/clean-your-tv-lg-webos/issues/new', text)
            self.assertIn('diagnostic-', text)
            self.assertIn('expected', text)
            self.assertNotIn('PRIVATE TRANSPORT DATA', text)
            reports = list(Path(tmp).glob('reports/*.json'))
            self.assertEqual(len(reports), 1)
            self.assertEqual(json.loads(reports[0].read_text())['phase'], 'ssh-connect')


if __name__ == '__main__':
    unittest.main()
