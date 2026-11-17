import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from updater.package import inspect_package, verify_payload


class PackageTests(unittest.TestCase):
    def test_generic_package_admission_does_not_change_companion_parent_authority(self):
        from unittest.mock import patch
        from updater import package
        foreign = 'usr/palm/applications/com.cleanyourtv.root.updater/'
        with patch.object(package, 'PREFIX', foreign):
            self.assertIsNone(package.companion_files({}))
            self.assertIsNone(package.companion_files({}, 'usr/palm/applications/com.gathin.tvhome/'))
            with self.assertRaisesRegex(ValueError, 'Foreign companion parent'):
                package.companion_files({}, foreign)

    def package(self, files):
        spec = importlib.util.spec_from_file_location('root_update_builder', ROOT/'build.py')
        builder = importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)
        return builder.ar({'debian-binary': b'2.0\n', 'control.tar.gz': builder.tgz({'control': b'Package: com.cleanyourtv.root.preview\nVersion: 0.1.0\n'}), 'data.tar.gz': builder.tgz(files)})

    def files(self):
        return {'usr/palm/applications/com.cleanyourtv.root.preview/appinfo.json': json.dumps({'id': 'com.cleanyourtv.root.preview', 'version': '0.1.0', 'type': 'web', 'main': 'index.html'}).encode(),
                'usr/palm/applications/com.cleanyourtv.root.preview/index.html': b'<html></html>',
                'usr/palm/packages/com.cleanyourtv.root.preview/packageinfo.json': json.dumps({'id':'com.cleanyourtv.root.preview','version':'0.1.0','app':'com.cleanyourtv.root.preview','services':[]}).encode()}

    def manifest(self, raw):
        return {'version':'0.1.0','sha256':hashlib.sha256(raw).hexdigest(),'size':len(raw)}

    def test_new_package_emits_secure_owned_leaves_only(self):
        raw=self.package(self.files())
        from updater.package import members
        with tarfile.open(fileobj=io.BytesIO(members(raw)['data.tar.gz'])) as archive:
            dirs={entry.name:entry for entry in archive if entry.isdir()}
        self.assertIn('usr/palm/applications/com.cleanyourtv.root.preview',dirs)
        self.assertIn('usr/palm/packages/com.cleanyourtv.root.preview',dirs)
        self.assertNotIn('usr/palm/applications',dirs)
        self.assertTrue(all(entry.mode==0o755 and entry.uid==0 for entry in dirs.values()))

    def test_checks_content_identity_and_installed_bytes(self):
        files=self.files(); raw=self.package(files); hashes=inspect_package(raw,self.manifest(raw))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve()
            for name,data in files.items():
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
            verify_payload(root,hashes,uid=os.getuid())
            (root/next(iter(files))).write_text('{}')
            with self.assertRaises(ValueError):verify_payload(root,hashes,uid=os.getuid())

    def test_rejects_foreign_payload_wrong_identity_and_hash(self):
        for extra in ({'etc/cron.d/unsafe':b'bad'}, {'usr/palm/applications/com.gathin.tvhome/index.html':b'bad'}):
            raw=self.package({**self.files(),**extra})
            with self.assertRaises(ValueError):inspect_package(raw,self.manifest(raw))
        files=self.files();files[next(iter(files))]=b'{"id":"wrong","version":"0.1.0"}';raw=self.package(files)
        with self.assertRaises(ValueError):inspect_package(raw,self.manifest(raw))
        raw=self.package(self.files())
        with self.assertRaises(ValueError):inspect_package(raw,{**self.manifest(raw),'sha256':'a'*64})

    def test_rejects_duplicate_ar_entries(self):
        raw=self.package(self.files());part=raw[8:]
        with self.assertRaises(ValueError):inspect_package(raw+part,self.manifest(raw+part))

    def test_installed_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();p=root/'file';p.symlink_to('/etc/hosts')
            with self.assertRaises(ValueError):verify_payload(root,{'file':'a'*64})


if __name__=='__main__':unittest.main()
