import asyncio
import contextlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, Mock, patch

import lgtv


def registration(key):
    return json.dumps({"type": "registered", "payload": {"client-key": key}})


def pairing_socket(key):
    return Mock(send=AsyncMock(), recv=AsyncMock(return_value=registration(key)), close=AsyncMock())


class SourcePairingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.store = Path(directory) / ".lgtv-key.json"
        self.original = b'{ "earlier-tv": "earlier-key" }\n'
        self.store.write_bytes(self.original)
        self.enterContext(patch.object(lgtv, "KEY_FILE", str(self.store)))
        self.output = self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.connect = self.enterContext(patch.object(lgtv.websockets, "connect", new_callable=AsyncMock))

    async def test_overlapping_registrations_keep_all_saved_tvs(self):
        first, second = pairing_socket("first-key"), pairing_socket("second-key")
        self.connect.side_effect = [first, second]
        waiting_for_approval, approve = asyncio.Event(), asyncio.Event()

        async def delayed_registration():
            waiting_for_approval.set()
            await approve.wait()
            return registration("first-key")

        first.recv.side_effect = delayed_registration
        pending = asyncio.create_task(lgtv.session("first-tv"))
        try:
            await asyncio.wait_for(waiting_for_approval.wait(), 5)
            self.assertIs(await asyncio.wait_for(lgtv.session("second-tv"), 5), second)
        finally:
            approve.set()
            self.assertIs(await asyncio.wait_for(pending, 5), first)

        self.assertEqual(json.loads(self.store.read_bytes()), {
            "earlier-tv": "earlier-key", "first-tv": "first-key", "second-tv": "second-key",
        })
        for socket in (first, second):
            sent = json.loads(socket.send.await_args.args[0])
            self.assertEqual(sent["payload"]["pairingType"], "PROMPT")
            self.assertNotIn("client-key", sent["payload"])
            socket.close.assert_not_awaited()
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(self.store.stat().st_mode), 0o600)

    async def test_other_process_cannot_lock_the_store_during_merge_or_publish(self):
        socket = pairing_socket("new-key")
        self.connect.return_value = socket
        lock = self.store.with_suffix(".json.lock")
        probe = """
import errno
import os
import sys

fd = os.open(sys.argv[1], os.O_RDWR)
try:
    if os.name == "nt":
        import msvcrt
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
except OSError as error:
    if error.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
        raise
    print("locked")
else:
    print("available")
finally:
    os.close(fd)
"""

        def lock_state():
            return subprocess.check_output([sys.executable, "-c", probe, str(lock)], text=True, timeout=5).strip()

        read_keys = lgtv._read_keys
        replace = os.replace
        observed = []

        def check_merge():
            if lock.exists():
                observed.append(lock_state())
            return read_keys()

        def check_publish(source, destination):
            observed.append(lock_state())
            replace(source, destination)

        with patch.object(lgtv, "_read_keys", side_effect=check_merge), patch.object(os, "replace", side_effect=check_publish):
            self.assertIs(await lgtv.session("new-tv"), socket)

        self.assertEqual(observed, ["locked", "locked"])
        self.assertEqual(lock_state(), "available")

    async def test_existing_key_is_reused_without_rewriting_store(self):
        socket = pairing_socket("earlier-key")
        self.connect.return_value = socket

        self.assertIs(await lgtv.session("earlier-tv"), socket)
        message = json.loads(socket.send.await_args.args[0])
        self.assertEqual(message["payload"]["client-key"], "earlier-key")
        self.assertEqual(self.store.read_bytes(), self.original)

    async def test_merge_read_failure_preserves_original_and_closes_socket(self):
        socket = pairing_socket("new-key")
        self.connect.return_value = socket

        with patch.object(lgtv, "_read_keys", side_effect=[
            {"earlier-tv": "earlier-key"}, PermissionError("injected read failure"),
        ]):
            with self.assertRaisesRegex(PermissionError, "injected read failure"):
                await lgtv.session("new-tv")

        self.assertEqual(self.store.read_bytes(), self.original)
        socket.close.assert_awaited_once()

    async def test_missing_store_is_created_for_first_registration(self):
        self.store.unlink()
        socket = pairing_socket("new-key")
        self.connect.return_value = socket

        self.assertIs(await lgtv.session("new-tv"), socket)
        self.assertEqual(json.loads(self.store.read_bytes()), {"new-tv": "new-key"})

    async def test_invalid_existing_store_is_not_overwritten(self):
        for raw in (b'{"earlier-tv":"earlier-key",', b'["earlier-key"]'):
            with self.subTest(raw=raw):
                self.store.write_bytes(raw)
                socket = pairing_socket("new-key")
                self.connect.return_value = socket

                with self.assertRaises(ValueError) as failure:
                    await lgtv.session("new-tv")

                self.assertEqual(self.store.read_bytes(), raw)
                self.assertNotIn("earlier-key", str(failure.exception))
                self.assertNotIn("earlier-key", self.output.getvalue())
                self.assertNotIn("new-key", self.output.getvalue())
                socket.close.assert_awaited_once()

    async def test_partial_write_preserves_original_and_closes_socket(self):
        socket = pairing_socket("new-key")
        self.connect.return_value = socket

        def interrupted_dump(keys, stream, **kwargs):
            stream.write('{"incomplete":')
            raise OSError("injected partial write")

        with patch.object(lgtv.json, "dump", side_effect=interrupted_dump):
            with self.assertRaisesRegex(OSError, "injected partial write"):
                await lgtv.session("new-tv")

        self.assertEqual(self.store.read_bytes(), self.original)
        socket.close.assert_awaited_once()
        self.assertEqual(set(self.store.parent.iterdir()) - {self.store, self.store.with_suffix(".json.lock")}, set())

    async def test_failed_replace_preserves_original_and_allows_retry(self):
        socket = pairing_socket("new-key")
        self.connect.return_value = socket

        def fail_replace(source, destination):
            self.assertEqual(Path(source).parent, self.store.parent)
            self.assertEqual(Path(destination), self.store)
            if os.name == "posix":
                self.assertEqual(stat.S_IMODE(Path(source).stat().st_mode), 0o600)
            raise OSError("injected replace failure")

        with patch.object(lgtv.os, "replace", side_effect=fail_replace):
            with self.assertRaisesRegex(OSError, "injected replace failure"):
                await lgtv.session("new-tv")

        self.assertEqual(self.store.read_bytes(), self.original)
        self.assertFalse(list(self.store.parent.glob(".lgtv-key.json.*.tmp")))
        socket.close.assert_awaited_once()

        retry = pairing_socket("new-key")
        self.connect.return_value = retry
        self.assertIs(await lgtv.session("new-tv"), retry)
        self.assertEqual(json.loads(self.store.read_bytes()), {"earlier-tv": "earlier-key", "new-tv": "new-key"})
