import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cytv import state
from cytv.errors import UserError
from cytv.root_runtime import require_idle


class ProfileReconciliation(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.store = state.Store(temp.name)
        self.profile = state.target('192.0.2.55', 'no-root')
        self.other = state.target(self.profile['host'], 'root')
        self.store.save(self.profile)
        self.store.save(self.other)
        self.store.begin(self.other, 'install', stage='pending', failure={'reason': 'old-install-unknown'})
        self.path = self.store.device_dir(self.other) / 'operation.json'
        self.original = self.path.read_bytes()
        timestamp = self.path.stat().st_mtime_ns - 1_000_000_000
        os.utime(self.path, ns=(timestamp, timestamp))
        self.store.request_clean_removal(self.profile)

    def complete(self):
        self.store.checkpoint(self.profile, stage='verified-clean', result={'removed': True, 'verified_clean': True})
        self.store.finish_clean_removal(self.profile)

    def test_completed_no_root_removal_unblocks_other_profile_without_losing_original(self):
        with self.assertRaises(UserError):
            require_idle(self.store, self.profile)
        self.complete()
        require_idle(self.store, self.profile)
        self.assertIsNone(self.store.pending(self.other))
        directory = self.path.parent
        archives = list(directory.glob('operation-superseded-*.json'))
        self.assertEqual([p.read_bytes() for p in archives], [self.original])
        evidence, = directory.glob('superseded-removal-*.json')
        self.assertTrue(json.loads(evidence.read_text())['result']['verified_clean'])
        require_idle(self.store, self.profile)
        self.assertEqual(len(list(directory.glob('operation-superseded-*.json'))), 1)
        self.store.begin(self.profile, 'install')
        self.assertEqual(self.store.pending(self.profile)['action'], 'install')

    def test_installing_via_another_connection_uses_completed_removal(self):
        self.complete()
        selected = state.target(self.profile['host'], 'no-root', 2222)
        self.store.save(selected)
        require_idle(self.store, selected)
        self.assertIsNone(self.store.pending(self.other))

    def test_current_newer_and_foreign_or_specialized_operations_are_preserved(self):
        self.complete()
        self.store.reconcile_removed_profiles(self.profile)
        for profile, action in (
                (self.other, 'install'),
                (state.target('192.0.2.56', 'no-root'), 'install'),
                (state.target(self.profile['host'], 'no-root', 2222), 'enable-system-updates')):
            self.store.save(profile)
            self.store.begin(profile, action)
            before = self.store.pending(profile)
            self.store.reconcile_removed_profiles(self.profile)
            self.assertEqual(self.store.pending(profile), before)
        with self.assertRaises(UserError):
            require_idle(self.store, self.profile)

    def test_equal_timestamp_is_not_treated_as_an_older_operation(self):
        self.complete()
        proof = self.store.device_dir(self.profile) / 'clean-removal.json'
        timestamp = proof.stat().st_mtime_ns
        os.utime(self.path, ns=(timestamp, timestamp))
        with self.assertRaises(UserError):
            require_idle(self.store, self.profile)
        self.assertEqual(self.path.read_bytes(), self.original)

    def test_old_uninstall_is_archived_without_becoming_a_successful_install(self):
        self.store.checkpoint(self.other, action='uninstall')
        self.original = self.path.read_bytes()
        timestamp = self.path.stat().st_mtime_ns - 1_000_000_000
        os.utime(self.path, ns=(timestamp, timestamp))
        self.complete()
        require_idle(self.store, self.profile)
        archive, = self.path.parent.glob('operation-superseded-*.json')
        self.assertEqual(archive.read_bytes(), self.original)
        self.assertFalse((self.path.parent / 'clean-removal.json').exists())

    def assert_submitted_root_uninstall_retained(self, *, wrapped):
        self.store.checkpoint(self.other, action='uninstall', stage='coordinator-submitted',
                              full_project=True, product_operation='a' * 32)
        if wrapped:
            self.store.request_clean_removal(self.other)
        original = self.path.read_bytes()
        timestamp = self.path.stat().st_mtime_ns - 1_000_000_000
        os.utime(self.path, ns=(timestamp, timestamp))
        self.complete()
        with self.assertRaises(UserError) as blocked:
            require_idle(self.store, self.profile)
        self.assertEqual(blocked.exception.reason_code, 'pending-operation')
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(list(self.path.parent.glob('operation-superseded-*')), [])

    def test_other_connection_cannot_retire_submitted_root_uninstall(self):
        self.assert_submitted_root_uninstall_retained(wrapped=False)

    def test_other_connection_cannot_retire_wrapped_submitted_root_uninstall(self):
        self.assert_submitted_root_uninstall_retained(wrapped=True)

    def test_error_archiving_leaves_original_and_retry_recovers(self):
        self.complete()
        original_write = state.private_write
        def fail_archive(path, raw):
            if Path(path).name.startswith('operation-superseded-'):
                raise OSError('fixture failure')
            return original_write(path, raw)
        with patch('cytv.state.private_write', side_effect=fail_archive), self.assertRaises(OSError):
            require_idle(self.store, self.profile)
        self.assertEqual(self.path.read_bytes(), self.original)
        require_idle(self.store, self.profile)
        self.assertIsNone(self.store.pending(self.other))

    def test_unfinished_removal_does_not_clear_another_profile(self):
        self.store.checkpoint(self.profile, stage='restart-required', result={
            'removed': True, 'verified_clean': False, 'restart_required': True})
        with self.assertRaises(UserError):
            require_idle(self.store, self.profile)
        self.assertEqual(self.path.read_bytes(), self.original)

    def test_corrupt_receipt_and_identity_review_stay_blocking(self):
        self.complete()
        self.path.write_bytes(b'{corrupt')
        with self.assertRaises(UserError):
            require_idle(self.store, self.profile)
        self.assertEqual(self.path.read_bytes(), b'{corrupt')
        state.private_write(self.path, self.original)
        # Keep this receipt older than the proof; identity review alone holds it.
        proof = self.store.device_dir(self.profile) / 'clean-removal.json'
        state.private_write(proof, proof.read_bytes())
        state.private_write(self.path.parent / state.SSH_IDENTITY_REVIEW, b'{}')
        with self.assertRaises(UserError):
            require_idle(self.store, self.profile)
        self.assertEqual(self.path.read_bytes(), self.original)

    @unittest.skipIf(os.name == 'nt', 'symlink fixture needs POSIX privileges')
    def test_dangling_identity_review_link_stays_blocking(self):
        self.complete()
        (self.path.parent / state.SSH_IDENTITY_REVIEW).symlink_to('missing-review')
        with self.assertRaises(UserError):
            require_idle(self.store, self.profile)
        self.assertEqual(self.path.read_bytes(), self.original)

    def test_changed_receipt_during_archive_is_retained(self):
        self.complete()
        original_write = state.private_write
        changed = b'{"action":"install","stage":"new-attempt"}'
        def replace_receipt(path, raw):
            original_write(path, raw)
            if Path(path).name.startswith('superseded-removal-'):
                original_write(self.path, changed)
        with patch('cytv.state.private_write', side_effect=replace_receipt), self.assertRaises(UserError):
            require_idle(self.store, self.profile)
        self.assertEqual(self.path.read_bytes(), changed)
        archive, = self.path.parent.glob('operation-superseded-*.json')
        self.assertEqual(archive.read_bytes(), self.original)

    def test_partial_or_tampered_removal_does_not_authorize_archiving(self):
        for result in ({'removed': True}, {'removed':True, 'verified_clean':1},
                       {'removed':True,'verified_clean':True,'restart_required':True}):
            self.store.checkpoint(self.profile, stage='verified-clean', result=result)
            raw = (self.store.device_dir(self.profile) / 'operation.json').read_bytes()
            state.private_write(self.store.device_dir(self.profile) / 'clean-removal.json', raw)
            self.store.finish(self.profile)
            self.store.reconcile_removed_profiles(self.profile)
            self.assertEqual(self.path.read_bytes(), self.original)
            self.store.request_clean_removal(self.profile)


@unittest.skipUnless(os.name != 'nt' and getattr(os, 'getuid', lambda: -1)() == 0
                     and shutil.which('node'), 'exact ownership replay needs Linux root and Node')
class EF950ProfileReplay(unittest.TestCase):
    def test_terminal_empty_tree_reconciles_profiles_with_reported_credentials(self):
        from tests.cytv.test_no_root_simple_removal import SimpleRemoval
        case = SimpleRemoval()
        case.setUp()
        self.addCleanup(case.doCleanups)
        case.store.save(case.profile)
        other = state.target(case.profile['host'], 'root')
        case.store.save(other)
        case.store.begin(other, 'install', stage='setup')
        original = (case.store.device_dir(other) / 'operation.json').read_bytes()
        app = case.cleanup.APPS[0]
        helper = case.root / 'developer/apps/usr/palm/applications' / app
        leaf = helper / 'state'
        leaf.mkdir(parents=True)
        (case.root / 'proc').mkdir()
        case.store.request_clean_removal(case.profile)
        case.store.checkpoint(case.profile, stage='private-cleanup', removals={app: 'terminal'})
        for folder, _, files in os.walk(case.root):
            os.chown(folder, 5755, 5000)
            for name in files:
                os.chown(Path(folder) / name, 5755, 5000)
        for folder, owner in ((helper.parent, (0, 0)), (helper, (0, 0)), (leaf, (5999, 5000))):
            os.chown(folder, *owner)
            folder.chmod(0o775)
        pid = os.fork()
        if pid == 0:
            try:
                os.setgroups([44, 505, 509, 777])
                os.setgid(5000)
                os.setuid(5755)
                self.assertFalse(os.access(helper, os.W_OK))
                self.assertTrue(os.access(leaf, os.W_OK))
                with self.assertRaises(UserError):
                    require_idle(case.store, case.profile)
                result = case.remove()
                self.assertTrue(result['verified_clean'])
                self.assertTrue(result['empty_helper_dirs_retained'])
                self.assertEqual(list(leaf.iterdir()), [])
                self.assertIsNone(case.store.pending(other))
                archive, = case.store.device_dir(other).glob('operation-superseded-*.json')
                self.assertEqual(archive.read_bytes(), original)
                require_idle(case.store, case.profile)
                case.store.begin(case.profile, 'install')
                self.assertEqual(case.store.pending(case.profile)['action'], 'install')
            except BaseException:
                import traceback
                traceback.print_exc()
                os._exit(1)
            os._exit(0)
        _, status = os.waitpid(pid, 0)
        self.assertEqual(os.waitstatus_to_exitcode(status), 0)


if __name__ == '__main__':
    unittest.main()
