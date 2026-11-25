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
 def test_unreadable_input_directory_is_a_fault_instead_of_verified_device_absence(self):
  import errno
  import emergency_reader as reader
  from unittest.mock import patch
  with patch.object(reader.struct,'calcsize',side_effect=lambda fmt:16 if fmt=='@llHHi' else 4), \
       patch.object(reader.Path,'iterdir',side_effect=PermissionError(errno.EACCES,'denied')), \
       self.assertRaises(PermissionError):
   reader.open_remote()

 def test_disconnected_unrelated_node_is_skipped(self):
  import emergency_reader as r,errno
  from unittest.mock import patch,Mock
  paths=[Path('/dev/input/event11'),Path('/dev/input/event3')]
  def opened(path,flags):
   self.assertEqual(flags & os.O_ACCMODE,os.O_RDONLY)
   if path==paths[0]:raise OSError(errno.ENXIO,'inactive')
   return 42
  with patch.object(r.struct,'calcsize',side_effect=lambda fmt:16 if fmt=='@llHHi' else 4),patch.object(r.Path,'iterdir',return_value=paths),patch.object(r.os,'open',side_effect=opened),patch.object(r.os,'fstat',return_value=Mock(st_mode=0o020600)),patch.object(r,'query',return_value=r.NAME+b'\0'),patch.object(r.os,'close'):
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
  for phase, typed, code in (('startup',True,errno.ENODEV),
                             ('active',True,errno.ENODEV),
                             ('active',True,errno.EIO),
                             ('active',False,errno.EIO)):
   with self.subTest(phase=phase,typed=typed,code=code):
    hr,hw=os.pipe();log=io.StringIO()
    reads=([BlockingIOError()] if phase=='active' else [])+[OSError(code,'private device text')]
    try:
     with patch.object(reader.os,'set_blocking'),patch.object(reader.os,'read',side_effect=reads),patch.object(reader.select,'select',return_value=([42],[],[])),patch.object(reader,'open_remote',side_effect=AssertionError('Terminal loss must not reconnect')),contextlib.redirect_stderr(log):
      with self.assertRaises(OSError):reader.observe(42,hw,lambda:True,report_device_gone=typed)
     os.close(hw);hw=None
     frames=os.read(hr,256).splitlines()
     if phase=='active' and typed and code==errno.ENODEV:
      self.assertEqual(len(frames),2)
      self.assertEqual(frames[0],b'READY')
      self.assertRegex(frames[1],rb'^DEVICE_GONE [0-9]+\.[0-9]{9}$')
     else:self.assertEqual(frames,[b'READY'] if phase=='active' else [])
     self.assertTrue(log.getvalue(), 'I/O failure must identify its phase and errno')
     self.assertEqual(json.loads(log.getvalue()),{'event':'input-observer-fault','phase':phase,'reason':'read_error','errno':code})
    finally:
     os.close(hr)
     if hw is not None:os.close(hw)

