"""Recovery of a payload rejected before native preparation/package submission."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import deploy
import install_device
from updater.store import Store
import test_clean_removal as removal_fixture


class PreSubmissionCleanup(unittest.TestCase):
    def fixture(self):
        fixture = removal_fixture.PartialDeviceRemoval.fixture(self)
        driver, identifier, root, updater, payload, calls, present = fixture
        shutil.rmtree(root)
        root.mkdir(mode=0o700)
        shutil.rmtree(updater)
        present.clear()
        package = deploy.APP + '_0.24.2_all.ipk'
        names = set(deploy.SUPPORT_FILES) | {'runtime/'+n for n in deploy.RUNTIME_FILES}
        names |= {'runtime/'+n for n in ('c1_gate.py', 'c1_keyfilter.py', 'c1-keyfilter-guard',
                                        'c1-home-filter.js', 'embedded_home.py', 'embedded-home.qml', 'embedded-home.js')}
        release = {'application_id':deploy.APP, 'version':'0.24.2', 'home_backend':'c1-native-gate',
                   'experimental':True, 'routing':'compositor-keyfilter-v1'}
        files = {}
        for name in sorted(names | {'release.json'}):
            raw = json.dumps(release).encode() if name == 'release.json' else b'old packaged data; never execute'
            if name == 'runtime/embedded-home.js':raw = b'x'*285303
            path = root/name
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            path.write_bytes(raw)
            path.chmod(0o600)
            files[name] = hashlib.sha256(raw).hexdigest()
        files.update({package:'a'*64, 'SHA256SUMS':'b'*64, deploy.BETA_MIGRATION_SCRIPT:'c'*64})
        (root/'bundle.json').write_text(json.dumps({'package':package, 'files':files}))
        Store(root, uid=os.getuid()).write('deploy', {'version':1, 'app':deploy.APP, 'stage':'prepared', 'package':package})
        original = deploy.command
        def restore(args):
            if 'runtime_restore_report' in args[-1]:
                raise ValueError('Missing experimental Home backend selection; retain recovery evidence')
            return original(args)
        patcher = patch.object(deploy, 'command', side_effect=restore)
        patcher.start()
        self.addCleanup(patcher.stop)
        return fixture

    def test_prepared_payload_removes_without_running_missing_backend(self):
        driver, identifier, root, _, _, calls, _ = self.fixture()
        result = driver.clean_remove(identifier)
        self.assertEqual(result['stage'], 'restart-required', result)
        self.assertIn('package-removal', result['done'])
        self.assertNotIn('current-restore', calls)
        self.assertFalse((root/'runtime/embedded-home.js').exists())
        driver.device.current_boot = '22222222-2222-2222-2222-222222222222'
        final = driver.clean_remove(identifier)
        self.assertEqual(final['stage'], 'verified-clean', final)
        self.assertEqual(final['routes'], {'mode':'never-applied'})

    def test_direct_native_setup_without_product_submission_can_clean(self):
        driver, identifier, root, _, _, calls, _ = self.fixture()
        (Path(driver.store.root)/('request-'+identifier+'.json')).unlink()
        result=driver.clean_remove(identifier)
        self.assertEqual(result['stage'],'verified-clean',result)
        self.assertIsNone(result['original']['request'])
        self.assertIsNone(result['original']['submission'])
        self.assertFalse((root/'runtime/embedded-home.js').exists())
        self.assertNotIn('current-restore',calls)

    def test_real_beta_bundle_with_old_node_transformed_qml_recovers(self):
        from test_c1_gate_bundle import load, static_arm
        driver, identifier, root, _, _, calls, _ = self.fixture()
        base=root.parent
        helper=base/'guardian'
        helper.write_bytes(static_arm()+b'CYTV-QML-KEYFILTER-1\0')
        bundle=base/'original-beta'
        load('build').build(bundle,legacy_node_beta=True,experimental_c1_keyfilter=helper)
        source=(bundle/'runtime/embedded-home.js').read_text()
        compiler=Path(__file__).resolve().parents[2]/'scripts/compile-root-node.cjs'
        compiled=subprocess.run(['node',str(compiler)],input=json.dumps({'runtime/embedded-home.js':source}),
                                capture_output=True,text=True,check=True)
        old_js=json.loads(compiled.stdout)['runtime/embedded-home.js'].encode()
        self.assertGreater(len(old_js),256*1024)
        manifest=json.loads((bundle/'bundle.json').read_text())
        self.assertIn(deploy.BETA_MIGRATION_SCRIPT,manifest['files'])
        self.assertEqual(json.loads((bundle/'release.json').read_text())['runtime_variant'],'node012-beta')
        shutil.rmtree(root);root.mkdir(mode=0o700)
        excluded={manifest['package'],'SHA256SUMS',deploy.BETA_MIGRATION_SCRIPT,'runtime/c1-home-gate'}
        for name in set(manifest['files'])-excluded:
            target=root/name;target.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
            raw=old_js if name=='runtime/embedded-home.js' else (bundle/name).read_bytes()
            target.write_bytes(raw);target.chmod(0o600)
            manifest['files'][name]=hashlib.sha256(raw).hexdigest()
        (root/'bundle.json').write_text(json.dumps(manifest))
        Store(root,uid=os.getuid()).write('deploy',{'version':1,'app':deploy.APP,'stage':'prepared','package':manifest['package']})
        result=driver.clean_remove(identifier)
        self.assertEqual(result['stage'],'restart-required',result)
        self.assertFalse((root/'runtime/embedded-home.js').exists())
        self.assertNotIn('current-restore',calls)
        driver.device.current_boot='22222222-2222-2222-2222-222222222222'
        self.assertEqual(driver.clean_remove(identifier)['stage'],'verified-clean')

    def test_conflicting_evidence_preserves_retained_payload(self):
        cases = ('changed', 'missing', 'unknown', 'descriptor', 'gate', 'provision',
                 'app', 'package-path', 'worker', 'submitted', 'startup', 'registration', 'symlink', 'hardlink')
        for case in cases:
            with self.subTest(case=case):
                driver, identifier, root, _, _, calls, present = self.fixture()
                asset = root/'runtime/embedded-home.js'
                if case == 'changed':asset.write_bytes(b'changed')
                if case == 'missing':(root/'runtime/embedded-home.qml').unlink()
                if case == 'symlink':
                    path=root/'runtime/embedded-home.qml';path.unlink();path.symlink_to(asset)
                if case == 'hardlink':
                    os.link(root/'runtime/embedded-home.qml',root.parent/'foreign-link')
                if case == 'unknown':(root/'unexpected').write_text('preserve')
                if case == 'descriptor':(root/'home-backend.json').write_text('{}')
                if case == 'gate':(root/'c1-keyfilter').mkdir()
                if case == 'provision':(root/'ls2-provision-snapshot.json').write_text('{}')
                if case == 'app':present.add(deploy.APP)
                if case == 'package-path':
                    path = driver.device.package_paths(deploy.APP)[0]
                    path.mkdir(parents=True)
                if case == 'worker':
                    process = install_device.PROC/'987654'
                    process.mkdir()
                    (process/'cmdline').write_bytes(str(root/'runtime/c1-keyfilter-guard').encode()+b'\0')
                if case == 'submitted':
                    Store(root,uid=os.getuid()).write('deploy',{'version':1,'app':deploy.APP,'stage':'install-submitting'})
                if case == 'startup':(install_device.INIT/'50-clean-your-tv-root').write_text('preserve')
                if case == 'registration':
                    directory=install_device.BUS/'services.d';directory.mkdir()
                    (directory/(deploy.APP+'.service')).write_text('preserve')
                before=asset.read_bytes()
                with patch.object(driver.device,'log'):
                    result=driver.clean_remove(identifier)
                self.assertEqual(result['state'],'recovery_required',result)
                self.assertNotIn('controls-restored',result['done'])
                self.assertEqual(asset.read_bytes(),before)
                self.assertFalse(any(call.startswith('remove-') for call in calls))

    def test_changed_cleanup_fence_is_not_admitted(self):
        import clean_removal
        _, _, root, _, _, _, _ = self.fixture()
        store=Store(root,uid=os.getuid())
        original=store.read('deploy')
        for changed in ({'version':1,'app':deploy.APP,'stage':'prepared','package':original['package']},
                        {'version':1,'app':deploy.APP,'stage':'cancellation-admitted','extra':True}):
            with self.subTest(changed=changed):
                store.write('deploy',changed)
                with self.assertRaisesRegex(ValueError,'unprepared_native_fence_changed'):
                    clean_removal.unprepared_native_payload(root,original,os.getuid())
                self.assertTrue((root/'runtime/embedded-home.js').exists())

    def test_ordinary_prepared_uses_existing_runtime_restore(self):
        driver, identifier, root, _, _, calls, _ = removal_fixture.PartialDeviceRemoval.fixture(self)
        Store(root,uid=os.getuid()).write('deploy',{'version':1,'app':deploy.APP,'stage':'prepared'})
        with patch.object(driver.device,'log'):
            result=driver.clean_remove(identifier)
        self.assertIn('current-restore',calls)
        self.assertIn('controls-restored',result['done'])


if __name__ == '__main__':
    unittest.main()
