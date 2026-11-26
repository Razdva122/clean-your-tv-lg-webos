"""Passive Root Doctor observation of the compositor emergency input channel."""

# Sent to the existing TV Python over SSH stdin. Only EVIOCGNAME and
# EVIOCGBIT(EV_KEY) are queried. Keep the matching descriptor through both.
PROBE = """
import fcntl
import os
import stat

def query(fd, number, size):
    buffer = bytearray(size)
    fcntl.ioctl(fd, 0x80000000 | (size << 16) | (ord('E') << 8) | number, buffer, True)
    return buffer

def observe():
    match = None
    try:
        for entry in os.listdir('/dev/input'):
            if not entry.startswith('event'):
                continue
            fd = os.open('/dev/input/' + entry, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
            try:
                if not stat.S_ISCHR(os.fstat(fd).st_mode):
                    return 'unavailable'
                name = query(fd, 6, 256).split(bytes(1), 1)[0]
                if name == b'LGE M-RCU - Builtin [0]':
                    if match is not None:
                        return 'ambiguous'
                    match, fd = fd, None
            finally:
                if fd is not None:
                    os.close(fd)
        if match is None:
            return 'missing'
        keys = query(match, 0x21, 128)
        home, back = (int(bool(keys[key // 8] & (1 << (key % 8)))) for key in (773, 412))
        return 'unique %d %d' % (home, back)
    except OSError:
        return 'unavailable'
    finally:
        if match is not None:
            os.close(match)

print(observe())
"""


def observe(remote, command):
    try:
        reply = remote.run(command, data=PROBE.encode(), timeout=5).strip()
    except Exception:
        return {'state': 'unavailable'}
    if reply in ('missing', 'ambiguous'):
        return {'state': reply}
    if reply in ('unique 0 0', 'unique 0 1', 'unique 1 0', 'unique 1 1'):
        _, home, back = reply.split()
        return {'state': 'unique', 'home': home == '1', 'back': back == '1'}
    return {'state': 'unavailable'}


def summary(value):
    if isinstance(value, dict):
        state = value.get('state')
        if state in ('missing', 'ambiguous'):
            return {'state': state}
        if state == 'unique' and all(type(value.get(key)) is bool for key in ('home', 'back')):
            return {key: value[key] for key in ('state', 'home', 'back')}
    return {'state': 'unavailable'}
