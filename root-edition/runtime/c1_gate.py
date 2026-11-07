"""Explicit experimental C1 routing; never an automatic profile fallback.

Python owns admission and user intent. The separately running native guardian
owns mounts, the input lease, stop latches and recovery without this interpreter.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import select
import stat
import struct
import subprocess
import sys
import tempfile
import time
import uuid

STATE = Path('/var/lib/clean-your-tv-root')
TARGET = Path('/usr/bin/com.webos.app.home')
CHECKPOINTS = (Path('/mnt/lg/cmn_data/checkpoint/com.webos.app.home'),
               Path('/tmp/checkpoint/com.webos.app.home'))
VOLATILE = Path('/tmp/clean-your-tv-root-gate/gate')
BACKEND = 'c1-native-gate'
APP = 'com.cleanyourtv.root.preview'
TOKEN = re.compile(r'[a-f0-9]{32}')
DIGEST = re.compile(r'[a-f0-9]{64}')
VERSION = re.compile(r'\d{1,3}\.\d{1,3}\.\d{1,3}(?:-[A-Za-z0-9.]+)?')


def trusted_directory(path, uid=0):
    path = Path(path)
    for parent in (path, *path.parents):
        info = parent.lstat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid not in (0, uid)
                or info.st_mode & 0o022 and not (parent != path and info.st_mode & stat.S_ISVTX)):
            raise ValueError('Unsafe experimental backend directory')


def secure(path, uid=0, limit=65536):
    path = Path(path)
    trusted_directory(path.parent, uid)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != uid or info.st_nlink != 1
                or info.st_mode & 0o022 or info.st_size > limit):
            raise ValueError('Unsafe experimental backend file')
        data = stream.read(limit + 1)
        if len(data) > limit:
            raise ValueError('Oversized experimental backend file')
        return data


def atomic(path, value, uid=0, raw=False):
    path = Path(path)
    trusted_directory(path.parent, uid)
    if os.path.lexists(path):
        secure(path, uid)
    data = value if raw else (json.dumps(value, sort_keys=True) + '\n').encode()
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.gate-')
    try:
        with os.fdopen(fd, 'wb') as out:
            os.fchmod(out.fileno(), 0o600)
            out.write(data); out.flush(); os.fsync(out.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try: os.fsync(directory)
        finally: os.close(directory)
    finally:
        if os.path.lexists(temporary): os.unlink(temporary)


def admission_valid(value):
    if not isinstance(value, dict) or set(value) != {'model', 'firmware', 'webos', 'target_sha256', 'target'}:
        return False
    target = value['target']
    return (isinstance(value['model'], str)
            and re.fullmatch(r'OLED(?:48|55|65|77|83)C1[A-Z0-9]{2,12}', value['model']) is not None
            and isinstance(value['firmware'], str) and VERSION.fullmatch(value['firmware']) is not None
            and isinstance(value['webos'], str) and VERSION.fullmatch(value['webos']) is not None
            and value['webos'].startswith('6.')
            and isinstance(value['target_sha256'], str) and DIGEST.fullmatch(value['target_sha256']) is not None
            and isinstance(target, dict) and set(target) == {'dev', 'ino', 'size', 'mtime_ns'}
            and all(type(v) is int and 0 <= v < 2**63 for v in target.values())
            and target['ino'] > 0 and target['size'] >= 52)


def selection(root=STATE, uid=0):
    path = Path(root) / 'home-backend.json'
    if not os.path.lexists(path):
        if any(os.path.lexists(Path(root) / name) for name in ('c1-gate', 'c1-keyfilter', 'runtime/c1-home-gate', 'runtime/c1-keyfilter-guard', 'runtime/c1_gate.py', 'runtime/c1_keyfilter.py')):
            raise ValueError('Missing experimental Home backend selection; retain recovery evidence')
        return None
    value = json.loads(secure(path, uid, 8192))
    if isinstance(value, dict) and type(value.get('schema')) is int and value['schema'] in (2,3):
        if __package__:
            from . import c1_keyfilter
        else:
            import c1_keyfilter
        return c1_keyfilter.selection(root, uid)
    if (not isinstance(value, dict)
            or set(value) != {'schema', 'backend', 'experimental', 'native_sha256', 'admission'}
            or type(value['schema']) is not int or value['schema'] != 1
            or value['backend'] != BACKEND or value['experimental'] is not True
            or not isinstance(value['native_sha256'], str) or not DIGEST.fullmatch(value['native_sha256'])
            or not admission_valid(value['admission'])):
        raise ValueError('Invalid experimental Home backend selection; retain recovery evidence')
    return value


def admit(info, elf, pointer_bits=None):
    """Validate actual observations, never a missing-service error code."""
    bits = struct.calcsize('P') * 8 if pointer_bits is None else pointer_bits
    if (not isinstance(info, dict) or info.get('returnValue') is not True or bits != 32
            or len(elf) < 52 or elf[:7] != b'\x7fELF\x01\x01\x01'
            or int.from_bytes(elf[18:20], 'little') != 40):
        raise ValueError('Experimental C1 backend requires an observed ARM32 native Home')
    values = {key: info.get(field) for key, field in
              (('model', 'modelName'), ('firmware', 'firmwareVersion'), ('webos', 'sdkVersion'))}
    placeholder = dict(values, target_sha256='0' * 64,
                       target={'dev': 0, 'ino': 1, 'size': len(elf), 'mtime_ns': 0})
    if not admission_valid(placeholder):
        raise ValueError('Experimental C1 backend requires an exact C1 / webOS 6 identity')
    return values


def luna(uri, payload, timeout=5):
    # Share the existing bounded transport: this firmware needs stdin held open
    # until the first reply. A run(input=b'') would close it prematurely.
    from runtime.transport import call
    return call(uri, payload, timeout=timeout)


def checkpoint_preflight(uid=0):
    """Mirror native path admission early; never authorize or repair a mount."""
    for path in CHECKPOINTS:
        try:
            info = path.lstat()
        except FileNotFoundError:
            continue  # Native admission also skips absent optional checkpoints.
        try:
            if not stat.S_ISDIR(info.st_mode) or info.st_uid != uid or info.st_mode & 0o022:
                raise ValueError('Unsafe checkpoint leaf')
            trusted_directory(path, uid)
        except (ValueError, OSError):
            raise ValueError('Unsafe C1 checkpoint path; setup/activation stopped. '
                             'Keep vendor permissions and recovery data unchanged.') from None


def probe():
    if os.geteuid() != 0 or sys.platform != 'linux':
        raise ValueError('Experimental C1 admission requires an existing root TV session')
    checkpoint_preflight()
    data = secure(TARGET, limit=4 * 1024 * 1024)
    before = TARGET.stat()
    info = luna('luna://com.webos.service.tv.systemproperty/getSystemInfo',
                {'keys': ['modelName', 'firmwareVersion', 'sdkVersion']})
    result = admit(info, data)
    after = TARGET.stat()
    identity = lambda st: dict(dev=st.st_dev, ino=st.st_ino, size=st.st_size, mtime_ns=st.st_mtime_ns)
    if identity(before) != identity(after) or not before.st_mode & 0o111:
        raise ValueError('Native Home changed during admission')
    return dict(result, target_sha256=hashlib.sha256(data).hexdigest(), target=identity(after))


def boot_identity():
    value = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    if str(uuid.UUID(value)) != value: raise ValueError('Invalid boot identity')
    return value


def write_config(root, admission, token, uid=0):
    import fcntl
    t = admission['target']
    content = ('CYTV-C1-GATE-1\ntoken ' + token + '\nboot ' + boot_identity()
               + '\ndev ' + str(t['dev']) + '\nino ' + str(t['ino'])
               + '\nsize ' + str(t['size']) + '\nmtime_ns ' + str(t['mtime_ns']) + '\n').encode()
    # Serialize token publication with native journal/inverse writes. The Python
    # lifecycle lock alone cannot exclude an independently running guardian.
    directory = Path(root) / 'c1-gate'
    trusted_directory(directory, uid)
    fd = os.open(directory / 'lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != uid
                or info.st_nlink != 1 or info.st_mode & 0o077):
            raise ValueError('Unsafe native configuration lock')
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        atomic(directory / 'config', content, uid, raw=True)
    finally:
        os.close(fd)


def prepare(root, native_sha256, admission, uid=0):
    root = Path(root)
    if os.path.lexists(root / 'home-backend.json') or os.path.lexists(root / 'c1-gate'):
        raise ValueError('Experimental backend already prepared; retain its evidence')
    value = dict(schema=1, backend=BACKEND, experimental=True,
                 native_sha256=native_sha256, admission=admission)
    if not admission_valid(admission) or not DIGEST.fullmatch(native_sha256):
        raise ValueError('Invalid experimental admission')
    trusted_directory(root, uid)
    (root / 'c1-gate').mkdir(mode=0o700)
    atomic(root / 'home-backend.json', value, uid)
    token = uuid.uuid4().hex
    write_config(root, admission, token, uid)
    write_intent(root, False, token, 'disabled', uid)
    return value


def read_intent(root=STATE, uid=0):
    try: value = json.loads(secure(Path(root) / 'c1-gate/intent.json', uid, 4096))
    except FileNotFoundError: return None
    if (not isinstance(value, dict) or set(value) != {'schema', 'enabled', 'phase', 'token', 'boot'}
            or type(value['schema']) is not int or value['schema'] != 1
            or type(value['enabled']) is not bool
            or value['phase'] not in ('disabled', 'starting', 'active', 'trial', 'recovering')
            or not isinstance(value['token'], str) or not TOKEN.fullmatch(value['token'])
            or not isinstance(value['boot'], str) or str(uuid.UUID(value['boot'])) != value['boot']):
        raise ValueError('Invalid experimental Home intent')
    return value


def write_intent(root, enabled, token, phase, uid=0):
    value = dict(schema=1, enabled=enabled, phase=phase, token=token, boot=boot_identity())
    atomic(Path(root) / 'c1-gate/intent.json', value, uid)
    return value


def binary(root=STATE, uid=0):
    saved = selection(root, uid)
    if saved is None: raise ValueError('Experimental backend was not explicitly selected')
    for path in (Path(root) / 'runtime/c1-home-gate', VOLATILE):
        try:
            raw = secure(path, uid, 4 * 1024 * 1024)
            if hashlib.sha256(raw).hexdigest() == saved['native_sha256'] and path.stat().st_mode & 0o111:
                return path
        except FileNotFoundError: pass
    raise ValueError('Verified native recovery executable unavailable; retain state')


def stage_volatile(root, uid, digest):
    # Never replace the source inode: the native recovery journal pins it.
    source = secure(Path(root) / 'runtime/c1-home-gate', uid, 4 * 1024 * 1024)
    if hashlib.sha256(source).hexdigest() != digest:
        raise ValueError('Native Home recovery identity changed')
    directory = VOLATILE.parent
    directory.mkdir(mode=0o700, exist_ok=True)
    trusted_directory(directory, uid)
    info = directory.lstat()
    if info.st_uid != uid or stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError('Unsafe volatile recovery directory')
    if not os.path.lexists(VOLATILE):
        fd, temporary = tempfile.mkstemp(dir=directory, prefix='.stage-')
        try:
            with os.fdopen(fd, 'wb') as out:
                out.write(source)
                out.flush()
                os.fchmod(out.fileno(), 0o755)
                os.fsync(out.fileno())
            os.link(temporary, VOLATILE)  # Fails if another publisher created the name.
        finally:
            os.unlink(temporary)
    if (secure(VOLATILE, uid, 4 * 1024 * 1024) != source or
            not VOLATILE.lstat().st_mode & 0o111):
        raise ValueError('Volatile native Home identity mismatch; retain evidence')


def stock_running(target):
    for process in Path('/proc').iterdir():
        if not process.name.isdecimal():
            continue
        try:
            info = (process / 'exe').stat()
        except (FileNotFoundError, ProcessLookupError):
            continue  # Exited process or kernel thread with no executable.
        if (info.st_dev, info.st_ino) == (target['dev'], target['ino']):
            if (info.st_size, info.st_mtime_ns) != (target['size'], target['mtime_ns']):
                raise ValueError('Running stock Home identity changed')
            return True
    return False


def foreground(timeout=5):
    reply = luna('luna://com.webos.applicationManager/getForegroundAppInfo', {}, timeout=timeout)
    app = reply.get('appId') if isinstance(reply, dict) and reply.get('returnValue') is True else None
    if not isinstance(app, str) or not re.fullmatch(r'[A-Za-z0-9._-]{0,255}', app):
        raise ValueError('Cannot verify foreground during native Home activation')
    return app


def retire_stock(target):
    if not stock_running(target):
        return
    stock = 'com.webos.app.home'
    before = foreground()
    # SAM acknowledges submission immediately. On C1 the old executable can
    # remain alive another 9–10 seconds, independently of that acknowledgement.
    reply = luna('luna://com.webos.applicationManager/closeByAppId', {'id': stock, 'forceMode': True})
    if not isinstance(reply, dict) or reply.get('returnValue') is not True:
        raise ValueError('Could not close running stock Home')
    submitted = time.monotonic()
    while stock_running(target):
        if time.monotonic() >= submitted + 18:
            raise ValueError('Running stock Home remained after SAM close')
        time.sleep(.25)
    if before not in ('', stock):
        return  # A preloaded stock process need not displace another foreground app.
    # SAM's idle relaunch invokes the mounted gate. An independent launch here
    # could race that invocation and reopen Home over the user's next selection.
    while True:
        remaining = submitted + 23 - time.monotonic()
        if remaining <= 0:
            raise ValueError('SAM foreground did not settle after closing stock Home')
        settled = foreground(timeout=min(5, remaining)) not in ('', stock)
        remaining = submitted + 23 - time.monotonic()
        if not settled and remaining > 0:
            # Root is an overlay: SAM may keep reporting Home underneath it.
            # The compositor lists visible surfaces; its API does not require
            # a separate visible flag. Reject an explicit hidden surface.
            reply = luna('luna://com.webos.surfacemanager/getForegroundAppInfo', {},
                         timeout=min(5, remaining))
            surfaces = reply.get('foregroundAppInfo') if isinstance(reply, dict) else None
            if (isinstance(reply, dict) and reply.get('returnValue') is True
                    and isinstance(surfaces, list) and len(surfaces) <= 128
                    and all(isinstance(surface, dict)
                        and isinstance(surface.get('appId'), str)
                        and isinstance(surface.get('windowType'), str) for surface in surfaces)):
                settled = any(isinstance(surface, dict)
                    and surface.get('appId') == APP
                    and surface.get('windowType') == '_WEBOS_WINDOW_TYPE_OVERLAY'
                    and surface.get('visible', True) is True
                    and type(surface.get('displayId', 0)) is int
                    and surface.get('displayId', 0) == 0 for surface in surfaces)
        # A restored CRIU executable must never be mistaken for a successful
        # handoff, including when Root is already visible over that executable.
        if stock_running(target):
            raise ValueError('Running stock Home reappeared after SAM close')
        if settled and time.monotonic() < submitted + 23:
            return
        time.sleep(min(.25, max(0, submitted + 23 - time.monotonic())))


def native(args, root=STATE, uid=0):
    helper = binary(root, uid)
    reply = subprocess.run([str(helper), *args], stdin=subprocess.DEVNULL,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           env={'PATH': '/usr/bin:/bin', 'LANG': 'C'}, timeout=12, check=False)
    if len(reply.stdout) > 16384: raise ValueError('Oversized native recovery reply')
    value = json.loads(reply.stdout)
    if reply.returncode or not isinstance(value, dict) or value.get('returnValue') is not True:
        raise ValueError('Native recovery did not confirm success; retain state')
    return value


def validate_native(value):
    fields = ('mounted', 'healthy', 'stock_verified', 'stopped')
    if (not isinstance(value, dict) or value.get('returnValue') is not True
            or value.get('backend') != BACKEND or value.get('profiles', {}) is not None
            or value.get('state') not in ('armed', 'stock', 'stopped', 'blocked')
            or any(type(value.get(key)) is not bool for key in fields)
            or not isinstance(value.get('token'), str) or not TOKEN.fullmatch(value['token'])
            or type(value.get('guardian_pid')) is not int or value['guardian_pid'] < 0
            or not isinstance(value.get('reason'), str) or not re.fullmatch(r'[a-z0-9_-]{0,80}', value['reason'])
            or value['stock_verified'] and value['mounted']
            or value['state'] == 'stock' and value['mounted']
            or value['healthy'] and (not value['mounted'] or value['guardian_pid'] == 0 or value['stopped'])):
        raise ValueError('Incomplete or inconsistent native Home proof')
    return value


def verify_ready():
    from provision import verify
    return verify()


def status(root=STATE, uid=0):
    if selection(root, uid) is None: raise ValueError('Experimental backend not selected')
    value = validate_native(native(['--status'], root, uid))
    intent = read_intent(root, uid)
    active = bool(intent and intent['phase'] in ('active', 'trial') and value['healthy'] and not value['stopped']
                  and intent['token'] == value['token'])
    phase = ('trial' if intent['phase'] == 'trial' else 'active') if active else 'disabled' if value['stock_verified'] else 'recovering'
    projected = dict(intent or {}, phase=phase, enabled=bool(active and intent['enabled']))
    try: recovery = verify_ready()
    except (OSError, ValueError, RuntimeError, ImportError): recovery = {'integrity_verified': False}
    return dict(backend=BACKEND, experimental=True, effective=dict(value), intent=projected,
                recovery=recovery, candidate=APP, update_home_resume_available=False,
                persistent_enable_available=recovery.get('integrity_verified') is True)


@contextmanager
def operation(root=STATE, uid=0):
    import fcntl
    path = Path(root) / 'c1-gate/operation.lock'
    trusted_directory(path.parent, uid)
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != uid or info.st_nlink != 1 or info.st_mode & 0o022:
            raise ValueError('Unsafe experimental control lock')
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally: os.close(fd)


def restore(root=STATE, uid=0):
    with operation(root, uid):
        return restore_locked(root, uid)


def restore_locked(root, uid):
    # Native release and latch must run even when the Python intent is corrupt
    # or cannot be persisted. Only acknowledge Off after both readbacks.
    native(['--restore'], root, uid)
    after = validate_native(native(['--status'], root, uid))
    if (not after['stock_verified'] or after['mounted'] or after['healthy']
            or not after['stopped'] or after['guardian_pid'] != 0):
        raise ValueError('Original Home and stop latch not verified; retain experimental recovery state')
    write_intent(root, False, after['token'], 'disabled', uid)
    return 'restored'


def enable(root=STATE, uid=0, seconds=0):
    root = Path(root)
    if type(seconds) is not int or not 0 <= seconds <= 60:
        raise ValueError('Invalid experimental trial duration')
    with operation(root, uid):
        return enable_locked(root, uid, seconds)


def enable_locked(root, uid, seconds, resume_token=None):
    descriptor = selection(root, uid)
    verify_ready()
    current = validate_native(native(['--status'], root, uid))
    previous = read_intent(root, uid)
    if resume_token is not None and (current['token'] != resume_token or current['stopped']
            or not previous or previous['token'] != resume_token or not previous['enabled']
            or previous['phase'] != 'active' or previous['boot'] == boot_identity()):
        return restore_locked(root, uid)
    if current['healthy']:
        if (not seconds and previous and previous['enabled'] and previous['phase'] == 'active'
                and previous['token'] == current['token']):
            return status(root, uid)
        raise ValueError('Restore the active Home attempt before starting a different mode')
    if not current['stock_verified'] or current['mounted'] or current['guardian_pid']:
        raise ValueError('Restore the previous Home attempt before enabling the experiment')
    if probe() != descriptor['admission']:
        raise ValueError('C1 firmware or native Home changed; new experimental admission required')
    from helper_bridge import require_idle
    require_idle()
    helper = binary(root, uid)
    stage_volatile(root, uid, descriptor['native_sha256'])
    token = uuid.uuid4().hex
    write_config(root, descriptor['admission'], token, uid)
    input_read = input_write = ready_read = ready_write = log = None
    observer = guard = None
    try:
        write_intent(root, seconds == 0, token, 'starting', uid)
        input_read, input_write = os.pipe()
        ready_read, ready_write = os.pipe()
        log = os.open(root / 'c1-gate/native.log', os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
        info = os.fstat(log)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != uid or info.st_nlink != 1 or info.st_mode & 0o077:
            raise ValueError('Unsafe experimental recovery log')
        from python_binding import command
        observer = subprocess.Popen([command(root), str(root / 'runtime/emergency_reader.py'), str(input_write)],
            pass_fds=(input_write,), stdin=subprocess.DEVNULL, stdout=log, stderr=log,
            start_new_session=True, close_fds=True)
        os.close(input_write); input_write = None
        guard = subprocess.Popen([str(helper), '--guard', token, str(input_read), str(ready_write), str(seconds)],
            pass_fds=(input_read, ready_write), stdin=subprocess.DEVNULL, stdout=log, stderr=log,
            env={'PATH': '/usr/bin:/bin', 'LANG': 'C'}, start_new_session=True, close_fds=True)
        os.close(input_read); input_read = None
        os.close(ready_write); ready_write = None
        deadline = time.monotonic() + 10
        response = b''
        while time.monotonic() < deadline:
            if guard.poll() is not None or observer.poll() is not None: break
            if select.select([ready_read], [], [], .1)[0]:
                chunk = os.read(ready_read, 256)
                if not chunk: break
                response += chunk
                if len(response) > 128: break
                if b'\n' in response: break
        after = validate_native(native(['--status'], root, uid))
        if (response != ('ARMED ' + token + '\n').encode() or guard.poll() is not None
                or observer.poll() is not None or not after['healthy'] or after['token'] != token):
            raise ValueError('Independent native protection did not confirm activation')
        retire_stock(descriptor['admission']['target'])
        after = validate_native(native(['--status'], root, uid))
        if not after['healthy'] or after['token'] != token:
            raise ValueError('Native protection stopped while releasing preloaded Home')
        write_intent(root, seconds == 0, token, 'active' if not seconds else 'trial', uid)
        result = status(root, uid)
        if not result['effective']['healthy'] or result['effective']['token'] != token:
            raise ValueError('Native protection stopped before activation completed')
        return result
    except BaseException:
        try: restore_locked(root, uid)
        finally:
            for child in (observer, guard):
                if child is not None and child.poll() is None:
                    child.terminate()
                    try: child.wait(timeout=3)
                    except subprocess.TimeoutExpired: child.kill(); child.wait(timeout=1)
        raise
    finally:
        for fd in (input_read, input_write, ready_read, ready_write, log):
            if fd is not None: os.close(fd)


def execute(mode, transaction=None, root=STATE, uid=0):
    # Dispatch compositor schemas without changing schema 1 recovery ordering.
    # Native/binary authority still rejects any missing or orphaned selection.
    selected = selection(root, uid) if os.path.lexists(Path(root)/'home-backend.json') else None
    if selected and selected.get('routing') == 'compositor-keyfilter-v1':
        if __package__:
            from . import c1_keyfilter
        else:
            import c1_keyfilter
        return c1_keyfilter.execute(mode, transaction, root, uid)
    if mode == 'status': return status(root, uid)
    if mode == 'restore': return restore(root, uid)
    if mode == 'enable': return enable(root, uid)
    if mode in ('trial', 'intent-trial', 'emergency-trial'): return enable(root, uid, seconds=60)
    if mode == 'boot':
        from boot_gate import wait
        root = Path(root)
        normal = wait()
        with operation(root, uid):
            if not normal:
                return restore_locked(root, uid)
            try:
                intent = read_intent(root, uid)
                current = validate_native(native(['--status'], root, uid))
                boot = boot_identity()
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
                return restore_locked(root, uid)
            if (intent and intent['phase'] == 'active' and intent['enabled']
                    and intent['token'] == current['token'] and not current['stopped']):
                if current['healthy'] and intent['boot'] == boot:
                    return status(root, uid)
                if intent['boot'] != boot and current['stock_verified'] and not current['guardian_pid']:
                    return enable_locked(root, uid, 0, resume_token=intent['token'])
            # A same-boot dead guardian, orphan/uncertain attempt, an explicit
            # stop, or an interrupted trial must release, never automatically rearm.
            return restore_locked(root, uid)
    raise ValueError('Experimental C1 backend does not support this lifecycle operation; restore and use its developer bundle')
