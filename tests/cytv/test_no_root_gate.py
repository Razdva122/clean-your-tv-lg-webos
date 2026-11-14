"""Real kernel-lock tests. Changing exec inheritance or revocation fails here."""
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

REPO = Path(__file__).resolve().parents[2]


@unittest.skipIf(os.name == 'nt' or not shutil.which('cc'), 'POSIX native gate')
class LifecycleGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory(prefix='cytv-gate-', dir='/private/tmp' if sys.platform == 'darwin' else '/tmp')
        cls.binary = Path(cls.work.name) / 'gate'
        source = REPO / 'native/installer/lifecycle-gate.c'
        if source.exists():
            subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror', str(source), '-o', str(cls.binary)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.work.cleanup()

    def setUp(self):
        self.directory = Path(tempfile.mkdtemp(dir=self.work.name))
        self.root = self.directory / 'state'
        self.root.mkdir(mode=0o750)
        os.chown(self.root, -1, os.getgid())
        self.generation = 'a' * 32
        self.children = []

    def tearDown(self):
        for process in self.children:
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=5)
        shutil.rmtree(self.directory)

    def call(self, action, *args):
        self.assertTrue(self.binary.exists(), 'native lifecycle gate is not implemented')
        return subprocess.run([str(self.binary), str(self.root), self.generation, action, *args], capture_output=True, timeout=5)

    def start(self, *args):
        self.assertTrue(self.binary.exists(), 'native lifecycle gate is not implemented')
        process = subprocess.Popen([str(self.binary), str(self.root), self.generation, 'run', *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.children.append(process)
        return process

    def test_revoke_keeps_inode_and_prevents_late_executor(self):
        self.assertEqual(self.call('run', shutil.which('true')).returncode, 0)
        inode = (self.root / 'lifecycle.lock').stat().st_ino
        self.assertEqual(self.call('revoke').returncode, 0)
        self.assertEqual(self.call('revoke').returncode, 0)
        effect = self.directory / 'effect'
        result = self.call('run', '/bin/sh', '-c', 'echo effect > "$1"', 'sh', str(effect))
        self.assertEqual(result.returncode, 73)
        self.assertFalse(effect.exists())
        self.assertEqual((self.root / 'lifecycle.lock').stat().st_ino, inode)

    def test_child_inherits_lock_and_revoke_waits_after_wrapper_death(self):
        script = 'import os,subprocess,time; p=subprocess.Popen(["/bin/sleep","1"],pass_fds=(3,)); print("ready",flush=True); time.sleep(10)'
        first = self.start(sys.executable, '-c', script)
        self.assertEqual(first.stdout.readline(), b'ready\n')
        first.kill(); first.wait(timeout=5)
        start = time.monotonic()
        self.assertEqual(self.call('revoke').returncode, 0)
        self.assertGreater(time.monotonic() - start, .65)

    def test_symlink_hardlink_unsafe_mode_and_ancestor_refused(self):
        external = self.directory / 'foreign'; external.write_text('')
        lock = self.root / 'lifecycle.lock'
        lock.symlink_to(external)
        self.assertNotEqual(self.call('revoke').returncode, 0); lock.unlink()
        os.link(external, lock)
        self.assertNotEqual(self.call('revoke').returncode, 0); lock.unlink()
        lock.write_text(''); lock.chmod(0o644)
        self.assertNotEqual(self.call('revoke').returncode, 0); lock.unlink()
        self.root.chmod(0o777)
        self.assertNotEqual(self.call('revoke').returncode, 0)
        self.assertEqual(external.read_text(), '')

    def test_revocation_is_specific_and_durable(self):
        self.assertEqual(self.call('revoke').returncode, 0)
        self.generation = 'b' * 32
        self.assertEqual(self.call('run', shutil.which('true')).returncode, 0)
        self.assertEqual((self.root / ('revoked-' + 'a' * 32)).read_bytes(), b'revoked\n')
        self.assertEqual((self.root / 'lifecycle.lock').stat().st_mode & 0o777, 0o640)

    def test_missing_root_is_never_recreated(self):
        self.root.rmdir()
        self.assertNotEqual(self.call('revoke').returncode, 0)
        self.assertFalse(self.root.exists())

    def test_legacy_open_before_flock_can_restart_after_remove_and_reinstall(self):
        # Source counterexample: taking Helper locks is NOT an executor drain.
        # This pins why byte-identical Helper cannot support verified revocation.
        import fcntl
        helper = self.directory / 'helper'; helper.mkdir()
        state = helper / 'state'; state.mkdir(mode=0o770)
        marker = self.directory / 'resurrected'
        lock_header = (REPO / 'native/app/lock.h').read_text().replace('if(flock(fd,', 'raise(SIGSTOP);if(flock(fd,')
        source = (REPO / 'native/app/detach.c').read_text().replace('#include "lock.h"', '#include <signal.h>\n' + lock_header)
        # Retain the published 0.7.4 path as the deliberately unfenced control.
        source = source.replace('#include "../installer/runtime-lifecycle.h"', '')
        source = source.replace(' if(cytv_runtime_guard("/media/developer/apps/usr/palm/applications/com.local.nativehome/detach")<0)return 73;', '')
        source = source.replace('/media/developer/apps/usr/palm/applications/com.local.nativehome', str(helper))
        source = source.replace('/usr/bin/node', shutil.which('node'))
        c = self.directory / 'detach.c'; c.write_text(source)
        binary = helper / 'detach'
        subprocess.run(['cc', str(c), '-o', str(binary)], check=True)
        process = subprocess.Popen([str(binary), '{"nativeHomeAuto":true}', '--controller'])
        self.children.append(process)
        pid, status = os.waitpid(process.pid, os.WUNTRACED)
        self.assertEqual(pid, process.pid); self.assertTrue(os.WIFSTOPPED(status))
        with (state / 'controller.lock').open('rb') as owned:
            fcntl.flock(owned, fcntl.LOCK_EX | fcntl.LOCK_NB)
            shutil.rmtree(helper)
        helper.mkdir(); (helper / 'state').mkdir()
        (helper / 'native.js').write_text('require("fs").writeFileSync(' + repr(str(marker)) + ',"late old executor");')
        process.send_signal(signal.SIGCONT); process.wait(timeout=5)
        deadline = time.monotonic() + 5
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertEqual(marker.read_text(), 'late old executor')

    def test_explicit_helper_start_waits_only_for_the_observed_stop(self):
        import fcntl
        helper = self.directory / 'helper'
        state = helper / 'state'
        state.mkdir(parents=True)
        lock = state / 'controller.lock'
        lock.touch()
        (state / 'blocked').write_text('stopped')
        generation = state / 'stop-generation'
        generation.write_text('S' + 'a' * 32)
        source = (REPO / 'native/app/detach.c').read_text()
        source = source.replace('/media/developer/apps/usr/palm/applications/com.local.nativehome', str(helper))
        source = source.replace('/usr/bin/node', shutil.which('node'))
        c = self.directory / 'detach.c'
        c.write_text(source)
        binary = helper / 'detach'
        subprocess.run(['cc', '-I', str(REPO / 'native/app'), str(c), '-o', str(binary)], check=True)
        marker = helper / 'started'
        (helper / 'native.js').write_text('require("fs").writeFileSync(' + repr(str(marker)) + ',"started");')
        for changed in (False, True):
            marker.unlink(missing_ok=True)
            with lock.open('rb') as owner:
                fcntl.flock(owner, fcntl.LOCK_EX)
                process = subprocess.Popen([str(binary), '{}', '--controller', '--wait-for-stop'])
                self.children.append(process)
                time.sleep(.23)
                self.assertIsNone(process.poll())
                if changed:
                    replacement = state / 'new-generation'
                    replacement.write_text('S' + 'b' * 32)
                    replacement.replace(generation)
            process.wait(timeout=5)
            if not changed:
                deadline = time.monotonic() + 3
                while not marker.exists() and time.monotonic() < deadline:
                    time.sleep(.02)
            self.assertEqual(marker.exists(), not changed)

    def test_removed_stable_lock_is_not_recreated(self):
        self.assertEqual(self.call('revoke').returncode, 0)
        (self.root / 'lifecycle.lock').unlink()
        self.assertNotEqual(self.call('revoke').returncode, 0)
        self.assertFalse((self.root / 'lifecycle.lock').exists())

    def test_removal_owner_excludes_other_hosts_until_verified_finish(self):
        old = self.generation
        self.assertEqual(self.call('run', shutil.which('true')).returncode, 0)
        self.generation = 'b' * 32
        self.assertEqual(self.call('remove', old, shutil.which('true')).returncode, 0)
        self.generation = 'c' * 32
        self.assertEqual(self.call('run', shutil.which('true')).returncode, 73)
        self.assertNotEqual(self.call('finish-removal').returncode, 0)
        self.generation = 'b' * 32
        self.assertEqual(self.call('run', shutil.which('true')).returncode, 0)
        self.assertEqual(self.call('finish-removal').returncode, 0)
        self.generation = old
        self.assertEqual(self.call('run', shutil.which('true')).returncode, 73)
        self.generation = 'c' * 32
        self.assertEqual(self.call('run', shutil.which('true')).returncode, 0)

    def test_root_existing_ownership_lock_is_held_without_recreation(self):
        import fcntl
        owned = self.directory / 'root-ownership'; owned.mkdir(mode=0o700)
        mutex = owned / 'ownership.lock'; mutex.write_bytes(b''); mutex.chmod(0o600)
        binary = self.directory / 'root-gate'
        subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror',
                        '-DCYTV_ROOT_LOCK_DIRECTORY="' + str(owned) + '"',
                        str(REPO / 'native/installer/lifecycle-gate.c'), '-o', str(binary)], check=True)
        process = subprocess.Popen([str(binary), 'root-lock', sys.executable, '-c',
                                    'import os,sys;os.fstat(3);print("ready",flush=True);sys.stdin.read()'],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.children.append(process)
        self.assertEqual(process.stdout.readline(), b'ready\n')
        with mutex.open('rb') as stream:
            with self.assertRaises(BlockingIOError): fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        process.communicate(b'', timeout=5)
        mutex.unlink()
        result = subprocess.run([str(binary), 'root-lock', shutil.which('true')], capture_output=True, timeout=5)
        self.assertNotEqual(result.returncode, 0); self.assertFalse(mutex.exists())

    def test_removal_revokes_before_waiting_for_running_helper_to_drain(self):
        import fcntl
        old=self.generation
        self.assertEqual(self.call('run',shutil.which('true')).returncode,0)
        with (self.root/'lifecycle.lock').open('rb') as runtime:
            fcntl.flock(runtime,fcntl.LOCK_SH)
            self.generation='b'*32
            result=self.call('prepare-removal',old,shutil.which('true'))
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue((self.root/('revoked-'+old)).exists())
        self.assertEqual(self.call('remove',old,shutil.which('true')).returncode,0)

    def test_root_cleanup_holds_the_original_python_promotion_lock(self):
        import fcntl
        owned=self.directory/'ownership';owned.mkdir(mode=0o700)
        mutex=owned/'ownership.lock';mutex.write_bytes(b'');mutex.chmod(0o600)
        worker=owned/'worker.lock';worker.write_bytes(b'');worker.chmod(0o600)
        runtime=self.directory/'python';runtime.mkdir(mode=0o755)
        promotion=runtime/'.install.lock';promotion.write_bytes(b'');promotion.chmod(0o600)
        binary=self.directory/'root-clean-gate'
        subprocess.run(['cc','-std=c99','-Wall','-Wextra','-Werror',
                        '-DCYTV_ROOT_LOCK_DIRECTORY="'+str(owned)+'"',
                        '-DCYTV_RUNTIME_LOCK_DIRECTORY="'+str(runtime)+'"',
                        str(REPO/'native/installer/lifecycle-gate.c'),'-o',str(binary)],check=True)
        process=subprocess.Popen([str(binary),'root-clean-lock',sys.executable,'-c',
                                  'import os,sys;os.fstat(3);os.fstat(4);os.fstat(5);print("ready",flush=True);sys.stdin.read()'],
                                 stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        self.children.append(process)
        self.assertEqual(process.stdout.readline(),b'ready\n')
        for path in (mutex,promotion,worker):
            with path.open('rb') as stream:
                with self.assertRaises(BlockingIOError):fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        busy=subprocess.run([str(binary),'root-clean-lock',shutil.which('true')],capture_output=True,timeout=5)
        self.assertEqual(busy.returncode,75)
        process.communicate(b'',timeout=5)
        promotion.unlink()
        result=subprocess.run([str(binary),'root-clean-lock',shutil.which('true')],capture_output=True,timeout=5)
        self.assertNotEqual(result.returncode,0);self.assertFalse(promotion.exists())
