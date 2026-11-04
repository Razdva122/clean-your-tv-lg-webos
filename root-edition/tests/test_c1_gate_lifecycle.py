"""Focused host tests for C1 activation/restore failure boundaries."""
from contextlib import ExitStack
import hashlib
import fcntl
import json
import os
from pathlib import Path
import sys
import shutil
import subprocess
import time
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'runtime'))
import c1_gate as gate


class GateLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name).resolve()
        self.uid = os.getuid()
        (self.root/'c1-gate').mkdir(mode=0o700)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.token = 'a'*32
        self.boot = '33333333-2222-4444-8888-000000000001'
        self.mock('boot_identity', return_value=self.boot)
        self.stock = dict(returnValue=True, backend=gate.BACKEND, state='stopped', mounted=False,
                          healthy=False, stock_verified=True, stopped=True, token=self.token,
                          guardian_pid=0, profiles=None, reason='explicit_off')

    def mock(self, name, **kwargs):
        return self.stack.enter_context(patch.object(gate, name, **kwargs))

    def test_orphaned_state_blocks_profile_fallback(self):
        with self.assertRaisesRegex(ValueError, 'selection'):
            gate.selection(self.root, self.uid)

    def test_config_token_publication_excludes_native_mutations(self):
        admission = {'target': dict(dev=1, ino=2, size=52, mtime_ns=3)}
        with (self.root/'c1-gate/lock').open('w') as lock:
            os.fchmod(lock.fileno(), 0o600)
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):
                gate.write_config(self.root, admission, self.token, self.uid)
            self.assertFalse((self.root/'c1-gate/config').exists())
        gate.write_config(self.root, admission, self.token, self.uid)
        self.assertIn('token '+self.token, (self.root/'c1-gate/config').read_text())

    def test_off_uses_native_latch_with_malformed_or_unwritable_intent(self):
        path = self.root/'c1-gate/intent.json'
        path.write_text('{broken')
        call = self.mock('native', return_value=self.stock)
        self.assertEqual(gate.restore(self.root, self.uid), 'restored')
        self.assertFalse(json.loads(path.read_bytes())['enabled'])
        call.reset_mock()
        self.mock('write_intent', side_effect=OSError('full'))
        with self.assertRaises((ValueError, OSError)):
            gate.restore(self.root, self.uid)
        self.assertEqual([c.args[0] for c in call.call_args_list], [['--restore'], ['--status']])

    def test_dead_guardian_restored_by_boot_even_if_status_refuses(self):
        gate.write_intent(self.root, True, self.token, 'active', self.uid)
        self.stack.enter_context(patch('boot_gate.wait', return_value=True))
        native = self.mock('native', side_effect=[ValueError('blocked'), self.stock, self.stock])
        activate = self.mock('enable')
        self.assertEqual(gate.execute('boot', root=self.root, uid=self.uid), 'restored')
        activate.assert_not_called()
        self.assertEqual([c.args[0] for c in native.call_args_list], [['--status'], ['--restore'], ['--status']])

    def test_mismatched_active_mode_refuses_bounded_trial(self):
        gate.write_intent(self.root, True, self.token, 'active', self.uid)
        self.mock('selection', return_value={})
        self.mock('verify_ready', return_value={})
        self.mock('native', return_value=dict(self.stock, state='armed', mounted=True, healthy=True,
                                               stopped=False, stock_verified=False, guardian_pid=123))
        with self.assertRaisesRegex(ValueError, '[Rr]estore'):
            gate.enable(self.root, self.uid, seconds=60)

    def test_volatile_publication_never_overwrites_existing_inode(self):
        data = b'arm fixture'
        source = self.root/'runtime/c1-home-gate'
        source.parent.mkdir()
        source.write_bytes(data)
        source.chmod(0o700)
        dest = self.root/'volatile/gate'
        self.mock('VOLATILE', new=dest)
        digest = hashlib.sha256(data).hexdigest()
        gate.stage_volatile(self.root, self.uid, digest)
        self.assertEqual(dest.parent.stat().st_mode & 0o777, 0o700)
        self.assertEqual(dest.read_bytes(), data)
        inode = dest.stat().st_ino
        gate.stage_volatile(self.root, self.uid, digest)
        self.assertEqual(inode, dest.stat().st_ino)
        dest.write_bytes(b'foreign')
        with self.assertRaises(ValueError):
            gate.stage_volatile(self.root, self.uid, digest)
        self.assertEqual(dest.read_bytes(), b'foreign')

    def test_failed_start_latches_even_when_intent_storage_fails(self):
        self.mock('selection', return_value={'native_sha256':'a'*64, 'admission':{}})
        self.mock('probe', return_value={})
        self.mock('verify_ready', return_value={})
        self.mock('binary', return_value='native')
        self.mock('stage_volatile')
        self.mock('write_config')
        self.stack.enter_context(patch('helper_bridge.require_idle'))
        self.mock('write_intent', side_effect=OSError('full'))
        call = self.mock('native', return_value=self.stock)
        with self.assertRaises(OSError):
            gate.enable(self.root, self.uid, seconds=60)
        self.assertEqual([c.args[0] for c in call.call_args_list], [['--status'], ['--restore'], ['--status']])

    @unittest.skipUnless(shutil.which('cc'), 'POSIX host compiler required')
    def test_adapter_arms_actual_guard_and_escape_restores_without_python_controller(self):
        root = self.root
        source = ROOT/'tests/native_gate_fixture.h'
        (root/source.name).write_text(source.read_text().replace('FIXTURE_ROOT "/state"', 'FIXTURE_ROOT "/c1-gate"'))
        home = root/'home'
        home.write_bytes(b'stock native fixture'*5)
        home.chmod(0o700)
        (root/'mountinfo').write_text('1 0 0:1 / / rw - fixture fixture rw\n')
        (root/'boot').write_text(self.boot+'\n')
        (root/'luna').write_text("#!/bin/sh\necho '{\"returnValue\":true}'\n")
        (root/'luna').chmod(0o700)
        runtime = root/'runtime'
        runtime.mkdir()
        helper = runtime/'c1-home-gate'
        subprocess.run(['cc','-std=c11','-DCYTV_GATE_FIXTURE',f'-DFIXTURE_ROOT="{root}"',
                        '-I',str(root),str(ROOT/'gate/gate.c'),'-o',str(helper)], check=True)
        (runtime/'emergency_reader.py').write_text(
            "import os, sys, time\nfrom pathlib import Path\n"
            "fd = int(sys.argv[1])\nos.write(fd, b'READY\\n')\n"
            "while not Path(__file__).with_name('escape').exists():\n"
            "    os.write(fd, b'PING\\n')\n    time.sleep(.2)\n"
            "os.write(fd, b'ESCAPE\\n')\n")
        self.mock('VOLATILE', new=root/'volatile/gate')
        info = home.stat()
        admission = dict(model='OLED65C14LB', firmware='03.51.15', webos='6.5.0',
                         target_sha256=hashlib.sha256(home.read_bytes()).hexdigest(),
                         target=dict(dev=info.st_dev, ino=info.st_ino, size=info.st_size, mtime_ns=info.st_mtime_ns))
        (root/'c1-gate').rmdir()
        gate.prepare(root, hashlib.sha256(helper.read_bytes()).hexdigest(), admission, self.uid)
        self.mock('verify_ready', return_value={'integrity_verified':True})
        self.mock('probe', return_value=admission)
        self.mock('stock_running', return_value=False)
        self.stack.enter_context(patch('helper_bridge.require_idle'))
        self.stack.enter_context(patch('python_binding.command', return_value=sys.executable))
        children = []
        popen = subprocess.Popen
        def capture(*args, **kwargs):
            child = popen(*args, **kwargs)
            if kwargs.get('start_new_session'):
                children.append(child)
            return child
        self.stack.enter_context(patch.object(subprocess, 'Popen', side_effect=capture))
        def reap():
            (runtime/'escape').touch()
            for child in children:
                try: child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=2)
        self.addCleanup(reap)
        try:
            live = gate.enable(root, self.uid, seconds=15)
            self.assertEqual(live['intent']['phase'], 'trial')
            self.assertTrue(live['effective']['mounted'])
            self.assertIsNone(live['effective']['profiles'])
        finally:
            (runtime/'escape').touch()
        deadline = time.monotonic()+4
        while time.monotonic() < deadline:
            try: after = gate.status(root, self.uid)['effective']
            except ValueError: continue  # Native guardian holds its lock during release.
            if after['stock_verified'] and after['stopped']: break
            time.sleep(.05)
        else: self.fail('native guardian did not restore stock')
        self.assertEqual(after['reason'], 'escape')

    def close_scenario(self, gone_at, foreground):
        clock = [0.0]
        self.stack.enter_context(patch.object(gate.time, 'monotonic', side_effect=lambda: clock[0]))
        self.stack.enter_context(patch.object(gate.time, 'sleep', side_effect=lambda seconds: clock.__setitem__(0, clock[0]+seconds)))
        self.mock('stock_running', side_effect=lambda target: clock[0] < gone_at)
        requests = []
        def call(uri, payload, timeout=5):
            requests.append((uri.rsplit('/',1)[-1], payload))
            if uri.endswith('/getForegroundAppInfo'):
                return {'returnValue':True, 'appId':foreground(clock[0])}
            if uri.endswith('/closeByAppId'):
                return {'returnValue':True}
            self.fail('unexpected RPC: '+uri)
        self.mock('luna', side_effect=call)
        return clock, requests

    def test_delayed_close_waits_for_sam_idle_and_does_not_launch_again(self):
        def fg(now):
            return 'com.webos.app.home' if now < 10 else '' if now < 13 else gate.APP
        clock, requests = self.close_scenario(10, fg)
        gate.retire_stock({})
        self.assertGreaterEqual(clock[0], 13)
        self.assertEqual([request for request in requests if request[0]!='getForegroundAppInfo'],
            [('closeByAppId', {'id':'com.webos.app.home','forceMode':True})])

    def test_existing_stock_process_requires_exact_close_readback(self):
        clock, requests = self.close_scenario(3600, lambda now: 'com.webos.app.home')
        with self.assertRaisesRegex(ValueError, 'stock Home'):
            gate.retire_stock({})
        self.assertGreaterEqual(clock[0], 15)
        self.assertLess(clock[0], 20)

    def test_preloaded_stock_close_keeps_live_tv_in_foreground(self):
        clock, requests = self.close_scenario(10, lambda now: 'com.webos.app.livetv')
        gate.retire_stock({})
        self.assertEqual([method for method,_ in requests], ['getForegroundAppInfo','closeByAppId'])
        self.assertLess(clock[0], 12)

    def test_empty_foreground_after_close_times_out_without_duplicate_launch(self):
        clock, requests = self.close_scenario(10, lambda now: '')
        with self.assertRaisesRegex(ValueError, 'foreground'):
            gate.retire_stock({})
        self.assertGreaterEqual(clock[0], 20)
        self.assertLess(clock[0], 25)
        self.assertNotIn('launch', [method for method,_ in requests])


if __name__ == '__main__':
    unittest.main()
