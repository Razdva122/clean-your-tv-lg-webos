"""Boot-only foreground fallback, with real intent, routing and health records."""
import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
import intent_runtime as runtime
import persistent_health as health
from profile_plan import CANDIDATE,STOCK
import test_persistent_recovery as recovery_tests

class PresentationTests(unittest.TestCase):
 create_route=recovery_tests.IntegrationTests.create_route
 read=recovery_tests.IntegrationTests.read
 call=recovery_tests.IntegrationTests.call
 write=recovery_tests.IntegrationTests.write
 def tearDown(self):recovery_tests.IntegrationTests.tearDown(self)
 def setUp(self):
  recovery_tests.IntegrationTests.setUp(self)
  self.hp=patch.object(health,'ROOT',self.root/'health');self.hp.start();self.addCleanup(self.hp.stop)
  self.bp=patch.object(runtime,'boot_identity',return_value='boot-a');self.bp.start();self.addCleanup(self.bp.stop)
  health.publish('route-a',1)
  self.launches=[];self.foreground='com.webos.app.livetv';self.auto='on';self.stop_before_launch=False
  self.rpc=patch.object(self,'call',side_effect=self.rpc_call);self.rpc.start();self.addCleanup(self.rpc.stop)
  self.result={'intent':self.intent,'trial':{'transaction':'route-a'}}
 def rpc_call(self,uri,payload,timeout=5):
  self.assertLessEqual(timeout,.5)
  if uri.endswith('/getSystemSettings'):
   self.assertEqual(payload,{'category':'general','keys':['homeAutoLaunch']})
   return {'returnValue':True,'settings':{'homeAutoLaunch':self.auto}}
  if uri.endswith('/getBootStatus'):
   return {'returnValue':True,'powerStatus':'active','bootStatus':'normal','bootTarget':'hardware','firstAppLaunched':True,'firstAppId':'','signals':{'core-boot-done':True},'subscribed':False}
  if uri.endswith('/getForegroundAppInfo'):
   if self.stop_before_launch:self.c.exit(self.intent)
   return {'returnValue':True,'appId':self.foreground,'appCategory':[],'processId':'123','windowId':'window'}
  if uri.endswith('/launch'):
   self.assertEqual(payload,{'id':CANDIDATE});self.launches.append(payload['id'])
   return {'returnValue':True}
  self.fail('Unexpected RPC '+uri)
 def test_live_tv_startup_is_presented_only_after_confirmed_health(self):
  self.assertEqual(runtime.present_boot(self.c,self.result),'launch-requested')
  self.assertEqual(self.launches,[CANDIDATE]);self.assertTrue(self.store.read()['enabled'])
 def test_opened_user_app_or_already_visible_clean_is_preserved(self):
  for app in ('com.emby.app',CANDIDATE):
   with self.subTest(app=app):
    self.foreground=app
    self.assertEqual(runtime.present_boot(self.c,self.result),'preserved-foreground')
    self.assertEqual(self.launches,[])
 def test_last_input_preference_does_not_launch_clean(self):
  self.auto='off'
  self.assertEqual(runtime.present_boot(self.c,self.result),'preserved-startup-setting')
  self.assertEqual(self.launches,[])
 def test_concurrent_explicit_off_wins_before_launch(self):
  self.stop_before_launch=True
  self.assertEqual(runtime.present_boot(self.c,self.result),'unavailable')
  self.assertEqual(self.launches,[]);self.assertFalse(self.store.read()['enabled'])
 def test_missing_input_health_never_launches_or_disables_healthy_intent(self):
  health.path('route-a').unlink()
  self.assertEqual(runtime.present_boot(self.c,self.result),'unavailable')
  self.assertEqual(self.launches,[]);self.assertEqual(self.store.read(),self.intent)
 def test_unavailable_foreground_does_not_request_launch(self):
  self.foreground=None
  self.assertEqual(runtime.present_boot(self.c,self.result),'preserved-foreground')
  self.assertEqual(self.launches,[])
 def test_failed_launch_is_not_retried_or_converted_to_intent_fault(self):
  original=self.rpc_call
  def fail_launch(uri,payload,timeout=5):
   if uri.endswith('/launch'):raise TimeoutError('unknown launch outcome')
   return original(uri,payload,timeout)
  self.call.side_effect=fail_launch
  self.assertEqual(runtime.present_boot(self.c,self.result),'unavailable')
  self.assertEqual(self.store.read(),self.intent)
 def test_software_reboot_does_not_request_hardware_startup_fallback(self):
  original=self.rpc_call
  def software_boot(uri,payload,timeout=5):
   reply=original(uri,payload,timeout)
   if uri.endswith('/getBootStatus'):reply['bootTarget']='software'
   return reply
  self.call.side_effect=software_boot
  self.assertEqual(runtime.present_boot(self.c,self.result),'preserved-startup-setting')
  self.assertEqual(self.launches,[])
 def test_explicit_off_during_inflight_launch_completes_and_stays_off(self):
  original=self.rpc_call
  def stop_during_launch(uri,payload,timeout=5):
   if uri.endswith('/launch'):self.c.exit(self.intent)
   return original(uri,payload,timeout)
  self.call.side_effect=stop_during_launch
  self.assertEqual(runtime.present_boot(self.c,self.result),'superseded')
  self.assertFalse(self.store.read()['enabled']);self.assertEqual(self.read(),self.baseline)
 def test_app_opened_while_health_is_checked_is_preserved(self):
  original=health.require_fresh
  def opened_app(tx):
   self.foreground='com.emby.app';return original(tx)
  with patch.object(health,'require_fresh',side_effect=opened_app):
   self.assertEqual(runtime.present_boot(self.c,self.result),'preserved-foreground')
  self.assertEqual(self.launches,[])


