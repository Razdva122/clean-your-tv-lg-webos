import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
from persistent_lease import watch

class LeaseTests(unittest.TestCase):
 def run_case(self, records, stop=10):
  self.now=0.;self.restores=[];self.steps=0
  def load():return records[min(self.steps,len(records)-1)]
  def sleep(n):
   self.now+=n;self.steps+=1
   if self.steps>stop:raise AssertionError('Guard did not terminate')
  return watch('tx','boot',load,lambda reason:self.restores.append(reason),lambda:self.now,sleep)
 def lease(self,**kw):return dict(transaction='tx',boot='boot',state='active',sequence=1,issued=0.,expires=2.,**kw)
 def test_stalled_supervisor_lease_expires(self):
  self.assertEqual(self.run_case([self.lease()]),'lease-expired')
  self.assertEqual(self.restores,['lease-expired'])
 def test_new_heartbeat_extends_only_bounded_period(self):
  a=self.lease();b=dict(a,sequence=2,issued=.25,expires=2.25)
  self.assertEqual(self.run_case([a,b]),'lease-expired');self.assertEqual(self.now,2.25)
 def test_same_sequence_cannot_extend_lease(self):
  a=self.lease();b=dict(a,issued=.25,expires=2.25)
  self.assertEqual(self.run_case([a,b]),'invalid-lease')
 def test_waiting_scans_are_watched_and_can_recover_active_input(self):
  waiting=dict(self.lease(),state='waiting-input',sequence=2,issued=.25,expires=2.25)
  self.assertEqual(self.run_case([self.lease(),waiting]),'lease-expired')
  self.assertEqual(self.now,2.25)
  active=dict(self.lease(),sequence=3,issued=.5,expires=2.5)
  self.assertEqual(self.run_case([self.lease(),waiting,active,dict(transaction='tx',state='restored')]),'restored')
  self.assertEqual(self.restores,[])
 def test_missing_and_wrong_boot_recover(self):
  for record in (None,dict(self.lease(),boot='other')):
   self.assertEqual(self.run_case([record]),'invalid-lease')
 def test_new_transaction_is_not_touched(self):
  self.assertEqual(self.run_case([dict(self.lease(),transaction='new')]),'superseded')
  self.assertEqual(self.restores,[])
 def test_terminal_state_does_not_recover_again(self):
  for state in ('restored','conflict'):
   self.assertEqual(self.run_case([dict(self.lease(),state=state)]),state)
   self.assertEqual(self.restores,[])
 def test_nonfinite_future_excessive_and_regressing_heartbeat(self):
  for changes in ({'expires':float('nan')},{'expires':30.},{'issued':1.},
                  {'sequence':True},{'expires':-1.},{'issued':-1.}):
   self.assertEqual(self.run_case([dict(self.lease(),**changes)]),'invalid-lease')
  a=self.lease()
  self.assertEqual(self.run_case([dict(a,sequence=2),a]),'invalid-lease')
 def test_read_error_restores(self):
  calls=[]
  def fail():raise OSError('unreadable')
  result=watch('tx','boot',fail,calls.append,lambda:0,lambda _:None)
  self.assertEqual((result,calls),('unreadable-lease',['unreadable-lease']))

 def test_heartbeat_published_during_read_is_not_from_future(self):
  now=[100.];restored=[];calls=[0]
  def load():
   calls[0]+=1;now[0]+=.001
   if calls[0]>1:return dict(transaction='tx',state='restored')
   return dict(transaction='tx',boot='boot',state='active',sequence=1,issued=now[0],expires=now[0]+2)
  result=watch('tx','boot',load,restored.append,lambda:now[0],lambda n:now.__setitem__(0,now[0]+n))
  self.assertEqual(result,'restored');self.assertFalse(restored)

 def test_frozen_publisher_does_not_freeze_independent_guard(self):
  import json,os,signal,subprocess,tempfile,time
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);lease=root/'lease.json';result=root/'result'
   publisher_code="""
import json,os,sys,time
from pathlib import Path
p=Path(sys.argv[1]);seq=0
while True:
 seq+=1;now=time.monotonic()
 temp=p.with_suffix('.next')
 temp.write_text(json.dumps(dict(transaction='tx',boot='boot',state='active',sequence=seq,issued=now,expires=now+2)))
 os.replace(temp,p)
 if seq==1: print('READY',flush=True)
 time.sleep(.1)
"""
   guard_code="""
import json,sys,time
from pathlib import Path
from persistent_lease import watch
p=Path(sys.argv[1]);out=Path(sys.argv[2])
print('READY',flush=True)
watch('tx','boot',lambda:json.loads(p.read_text()),lambda reason:out.write_text(reason),time.monotonic,time.sleep)
"""
   pub=subprocess.Popen([sys.executable,'-c',publisher_code,str(lease)],stdout=subprocess.PIPE,text=True)
   guard=None
   try:
    import select
    self.assertTrue(select.select([pub.stdout],[],[],3)[0]);self.assertEqual(pub.stdout.readline().strip(),'READY')
    guard=subprocess.Popen([sys.executable,'-c',guard_code,str(lease),str(result)],cwd=Path(__file__).resolve().parents[1]/'runtime',stdout=subprocess.PIPE,text=True)
    self.assertTrue(select.select([guard.stdout],[],[],3)[0]);self.assertEqual(guard.stdout.readline().strip(),'READY')
    os.kill(pub.pid,signal.SIGSTOP)
    self.assertEqual(guard.wait(timeout=5),0)
    self.assertIsNone(pub.poll())
    self.assertEqual(result.read_text(),'lease-expired')
   finally:
    pub.kill();pub.wait();pub.stdout.close()
    if guard is not None:
     if guard.poll() is None:guard.kill();guard.wait()
     guard.stdout.close()

 def test_exact_two_second_publications_across_float_boundaries(self):
  for issued in (62.4,126.4,254.4,510.4,1022.4):
   with self.subTest(issued=issued):
    records=iter([dict(transaction='tx',boot='boot',state='active',sequence=1,issued=issued,expires=issued+2),dict(transaction='tx',state='restored')])
    restored=[]
    result=watch('tx','boot',lambda:next(records),restored.append,lambda:issued,lambda _:None)
    self.assertEqual(result,'restored');self.assertEqual(restored,[])
