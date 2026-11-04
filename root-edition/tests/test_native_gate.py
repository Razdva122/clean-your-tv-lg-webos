"""Real native parser/process tests; fake mounts exist only at compile time."""
import json
try:
 import fcntl
except ImportError:
 fcntl = None
import threading
import os
from pathlib import Path
import select
import shutil
import signal
import subprocess
import tempfile
import time
import unittest
ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'root-edition/gate/gate.c'
FIXTURE = ROOT / 'root-edition/tests/native_gate_fixture.h'
TOKEN='a'*32
BOOT='01234567-89ab-cdef-0123-456789abcdef'

@unittest.skipUnless(os.name == 'posix' and shutil.which('cc'), 'POSIX C compiler required')
class NativeGateTests(unittest.TestCase):
 def setUp(self):
  if hasattr(self,'guards'): self.tearDown()
  assert SOURCE.is_file(), 'native independent helper is missing'
  self.tmp=tempfile.TemporaryDirectory(prefix='cytv-native-')
  self.root=Path(self.tmp.name).resolve()
  self.binary=self.root/'helper'
  subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-DCYTV_GATE_FIXTURE',f'-DFIXTURE_ROOT="{self.root}"','-I',str(FIXTURE.parent),str(SOURCE),'-o',str(self.binary)],check=True,capture_output=True)
  for p in self.root.iterdir():
   if p==self.binary:continue
   if p.is_dir():shutil.rmtree(p)
   else:p.unlink()
  for d in ['state','volatile']: (self.root/d).mkdir(mode=0o700)
  (self.root/'home').write_bytes(b'original executable')
  os.chmod(self.root/'home',0o700)
  shutil.copy2(self.binary,self.root/'volatile/gate')
  (self.root/'boot').write_text(BOOT+'\n')
  (self.root/'mountinfo').write_text('1 0 0:1 / / rw - fixture fixture rw\n')
  (self.root/'luna').write_text('#!/bin/sh\nprintf \'%s\\n\' "$*" >> "'+str(self.root/'calls')+'"\nprintf \'{"returnValue":true}\\n\'\n')
  os.chmod(self.root/'luna',0o700)
  self.config()
  self.guards=[]
 def tearDown(self):
  for p,w in self.guards:
   try:os.close(w)
   except OSError:pass
   if p.poll() is None:p.terminate()
   try:p.communicate(timeout=5)
   except subprocess.TimeoutExpired:p.kill();p.communicate()
  self.guards=[]
  # Detached stock requests are bounded; distinct compile-time roots isolate them.
  self.tmp.cleanup()
 def config(self,extra=''):
  s=(self.root/'home').stat()
  p=self.root/'state/config'
  p.write_text(f'CYTV-C1-GATE-1\ntoken {TOKEN}\nboot {BOOT}\ndev {s.st_dev}\nino {s.st_ino}\nsize {s.st_size}\nmtime_ns {s.st_mtime_ns}\n'+extra)
  p.chmod(0o600)
 def run_gate(self,*args,timeout=5):
  p=subprocess.run([str(self.binary),*args],capture_output=True,text=True,timeout=timeout)
  return json.loads(p.stdout),p.returncode
 def guard(self,seconds=0,ready=True,token=TOKEN):
  r,w=os.pipe();ar,aw=os.pipe()
  p=subprocess.Popen([str(self.binary),'--guard',token,str(r),str(aw),str(seconds)],pass_fds=(r,aw),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  os.close(r);os.close(aw);self.guards.append((p,w))
  if ready:os.write(w,b'READY\n')
  if ready:
   self.assertTrue(select.select([ar],[],[],3)[0], 'guardian readiness timed out')
   ack=os.read(ar,128)
   self.assertEqual(ack,('ARMED '+token+'\n').encode(),p.communicate(timeout=4) if not ack else '')
  os.close(ar)
  return p,w
 def finish(self,p,w,line=b'ESCAPE\n'):
  os.write(w,line)
  out,err=p.communicate(timeout=5)
  self.assertEqual(err,'')
  return json.loads(out)
 def test_selfcheck(self): self.assertTrue(self.run_gate('--selfcheck')[0]['returnValue'])
 def test_clean_status_and_config_rejection(self):
  s,rc=self.run_gate('--status');self.assertEqual(rc,0);self.assertTrue(s['stock_verified']);self.assertIsNone(s['profiles'])
  for bad in ['extra x\n','\n','\x00']:
   self.config(bad);s,rc=self.run_gate('--status');self.assertNotEqual(rc,0);self.assertEqual(s['reason'],'config_invalid')
 def test_config_boundaries_permissions_and_identity(self):
  p=self.root/'state/config';good=p.read_text()
  for bad in [good.replace(TOKEN,'g'*32),good.replace('dev ','ino '),good.replace('size ','size 0'),good+'x'*600]:
   p.write_text(bad);s,rc=self.run_gate('--status');self.assertNotEqual(rc,0)
  self.config();p.chmod(0o644);self.assertNotEqual(self.run_gate('--status')[1],0)
 def test_ready_before_mount_and_escape_restores_latches(self):
  p,w=self.guard();s,rc=self.run_gate('--status');self.assertEqual(rc,0);self.assertTrue(s['mounted']);self.assertTrue(s['healthy'])
  s=self.finish(p,w);self.assertTrue(s['stock_verified']);self.assertTrue(s['stopped']);self.assertEqual(s['reason'],'escape')
  s,rc=self.run_gate('--status');self.assertEqual(rc,0);self.assertTrue(s['stopped'])
 def test_no_ready_has_no_mount(self):
  p,w=self.guard(ready=False);self.assertFalse((self.root/'home.original').exists());os.close(w)
  out,_=p.communicate(timeout=4);self.assertTrue(json.loads(out)['stock_verified'])
 def test_eof_malformed_lost_lghome_signal(self):
  for event in [b'LOST\n',b'LGHOME\n',b'BAD\n',b'x'*30+b'\n',None,'signal']:
   with self.subTest(event=event):
    self.setUp();p,w=self.guard()
    if event is None:os.close(w)
    elif event=='signal':p.send_signal(signal.SIGTERM)
    else:os.write(w,event)
    out,_=p.communicate(timeout=5);s=json.loads(out);self.assertTrue(s['stock_verified']);self.assertTrue(s['stopped'])
 def test_trial_and_heartbeat_deadlines(self):
  for seconds,reason in [(1,'trial_expired'),(0,'heartbeat_expired')]:
   self.setUp();p,w=self.guard(seconds);start=time.monotonic();out,_=p.communicate(timeout=4);s=json.loads(out);self.assertEqual(s['reason'],reason);self.assertLess(time.monotonic()-start,3)
 def test_ping_keeps_guardian_and_preload_does_not_launch(self):
  p,w=self.guard();
  for _ in range(5):time.sleep(.45);os.write(w,b'PING\n')
  s,rc=self.run_gate('{"preload":true}');self.assertEqual(rc,0);self.assertFalse((self.root/'calls').exists());self.assertIsNone(p.poll())
  s,rc=self.run_gate('{}');self.assertEqual(rc,0);self.assertIn('com.cleanyourtv.root.preview',(self.root/'calls').read_text())
  self.finish(p,w)
 def test_malformed_launches_are_rejected_and_restore(self):
  for envelope in ['[]','null','{"preload":"true"}','{"preload":true,"preload":false}','{"x":1e}','{"x":[[[[[[[[[[[[[[[[[1]]]]]]]]]]]]]]]]]}','{"x":"'+('a'*17000)+'"}']:
   self.setUp();s,rc=self.run_gate(envelope);self.assertNotEqual(rc,0);self.assertTrue(s['stock_verified']);self.assertTrue(s['stopped'])
 def test_foreign_stacked_propagated_and_incomplete_mounts_refuse(self):
  for line in ['10 1 0:1 /other ROOT/home rw - fixture fixture rw\n','1 0 0:1 / / rw master:5 - fixture fixture rw\n','broken mount line\n','x'*17000]:
   self.setUp();(self.root/'mountinfo').write_text(line.replace('ROOT',str(self.root)));r,w=os.pipe();ar,aw=os.pipe();p=subprocess.Popen([str(self.binary),'--guard',TOKEN,str(r),str(aw),'0'],pass_fds=(r,aw),stdout=subprocess.PIPE,text=True);os.close(r);os.close(aw);os.write(w,b'READY\n');os.close(w);out,_=p.communicate(timeout=4);os.close(ar);self.assertFalse(json.loads(out)['returnValue']);self.assertFalse((self.root/'home.original').exists())
 def test_failed_inverse_preserves_journal(self):
  p,w=self.guard();(self.root/'fail-inverse').touch();s=self.finish(p,w);self.assertFalse(s['returnValue']);self.assertTrue((self.root/'state/active').exists());self.assertTrue(s['stopped'])
 def test_dead_guardian_next_invocation_restores(self):
  p,w=self.guard();p.kill();p.communicate();s,rc=self.run_gate('--status');self.assertFalse(s['healthy']);s,rc=self.run_gate('{"preload":true}');self.assertTrue(s['stock_verified']);self.assertTrue(s['stopped']);self.assertFalse((self.root/'calls').exists())
 def test_negative_and_timed_out_luna_restore(self):
  for body in ['printf \'{"returnValue":false}\\n\'','sleep 20']:
   self.setUp();p,w=self.guard();(self.root/'luna').write_text('#!/bin/sh\n'+body+'\n');start=time.monotonic();s,rc=self.run_gate('{}');self.assertTrue(s['stock_verified']);self.assertTrue(s['stopped']);self.assertLess(time.monotonic()-start,4)
 def test_optional_checkpoint_inverse_order(self):
  # Source identity is checked for real file binds; directory fixture support
  # uses mkdir and must preserve source directory inode via rename in fixture.
  for name in ['checkpoint1','checkpoint2']:(self.root/name).mkdir(mode=0o700)
  p,w=self.guard();s=self.finish(p,w);self.assertTrue(s['stock_verified']);self.assertEqual((self.root/'inverse').read_text().splitlines(),[str(self.root/x) for x in ['checkpoint2','checkpoint1','home']])
 def test_c1_full_preload_does_not_launch(self):
  p,w=self.guard();s,rc=self.run_gate('{"preload":"full","params":{}}');self.assertEqual(rc,0);self.assertTrue(s['mounted']);self.assertFalse((self.root/'calls').exists());self.finish(p,w)
 def test_old_boot_status_and_restore_allow_stock_proof(self):
  (self.root/'boot').write_text('fedcba98-7654-3210-fedc-ba9876543210\n');s,rc=self.run_gate('--status');self.assertEqual(rc,0);self.assertTrue(s['stock_verified']);self.assertFalse(s['healthy']);s,rc=self.run_gate('--restore');self.assertEqual(rc,0);self.assertTrue(s['stock_verified'])
 def test_explicit_restore_stops_live_guard_and_retains_latch(self):
  p,w=self.guard();s,rc=self.run_gate('--restore');self.assertEqual(rc,0);self.assertTrue(s['stock_verified']);self.assertTrue(s['stopped']);p.communicate(timeout=4)
 def test_post_arm_foreign_mount_or_peer_is_never_unmounted(self):
  for peer in [True,False]:
   self.setUp();p,w=self.guard()
   if peer:(self.root/'peer').touch()
   else:
    with (self.root/'mountinfo').open('a') as f:f.write(f'900 1 0:1 /foreign {self.root}/home rw - fixture fixture rw\n')
   s=self.finish(p,w);self.assertFalse(s['returnValue']);self.assertTrue((self.root/'home.original').exists());self.assertFalse((self.root/'inverse').exists());self.assertTrue((self.root/'state/active').exists())
 def test_stale_live_guard_and_reused_pid_are_not_healthy(self):
  p,w=self.guard();path=self.root/'state/active';raw=path.read_text();lines=raw.splitlines();parts=lines[2].split();parts[1]=str(int(parts[1])+1);lines[2]=' '.join(parts);path.write_text('\n'.join(lines)+'\n');s,rc=self.run_gate('--status');self.assertFalse(s['healthy']);path.write_text(raw);self.finish(p,w)
 def test_negative_missing_and_oversized_child_are_bounded(self):
  for body in [None,"printf '%s' '{\"returnValue\":true,\"returnValue\":false}'",'head -c 17000 /dev/zero']:
   self.setUp();p,w=self.guard()
   if body is None:(self.root/'luna').unlink()
   else:(self.root/'luna').write_text('#!/bin/sh\n'+body+'\n')
   start=time.monotonic();s,rc=self.run_gate('{}');self.assertTrue(s['stock_verified']);self.assertTrue(s['stopped']);self.assertLess(time.monotonic()-start,4)
 def propagated_fixture(self):
  (self.root/'propagate').touch();(self.root/'jail').mkdir(mode=0o700)
  for name in ['home','checkpoint1','checkpoint2']:
   if name=='home':shutil.copy2(self.root/'home',self.root/'jail/home')
   else:
    (self.root/name).mkdir(mode=0o700);(self.root/'jail'/name).mkdir(mode=0o700)
    (self.root/name/'snapshot').write_text('original checkpoint')
    (self.root/'jail'/name/'snapshot').write_text('original peer checkpoint')
  (self.root/'mountinfo').write_text(f'1 0 0:1 / {self.root} rw shared:5 - fixture fixture rw\n2 1 0:1 / {self.root}/jail rw shared:5 - fixture fixture rw\n')
 def test_owned_same_namespace_propagated_aliases_restore(self):
  for automatic in [False,True]:
   self.setUp();self.propagated_fixture()
   if automatic:(self.root/'auto-release').touch()
   p,w=self.guard();s,rc=self.run_gate('--status');self.assertTrue(s['healthy']);self.assertTrue(s['mounted'])
   s=self.finish(p,w);self.assertTrue(s['stock_verified']);self.assertTrue(s['stopped'])
   inverse=(self.root/'inverse').read_text().splitlines()
   self.assertEqual(inverse,[str(self.root/prefix/name) for name in ['checkpoint2','checkpoint1','home'] for prefix in ['','jail']])
   for prefix in ['', 'jail']:
    for name in ['checkpoint1','checkpoint2']:self.assertTrue((self.root/prefix/name/'snapshot').exists())
 def test_foreign_overlay_on_owned_alias_retains_all_evidence(self):
  self.propagated_fixture();p,w=self.guard()
  with (self.root/'mountinfo').open('a') as f:f.write(f'900 1 0:1 /foreign {self.root}/jail/home rw - fixture fixture rw\n')
  s=self.finish(p,w);self.assertFalse(s['returnValue']);self.assertTrue((self.root/'state/active').exists());self.assertFalse((self.root/'inverse').exists())
 def test_pending_prebind_authority_recovers_after_guard_death(self):
  self.propagated_fixture();p,w=self.guard();p.kill();p.communicate()
  path=self.root/'state/active';lines=path.read_text().splitlines()
  for i in range(4,len(lines)):
   fields=lines[i].split();fields[0]='-1';lines[i]=' '.join(fields)
  path.write_text('\n'.join(lines)+'\n');s,rc=self.run_gate('--restore');self.assertEqual(rc,0);self.assertTrue(s['stock_verified'])
 def test_heartbeat_lease_is_volatile_not_fsyncing_durable_journal(self):
  p,w=self.guard();original=(self.root/'state/active').read_bytes();time.sleep(.1);os.write(w,b'PING\n');time.sleep(.1);self.assertEqual((self.root/'state/active').read_bytes(),original);self.assertTrue((self.root/'volatile/gate.lease').exists());self.finish(p,w)
 def test_malformed_envelope_while_armed_restores_and_status_is_current(self):
  p,w=self.guard();s,rc=self.run_gate('{"preload":"invalid"}');self.assertNotEqual(rc,0);self.assertTrue(s['stock_verified']);self.assertTrue(s['stopped']);p.communicate(timeout=4)
 def test_untrusted_paths_and_optional_checkpoint_symlinks_refuse(self):
  for name in ['config','source','checkpoint']:
   self.setUp()
   if name=='config':
    p=self.root/'state/config';p.rename(self.root/'config-target');p.symlink_to(self.root/'config-target');self.assertNotEqual(self.run_gate('--status')[1],0);continue
   if name=='source':(self.root/'volatile').chmod(0o755)
   else:(self.root/'checkpoint1').symlink_to(self.root/'state')
   r,w=os.pipe();ar,aw=os.pipe();p=subprocess.Popen([str(self.binary),'--guard',TOKEN,str(r),str(aw),'0'],pass_fds=(r,aw),stdout=subprocess.PIPE,text=True);os.close(r);os.close(aw);os.write(w,b'READY\n');os.close(w);out,_=p.communicate(timeout=4);os.close(ar);self.assertFalse(json.loads(out)['returnValue']);self.assertFalse((self.root/'home.original').exists())
 def test_native_parser_under_address_and_undefined_sanitizers(self):
  harness=ROOT/'root-edition/tests/native_gate_parser_test.c';binary=self.root/'parser-check'
  subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-sanitize-recover=all','-DCYTV_GATE_FIXTURE',f'-DFIXTURE_ROOT="{self.root}"','-I',str(FIXTURE.parent),str(harness),'-o',str(binary)],check=True,capture_output=True)
  checked=subprocess.run([str(binary)],capture_output=True,text=True,timeout=15)
  self.assertEqual(checked.returncode,0,checked.stderr);self.assertIn('sanitizer checks passed',checked.stdout)
 def test_status_and_off_wait_for_bounded_control_contention(self):
  for command in ['--status','--restore']:
   fd=os.open(self.root/'state/lock',os.O_RDWR|os.O_CREAT,0o600);fcntl.flock(fd,fcntl.LOCK_EX)
   timer=threading.Timer(.15,lambda:fcntl.flock(fd,fcntl.LOCK_UN));timer.start()
   start=time.monotonic();s,rc=self.run_gate(command);timer.join();os.close(fd)
   self.assertEqual(rc,0);self.assertTrue(s['stock_verified']);self.assertGreater(time.monotonic()-start,.1);self.assertLess(time.monotonic()-start,2)
 def test_guard_start_refuses_busy_without_effects(self):
  fd=os.open(self.root/'state/lock',os.O_RDWR|os.O_CREAT,0o600);fcntl.flock(fd,fcntl.LOCK_EX)
  r,w=os.pipe();ar,aw=os.pipe();start=time.monotonic()
  try:
   p=subprocess.Popen([str(self.binary),'--guard',TOKEN,str(r),str(aw),'0'],pass_fds=(r,aw),stdout=subprocess.PIPE,text=True);os.close(r);os.close(aw)
   out,_=p.communicate(timeout=2);self.assertFalse(json.loads(out)['returnValue']);self.assertLess(time.monotonic()-start,1);self.assertFalse((self.root/'home.original').exists())
  finally:
   os.close(w);os.close(ar);fcntl.flock(fd,fcntl.LOCK_UN);os.close(fd)
 def test_off_refuses_still_live_guard_and_retains_authority(self):
  p,w=self.guard();p.send_signal(signal.SIGSTOP)
  try:
   start=time.monotonic();s,rc=self.run_gate('--restore',timeout=6)
   self.assertNotEqual(rc,0);self.assertFalse(s['stock_verified']);self.assertEqual(s['guardian_pid'],p.pid);self.assertTrue((self.root/'state/active').exists());self.assertTrue((self.root/'home.original').exists());self.assertLess(time.monotonic()-start,5)
  finally:p.send_signal(signal.SIGCONT)
  p.communicate(timeout=4)
 def test_delayed_old_guard_cannot_mutate_new_attempt(self):
  p,w=self.guard();p.send_signal(signal.SIGSTOP)
  # Simulate a privileged recovery that restored the old owned fixture bind but
  # mistakenly left that stopped process alive. A new attempt now owns routing.
  (self.root/'home').unlink();(self.root/'home.original').rename(self.root/'home')
  (self.root/'mountinfo').write_text('1 0 0:1 / / rw - fixture fixture rw\n');(self.root/'state/active').unlink()
  config=self.root/'state/config';config.write_text(config.read_text().replace(TOKEN,'b'*32))
  newer,nw=self.guard(token='b'*32);journal=(self.root/'state/active').read_bytes()
  (self.root/'state/stopped').write_text('b'*32+' test_newer\n');(self.root/'state/stopped').chmod(0o600)
  p.send_signal(signal.SIGTERM);p.send_signal(signal.SIGCONT);out,_=p.communicate(timeout=4)
  self.assertFalse(json.loads(out)['returnValue']);self.assertEqual((self.root/'state/active').read_bytes(),journal);self.assertEqual((self.root/'state/stopped').read_text(),'b'*32+' test_newer\n');self.assertTrue((self.root/'home.original').exists());self.assertIsNone(newer.poll())
  self.finish(newer,nw)
 def test_corrupt_active_count_refuses_without_parser_crash(self):
  path=self.root/'state/active'
  path.write_text('CYTV-ACTIVE-2\n'+TOKEN+'\n'+str(os.getpid())+' 1 1\n2147483647\n');path.chmod(0o600)
  for command in ['--status','--restore']:
   s,rc=self.run_gate(command);self.assertNotEqual(rc,0);self.assertEqual(s['state'],'blocked');self.assertFalse(s['stock_verified'])
if __name__=='__main__':unittest.main()