class WakePresentationTests(PresentationTests):
 def setUp(self):
  super().setUp()
  for name in ('require_guardian',):
   guard=patch.object(health,name);guard.start();self.addCleanup(guard.stop)
  guard=patch.object(runtime.d,'active_guardian',return_value=True);guard.start();self.addCleanup(guard.stop)
  c=patch.object(runtime,'coordinator',return_value=self.c);c.start();self.addCleanup(c.stop)
 def wake(self,cancelled=lambda:False):
  return runtime.present_wake('route-a','boot-a',cancelled)
 def test_wake_is_independent_of_stale_boot_manager_target(self):
  original=self.rpc_call
  def rpc(uri,payload,timeout=.5):
   self.assertFalse(uri.endswith('/getBootStatus'),'wake must use the observed live power edge')
   return original(uri,payload,timeout)
  self.call.side_effect=rpc
  self.assertEqual(self.wake(),'launch-requested');self.assertEqual(self.launches,[CANDIDATE])
 def test_wake_preserves_other_missing_or_already_visible_foreground(self):
  for app in ('synthetic.channels',None,CANDIDATE,'com.emby.app'):
   self.foreground=app
   self.assertEqual(self.wake(),'preserved-foreground');self.assertEqual(self.launches,[])
 def test_wake_off_failsafe_session_guardian_and_package_guards(self):
  with patch.object(runtime,'boot_identity',return_value='new'):
   self.assertEqual(self.wake(),'unavailable')
  with patch.object(health,'require_guardian',side_effect=ValueError('expired')):
   self.assertEqual(self.wake(),'unavailable')
  with patch.object(runtime.d,'active_guardian',return_value=False):
   self.assertEqual(self.wake(),'unavailable')
  with patch.object(runtime.d,'home_present',return_value=False):
   self.assertEqual(self.wake(),'unavailable')
  with patch.object(runtime.d,'FAILSAFE',self.root/'failsafe'):
   runtime.d.FAILSAFE.touch();self.assertEqual(self.wake(),'unavailable')
  self.assertEqual(self.launches,[]);self.assertTrue(self.store.read()['enabled'])
 def test_cancelled_stream_before_or_after_foreground_never_launches(self):
  self.assertEqual(self.wake(lambda:True),'unavailable')
  checks=[]
  def cancelled():checks.append(True);return len(checks)>1
  self.assertEqual(self.wake(cancelled),'unavailable');self.assertEqual(self.launches,[])
 def test_explicit_off_during_foreground_wins(self):
  self.stop_before_launch=True
  self.assertEqual(self.wake(),'unavailable');self.assertEqual(self.launches,[])
  self.assertFalse(self.store.read()['enabled'])
 def test_stale_binding_and_restored_route_never_launch(self):
  self.assertEqual(runtime.present_wake('different','boot-a',lambda:False),'unavailable')
  self.target.unlink()
  self.assertEqual(self.wake(),'unavailable');self.assertEqual(self.launches,[])
 def test_optional_error_does_not_disable_home(self):
  self.call.side_effect=TimeoutError('optional')
  self.assertEqual(self.wake(),'unavailable');self.assertEqual(self.store.read(),self.intent)
 def test_health_is_checked_again_after_foreground(self):
  original=self.rpc_call
  def expire(uri,payload,timeout=.5):
   reply=original(uri,payload,timeout)
   if uri.endswith('/getForegroundAppInfo'):health.path('route-a').unlink()
   return reply
  self.call.side_effect=expire
  self.assertEqual(self.wake(),'unavailable');self.assertEqual(self.launches,[])

 def wake_decision(self):
  import json
  return json.loads((runtime.d.STATE/'boot-decision.json').read_text())
 def test_missing_post_wake_health_is_recorded_without_promotion_or_launch(self):
  health.path('route-a').unlink()
  self.assertEqual(self.wake(),'unavailable')
  decision=self.wake_decision()
  self.assertEqual(decision['event'],'wake-presentation')
  self.assertEqual(decision['outcome'],'unavailable')
  self.assertEqual(decision['context']['stage'],'health-routing')
  self.assertEqual(self.store.read(),self.intent);self.assertEqual(self.launches,[])
 def test_real_power_edge_with_missing_health_reaches_a_recorded_refusal(self):
  import json,shutdown_state as power
  from unittest.mock import Mock
  health.path('route-a').unlink()
  monitor=power.Monitor();child=Mock();child.stdout.fileno.return_value=7;child.poll.return_value=None
  frames=b'{"returnValue":true,"subscribed":true,"state":"Active"}{"returnValue":true,"state":"Active Standby"}{"returnValue":true,"state":"Active"}'
  chunks=[frames]
  def read(*args):
   if chunks:return chunks.pop()
   self.assertIsNotNone(monitor.presentation)
   monitor.presentation.join(1)
   self.assertFalse(monitor.presentation.is_alive())
   self.assertEqual(self.wake_decision()['context']['stage'],'health-routing')
   return b''
  with patch.object(power.subprocess,'Popen',return_value=child),patch.object(power.select,'select',return_value=([child.stdout],[],[])),patch.object(power.os,'read',side_effect=read):
   try:
    power.observe_power('route-a','boot-a',monitor,wake=lambda cancelled:monitor.request_wake('route-a','boot-a',cancelled))
   finally:monitor.close()
  snapshot=json.loads(health.path('route-a').with_suffix('.wake').read_text())
  self.assertEqual(snapshot['wake_count'],1);self.assertEqual(snapshot['event'],'eof')
  self.assertEqual(self.launches,[]);self.assertEqual(self.store.read(),self.intent)

 def test_cancelled_session_and_disabled_wake_refusals_are_recorded(self):
  import json
  cases=(('cancelled',lambda:self.wake(lambda:True)),
         ('session',lambda:runtime.present_wake('route-a','old-boot',lambda:False)))
  for stage,run in cases:
   self.assertEqual(run(),'unavailable')
   self.assertEqual(self.wake_decision()['context']['stage'],stage)
  self.store.path.write_text(json.dumps(dict(self.intent,phase='disabled',enabled=False)))
  self.assertEqual(self.wake(),'unavailable')
  self.assertEqual(self.wake_decision()['context']['stage'],'intent')
 def test_optional_rpc_failure_records_stage_without_private_error_or_app_id(self):
  def private_error(*args,**kwargs):raise TimeoutError('private address and token')
  self.call.side_effect=private_error
  self.assertEqual(self.wake(),'unavailable')
  decision=self.wake_decision()
  self.assertEqual(decision['context']['stage'],'startup-setting')
  self.assertNotIn('private',str(decision))
  self.assertEqual(self.store.read(),self.intent)
 def test_diagnostic_write_failure_cannot_change_wake_outcome(self):
  with patch('boot_gate.audit',side_effect=OSError('diagnostic unavailable')):
   self.assertEqual(self.wake(),'launch-requested')
  self.assertEqual(self.launches,[CANDIDATE])

 def test_disabled_stopping_and_trial_intent_cannot_be_promoted_by_wake(self):
  import json
  for phase,enabled in (('disabled',False),('stopping',True),('trial',False)):
   self.store.path.write_text(json.dumps(dict(self.intent,phase=phase,enabled=enabled)))
   self.assertEqual(self.wake(),'unavailable');self.assertEqual(self.launches,[])
   self.assertEqual(self.store.read()['phase'],phase)
 def test_native_last_input_setting_is_preserved_on_wake(self):
  self.auto='off'
  self.assertEqual(self.wake(),'preserved-startup-setting');self.assertEqual(self.launches,[])
 def test_explicit_off_during_wake_launch_stays_off(self):
  original=self.rpc_call
  def off(uri,payload,timeout=.5):
   if uri.endswith('/launch'):self.c.exit(self.intent)
   return original(uri,payload,timeout)
  self.call.side_effect=off
  self.assertEqual(self.wake(),'superseded');self.assertFalse(self.store.read()['enabled'])
  self.assertEqual(self.read(),self.baseline)
 def test_new_off_during_launch_is_reported_superseded_without_retry(self):
  original=self.rpc_call;cancelled=[False]
  def off(uri,payload,timeout=.5):
   if uri.endswith('/launch'):cancelled[0]=True
   return original(uri,payload,timeout)
  self.call.side_effect=off
  self.assertEqual(self.wake(lambda:cancelled[0]),'superseded')
  self.assertEqual(self.launches,[CANDIDATE]);self.assertTrue(self.store.read()['enabled'])

 def test_live_observer_off_eof_or_close_cancels_worker_stalled_in_health(self):
  import threading
  import shutdown_state as power
  from unittest.mock import Mock
  for end in ('off','eof','close'):
   with self.subTest(end=end):
    entered=threading.Event();release=threading.Event();monitor=power.Monitor()
    original=self.c._healthy
    def stalled(intent):
     entered.set();release.wait(2);return original(intent)
    child=Mock();child.stdout.fileno.return_value=7;child.poll.return_value=None
    chunks=[b'{"returnValue":true,"subscribed":true,"state":"Active"}{"returnValue":true,"state":"Active Standby"}{"returnValue":true,"state":"Active"}'];sent_off=[False]
    def read(*args):
     if chunks:return chunks.pop()
     self.assertTrue(entered.wait(1))
     if end=='close':monitor.set()
     if end=='off':
      if not sent_off[0]:
       sent_off[0]=True;return b'{"returnValue":true,"state":"Active Standby"}'
      # OFF has been parsed; test its revision guard before EOF/stop can mask it.
      self.assertFalse(monitor.is_set());release.set();monitor.presentation.join(1)
      self.assertFalse(monitor.presentation.is_alive());self.assertEqual(self.launches,[])
     return b''
    with patch.object(self.c,'_healthy',side_effect=stalled),patch.object(power.subprocess,'Popen',return_value=child),patch.object(power.select,'select',return_value=([child.stdout],[],[])),patch.object(power.os,'read',side_effect=read):
     try:
      power.observe_power('route-a','boot-a',monitor,wake=lambda cancelled:monitor.request_wake('route-a','boot-a',cancelled))
     finally:release.set();monitor.close()
    self.assertEqual(self.launches,[]);self.assertTrue(self.store.read()['enabled'])

