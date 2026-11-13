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
                return json.dumps({'operation':words[words.index('--operation')+1],'state':'fresh','target_operation':'e'*32,'target_lease':'f'*32})
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

    def test_saved_transport_failure_keeps_only_evidence_supported_by_ssh(self):
        import errno
        from paramiko.ssh_exception import NoValidConnectionsError, SSHException
        from cytv.desktop import DesktopConsole
        from cytv.recovery import removal_plan

        installer = self.prepare()
        events = []
        write = DesktopConsole(lambda kind, value: events.append((kind, value)))
        cases = [
            (TimeoutError('PRIVATE'), 'connection-interrupted', 'transient'),
            (SSHException('PRIVATE'), 'connection-unverified', 'unverified'),
            (NoValidConnectionsError({
                ('192.0.2.10',22): PermissionError(errno.EACCES, 'PRIVATE'),
                ('192.0.2.11',22): ConnectionRefusedError(errno.ECONNREFUSED, 'PRIVATE'),
            }), 'connection-unverified', 'unverified'),
        ]
        for error, reason, condition in cases:
            with self.subTest(error=type(error)):
                self.error = error
                with self.assertRaises(type(error)):
                    installer.uninstall(full_project=True)
                self.assertEqual(self.store.pending(self.profile)['removal_reason'], reason)
                removal_plan(write, self.store, self.profile)
                result = [value for kind, value in events if kind == 'recovery-plan'][-1]
                self.assertEqual(result['removal_action']['condition'], condition)
                self.assertNotIn('PRIVATE', str(events))

    def test_cleanup_reconnect_authentication_preserves_connection_guidance(self):
        from paramiko.ssh_exception import AuthenticationException
        from cytv.desktop import DesktopConsole
        from cytv.failure_help import for_error
        from cytv.recovery import recover

        installer = self.prepare()
        self.store.request_clean_removal(self.profile)
        self.error = ConnectionError('PRIVATE')
        def reconnect():
            raise AuthenticationException('PRIVATE')
        installer.reconnect = reconnect
        events = []
        write = DesktopConsole(lambda kind, value: events.append((kind, value)))
        with patch('cytv.operations.sleep'), self.assertRaises(AuthenticationException) as error:
            recover(installer, lambda _: 'y', write)
        result = [value for kind, value in events if kind == 'recovery-plan'][-1]
        self.assertEqual(result['removal_action']['condition'], 'unverified')
        self.assertIs(result['connection_failure'], True)
        self.assertIn('SSH', result['next_step'])
        self.assertNotIn('PRIVATE', str(events))
        pending = self.store.pending(self.profile)
        self.assertEqual(pending['removal_reason'], 'connection-unverified')
        self.assertEqual(for_error(error.exception, 'recover', self.profile, pending)['code'], 'ssh-auth-root')

    def test_final_tail_live_process_requests_restart_instead_of_generic_cleanup_error(self):
        installer=self.prepare()
        reply={'state':'recovery_required','stage':'private-cleanup','current':False,
               'reason':'private-cleanup-incomplete','cleanup_error':'owned-process-still-used',
               'restart_required':True}
        with patch('cytv.root_clean_tail.resume',return_value=reply):
            result=installer.uninstall(full_project=True)
        self.assertTrue(result['restart_required'])
        self.assertFalse(result['verified_clean'])
        self.assertEqual(self.store.pending(self.profile)['removal_reason'],'restart-required')

        reply['restart_required']=False
        with patch('cytv.root_clean_tail.resume',return_value=reply):
            with self.assertRaises(UserError) as error:
                installer.uninstall(full_project=True)
        self.assertEqual(error.exception.reason_code,'cleanup-check-failed')
        self.assertEqual(self.store.pending(self.profile)['stage'],'private-cleanup')

    def test_tail_boot_retry_cannot_adopt_another_removal_intent(self):
        installer=self.prepare()
        installer.uninstall(full_project=True)
        pending=self.store.pending(self.profile)
        with patch('cytv.root_clean_tail.resume',return_value={'recheck_boot':True}), \
             patch.object(installer,'product_action',return_value={
                 'target_operation':pending['removal_target_operation'],
                 'target_removal':'a'*32,'target_lease':pending['removal_target_lease'],
             }) as product:
            with self.assertRaisesRegex(UserError,'Removal evidence changed'):
                installer.uninstall(full_project=True)
        self.assertEqual(product.call_count,1)
        self.assertEqual(product.call_args.args[0],'clean-target')
        self.assertEqual(self.store.pending(self.profile)['removal_target_intent'],pending['removal_target_intent'])

    def test_completed_cleanup_invalidates_retired_support_and_python_cache(self):
        installer=self.prepare();self.restarted=True
        installer._coordinator_code='/tmp/retired-coordinator'
        installer._recovery_code='/tmp/retired-recovery'
        installer._selected_python='/var/lib/clean-your-tv-python/retired/bin/python'
        installer.uninstall(full_project=True)
        for field in ('_coordinator_code','_recovery_code','_selected_python'):
            self.assertIsNone(getattr(installer,field,None))

    def test_pre_journal_native_pending_selects_current_native_support_for_explicit_cleanup(self):
        import shutil
        installer=self.prepare()
        self.store.finish(self.profile)
        self.store.begin(self.profile,'install',stage='setup',home_backend='c1-native-gate')
        original=self.store.pending(self.profile)
        shutil.copytree(self.payload/'root',self.payload/'root-c1')
        with patch.object(installer,'native_root_present',return_value=False),patch.object(installer,'upload_product',wraps=installer.upload_product) as upload:
            installer.uninstall(full_project=True)
        self.assertEqual(upload.call_args.args[0],self.payload/'root-c1')
        self.assertEqual(self.store.pending(self.profile)['previous'],original)

    def test_connection_message_does_not_mislabel_permission_or_vendor_errors(self):
        from cytv.cli import removal_connection_message
        self.prepare();self.store.request_clean_removal(self.profile)
        self.assertIsNone(removal_connection_message(self.store,self.profile,'uninstall',PermissionError()))
        self.assertIsNone(removal_connection_message(self.store,self.profile,'uninstall',RuntimeError('vendor busy')))
        self.assertEqual(removal_connection_message(self.store,self.profile,'uninstall',ConnectionError()),
                         'Connection to the TV was interrupted. Check the connection and try again.')


if __name__=='__main__':unittest.main()
