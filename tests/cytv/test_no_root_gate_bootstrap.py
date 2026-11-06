"""Execute the actual Node bootstrap against private/shared local directories."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


class GateBootstrap(unittest.TestCase):
    def test_operation_generation_is_packaged_before_any_runtime_can_start(self):
        from cytv import no_root_gate as gate, package
        self.assertTrue(hasattr(gate, 'bind_artifacts'), 'package generations are not bound')
        import io,tarfile
        app='com.local.nativehome'
        raw=package.ipk(app,'0.8.0',{'usr/palm/applications/'+app+'/appinfo.json':b'{"id":"com.local.nativehome"}'},architecture='arm')
        bound=gate.bind_artifacts({'helper.ipk':raw},'a'*32)['helper.ipk']
        self.assertEqual(package.read_ar(bound)['control.tar.gz'],package.read_ar(raw)['control.tar.gz'])
        with tarfile.open(fileobj=io.BytesIO(package.read_ar(bound)['data.tar.gz'])) as archive:
            for path in ('applications/'+app,'services/'+app+'.service'):
                entry=archive.getmember('usr/palm/'+path+'/state/installer-generation')
                self.assertEqual((entry.uid,entry.gid,entry.mode),(5999,5000,0o640))
                self.assertEqual(archive.extractfile(entry).read(),b'a'*32)
        with self.assertRaises(ValueError):gate.bind_artifacts({'helper.ipk':bound},'b'*32)

    def test_bootstrap_keeps_shared_fence_nonsecret_and_never_replaces_code(self):
        source = Path(__file__).resolve().parents[2] / 'cytv/no_root_gate.py'
        self.assertTrue(source.exists(), 'native gate bootstrap is not implemented')
        spec=importlib.util.spec_from_file_location('cytv.no_root_gate',source)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory(dir='/private/tmp' if sys.platform=='darwin' else '/tmp') as directory:
            root=Path(directory); private=root/'private'; fence=root/'fence'
            import base64,hashlib
            raw=b'\x7fELFfixture';digest=hashlib.sha256(raw).hexdigest()
            args={'private':str(private),'fence':str(fence),'sha256':digest,'binary':base64.b64encode(raw).decode()}
            def run():return subprocess.run([shutil.which('node'),'-e',module.BOOTSTRAP,json.dumps(args)],capture_output=True)
            result=run();self.assertEqual(result.returncode,0,result.stderr)
            binary=private/('gate-'+digest)
            self.assertEqual(binary.read_bytes(),raw);self.assertEqual(binary.stat().st_mode&0o777,0o700)
            self.assertEqual(fence.stat().st_mode&0o777,0o750)
            self.assertEqual(list(fence.iterdir()),[])
            inode=binary.stat().st_ino
            self.assertEqual(run().returncode,0);self.assertEqual(binary.stat().st_ino,inode)
            binary.write_bytes(b'changed')
            self.assertNotEqual(run().returncode,0);self.assertEqual(binary.read_bytes(),b'changed')

    def test_bootstrap_does_not_follow_substituted_directory(self):
        source = Path(__file__).resolve().parents[2] / 'cytv/no_root_gate.py'
        self.assertTrue(source.exists(), 'native gate bootstrap is not implemented')
        spec=importlib.util.spec_from_file_location('cytv.no_root_gate',source)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory(dir='/private/tmp' if sys.platform=='darwin' else '/tmp') as directory:
            import base64,hashlib
            root=Path(directory); foreign=root/'foreign';foreign.mkdir();(root/'private').symlink_to(foreign)
            raw=b'\x7fELFfixture'
            args={'private':str(root/'private'),'fence':str(root/'fence'),'sha256':hashlib.sha256(raw).hexdigest(),'binary':base64.b64encode(raw).decode()}
            result=subprocess.run([shutil.which('node'),'-e',module.BOOTSTRAP,json.dumps(args)],capture_output=True)
            self.assertNotEqual(result.returncode,0);self.assertEqual(list(foreign.iterdir()),[])
