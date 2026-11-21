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
DISCONNECTED = (errno.ENODEV, errno.ENXIO, errno.ENOENT)


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
                if exc.errno in DISCONNECTED: continue
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


def recheck_acknowledged(stamp):
    # Only the guardian's atomically replaced health pulse acknowledges CHECK.
    # This read suppresses retries; launch authority always remains native.
    try:
        path = '/tmp/clean-your-tv-root-keyfilter/health'
        with os.fdopen(os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW), 'rb') as source:
            info = os.fstat(source.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                    or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1):
                return False
            fields = source.read(256).split()
        return len(fields) == 6 and fields[5] == b'3' and int(fields[3]) >= stamp
    except (OSError, ValueError):
        return False


def observe(fd, health, keys_released, *, report_device_gone=False, reconnect_on_disconnect=False, recover_input=False):
    os.set_blocking(fd, False)
    reconnect_on_disconnect = reconnect_on_disconnect or recover_input
    guardian = select.poll() if reconnect_on_disconnect else None
    if guardian is not None:
        guardian.register(health, select.POLLERR | select.POLLHUP | select.POLLNVAL)
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
    validation_stamp = 0
    def require_emergency_keys(source):
        keys = query(source, 0x21, 128)
        if any(not keys[code // 8] & (1 << (code % 8)) for code in (773, 412)):
            raise ValueError('Emergency Home/Back input capabilities not verified')

    def reconnect(deadline):
        nonlocal validation_stamp
        while time.monotonic() < deadline:
            if guardian is not None and guardian.poll(0):
                return None  # The existing guardian retired; there is no route to renew.
            replacement = None
            try:
                replacement = open_remote()
                require_emergency_keys(replacement)
                pressed = query(replacement, 0x18, 256)
                while guardian is not None and any(pressed) and time.monotonic() < deadline:
                    if guardian.poll(0):
                        return None
                    if pressed[773 // 8] & (1 << (773 % 8)):
                        lost('reconnect', 'home_activity')
                        return None
                    # Keep this descriptor open so fresh Home presses cannot be
                    # discarded while waiting for another held key's release.
                    if not drain(False, source=replacement, phase='reconnect'):
                        return None
                    time.sleep(min(.02, max(0, deadline - time.monotonic())))
                    pressed = query(replacement, 0x18, 256)
                if not any(pressed) and time.monotonic() < deadline:
                    if guardian is not None and guardian.poll(0):
                        return None
                    # Keep the caller's descriptor ownership and close-on-exec.
                    if recover_input:
                        validation_stamp = time.clock_gettime_ns(time.CLOCK_MONOTONIC) // 1_000_000
                    os.dup2(replacement, fd, inheritable=False)
                    return True
            except InputUnavailable:
                pass
            except OSError as exc:
                if exc.errno not in DISCONNECTED: raise
            finally:
                if replacement is not None: os.close(replacement)
            time.sleep(min(.02, max(0, deadline - time.monotonic())))
        return False
    def drain(history, *, source=fd, phase='startup'):
        for _ in range(64):
            try: data = os.read(source, EVENT.size * 64)
            except BlockingIOError: return True
            except OSError as exc:
                report(phase, 'read_error', exc)
                raise
            if not data: lost(phase, 'eof'); return False
            if history: continue
            if len(data) % EVENT.size: lost(phase, 'partial_event'); return False
            for offset in range(0, len(data), EVENT.size):
                sec, usec, kind, code, value = EVENT.unpack_from(data, offset)
                if usec >= 1000000: lost(phase, 'invalid_timestamp'); return False
                if kind == 0 and code == 3: lost(phase, 'events_dropped'); return False
                if kind == 1 and code == 773:
                    if value not in (0, 1, 2): lost(phase, 'invalid_key_value'); return False
                    # New Home input must cancel pending activation, including a
                    # gesture that could finish just after readiness is published.
                    if value: lost(phase, 'home_activity'); return False
        lost(phase, 'drain_limit'); return False
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
    last_heartbeat = time.monotonic() if recover_input else None
    awaiting_recheck = False
    last_recovery_home = None
    offered_at = 0
    while True:
        reconnect_deadline = None
        # A scheduler gap can expire the native lease even while evdev never
        # returned EOF. Do not let the old descriptor renew it after the gap.
        if recover_input and not awaiting_recheck and time.monotonic() - last_heartbeat >= 1.5:
            disconnect_at = time.monotonic()
            try:
                resumed = reconnect(disconnect_at + 60)
            except BrokenPipeError:
                return
            except (OSError, ValueError):
                resumed = False
            if resumed is None:
                return
            if not resumed:
                lost('active', 'reconnect_failed'); return
            policy = TripleHome(); back = LongBack()
            reconnect_deadline = disconnect_at + 60
            awaiting_recheck = True
            last_recovery_home = None
            offered_at = 0
        select.select([fd], [], [], .1)
        for _ in range(64):
            try: data = os.read(fd, EVENT.size * 64)
            except BlockingIOError: break
            except OSError as exc:
                if report_device_gone and exc.errno == errno.ENODEV:
                    # Mark the read boundary before logging or supervisor scheduling.
                    send(('DEVICE_GONE %.9f' % time.monotonic()).encode('ascii'))
                report('active', 'read_error', exc)
                # The persistent supervisor owns recovery after DEVICE_GONE.
                if report_device_gone or not (
                    exc.errno == errno.ENODEV or reconnect_on_disconnect and exc.errno in DISCONNECTED
                ):
                    raise
                data = b''
            else:
                if not data:
                    if not reconnect_on_disconnect:
                        lost('active', 'eof'); return
                    report('active', 'eof')
            if not data:
                if reconnect_deadline is None:
                    reconnect_deadline = time.monotonic() + (60 if recover_input else .75)
                try:
                    resumed = reconnect(reconnect_deadline)
                except BrokenPipeError:
                    return
                except (OSError, ValueError):
                    resumed = False
                if resumed is None:
                    return
                if not resumed:
                    lost('active', 'reconnect_failed'); return
                # No gesture may span two kernel input-device instances. Process
                # fresh events before publishing the first replacement heartbeat.
                policy = TripleHome(); back = LongBack()
                awaiting_recheck = recover_input
                last_recovery_home = None
                offered_at = 0
                continue
            if len(data) % EVENT.size: lost('active', 'partial_event'); return
            for offset in range(0, len(data), EVENT.size):
                sec, usec, kind, code, value = EVENT.unpack_from(data, offset)
                if usec >= 1000000: lost('active', 'invalid_timestamp'); return
                if kind == 0 and code == 3: lost('active', 'events_dropped'); return
                try: fired = policy.event(kind, code, value, sec * 1000 + usec / 1000)
                except ValueError: lost('active', 'invalid_key_value'); return
                now = time.monotonic()
                if awaiting_recheck and kind == 1 and code == 773:
                    last_recovery_home = now
                back.event(kind, code, value, now * 1000)
                if fired: send(b'ESCAPE'); return
        else: lost('active', 'drain_limit'); return
        if back.tick(time.monotonic() * 1000): send(b'LGHOME')
        if recover_input:
            now = time.monotonic()
            if awaiting_recheck:
                if offered_at and recheck_acknowledged(validation_stamp):
                    awaiting_recheck = False
                    last_heartbeat = now
                    continue
                if offered_at and now - offered_at < .25:
                    continue
                if last_recovery_home is not None and now - last_recovery_home < 2:
                    continue  # A partial Home gesture can complete on this descriptor.
                if guardian.poll(0):
                    return
                if time.clock_gettime_ns(time.CLOCK_MONOTONIC) // 1_000_000 - validation_stamp >= 250:
                    try:
                        require_emergency_keys(fd)
                        if any(query(fd, 0x18, 256)):
                            continue
                    except OSError as exc:
                        if exc.errno not in DISCONNECTED: raise
                        awaiting_recheck = False
                        continue
                    validation_stamp = time.clock_gettime_ns(time.CLOCK_MONOTONIC) // 1_000_000
                send(('CHECK %d' % validation_stamp).encode('ascii'))
                offered_at = now
                continue
            elif now - last_heartbeat >= 1.5:
                continue
            else:
                send(b'PING')
            last_heartbeat = now
        else:
            send(b'PING')


if __name__ == '__main__':
    args = sys.argv[1:]
    if os.geteuid() != 0 or not (len(args) == 1 or len(args) == 2 and args[1] in ('--report-device-gone', '--reconnect-on-disconnect', '--recover-input')):
        raise SystemExit('Root and private health fd required')
    health = int(args[0]); fd = open_remote()
    try:
        observe(fd, health, lambda: not any(query(fd, 0x18, 256)),
                report_device_gone=args[1:] == ['--report-device-gone'],
                reconnect_on_disconnect=args[1:] == ['--reconnect-on-disconnect'],
                recover_input=args[1:] == ['--recover-input'])
    finally: os.close(fd); os.close(health)
