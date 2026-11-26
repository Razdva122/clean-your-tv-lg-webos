import io
import json
import tarfile
import tempfile
from pathlib import Path
from unittest.mock import patch
import unittest
from cytv import package
from homebrew import build

class InstallerPackageTests(unittest.TestCase):
    def raw(self,files):return build.installer_ipk('0.0.0',files)
    def test_homebrew_payload_requires_a_hidden_new_generation_home(self):
        info = {'id': build.IDENTITIES['root'], 'cytvProductGeneration': 2, 'visible': False}
        build.require_tile_home(info)
        for incompatible in ({'visible': True}, {'cytvProductGeneration': 1},
                             {'cytvProductGeneration': '2'}, {'id': 'com.gathin.tvhome'}):
            with self.subTest(incompatible), self.assertRaisesRegex(ValueError, 'second-generation'):
                build.require_tile_home(dict(info, **incompatible))

    def test_complete_homebrew_tile_retains_standard_sdk_access(self):
        with patch('scripts.tv_web_build.compile_web', side_effect=lambda files: files):
            files = build.tile_web_files('0.0.0', versions={})
        info = json.loads(files[build.APP_PREFIX + 'appinfo.json'])
        self.assertNotIn('requiredACG', info)
        self.assertEqual(info['cytvTileProtocol'], 1)
        self.assertIn(build.APP_PREFIX + 'setup.html', files)

        for name in ('debloat.html', 'debloat-page.js', 'root-settings.css',
                     'root-post-install.js', 'root-post-install-locales.js'):
            self.assertTrue(build.APP_PREFIX + name in files, 'Missing tile asset: ' + name)
        page = files[build.APP_PREFIX + 'debloat.html']
        self.assertLess(page.index(b'src="debloat-page.js"'), page.index(b'src="root-post-install.js"'))

    def test_host_tiles_bind_one_edition_and_exclude_homebrew_installer(self):
        with tempfile.TemporaryDirectory() as temp, patch('scripts.tv_web_build.compile_web', side_effect=lambda files: files):
            for edition in ('root','no-root'):
                target = Path(temp) / (edition+'.ipk')
                self.assertEqual(build.build_tile(target,'1.2.3',edition), target)
                raw = target.read_bytes()
                info = build.installer_metadata(raw)
                self.assertEqual(info['cytvTileEdition'], edition)
                self.assertEqual(info['requiredACG'], ['application.launcher'])
                self.assertEqual((info['cytvTileProtocol'], info['title']), (1, 'Clean Your TV'))
                files = build.installer_files(raw)
                for name in ('debloat.html', 'debloat-page.js', 'root-post-install.js'):
                    self.assertNotIn(build.APP_PREFIX + name, files.keys())
                self.assertIn(json.dumps(edition).encode(), files[build.APP_PREFIX+'tile-config.js'])
                self.assertIn(build.APP_PREFIX+'recovery.html', files)
                self.assertFalse(any(name.endswith(('setup.html','bridge.js','bootstrap.js')) or '/payload/' in name for name in files))
            with self.assertRaises(ValueError):
                build.build_tile(Path(temp)/'unknown.ipk','1.2.3','auto')

    def test_homebrew_catalog_can_read_installed_size_in_bytes(self):
        files = {build.APP_PREFIX + 'index.html': b'x' * 12000,
                 build.PACKAGE_INFO: b'{}'}
        raw = build.installer_ipk('0.0.0', files)
        with tarfile.open(fileobj=io.BytesIO(package.read_ar(raw)['control.tar.gz'])) as archive:
            lines = archive.extractfile('control').read().decode().splitlines()
        self.assertEqual([line for line in lines if line.startswith('Installed-Size:')],
                         ['Installed-Size: 12002'])
        self.assertEqual(build.installer_files(raw), files)

    def test_metadata_rejects_absent_or_incorrect_control_size(self):
        info = {'id': build.APP_ID, 'version': '0.0.0', 'title': 'Clean Your TV',
                'type': 'web', 'main': 'index.html'}
        parts = package.read_ar(self.raw({build.APP_PREFIX + 'appinfo.json': json.dumps(info).encode()}))
        with tarfile.open(fileobj=io.BytesIO(parts['control.tar.gz'])) as archive:
            control = archive.extractfile('control').read().decode()
        line = next(line for line in control.splitlines(keepends=True) if line.startswith('Installed-Size:'))
        for replacement in ('', 'Installed-Size: -1\n', 'Installed-Size: 1\n',
                            'Installed-Size: many\n', line + line):
            with self.subTest(replacement=replacement):
                parts['control.tar.gz'] = package.tgz({'control': control.replace(line, replacement).encode()})
                with self.assertRaisesRegex(ValueError, 'Installed-Size'):
                    build.installer_metadata(package.ar(parts))

    def test_dedicated_metadata_reader_accepts_only_fixed_installer_identity(self):
        prefix='usr/palm/applications/io.github.razdva122.cytvinstaller/'
        raw=self.raw({prefix+'appinfo.json':json.dumps({'id':'io.github.razdva122.cytvinstaller','version':'0.0.0','title':'Clean Your TV','type':'web','main':'index.html'}).encode(),prefix+'payload/runtime.tar.gz':b'x'*(17*1024*1024)})
        with self.assertRaises(ValueError):package.data_files(raw)
        self.assertEqual(build.installer_metadata(raw)['version'],'0.0.0')
        with self.assertRaises(ValueError):build.installer_metadata(self.raw({'usr/palm/applications/foreign/appinfo.json':b'{}'}))
    def test_large_nested_root_package_has_a_scoped_limit(self):
        prefix=build.APP_PREFIX+'payload/'
        root=prefix+'root/com.cleanyourtv.root.preview_0.9.2_all.ipk'
        payload=b'x'*(17*1024*1024)
        raw=self.raw({root:payload})
        self.assertEqual(build.installer_files(raw),{root:payload})
        with self.assertRaises(ValueError):package.data_files(raw)
        for name in (prefix+'root/foreign_0.9.2_all.ipk',
                     prefix+'root/com.cleanyourtv.root.preview_invalid_all.ipk',
                     prefix+'other/com.cleanyourtv.root.preview_0.9.2_all.ipk',
                     prefix+'root/unexpected.bin'):
            with self.subTest(name=name),self.assertRaises(ValueError):
                build.installer_files(self.raw({name:payload}))
        with self.assertRaises(ValueError):
            build.installer_files(self.raw({root:b'x'*(64*1024*1024+1)}))

    def test_large_baseline_cache_package_has_a_scoped_limit(self):
        prefix=build.APP_PREFIX+'payload/baseline/cache/'
        name=prefix+'a'*64
        payload=b'x'*(17*1024*1024)
        self.assertEqual(build.installer_files(self.raw({name:payload})),{name:payload})
        for invalid in (prefix+'a'*63,prefix+'g'*64,
                        build.APP_PREFIX+'payload/other/cache/'+'a'*64):
            with self.subTest(name=invalid),self.assertRaises(ValueError):
                build.installer_files(self.raw({invalid:payload}))
        with self.assertRaises(ValueError):
            build.installer_files(self.raw({name:b'x'*(64*1024*1024+1)}))

    def test_duplicate_and_link_entries_are_rejected(self):
        prefix='usr/palm/applications/io.github.razdva122.cytvinstaller/'
        for kind in ('duplicate','link','oversize'):
            out=io.BytesIO()
            with tarfile.open(fileobj=out,mode='w:gz') as archive:
                member=tarfile.TarInfo(prefix+'appinfo.json');member.size=2;archive.addfile(member,io.BytesIO(b'{}'))
                if kind=='duplicate':archive.addfile(member,io.BytesIO(b'{}'))
                elif kind=='link':
                    member=tarfile.TarInfo(prefix+'link');member.type=tarfile.SYMTYPE;member.linkname='/etc/passwd';archive.addfile(member)
                else:
                    member=tarfile.TarInfo(prefix+'oversize');member.size=17*1024*1024;archive.addfile(member,io.BytesIO(b'x'*member.size))
            raw=package.ar({'debian-binary':b'2.0\n','control.tar.gz':package.tgz({'control':b'Package: io.github.razdva122.cytvinstaller\nVersion: 0.0.0\n'}),'data.tar.gz':out.getvalue()})
            with self.subTest(kind=kind),self.assertRaises(ValueError):build.installer_metadata(raw)

if __name__=='__main__':unittest.main()
