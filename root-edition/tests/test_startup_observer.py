"""Event subscriptions cannot keep stale native-selection authority."""
import json,os,subprocess,sys,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
try:import startup_observer as observer
except ModuleNotFoundError:observer=None

class Tests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(observer,'Native input observer is missing')
 def ready(self,o):
  o.feed('foreground',{'returnValue':True,'subscribed':True,'appId':'mgg4.5.channelplus'})
  o.feed('input',{'returnValue':True,'subscribed':True,'settings':{'lastInputApp':'mgg4.5.channelplus','lastInputAppType':'MVPD_IP','homeAutoLaunch':'on'}})
 def test_missing_foreground_cancels_blocked_work_and_root_echo_cannot_replay(self):
  entered=threading.Event();release=threading.Event();seen=[]
  def reconcile(tx,boot,cancelled,**kw):
   seen.append(cancelled);entered.set();release.wait(1);return 'canceled' if cancelled() else 'selected'
  o=observer.Observer('tx','boot',threading.Event())
  with patch.object(observer.policy,'reconcile',side_effect=reconcile):
   try:
    self.ready(o);self.assertTrue(entered.wait(1))
    o.feed('foreground',{'returnValue':True,'subscribed':True,'appId':''})
    self.assertTrue(seen[0]())
    o.feed('input',{'returnValue':True,'subscribed':True,'settings':{'lastInputApp':'com.cleanyourtv.root.preview'}})
   finally:release.set();o.close(withdraw=False)
  self.assertEqual(len(seen),1)
 def test_invalid_or_lost_subscription_cancels_and_withdraws_owned_priority(self):
  for frame in ({'returnValue':False},{'returnValue':True,'subscribed':False,'appId':'mgg4.5.channelplus'}, {'returnValue':True,'subscribed':True,'appId':[]}):
   o=observer.Observer('tx','boot',threading.Event())
   with patch.object(observer.policy,'reconcile',return_value='withdrawn') as reconcile:
    with self.assertRaises(ValueError):o.feed('foreground',frame)
    o.close()
    self.assertTrue(o.closed)
    self.assertTrue(any(c.kwargs.get('withdraw') is True for c in reconcile.call_args_list))
 def test_distinct_foreground_event_is_coalesced_after_pending_worker(self):
  entered=threading.Event();release=threading.Event();events=[]
  def reconcile(tx,boot,cancelled,**kw):
   events.append(kw.get('event'));entered.set();release.wait(1);return 'selected'
  o=observer.Observer('tx','boot',threading.Event())
  with patch.object(observer.policy,'reconcile',side_effect=reconcile):
   self.ready(o);self.assertTrue(entered.wait(1))
   o.feed('foreground',{'returnValue':True,'appId':'youtube.leanback.v4'})
   release.set()
   end=time.monotonic()+1
   while len(events)<2 and time.monotonic()<end:time.sleep(.01)
   o.close(withdraw=False)
  self.assertEqual(events,['foreground','foreground'])
 def test_real_subscription_children_are_reaped_without_reconnect(self):
  children=[];real=subprocess.Popen;stop=threading.Event();entered=threading.Event()
  def launch(args,**kw):
   foreground='getForegroundAppInfo' in args[-2]
   value={'returnValue':True,'subscribed':True}
   value.update({'appId':'mgg4.5.channelplus'} if foreground else {'settings':{'lastInputApp':'mgg4.5.channelplus','homeAutoLaunch':'on'}})
   code='import sys;print('+repr(json.dumps(value))+',flush=True);sys.stdin.read()'
   p=real([sys.executable,'-c',code],**kw);children.append(p);return p
  o=observer.Observer('tx','boot',stop)
  with patch.object(observer.subprocess,'Popen',side_effect=launch),patch('intent_runtime.boot_identity',return_value='boot'),patch.object(observer.policy,'reconcile',side_effect=lambda *a,**k:entered.set()):
   thread=threading.Thread(target=o.run);thread.start()
   try:self.assertTrue(entered.wait(2))
   finally:stop.set();thread.join(3)
  self.assertFalse(thread.is_alive());self.assertEqual(len(children),2)
  self.assertTrue(all(c.poll() is not None for c in children))
 def test_delayed_root_echo_preserves_newer_protected_foreground_work(self):
  entered=threading.Event();release=threading.Event();events=[]
  def reconcile(tx,boot,cancelled,**kw):
   events.append(kw.get('event'));entered.set();release.wait(1);return 'selected'
  o=observer.Observer('tx','boot',threading.Event())
  with patch.object(observer.policy,'reconcile',side_effect=reconcile):
   self.ready(o);self.assertTrue(entered.wait(1))
   o.feed('foreground',{'returnValue':True,'appId':'youtube.leanback.v4'})
   o.feed('input',{'returnValue':True,'settings':{'lastInputApp':'com.cleanyourtv.root.preview'}})
   release.set();end=time.monotonic()+1
   while len(events)<2 and time.monotonic()<end:time.sleep(.01)
   o.close(withdraw=False)
  self.assertEqual(events,['foreground','foreground'])
 def test_global_startup_disable_is_observed_during_blank_foreground(self):
  seen=threading.Event();events=[]
  def reconcile(tx,boot,cancelled,**kw):
   events.append(kw.get('event'))
   if kw.get('event')=='policy':seen.set()
  o=observer.Observer('tx','boot',threading.Event())
  with patch.object(observer.policy,'reconcile',side_effect=reconcile):
   self.ready(o)
   o.feed('foreground',{'returnValue':True,'appId':''})
   o.feed('input',{'returnValue':True,'settings':{'homeAutoLaunch':'off'}})
   self.assertTrue(seen.wait(1));o.close(withdraw=False)
 def assert_global_off_survives(self,later):
  entered=threading.Event();release=threading.Event();events=[]
  def reconcile(tx,boot,cancelled,**kw):
   events.append(kw.get('event'));entered.set();release.wait(1);return 'selected'
  o=observer.Observer('tx','boot',threading.Event())
  with patch.object(observer.policy,'reconcile',side_effect=reconcile):
   self.ready(o);self.assertTrue(entered.wait(1))
   o.feed('foreground',{'returnValue':True,'appId':''})
   o.feed('input',{'returnValue':True,'settings':{'homeAutoLaunch':'off'}})
   o.feed(*later);release.set();end=time.monotonic()+1
   while 'policy' not in events and time.monotonic()<end:time.sleep(.01)
   o.close(withdraw=False)
  self.assertIn('policy',events)
 def test_global_off_withdrawal_survives_delayed_root_echo_under_blank(self):
  self.assert_global_off_survives(('input',{'returnValue':True,'settings':{'lastInputApp':'com.cleanyourtv.root.preview'}}))
 def test_global_off_withdrawal_survives_another_blank_frame(self):
  self.assert_global_off_survives(('foreground',{'returnValue':True,'appId':''}))
 def test_initial_global_off_snapshot_precedes_blank_foreground(self):
  entered=threading.Event();events=[];o=observer.Observer('tx','boot',threading.Event())
  def reconcile(*args,**kw):events.append(kw.get('event'));entered.set()
  with patch.object(observer.policy,'reconcile',side_effect=reconcile):
   o.feed('input',{'returnValue':True,'subscribed':True,'settings':{'lastInputApp':'com.cleanyourtv.root.preview','homeAutoLaunch':'off'}})
   o.feed('foreground',{'returnValue':True,'subscribed':True,'appId':''})
   self.assertTrue(entered.wait(1));o.close(withdraw=False)
  self.assertIn('policy',events)
