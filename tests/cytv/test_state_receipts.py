"""Operation receipts work in Android's sandbox and never replace evidence."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import errno
import json
import tempfile
from threading import Barrier
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from cytv import state


class ReceiptTests(unittest.TestCase):
    def test_begin_succeeds_when_android_denies_hard_links(self):
        with tempfile.TemporaryDirectory() as directory:
            store = state.Store(directory)
            profile = state.target('tv.local', 'no-root')
            with patch('cytv.state.os.link', side_effect=PermissionError(errno.EPERM, 'denied')):
                store.begin(profile, 'install', versions={'home': '1.0.0'})
            receipt = store.device_dir(profile) / 'operation.json'
            value = json.loads(receipt.read_text())
            self.assertRegex(value.pop('diagnostic_id'), r'^[a-f0-9]{32}$')
            self.assertEqual(value, {
                'action': 'install', 'stage': 'pending', 'versions': {'home': '1.0.0'}})
            if state.os.name != 'nt':
                self.assertEqual(receipt.stat().st_mode & 0o777, 0o600)

    def test_existing_receipts_are_preserved_byte_for_byte_without_hard_links(self):
        for contents in (b'{"action":"uninstall","stage":"pending"}', b'{', b''):
            with self.subTest(contents=contents), tempfile.TemporaryDirectory() as directory:
                store = state.Store(directory)
                profile = state.target('tv.local', 'no-root')
                receipt = store.device_dir(profile) / 'operation.json'
                receipt.write_bytes(contents)
                with patch('cytv.state.os.link', side_effect=PermissionError(errno.EPERM, 'denied')):
                    with self.assertRaises(state.UserError):
                        store.begin(profile, 'install')
                self.assertEqual(receipt.read_bytes(), contents)
                self.assertIsNotNone(store.pending(profile))

    def test_competing_begins_publish_exactly_one_receipt_without_hard_links(self):
        with tempfile.TemporaryDirectory() as directory:
            profile = state.target('tv.local', 'no-root')
            barrier = Barrier(2)

            def begin(action):
                store = state.Store(directory)
                barrier.wait(timeout=5)
                try:
                    store.begin(profile, action)
                    return action
                except state.UserError:
                    return None

            with patch('cytv.state.os.link', side_effect=PermissionError(errno.EPERM, 'denied')):
                with ThreadPoolExecutor(max_workers=2) as executor:
                    winners = list(filter(None, executor.map(begin, ('install', 'uninstall'))))
            self.assertEqual(len(winners), 1)
            value = state.Store(directory).pending(profile)
            self.assertRegex(value.pop('diagnostic_id'), r'^[a-f0-9]{32}$')
            self.assertEqual(value, {
                'action': winners[0], 'stage': 'pending'})

    def test_failed_receipt_sync_retains_evidence_and_blocks_retry(self):
        for sync in ('cytv.state.os.fsync', 'cytv.state.sync_directory'):
            with self.subTest(sync=sync), tempfile.TemporaryDirectory() as directory:
                store = state.Store(directory)
                profile = state.target('tv.local', 'no-root')
                with patch(sync, side_effect=OSError(errno.EIO, 'disk failure')):
                    with self.assertRaises(OSError):
                        store.begin(profile, 'install')
                receipt = store.device_dir(profile) / 'operation.json'
                self.assertTrue(receipt.exists())
                contents = receipt.read_bytes()
                with self.assertRaises(state.UserError):
                    store.begin(profile, 'uninstall')
                self.assertEqual(receipt.read_bytes(), contents)

    def test_partial_write_is_retained_as_a_blocking_corrupt_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            store = state.Store(directory)
            profile = state.target('tv.local', 'no-root')
            fdopen = state.os.fdopen

            @contextmanager
            def fail_write(fd, *args, **kwargs):
                with fdopen(fd, *args, **kwargs) as stream:
                    def write(data):
                        stream.write(data[:1])
                        stream.flush()
                        raise OSError(errno.ENOSPC, 'disk full')
                    yield SimpleNamespace(write=write)

            with patch('cytv.state.os.fdopen', fail_write):
                with self.assertRaises(OSError):
                    store.begin(profile, 'install')
            self.assertEqual(store.pending(profile)['action'], 'unknown')
            receipt = store.device_dir(profile) / 'operation.json'
            self.assertEqual(receipt.read_bytes(), b'{')
            with self.assertRaises(state.UserError):
                store.begin(profile, 'uninstall')
            self.assertEqual(receipt.read_bytes(), b'{')


if __name__ == '__main__':
    unittest.main()
