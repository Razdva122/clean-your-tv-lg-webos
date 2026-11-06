import os,struct,subprocess,sys,unittest
from pathlib import Path
RUNTIME=Path(__file__).resolve().parents[1]/'runtime'
sys.path.insert(0,str(RUNTIME))
from emergency_watchdog import watch
class ReaderTests(unittest.TestCase):
 def run_input(self,events,release_delay=0):
  ir,iw=os.pipe();hr,hw=os.pipe();env=os.environ.copy();env['PYTHONPATH']=str(RUNTIME)
  code='import sys,time;from emergency_reader import observe;started=time.monotonic();observe(int(sys.argv[1]),int(sys.argv[2]),lambda:time.monotonic()-started>=float(sys.argv[3]))'
  p=subprocess.Popen([sys.executable,'-c',code,str(ir),str(hw),str(release_delay)],pass_fds=(ir,hw),env=env,stderr=subprocess.PIPE)
  os.close(ir);os.close(hw)
  try:
   return watch(hr,lambda reason:True,timeout=2,on_ready=lambda:os.write(iw,events))
  finally:
   if p.poll() is None:p.kill()
   p.communicate();os.close(iw);os.close(hr)
 def test_three_taps_pass_through_reader_to_watchdog(self):
  data=b''.join(struct.pack('<IIHHi',1,t*1000,1,773,v) for t,v in [(0,1),(100,0),(300,1),(400,0),(600,1),(700,0)])
  self.assertEqual(self.run_input(data),'escape')
 def test_released_wake_key_allows_fresh_emergency_gesture(self):
  data=b''.join(struct.pack('<IIHHi',1,t*1000,1,773,v) for t,v in [(0,1),(100,0),(300,1),(400,0),(600,1),(700,0)])
  self.assertEqual(self.run_input(data,release_delay=.15),'escape')
 def test_key_that_stays_held_never_becomes_ready(self):
  self.assertEqual(self.run_input(b'',release_delay=10),'input_lost')
 def test_only_initial_historical_gestures_are_discarded(self):
  import contextlib,io
  import emergency_reader as reader
  from unittest.mock import patch
  taps=b''.join(struct.pack('<IIHHi',1,t*1000,1,773,v) for t,v in [(0,1),(100,0),(300,1),(400,0),(600,1),(700,0)])
  dropped=struct.pack('<IIHHi',2,0,0,3,0)
  hr,hw=os.pipe()
  try:
   with patch.object(reader.os,'set_blocking'),patch.object(reader.os,'read',side_effect=[taps,BlockingIOError(),dropped]),patch.object(reader.select,'select',return_value=([42],[],[])),contextlib.redirect_stderr(io.StringIO()):
    reader.observe(42,hw,lambda:True)
   os.close(hw);hw=None
   self.assertEqual(os.read(hr,256),b'READY\nLOST\n')
  finally:
   os.close(hr)
   if hw is not None:os.close(hw)
 def test_fresh_home_during_release_wait_cancels_activation(self):
  import contextlib,io,json
  import emergency_reader as reader
  from unittest.mock import Mock,patch
  for value in (1,2):
   with self.subTest(value=value):
    home=struct.pack('<IIHHi',1,0,1,773,value);hr,hw=os.pipe();log=io.StringIO()
    try:
     with patch.object(reader.os,'set_blocking'),patch.object(reader.os,'read',side_effect=[BlockingIOError(),home,BlockingIOError(),b'']),patch.object(reader.select,'select',return_value=([42],[],[])),contextlib.redirect_stderr(log):
      reader.observe(42,hw,Mock(side_effect=[False,True]))
     os.close(hw);hw=None
     self.assertEqual(os.read(hr,256),b'LOST\n','Fresh Home must prevent READY and pending activation')
     self.assertEqual(json.loads(log.getvalue()),{'event':'input-observer-fault','phase':'startup','reason':'home_activity'})
    finally:
     os.close(hr)
     if hw is not None:os.close(hw)
 def test_release_wait_accepts_key_up_without_counting_it_as_a_gesture(self):
  import contextlib,io
  import emergency_reader as reader
  from unittest.mock import Mock,patch
  up=struct.pack('<IIHHi',1,0,1,773,0);dropped=struct.pack('<IIHHi',2,0,0,3,0)
  hr,hw=os.pipe()
  try:
   with patch.object(reader.os,'set_blocking'),patch.object(reader.os,'read',side_effect=[BlockingIOError(),up,BlockingIOError(),dropped]),patch.object(reader.select,'select',return_value=([42],[],[])),contextlib.redirect_stderr(io.StringIO()):
    reader.observe(42,hw,Mock(side_effect=[False,True]))
   os.close(hw);hw=None
   self.assertEqual(os.read(hr,256),b'READY\nLOST\n')
  finally:
   os.close(hr)
   if hw is not None:os.close(hw)
 def test_release_wait_still_refuses_input_faults_before_ready(self):
  import contextlib,io,json
  import emergency_reader as reader
  from unittest.mock import Mock,patch
  cases=[(b'','eof'),(b'bad','partial_event'),(struct.pack('<IIHHi',1,1000000,1,116,0),'invalid_timestamp'),(struct.pack('<IIHHi',1,0,0,3,0),'events_dropped'),(struct.pack('<IIHHi',1,0,1,773,3),'invalid_key_value')]
  for data,reason in cases:
   with self.subTest(reason=reason):
    hr,hw=os.pipe();log=io.StringIO()
    try:
     with patch.object(reader.os,'set_blocking'),patch.object(reader.os,'read',side_effect=[BlockingIOError(),data]),contextlib.redirect_stderr(log):
      reader.observe(42,hw,Mock(side_effect=[False,True]))
     os.close(hw);hw=None
     self.assertEqual(os.read(hr,256),b'LOST\n')
     self.assertEqual(json.loads(log.getvalue()),{'event':'input-observer-fault','phase':'startup','reason':reason})
    finally:
     os.close(hr)
     if hw is not None:os.close(hw)
 def test_input_loss_recovers(self):
  self.assertEqual(self.run_input(struct.pack('<IIHHi',1,0,0,3,0)),'input_lost')
 def test_partial_event_recovers(self):
  self.assertEqual(self.run_input(b'bad'),'input_lost')

