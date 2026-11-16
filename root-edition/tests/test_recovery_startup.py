"""Real Node startup failures must survive without changing process exit behavior."""
import importlib.util
import json
import os
from pathlib import Path
import shlex
import shutil
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location('startup_provision', ROOT / 'provision.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class StartupTests(unittest.TestCase):
    def setUp(self):
        context = patch.object(p, 'prepare_stock_home')
        context.start(); self.addCleanup(context.stop)

    def test_beta_uses_lg_local_activity_before_bootstrap_positionals(self):
        with patch.object(p, 'LEGACY_NODE_BETA', True):
            command = shlex.split(p.runner_bytes().decode().splitlines()[-1])
        self.assertEqual(command, [
            'exec', '/usr/bin/node', '/usr/palm/services/jsservicelauncher/bootstrap-node.js',
            '--disable-activity-creation', '--', str(p.STATE/'bootstrap.pid'),
            '/var/palm/ls2-dev', str(p.PRIVATE_SERVICE),
        ])

    def test_node_records_exit_and_exception_without_swallowing_failure(self):
        source = ROOT / 'service/startup-diagnostics.js'
        self.assertTrue(source.is_file(), 'preload must observe bootstrap failures before service.js loads')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); service = root / 'service'; service.mkdir()
            shutil.copyfile(source, service / source.name)
            # Model root ownership only; retain actual file types/link counts/modes.
            metadata = root / 'metadata.js'
            metadata.write_text("var fs=require('fs'),s=fs.lstatSync;fs.lstatSync=function(p){var v=s.apply(fs,arguments);v.uid=0;if(v.isDirectory())v.mode&=~18;return v;};var f=fs.fstatSync;fs.fstatSync=function(){var v=f.apply(fs,arguments);v.uid=0;return v;};")
            record = root / 'recovery-service.json'
            for script, status, kind in [("process.exit(17)", 17, None),
                                         ("setImmediate(function(){require('./missing-private-module')})", 1, 'MODULE_NOT_FOUND'),
                                         ("", 0, None)]:
                result = subprocess.run(['node', '--require', str(metadata), '--require', str(service / source.name), '-e', script], capture_output=True)
                self.assertEqual(result.returncode, status)
                data = json.loads(record.read_text())
                self.assertEqual(data['phase'], 'exited')
                self.assertEqual(data['exit_status'], status)
                if kind:
                    self.assertEqual(data['exception']['code'], kind)
                    self.assertIn('missing-private-module', data['exception']['stack'])
                else:
                    self.assertNotIn('exception', data, 'a fresh start must replace stale failure details')
                self.assertLess(record.stat().st_size, 32768)
                self.assertEqual(record.stat().st_mode & 0o777, 0o600)
            record.unlink(); target = root / 'outside'; target.write_text('untouched')
            for indirect in ('symlink', 'hardlink'):
                if indirect == 'symlink': record.symlink_to(target)
                else: os.link(target, record)
                result = subprocess.run(['node', '--require', str(metadata), '--require', str(service / source.name), '-e', ''], capture_output=True)
                self.assertEqual(result.returncode, 0, 'diagnostic I/O must not break the service')
                self.assertEqual(target.read_text(), 'untouched')
                record.unlink()

    def test_finalize_failure_retains_phase_and_safe_luna_code_without_readiness(self):
        child = MagicMock(); child.poll.return_value = 0
        expected = {'version': 1}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'recovery-provision.pending.json').write_text(json.dumps(expected))
            def read(path): return path.read_bytes()
            with patch.dict(os.environ, {'CYTV_ROOT_INSTALL_ATTEMPT':'a'*32}), patch.object(p, 'STATE', root), patch.object(p, 'secure', side_effect=read), patch.object(p, 'manifest', return_value=expected), patch.object(p.subprocess, 'Popen', return_value=child), patch.object(p.select, 'select', return_value=([child.stdout], [], [])), patch.object(p.os, 'read', return_value=b'{"returnValue":false,"errorCode":-1,"errorText":"PRIVATE 192.0.2.1"}'):
                with self.assertRaises(ValueError): p.finalize()
            report = root / 'recovery-failure.json'
            self.assertTrue(report.is_file(), 'finalize must retain its failure before deploy loses stderr')
            data = json.loads(report.read_text())
            self.assertEqual(data['attempt'], 'a'*32)
            self.assertEqual(data['phase'], 'status')
            self.assertEqual(data['reason'], 'negative-reply')
            self.assertEqual(data['luna_error_code'], -1)
            self.assertNotIn('PRIVATE', report.read_text())
            self.assertNotIn('192.0.2.1', report.read_text())
            self.assertFalse((root / 'recovery-provision.json').exists())

    def test_rpc_bounds_noisy_stderr_instead_of_hanging_on_stdout(self):
        child = MagicMock(); child.poll.return_value = None
        with patch.object(p.subprocess, 'Popen', return_value=child), patch.object(p.select, 'select', return_value=([child.stderr], [], [])), patch.object(p.os, 'read', return_value=b'x' * 4096):
            with self.assertRaises(ValueError) as caught: p.rpc('status')
        self.assertEqual(getattr(caught.exception, 'details', {}).get('reason'), 'oversized-client-output')

    def test_finalize_distinguishes_fresh_exit_from_stale_diagnostics(self):
        for fresh in (False, True):
            with self.subTest(fresh=fresh), tempfile.TemporaryDirectory() as folder:
                root = Path(folder); expected = {'version':1}
                (root / 'recovery-provision.pending.json').write_text(json.dumps(expected))
                record = root / 'recovery-service.json'
                old = {'schema':1,'attempt':'old','phase':'exited','exit_status':17}
                record.write_text(json.dumps(old))
                def failed(method):
                    if fresh:
                        record.write_text(json.dumps({'schema':1,'attempt':'new','phase':'exited','exit_status':1,
                            'exception':{'name':'Error','code':'MODULE_NOT_FOUND','stack':'PRIVATE'}}))
                    raise p.RecoveryRPCError('timeout')
                with patch.object(p,'STATE',root), patch.object(p,'secure',side_effect=lambda path:path.read_bytes()), patch.object(p,'manifest',return_value=expected), patch.object(p,'rpc',side_effect=failed):
                    with self.assertRaises(ValueError): p.finalize()
                result=json.loads((root / 'recovery-failure.json').read_text())
                self.assertEqual(result['startup_state'], 'exited' if fresh else 'stale')
                if fresh:
                    self.assertEqual(result['exception_code'], 'MODULE_NOT_FOUND')
                    self.assertEqual(result['startup_exit_status'],1)
                else: self.assertNotIn('startup_exit_status',result)
                self.assertNotIn('PRIVATE',json.dumps(result))
                self.assertFalse((root / 'recovery-provision.json').exists())

    def test_real_runner_keeps_bootstrap_arguments_and_exit_status(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); service=root/'service';service.mkdir()
            shutil.copyfile(ROOT/'service/startup-diagnostics.js',service/'startup-diagnostics.js')
            metadata=root/'metadata.js'
            metadata.write_text("var fs=require('fs'),s=fs.lstatSync,f=fs.fstatSync;fs.lstatSync=function(){var v=s.apply(fs,arguments);v.uid=0;if(v.isDirectory())v.mode&=~18;return v;};fs.fstatSync=function(){var v=f.apply(fs,arguments);v.uid=0;return v;};")
            bootstrap=root/'bootstrap.js'
            bootstrap.write_text("console.log(JSON.stringify(process.argv.slice(2)));process.exit(23);")
            with patch.object(p,'STATE',root),patch.object(p,'PRIVATE_SERVICE',service): script=p.runner_bytes().decode()
            script=script.replace('/usr/bin/node',shutil.which('node')+' --require '+str(metadata)).replace('/usr/palm/services/jsservicelauncher/bootstrap-node.js',str(bootstrap))
            runner=root/'run';runner.write_text(script)
            result=subprocess.run(['/bin/sh',str(runner)],capture_output=True,text=True)
            self.assertEqual(result.returncode,23)
            self.assertEqual(json.loads(result.stdout),['--',str(root/'bootstrap.pid'),'/var/palm/ls2-dev',str(service)])
            self.assertEqual(json.loads((root/'recovery-service.json').read_text())['exit_status'],23)

    def test_real_rpc_drains_and_bounds_client_stderr(self):
        original=subprocess.Popen
        def start(args,**kwargs):
            return original([sys.executable,'-c',"import os\nwhile True: os.write(2,b'x'*4096)"],**kwargs)
        with patch.object(p.subprocess,'Popen',side_effect=start):
            with self.assertRaises(ValueError) as caught:p.rpc('status')
        self.assertEqual(caught.exception.details['reason'],'oversized-client-output')

    def test_timeout_and_logging_failure_keep_original_failure(self):
        child=MagicMock();child.poll.return_value=None
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'recovery-provision.pending.json').write_text('{}')
            with patch.object(p,'STATE',root),patch.object(p,'secure',side_effect=lambda path:path.read_bytes()),patch.object(p,'manifest',return_value={}),patch.object(p.subprocess,'Popen',return_value=child),patch.object(p.select,'select',return_value=([],[],[])),patch.object(p,'write',side_effect=OSError('read-only')):
                with self.assertRaises(ValueError) as caught:p.finalize()
            self.assertEqual(caught.exception.details['reason'],'timeout')
            self.assertFalse((root/'recovery-provision.json').exists())

    def test_negative_rpc_classifies_service_and_permission_failures_without_raw_text(self):
        for text, category in [('Denied methods call status PRIVATE', 'permission-denied'),
                               ('Service does not exist: PRIVATE', 'service-missing'),
                               ('Unknown method PRIVATE', 'method-missing')]:
            child=MagicMock();child.poll.return_value=0
            raw=json.dumps({'returnValue':False,'errorCode':-1,'errorText':text}).encode()
            with patch.object(p.subprocess,'Popen',return_value=child),patch.object(p.select,'select',return_value=([child.stdout],[],[])),patch.object(p.os,'read',return_value=raw):
                with self.assertRaises(ValueError) as caught:p.rpc('status')
            self.assertEqual(caught.exception.details['luna_reason'],category)
            self.assertNotIn('PRIVATE',json.dumps(caught.exception.details))
