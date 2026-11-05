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

    def test_compressed_ipk_budget_uses_expanded_blocks(self):
        data = package.ipk('test', '1', {'usr/palm/applications/test/data': b'0' * 1024*1024})
        self.assertGreater(storage.unpacked(data), len(data)*10)
        remote = Mock(); remote.run.return_value = 'Filesystem 1024-blocks Used Available Capacity Mounted on\n/dev/test 10000000 0 10000000 0% /shared'
        messages = []; storage.install(remote, {'test.ipk': data}, messages.append)
        self.assertIn('shortfall 0.0 MiB', messages[0])

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
