"""A successful No-root successor must be removable with its existing Root SSH."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from cytv.errors import UserError
from cytv.operations import Installer
from cytv.state import Store,target


class InertRootRemoval(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name).resolve();self.store=Store(self.path/'store')
        self.profile=target('tv.local','no-root',22,connection='root-ssh')
        self.installer=Installer(Mock(root=True),self.store,self.profile,self.path,{},progress=lambda message:None)
        self.stamp=dict(lease='a'*32,operation='b'*32,node='20.12.2')
        self.complete=dict(state='complete',stage='verified-clean',current=True,
            result=dict(removed=True,private_cleanup_verified=True))
        self.denied=UserError('Some project files require Root access.',reason_code='root-access-required')

    def test_completed_successor_uses_shared_root_cleanup_with_same_goal(self):
        with patch('cytv.no_root_cleanup.continue_removal',side_effect=self.denied), \
             patch('cytv.root_no_root_handoff.cleanup_target',return_value=self.stamp,create=True), \
             patch('cytv.root_clean_tail.resume',return_value=self.complete):
            result=self.installer.uninstall(full_project=True)
        self.assertTrue(result['verified_clean']);self.assertIsNone(self.store.pending(self.profile))
        saved=json.loads((self.store.device_dir(self.profile)/'clean-removal.json').read_text())
        self.assertEqual(saved['root_cleanup_lease'],self.stamp['lease'])
        self.assertNotEqual(saved['product_operation'],self.stamp['operation'])
        self.assertEqual(saved['product_operation'],saved['removal_operation'])

    def test_real_or_unverified_root_still_requires_root_workflow(self):
        with patch('cytv.no_root_cleanup.continue_removal',side_effect=self.denied), \
             patch('cytv.root_no_root_handoff.cleanup_target',side_effect=UserError('Unverified'),create=True), \
             patch('cytv.root_clean_tail.resume') as tail:
            with self.assertRaises(UserError) as caught:self.installer.uninstall(full_project=True)
        self.assertEqual(caught.exception.reason_code,'root-access-required')
        self.assertEqual(self.store.pending(self.profile)['removal_reason'],'root-access-required')
        tail.assert_not_called()

    def test_original_lease_is_not_replaced_by_current_clean_target(self):
        self.installer.native_root_present=Mock(return_value=False)
        self.installer.upload_product=Mock(return_value='/tmp/cytv-product-'+'d'*32)
        def query(action,operation,payload,**kwargs):
            self.assertEqual(action,'clean-target')
            return dict(target_operation=operation,target_lease='c'*32,target_removal=None)
        self.installer.product_action=Mock(side_effect=query)
        with patch('cytv.no_root_cleanup.continue_removal',side_effect=self.denied), \
             patch('cytv.root_no_root_handoff.cleanup_target',return_value=self.stamp,create=True), \
             patch('cytv.root_clean_tail.resume',return_value=None):
            with self.assertRaises(UserError):self.installer.uninstall(full_project=True)
        saved=self.store.pending(self.profile)
        self.assertEqual(saved.get('root_cleanup_lease'),self.stamp['lease'])
        self.assertEqual(saved['product_operation'],saved['removal_operation'])
        self.assertEqual(self.installer.product_action.call_count,1)

    def test_legacy_successor_uses_verified_beta_cleanup_and_restores_host_payload(self):
        nested=self.path/'legacy-root-beta';nested.mkdir();(nested/'fixture').write_bytes(b'x')
        digest=hashlib.sha256(b'x').hexdigest()
        (nested/'payload.json').write_text(json.dumps(dict(runtime_variant='node012-beta',files={'fixture':digest})))
        self.installer.manifest=dict(legacy_root_beta='legacy-root-beta',files={'legacy-root-beta/fixture':digest})
        original=self.installer.manifest
        def tail(installer,pending):
            self.assertEqual(installer.payload,nested)
            self.assertEqual(installer.manifest['runtime_variant'],'node012-beta')
            return self.complete
        with patch('cytv.no_root_cleanup.continue_removal',side_effect=self.denied), \
             patch('cytv.root_no_root_handoff.cleanup_target',return_value=dict(self.stamp,node='0.12.2'),create=True), \
             patch('cytv.root_clean_tail.resume',side_effect=tail):
            self.assertTrue(self.installer.uninstall(full_project=True)['verified_clean'])
        self.assertEqual(self.installer.payload,self.path)
        self.assertIs(self.installer.manifest,original)

    def test_same_lease_with_another_removal_goal_is_not_adopted(self):
        self.installer.native_root_present=Mock(return_value=False)
        self.installer.upload_product=Mock(return_value='/tmp/cytv-product-'+'d'*32)
        def query(action,operation,payload,**kwargs):
            self.assertEqual(action,'clean-target','No destructive request may follow a foreign target')
            return dict(target_operation='e'*32,target_lease=self.stamp['lease'],target_removal='f'*32)
        self.installer.product_action=Mock(side_effect=query)
        with patch('cytv.no_root_cleanup.continue_removal',side_effect=self.denied), \
             patch('cytv.root_no_root_handoff.cleanup_target',return_value=self.stamp), \
             patch('cytv.root_clean_tail.resume',return_value=None):
            with self.assertRaises(UserError):self.installer.uninstall(full_project=True)
        pending=self.store.pending(self.profile)
        self.assertNotEqual(pending.get('removal_target_intent'),'f'*32)
        self.assertEqual(self.installer.product_action.call_count,1)
