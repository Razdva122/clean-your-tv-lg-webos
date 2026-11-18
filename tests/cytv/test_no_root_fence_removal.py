"""Verify admission and request ownership during No-root removal."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import Mock, patch

from cytv.errors import TVRejected, UserError
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


@unittest.skipIf(os.name == 'nt' or not shutil.which('node'), 'POSIX TV filesystem model requires Node')
class VendorRemoval(unittest.TestCase):
    def setUp(self):
        from tests.cytv import test_no_root_simple_removal as fixture

        self.case = fixture.SimpleRemoval()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.case.installer.tv_info = {}
        (self.case.root / 'proc').mkdir()
        self.app = self.case.cleanup.APPS[1]
        self.case.remote.apps.add(self.app)

    def test_timeout_refreshes_original_vendor_request_without_resubmitting(self):
        from cytv.recovery import recover

        remote = self.case.remote
        original = remote.luna
        state = 'busy'

        def luna(uri, payload, **options):
            if uri.endswith('/dev/remove'):
                remote.calls.append((uri, payload))
                raise UserError('TV operation timed out. Run cytv status before retrying.',
                                reason_code='operation-timeout')
            if uri.endswith('/status'):
                if state == 'busy':
                    remote.calls.append((uri, payload))
                    return {'returnValue': True, 'status': {'apps': [self.app]}}
                if state == 'denied':
                    raise TVRejected('Denied', {'returnValue': False, 'errorCode': -1}, uri)
            return original(uri, payload, **options)

        remote.luna = luna
        store, profile = self.case.store, self.case.profile
        goal = store.request_clean_removal(profile)['removal_operation']
        with self.assertRaises(UserError) as timeout:
            self.case.remove()
        self.assertEqual(timeout.exception.reason_code, 'operation-timeout')
        pending = store.pending(profile)
        self.assertEqual(pending['removals'], {self.app: 'submitted'})
        self.assertEqual(pending.get('removal_failure_phase'), 'removal-terminal-unknown')
        before = len(remote.calls)
        for _ in range(2):
            observation = self.case.installer.status()
            self.assertEqual(observation['assessment'],
                             {'state': 'waiting', 'reason': 'original-writer-active',
                              'actions': ['check', 'retain-evidence']})
            self.assertEqual(store.pending(profile), pending)
        self.assertEqual([uri for uri, _ in remote.calls[before:]], ['com.webos.appInstallService/status'] * 2)

        write, ask = Mock(), Mock()
        recover(self.case.installer, ask, write, review_confirmed=True)
        ask.assert_not_called()
        plan = write.recovery_plan.call_args.args[0]
        self.assertEqual(plan['state'], 'waiting')
        self.assertEqual(plan['removal_action']['action'], 'check')

        state = 'denied'
        self.assertIn('continue-removal', self.case.installer.status()['assessment']['actions'])
        self.assertEqual(store.pending(profile), pending)
        self.assertTrue(self.case.remove()['restart_required'])
        pending = store.pending(profile)
        state = 'busy'
        recover(self.case.installer, ask, write, review_confirmed=True)
        plan = write.recovery_plan.call_args.args[0]
        self.assertEqual(plan['removal']['reason'], 'original-writer-active')
        self.assertEqual(plan['removal_action']['action'], 'check')
        self.assertEqual(store.pending(profile), pending)

        # The same vendor request finishes after the transport timeout.
        state = 'idle'
        remote.apps.remove(self.app)
        self.assertIn('continue-removal', self.case.installer.status()['assessment']['actions'])
        self.assertEqual(store.pending(profile), pending)
        self.assertTrue(self.case.remove()['verified_clean'])
        self.assertEqual(self.case.vendor_removals(), [self.app])
        completed = json.loads((store.device_dir(profile) / 'clean-removal.json').read_text())
        self.assertEqual(completed['removal_operation'], goal)

    def test_acceptance_reply_requires_a_terminal_and_rejection_names_removal(self):
        from cytv.transport import LunaReplyUnconfirmed, SSH

        remote = self.case.remote
        original = remote.luna
        ssh = object.__new__(SSH)
        ssh.root = False
        ssh.channel = Mock()
        ssh.chunks = Mock()
        accepted = b'{"returnValue":true,"details":{"state":"removing"}}'

        def luna(uri, payload, **options):
            return ssh.luna(uri, payload, **options) if uri.endswith('/dev/remove') else original(uri, payload, **options)

        remote.luna = luna
        store, profile = self.case.store, self.case.profile
        goal = store.request_clean_removal(profile)['removal_operation']
        ssh.chunks.return_value = iter((accepted, b'{"returnValue":false,"errorCode":-102}'))
        with self.assertRaisesRegex(TVRejected, 'The TV rejected removal') as rejected:
            self.case.remove()
        self.assertEqual(rejected.exception.luna['operation'], 'package-remove')
        self.assertEqual(store.pending(profile)['removals'], {})

        ssh.chunks.return_value = iter((accepted,))
        with self.assertRaises(LunaReplyUnconfirmed):
            self.case.remove()
        pending = store.pending(profile)
        self.assertEqual(pending['removals'], {self.app: 'submitted'})
        self.assertEqual(pending.get('removal_failure_phase'), 'removal-terminal-unknown')
        self.assertEqual(pending['removal_operation'], goal)

    def test_delayed_terminal_reply_completes_the_original_vendor_call(self):
        from cytv.transport import SSH

        remote = self.case.remote
        original = remote.luna
        ssh = object.__new__(SSH)
        ssh.root = False
        ssh.channel = Mock()
        store, profile = self.case.store, self.case.profile
        goal = store.request_clean_removal(profile)['removal_operation']

        def replies(channel, timeout):
            yield b'{"returnValue":true,"details":{"state":"removing"}}'
            self.assertEqual(store.pending(profile)['removals'], {self.app: 'submitted'})
            remote.apps.remove(self.app)
            yield b'{"returnValue":true,"details":{"state":"removed"}}'

        def luna(uri, payload, **options):
            return ssh.luna(uri, payload, **options) if uri.endswith('/dev/remove') else original(uri, payload, **options)

        ssh.chunks = replies
        remote.luna = luna
        self.assertTrue(self.case.remove()['verified_clean'])
        self.assertEqual(ssh.channel.call_count, 1)
        completed = json.loads((store.device_dir(profile) / 'clean-removal.json').read_text())
        self.assertEqual(completed['removal_operation'], goal)
