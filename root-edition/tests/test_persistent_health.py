import json,os,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
import device_adapter as d
import persistent_health as h
from test_persistent_recovery import IntegrationFixture

class HealthTests(IntegrationFixture, unittest.TestCase):
 def setUp(self):
  super().setUp()
  self.health=self.root/'volatile';self.health.mkdir(mode=0o700)
  self.hp=patch.object(h,'ROOT',self.health);self.hp.start()
  self.bp=patch('intent_runtime.boot_identity',return_value='boot-a');self.bp.start()
 def tearDown(self):
  self.bp.stop();self.hp.stop();super().tearDown()
 def test_deleted_home_revokes_health_and_existing_guard_recovers(self):
  from profile_plan import CANDIDATE
  h.publish('route-a',1)
  (self.apps/CANDIDATE/'appinfo.json').unlink()
  self.assertFalse(h.authorized('route-a'))
  h.run('route-a',lambda tx:self.c.exit(self.store.read()))
  self.assertEqual(self.store.read()['phase'],'disabled');self.assertEqual(self.read(),self.baseline)
 def test_only_current_binding_can_publish(self):
  h.publish('route-a',1)
  with self.assertRaises(ValueError):h.publish('old',2)
  self.assertEqual(h.load('route-a')['sequence'],1)
 def test_each_context_refusal_has_a_fixed_reason_without_private_identity(self):
  import copy
  original=self.store.read();binding=self.c.read_binding()
  for field,value,reason in (('transaction','old','transaction-mismatch'),
       ('restored',True,'binding-restored'),('generation',9,'generation-mismatch'),
       ('token','private-other-token','token-mismatch'),('boot','other-boot','boot-mismatch'),
       ('phase','disabled','phase-inactive'),('failsafe',True,'failsafe-present')):
   with self.subTest(field=field),patch.object(d,'FAILSAFE',self.root/'failsafe'):
    intent=copy.deepcopy(original);current=copy.deepcopy(binding)
    if field in ('transaction','restored','generation','token'):current[field]=value
    elif field=='failsafe':d.FAILSAFE.touch()
    else:
     intent[field]=value
     if field=='phase':intent['enabled']=False
    self.store.path.write_text(json.dumps(intent));self.c.write_binding(current)
    with self.assertRaises(ValueError) as caught:h.publish('route-a',1)
    self.assertEqual(getattr(caught.exception,'reason',None),reason)
    self.assertNotIn('private-other-token',str(caught.exception))
    self.assertNotIn('route-a',str(caught.exception))
    self.store.path.write_text(json.dumps(original));self.c.write_binding(binding)
    if d.FAILSAFE.exists():d.FAILSAFE.unlink()
 def test_expired_heartbeat_is_not_health(self):
  with patch.object(h.time,'monotonic',return_value=10):h.publish('route-a',1)
  with patch.object(h.time,'monotonic',return_value=13):
   with self.assertRaises(ValueError):h.require_fresh('route-a')
 def test_exit_revokes_persistent_authority(self):
  h.publish('route-a',1);self.assertTrue(h.authorized('route-a'))
  self.c.exit(self.intent)
  self.assertFalse(h.authorized('route-a'))
 def test_previous_boot_lease_cannot_be_used(self):
  h.publish('route-a',1)
  with patch('intent_runtime.boot_identity',return_value='boot-b'):
   with self.assertRaises(ValueError):h.require_fresh('route-a')
 def test_lease_is_private_and_volatile(self):
  h.publish('route-a',1)
  self.assertEqual(h.path('route-a').stat().st_mode & 0o777,0o600)
  self.assertFalse((self.root/'lease.json').exists())

 # Exercise the actual publisher/reader contract at a binary exponent boundary.
 def test_publisher_two_seconds_are_valid_at_float_boundaries(self):
  for seq,issued in enumerate((62.4,126.4,254.4,510.4,1022.4),1):
   with patch.object(h.time,'monotonic',return_value=issued):
    h.publish('route-a',seq)
    self.assertEqual(h.require_fresh('route-a')['sequence'],seq)
   with patch.object(h.time,'monotonic',return_value=issued+2):
    with self.assertRaises(ValueError):h.require_fresh('route-a')

 def test_clock_correction_preserves_health_shutdown_and_normal_gate(self):
  import shutil
  import intent_runtime as runtime,boot_gate,shutdown_state
  self.bp.stop()
  proc=self.root/'proc';(proc/'sys/kernel/random').mkdir(parents=True)
  (proc/'sys/kernel/random/boot_id').write_text('snapshot-kernel\n')
  (proc/'stat').write_text('btime 100\n')
  session=self.root/'boot';identity=runtime.boot_identity
  self.intent=dict(self.intent,boot=identity(proc,session))
  self.store.path.write_text(json.dumps(self.intent))
  with patch.object(runtime,'boot_identity',side_effect=lambda:identity(proc,session)),patch.object(boot_gate,'ROOT',session),patch.object(shutdown_state,'query',return_value=False):
   h.publish('route-a',1);shutdown_state.record('route-a');boot_gate.mark()
   (proc/'stat').write_text('btime 526\n')
   self.assertEqual(h.require_fresh('route-a')['sequence'],1)
   self.assertTrue(shutdown_state.stopping('route-a'))
   self.assertEqual(boot_gate.observation(),(True,False))
   shutil.rmtree(session)
   with self.assertRaises(ValueError):h.require_fresh('route-a')
   self.assertFalse(shutdown_state.stopping('route-a'))
   self.assertEqual(boot_gate.observation(),(False,False))

