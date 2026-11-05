import io
import json
import tarfile
import unittest
from cytv import package
from homebrew import build

class InstallerPackageTests(unittest.TestCase):
    def raw(self,files):return package.ipk('com.cleanyourtv.installer','0.0.0',files)
    def test_dedicated_metadata_reader_accepts_only_fixed_installer_identity(self):
        prefix='usr/palm/applications/com.cleanyourtv.installer/'
        raw=self.raw({prefix+'appinfo.json':json.dumps({'id':'com.cleanyourtv.installer','version':'0.0.0','title':'CYTV Installer','type':'web','main':'index.html'}).encode(),prefix+'payload/runtime.tar.gz':b'x'*(17*1024*1024)})
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
        prefix='usr/palm/applications/com.cleanyourtv.installer/'
        for kind in ('duplicate','link','oversize'):
            out=io.BytesIO()
            with tarfile.open(fileobj=out,mode='w:gz') as archive:
                member=tarfile.TarInfo(prefix+'appinfo.json');member.size=2;archive.addfile(member,io.BytesIO(b'{}'))
                if kind=='duplicate':archive.addfile(member,io.BytesIO(b'{}'))
                elif kind=='link':
                    member=tarfile.TarInfo(prefix+'link');member.type=tarfile.SYMTYPE;member.linkname='/etc/passwd';archive.addfile(member)
                else:
                    member=tarfile.TarInfo(prefix+'oversize');member.size=17*1024*1024;archive.addfile(member,io.BytesIO(b'x'*member.size))
            raw=package.ar({'debian-binary':b'2.0\n','control.tar.gz':package.tgz({'control':b'Package: com.cleanyourtv.installer\nVersion: 0.0.0\n'}),'data.tar.gz':out.getvalue()})
            with self.subTest(kind=kind),self.assertRaises(ValueError):build.installer_metadata(raw)

if __name__=='__main__':unittest.main()
