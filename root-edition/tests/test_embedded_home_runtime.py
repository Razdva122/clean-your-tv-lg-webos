"""Host tests of the embedded launch transaction and shared backend dispatch."""
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'runtime'), str(ROOT)]


class EmbeddedHomeTests(unittest.TestCase):
    def setUp(self):
        self.k = importlib.import_module('c1_keyfilter')
        self.e = importlib.import_module('embedded_home')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.directory = self.root / 'c1-keyfilter'
        self.directory.mkdir(mode=0o700)
        self.uid = os.getuid()
        self.job = self.root / 'surface-manager.conf'
        self.job.write_bytes(b'respawn\nscript\nexec /usr/bin/surface-manager-starfish -platform starfish\nend script\n')
        self.addCleanup(patch.stopall)
        patch.object(self.e, 'JOB', self.job).start()
        patch.object(self.e, 'path', side_effect=lambda root, name: Path(root) / 'c1-keyfilter' / name).start()
        self.k.secure = patch.object(self.k, 'secure', side_effect=lambda path, *args, **kwargs: Path(path).read_bytes()).start()
        patch.object(self.k, 'atomic', side_effect=lambda path, value, *args, **kwargs: Path(path).write_text(json.dumps(value))).start()
        patch.object(self.k, 'process_start', return_value=123).start()
        patch.object(self.k, 'boot_identity', return_value='12345678-1234-1234-1234-123456789abc').start()

    def test_disabled_lifecycle_return_never_calls_native_home_interfaces(self):
        with patch.object(self.k, 'selection', return_value={'schema': 4}), patch.object(self.k, 'luna') as luna, patch.object(self.k, 'native') as native, patch.object(self.k, 'read_intent') as intent:
            self.assertFalse(self.k.return_ready(self.root, self.uid, 'a'*32, lambda: False))
        luna.assert_not_called()
        native.assert_not_called()
        intent.assert_not_called()

    def test_controller_reuses_health_loop_without_lifecycle_rpc(self):
        token = 'a'*32
        control_read, control_write = os.pipe()
        ready_read, ready_write = os.pipe()
        proof = dict(returnValue=True, backend=self.k.BACKEND, routing=self.k.ROUTING,
                     profiles=None, state='armed', token=token, mounted=False,
                     healthy=True, stock_verified=False, stopped=False,
                     guardian_pid=42, reason='')
        try:
            with patch.object(self.k, 'selection', return_value={'schema': 4}), patch.object(self.k, 'read_intent', return_value={'token': token, 'phase': 'active'}), patch.object(self.k, 'filter_present', return_value=True), patch.object(self.k, 'native', side_effect=[proof, ValueError('retired')]), patch.object(self.k.subprocess, 'Popen') as spawn:
                with self.assertRaisesRegex(ValueError, 'retired'):
                    self.k.watch(token, control_write, ready_write, self.root, self.uid)
            spawn.assert_not_called()
            self.assertEqual(os.read(ready_read, 128), ('WATCH '+token+'\n').encode())
            self.assertEqual(os.read(control_read, 128), b'READY\nPING\nLOST\n')
        finally:
            os.close(control_read)
            os.close(ready_read)

    def test_restore_records_inverse_before_stopping(self):
        observed = []
        state = [self.e.wrapper_url(self.root)]
        def command(*args):
            observed.append((args, self.e.receipt(self.root)['phase']))
            if args[0] == 'start':
                state[0] = self.e.STOCK_QML
            return ''
        with patch.object(self.e, 'current', side_effect=lambda _: (42, state[0])), patch.object(self.e, 'run', side_effect=command):
            self.e.restore(self.root)
        self.assertEqual([item[0][0] for item in observed], ['stop', 'start'])
        self.assertTrue(all(phase == 'restoring' for _, phase in observed))
        self.assertEqual(self.e.receipt(self.root)['phase'], 'stock')
        self.assertEqual(observed[1][0][-1], 'LSM_MAIN_QML=qrc:///main.qml')

    def test_recovery_restarts_a_job_left_stopped(self):
        with patch.object(self.e, 'current', side_effect=[ValueError('stopped'), (43, self.e.STOCK_QML)]), patch.object(self.e, 'run', side_effect=['surface-manager stop/waiting', 'started']) as run:
            self.e.restore(self.root)
        self.assertEqual(run.call_args_list[-1].args, ('start', 'surface-manager', 'LSM_MAIN_QML=qrc:///main.qml'))
        self.assertEqual(self.e.receipt(self.root)['phase'], 'stock')

    def test_changed_factory_job_preserves_prior_receipt(self):
        self.e.record(self.root, 'attaching')
        prior = self.e.receipt(self.root)
        self.job.write_bytes(b'foreign launch configuration')
        with patch.object(self.e, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'job changed'):
                self.e.restore(self.root)
        run.assert_not_called()
        self.assertEqual(self.e.receipt(self.root), prior)

    def test_unverified_stock_readback_keeps_failure_record(self):
        with patch.object(self.e, 'current', return_value=(42, self.e.wrapper_url(self.root))), patch.object(self.e, 'transition'):
            with self.assertRaisesRegex(ValueError, 'unverified'):
                self.e.restore(self.root)
        self.assertEqual(self.e.receipt(self.root)['phase'], 'failed')

    def test_stock_restore_is_idempotent_without_restart(self):
        with patch.object(self.e, 'current', return_value=(42, self.e.STOCK_QML)), patch.object(self.e, 'run') as run:
            self.e.restore(self.root)
            self.e.restore(self.root)
        run.assert_not_called()
        self.assertEqual(self.e.receipt(self.root)['phase'], 'stock')

    def test_foreign_launch_failure_is_not_overwritten(self):
        with patch.object(self.e, 'current', side_effect=ValueError('foreign')), patch.object(self.e, 'run', return_value='surface-manager start/running, process 99') as run:
            with self.assertRaisesRegex(ValueError, 'foreign'):
                self.e.restore(self.root)
        self.assertEqual(run.call_args.args, ('status', 'surface-manager'))
        self.assertEqual(self.e.receipt(self.root)['phase'], 'failed')

    def test_attachment_requires_matching_environment_and_broker(self):
        with patch.object(self.e, 'current', return_value=(42, self.e.STOCK_QML)), patch.object(self.k, 'luna') as luna:
            self.assertFalse(self.e.attached(self.root))
        luna.assert_not_called()
        with patch.object(self.e, 'current', return_value=(42, self.e.wrapper_url(self.root))), patch.object(self.k, 'luna', return_value={'returnValue': True, 'adapter': self.e.ADAPTER, 'attached': True}):
            self.assertTrue(self.e.attached(self.root))

    def test_malformed_receipt_refuses_recovery(self):
        (self.directory / 'embedded-launch.json').write_text('{"schema":1}')
        with patch.object(self.e, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'Invalid'):
                self.e.restore(self.root)
        run.assert_not_called()

    def test_command_failure_never_means_stopped(self):
        failure = subprocess.CalledProcessError(1, ['initctl', 'status'])
        with patch.object(self.e, 'current', side_effect=failure), patch.object(self.e, 'run') as run:
            with self.assertRaises(subprocess.CalledProcessError):
                self.e.restore(self.root)
        run.assert_not_called()
        self.assertEqual(self.e.receipt(self.root)['phase'], 'failed')

    def test_parent_disappearance_cancels_before_attach_commit(self):
        read, write = os.pipe()
        os.close(write)
        try:
            with self.assertRaisesRegex(ValueError, 'cancelled'):
                self.e.check_cancelled(read)
        finally:
            os.close(read)

    def test_busy_transition_lock_cannot_mutate_receipt(self):
        import fcntl
        lock = os.open(self.directory / 'embedded-transition.lock', os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(lock, fcntl.LOCK_EX)
            with patch.object(self.e.time, 'monotonic', side_effect=[0, 101]):
                with self.assertRaisesRegex(ValueError, 'transition busy'):
                    self.e.restore(self.root)
            self.assertIsNone(self.e.receipt(self.root))
        finally:
            os.close(lock)

    def test_changed_process_instance_refuses_stop(self):
        with patch.object(self.e, 'current', side_effect=[(42, self.e.wrapper_url(self.root)), (43, self.e.wrapper_url(self.root))]), patch.object(self.e, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'instance changed'):
                self.e.transition(self.root, self.e.STOCK_QML)
        run.assert_not_called()

    def test_attachment_cancellation_restores_before_unlock(self):
        ready_read, ready_write = os.pipe()
        cancel_read, cancel_write = os.pipe()
        def cancel_during_launch(*args):
            os.close(cancel_write)
        try:
            with patch.object(self.k, 'verify_ready', return_value={'integrity_verified': True}), patch.object(self.e, 'transition', side_effect=cancel_during_launch), patch.object(self.e, 'restore_locked') as restore:
                for name in self.e.ASSETS:
                    target = self.root / 'runtime' / name
                    target.parent.mkdir(exist_ok=True)
                    target.write_text('fixture')
                with self.assertRaisesRegex(ValueError, 'cancelled'):
                    self.e.supervise(self.root, ready_write, cancel_read)
            restore.assert_called_once_with(self.root)
        finally:
            os.close(ready_read)

    def test_resident_wrapper_does_not_query_lease_or_restart_after_attachment(self):
        ready_read, ready_write = os.pipe()
        for name in self.e.ASSETS:
            target = self.root / 'runtime' / name
            target.parent.mkdir(exist_ok=True)
            target.write_text('fixture')
        def tick(_):
            # Simulate removal request after a controller died. Attachment would
            # now report false, but the resident policy must be left running.
            self.e.record(self.root, 'restoring')
        try:
            with patch.object(self.k, 'verify_ready', return_value={'integrity_verified': True}), patch.object(self.e, 'transition') as transition, patch.object(self.e, 'attached', side_effect=[True, False]) as attached, patch.object(self.e, 'current', return_value=(42, self.e.wrapper_url(self.root))), patch.object(self.e.time, 'sleep', side_effect=tick), patch.object(self.e, 'restore_locked') as restore:
                self.e.supervise(self.root, ready_write)
            self.assertEqual(os.read(ready_read, 32), b'ATTACHED\n')
            self.assertEqual(attached.call_count, 1)
            transition.assert_called_once_with(self.root, self.e.wrapper_url(self.root))
            restore.assert_not_called()
        finally:
            os.close(ready_read)

    def test_root_commands_reject_writable_executable_before_spawn(self):
        executable = self.root / 'initctl'
        executable.write_text('fixture')
        executable.chmod(0o777)
        with patch.object(self.e, 'INITCTL', executable), patch.object(self.k.legacy, 'trusted_directory'), patch.object(self.e.subprocess, 'run') as spawn:
            with self.assertRaisesRegex(ValueError, 'Untrusted'):
                self.e.run('status', 'surface-manager')
        spawn.assert_not_called()

    def test_failed_handshake_cancels_and_retires_launcher_before_return(self):
        import select
        child = Mock()
        cancellation = []
        def launch(*args, **kwargs):
            cancellation.append(os.dup(kwargs['pass_fds'][1]))
            return child
        def retire(**kwargs):
            self.assertTrue(select.select(cancellation, [], [], 0)[0])
            self.assertEqual(os.read(cancellation[0], 1), b'')
        child.wait.side_effect = retire
        try:
            with patch.object(self.e, 'capabilities'), patch.object(self.e, 'attached', return_value=False), patch('python_binding.command', return_value=sys.executable), patch.object(self.e.subprocess, 'Popen', side_effect=launch), patch.object(self.k, 'read_handshake', side_effect=ValueError('handshake failed')):
                with self.assertRaisesRegex(ValueError, 'handshake failed'):
                    self.e.install(self.root)
            child.wait.assert_called_once_with(timeout=65)
        finally:
            for fd in cancellation:
                os.close(fd)

    def test_existing_native_guardian_uses_original_home_header(self):
        admission = {'target': dict(dev=1, ino=2, size=52, mtime_ns=3)}
        captured = {}
        with patch.object(self.k, 'private_directory', return_value=self.directory), patch.object(self.k, 'atomic', side_effect=lambda path, data, *args, **kw: captured.update(raw=data)):
            self.k.write_config(self.root, admission, 'a' * 32, self.uid)
        self.assertTrue(captured['raw'].startswith(b'CYTV-C1-KEYFILTER-1\n'))

    def test_embedded_guardian_uses_explicit_target_header(self):
        admission = {'target': dict(dev=1, ino=2, size=52, mtime_ns=3)}
        captured = {}
        with patch.object(self.k, 'private_directory', return_value=self.directory), patch.object(self.k, 'atomic', side_effect=lambda path, data, *args, **kw: captured.update(raw=data)):
            self.k.write_config(self.root, admission, 'a' * 32, self.uid, embedded=True)
        self.assertTrue(captured['raw'].startswith(b'CYTV-QML-KEYFILTER-1\n'))


if __name__ == '__main__':
    unittest.main()
