"""Root uses the same live kernel fence, without taking over No-root state."""
import json
import hashlib
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from cytv import no_root_gate as gate
from cytv import package


class RootHelperFence(unittest.TestCase):
    def test_prepared_owner_blocks_new_install_until_explicit_verified_finish(self):
        self.assertTrue(hasattr(gate,'fence_root_helper'),'Root lifecycle adapter is missing')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();base=root/'apps';base.mkdir()
            for suffix in ('applications/com.local.nativehome','services/com.local.nativehome.service'):
                state=base/suffix/'state';state.mkdir(parents=True,mode=0o770)
                os.chown(state,-1,os.getgid())
                marker=state/'installer-generation';marker.write_text('a'*32);marker.chmod(0o640);os.chown(marker,-1,os.getgid())
            fence=root/'fence';fence.mkdir(mode=0o750);os.chown(fence,-1,os.getgid())
            binary=root/'gate'
            repo=Path(__file__).resolve().parents[2]
            subprocess.run(['cc',str(repo/'native/installer/lifecycle-gate.c'),'-o',str(binary)],check=True)
            pending={'removal_operation':'b'*32}
            class Remote:
                def run(self,command,**kwargs):
                    args=shlex.split(command)
                    args=[shutil.which('node') if part=='/usr/bin/node' else shutil.which('true') if part=='/bin/true' else part for part in args]
                    result=subprocess.run(args,capture_output=True,timeout=5)
                    if result.returncode:raise RuntimeError(result.stderr.decode())
                    return result.stdout.decode()
            files={}
            for name in ('applications/com.local.nativehome/detach','applications/com.local.nativehome/relay',
                         'applications/com.local.nativehome/native.js','applications/com.local.nativehome/installer-lifecycle.js',
                         'services/com.local.nativehome.service/service.js','services/com.local.nativehome.service/service-removal.js'):
                (base/name).write_bytes(b'authenticated fixture runtime');files['usr/palm/'+name]=(base/name).read_bytes()
            payload=root/'payload';payload.mkdir();raw=package.ipk('com.local.nativehome','0.8.0',files,architecture='arm')
            (payload/'helper.ipk').write_bytes(raw)
            installer=SimpleNamespace(remote=Remote(),profile={},store=SimpleNamespace(pending=lambda p:pending),
                payload=payload,manifest={'helper':'helper.ipk','files':{'helper.ipk':hashlib.sha256(raw).hexdigest()}})
            sender=root/'sender'
            sender.write_text('#!/usr/bin/env python3\nimport json,sys,os\nos.fstat(3)\nr=json.loads(sys.argv[-1]);r.update(returnValue=True,quiescent=True);print(json.dumps(r))\n')
            sender.chmod(0o700)
            with patch.object(gate,'FENCE',str(fence)),patch.object(gate,'HELPER_BASE',str(base)),patch.object(gate,'SENDER',str(sender)):
                proof=gate.fence_root_helper(installer,pending,str(binary))
                self.assertEqual(proof['mode'],'managed')
                self.assertEqual(proof['generation'],'a'*32)
                self.assertEqual((fence/'removal-owner').read_text(),'b'*32)
                blocked=subprocess.run([str(binary),str(fence),'c'*32,'run',shutil.which('true')],capture_output=True)
                self.assertEqual(blocked.returncode,73)
                gate.complete_root_helper_fence(installer,pending,proof)
                self.assertEqual(proof['native_drained'],True)
                gate.finish_root_helper(installer,pending,proof,verified_absent=True)
                self.assertFalse((fence/'removal-owner').exists())
                (base/'applications/com.local.nativehome/detach').write_bytes(b'old unfenced executable')
                self.assertEqual(gate.fence_root_helper(installer,pending,str(binary))['mode'],'unmanaged')
