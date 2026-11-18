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

    def test_beta_repair_retries_without_replacing_package_or_activation(self):
        import deploy
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            runner = root/'run-recovery-service'
            pending = root/'recovery-provision.pending.json'
            installed = root/'installed-app'
            installed.write_bytes(b'installed app')
            release = {'application_id': deploy.APP, 'version': '0.20.0',
                       'runtime_variant': 'node012-beta', 'home_backend': 'c1-native-gate',
                       'routing': 'compositor-keyfilter-v1', 'compositor_admission': 3,
                       'native_sha256': 'a'*64}
            (root/'release.json').write_text(json.dumps(release))
            (root/'deploy.json').write_text(json.dumps(
                {'version': 1, 'app': deploy.APP, 'stage': 'provision-finalize-starting'}))
            (root/'recovery-failure.json').write_text(json.dumps(
                {'schema': 1, 'phase': 'status', 'reason': 'timeout',
                 'startup_state': 'exited', 'startup_exit_status': 0}))
            with patch.multiple(p, STATE=root, RUNNER=runner, LEGACY_NODE_BETA=True, FILES={}), \
                    patch.object(p, 'secure', side_effect=Path.read_bytes), \
                    patch.object(p, 'manifest', side_effect=lambda: {'files': {str(runner): p.sha(runner.read_bytes())}}), \
                    patch.object(p, 'verify_beta_repair_registration'), \
                    patch('package_identity.bootstrap_inventory') as verify_package, \
                    patch('runtime.c1_keyfilter.selection', return_value={'schema': 3, 'native_sha256': 'a'*64}), \
                    patch.object(p, 'finalize', side_effect=[TimeoutError(), None]) as finalize, \
                    patch.object(p, 'rpc') as status:
                # The real service handler wraps the Python CLI envelope.
                reply = subprocess.check_output(['node', '-e', """
const handlers = require(process.argv[1])(() => Promise.resolve({
  returnValue: true, result: {recovery: {integrity_verified: true}}
}));
handlers.status({}).then(reply => {
  reply.root = true;
  console.log(JSON.stringify(reply));
});
""", str(ROOT/'service/handlers.js')])
                status.return_value = json.loads(reply)
                runner.write_bytes(p.runner_bytes().replace(b'--disable-activity-creation ', b''))
                original_proof = p.manifest()
                pending.write_bytes(p.encoded({'files': {str(runner): '0'*64}}))
                with self.assertRaisesRegex(ValueError, 'manifest changed'):
                    p.repair_beta_recovery()
                self.assertNotIn(b'--disable-activity-creation ', runner.read_bytes())
                finalize.assert_not_called()
                pending.write_bytes(p.encoded(original_proof))
                runner.with_name(runner.name+'.root-preview-tmp').write_bytes(p.runner_bytes()[:15])
                with self.assertRaises(TimeoutError):
                    p.repair_beta_recovery()
                self.assertEqual(pending.read_bytes(), p.encoded(p.manifest()))
                self.assertEqual(runner.read_bytes(), p.runner_bytes())
                self.assertEqual(json.loads((root/'deploy.json').read_bytes())['stage'], 'provision-finalize-starting')
                result = p.repair_beta_recovery()
                self.assertTrue(result['status_verified'])
                self.assertEqual(json.loads((root/'deploy.json').read_bytes())['stage'], 'installed-recovery-only')
                status.assert_called_once_with('status')
                self.assertEqual(finalize.call_count, 2)
                verify_package.assert_called_with(root)
                (root/'recovery-provision.json').write_bytes(pending.read_bytes())
                self.assertTrue(p.repair_beta_recovery()['status_verified'])
                self.assertEqual(finalize.call_count, 2)
                good = status.return_value
                for bad in (
                        dict(good, root=False),
                        dict(good, result={'returnValue': False, 'result': good['result']['result']}),
                        dict(good, result={'returnValue': True, 'result': {'recovery': {'integrity_verified': False}}}),
                        dict(good, result=None),
                        dict(good, result={'returnValue': True, 'result': None}),
                        dict(good, result={'returnValue': True, 'result': {'recovery': None}})):
                    with self.subTest(reply=bad):
                        status.return_value = bad
                        with self.assertRaisesRegex(ValueError, 'status could not be verified'):
                            p.repair_beta_recovery()
                self.assertEqual(finalize.call_count, 2)
            self.assertEqual(installed.read_bytes(), b'installed app')

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
