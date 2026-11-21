"""Connection to an LG TV's remote-control service (wss://TV:3001), the one LG's phone app uses.

The first connection shows a prompt on the TV: accept it. The key is kept in .lgtv-key.json.
"""
import asyncio
from contextlib import suppress
import json
import os
import ssl
import sys
import tempfile
from time import sleep

import websockets

HERE = os.path.dirname(os.path.abspath(__file__))
KEY_FILE = os.path.join(HERE, ".lgtv-key.json")

# Unsigned on purpose: newer firmware rejects the signed manifest that open-source clients share
# ("403 Pairing rejected: blacklisted certificate detected") but still accepts an unsigned one.
PERMISSIONS = [
    "LAUNCH", "LAUNCH_WEBAPP", "APP_TO_APP", "CLOSE", "TEST_OPEN", "TEST_PROTECTED", "CONTROL_AUDIO",
    "CONTROL_DISPLAY", "CONTROL_INPUT_JOYSTICK", "CONTROL_INPUT_MEDIA_RECORDING",
    "CONTROL_INPUT_MEDIA_PLAYBACK", "CONTROL_INPUT_TV", "CONTROL_POWER", "CONTROL_TV_SCREEN",
    "READ_APP_STATUS", "READ_CURRENT_CHANNEL", "READ_INPUT_DEVICE_LIST", "READ_NETWORK_STATE",
    "READ_RUNNING_APPS", "READ_TV_CHANNEL_LIST", "WRITE_NOTIFICATION_TOAST", "READ_POWER_STATE",
    "READ_COUNTRY_INFO", "CONTROL_INPUT_TEXT", "CONTROL_MOUSE_AND_KEYBOARD", "READ_INSTALLED_APPS",
    "READ_SETTINGS", "READ_STORAGE_DEVICE_LIST",
]


def insecure_ctx():
    # The TV uses a certificate from LG's own CA.
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _read_keys():
    try:
        with open(KEY_FILE, encoding="utf-8") as stream:
            keys = json.load(stream)
    except FileNotFoundError:
        return {}
    if not isinstance(keys, dict):
        raise ValueError("The saved TV pairing store must contain a JSON object")
    return keys


def load_keys():
    try:
        return _read_keys()
    except (OSError, ValueError):
        return {}


def _replace_keys(temporary):
    for attempt in range(3):
        try:
            os.replace(temporary, KEY_FILE)
            return
        except PermissionError as error:
            # An unlocked reader can briefly prevent replacement on Windows.
            if os.name != "nt" or getattr(error, "winerror", None) not in (5, 32, 33) or attempt == 2:
                raise
            sleep(0.05 * (attempt + 1))


def _save_key(host, key):
    # Keep the sidecar so all writers lock the same file even after replacing the JSON.
    lock = os.open(f"{KEY_FILE}.lock", os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(lock, msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX)

        keys = _read_keys()
        if keys.get(host) == key:
            return
        keys[host] = key
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False,
                                             dir=os.path.dirname(KEY_FILE) or ".",
                                             prefix=os.path.basename(KEY_FILE) + ".", suffix=".tmp") as stream:
                temporary = stream.name
                json.dump(keys, stream, indent=1)
                stream.flush()
                os.fsync(stream.fileno())
            _replace_keys(temporary)
        finally:
            if temporary is not None:
                with suppress(FileNotFoundError):
                    os.unlink(temporary)
    finally:
        os.close(lock)


async def session(host, **connect_args):
    saved_key = load_keys().get(host)
    ws = await websockets.connect(f"wss://{host}:3001", ssl=insecure_ctx(), open_timeout=10, max_size=None,
                                  **connect_args)
    try:
        payload = {
            "forcePairing": False,
            "pairingType": "PROMPT",
            "manifest": {"manifestVersion": 1, "appVersion": "1.1", "permissions": PERMISSIONS},
        }
        if isinstance(saved_key, str) and saved_key:
            payload["client-key"] = saved_key
        else:
            print("Accept the prompt on the TV...")
        await ws.send(json.dumps({"type": "register", "id": "register_0", "payload": payload}))
        while True:
            msg = json.loads(await asyncio.wait_for(ws.recv(), 60))
            if msg["type"] == "registered":
                break
            if msg["type"] == "error":
                sys.exit(f"Pairing failed: {msg.get('error')}")
        key = msg["payload"]["client-key"]
        if not isinstance(key, str) or not key:
            raise ValueError("Invalid TV pairing response")
        if saved_key != key:
            await asyncio.to_thread(_save_key, host, key)
        return ws
    except BaseException:
        with suppress(Exception):
            await ws.close()
        raise


async def call(ws, uri, payload=None, n=[0], *, strict=False):
    n[0] += 1
    rid = f"c{n[0]}"
    await ws.send(json.dumps({"type": "request", "id": rid, "uri": uri, "payload": payload or {}}))
    while True:
        msg = json.loads(await asyncio.wait_for(ws.recv(), 20))
        if msg.get("id") == rid:
            reply = msg.get("payload", {})
            if strict and (msg.get("type", "response") != "response" or
                           not isinstance(reply, dict) or reply.get("returnValue") is False):
                raise ValueError("TV did not return a successful response for " + uri)
            return reply
