"""Installed package data accepts only the platform chain, with strict leaves."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

SOURCE=Path(__file__).parents[1]/'package_data.py'

class PackageDataTests(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('package_data_test',SOURCE)
        self.reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.reader)
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name).resolve()/'apps'
        self.owner='com.cleanyourtv.root.preview'
        self.file=self.root/'usr/palm/applications'/self.owner/'appinfo.json'
        self.file.parent.mkdir(parents=True)
        for directory in (self.root,self.root/'usr',self.root/'usr/palm',self.file.parent.parent):directory.chmod(0o777)
        self.file.parent.chmod(0o755);self.file.write_text(json.dumps({'id':self.owner,'type':'web'}));self.file.chmod(0o644)
        self.metadata=self.root/'usr/palm/packages'/self.owner/'packageinfo.json'
        self.metadata.parent.mkdir(parents=True);self.metadata.parent.chmod(0o755)
        self.metadata.parent.parent.chmod(0o777)
        self.metadata.write_text(json.dumps({'id':self.owner}));self.metadata.chmod(0o644)
    def tearDown(self):self.temp.cleanup()
    def read(self):return self.reader.read(self.file,installed=self.root,uid=os.getuid())
    def test_fixed_shared_chain_accepts_real_0777_with_0755_leaf(self):
        self.assertEqual(json.loads(self.read())['id'],self.owner)
    def test_writable_leaf_file_links_and_foreign_identity_fail(self):
        self.file.parent.chmod(0o777)
        with self.assertRaises(ValueError):self.read()
        self.file.parent.chmod(0o755);self.file.chmod(0o666)
        with self.assertRaises(ValueError):self.read()
        self.file.chmod(0o644);other=self.file.with_name('hardlink');os.link(self.file,other)
        with self.assertRaises(ValueError):self.read()
        other.unlink();self.file.rename(other);self.file.symlink_to(other.name)
        with self.assertRaises((ValueError,OSError)):self.read()
    def test_leaf_replacement_during_read_fails_binding(self):
        original=os.read;switched=[]
        def race(fd,count):
            raw=original(fd,count)
            if not switched:
                switched.append(True);old=self.file.parent.with_name('old');self.file.parent.rename(old)
                self.file.parent.mkdir();self.file.write_text('{"id":"foreign"}')
            return raw
        with patch.object(self.reader.os,'read',side_effect=race):
            with self.assertRaises(ValueError):self.read()
    def test_generic_writable_ancestor_is_rejected(self):
        self.file.parent.parent.chmod(0o755)
        # A directory below the allowlisted package leaf is never a shared exception.
        nested=self.file.parent/'nested';nested.mkdir();nested.chmod(0o777)
        path=nested/'appinfo.json';path.write_text('{}')
        with self.assertRaises(ValueError):self.reader.read(path,installed=self.root,uid=os.getuid())
    def test_symlink_at_each_platform_or_leaf_level_is_rejected(self):
        for directory in (self.root/'usr',self.root/'usr/palm',self.file.parent.parent,self.file.parent):
            old=directory.with_name(directory.name+'-saved');directory.rename(old);directory.symlink_to(old.name,target_is_directory=True)
            try:
                with self.assertRaises((ValueError,OSError)):self.read()
            finally:directory.unlink();old.rename(directory)

    def test_foreign_owner_at_each_boundary_fails(self):
        original=os.fstat
        for attacked in (self.root,self.root/'usr',self.root/'usr/palm',self.file.parent.parent,self.file.parent,self.file):
            inode=attacked.stat().st_ino
            def changed(fd):
                value=original(fd)
                if value.st_ino==inode:
                    parts=list(value);parts[4]=os.getuid()+1;return os.stat_result(parts)
                return value
            with patch.object(self.reader.os,'fstat',side_effect=changed):
                with self.assertRaises(ValueError):self.read()

    def read_as_root(self,path,owners,verified=False):
        # Real fds, modes, inodes and bytes; model only platform ownership on a
        # host that cannot chown fixtures to root or the observed metadata owner.
        import hashlib
        expected=hashlib.sha256(path.read_bytes()).hexdigest() if verified else None
        original_fstat,original_lstat=os.fstat,Path.lstat
        identities={(value.st_dev,value.st_ino):uid
                    for name,uid in owners.items() for value in (original_lstat(name),)}
        def ownership(info):
            values={name:getattr(info,name) for name in dir(info) if name.startswith('st_')}
            values['st_uid']=identities.get((info.st_dev,info.st_ino),0)
            return SimpleNamespace(**values)
        with patch.object(self.reader.os,'fstat',side_effect=lambda fd:ownership(original_fstat(fd))), \
             patch.object(Path,'lstat',lambda path:ownership(original_lstat(path))):
            if verified:return self.reader.read_verified(path,sha256=expected,installed=self.root,uid=0)
            return self.reader.read(path,installed=self.root,uid=0)

    def test_fixed_package_metadata_container_uid501_accepts_strict_root_owned_leaf_and_file(self):
        for owner in (0,501):
            with self.subTest(container_uid=owner):
                raw=self.read_as_root(self.metadata,{self.metadata.parent.parent:owner})
                self.assertEqual(json.loads(raw)['id'],self.owner)

    def test_verified_sdk_containers_accept_any_owner_for_pinned_data(self):
        service=self.root/'usr/palm/services'/(self.owner+'.service')/'service.js'
        service.parent.mkdir(parents=True);service.parent.chmod(0o755)
        service.parent.parent.chmod(0o777);service.write_bytes(b'checked service data');service.chmod(0o644)
        for path in (self.file,self.metadata,service):
            for owner in (501,1001,4242):
                with self.subTest(path=path,owner=owner):
                    owners = dict.fromkeys((self.root,self.root/'usr',self.root/'usr/palm',path.parent.parent),owner)
                    self.assertEqual(self.read_as_root(path,owners,verified=True),path.read_bytes())
                    with self.assertRaises(ValueError):
                        self.read_as_root(path,owners)

    def test_verified_services_container_rejects_symlink(self):
        service=self.root/'usr/palm/services'/(self.owner+'.service')/'service.js'
        service.parent.mkdir(parents=True)
        service.write_bytes(b'checked service data')
        container=service.parent.parent
        saved=container.with_name('services-saved');container.rename(saved);container.symlink_to(saved.name,target_is_directory=True)
        with self.assertRaises((ValueError,OSError)):
            self.read_as_root(service,{saved:501},verified=True)

    def test_verified_data_keeps_owner_checks_outside_shared_sdk_containers(self):
        nested = self.file.parent / 'nested'
        nested.mkdir()
        path = nested / self.file.name
        path.write_bytes(self.file.read_bytes())
        for attacked in (self.root.parent,self.file.parent,nested,path):
            with self.subTest(attacked=attacked),self.assertRaises(ValueError):
                self.read_as_root(path,{attacked:1001},verified=True)

    def test_metadata_uid_exception_rejects_other_owners_and_every_noncontainer_path(self):
        container=self.metadata.parent.parent
        for owner in (500,502,1000):
            with self.subTest(container_uid=owner),self.assertRaises(ValueError):
                self.read_as_root(self.metadata,{container:owner})
        for path in (self.root,self.root/'usr',self.root/'usr/palm',
                     self.file.parent.parent,self.file.parent,self.file,
                     self.metadata.parent,self.metadata):
            target=self.file if path in (self.file.parent.parent,self.file.parent,self.file) else self.metadata
            with self.subTest(foreign_path=path),self.assertRaises(ValueError):
                self.read_as_root(target,{container:501,path:501})

    def test_uid501_metadata_container_does_not_allow_symlinks(self):
        container=self.metadata.parent.parent;old=container.with_name('packages-saved')
        container.rename(old);container.symlink_to(old.name,target_is_directory=True)
        with self.assertRaises((ValueError,OSError)):
            self.read_as_root(self.metadata,{old:501})

    def assert_metadata_replacement_rejected(self,directory):
        original_read=os.read;original=self.metadata.read_bytes();switched=[]
        def replace(fd,count):
            raw=original_read(fd,count)
            if not switched:
                switched.append(True);directory.rename(directory.with_name(directory.name+'-saved'))
                self.metadata.parent.mkdir(parents=True);self.metadata.parent.chmod(0o755)
                self.metadata.write_bytes(original);self.metadata.chmod(0o644)
            return raw
        with patch.object(self.reader.os,'read',side_effect=replace),self.assertRaises(ValueError):
            self.read_as_root(self.metadata,{self.metadata.parent.parent:501})
        self.assertTrue(switched,'the metadata read reached the replacement race')

    def test_uid501_metadata_container_replacement_is_detected(self):
        self.assert_metadata_replacement_rejected(self.metadata.parent.parent)

    def test_uid501_metadata_own_leaf_replacement_is_detected(self):
        self.assert_metadata_replacement_rejected(self.metadata.parent)

    def test_verified_data_accepts_complete_0777_sdk_tree_and_checks_digest(self):
        import hashlib
        for path in (self.file.parent,self.file,self.metadata.parent,self.metadata):path.chmod(0o777)
        for path in (self.file,self.metadata):
            raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
            self.assertEqual(self.reader.read_verified(path,sha256=digest,installed=self.root,uid=os.getuid()),raw)
            with self.assertRaises(ValueError):self.reader.read_verified(path,sha256='0'*64,installed=self.root,uid=os.getuid())
        with self.assertRaises(ValueError):self.read()

    def test_verified_data_refuses_unpinned_private_special_bits_and_hardlinks(self):
        import hashlib
        digest=hashlib.sha256(self.file.read_bytes()).hexdigest()
        for invalid in (None,'','A'*64,'0'*63):
            with self.assertRaises(ValueError):self.reader.read_verified(self.file,sha256=invalid,installed=self.root,uid=os.getuid())
        private=self.root.parent/'private.json';private.write_bytes(self.file.read_bytes());private.chmod(0o777)
        with self.assertRaises(ValueError):self.reader.read_verified(private,sha256=digest,installed=self.root,uid=os.getuid())
        original=os.fstat;inode=self.file.stat().st_ino
        def special(fd):
            info=original(fd)
            values={name:getattr(info,name) for name in dir(info) if name.startswith('st_')}
            if info.st_ino==inode:values['st_mode']|=0o4000
            return SimpleNamespace(**values)
        with patch.object(self.reader.os,'fstat',side_effect=special),self.assertRaises(ValueError):
            self.reader.read_verified(self.file,sha256=digest,installed=self.root,uid=os.getuid())
        self.file.chmod(0o777);os.link(self.file,self.file.with_name('hard'))
        with self.assertRaises(ValueError):self.reader.read_verified(self.file,sha256=digest,installed=self.root,uid=os.getuid())

    def test_verified_uid501_container_with_full_0777_and_same_byte_replacement(self):
        import hashlib
        self.metadata.parent.chmod(0o777);self.metadata.chmod(0o777)
        self.assertEqual(json.loads(self.read_as_root(self.metadata,{self.metadata.parent.parent:501},verified=True))['id'],self.owner)
        original=self.metadata.read_bytes();expected=hashlib.sha256(original).hexdigest();read=os.read;switched=[]
        def replace(fd,count):
            raw=read(fd,count)
            if not switched:
                switched.append(True);old=self.metadata.parent.with_name('old');self.metadata.parent.rename(old)
                self.metadata.parent.mkdir();self.metadata.parent.chmod(0o777);self.metadata.write_bytes(original);self.metadata.chmod(0o777)
            return raw
        with patch.object(self.reader.os,'read',side_effect=replace),self.assertRaises(ValueError):
            self.reader.read_verified(self.metadata,sha256=expected,installed=self.root,uid=os.getuid())
        self.assertTrue(switched)

    def test_sticky_shared_ancestor_is_data_but_own_sticky_leaf_is_refused(self):
        import hashlib
        ancestor=self.root.parent;ancestor.chmod(0o1777)
        self.assertTrue(ancestor.stat().st_mode&0o1000)
        expected=hashlib.sha256(self.file.read_bytes()).hexdigest()
        self.assertEqual(self.read(),self.file.read_bytes())
        self.assertEqual(self.reader.read_verified(self.file,sha256=expected,installed=self.root,uid=os.getuid()),self.file.read_bytes())
        self.file.parent.chmod(0o1755)
        for reader in (self.read,lambda:self.reader.read_verified(self.file,sha256=expected,installed=self.root,uid=os.getuid())):
            with self.assertRaises(ValueError):reader()
        self.file.parent.chmod(0o755)
        import python_binding
        with patch.object(python_binding,'EXPECTED_UID',os.getuid()),self.assertRaises(ValueError):python_binding._read(self.file)

    def test_shared_setid_bits_are_refused_even_with_sticky(self):
        import hashlib
        ancestor=self.root.parent;ancestor.chmod(0o1777);inode=ancestor.stat().st_ino;original=os.fstat
        expected=hashlib.sha256(self.file.read_bytes()).hexdigest()
        for bit in (0o2000,0o4000):
            def setid(fd):
                info=original(fd);values={name:getattr(info,name) for name in dir(info) if name.startswith('st_')}
                if info.st_ino==inode:values['st_mode']|=bit
                return SimpleNamespace(**values)
            with patch.object(self.reader.os,'fstat',side_effect=setid):
                with self.assertRaises(ValueError):self.read()
                with self.assertRaises(ValueError):self.reader.read_verified(self.file,sha256=expected,installed=self.root,uid=os.getuid())
