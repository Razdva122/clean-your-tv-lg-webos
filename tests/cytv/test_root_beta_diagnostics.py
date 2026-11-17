import json
import shlex
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from cytv import diagnostics, state
from cytv.errors import TVCommandError


class BetaDiagnosticsTests(unittest.TestCase):
    def test_report_keeps_repair_stage_and_passive_observations_without_raw_data(self):
        with TemporaryDirectory() as folder:
            store = state.Store(folder)
            profile = state.target('192.0.2.10', 'root', root_variant='node012-beta')
            error = TVCommandError(1)
            error.root_beta_repair_failure = {
                'stage': 'register', 'reason': 'timeout', 'message': 'private exception'
            }
            tv = {'root_beta_state': {'status': 'read', 'runner': 'patched',
                                      'pending_proof': 'original', 'ready_proof': 'missing',
                                      'private': 'private content'}}
            report = json.loads(Path(diagnostics.create_report(
                store, 'recover', profile, 'recover', error, tv)).read_text())
            self.assertEqual(report['root_beta_repair_failure'], {
                'stage': 'register', 'reason': 'timeout'
            })
            self.assertEqual(report['tv']['root_beta_state']['runner'], 'patched')
            self.assertNotIn('private', json.dumps(report['tv']['root_beta_state']))
            self.assertNotIn('private exception', json.dumps(report))

    def test_passive_read_uses_system_node_from_stdin_only(self):
        from cytv import root_passive

        remote = Mock()
        remote.run.return_value = '{"status":"read","runner":"original","private":"secret"}'
        self.assertEqual(root_passive.collect_beta(remote), {'status': 'read', 'runner': 'original'})
        command = remote.run.call_args.args[0]
        self.assertEqual(command, 'env -u NODE_OPTIONS -u NODE_PATH /usr/bin/node')
        self.assertIn(b'recovery-provision.pending.json', remote.run.call_args.kwargs['data'])
        remote.upload.assert_not_called()

    def test_private_python_binding_failure_exports_only_fixed_stage(self):
        from cytv import root_install_recovery
        from cytv.operations import Installer

        with TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'python_binding.py').write_text(
                "def verify_binding(_): raise ValueError('private binding path')\n")
            # Model the POSIX TV path, including on a Windows installer host.
            stage = root.as_posix()
            observed = []

            def execute(command, *, timeout):
                argv = shlex.split(command)
                self.assertEqual(argv[-2:], [stage+'/provision.py', 'repair_beta_recovery'])
                result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
                observed.append(result)
                raise TVCommandError(result.returncode)

            installer = Mock()
            installer._python_command = Installer._python_command
            installer.remote.run.side_effect = execute
            with patch.object(root_install_recovery, 'recovery_python', return_value=sys.executable):
                with self.assertRaises(TVCommandError):
                    root_install_recovery.run(installer, stage, 'provision.py',
                                              ['repair_beta_recovery'], timeout=10)
            result, = observed
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, '')
        self.assertEqual(json.loads(result.stdout), {'returnValue': False,
            'root_beta_repair_failure': {'stage': 'python-binding', 'reason': 'failed'}})

    def test_ssh_failure_envelope_is_projected(self):
        from cytv.transport import SSH

        ssh = SSH.__new__(SSH)
        ssh._command_channel = Mock()

        def chunks(*args):
            yield b'{"returnValue":false,"root_beta_repair_failure":{"stage":"write-runner","reason":"failed","raw":"private"}}'
            raise TVCommandError(1)

        ssh.chunks = chunks
        with self.assertRaises(TVCommandError) as error:
            ssh.run('fixture')
        self.assertEqual(error.exception.root_beta_repair_failure,
                         {'stage': 'write-runner', 'reason': 'failed'})

    def test_interrupted_beta_status_does_not_launch_service_or_stage_recovery(self):
        from cytv.operations import Installer

        installer = Mock(profile={'edition': 'root', 'root_variant': 'node012-beta'}, tv_info={})
        installer.store.pending.return_value = None
        observation = {'status': 'read', 'deployment_stage': 'provision-finalize-starting',
                       'runner': 'patched', 'ready_proof': 'missing'}
        with patch('cytv.diagnostic_context.collect_node_version'), \
                patch('cytv.root_passive.collect_beta', return_value=observation):
            result = Installer.status(installer)
        self.assertEqual(result['deployment_stage'], 'provision-finalize-starting')
        self.assertEqual(installer.tv_info['root_beta_state'], observation)
        installer._status.assert_not_called()
        installer._collect_observed_root_diagnostics.assert_not_called()