class ReconnectTests(unittest.TestCase):
    def replay(self, reads, candidates=None, query=None, clock=None, *, c1=False, guardian_events=None, recover=False, wait_input=False, profile=False, boot_wait=False, initial=42, sleep=None, log=None):
        import contextlib
        import io
        import emergency_reader as reader
        from contextlib import ExitStack
        from unittest.mock import patch

        def capabilities(fd, nr, size):
            bits = bytearray(size)
            if nr == 0x21:
                for code in (773, 412):
                    bits[code // 8] |= 1 << (code % 8)
            return bits

        messages = []
        with ExitStack() as stack:
            for target, name, options in (
                (reader.os, 'set_blocking', {}),
                (reader.os, 'read', {'side_effect': reads}),
                (reader.os, 'write', {'side_effect': lambda fd, data: messages.append(data) or len(data)}),
                (reader.select, 'select', {'return_value': ([42], [], [])}),
                (reader, 'query', {'side_effect': query or capabilities}),
            ):
                stack.enter_context(patch.object(target, name, **options))
            replace = stack.enter_context(patch.object(reader.os, 'dup2'))
            close = stack.enter_context(patch.object(reader.os, 'close'))
            opened = stack.enter_context(patch.object(reader, 'open_remote', side_effect=candidates or [43]))
            if clock:
                stack.enter_context(patch.object(reader.time, 'monotonic', side_effect=clock))
                stack.enter_context(patch.object(reader.time, 'sleep', side_effect=sleep))
            stack.enter_context(contextlib.redirect_stderr(log or io.StringIO()))
            if c1 or profile:
                poll = stack.enter_context(patch.object(reader.select, 'poll'))
                poll.return_value.poll.side_effect = guardian_events or (lambda _: [])
                if profile:
                    reader.observe(initial, 99, lambda: True, recover_profile_input=True)
                else:
                    reader.observe(initial, 99, lambda: True, reconnect_on_disconnect=True, recover_input=recover, wait_input=wait_input, boot_wait=boot_wait)
            else:
                reader.observe(42, 99, lambda: True)
        return messages, replace, close, opened

    def taps(self, count, start=0):
        import emergency_reader as reader
        return b''.join(reader.EVENT.pack(2, (start + tap * 300 + offset) * 1000, 1, 773, value)
                        for tap in range(count) for offset, value in ((0, 1), (100, 0)))

    def test_disconnected_reader_can_wait_overnight_without_renewing_input_health(self):
        import emergency_reader as reader
        for profile in (False, True):
            with self.subTest(profile=profile):
                now = [100.0]
                pauses = []
                def sleep(seconds):
                    pauses.append(seconds)
                    now[0] += 8 * 3600 if len(pauses) == 1 else seconds

                messages, _, _, opened = self.replay(
                    [BlockingIOError(), b'', self.taps(3)],
                    candidates=[reader.InputUnavailable('missing')] * 3 + [43],
                    c1=True, wait_input=not profile, profile=profile, clock=lambda: now[0], sleep=sleep)
                self.assertEqual(opened.call_count, 4)
                self.assertEqual(messages[0], b'READY\n')
                self.assertEqual(messages[-1], b'ESCAPE\n')
                self.assertGreaterEqual(len(messages[1:-1]), 3)
                for frame in messages[1:-1]:
                    self.assertRegex(frame, rb'^WAIT [0-9]+\n$')
                self.assertTrue(all(.25 <= pause <= 1 for pause in pauses))

    def test_confirmed_profile_can_start_with_input_missing_then_validate_before_ping(self):
        import emergency_reader as reader
        messages, _, _, _ = self.replay(
            [BlockingIOError(), BlockingIOError(), self.taps(3)],
            candidates=[reader.InputUnavailable('missing'), 43], profile=True, initial=None)
        self.assertRegex(messages[0], rb'^WAIT [0-9]+\n$')
        self.assertRegex(messages[-3], rb'^CHECK [0-9]+\n$')
        self.assertEqual(messages[-2:], [b'PING\n', b'ESCAPE\n'])
        self.assertNotIn(b'READY\n', messages)

    def test_resumed_compositor_boot_waits_for_native_ack_before_heartbeat(self):
        from unittest.mock import patch
        import emergency_reader as reader
        with patch.object(reader, 'recheck_acknowledged', return_value=True):
            messages, _, _, _ = self.replay(
                [BlockingIOError(), BlockingIOError(), BlockingIOError(), self.taps(3)],
                candidates=[reader.InputUnavailable('missing'), 43], c1=True, boot_wait=True, initial=None)
        self.assertRegex(messages[0], rb'^WAIT [0-9]+\n$')
        self.assertRegex(messages[1], rb'^CHECK [0-9]+\n$')
        self.assertEqual(messages[2:], [b'PING\n', b'ESCAPE\n'])

    def test_profile_device_disappears_after_open_and_before_startup_drain(self):
        messages, _, _, _ = self.replay(
            [b'', BlockingIOError(), BlockingIOError(), self.taps(3)], profile=True)
        self.assertRegex(messages[0], rb'^WAIT [0-9]+\n$')
        self.assertRegex(messages[1], rb'^CHECK [0-9]+\n$')
        self.assertEqual(messages[2:], [b'PING\n', b'ESCAPE\n'])

    def test_held_replacement_key_prevents_rearming_without_disabling_triple_home(self):
        import emergency_reader as reader
        def held(fd, nr, size):
            bits = bytearray(size)
            for code in ((773, 412) if nr == 0x21 else (116,)):
                bits[code // 8] |= 1 << (code % 8)
            return bits
        messages, _, _, _ = self.replay(
            [BlockingIOError(), b'', BlockingIOError(), self.taps(3)],
            profile=True, query=held)
        self.assertEqual(messages[0], b'READY\n')
        self.assertEqual(messages[-1], b'ESCAPE\n')
        self.assertTrue(messages[1:-1])
        self.assertTrue(all(frame.startswith(b'WAIT ') for frame in messages[1:-1]))

    def test_new_key_down_after_reopen_is_rechecked_before_routing(self):
        key_states = iter(((), (116,), ()))
        def query(fd, nr, size):
            bits = bytearray(size)
            for code in ((773, 412) if nr == 0x21 else next(key_states)):
                bits[code // 8] |= 1 << (code % 8)
            return bits
        messages, _, _, _ = self.replay(
            [BlockingIOError(), b'', BlockingIOError(), self.taps(3)],
            profile=True, query=query)
        self.assertEqual(messages[-1], b'ESCAPE\n')
        self.assertFalse(any(frame.startswith(b'CHECK ') for frame in messages),
                         'Key went down between opening the device and publishing CHECK')

    def test_device_that_reopens_but_immediately_returns_eof_keeps_waiting(self):
        from io import StringIO
        log = StringIO()
        elapsed = [100.0]
        def sleep(seconds):
            elapsed[0] += seconds
        count = 100
        messages, _, _, opened = self.replay(
            [BlockingIOError()] + [b''] * count + [self.taps(3)],
            profile=True, candidates=[43] * count, clock=lambda: elapsed[0], sleep=sleep, log=log)
        self.assertEqual(messages[-1], b'ESCAPE\n')
        self.assertEqual(opened.call_count, count)
        self.assertGreaterEqual(elapsed[0], 100 + .25 * (count - 1))
        self.assertEqual(len(log.getvalue().splitlines()), 1)
        self.assertTrue(all(frame.startswith(b'WAIT ') for frame in messages[1:-1]))

    def test_scheduler_gap_preserves_emergency_events_queued_on_original_device(self):
        import emergency_reader as reader
        from itertools import chain, repeat
        # Startup deadline and first heartbeat run before suspension. Afterwards
        # the old queue contains the entire emergency gesture from that interval.
        clock = chain((100., 100.), repeat(103.))
        startup = [True]
        reopened = [False]
        def read(fd, size):
            if startup:
                startup.pop()
                raise BlockingIOError
            if reopened[0]:
                return reader.EVENT.pack(2, 0, 0, 3, 0)
            return self.taps(3)
        def open_remote():
            reopened[0] = True
            return 43
        messages, _, _, _ = self.replay(read, candidates=open_remote, c1=True, wait_input=True,
                                         clock=lambda: next(clock))
        self.assertEqual(messages[-1], b'ESCAPE\n')

    def test_elapsed_sleep_alone_cannot_turn_a_short_back_press_into_a_long_back(self):
        import emergency_reader as reader
        elapsed = [100.]
        reads = iter((BlockingIOError(), reader.EVENT.pack(2, 0, 1, 412, 1),
                      BlockingIOError(), None, self.taps(3)))
        def read(fd, size):
            event = next(reads)
            if event is None:
                elapsed[0] += 3600
                raise BlockingIOError
            if isinstance(event, BlockingIOError):
                raise event
            return event
        messages, _, _, _ = self.replay(read, c1=True, wait_input=True, clock=lambda: elapsed[0])
        self.assertEqual(messages[-1], b'ESCAPE\n')
        self.assertNotIn(b'LGHOME\n', messages)

    def test_second_loss_before_check_acknowledgement_immediately_revokes_again(self):
        import emergency_reader as reader
        messages, _, _, _ = self.replay(
            [BlockingIOError(), b'', BlockingIOError(), b'', self.taps(3)],
            c1=True, wait_input=True, candidates=[43, 44],
            clock=lambda: 100., sleep=lambda _: None)
        self.assertEqual([frame.split()[0] for frame in messages],
                         [b'READY', b'WAIT', b'CHECK', b'WAIT', b'ESCAPE'])

    def test_older_guardian_protocol_still_expires_without_any_wait_frame(self):
        import emergency_reader as reader
        now = [100.]
        def sleep(seconds):
            now[0] += 61
        messages, _, _, _ = self.replay(
            [BlockingIOError(), b''], c1=True, recover=True,
            candidates=[reader.InputUnavailable('missing')],
            clock=lambda: now[0], sleep=sleep)
        self.assertEqual(messages, [b'READY\n', b'LOST\n'])

    def test_untrusted_replacement_cannot_keep_the_new_reader_alive(self):
        import errno
        for candidate in (ValueError('ambiguous'), OSError(errno.EACCES, 'inaccessible')):
            with self.subTest(candidate=candidate):
                messages, _, _, _ = self.replay(
                    [BlockingIOError(), b''], c1=True, wait_input=True, candidates=[candidate])
                self.assertEqual([frame.split()[0] for frame in messages],
                                 [b'READY', b'WAIT', b'LOST'])

    def test_c1_reopens_after_eof_and_delivers_escape_before_a_heartbeat(self):
        import emergency_reader as reader
        messages, replace, _, opened = self.replay(
            [BlockingIOError(), b'', self.taps(3)],
            candidates=[reader.InputUnavailable('missing'), 43], c1=True)
        self.assertEqual(opened.call_count, 2)
        replace.assert_called_once_with(43, 42, inheritable=False)
        self.assertEqual(messages, [b'READY\n', b'ESCAPE\n'])

    def test_c1_replacement_can_renew_only_after_a_valid_read(self):
        import emergency_reader as reader
        dropped = reader.EVENT.pack(2, 0, 0, 3, 0)
        messages, replace, _, _ = self.replay(
            [BlockingIOError(), b'', BlockingIOError(), dropped], c1=True)
        replace.assert_called_once_with(43, 42, inheritable=False)
        self.assertEqual(messages, [b'READY\n', b'PING\n', b'LOST\n'])

    def test_c1_reconnect_abandons_open_descriptor_if_guardian_retires(self):
        import select
        messages, replace, close, opened = self.replay(
            [BlockingIOError(), b''], c1=True,
            guardian_events=[[], [(99, select.POLLERR)]])
        opened.assert_called_once()
        replace.assert_not_called()
        close.assert_called_once_with(43)
        self.assertEqual(messages, [b'READY\n'])

    def test_c1_home_activity_while_replacement_keys_are_held_cancels_recovery(self):
        def held_other_key(fd, nr, size):
            bits = bytearray(size)
            for code in ((773, 412) if nr == 0x21 else (116,)):
                bits[code // 8] |= 1 << (code % 8)
            return bits

        messages, replace, close, _ = self.replay(
            [BlockingIOError(), b'', self.taps(3)], c1=True, query=held_other_key)
        replace.assert_not_called()
        close.assert_called_once_with(43)
        self.assertEqual(messages, [b'READY\n', b'LOST\n'])

    def test_c1_reopens_when_old_descriptor_reports_enxio(self):
        import errno
        messages, replace, _, _ = self.replay(
            [BlockingIOError(), OSError(errno.ENXIO, 'gone'), self.taps(3)], c1=True)
        replace.assert_called_once_with(43, 42, inheritable=False)
        self.assertEqual(messages, [b'READY\n', b'ESCAPE\n'])

    def test_c1_rechecks_device_after_scheduler_gap_before_renewing(self):
        from itertools import chain, count
        import emergency_reader as reader
        dropped = reader.EVENT.pack(2, 0, 0, 3, 0)
        clock = chain([0, 0, 2.1], count(2.2, .1))
        messages, replace, _, opened = self.replay(
            [BlockingIOError(), BlockingIOError(), dropped],
            c1=True, recover=True, clock=lambda: next(clock))
        opened.assert_called_once()
        replace.assert_called_once_with(43, 42, inheritable=False)
        self.assertEqual(messages[0], b'READY\n')
        self.assertRegex(messages[1], rb'^CHECK [0-9]+\n$')
        self.assertEqual(messages[2:], [b'LOST\n'])

    def test_c1_revalidates_again_if_first_check_has_no_acknowledgement(self):
        from itertools import chain, count
        from unittest.mock import patch
        import emergency_reader as reader
        dropped = reader.EVENT.pack(2, 0, 0, 3, 0)
        clock = chain([0, 0, 2.1], count(2.2, .2))
        with patch.object(reader, 'recheck_acknowledged', side_effect=[False, True]), \
             patch.object(reader.time, 'clock_gettime_ns',
                          side_effect=[10_000_000_000, 10_000_000_000, 10_300_000_000, 10_300_000_000]):
            messages, _, _, _ = self.replay(
                [BlockingIOError()] * 5 + [dropped], c1=True, recover=True,
                clock=lambda: next(clock))
        self.assertEqual(messages, [b'READY\n', b'CHECK 10000\n',
                                    b'CHECK 10300\n', b'PING\n', b'LOST\n'])

    def test_c1_triple_home_across_reads_wins_before_recheck(self):
        messages, _, _, _ = self.replay(
            [BlockingIOError(), b'', self.taps(2), BlockingIOError(), self.taps(1, 600)],
            c1=True, wait_input=True)
        self.assertEqual(messages[0], b'READY\n')
        self.assertRegex(messages[1], rb'^WAIT [0-9]+\n$')
        self.assertEqual(messages[2:], [b'ESCAPE\n'])

    def test_enodev_replacement_keeps_health_and_emergency_escape(self):
        import errno
        messages, replace, close, _ = self.replay([
            BlockingIOError(), OSError(errno.ENODEV, 'gone'), self.taps(3)])
        replace.assert_called_once_with(43, 42, inheritable=False)
        close.assert_called_once_with(43)
        self.assertEqual(messages, [b'READY\n', b'ESCAPE\n'])

    def test_partial_gesture_cannot_cross_input_device_instances(self):
        import errno
        messages, _, _, _ = self.replay([
            BlockingIOError(), self.taps(2), OSError(errno.ENODEV, 'gone'),
            self.taps(1, 600), BlockingIOError(), b''])
        self.assertEqual(messages, [b'READY\n', b'PING\n', b'LOST\n'])

    def test_temporarily_missing_device_is_retried_without_a_heartbeat(self):
        import errno
        import emergency_reader as reader
        messages, _, _, opened = self.replay([
            BlockingIOError(), OSError(errno.ENODEV, 'gone'), self.taps(3)],
            candidates=[reader.InputUnavailable('missing'), 43])
        self.assertEqual(opened.call_count, 2)
        self.assertEqual(messages, [b'READY\n', b'ESCAPE\n'])

    def test_reconnect_timeout_reports_loss_without_renewing_health(self):
        import errno
        import emergency_reader as reader
        messages, replace, _, _ = self.replay([
            BlockingIOError(), OSError(errno.ENODEV, 'gone')],
            candidates=[reader.InputUnavailable('missing')], clock=[0, 0, 1, 1])
        self.assertEqual(messages, [b'READY\n', b'LOST\n'])
        replace.assert_not_called()

    def test_ambiguous_or_unusable_replacement_fails_open(self):
        import errno
        for candidate in (ValueError('ambiguous'), OSError(errno.EACCES, 'denied')):
            with self.subTest(candidate=candidate):
                messages, replace, _, _ = self.replay([
                    BlockingIOError(), OSError(errno.ENODEV, 'gone')], candidates=[candidate])
                self.assertEqual(messages, [b'READY\n', b'LOST\n'])
                replace.assert_not_called()

    def test_repeated_enodev_never_renews_health_and_keeps_one_deadline(self):
        import errno
        from itertools import count
        clock = count(0, .1)
        messages, _, _, opened = self.replay(
            [BlockingIOError()] + [OSError(errno.ENODEV, 'gone')] * 10,
            candidates=[43] * 10, clock=lambda: next(clock))
        self.assertEqual(messages, [b'READY\n', b'LOST\n'])
        self.assertLess(opened.call_count, 10)

    def test_held_keys_cannot_publish_replacement_health(self):
        import errno
        from itertools import count
        clock = count(0, .1)
        def held(fd, nr, size):
            bits = bytearray(size)
            for code in (773, 412):
                bits[code // 8] |= 1 << (code % 8)
            return bits
        messages, replace, _, _ = self.replay(
            [BlockingIOError(), OSError(errno.ENODEV, 'gone')],
            candidates=[43] * 10, query=held, clock=lambda: next(clock))
        self.assertEqual(messages, [b'READY\n', b'LOST\n'])
        replace.assert_not_called()

    def test_long_back_still_opens_lg_home_after_replacement(self):
        import errno
        import emergency_reader as reader
        from itertools import count
        clock = count(0, .1)
        messages, _, _, _ = self.replay(
            [BlockingIOError(), OSError(errno.ENODEV, 'gone'),
             reader.EVENT.pack(2, 0, 1, 412, 1)] + [BlockingIOError()] * 20 + [b''],
            clock=lambda: next(clock))
        self.assertEqual(messages.count(b'LGHOME\n'), 1)
        self.assertNotIn(b'ESCAPE\n', messages)

    def test_current_setting_gates_one_hold_and_triple_home_still_fires(self):
        import device_adapter as d
        import emergency_reader as reader
        import json, tempfile
        from unittest.mock import patch

        on = json.dumps({'enabled': True, 'generation': 'a'*32})
        off = json.dumps({'enabled': False, 'generation': 'b'*32})
        on_again = json.dumps({'enabled': True, 'generation': 'c'*32})
        with tempfile.TemporaryDirectory() as directory, patch.object(d, 'STATE', Path(directory)), \
                patch.object(d, 'EXPECTED_UID', os.getuid()):
            prefs = Path(directory)/'long-back.json'
            for profile, c1 in [(False, False), (True, False), (False, True)]:
                for before, after, visits in [(on, on, 1), (off, off, 0), (on, off, 0),
                                              (off, on, 0), (on, on_again, 0), ('broken', 'broken', 0)]:
                    with self.subTest(profile=profile, c1=c1, before=before, after=after):
                        now = [100.]
                        def events():
                            yield BlockingIOError()  # Startup drain.
                            prefs.write_text(before)
                            yield reader.EVENT.pack(2, 0, 1, 412, 1)
                            yield BlockingIOError()
                            prefs.write_text(after)
                            for _ in range(14):
                                now[0] += .1
                                yield BlockingIOError()
                            yield reader.EVENT.pack(2, 0, 1, 412, 0)
                            yield self.taps(3)
                        messages, _, _, _ = self.replay(events(), profile=profile, c1=c1,
                                                         clock=lambda: now[0])
                        self.assertEqual(messages.count(b'LGHOME\n'), visits)
                        self.assertEqual(messages[-1], b'ESCAPE\n')

    def test_replacement_requires_home_and_back_capabilities(self):
        import errno
        messages, replace, close, _ = self.replay([
            BlockingIOError(), OSError(errno.ENODEV, 'gone')], query=lambda fd, nr, size: bytearray(size))
        self.assertEqual(messages, [b'READY\n', b'LOST\n'])
        replace.assert_not_called()
        close.assert_called_once_with(43)

    def test_real_descriptor_replacement_delivers_emergency_and_closes_new_fd(self):
        import contextlib
        import errno
        import io
        import emergency_reader as reader
        from unittest.mock import patch
        old_read, old_write = os.pipe()
        new_read, new_write = os.pipe()
        health_read, health_write = os.pipe()
        original_read = os.read
        reads = 0
        def device_read(fd, size):
            nonlocal reads
            reads += 1
            if reads == 2:
                raise OSError(errno.ENODEV, 'device replaced')
            return original_read(fd, size)
        def query(fd, nr, size):
            bits = bytearray(size)
            if nr == 0x21:
                for code in (773, 412):
                    bits[code // 8] |= 1 << (code % 8)
            return bits
        try:
            os.write(new_write, self.taps(3))
            os.set_blocking(new_read, False)
            with patch.object(reader.os, 'read', side_effect=device_read), \
                    patch.object(reader, 'open_remote', return_value=new_read), \
                    patch.object(reader, 'query', side_effect=query), \
                    contextlib.redirect_stderr(io.StringIO()):
                reader.observe(old_read, health_write, lambda: True)
            self.assertEqual(original_read(health_read, 128), b'READY\nESCAPE\n')
            self.assertFalse(os.get_inheritable(old_read))
            with self.assertRaises(OSError):
                os.fstat(new_read)
            new_read = None
        finally:
            for fd in (old_read, old_write, new_read, new_write, health_read, health_write):
                if fd is not None:
                    try: os.close(fd)
                    except OSError: pass
