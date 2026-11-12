import hashlib
import json
from pathlib import Path
import shlex
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
            with self.assertRaisesRegex(UserError, 'files or settings remain'):
                Installer._continue_root_clean_removal(self.installer, self.pending)
        self.installer.store.finish_clean_removal.assert_not_called()
