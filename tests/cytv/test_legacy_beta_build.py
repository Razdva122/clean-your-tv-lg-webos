"""Execute generated Beta policy; default and prototype remain gated."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'root-edition'))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BetaBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.tmp.name).resolve()
        cls.builder = load('beta_root_builder', ROOT/'root-edition/build.py')
        cls.builder.build(cls.base/'beta', legacy_node_beta=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    @unittest.skipUnless(os.environ.get('NODE012'), 'Exact NODE012 runtime not supplied')
    def test_generated_device_gate_only_accepts_exact_runtime(self):
        deploy = load('beta_deploy', self.base/'beta/deploy.py')
        real_run = subprocess.run
        node = os.environ.get('NODE012')
        self.assertTrue(node, 'Run with exact NODE012')
        with patch.object(deploy.subprocess, 'run', side_effect=lambda args, **kw: real_run([node,*args[1:]], **kw)):
            deploy.require_node()
        with patch.object(deploy.subprocess, 'run', side_effect=lambda args, **kw: real_run(['node',*args[1:]], **kw)):
            with self.assertRaises(RuntimeError):
                deploy.require_node()
        deploy.verify_bundle(self.base/'beta')
        normal = load('stable_deploy', ROOT/'root-edition/deploy.py')
        with self.assertRaises(ValueError):
            normal.verify_bundle(self.base/'beta')

    @unittest.skipUnless(os.environ.get('NODE012'), 'Exact NODE012 runtime not supplied')
    def test_beta_runner_keeps_vendor_main_without_unsupported_require_option(self):
        provision = load('beta_provision', self.base/'beta/provision.py')
        import shlex
        line = provision.runner_bytes().decode().splitlines()[-1]
        argv = shlex.split(line)[1:]
        # Exact Node must accept the invocation before trying the absent TV bootstrap.
        result = subprocess.run([os.environ['NODE012'], *argv[1:]], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 9, result.stderr)
        self.assertEqual(argv[1], '/usr/palm/services/jsservicelauncher/bootstrap-node.js')

    def test_beta_updaters_reject_new_delivery_before_device_or_transaction_work(self):
        for name, relative in [('root', 'root-edition/build_updater.py'), ('system', 'system-updater/build.py')]:
            folder = self.base/name
            load('beta_'+name+'_builder', ROOT/relative).build(folder, legacy_node_beta=True)
            file = folder/('updater/cli.py' if name == 'root' else 'system_updater/cli.py')
            # Execute the real handler with imports supplied by their existing source trees.
            source = file.read_text()
            context = {'__name__':'beta_handler', '__file__':str(file), 'spawn_worker':lambda:None}
            code = source[:source.index('def spawn_worker')]
            # Imports are covered by updater suites; the isolated policy never uses TV worker locks.
            code = '\n'.join(line for line in code.splitlines() if line != 'import fcntl' and not line.startswith(('from updater.', 'from system_updater.', 'from .')))
            exec(code, context)
            start = source.index('def handle(')
            end = source.index('\ndef worker(', start)
            exec(source[start:end], context)
            for method, payload in [('check', {} if name=='root' else {'edition':'root'}),
                                    ('install', {'version':'1.0.0','profile':{}} if name=='root' else {'edition':'root','release':'v1.0.0','profile':{}})]:
                with self.assertRaisesRegex(ValueError, 'Beta'):
                    context['handle'](method, payload, None, None)


if __name__ == '__main__':
    unittest.main()
