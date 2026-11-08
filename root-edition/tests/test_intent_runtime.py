import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
import intent_runtime as r

class RuntimeTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.state=patch.object(r.d,'STATE',self.root);self.state.start();self.addCleanup(self.state.stop)
  self.uid=patch.object(r.d,'EXPECTED_UID',__import__('os').getuid());self.uid.start();self.addCleanup(self.uid.stop)
  (self.root/'persistent-intent.json').write_text('{}')
  self.presence=patch.object(r.d,'home_present',return_value=True);self.presence.start();self.addCleanup(self.presence.stop)
  self.audit=patch('boot_gate.audit');self.audit.start();self.addCleanup(self.audit.stop)
  self.observation=patch('boot_gate.observation',return_value=(False,False));self.observation.start();self.addCleanup(self.observation.stop)
 def tearDown(self):self.tmp.cleanup()
 def test_clock_correction_does_not_invalidate_current_session(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'proc';(p/'sys/kernel/random').mkdir(parents=True)
   session=Path(tmp)/'session'
   (p/'sys/kernel/random/boot_id').write_text('abc-boot\n');(p/'stat').write_text('btime 100\n')
   a=r.boot_identity(p,session)
   (p/'stat').write_text('btime 526\n')
   self.assertEqual(a,r.boot_identity(p,session))
 def test_snapshot_with_reused_kernel_id_gets_new_session_after_volatile_reset(self):
  import shutil
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'proc';(p/'sys/kernel/random').mkdir(parents=True)
   session=Path(tmp)/'session'
   (p/'sys/kernel/random/boot_id').write_text('abc-boot\n');(p/'stat').write_text('btime 100\n')
   a=r.boot_identity(p,session);shutil.rmtree(session)
   self.assertNotEqual(a,r.boot_identity(p,session))
 def test_concurrent_callers_share_one_private_session(self):
  from concurrent.futures import ThreadPoolExecutor
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'proc';(p/'sys/kernel/random').mkdir(parents=True)
   session=Path(tmp)/'session'
   (p/'sys/kernel/random/boot_id').write_text('abc-boot\n');(p/'stat').write_text('btime 100\n')
   with ThreadPoolExecutor(max_workers=8) as pool:
    identities=list(pool.map(lambda _:r.boot_identity(p,session),range(16)))
   self.assertEqual(len(set(identities)),1)
   self.assertEqual(session.stat().st_mode & 0o777,0o700)
   self.assertEqual((session/'session.json').stat().st_mode & 0o777,0o600)
 def test_unsafe_session_is_rejected_without_replacement(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'proc';(p/'sys/kernel/random').mkdir(parents=True)
   session=Path(tmp)/'session'
   (p/'sys/kernel/random/boot_id').write_text('abc-boot\n');(p/'stat').write_text('btime 100\n')
   session.symlink_to(self.root,target_is_directory=True)
   with self.assertRaises(ValueError):r.boot_identity(p,session)
   self.assertTrue(session.is_symlink())
 def test_missing_identity_is_not_inferred_from_wall_clock(self):
  with tempfile.TemporaryDirectory() as tmp:
   with self.assertRaises(OSError):r.boot_identity(Path(tmp))
 def test_legacy_install_has_no_intent_side_effects(self):
  with patch.object(r.os.path,'lexists',return_value=False),patch.object(r,'Coordinator') as c:
   self.assertIsNone(r.restore());self.assertIsNone(r.boot());c.assert_not_called()
 def test_bound_restore_uses_intent_coordinator(self):
  c=Mock(binding=self.root/'missing-binding');c.store.read.return_value={'phase':'active'};c.exit.return_value={'restored_transaction':'tx'}
  with patch.object(r,'coordinator',return_value=c):self.assertEqual(r.restore(),'restored')
  c.exit.assert_called_once_with({'phase':'active'})
 def test_live_bounded_guard_is_preserved_on_duplicate_boot(self):
  c=Mock(binding=self.root/'missing-binding');s={'boot':'same','phase':'trial'};c.store.read.return_value=s
  with patch.object(r,'coordinator',return_value=c),patch.object(r,'boot_identity',return_value='same'),patch.object(r.d.FAILSAFE.__class__,'exists',return_value=False),patch.object(r.d,'safe_json',return_value={}),patch.object(r.d,'active_guardian',return_value=True):
   self.assertEqual(r.boot(),'guarded-intent-trial')
  c.boot.assert_not_called()
 def test_failsafe_never_preserves_guarded_route(self):
  c=Mock(binding=self.root/'missing-binding');c.store.read.return_value={'boot':'same','phase':'trial'}
  c.boot.return_value={'effect':'none','intent':{'phase':'disabled'}}
  with patch.object(r,'coordinator',return_value=c),patch.object(r,'boot_identity',return_value='same'),patch.object(r.d.FAILSAFE.__class__,'exists',return_value=True),patch.object(r.d,'active_guardian',return_value=True):r.boot()
  self.assertTrue(c.boot.call_args.args[-1])
 def test_boot_restarts_only_after_coordinator_verified_recovery(self):
  c=Mock(binding=self.root/'missing-binding');c.store.read.return_value={'version':1,'generation':1,'boot':'old','phase':'active','enabled':True,'token':'old-attempt'}
  new={'phase':'starting'};c.boot.return_value={'effect':'start_guarded','intent':new}
  with patch.object(r,'coordinator',return_value=c),patch.object(r,'boot_identity',return_value='new'),patch('boot_gate.eligible',return_value=False),patch('boot_gate.wait',return_value=True),patch.object(r.d.FAILSAFE.__class__,'exists',return_value=False):r.boot()
  c.restart.assert_called_once_with(new)
  c.exit.assert_not_called()

 def test_true_failsafe_restores_before_refusing_restart(self):
  c=Mock(binding=self.root/'missing-binding');c.store.read.return_value={'version':1,'generation':1,'boot':'old','phase':'active','enabled':True,'token':'old-attempt'}
  new={'phase':'starting'};c.boot.return_value={'effect':'start_guarded','intent':new}
  def refused():
   c.boot.assert_called_once();c.restart.assert_not_called();return False
  with patch.object(r,'coordinator',return_value=c),patch.object(r,'boot_identity',return_value='new'),patch.object(r.d.FAILSAFE.__class__,'exists',return_value=True),patch('boot_gate.eligible',return_value=False),patch('boot_gate.wait',side_effect=refused):
   self.assertEqual(r.boot(),'restored')
  c.exit.assert_called_once_with(new,reason='fault');c.restart.assert_not_called()

 def test_duplicate_callback_during_shutdown_does_not_revoke_or_restart(self):
  c=Mock(binding=self.root/'missing-binding');intent={'boot':'same','phase':'stopping'};c.store.read.return_value=intent
  with patch.object(r,'coordinator',return_value=c),patch.object(r,'boot_identity',return_value='same'),patch.object(r.d.FAILSAFE.__class__,'exists',return_value=False):
   self.assertEqual(r.boot(),'shutdown-pending')
  c.shutdown.assert_called_once_with(intent);c.exit.assert_not_called();c.restart.assert_not_called()

 def test_duplicate_boot_during_gate_wait_cannot_disable_starting_intent(self):
  current=[{'version':1,'generation':1,'boot':'old','phase':'active','enabled':True,'token':'old-attempt'}]
  new={'boot':'new','phase':'starting'}
  c=Mock(binding=self.root/'missing-binding');c.store.read.side_effect=lambda:current[0]
  def recover(*args):
   current[0]=new;return {'effect':'start_guarded','intent':new}
  c.boot.side_effect=recover
  def gate():
   self.assertEqual(r.boot(),'boot-in-progress')
   c.exit.assert_not_called()
   return True
  with patch.object(r,'coordinator',return_value=c),patch.object(r,'boot_identity',return_value='new'),patch.object(r.d.FAILSAFE.__class__,'exists',return_value=False),patch('boot_gate.eligible',return_value=False),patch('boot_gate.wait',side_effect=gate),patch.object(r.d,'safe_json',return_value={}),patch.object(r.d,'active_guardian',return_value=False):
   r.boot()
  c.restart.assert_called_once_with(new);c.exit.assert_not_called()
 def test_invalid_identity_attempts_fault_recovery_without_rearm(self):
  c=Mock(binding=self.root/'missing-binding');intent={'phase':'active','enabled':True};c.store.read.return_value=intent
  with patch.object(r,'coordinator',return_value=c),patch.object(r,'boot_identity',side_effect=ValueError('unsafe session')):
   with self.assertRaises(ValueError):r.boot()
  c.exit.assert_called_once_with(intent,reason='fault');c.boot.assert_not_called();c.restart.assert_not_called()
 def test_same_session_fault_recovery_does_not_depend_on_audit_writes(self):
  c=Mock(binding=self.root/'missing-binding');intent={'boot':'same','phase':'active','enabled':True,'generation':1};c.store.read.return_value=intent
  with patch.object(r,'coordinator',return_value=c),patch.object(r,'boot_identity',return_value='same'),patch.object(r.d.FAILSAFE.__class__,'exists',return_value=False),patch.object(r.d,'safe_json',return_value={}),patch.object(r.d,'active_guardian',return_value=False),patch('boot_gate.audit',side_effect=OSError('full')):
   self.assertEqual(r._boot(),'restored')
  c.exit.assert_called_once_with(intent,reason='fault')
 def test_existing_invalid_session_records_are_never_replaced(self):
  import json
  with tempfile.TemporaryDirectory() as tmp:
   proc=Path(tmp)/'proc';(proc/'sys/kernel/random').mkdir(parents=True)
   (proc/'sys/kernel/random/boot_id').write_text('kernel\n');session=Path(tmp)/'session'
   r.boot_identity(proc,session);record=session/'session.json'
   for value in (None,{},dict(version=True,kernel='kernel',token='a'*32),dict(version=1,kernel='kernel',token='bad')):
    with self.subTest(value=value):
     raw=json.dumps(value);record.write_text(raw)
     with self.assertRaises(ValueError):r.boot_identity(proc,session)
     self.assertEqual(record.read_text(),raw)
