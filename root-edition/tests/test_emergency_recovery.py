import sys,unittest,time
from pathlib import Path
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
import emergency_trial as e
class RecoveryTests(unittest.TestCase):
 def test_health_refusal_is_logged_before_recovery_without_changing_watchdog(self):
  import json,os
  from contextlib import redirect_stderr,redirect_stdout
  from io import StringIO
  import persistent_health as health
  from persistent_recovery import Coordinator
  class Observer:
   pid=12
   def poll(self):return 0
   def wait(self):pass
  def observe(args,**kwargs):
   os.write(kwargs['pass_fds'][0],b'READY\nPING\n');return Observer()
  log=StringIO()
  with patch.object(e.d,'trusted_dir'),patch.object(e.d,'safe_json',return_value={'transaction':'private-tx','state':'pending','deadline':time.monotonic()+60}), \
       patch.object(e,'save_ready'),patch.object(e,'completed',return_value=False), \
       patch.object(e.subprocess,'Popen',side_effect=observe),patch.object(e.os.path,'lexists',return_value=True), \
       patch.object(Coordinator,'read_binding',return_value={'transaction':'private-tx'}), \
       patch('boot_gate.waiting',return_value=False), \
       patch.object(health,'context',return_value={}),patch.object(health,'require_guardian'), \
       patch.object(health,'publish',side_effect=health.HealthContextError('failsafe-present')), \
       patch.object(e,'recover',side_effect=lambda *a:print('RECOVER',file=__import__('sys').stderr) or True), \
       redirect_stderr(log),redirect_stdout(StringIO()):
   with self.assertRaises(ValueError):e.supervise('private-tx')
  lines=log.getvalue().splitlines();record=json.loads(lines[0])
  self.assertEqual(record['event'],'health-context-rejected')
  self.assertEqual(record['reason'],'failsafe-present')
  self.assertEqual(lines[1],'RECOVER')
  self.assertNotIn('private-tx',lines[0])
 def test_diagnostic_output_failure_cannot_skip_recovery(self):
  import persistent_health as health
  with patch.object(e.d,'trusted_dir'),patch.object(e.d,'safe_json',return_value={'transaction':'tx','state':'pending'}), \
       patch.object(e.subprocess,'Popen',side_effect=health.HealthContextError('boot-mismatch')), \
       patch.object(e,'print',side_effect=OSError('full'),create=True),patch.object(e,'recover',return_value=True) as restore:
   with self.assertRaises(ValueError):e.supervise('tx')
  restore.assert_called_once_with('tx','supervisor_error')
 def test_full_log_cannot_prevent_real_recovery_from_restoring_stock(self):
  with patch.object(e,'print',side_effect=OSError('full'),create=True), \
       patch('persistent_recovery.bound_exit',return_value=None), \
       patch.object(e.d,'restore_once',return_value='restored') as restore, \
       patch.object(e.d,'safe_json',return_value={'transaction':'tx','baseline':{'home':'stock'}}), \
       patch.object(e.d,'read',return_value={'home':'stock'}),patch.object(e.d,'sam_transport'):
   self.assertTrue(e.recover('tx','supervisor_error'))
  restore.assert_called_once_with(expected_transaction='tx')
 def test_broken_diagnostic_import_cannot_skip_supervisor_recovery(self):
  import builtins
  original=builtins.__import__
  def importing(name,*args,**kwargs):
   if name=='persistent_health':raise ImportError('diagnostic unavailable')
   return original(name,*args,**kwargs)
  with patch.object(e.d,'trusted_dir'),patch.object(e.d,'safe_json',return_value={'transaction':'tx','state':'pending'}), \
       patch.object(e.subprocess,'Popen',side_effect=RuntimeError('original failure')), \
       patch.object(builtins,'__import__',side_effect=importing),patch.object(e,'recover',return_value=True) as restore:
   with self.assertRaisesRegex(RuntimeError,'original failure'):e.supervise('tx')
  restore.assert_called_once_with('tx','supervisor_error')
 def test_full_shared_log_cannot_block_bound_transaction_recovery(self):
  import test_persistent_recovery as fixture
  case=fixture.IntegrationTests('test_exit_disables_intent_before_real_routing_restore');case.setUp()
  try:
   with patch('builtins.print',side_effect=OSError('full')),patch.object(e.time,'sleep'), \
        patch('intent_runtime.boot_identity',return_value='boot-a'), \
        patch('shutdown_state.stopping',return_value=None),patch.object(e.d,'FAILSAFE',case.root/'failsafe'):
    self.assertTrue(e.recover('route-a','supervisor_error'))
   self.assertEqual(case.store.read()['phase'],'disabled')
   self.assertEqual(case.read(),case.baseline)
  finally:case.tearDown()
 def test_superseded_never_launches_or_reads_new_state(self):
  with patch.object(e.d,'restore_once',return_value='superseded') as restore,patch.object(e.d,'read') as read,patch.object(e.d,'sam_transport') as bus:
   self.assertTrue(e.recover('old','escape'));restore.assert_called_once_with(expected_transaction='old');read.assert_not_called();bus.assert_not_called()
 def test_conflict_does_not_launch(self):
  with patch.object(e.d,'restore_once',return_value='conflict'),patch.object(e.d,'sam_transport') as bus:
   self.assertFalse(e.recover('tx','escape'));bus.assert_not_called()
 def test_mismatched_readback_never_launches(self):
  with patch.object(e.d,'restore_once',return_value='restored'),patch.object(e.d,'safe_json',return_value={'transaction':'tx','baseline':{'home':'stock'}}),patch.object(e.d,'read',return_value={'home':'other'}),patch.object(e.d,'sam_transport') as bus:
   self.assertFalse(e.recover('tx','escape'));bus.assert_not_called()
 def test_verified_restore_launches_only_lg_home(self):
  bus=Mock()
  with patch.object(e.d,'restore_once',return_value='restored'),patch.object(e.d,'safe_json',return_value={'transaction':'tx','baseline':{'home':'stock'}}),patch.object(e.d,'read',return_value={'home':'stock'}),patch.object(e.d,'sam_transport',return_value=bus):
   self.assertTrue(e.recover('tx','escape'));bus.call.assert_called_once_with('luna://com.webos.applicationManager/launch',{'id':'com.webos.app.home'})
 def test_no_ready_prevents_returning_guardian_for_publication(self):
  supervisor=Mock(pid=123);supervisor.poll.return_value=1
  guardian=Mock(pid=456)
  with patch.object(e.bounded,'spawn',return_value=guardian),patch.object(e.subprocess,'Popen',return_value=supervisor),patch.object(e.os,'open',return_value=9),patch.object(e.os,'close'),patch.object(e.d,'safe_json',return_value={'transaction':'tx','state':'pending','deadline':time.monotonic()+60}),patch.object(e.bounded,'begin',side_effect=lambda spawn:spawn('tx')):
   with self.assertRaisesRegex(RuntimeError,'before activation'):e.start()
