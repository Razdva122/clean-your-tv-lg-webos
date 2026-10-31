import copy,json,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
import device_adapter as d
from persistent_store import Store
from persistent_recovery import Coordinator
from profile_recovery import prepare,PAYLOAD
from profile_plan import STOCK,CANDIDATE,snapshot
from test_root_runtime_profile_plan import response

class IntegrationTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve();self.root.chmod(0o700)
  self.apps=self.root/'apps/usr/palm/applications';self.apps.mkdir(parents=True);
  for shared in (self.apps,self.apps.parent,self.apps.parent.parent,self.apps.parents[2]):shared.chmod(0o777)
  (self.apps/CANDIDATE).mkdir();(self.apps/CANDIDATE/'appinfo.json').write_text(json.dumps({'id':CANDIDATE,'type':'web'}))
  import package_identity
  meta=self.apps/CANDIDATE/'appinfo.json'
  meta.write_text(json.dumps({'id':CANDIDATE,'type':'web','version':'1.0.0'}))
  pkg=self.apps.parents[0]/'packages'/CANDIDATE/'packageinfo.json';pkg.parent.mkdir(parents=True)
  pkg.write_text(json.dumps({'id':CANDIDATE,'app':CANDIDATE,'version':'1.0.0'}))
  original={'usr/palm/applications/'+CANDIDATE+'/appinfo.json':package_identity.digest(meta.read_bytes()),'usr/palm/packages/'+CANDIDATE+'/packageinfo.json':package_identity.digest(pkg.read_bytes())}
  self.target=self.root/'profile';self.home=STOCK;self.baseline=snapshot(response(),STOCK)
  self.patches=[patch.object(package_identity,'inventory',return_value=original),patch.object(d,'APPLICATIONS',self.apps),patch.object(d,'STATE',self.root),patch.object(d,'TARGET',self.target),patch.object(d,'EXPECTED_UID',os.getuid()),patch.object(d,'read',side_effect=self.read),patch.object(d,'sam_transport',return_value=self)]
  for p in self.patches:p.start()
  self.store=Store(self.root);self.c=Coordinator(self.store)
  s=self.store.read();self.intent,_=self.store.apply(s,dict(kind='enable',generation=0,boot='boot-a',token='attempt-a'))
  self.create_route('route-a');self.c.bind(self.intent,'route-a')
  self.intent,_=self.store.apply(self.intent,dict(kind='confirmed',generation=1,token='attempt-a'))
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  self.tmp.cleanup()
 def create_route(self,tx):
  self.target.write_bytes(PAYLOAD);self.target.chmod(0o600);self.home=CANDIDATE
  info=self.target.stat();j=prepare(response(),STOCK)
  j.update(transaction=tx,candidate_identity=dict(device=info.st_dev,inode=info.st_ino),deadline=100)
  d.save(j)
 def read(self):
  b=copy.deepcopy(self.baseline);b['sam_home']=self.home
  if self.target.exists():
   b['profiles']['defaultApps']['categories']['home']=CANDIDATE
   b['profiles']['idleApp']['appId']=CANDIDATE
  return b
 def call(self,uri,payload):return {'returnValue':True}
 def write(self,target):self.home=target
 def test_exit_disables_intent_before_real_routing_restore(self):
  original=d.restore_once;seen=[]
  def restore(**kw):seen.append(self.store.read()['enabled']);return original(**kw)
  with patch.object(d,'restore_once',side_effect=restore):r=self.c.exit(self.intent)
  self.assertEqual(seen,[False]);self.assertEqual(r['effect'],'none')
  self.assertEqual(self.read(),self.baseline);self.assertFalse(self.target.exists())
  self.assertEqual(self.store.read()['phase'],'disabled')
 def test_package_loss_during_recovery_or_before_restart_never_leaves_enabled_intent(self):
  starting=self.c.boot(self.intent,'boot-b','attempt-b',False)['intent']
  with patch.object(d,'home_present',return_value=False):
   with self.assertRaises(ValueError):self.c.restart(starting)
  self.assertFalse(self.store.read()['enabled']);self.assertEqual(self.read(),self.baseline)
 def test_dispatch_same_boot_shutdown_recovers_when_package_disappears(self):
  import intent_runtime
  self.store.apply(self.intent,dict(kind='shutdown',generation=1,token='attempt-a'))
  with patch.object(d,'home_present',return_value=False),patch.object(intent_runtime,'boot_identity',return_value='boot-a'):
   self.assertEqual(intent_runtime._boot(),'restored')
  self.assertEqual(self.store.read()['phase'],'disabled');self.assertEqual(self.read(),self.baseline)
 def test_package_loss_disables_even_a_shutdown_and_restores_routing(self):
  from persistent_recovery import bound_exit
  stopping,_=self.store.apply(self.intent,dict(kind='shutdown',generation=1,token='attempt-a'))
  with patch.object(d,'home_present',return_value=False):
   self.assertTrue(bound_exit('route-a'))
  self.assertEqual(self.store.read()['phase'],'disabled');self.assertEqual(self.read(),self.baseline)
 def test_package_loss_on_same_boot_cannot_preserve_or_rearm_home(self):
  with patch.object(d,'home_present',return_value=False):r=self.c.boot(self.intent,'boot-a','attempt-b',False)
  self.assertEqual(r['effect'],'none');self.assertFalse(r['intent']['enabled']);self.assertEqual(self.read(),self.baseline)
 def test_normal_boot_requests_restart_only_after_exact_restore(self):
  r=self.c.boot(self.intent,'boot-b','attempt-b',False)
  self.assertEqual(r['effect'],'start_guarded');self.assertEqual(self.read(),self.baseline)
  self.assertEqual(r['intent']['phase'],'starting')
  self.assertTrue(r['intent']['enabled'])
 def test_boot_rearms_protection_without_reopening_home_over_user_app(self):
  starting=self.c.boot(self.intent,'boot-b','attempt-b',False)['intent']
  foreground=['com.emby.app']
  def start(before_publish):
   self.create_route('route-b');before_publish('route-b')
   return {'transaction':'route-b'}
  def call(uri,payload):
   if uri.endswith('/launch'):foreground[0]=payload['id']
   return {'returnValue':True}
  with patch('emergency_trial.start',side_effect=start),patch('persistent_health.require_fresh') as fresh,patch('persistent_health.require_guardian') as guardian,patch.object(d,'active_guardian',return_value=True),patch.object(self,'call',side_effect=call):
   result=self.c.restart(starting)
  fresh.assert_called_with('route-b');guardian.assert_called_once_with('route-b')
  self.assertEqual(result['intent']['phase'],'active')
  self.assertTrue(result['intent']['enabled']);self.assertEqual(self.home,CANDIDATE)
  self.assertEqual(foreground,['com.emby.app'])
 def test_failsafe_does_not_request_restart(self):
  r=self.c.boot(self.intent,'boot-a','failsafe',True)
  self.assertEqual(r['effect'],'none');self.assertFalse(r['intent']['enabled'])
 def test_duplicate_boot_preserves_current_route(self):
  with patch.object(d,'restore_once') as restore:
   r=self.c.boot(self.intent,'boot-a','ignored',False)
   restore.assert_not_called();self.assertEqual(r['effect'],'none')
  self.assertEqual(self.home,CANDIDATE)
 def test_stale_exit_does_not_disable_newer_attempt(self):
  old=self.intent;r=self.c.exit(old);s=r['intent']
  new,_=self.store.apply(s,dict(kind='enable',generation=s['generation'],boot='boot-a',token='new'))
  self.create_route('route-new');self.c.bind(new,'route-new')
  with self.assertRaises(ValueError):self.c.exit(old)
  self.assertEqual(self.store.read(),new);self.assertEqual(self.home,CANDIDATE)
 def test_foreign_routing_transaction_not_modified(self):
  j=d.safe_json(self.root/'profile-trial.json');j['transaction']='foreign';d.save(j)
  with patch.object(d,'restore_once') as restore:
   with self.assertRaises(ValueError):self.c.exit(self.intent)
   restore.assert_not_called()
  self.assertFalse(self.store.read()['enabled']);self.assertTrue(self.target.exists())
 def test_conflict_blocks_boot_restart(self):
  self.target.write_bytes(b'foreign bytes')
  with self.assertRaises(ValueError):self.c.boot(self.intent,'boot-b','b',False)
  self.assertFalse(self.store.read()['enabled']);self.assertEqual(self.target.read_bytes(),b'foreign bytes')
 def test_claimed_restore_with_wrong_readback_does_not_restart(self):
  with patch.object(d,'restore_once',return_value='restored'):
   with self.assertRaises(ValueError):self.c.boot(self.intent,'boot-b','b',False)
  self.assertFalse(self.store.read()['enabled'])
 def test_reload_after_disabling_before_recovery(self):
  with patch.object(d,'restore_once',side_effect=OSError('lost connection')):
   with self.assertRaises(OSError):self.c.exit(self.intent)
  c=Coordinator(Store(self.root));s=c.store.read();self.assertFalse(s['enabled'])
  r=c.resume_recovery(s);self.assertEqual(r['effect'],'none');self.assertEqual(self.read(),self.baseline)
 def test_stale_binding_and_missing_binding_rejected(self):
  (self.root/'persistent-binding.json').unlink()
  with self.assertRaises(ValueError):self.c.exit(self.intent)
  self.assertFalse(self.store.read()['enabled']);self.assertTrue(self.target.exists())
 def test_bind_rejects_mismatched_route(self):
  with self.assertRaises(ValueError):self.c.bind(self.intent,'other')
 def test_intent_fault_during_recovery_is_not_overwritten(self):
  original=d.restore_once
  def restore(**kw):
   s=self.store.read();self.store.apply(s,dict(kind='fault',generation=s['generation'],token=s['token']))
   return original(**kw)
  with patch.object(d,'restore_once',side_effect=restore):
   with self.assertRaises(ValueError):self.c.boot(self.intent,'boot-b','b',False)
  self.assertFalse(self.store.read()['enabled']);self.assertEqual(self.read(),self.baseline)
 def test_bound_escape_disables_before_restore(self):
  from persistent_recovery import bound_exit
  self.assertTrue(bound_exit('route-a',reason='escape'))
  self.assertFalse(self.store.read()['enabled']);self.assertEqual(self.read(),self.baseline)
 def test_unbound_legacy_route_is_not_adopted(self):
  from persistent_recovery import bound_exit
  self.assertIsNone(bound_exit('unrelated'));self.assertEqual(self.store.read(),self.intent)
 def test_new_trial_binds_before_start_returns(self):
  self.c.exit(self.intent);s=self.store.read()
  def start(before_publish):
   self.create_route('route-b');before_publish('route-b')
   self.assertEqual(self.c.read_binding()['transaction'],'route-b')
   return {'transaction':'route-b'}
  with patch('emergency_trial.start',side_effect=start):
   r=self.c.start_trial(s,'boot-a','attempt-b')
  self.assertFalse(r['persistent']);self.assertFalse(r['intent']['enabled'])
 def test_failed_start_disables_intent(self):
  self.c.exit(self.intent);s=self.store.read()
  with patch('emergency_trial.start',side_effect=RuntimeError('observer unavailable')):
   with self.assertRaises(RuntimeError):self.c.start_trial(s,'boot-a','attempt-b')
  self.assertFalse(self.store.read()['enabled']);self.assertEqual(self.store.read()['phase'],'recovering')
 def test_failed_first_start_before_route_can_reconcile_stock(self):
  self.c.exit(self.intent)
  (self.root/'persistent-binding.json').unlink();(self.root/'profile-trial.json').unlink()
  s=self.store.read()
  with patch('emergency_trial.start',side_effect=RuntimeError('not registered')):
   with self.assertRaises(RuntimeError):self.c.start_trial(s,'boot-a','new')
  r=self.c.resume_recovery(self.store.read())
  self.assertEqual(r['intent']['phase'],'disabled');self.assertEqual(r['effect'],'none')
 def test_dispatch_does_not_capture_later_legacy_trial(self):
  import intent_runtime
  self.c.exit(self.intent);self.create_route('legacy-trial')
  with patch.object(intent_runtime,'boot_identity',return_value='boot-b'):
   self.assertIsNone(intent_runtime.boot())
   self.assertIsNone(intent_runtime.restore())
  self.assertEqual(self.home,CANDIDATE)

