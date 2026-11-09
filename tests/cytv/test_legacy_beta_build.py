"""Execute generated Beta policy; default and prototype remain gated."""
import importlib.util
import json
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

    def test_compositor_script_stays_outside_node_compatibility_runtime(self):
        from scripts.root_node_build import compile_root_beta
        name = 'runtime/c1-home-filter.js'
        source = (ROOT/'root-edition'/name).read_bytes()
        compiled = compile_root_beta({name: source, 'python_boot.js': b'module.exports = true;\n'})
        self.assertEqual(compiled[name], source)
        self.assertIn(b'__cytvRootNodePrototypeCompat', compiled['python_boot.js'])

    def test_beta_keyfilter_bundle_uses_shared_backend_and_exact_runtime_driver(self):
        from cytv.package import data_files
        fixture = load('beta_gate_fixture', ROOT/'root-edition/tests/test_c1_gate_bundle.py')
        helper = self.base/'guardian'
        helper.write_bytes(fixture.static_arm())
        folder = self.base/'beta-keyfilter'
        self.builder.build(folder, legacy_node_beta=True, experimental_c1_keyfilter=helper)
        release = json.loads((folder/'release.json').read_bytes())
        self.assertEqual(release['runtime_variant'], 'node012-beta')
        self.assertIs(release['automatic_updates'], False)
        self.assertEqual(release['routing'], 'compositor-keyfilter-v1')
        self.assertEqual(release['compositor_admission'], 3)
        deploy = load('beta_keyfilter_deploy', folder/'deploy.py')
        self.assertIs(deploy.LEGACY_NODE_BETA, True)
        deploy.verify_bundle(folder, allow_experimental=True)
        with self.assertRaises(ValueError):
            deploy.verify_bundle(folder)
        with self.assertRaises(ValueError):
            load('normal_keyfilter_deploy', ROOT/'root-edition/deploy.py').verify_bundle(folder, allow_experimental=True)
        for name in ('c1_keyfilter.py', 'c1_gate.py', 'c1-home-filter.js'):
            self.assertEqual((folder/'runtime'/name).read_bytes(), (ROOT/'root-edition/runtime'/name).read_bytes())
        self.assertEqual((folder/'runtime/c1-keyfilter-guard').read_bytes(), helper.read_bytes())
        self.assertFalse((folder/'runtime/c1-home-gate').exists())
        contents = data_files((folder/json.loads((folder/'bundle.json').read_bytes())['package']).read_bytes())
        service = contents['usr/palm/services/com.cleanyourtv.root.preview.service/service.js']
        self.assertIn(b'__cytvRootNodePrototypeCompat', service)
        if os.environ.get('NODE012'):
            real_run = subprocess.run
            with patch.object(deploy.subprocess, 'run', side_effect=lambda args, **kw: real_run([os.environ['NODE012'], *args[1:]], **kw)):
                deploy.require_node()
        with patch.object(deploy.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1)):
            with self.assertRaisesRegex(RuntimeError, '0.12.2'):
                deploy.require_node()

    def test_beta_does_not_admit_legacy_mount_or_host_only_prototype(self):
        fixture = load('beta_refusal_fixture', ROOT/'root-edition/tests/test_c1_gate_bundle.py')
        helper = self.base/'refused-guardian'
        helper.write_bytes(fixture.static_arm())
        for flags in ({'legacy_node_beta':True, 'experimental_c1_gate':helper},
                      {'legacy_node_prototype':True, 'experimental_c1_keyfilter':helper}):
            with self.subTest(flags=flags), self.assertRaises(ValueError):
                self.builder.build(self.base/'refused', **flags)

    @unittest.skipUnless(os.environ.get('NODE012'), 'Exact NODE012 runtime not supplied')
    def test_shared_lease_authority_and_stop_checks_on_exact_legacy_node(self):
        from scripts.root_node_build import compile_root_node
        from scripts.theme_receiver import inject
        service = ROOT/'root-edition/service'
        compiled = compile_root_node(inject({'c1-lease.js':(service/'c1-lease.js').read_bytes(),
                                     'presentation-context.js':(service/'presentation-context.js').read_bytes(),
                                     'app-inventory.js':(service/'app-inventory.js').read_bytes(),
                                     'test-c1-lease.js':(service/'test-c1-lease.cjs').read_bytes()}))
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            for name, raw in compiled.items():
                target = folder/name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
            # Keep the C1 import boundary; reuse real weather/CA and receiver closures.
            registration = self.builder.bundle_weather({'service.js':(service/'service.js').read_bytes()})
            (folder/'service.js').write_bytes(registration['service.js'])
            subprocess.run([os.environ['NODE012'], str(folder/'test-c1-lease.js'), str(folder)], check=True, timeout=30)

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
