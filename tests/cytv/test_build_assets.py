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
        self.assertEqual(files[prefix+'diagnostics.js'], build['compile_helper'](sources)['diagnostics.js'])
        self.assertIn(b"require('./diagnostics')", files[prefix+'service.js'])
        canonical = {name: (root/'native/app'/name).read_bytes()
                     for name in ('state-permissions.js', 'contract-events.js')}
        compiled = build['compile_helper'](canonical)
        for name in canonical:
            self.assertEqual(files[prefix+name], compiled[name])
        import subprocess
        import tempfile
        import os
        # Package/source equality above is portable; this actual TV storage
        # exercise needs POSIX UID/GID, permissions and path semantics.
        if os.name == 'nt':
            return
        with tempfile.TemporaryDirectory() as directory:
            for name, raw in files.items():
                target = Path(directory) / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
            state = Path(directory).resolve()/'storage'
            state.mkdir(mode=0o770)
            module = str(Path(directory).resolve()/prefix/'state-permissions.js')
            for runtime in dict.fromkeys(filter(None, ['node', os.environ.get('NODE010'), os.environ.get('NODE01025'), os.environ.get('NODE012')])):
                result = subprocess.run([runtime, '-e',
                    "var p=require(process.argv[1]);p.atomicRecord(process.argv[2],'home-preference','{}');",
                    module, str(state)], capture_output=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual((state/'home-control.json').read_bytes(), b'{}')


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

    def test_installer_documents_are_staged_for_offline_desktop_use(self):
        import tempfile
        root = Path(__file__).resolve().parents[2]
        build = runpy.run_path(str(root / 'scripts/build-cytv.py'))
        with tempfile.TemporaryDirectory() as directory:
            payload = Path(directory)
            guide = root / 'android/app/src/main/assets/ui/guide'
            build['stage_installer_docs'](payload)
            for name in ('sign-in.png', 'dev-mode.png', 'key-server.png'):
                actual = (payload / 'setup-guide' / name).read_bytes()
                self.assertTrue(actual.startswith(b'\x89PNG\r\n\x1a\n'))
                self.assertEqual(actual, (guide / name).read_bytes())
            self.assertEqual((payload / 'setup-guide/README.md').read_bytes(),
                             (guide / 'README.md').read_bytes())
            for name in ('LICENSE', 'THIRD_PARTY_NOTICES.md'):
                self.assertEqual((payload / name).read_bytes(), (root / name).read_bytes())

    def test_theme_previews_are_staged_for_offline_desktop_use(self):
        import tempfile
        root = Path(__file__).resolve().parents[2]
        build = runpy.run_path(str(root / 'scripts/build-cytv.py'))
        with tempfile.TemporaryDirectory() as directory:
            build['stage_theme_previews'](Path(directory))
            for name, source in [('classic.png','showcase/assets/classic-preview.png'),
                                 ('liquid-glass.jpg','themes/liquid-glass/assets/preview.jpg'),
                                 ('ribbon.jpg','themes/ribbon/assets/preview.jpg')]:
                actual = (Path(directory)/'setup-themes'/name).read_bytes()
                self.assertGreater(len(actual),1024)
                self.assertEqual(actual,(root/source).read_bytes())

    def test_new_public_runtime_modules_are_packaged(self):
        build = runpy.run_path(str(Path(__file__).resolve().parents[2] / 'scripts/build-cytv.py'))
        self.assertIn('state-permissions.js', list(build['tracked_files']('native/app')))
        self.assertIn('app-library.js', list(build['tracked_files']('launcher')))
        self.assertIn('release-notes.js', list(build['tracked_files']('launcher')))
        self.assertIn('app-inventory.js', list(build['tracked_files']('native/service')))

    def test_fresh_helper_uses_only_tracked_sources_and_named_dependencies(self):
        import json
        import os
        import shutil
        import subprocess
        import tempfile
        from cytv import package

        root = Path(__file__).resolve().parents[2]
        app_names = {'appinfo.json', 'icon.png', 'state-permissions.js', 'contract-events.js',
                     'helper-entry.js', 'home-control.js', 'websocket.js', 'screensaver-controller.js',
                     'screensaver-lg.js', 'screensaver-owner.js', 'vendor/ws-legacy/LICENSE'}
        service_names = {'services.json', 'package.json', 'service.js', 'app-inventory.js'}
        generated_compat = {'compat-runtime.js', 'compat-polyfills.js', 'compat-buffer.js',
                            'compat-LICENSE.txt', 'state/.keep'}
        expected_app = app_names | generated_compat | {'app-inventory.js'} | {
            'screensaver/' + name + '.js' for name in ('controller', 'policy', 'transport', 'media', 'settings')
        }
        expected_service = service_names | generated_compat | {'state-permissions.js', 'contract-events.js'}
        explicit_untracked = {'native/app/home-control.js'}
        tracked = []
        with tempfile.TemporaryDirectory() as directory:
            checkout = Path(directory)
            paths = {'native/app/' + name for name in app_names} | {
                'native/service/' + name for name in service_names
            } | {'native/app/stop-generation.h', 'scripts/build-cytv.py', 'scripts/build.sh'} | {
                'screensaver/' + name + '.js' for name in ('controller', 'policy', 'transport', 'media', 'settings')
            }
            for name in sorted(paths):
                target = checkout / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(root / name, target)
                if name not in explicit_untracked:
                    tracked.append(name)
            info = checkout / 'native/app/appinfo.json'
            manifest = json.loads(info.read_text())
            info.write_text(json.dumps({**manifest, 'version': '9.9.9'}))
            (checkout / 'launcher').mkdir()
            for name in ('native/app/vendor/ws-legacy/notes.txt', 'native/app/stray.js',
                         'native/service/stray.js', 'native/app/state/private.json',
                         'native/service/state/private.json'):
                path = checkout / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('{}\n')
                if '/state/' in name:
                    tracked.append(name)
            subprocess.run(['git', 'init', '-q'], cwd=checkout, check=True)
            subprocess.run(['git', 'add', '--', *tracked], cwd=checkout, check=True)

            bash = shutil.which('bash')
            staged = {}
            if bash and os.name != 'nt':
                # Stop at the packager boundary, after build.sh has compiled the files.
                stop = checkout / 'stop-at-packager'
                stop.write_text('#!/bin/sh\nexit 77\n')
                stop.chmod(0o755)
                result = subprocess.run([bash, 'scripts/build.sh'], cwd=checkout,
                    env={**os.environ, 'PYTHONPATH': str(root), 'ZIG': 'true', 'ARES_PACKAGE': str(stop)},
                    capture_output=True, text=True)
                self.assertEqual(result.returncode, 77, result.stdout + result.stderr)
                for component, expected in (('app', expected_app), ('service', expected_service)):
                    folder = checkout / ('build/native-' + component)
                    staged[component] = {path.relative_to(folder).as_posix(): path.read_bytes()
                                         for path in folder.rglob('*') if path.is_file()}
                    self.assertEqual(set(staged[component]), expected)

            build = runpy.run_path(str(checkout / 'scripts/build-cytv.py'))
            raw = build['pack_app'](*build['helper_sources'](), architecture='arm', helper=True)
            files = package.data_files(raw)
            for component, prefix, expected in (
                ('app', 'usr/palm/applications/com.local.nativehome/', expected_app),
                ('service', 'usr/palm/services/com.local.nativehome.service/', expected_service),
            ):
                packaged = {name.removeprefix(prefix): data for name, data in files.items()
                            if name.startswith(prefix)}
                self.assertEqual(set(packaged), expected)
                if component in staged:
                    self.assertEqual(packaged, staged[component])
            vendor = 'native/app/vendor/ws-legacy/LICENSE'
            self.assertEqual(files['usr/palm/applications/com.local.nativehome/vendor/ws-legacy/LICENSE'],
                             (checkout / vendor).read_bytes())

    def test_helper_service_bundles_permissions_module_inside_its_sandbox(self):
        import json
        from cytv import package
        root = Path(__file__).resolve().parents[2]
        build = runpy.run_path(str(root / 'scripts/build-cytv.py'))
        permissions = (root / 'native/app/state-permissions.js').read_bytes()
        app = {'appinfo.json': json.dumps({'id': 'com.local.nativehome',
                                         'version': '0.6.18', 'type': 'native'}).encode(),
               'state-permissions.js': permissions,
               'contract-events.js': (root/'native/app/contract-events.js').read_bytes()}
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
            for runtime in dict.fromkeys(filter(None, ['node', os.environ.get('NODE010'), os.environ.get('NODE01025'), os.environ.get('NODE012')])):
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
            root=Path(tmp); (root/'root').mkdir(); (root/'root-720p').mkdir()
            versions={'cytv':__version__,'home':'1.3.0','helper':'0.6.14','root':'0.1.2'}
            for filename,app,service,version in [('launcher.ipk','com.gathin.tvhome','com.gathin.tvhome.renewal',versions['home']),('helper.ipk','com.local.nativehome','com.local.nativehome.service',versions['helper']),('root/root.ipk',package.ROOT_APP,package.ROOT_APP+'.service',versions['root'])]:
                files={f'usr/palm/applications/{app}/appinfo.json':json.dumps({'id':app,'version':version,'resolution':'1920x1080'}).encode(),f'usr/palm/services/{service}/package.json':json.dumps({'version':version}).encode()}
                (root/filename).write_bytes(package.ipk(app,version,files))
            (root/'root/bundle.json').write_text('{"package":"root.ipk"}')
            (root/'root/release.json').write_text('{"version":"0.1.2"}')
            for original,target,app in [('launcher.ipk','launcher-720p.ipk','com.gathin.tvhome'),('root/root.ipk','root-720p/root.ipk',package.ROOT_APP)]:
                files=package.data_files((root/original).read_bytes());name='usr/palm/applications/'+app+'/appinfo.json'
                info=json.loads(files[name]);info['resolution']='1280x720';files[name]=json.dumps(info).encode()
                (root/target).write_bytes(package.ipk(app,info['version'],files))
            for name in ('bundle.json','release.json'):(root/'root-720p'/name).write_bytes((root/'root'/name).read_bytes())
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
