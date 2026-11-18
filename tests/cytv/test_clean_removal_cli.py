import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from paramiko import AuthenticationException
from cytv import cli, diagnostics, state
from cytv.errors import TVCommandError, UserError
from cytv.terminal import Console


class Capture(Console):
    frontend='android'
    def __init__(self):
        super().__init__(lambda value:None,interactive=False)
        self.plans=[];self.profiles=[];self.reports=[]
    def recovery(self,profile):self.profiles.append(dict(profile))
    def recovery_plan(self,value):self.plans.append(value)
    def report(self,path):self.reports.append(path)


class CleanupConnectionWire(unittest.TestCase):
    def test_unreadable_operation_stops_before_ssh_with_local_diagnostic(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = state.Store(tmp)
            profile = state.target('192.0.2.50', 'root')
            store.save(profile)
            directory = store.device_dir(profile)
            (directory / 'known_hosts').write_bytes(b'original pin')
            store.request_clean_removal(profile)
            receipt = directory / 'operation.json'
            original = receipt.read_bytes()
            open_file = Path.open

            def open_with_denial(path, *args, **kwargs):
                if path == receipt:
                    denied = PermissionError('PRIVATE failure')
                    denied.winerror = 5
                    raise denied
                return open_file(path, *args, **kwargs)

            for command in ('uninstall', 'recover'):
                with self.subTest(command=command):
                    write, connect = Capture(), Mock()
                    with patch('cytv.state.platform', 'win32'), patch.object(Path, 'open', open_with_denial):
                        code = cli.main([command, '--language', 'en', '--yes', '--host', profile['host'],
                                         '--edition', 'root', '--data-dir', tmp], write=write, connect=connect, ask=lambda _: 'y')
                    self.assertEqual(code, 2)
                    connect.assert_not_called()
                    report = json.loads(write.reports[-1].read_bytes())
                    self.assertEqual(report['local_recovery'], {'reason': 'operation-access', 'location': 'operation'})
                    self.assertNotIn('PRIVATE', json.dumps(report))
            self.assertEqual(receipt.read_bytes(), original)
            self.assertEqual(list(directory.glob('removal-original-*.json')), [])

    def test_ssh_failure_keeps_bound_plan_current_error_and_original_failure(self):
        for edition,command in (('root','uninstall'),('no-root','uninstall'),('root','recover')):
            with self.subTest(edition=edition,command=command),tempfile.TemporaryDirectory() as tmp:
                store=state.Store(tmp);profile=state.target('192.0.2.50',edition)
                store.save(profile);(store.device_dir(profile)/'known_hosts').write_bytes(b'original pin')
                store.begin(profile,'install',stage='pending')
                original=store.pending(profile)
                diagnostics.create_report(store,'install',profile,'install-helper',TVCommandError(127))
                if command=='recover':store.request_clean_removal(profile)
                write=Capture();connect=Mock(side_effect=AuthenticationException('PRIVATE CURRENT'))
                with patch('cytv.cli.package.verify_payload',return_value={'files':{'fixture':'digest'}}) as verify:
                    code=cli.main([command,'--language','en','--yes','--host',profile['host'],'--edition',edition,'--data-dir',tmp],
                                  write=write,connect=connect,payload_root=Path(tmp)/'payload')
                self.assertEqual(code,1)
                verify.assert_called_once_with((Path(tmp)/'payload').resolve())
                self.assertEqual(write.profiles[-1],profile)
                self.assertEqual(write.plans[0]['state'],'waiting')
                self.assertEqual(write.plans[-1]['state'],'blocked')
                self.assertEqual(write.plans[-1]['removal']['stage'],'requested')
                self.assertIn('continue-removal',write.plans[-1]['actions'])
                report=json.loads(write.reports[-1].read_bytes())
                self.assertEqual(report['frontend'],'android')
                self.assertEqual(report['first_failure']['ssh_command']['exit_status'],127)
                self.assertEqual(report['reason_code'],'ssh-authentication')
                self.assertEqual(store.pending(profile)['previous'],original)
                self.assertNotIn('PRIVATE',json.dumps(report))

    def test_current_ssh_error_does_not_reprint_restart_instructions_after_error(self):
        for error in (TimeoutError('current connection lost'),AuthenticationException('current credentials refused')):
            with self.subTest(error=type(error).__name__),tempfile.TemporaryDirectory() as tmp:
                store=state.Store(tmp);profile=state.target('192.0.2.50','root')
                store.save(profile);(store.device_dir(profile)/'known_hosts').write_bytes(b'original pin')
                store.request_clean_removal(profile)
                store.checkpoint(profile,stage='restart-required',removal_reason='restart-required')
                lines=[];write=Console(lines.append,interactive=False,color=False)
                with patch('cytv.cli.package.verify_payload',return_value={'files':{'fixture':'digest'}}):
                    code=cli.main(['uninstall','--language','en','--yes','--host',profile['host'],'--edition','root','--data-dir',tmp],
                                  write=write,connect=Mock(side_effect=error),payload_root=Path(tmp)/'payload')
                self.assertEqual(code,1)
                text='\n'.join(lines);current=text.index('Could not complete this step')
                self.assertNotIn('disconnect it from power',text[current:])
                self.assertNotIn('Restart the TV to finish removal',text[current:])
                self.assertEqual(store.pending(profile)['stage'],'restart-required')

    def test_ambiguous_connection_failure_does_not_persist_transient_retry(self):
        import errno
        from paramiko.ssh_exception import NoValidConnectionsError
        errors = (
            NoValidConnectionsError({('192.0.2.50', 22): PermissionError(errno.EACCES, 'denied'),
                                     ('192.0.2.51', 22): ConnectionRefusedError(errno.ECONNREFUSED, 'refused')}),
            OSError('unknown socket cause'),
        )
        for error in errors:
            with self.subTest(error=type(error).__name__), tempfile.TemporaryDirectory() as tmp:
                store = state.Store(tmp)
                profile = state.target('192.0.2.50', 'root')
                store.save(profile)
                (store.device_dir(profile) / 'known_hosts').write_bytes(b'original pin')
                store.request_clean_removal(profile)
                store.checkpoint(profile, stage='restart-required', removal_reason='restart-required')
                write = Capture()
                with patch('cytv.cli.package.verify_payload', return_value={'files': {'fixture': 'digest'}}):
                    code = cli.main(['uninstall', '--language', 'en', '--yes', '--host', profile['host'],
                                     '--edition', 'root', '--data-dir', tmp], write=write,
                                    connect=Mock(side_effect=error), payload_root=Path(tmp) / 'payload')
                self.assertEqual(code, 1)
                self.assertEqual(write.plans[-1]['removal_action']['action'], 'check')
                self.assertNotEqual(store.pending(profile)['removal_reason'], 'connection-interrupted')
                self.assertEqual(store.pending(profile)['stage'], 'restart-required')

    def test_result_json_reports_storage_preflight_retry_without_resubmission(self):
        with tempfile.TemporaryDirectory() as tmp:
            remote = Mock()
            lines = []
            (Path(tmp) / 'fallback.png').write_bytes(b'fixture')
            manifest = {'files': {}, 'home_version': '1.0.0', 'helper_version': '1.0.0'}
            with patch('cytv.cli.package.verify_payload', return_value=manifest), \
                 patch('cytv.tv.SSAP') as ssap, \
                 patch.object(cli.Installer, 'preflight'), \
                 patch.object(cli.Installer, 'select_graphics'), \
                 patch.object(cli.Installer, 'installed_apps', return_value=[]), \
                 patch.object(cli.Installer, 'install', side_effect=UserError(
                     'Storage check failed', reason_code='storage-preflight-failed')):
                ssap.return_value.__enter__.return_value.inventory.return_value = {'apps': []}
                code = cli.main(['install', '--host', '192.0.2.50', '--edition', 'no-root',
                                 '--connection', 'root-ssh', '--data-dir', tmp, '--yes', '--result-json'],
                                connect=lambda *args: remote, write=lines.append, payload_root=tmp)
            self.assertEqual(code, 2)
            value, = map(json.loads, lines)
            self.assertEqual(value['outcome'], {'state': 'retryable-check', 'action': 'check-storage'})
            self.assertIsNone(state.Store(tmp).pending(state.target('192.0.2.50', 'no-root', connection='root-ssh')))

    def test_status_reports_pending_no_root_removal_without_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = state.Store(tmp)
            profile = state.target('192.0.2.50', 'no-root')
            directory = store.device_dir(profile)
            store.save(profile)
            (directory / 'known_hosts').write_bytes(b'original pin')
            store.request_clean_removal(profile)
            before = {path.relative_to(tmp): path.read_bytes()
                      for path in Path(tmp).rglob('*') if path.is_file()}
            lines = []
            remote = Mock()
            with patch('cytv.no_root_cleanup.inspect_binding', return_value={'reservation': 'matched'}), \
                 patch('cytv.no_root_cleanup.inspect_package_removal', return_value='busy'):
                code = cli.main(['status', '--data-dir', tmp, '--language', 'en', '--result-json'],
                                connect=lambda *args, persist: remote, write=lines.append)
            self.assertEqual(code, 0)
            value, = map(json.loads, lines)
            self.assertEqual(value['outcome'], {'state': 'waiting-for-evidence', 'action': 'check'})
            self.assertEqual(value['assessment']['state'], 'waiting')
            self.assertEqual(value['package_removal_monitor'], 'busy')
            self.assertEqual(value['pending'], store.pending(profile))
            self.assertEqual({path.relative_to(tmp): path.read_bytes()
                              for path in Path(tmp).rglob('*') if path.is_file()}, before)

    def test_status_reads_pending_root_product_without_staging_support(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = state.Store(tmp)
            profile = state.target('192.0.2.50', 'root')
            store.save(profile)
            (store.device_dir(profile) / 'known_hosts').write_bytes(b'original pin')
            store.begin(profile, 'install', stage='verify', product_operation='a' * 32)
            original = store.pending(profile)
            remote = Mock()
            remote.run.side_effect = ['CYTV_NODE_VERSION v8.12.0', '{"schema":1,"status":"missing"}']
            lines = []
            code = cli.main(['status', '--result-json', '--data-dir', tmp],
                            connect=lambda *args: remote, write=lines.append)
            self.assertEqual(code, 0)
            value, = map(json.loads, lines)
            self.assertEqual(value['outcome'], {'state': 'waiting-for-evidence', 'action': 'check'})
            self.assertEqual(value['device']['product']['passive']['status'], 'missing')
            self.assertEqual(store.pending(profile), original)
            self.assertEqual(remote.run.call_args.args[0], 'env -u NODE_OPTIONS -u NODE_PATH /usr/bin/node')
            remote.upload.assert_not_called()

    def test_removal_result_distinguishes_restart_from_verified_completion(self):
        for restart, expected in ((True, {'state': 'owner-input-required', 'action': 'restart-tv'}),
                                  (False, {'state': 'verified-completion', 'action': 'none'})):
            with self.subTest(restart=restart), tempfile.TemporaryDirectory() as tmp:
                store = state.Store(tmp)
                profile = state.target('192.0.2.50', 'root')
                store.save(profile)
                (store.device_dir(profile) / 'known_hosts').write_bytes(b'original pin')
                store.request_clean_removal(profile)
                if restart:
                    store.checkpoint(profile, stage='restart-required', removal_reason='restart-required')
                proof = {'removed': not restart, 'verified_clean': not restart, 'restart_required': restart}
                lines = []
                with patch('cytv.cli.package.verify_payload', return_value={'files': {}}), \
                     patch.object(cli.Installer, 'uninstall', return_value=proof):
                    code = cli.main(['uninstall', '--data-dir', tmp, '--yes', '--result-json'],
                                    connect=lambda *args: Mock(), write=lines.append, payload_root=tmp)
                self.assertEqual(code, 0)
                value, = map(json.loads, lines)
                self.assertEqual(value['outcome'], expected)
                self.assertEqual({key: value[key] for key in proof}, proof)
