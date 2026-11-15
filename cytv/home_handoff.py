"""Install-time handoff for a proven native Home bind and its startup registrations."""

import json
import re

from .errors import UserError

PENDING_CHECK = (
    'if [ -e /var/lib/clean-your-tv-home-handoff/pending ] || '
    '[ -L /var/lib/clean-your-tv-home-handoff/pending ]; then printf CYTV_HOME_HANDOFF_PENDING; fi'
)


# Runs over the authenticated SSH connection using the normal Root Python runtime.
# Keep discovery and mutation in the same program so apply can recheck the plan.
PROGRAM = r"""
import ctypes
import errno
import fcntl
import hashlib
import json
import os
import re
import select
import shlex
import stat
import subprocess
import sys
import time
from pathlib import Path, PurePosixPath

ROOT = Path('/')
OWNER = 0
HOME = '/usr/bin/com.webos.app.home'
APP_ID = 'com.webos.app.home'
APP_ROOT = '/media/developer/apps/usr/palm/applications'
BOOT = '/var/lib/webosbrew/init.d'
LS2 = '/var/luna-service2'
ARCHIVE = '/var/lib/clean-your-tv-home-handoff'
RECEIPT = ARCHIVE + '/pending'
KEY = 'com.webos.surfacemanager.keyFilters'
VENDOR = re.compile(r'/usr/lib/(?:qt5/)?qml/KeyFilters/[A-Za-z0-9_-]+\.js')
SAFE_PATH = re.compile(r'/(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+')


def require(condition):
    if not condition:
        raise ValueError('Unverified Home handoff')


def safe_path(value):
    return (isinstance(value, str) and len(value) <= 512 and SAFE_PATH.fullmatch(value)
            and not {'.', '..'}.intersection(value.split('/')))


def local(value):
    return ROOT / value.lstrip('/')


def trusted(path, kind=stat.S_ISREG):
    for parent in (path.parent, *path.parent.parents):
        if parent == ROOT.parent:
            break
        meta = parent.lstat()
        require(stat.S_ISDIR(meta.st_mode) and meta.st_uid == OWNER and not meta.st_mode & 0o022)
    meta = path.lstat()
    require(kind(meta.st_mode) and meta.st_uid == OWNER)
    if kind != stat.S_ISLNK:
        require(not meta.st_mode & 0o022 and (kind != stat.S_ISREG or meta.st_nlink == 1))
    return meta


def read_file(path, metadata, limit):
    keys = ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_nlink',
            'st_size', 'st_mtime_ns', 'st_ctime_ns')
    identity = tuple(getattr(metadata, key) for key in keys)
    require(stat.S_ISREG(metadata.st_mode) and metadata.st_size <= limit)
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), 'rb') as stream:
        require(tuple(getattr(os.fstat(stream.fileno()), key) for key in keys) == identity)
        value = stream.read(limit + 1)
        require(tuple(getattr(os.fstat(stream.fileno()), key) for key in keys) == identity)
    require(len(value) == metadata.st_size)
    return value


def read(path, limit=262144):
    target = local(path)
    return read_file(target, trusted(target), limit)


def mountinfo():
    with open('/proc/self/mountinfo', encoding='utf-8') as stream:
        text = stream.read(1024*1024 + 1)
    require(len(text) <= 1024*1024)
    rows = []
    for line in text.splitlines():
        left, right = line.split(' - ')
        fields, tail = left.split(), right.split()
        require(len(fields) >= 6 and len(tail) == 3)
        rows.append((fields, tail))
    return rows


def covering(rows):
    return [(fields, tail) for fields, tail in rows if fields[4] == HOME]


def mount_source():
    rows = mountinfo()
    (mounted,) = covering(rows)
    fields, tail = mounted
    require(not any(item.startswith(('shared:', 'master:')) for item in fields[6:]))
    require(tail[0] in ('ext2', 'ext3', 'ext4', 'f2fs', 'tmpfs') and safe_path(fields[3]))
    identity = local(HOME).lstat()
    require(stat.S_ISREG(identity.st_mode) and identity.st_nlink == 1)
    candidates = set()
    mount_root = PurePosixPath(fields[3])
    for source, _ in rows:
        if source[2] != fields[2] or source[4] == HOME:
            continue
        if not all(p == '/' or safe_path(p) for p in (source[3], source[4])):
            continue
        try:
            suffix = mount_root.relative_to(source[3])
        except ValueError:
            continue
        candidate = str(PurePosixPath(source[4]) / suffix)
        if not candidate.startswith((APP_ROOT + '/', '/var/lib/')) or not safe_path(candidate):
            continue
        path = local(candidate)
        if path.resolve(strict=False) != path:
            continue
        try:
            meta = path.lstat()
        except FileNotFoundError:
            continue
        if (meta.st_dev, meta.st_ino) == (identity.st_dev, identity.st_ino):
            candidates.add(candidate)
    (source,) = candidates
    return source, fields, tail, identity.st_dev, identity.st_ino


def device_id(meta):
    return '%d:%d' % (os.major(meta.st_dev), os.minor(meta.st_dev))


def stock_home():
    rows = mountinfo()
    critical = (HOME, '/usr/palm/applications/' + APP_ID + '/appinfo.json')
    system = [(fields, tail) for fields, tail in rows if fields[4] == '/']
    require(len(system) == 1)
    (root, root_tail), = system
    require(root[3] == '/' and root_tail[0] == 'squashfs'
            and re.fullmatch(r'179:[0-9]{1,3}', root[2])
            and all('ro' in options.split(',') and 'rw' not in options.split(',')
                    for options in (root[5], root_tail[2])))
    mounts = [(fields, tail) for fields, tail in rows if fields[4] != '/' and
              any(p == fields[4] or p.startswith(fields[4] + '/') for p in critical)]
    if mounts:
        ((overlay, overlay_tail),) = mounts
        require(overlay[4] == '/usr' and overlay[3] == '/' and overlay_tail[0] == 'overlay')
        options = overlay_tail[2].split(',')
        require('ro' in options and [o for o in options if
                o.startswith(('lowerdir=', 'upperdir=', 'workdir=', 'datadir='))]
                == ['lowerdir=/overlay/bsppart/bsp/usr:/usr'])
        ((bsp, bsp_tail),) = [(f, t) for f, t in rows if f[4] == '/overlay/bsppart']
        require(bsp[3] == '/' and bsp_tail[0] == 'squashfs' and bsp[2] != root[2]
                and re.fullmatch(r'179:[0-9]{1,3}', bsp[2])
                and all('ro' in flags.split(',') and 'rw' not in flags.split(',')
                        for flags in (bsp[5], bsp_tail[2])))
        # Match the runtime proof: the executable comes from the root
        # lower image and the app directory is on the verified BSP overlay.
        parent = trusted(local(critical[1]).parent, stat.S_ISDIR)
        require(device_id(parent) == overlay[2])
        bsp_directory = trusted(local('/overlay/bsppart/bsp/usr'), stat.S_ISDIR)
        require(device_id(bsp_directory) == bsp[2])
    require(device_id(trusted(local(HOME))) == root[2])
    trusted(local(critical[1]))
    mode = local(HOME).lstat().st_mode
    require(mode & 0o111 and not mode & 0o7022)
    app = json.loads(read(critical[1], 65536))
    require(app.get('id') == APP_ID and app.get('type') == 'native'
            and app.get('main') in (HOME, 'file://' + HOME))
    binary = read(HOME, 16*1024*1024)
    require(len(binary) >= 52 and binary[:7] == b'\x7fELF\x01\x01\x01'
            and binary[16:18] in (b'\x02\0', b'\x03\0')
            and binary[18:24] == b'\x28\0\x01\0\0\0'
            and binary[40:44] == b'\x34\0\x20\0'
            and int.from_bytes(binary[28:32], 'little') >= 52 and binary[44:46] != b'\0\0')
    return hashlib.sha256(binary).hexdigest()


def libc_call(name, *args):
    libc = ctypes.CDLL(None, use_errno=True)
    if getattr(libc, name)(*args) != 0:
        raise OSError(ctypes.get_errno(), name)


def unmount():
    libc_call('umount2', os.fsencode(HOME), 0)


def stock_preview():
    # Inspect the real lower file in a private mount namespace. C1 factory
    # firmware has no unshare executable, so call libc from the Root runtime.
    reader, writer = os.pipe()
    child = os.fork()
    if child == 0:
        os.close(reader)
        try:
            libc_call('unshare', 0x00020000)  # CLONE_NEWNS
            libc_call('mount', None, b'/', None, ctypes.c_ulong(0x44000), None)  # MS_REC | MS_PRIVATE
            unmount()
            os.write(writer, stock_home().encode())
        except (OSError, ValueError, TypeError):
            os._exit(1)
        os._exit(0)
    os.close(writer)
    try:
        digest = os.read(reader, 65).decode()
    finally:
        os.close(reader)
        _, status = os.waitpid(child, 0)
    require(status == 0 and re.fullmatch(r'[0-9a-f]{64}', digest))
    return digest


def luna(method, payload):
    # luna-send exits early at EOF on this firmware. Keep stdin open until
    # a complete reply, as the ordinary Root transport does.
    proc = subprocess.Popen(
        ['/usr/bin/luna-send', '-n', '1', 'luna://com.webos.service.config/' + method,
         json.dumps(payload, separators=(',', ':'))],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 5
        reply = b''
        while select.select([proc.stdout], [], [], max(0, deadline-time.monotonic()))[0]:
            chunk = os.read(proc.stdout.fileno(), 4096)
            if not chunk:
                break
            reply += chunk
            require(len(reply) <= 65536 and time.monotonic() <= deadline)
            try:
                result = json.loads(reply)
            except ValueError:
                continue
            require(isinstance(result, dict) and result.get('returnValue') is True)
            return result
        raise TimeoutError('Luna reply unavailable')
    finally:
        if proc.poll() is None:
            proc.terminate()
        try:
            proc.communicate(timeout=1)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()


def read_chain():
    chain = luna('getConfigs', {'configNames':[KEY]})['configs'][KEY]
    require(isinstance(chain, list) and 1 <= len(chain) <= 128 and
            all(isinstance(row, dict) and safe_path(row.get('file')) and
                isinstance(row.get('handler'), str) and
                re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]{0,127}', row['handler']) for row in chain))
    require(len(json.dumps(chain, allow_nan=False).encode()) <= 16384)
    return chain


def write_chain(chain):
    luna('setConfigs', {'configs':{KEY:chain}})
    require(read_chain() == chain)


def rescan():
    subprocess.run(['/usr/sbin/ls-control', 'scan-volatile-dirs'],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=10)


def early_registrations(work, filters):
    names = set()
    for filename in filters:
        source = read(filename).decode()
        names.update(re.findall(
            r"lunaCall\.send\(\s*['\x22]([A-Za-z0-9_.-]+)['\x22]\s*,\s*['\x22]/prepare['\x22]",
            source))
    require(len(names) <= 16)
    paths = []
    for name in sorted(names):
        service = f'{LS2}/services.d/{name}.service'
        if not local(service).exists():
            continue
        body = read(service, 65536).decode()
        executables = re.findall(r'^Exec=(.+)$', body, re.M)
        if len(executables) != 1 or not executables[0].startswith(work + '/'):
            continue
        require(safe_path(executables[0]) and re.findall(r'^Name=(.+)$', body, re.M) == [name])
        trusted(local(executables[0]))
        manifest = f'{LS2}/manifests.d/{name}.json'
        contents = json.loads(read(manifest, 65536))
        require(contents.get('id') == name and contents.get('serviceFiles') == [service])
        role = f'{LS2}/roles.d/{name}.json'
        api = f'{LS2}/api-permissions.d/{name}.json'
        require(contents.get('roleFiles') == [role] and contents.get('apiPermissionFiles') == [api]
                and not (set(contents) - {'id', 'version', 'serviceFiles', 'roleFiles', 'apiPermissionFiles'}))
        permissions = json.loads(read(role, 65536))
        require(permissions.get('exeName') == executables[0] and permissions.get('allowedNames') == [name]
                and permissions.get('permissions') == [{
                    'service':name, 'inbound':['com.webos.starfish.keyfilters'], 'outbound':[],
                }])
        require(json.loads(read(api, 65536)) == {'all':[name + '/prepare']})
        paths.extend((manifest, service, role, api))
    services = local(LS2 + '/services.d')
    if services.is_dir():
        registrations = sorted(services.glob('*.service'))
        require(len(registrations) <= 1024)
        for registration in registrations:
            filename = LS2 + '/services.d/' + registration.name
            if filename not in paths:
                data = read(filename, 65536).decode()
                require(not any(work + '/' in line for line in data.splitlines() if line.startswith('Exec=')))
    return paths


def inspect():
    require(not os.path.lexists(local(RECEIPT)))
    require(not any(os.path.lexists(local(path)) for path in (
        '/var/lib/clean-your-tv-root', '/var/lib/clean-your-tv-installation/operation.json',
        APP_ROOT + '/com.cleanyourtv.root.preview',
        '/media/developer/apps/usr/palm/services/com.cleanyourtv.root.preview.service',
        '/media/developer/apps/usr/palm/packages/com.cleanyourtv.root.preview',
    )))
    mount = mount_source()
    source = mount[0]
    chain = read_chain()
    stock = [row for row in chain if VENDOR.fullmatch(row['file'])]
    require(sum(row['file'].endswith('/systemUi.js') and row['handler'] == 'handleSystemKeys'
                for row in stock) == 1)
    filters = [row['file'] for row in chain if row not in stock]
    files, lock = startup_files(source, filters)
    return {'mount':mount, 'stock_chain':stock, 'chain':chain,
            'files':{filename:path_identity(local(filename)) for filename in files},
            'stock_digest':stock_preview(), 'source_digest':source_digest(source), 'lock':lock}


def startup_files(source, filters):
    owners, direct = {}, []
    entries = sorted(local(BOOT).iterdir())
    require(len(entries) <= 128)
    for path in entries:
        hook = BOOT + '/' + path.name
        if not safe_path(hook):
            continue
        if not path.is_symlink():
            if path.is_file() and not filters and direct_mount(hook, source):
                direct.append(hook)
            continue
        target = os.readlink(path)
        if not safe_path(target) or not target.startswith('/var/lib/'):
            continue
        folder = PurePosixPath(target).parent
        work = str(folder)
        if len(folder.parts) != 4 or not folder.name.endswith('-home') or not work.startswith('/var/lib/'):
            continue
        if filters and not all(filename.startswith(work + '/') for filename in filters):
            continue
        state = work + '/state.json'
        if not local(state).exists():
            continue
        try:
            settings = json.loads(read(state, 65536))
        except (OSError, ValueError):
            continue
        if (not isinstance(settings, dict) or settings.get('enabled') is not True
                or settings.get('method') != 'executable' or settings.get('homeId', APP_ID) != APP_ID
                or settings.get('appDir') != str(PurePosixPath(source).parent)):
            continue
        script = b'\n'.join(line for line in read(target).splitlines()
                            if not line.lstrip().startswith(b'#'))
        require(all(word in script for word in (APP_ID.encode(), b'state.json', b'boot', b'mount --bind')))
        trusted(path, stat.S_ISLNK)
        owners[hook] = (work, state)
    if direct and not owners:
        return direct, None
    require(not direct)
    (owner,) = owners.values()
    work, _ = owner
    require(not source.startswith(work + '/'))
    trusted(local(work), stat.S_ISDIR)
    require(not any(fields[4] == work or fields[4].startswith(work + '/')
                    for fields, _ in mountinfo()))
    files = [work, *owners, *early_registrations(work, filters)]
    require(len(files) == len(set(files)) <= 32)
    return files, work + '/lock'


def direct_mount(hook, source):
    # Accept a standalone literal bind hook, without treating an arbitrary
    # multi-purpose shell program as an editable configuration file.
    try:
        lines = [line.strip() for line in read(hook, 65536).decode().splitlines()
                 if line.strip() and not line.lstrip().startswith('#')]
        if len(lines) != 1 or any(char in lines[0] for char in '$`;&|<>\\'):
            return False
        args = shlex.split(lines[0])
    except (OSError, ValueError):
        return False
    return bool(args and args[0] in ('mount', '/bin/mount') and args[1:] in (
        ['--bind', source, HOME], ['-o', 'bind', source, HOME],
    ))


def path_identity(path):
    if path.is_symlink():
        trusted(path, stat.S_ISLNK)
        return os.readlink(path)
    if path.is_dir():
        trusted(path, stat.S_ISDIR)
        # The dedicated takeover folder can contain a growing boot log. Bind
        # identity to its trusted declaration and keep the entire directory.
        manifest = path / 'state.json'
        trusted(manifest)
        relative = '/' + str(manifest.relative_to(ROOT))
        return 'directory:' + hashlib.sha256(read(relative, 65536)).hexdigest()
    return hashlib.sha256(read('/' + str(path.relative_to(ROOT)))).hexdigest()


def source_digest(source):
    path = local(source)
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and 1 <= info.st_size <= 16*1024*1024)
    return hashlib.sha256(read_file(path, info, 16*1024*1024)).hexdigest()


def fingerprint(plan):
    return hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()


def durable(path):
    with open(path,'rb') as stream:
        os.fsync(stream.fileno())


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def open_lock(plan):
    name = plan['lock']
    if name is None:
        return None
    path = local(name)
    saved = local(RECEIPT) / '0' / Path(name).name
    if not os.path.lexists(path) and os.path.lexists(saved):
        path = saved
    trusted(path)
    fd = os.open(path, os.O_RDWR | os.O_NOFOLLOW)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BaseException:
        os.close(fd)
        raise
    return fd


def archive_receipt(path):
    complete = path.parent / ('complete-' + str(time.time_ns()))
    path.rename(complete)
    sync_directory(complete.parent)


def recorded_mount(plan):
    # JSON turns the outer mount tuple into a list.
    return list(mount_source()) == list(plan['mount'])


def move(origin, saved, identity):
    require(not os.path.lexists(saved) and path_identity(origin) == identity)
    try:
        origin.rename(saved)
    except OSError as error:
        if error.errno != errno.EXDEV or origin.is_dir() and not origin.is_symlink():
            raise
        # Dynamic service definitions can live on a different filesystem.
        # Publish a verified, fsynced copy before removing the active name.
        # Recovery accepts two identical copies after an interruption.
        meta = origin.lstat()
        temporary = saved.with_name('.' + saved.name + '.handoff-copy')
        require(not os.path.lexists(temporary))
        try:
            if origin.is_symlink():
                temporary.symlink_to(os.readlink(origin))
                os.chown(temporary, meta.st_uid, meta.st_gid, follow_symlinks=False)
            else:
                contents = read_file(origin, meta, 262144)
                with temporary.open('xb') as destination:
                    destination.write(contents)
                os.chown(temporary, meta.st_uid, meta.st_gid)
                os.chmod(temporary, stat.S_IMODE(meta.st_mode))
                durable(temporary)
            require(path_identity(temporary) == identity and path_identity(origin) == identity)
            temporary.rename(saved)
            sync_directory(saved.parent)
            origin.unlink()
        finally:
            if os.path.lexists(temporary):
                temporary.unlink()
    sync_directory(origin.parent)
    sync_directory(saved.parent)


def inactive(plan):
    return all(not os.path.lexists(local(filename)) for filename in plan['files'])


def restore_before_detach(path, plan, *, retry=False):
    if retry:
        current = mount_source()
        require(current[0] == plan['mount'][0] and source_digest(current[0]) == plan['source_digest']
                and stock_preview() == plan['stock_digest'])
    else:
        require(recorded_mount(plan))
    original, filtered = plan['chain'], plan['stock_chain']
    current = read_chain()
    require(current in (original, filtered))
    if current != original:
        write_chain(original)
    files = list(plan['files'].items())
    for index in range(len(files)-1, -1, -1):
        filename, identity = files[index]
        origin = local(filename)
        saved = path / str(index)
        if os.path.lexists(saved):
            require(path_identity(saved) == identity)
            if os.path.lexists(origin):
                require(path_identity(origin) == identity and (saved.is_symlink() or not saved.is_dir()))
                saved.unlink()
                sync_directory(path)
            else:
                move(saved, origin, identity)
        require(path_identity(origin) == identity)
    if any(filename.startswith(LS2 + '/') for filename in plan['files']):
        rescan()
    (path / 'plan.json').unlink()
    path.rmdir()
    sync_directory(path.parent)


def quarantine(path, plan, *, retry=False):
    for index, (filename, identity) in enumerate(plan['files'].items()):
        origin = local(filename)
        saved = path / str(index)
        if retry and os.path.lexists(saved):
            require(path_identity(saved) == identity)
            if os.path.lexists(origin):
                require(path_identity(origin) == identity and (origin.is_symlink() or not origin.is_dir()))
                origin.unlink()
                sync_directory(origin.parent)
            continue
        move(origin, saved, identity)


def clear_registrations(plan):
    current = read_chain()
    require(current in (plan['chain'], plan['stock_chain']))
    if current != plan['stock_chain']:
        write_chain(plan['stock_chain'])
    if any(filename.startswith(LS2 + '/') for filename in plan['files']):
        rescan()


def recover():
    path = local(RECEIPT)
    require(stat.S_IMODE(trusted(path, stat.S_ISDIR).st_mode) == 0o700)
    require(stat.S_IMODE(trusted(path.parent, stat.S_ISDIR).st_mode) == 0o700)
    plan = json.loads(read(RECEIPT + '/plan.json', 131072))
    fd = open_lock(plan)
    try:
        if covering(mountinfo()):
            restore_before_detach(path, plan, retry=True)
            return False
        require(stock_home() == plan['stock_digest'])
        require(read_chain() in (plan['chain'], plan['stock_chain']))
        quarantine(path, plan, retry=True)
        clear_registrations(plan)
        require(inactive(plan) and stock_home() == plan['stock_digest']
                and read_chain() == plan['stock_chain'])
        archive_receipt(path)
        return True
    finally:
        if fd is not None:
            os.close(fd)


def apply(expected):
    plan = inspect()
    require(fingerprint(plan) == expected)
    fd = open_lock(plan)
    try:
        require(fingerprint(inspect()) == expected)
        path = local(RECEIPT)
        trusted(path.parent.parent, stat.S_ISDIR)
        path.parent.mkdir(mode=0o700, exist_ok=True)
        trusted(path.parent, stat.S_ISDIR)
        require(stat.S_IMODE(path.parent.lstat().st_mode) == 0o700)
        path.mkdir(mode=0o700)
        receipt = path / 'plan.json'
        with receipt.open('x', encoding='utf-8') as stream:
            json.dump(plan, stream)
        durable(receipt)
        sync_directory(path)
        sync_directory(path.parent)
        detached = False
        try:
            quarantine(path, plan)
            require(read_chain() == plan['chain'])
            clear_registrations(plan)
            require(recorded_mount(plan) and source_digest(plan['mount'][0]) == plan['source_digest'])
            unmount()
            detached = True
            require(inactive(plan) and stock_home() == plan['stock_digest']
                and read_chain() == plan['stock_chain'])
        except Exception:
            # If the route is uncertain, retain the journal and quarantined
            # files for a later authenticated readback rather than overwrite it.
            if not detached:
                restore_before_detach(path, plan)
            raise
        archive_receipt(path)
    finally:
        if fd is not None:
            os.close(fd)


if __name__ == '__main__':
    try:
        if len(sys.argv) == 1:
            if os.path.lexists(local(RECEIPT)):
                print(json.dumps({'interrupted':True}))
            else:
                print(json.dumps({'plan':fingerprint(inspect())}))
        elif sys.argv[1] == 'recover':
            print('CYTV_HOME_HANDOFF_COMPLETE' if recover() else 'CYTV_HOME_HANDOFF_RECOVERED')
        else:
            apply(sys.argv[1])
            print('CYTV_HOME_HANDOFF_COMPLETE')
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        # Do not export mount sources, hook paths or application inventories.
        if len(sys.argv) == 1:
            print('{}')
        else:
            raise SystemExit(1)
"""


