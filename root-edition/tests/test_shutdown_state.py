import sys,subprocess,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
import shutdown_state as s
class Tests(unittest.TestCase):
 def test_only_manager_stopping_is_accepted(self):
  for state in ('stopping\n','running\n','degraded\n','offline\n','unknown\n',''):
   with patch.object(s.subprocess,'run',return_value=subprocess.CompletedProcess([],1,stdout=state,stderr='')):
    self.assertEqual(s.stopping(),state=='stopping\n')
 def test_unavailable_manager_is_not_shutdown_permission(self):
  with patch.object(s.subprocess,'run',side_effect=OSError()):self.assertFalse(s.stopping())

class CachedTests(unittest.TestCase):
 def test_recent_confirmed_shutdown_survives_query_timeout_but_expires(self):
  import tempfile,os
  import persistent_health as h,device_adapter as d
  with tempfile.TemporaryDirectory() as tmp,patch.object(h,'ROOT',Path(tmp)),patch.object(d,'EXPECTED_UID',os.getuid()),patch('intent_runtime.boot_identity',return_value='boot-a'):
   with patch.object(s.time,'monotonic',return_value=10):s.record('tx')
   with patch.object(s.time,'monotonic',return_value=11),patch.object(s.subprocess,'run',side_effect=subprocess.TimeoutExpired('systemctl',.5)):
    self.assertTrue(s.stopping('tx'));self.assertFalse(s.stopping('other'))
   with patch.object(s.time,'monotonic',return_value=16),patch.object(s.subprocess,'run',side_effect=OSError()):
    self.assertFalse(s.stopping('tx'))
 def test_cached_shutdown_from_previous_boot_is_rejected(self):
  import tempfile,os
  import persistent_health as h,device_adapter as d
  with tempfile.TemporaryDirectory() as tmp,patch.object(h,'ROOT',Path(tmp)),patch.object(d,'EXPECTED_UID',os.getuid()):
   with patch('intent_runtime.boot_identity',return_value='old'):s.record('tx')
   with patch('intent_runtime.boot_identity',return_value='new'),patch.object(s.subprocess,'run',side_effect=OSError()):self.assertFalse(s.stopping('tx'))

class SessionTests(unittest.TestCase):
 def test_old_monitor_cannot_stamp_evidence_with_new_session(self):
  import tempfile,os
  import persistent_health as h,device_adapter as d
  with tempfile.TemporaryDirectory() as tmp,patch.object(h,'ROOT',Path(tmp)),patch.object(d,'EXPECTED_UID',os.getuid()),patch('intent_runtime.boot_identity',return_value='new'):
   self.assertFalse(s.record('tx',boot='old'))
   self.assertFalse(h.path('tx').with_suffix('.shutdown').exists())

class PowerTests(unittest.TestCase):
 def setUp(self):
  import tempfile,os
  import persistent_health as h,device_adapter as d
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  for p in (patch.object(h,'ROOT',Path(self.tmp.name)),patch.object(d,'EXPECTED_UID',os.getuid()),patch('intent_runtime.boot_identity',return_value='boot-a'),patch.object(s,'query',return_value=False)):
   p.start();self.addCleanup(p.stop)
 def event(self,power,state,initial=False):
  value=dict(returnValue=True,state=state)
  if initial:value['subscribed']=True
  power.event(value)
 def test_observed_active_to_standby_precedes_manager_and_preserves_fresh_evidence(self):
  power=s.PowerState('tx','boot-a')
  self.event(power,'Active',True)
  with patch.object(s.time,'monotonic',return_value=1300.691):self.event(power,'Active Standby')
  with patch.object(s.time,'monotonic',return_value=1312.991):self.event(power,'Active Standby')
  with patch.object(s.time,'monotonic',return_value=1314.386):self.assertTrue(s.stopping('tx'))
  with patch.object(s.time,'monotonic',return_value=1318):self.assertFalse(s.stopping('tx'))
 def test_initial_shutdown_unknown_and_unsubscribed_snapshots_fail_closed(self):
  for state in ('Active Standby','Power Off','unknown'):
   power=s.PowerState('tx','boot-a');self.event(power,state,True)
   self.event(power,'Active Standby');self.assertFalse(s.stopping('tx'))
  power=s.PowerState('tx','boot-a')
  with self.assertRaises(ValueError):self.event(power,'Active')
  self.assertFalse(s.stopping('tx'))
 def test_resume_unknown_and_disconnect_revoke_power_evidence(self):
  for state in ('Active','Screen Saver','unknown',None):
   power=s.PowerState('tx','boot-a');self.event(power,'Screen Saver',True)
   self.event(power,'Active Standby');self.assertTrue(s.stopping('tx'))
   if state is None:power.close()
   else:self.event(power,state)
   self.assertFalse(s.stopping('tx'))
 def test_unknown_breaks_transition_and_stream_errors_fail_closed(self):
  power=s.PowerState('tx','boot-a');self.event(power,'Active',True)
  self.event(power,'unknown');self.event(power,'Power Off');self.assertFalse(s.stopping('tx'))
  self.event(power,'Active');self.event(power,'Power Off');self.assertTrue(s.stopping('tx'))
  for value in ({'returnValue':False,'state':'Power Off'},[],{'returnValue':True,'state':7}):
   with self.assertRaises(ValueError):power.event(value)
   self.assertFalse(s.stopping('tx'))
 def test_old_power_session_and_wrong_transaction_never_authorize(self):
  power=s.PowerState('tx','boot-a');self.event(power,'Active',True)
  with patch('intent_runtime.boot_identity',return_value='boot-b'):
   self.event(power,'Active Standby');self.assertFalse(s.stopping('tx'))
  self.assertFalse(s.stopping('other'))

 def test_explicit_subscription_loss_revokes_or_refuses_shutdown_evidence(self):
  for state in ('Active','Active Standby'):
   power=s.PowerState('tx','boot-a');self.event(power,'Active',True)
   self.event(power,state)
   with self.assertRaises(ValueError):power.event(dict(returnValue=True,subscribed=False,state='Active Standby'))
   self.assertFalse(s.stopping('tx'))

 def test_new_subscription_cannot_inherit_previous_stream_evidence(self):
  old=s.PowerState('tx','boot-a');self.event(old,'Active',True)
  self.event(old,'Active Standby');self.assertTrue(s.stopping('tx'))
  new=s.PowerState('tx','boot-a')
  self.assertFalse(s.stopping('tx'));self.event(new,'Active Standby',True)
  self.assertFalse(s.stopping('tx'))

