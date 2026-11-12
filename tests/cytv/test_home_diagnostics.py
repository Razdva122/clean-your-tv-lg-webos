import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from cytv import diagnostics, state
from cytv.errors import TVCommandError, UserError


class HomeDiagnosticsTests(unittest.TestCase):
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