class ShutdownTests(IntegrationTests):
 def setUp(self):
  super().setUp()
  boot=patch('intent_runtime.boot_identity',return_value='boot-a')
  boot.start();self.addCleanup(boot.stop)
 def decision(self,proof=False,home=True,failsafe=False,unknown=False,reason='observer_exit'):
  import io
  from contextlib import redirect_stdout
  from types import SimpleNamespace
  from unittest.mock import Mock
  from persistent_recovery import bound_exit
  flag=SimpleNamespace(exists=Mock(return_value=failsafe));output=io.StringIO()
  with patch.object(d,'home_present',return_value=home),patch.object(d,'FAILSAFE',flag),patch('intent_runtime.boot_identity',return_value='boot-a',side_effect=ValueError('unavailable') if unknown else None),patch('shutdown_state.stopping',return_value=proof) as stopping,redirect_stdout(output):
   self.assertTrue(bound_exit('route-a',reason=reason))
  events=[json.loads(line) for line in output.getvalue().splitlines() if line.startswith('{')]
  event=next(value for value in events if value.get('event')=='bound-exit-decision')
  self.assertTrue({'home_present','failsafe_present','current_session_known','same_session','shutdown_proof'}<=set(event),'Decision diagnostics missing')
  return event,stopping.call_args_list,flag.exists.call_count

 def test_decision_reports_false_proof_once_and_still_disables(self):
  event,calls,_=self.decision(proof=False)
  self.assertEqual(event['shutdown_proof'],False);self.assertEqual(len(calls),1)
  self.assertEqual(calls[0].args,('route-a',));self.assertFalse(event['shutdown'])
  self.assertTrue(event['home_present']);self.assertFalse(event['failsafe_present'])
  self.assertTrue(event['current_session_known']);self.assertTrue(event['same_session'])
  self.assertFalse(self.store.read()['enabled']);self.assertEqual(self.read(),self.baseline)

 def test_decision_reports_true_proof_once_and_still_retains(self):
  event,calls,_=self.decision(proof=True)
  self.assertTrue(event['shutdown_proof']);self.assertTrue(event['shutdown']);self.assertEqual(len(calls),1)
  self.assertEqual(self.store.read()['phase'],'stopping');self.assertTrue(self.store.read()['enabled'])
  self.assertTrue(self.target.exists())

 def test_decision_reports_failsafe_without_reading_power_proof(self):
  event,calls,reads=self.decision(failsafe=True)
  self.assertTrue(event['failsafe_present']);self.assertIsNone(event['shutdown_proof'])
  self.assertEqual(calls,[]);self.assertEqual(reads,1);self.assertFalse(event['shutdown'])
  self.assertFalse(self.store.read()['enabled']);self.assertEqual(self.read(),self.baseline)

 def test_decision_reports_unknown_session_without_reading_power_proof(self):
  event,calls,_=self.decision(unknown=True)
  self.assertFalse(event['current_session_known']);self.assertIsNone(event['same_session'])
  self.assertIsNone(event['shutdown_proof']);self.assertEqual(calls,[])
  self.assertFalse(self.store.read()['enabled']);self.assertEqual(self.read(),self.baseline)

 def test_decision_preserves_home_missing_short_circuit(self):
  event,calls,reads=self.decision(home=False)
  self.assertFalse(event['home_present']);self.assertIsNone(event['failsafe_present'])
  self.assertIsNone(event['shutdown_proof']);self.assertEqual(calls,[]);self.assertEqual(reads,0)
  self.assertFalse(self.store.read()['enabled']);self.assertEqual(self.read(),self.baseline)

 def test_decision_does_not_requery_already_stopping_intent(self):
  self.intent,_=self.store.apply(self.intent,dict(kind='shutdown',generation=1,token='attempt-a'))
  event,calls,_=self.decision()
  self.assertTrue(event['shutdown']);self.assertIsNone(event['shutdown_proof']);self.assertEqual(calls,[])
  self.assertEqual(self.store.read()['phase'],'stopping');self.assertTrue(self.store.read()['enabled'])

 def test_decision_escape_never_queries_power_or_retains_intent(self):
  event,calls,_=self.decision(proof=True,reason='escape')
  self.assertIsNone(event['shutdown_proof']);self.assertEqual(calls,[]);self.assertFalse(event['shutdown'])
  self.assertFalse(self.store.read()['enabled']);self.assertEqual(self.read(),self.baseline)

 def test_input_observer_accepts_retained_shutdown_profile(self):
  from emergency_trial import recover
  with patch('shutdown_state.stopping',return_value=True):
   self.assertTrue(recover('route-a','observer_exit'))
  self.assertTrue(self.target.exists());self.assertEqual(self.home,CANDIDATE)
  self.assertEqual(self.store.read()['phase'],'stopping')
 def test_system_shutdown_keeps_home_profile_for_first_app_on_next_boot(self):
  from persistent_recovery import bound_exit
  before=self.read();binding=self.c.read_binding();payload=self.target.read_bytes()
  with patch('shutdown_state.stopping',return_value=True):
   self.assertTrue(bound_exit('route-a'))
  self.assertEqual(self.read(),before);self.assertEqual(self.target.read_bytes(),payload)
  self.assertEqual(self.c.read_binding(),binding)
  self.assertTrue(self.store.read()['enabled']);self.assertEqual(self.store.read()['phase'],'stopping')
  outcome=self.c.boot(self.store.read(),'boot-b','new-boot',False)
  self.assertEqual(outcome['effect'],'start_guarded');self.assertEqual(self.read(),self.baseline)
 def test_explicit_escape_during_shutdown_still_disables_intent(self):
  from persistent_recovery import bound_exit
  with patch('shutdown_state.stopping',return_value=True):
   self.assertTrue(bound_exit('route-a',reason='escape'))
  self.assertFalse(self.store.read()['enabled'])

 def test_firmware_request_preserves_intent_with_systemctl_unavailable(self):
  import shutdown_state as shutdown,persistent_health as health
  from persistent_recovery import bound_exit
  reason=self.root/'poweroff_reason'
  with patch.object(health,'ROOT',self.root/'health'),patch('intent_runtime.boot_identity',return_value='boot-a'),patch.object(shutdown,'query',return_value=False):
   observer=shutdown.PowerReason(reason);self.assertFalse(observer.poll())
   reason.write_text('poweroff_reason=remoteKey')
   self.assertTrue(observer.poll());shutdown.record('route-a',source='firmware-remoteKey')
   self.assertTrue(bound_exit('route-a',reason='observer_exit'))
  self.assertTrue(self.store.read()['enabled']);self.assertEqual(self.home,CANDIDATE)
  self.assertTrue(self.target.exists())
  outcome=self.c.boot(self.store.read(),'boot-b','new-boot',False)
  self.assertEqual(outcome['effect'],'start_guarded')
 def test_same_input_fault_without_shutdown_revokes_intent(self):
  import shutdown_state as shutdown,persistent_health as health
  from persistent_recovery import bound_exit
  with patch.object(health,'ROOT',self.root/'health'),patch.object(shutdown,'query',return_value=False):
   self.assertTrue(bound_exit('route-a',reason='observer_exit'))
  self.assertFalse(self.store.read()['enabled']);self.assertEqual(self.read(),self.baseline)
  outcome=self.c.boot(self.store.read(),'boot-b','new-boot',False)
  self.assertEqual(outcome['effect'],'none')

 def test_recognized_shutdown_does_not_need_available_system_services(self):
  from persistent_recovery import bound_exit
  with patch('shutdown_state.stopping',return_value=True),patch.object(d,'restore_once',side_effect=OSError('manager shutting down')),patch.object(d,'read',side_effect=OSError('manager shutting down')):
   self.assertTrue(bound_exit('route-a',reason='observer_exit'))
  self.assertEqual(self.store.read()['phase'],'stopping')
  with patch('shutdown_state.stopping',return_value=False):
   self.assertTrue(bound_exit('route-a',reason='observer_exit'))
  self.assertTrue(self.store.read()['enabled']);self.assertEqual(self.home,CANDIDATE)
  self.assertTrue(self.target.exists())
 def test_explicit_escape_overrides_already_recorded_shutdown(self):
  from persistent_recovery import bound_exit
  with patch('shutdown_state.stopping',return_value=True):
   self.assertTrue(bound_exit('route-a',reason='observer_exit'))
  with patch('shutdown_state.stopping',return_value=True):
   self.assertTrue(bound_exit('route-a',reason='escape'))
  self.assertFalse(self.store.read()['enabled']);self.assertEqual(self.read(),self.baseline)

 def test_restored_old_observer_cannot_revoke_intent_before_boot_dispatch(self):
  from persistent_recovery import bound_exit
  with patch('intent_runtime.boot_identity',return_value='boot-b'),patch.object(d,'restore_once') as restore:
   self.assertTrue(bound_exit('route-a',reason='observer_exit'))
   restore.assert_not_called()
  self.assertEqual(self.store.read(),self.intent)
  outcome=self.c.boot(self.store.read(),'boot-b','new-boot',False)
  self.assertEqual(outcome['effect'],'start_guarded');self.assertEqual(self.read(),self.baseline)
 def test_session_mismatch_does_not_override_escape_package_loss_or_failsafe(self):
  from persistent_recovery import bound_exit
  with patch('intent_runtime.boot_identity',return_value='boot-b'):
   self.assertTrue(bound_exit('route-a',reason='escape'))
  self.assertFalse(self.store.read()['enabled'])
 def test_firmware_transition_shutdown_still_needs_confirmed_active_intent(self):
  import shutdown_state as shutdown,persistent_health as health
  from persistent_recovery import bound_exit
  with patch.object(health,'ROOT',self.root/'health'),patch.object(shutdown,'query',return_value=False):
   power=shutdown.PowerState('route-a','boot-a')
   power.event(dict(returnValue=True,subscribed=True,state='Active'))
   power.event(dict(returnValue=True,state='Active Standby'))
   self.assertTrue(bound_exit('route-a',reason='observer_exit'))
  self.assertEqual(self.store.read()['phase'],'stopping');self.assertTrue(self.store.read()['enabled'])
  self.assertEqual(self.home,CANDIDATE)

 def test_session_mismatch_cannot_hide_package_loss_or_failsafe(self):
  from persistent_recovery import bound_exit
  with patch('intent_runtime.boot_identity',return_value='boot-b'),patch.object(d,'home_present',return_value=False):
   self.assertTrue(bound_exit('route-a',reason='observer_exit'))
  self.assertFalse(self.store.read()['enabled']);self.assertEqual(self.read(),self.baseline)
 def test_session_mismatch_with_failsafe_disables(self):
  from persistent_recovery import bound_exit
  with patch('intent_runtime.boot_identity',return_value='boot-b'),patch.object(d,'FAILSAFE',self.root/'failsafe'):
   d.FAILSAFE.touch();self.assertTrue(bound_exit('route-a',reason='observer_exit'))
  self.assertFalse(self.store.read()['enabled']);self.assertEqual(self.read(),self.baseline)
 def test_power_evidence_cannot_promote_unconfirmed_trial(self):
  import shutdown_state as shutdown,persistent_health as health
  from persistent_recovery import bound_exit
  self.c.exit(self.intent);disabled=self.store.read()
  trial,_=self.store.apply(disabled,dict(kind='enable',generation=disabled['generation'],boot='boot-a',token='unconfirmed'))
  self.create_route('route-b');self.c.bind(trial,'route-b')
  with patch.object(health,'ROOT',self.root/'health'),patch.object(shutdown,'query',return_value=False):
   power=shutdown.PowerState('route-b','boot-a')
   power.event(dict(returnValue=True,subscribed=True,state='Active'))
   power.event(dict(returnValue=True,state='Active Standby'))
   self.assertTrue(bound_exit('route-b',reason='observer_exit'))
  self.assertFalse(self.store.read()['enabled']);self.assertEqual(self.read(),self.baseline)

 def test_monitor_start_rejects_old_bound_startup_session(self):
  import shutdown_state as shutdown
  with patch('intent_runtime.boot_identity',return_value='boot-b'),patch.object(shutdown,'observe_power') as subscribe,patch.object(shutdown,'query') as query:
   monitor=shutdown.monitor('route-a');monitor.close()
  subscribe.assert_not_called();query.assert_not_called()
  self.assertEqual(self.store.read(),self.intent)
