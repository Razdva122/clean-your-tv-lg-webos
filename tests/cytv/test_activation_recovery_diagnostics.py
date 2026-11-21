"""Synthetic retained activation evidence; no TV or private reporter records."""
import copy
import json
import unittest
from unittest.mock import MagicMock, patch
import test_activation_recovery as fixture
from cytv import diagnostic_context, diagnostics
from cytv.errors import TVCommandError, UserError
from cytv.recovery import recover
from cytv.terminal import Console


class ActivationDiagnosticTests(unittest.TestCase):
    def setUp(self):
        fixture.ActivationRecoveryTests.setUp(self)

    def observe(self):
        self.installer.root_action = MagicMock(return_value={'returnValue': True, 'result': self.device})
        self.remote.run.return_value = '{"stage":"installed-recovery-only"}'
        return self.installer.observe_recovery()

    def details(self):
        return self.installer.tv_info['root_setup_recovery']

    def eligible(self):
        return self.installer.can_resume_root_setup(self.store.pending(self.profile), self.device)

    def test_first_refusal_records_not_run_without_extra_calls_or_changed_receipt(self):
        self.store.checkpoint(self.profile, updates_ready=False)
        before=self.store.pending(self.profile)
        result=self.observe()
        self.assertFalse(result['can_resume_root_setup'])
        self.assertEqual(result['assessment']['reason'], 'observation-unverified')
        detail=self.details()
        self.assertEqual(detail['reason'], 'receipt-unverified')
        self.assertEqual(detail['checks']['receipt'], 'unverified')
        self.assertTrue(all(value=='not-run' for name,value in detail['checks'].items() if name!='receipt'))
        self.installer.root_files_match.assert_not_called()
        self.installer.product_action.assert_not_called()
        self.installer.verify_root_updater.assert_not_called()
        self.assertEqual(self.remote.run.call_count, 1)
        self.assertEqual(self.store.pending(self.profile), before)

    def test_files_product_updater_and_binding_failures_are_distinct_and_conservative(self):
        cases=(('files', self.installer.root_files_match, False),
               ('product', self.installer.product_action, {'state':'complete','current':False}),
               ('updater', self.installer.verify_root_updater, RuntimeError('PRIVATE')),
               ('binding', self.remote.run, 'PRIVATE'))
        original=[(mock, mock.return_value, mock.side_effect) for _,mock,_ in cases]
        before=self.store.pending(self.profile)
        for stage, mock, result in cases:
            for target, value, error in original:
                target.return_value=value;target.side_effect=error
            if isinstance(result,Exception):mock.side_effect=result
            else:mock.return_value=result
            with self.subTest(stage=stage):
                self.assertFalse(self.eligible())
                self.assertEqual(self.details()['reason'], stage+'-unverified')
                self.assertEqual(self.details()['checks'][stage], 'unverified')
                self.assertNotIn('PRIVATE',json.dumps(self.details()))
                self.assertEqual(self.store.pending(self.profile),before)
        self.remote.upload.assert_not_called()

    def test_restoration_pending_and_success_do_not_reuse_old_failure(self):
        self.store.checkpoint(self.profile, activation_restore_pending=True)
        self.assertFalse(self.eligible())
        self.assertEqual(self.details()['reason'],'restoration-pending')
        self.assertTrue(all(value=='not-run' for value in self.details()['checks'].values()))
        self.store.checkpoint(self.profile, activation_restore_pending=False)
        self.assertTrue(self.eligible())
        self.assertEqual(self.details()['reason'],'verified')
        self.assertTrue(all(value=='verified' for value in self.details()['checks'].values()))
        self.store.finish(self.profile)
        self.installer.root_action=MagicMock(return_value={'returnValue':True,'result':self.device})
        self.remote.run.return_value='{"stage":"installed-recovery-only"}'
        self.installer.native_root_present=MagicMock(return_value=True)
        self.installer.status()
        self.assertNotIn('root_setup_recovery',self.installer.tv_info)

    def test_updater_boundaries_and_transport_unknown_are_not_conflated(self):
        del self.installer.verify_root_updater
        before=self.store.pending(self.profile)
        for reply, reason, updater, baseline in (
            ('CYTV_UPDATER_UNVERIFIED updater','updater-unverified','unverified','not-run'),
            ('CYTV_UPDATER_UNVERIFIED rollback-baseline','rollback-baseline-unverified','verified','unverified'),
            (TVCommandError(1),'updater-unverified','unverified','pending')):
            self.remote.run.side_effect=reply if isinstance(reply,Exception) else None
            self.remote.run.return_value=reply
            with self.subTest(reason=reason):
                self.assertFalse(self.eligible())
                self.assertEqual(self.details()['reason'],reason)
                self.assertEqual(self.details()['checks']['updater'],updater)
                self.assertEqual(self.details()['checks']['rollback-baseline'],baseline)
                self.assertEqual(self.details()['checks']['binding'],'not-run')
                self.assertEqual(self.store.pending(self.profile),before)
        self.remote.run.side_effect=None;self.remote.run.return_value='CYTV_UPDATER_VERIFIED'
        self.remote.luna.return_value={'returnValue':True,'result':{'phase':'verifying'}}
        self.assertFalse(self.eligible())
        self.assertEqual(self.details()['reason'],'updater-transaction-unverified')
        self.assertEqual(self.details()['checks']['rollback-baseline'],'verified')

    def test_report_and_observation_history_revalidate_fixed_fields(self):
        self.store.checkpoint(self.profile, updates_ready=False)
        result=self.observe()
        raw=copy.deepcopy(self.details())
        raw['secret']='PRIVATE';raw['checks']['token']='PRIVATE'
        raw['checks']['binding']={'private':'PRIVATE'}
        self.installer.tv_info['root_setup_recovery']=raw
        report=json.loads(diagnostics.create_report(self.store,'recover',self.profile,'recover',
            UserError('PRIVATE'),self.installer.tv_info,status=result).read_text())
        for value in (report['tv'],report['observation_failure']['tv']):
            self.assertEqual(value['root_setup_recovery']['reason'],'receipt-unverified')
            self.assertEqual(value['root_setup_recovery']['checks']['binding'],'unknown')
        self.assertNotIn('PRIVATE',json.dumps(report))
        hostile=diagnostic_context.tv_summary({'root_setup_recovery':{'reason':{'PRIVATE':True},'checks':{'files':'PRIVATE'}}})
        self.assertNotIn('PRIVATE',json.dumps(hostile))

    def test_recovery_report_keeps_detail_when_generic_blocker_is_raised(self):
        self.store.checkpoint(self.profile, updates_ready=False)
        self.installer.root_action=MagicMock(return_value={'returnValue':True,'result':self.device})
        self.remote.run.return_value='{"stage":"installed-recovery-only"}'
        before=self.store.pending(self.profile)
        with self.assertRaises(UserError):
            recover(self.installer,lambda _: 'y',Console(lambda *_:None))
        report=json.loads(diagnostics.create_report(self.store,'recover',self.profile,'recover',
            UserError('blocked',reason_code='pending-operation'),self.installer.tv_info,
            status=self.installer.tv_info['status']).read_text())
        self.assertEqual(report['tv']['root_setup_recovery']['reason'],'receipt-unverified')
        self.assertEqual(report['recovery']['reason'],'observation-unverified')
        self.assertEqual(self.store.pending(self.profile),before)
        self.remote.upload.assert_not_called()


    def test_failed_activation_restore_exports_stop_step_and_cause(self):
        stock = {'backend': 'c1-native-gate', 'recovery': {'integrity_verified': True},
                 'intent': {'enabled': False}, 'effective': {
                     'returnValue': True, 'backend': 'c1-native-gate', 'profiles': None,
                     'stock_verified': True, 'mounted': False, 'healthy': False, 'guardian_pid': 0}}
        active = {**stock, 'intent': {'enabled': True}}
        def reply(result):
            return {'returnValue': True, 'result': result}
        cases = (
            ([TVCommandError(1)], ['status'], 'initial-status', 'ssh-command-failed', 1),
            ([reply({'recovery': {}})], ['status'], 'initial-status', 'integrity-unverified', None),
            ([reply(active), TVCommandError(2)], ['status', 'restore'], 'restore', 'ssh-command-failed', 2),
            ([reply(active), TVCommandError(-1)], ['status', 'restore'], 'restore', 'ssh-exit-status-missing', None),
            ([reply(active), {}, TVCommandError(3)], ['status', 'restore', 'status'],
             'final-status', 'ssh-command-failed', 3),
            ([reply(active), {}, reply({**stock, 'recovery': {}})], ['status', 'restore', 'status'],
             'final-status', 'integrity-unverified', None),
            ([reply(active), {}, reply(active)], ['status', 'restore', 'status'],
             'final-status', 'stock-home-unverified', None),
            ([json.JSONDecodeError('invalid', 'PRIVATE', 0)], ['status'], 'initial-status', 'invalid-response', None),
        )
        self.store.finish(self.profile)
        self.store.begin(self.profile, 'install', home_backend='c1-native-gate')
        self.store.checkpoint(self.profile, action='activate-root', stage='enable',
                              activation_restore_pending=True, activation_restore='unverified')
        original = self.store.pending(self.profile)
        first = self.report_failure(TVCommandError(7), action='install')
        for replies, calls, step, reason, code in cases:
            with self.subTest(step=step, reason=reason):
                self.installer.root_action = MagicMock(side_effect=replies)
                with self.assertRaises(UserError) as blocker:
                    recover(self.installer, lambda _: 'y', Console(lambda *_: None))
                report = self.report_failure(blocker.exception)
                expected = {'step': step, 'reason': reason}
                if code is not None:
                    expected['exit_status'] = code
                self.assertEqual(report['tv']['root_activation_restore_failure'], expected)
                self.assertEqual(report['observation_failure']['tv']['root_activation_restore_failure'], expected)
                self.assertEqual(report['first_failure']['ssh_command'], first['ssh_command'])
                self.assertNotIn('PRIVATE', json.dumps(report))
                self.assertEqual([call.args[0] for call in self.installer.root_action.call_args_list], calls)
                self.assertEqual(self.store.pending(self.profile), original)

        self.installer.root_action = MagicMock(return_value=reply(stock))
        self.assertTrue(self.installer.recover_failed_activation())
        self.installer.root_action.assert_called_once_with('status')
        self.assertFalse(self.store.pending(self.profile)['activation_restore_pending'])
        self.assertNotIn('root_activation_restore_failure', diagnostic_context.tv_summary(self.installer.tv_info))




    def test_review_restores_retained_c1_using_only_verified_bundle(self):
        from unittest.mock import call
        self.store.checkpoint(self.profile, home_backend='c1-native-gate', stage='enable',
                              activation_restore_pending=True, activation_restore='unverified')
        original = self.store.pending(self.profile)
        token = '1'*32
        old = {'backend': 'c1-native-gate', 'recovery': {'integrity_verified': True},
               'intent': {'enabled': False, 'token': token}, 'effective': {
                   'returnValue': True, 'backend': 'c1-native-gate', 'profiles': None, 'token': token,
                   'routing': 'compositor-keyfilter-v1', 'stopped': True, 'healthy': False,
                   'mounted': False, 'guardian_pid': 0, 'stock_verified': False,
                   'filter_installed': True, 'routing_active': False}}
        current = copy.deepcopy(old)
        current['effective'].update(stock_verified=True, filter_installed=False)
        calls = []

        def retained_runtime(action):
            calls.append(action)
            if action != 'status':
                raise TVCommandError(1)
            return {'result': current if 'verified-restore' in calls else old}

        def verified_bundle(*args, **kwargs):
            calls.append('verified-restore')
            return json.dumps({'returnValue': True, 'result': 'restored',
                               'native_restored_sha256': 'a'*64})

        self.installer.root_action = MagicMock(side_effect=retained_runtime)
        self.installer.observe_recovery = MagicMock(return_value={'device': current})
        self.installer.upload_product = MagicMock(return_value='/tmp/cytv-product-'+'0'*32)
        self.installer.product_action = MagicMock(side_effect=AssertionError('package command'))
        self.installer.uninstall_project = MagicMock(side_effect=AssertionError('package removal'))
        with patch('cytv.root_install_recovery.run', side_effect=verified_bundle) as runner, \
                patch('cytv.package.verify_payload', return_value={}):
            recover(self.installer, lambda _: 'y', Console(lambda *_: None))
        self.assertEqual(calls, ['status', 'verified-restore', 'status'])
        self.assertEqual(self.installer.upload_product.call_args, call(self.installer.payload/'root-c1'))
        stage = self.installer.upload_product.return_value
        self.assertEqual(runner.call_args.args, (self.installer, stage+'/root-updater',
                         'clean_removal.py', [stage+'/root', '--restore-activation', token]))
        self.assertEqual(self.store.pending(self.profile), {
            **original, 'activation_restore_pending': False, 'activation_restore': 'verified'})
        self.installer.product_action.assert_not_called()
        self.installer.uninstall_project.assert_not_called()

        with patch('cytv.root_install_recovery.run', side_effect=AssertionError('already restored')):
            recover(self.installer, lambda _: 'y', Console(lambda *_: None))
        self.installer.upload_product.assert_called_once()
        self.assertEqual(calls[-1], 'status')

    def test_native_restore_failure_survives_ssh_and_report_without_raw_reply(self):
        from cytv.transport import SSH
        self.store.checkpoint(self.profile, stage='enable', activation_restore_pending=True,
                              activation_restore='unverified')
        remote = SSH(MagicMock())
        remote._command_channel = MagicMock()
        state = copy.deepcopy(self.device)
        state['intent']['enabled'] = True
        root_reply = {'returnValue': False, 'error': 'PRIVATE', 'root_restore_failure': {
            'restore_check': 'native-restore-unverified', 'native_reason': 'ui_release_failed',
            'token': 'PRIVATE'}}
        def replies(_channel, _timeout):
            if remote._command_channel.call_count == 1:
                yield json.dumps({'returnValue': True, 'result': state}).encode()
                return
            yield json.dumps(root_reply).encode()
            raise TVCommandError(1)
        remote.chunks = replies
        self.installer.remote = remote
        with self.assertRaises(UserError) as caught:
            recover(self.installer, lambda _: 'y', Console(lambda *_: None))
        report = self.report_failure(caught.exception)
        self.assertNotIn('PRIVATE', json.dumps(report))
        detail = report['tv']['root_activation_restore_failure']
        self.assertEqual(detail, {'step': 'restore', 'reason': 'ssh-command-failed', 'exit_status': 1,
                                  'restore_check': 'native-restore-unverified', 'native_reason': 'ui_release_failed'})
        self.assertEqual(remote._command_channel.call_count, 2)
        self.assertTrue(self.store.pending(self.profile)['activation_restore_pending'])

    def test_activation_restore_transport_failure_preserves_failed_step(self):
        state = copy.deepcopy(self.device)
        state['intent']['enabled'] = True
        self.installer.root_action = MagicMock(side_effect=[
            {'result': state}, TimeoutError('PRIVATE')])
        self.installer.reconnect = MagicMock(side_effect=RuntimeError('PRIVATE'))
        self.assertFalse(self.installer.recover_failed_activation())
        report = self.report_failure(UserError('blocked'))
        self.assertEqual(report['tv']['root_activation_restore_failure'], {
            'step': 'restore', 'reason': 'connection-interrupted', 'reconnect_failed': True})
        self.assertNotIn('PRIVATE', json.dumps(report))
        self.assertEqual([call.args[0] for call in self.installer.root_action.call_args_list],
                         ['status', 'restore'])

    def test_retained_routing_restore_reports_child_stage(self):
        self.installer.observe_recovery = MagicMock()
        self.installer.retained_activation_token = MagicMock(return_value='a'*32)
        error = TVCommandError(1)
        error.root_restore_failure = {'restore_check': 'stock-destination-unverified',
                                      'destination_check': 'home-missing', 'raw': 'PRIVATE'}
        with patch('cytv.root_install_recovery.restore_activation', side_effect=error), \
                self.assertRaises(TVCommandError) as caught:
            self.installer.restore_retained_activation_routing(self.store.pending(self.profile), 'a'*32)
        report = self.report_failure(caught.exception)
        self.assertEqual(report['tv']['root_activation_restore_failure'], {
            'step': 'restore', 'reason': 'ssh-command-failed', 'exit_status': 1,
            'restore_check': 'stock-destination-unverified', 'destination_check': 'home-missing'})
        self.assertNotIn('PRIVATE', json.dumps(report))

    def test_failed_retry_attempt_proof_stays_out_of_reports(self):
        from cytv.transport import SSH

        old, new = 'b'*32, 'a'*32
        remote = SSH(MagicMock())
        remote._command_channel = MagicMock()

        def replies(_channel, _timeout):
            yield json.dumps({'returnValue': False, 'retained_retry_attempt': [old, new]}).encode()
            raise TVCommandError(1)

        remote.chunks = replies
        with self.assertRaises(TVCommandError) as failed:
            remote.run('enable')
        self.assertEqual(failed.exception._retained_retry_attempt, (old, new))
        report = json.dumps(self.report_failure(failed.exception))
        self.assertNotIn(old, report)
        self.assertNotIn(new, report)

    def report_failure(self, error, action='recover'):
        return json.loads(diagnostics.create_report(self.store, action, self.profile, action,
            error, self.installer.tv_info).read_text())

    def test_activation_restore_detail_rejects_unbounded_values(self):
        raw = {'step': 'restore', 'reason': 'ssh-command-failed', 'exit_status': 1024,
               'error': 'PRIVATE'}
        summary = diagnostic_context.tv_summary({'root_activation_restore_failure': raw})
        self.assertEqual(summary['root_activation_restore_failure'],
                         {'step': 'restore', 'reason': 'ssh-command-failed'})
        raw.update(step={'PRIVATE': True}, reason='PRIVATE')
        self.assertNotIn('PRIVATE', json.dumps(diagnostic_context.tv_summary(
            {'root_activation_restore_failure': raw})))

    def test_embedded_updater_probe_classifies_real_check_failures_without_text(self):
        import contextlib
        import hashlib
        import io
        from pathlib import Path
        import shlex
        import sys
        import types
        del self.installer.verify_root_updater
        self.remote.run.return_value='CYTV_UPDATER_VERIFIED'
        self.remote.luna.return_value={'returnValue':True,'result':None}
        self.installer.verify_root_updater('a'*64)
        words=shlex.split(self.remote.run.call_args.args[0])
        program=words[words.index('-c')+1]
        digest=hashlib.sha256(b'cache').hexdigest()
        for failure in ('integrity','bootstrap','baseline','cache','package','storage-full',None):
            visited=[]
            def integrity():
                visited.append('integrity')
                if failure=='integrity':raise ValueError('PRIVATE')
                if failure=='storage-full':raise OSError(__import__('errno').ENOSPC,'PRIVATE')
            def read(name):
                visited.append(name)
                return ({'phase':'pending' if failure=='bootstrap' else 'complete'} if name=='bootstrap'
                        else {'sha256':'a'*64 if failure=='baseline' else digest})
            def safe_bytes(*args,**kwargs):
                visited.append('cache')
                return b'changed' if failure=='cache' else b'cache'
            def inspect(*args):
                visited.append('package')
                if failure=='package':raise ValueError('PRIVATE')
            modules={name:types.ModuleType(name) for name in ('updater','updater.device','updater.store','updater.package')}
            modules['updater.device'].STATE=Path('/synthetic')
            modules['updater.device'].Device=lambda store:types.SimpleNamespace(integrity=integrity)
            modules['updater.store'].Store=lambda path:types.SimpleNamespace(read=read)
            modules['updater.package'].safe_bytes=safe_bytes
            modules['updater.package'].inspect_package=inspect
            output=io.StringIO()
            with self.subTest(failure=failure), patch.dict(sys.modules,modules), patch.object(sys,'argv',['probe',digest]), patch.object(sys,'path',list(sys.path)), contextlib.redirect_stdout(output):
                if failure=='storage-full':
                    with self.assertRaises(OSError):
                        exec(compile(program,'<synthetic-updater-probe>','exec'),{'__name__':'__main__'})
                    self.assertEqual(output.getvalue(),'')
                    continue
                exec(compile(program,'<synthetic-updater-probe>','exec'),{'__name__':'__main__'})
            expected=('CYTV_UPDATER_VERIFIED' if failure is None else
                      'CYTV_UPDATER_UNVERIFIED '+('updater' if failure in ('integrity','bootstrap') else 'rollback-baseline'))
            self.assertEqual(output.getvalue().strip(),expected)
            if failure in ('integrity','bootstrap'):self.assertNotIn('current',visited)
            if failure=='baseline':self.assertNotIn('cache',visited)
            if failure=='cache':self.assertNotIn('package',visited)

    def test_absent_product_operation_still_uses_original_optional_gate(self):
        self.store.checkpoint(self.profile,product_operation=None)
        self.assertTrue(self.eligible())
        self.assertEqual(self.details()['checks']['product'],'not-required')
        self.installer.product_action.assert_not_called()

    def test_python_selection_failure_does_not_claim_remote_baseline_was_submitted(self):
        del self.installer.verify_root_updater
        self.installer._python=MagicMock(side_effect=RuntimeError('PRIVATE'))
        self.assertFalse(self.eligible())
        self.assertEqual(self.details()['checks']['updater'],'unverified')
        self.assertEqual(self.details()['checks']['rollback-baseline'],'not-run')
        self.remote.run.assert_not_called()
