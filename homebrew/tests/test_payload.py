import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from homebrew.payload import checked_bundle, validate_runtime
from cytv import python_runtime
from cytv.errors import UserError
from homebrew.build import build_payload
from cytv import package

class PayloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root/'code.py').write_bytes(b'pass\n')
        self.manifest = {'files': {'code.py': hashlib.sha256(b'pass\n').hexdigest()}}
        self.save()
    def save(self):
        (self.root/'bundle.json').write_text(json.dumps(self.manifest))
    def test_exact_bundle(self):
        self.assertEqual(set(checked_bundle(self.root)), {'code.py', 'bundle.json'})
    def test_missing_extra_hash_and_link(self):
        for change in ('missing', 'extra', 'hash', 'link'):
            with self.subTest(change=change):
                p=self.root/'code.py'
                if p.exists() or p.is_symlink(): p.unlink()
                p.write_bytes(b'pass\n')
                if change=='missing': p.unlink()
                if change=='extra': (self.root/'extra').write_bytes(b'x')
                if change=='hash': p.write_bytes(b'wrong')
                if change=='link': p.unlink();p.symlink_to('bundle.json')
                with self.assertRaises(ValueError): checked_bundle(self.root)
                if (self.root/'extra').exists(): (self.root/'extra').unlink()
    def test_unsafe_name(self):
        self.manifest['files']['../outside']='0'*64;self.save()
        with self.assertRaises(ValueError): checked_bundle(self.root)
    def test_invalid_runtime_binding_and_duplicate(self):
        for names in (['bin/python3.13'], ['bin/python3.13', 'bin/python3.13']):
            archive=self.root/'runtime.tar.gz'
            with tarfile.open(archive, 'w:gz') as tar:
                for name in names:
                    item=tarfile.TarInfo(name);item.size=1;item.mode=0o755;tar.addfile(item,io.BytesIO(b'x'))
            with self.assertRaises(ValueError): validate_runtime(archive, {'schema':1,'archive_sha256':'bad','files':{}})

class RuntimeArchiveTests(unittest.TestCase):
    def archive(self, duplicate=False, link=False, unsafe=False):
        raw=io.BytesIO()
        with tarfile.open(fileobj=raw,mode='w:gz') as tar:
            for name,content in [('python/bin/python3.13',b'executable'),('python/LICENSE',b'Python license')]:
                member=tarfile.TarInfo(name);member.mode=0o755;member.size=len(content);tar.addfile(member,io.BytesIO(content))
                if duplicate: tar.addfile(member,io.BytesIO(content))
            if link:
                member=tarfile.TarInfo('python/escape');member.type=tarfile.SYMTYPE;member.linkname='/outside';tar.addfile(member)
            if unsafe:
                member=tarfile.TarInfo('python/../outside');tar.addfile(member,io.BytesIO(b''))
        return raw.getvalue()
    def test_normalizer_rejects_duplicate_unsafe_and_escaping_link(self):
        with tempfile.TemporaryDirectory() as temp:
            for kwargs in ({'duplicate':True},{'link':True},{'unsafe':True}):
                with self.subTest(kwargs=kwargs), self.assertRaises(UserError): python_runtime.normalize_to_file(self.archive(**kwargs),Path(temp)/'out')
    def test_normalized_binding_missing_extra_hash_and_duplicate(self):
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/'runtime.tar.gz';binding=python_runtime.normalize_to_file(self.archive(),output)
            records=validate_runtime(output,binding)
            self.assertIn('bin/python3.13',records)
            for change in ('missing','extra','hash','duplicate','link','unsafe'):
                altered=Path(temp)/'altered.tar.gz'
                with tarfile.open(output,'r:gz') as source, tarfile.open(altered,'w:gz') as dest:
                    for member in source:
                        if change=='missing' and member.name=='LICENSE': continue
                        data=source.extractfile(member).read() if member.isfile() else None
                        if change=='hash' and member.name=='LICENSE': data=b'x'*member.size
                        dest.addfile(member,io.BytesIO(data) if data is not None else None)
                        if change=='duplicate': dest.addfile(member,io.BytesIO(data) if data is not None else None)
                    if change in ('extra','link','unsafe'):
                        member=tarfile.TarInfo('../escape' if change=='unsafe' else 'unexpected')
                        if change=='link': member.type=tarfile.SYMTYPE;member.linkname='LICENSE'
                        dest.addfile(member)
                with self.subTest(change=change), self.assertRaises(ValueError): validate_runtime(altered,binding)
    def test_bare_normalized_archive_is_not_trusted_source(self):
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/'normalized.tar.gz';python_runtime.normalize_to_file(self.archive(),output)
            with self.assertRaises(UserError): python_runtime._verified_bytes(output)
    def test_mismatched_component_baseline(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();inputs=[]
            identities=('com.cleanyourtv.root.preview','com.cleanyourtv.root.updater','com.cleanyourtv.system.updater')
            for index,identity in enumerate(identities):
                folder=root/str(index);folder.mkdir();inputs.append(folder)
                info = {'id': identity, 'version': '0.1.0'}
                if index == 0:
                    info.update(cytvProductGeneration=2, visible=False)
                raw=package.ipk(identity,'0.1.0',{'usr/palm/applications/'+identity+'/appinfo.json':json.dumps(info).encode()})
                files={'component.ipk':raw}
                for name in ('installation.py','observed_install.py','installer_status.py','startup_hook.py','package_data.py','package_identity.py','startup_guard.py','python_binding.py','python_boot.js'): files[name]=b'same'
                for name,data in files.items(): (folder/name).write_bytes(data)
                (folder/'bundle.json').write_text(json.dumps({'files':{n:hashlib.sha256(b).hexdigest() for n,b in files.items()}}))
            for name in ('python_binding.py','package_data.py','package_identity.py','startup_guard.py'):
                (inputs[1]/name).write_bytes(b'different')
                manifest=json.loads((inputs[1]/'bundle.json').read_text());manifest['files'][name]=hashlib.sha256(b'different').hexdigest();(inputs[1]/'bundle.json').write_text(json.dumps(manifest))
                with self.subTest(name=name),self.assertRaisesRegex(ValueError,'Mismatched component baseline'):build_payload(*inputs,root/'absent-runtime',root/'output')
                (inputs[1]/name).write_bytes(b'same');manifest['files'][name]=hashlib.sha256(b'same').hexdigest();(inputs[1]/'bundle.json').write_text(json.dumps(manifest))

if __name__=='__main__': unittest.main()
