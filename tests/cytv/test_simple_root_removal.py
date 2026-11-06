"""Real host adapter and Store, simulated SSH replies only."""
import json
import shlex
import unittest
from unittest.mock import patch

from cytv.operations import Installer
from cytv.errors import UserError
from tests.cytv import test_operations, clean_removal_fixture


class SimpleRootWire(unittest.TestCase):
    setUp=test_operations.OperationTests.setUp

    def prepare(self):
        self.remote=test_operations.Remote()
        clean_removal_fixture.prepare(self)
        original=self.remote.run
        self.restarted=False
        self.error=None
        def run(command,**kwargs):
            words=shlex.split(command)
            if 'clean-target' in words:
                return json.dumps({'operation':'d'*32,'state':'fresh','target_operation':'e'*32,'target_lease':'f'*32})
            if 'clean-remove' in words:
                self.assertEqual(words[words.index('--operation')+1],'e'*32)
                self.assertEqual(words[words.index('--removal-lease')+1],'f'*32)
                if self.error:raise self.error
                if not self.restarted:
                    return json.dumps({'operation':'e'*32,'state':'recovery_required','stage':'restart-required',
                        'reason':'restart-required','cleanup_boot_id':'11111111-1111-1111-1111-111111111111',
                        'result':{'removed':False,'verified_clean':False,'restart_required':True}})
                return json.dumps({'operation':'e'*32,'state':'complete','stage':'verified-clean','current':True,
                    'result':{'removed':True,'verified_clean':True,'private_cleanup_verified':True}})
            return original(command,**kwargs)
        self.remote.run=run
        return Installer(self.remote,self.store,self.profile,self.payload,self.manifest,lambda _:None)

    def test_restart_pending_then_retry_finishes_without_helper_protocol(self):
        installer=self.prepare()
        first=installer.uninstall(full_project=True)
        self.assertFalse(first['removed']);self.assertTrue(first['restart_required'])
        pending=self.store.pending(self.profile)
        self.assertEqual(pending['product_operation'],'d'*32)
        self.assertEqual(pending['removal_target_operation'],'e'*32)
        self.assertEqual(pending['stage'],'restart-required')
        self.restarted=True
        self.assertTrue(installer.uninstall(full_project=True)['verified_clean'])
        self.assertIsNone(self.store.pending(self.profile))
        self.assertFalse(any('prepareRemoval' in str(call) or '.cytv-lifecycle' in str(call) for call in self.remote.calls))

    def test_connection_loss_keeps_goal_for_normal_retry(self):
        installer=self.prepare();self.error=ConnectionError('closed')
        with self.assertRaises(ConnectionError):installer.uninstall(full_project=True)
        identifier=self.store.pending(self.profile)['removal_operation']
        self.error=None
        self.assertTrue(installer.uninstall(full_project=True)['restart_required'])
        self.assertEqual(self.store.pending(self.profile)['removal_operation'],identifier)

    def test_connection_message_does_not_mislabel_permission_or_vendor_errors(self):
        from cytv.cli import removal_connection_message
        self.prepare();self.store.request_clean_removal(self.profile)
        self.assertIsNone(removal_connection_message(self.store,self.profile,'uninstall',PermissionError()))
        self.assertIsNone(removal_connection_message(self.store,self.profile,'uninstall',RuntimeError('vendor busy')))
        self.assertEqual(removal_connection_message(self.store,self.profile,'uninstall',ConnectionError()),
                         'Connection to the TV was interrupted. Check the connection and try again.')


if __name__=='__main__':unittest.main()
