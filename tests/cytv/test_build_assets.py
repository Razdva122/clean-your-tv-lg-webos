"""All runtime modules must be included even before their first Git commit."""
import hashlib
from pathlib import Path
import runpy
import unittest


class BuildAssetsTests(unittest.TestCase):
    def test_home_package_includes_storage_diagnostics_dependency(self):
        import json
        from cytv import package
        root = Path(__file__).resolve().parents[2]
        build = runpy.run_path(str(root / 'scripts/build-cytv.py'))
        sources = build['tracked_files']('renewal-service')
        app = {'appinfo.json': json.dumps({'id':'com.gathin.tvhome','version':'1.0.0','type':'native'}).encode()}
        files = package.data_files(build['pack_app'](app, sources))
        prefix = 'usr/palm/services/com.gathin.tvhome.renewal/'
        self.assertEqual(files[prefix+'diagnostics.js'], (root/'renewal-service/diagnostics.js').read_bytes())
        self.assertIn(b"require('./diagnostics')", files[prefix+'service.js'])

    def test_home_channel_is_provisioned_and_survives_personalization(self):
        import io
        import json
        import tarfile
        from cytv import package
        root = Path(__file__).resolve().parents[2]
        build = runpy.run_path(str(root / 'scripts/build-cytv.py'))
        app = {'appinfo.json': json.dumps({'id':'com.gathin.tvhome','version':'1.0.0','type':'native'}).encode()}
        raw = build['pack_app'](app, build['tracked_files']('renewal-service'))
        personalized, _ = package.personalize(raw, 'com.gathin.tvhome', {'apps':[{'id':'test.app'}]})
        channel = 'usr/palm/services/com.gathin.tvhome.renewal/state/home-control'
        for data in (raw, personalized):
            with tarfile.open(fileobj=io.BytesIO(package.read_ar(data)['data.tar.gz']), mode='r:gz') as archive:
                entry = archive.getmember(channel)
                self.assertEqual((entry.uid, entry.gid, entry.mode), (5999, 5000, 0o2770))
                self.assertEqual(archive.extractfile(channel+'/.keep').read(), b'')
                self.assertEqual(archive.getmember('usr/palm/services/com.gathin.tvhome.renewal').mode, 0o755)

    def test_https_service_assets_survive_the_public_source_filter(self):
        import json
        from cytv import package
        root = Path(__file__).resolve().parents[2]
        build = runpy.run_path(str(root / 'scripts/build-cytv.py'))
        for folder in ('renewal-service', 'updater-service'):
            sources = build['tracked_files'](folder)
            app = {'appinfo.json': json.dumps({'id':'com.test.home','version':'1.0.0','type':'native'}).encode()}
            files = package.data_files(build['pack_app'](app, sources))
            prefix = 'usr/palm/services/'+json.loads(sources['services.json'])['id']+'/'
            bundle = files[prefix+'ca-bundle.crt']
            self.assertIn(b'-----BEGIN CERTIFICATE-----', bundle)
            self.assertEqual(bundle, (root/'renewal-service/ca-bundle.crt').read_bytes())
            self.assertIn(prefix+'ca-LICENSE.txt', files)

    def test_installer_bundle_contains_approved_brand_masters(self):
        import tempfile
        root = Path(__file__).resolve().parents[2]
        build = runpy.run_path(str(root / 'scripts/build-cytv.py'))
        with tempfile.TemporaryDirectory() as directory:
            self.assertIn('stage_brand_assets', build, 'Installer branding is not staged')
            build['stage_brand_assets'](Path(directory))
            for packaged, master in [('brand-symbol.svg', 'symbol-reversed.svg'),
                                     ('brand-stacked.svg', 'logo-stacked-dark.svg')]:
                self.assertEqual((Path(directory) / packaged).read_bytes(),
                                 (root / 'assets/brand' / master).read_bytes())

    def test_setup_examples_are_staged_for_offline_desktop_use(self):
        import tempfile
        root = Path(__file__).resolve().parents[2]
        build = runpy.run_path(str(root / 'scripts/build-cytv.py'))
        with tempfile.TemporaryDirectory() as directory:
            build['stage_guide_assets'](Path(directory))
            for name in ('sign-in.png', 'dev-mode.png', 'key-server.png'):
                actual = (Path(directory) / 'setup-guide' / name).read_bytes()
                self.assertTrue(actual.startswith(b'\x89PNG\r\n\x1a\n'))
                self.assertEqual(actual, (root / 'android/app/src/main/assets/ui/guide' / name).read_bytes())

    def test_new_public_runtime_modules_are_packaged(self):
        build = runpy.run_path(str(Path(__file__).resolve().parents[2] / 'scripts/build-cytv.py'))
        self.assertIn('state-permissions.js', list(build['tracked_files']('native/app')))
        self.assertIn('app-library.js', list(build['tracked_files']('launcher')))
        self.assertIn('release-notes.js', list(build['tracked_files']('launcher')))
        self.assertIn('app-inventory.js', list(build['tracked_files']('native/service')))

    def test_helper_service_bundles_permissions_module_inside_its_sandbox(self):
        import json
        from cytv import package
        root = Path(__file__).resolve().parents[2]
        build = runpy.run_path(str(root / 'scripts/build-cytv.py'))
        permissions = (root / 'native/app/state-permissions.js').read_bytes()
        app = {'appinfo.json': json.dumps({'id': 'com.local.nativehome',
                                         'version': '0.6.18', 'type': 'native'}).encode(),
               'state-permissions.js': permissions}
        service = {'services.json': (root / 'native/service/services.json').read_bytes(),
                   'service.js': (root / 'native/service/service.js').read_bytes()}
        files = package.data_files(build['pack_app'](app, service, helper=True, architecture='arm'))
        prefix = 'usr/palm/services/com.local.nativehome.service/'
        self.assertEqual(files[prefix + 'state-permissions.js'],
                         files['usr/palm/applications/com.local.nativehome/state-permissions.js'])
        import os
        import subprocess
        import tempfile
        # Execute the service's packaged entry dependency, not its source copy.
        with tempfile.TemporaryDirectory() as directory:
            for name, raw in files.items():
                target = Path(directory) / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
            for runtime in dict.fromkeys(filter(None, ['node', os.environ.get('NODE010'), os.environ.get('NODE012')])):
                result = subprocess.run([runtime, '-e',
                    'var secure=require(process.argv[1]);if(typeof secure!=="function"||typeof Object.assign!=="function"||typeof Promise!=="function")process.exit(1);',
                    str(Path(directory) / prefix / 'state-permissions.js')], capture_output=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(b"require('./state-permissions')", files[prefix + 'service.js'])
        self.assertNotIn('state-permissions.js', service, 'Do not mutate the source mapping')

    def test_release_metadata_rejects_old_embedded_versions(self):
        import json
        import tempfile
        from cytv import package, __version__
        build = runpy.run_path(str(Path(__file__).resolve().parents[2] / 'scripts/build-cytv.py'))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'root').mkdir()
            versions={'cytv':__version__,'home':'1.3.0','helper':'0.6.14','root':'0.1.2'}
            for filename,app,service,version in [('launcher.ipk','com.gathin.tvhome','com.gathin.tvhome.renewal',versions['home']),('helper.ipk','com.local.nativehome','com.local.nativehome.service',versions['helper']),('root/root.ipk',package.ROOT_APP,package.ROOT_APP+'.service',versions['root'])]:
                files={f'usr/palm/applications/{app}/appinfo.json':json.dumps({'id':app,'version':version}).encode(),f'usr/palm/services/{service}/package.json':json.dumps({'version':version}).encode()}
                (root/filename).write_bytes(package.ipk(app,version,files))
            (root/'root/bundle.json').write_text('{"package":"root.ipk"}')
            (root/'root/release.json').write_text('{"version":"0.1.2"}')
            build['verify_release_versions'](root,versions)
            helper_path = root / 'helper.ipk'
            original_helper = helper_path.read_bytes()
            for name in ('usr/palm/applications/com.local.nativehome/appinfo.json',
                         'usr/palm/services/com.local.nativehome.service/package.json'):
                files = package.data_files(original_helper)
                metadata = json.loads(files[name]); metadata['version'] = '0.0.1'
                files[name] = json.dumps(metadata).encode()
                helper_path.write_bytes(package.ipk('com.local.nativehome', versions['helper'], files))
                with self.assertRaisesRegex(ValueError, 'application/service version'):
                    build['verify_release_versions'](root, versions)
            helper_path.write_bytes(original_helper)
            versions['root']='0.0.1'
            with self.assertRaisesRegex(ValueError,'version'):
                build['verify_release_versions'](root,versions)

    def test_published_helper_baseline_is_pinned_and_future_versions_build_from_source(self):
        import tempfile
        from unittest.mock import patch
        root = Path(__file__).resolve().parents[2]
        build = runpy.run_path(str(root / 'scripts/build-cytv.py'))
        self.assertIn('helper_baseline', build, 'Published Helper bytes are not preserved')
        baseline = build['helper_baseline']
        published = root / 'native/published/com.local.nativehome_0.6.16_arm.ipk'
        self.assertEqual(baseline('0.6.16'), published.read_bytes())
        self.assertEqual(baseline('0.6.17'), (root / 'native/published/com.local.nativehome_0.6.17_arm.ipk').read_bytes())
        current = baseline('0.6.19')
        self.assertIsNotNone(current, 'Keep the exact published 0.6.19 package')
        self.assertEqual(hashlib.sha256(current).hexdigest(), '52510c9115a518a05849f6618516b41886aea54b7f74ea4763ffeeaf63c03e7b')
        self.assertIsNone(baseline('0.6.20'))
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / 'native/published' / published.name
            fixture.parent.mkdir(parents=True)
            fixture.write_bytes(published.read_bytes() + b'corruption')
            with patch.dict(baseline.__globals__, ROOT=Path(directory)):
                with self.assertRaisesRegex(ValueError, 'hash'):
                    baseline('0.6.16')
            current_fixture = fixture.with_name('com.local.nativehome_0.6.19_arm.ipk')
            current_fixture.write_bytes(current + b'corruption')
            with patch.dict(baseline.__globals__, ROOT=Path(directory)):
                with self.assertRaisesRegex(ValueError, 'hash'):
                    baseline('0.6.19')
