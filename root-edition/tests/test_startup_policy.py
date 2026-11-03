"""Native startup choices: real journals/health, simulated firmware boundaries."""
import copy,json,sys,unittest,threading,time,os
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
try:import intent_runtime as policy
except ModuleNotFoundError:policy=None
import device_adapter as d
import persistent_health as health
import test_wake_lifecycle as lifecycle
import test_native_input as native

class Tests(unittest.TestCase):
 create_route=lifecycle.WakeLifecycleTests.create_route
 read=lifecycle.WakeLifecycleTests.read
 write=lifecycle.WakeLifecycleTests.write
 tearDown=lifecycle.WakeLifecycleTests.tearDown
 def setUp(self):
  self.assertIsNotNone(policy,'Native source policy is missing')
  lifecycle.WakeLifecycleTests.setUp(self)
  p=patch.object(d,'active_guardian',return_value=True);p.start();self.addCleanup(p.stop)
  process=patch.object(d,'process_start',return_value='123');process.start();self.addCleanup(process.stop)
  (self.root/'profile-guardian-ready.json').write_text(json.dumps(dict(transaction='route-a',pid=os.getpid(),start_ticks='123')))
  (self.root/'profile-guardian-ready.json').chmod(0o600)
  policy.startup_observer_mark('route-a',self.session,True)
  self.metadata_override=None
  self.surfaces=[]
 def call(self,uri,payload,timeout=5):
  if uri=='luna://com.webos.surfacemanager/getForegroundAppInfo':
   return dict(returnValue=True,foregroundAppInfo=self.surfaces)
  if uri.endswith('/getForegroundAppInfo'):return dict(returnValue=True,appId=self.foreground)
  if uri.endswith('/getAppInfo'):
   app=payload['id'];store='/media/cryptofs/apps/usr/palm/applications/'+app
   info=dict(id=app,type='web',vendor='LifeStream ltd.',folderPath=store,activeFolderPath=store,CPApp=True,internalInstallationOnly=True,visible=app!='com.webos.app.cpcover')
   if self.metadata_override is not None:info.update(self.metadata_override)
   return dict(returnValue=True,appInfo=info)
  if uri.endswith('/launch'):raise AssertionError('Startup must never launch an app')
  return native.NativeInputTests.call(self,uri,payload,timeout)
 def run_policy(self,**kw):return policy.startup_reconcile('route-a',self.session,**kw)
 def channels(self):
  self.foreground='mgg4.5.channelplus';self.last={'type':'MVPD_IP','appId':self.foreground};return dict(self.last)
 def test_defaults_status_are_read_only(self):
  before=len(self.calls)
  self.assertEqual(policy.startup_status(),{'sources':{'tv':True,'youtube':False,'hdmi':False},'active':True})
  self.assertEqual(len(self.calls),before);self.assertFalse((self.root/'startup-policy.json').exists())
 def test_exact_boolean_policy_persists_and_off_rejects_changes(self):
  wanted={'tv':False,'youtube':True,'hdmi':True}
  self.assertEqual(policy.startup_configure(wanted)['sources'],wanted)
  raw=(self.root/'startup-policy.json').read_bytes();self.assertEqual((self.root/'startup-policy.json').stat().st_mode&0o777,0o600)
  for invalid in ({'tv':1,'youtube':False,'hdmi':False},{'tv':True},dict(wanted,other=True)):
   with self.assertRaises(ValueError):policy.startup_configure(invalid)
   self.assertEqual((self.root/'startup-policy.json').read_bytes(),raw)
  self.c.exit(self.store.read())
  self.assertFalse(policy.startup_status()['active'])
  with self.assertRaises(ValueError):policy.startup_configure({'tv':True,'youtube':False,'hdmi':False})
  self.assertEqual((self.root/'startup-policy.json').read_bytes(),raw)
 def test_channels_select_existing_root_without_changing_foreground(self):
  displaced=self.channels();devices=copy.deepcopy(self.devices)
  self.assertEqual(self.run_policy(),'selected')
  self.assertEqual(self.last,{'type':'MVPD_IP','appId':d.CANDIDATE})
  self.assertEqual(self.foreground,'mgg4.5.channelplus');self.assertEqual(self.devices,devices)
  self.assertEqual(d._native_read()['baseline'],displaced)
  self.assertEqual(self.run_policy(),'already-selected')
 def test_protected_youtube_withdraws_only_our_selection(self):
  displaced=self.channels();self.run_policy();self.foreground='youtube.leanback.v4'
  self.assertEqual(self.run_policy(),'withdrawn');self.assertEqual(self.last,displaced)
  self.assertEqual(self.foreground,'youtube.leanback.v4')
 def test_disallowed_hdmi_and_newer_native_input_are_preserved(self):
  self.channels();self.run_policy()
  self.last={'type':'HDMI_2','appId':'com.webos.app.hdmi2'};expected=dict(self.last)
  self.assertEqual(self.run_policy(event='input'),'inconsistent-input')
  self.assertEqual(self.last,expected)
  self.foreground=expected['appId'];self.run_policy();self.assertEqual(self.last,expected)
 def test_youtube_and_hdmi_can_be_opted_in(self):
  self.foreground='youtube.leanback.v4';self.run_policy()
  policy.startup_configure({'tv':True,'youtube':True,'hdmi':True})
  self.assertEqual(self.last['appId'],d.CANDIDATE)
  self.foreground='com.webos.app.hdmi2';self.last={'type':'HDMI_2','appId':self.foreground};displaced=dict(self.last)
  self.assertEqual(self.run_policy(event='input'),'selected')
  self.assertEqual(d._native_read()['baseline'],displaced)
 def test_missing_or_platform_cover_foreground_never_withdraws_selection(self):
  self.channels();self.run_policy();expected=dict(self.last)
  for app in ('','com.webos.app.cpcover'):
   self.foreground=app;self.run_policy();self.assertEqual(self.last,expected)
 def test_visible_unselected_app_withdraws_but_never_launches(self):
  displaced=self.channels();self.run_policy();self.foreground='org.example.player'
  self.assertEqual(self.run_policy(),'withdrawn');self.assertEqual(self.last,displaced)
 def test_input_event_cannot_use_stale_youtube_to_steal_hdmi(self):
  policy.startup_configure({'tv':True,'youtube':True,'hdmi':False})
  self.foreground='youtube.leanback.v4';self.last={'type':'HDMI_1','appId':'com.webos.app.hdmi1'};expected=dict(self.last)
  self.assertEqual(self.run_policy(event='input'),'inconsistent-input');self.assertEqual(self.last,expected)
 def test_fault_contexts_and_cancellation_cannot_change_native_input(self):
  for fault in ('input','guardian','binding','failsafe','cancel','session'):
   with self.subTest(fault=fault):
    displaced=self.channels();binding=self.c.binding.read_bytes()
    inp=health.path('route-a');guard=inp.with_suffix('.guard')
    iraw=inp.read_bytes();graw=guard.read_bytes()
    if fault=='input':inp.unlink()
    if fault=='guardian':guard.unlink()
    if fault=='binding':
     v=self.c.read_binding();v['token']='stale';self.c.binding.write_text(json.dumps(v))
    if fault=='failsafe':d.FAILSAFE.touch()
    if fault=='session':result=policy.startup_reconcile('route-a','old-session')
    else:result=self.run_policy(cancelled=lambda:fault=='cancel')
    self.assertEqual(self.last,displaced);self.assertIn(result,('unavailable','canceled'))
    self.c.binding.write_bytes(binding);inp.write_bytes(iraw);guard.write_bytes(graw)
    if d.FAILSAFE.exists():d.FAILSAFE.unlink()
 def test_uncertain_select_is_journaled_and_readback_not_replayed(self):
  displaced=self.channels()
  def fail(method,payload):
   if method=='setLastInput':self.last=dict(payload);raise TimeoutError('lost ack')
  self.fault_hook=fail
  self.assertEqual(self.run_policy(),'unavailable')
  receipt=d._native_read();self.assertEqual(receipt['phase'],'selecting');self.assertEqual(receipt['pending'],'select');self.assertEqual(receipt['baseline'],displaced)
  before=sum(k=='setLastInput' for k,_ in self.calls);self.fault_hook=None
  self.assertEqual(self.run_policy(),'reconciled')
  self.assertEqual(sum(k=='setLastInput' for k,_ in self.calls),before)
  self.assertEqual(d._native_read()['phase'],'active')
  d.native_input_disable();self.assertEqual(self.last,displaced)
 def test_uncertain_withdraw_retains_direction_and_foreign_choice(self):
  displaced=self.channels();self.run_policy();self.foreground='youtube.leanback.v4'
  def fail(method,payload):
   if method=='setLastInput':self.last=dict(payload);raise TimeoutError('lost ack')
  self.fault_hook=fail;self.assertEqual(self.run_policy(),'unavailable')
  self.assertEqual(d._native_read()['pending'],'restore');self.fault_hook=None
  self.assertEqual(self.run_policy(),'reconciled');self.assertEqual(self.last,displaced)
 def test_off_cleanup_of_pending_selection_preserves_newer_hdmi(self):
  self.channels()
  def fail(method,payload):
   if method=='setLastInput':raise TimeoutError('unknown effect')
  self.fault_hook=fail;self.run_policy();self.fault_hook=None
  self.last={'type':'HDMI_3','appId':'com.webos.app.hdmi3'};expected=dict(self.last)
  self.assertEqual(self.run_policy(),'pending')
  self.c.exit(self.store.read());self.assertEqual(self.last,expected);self.assertEqual(self.devices,[])
 def lost_selection_ack(self):
  displaced=self.channels()
  def fail(method,payload):
   if method=='setLastInput':self.last=dict(payload);raise TimeoutError('lost ack')
  self.fault_hook=fail;self.assertEqual(self.run_policy(),'unavailable');self.fault_hook=None
  return displaced
 def test_new_policy_withdraws_even_after_lost_selection_ack(self):
  displaced=self.lost_selection_ack()
  before=sum(method=='setLastInput' and payload.get('appId')==d.CANDIDATE for method,payload in self.calls)
  policy.startup_configure({'tv':False,'youtube':False,'hdmi':False})
  self.assertEqual(self.last,displaced)
  self.assertEqual(sum(method=='setLastInput' and payload.get('appId')==d.CANDIDATE for method,payload in self.calls),before)
 def test_disconnect_withdraws_even_after_lost_selection_ack(self):
  displaced=self.lost_selection_ack()
  self.assertEqual(self.run_policy(withdraw=True,event='disconnect'),'withdrawn')
  self.assertEqual(self.last,displaced)
 def test_native_startup_off_withdraws_under_blank_or_platform_foreground(self):
  for app in ('','com.webos.app.cpcover'):
   self.startup='on';displaced=self.channels();self.run_policy()
   self.foreground=app;self.startup='off'
   self.assertEqual(self.run_policy(event='policy'),'withdrawn')
   self.assertEqual(self.last,displaced)
 def test_post_ready_reconciliation_applies_protected_source(self):
  self.foreground='youtube.leanback.v4'
  result={'intent':self.intent,'transaction':'route-a'}
  self.assertTrue(callable(getattr(policy,'startup_after_ready',None)),'Post-ready native policy is missing')
  self.assertEqual(policy.startup_after_ready(result),'withdrawn')
  self.assertEqual(self.last,{'type':'DTV','appId':'com.webos.app.livetv'})

 def test_observer_ends_before_activation_then_after_ready_withdraws_initial_selection(self):
  import shutdown_state
  saved=dict(self.intent);inactive=dict(saved,phase='trial')
  self.store.path.write_text(json.dumps(inactive))
  o=shutdown_state.StartupObserver('route-a',self.session,threading.Event());o.close()
  self.assertTrue(o.closed)
  self.store.path.write_text(json.dumps(saved))
  self.foreground='mgg4.5.channelplus'
  self.assertEqual(policy.startup_after_ready({'intent':saved,'transaction':'route-a'}),'withdrawn')
  self.assertEqual(self.last,{'type':'DTV','appId':'com.webos.app.livetv'})
 def test_observer_close_waits_for_enable_operation_then_withdraws(self):
  import shutdown_state
  o=shutdown_state.StartupObserver('route-a',self.session,threading.Event())
  c=policy.coordinator()
  with c.locked(self.intent):
   worker=threading.Thread(target=o.close);worker.start();time.sleep(.05)
   self.assertTrue(worker.is_alive(),'withdrawal waits for the existing operation')
  worker.join(2)
  self.assertFalse(worker.is_alive())
  self.assertEqual(self.last,{'type':'DTV','appId':'com.webos.app.livetv'})

 def test_replaced_guardian_cannot_reuse_observer_marker(self):
  guardian=self.root/'profile-guardian-ready.json'
  value=json.loads(guardian.read_text());value['pid']+=1;guardian.write_text(json.dumps(value))
  self.assertEqual(self.run_policy(),'withdrawn')
  self.assertEqual(self.last,{'type':'DTV','appId':'com.webos.app.livetv'})
 def test_close_racing_submitted_selection_waits_then_withdraws(self):
  import shutdown_state
  displaced=self.channels();o=shutdown_state.StartupObserver('route-a',self.session,threading.Event())
  worker=[];removed=threading.Event();mark=policy.startup_observer_mark
  def marker(*args):
   result=mark(*args)
   if args[-1] is False:removed.set()
   return result
  def close_during_submit(method,payload):
   if method=='setLastInput' and payload==policy.startup_ROOT_INPUT and not worker:
    t=threading.Thread(target=o.close);worker.append(t);t.start()
    self.assertTrue(removed.wait(1),'close removes eligibility before waiting for operation')
    self.assertTrue(t.is_alive())
  self.fault_hook=close_during_submit
  with patch.object(policy,'startup_observer_mark',side_effect=marker):
   self.assertEqual(self.run_policy(),'selected')
   worker[0].join(2)
  self.assertFalse(worker[0].is_alive());self.assertEqual(self.last,displaced)

 def test_dead_observer_withdrawal_does_not_require_settings_service(self):
  policy.startup_observer_mark('route-a',self.session,False)
  def fail_settings(method,payload):
   if method=='getSystemSettings':raise TimeoutError('subscription service unavailable')
  self.fault_hook=fail_settings
  self.assertEqual(self.run_policy(),'withdrawn')
  self.assertEqual(self.last,{'type':'DTV','appId':'com.webos.app.livetv'})

 def test_overlay_preserves_remembered_input_and_receipt_for_underlying_sources(self):
  for app in ('youtube.leanback.v4','com.webos.app.hdmi2','com.webos.app.livetv'):
   for allowed in (False,True):
    with self.subTest(app=app,allowed=allowed):
     self.surfaces=[]
     policy.startup_configure({'tv':allowed,'youtube':allowed,'hdmi':allowed})
     self.foreground=app
     self.surfaces=[{'appId':d.CANDIDATE,'windowType':'_WEBOS_WINDOW_TYPE_OVERLAY'},
                    {'appId':app,'windowType':'_WEBOS_WINDOW_TYPE_CARD'}]
     before=copy.deepcopy(self.last);receipt=d._native_read()
     self.assertEqual(self.run_policy(),'overlay-visible')
     self.assertEqual(self.last,before);self.assertEqual(d._native_read(),receipt)
 def test_unknown_surface_context_never_changes_remembered_input(self):
  self.channels();self.surfaces=None;before=dict(self.last);receipt=d._native_read()
  self.assertEqual(self.run_policy(),'unknown-presentation')
  self.assertEqual(self.last,before);self.assertEqual(d._native_read(),receipt)
 def test_startup_home_overlay_without_content_still_selects_root(self):
  self.channels()
  self.foreground=d.CANDIDATE
  self.surfaces=[{'appId':d.CANDIDATE,'windowType':'_WEBOS_WINDOW_TYPE_OVERLAY'}]
  self.assertEqual(self.run_policy(event='activation'),'selected')
  self.assertEqual(self.last,{'type':'MVPD_IP','appId':d.CANDIDATE})

 def test_overlay_appearing_during_observation_cannot_change_input(self):
  self.channels();before=dict(self.last);receipt=d._native_read();observations=[]
  call=self.call
  def changing(uri,payload,timeout=5):
   if uri=='luna://com.webos.surfacemanager/getForegroundAppInfo':
    observations.append(True)
    surfaces=[] if len(observations)==1 else [{'appId':d.CANDIDATE,'windowType':'_WEBOS_WINDOW_TYPE_OVERLAY'},
        {'appId':self.foreground,'windowType':'_WEBOS_WINDOW_TYPE_CARD'}]
    return dict(returnValue=True,foregroundAppInfo=surfaces)
   return call(uri,payload,timeout)
  with patch.object(self,'call',side_effect=changing):
   self.assertEqual(self.run_policy(),'overlay-visible')
  self.assertEqual(self.last,before);self.assertEqual(d._native_read(),receipt)
