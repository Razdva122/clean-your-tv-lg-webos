import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def ar_members(raw):
    assert raw[:8] == b'!<arch>\n'
    members, offset = {}, 8
    while offset < len(raw):
        header = raw[offset:offset + 60]
        size = int(header[48:58])
        members[header[:16].decode().strip().rstrip('/')] = raw[offset + 60:offset + 60 + size]
        offset += 60 + size + size % 2
    return members


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'build.py').exists(), 'Offline package builder is missing')
        spec = importlib.util.spec_from_file_location('root_build', ROOT / 'build.py')
        self.builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.builder)

    def test_weather_closure_preserves_private_inventory_and_bundles_trust(self):
        source={'service.js':b"module.exports = require('./weather');"}
        result=self.builder.bundle_weather(source)
        self.assertEqual(set(result),set(source))
        self.assertNotIn(b"require('./weather')",result['service.js'])
        self.assertNotIn(b"/ca-bundle.crt",result['service.js'])
        import subprocess
        with tempfile.TemporaryDirectory() as directory:
            script=Path(directory)/'weather.js';script.write_bytes(result['service.js'])
            run=subprocess.run(['node','tests/weather/service.cjs',str(script)],cwd=ROOT.parent,capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)

    def test_candidate_is_deterministic_isolated_and_hashes_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            first, second = Path(tmp).resolve() / 'first', Path(tmp).resolve() / 'second'
            self.builder.build(first)
            self.builder.build(second)
            self.assertEqual({str(p.relative_to(first)): p.read_bytes() for p in first.rglob('*') if p.is_file()},
                             {str(p.relative_to(second)): p.read_bytes() for p in second.rglob('*') if p.is_file()})
            from deploy import verify_bundle
            manifest = verify_bundle(first)
            self.assertIn('runtime/cli.py', manifest['files'])
            for name in ('intent_runtime.py', 'shutdown_state.py'):
                self.assertEqual((first / 'runtime' / name).read_bytes(), (ROOT / 'runtime' / name).read_bytes())
            self.assertIn('setup.py', manifest['files'])
            self.assertIn('installation.py',manifest['files'])
            self.assertIn('updater/store.py',manifest['files'])
            import subprocess
            result = subprocess.run([sys.executable,'-I','-B','-c',
                'import sys;sys.path.insert(0,sys.argv[1]);import deploy,installation,package_data,startup_guard;'
                'assert installation.Store.__module__ == "updater.store";'
                'sys.path.insert(0,sys.argv[1]+"/runtime");import intent_runtime,shutdown_state;assert callable(intent_runtime.startup_reconcile);assert callable(shutdown_state.observe_startup)',str(first)],
                cwd=Path(tmp),capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            ipk = next(first.glob('*.ipk'))
            parts = ar_members(ipk.read_bytes())
            self.assertEqual(set(parts), {'debian-binary', 'control.tar.gz', 'data.tar.gz'})
            self.assertEqual(parts['debian-binary'], b'2.0\n')
            with tarfile.open(fileobj=io.BytesIO(parts['data.tar.gz'])) as archive:
                files = {m.name: archive.extractfile(m).read() for m in archive if m.isfile()}
                self.assertTrue(all((m.isfile() or (m.isdir() and m.mode==0o755 and len(Path(m.name).parts)>=4)) and 1577836800 <= m.mtime <= 1767225600 for m in archive))
            prefix = 'usr/palm/applications/com.cleanyourtv.root.preview/'
            self.assertTrue(all(n.startswith(prefix) or n.startswith('usr/palm/services/com.cleanyourtv.root.preview.service/') or n == 'usr/palm/packages/com.cleanyourtv.root.preview/packageinfo.json' for n in files))
            self.assertEqual(json.loads(files[prefix + 'appinfo.json'])['id'], 'com.cleanyourtv.root.preview')
            self.assertEqual(json.loads(files[prefix + 'appinfo.json'])['themeEngineVersion'], json.loads((ROOT.parent/'launcher/appinfo.json').read_text())['version'])
            self.assertEqual(json.loads(files['usr/palm/packages/com.cleanyourtv.root.preview/packageinfo.json'])['services'], ['com.cleanyourtv.root.preview.service'])
            service_prefix = 'usr/palm/services/com.cleanyourtv.root.preview.service/'
            self.assertEqual({n[len(service_prefix):] for n in files if n.startswith(service_prefix)}, {'service.js', 'startup-diagnostics.js', 'app-inventory.js', 'presentation-context.js', 'handlers.js', 'services.json', 'package.json', 'boot-recover.sh', 'activity.json'})
            self.assertEqual(json.loads(files[service_prefix+'package.json'])['wallpaperMediaProtocol'],1)
            self.assertIn(b'themeReceiverStart',files[service_prefix+'service.js'])
            self.assertNotIn(b"require('./theme-receiver')",files[service_prefix+'service.js'])
            with tarfile.open(fileobj=io.BytesIO(parts['data.tar.gz'])) as archive:
                self.assertEqual(archive.getmember(service_prefix + 'boot-recover.sh').mode, 0o755)
            self.assertEqual(files[prefix + 'apps.js'], b'window.TV_APPS = {apps: [], inputs: []};\n')
            self.assertNotIn(prefix + 'user-data.js', files)
            self.assertNotIn(prefix + 'native-bootstrap.js', files)
            with tarfile.open(fileobj=io.BytesIO(parts['control.tar.gz'])) as archive:
                self.assertEqual(archive.getnames(), ['control'])
                self.assertGreaterEqual(archive.getmember('control').mtime, 1577836800)
            release = json.loads((first / 'release.json').read_text())
            self.assertFalse(release['hardware_validated'])
            self.assertEqual(release['capabilities'],['theme-receiver-v1','wallpaper-media-v1'])
            # Recovery and runtime provisioning have different contracts but share a filename.
            spec = importlib.util.spec_from_file_location('root_build_recovery_provision', ROOT / 'provision.py')
            provision = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(provision)
            original={'service':'Exec=/usr/bin/run-js-service -n '+str(provision.SERVICE),'role':json.dumps({'appId':provision.NAME}),'client':'{}','api':'{}'}
            api=json.loads(provision.plan(original,provision.snapshot_capabilities(release))['api'])
            methods=api[provision.NAME+'.control']
            for method in ('wallpaperCacheStart','wallpaperCacheWrite','wallpaperCacheCommit','wallpaperCacheKeepAlive','wallpaperCacheStop'):
                self.assertIn(provision.NAME+'/'+method,methods)
                self.assertIn(method.encode(),files[service_prefix+'service.js'])
            for name, digest in release['files'].items():
                self.assertEqual(hashlib.sha256(files[name]).hexdigest(), digest)
            self.assertEqual((first / 'SHA256SUMS').read_text(), hashlib.sha256(ipk.read_bytes()).hexdigest() + '  ' + ipk.name + '\n')

    def test_personalized_bundle_retains_executable_startup_and_passes_staged_ownership(self):
        import subprocess
        from cytv import package
        from deploy import verify_bundle
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();bundle=root/'bundle';self.builder.build(bundle,version='1.2.3')
            package.personalize_root(bundle,{'apps':[{'id':'org.example.video','title':'Video'}],'inputs':[]})
            manifest=verify_bundle(bundle);raw=(bundle/manifest['package']).read_bytes()
            package.verify_root_rollback_format(raw)
            installed=root/'installed';installed.mkdir()
            with tarfile.open(fileobj=io.BytesIO(package.read_ar(raw)['data.tar.gz'])) as archive:
                app='usr/palm/applications/com.cleanyourtv.root.preview/'
                self.assertEqual(archive.getmember(app+'startup.sh').mode,0o755)
                self.assertEqual(archive.getmember('usr/palm/services/com.cleanyourtv.root.preview.service/boot-recover.sh').mode,0o755)
                for member in archive:
                    if member.isdir():continue
                    target=installed/member.name;target.parent.mkdir(parents=True,exist_ok=True)
                    target.write_bytes(archive.extractfile(member).read());target.chmod(member.mode)
            script="""
import os,sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,sys.argv[1])
import deploy,startup_hook as h
deploy.verify_bundle(sys.argv[1])
h.INSTALLED=Path(sys.argv[2]);h.EXPECTED_UID=os.getuid()
# The temporary host ancestors are outside the synthetic TV trust root.
with patch.object(h,'trusted_directory'):
    value=h.target_receipt(Path.read_bytes,h.INSTALLED/'hook','com.cleanyourtv.root.preview')
assert value['version']==2
assert value['target']==str(h.INSTALLED/'usr/palm/applications/com.cleanyourtv.root.preview/startup.sh')
"""
            result=subprocess.run([sys.executable,'-I','-B','-c',script,str(bundle),str(installed)],cwd=root,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)

    def test_existing_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp).resolve() / 'existing'
            output.mkdir()
            (output / 'keep').write_text('user data')
            with self.assertRaises(FileExistsError):
                self.builder.build(output)
            self.assertEqual(list(output.iterdir()), [output / 'keep'])

    def test_versioned_package_and_bootstrap_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp).resolve() / 'candidate'
            package = self.builder.build(output, version='1.2.3')
            self.assertEqual(package.name, 'com.cleanyourtv.root.preview_1.2.3_all.ipk')
            self.assertEqual(json.loads((output / 'release.json').read_text())['version'], '1.2.3')
            with tarfile.open(fileobj=io.BytesIO(ar_members(package.read_bytes())['data.tar.gz'])) as archive:
                prefix = 'usr/palm/applications/com.cleanyourtv.root.preview/'
                self.assertEqual(json.loads(archive.extractfile(prefix + 'appinfo.json').read())['version'], '1.2.3')
                self.assertIn(b'window.ROOT_VERSION = "1.2.3"', archive.extractfile(prefix + 'index.html').read())
            from deploy import verify_bundle
            verify_bundle(output)

    def test_invalid_versions_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            for index, version in enumerate(('1', 'v1.2.3', '1.2.3;id', '01.2.3', '1.2.-1', '1.2.3-beta')):
                output = Path(tmp).resolve() / str(index)
                with self.assertRaises(ValueError):
                    self.builder.build(output, version=version)
                self.assertFalse(output.exists())

    def test_archive_rejects_unsafe_paths(self):
        for name in ('../secret', '/absolute', 'a/../b', 'a//b', './a', 'a\\b', 'a\x00b'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.builder.tgz({name: b'data'})

    def test_service_identity_mismatch_is_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            source = root / 'service'
            source.mkdir()
            for name in self.builder.SERVICE_FILES:
                (source / name).write_bytes((self.builder.SERVICE_SOURCE / name).read_bytes())
            (source / 'services.json').write_text('{"id":"com.gathin.tvhome"}')
            self.builder.SERVICE_SOURCE = source
            with self.assertRaises(ValueError):
                self.builder.build(root / 'candidate')
            self.assertFalse((root / 'candidate').exists())

    def test_output_through_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root / 'real').mkdir()
            (root / 'link').symlink_to(root / 'real', target_is_directory=True)
            with self.assertRaises(ValueError):
                self.builder.build(root / 'link' / 'candidate')
            self.assertFalse((root / 'real' / 'candidate').exists())


if __name__ == '__main__':
    unittest.main()