if __name__=='__main__':unittest.main()

class GuardianPulseTests(unittest.TestCase):
 def test_missing_or_stalled_guardian_pulse_is_not_healthy(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(h,'ROOT',Path(tmp)),patch.object(d,'EXPECTED_UID',os.getuid()):
   with self.assertRaises(OSError):h.require_guardian('tx')
   with patch.object(h.time,'monotonic',return_value=10):h.guardian_ping('tx')
   with patch.object(h.time,'monotonic',return_value=11):h.require_guardian('tx')
   with patch.object(h.time,'monotonic',return_value=13):
    with self.assertRaises(ValueError):h.require_guardian('tx')

class IndependentDeviceGuardTests(unittest.TestCase):
 def test_real_health_adapter_recovers_when_publisher_is_stopped(self):
  import subprocess,signal,select
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);volatile=root/'health';volatile.mkdir(mode=0o700)
   state=dict(version=1,generation=1,phase='active',enabled=True,boot='boot-a',token='attempt-a')
   (root/'persistent-intent.json').write_text(json.dumps(state))
   (root/'persistent-binding.json').write_text(json.dumps(dict(version=1,generation=1,token='attempt-a',transaction='tx',restored=False)))
   (root/'profile-trial.json').write_text(json.dumps(dict(transaction='tx',state='pending')))
   setup="""
import os,sys,time
from pathlib import Path
import persistent_health as h, intent_runtime, device_adapter as d
d.STATE=Path(sys.argv[1]);d.EXPECTED_UID=os.getuid();h.ROOT=d.STATE/'health'
d.home_present=lambda **kwargs:True
intent_runtime.boot_identity=lambda:'boot-a'
"""
   pub=setup+"\nseq=0\nwhile True:\n seq+=1;h.publish('tx',seq)\n if seq==1:print('READY',flush=True)\n time.sleep(.1)\n"
   guard=setup+"\nprint('READY',flush=True)\nh.run('tx',lambda tx:(d.STATE/'recovered').write_text(tx))\n"
   cwd=Path(__file__).resolve().parents[1]/'runtime'
   p=subprocess.Popen([sys.executable,'-c',pub,tmp],cwd=cwd,stdout=subprocess.PIPE,text=True);g=None
   try:
    self.assertTrue(select.select([p.stdout],[],[],3)[0]);self.assertEqual(p.stdout.readline().strip(),'READY')
    g=subprocess.Popen([sys.executable,'-c',guard,tmp],cwd=cwd,stdout=subprocess.PIPE,text=True)
    self.assertTrue(select.select([g.stdout],[],[],3)[0]);self.assertEqual(g.stdout.readline().strip(),'READY')
    os.kill(p.pid,signal.SIGSTOP)
    self.assertEqual(g.wait(timeout=5),0);self.assertIsNone(p.poll())
    self.assertEqual((root/'recovered').read_text(),'tx')
   finally:
    p.kill();p.wait();p.stdout.close()
    if g is not None:
     if g.poll() is None:g.kill();g.wait()
     g.stdout.close()
