"""Local recovery refusals remain distinct, private and non-authorizing."""
import hashlib
import errno
import json
import os
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from cytv import cli, diagnostics, diagnostic_context, no_root_observer as observer
from cytv.errors import UserError, LocalRecoveryError
from cytv.state import Store, target


class LocalRecoveryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.store = Store(self.root / 'PRIVATE-DATA')
        self.profile = target('test-tv', 'no-root')
        self.operation = 'a' * 32

    def saved(self):
        self.store.begin(self.profile, 'install', recovery_protocol=observer.PROTOCOL,
                         observer_operation=self.operation)
        digest = self.store.save_capsule(self.profile, self.operation, {'original': True})
        self.store.checkpoint(self.profile, capsule_sha256=digest)
        return digest, self.store.device_dir(self.profile) / ('capsule-' + self.operation + '.json')

    @unittest.skipUnless(os.name == 'posix', 'POSIX ownership/permissions')
    def test_unsafe_ancestor_reports_permissions_without_claiming_data_loss(self):
        digest, capsule = self.saved()
        original = capsule.read_bytes()
        pending = self.store.pending(self.profile)
        first = json.loads(diagnostics.create_report(self.store, 'install', self.profile,
                                                     'install-packages', UserError('Original setup failed.')).read_text())
        self.store.root.chmod(0o770)
        with self.assertRaises(UserError) as caught:
            self.store.read_capsule(self.profile, self.operation, digest)
        error = caught.exception
        self.assertEqual(error.local_recovery, {'reason': 'directory-permissions',
                         'location': 'ancestor', 'mode': '0770',
                         'owner': 'root' if os.getuid() == 0 else 'current-user'})
        self.assertNotIn('missing or changed', str(error))
        report = json.loads(diagnostics.create_report(self.store, 'status', self.profile, 'status', error).read_text())
        self.assertEqual(report['local_recovery'], error.local_recovery)
        self.assertEqual(report['observation_failure']['local_recovery'], error.local_recovery)
        self.assertEqual(report['first_failure'], first['first_failure'])
        self.assertNotIn('PRIVATE-DATA', json.dumps(report))
        self.assertEqual(capsule.read_bytes(), original)
        self.assertEqual(self.store.pending(self.profile), pending)

    def test_missing_and_changed_capsules_have_distinct_reasons(self):
        digest, capsule = self.saved()
        original = capsule.read_bytes()
        for reason, raw in [('capsule-missing', None), ('capsule-changed', b'{}'),
                            ('capsule-invalid', b'not-json')]:
            with self.subTest(reason=reason):
                if raw is None:
                    capsule.unlink()
                else:
                    capsule.write_bytes(raw)
                    capsule.chmod(0o600)
                expected_digest = hashlib.sha256(raw).hexdigest() if reason == 'capsule-invalid' else digest
                with self.assertRaises(UserError) as caught:
                    self.store.read_capsule(self.profile, self.operation, expected_digest)
                self.assertEqual(caught.exception.local_recovery['reason'], reason)
                self.assertIsNotNone(self.store.pending(self.profile))
        capsule.write_bytes(original)

    @unittest.skipUnless(os.name == 'posix', 'POSIX ownership/permissions')
    def test_local_storage_refusal_happens_before_pending_and_remote_check(self):
        self.store.device_dir(self.profile)
        self.store.root.chmod(0o770)
        installer = SimpleNamespace(store=self.store, profile=self.profile, remote=Mock())
        with patch.object(observer, 'invoke', return_value={}) as invoke:
            with self.assertRaises(UserError):
                observer.begin(installer, 'install', {'helper.ipk': b'helper', 'launcher.ipk': b'home'},
                               dict(zip(observer.APPS, ['1', '2'])), {}, {})
        self.assertIsNone(self.store.pending(self.profile))
        self.assertFalse(list(self.store.device_dir(self.profile).glob('capsule-*.json')))
        invoke.assert_not_called()
        installer.remote.run.assert_not_called()

    @unittest.skipUnless(os.name == 'posix', 'POSIX ownership/permissions')
    def test_foreign_owner_is_reported_without_its_uid_or_path(self):
        digest, capsule = self.saved()
        mode = format(self.store.root.stat().st_mode & 0o7777, '04o')
        original_stat = Path.lstat
        def metadata(path):
            info = original_stat(path)
            if path == self.store.root:
                return SimpleNamespace(st_mode=info.st_mode, st_uid=os.getuid() + 12345)
            return info
        with patch.object(Path, 'lstat', metadata):
            with self.assertRaises(UserError) as caught:
                self.store.read_capsule(self.profile, self.operation, digest)
        self.assertEqual(caught.exception.local_recovery,
                         {'reason': 'directory-owner', 'location': 'ancestor', 'mode': mode, 'owner': 'other'})
        self.assertTrue(capsule.exists())

    def test_local_storage_io_refusal_does_not_create_pending(self):
        installer = SimpleNamespace(store=self.store, profile=self.profile, remote=Mock())
        with patch('cytv.state.tempfile.TemporaryFile', side_effect=OSError('PRIVATE-DATA')), \
             patch.object(observer, 'invoke', return_value={}) as invoke:
            with self.assertRaises(UserError) as caught:
                observer.begin(installer, 'remove', {}, {}, {}, {})
        self.assertEqual(caught.exception.local_recovery['reason'], 'storage-unavailable')
        self.assertIsNone(self.store.pending(self.profile))
        invoke.assert_not_called()

    def test_full_local_disk_keeps_computer_storage_guidance(self):
        with patch('cytv.state.tempfile.TemporaryFile', side_effect=OSError(errno.ENOSPC, 'PRIVATE-DATA')):
            with self.assertRaises(UserError) as caught:
                self.store.check_capsule_storage(self.profile)
        self.assertEqual(caught.exception.reason_code, 'computer-storage-full')
        report = json.loads(diagnostics.create_report(self.store, 'install', self.profile,
                                                      'install-packages', caught.exception).read_text())
        self.assertEqual(report['guidance']['code'], 'computer-storage-full')
        self.assertEqual(report['local_recovery']['reason'], 'storage-unavailable')
        self.assertNotIn('PRIVATE-DATA', json.dumps(report))

    def test_full_disk_during_profile_creation_keeps_computer_storage_guidance(self):
        with patch.object(self.store, 'device_dir', side_effect=OSError(errno.ENOSPC, 'PRIVATE-DATA')):
            with self.assertRaises(UserError) as caught:
                self.store.check_capsule_storage(self.profile)
        self.assertEqual(caught.exception.reason_code, 'computer-storage-full')
        self.assertEqual(caught.exception.local_recovery['reason'], 'directory-access')
        self.assertIsNone(self.store.pending(self.profile))

    def test_local_probe_removes_temporary_file_without_creating_a_journal(self):
        directory = self.store.device_dir(self.profile)
        before = set(directory.iterdir())
        self.store.check_capsule_storage(self.profile)
        self.assertEqual(set(directory.iterdir()), before)
        self.assertIsNone(self.store.pending(self.profile))

    def test_fresh_cli_checks_local_writes_before_connecting_to_the_tv(self):
        for number, message in ((errno.EROFS, 'Check write access to the application data folder'),
                                (errno.ENOSPC, 'Not enough space on this computer')):
            with self.subTest(errno=number):
                connect = Mock(side_effect=AssertionError('SSH must remain untouched'))
                output = []
                with patch('cytv.cli.package.verify_payload', return_value={}), \
                     patch('cytv.state.tempfile.TemporaryFile', side_effect=OSError(number, 'PRIVATE-DATA')):
                    result = cli.main(['install', '--host', 'test-tv', '--edition', 'no-root',
                                       '--data-dir', str(self.store.root), '--non-interactive', '--yes', '--language', 'en'],
                                      write=output.append, connect=connect)
                self.assertEqual(result, 2, output)
                self.assertIn(message, '\n'.join(output))
                self.assertIn('Installation stopped before package submission.', '\n'.join(output))
                self.assertIsNone(self.store.pending(self.profile))
                connect.assert_not_called()

    def test_desktop_preference_write_failure_still_identifies_local_storage(self):
        from cytv.desktop import DesktopConsole

        events = []
        connect = Mock(side_effect=AssertionError('SSH must remain untouched'))
        with patch('cytv.state.private_write', side_effect=OSError(errno.ENOSPC, 'PRIVATE-DATA')):
            result = cli.main(['install', '--language', 'en', '--data-dir', str(self.store.root)],
                              write=DesktopConsole(lambda *event: events.append(event)), connect=connect)
        self.assertEqual(result, 2)
        guide, = [value for kind, value in events if kind == 'failure-help']
        self.assertEqual(guide['code'], 'computer-storage-full')
        self.assertTrue(guide['can_retry_setup'])
        connect.assert_not_called()

    def test_local_precheck_never_offers_retry_with_an_unresolved_receipt(self):
        from cytv.failure_help import for_error

        self.saved()
        original = self.store.pending(self.profile)
        with patch('cytv.state.tempfile.TemporaryFile', side_effect=OSError(errno.EROFS, 'PRIVATE-DATA')):
            with self.assertRaises(LocalRecoveryError) as caught:
                self.store.check_capsule_storage(self.profile)
        guide = for_error(caught.exception, 'install-packages', self.profile, original)
        self.assertEqual(guide['code'], 'computer-storage-unavailable')
        self.assertFalse(guide.get('can_retry_setup'))
        self.assertEqual(self.store.pending(self.profile), original)

    def test_new_messages_translate_in_every_installer_locale(self):
        from cytv import i18n
        self.addCleanup(i18n.set_language, 'en')
        for reason in ('directory-permissions', 'capsule-missing', 'capsule-changed', 'source-incompatible'):
            sentence = str(LocalRecoveryError(reason)).split(' Recovery data was kept.')[0]
            for language in set(i18n.LANGUAGES) - {'auto', 'en'}:
                with self.subTest(reason=reason, language=language):
                    i18n.set_language(language)
                    self.assertNotEqual(i18n.translate(sentence), sentence)

    def test_persisted_metadata_is_revalidated(self):
        report = diagnostic_context.failure_summary({'local_recovery': {
            'reason': 'PRIVATE-DATA', 'location': 'PRIVATE-DATA', 'owner': 'PRIVATE-DATA',
            'mode': 'PRIVATE-DATA', 'path': 'PRIVATE-DATA', 'uid': 12345}})
        self.assertEqual(report['local_recovery'], {'reason': 'unknown', 'location': 'unknown'})

    def test_older_source_is_identified_without_execution_or_journal_changes(self):
        plan = observer.make_plan(self.operation, 'b' * 32, 'remove', {}, {})
        source = 'old observer source'
        plan['source_sha256'] = hashlib.sha256(source.encode()).hexdigest()
        self.store.begin(self.profile, 'uninstall', recovery_protocol=observer.PROTOCOL,
                         observer_operation=self.operation, expected={}, versions={})
        pending = self.store.pending(self.profile)
        plan['diagnostic_id'] = pending['diagnostic_id']
        value = dict(schema=1, profile=self.profile, plan=plan, source=source,
                     expected={}, artifacts={}, configuration={})
        digest = self.store.save_capsule(self.profile, self.operation, value)
        self.store.checkpoint(self.profile, capsule_sha256=digest)
        pending = self.store.pending(self.profile)
        installer = SimpleNamespace(store=self.store, profile=self.profile, remote=Mock())
        with self.assertRaises(UserError) as caught:
            observer.capsule(installer, pending)
        self.assertEqual(caught.exception.local_recovery['reason'], 'source-incompatible')
        self.assertEqual(self.store.pending(self.profile), pending)
        installer.remote.run.assert_not_called()