class ForegroundDecisionTests(PresentationTests):
 def test_cold_boot_preserves_unknown_and_reports_only_redacted_provenance(self):
  self.foreground='synthetic.private.app'
  self.assertEqual(runtime.present_boot(self.c,self.result),'preserved-foreground')
  self.assertEqual(self.result['presentation_context'],{'foreground_kind':'other-or-missing','first_app_matches':None})
  self.assertNotIn(self.foreground,str(self.result['presentation_context']))
 def test_cold_boot_already_visible_root_is_distinguished_without_relaunch(self):
  self.foreground=CANDIDATE
  self.assertEqual(runtime.present_boot(self.c,self.result),'preserved-foreground')
  self.assertEqual(self.result['presentation_context']['foreground_kind'],'root')
  self.assertEqual(self.launches,[])

 def test_firmware_first_app_match_alone_never_authorizes_unknown_app(self):
  self.foreground='synthetic.private.app';original=self.rpc_call
  def boot(uri,payload,timeout=.5):
   reply=original(uri,payload,timeout)
   if uri.endswith('/getBootStatus'):reply['firstAppId']=self.foreground
   return reply
  self.call.side_effect=boot
  self.assertEqual(runtime.present_boot(self.c,self.result),'preserved-foreground')
  self.assertEqual(self.result['presentation_context'],{'foreground_kind':'other-or-missing','first_app_matches':True})
  self.assertEqual(self.launches,[])


