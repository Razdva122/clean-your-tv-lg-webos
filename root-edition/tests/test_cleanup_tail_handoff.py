"""Opt-in fixed-path kernel integration, ONLY inside a disposable Linux container.

The controller supplies the compiled current native gate and exact Node 8. No
TV, network or host paths are used. Ordinary development runs skip this module.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from test_cleanup_tail import HARNESS, ID, RUNTIME, SOURCE, STATE, packages


@unittest.skipUnless(sys.platform=='linux' and os.environ.get('CYTV_DISPOSABLE_ROOT_FIXTURE')=='1',
                     'fixed paths require explicit disposable Linux root fixture')
class CleanupTailHandoff(unittest.TestCase):
    def test_original_three_locks_failure_then_native_gate_node_only_reconnect(self):
        self.handoff(False)

    def handoff(self, helper):
        self.assertEqual(os.getuid(),0)
        gate=os.environ['CYTV_ROOT_GATE'];node=os.environ['NODE8']
        state=Path(STATE);base=Path(RUNTIME).parent;runtime=Path(RUNTIME)
        self.assertFalse(state.exists());self.assertFalse(base.exists())
        state.mkdir(mode=0o700,parents=True);base.mkdir(mode=0o755,parents=True)
        self.addCleanup(shutil.rmtree,state);self.addCleanup(shutil.rmtree,base)
        runtime.mkdir(mode=0o700);(runtime/'bin').mkdir();(runtime/'lib').mkdir()
        for name in ('bin/python3.13','lib/secret.py'):(runtime/name).write_text('owned '+name)
        files={str(p.relative_to(runtime)):hashlib.sha256(p.read_bytes()).hexdigest() for p in runtime.rglob('*') if p.is_file()}
        record=dict(schema=1,protocol='clean-removal-v1',operation=ID,removal='d'*32,lease='b'*32,stage='private-cleanup',state='recovery_required',cleanup_boot_id='11111111-1111-1111-1111-111111111111',cleanup_verified_boot_id='22222222-2222-2222-2222-222222222222',
            routes=['third.party.home']*3,support_stages=[],packages=packages(),runtime_cleanup=dict(root=RUNTIME,files=files),
            done=['original-writers-fenced','controls-restored','package-removal','private-cleanup'],
            result=dict(removed=True,applications_services_startup_removed=True,private_cleanup_verified=False))
        for name,value in (('clean-removal-'+ID+'.json',record),('operation.json',
                dict(schema=1,id='b'*32,owner='clean-removal',journal='product-'+ID+'.json',terminal=False,stage='private-cleanup'))):
            (state/name).write_text(json.dumps(value));(state/name).chmod(0o600)
        paths=(state/'worker.lock',state/'ownership.lock',base/'.install.lock')
        descriptors=[]
        for path in paths:
            fd=os.open(path,os.O_RDWR|os.O_CREAT|os.O_EXCL,0o600);descriptors.append(fd);fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        inodes=[p.stat().st_ino for p in paths]
        with tempfile.TemporaryDirectory() as temporary:
            harness=Path(temporary)/'harness.js';harness.write_text(HARNESS)
            # Harness uses the real /proc FD namespace; fixed TV RPCs alone are
            # bounded fixture replies. The gate/Ownership files are REAL paths.
            env={**os.environ,'CYTV_REAL_PROC_FD':'1','OWNERSHIP_FD':str(descriptors[1]),
                 'PROMOTION_FD':str(descriptors[2]),'WORKER_FD':str(descriptors[0]),'FAIL_MEMBER':'secret.py',
                 'MUTATION_LOG':str(Path(temporary)/'mutations.json')}
            try:
                blocked=subprocess.run([gate,'root-clean-lock',node,'-e','process.exit(99)'],capture_output=True,timeout=10)
                self.assertEqual(blocked.returncode,75,blocked.stderr)
                first=subprocess.run([node,str(harness),'/',str(SOURCE)],env=env,pass_fds=tuple(descriptors),capture_output=True,text=True,timeout=20)
                self.assertEqual(json.loads(first.stdout)['reason'],'private-cleanup-incomplete',first.stderr)
                self.assertFalse((runtime/'bin/python3.13').exists())
                self.assertTrue((runtime/'lib/secret.py').exists())
            finally:
                for fd in descriptors:os.close(fd)
            # No Python in the deleted runtime is needed to regain all original
            # inodes and finish exactly the remaining cleanup with current JS.
            env.pop('FAIL_MEMBER');env.update(OWNERSHIP_FD='3',PROMOTION_FD='4',WORKER_FD='5')
            command=[gate,'root-clean-lock',node,str(harness),'/',str(SOURCE)]
            second=subprocess.run(command,env=env,capture_output=True,text=True,timeout=20)
            self.assertEqual(second.returncode,0,second.stderr)
            self.assertTrue(json.loads(second.stdout)['result']['private_cleanup_verified'])
            self.assertFalse(runtime.exists());self.assertEqual([p.stat().st_ino for p in paths],inodes)
            again=subprocess.run(command,env=env,capture_output=True,text=True,timeout=20)
            self.assertEqual(again.returncode,0,again.stderr)
            remaining=json.loads(Path(env['MUTATION_LOG']).read_text())
            self.assertEqual(remaining, [])