class SubscriptionTests(PowerTests):
 def run_stream(self, chunks):
  import threading
  from unittest.mock import Mock
  child=Mock();child.stdout.fileno.return_value=7;child.poll.return_value=None
  with patch.object(s.subprocess,'Popen',return_value=child),patch.object(s.select,'select',return_value=([child.stdout],[],[])),patch.object(s.os,'read',side_effect=chunks+[b'']):
   s.observe_power('tx','boot-a',threading.Event())
  child.terminate.assert_called_once();child.communicate.assert_called_once_with(timeout=1)
  self.assertFalse(s.stopping('tx'))
 def test_fragmented_json_and_multiple_frames_are_consumed_then_revoked_on_eof(self):
  calls=[];original=s.record
  def record(*args,**kwargs):
   calls.append(kwargs);return original(*args,**kwargs)
  with patch.object(s,'record',side_effect=record):
   self.run_stream([b'{"returnValue":true,"subscribed":true,"sta',b'te":"Active"}\n{"returnValue":true,"state":"Active Standby"}\n'])
  self.assertEqual(calls,[dict(source='firmware-power',boot='boot-a')])
 def test_malformed_oversized_failed_and_initial_off_streams_never_retain_authority(self):
  for chunks in ([b'[]'],[b'x'*8193],[b'{"returnValue":false}'],[b'{"returnValue":true,"subscribed":true,"state":"Active Standby"}'],[b'\xff']):
   with self.subTest(chunks=chunks[:1]):self.run_stream(chunks)
 def test_live_child_is_reaped_and_evidence_removed_when_guardian_stops(self):
  import threading,time,json
  from unittest.mock import Mock
  real_popen=subprocess.Popen;children=[]
  code='import sys;print(\'{"returnValue":true,"subscribed":true,"state":"Active"}\\n{"returnValue":true,"state":"Active Standby"}\',flush=True);sys.stdin.read()'
  def launch(*args,**kwargs):
   child=real_popen([sys.executable,'-c',code],**kwargs);children.append(child);return child
  stop=threading.Event();errors=[]
  def run():
   try:s.observe_power('tx','boot-a',stop)
   except Exception as exc:errors.append(exc)
  with patch.object(s.subprocess,'Popen',side_effect=launch):
   thread=threading.Thread(target=run);thread.start()
   try:
    deadline=time.monotonic()+2
    while not s.stopping('tx') and thread.is_alive() and time.monotonic()<deadline:time.sleep(.01)
    self.assertTrue(s.stopping('tx'))
   finally:stop.set();thread.join(3)
  self.assertFalse(thread.is_alive());self.assertEqual(errors,[])
  self.assertIsNotNone(children[0].poll());self.assertFalse(s.stopping('tx'))

 def test_invalid_frame_revokes_existing_evidence_before_eof(self):
  import threading
  from unittest.mock import Mock
  child=Mock();child.stdout.fileno.return_value=7;child.poll.return_value=None
  stop=threading.Event();chunks=iter([b'{"returnValue":true,"subscribed":true,"state":"Active"}{"returnValue":true,"state":"Active Standby"}',b'garbage\n'])
  def read(*args):
   try:return next(chunks)
   except StopIteration:
    self.assertFalse(s.stopping('tx'));stop.set();return b''
  with patch.object(s.subprocess,'Popen',return_value=child),patch.object(s.select,'select',return_value=([child.stdout],[],[])),patch.object(s.os,'read',side_effect=read):
   s.observe_power('tx','boot-a',stop)