def handoff_pending(remote):
    return remote.run(PENDING_CHECK, timeout=5).strip() == 'CYTV_HOME_HANDOFF_PENDING'


def takeover(installer, *, pending=False):
    """Run only from ordinary Root setup for a native conflict or an interrupted handoff."""
    from .root_capabilities import NATIVE_HOME_MOUNT_PROBE
    remote = installer.remote
    try:
        if not pending:
            mount = remote.run(NATIVE_HOME_MOUNT_PROBE, timeout=5).strip()
            if mount not in ('file-mount', 'file-and-parent-mounts'):
                return False
        python = installer._select_python(provision=True)
        # The selected runtime smoke does not exercise libffi. Probe it
        # separately before opening the handoff transaction.
        required = installer._python_command([
            python, '-I', '-B', '-c', 'import ctypes; ctypes.CDLL(None); print("CYTV_HOME_LIBC_READY")',
        ])
        try:
            libc_ready = remote.run(required, timeout=5).strip() == 'CYTV_HOME_LIBC_READY'
        except (UserError, OSError, TimeoutError):
            libc_ready = False
        if not libc_ready:
            raise UserError('Root operation was not confirmed. Run cytv status; retain recovery state.',
                            reason_code='root-operation-unconfirmed')
        command = installer._python_command([python, '-I', '-B', '-'])
        source = PROGRAM.encode()
        inspection = json.loads(remote.run(command, data=source, timeout=30))
        if inspection.get('interrupted') is True:
            restored = remote.run(command + ' recover', data=source, timeout=45).strip()
            if restored == 'CYTV_HOME_HANDOFF_COMPLETE':
                installer._selected_python = python
                return True
            if restored != 'CYTV_HOME_HANDOFF_RECOVERED':
                return False
            inspection = json.loads(remote.run(command, data=source, timeout=30))
        plan = inspection.get('plan')
    except UserError as error:
        if error.reason_code == 'root-operation-unconfirmed':
            raise
        return False
    except (OSError, TimeoutError, ValueError, AttributeError):
        return False
    if not isinstance(plan, str) or not re.fullmatch(r'[0-9a-f]{64}', plan):
        return False
    installer.progress('Restoring LG Home…')
    try:
        installer._selected_python = python
        reply = remote.run(command + ' ' + plan, data=source, timeout=90).strip()
    except (UserError, OSError, TimeoutError):
        reply = ''
    if reply != 'CYTV_HOME_HANDOFF_COMPLETE':
        raise UserError('Root operation was not confirmed. Run cytv status; retain recovery state.',
                        reason_code='root-operation-unconfirmed')
    return True
