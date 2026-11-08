"""Compile and exercise the independent native guardian; no mounts or TV access."""
import json
import os
from pathlib import Path
import select
import shutil
import signal
import subprocess
import tempfile
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'root-edition/gate/keyfilter.c'
TOKEN = 'a' * 32
BOOT = '01234567-89ab-cdef-0123-456789abcdef'

@unittest.skipUnless(os.name == 'posix' and shutil.which('cc'), 'POSIX compiler required')
class KeyfilterGuardTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SOURCE.is_file(), 'native keyfilter guardian missing')
        self.tmp = tempfile.TemporaryDirectory(prefix='cytv-keyfilter-')
        self.root = Path(self.tmp.name).resolve()
        self.binary = self.root / 'guard'
        subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                        '-DCYTV_KEYFILTER_FIXTURE', f'-DFIXTURE_ROOT="{self.root}"',
                        str(SOURCE), '-o', str(self.binary)], check=True, capture_output=True)
        for name in ('state', 'volatile'):
            (self.root / name).mkdir(mode=0o700)
        (self.root / 'home').write_bytes(b'LG Home executable')
        (self.root / 'home').chmod(0o700)
        (self.root / 'boot').write_text(BOOT + '\n')
        self.config()
        self.luna_script = ('#!/bin/sh\n'
            'case "$*" in *launch*com.cleanyourtv.root.preview*) ;; *) test -s "'+str(self.root/'state/stopped')+'" || exit 80 ;; esac\n'
            'printf "%s\\n" "$*" >> "'+str(self.root/'luna-calls')+'"\n'
            'case "$*" in *launch*com.cleanyourtv.root.preview*) if test -f "'+str(self.root/'root-delay')+'"; then touch "'+str(self.root/'root-entered')+'"; sleep 1; fi ;; esac\n'
            'if test -f "'+str(self.root/'luna-slow')+'"; then sleep 20; fi\n'
            'case "$*" in *closeByAppId*) if test -f "'+str(self.root/'luna-close-reply')+'"; then cat "'+str(self.root/'luna-close-reply')+'"; exit 0; fi ;; esac\n'
            'if test -f "'+str(self.root/'luna-reply')+'"; then cat "'+str(self.root/'luna-reply')+'"; else echo "{\\\"returnValue\\\":true}"; fi\n')
        (self.root/'luna').write_text(self.luna_script); (self.root/'luna').chmod(0o700)
        self.guards = []
    def tearDown(self):
        for p, writers in getattr(self, 'guards', []):
            for w in writers:
                try: os.close(w)
                except OSError: pass
            if p.poll() is None: p.terminate()
            try: p.communicate(timeout=5)
            except subprocess.TimeoutExpired: p.kill(); p.communicate()
        if hasattr(self, 'tmp'): self.tmp.cleanup()
    def config(self):
        s = (self.root / 'home').stat()
        p = self.root / 'state/config'
        p.write_text(f'CYTV-C1-KEYFILTER-1\ntoken {TOKEN}\nboot {BOOT}\ndev {s.st_dev}\nino {s.st_ino}\nsize {s.st_size}\nmtime_ns {s.st_mtime_ns}\n')
        p.chmod(0o600)
    def run_guard(self, *args):
        p = subprocess.run([str(self.binary), *args], capture_output=True, text=True, timeout=8)
        self.assertEqual(p.stderr, '')
        return json.loads(p.stdout), p.returncode
    def spawn(self, seconds=0, ready=(True, True), broker=True):
        ir, iw = os.pipe(); cr, cw = os.pipe(); rr, rw = os.pipe()
        # Queue the tiny fixture records while our read ends are still open;
        # a stopped guardian may refuse and close its inherited ends at once.
        for flag, fd in zip(ready, (iw, cw)):
            if flag: os.write(fd, b'READY\n')
        p = subprocess.Popen([str(self.binary), '--guard', TOKEN, str(ir), str(cr), str(rw), str(seconds)],
                             pass_fds=(ir, cr, rw), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for fd in (ir, cr, rw): os.close(fd)
        self.guards.append((p, (iw, cw)))
        if broker:
            deadline = time.monotonic() + 1
            while time.monotonic() < deadline:
                self.run_guard('--lease')
                if select.select([rr], [], [], .03)[0]: break
        return p, iw, cw, rr
    def armed(self, seconds=0):
        p, iw, cw, rr = self.spawn(seconds)
        self.assertTrue(select.select([rr], [], [], 3)[0])
        ack = os.read(rr, 128); os.close(rr)
        self.assertEqual(ack, f'ARMED {TOKEN}\n'.encode())
        return p, iw, cw
    def finish(self, p):
        out, err = p.communicate(timeout=7)
        self.assertEqual(err, '')
        return json.loads(out)
    def test_selfcheck_and_stock_contract(self):
        s, rc = self.run_guard('--selfcheck'); self.assertEqual(rc, 0)
        self.assertEqual(s['routing'], 'compositor-keyfilter-v1')
        s, rc = self.run_guard('--status'); self.assertEqual(rc, 0)
        self.assertEqual(s['state'], 'stock'); self.assertTrue(s['stock_verified'])
        self.assertFalse(s['mounted']); self.assertFalse(s['healthy']); self.assertIsNone(s['profiles'])
    def test_config_is_strict_and_private(self):
        p = self.root / 'state/config'; original = p.read_text()
        for raw in (original + '\n', original.replace('dev ', 'ino '), original.replace(TOKEN, 'g'*32), original+'\x00'):
            p.write_text(raw); s, rc = self.run_guard('--status')
            self.assertNotEqual(rc, 0); self.assertFalse(s['stock_verified'])
        p.write_text(original); p.chmod(0o644)
        self.assertNotEqual(self.run_guard('--status')[1], 0)
    def test_both_observers_and_broker_required(self):
        p, iw, cw, rr = self.spawn(ready=(True, False))
        self.assertFalse(select.select([rr], [], [], .1)[0])
        s, _ = self.run_guard('--lease'); self.assertFalse(s['healthy'])
        self.assertEqual(s['state'],'stock'); self.assertFalse(s['stock_verified'])
        self.assertGreater(s['guardian_pid'],1)
        os.write(cw, b'READY\n')
        self.assertTrue(select.select([rr], [], [], 1)[0]); self.assertTrue(os.read(rr,128).startswith(b'ARMED ')); os.close(rr)
        s, _ = self.run_guard('--status'); self.assertTrue(s['healthy'])
        os.write(iw, b'ESCAPE\n'); s = self.finish(p)
        self.assertTrue(s['stopped']); self.assertTrue(s['stock_verified']); self.assertEqual(s['reason'], 'escape')
        s, _ = self.run_guard('--lease'); self.assertFalse(s['healthy']); self.assertTrue(s['stopped'])
    def test_missing_broker_never_arms(self):
        p, iw, cw, rr = self.spawn(broker=False)
        s = self.finish(p); self.assertFalse(s['healthy']); self.assertTrue(s['stopped'])
        self.assertEqual(os.read(rr,128), b''); os.close(rr)
    def test_stale_independent_channels_and_broker(self):
        p, iw, cw = self.armed()
        started = time.monotonic()
        deadline = started + 2.3
        while p.poll() is None and time.monotonic() < deadline:
            time.sleep(.3)
            try: os.write(iw,b'PING\n')
            except BrokenPipeError: break
            # Keep the broker fresh beyond controller expiry, but stop renewing
            # before stale controller health can make --lease win the stop race.
            if time.monotonic() - started < 1.5:
                self.run_guard('--lease')
        s = self.finish(p); self.assertEqual(s['reason'], 'controller_expired'); self.assertFalse(s['healthy'])
    def test_broker_cannot_revive_expired_health(self):
        p, iw, cw = self.armed()
        deadline = time.monotonic() + 2.3
        while p.poll() is None and time.monotonic() < deadline:
            time.sleep(.3)
            try: os.write(iw,b'PING\n'); os.write(cw,b'PING\n')
            except BrokenPipeError: break
        s = self.finish(p); self.assertEqual(s['reason'], 'broker_expired')
        self.assertFalse(self.run_guard('--lease')[0]['healthy'])
    def test_trial_expiry(self):
        p, iw, cw = self.armed(1); s = self.finish(p); self.assertEqual(s['reason'], 'trial_expired')
    def test_restore_latches_before_retirement_and_no_rearm(self):
        p, iw, cw = self.armed(); s, rc = self.run_guard('--restore')
        self.assertEqual(rc,0); self.assertTrue(s['stopped']); self.assertTrue(s['stock_verified']); self.finish(p)
        stopped = (self.root/'state/stopped').read_bytes()
        launch = subprocess.Popen
        def refused_before_parent_resumes(*args, **kwargs):
            child = launch(*args, **kwargs)
            child.wait(timeout=3)
            return child
        # Reproduce the CI schedule: the retained stop latch lets the child
        # refuse before the parent continues after Popen.
        with mock.patch.object(subprocess, 'Popen', side_effect=refused_before_parent_resumes):
            p, iw, cw, rr = self.spawn(broker=False)
        refused = self.finish(p)
        self.assertFalse(refused['returnValue']); self.assertFalse(refused['healthy'])
        self.assertTrue(refused['stopped']); self.assertEqual(refused['reason'], 'guard_refused')
        self.assertEqual((self.root/'state/stopped').read_bytes(), stopped)
        self.assertEqual(os.read(rr,128), b''); os.close(rr)
    def test_malformed_active_is_preserved(self):
        (self.root/'state/active').write_text('invalid\n'); (self.root/'state/active').chmod(0o600)
        s, rc = self.run_guard('--restore'); self.assertNotEqual(rc,0)
        self.assertTrue((self.root/'state/active').exists()); self.assertFalse(s['stock_verified']); self.assertTrue(s['stopped'])
    def test_home_identity_change_blocks_health(self):
        p, iw, cw = self.armed(); (self.root/'home').write_bytes(b'changed')
        s, _ = self.run_guard('--lease'); self.assertFalse(s['healthy']); self.assertFalse(s['stock_verified'])
        s = self.finish(p); self.assertTrue(s['stopped'])

    def test_signal_latches_stop(self):
        p, iw, cw = self.armed(); p.send_signal(signal.SIGTERM)
        s = self.finish(p); self.assertEqual(s['reason'], 'signal'); self.assertTrue(s['stopped'])
    def test_malformed_observer_latches(self):
        p, iw, cw = self.armed(); os.write(iw, b'BAD\n')
        s = self.finish(p); self.assertEqual(s['reason'], 'malformed_input'); self.assertTrue(s['stopped'])
    def test_controller_lghome_latches(self):
        p, iw, cw = self.armed(); os.write(cw, b'LGHOME\n')
        self.assertEqual(self.finish(p)['reason'], 'lg_home')
    def test_observer_eof_latches(self):
        p, iw, cw = self.armed(); os.close(iw)
        s = self.finish(p); self.assertEqual(s['reason'], 'input_lost'); self.assertTrue(s['stock_verified'])
    def test_stale_input_does_not_get_controller_lease(self):
        p, iw, cw = self.armed(); deadline = time.monotonic()+2.5
        while p.poll() is None and time.monotonic()<deadline:
            time.sleep(.3)
            try: os.write(cw,b'PING\n')
            except BrokenPipeError: break
            self.run_guard('--lease')
        s = self.finish(p); self.assertFalse(s['healthy']); self.assertTrue(s['stopped'])
    def test_reused_pid_is_not_signalled(self):
        child = subprocess.Popen(['sleep','10'])
        try:
            p = self.root/'state/active'
            p.write_text(f'CYTV-KEYFILTER-ACTIVE-1\n{TOKEN}\n{BOOT}\n{child.pid} 1 1\n'); p.chmod(0o600)
            s, rc = self.run_guard('--restore')
            self.assertEqual(rc,0); self.assertIsNone(child.poll()); self.assertTrue(s['stock_verified'])
        finally: child.terminate(); child.wait()
    def test_killed_guard_cannot_be_reported_healthy(self):
        p, iw, cw = self.armed(); p.kill(); p.communicate()
        s, _ = self.run_guard('--status'); self.assertFalse(s['healthy'])
        s, _ = self.run_guard('--lease'); self.assertFalse(s['healthy'])
        s, rc = self.run_guard('--restore'); self.assertEqual(rc,0); self.assertTrue(s['stock_verified'])
    def test_malformed_stop_never_cleared(self):
        p = self.root/'state/stopped'; p.write_text('broken\n'); p.chmod(0o600)
        s, rc = self.run_guard('--lease'); self.assertNotEqual(rc,0); self.assertFalse(s['healthy'])
        self.assertEqual(p.read_text(),'broken\n'); self.assertNotEqual(self.run_guard('--restore')[1],0)
    def test_bootstrap_lease_has_no_guardian(self):
        s, rc = self.run_guard('--lease'); self.assertEqual(rc,0)
        self.assertEqual(s['guardian_pid'],0); self.assertFalse(s['healthy'])
        self.assertFalse((self.root/'state/active').exists())
        self.assertTrue((self.root/'volatile/broker').exists())
    def test_corrupt_broker_pulse_cannot_renew(self):
        p, iw, cw = self.armed()
        (self.root/'volatile/broker').write_text('broken\n')
        s, _ = self.run_guard('--lease'); self.assertFalse(s['healthy']); self.assertTrue(s['stopped'])
        self.finish(p)
    def test_missing_armed_broker_cannot_renew(self):
        p, iw, cw = self.armed(); (self.root/'volatile/broker').unlink()
        s, _ = self.run_guard('--lease'); self.assertFalse(s['healthy']); self.assertTrue(s['stopped'])
        self.finish(p)
    def test_state_symlink_and_nonprivate_directory_refused(self):
        state=self.root/'state'; real=self.root/'real-state'; state.rename(real); state.symlink_to(real, target_is_directory=True)
        self.assertNotEqual(self.run_guard('--status')[1],0)
        state.unlink(); real.rename(state); state.chmod(0o755)
        self.assertNotEqual(self.run_guard('--status')[1],0)
    def test_invalid_guard_descriptor_does_not_create_attempt(self):
        s, rc = self.run_guard('--guard', TOKEN, '0', '1', '2', '0')
        self.assertNotEqual(rc,0); self.assertFalse((self.root/'state/active').exists())
    def test_same_pipe_cannot_supply_both_channels(self):
        r,w=os.pipe(); duplicate=os.dup(r); rr,rw=os.pipe()
        try:
            child=subprocess.run([str(self.binary),'--guard',TOKEN,str(r),str(duplicate),str(rw),'1'],
                                 pass_fds=(r,duplicate,rw),capture_output=True,text=True,timeout=4)
            self.assertNotEqual(child.returncode,0)
            self.assertFalse((self.root/'state/active').exists())
        finally:
            for fd in (r,w,duplicate,rr,rw): os.close(fd)
    def test_escape_closes_only_owned_root_then_launches_stock_after_stop(self):
        p,iw,cw=self.armed(); os.write(iw,b'ESCAPE\n'); s=self.finish(p)
        self.assertTrue(s['stopped']); self.assertTrue(s['returnValue'])
        calls=(self.root/'luna-calls').read_text().splitlines()
        self.assertEqual(calls,[
            '-n 1 luna://com.webos.applicationManager/closeByAppId {"id":"com.cleanyourtv.root.preview"}',
            '-n 1 luna://com.webos.applicationManager/launch {"id":"com.webos.app.home"}'])
    def test_standalone_restore_releases_ui(self):
        s,rc=self.run_guard('--restore'); self.assertEqual(rc,0)
        self.assertTrue(s['stopped']); self.assertTrue((self.root/'luna-calls').is_file(),'standalone native restore must release UI')
        self.assertEqual(len((self.root/'luna-calls').read_text().splitlines()),2)
    def test_luna_malformed_reply_reports_failure_keeps_stop(self):
        (self.root/'luna-reply').write_text('{"returnValue":true,"returnValue":false}\n')
        s,rc=self.run_guard('--restore'); self.assertNotEqual(rc,0)
        self.assertTrue(s['stopped']); self.assertFalse(s['healthy']); self.assertEqual(s['reason'],'ui_release_failed')
        self.assertEqual(len((self.root/'luna-calls').read_text().splitlines()),2)
    def test_luna_timeout_bounded_and_does_not_kill_foreign_process(self):
        child=subprocess.Popen(['sleep','10'])
        try:
            (self.root/'luna-slow').touch(); started=time.monotonic()
            s,rc=self.run_guard('--restore'); self.assertNotEqual(rc,0)
            self.assertLess(time.monotonic()-started,6); self.assertIsNone(child.poll())
            self.assertTrue(s['stopped']); self.assertEqual(s['reason'],'ui_release_failed')
        finally: child.terminate(); child.wait()
    def test_home_launch_is_fixed_and_requires_fresh_guard(self):
        p,iw,cw=self.armed()
        s,rc=self.run_guard('--home',TOKEN)
        self.assertEqual(rc,0); self.assertTrue(s['healthy']); self.assertEqual(s['state'],'armed')
        self.assertEqual((self.root/'luna-calls').read_text().splitlines(),[
            '-n 1 luna://com.webos.applicationManager/launch {"id":"com.cleanyourtv.root.preview"}'])
        os.write(iw,b'ESCAPE\n'); self.finish(p)
    def test_home_refuses_stale_token_without_effect(self):
        p,iw,cw=self.armed(); s,rc=self.run_guard('--home','b'*32)
        self.assertNotEqual(rc,0); self.assertFalse((self.root/'luna-calls').exists())
        os.write(iw,b'ESCAPE\n'); self.finish(p)
    def test_home_after_restore_cannot_launch_root(self):
        self.run_guard('--restore'); before=(self.root/'luna-calls').read_text()
        s,rc=self.run_guard('--home',TOKEN); self.assertNotEqual(rc,0)
        self.assertEqual((self.root/'luna-calls').read_text(),before)
    def test_home_with_expired_broker_never_launches_root(self):
        p,iw,cw=self.armed(); (self.root/'volatile/broker').write_text(f'{TOKEN} {p.pid} 1 1 0 0\n')
        s,rc=self.run_guard('--home',TOKEN); self.assertNotEqual(rc,0)
        if (self.root/'luna-calls').exists():
            self.assertNotIn('launch {"id":"com.cleanyourtv.root.preview"}',(self.root/'luna-calls').read_text())
        self.finish(p)
    def test_home_effect_does_not_block_health_and_restore_orders_after_it(self):
        p,iw,cw=self.armed(); (self.root/'root-delay').touch()
        home=subprocess.Popen([str(self.binary),'--home',TOKEN],stdout=subprocess.PIPE,text=True)
        try:
            deadline=time.monotonic()+2
            while not (self.root/'root-entered').exists() and time.monotonic()<deadline: time.sleep(.01)
            self.assertTrue((self.root/'root-entered').exists())
            started=time.monotonic(); s,rc=self.run_guard('--status')
            self.assertLess(time.monotonic()-started,.5); self.assertEqual(rc,0); self.assertTrue(s['healthy'])
            started=time.monotonic(); s,rc=self.run_guard('--lease')
            self.assertLess(time.monotonic()-started,.5); self.assertEqual(rc,0)
            s,rc=self.run_guard('--restore'); self.assertEqual(rc,0); self.assertTrue(s['stopped'])
            home.communicate(timeout=5); self.finish(p)
            calls=(self.root/'luna-calls').read_text().splitlines()
            self.assertEqual(calls,[
                '-n 1 luna://com.webos.applicationManager/launch {"id":"com.cleanyourtv.root.preview"}',
                '-n 1 luna://com.webos.applicationManager/closeByAppId {"id":"com.cleanyourtv.root.preview"}',
                '-n 1 luna://com.webos.applicationManager/launch {"id":"com.webos.app.home"}'])
        finally:
            if home.poll() is None: home.kill(); home.communicate()
    def test_home_parent_death_cannot_release_effect_barrier_early(self):
        p,iw,cw=self.armed(); (self.root/'root-delay').touch()
        home=subprocess.Popen([str(self.binary),'--home',TOKEN],stdout=subprocess.PIPE,text=True)
        try:
            deadline=time.monotonic()+2
            while not (self.root/'root-entered').exists() and time.monotonic()<deadline: time.sleep(.01)
            self.assertTrue((self.root/'root-entered').exists())
            started=time.monotonic(); home.kill(); home.communicate(timeout=4)
            s,rc=self.run_guard('--restore'); self.assertEqual(rc,0); self.assertTrue(s['stopped'])
            # Linux kills the LS2 child on parent death; POSIX fixtures retain
            # the inherited effect lock until their already-issued work ends.
            if os.uname().sysname=='Darwin': self.assertGreater(time.monotonic()-started,.7)
            before=(self.root/'luna-calls').read_text(); time.sleep(.2)
            self.assertEqual((self.root/'luna-calls').read_text(),before); self.finish(p)
        finally:
            if home.poll() is None: home.kill(); home.communicate()
    def test_restore_retires_via_latch_without_queued_pid_signal(self):
        p,iw,cw=self.armed(); p.send_signal(signal.SIGSTOP)
        restore=subprocess.Popen([str(self.binary),'--restore'],stdout=subprocess.PIPE,text=True)
        try:
            deadline=time.monotonic()+1.5
            while not (self.root/'state/stopped').exists() and time.monotonic()<deadline: time.sleep(.01)
            self.assertTrue((self.root/'state/stopped').exists())
            # Give restore time to enter retirement waiting. A SIGTERM sent to
            # the saved PID would be queued while stopped and delivered here.
            time.sleep(.15); p.send_signal(signal.SIGCONT)
            s=self.finish(p); self.assertEqual(s['reason'],'external_stop')
            out,_=restore.communicate(timeout=5); result=json.loads(out)
            self.assertEqual(restore.returncode,0); self.assertTrue(result['stock_verified'])
        finally:
            if p.poll() is None: p.send_signal(signal.SIGCONT)
            if restore.poll() is None: restore.terminate(); restore.communicate(timeout=5)
    def test_frozen_guard_retirement_timeout_preserves_evidence(self):
        p,iw,cw=self.armed(); p.send_signal(signal.SIGSTOP)
        try:
            s,rc=self.run_guard('--restore'); self.assertNotEqual(rc,0)
            self.assertEqual(s['reason'],'retirement_failed'); self.assertTrue(s['stopped'])
            self.assertTrue((self.root/'state/active').is_file())
            self.assertFalse((self.root/'luna-calls').exists())
        finally: p.send_signal(signal.SIGCONT)
        self.finish(p)
    def test_new_attempt_discards_old_broker_but_requires_real_fresh_pulse(self):
        # A prior Off leaves volatile records; Enable writes a new config token.
        old='b'*32; stamp=int(time.monotonic()*1000)
        broker=self.root/'volatile/broker'
        broker.write_text(f'{old} 0 0 {stamp} 0 0\n'); broker.chmod(0o600)
        p,iw,cw,rr=self.spawn(broker=False)
        try:
            self.assertFalse(select.select([rr],[],[],.6)[0], 'old-token broker must neither arm nor stop new attempt')
            s,rc=self.run_guard('--status'); self.assertEqual(rc,0); self.assertFalse(s['healthy'])
            self.run_guard('--lease')
            self.assertTrue(select.select([rr],[],[],1)[0])
            self.assertEqual(os.read(rr,128),f'ARMED {TOKEN}\n'.encode())
            os.write(iw,b'ESCAPE\n'); self.finish(p)
        finally: os.close(rr)
    def test_restore_succeeds_when_exact_owned_root_is_already_absent(self):
        (self.root/'luna-close-reply').write_text(json.dumps(dict(
            returnValue=False,errorCode=40,errorText='com.cleanyourtv.root.preview is not running')))
        s,rc=self.run_guard('--restore'); self.assertEqual(rc,0)
        self.assertTrue(s['stopped']); self.assertTrue(s['stock_verified'])
        self.assertEqual((self.root/'luna-calls').read_text().splitlines()[-1],
            '-n 1 luna://com.webos.applicationManager/launch {"id":"com.webos.app.home"}')
    def test_absent_root_exception_does_not_accept_other_errors(self):
        valid=dict(returnValue=False,errorCode=40,errorText='com.cleanyourtv.root.preview is not running')
        invalid=[dict(valid,errorText='com.webos.app.home is not running'),
                 dict(valid,errorText='Permission denied'),dict(valid,errorCode='40'),
                 dict(valid,errorCode=41),dict(valid,errorText=None),dict(valid,returnValue='false')]
        for value in invalid:
            with self.subTest(value=value):
                (self.root/'luna-close-reply').write_text(json.dumps(value))
                s,rc=self.run_guard('--restore'); self.assertNotEqual(rc,0)
                self.assertEqual(s['reason'],'ui_release_failed'); self.assertTrue(s['stopped'])
        # The exact absent-Root error never makes LG Home launch idempotent.
        (self.root/'luna-close-reply').write_text(json.dumps(valid))
        (self.root/'luna-reply').write_text(json.dumps(valid))
        s,rc=self.run_guard('--restore'); self.assertNotEqual(rc,0)
        self.assertEqual(s['reason'],'ui_release_failed')
    def test_exact_config_mode(self):
        (self.root/'state/config').chmod(0o700)
        self.assertNotEqual(self.run_guard('--status')[1],0)

if __name__ == '__main__': unittest.main()
