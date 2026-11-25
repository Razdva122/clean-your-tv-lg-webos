"""Failed Root setup must export safe recovery evidence without repeating setup."""
import os
import json
import shlex
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace
from cytv import diagnostics, operations, state
from cytv.errors import TVCommandError, root_recovery_details


class RootRecoveryDiagnosticsTests(unittest.TestCase):
    def test_stock_home_phase_exports_only_safe_categories(self):
        self.assertEqual(root_recovery_details({'schema':1,'phase':'stock-home',
            'reason':'failed','startup_milestone':'PRIVATE','defaultApps':{'private':'data'},
            'profiles':{'private':'data'}}),
            {'phase':'stock-home','reason':'failed'})

    def test_failed_install_collects_only_allowlisted_evidence_and_keeps_original_error(self):
        for extra in ({'reason':'negative-reply','luna_error_code':-1},
                      {'reason':'timeout','startup_state':'exited','startup_exit_status':1,
                       'startup_milestone':'status-requested',
                       'exception_name':'Error','exception_code':'MODULE_NOT_FOUND'}):
            with self.subTest(extra=extra), tempfile.TemporaryDirectory() as folder:
                error=TVCommandError(1)
                raw={'schema':1,'attempt':'a'*32,'phase':'status',**extra,'stack':'PRIVATE 192.0.2.1','pid':1234}
                remote=MagicMock()
                remote.run.side_effect=[error,json.dumps(raw)]
                installer=operations.Installer(remote,None,{},Path(folder),{})
                installer._python=lambda path:'/usr/bin/python3'
                with patch.object(operations.uuid,'uuid4',return_value=SimpleNamespace(hex='a'*32)):
                    with self.assertRaises(TVCommandError) as caught:
                        installer.root_action('install',bundle='/tmp/verified-bundle')
                self.assertIs(caught.exception,error)
                self.assertEqual(remote.run.call_count,2, 'one failed install and one read-only diagnostic collection')
                second=remote.run.call_args.args[0]
                self.assertIn('recovery-failure.json',second)
                self.assertNotIn('deploy.py',second)
                report=diagnostics.create_report(state.Store(folder),'install',None,'root-install',error)
                data=json.loads(report.read_text())
                self.assertEqual(data['root_recovery'],{'phase':'status',**extra})
                self.assertNotIn('PRIVATE',report.read_text())
                self.assertNotIn('192.0.2.1',report.read_text())
                self.assertNotIn('pid',data['root_recovery'])

    def test_current_root_control_failure_wins_over_prior_package_failure(self):
        from cytv.recovery import removal_plan
        from cytv.errors import UserError
        from tests.cytv.test_full_uninstall import FullUninstallTests

        fixture = FullUninstallTests()
        self.addCleanup(fixture.doCleanups)
        installer, remote, store, profile, _, _ = fixture.fixture('failed')
        run = remote.run.side_effect
        first_failure = {'exception_type': 'ValueError', 'stage': 'package-removal'}
        latest_failure = {'exception_type': 'ValueError', 'stage': 'private-cleanup',
                          'cleanup_step': 'home-readback'}
        def fail_controls(command, **kwargs):
            raw = run(command, **kwargs)
            if '/install_driver.py clean-remove ' not in command:
                return raw
            reply = json.loads(raw)
            return json.dumps(dict(reply, stage='private-cleanup', reason='private-cleanup-incomplete',
                                   cleanup_error='cleanup-check-failed', failure=first_failure,
                                   last_failure={**latest_failure, 'message': 'PRIVATE'}))
        remote.run.side_effect = fail_controls
        with self.assertRaises(UserError) as caught:
            installer.uninstall_project()

        plans = []
        write = SimpleNamespace(recovery=lambda _profile: None, recovery_plan=plans.append)
        removal_plan(write, store, profile, error=caught.exception, phase='uninstall')
        self.assertEqual(plans[-1]['summary'], 'TV controls could not be verified.')
        self.assertNotIn('Removing private setup data…', str(plans[-1]))
        self.assertNotIn('PRIVATE', str(plans[-1]))
        self.assertEqual(plans[-1]['removal_action']['action'], 'check')
        removal_plan(write, store, profile)
        self.assertEqual(plans[-1]['summary'], 'TV controls could not be verified.')

        report = diagnostics.create_report(store, 'uninstall', profile, 'uninstall', caught.exception,
                                           installer.tv_info, status=installer.tv_info['status'])
        product = json.loads(report.read_text())['status']['product']
        self.assertEqual(product['failure'], first_failure)
        self.assertEqual(product['last_failure'], latest_failure)
        self.assertNotIn('PRIVATE', report.read_text())

    def test_root_package_removal_distinguishes_a_terminal_rejection_from_missing_evidence(self):
        from cytv.recovery import removal_plan
        from cytv.errors import UserError
        from tests.cytv.test_full_uninstall import FullUninstallTests

        for worker_evidence, title in (
                ({}, 'The TV package result could not be verified.'),
                ({'package_rejected': 'PRIVATE'}, 'The TV package result could not be verified.'),
                ({'package_rejected': True}, 'The TV could not remove a package')):
            with self.subTest(evidence=worker_evidence):
                fixture = FullUninstallTests()
                self.addCleanup(fixture.doCleanups)
                installer, remote, store, profile, _, _ = fixture.fixture('package-failed')
                run = remote.run.side_effect
                def fail_package(command, **kwargs):
                    raw = run(command, **kwargs)
                    if '/install_driver.py clean-remove ' not in command:
                        return raw
                    return json.dumps(dict(json.loads(raw), last_failure={
                        'exception_type': 'unknown', 'stage': 'package-removal', **worker_evidence}))
                remote.run.side_effect = fail_package
                with self.assertRaises(UserError) as caught:
                    installer.uninstall_project()
                self.assertEqual(caught.exception.reason_code, 'removal-failed')
                plans = []
                write = SimpleNamespace(recovery=lambda _profile: None, recovery_plan=plans.append)
                removal_plan(write, store, profile, error=caught.exception, phase='uninstall')
                self.assertEqual(plans[-1]['summary'], title)
                self.assertEqual(plans[-1]['removal_action']['action'], 'check')
                report = diagnostics.create_report(store, 'uninstall', profile, 'uninstall', caught.exception,
                                                   installer.tv_info, status=installer.tv_info['status'])
                self.assertNotIn('PRIVATE', report.read_text())
                product = json.loads(report.read_text())['status']['product']['last_failure']
                self.assertEqual(product.get('package_rejected'), True if worker_evidence.get('package_rejected') is True else None)

    def test_unavailable_or_untrusted_diagnostics_never_replace_failure(self):
        for raw in (OSError('unavailable'), 'not JSON', '[]', '{"schema":99}',
                    '{"schema":1,"attempt":"old","phase":"status","reason":"negative-reply","luna_error_code":-1}',
                    '{"schema":1,"phase":"PRIVATE","reason":"PRIVATE","startup_exit_status":true}'):
            with self.subTest(raw=raw):
                error=TVCommandError(7); remote=MagicMock();remote.run.side_effect=[error,raw]
                installer=operations.Installer(remote,None,{},'.',{})
                installer._python=lambda path:'/usr/bin/python3'
                with self.assertRaises(TVCommandError) as caught:installer.root_action('install')
                self.assertIs(caught.exception,error)
                self.assertFalse(getattr(error,'root_recovery',{}))

    @unittest.skipUnless(os.name=='posix','Requires POSIX device filesystem/process fixture')
    def test_attempt_identity_crosses_real_process_boundary(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'deploy.py').write_text("import json,os,pathlib,sys\np=pathlib.Path(__file__).parent/'recovery-failure.json'\np.write_text(json.dumps({'schema':1,'attempt':os.environ.get('CYTV_ROOT_INSTALL_ATTEMPT'),'phase':'status','reason':'timeout'}))\np.chmod(0o600)\nsys.exit(1)\n")
            class Device:
                def run(self, command, timeout=30):
                    argv=shlex.split(command)
                    if '-c' in argv:
                        # Map only the TV path and root uid to this local device fixture.
                        argv[-1]=argv[-1].replace('/var/lib/clean-your-tv-root/recovery-failure.json',str(root/'recovery-failure.json')).replace('s.st_uid!=0','s.st_uid!=os.geteuid()')
                    result=subprocess.run(argv,capture_output=True,text=True,timeout=timeout)
                    if result.returncode:raise TVCommandError(result.returncode)
                    return result.stdout
            installer=operations.Installer(Device(),None,{},root,{})
            installer._python=lambda path:sys.executable
            with self.assertRaises(TVCommandError) as caught:installer.root_action('install',bundle=str(root))
            self.assertEqual(getattr(caught.exception,'root_recovery',None),{'phase':'status','reason':'timeout'})
            attempt=json.loads((root/'recovery-failure.json').read_text())['attempt']
            self.assertRegex(attempt,r'^[a-f0-9]{32}$')
