import errno
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from cytv import diagnostics, state
from cytv.errors import TVCommandError, UserError


class HomeDiagnosticsTests(unittest.TestCase):
    @unittest.skipUnless(os.name == 'posix', 'requires POSIX file group ownership')
    def test_root_ssh_publishes_diagnostics_with_the_helper_state_group(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp).resolve() / 'helper-state'
            directory.mkdir()
            group = (5000 if os.getuid() == 0 else
                     next((gid for gid in os.getgroups() if gid != os.getegid()), os.getegid()))
            os.chown(directory, -1, group)
            control = directory / 'control.json'
            control.write_text('{}')
            control.chmod(0o640)
            os.chown(control, -1, os.getegid())
            requests = []
            permissions = []

            class Remote:
                def upload(self, path, data, mode):
                    raise AssertionError('Root SSH upload leaves the control record in the SSH group')

                def run(self, command, data=None, timeout=None):
                    if command == '/usr/bin/node':
                        script = data.replace(
                            b'/media/developer/apps/usr/palm/applications/com.local.nativehome/state',
                            str(directory).encode())
                        result = subprocess.check_output(['node'], input=script).decode()
                        requests.append(json.loads(control.read_text()))
                        current = control.stat()
                        permissions.append((current.st_gid, current.st_mode & 0o777))
                        return result
                    return '\n'.join(json.dumps(dict(event='home-diagnostic',
                        session=requests[0]['nonce'], trigger=trigger))
                        for trigger in ('started', 'expired'))

            report = diagnostics.collect_home_report(Remote(), state.Store(tmp),
                state.target('192.0.2.55', 'no-root', connection='root-ssh'), Mock())
            self.assertTrue(json.loads(report.read_text())['helper_diagnostics']['complete'])
            self.assertEqual(permissions, [(group, 0o660), (group, 0o660)])
            start, stop = requests
            self.assertEqual(start['cmd'], 'diagnostics-start')
            self.assertEqual(stop, {'cmd': 'diagnostics-stop', 'nonce': start['nonce']})

    def test_collects_one_allowlisted_report_and_stops_recording(self):
        class Remote:
            def __init__(self): self.commands = []
            def upload(self, path, data, mode):
                self.commands.append(json.loads(data))
            def run(self, command):
                session = self.commands[0]['nonce']
                return '\n'.join(json.dumps(x) for x in [
                    {'event':'launch','secret':'PAIRINGKEY'},
                    {'event':'home-diagnostic','session':'old','trigger':'home'},
                    {'event':'home-diagnostic','session':session,'trigger':'started','time':1},
                    {'event':'home-diagnostic','session':session,'trigger':'foreground','foreground':'com.webos.app.home','foregroundAgeMs':0,'secret':'PAIRINGKEY'},
                    {'event':'home-diagnostic','session':session,'trigger':'expired','time':2},
                ])
        with tempfile.TemporaryDirectory() as tmp:
            remote = Remote()
            path = diagnostics.collect_home_report(remote, state.Store(tmp),
                state.target('192.0.2.55', 'no-root'), lambda text: None)
            value = json.loads(path.read_text())
            self.assertTrue(value['helper_diagnostics']['complete'])
            self.assertEqual(len(value['helper_diagnostics']['records']), 3)
            self.assertEqual(len(list(path.parent.glob('*.json'))), 1)
            self.assertNotIn('PAIRINGKEY', path.read_text())
            self.assertEqual(remote.commands[-1]['cmd'], 'diagnostics-stop')

    def test_report_686_replay_keeps_waiting_for_restarted_helper(self):
        # The six observed events end at 4.268 s, then SSH reads stale logs.
        prefix = [
            ('started', 0), ('sample', 1379), ('monitor-reset', 2390),
            ('monitor', 2439), ('sample', 2855), ('sample', 4268),
        ]
        clock = [0]
        remote = Mock()
        def read_log(command):
            request = json.loads(remote.upload.call_args_list[0].args[1])
            events = [dict(event='home-diagnostic', session=request['nonce'],
                           trigger=trigger, time=offset)
                      for trigger, offset in prefix]
            if clock[0] >= 85:
                events.extend([
                    dict(event='home-diagnostic', session=request['nonce'],
                         trigger='resumed', time=85000, controllerPid=22),
                    dict(event='home-diagnostic', session=request['nonce'],
                         trigger='launch-request', time=85001, id='com.gathin.tvhome'),
                    dict(event='home-diagnostic', session=request['nonce'],
                         trigger='foreground', time=86000, foreground='youtube.leanback.v4'),
                ])
            if clock[0] >= 146:
                events.append(dict(event='home-diagnostic', session=request['nonce'],
                                   trigger='expired', time=146000))
            return '\n'.join(map(json.dumps, events))
        remote.run.side_effect = read_log
        with tempfile.TemporaryDirectory() as tmp, patch('time.monotonic', side_effect=lambda: clock[0]), \
                patch('time.sleep', side_effect=lambda seconds: clock.__setitem__(0, clock[0] + seconds)):
            path = diagnostics.collect_home_report(remote, state.Store(tmp),
                state.target('192.0.2.55', 'no-root'), Mock())
            capture = json.loads(path.read_text())['helper_diagnostics']
        self.assertTrue(capture['complete'])
        self.assertEqual(len(capture['records']), 10)
        self.assertEqual(capture['records'][6]['trigger'], 'resumed')
        self.assertEqual(capture['records'][8]['foreground'], 'youtube.leanback.v4')
        self.assertEqual(len(remote.upload.call_args_list), 2)
        self.assertLessEqual(clock[0], 190)

    def test_disconnect_before_monitor_reset_waits_for_late_helper_restart(self):
        clock = [0]
        before, after = Mock(), Mock()
        def event(trigger, **fields):
            request = json.loads(before.upload.call_args_list[0].args[1])
            return json.dumps(dict(event='home-diagnostic', session=request['nonce'],
                                   trigger=trigger, **fields))
        def read_before(command):
            if before.run.call_count == 1:
                return event('started', time=1)
            raise ConnectionResetError()
        before.run.side_effect = read_before
        after.run.return_value = ''
        after.run.side_effect = lambda command: '\n'.join([
            event('resumed', time=85000, controllerPid=22),
            event('foreground', time=86000, foreground='youtube.leanback.v4'),
            event('expired', time=146000)])
        def reconnect():
            if clock[0] < 85:
                raise ConnectionRefusedError()
            return after
        with tempfile.TemporaryDirectory() as tmp, patch('time.monotonic', side_effect=lambda: clock[0]), \
                patch('time.sleep', side_effect=lambda seconds: clock.__setitem__(0, clock[0] + seconds)):
            path = diagnostics.collect_home_report(before, state.Store(tmp),
                state.target('192.0.2.55', 'no-root'), Mock(), reconnect=reconnect)
            capture = json.loads(path.read_text())['helper_diagnostics']
        self.assertTrue(capture['complete'])
        self.assertGreater(clock[0], 70)
        self.assertGreater(capture['connection']['reconnect_attempts'], 1)
        self.assertEqual(capture['records'][1]['trigger'], 'resumed')
        self.assertEqual(json.loads(before.upload.call_args.args[1])['durationMs'], 180000)
        self.assertEqual(json.loads(after.upload.call_args.args[1])['cmd'], 'diagnostics-stop')

    def test_cli_recovers_the_same_recording_after_standby_disconnect(self):
        from paramiko import SSHException
        from cytv import cli

        before = Mock()
        after = Mock()
        clock = [0]

        def line(trigger, **fields):
            request = json.loads(before.upload.call_args_list[0].args[1])
            return json.dumps(dict(event='home-diagnostic', session=request['nonce'],
                                   trigger=trigger, **fields))

        def first_read(command):
            if before.run.call_count == 1:
                return line('started', time=1)
            raise SSHException('session closed during standby')

        before.run.side_effect = first_read
        def read_after_wake(command):
            events = [line('started', time=1)]
            if clock[0] >= 12:
                events.append(line('foreground', time=12000, foreground='com.gathin.tvhome'))
            if clock[0] >= 13:
                events.append(line('foreground', time=13000, foreground='youtube.leanback.v4'))
            if clock[0] >= 23:
                events.append(line('launch-request', time=23000, id='com.gathin.tvhome', private='PRIVATE'))
            if clock[0] >= 60:
                events.append(line('expired', time=60001))
            return '\n'.join(events)

        after.run.side_effect = read_after_wake
        def tv_still_asleep():
            clock[0] += 12
            raise OSError(errno.ENETUNREACH, 'network unreachable during standby')

        def connect_to_tv(*args, **kwargs):
            if connect.call_count == 1:
                return before
            if connect.call_count == 2:
                tv_still_asleep()
            return after

        connect = Mock(side_effect=connect_to_tv)
        with tempfile.TemporaryDirectory() as tmp, patch('time.monotonic', side_effect=lambda: clock[0]), \
                patch('cytv.diagnostics.time.sleep', side_effect=lambda seconds: clock.__setitem__(0, clock[0] + seconds)):
            code = cli.main(['home-diagnostics', '--host', '192.0.2.55', '--edition', 'no-root',
                             '--data-dir', tmp, '--language', 'en'], ask=lambda _: 'y',
                            write=lambda _: None, connect=connect)
            self.assertEqual(code, 0)
            path, = (Path(tmp) / 'reports').glob('diagnostic-*.json')
            raw = path.read_text()
            capture = json.loads(raw)['helper_diagnostics']
            self.assertTrue(capture['complete'])
            self.assertEqual([record['trigger'] for record in capture['records']],
                             ['started', 'foreground', 'foreground', 'launch-request', 'expired'])
            self.assertEqual(capture['records'][2]['foreground'], 'youtube.leanback.v4')
            self.assertNotIn('PRIVATE', raw)
        self.assertEqual(connect.call_count, 3)
        for attempt in connect.call_args_list[1:]:
            self.assertEqual(attempt.kwargs, {'persist': False})
            self.assertFalse(attempt.args[3]('untrusted-key', False))
        before.close.assert_called_once()
        after.close.assert_called_once()
        before.upload.assert_called_once()
        after.upload.assert_called_once()
        start = json.loads(before.upload.call_args.args[1])
        stop = json.loads(after.upload.call_args.args[1])
        self.assertEqual(start['cmd'], 'diagnostics-start')
        self.assertEqual(stop, {'cmd': 'diagnostics-stop', 'nonce': start['nonce']})

    @unittest.skipUnless(os.name == 'posix', 'Requires a POSIX shell for the TV command')
    def test_reads_rotated_wake_events_in_order(self):
        remote = Mock()
        with tempfile.TemporaryDirectory() as tmp:
            def read_log(command):
                log = Path(tmp) / 'controller.log'
                start = json.loads(remote.upload.call_args.args[1])
                def event(trigger):
                    return json.dumps(dict(event='home-diagnostic', session=start['nonce'],
                                           trigger=trigger)) + '\n'
                log.with_suffix('.log.previous').write_text(event('started') + event('foreground'))
                log.write_text(event('foreground') + event('launch-request') + event('expired'))
                return subprocess.check_output(command.replace(
                    '/media/developer/apps/usr/palm/applications/com.local.nativehome/state', tmp),
                    shell=True, text=True)

            remote.run.side_effect = read_log
            path = diagnostics.collect_home_report(remote, state.Store(tmp),
                state.target('192.0.2.55', 'no-root'), Mock())
            capture = json.loads(path.read_text())['helper_diagnostics']
        self.assertTrue(capture['complete'])
        self.assertEqual([record['trigger'] for record in capture['records']],
                         ['started', 'foreground', 'launch-request', 'expired'])

    def test_saves_partial_recording_when_tv_does_not_reconnect_in_time(self):
        remote = Mock()

        def read_log(command):
            if remote.run.call_count > 1:
                raise TVCommandError(-1)
            request = json.loads(remote.upload.call_args.args[1])
            return json.dumps(dict(event='home-diagnostic', session=request['nonce'], trigger='started'))

        remote.run.side_effect = read_log
        reconnect = Mock(side_effect=ConnectionRefusedError)
        write = Mock()
        with tempfile.TemporaryDirectory() as tmp, patch('time.sleep'), \
                patch('time.monotonic', side_effect=[0, 0, 2, 4, 190, 190]):
            path = diagnostics.collect_home_report(remote, state.Store(tmp),
                state.target('192.0.2.55', 'no-root'), write, reconnect=reconnect)
            report = json.loads(path.read_text())['helper_diagnostics']
        self.assertFalse(report['complete'])
        self.assertEqual(report['failure_stage'], 'log-read')
        self.assertEqual([record['trigger'] for record in report['records']], ['started'])
        reconnect.assert_called_once()
        remote.upload.assert_called_once()
        self.assertIn('incomplete', write.call_args.args[0])

    def test_does_not_retry_when_reconnect_rejects_host_identity(self):
        remote = Mock()
        remote.run.side_effect = ConnectionResetError()
        reconnect = Mock(side_effect=UserError('Host key was not verified.',
                                              reason_code='ssh-identity-unverified'))
        with tempfile.TemporaryDirectory() as tmp, patch('time.sleep'):
            with self.assertRaisesRegex(UserError, 'Host key was not verified') as failure:
                diagnostics.collect_home_report(remote, state.Store(tmp),
                    state.target('192.0.2.55', 'no-root'), Mock(), reconnect=reconnect)
        self.assertEqual(failure.exception.home_diagnostic_stage, 'log-read')
        reconnect.assert_called_once()
        remote.upload.assert_called_once()

    def test_unsupported_helper_stops_and_explains_without_waiting_a_minute(self):
        class Remote:
            def __init__(self): self.commands=[]
            def upload(self,path,data,mode): self.commands.append(json.loads(data))
            def run(self,command): return '{}'
        with tempfile.TemporaryDirectory() as tmp, patch('time.sleep'), patch('time.monotonic', side_effect=[0,0,1,6]):
            remote=Remote()
            store = state.Store(tmp)
            profile = state.target('192.0.2.55', 'no-root')
            with self.assertRaisesRegex(UserError,'Helper') as failure:
                diagnostics.collect_home_report(remote, store, profile, lambda text: None)
            self.assertEqual(remote.commands[-1]['cmd'],'diagnostics-stop')
            path = diagnostics.create_report(store, 'home-diagnostics', profile, 'home-diagnostics', failure.exception)
            self.assertEqual(json.loads(path.read_text()).get('helper_diagnostics'),
                             {'failure_stage': 'start-unacknowledged'})

    def test_cli_exports_failed_control_upload_separately_from_log_read_failure(self):
        from cytv import cli
        for failed_upload, probe, expected in (
            (True, 'unavailable', {'failure_stage': 'start-upload', 'state_directory': 'unavailable'}),
            (True, 'access-denied', {'failure_stage': 'start-upload', 'state_directory': 'access-denied'}),
            (True, 'access-available', {'failure_stage': 'start-upload', 'state_directory': 'access-available'}),
            (True, 'PRIVATE-REMOTE-OUTPUT', {'failure_stage': 'start-upload', 'state_directory': 'unknown'}),
            (True, OSError('PRIVATE-REMOTE-OUTPUT'), {'failure_stage': 'start-upload', 'state_directory': 'unknown'}),
            (False, None, {'failure_stage': 'log-read'}),
        ):
            with self.subTest(probe=probe), tempfile.TemporaryDirectory() as tmp:
                remote = Mock()
                remote.run.side_effect = [probe if failed_upload else TVCommandError(1)]
                if failed_upload:
                    remote.upload.side_effect = [TVCommandError(1), TVCommandError(2)]
                code = cli.main(['home-diagnostics', '--host', '192.0.2.55', '--edition', 'no-root',
                                 '--data-dir', tmp, '--language', 'en'],
                                ask=lambda _: 'y', write=lambda _: None, connect=lambda *args: remote)
                self.assertEqual(code, 2)
                path, = (Path(tmp) / 'reports').glob('diagnostic-*.json')
                raw = path.read_text()
                report = json.loads(raw)
                self.assertEqual(report.get('helper_diagnostics'), expected)
                self.assertEqual(report['ssh_command'], {'exit_status': 1})
                self.assertIsNone(report['pending'])
                self.assertNotIn('PRIVATE-REMOTE-OUTPUT', raw)
                self.assertNotIn('192.0.2.55', raw)
                self.assertEqual([json.loads(call.args[1])['cmd'] for call in remote.upload.call_args_list],
                                 ['diagnostics-start', 'diagnostics-stop'])
                self.assertEqual(remote.run.call_count, 1)

    def test_cli_action_saves_report_without_installing(self):
        from cytv import cli
        from unittest.mock import MagicMock
        with tempfile.TemporaryDirectory() as tmp, patch('cytv.cli.Installer') as installer, patch('cytv.diagnostics.collect_home_report') as collect:
            collect.return_value = __import__('pathlib').Path(tmp) / 'diagnostic-123456abcdef.json'
            code = cli.main(['home-diagnostics', '--host', '192.0.2.55', '--edition', 'no-root', '--data-dir', tmp, '--language', 'en'],
                            ask=lambda _: 'y', write=lambda _: None, connect=lambda *args: MagicMock())
            self.assertEqual(code, 0)
            collect.assert_called_once()
            installer.return_value.install.assert_not_called()

    def test_cancellation_stops_recording(self):
        class Remote:
            def __init__(self): self.commands=[]
            def upload(self,path,data,mode): self.commands.append(json.loads(data))
            def run(self,command): raise KeyboardInterrupt
        with tempfile.TemporaryDirectory() as tmp:
            remote=Remote()
            with self.assertRaises(KeyboardInterrupt):
                diagnostics.collect_home_report(remote,state.Store(tmp),state.target('192.0.2.55', 'no-root'),lambda text:None)
            self.assertEqual(remote.commands[-1]['cmd'],'diagnostics-stop')
