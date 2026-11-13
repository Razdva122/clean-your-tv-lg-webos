import unittest
from unittest.mock import Mock
from cytv import storage, package
from cytv.errors import UserError

class StorageTests(unittest.TestCase):
    def test_shared_partition_sums_demands_and_reports_shortfall_before_upload(self):
        remote = Mock()
        remote.run.return_value = 'Filesystem 1024-blocks Used Available Capacity Mounted on\n/dev/test 100000 90000 10000 90% /shared\n'
        messages = []
        with self.assertRaises(UserError) as caught:
            storage.check(remote, {'/tmp': 8*1024*1024, '/var/lib': 8*1024*1024}, messages.append)
        self.assertEqual(len(messages), 1)
        self.assertIn('required 32.0 MiB', str(caught.exception))
        self.assertIn('available 9.7 MiB', str(caught.exception))
        self.assertIn('shortfall 22.3 MiB', str(caught.exception))
        remote.upload.assert_not_called()

    def test_unknown_capacity_is_not_invented(self):
        remote = Mock(); remote.run.return_value = 'PRIVATE invalid result'
        messages = []
        with self.assertRaises(UserError): storage.check(remote, {'/tmp': 1024}, messages.append)
        self.assertIn('could not be determined', messages[0])
        self.assertNotIn('PRIVATE', str(messages))

    def test_ramfs_zero_blocks_reports_unmeasurable_capacity_before_submission(self):
        import json
        from tempfile import TemporaryDirectory
        from cytv import diagnostic_context, diagnostics, failure_help, state

        remote = Mock()
        remote.run.side_effect = [
            'Filesystem 1024-blocks Used Available Capacity Mounted on\ntmp 0 0 0 0% /tmp',
            '858458f6\n',
        ]
        messages = []
        with self.assertRaises(UserError) as caught:
            storage.check(remote, {'/tmp': 1024}, messages.append)

        self.assertEqual(caught.exception.reason_code, 'tv-storage-ramfs')
        self.assertIn('could not be determined', messages[0])
        self.assertIn('before package submission', str(caught.exception))
        remote.upload.assert_not_called()
        profile = state.target('tv.local', 'no-root')
        guide = failure_help.for_error(caught.exception, 'install-packages', profile)
        self.assertEqual(guide['code'], 'tv-storage-ramfs')
        self.assertIn('ramfs', guide['detail'])
        with TemporaryDirectory() as directory:
            path = diagnostics.create_report(state.Store(directory), 'install', profile,
                                             'install-packages', caught.exception)
            report = json.loads(path.read_text())
        self.assertEqual(report['reason_code'], 'tv-storage-ramfs')
        self.assertEqual(report['previous_attempt_failure']['reason_code'], 'tv-storage-ramfs')
        self.assertEqual(diagnostic_context.failure_summary(report)['reason_code'], 'tv-storage-ramfs')

    def test_ambiguous_zero_blocks_keep_existing_preflight_failure(self):
        zero = 'Filesystem 1024-blocks Used Available Capacity Mounted on\ntmp 0 0 0 0% /tmp'
        for result in ('858458f6\nPRIVATE', '1021994', None, OSError('PRIVATE')):
            with self.subTest(result=result):
                remote = Mock()
                remote.run.side_effect = [zero, result]
                with self.assertRaises(UserError) as caught:
                    storage.check(remote, {'/tmp': 1024}, lambda _: None)
                self.assertEqual(caught.exception.reason_code, 'tv-storage-full')
                self.assertNotIn('PRIVATE', str(caught.exception))

    def test_measured_full_partition_still_takes_precedence(self):
        remote = Mock()
        remote.run.side_effect = [
            'Filesystem 1024-blocks Used Available Capacity Mounted on\ntmp 0 0 0 0% /tmp',
            '858458f6',
            'Filesystem 1024-blocks Used Available Capacity Mounted on\n/dev/full 100 100 0 100% /var/lib',
        ]
        with self.assertRaises(UserError) as caught:
            storage.check(remote, {'/tmp': 1024, '/var/lib': 1024}, lambda _: None)
        self.assertEqual(caught.exception.reason_code, 'tv-storage-full')
        self.assertIn('(/var/lib)', str(caught.exception))
        self.assertNotIn('(/tmp)', str(caught.exception))

    def test_compressed_ipk_budget_uses_expanded_blocks(self):
        data = package.ipk('test', '1', {'usr/palm/applications/test/data': b'0' * 1024*1024})
        self.assertGreater(storage.unpacked(data), len(data)*10)
        remote = Mock(); remote.run.return_value = 'Filesystem 1024-blocks Used Available Capacity Mounted on\n/dev/test 10000000 0 10000000 0% /shared'
        messages = []; storage.install(remote, {'test.ipk': data}, messages.append)
        self.assertIn('shortfall 0.0 MiB', messages[0])

    def test_root_ssh_noroot_only_accepts_confirmed_ramfs(self):
        header = 'Filesystem 1024-blocks Used Available Capacity Mounted on\n'
        available = header + '/dev/data 1000000 0 1000000 0% /data'
        ramfs = header + 'tmp 0 0 0 0% /tmp'
        full = header + '/dev/tmp 1024 1024 0 100% /tmp'
        for tmp, magic, root, reason in (
                (ramfs, '858458f6', False, None),
                (ramfs, '858458f6', True, 'tv-storage-ramfs'),
                (ramfs, '1021994', False, 'tv-storage-full'),
                (full, '', False, 'tv-storage-full')):
            with self.subTest(tmp=tmp, magic=magic, root=root):
                remote = Mock()
                remote.run.side_effect = [tmp, *([magic] if tmp == ramfs else []), available, available]
                options = {'root': True} if root else {'no_root_root_ssh': True}
                if reason is None:
                    storage.install(remote, {'data': b'data'}, lambda _: None, **options)
                else:
                    with self.assertRaises(UserError) as caught:
                        storage.install(remote, {'data': b'data'}, lambda _: None, **options)
                    self.assertEqual(caught.exception.reason_code, reason)

    def test_noroot_install_stops_before_receipt_or_upload_on_full_partition(self):
        from test_operations import OperationTests, Remote
        from cytv import operations
        fixture = OperationTests(); fixture.setUp(); self.addCleanup(fixture.doCleanups)
        remote = Remote()
        original = remote.run
        remote.run = lambda command, **kw: ('Filesystem 1024-blocks Used Available Capacity Mounted on\n/dev/full 1 1 0 100% /full' if command.startswith('LC_ALL=C df -Pk ') else original(command, **kw))
        installer = fixture.installer(remote)
        with self.assertRaises(UserError) as caught:
            installer.install(fixture.inventory, ssap_key='PRIVATE')
        self.assertIn('shortfall', str(caught.exception))
        self.assertIsNone(installer.store.pending(installer.profile))
        self.assertEqual(remote.uploads, {})
