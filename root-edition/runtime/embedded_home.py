"""Embedded LG Home adapter for the shared C1 guardian and lifecycle."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import select
import stat
import subprocess
import sys
import time

COMPOSITOR = Path('/usr/bin/surface-manager-starfish')
INITCTL = Path('/sbin/initctl')
JOB = Path('/etc/init/surface-manager.conf')
STOCK_QML = 'qrc:///main.qml'
ADAPTER = 'embedded-qml-v1'
ASSETS = ('embedded_home.py', 'embedded-home.qml', 'embedded-home.js', 'c1-home-filter.js')


def backend():
    try:
        from . import c1_keyfilter
    except ImportError:
        import c1_keyfilter
    return c1_keyfilter


def path(root, name):
    return backend().private_directory(root) / name


def wrapper_url(root):
    return (Path(root) / 'runtime/embedded-home.qml').as_uri()


def trusted_executable(executable):
    backend().legacy.trusted_directory(executable.parent)
    info = executable.lstat()
    if (not stat.S_ISREG(info.st_mode) or not info.st_mode & 0o111
            or info.st_uid != 0 or info.st_mode & 0o022):
        raise ValueError('Untrusted compositor launch executable')


def run(*args):
    # Recovery also executes this path without a preceding admission probe.
    trusted_executable(INITCTL)
    trusted_executable(COMPOSITOR)
    return subprocess.run(
        [str(INITCTL), *args], check=True, capture_output=True,
        timeout=12, env={'PATH': '/usr/bin:/bin', 'LANG': 'C'},
    ).stdout.decode('ascii', 'strict')


def current(root):
    value = run('status', 'surface-manager').strip()
    match = re.fullmatch(r'surface-manager start/running, process ([1-9][0-9]*)', value)
    if match is None:
        raise ValueError('Running compositor job unavailable')
    pid = int(match[1])
    process = Path('/proc') / str(pid)
    start = backend().process_start(pid)
    if process.joinpath('exe').resolve(strict=True) != COMPOSITOR:
        raise ValueError('Unexpected compositor job executable')
    with process.joinpath('environ').open('rb') as stream:
        raw = stream.read(65537)
    if len(raw) > 65536:
        raise ValueError('Oversized compositor environment')
    values = [item.split(b'=', 1)[1] for item in raw.split(b'\0')
              if item.startswith(b'LSM_MAIN_QML=')]
    if len(values) > 1:
        raise ValueError('Ambiguous compositor entry file')
    selected = values[0].decode('ascii', 'strict') if values else STOCK_QML
    if selected not in ('', STOCK_QML, wrapper_url(root)):
        raise ValueError('Foreign compositor entry file; preserve its installation')
    if (backend().process_start(pid) != start
            or process.joinpath('exe').resolve(strict=True) != COMPOSITOR
            or run('status', 'surface-manager').strip() != value):
        raise ValueError('Compositor process changed during observation')
    return pid, selected or STOCK_QML


def capabilities(root):
    k = backend()
    if Path('/proc/1/exe').resolve(strict=True).name != 'init.upstart':
        raise ValueError('Embedded Home requires the running Upstart manager')
    for executable in (INITCTL, COMPOSITOR):
        trusted_executable(executable)
    job = k.secure(JOB, limit=65536)
    if (job.count(b'/usr/bin/surface-manager-starfish') != 1
            or b'LSM_MAIN_QML' in job or b'respawn' not in job
            or not re.search(rb'^\s*exec\s+[^\n]*?/usr/bin/surface-manager-starfish(?:\s|$)', job, re.M)):
        raise ValueError('Unsupported compositor launch job')
    help_text = run('help')
    if not all(re.search(r'^\s*' + verb + r'\s', help_text, re.M)
               for verb in ('start', 'stop', 'status')):
        raise ValueError('Bounded compositor job operations unavailable')
    pid, selected = current(root)
    return hashlib.sha256(job).hexdigest(), pid, selected


def probe(root=None):
    k = backend()
    root = k.STATE if root is None else Path(root)
    before = COMPOSITOR.stat()
    data = k.legacy.native_home(target=COMPOSITOR)
    if (data[:7] != b'\x7fELF\x01\x01\x01' or data[18:20] != b'\x28\0'
            or b'LSM_MAIN_QML\0' not in data or b'qrc:///main.qml\0' not in data):
        raise ValueError('Embedded compositor entry-file capability unavailable')
    capabilities(root)
    k.require_generic_environment(embedded_target=COMPOSITOR)
    reply = k.luna('luna://com.webos.service.tv.systemproperty/getSystemInfo',
                   {'keys': ['modelName', 'firmwareVersion', 'sdkVersion']})
    identity = lambda info: dict(dev=info.st_dev, ino=info.st_ino,
                                 size=info.st_size, mtime_ns=info.st_mtime_ns)
    after = COMPOSITOR.stat()
    result = dict(
        model=reply.get('modelName'), firmware=reply.get('firmwareVersion'),
        webos=reply.get('sdkVersion'), target_sha256=hashlib.sha256(data).hexdigest(),
        target=identity(after),
    )
    if (reply.get('returnValue') is not True or identity(before) != identity(after)
            or not k.admission_valid(result)):
        raise ValueError('Compositor identity changed or is unreadable')
    return result


def matches(admission):
    return (not os.path.lexists(backend().legacy.TARGET)
            and hashlib.sha256(backend().legacy.native_home(target=COMPOSITOR)).hexdigest()
            == admission['target_sha256'])


def attached(root):
    _, selected = current(root)
    if selected != wrapper_url(root):
        return False
    reply = backend().luna(
        'luna://com.webos.cleanyourtv.root.lease/c1AdapterStatus', {}, timeout=.5, named=True)
    return reply == dict(returnValue=True, adapter=ADAPTER, attached=True)


def receipt(root):
    file = path(root, 'embedded-launch.json')
    try:
        value = json.loads(backend().secure(file, limit=4096))
    except FileNotFoundError:
        return None
    if (not isinstance(value, dict) or set(value) != {'schema', 'boot', 'job_sha256', 'phase'}
            or value['schema'] != 1 or type(value['schema']) is not int
            or not isinstance(value['boot'], str)
            or not re.fullmatch(r'[0-9a-f-]{36}', value['boot'])
            or not isinstance(value['job_sha256'], str)
            or not re.fullmatch(r'[0-9a-f]{64}', value['job_sha256'])
            or value['phase'] not in ('attaching', 'attached', 'restoring', 'stock', 'failed')):
        raise ValueError('Invalid embedded compositor recovery record')
    return value


def record(root, phase):
    k = backend()
    prior = receipt(root)
    digest = hashlib.sha256(k.secure(JOB, limit=65536)).hexdigest()
    if prior and prior['job_sha256'] != digest:
        raise ValueError('Compositor job changed; retain recovery record')
    k.atomic(path(root, 'embedded-launch.json'), dict(
        schema=1, boot=k.boot_identity(), job_sha256=digest, phase=phase,
    ))


@contextmanager
def transition_lock(root):
    fd = os.open(path(root, 'embedded-transition.lock'),
                 os.O_CREAT | os.O_NOFOLLOW | os.O_RDWR, 0o600)
    try:
        deadline = time.monotonic() + 100
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise ValueError('Embedded compositor transition busy; retain recovery data')
                time.sleep(.05)
        yield
    finally:
        os.close(fd)


def check_cancelled(fd):
    if fd is not None and select.select([fd], [], [], 0)[0]:
        # Both an explicit cancellation byte and parent death (EOF) cancel.
        os.read(fd, 1)
        raise ValueError('Embedded compositor attachment cancelled')


def transition(root, selected):
    if selected not in (STOCK_QML, wrapper_url(root)):
        raise ValueError('Unexpected embedded compositor entry file')
    pid, previous = current(root)
    if previous == selected:
        return
    start = backend().process_start(pid)
    if current(root) != (pid, previous) or backend().process_start(pid) != start:
        raise ValueError('Compositor instance changed before transition')
    run('stop', 'surface-manager')
    # Per-instance environment is discarded on the next ordinary stock boot.
    run('start', 'surface-manager', 'LSM_MAIN_QML=' + selected)
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        try:
            if current(root)[1] == selected:
                return
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
        time.sleep(.1)
    raise ValueError('Compositor launch readback timed out')


def restore(root):
    with transition_lock(root):
        restore_locked(root)


def restore_locked(root):
    record(root, 'restoring')
    try:
        # An interrupted stop may leave the job stopped.
        try:
            selected = current(root)[1]
        except ValueError:
            if run('status', 'surface-manager').strip() != 'surface-manager stop/waiting':
                raise
            selected = None
        if selected is None:
            run('start', 'surface-manager', 'LSM_MAIN_QML=' + STOCK_QML)
        else:
            transition(root, STOCK_QML)
        if current(root)[1] != STOCK_QML:
            raise ValueError('Stock compositor restoration unverified')
        record(root, 'stock')
    except BaseException:
        record(root, 'failed')
        raise


def supervise(root, ready, cancel=None):
    """Rollback an interrupted attachment; resident QML later fails open itself."""
    k = backend()
    lock = os.open(path(root, 'embedded-watch.lock'), os.O_CREAT | os.O_NOFOLLOW | os.O_RDWR, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with transition_lock(root):
            for name in ASSETS:
                k.secure(Path(root) / 'runtime' / name, limit=256 * 1024)
            if k.verify_ready().get('integrity_verified') is not True:
                raise ValueError('Recovery integrity unavailable')
            check_cancelled(cancel)
            record(root, 'attaching')
            try:
                transition(root, wrapper_url(root))
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    check_cancelled(cancel)
                    if attached(root):
                        check_cancelled(cancel)
                        record(root, 'attached')
                        os.write(ready, b'ATTACHED\n')
                        os.close(ready)
                        ready = None
                        break
                    time.sleep(.1)
                else:
                    raise ValueError('Embedded policy attachment timed out')
            except BaseException:
                restore_locked(root)
                raise
        # A controller/broker lease loss is handled by the resident policy and
        # native guardian. Never restart LG's compositor for that event.
        while receipt(root)['phase'] == 'attached' and current(root)[1] == wrapper_url(root):
            time.sleep(.5)
    finally:
        if ready is not None:
            os.close(ready)
        if cancel is not None:
            os.close(cancel)
        os.close(lock)


def install(root, uid=0):
    k = backend()
    if uid != 0:
        raise ValueError('Embedded launch requires root')
    capabilities(root)
    previous = receipt(root)
    if previous and previous['phase'] not in ('stock', 'attached'):
        raise ValueError('Restore interrupted compositor launch before enabling')
    if attached(root):
        return
    from python_binding import command
    read, write = os.pipe()
    cancel_read, cancel_write = os.pipe()
    child = None
    try:
        child = subprocess.Popen(
            [command(root), str(Path(root) / 'runtime/embedded_home.py'), '--supervise', str(write), str(cancel_read)],
            pass_fds=(write, cancel_read), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, start_new_session=True, close_fds=True)
        os.close(write)
        write = None
        os.close(cancel_read)
        cancel_read = None
        k.read_handshake(read, b'ATTACHED\n', [child], seconds=60)
    except BaseException:
        # Do not race rollback against a detached child still changing the job.
        os.close(cancel_write)
        cancel_write = None
        if child is not None:
            try:
                child.wait(timeout=65)
            except subprocess.TimeoutExpired as error:
                raise ValueError('Compositor rollback still running; retain recovery data') from error
        raise
    finally:
        os.close(read)
        if write is not None:
            os.close(write)
        if cancel_read is not None:
            os.close(cancel_read)
        if cancel_write is not None:
            os.close(cancel_write)


def remove(root):
    with transition_lock(root):
        restore_locked(root)
        # Retain evidence while the supervisor observes the new stock process.
        file = path(root, 'embedded-watch.lock')
        if file.exists():
            fd = os.open(file, os.O_NOFOLLOW | os.O_RDWR)
            try:
                deadline = time.monotonic() + 3
                while True:
                    try:
                        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except BlockingIOError:
                        if time.monotonic() >= deadline:
                            raise ValueError('Compositor launcher has not retired')
                        time.sleep(.05)
            finally:
                os.close(fd)
        if current(root)[1] != STOCK_QML:
            raise ValueError('Stock compositor readback changed')



if __name__ == '__main__':
    if (os.geteuid() != 0 or len(sys.argv) != 4 or sys.argv[1] != '--supervise'
            or not sys.argv[2].isdigit() or not sys.argv[3].isdigit()):
        raise SystemExit('Private compositor launch channel required')
    supervise(Path(__file__).resolve().parent.parent, int(sys.argv[2]), int(sys.argv[3]))