class NativeChannelTests(PresentationTests):
 """The recorded C3 store-managed partner TV surface, never a CP wildcard."""
 def setUp(self):
  super().setUp()
  self.foreground='mgg4.5.channelplus'
  self.metadata=dict(id=self.foreground,type='web',vendor='LifeStream ltd.',
   folderPath='/media/cryptofs/apps/usr/palm/applications/'+self.foreground,
   activeFolderPath='/media/cryptofs/apps/usr/palm/applications/'+self.foreground,
   CPApp=True,internalInstallationOnly=True,systemApp=False,trustLevel='default',removable=True)
  self.info_calls=0
 def present(self):
  return runtime.present_boot(self.c,self.result)
 def rpc_call(self,uri,payload,timeout=.5):
  if uri.endswith('/getAppInfo'):
   self.assertEqual(payload,{'id':'mgg4.5.channelplus'});self.assertLessEqual(timeout,.5)
   self.info_calls+=1;return {'returnValue':True,'appInfo':self.metadata}
  return PresentationTests.rpc_call(self,uri,payload,timeout)
 def test_confirmed_native_tv_surface_is_presented(self):
  self.assertEqual(self.present(),'launch-requested')
  self.assertEqual(self.launches,[CANDIDATE]);self.assertEqual(self.info_calls,1)
 def test_missing_mismatched_or_developer_metadata_is_preserved(self):
  original=dict(self.metadata)
  for key,value in (('id','different'),('type','native'),('vendor','different'),
   ('folderPath','/media/developer/apps/usr/palm/applications/mgg4.5.channelplus'),
   ('activeFolderPath','/media/developer/apps/usr/palm/applications/mgg4.5.channelplus'),
   ('folderPath',original['folderPath']+'/../other'),('CPApp',False),('CPApp',1),
   ('internalInstallationOnly',False),('internalInstallationOnly',1)):
   with self.subTest(key=key,value=value):
    self.metadata=dict(original);self.metadata[key]=value
    self.assertEqual(self.present(),'preserved-foreground');self.assertEqual(self.launches,[])
  for key in ('id','type','vendor','folderPath','activeFolderPath','CPApp','internalInstallationOnly'):
   with self.subTest(missing=key):
    self.metadata=dict(original);del self.metadata[key]
    self.assertEqual(self.present(),'preserved-foreground');self.assertEqual(self.launches,[])
 def test_other_ids_are_never_queried_or_classified_by_cp_flags(self):
  for app in ('mgg4.5.channelplus.other','mgg3.0.channelplus','third.party.app',None):
   self.foreground=app
   self.assertEqual(self.present(),'preserved-foreground')
  self.assertEqual(self.info_calls,0);self.assertEqual(self.launches,[])
 def test_user_app_opened_during_metadata_check_is_preserved(self):
  original=self.rpc_call
  def opened(uri,payload,timeout=.5):
   result=original(uri,payload,timeout)
   if uri.endswith('/getAppInfo'):self.foreground='third.party.app'
   return result
  self.call.side_effect=opened
  self.assertEqual(self.present(),'preserved-foreground')
  self.assertEqual(self.launches,[])
 def test_current_root_opened_during_metadata_check_is_preserved(self):
  original=self.rpc_call
  def opened(uri,payload,timeout=.5):
   result=original(uri,payload,timeout)
   if uri.endswith('/getAppInfo'):self.foreground=CANDIDATE
   return result
  self.call.side_effect=opened
  self.assertEqual(self.present(),'preserved-foreground')
  self.assertEqual(self.launches,[])
 def test_metadata_timeout_does_not_disable_healthy_home(self):
  original=self.rpc_call
  def unavailable(uri,payload,timeout=.5):
   if uri.endswith('/getAppInfo'):raise TimeoutError('optional metadata')
   return original(uri,payload,timeout)
  self.call.side_effect=unavailable
  self.assertEqual(self.present(),'unavailable')
  self.assertEqual(self.store.read(),self.intent);self.assertEqual(self.launches,[])
 def test_explicit_off_during_metadata_wins(self):
  original=self.rpc_call
  def off(uri,payload,timeout=.5):
   result=original(uri,payload,timeout)
   if uri.endswith('/getAppInfo'):self.c.exit(self.intent)
   return result
  self.call.side_effect=off
  self.assertEqual(self.present(),'unavailable')
  self.assertFalse(self.store.read()['enabled']);self.assertEqual(self.launches,[])
 def test_stale_health_during_metadata_does_not_launch_or_disable(self):
  original=self.rpc_call
  def expired(uri,payload,timeout=.5):
   result=original(uri,payload,timeout)
   if uri.endswith('/getAppInfo'):health.path('route-a').unlink()
   return result
  self.call.side_effect=expired
  self.assertEqual(self.present(),'unavailable')
  self.assertEqual(self.store.read(),self.intent);self.assertEqual(self.launches,[])
 def test_native_last_input_setting_avoids_even_metadata_query(self):
  self.auto='off'
  self.assertEqual(self.present(),'preserved-startup-setting')
  self.assertEqual(self.info_calls,0);self.assertEqual(self.launches,[])
 def test_guarded_wake_uses_same_narrow_native_tv_classification(self):
  with patch.object(runtime,'coordinator',return_value=self.c),patch.object(health,'require_guardian'),patch.object(runtime.d,'active_guardian',return_value=True):
   self.assertEqual(runtime.present_wake('route-a','boot-a',lambda:False),'launch-requested')
  self.assertEqual(self.launches,[CANDIDATE]);self.assertEqual(self.info_calls,1)


class NativeWakeChannelTests(NativeChannelTests):
 """Run all metadata rejection, app-switch and final-guard cases on wake too."""
 def present(self):
  with patch.object(runtime,'coordinator',return_value=self.c),patch.object(health,'require_guardian'),patch.object(runtime.d,'active_guardian',return_value=True):
   return runtime.present_wake('route-a','boot-a',lambda:False)
