import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from paramiko import AuthenticationException
from cytv import cli, diagnostics, state
from cytv.errors import TVCommandError
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