class DiscoveryTests(unittest.TestCase):
 def test_disconnected_unrelated_node_is_skipped(self):
  import emergency_reader as r,errno
  from unittest.mock import patch,Mock
  paths=[Path('/dev/input/event11'),Path('/dev/input/event3')]
  def opened(path,flags):
   self.assertEqual(flags & os.O_ACCMODE,os.O_RDONLY)
   if path==paths[0]:raise OSError(errno.ENXIO,'inactive')
   return 42
  with patch.object(r.struct,'calcsize',side_effect=lambda fmt:16 if fmt=='@llHHi' else 4),patch.object(r.Path,'glob',return_value=paths),patch.object(r.os,'open',side_effect=opened),patch.object(r.os,'fstat',return_value=Mock(st_mode=0o020600)),patch.object(r,'query',return_value=r.NAME+b'\0'),patch.object(r.os,'close'):
   self.assertEqual(r.open_remote(),42)

class FaultDiagnosticsTests(unittest.TestCase):
 def test_each_input_loss_has_a_safe_phase_and_cause_without_changing_protocol(self):
  import contextlib,io,json
  import emergency_reader as reader
  from unittest.mock import patch
  event=lambda kind,code,value,usec=0:struct.pack('<IIHHi',1,usec,kind,code,value)
  cases=[
   ([b''],True,'startup','eof',b'LOST\n'),
   ([BlockingIOError()]*64,False,'startup','keys_held',b'LOST\n'),
   ([event(1,773,1)]*64,True,'startup','drain_limit',b'LOST\n'),
   ([BlockingIOError(),b''],True,'active','eof',b'READY\nLOST\n'),
   ([BlockingIOError(),b'bad'],True,'active','partial_event',b'READY\nLOST\n'),
   ([BlockingIOError(),event(1,773,1,1000000)],True,'active','invalid_timestamp',b'READY\nLOST\n'),
   ([BlockingIOError(),event(0,3,0)],True,'active','events_dropped',b'READY\nLOST\n'),
   ([BlockingIOError(),event(1,773,3)],True,'active','invalid_key_value',b'READY\nLOST\n'),
   ([BlockingIOError()]+[event(0,0,0)]*64,True,'active','drain_limit',b'READY\nLOST\n'),
  ]
  for reads,released,phase,reason,wire in cases:
   with self.subTest(phase=phase,reason=reason):
    hr,hw=os.pipe();log=io.StringIO()
    try:
     with patch.object(reader.os,'set_blocking'),patch.object(reader.os,'read',side_effect=reads),patch.object(reader.select,'select',return_value=([42],[],[])),contextlib.redirect_stderr(log):
      reader.observe(42,hw,lambda:released)
     os.close(hw);hw=None
     self.assertEqual(os.read(hr,256),wire)
     self.assertTrue(log.getvalue(), 'Input failure must identify its phase and cause')
     self.assertEqual(json.loads(log.getvalue()),{'event':'input-observer-fault','phase':phase,'reason':reason})
    finally:
     os.close(hr)
     if hw is not None:os.close(hw)

 def test_full_diagnostic_log_does_not_hide_input_loss(self):
  import contextlib,errno
  import emergency_reader as reader
  from unittest.mock import Mock,patch
  hr,hw=os.pipe()
  log=Mock();log.write.side_effect=OSError(errno.ENOSPC,'full')
  try:
   with patch.object(reader.os,'set_blocking'),patch.object(reader.os,'read',return_value=b''),contextlib.redirect_stderr(log):
    reader.observe(42,hw,lambda:True)
   os.close(hw);hw=None
   self.assertEqual(os.read(hr,256),b'LOST\n')
  finally:
   os.close(hr)
   if hw is not None:os.close(hw)

 def test_io_errors_keep_their_existing_exit_path_and_report_only_errno(self):
  import contextlib,errno,io,json
  import emergency_reader as reader
  from unittest.mock import patch
  for phase in ('startup','active'):
   with self.subTest(phase=phase):
    hr,hw=os.pipe();log=io.StringIO()
    reads=([BlockingIOError()] if phase=='active' else [])+[OSError(errno.ENODEV,'private device text')]
    try:
     with patch.object(reader.os,'set_blocking'),patch.object(reader.os,'read',side_effect=reads),patch.object(reader.select,'select',return_value=([42],[],[])),contextlib.redirect_stderr(log):
      with self.assertRaises(OSError):reader.observe(42,hw,lambda:True)
     os.close(hw);hw=None
     self.assertEqual(os.read(hr,256),b'READY\n' if phase=='active' else b'')
     self.assertTrue(log.getvalue(), 'I/O failure must identify its phase and errno')
     self.assertEqual(json.loads(log.getvalue()),{'event':'input-observer-fault','phase':phase,'reason':'read_error','errno':19})
    finally:
     os.close(hr)
     if hw is not None:os.close(hw)
