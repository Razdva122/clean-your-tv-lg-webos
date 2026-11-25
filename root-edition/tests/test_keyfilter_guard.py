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
        (self.root / 'home').write_bytes(b'LG Home executable'.ljust(52,b'\0'))
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
    def spawn(self, seconds=0, ready=(True, True), broker=True, *, resumable=False, reconnect=False, wait_input=False, boot_wait=False):
        ir, iw = os.pipe(); cr, cw = os.pipe(); rr, rw = os.pipe()
        # Queue the tiny fixture records while our read ends are still open;
        # a stopped guardian may refuse and close its inherited ends at once.
        for flag, fd in zip(ready, (iw, cw)):
            if flag: os.write(fd, b'READY\n')
        mode = '--guard-resumable' if resumable else '--guard'
        if boot_wait: mode = '--guard-boot-wait-input'
        elif wait_input: mode += '-wait-input'
        elif reconnect: mode += '-reconnect'
        p = subprocess.Popen([str(self.binary), mode, TOKEN, str(ir), str(cr), str(rw), str(seconds)],
                             pass_fds=(ir, cr, rw), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for fd in (ir, cr, rw): os.close(fd)
        self.guards.append((p, (iw, cw)))
        if broker:
            deadline = time.monotonic() + 1
            while time.monotonic() < deadline:
                self.run_guard('--lease')
                if select.select([rr], [], [], .03)[0]: break
        return p, iw, cw, rr
    def armed(self, seconds=0, *, resumable=False, reconnect=False, wait_input=False):
        p, iw, cw, rr = self.spawn(seconds, resumable=resumable, reconnect=reconnect, wait_input=wait_input)
        self.assertTrue(select.select([rr], [], [], 3)[0])
        ack = os.read(rr, 128); os.close(rr)
        self.assertEqual(ack, f'ARMED {TOKEN}\n'.encode())
        return p, iw, cw
    def freeze(self, p):
        # ARMED is written inside the state critical section. Stop only after
        # acquiring that lock ourselves; otherwise Restore cannot latch stop.
        import fcntl
        deadline=time.monotonic()+3
        with (self.root/'state/lock').open('rb') as lock:
            while True:
                try:
                    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    self.assertIsNone(p.poll(),'guardian exited before freeze')
                    self.assertLess(time.monotonic(),deadline,'guardian did not release state lock')
                    time.sleep(.01)
            stopped=False
            try:
                p.send_signal(signal.SIGSTOP)
                while True:
                    pid,status=os.waitpid(p.pid,os.WUNTRACED|os.WNOHANG)
                    if pid:
                        self.assertEqual(pid,p.pid)
                        self.assertTrue(os.WIFSTOPPED(status))
                        self.assertEqual(os.WSTOPSIG(status),signal.SIGSTOP)
                        stopped=True
                        break
                    self.assertLess(time.monotonic(),deadline,'guardian did not stop')
                    time.sleep(.01)
            finally:
                if not stopped and p.poll() is None:p.send_signal(signal.SIGCONT)

    def finish(self, p):
        out, err = p.communicate(timeout=7)
        self.assertEqual(err, '')
        return json.loads(out)
    def test_stock_identity_requires_immutable_home_for_nonroot_owners(self):
        # Interpose only kernel observations; execute the guardian's actual
        # identity check against the real configured file, including its inode.
        with (self.root/'home').open('wb') as stream: stream.truncate(4530960)
        harness=self.root/'stock-test.c'
        harness.write_text(r'''#define _GNU_SOURCE
#include <sys/stat.h>
#include <sys/statvfs.h>
#ifdef __linux__
#include <sys/vfs.h>
#else
#include <sys/mount.h>
#endif
#include <string.h>
#include <stdio.h>
#include <unistd.h>
static unsigned owner=1001;
static int immutable=1, readonly_fs=1;
static int attr(int fd, struct stat *s) {
  int r=fstat(fd,s); if(!r) s->st_uid=owner; return r;
}
static int lattr(const char *p, struct stat *s) {
  int r=lstat(p,s); if(!r) s->st_uid=!strcmp(p,FIXTURE_ROOT "/home") ? owner:0; return r;
}
static int fixture_vfs(int fd, struct statvfs *s) {
  int r=fstatvfs(fd,s); if(!r) s->f_flag=readonly_fs ? ST_RDONLY:0; return r;
}
static int fixture_fs(int fd, struct statfs *s) {
  (void)fd; memset(s,0,sizeof(*s));
#ifdef __linux__
  s->f_type=immutable ? 0x73717368:0xef53;
#else
  strcpy(s->f_fstypename,immutable ? "squashfs":"apfs");
#endif
  return 0;
}
// Model production root even when the CI runner itself has UID 1001.
#define getuid() ((uid_t)0)
#define fstat(fd,s) attr(fd,s)
#define lstat(p,s) lattr(p,s)
#define fstatfs(fd,s) fixture_fs(fd,s)
#define fstatvfs(fd,s) fixture_vfs(fd,s)
#define main guardian_main
#include "SOURCE"
#undef main
int main(void) {
  (void)attr; (void)fixture_vfs; (void)fixture_fs;
  struct stat s; if(stat(HOME,&s)) return 2;
  cfg.dev=s.st_dev; cfg.ino=s.st_ino; cfg.size=s.st_size; cfg.mtime=mtime_ns(&s);
  printf("%d ",stock_identity());
  immutable=0; printf("%d ",stock_identity());
  immutable=1; readonly_fs=0; printf("%d ",stock_identity());
  readonly_fs=1; owner=1002; printf("%d ",stock_identity());
  owner=1001; cfg.ino++; printf("%d\n",stock_identity());
  return 0;
}
'''.replace('\"SOURCE\"','\"'+str(SOURCE)+'\"'))
        binary=self.root/'stock-test'
        subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',
            '-DCYTV_KEYFILTER_FIXTURE',f'-DFIXTURE_ROOT="{self.root}"',
            str(harness),'-o',str(binary)],check=True,capture_output=True)
        result=subprocess.run([str(binary)],check=True,capture_output=True,text=True)
        self.assertEqual(result.stdout.strip(),'1 0 0 1 0')

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
    def await_broker_reconnect(self):
        proc, iw, cw = self.armed(reconnect=True)
        end = time.monotonic() + 4
        while time.monotonic() < end:
            os.write(iw, b'PING\n')
            os.write(cw, b'PING\n')
            if self.run_guard('--status')[0]['state'] == 'reconnecting':
                break
            time.sleep(.12)
        else:
            self.fail('Broker gap did not enter recovery')
        return proc, iw, cw

    def test_persistent_broker_recovery_stays_off_until_fresh_lease_and_can_escape(self):
        proc, iw, _ = self.await_broker_reconnect()
        self.assertNotEqual(self.run_guard('--home', TOKEN)[1], 0)
        self.assertEqual(self.run_guard('--lease-reconnect', TOKEN)[0]['state'], 'reconnecting')
        os.write(iw, b'ESCAPE\n')
        self.assertEqual(self.finish(proc)['reason'], 'escape')
        self.assertFalse(self.run_guard('--lease')[0]['healthy'])

    def test_persistent_broker_recovery_requires_matching_token_and_recovers(self):
        proc, iw, cw = self.await_broker_reconnect()
        self.assertNotEqual(self.run_guard('--lease-reconnect', 'b' * 32)[1], 0)
        self.assertEqual(self.run_guard('--lease-reconnect', TOKEN)[0]['state'], 'reconnecting')
        self.assertNotEqual(self.run_guard('--home', TOKEN)[1], 0)
        end = time.monotonic() + 4
        while time.monotonic() < end:
            os.write(iw, b'PING\n')
            os.write(cw, b'PING\n')
            status, rc = self.run_guard('--lease')
            self.assertEqual(rc, 0, status)
            if status['healthy']:
                break
            time.sleep(.12)
        else:
            self.fail('Fresh broker did not restore routing')
        os.write(iw, b'ESCAPE\n')
        self.assertEqual(self.finish(proc)['reason'], 'escape')

    def test_broker_barrier_waits_for_guardian_to_drain_queued_escape(self):
        proc, iw, _ = self.await_broker_reconnect()
        self.assertEqual(self.run_guard('--lease-reconnect', TOKEN)[0]['state'], 'reconnecting')
        self.freeze(proc)
        try:
            os.write(iw, b'ESCAPE\n')
            # Simulate the deadline elapsing while the guardian is not scheduled.
            broker = self.root / 'volatile/broker'
            fields = broker.read_text().split()
            fields[4] = fields[3]
            broker.write_text(' '.join(fields) + '\n')
            self.assertEqual(self.run_guard('--lease')[0]['state'], 'reconnecting')
            self.assertNotEqual(self.run_guard('--home', TOKEN)[1], 0)
        finally:
            proc.send_signal(signal.SIGCONT)
        self.assertEqual(self.finish(proc)['reason'], 'escape')
        self.assertFalse(self.run_guard('--lease-reconnect', TOKEN)[0]['healthy'])

    def test_manual_off_during_broker_recovery_is_terminal(self):
        proc, _, _ = self.await_broker_reconnect()
        self.assertEqual(self.run_guard('--lease-reconnect', TOKEN)[0]['state'], 'reconnecting')
        self.assertEqual(self.run_guard('--restore')[1], 0)
        self.finish(proc)
        self.assertFalse(self.run_guard('--lease-reconnect', TOKEN)[0]['healthy'])
        self.assertNotEqual(self.run_guard('--home', TOKEN)[1], 0)
        self.assertIn('explicit_off', (self.root / 'state/stopped').read_text())

    def test_broker_cannot_revive_expired_health(self):
        p, iw, cw = self.armed()
        deadline = time.monotonic() + 2.3
        while p.poll() is None and time.monotonic() < deadline:
            time.sleep(.3)
            try: os.write(iw,b'PING\n'); os.write(cw,b'PING\n')
            except BrokenPipeError: break
        s = self.finish(p); self.assertEqual(s['reason'], 'broker_expired')
        self.assertFalse(self.run_guard('--lease')[0]['healthy'])
    def await_input_reconnect(self):
        proc, iw, cw = self.armed(reconnect=True)
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            os.write(cw, b'PING\n')
            status, rc = self.run_guard('--lease')
            self.assertEqual(rc, 0, status)
            if status['state'] == 'reconnecting':
                self.assertFalse(status['healthy'])
                self.assertFalse(status['stopped'])
                return proc, iw, cw
            time.sleep(.15)
        self.fail('Guardian never suspended routing for input expiry')

    def test_input_expiry_resumes_only_with_fresh_revalidation(self):
        proc, iw, _ = self.await_input_reconnect()
        self.assertNotEqual(self.run_guard('--home', TOKEN)[1], 0)
        os.write(iw, b'PING\nCHECK 1\n')
        self.assertFalse(self.run_guard('--lease')[0]['healthy'])
        os.write(iw, ('CHECK %d\n' % (time.clock_gettime_ns(time.CLOCK_MONOTONIC) // 1_000_000)).encode())
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline:
            if self.run_guard('--lease')[0]['healthy']: break
            time.sleep(.02)
        else: self.fail('Fresh input validation never restored the route')
        os.write(iw, b'ESCAPE\n')
        self.assertEqual(self.finish(proc)['reason'], 'escape')

    def report_missing_input(self, fd):
        stamp = time.clock_gettime_ns(time.CLOCK_MONOTONIC) // 1_000_000
        os.write(fd, f'WAIT {stamp}\n'.encode())

    def test_missing_input_keeps_guardian_without_authorizing_home(self):
        proc, iw, cw = self.armed(wait_input=True)
        deadline = time.monotonic() + 2.5
        while time.monotonic() < deadline:
            self.report_missing_input(iw)
            os.write(cw, b'PING\n')
            status, rc = self.run_guard('--lease')
            self.assertEqual(rc, 0, status)
            self.assertEqual(status['guardian_pid'], proc.pid)
            time.sleep(.15)
        status, rc = self.run_guard('--home', TOKEN)
        self.assertNotEqual(rc, 0)
        self.assertEqual(status['state'], 'reconnecting')
        self.assertFalse(status['healthy'])
        self.assertFalse((self.root/'luna-calls').exists())
        # A queued ordinary heartbeat cannot re-arm a removed device.
        os.write(iw, b'PING\n')
        self.assertFalse(self.run_guard('--lease')[0]['healthy'])
        stamp = time.clock_gettime_ns(time.CLOCK_MONOTONIC) // 1_000_000
        os.write(iw, f'CHECK {stamp}\n'.encode())
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline:
            if self.run_guard('--lease')[0]['healthy']:
                break
            time.sleep(.02)
        else:
            self.fail('Validated replacement did not resume the original guardian')
        os.write(iw, b'ESCAPE\n')
        self.assertEqual(self.finish(proc)['reason'], 'escape')

    def test_confirmed_boot_can_wait_before_first_remote(self):
        proc, iw, cw, rr = self.spawn(ready=(False, True), broker=False, boot_wait=True)
        try:
            self.report_missing_input(iw)
            deadline = time.monotonic() + 1
            while not select.select([rr], [], [], .02)[0]:
                self.assertLess(time.monotonic(), deadline)
                self.run_guard('--lease')
            self.assertEqual(os.read(rr, 128), f'SUPERVISED {TOKEN}\n'.encode())
        finally:
            os.close(rr)
        status, rc = self.run_guard('--home', TOKEN)
        self.assertNotEqual(rc, 0)
        self.assertEqual(status['state'], 'reconnecting')
        self.assertFalse(status['healthy'])
        self.assertEqual(status['guardian_pid'], proc.pid)
        self.assertFalse((self.root/'luna-calls').exists())
        stamp = time.clock_gettime_ns(time.CLOCK_MONOTONIC) // 1_000_000
        os.write(iw, f'CHECK {stamp}\n'.encode())
        deadline = time.monotonic() + 1
        while not self.run_guard('--lease')[0]['healthy']:
            self.assertLess(time.monotonic(), deadline)
        os.write(iw, b'ESCAPE\n')
        self.assertEqual(self.finish(proc)['reason'], 'escape')

    def test_queued_escape_prevents_first_activation(self):
        proc, iw, cw, rr = self.spawn(ready=(False, True), broker=False, wait_input=True)
        try:
            deadline = time.monotonic() + 1
            while self.run_guard('--lease')[0]['guardian_pid'] != proc.pid:
                self.assertLess(time.monotonic(), deadline)
            time.sleep(.05)
            os.write(iw, b'READY\nESCAPE\n')
            self.assertEqual(self.finish(proc)['reason'], 'escape')
            self.assertEqual(os.read(rr, 128), b'')
        finally:
            os.close(rr)

    def test_first_enable_refuses_wait_before_remote_validation(self):
        proc, iw, cw, rr = self.spawn(ready=(False, True), broker=False, wait_input=True)
        try:
            self.report_missing_input(iw)
            self.assertEqual(self.finish(proc)['reason'], 'malformed_input')
            self.assertEqual(os.read(rr, 128), b'')
        finally:
            os.close(rr)

    def test_queued_ping_cannot_hide_fresh_device_removal(self):
        proc, iw, _ = self.armed(wait_input=True)
        # The reader observed removal while the preceding PING was still queued.
        stamp = time.clock_gettime_ns(time.CLOCK_MONOTONIC) // 1_000_000 - 100
        os.write(iw, f'PING\nWAIT {stamp}\n'.encode())
        deadline = time.monotonic() + .8
        while self.run_guard('--lease')[0]['healthy']:
            self.assertLess(time.monotonic(), deadline)
            time.sleep(.02)
        os.write(iw, b'ESCAPE\n')
        self.assertEqual(self.finish(proc)['reason'], 'escape')

    def test_loss_in_same_millisecond_as_check_revokes_pending_grant(self):
        proc, iw, _ = self.armed(wait_input=True)
        time.sleep(.03)
        stamp = time.clock_gettime_ns(time.CLOCK_MONOTONIC) // 1_000_000
        os.write(iw, f'WAIT {stamp}\nCHECK {stamp}\nWAIT {stamp}\n'.encode())
        time.sleep(.15)
        status, _ = self.run_guard('--lease')
        self.assertEqual(status['state'], 'reconnecting')
        self.assertFalse(status['healthy'])
        os.write(iw, b'ESCAPE\n')
        self.assertEqual(self.finish(proc)['reason'], 'escape')

    def test_input_removed_during_home_request_keeps_guardian(self):
        proc, iw, cw = self.armed(wait_input=True)
        (self.root/'root-delay').touch()
        with subprocess.Popen([str(self.binary), '--home', TOKEN],
                              stdout=subprocess.PIPE, text=True) as home:
            deadline = time.monotonic() + 2
            while not (self.root/'root-entered').exists():
                self.assertLess(time.monotonic(), deadline)
                time.sleep(.01)
            self.report_missing_input(iw)
            reply = json.loads(home.communicate(timeout=3)[0])
        self.assertEqual(reply['reason'], 'home_refused')
        self.assertEqual(reply['state'], 'reconnecting')
        self.assertFalse(reply['stopped'])
        self.assertEqual(reply['guardian_pid'], proc.pid)
        os.write(cw, b'LGHOME\n')
        self.assertEqual(self.finish(proc)['reason'], 'lg_home')

    def test_hung_reader_still_expires_while_waiting_for_input(self):
        proc, iw, cw = self.armed(wait_input=True)
        self.report_missing_input(iw)
        deadline = time.monotonic() + 4
        while proc.poll() is None and time.monotonic() < deadline:
            try:
                os.write(cw, b'PING\n')
            except BrokenPipeError:
                break
            self.run_guard('--lease')
            time.sleep(.12)
        result = self.finish(proc)
        self.assertEqual(result['reason'], 'input_expired')
        self.assertTrue(result['stopped'])

    def test_manual_off_while_input_reconnect_is_pending(self):
        proc, iw, _ = self.await_input_reconnect()
        self.freeze(proc)
        restore = subprocess.Popen([str(self.binary), '--restore'], stdout=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 1
            while not (self.root/'state/stopped').exists() and time.monotonic() < deadline:
                time.sleep(.01)
            self.assertTrue((self.root/'state/stopped').exists())
            os.write(iw, ('CHECK %d\n' % (time.clock_gettime_ns(time.CLOCK_MONOTONIC) // 1_000_000)).encode())
            self.assertFalse(self.run_guard('--lease')[0]['healthy'])
        finally:
            proc.send_signal(signal.SIGCONT)
            restore.communicate(timeout=5)
        self.assertEqual(restore.returncode, 0)
        self.assertEqual(self.finish(proc)['reason'], 'external_stop')

    def test_escape_while_input_reconnect_is_pending(self):
        proc, iw, _ = self.await_input_reconnect()
        os.write(iw, b'ESCAPE\n')
        self.assertEqual(self.finish(proc)['reason'], 'escape')
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
        self.assertNotIn('input_timeout_phase', s)
    def test_input_timeout_before_first_ready(self):
        (self.root/'luna-reply').write_text('{"returnValue":false}')
        p, iw, cw, rr = self.spawn(ready=(False, True), broker=False)
        self.addCleanup(os.close, rr)
        result = self.finish(p)
        self.assertEqual(os.read(rr, 128), b'')
        self.assertEqual(result['reason'], 'ui_release_failed')
        self.assertEqual(result['input_timeout_phase'], 'waiting-for-ready')
        self.assertEqual((self.root/'state/outcome').read_text(), f'{TOKEN} input_expired\n')
    def test_stale_input_does_not_get_controller_lease(self):
        p, iw, cw = self.armed()
        # Extend the other channels once. A lease request at the input deadline
        # can publish its own stop before the guardian records input_expired.
        time.sleep(.5)
        os.write(cw, b'PING\n')
        lease, _ = self.run_guard('--lease')
        self.assertTrue(lease['healthy'])
        s = self.finish(p); self.assertFalse(s['healthy']); self.assertTrue(s['stopped'])
        expired, _ = self.run_guard('--lease')
        self.assertFalse(expired['healthy'])
        self.assertEqual(s['reason'], 'input_expired')
        self.assertEqual(s['input_timeout_phase'], 'waiting-for-ping')
        self.assertEqual((self.root/'state/outcome').read_text(), f'{TOKEN} input_expired\n')
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
    def test_boot_retirement_refuses_live_guard_and_preserves_emergency_stop(self):
        p, iw, _ = self.armed()
        self.assertNotEqual(self.run_guard('--retire-boot', TOKEN)[1], 0)
        self.assertTrue(self.run_guard('--status')[0]['healthy'])
        os.write(iw, b'ESCAPE\n')
        self.finish(p)
        latch = self.root/'state/stopped'
        saved = latch.read_bytes()
        self.assertNotEqual(self.run_guard('--retire-boot', TOKEN)[1], 0)
        self.assertEqual(self.run_guard('--restore-routing')[1], 0)
        self.assertEqual(latch.read_bytes(), saved)

    def test_verified_system_shutdown_allows_retirement_but_explicit_off_revokes_it(self):
        systemctl = self.root/'systemctl'
        systemctl.write_text('#!/bin/sh\n[ "$*" = is-system-running ] || exit 4\nprintf "stopping\\n"\nexit 1\n')
        systemctl.chmod(0o700)
        p, _, _ = self.armed(resumable=True)
        p.terminate()
        self.finish(p)
        latch = self.root/'state/stopped'
        self.assertEqual(latch.read_text(), f'{TOKEN} normal_shutdown\n')
        self.assertFalse((self.root/'luna-calls').exists())
        result, rc = self.run_guard('--retire-boot', TOKEN)
        self.assertEqual(rc, 0)
        self.assertTrue(result['stopped'])
        self.assertEqual(result['reason'], 'normal_shutdown')
        self.assertEqual(latch.read_text(), f'{TOKEN} normal_shutdown\n')
        self.assertEqual(self.run_guard('--restore-routing')[1], 0)
        self.assertEqual(latch.read_text(), f'{TOKEN} explicit_off\n')
        self.assertNotEqual(self.run_guard('--retire-boot', TOKEN)[1], 0)

    def test_remote_disappears_before_broker_during_verified_shutdown(self):
        self.check_remote_disappears_before_broker('stopping', 1, 'normal_shutdown')

    def test_remote_disappears_before_broker_without_verified_shutdown(self):
        self.check_remote_disappears_before_broker('running', 0, 'broker_expired')

    def check_remote_disappears_before_broker(self, system_state, status, reason):
        systemctl = self.root/'systemctl'
        systemctl.write_text(f'#!/bin/sh\nprintf "{system_state}\\n"\nexit {status}\n')
        systemctl.chmod(0o700)
        proc, iw, cw = self.armed(resumable=True, wait_input=True)
        # Replay ENODEV as WAIT, then stop renewing the broker lease while
        # the observer and controller are still alive.
        deadline = time.monotonic() + 4
        while proc.poll() is None and time.monotonic() < deadline:
            try:
                self.report_missing_input(iw)
                os.write(cw, b'PING\n')
            except BrokenPipeError:
                break
            time.sleep(.12)
        self.assertEqual(self.finish(proc)['reason'], reason)
        result, rc = self.run_guard('--retire-boot', TOKEN)
        if reason == 'normal_shutdown':
            self.assertEqual(rc, 0)
            self.assertEqual(result['reason'], reason)
            self.assertFalse((self.root/'luna-calls').exists())
        else:
            self.assertNotEqual(rc, 0)
            self.assertTrue((self.root/'luna-calls').exists())

    def test_capabilities_are_static_and_do_not_require_or_change_state(self):
        before = {p.relative_to(self.root): p.read_bytes()
                  for p in self.root.rglob('*') if p.is_file()}
        (self.root/'state/config').unlink()
        before.pop(Path('state/config'))
        result, rc = self.run_guard('--capabilities')
        self.assertEqual(rc, 0)
        self.assertEqual(result, {'returnValue': True, 'backend': 'c1-native-gate',
            'routing': 'compositor-keyfilter-v1', 'protocol': 1,
            'resumable_guard': True, 'boot_retirement': True,
            'shutdown_probes': ['systemd-is-system-running-v1', 'upstart-shutdown-jobs-v1']})
        after = {p.relative_to(self.root): p.read_bytes()
                 for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(after, before)

    def test_upstart_shutdown_probe_requires_known_running_jobs_and_is_bounded(self):
        # Exercise the real bounded subprocess/parser directly without needing
        # a simulated TV session for every invalid daemon response.
        source = self.root/'shutdown-probe.c'
        source.write_text('#define main guardian_main\n#include "'+str(SOURCE)+
                          '"\n#undef main\nint main(void) { return !normal_shutdown(); }\n')
        binary = self.root/'shutdown-probe'
        subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
            '-DCYTV_KEYFILTER_FIXTURE', f'-DFIXTURE_ROOT="{self.root}"',
            str(source), '-o', str(binary)], check=True, capture_output=True)
        initctl = self.root/'initctl'
        def script(body):
            initctl.write_text('#!/bin/sh\n'+body+'\n')
            initctl.chmod(0o700)
        def check(expected):
            started = time.monotonic()
            p = subprocess.run([str(binary)], capture_output=True, timeout=2)
            self.assertEqual(p.returncode, 0 if expected else 1, p.stderr)
            self.assertLess(time.monotonic()-started, 1.5)
        check(False)  # Unsupported init system.
        for job in ('shutdown', 'reboot'):
            with self.subTest(running_job=job):
                script('case "$*" in "status '+job+'") echo "'+job+' start/running, process 42" ;; '
                       '"status shutdown"|"status reboot") echo "${2} stop/waiting" ;; *) exit 4 ;; esac')
                check(True)
        script('case "$*" in "status shutdown"|"status reboot") echo "${2} stop/waiting" ;; *) exit 4 ;; esac')
        check(False)  # Both factory jobs are inactive during normal operation.
        for reply in ('shutdown stop/waiting', 'shutdown start/starting',
                      'shutdown start/running', 'shutdown start/running, process 0',
                      'shutdown start/running, process -1', 'shutdown start/running, process 42 extra',
                      'shutdown start/running, process 999999999999999999999999999999',
                      'reboot start/running, process 42', 'shutdown stop/running'):
            with self.subTest(reply=reply):
                script('printf "%s\\n" "'+reply+'"')
                check(False)
        for body in ('echo "shutdown start/running, process 42"; exit 1',
                     'printf "shutdown start/running, process 42\\nextra\\n"',
                     'printf "shutdown start/running, process 42\\000\\n"',
                     'sleep 5', 'printf "%01000d" 0', 'exit 1'):
            with self.subTest(body=body):
                script(body)
                check(False)
        script('echo "shutdown start/running, process 42"')
        initctl.chmod(0o722)
        check(False)
        initctl.chmod(0o700)
        systemctl = self.root/'systemctl'
        for body in ('echo running; exit 0', 'sleep 5', 'exit 1'):
            systemctl.write_text('#!/bin/sh\n'+body+'\n')
            systemctl.chmod(0o700)
            check(False)  # A systemd probe failure must not fall through.

    def test_verified_upstart_shutdown_allows_retirement(self):
        initctl = self.root/'initctl'
        initctl.write_text('#!/bin/sh\n[ "$*" = "status shutdown" ] || exit 4\n'
                           'echo "shutdown start/running, process 42"\n')
        initctl.chmod(0o700)
        p, _, _ = self.armed(resumable=True)
        p.terminate()
        self.finish(p)
        self.assertEqual((self.root/'state/stopped').read_text(), f'{TOKEN} normal_shutdown\n')
        self.assertFalse((self.root/'luna-calls').exists())
        result, rc = self.run_guard('--retire-boot', TOKEN)
        self.assertEqual(rc, 0)
        self.assertEqual(result['reason'], 'normal_shutdown')
        self.assertEqual(self.run_guard('--restore-routing')[1], 0)
        self.assertNotEqual(self.run_guard('--retire-boot', TOKEN)[1], 0)

    def test_emergency_escape_during_system_shutdown_still_vetoes_rearm(self):
        self.shutdown_escape('systemctl', 'stopping', 1)

    def test_emergency_escape_during_upstart_shutdown_still_vetoes_rearm(self):
        self.shutdown_escape('initctl', 'shutdown start/running, process 42', 0)

    def shutdown_escape(self, command, response, status):
        systemctl = self.root/command
        probing = self.root/'shutdown-probing'
        released = self.root/'shutdown-probe-release'
        systemctl.write_text('#!/bin/sh\ntouch "'+str(probing)+'"\nwhile test ! -f "'+
                             str(released)+'"; do sleep .01; done\nprintf "'+response+'\\n"\nexit '+str(status)+'\n')
        systemctl.chmod(0o700)
        p, iw, _ = self.armed(resumable=True)
        p.terminate()
        deadline = time.monotonic() + 1
        while not probing.exists():
            self.assertLess(time.monotonic(), deadline)
            time.sleep(.005)
        self.assertFalse(self.run_guard('--status')[0]['healthy'])
        self.assertNotEqual(self.run_guard('--home', TOKEN)[1], 0)
        os.write(iw, b'ESCAPE\n')
        released.touch()
        self.finish(p)
        self.assertEqual((self.root/'state/stopped').read_text(), f'{TOKEN} escape\n')
        self.assertNotEqual(self.run_guard('--retire-boot', TOKEN)[1], 0)
        self.assertNotIn('launch {"id":"com.cleanyourtv.root.preview"}',
                         (self.root/'luna-calls').read_text())

    def test_boot_retires_dead_guard_without_changing_the_stop_latch_or_ui(self):
        p, _, _ = self.armed()
        p.kill()
        p.communicate(timeout=2)
        self.assertTrue((self.root/'state/active').is_file())
        self.assertNotEqual(self.run_guard('--retire-boot', 'b'*32)[1], 0)
        result, rc = self.run_guard('--retire-boot', TOKEN)
        self.assertEqual(rc, 0)
        self.assertEqual(result['guardian_pid'], 0)
        self.assertTrue(result['stock_verified'])
        self.assertFalse(result['stopped'])
        self.assertFalse((self.root/'luna-calls').exists())
        self.assertEqual(self.run_guard('--restore-routing')[1], 0)
        self.assertFalse((self.root/'luna-calls').exists())

    def test_standalone_restore_releases_ui(self):
        s,rc=self.run_guard('--restore'); self.assertEqual(rc,0)
        self.assertTrue(s['stopped']); self.assertTrue((self.root/'luna-calls').is_file(),'standalone native restore must release UI')
        self.assertEqual(len((self.root/'luna-calls').read_text().splitlines()),2)
    def test_restore_separates_ls2_failure_from_an_unverified_effect_lock(self):
        rejection = '{"returnValue":false,"errorCode":41}'
        for name in ('luna-close-reply', 'luna-reply'):
            with self.subTest(failed_reply=name):
                reply = self.root / name
                if name == 'luna-reply':
                    (self.root / 'luna-close-reply').write_text('{"returnValue":true}')
                reply.write_text(rejection)
                result, rc = self.run_guard('--restore')
                self.assertEqual(rc, 1)
                self.assertEqual(result['reason'], 'ui_release_failed')
                self.assertTrue(result['stopped'])
                self.assertTrue(result['stock_verified'])
                self.assertEqual(result['guardian_pid'], 0)
                reply.unlink()
        calls = (self.root / 'luna-calls').read_text()
        lock = self.root / 'state/effect.lock'
        lock.unlink()
        lock.symlink_to(self.root / 'state/config')
        result, rc = self.run_guard('--restore')
        self.assertEqual(rc, 1)
        self.assertEqual(result['reason'], 'effect_busy')
        self.assertEqual((self.root / 'luna-calls').read_text(), calls)

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
    def test_restore_retirement_waits_for_ready_state_lock_release(self):
        # Hold the real ARMED critical section until the parent observes lock
        # contention. A handshake avoids consuming the guardian health budget.
        import fcntl
        source=SOURCE.read_text()
        anchor='else { armed=1; close(ready); ready=-1; }'
        self.assertEqual(source.count(anchor),1)
        source=source.replace(anchor,'else { armed=1; close(ready); ready=-1; while(access(FIXTURE_ROOT "/ready-release",F_OK)<0)poll(NULL,0,1); }',1)
        subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-DCYTV_KEYFILTER_FIXTURE',
                        f'-DFIXTURE_ROOT="{self.root}"','-I',str(SOURCE.parent),
                        '-x','c','-','-o',str(self.binary)],
                       input=source,text=True,check=True,capture_output=True)
        release=self.root/'ready-release';original=fcntl.flock;contended=[]
        def release_on_contention(fd,operation):
            try:return original(fd,operation)
            except BlockingIOError:
                contended.append(True);release.touch();raise
        try:
            with mock.patch.object(fcntl,'flock',side_effect=release_on_contention):
                self.test_restore_retires_via_latch_without_queued_pid_signal()
            self.assertTrue(contended,'fixture must encounter the guardian-held state lock')
        finally:release.touch()

    def test_restore_retires_via_latch_without_queued_pid_signal(self):
        p,iw,cw=self.armed(); self.freeze(p)
        restore=subprocess.Popen([str(self.binary),'--restore'],stdout=subprocess.PIPE,text=True)
        try:
            deadline=time.monotonic()+1.5
            while not (self.root/'state/stopped').exists() and time.monotonic()<deadline: time.sleep(.01)
            self.assertTrue((self.root/'state/stopped').exists())
            # A reconnect that was already in flight can still write to the
            # open pipe. Explicit Off must veto that heartbeat under the latch.
            os.write(iw, b'PING\n')
            self.assertFalse(self.run_guard('--lease')[0]['healthy'])
            self.assertNotEqual(self.run_guard('--home', TOKEN)[1], 0)
            # A SIGTERM sent to the saved PID would be delivered here.
            time.sleep(.15); p.send_signal(signal.SIGCONT)
            s=self.finish(p); self.assertEqual(s['reason'],'external_stop')
            out,_=restore.communicate(timeout=5); result=json.loads(out)
            self.assertEqual(restore.returncode,0); self.assertTrue(result['stock_verified'])
        finally:
            if p.poll() is None: p.send_signal(signal.SIGCONT)
            if restore.poll() is None: restore.terminate(); restore.communicate(timeout=5)
    def test_frozen_guard_retirement_timeout_preserves_evidence(self):
        p,iw,cw=self.armed(); self.freeze(p)
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
    def test_restore_succeeds_with_webos6_absent_root_reply(self):
        # Stock SAM on OLED55C14LB 03.53.45 (webOS 6.5.3), captured byte-for-byte
        # from closeByAppId for an installed app with no running instance.
        (self.root/'luna-close-reply').write_text(
            '{"errorCode":1,"returnValue":false,"errorText":"app is not running"}\n')
        s,rc=self.run_guard('--restore'); self.assertEqual(rc,0)
        self.assertEqual(s['reason'],'explicit_off')
        self.assertTrue(s['stopped']); self.assertTrue(s['stock_verified'])
        self.assertEqual((self.root/'luna-calls').read_text().splitlines()[-2:],
            ['-n 1 luna://com.webos.applicationManager/closeByAppId {"id":"com.cleanyourtv.root.preview"}',
             '-n 1 luna://com.webos.applicationManager/launch {"id":"com.webos.app.home"}'])
    def test_webos6_absent_root_exception_does_not_accept_other_errors(self):
        valid=dict(errorCode=1,returnValue=False,errorText='app is not running')
        # The same firmware answers errorCode 1 for an unknown or empty id and
        # errorCode 2 for a missing id; only the exact absent text is idempotent.
        invalid=[dict(valid,errorText='no valid life handler'),
                 dict(valid,errorCode=2,errorText='invalid parameters'),
                 dict(valid,errorText='Permission denied'),dict(valid,errorText='app is not running '),
                 dict(valid,errorText='com.cleanyourtv.root.preview is not running'),
                 dict(valid,errorCode=40),dict(valid,errorCode='1'),dict(valid,errorCode=True),
                 dict(valid,errorCode=-1),dict(valid,errorText=None),dict(valid,returnValue='false')]
        for value in invalid:
            with self.subTest(value=value):
                (self.root/'luna-close-reply').write_text(json.dumps(value))
                s,rc=self.run_guard('--restore'); self.assertNotEqual(rc,0)
                self.assertEqual(s['reason'],'ui_release_failed'); self.assertTrue(s['stopped'])
        # The absent-Root reply never makes LG Home launch idempotent.
        (self.root/'luna-close-reply').write_text(json.dumps(valid))
        (self.root/'luna-reply').write_text(json.dumps(valid))
        s,rc=self.run_guard('--restore'); self.assertNotEqual(rc,0)
        self.assertEqual(s['reason'],'ui_release_failed')
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
