import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from cytv.errors import UserError
from cytv.root_clean_tail import resume


class RootTailWire(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        root=Path(tmp.name).resolve();bundle=root/'root-updater';bundle.mkdir()
        source=b'current verified source';(bundle/'cleanup_tail.js').write_bytes(source)
        (bundle/'bundle.json').write_text(json.dumps({'files':{'cleanup_tail.js':hashlib.sha256(source).hexdigest()}}))
        support=root/'installer-support';support.mkdir();gate=b'current verified gate';(support/'lifecycle-gate').write_bytes(gate)
        self.pending={'product_operation':'a'*32,'removal_operation':'d'*32}
        self.installer=SimpleNamespace(payload=root,manifest={'files':{'installer-support/lifecycle-gate':hashlib.sha256(gate).hexdigest()}},remote=Mock(),store=Mock(),profile={})

    def test_expected_intent_reaches_both_node_entrypoints_and_reply_is_bound(self):
        commands=[]
        def run(command,**kwargs):
            commands.append(shlex.split(command))
            if 'inspect' in commands[-1]:
                return json.dumps({'operation':'a'*32,'removal':'d'*32,'state':'tail-ready'})
            if 'finish' in commands[-1]:
                return json.dumps({'operation':'a'*32,'removal':'e'*32,'state':'complete','stage':'verified-clean'})
            return ''
        self.installer.remote.run.side_effect=run
        with self.assertRaises(UserError):resume(self.installer,self.pending)
        for command in commands:
            if 'inspect' in command or 'finish' in command:self.assertEqual(command[-1],'d'*32)
        self.installer.store.finish_clean_removal.assert_not_called()

    @unittest.skipUnless(os.environ.get('NODE012'), 'Exact Node 0.12.2 is optional on the host')
    def test_resume_launches_both_entrypoints_on_node012(self):
        node = os.environ['NODE012']
        self.assertEqual(subprocess.check_output([node, '--version']).strip(), b'v0.12.2')
        bundle = self.installer.payload / 'root-updater'
        source = b"""
var argv = process.argv;
var finish = argv[2] === 'finish';
if (argv.length !== 10 || (!finish && argv[2] !== 'inspect'))
    throw Error('invalid selector');
process.stdout.write(JSON.stringify({
    operation: argv[3], removal: argv[9],
    state: finish ? 'complete' : 'tail-ready',
    descriptors: argv.slice(5, 8), gate: argv[8]
}));
"""
        (bundle / 'cleanup_tail.js').write_bytes(source)
        (bundle / 'bundle.json').write_text(json.dumps({
            'files': {'cleanup_tail.js': hashlib.sha256(source).hexdigest()}
        }))
        modes = []

        def run(command, **kwargs):
            args = shlex.split(command)
            if '/usr/bin/node' not in args:
                return ''
            if 'finish' in args:
                self.assertEqual(args[6], 'root-clean-lock')
            result = subprocess.run([node, *args[args.index('/usr/bin/node') + 1:]],
                                    input=kwargs['data'], capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            reply = json.loads(result.stdout)
            modes.append(reply['state'])
            return result.stdout.decode()

        self.installer.remote.run.side_effect = run
        reply = resume(self.installer, self.pending)
        self.assertEqual(modes, ['tail-ready', 'complete'])
        self.assertEqual(reply['descriptors'], ['3', '4', '5'])
        self.assertEqual(reply['gate'], hashlib.sha256(b'current verified gate').hexdigest())

    def test_changed_cleanup_source_refuses_before_remote_execution(self):
        (self.installer.payload / 'root-updater' / 'cleanup_tail.js').write_bytes(b'changed')
        with self.assertRaisesRegex(UserError, 'support code is missing or changed'):
            resume(self.installer, self.pending)
        self.installer.remote.run.assert_not_called()

    def test_changed_gate_refuses_before_finish_or_upload(self):
        (self.installer.payload / 'installer-support' / 'lifecycle-gate').write_bytes(b'changed')
        self.installer.remote.run.return_value = json.dumps({
            'operation': 'a' * 32, 'removal': 'd' * 32, 'state': 'tail-ready',
        })
        with self.assertRaisesRegex(UserError, 'support code is missing or changed'):
            resume(self.installer, self.pending)
        self.installer.remote.run.assert_called_once()
        self.assertIn('inspect', shlex.split(self.installer.remote.run.call_args.args[0]))
        self.installer.remote.upload.assert_not_called()

    def test_changed_observed_intent_refuses_before_staging(self):
        self.installer.remote.run.return_value=json.dumps({'operation':'a'*32,'removal':'e'*32,'state':'tail-ready'})
        with self.assertRaises(UserError):resume(self.installer,self.pending)
        self.installer.remote.upload.assert_not_called()
        self.installer.store.checkpoint.assert_not_called()

    def test_device_can_return_control_to_the_coordinator(self):
        self.installer.remote.run.return_value=json.dumps({
            'operation':'a'*32,'removal':'d'*32,'state':'coordinator-ready',
        })
        self.assertEqual(resume(self.installer,self.pending),{'recheck_boot':True})
        self.installer.remote.upload.assert_not_called()

    def test_completed_readback_failure_returns_to_current_support_sweep(self):
        from cytv.errors import TVCommandError
        self.pending['stage']='verified-clean'
        def run(command,**kwargs):
            if 'inspect' in shlex.split(command):
                return json.dumps({'operation':'a'*32,'removal':'d'*32,'state':'tail-ready'})
            if 'finish' in shlex.split(command):raise TVCommandError(1)
            return ''
        self.installer.remote.run.side_effect=run
        self.assertIsNone(resume(self.installer,self.pending))

    def test_cleanup_guard_paths_reach_export_and_first_failure(self):
        from unittest.mock import patch
        from cytv import diagnostics, state
        from cytv.errors import HOME_CONFLICT_PATHS
        from cytv.operations import Installer
        paths = list(HOME_CONFLICT_PATHS)
        for reason, fields in [
                ('route-changed', {'home_conflict_paths': paths}),
                ('cleanup-check-failed', {'last_failure': {'home_conflict_paths': paths}}),
                ('cleanup-check-failed', {'last_failure': {'cleanup_probe': {
                    'exception_type': 'ValueError', 'home_conflict_paths': paths}}})]:
            with self.subTest(fields=fields), tempfile.TemporaryDirectory() as directory:
                store = state.Store(directory)
                profile = state.target('test-tv', 'root')
                store.begin(profile, 'install', stage='setup')
                self.installer.profile, self.installer.store = profile, store
                self.installer.progress = Mock()
                reply = dict(stage='private-cleanup', state='recovery_required', cleanup_error=reason, **fields)
                with patch('cytv.root_clean_tail.resume', return_value=reply), self.assertRaises(UserError) as caught:
                    Installer._continue_root_clean_removal(self.installer, self.pending)
                report = diagnostics.create_report(store, 'install', profile, 'remove-existing-root', caught.exception,
                                                   tv_info={'frontend': 'android'})
                saved = json.loads(report.read_text())
                self.assertEqual(saved['home_conflict_paths'], paths)
                self.assertEqual(saved['first_failure']['home_conflict_paths'], paths)

    def test_unavailable_readback_survives_report_and_first_failure(self):
        from unittest.mock import patch
        from cytv import diagnostics, state
        from cytv.operations import Installer
        detail = {'check':'activities-info', 'reason':'client-exit', 'exit_status':1}
        old = {'check':'apps', 'reason':'timeout'}
        for reason, fields, expected in [
                ('cleanup-readback-unavailable', {'cleanup_readback':dict(detail, stderr='PRIVATE')}, detail),
                ('cleanup-check-failed', {'last_failure':{'cleanup_readback':detail}}, detail),
                ('cleanup-readback-unavailable', {'last_failure':{'cleanup_readback':old}}, None),
                ('cleanup-readback-unavailable', {'cleanup_readback':dict(detail, check='PRIVATE')}, None)]:
            with self.subTest(fields=fields), tempfile.TemporaryDirectory() as directory:
                store = state.Store(directory)
                profile = state.target('test-tv', 'root')
                store.begin(profile, 'recover', stage='private-cleanup')
                self.installer.profile, self.installer.store = profile, store
                self.installer.progress = Mock()
                reply = dict(stage='private-cleanup', state='recovery_required', cleanup_error=reason, **fields)
                with patch('cytv.root_clean_tail.resume', return_value=reply), self.assertRaises(UserError) as caught:
                    Installer._continue_root_clean_removal(self.installer, self.pending)
                saved = json.loads(diagnostics.create_report(store, 'recover', profile, 'recover', caught.exception,
                                   tv_info={'frontend':'android'}, status={'device':{'product':reply}}).read_text())
                for item in (saved, saved['first_failure'], saved['observation_failure']):
                    self.assertEqual(item.get('cleanup_readback'), expected)
                product = saved['status']['product']
                if reason == 'cleanup-readback-unavailable':
                    self.assertEqual(product.get('cleanup_readback'), expected)
                else:
                    self.assertEqual(product['last_failure']['cleanup_readback'], expected)
                self.assertNotIn('PRIVATE', json.dumps(saved))

    def test_current_cleanup_failure_takes_precedence_over_old_restart(self):
        from unittest.mock import patch
        from cytv.operations import Installer
        self.installer.profile = {'edition': 'root'}
        self.installer.progress = Mock()
        with patch('cytv.root_clean_tail.resume', return_value={
            'stage': 'restart-required',
            'cleanup_error': 'cleanup-check-failed',
            'result': {'restart_required': True},
        }):
            with self.assertRaisesRegex(UserError, 'Final cleanup could not be verified') as failure:
                Installer._continue_root_clean_removal(self.installer, self.pending)
        self.assertEqual(failure.exception.reason_code, 'cleanup-check-failed')
        self.installer.store.finish_clean_removal.assert_not_called()
