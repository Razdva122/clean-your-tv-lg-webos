"""Public engine artifacts must reproduce the exact installer engine bytes."""
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
import base64
import zipfile
from unittest.mock import patch

from test_build import load


class EngineBuildTests(unittest.TestCase):
    def test_signing_reconstructs_both_installer_engines(self):
        import importlib.util
        from cytv.package import tgz
        spec = importlib.util.spec_from_file_location('engine_release_bundles', Path(__file__).resolve().parents[2]/'scripts/prepare-release.py')
        release = importlib.util.module_from_spec(spec); spec.loader.exec_module(release)
        commit = 'a'*40
        versions = {key:'1.0.0' for key in ('cytv','home','helper','root','updater')}
        build = {'tag':'v1.23.0','source_commit':commit,'versions':versions,'system_engine':{'version':'1.2.11'}}
        def inventory(raw):
            return json.dumps({'schema':1,'engine_version':'1.2.11','files':{'engine-entry.py':hashlib.sha256(raw).hexdigest()}}).encode()
        original = b'verified engine'
        root_archive = tgz({'root/build/root-candidate/com.cleanyourtv.root.preview_1.0.0_all.ipk':b'root',
                            'root/build/system-updater/bundle.json':inventory(original),
                            'root/build/system-updater/engine-entry.py':original}, directories=False)
        def check(home_engine, metadata):
            zipped = io.BytesIO()
            with zipfile.ZipFile(zipped,'w') as archive:
                for name,raw in {'com.gathin.tvhome_1.0.0_all.ipk':b'home','com.local.nativehome_1.0.0_arm.ipk':b'helper',
                                 'system-updater/bundle.json':inventory(home_engine),'system-updater/engine-entry.py':home_engine}.items():
                    archive.writestr(name,raw)
            assets = {'BUILD-INFO.json':json.dumps(metadata).encode(),'clean-your-tv-no-root-1.0.0.zip':zipped.getvalue(),'clean-your-tv-root-1.0.0.tar.gz':root_archive}
            def download(meta,name,folder):
                (folder/name).write_bytes(assets[name]); return assets[name]
            def gh(*args):
                return json.dumps({'sha':commit} if '/commits/' in args[-1] else {'content':base64.b64encode(json.dumps(versions).encode()).decode()}).encode()
            with tempfile.TemporaryDirectory() as tmp, patch.object(release,'download',side_effect=download), patch.object(release,'gh',side_effect=gh), patch.object(release,'source_engine_version',return_value='1.2.11'):
                return release.bundles({'tag_name':'v1.23.0','target_commitish':commit},Path(tmp)/'current')
        self.assertIn('system-engine',check(original,build)[1])
        with self.assertRaisesRegex(ValueError,'engines differ'):
            check(b'different authenticated engine',build)
        with self.assertRaisesRegex(ValueError,'capability'):
            check(original,{k:v for k,v in build.items() if k!='system_engine'})

    def test_no_root_companion_requires_capable_remote_supervisor(self):
        from cytv import package
        builder = load('build')
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp).resolve()
            for name, filename in (('home', 'launcher.ipk'), ('helper', 'helper.ipk'), ('updater', 'updater.ipk')):
                app = builder.APPS[name]
                prefix = 'usr/palm/applications/' + app + '/'
                files = {prefix + 'appinfo.json': json.dumps({'id':app,'version':'2.0.0'}).encode()}
                if name == 'home': files[prefix+'screensaver-companion/manifest.json'] = b'{}'
                (Path(tmp)/filename).write_bytes(package.ipk(app, '2.0.0', files))
            manifest, _ = builder.release_set(tmp, 'no-root', 'v1.23.0', local=False)
            self.assertEqual((manifest['supervisor'], manifest['minimumSupervisorVersion']), (2, '1.2.11'))
            self.assertEqual([c['name'] for c in manifest['components']], ['home','helper','updater'])
            baseline, _ = builder.release_set(tmp, 'no-root', 'v1.23.0')
            self.assertEqual(baseline['supervisor'], 1)

    def test_missing_engine_source_stops_release_before_product_preparation(self):
        builder = load('build')
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'engine'):
                builder.prepare_release(Path(tmp), Path(tmp)/'out', 'v1.23.0', 'Changes')

    def test_release_engine_matches_installer_and_requires_version_bump(self):
        import importlib.util
        path = Path(__file__).resolve().parents[2]/'scripts/prepare-release.py'
        spec = importlib.util.spec_from_file_location('engine_release', path)
        release = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(release)
        raw = b'exact-installer-engine'
        engine = {'version': '1.2.11', 'size': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        release.verify_engine_transition(engine, raw, raw, None)
        with self.assertRaisesRegex(ValueError, 'installer'):
            release.verify_engine_transition(engine, raw, b'foreign', None)
        with self.assertRaisesRegex(ValueError, 'version bump'):
            release.verify_engine_transition(engine, raw, raw, {**engine, 'sha256': 'a'*64})

    def test_engine_archive_is_reproducible_and_matches_bundle_inventory(self):
        builder = load('build')
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp).resolve() / 'system-updater'
            bundle.mkdir()
            files = {'engine-entry.py': b'print("ready")\n',
                     'system_updater/core.py': b'VERSION = 1\n'}
            for name, raw in files.items():
                target = bundle / name
                target.parent.mkdir(exist_ok=True)
                target.write_bytes(raw)
            inventory = {name: hashlib.sha256(raw).hexdigest() for name, raw in files.items()}
            (bundle / 'bundle.json').write_text(json.dumps({'schema': 1, 'files': inventory}))
            first = builder.engine_archive(bundle)
            self.assertEqual(first, builder.engine_archive(bundle))
            with tarfile.open(fileobj=io.BytesIO(first), mode='r:gz') as archive:
                actual = {item.name: archive.extractfile(item).read() for item in archive}
            self.assertEqual(json.loads(actual.pop('engine.json')),
                             {'schema': 1, 'version': builder.ENGINE_VERSION, 'files': inventory})
            self.assertEqual(actual, files)
            (bundle / 'engine-entry.py').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'hash'):
                builder.engine_archive(bundle)

    def test_catalog_covers_both_editions_and_graphics_from_exact_manifests(self):
        builder = load('build')
        manifests = {name: {'edition': name.removesuffix('-720p'), 'release': 'v1.23.0'}
                     for name in ('root', 'root-720p', 'no-root', 'no-root-720p')}
        raw = b'verified-engine-archive'
        catalog = builder.engine_catalog(raw, manifests, 'v1.23.0')
        self.assertEqual(catalog['releases'], manifests)
        self.assertEqual(catalog['schema'], 1)
        self.assertEqual(catalog['engine']['size'], len(raw))
        self.assertEqual(catalog['engine']['sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(catalog['engine']['url'],
                         'https://github.com/Razdva122/clean-your-tv-lg-webos/releases/download/v1.23.0/system-engine_' + builder.ENGINE_VERSION + '.tar.gz')
        with self.assertRaises(ValueError):
            builder.engine_catalog(raw, {'root': manifests['root']}, 'v1.23.0')


if __name__ == '__main__':
    unittest.main()
