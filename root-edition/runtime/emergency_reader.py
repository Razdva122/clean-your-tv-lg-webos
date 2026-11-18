"""Read-only observer for the validated ARM32 Magic Remote channel.

No EVIOCGRAB, input writes, reinjection, system library patches or key filtering.
"""
import errno
import fcntl
import json
import os
import select
import stat
import struct
import sys
import time
from pathlib import Path
try: from .emergency_gesture import TripleHome, LongBack
except ImportError: from emergency_gesture import TripleHome, LongBack
EVENT = struct.Struct('<IIHHi')
NAME = b'LGE M-RCU - Builtin [0]'


class InputUnavailable(ValueError):
    """The validated channel is temporarily absent during device recreation."""


def query(fd, nr, size):
    value = bytearray(size)
    fcntl.ioctl(fd, 0x80000000 | (size << 16) | (ord('E') << 8) | nr, value, True)
    return value


def open_remote():
    if sys.byteorder != 'little' or struct.calcsize('@llHHi') != 16 or struct.calcsize('P') != 4:
        raise ValueError('Only the validated ARM32 input ABI is supported')
    found = []
    try:
        for path in sorted(Path('/dev/input').glob('event*')):
            try:
                fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC | os.O_NOFOLLOW)
            except OSError as exc:
                if exc.errno in (errno.ENXIO, errno.ENODEV, errno.ENOENT): continue
                raise
            try:
                if not stat.S_ISCHR(os.fstat(fd).st_mode): raise ValueError('Not an input device')
                try:
                    name = bytes(query(fd, 6, 256)).split(b'\0')[0]
                except OSError as exc:
                    if exc.errno == errno.ENODEV: continue
                    raise
                if name != NAME: continue
                found.append(fd); fd = None
            finally:
                if fd is not None: os.close(fd)
        if not found: raise InputUnavailable('Validated input channel missing')
        if len(found) != 1: raise ValueError('Validated input channel ambiguous')
        return found.pop()
    finally:
        for fd in found: os.close(fd)


def observe(fd, health, keys_released):
    os.set_blocking(fd, False)
    def send(message):
        data = message + b'\n'
        if os.write(health, data) != len(data): raise RuntimeError('Short health write')
    def report(phase, reason, error=None):
        # Fixed codes only: no key history, device paths or private input data.
        record = {'event':'input-observer-fault', 'phase':phase, 'reason':reason}
        if error is not None: record['errno'] = error.errno
        try:
            print(json.dumps(record), file=sys.stderr, flush=True)
        except OSError:
            pass  # Full/unavailable logs must not replace the input-loss signal.
    def lost(phase, reason):
        report(phase, reason)
        send(b'LOST')
    def reconnect(deadline):
        while time.monotonic() < deadline:
            replacement = None
            try:
                replacement = open_remote()
                keys = query(replacement, 0x21, 128)
                if any(not keys[code // 8] & (1 << (code % 8)) for code in (773, 412)):
                    raise ValueError('Emergency Home/Back input capabilities not verified')
                released = not any(query(replacement, 0x18, 256))
                if released and time.monotonic() < deadline:
                    # Keep the caller's descriptor ownership and close-on-exec.
                    os.dup2(replacement, fd, inheritable=False)
                    return True
            except InputUnavailable:
                pass
            except OSError as exc:
                if exc.errno not in (errno.ENODEV, errno.ENXIO, errno.ENOENT): raise
            finally:
                if replacement is not None: os.close(replacement)
            time.sleep(min(.02, max(0, deadline - time.monotonic())))
        return False
    def drain(history):
        for _ in range(64):
            try: data = os.read(fd, EVENT.size * 64)
            except BlockingIOError: return True
            except OSError as exc:
                report('startup', 'read_error', exc)
                raise
            if not data: lost('startup', 'eof'); return False
            if history: continue
            if len(data) % EVENT.size: lost('startup', 'partial_event'); return False
            for offset in range(0, len(data), EVENT.size):
                sec, usec, kind, code, value = EVENT.unpack_from(data, offset)
                if usec >= 1000000: lost('startup', 'invalid_timestamp'); return False
                if kind == 0 and code == 3: lost('startup', 'events_dropped'); return False
                if kind == 1 and code == 773:
                    if value not in (0, 1, 2): lost('startup', 'invalid_key_value'); return False
                    # New Home input must cancel pending activation, including a
                    # gesture that could finish just after readiness is published.
                    if value: lost('startup', 'home_activity'); return False
        lost('startup', 'drain_limit'); return False
    # Only the initial queue is historical. Input arriving while waiting is new.
    if not drain(True): return
    # Wake may start the observer before a wake key is released. Stay unready
    # within the supervisor's existing two-second deadline; never renew it here.
    release_deadline = time.monotonic() + .75
    while not keys_released():
        remaining = release_deadline - time.monotonic()
        if remaining <= 0: lost('startup', 'keys_held'); return
        time.sleep(min(.02, remaining))
        if not drain(False): return
    policy = TripleHome(); back = LongBack(); send(b'READY')
    while True:
        select.select([fd], [], [], .1)
        reconnect_deadline = None
        for _ in range(64):
            try: data = os.read(fd, EVENT.size * 64)
            except BlockingIOError: break
            except OSError as exc:
                report('active', 'read_error', exc)
                if exc.errno == errno.ENODEV:
                    if reconnect_deadline is None:
                        reconnect_deadline = time.monotonic() + .75
                    try:
                        resumed = reconnect(reconnect_deadline)
                    except (OSError, ValueError):
                        resumed = False
                    if not resumed:
                        lost('active', 'reconnect_failed'); return
                    # No gesture may span two kernel input-device instances.
                    policy = TripleHome(); back = LongBack()
                    continue
                raise
            if not data: lost('active', 'eof'); return
            if len(data) % EVENT.size: lost('active', 'partial_event'); return
            for offset in range(0, len(data), EVENT.size):
                sec, usec, kind, code, value = EVENT.unpack_from(data, offset)
                if usec >= 1000000: lost('active', 'invalid_timestamp'); return
                if kind == 0 and code == 3: lost('active', 'events_dropped'); return
                try: fired = policy.event(kind, code, value, sec * 1000 + usec / 1000)
                except ValueError: lost('active', 'invalid_key_value'); return
                back.event(kind, code, value, time.monotonic() * 1000)
                if fired: send(b'ESCAPE'); return
        else: lost('active', 'drain_limit'); return
        if back.tick(time.monotonic() * 1000): send(b'LGHOME')
        send(b'PING')


if __name__ == '__main__':
    if os.geteuid() != 0 or len(sys.argv) != 2: raise SystemExit('Root and private health fd required')
    health = int(sys.argv[1]); fd = open_remote()
    try: observe(fd, health, lambda: not any(query(fd, 0x18, 256)))
    finally: os.close(fd); os.close(health)