class WakeTransitionTests(PowerTests):
 def test_only_genuine_same_stream_on_off_on_requests_one_wake(self):
  power=s.PowerState('tx','boot-a')
  self.assertIsNone(power.event(dict(returnValue=True,subscribed=True,state='Active')))
  self.assertIsNone(power.event(dict(returnValue=True,state='Active Standby')))
  token=power.event(dict(returnValue=True,state='Active'))
  self.assertIsNotNone(token)
  self.assertEqual(power.revision,token)
  self.assertIsNone(power.event(dict(returnValue=True,state='Active')))
  self.assertEqual(power.revision,token)
  self.assertFalse(s.stopping('tx'))
 def test_initial_off_unknown_reconnect_and_screen_saver_never_request_wake(self):
  for states in (('Active Standby','Active'),('Active','unknown','Power Off','Active'),('Screen Saver','Active')):
   power=s.PowerState('tx','boot-a')
   for index,state in enumerate(states):
    self.assertIsNone(power.event(dict(returnValue=True,state=state,**({'subscribed':True} if index==0 else {}))))
 def test_processing_on_and_new_off_cancel_inflight_wake(self):
  power=s.PowerState('tx','boot-a')
  self.event(power,'Active',True);self.event(power,'Power Off')
  self.assertIsNone(power.event(dict(returnValue=True,state='Active',processing=True)))
  token=power.event(dict(returnValue=True,state='Active',processing=False,onOff='on'))
  self.assertIsNotNone(token)
  self.event(power,'Power Off');self.assertNotEqual(power.revision,token)
  new=power.event(dict(returnValue=True,state='Active'))
  self.assertIsNotNone(new);self.assertNotEqual(new,token)
  power.close();self.assertNotEqual(power.revision,new)
 def test_onoff_off_is_never_a_wake(self):
  power=s.PowerState('tx','boot-a');self.event(power,'Active',True);self.event(power,'Power Off')
  self.assertIsNone(power.event(dict(returnValue=True,state='Active',onOff='off')))

class WakeWorkerTests(unittest.TestCase):
 setUp=PowerTests.setUp
 def test_optional_worker_cannot_block_power_observer_or_duplicate_inflight(self):
  import threading
  from unittest.mock import Mock
  entered=threading.Event();release=threading.Event()
  def present(*args,**kwargs):
   entered.set();release.wait(2);return 'unavailable'
  monitor=s.Monitor()
  with patch('intent_runtime.present_wake',side_effect=present) as launch:
   try:
    monitor.request_wake('tx','boot-a',lambda:False)
    self.assertTrue(entered.wait(1))
    monitor.request_wake('tx','boot-a',lambda:False)
    self.assertEqual(launch.call_count,1)
   finally:release.set();monitor.close()
   self.assertFalse(monitor.presentation.is_alive())
 def test_stream_wires_wake_and_eof_revokes_queued_request(self):
  import threading,json
  from unittest.mock import Mock
  callbacks=[];stop=threading.Event();child=Mock();child.stdout.fileno.return_value=7;child.poll.return_value=None
  data=''.join(json.dumps(dict(returnValue=True,state=state,**({'subscribed':True} if i==0 else {}))) for i,state in enumerate(('Active','Active Standby','Active'))).encode()
  with patch.object(s.subprocess,'Popen',return_value=child),patch.object(s.select,'select',return_value=([child.stdout],[],[])),patch.object(s.os,'read',side_effect=[data,b'']):
   s.observe_power('tx','boot-a',stop,wake=lambda cancelled:callbacks.append(cancelled))
  self.assertEqual(len(callbacks),1);self.assertTrue(callbacks[0]())

 def test_fragmented_valid_active_frame_keeps_pending_wake_until_complete(self):
  import threading
  from unittest.mock import Mock
  child=Mock();child.stdout.fileno.return_value=7;child.poll.return_value=None
  callbacks=[];chunks=iter([b'{"returnValue":true,"subscribed":true,"state":"Active"}{"returnValue":true,"state":"Active Standby"}{"returnValue":true,"state":"Act',b'ive"}',b''])
  def read(*args):
   chunk=next(chunks)
   if chunk == b'ive"}':self.assertEqual(callbacks,[])
   return chunk
  with patch.object(s.subprocess,'Popen',return_value=child),patch.object(s.select,'select',return_value=([child.stdout],[],[])),patch.object(s.os,'read',side_effect=read):
   s.observe_power('tx','boot-a',threading.Event(),wake=lambda cancelled:callbacks.append(cancelled))
  self.assertEqual(len(callbacks),1);self.assertTrue(callbacks[0]())


