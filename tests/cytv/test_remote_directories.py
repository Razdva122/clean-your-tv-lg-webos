"""Real host upload methods must create TV POSIX parents on every host OS."""
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import shlex
import tempfile
import unittest
from unittest.mock import patch
from cytv import operations, state


class RemoteTree:
    def __init__(self):
        self.directories={'/','/tmp'};self.uploads=set();self.stage=None
    def run(self,command,**kwargs):
        if command.startswith('umask 077; mkdir '):
            directory=shlex.split(command)[-1];self.stage=directory
        elif command.startswith('mkdir -p '):directory=shlex.split(command)[-1]
        elif 'CYTV_SYSTEM_ROOT_READY' in command:return 'CYTV_SYSTEM_ROOT_READY'
        elif 'CYTV_PYTHON_READY' in command:return 'CYTV_PYTHON_READY'
        elif 'setup-system-updater.py' in command:return '{"installed":true}'
        else:raise AssertionError('Unexpected device command')
        if '\\' in directory:raise AssertionError('Windows separators in TV mkdir: '+directory)
        self.directories.add(directory)
        self.directories.update(str(p) for p in PurePosixPath(directory).parents)
        return ''
    def upload(self,target,raw,mode=0o600):
        if str(PurePosixPath(target).parent) not in self.directories:
            raise AssertionError('TV upload parent missing: '+target)
        self.uploads.add(str(PurePosixPath(target).relative_to(self.stage)))


def bundle(folder,files,**metadata):
    for name,raw in files.items():
        target=folder/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    (folder/'bundle.json').write_text(json.dumps(dict(metadata,files={name:hashlib.sha256(raw).hexdigest() for name,raw in files.items()})))


class RemoteDirectoryTests(unittest.TestCase):
    def test_all_three_upload_routes_use_posix_parents_on_windows_and_posix(self):
        with tempfile.TemporaryDirectory() as temporary:
            payload=Path(temporary).resolve()
            bundle(payload/'root',{'deploy.py':b'# deploy','runtime/native/helper':b'helper'})
            bundle(payload/'root-updater',{'install_driver.py':b'# driver','system_updater/support/core.py':b'# core','root-updater.ipk':b'ipk'})
            bundle(payload/'system-updater',{'setup-system-updater.py':b'# setup','system-updater.ipk':b'ipk','system_updater/support/core.py':b'# core'},schema=1,supervisor=1)
            expected={
                'coordinator_code':{'install_driver.py','system_updater/support/core.py','bundle.json'},
                'upload_product':{'root/deploy.py','root/runtime/native/helper','root/bundle.json','root-updater/install_driver.py','root-updater/system_updater/support/core.py','root-updater/root-updater.ipk','root-updater/bundle.json'},
                'enable_system_updates':{'setup-system-updater.py','system-updater.ipk','system_updater/support/core.py','bundle.json'},
            }
            for flavor in (PurePosixPath,PureWindowsPath):
                for method,wanted in expected.items():
                    with self.subTest(host=flavor.__name__,method=method):
                        remote=RemoteTree();store=state.Store(payload/'host');profile=state.target('fixture.local','root')
                        installer=operations.Installer(remote,store,profile,payload,{},lambda *_:None)
                        installer._selected_python='/usr/bin/python3'
                        # Local payload paths are already real. Adapt only the
                        # host Path symbol used by remote-parent expressions.
                        with patch.object(operations,'Path',flavor):
                            args=(payload/'root',) if method=='upload_product' else ()
                            getattr(installer,method)(*args)
                        self.assertEqual(remote.uploads,wanted)
                        self.assertIsNone(store.pending(profile))


if __name__=='__main__':unittest.main()
