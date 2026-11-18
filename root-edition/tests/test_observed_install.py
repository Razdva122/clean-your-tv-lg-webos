import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import unittest,os,json,io,tempfile
from unittest.mock import patch
from observed_install import install,OutcomeUnknown
class Fake:
 def __init__(self,pid):
  self.pid=pid;self.code=None;self.stdin=io.BytesIO();self.stderr=io.BytesIO();r,w=os.pipe();self.stdout=os.fdopen(r,'rb',buffering=0);self.writer=w
 def send(self,obj):os.write(self.writer,json.dumps(obj,ensure_ascii=False).encode())
 def poll(self):return self.code
 def terminate(self):self.code=-15
 def kill(self):self.code=-9
 def communicate(self,timeout):return b'',b''
 def close(self):self.stdout.close();os.close(self.writer)
class Tests(unittest.TestCase):
 def run_case(self,final=True,mismatch=False,active=False,callback=None,accepted_event=False,accept_error=False,ready_callback=None,check_stage=False):
  tmp=tempfile.TemporaryDirectory();root=Path(tmp.name);source=root/'private';source.mkdir(mode=0o700)
  package=source/'test.ipk';package.write_bytes(b'verified package');package.chmod(0o600)
  public=root/'public'
  procs=[]
  def popen(args,**kwargs):
   p=Fake(41+len(procs));procs.append(p)
   if len(procs)==1:p.send({'subscribed':True,'returnValue':True,'status':{'apps':[{'id':'other'}] if active else []}})
   else:
    self.assertIn('/status',procs[0].uri)
    ipk=json.loads(args[3])['ipkUrl']
    if check_stage:
     self.assertNotEqual(Path(ipk),package)
     self.assertEqual(Path(ipk).parent.parent,public)
     self.assertEqual(Path(ipk).read_bytes(),b'verified package')
     self.assertEqual(Path(ipk).stat().st_mode & 0o777,0o644)
     self.assertEqual(Path(ipk).parent.stat().st_mode & 0o777,0o755)
     self.assertEqual(source.stat().st_mode & 0o777,0o700)
     self.assertEqual(package.stat().st_mode & 0o777,0o600)
    p.send({'statusValue':37})
    if accepted_event:procs[0].send({'id':'test.app','returnValue':False if accept_error else True,'statusValue':37,'details':{'packageId':'test.app','ipkFile':ipk,'client':'wrong' if mismatch else 'com.webos.lunasend-42'}})
    if final:procs[0].send({'message':'Готово','id':'test.app','statusValue':30,'details':{'packageId':'test.app','ipkFile':ipk,'client':'wrong' if mismatch else 'com.webos.lunasend-42'}})
   p.uri=args[2];return p
  try:
   with patch('observed_install.subprocess.Popen',popen),patch('observed_install.STAGING_ROOT',public,create=True),patch('observed_install.TRUST_ANCHOR',root,create=True):
    result=install('test.app',str(package),timeout=.03,on_accepted=callback,on_ready=ready_callback)
    if check_stage:self.assertEqual(list(public.iterdir()),[])
    return result,procs
  finally:
   if check_stage and not final:self.assertTrue(list(public.glob('*/package.ipk')),'unknown install must retain its backend-readable IPK')
   for p in procs:p.close()
   tmp.cleanup()
 def test_only_the_verified_package_is_exposed_to_appinstalld(self):self.run_case(check_stage=True)
 def test_unknown_install_retains_the_backend_package(self):
  with self.assertRaises(OutcomeUnknown):self.run_case(final=False,check_stage=True)
 def test_unsafe_staging_root_is_rejected_before_luna_submission(self):
  import observed_install
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp).resolve();public=root/'public';public.mkdir();public.chmod(0o777)
   package=root/'test.ipk';package.write_bytes(b'verified package')
   with patch('observed_install.STAGING_ROOT',public),patch('observed_install.TRUST_ANCHOR',root,create=True),patch('observed_install.subprocess.Popen') as start:
    with self.assertRaisesRegex(ValueError,'Unsafe installer staging'):install('test.app',str(package))
    start.assert_not_called()
 def test_error_acceptance_never_reported(self):
  events=[]
  self.run_case(callback=events.append,accepted_event=True,accept_error=True)
  self.assertEqual(events,[])
 def test_ready_hook_precedes_submission(self):
  called=[]
  self.run_case(ready_callback=lambda:called.append('ready'))
  self.assertEqual(called,['ready'])
 def test_acceptance_saved_before_injected_loss(self):
  events=[]
  def accepted(event):events.append(event);raise OutcomeUnknown('Injected')
  with self.assertRaises(OutcomeUnknown):self.run_case(callback=accepted,accepted_event=True)
  self.assertEqual(len(events),1);self.assertEqual(events[0]['statusValue'],37)
 def test_foreign_acceptance_not_reported(self):
  events=[]
  with self.assertRaises(OutcomeUnknown):self.run_case(mismatch=True,callback=events.append,accepted_event=True)
  self.assertEqual(events,[])
 def test_split_utf8_response(self):
  real_read=os.read
  with patch('observed_install.os.read',lambda fd,n:real_read(fd,1)):
   self.assertTrue(self.run_case()[0]['completed'])
 def test_matching_independent_completion(self):self.assertTrue(self.run_case()[0]['completed'])
 def test_missing_completion_unknown(self):
  with self.assertRaises(OutcomeUnknown):self.run_case(final=False)
 def test_other_client_completion_unknown(self):
  with self.assertRaises(OutcomeUnknown):self.run_case(mismatch=True)
 def test_nonidle_refuses_start(self):
  with self.assertRaises(OutcomeUnknown):self.run_case(active=True)
if __name__=='__main__':unittest.main()

class RemoveTests(unittest.TestCase):
 def run_remove(self,event):
  import observed_install
  self.assertTrue(hasattr(observed_install,'remove'), 'Observed remove is missing')
  p=Fake(45);p.send(event)
  try:
   with patch('observed_install.subprocess.Popen',return_value=p):
    return observed_install.remove('test.app',timeout=.02)
  finally:p.close()
 def test_terminal_removed(self):
  self.assertTrue(self.run_remove({'returnValue':True,'details':{'state':'removed'}})['completed'])
 def test_terminal_success(self):
  self.assertTrue(self.run_remove({'returnValue':True,'details':{'state':'SUCCESS'}})['completed'])
 def test_terminal_rejection_requires_a_well_formed_reply_for_the_requested_package(self):
  from install_driver import failure_summary
  for event,rejected in (
   ({'returnValue':False,'id':'test.app','errorCode':-102},True),
   ({'returnValue':False,'id':'other','errorCode':-102},False),
   ({'returnValue':False,'details':[]},False),
   ({'returnValue':True,'subscribed':True},False),
  ):
   with self.subTest(event=event):
    with self.assertRaises(OutcomeUnknown) as caught:
     self.run_remove(event)
    self.assertIs(failure_summary(caught.exception).get('package_rejected',False),rejected)
 def test_acceptance_or_error_never_completes(self):
  for event in ({'returnValue':True,'subscribed':True}, {'returnValue':False,'details':{'state':'removed'}}, {'returnValue':True,'details':{'state':'not removed'}}, {'returnValue':True,'id':'other','details':{'state':'removed'}}):
   with self.subTest(event=event), self.assertRaises(OutcomeUnknown):self.run_remove(event)
