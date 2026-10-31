"""Owned native input lifecycle: real receipt state, simulated bounded Luna API."""
import copy,json,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
import device_adapter as d
native=d

class NativeInputTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name);self.root.chmod(0o700)
  self.baseline={'type':'DTV','appId':'com.webos.app.livetv'}
  self.last=dict(self.baseline);self.devices=[];self.calls=[];self.fail=None
  for target,name,value in ((d,'STATE',self.root),(d,'EXPECTED_UID',os.getuid()),(d,'sam_transport',lambda:self)):
   p=patch.object(target,name,value);p.start();self.addCleanup(p.stop)
 def call(self,uri,payload,timeout=5):
  method=uri.rsplit('/',1)[-1];self.calls.append((method,copy.deepcopy(payload)))
  if self.fail: self.fail(method,payload)
  if method=='getAllInputStatus':return {'returnValue':True,'devices':copy.deepcopy(self.devices)}
  if method=='getLastInput':return dict(returnValue=True,lastSourceId=self.last['type'],lastSourceAppId=self.last['appId'])
  if method=='addDevice':self.devices.append({'appId':d.CANDIDATE,'id':'MVPD_IP-'+d.CANDIDATE,'label':'Home Root'})
  elif method=='setLastInput':self.last=dict(payload)
  elif method=='deleteDevice':self.devices=[x for x in self.devices if x['appId']!=d.CANDIDATE]
  return {'returnValue':True}
 def saved(self):return json.loads((self.root/'native-input.json').read_text())
 def test_enable_and_disable_roundtrip_without_launch(self):
  self.assertEqual(native.native_input_enable(),'active');self.assertEqual(self.last,{'type':'MVPD_IP','appId':d.CANDIDATE})
  self.assertEqual(self.saved()['phase'],'active')
  self.assertEqual(native.native_input_disable(),'disabled');self.assertEqual(self.last,self.baseline);self.assertEqual(self.devices,[])
  self.assertNotIn('launch',[name for name,_ in self.calls])
  self.assertEqual(native.native_input_disable(),'disabled')
 def test_total_budget_shrinks_rpc_timeout_and_stops_before_late_add(self):
  from types import SimpleNamespace
  timeouts=[]
  def timed(uri,payload,timeout):
   timeouts.append(timeout)
   return self.call(uri,payload,timeout)
  with patch.object(d.time,'monotonic',side_effect=[100,100,101.4,101.6]),patch.object(d,'sam_transport',return_value=SimpleNamespace(call=timed)):
   with self.assertRaisesRegex(TimeoutError,'deadline'):native.native_input_enable()
  self.assertEqual(len(timeouts),2);self.assertEqual(timeouts[0],.5)
  self.assertAlmostEqual(timeouts[1],.05)
  self.assertNotIn('addDevice',[name for name,_ in self.calls])
  self.assertEqual(self.saved()['phase'],'adding');self.assertEqual(self.devices,[])
  self.assertEqual(native.native_input_disable(),'disabled')

 def test_uncertain_add_is_reconciled_not_resubmitted(self):
  def fault(method,payload):
   if method=='addDevice':
    self.devices=[{'appId':d.CANDIDATE,'id':'MVPD_IP-'+d.CANDIDATE}]
    raise TimeoutError('lost ack')
  self.fail=fault
  with self.assertRaises(TimeoutError):native.native_input_enable()
  self.assertEqual(self.saved()['phase'],'adding')
  self.fail=None;self.assertEqual(native.native_input_disable(),'disabled')
  self.assertEqual(sum(name=='addDevice' for name,_ in self.calls),1)
 def test_preexisting_entry_is_not_adopted_or_deleted(self):
  self.devices=[{'appId':d.CANDIDATE,'id':'MVPD_IP-'+d.CANDIDATE}]
  with self.assertRaisesRegex(ValueError,'unowned'):native.native_input_enable()
  self.assertEqual(native.native_input_disable(),'absent');self.assertEqual(len(self.devices),1)
  self.assertFalse((self.root/'native-input.json').exists())
 def test_other_selected_input_is_preserved_on_disable(self):
  native.native_input_enable();self.last={'type':'HDMI_2','appId':'com.webos.app.hdmi2'}
  self.assertEqual(native.native_input_disable(),'disabled');self.assertEqual(self.last['type'],'HDMI_2')
 def test_uncertain_delete_retains_receipt_and_reconciles_absence(self):
  native.native_input_enable()
  def fault(method,payload):
   if method=='deleteDevice':self.devices=[];raise TimeoutError('lost ack')
  self.fail=fault
  with self.assertRaises(TimeoutError):native.native_input_disable()
  self.assertEqual(self.saved()['phase'],'removing');self.fail=None
  self.assertEqual(native.native_input_disable(),'disabled')
  self.assertEqual(sum(name=='deleteDevice' for name,_ in self.calls),1)
 def test_wrong_readback_blocks_completion(self):
  native.native_input_enable()
  def fault(method,payload):
   if method=='setLastInput':raise TimeoutError('unverified restore')
  self.fail=fault
  with self.assertRaises(TimeoutError):native.native_input_disable()
  self.assertEqual(self.saved()['phase'],'removing');self.assertEqual(len(self.devices),1)
 def test_disabled_receipt_is_not_permission_to_delete_new_entry(self):
  native.native_input_enable();native.native_input_disable()
  self.devices=[{'appId':d.CANDIDATE,'id':'MVPD_IP-'+d.CANDIDATE}]
  self.assertEqual(native.native_input_disable(),'disabled');self.assertEqual(len(self.devices),1)
  with self.assertRaisesRegex(ValueError,'unowned'):native.native_input_enable()
 def test_repeated_enable_does_not_steal_new_input(self):
  native.native_input_enable();self.last={'type':'HDMI_1','appId':'com.webos.app.hdmi1'}
  self.assertEqual(native.native_input_enable(),'active');self.assertEqual(self.last['type'],'HDMI_1')
 def test_missing_entry_is_not_silently_reregistered(self):
  native.native_input_enable();self.devices=[]
  with self.assertRaisesRegex(ValueError,'changed'):native.native_input_enable()
 def test_tampered_or_unsafe_receipt_is_rejected(self):
  native.native_input_enable();p=self.root/'native-input.json';value=self.saved();value['baseline']['appId']=d.CANDIDATE;p.write_text(json.dumps(value))
  with self.assertRaises(ValueError):native.native_input_disable()
  p.chmod(0o666)
  with self.assertRaises(ValueError):native.native_input_disable()


