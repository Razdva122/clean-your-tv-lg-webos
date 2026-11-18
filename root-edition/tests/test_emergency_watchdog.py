import os,subprocess,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
from emergency_watchdog import watch
class Tests(unittest.TestCase):
 def test_closed_channel_still_requests_recovery(self):
  r,w=os.pipe();os.close(r);os.close(w);reasons=[]
  self.assertEqual(watch(r,lambda why:reasons.append(why) or True),'channel_error')
  self.assertEqual(reasons,['channel_error'])
 def test_terminal_escape_not_overwritten_by_trailing_bytes(self):
  self.assertEqual(self.run_stream(b'READY\nESCAPE\n'+b'x'*30),'escape')
 def stream(self,data):
  r,w=os.pipe();os.write(w,data);os.close(w);return r
 def run_stream(self,data):
  reasons=[];r=self.stream(data)
  try:result=watch(r,lambda why:reasons.append(why) or True,timeout=.1)
  finally:os.close(r)
  self.assertEqual(len(reasons),1);return result
 def test_escape_is_terminal(self):self.assertEqual(self.run_stream(b'READY\nPING\nESCAPE\n'),'escape')
 def test_eof_requests_recovery(self):self.assertEqual(self.run_stream(b'READY\n'),'observer_exit')
 def test_device_removal_requires_reader_readiness(self):
  self.assertEqual(self.run_stream(b'READY\nDEVICE_GONE 0.01\n'),'device_removed')
  self.assertEqual(self.run_stream(b'DEVICE_GONE 0.01\n'),'bad_protocol')
  self.assertEqual(self.run_stream(b'READY\nESCAPE\nDEVICE_GONE 0.01\n'),'escape')
 def test_input_loss_requests_recovery(self):self.assertEqual(self.run_stream(b'READY\nLOST\n'),'input_lost')
 def test_unknown_message_does_not_renew_health(self):self.assertEqual(self.run_stream(b'READY\nwrong\n'),'bad_protocol')
 def test_ping_without_ready_is_rejected(self):self.assertEqual(self.run_stream(b'PING\n'),'bad_protocol')
 def test_partial_message_is_bounded(self):self.assertEqual(self.run_stream(b'x'*100),'bad_protocol')
 def test_failed_recovery_is_not_reported_as_success(self):
  r=self.stream(b'READY\nESCAPE\n')
  try:
   with self.assertRaises(RuntimeError):watch(r,lambda why:False,timeout=.1)
  finally:os.close(r)
 def test_live_but_stopped_process_times_out(self):
  r,w=os.pipe()
  code='import os,signal,sys;os.write(int(sys.argv[1]),b"READY\\nPING\\n");os.kill(os.getpid(),signal.SIGSTOP)'
  p=subprocess.Popen([sys.executable,'-c',code,str(w)],pass_fds=(w,));os.close(w)
  try:
   self.assertEqual(watch(r,lambda why:True,timeout=.3),'heartbeat_timeout')
   self.assertIsNone(p.poll())
  finally:p.kill();p.wait();os.close(r)
 def test_killed_process_triggers_eof(self):
  r,w=os.pipe();code='import os,signal,sys;os.write(int(sys.argv[1]),b"READY\\n");os.kill(os.getpid(),signal.SIGKILL)'
  p=subprocess.Popen([sys.executable,'-c',code,str(w)],pass_fds=(w,));os.close(w)
  try:self.assertEqual(watch(r,lambda why:True,timeout=.3),'observer_exit')
  finally:p.wait();os.close(r)
 def test_health_callback_only_follows_valid_input_loop_ping(self):
  r=self.stream(b'READY\nPING\nPING\nESCAPE\n');seen=[]
  try:watch(r,lambda why:True,on_ping=lambda:seen.append('ping'))
  finally:os.close(r)
  self.assertEqual(seen,['ping','ping'])

 def test_lg_home_is_nonterminal_and_does_not_restore(self):
  r=self.stream(b'READY\nLGHOME\nPING\nESCAPE\n');visits=[];reasons=[];pings=[]
  try:watch(r,lambda why:reasons.append(why) or True,on_lg_home=lambda:visits.append('lg'),on_ping=lambda:pings.append('ping'))
  finally:os.close(r)
  self.assertEqual(visits,['lg']);self.assertEqual(pings,['ping']);self.assertEqual(reasons,['escape'])
