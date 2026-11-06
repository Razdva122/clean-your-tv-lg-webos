import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cytv.state import Store, target
from cytv.errors import UserError


class CapsuleTests(unittest.TestCase):
    @unittest.skipUnless(os.name=='posix','Android private application storage is POSIX')
    def test_android_capsule_reuses_verified_application_anchor(self):
        from tests.cytv import test_python_runtime
        fixture=test_python_runtime.RuntimeTests()
        store=Store('/unused');profile=target('test-tv','no-root')
        for alias in (False,True):
            with self.subTest(alias=alias):
                directory,records,java=fixture.android_cache_fixture(alias)
                with patch.dict(os.sys.modules,{'java':java}), patch('os.getuid',return_value=10123), patch('os.getgid',return_value=10123), \
                     patch.object(Path,'lstat',lambda path:records[str(path)]), patch.object(Path,'readlink',return_value=Path('/data/data')), \
                     patch.object(store,'device_dir',return_value=Path(directory)):
                    path=store._capsule_path(profile,'a'*32)
                expected=directory.replace('/data/user/0','/data/data') if alias else directory
                self.assertEqual(str(path),expected+'/capsule-'+'a'*32+'.json')

    def test_original_bytes_survive_restart_and_changed_capsule_is_refused(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root).resolve()
            store = Store(root)
            profile = target('test-tv', 'no-root')
            store.begin(profile, 'install')
            operation = 'a'*32
            value = {'plan': {'operation': operation}, 'files': {'ssap-key.json': 'original-private-key'}}
            digest = store.save_capsule(profile, operation, value)
            pending = store.pending(profile)
            self.assertEqual(Store(root).read_capsule(profile, operation, digest), value)
            path = store.device_dir(profile) / ('capsule-'+operation+'.json')
            if os.name!='nt':self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises((FileExistsError, UserError)):
                store.save_capsule(profile, operation, {'replacement': True})
            path.write_text('{}')
            with self.assertRaises(UserError):
                store.read_capsule(profile, operation, digest)
            self.assertEqual(store.pending(profile), pending)

    def test_capsule_links_and_unbound_paths_are_refused(self):
        with tempfile.TemporaryDirectory() as root:
            store=Store(Path(root).resolve()); profile=target('test-tv','no-root'); operation='b'*32
            digest=store.save_capsule(profile,operation,{'original':True})
            path=store.device_dir(profile)/('capsule-'+operation+'.json')
            os.link(path, path.with_suffix('.link'))
            with self.assertRaises(UserError): store.read_capsule(profile,operation,digest)
            with self.assertRaises(UserError): store.read_capsule(profile,'../other',digest)