import test_persistent_recovery as recovery
class NativeRecoveryTests(recovery.IntegrationTests):
 def test_fault_restores_routes_even_when_native_cleanup_fails(self):
  def fail():
   self.assertEqual(self.read(),self.baseline)
   raise ValueError('native cleanup pending')
  with patch.object(d,'native_input_disable',side_effect=fail) as cleanup:
   with self.assertRaisesRegex(ValueError,'native cleanup pending'):self.c.exit(self.intent)
  cleanup.assert_called_once();self.assertFalse(self.store.read()['enabled'])
 def test_boot_restore_keeps_owned_native_input_for_enabled_intent(self):
  with patch.object(d,'native_input_disable') as cleanup:self.c.boot(self.intent,'boot-b','new-b',False)
  cleanup.assert_not_called()
 def test_disabled_restore_retries_native_cleanup(self):
  import intent_runtime
  self.c.exit(self.intent)
  (self.root/'native-input.json').write_text('{}')
  with patch.object(d,'native_input_disable') as cleanup,patch.object(d,'main',return_value='restored') as routing:
   intent_runtime.restore()
  routing.assert_called_once_with('recover');cleanup.assert_called_once()

 def test_orphan_boot_restores_routes_before_cleanup(self):
  import intent_runtime
  (self.root/'native-input.json').write_text('{}')
  (self.root/'persistent-intent.json').unlink()
  order=[]
  with patch.object(d,'main',side_effect=lambda mode:order.append('routes') or 'restored'),patch.object(d,'native_input_disable',side_effect=lambda:order.append('native')):
   self.assertEqual(intent_runtime.boot(),'restored')
  self.assertEqual(order,['routes','native'])

 def test_public_boot_preserves_live_legacy_trial_with_retired_native_receipt(self):
  import intent_runtime
  self.c.exit(self.intent);self.create_route('legacy-trial')
  receipt=self.root/'native-input.json'
  receipt.write_text(json.dumps({'schema':1,'appId':d.CANDIDATE,'phase':'disabled','baseline':{'type':'DTV','appId':'com.webos.app.livetv'}}))
  original=receipt.read_bytes()
  with patch.object(d,'active_guardian',return_value=True),patch.object(intent_runtime,'boot_identity',return_value='boot-b'):
   self.assertIsNone(intent_runtime.boot())
   self.assertEqual(self.home,d.CANDIDATE);self.assertTrue(self.target.exists())
   (self.root/'persistent-intent.json').unlink()
   self.assertIsNone(intent_runtime.boot())
   self.assertEqual(self.home,d.CANDIDATE);self.assertTrue(self.target.exists())
  self.assertEqual(receipt.read_bytes(),original)
  self.assertEqual(intent_runtime.restore(),'restored')
  self.assertEqual(self.read(),self.baseline)

 def activation(self,healthy=True):
  import time
  self.c.exit(self.intent)
  disabled=self.store.read()
  def start(before_publish):
   self.create_route('route-native')
   journal=d.safe_json(self.root/'profile-trial.json')
   journal['deadline']=time.monotonic()+60;d.save(journal)
   before_publish('route-native')
   return {'transaction':'route-native'}
  self.enterContext(patch('emergency_trial.start',side_effect=start))
  self.enterContext(patch('provision.verify'))
  self.enterContext(patch('helper_bridge.require_idle'))
  self.enterContext(patch('persistent_health.require_fresh',side_effect=None if healthy else ValueError('missing heartbeat')))
  self.enterContext(patch('persistent_health.require_guardian'))
  self.enterContext(patch.object(d,'active_guardian',return_value=True))
  if not healthy:self.enterContext(patch('time.sleep'))
  return disabled

 def test_enable_registers_native_input_only_after_real_confirmation(self):
  disabled=self.activation()
  observed=[]
  def register():
   state=self.store.read()
   self.assertEqual(state['phase'],'active');self.assertTrue(state['enabled'])
   self.assertEqual(self.c.read_binding()['transaction'],'route-native')
   self.assertEqual(self.read()['sam_home'],d.CANDIDATE)
   observed.append(state)
   return 'active'
  with patch.object(d,'native_input_enable',side_effect=register):
   result=self.c.enable(disabled,'boot-b','native-attempt')
  self.assertEqual(observed,[result['intent']])
  self.assertTrue(result['persistent']);self.assertEqual(result['native_input'],'active')

 def test_missing_input_health_cannot_register_native_input(self):
  disabled=self.activation(healthy=False)
  with patch.object(d,'native_input_enable',side_effect=AssertionError('native registration before health')) as register:
   with self.assertRaisesRegex(ValueError,'missing heartbeat'):
    self.c.enable(disabled,'boot-b','native-attempt')
  register.assert_not_called()
  self.assertFalse(self.store.read()['enabled']);self.assertEqual(self.read(),self.baseline)

if __name__=='__main__':unittest.main()
