"""Retained Root refusals keep bounded observations in the standard report."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from cytv import diagnostics, operations, state
from cytv.errors import UserError, TVCommandError
from tests.cytv.test_operations import Remote


class RootInspectionDiagnosticsTests(unittest.TestCase):
    def test_doctor_retains_unconfirmed_native_status_without_accepting_it(self):
        device = {
            'backend': 'c1-native-gate',
            'effective': {
                'backend': 'c1-native-gate', 'routing': 'compositor-keyfilter-v1',
                'state': 'stopped', 'healthy': False, 'mounted': False,
                'stopped': True, 'stock_verified': False, 'filter_installed': True,
                'routing_active': False, 'guardian_pid': 0, 'profiles': None,
                'reason': 'explicit_off', 'token': 'PRIVATE',
            },
            'recovery': {'integrity_verified': True, 'path': 'PRIVATE'},
            'intent': {'enabled': False, 'phase': 'off', 'token': 'PRIVATE'},
            'private': 'PRIVATE',
        }
        with tempfile.TemporaryDirectory() as tmp:
            remote = Remote()
            original = remote.run
            def run(command, **kwargs):
                if command.endswith('/deploy.py status'):
                    return json.dumps({'returnValue': True, 'result': device})
                return original(command, **kwargs)
            remote.run = run
            profile = state.target('192.0.2.10', 'root')
            store = state.Store(tmp)
            info = {}
            inst = operations.Installer(remote, store, profile, Path(tmp), {}, tv_info=info)
            inst.native_root_present = Mock(return_value=True)
            with self.assertRaises(UserError) as caught:
                inst.preflight(home_interfaces=True, diagnose=True)
            self.assertEqual(caught.exception.reason_code, 'root-operation-unconfirmed')
            path = diagnostics.create_report(store, 'doctor', profile, 'doctor',
                caught.exception, tv_info=info, status=info.get('status'))
            report = json.loads(path.read_text())
            self.assertEqual(report['status']['native_root']['state'], 'stopped')
            self.assertIs(report['status']['native_root']['filter_installed'], True)
            self.assertIs(report['status']['native_root']['stock_verified'], False)
            self.assertIs(report['status']['recovery_integrity_verified'], True)
            self.assertIsNone(store.pending(profile))
            self.assertFalse(any(c[1].endswith('/deploy.py restore') for c in remote.calls if c[0] == 'run'))
            self.assertNotIn('PRIVATE', json.dumps(report))

    def test_confirmed_native_states_keep_existing_preflight_admission(self):
        for enabled in (False, True):
            with self.subTest(enabled=enabled), tempfile.TemporaryDirectory() as tmp:
                token = 'a' * 32
                device = {
                    'backend': 'c1-native-gate',
                    'effective': {
                        'returnValue': True, 'backend': 'c1-native-gate',
                        'routing': 'compositor-keyfilter-v1', 'profiles': None,
                        'state': 'armed' if enabled else 'stock',
                        'mounted': False, 'healthy': enabled, 'stopped': not enabled,
                        'stock_verified': not enabled, 'filter_installed': enabled,
                        'routing_active': enabled, 'guardian_pid': 42 if enabled else 0,
                        'token': token,
                    },
                    'intent': {'enabled': enabled, 'phase': 'active' if enabled else 'disabled',
                               'token': token},
                    'recovery': {'integrity_verified': True},
                }
                remote = Remote()
                original = remote.run
                def run(command, **kwargs):
                    if command.endswith('/deploy.py status'):
                        return json.dumps({'returnValue': True, 'result': device})
                    return original(command, **kwargs)
                remote.run = run
                inst = operations.Installer(remote, state.Store(tmp),
                    state.target('192.0.2.10', 'root'), Path(tmp), {})
                inst.native_root_present = Mock(return_value=True)
                inst.preflight(home_interfaces=True, diagnose=True)
                self.assertEqual(inst.tv_info['home_backend'], 'c1-native-gate')
                report = diagnostics.context.status_summary(inst.tv_info['status'])
                self.assertIs(report['native_root']['healthy'], enabled)
                self.assertNotIn(token, json.dumps(inst.tv_info))

    def test_new_status_replaces_old_observation_and_failure_clears_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            remote = Remote()
            inst = operations.Installer(remote, state.Store(tmp),
                state.target('192.0.2.10', 'root'), Path(tmp), {})
            inst._selected_python = '/usr/bin/python3'
            replies = [
                {'returnValue': True, 'result': {'backend': 'c1-native-gate',
                    'effective': {'state': phase, 'token': 'PRIVATE'},
                    'recovery': {'integrity_verified': integrity}}}
                for phase, integrity in (('armed', True), ('stopped', False))
            ]
            remote.run = Mock(side_effect=[json.dumps(reply) for reply in replies] + [TVCommandError(1)])
            inst.root_action('status')
            first = diagnostics.context.status_summary(inst.tv_info['status'])
            self.assertEqual(first['native_root']['state'], 'armed')
            inst.root_action('status')
            second = diagnostics.context.status_summary(inst.tv_info['status'])
            self.assertEqual(second['native_root']['state'], 'stopped')
            self.assertIs(second['recovery_integrity_verified'], False)
            self.assertNotIn('PRIVATE', json.dumps(inst.tv_info))
            with self.assertRaises(TVCommandError):
                inst.root_action('status')
            failed = diagnostics.context.status_summary(inst.tv_info['status'])
            self.assertNotIn('native_root', failed)
            self.assertNotIn('recovery_integrity_verified', failed)

    def test_cleanup_tail_refusal_survives_export(self):
        from cytv.diagnostic_context import product_summary
        for code in ('owned-process-still-used', 'runtime-member-changed',
                     'package-absence-unverified', 'cleanup-guard-failed'):
            product = {'protocol': 'clean-removal-v1', 'state': 'recovery_required',
                       'stage': 'private-cleanup', 'reason': 'private-cleanup-incomplete',
                       'cleanup_error': code}
            value = product_summary(product)
            self.assertEqual(value['cleanup_error'], code)
            self.assertEqual(product_summary(value), value)
        self.assertNotIn('PRIVATE', json.dumps(product_summary({'cleanup_error': 'PRIVATE'})))

    def test_native_summary_revalidates_untrusted_values(self):
        from cytv.diagnostic_context import status_summary
        raw = {'backend': 'c1-native-gate', 'effective': {
            'state': 'PRIVATE', 'routing': 'PRIVATE', 'reason': 'PRIVATE',
            'healthy': 'PRIVATE', 'mounted': 1, 'guardian_pid': True,
            'token': 'PRIVATE', 'profiles': {'PRIVATE': 'PRIVATE'},
        }}
        result = status_summary({'device': {'result': raw}})
        self.assertEqual(result['native_root']['state'], 'unknown')
        self.assertEqual(result['native_root']['routing'], 'unknown')
        self.assertNotIn('healthy', result['native_root'])
        self.assertNotIn('mounted', result['native_root'])
        self.assertNotIn('guardian_recorded', result['native_root'])
        self.assertNotIn('PRIVATE', json.dumps(result))
        self.assertEqual(status_summary(result), result)

    def test_inspection_reason_survives_product_export(self):
        from cytv.diagnostic_context import product_summary
        for reason in ('retained_operation', 'component_mismatch', 'verified_clean_removal'):
            raw = {'state': 'recovery_required', 'installation': {
                'state': 'recovery_required', 'reason': reason,
                'can_install': False, 'can_maintain': False,
                'clean_removal_verified': False, 'path': 'PRIVATE',
            }}
            report = product_summary(raw)
            self.assertEqual(report['installation']['reason'], reason)
            self.assertIs(report['installation']['can_install'], False)
            self.assertNotIn('PRIVATE', json.dumps(report))
            self.assertEqual(product_summary(report), report)
        raw['installation'].update(reason='PRIVATE', can_install=1)
        report = product_summary(raw)
        self.assertEqual(report['installation']['reason'], 'unknown')
        self.assertNotIn('can_install', report['installation'])
