"""Original host receipts survive explicit product continuation and cancellation."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from cytv import operations, state, package


class ProductRecoveryTests(unittest.TestCase):
    def test_legacy_support_check_requires_separate_default_no_confirmation(self):
        from cytv.recovery import recover
        from cytv.terminal import Console
        self.store.checkpoint(self.profile,recovery_protocol=None)
        answers=iter(['y',''])
        with patch('cytv.root_passive.collect',return_value={'schema':1,'status':'missing'}):
            recover(self.installer,lambda _:next(answers),Console(lambda _:None))
        self.installer.product_action.assert_not_called()
        self.installer.remote.upload.assert_not_called()

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=state.Store(self.tmp.name);self.profile=state.target('tv.local','root')
        self.store.begin(self.profile,'install',stage='coordinator-submitted',product_operation='a'*32,
                         requires_updater=True,recovery_protocol='root-final-readback-v1')
        self.original=self.store.pending(self.profile)
        self.installer=operations.Installer(Mock(),self.store,self.profile,Path(self.tmp.name),{})
        self.event=dict(operation='a'*32,action='install',state='recovery_required',can_resume=True,
                        resume_reason='original_final_readback_verified')
        self.complete=dict(operation='a'*32,action='install',state='complete',current=True,
            result=dict(installed=package.ROOT_APP,home_changed=False,verified=True,baseline_sha='b'*64))
        self.installer.product_action=Mock(return_value=self.event)
        self.installer.root_action=Mock(return_value={'result':{}})
        self.installer.root_setup_inactive=Mock(return_value=True)
        self.installer.verify_root_updater=Mock()

    def test_explicit_continuation_uses_original_id_and_never_activates_home(self):
        observed=self.installer.observe_recovery()
        self.assertIn('continue-product',observed['assessment']['actions'])
        self.assertEqual(self.store.pending(self.profile),self.original)
        def product(action,operation,**kwargs):
            if kwargs.get('resume'):
                self.assertEqual((action,operation),('install','a'*32))
                return self.complete
            return self.complete if getattr(self,'continued',False) else self.event
        def continuing(action,operation,**kwargs):
            result=product(action,operation,**kwargs)
            if kwargs.get('resume'):self.continued=True
            return result
        self.installer.product_action.side_effect=continuing
        result=self.installer.continue_root_product(self.original)
        self.assertTrue(result['can_resume_root_setup'])
        pending=self.store.pending(self.profile)
        self.assertEqual(pending['baseline_sha'],'b'*64)
        self.assertEqual(pending['product_operation'],'a'*32)
        self.assertEqual(pending['action'],'install')
        history=list(self.store.device_dir(self.profile).glob('recovery-*.json'))
        self.assertEqual(json.loads(history[0].read_text())['previous'],self.original)
        self.installer.remote.luna.assert_not_called()

    def test_changed_proof_refuses_without_submission_or_host_checkpoint(self):
        self.installer.product_action.return_value={**self.event,'can_resume':False}
        with self.assertRaises(RuntimeError):self.installer.continue_root_product(self.original)
        self.assertEqual(self.store.pending(self.profile),self.original)
        self.assertFalse(any(c.kwargs.get('resume') for c in self.installer.product_action.call_args_list))

    def test_setup_refusal_separates_routing_and_baseline_without_mutation(self):
        self.installer.product_action.return_value=self.complete
        self.installer.root_setup_inactive.return_value=False
        result=self.installer.observe_recovery()
        self.assertEqual(result['device']['product']['setup_reason'],'stock-routing-unverified')
        self.installer.root_setup_inactive.return_value=True
        self.installer.verify_root_updater.side_effect=ValueError('PRIVATE')
        result=self.installer.observe_recovery()
        self.assertEqual(result['device']['product']['setup_reason'],'updater-baseline-unverified')
        self.assertEqual(self.store.pending(self.profile),self.original)
        self.installer.remote.luna.assert_not_called()

    def test_complete_receipt_transfers_verified_baseline_before_activation(self):
        self.installer.product_action.return_value=self.complete
        self.installer.activate_root=Mock()
        self.installer.resume_root_setup(expected_pending=self.original)
        self.assertEqual(self.store.pending(self.profile)['baseline_sha'],'b'*64)
        self.assertEqual(self.store.pending(self.profile)['action'],'activate-root')
        self.installer.activate_root.assert_called_once()

    def test_complete_product_can_finish_with_home_off_without_activation(self):
        self.installer.product_action.return_value=self.complete
        self.installer.activate_root=Mock()
        self.installer.finish_root_setup_disabled(expected_pending=self.original)
        self.assertIsNone(self.store.pending(self.profile))
        self.installer.activate_root.assert_not_called()
        records=[json.loads(p.read_text()) for p in self.store.device_dir(self.profile).glob('recovery-*.json')]
        self.assertEqual(records[0]['previous'],self.original)
        self.assertEqual(records[0]['baseline_sha'],'b'*64)

    def test_legacy_passive_observation_does_not_execute_support(self):
        self.store.checkpoint(self.profile,recovery_protocol=None)
        with patch('cytv.root_passive.collect',return_value={'schema':1,'status':'missing'}):
            self.installer.observe_recovery()
        self.installer.product_action.assert_not_called()

    def test_cancellation_rechecks_proof_and_archives_original_only_after_terminal(self):
        proof=dict(operation='a'*32,state='admissible',candidate_sha256='c'*64,
                   proof_sha256='d'*64,code_sha256='e'*64,home_changed=False,lease_terminal=False)
        complete={**proof,'state':'cancelled-and-removed','lease_terminal':True}
        calls=[]
        def invoke(installer,action,pending,proof=None):
            calls.append(action)
            return complete if 'remove' in calls else dict(reviewed)
        reviewed=proof
        with patch('cytv.root_install_recovery.invoke',side_effect=invoke):
            self.installer.cancel_root_product(self.original,proof)
        self.assertEqual(calls,['inspect','remove','inspect'])
        self.assertIsNone(self.store.pending(self.profile))
        record=json.loads(next(self.store.device_dir(self.profile).glob('recovery-*.json')).read_text())
        self.assertEqual(record['previous'],self.original)
        self.assertEqual(record['disposition'],complete)

    def test_changed_cancellation_admission_never_removes(self):
        proof=dict(operation='a'*32,state='admissible',candidate_sha256='c'*64,
                   proof_sha256='d'*64,code_sha256='e'*64,home_changed=False,lease_terminal=False)
        with patch('cytv.root_install_recovery.invoke',return_value={**proof,'proof_sha256':'f'*64}) as invoke:
            with self.assertRaises(RuntimeError):self.installer.cancel_root_product(self.original,proof)
        self.assertEqual([c.args[1] for c in invoke.call_args_list],['inspect'])
        self.assertEqual(self.store.pending(self.profile),self.original)
