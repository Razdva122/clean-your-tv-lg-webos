"""Native Home activation records real launches and one verified attempt only."""
import copy
import json
import unittest
from unittest.mock import Mock
from cytv import package, root_activation
from cytv.errors import UserError
from cytv.operations import Installer


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