class WakeDiagnosticTests(PowerTests):
 def snapshot(self):
  import json,persistent_health as h
  return json.loads(h.path('tx').with_suffix('.wake').read_text())
 def test_missing_transition_and_real_wake_have_distinct_bounded_records(self):
  power=s.PowerState('tx','boot-a')
  self.assertEqual(self.snapshot()['event'],'observing')
  self.event(power,'Active',True)
  self.assertEqual(self.snapshot()['wake_count'],0)
  self.event(power,'Active Standby')
  self.assertEqual(self.snapshot()['event'],'off-observed')
  self.event(power,'Active Standby')
  self.assertEqual(self.snapshot()['off_count'],1)
  token=power.event(dict(returnValue=True,state='Active'))
  self.assertIsNotNone(token)
  self.assertEqual(self.snapshot()['event'],'wake-observed')
  self.assertEqual(self.snapshot()['wake_count'],1)
  self.assertEqual(self.snapshot()['revision'],token)
  for _ in range(50):self.event(power,'Active')
  self.assertEqual(self.snapshot()['event'],'wake-observed')
  self.assertEqual(self.snapshot()['wake_count'],1)
  power.close()
  self.assertEqual(self.snapshot()['event'],'closed')
 def test_new_active_baseline_is_recorded_without_inventing_a_wake(self):
  for state in ('Active Standby','unknown','Active'):
   power=s.PowerState('tx','boot-a')
   self.event(power,state,True)
   if state == 'Active':
    self.assertIsNone(power.event(dict(returnValue=True,state='Active',onOff='off')))
   self.assertIsNone(power.event(dict(returnValue=True,state='Active')))
   snapshot=self.snapshot()
   self.assertTrue(snapshot['on']);self.assertFalse(snapshot['asleep'])
   self.assertEqual(snapshot['wake_count'],0)

 def test_unknown_reply_is_classified_without_persisting_raw_data(self):
  power=s.PowerState('tx','boot-a');self.event(power,'Active',True)
  self.event(power,'private-state-with-address')
  snapshot=self.snapshot()
  self.assertEqual(snapshot['event'],'unknown-state')
  self.assertNotIn('private',str(snapshot))
  self.assertIsNone(power.event(dict(returnValue=True,state='Active')))
 def test_stream_eof_leaves_reason_and_cancels_edge(self):
  import threading
  from unittest.mock import Mock
  callbacks=[];child=Mock();child.stdout.fileno.return_value=7;child.poll.return_value=None
  frames=b'{"returnValue":true,"subscribed":true,"state":"Active"}{"returnValue":true,"state":"Active Standby"}{"returnValue":true,"state":"Active"}'
  with patch.object(s.subprocess,'Popen',return_value=child),patch.object(s.select,'select',return_value=([child.stdout],[],[])),patch.object(s.os,'read',side_effect=[frames,b'']):
   s.observe_power('tx','boot-a',threading.Event(),wake=lambda cancelled:callbacks.append(cancelled))
  snapshot=self.snapshot()
  self.assertEqual(snapshot['event'],'eof');self.assertEqual(snapshot['wake_count'],1)
  self.assertTrue(callbacks[0]());self.assertFalse(snapshot['on'])
 def test_diagnostic_file_cannot_replace_or_follow_a_foreign_symlink(self):
  import persistent_health as h
  target=h.ROOT/'foreign';target.write_text('keep')
  h.path('tx').with_suffix('.wake').symlink_to(target)
  power=s.PowerState('tx','boot-a');self.event(power,'Active',True)
  self.event(power,'Active Standby')
  self.assertIsNotNone(power.event(dict(returnValue=True,state='Active')))
  self.assertEqual(target.read_text(),'keep')
 def test_diagnostic_io_failure_does_not_revoke_an_eligible_edge(self):
  power=s.PowerState('tx','boot-a')
  with patch.object(s.tempfile,'mkstemp',side_effect=OSError('full')):
   self.event(power,'Active',True)
  self.event(power,'Active Standby')
  with patch.object(s.tempfile,'mkstemp',side_effect=OSError('full')):
   self.assertIsNotNone(power.event(dict(returnValue=True,state='Active')))
