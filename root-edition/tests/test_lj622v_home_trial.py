import importlib.util
from contextlib import redirect_stderr
import io
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from threading import Event
import unittest
from unittest.mock import Mock, patch


RUNTIME = Path(__file__).resolve().parents[1] / 'runtime'
sys.path.insert(0, str(RUNTIME))
try:
    spec = importlib.util.spec_from_file_location('lj622v_home_trial', RUNTIME / 'lj622v_home_trial.py')
    trial = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(trial)
finally:
    sys.path.remove(str(RUNTIME))


class RibbonRecoveryTests(unittest.TestCase):
    def test_an_open_ribbon_is_never_toggled(self):
        rpc = Mock(return_value={'homeUIState': [{'uiType': 'home', 'visibility': True}]})
        trial.restore_ribbon(rpc)
        self.assertEqual([call.args[0] for call in rpc.call_args_list], [trial.HOME_STATE])

    def test_a_missing_show_reply_is_followed_by_visibility_readback(self):
        rpc = Mock(side_effect=[
            {'homeUIState': [{'uiType': 'home', 'visibility': False}]},
            TimeoutError(),
            {'homeUIState': [{'uiType': 'home', 'visibility': True}]},
        ])
        trial.restore_ribbon(rpc)
        self.assertEqual([call.args[0] for call in rpc.call_args_list],
                         [trial.HOME_STATE, trial.SHOW_HOME, trial.HOME_STATE])

    def test_unknown_visibility_does_not_trigger_a_toggle(self):
        rpc = Mock(return_value={'homeUIState': []})
        with self.assertRaises(ValueError):
            trial.restore_ribbon(rpc)
        self.assertEqual(rpc.call_count, 1)

    def test_a_toggle_without_visible_readback_is_a_failure(self):
        rpc = Mock(return_value={'homeUIState': [{'uiType': 'home', 'visibility': False}]})
        with patch.object(trial.time, 'monotonic', side_effect=[0, 1]), self.assertRaises(RuntimeError):
            trial.restore_ribbon(rpc)
        self.assertEqual(rpc.call_count, 3)


class AdmissionTests(unittest.TestCase):
    def test_missing_interfaces_registered_app_ribbon_and_input_pair_are_required(self):
        profiles = {'returnValue': False, 'errorCode': -1,
                    'errorText': 'Service does not exist: com.webos.service.systemprofile.'}
        filters = {'returnValue': True, 'configs': {}}
        app = {'appInfo': {'id': trial.CANDIDATE, 'type': 'web', 'version': '0.1.0'}}
        home = {'homeUIState': [{'uiType': 'home', 'visibility': False}]}
        for bad_reply, replies in (
            ('available profiles', [{'returnValue': True}]),
            ('profile access denied', [dict(profiles, errorText='Access denied')]),
            ('configured filters', [profiles, {'returnValue': True, 'configs': {
                'com.webos.surfacemanager.keyFilters': [{}]}}]),
            ('filter access denied', [profiles, {'returnValue': False, 'errorCode': -1}]),
            ('unreadable configs', [profiles, {'returnValue': True}]),
            ('missing app', [profiles, filters, {'appInfo': {}}]),
            ('unknown ribbon state', [profiles, filters, app, {'homeUIState': []}]),
        ):
            with self.subTest(bad_reply=bad_reply):
                probe = Mock()
                with self.assertRaises(ValueError):
                    trial.require_activation(Mock(side_effect=replies), probe)
                probe.assert_not_called()
        rpc = Mock(side_effect=[profiles, filters, app, home])
        probe = Mock(side_effect=RuntimeError('incompatible pair'))
        with self.assertRaisesRegex(RuntimeError, 'incompatible pair'):
            trial.require_activation(rpc, probe)
        probe.assert_called_once_with()
        probe.reset_mock(side_effect=True)
        trial.require_activation(Mock(side_effect=[profiles, filters, app, home]), probe)
        probe.assert_called_once_with()

    def test_admission_timeout_log_does_not_include_remote_payload(self):
        log = io.StringIO()
        rpc = Mock(side_effect=TimeoutError('private reply'))
        with redirect_stderr(log), self.assertRaises(TimeoutError):
            trial.require_activation(rpc, Mock())
        self.assertEqual(json.loads(log.getvalue()), {
            'event': 'root-ribbon-relay', 'stage': 'system-profile-absence', 'result': 'timeout',
        })


class RelayRecoveryTests(unittest.TestCase):
    def test_emergency_releases_input_while_launch_is_in_flight(self):
        with TemporaryDirectory() as directory:
            relay = Path(directory) / 'relay'
            launched = Path(directory) / 'launched'
            released = Path(directory) / 'released'
            relay.write_text(f'#!{sys.executable}\n'
                             'from pathlib import Path\nimport time\n'
                             'print("READY\\nHOME", flush=True)\n'
                             f'while not Path({str(launched)!r}).exists(): time.sleep(.01)\n'
                             f'Path({str(released)!r}).touch()\n'
                             'print("EXIT 27", flush=True)\nraise SystemExit(27)\n')
            relay.chmod(0o700)
            launch_finished = Event()

            def rpc(uri, *_args, **_kwargs):
                if uri == trial.LAUNCH:
                    launched.touch()
                    for _ in range(200):
                        if released.exists():
                            launch_finished.set()
                            raise TimeoutError('Simulated stalled launch')
                        launch_finished.wait(.01)
                    self.fail('Relay did not release input during the launch')
                self.assertTrue(launch_finished.is_set())
                self.assertTrue(released.exists())
                return {'homeUIState': [{'uiType': 'home', 'visibility': True}]}

            self.assertEqual(trial.run_relay(relay, rpc, duration=3), 'Stock Home visible')

    def test_cleanup_failure_does_not_attempt_to_open_stock_home(self):
        with TemporaryDirectory() as directory:
            relay = Path(directory) / 'relay'
            relay.write_text('#!/bin/sh\nprintf "READY\\nEXIT 31\\n"\nexit 31\n')
            relay.chmod(0o700)
            rpc = Mock()
            with self.assertRaisesRegex(RuntimeError, 'status 31'):
                trial.run_relay(relay, rpc, duration=2)
            rpc.assert_not_called()
