"""Guidance uses typed/phase-bound evidence, never private exception prose."""
import errno
import unittest
from cytv.errors import DeveloperKeyError, TVConnectionError


class FailureHelpTests(unittest.TestCase):
    def test_clean_removal_plan_is_not_contradicted_by_generic_install_warning(self):
        from cytv.errors import UserError
        pending = {'action': 'uninstall', 'recovery_protocol': 'clean-removal-v1'}
        for edition in ('root', 'no-root'):
            self.assertIsNone(self.guide(UserError('PRIVATE', reason_code='cleanup-check-failed'),
                                         edition, 'uninstall', pending))
        error = type('BadHostKeyException', (Exception,), {})('PRIVATE')
        self.assertEqual(self.guide(error, pending=pending)['code'], 'ssh-identity')

    def guide(self,error,edition='root',phase='ssh-connect',pending=None):
        from cytv.failure_help import for_error
        return for_error(error,phase,{'edition':edition,'host':'PRIVATE-ADDRESS','identity':'PRIVATE-PATH'},pending)

    def test_package_space_reason_is_explained_even_with_pending_operation(self):
        from cytv.errors import TVRejected
        for reason in ('FAILED_NOT_ENOUGH_TEMP_SPACE', 'FAILED_NOT_ENOUGH_INSTALL_SPACE'):
            error = TVRejected('Package installation failed.', {'details': {'reason': reason}},
                               'com.webos.appInstallService/dev/install')
            self.assertIn('space', str(error))
            guide = self.guide(error, phase='install-helper', pending={'action': 'install'})
            self.assertEqual(guide['code'], 'tv-storage-full')
            self.assertFalse(guide['can_edit_connection'])
            self.assertIn('recovery', guide['next_step'])

    def test_local_full_disk_does_not_blame_tv_or_reveal_paths(self):
        for number in (errno.ENOSPC, errno.EDQUOT):
            guide = self.guide(OSError(number, 'PRIVATE', '/PRIVATE'), phase='prepare-payload')
            self.assertEqual(guide['code'], 'computer-storage-full')
            self.assertNotIn('PRIVATE', str(guide))
        self.assertIsNone(self.guide(OSError(errno.EIO, 'PRIVATE'), phase='prepare-payload'))

    def test_known_ssh_categories_do_not_copy_exception_text(self):
        cases=[('NoValidConnectionsError','ssh-unreachable'),('AuthenticationException','ssh-auth-root'),
               ('BadHostKeyException','ssh-identity'),('SSHException','ssh-protocol')]
        for name,code in cases:
            error=type(name,(Exception,),{})('PRIVATE-PASSWORD')
            with self.subTest(name=name):
                help=self.guide(error)
                self.assertEqual(help['code'],code)
                self.assertNotIn('PRIVATE',str(help))
        self.assertEqual(self.guide(TimeoutError('PRIVATE'))['code'],'ssh-timeout')
        self.assertEqual(self.guide(ConnectionRefusedError(errno.ECONNREFUSED,'PRIVATE'))['code'],'ssh-refused')

    def test_network_errors_keep_the_underlying_cause_without_private_text(self):
        from paramiko.ssh_exception import NoValidConnectionsError
        cases = [(errno.EACCES, 'ssh-access-denied'), (errno.EPERM, 'ssh-access-denied'),
                 (errno.ECONNREFUSED, 'ssh-refused'), (errno.ETIMEDOUT, 'ssh-timeout'),
                 (errno.EHOSTUNREACH, 'ssh-unreachable')]
        for number, expected in cases:
            for wrapped in (False, True):
                error = OSError(number, 'PRIVATE')
                if wrapped:
                    error = NoValidConnectionsError({('PRIVATE-ADDRESS', 22): error})
                with self.subTest(errno=number, wrapped=wrapped):
                    guide = self.guide(error)
                    self.assertEqual(guide['code'], expected)
                    self.assertNotIn('PRIVATE', str(guide))
                    pending = self.guide(error, pending={'action': 'install'})
                    self.assertFalse(pending['can_edit_connection'])
                    self.assertIn('original saved TV connection', pending['next_step'])
        self.assertEqual(self.guide(TimeoutError())['code'], 'ssh-timeout')
        mixed = NoValidConnectionsError({('PRIVATE-A', 22): PermissionError(errno.EACCES, 'PRIVATE'),
                                        ('PRIVATE-B', 22): ConnectionRefusedError(errno.ECONNREFUSED, 'PRIVATE')})
        self.assertEqual(self.guide(mixed)['code'], 'ssh-unreachable')
        self.assertIsNone(self.guide(PermissionError(errno.EACCES, 'PRIVATE'), phase='install-root'))

    def test_saved_developer_key_permission_error_does_not_blame_network(self):
        error = PermissionError(errno.EACCES, 'PRIVATE', '/PRIVATE/developer-key.pem')
        guide = self.guide(error, 'no-root')
        self.assertEqual(guide['code'], 'ssh-key-file')
        self.assertNotIn('network', guide['next_step'].lower())
        self.assertNotIn('PRIVATE', str(guide))

    def test_key_server_categories_are_actionable_without_claiming_wrong_password(self):
        for reason,code in [('key-server-unavailable','developer-key-server'),('key-unlock','developer-key-unlock'),
                            ('response-redirect','developer-key-response'),('response-format','developer-key-response')]:
            help=self.guide(DeveloperKeyError('PRIVATE',reason),'no-root')
            self.assertEqual(help['code'],code)
            self.assertTrue(help['can_edit_connection'])
            self.assertNotIn('PRIVATE',str(help))

    def test_pending_evidence_blocks_connection_edit_and_generic_recovery_advice(self):
        error=type('AuthenticationException',(Exception,),{})('PRIVATE')
        help=self.guide(error,pending={'action':'install','stage':'coordinator-submitted'})
        self.assertEqual(help['code'],'ssh-auth-root')
        self.assertFalse(help['can_edit_connection'])
        self.assertTrue(help['pending'])

    def test_post_submission_errors_are_not_relabelled_as_connection_setup(self):
        self.assertIsNone(self.guide(TimeoutError('PRIVATE'),phase='install-home'))
        self.assertIsNone(self.guide(OSError('PRIVATE'),phase='launch-root'))
        help=self.guide(OSError('PRIVATE'),phase='launch-root',pending={'action':'install'})
        self.assertEqual(help['code'],'pending-operation')

    def test_pairing_and_root_capability_have_distinct_nonrepair_help(self):
        from cytv.root_capabilities import RootCapabilityError
        pairing=self.guide(TVConnectionError('PRIVATE',reason_code='pairing-timeout'),phase='pair-tv')
        self.assertEqual(pairing['code'],'tv-pairing')
        root=self.guide(RootCapabilityError(),phase='inspect-installation')
        self.assertEqual(root['code'],'root-home-interfaces')
        self.assertFalse(root['can_edit_connection'])

    def test_unrelated_failure_or_success_has_no_invented_connection_diagnosis(self):
        self.assertIsNone(self.guide(ValueError('PRIVATE'),phase='read-inventory'))
        self.assertIsNone(self.guide(None,pending={'action':'install'}))

    def test_root_and_no_root_signin_remain_distinct(self):
        error=type('BadAuthenticationType',(type('AuthenticationException',(Exception,),{}),),{})('PRIVATE')
        self.assertEqual(self.guide(error)['code'],'ssh-auth-root')
        self.assertEqual(self.guide(error,'no-root')['code'],'ssh-auth-no-root')

    def test_unknown_key_reason_does_not_invent_a_bad_response(self):
        self.assertIsNone(self.guide(DeveloperKeyError('PRIVATE','unknown'),'no-root'))

    def test_runtime_requirements_are_not_described_as_a_password_failure(self):
        from cytv.errors import UserError
        help=self.guide(UserError('PRIVATE',reason_code='root-requirements'),phase='inspect-installation')
        self.assertEqual(help['code'],'root-requirements')
        self.assertFalse(help['can_edit_connection'])

    def test_developer_key_guidance_cannot_enable_developer_mode_for_root(self):
        self.assertIsNone(self.guide(DeveloperKeyError('PRIVATE','key-unlock'),'root'))

    def test_noninteractive_signin_never_requests_secret_input(self):
        import tempfile
        from unittest.mock import Mock
        from cytv import cli, state
        for edition in ('root','no-root'):
            with self.subTest(edition=edition),tempfile.TemporaryDirectory() as tmp:
                state.Store(tmp).save(state.target('192.0.2.10',edition))
                secret=Mock(return_value='PRIVATE')
                calls=[]
                def connect(profile,directory,ask_secret,trust):
                    calls.append(profile)
                    ask_secret('Root SSH password (hidden): ' if edition=='root' else 'Developer Mode passphrase: ')
                    raise AssertionError('secret callback must be blocked')
                code=cli.main(['doctor','--host','192.0.2.10','--edition',edition,'--data-dir',tmp,'--non-interactive'],
                              connect=connect,secret=secret,write=lambda _:None)
                self.assertEqual(len(calls),1)
                self.assertEqual(code,2)
                secret.assert_not_called()

    def test_report_projection_revalidates_codes_and_drops_text(self):
        from cytv.failure_help import report_summary
        self.assertEqual(report_summary({'code':'ssh-identity','pending':True,'detail':'PRIVATE'}),
                         {'code':'ssh-identity','pending':True})
        self.assertEqual(report_summary({'code':'PRIVATE','pending':'PRIVATE'}),{'code':'unknown','pending':False})

    def test_cli_error_emits_fixed_help_and_exports_only_its_code(self):
        import json,tempfile
        from pathlib import Path
        from cytv import cli,state
        from cytv.desktop import DesktopConsole
        with tempfile.TemporaryDirectory() as tmp:
            profile=state.target('192.0.2.10','root',2222);store=state.Store(tmp);store.save(profile)
            known=store.device_dir(profile)/'known_hosts';known.write_bytes(b'PRIVATE-TRUST-RECORD')
            events=[]
            def connect(*args):raise ConnectionRefusedError(errno.ECONNREFUSED,'PRIVATE-ADDRESS-PASSWORD')
            code=cli.main(['doctor','--host',profile['host'],'--port','2222','--edition','root','--data-dir',tmp],
                          connect=connect,write=DesktopConsole(lambda k,v:events.append((k,v))))
            self.assertEqual(code,1)
            help=next(v for k,v in events if k=='failure-help')
            self.assertEqual(help['code'],'ssh-refused')
            report=json.loads(next(Path(tmp).glob('reports/*.json')).read_text())
            self.assertEqual(report['guidance'],{'code':'ssh-refused','pending':False})
            self.assertNotIn('PRIVATE',json.dumps(report))
            self.assertNotIn('PRIVATE',str(events))
            self.assertEqual(known.read_bytes(),b'PRIVATE-TRUST-RECORD')

    def test_pending_cli_failure_keeps_journal_and_blocks_connection_actions(self):
        import json,tempfile
        from pathlib import Path
        from cytv import cli,state
        from cytv.desktop import DesktopConsole
        with tempfile.TemporaryDirectory() as tmp:
            profile=state.target('192.0.2.10','root');store=state.Store(tmp);store.save(profile)
            (store.device_dir(profile)/'known_hosts').write_bytes(b'original pin')
            store.begin(profile,'install',stage='coordinator-submitted')
            path=store.device_dir(profile)/'operation.json';before=path.read_bytes();events=[]
            def connect(*args):raise TimeoutError('PRIVATE')
            cli.main(['status','--host',profile['host'],'--edition','root','--data-dir',tmp],connect=connect,
                     write=DesktopConsole(lambda k,v:events.append((k,v))))
            self.assertEqual(path.read_bytes(),before)
            help=next(v for k,v in events if k=='failure-help')
            self.assertEqual(help['code'],'ssh-timeout')
            self.assertFalse(help['can_edit_connection'])
            report=json.loads(next(Path(tmp).glob('reports/*.json')).read_text())
            self.assertEqual(report['guidance'],{'code':'ssh-timeout','pending':True})
            self.assertNotIn('PRIVATE',json.dumps(report))
