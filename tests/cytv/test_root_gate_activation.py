"""Native Home activation records real launches and one verified attempt only."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, call, patch
from cytv import package, root_activation, state
from cytv.errors import UserError
from cytv.operations import Installer
from cytv.recovery import recover
from cytv.terminal import Console


class NativeActivationTests(unittest.TestCase):
    def setUp(self):
        self.tv = Mock()
        self.tv.root_active = Installer.root_active
        self.tv.root_setup_inactive = Installer.root_setup_inactive
        self.tv.store.pending.return_value = dict(action='activate-root', stage='stop-helper', home_backend='c1-native-gate')
        self.tv.remote.run.return_value = 'CYTV_HELPER_IDLE'
        def report(active):
            token = ('a' if active else 'b')*32
            return dict(returnValue=True, result=dict(backend='c1-native-gate', recovery=dict(integrity_verified=True),
                        intent=dict(enabled=active, phase='active' if active else 'disabled', token=token),
                        effective=dict(returnValue=True, backend='c1-native-gate', profiles=None, mounted=active,
                                       stock_verified=not active, healthy=active, stopped=False, token=token,
                                       guardian_pid=123 if active else 0, state='armed' if active else 'stock')))
        self.stock = report(False)
        self.active = report(True)
        self.tv.root_action.side_effect = [self.stock, self.active, self.active, self.active]

    def test_retained_retry_uses_conditioned_enable(self):
        old, new = 'b'*32, 'a'*32
        for report in (self.stock, self.active):
            effective = report['result']['effective']
            effective.update(routing='compositor-keyfilter-v1', mounted=False,
                             filter_installed=effective['healthy'], routing_active=effective['healthy'])
        self.stock['result']['effective'].update(state='stopped', stopped=True, reason='input_expired')
        self.tv.store.pending.return_value.update(stage='enable')
        self.tv.remote.luna.return_value = {'returnValue': True, 'appId': package.ROOT_APP}
        self.assertIs(root_activation.activate(self.tv, retry_token=old), False)
        self.tv.root_action.assert_any_call('enable', retry_token=old)
        self.tv.store.checkpoint.assert_any_call(self.tv.profile, stage='launch', home_token=new)
        self.tv.store.finish.assert_called_once()

    def test_retained_retry_refusal_does_not_restore_a_different_attempt(self):
        self.tv.store.pending.return_value.update(stage='enable')
        self.tv.root_action.side_effect = [self.stock, root_activation.RetryRefused('changed')]
        with self.assertRaises(root_activation.RetryRefused):
            root_activation.activate(self.tv, retry_token='b'*32)
        self.tv.recover_failed_activation.assert_not_called()
        self.tv.store.finish.assert_not_called()

    def test_retained_retry_unknown_enable_requests_only_stock_verification(self):
        self.tv.store.pending.return_value.update(stage='enable')
        self.tv.root_action.side_effect = [self.stock, TimeoutError('lost reply')]
        with self.assertRaises(TimeoutError):
            root_activation.activate(self.tv, retry_token='b'*32)
        self.tv.recover_failed_activation.assert_called_once_with(
            verified_support=True, expected_token=None, stock_only=True)
        self.tv.store.finish.assert_not_called()

    def test_recovery_offers_retained_retry_only_after_proof_and_explicit_confirmation(self):
        self.stock['result']['effective'].update(
            routing='compositor-keyfilter-v1', mounted=False, state='stopped', stopped=True,
            reason='input_expired', filter_installed=False, routing_active=False)
        for scenario in ('retry', 'decline', 'receipt-changed', 'files-changed', 'token-changed', 'escape',
                         'filter-retry', 'filter-decline-restore', 'filter-decline-enable',
                         'filter-not-cleared', 'filter-token-changed'):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as directory:
                store = state.Store(directory)
                profile = state.target('tv.local', 'root')
                remote = Mock()
                remote.run.return_value = '{"stage":"installed-recovery-only"}'
                installer = Installer(remote, store, profile, Path(directory), {}, lambda *_: None)
                store.begin(profile, 'activate-root', stage='enable', home_backend='c1-native-gate',
                            activation_restore='verified', activation_restore_pending=False,
                            requires_updater=False, migrate=False, release_sha='a'*64, bundle_sha='b'*64)
                original = store.pending(profile)
                stock = copy.deepcopy(self.stock)
                filter_left = scenario.startswith('filter-')
                restored = copy.deepcopy(stock)
                if filter_left:
                    stock['result']['effective'].update(stock_verified=False, filter_installed=True)
                    stock['result']['intent']['phase'] = 'recovering'
                if scenario == 'escape':
                    stock['result']['effective']['reason'] = 'escape'
                installer.root_action = Mock(return_value=stock)
                installer.root_files_match = Mock(return_value=True)
                installer._collect_observed_root_diagnostics = Mock()
                installer.stop_root_helper_for_activation = Mock()
                installer.outcome.review_home = Mock()
                staged = []

                def answer(prompt):
                    if 'Restore LG Home?' in prompt:
                        if scenario == 'filter-token-changed':
                            for key in ('effective', 'intent'):
                                stock['result'][key]['token'] = 'c'*32
                        return 'n' if scenario == 'filter-decline-restore' else 'y'
                    if 'Finish Root setup and turn on Home control?' not in prompt:
                        return 'y'
                    staged.append(prompt)
                    if filter_left:
                        restore.assert_called_once_with(installer, 'b'*32, routing_only=True)
                    if scenario in ('decline', 'filter-decline-enable'):
                        return 'n'
                    if scenario == 'files-changed':
                        installer.root_files_match.return_value = False
                    if scenario == 'receipt-changed':
                        store.checkpoint(profile, bundle_sha='c'*64)
                    if scenario == 'token-changed':
                        for key in ('effective', 'intent'):
                            stock['result'][key]['token'] = 'c'*32
                    return 'y'

                if scenario in ('retry', 'filter-retry'):
                    remote.luna.return_value = {'returnValue': True, 'appId': package.ROOT_APP}
                    active = copy.deepcopy(self.active)
                    active['result']['effective'].update(
                        routing='compositor-keyfilter-v1', mounted=False,
                        filter_installed=True, routing_active=True)

                    def action(command, **kwargs):
                        if command == 'enable':
                            self.assertEqual(kwargs, {'retry_token': 'b'*32})
                            installer.root_action.side_effect = None
                            installer.root_action.return_value = active
                            return active
                        return stock

                    installer.root_action.side_effect = action
                def restore_filter(*_args, **_kwargs):
                    if scenario != 'filter-not-cleared':
                        stock.update(restored)

                with patch('cytv.root_install_recovery.restore_activation', side_effect=restore_filter) as restore:
                    if scenario in ('retry', 'decline', 'filter-retry', 'filter-decline-restore', 'filter-decline-enable'):
                        recover(installer, answer, Console(lambda *_: None))
                    else:
                        with self.assertRaises(UserError):
                            recover(installer, answer, Console(lambda *_: None))
                if scenario in ('retry', 'filter-retry'):
                    self.assertIsNone(store.pending(profile))
                    archive, = store.device_dir(profile).glob('recovery-*.json')
                    self.assertEqual(json.loads(archive.read_text())['previous'], original)
                    self.assertEqual(installer.root_action.call_args_list.count(call('enable', retry_token='b'*32)), 1)
                else:
                    self.assertEqual(store.pending(profile), dict(original, bundle_sha='c'*64)
                                     if scenario == 'receipt-changed' else original)
                    self.assertFalse(list(store.device_dir(profile).glob('recovery-*.json')))
                    self.assertTrue(all(request.args == ('status',) for request in installer.root_action.call_args_list))
                self.assertEqual(restore.call_count, int(scenario in ('filter-retry', 'filter-decline-enable', 'filter-not-cleared')))
                self.assertEqual(len(staged), int(scenario not in ('escape', 'filter-decline-restore',
                                                                   'filter-not-cleared', 'filter-token-changed')))
                remote.upload.assert_not_called()

    def test_existing_cytv_foreground_makes_no_launch_request(self):
        self.tv.remote.luna.return_value = {'returnValue':True, 'appId':package.ROOT_APP}
        self.assertIs(root_activation.activate(self.tv), False)
        self.tv.remote.luna.assert_called_once_with('com.webos.applicationManager/getForegroundAppInfo', {}, timeout=5)
        self.tv.outcome.launch_submitted.assert_not_called()
        self.tv.outcome.launch_accepted.assert_not_called()
        self.tv.store.finish.assert_called_once()

    def test_common_entry_uses_the_existing_helper_stop_and_idle_check(self):
        self.tv.stop_root_helper_for_activation = lambda: Installer.stop_root_helper_for_activation(self.tv)
        self.tv.remote.luna.return_value={'returnValue':True, 'appId':package.ROOT_APP}
        self.assertIs(Installer.activate_root(self.tv),False)
        self.tv.stop_helper.assert_called_once()
        self.tv.remote.run.assert_called_once()
        self.tv.helper_retry.assert_not_called()

    def test_escape_during_foreground_read_prevents_launch(self):
        self.tv.root_action.side_effect=[self.stock,self.active,self.stock]
        self.tv.remote.luna.return_value={'returnValue':True,'appId':'com.webos.app.livetv'}
        with self.assertRaises(UserError):root_activation.activate(self.tv)
        self.assertEqual(self.tv.remote.luna.call_count,1)
        self.tv.outcome.launch_submitted.assert_not_called()
        self.tv.store.finish.assert_not_called()

    def test_launch_once_and_check_same_token(self):
        self.tv.remote.luna.side_effect=[{'returnValue':True,'appId':'com.webos.app.livetv'},{'returnValue':True}]
        self.assertIs(root_activation.activate(self.tv), True)
        self.assertEqual(self.tv.remote.luna.call_args_list[-1].args, ('com.webos.applicationManager/launch',{'id':package.ROOT_APP}))
        self.tv.outcome.launch_submitted.assert_called_once()
        self.tv.outcome.launch_accepted.assert_called_once()
        self.tv.store.finish.assert_called_once()

    def test_keyfilter_initial_launch_uses_native_token_barrier(self):
        for report in (self.stock,self.active):
            effective=report['result']['effective']
            effective.update(routing='compositor-keyfilter-v1',mounted=False,
                             filter_installed=effective['healthy'],routing_active=effective['healthy'])
        native=dict(self.active['result']['effective']);native.pop('filter_installed');native.pop('routing_active');native['reason']='none'
        self.tv.remote.run.return_value=json.dumps(native)
        self.tv.remote.luna.return_value={'returnValue':True,'appId':'com.webos.app.livetv'}
        self.assertTrue(root_activation.activate(self.tv))
        self.tv.remote.luna.assert_called_once_with('com.webos.applicationManager/getForegroundAppInfo',{},timeout=5)
        self.tv.remote.run.assert_called_once_with('/var/lib/clean-your-tv-root/runtime/c1-keyfilter-guard --home '+'a'*32,timeout=5)
        self.tv.outcome.launch_accepted.assert_called_once()

    def test_keyfilter_stopped_at_initial_launch_retains_receipt_without_raw_launch(self):
        for report in (self.stock,self.active):
            effective=report['result']['effective']
            effective.update(routing='compositor-keyfilter-v1',mounted=False,
                             filter_installed=effective['healthy'],routing_active=effective['healthy'])
        self.tv.remote.run.return_value='{"returnValue":false,"stopped":true}'
        self.tv.remote.luna.return_value={'returnValue':True,'appId':'com.webos.app.livetv'}
        with self.assertRaises(UserError):root_activation.activate(self.tv)
        self.tv.remote.luna.assert_called_once_with('com.webos.applicationManager/getForegroundAppInfo',{},timeout=5)
        self.tv.outcome.launch_accepted.assert_not_called();self.tv.store.finish.assert_not_called()

    def test_wrong_or_missing_backend_prevents_foreground_calls(self):
        for initial in (True, False):
            with self.subTest(initial=initial):
                wrong=copy.deepcopy(self.stock if initial else self.active)
                wrong['result']['backend']='system-profile'
                self.tv.root_action.side_effect=[wrong] if initial else [self.stock, wrong]
                with self.assertRaises(UserError):root_activation.activate(self.tv)
                self.tv.remote.luna.assert_not_called()
                self.tv.store.finish.assert_not_called()

    def test_malformed_foreground_never_triggers_launch(self):
        for bad in ({'returnValue':True},{'returnValue':False,'appId':'a'},{'returnValue':True,'appId':''}):
            with self.subTest(reply=bad):
                self.tv.remote.luna.reset_mock()
                self.tv.remote.luna.return_value=bad
                self.tv.root_action.side_effect=[self.stock,self.active]
                with self.assertRaises(UserError):root_activation.activate(self.tv)
                self.assertEqual(self.tv.remote.luna.call_count,1)
                self.tv.outcome.launch_submitted.assert_not_called()
                self.tv.store.finish.assert_not_called()

    def test_final_token_change_retains_receipt(self):
        changed=copy.deepcopy(self.active)
        changed['result']['intent']['token']=changed['result']['effective']['token']='f'*32
        self.tv.root_action.side_effect=[self.stock,self.active,changed]
        self.tv.remote.luna.return_value={'returnValue':True,'appId':package.ROOT_APP}
        with self.assertRaises(UserError):root_activation.activate(self.tv)
        self.tv.store.finish.assert_not_called()
        self.tv.outcome.startup_observed.assert_called_with('unverified')

    def test_ambiguous_prior_launch_is_not_repeated(self):
        self.tv.store.pending.return_value['stage']='launch'
        with self.assertRaises(UserError):root_activation.activate(self.tv)
        self.tv.root_action.assert_not_called()

    def test_rejected_launch_is_never_marked_accepted(self):
        self.tv.remote.luna.side_effect=[{'returnValue':True,'appId':'com.webos.app.livetv'},{'returnValue':False}]
        with self.assertRaises(UserError):root_activation.activate(self.tv)
        self.tv.outcome.launch_submitted.assert_called_once()
        self.tv.outcome.launch_accepted.assert_not_called()
        self.tv.store.finish.assert_not_called()


if __name__=='__main__': unittest.main()
