"""Fixed Homebrew entry point for a rooted TV's No-root installation."""
import argparse
from contextlib import contextmanager
import errno
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
import tempfile
import time

# The verified TV snapshot places the installer modules beside this script.
if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from cytv import no_root_observer, package
from cytv.errors import TVCommandError, UserError, reports_storage_full
from cytv.operations import Installer
from cytv.state import Store, private_write, sync_directory, target
from cytv.transport import JsonReplies, LunaReplyUnconfirmed, SSH, terminal_reply

HANDOFF_FILES = {'root-updater/bundle.json', 'root-updater/cleanup_tail.js', 'installer-support/lifecycle-gate'}
STATE = Path('/var/lib/clean-your-tv-homebrew-no-root')
PRODUCT = Path('/var/lib/clean-your-tv-installation')
PROFILE = target('localhost', 'no-root', connection='root-ssh')
ID = re.compile(r'[a-f0-9]{32}')
PIN = re.compile(r'[a-f0-9]{64}')
STAGES = {'reserved', 'pairing', 'packages', 'updates', 'complete'}
PAIRING_CODES = {'pairing-unavailable', 'pairing-rejected', 'pairing-timeout', 'inventory-unavailable'}
ERROR_CODES = PAIRING_CODES | {
    'original-work-unverified', 'no-root-prerequisites', 'root-admission-changed',
    'no-root-payload-invalid', 'worker-unavailable', 'original-worker-interrupted',
    'existing-installation', 'graphics-unverified', 'helper-running',
    'helper-state-unverified', 'storage-preflight-failed', 'tv-storage-full',
    'system-updates-incomplete', 'current-state-unverified', 'original-terminal-unverified',
}
ENV = {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LC_ALL': 'C', 'PYTHONDONTWRITEBYTECODE': '1'}


def check_directory(path, *, private=False):
    info = path.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
            or (info.st_mode & (0o077 if private else 0o022))):
        raise ValueError('Unsafe operation directory')


def read_private(path, limit):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as source:
        before = os.fstat(source.fileno())
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.geteuid()
                or before.st_mode & 0o022 or before.st_nlink != 1 or before.st_size > limit):
            raise ValueError('Unsafe operation file')
        raw = source.read(limit + 1)
        after = os.fstat(source.fileno())
        current = path.lstat()
        if (len(raw) != before.st_size or after.st_mtime_ns != before.st_mtime_ns
                or (before.st_dev, before.st_ino) != (current.st_dev, current.st_ino)):
            raise ValueError('Operation file changed')
        return raw


class LocalDevice:
    """Adapt host installer primitives for the fixed, verified worker only."""

    root = True

    def run(self, command, data=None, timeout=30):
        try:
            result = subprocess.run(
                ['/bin/sh', '-c', command], input=data,
                stdin=subprocess.DEVNULL if data is None else None,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, env=ENV,
            )
        except subprocess.TimeoutExpired as error:
            raise TimeoutError('TV operation timed out') from error
        if result.returncode:
            raise TVCommandError(result.returncode, storage_full=reports_storage_full(result.stderr))
        if len(result.stdout) > 2 * 1024 * 1024:
            raise ValueError('Oversized TV response')
        return result.stdout.decode('utf-8')

    def upload(self, path, data, mode=0o600):
        command = SSH._upload_command(path, hashlib.sha256(data).hexdigest(), mode)
        if self.run(command, data=data, timeout=90).strip() != 'CYTV_UPLOAD_OK':
            raise UserError('TV upload could not be verified.')

    def luna(self, uri, payload, terminal=None, timeout=30, app_id=None, *, allow_missing_return=False):
        args = ['/usr/bin/luna-send', *(['-i'] if terminal else ['-n', '1'])]
        if app_id:
            args.extend(['-a', app_id, '-m', app_id + '-cytv'])
        args.extend(['luna://' + uri, json.dumps(payload, separators=(',', ':'))])
        parser = JsonReplies()
        deadline = time.monotonic() + timeout
        with subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL, env=ENV) as client:
            try:
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0 or not select.select([client.stdout], [], [], remaining)[0]:
                        raise UserError('TV operation timed out.', reason_code='operation-timeout')
                    chunk = os.read(client.stdout.fileno(), 4096)
                    if not chunk:
                        raise LunaReplyUnconfirmed('TV command ended without a confirmed result. Run cytv status.')
                    for reply in parser.feed(chunk):
                        if terminal_reply(reply, terminal, uri, allow_missing_return=allow_missing_return):
                            return reply
            finally:
                if client.poll() is None:
                    client.kill()


class Coordinator:
    def __init__(self, root=STATE):
        self.root = Path(root)

    def path(self, operation):
        if not isinstance(operation, str) or not ID.fullmatch(operation):
            raise ValueError('Invalid operation')
        return self.root / ('operation-' + operation)

    def create_root(self):
        for parent in self.root.parents:
            if parent == self.root.parent:
                check_directory(parent)
            else:
                info = parent.lstat()
                if not stat.S_ISDIR(info.st_mode) or (info.st_mode & 0o022 and not info.st_mode & stat.S_ISVTX):
                    raise ValueError('Unsafe operation ancestor')
        self.root.mkdir(mode=0o700, exist_ok=True)
        check_directory(self.root, private=True)
        sync_directory(self.root.parent)

    @contextmanager
    def lock(self, *, create=False):
        if create:
            self.create_root()
        else:
            check_directory(self.root, private=True)
        flags = os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK
        if create:
            flags |= os.O_CREAT
        fd = os.open(self.root / 'worker.lock', flags, 0o600)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077 or info.st_nlink != 1:
                raise ValueError('Unsafe worker lock')
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as error:
                if error.errno not in (errno.EACCES, errno.EAGAIN):
                    raise
                yield None
            else:
                yield fd
        finally:
            # A spawned worker inherits the fd and the original flock.
            os.close(fd)

    def current(self):
        try:
            check_directory(self.root, private=True)
            record = json.loads(read_private(self.root / 'current.json', 16384))
        except FileNotFoundError:
            return None
        if (not isinstance(record, dict) or record.get('schema') != 1
                or not ID.fullmatch(record.get('operation', ''))
                or not PIN.fullmatch(record.get('payload_sha256', ''))
                or not PIN.fullmatch(record.get('candidate_sha256', ''))
                or record.get('stage') not in STAGES
                or ('removal' in record and not ID.fullmatch(record['removal']))):
            raise ValueError('Invalid original operation')
        check_directory(self.path(record['operation']), private=True)
        return record

    def write(self, record):
        private_write(self.root / 'current.json', json.dumps(record, sort_keys=True).encode())

    def reserve(self, operation, pin, candidate, snapshot=None, *, predecessor=None):
        self.create_root()
        previous = self.current()
        if not PIN.fullmatch(pin) or not PIN.fullmatch(candidate) or previous != predecessor:
            raise ValueError('An original operation still owns setup')
        if previous and (previous['operation'] == operation or 'removal' not in previous
                         or not removal_completed(previous['removal'])):
            raise ValueError('The predecessor is not currently verified clean')
        folder = self.path(operation)
        if snapshot is not None and os.path.lexists(folder):
            check_directory(folder, private=True)
            if {entry.name for entry in folder.iterdir()} != {'payload'}:
                raise ValueError('Original setup ID has already been used')
            verify_worker(folder / 'payload', pin)
        elif snapshot is not None:
            os.rename(snapshot, folder)
        else:
            folder.mkdir(mode=0o700)
        sync_directory(self.root)
        if previous:
            if not removal_completed(previous['removal']):
                raise ValueError('Original removal changed during setup review')
            archive = self.path(previous['operation']) / 'archived-setup.json'
            saved = json.dumps(previous, sort_keys=True).encode()
            if os.path.lexists(archive):
                if read_private(archive, 16384) != saved:
                    raise ValueError('Archived setup record changed')
            else:
                private_write(archive, saved)
            if self.current() != previous or not removal_completed(previous['removal']):
                raise ValueError('Original removal changed during setup review')
        record = {'schema': 1, 'operation': operation, 'payload_sha256': pin,
                  'candidate_sha256': candidate, 'stage': 'reserved'}
        self.write(record)
        return record

    def worker_active(self):
        try:
            with self.lock() as fd:
                return fd is None
        except FileNotFoundError:
            return False

    def store(self, operation):
        return Store(self.path(operation) / 'installer')

    def status(self, operation=None):
        record = self.current()
        if record is None or operation is not None and record['operation'] != operation:
            return answer('unknown', 'no-root-operation-unknown')
        fields = {'operation': record['operation'], 'stage': record['stage']}
        if 'removal' in record:
            return answer('recovery_required', 'no-root-removal-pending', **fields,
                          removal=record['removal'], can_resume=False)
        if record.get('stage') == 'complete':
            return answer('complete', 'no-root-installed', **fields, result=record['result'])
        if self.worker_active():
            return answer('pending', 'no-root-operation-pending', **fields)
        code = record.get('code', 'original-worker-interrupted')
        if code not in ERROR_CODES:
            raise ValueError('Invalid original result')
        return answer('recovery_required', code, **fields, can_resume=self.resumable(record))

    def resumable(self, record):
        if 'removal' in record:
            return False
        stage = record['stage']
        if stage in ('reserved', 'pairing'):
            try:
                root = self.path(record['operation']) / 'payload'
                _, files = manifest_at(root, record['payload_sha256'])
                worker_members(files)
            except (KeyError, OSError, RuntimeError, ValueError, TypeError):
                return False
            return True
        store = self.store(record['operation'])
        pending = store.pending(PROFILE)
        return bool(
            stage == 'packages' and (
                pending and pending.get('recovery_protocol') == no_root_observer.PROTOCOL
                and pending.get('capsule_sha256')
                or pending is None
            )
            or stage == 'updates' and (
                not pending or pending.get('action') == 'enable-system-updates'
                and pending.get('stage') in ('upload', 'setup') and pending.get('bootstrap_digest')
            )
        )


def answer(state, code, **fields):
    return {'state': state, 'code': code, 'edition': 'no-root', **fields}


def removal_completed(removal, product=PRODUCT, *, require_current=True):
    """Recognize only the Root coordinator's exact, finalized removal binding."""
    if not ID.fullmatch(removal):
        return False
    try:
        check_directory(product, private=True)
        binding = json.loads(read_private(product / ('homebrew-removal-' + removal + '.json'), 2048))
        target, original = binding['target'], binding['lease']
        if (set(binding) != {'schema', 'operation', 'target', 'lease'} or binding['schema'] != 1
                or binding['operation'] != removal or not ID.fullmatch(target)
                or original != '-' and not ID.fullmatch(original)):
            return False
        cleaned = json.loads(read_private(product / ('clean-removal-' + target + '.json'), 4 * 1024 * 1024))
        former, final = cleaned['lease'], cleaned['final_fence']
        result = cleaned['result']
        if (cleaned['schema'] != 1 or cleaned['protocol'] != 'clean-removal-v1'
                or cleaned['operation'] != target or cleaned['removal'] != removal
                or not ID.fullmatch(former) or not ID.fullmatch(final) or former == final
                or original not in ('-', former) or cleaned['final_original_lease'] != former
                or cleaned['state'] != 'complete' or cleaned['stage'] != 'verified-clean' or cleaned['current'] is not True
                or result.get('removed') is not True or result.get('private_cleanup_verified') is not True
                or result.get('applications_services_startup_removed') is not True):
            return False
        if not require_current:
            return True
        owner = json.loads(read_private(product / 'operation.json', 2048))
        return owner == {'schema': 1, 'id': final, 'journal': 'product-' + target + '.json',
                         'owner': 'clean-removal', 'stage': 'verified-clean', 'terminal': False}
    except (AttributeError, KeyError, OSError, TypeError, ValueError):
        return False


def prepare_remove(coordinator, removal, operation=None):
    if not ID.fullmatch(removal) or operation is not None and not ID.fullmatch(operation):
        raise ValueError('Invalid removal intent')
    if not coordinator.root.exists():
        return answer('unknown', 'no-root-operation-unknown')
    with coordinator.lock(create=True) as fd:
        record = coordinator.current()
        if fd is None:
            return {'state': 'pending', 'code': 'no-root-worker-busy',
                    'edition': 'no-root', 'stage': 'requested', 'can_resume': True}
        if record is None or ('removal' in record
                              and removal_completed(record['removal'], require_current=False)):
            return answer('unknown', 'no-root-operation-unknown')
        if (operation is not None and record['operation'] != operation
                or record.get('removal', removal) != removal):
            return answer('recovery_required', 'no-root-removal-mismatch', stage='blocked', can_resume=False)
        if 'removal' not in record:
            record['removal'] = removal
            coordinator.write(record)
        return answer('removal_ready', 'no-root-removal-ready', operation=record['operation'], removal=removal)


def package_completion(store):
    directory = store.device_path(PROFILE)
    if not directory.exists():
        return None
    matches = []
    for path in sorted(directory.glob('recovery-*.json')):
        if not re.fullmatch(r'recovery-[a-f0-9]{32}\.json', path.name):
            continue
        record = json.loads(read_private(path, 2 * 1024 * 1024))
        if record.get('action') != 'finish-no-root-operation' or record.get('stage') != 'verified':
            continue
        previous, observer = record['previous'], record['observer']
        if (previous.get('action') == 'install' and previous.get('recovery_protocol') == no_root_observer.PROTOCOL
                and observer.get('closed') and observer['operation'] == previous.get('observer_operation')
                and observer.get('protocol') == no_root_observer.PROTOCOL
                and observer.get('reservation') == 'closed'):
            matches.append(record)
    if len(matches) > 1:
        raise ValueError('Conflicting completion records')
    return matches[0] if matches else None


def manifest_at(stage, pin):
    check_directory(stage, private=True)
    raw = read_private(stage / 'manifest.json', 4 * 1024 * 1024)
    if hashlib.sha256(raw).hexdigest() != pin:
        raise ValueError('Payload identity changed')
    value = json.loads(raw)
    if not isinstance(value, dict) or not isinstance(value.get('files'), dict):
        raise ValueError('Invalid payload manifest')
    return raw, value['files']


def read_member(stage, files, name):
    path = stage / package.safe_name(name)
    for parent in path.parents:
        check_directory(parent, private=True)
        if parent == stage:
            break
    record = files[name]
    size, pin = record['size'], record['sha256']
    if type(size) is not int or not 0 <= size <= 64 * 1024 * 1024 or not PIN.fullmatch(pin):
        raise ValueError('Invalid member identity')
    raw = read_private(path, size)
    if len(raw) != size or hashlib.sha256(raw).hexdigest() != pin:
        raise ValueError('Payload member changed')
    return raw


def worker_members(files):
    selected = [name for name in files if name.startswith(('edition/', 'no-root/', 'supervisor/'))
                or name in HANDOFF_FILES]
    required = {'edition/no_root.py', 'edition/edition.py', 'edition/pairing.py', 'no-root/payload.json',
                'no-root/fallback.png', 'supervisor/bundle.json'} | HANDOFF_FILES
    if not required <= set(selected) or len(selected) > 4000:
        raise ValueError('Missing installer worker files')
    sizes = [files[name]['size'] for name in selected]
    if (any(type(size) is not int or size < 0 for size in sizes)
            or sum(sizes) > 160 * 1024 * 1024):
        raise ValueError('Oversized installer worker')
    return selected


def copy_worker(source, destination, pin):
    manifest, files = manifest_at(source, pin)
    members = worker_members(files)
    storage = os.statvfs(destination.parent)
    if storage.f_bavail * storage.f_frsize < sum(files[name]['size'] for name in members):
        raise UserError('Insufficient private recovery storage.', reason_code='tv-storage-full')
    destination.mkdir(mode=0o700)
    for name in members:
        relative = Path(name)
        for parent in reversed(relative.parents):
            directory = destination / parent
            directory.mkdir(mode=0o700, exist_ok=True)
            check_directory(directory, private=True)
        private_write(destination / relative, read_member(source, files, name))
    private_write(destination / 'manifest.json', manifest)
    sync_directory(destination.parent)


def verify_worker(stage, pin):
    _, files = manifest_at(stage, pin)
    for name in worker_members(files):
        read_member(stage, files, name)


def retirement_plan(root, pin, *, partial):
    check_directory(root, private=True)
    if partial and not any(root.iterdir()):
        return {}, {}
    _, files = manifest_at(root, pin)
    manifest_info = (root / 'manifest.json').lstat()
    expected = set(worker_members(files))
    expected_parents = {str(parent) for name in expected for parent in Path(name).parents if str(parent) != '.'}
    owned_files, owned_directories = {}, {}

    def unavailable(error):
        raise error

    for directory, names, leaves in os.walk(root, followlinks=False, onerror=unavailable):
        relative = Path(directory).relative_to(root)
        for name in names:
            member = relative / name
            if str(member) not in expected_parents:
                raise ValueError('Unexpected retained payload directory')
            path = root / member
            check_directory(path, private=True)
            owned_directories[member] = path.lstat()
        for name in leaves:
            member = relative / name
            if str(member) == 'manifest.json':
                owned_files[member] = manifest_info
            else:
                if str(member) not in expected:
                    raise ValueError('Unexpected retained payload file')
                path = root / member
                owned_files[member] = path.lstat()
                read_member(root, files, str(member))
    if not partial and {str(path) for path in owned_files} != expected | {'manifest.json'}:
        raise ValueError('Incomplete retained payload')
    return owned_files, owned_directories


def retire_worker(root, pin):
    """Retire the exact worker snapshot, leaving all sibling records intact."""
    retiring = root.with_name('payload-retiring')
    if os.path.lexists(retiring):
        if os.path.lexists(root):
            raise ValueError('Conflicting payload retirement states')
        files, directories = retirement_plan(retiring, pin, partial=True)
    elif os.path.lexists(root):
        files, directories = retirement_plan(root, pin, partial=False)
        os.rename(root, retiring)
        sync_directory(root.parent)
    else:
        return

    def remove(relative, before, *, directory=False):
        path = retiring / relative
        current = path.lstat()
        identity = ('st_dev', 'st_ino', 'st_mode', 'st_uid')
        if not directory:
            identity += ('st_nlink', 'st_size', 'st_mtime_ns')
        if any(getattr(current, key) != getattr(before, key) for key in identity):
            raise ValueError('Retiring payload changed')
        (path.rmdir if directory else path.unlink)()
        sync_directory(path.parent)

    manifest = files.pop(Path('manifest.json'), None)
    for relative, before in files.items():
        remove(relative, before)
    for relative in sorted(directories, key=lambda path: len(path.parts), reverse=True):
        remove(relative, directories[relative], directory=True)
    if manifest is not None:
        remove(Path('manifest.json'), manifest)
    retiring.rmdir()
    sync_directory(retiring.parent)


def retire_payload(coordinator, operation, pin):
    record = coordinator.current()
    if not record or record['operation'] != operation or record['payload_sha256'] != pin:
        return answer('unknown', 'no-root-operation-unknown')
    try:
        with coordinator.lock() as fd:
            if fd is None:
                return answer('pending', 'no-root-worker-busy', operation=operation, stage=record['stage'])
            if coordinator.current() != record:
                return answer('unknown', 'no-root-operation-unknown')
            result = record.get('result', {})
            verified = (removal_completed(record['removal']) if 'removal' in record else
                        record['stage'] == 'complete' and result.get('installed') == 'no-root'
                        and all(result.get(key) is True for key in
                                ('packages_verified', 'configuration_verified', 'system_updates')))
            if not verified:
                return answer('recovery_required', 'original-work-unverified', operation=operation,
                              stage=record['stage'], can_resume=False)
            retire_worker(coordinator.path(operation) / 'payload', pin)
    except (KeyError, OSError, RuntimeError, TypeError, ValueError):
        return answer('recovery_required', 'no-root-payload-retained', operation=operation,
                      stage=record['stage'], can_resume=False)
    return answer('retired', 'no-root-payload-retired', operation=operation, stage=record['stage'])


def edition_reader():
    if __package__:
        from . import edition
    else:
        import edition
    return edition


def pairing_reader():
    if __package__:
        from . import pairing
    else:
        import pairing
    return pairing


def make_installer(coordinator, stage=None, pin=None, operation=None):
    store = coordinator.store(operation) if operation else None
    manifest = {}
    payload = Path('.')
    if stage is not None:
        _, files = manifest_at(stage, pin)
        manifest = json.loads(read_member(stage, files, 'no-root/payload.json'))
        payload = stage / 'no-root'
    installer = Installer(LocalDevice(), store, PROFILE, payload, manifest, progress=lambda _: None, homebrew_entry=True)
    installer._selected_python = sys.executable
    if stage is not None:
        installer._system_bundle = stage / 'supervisor'
        cleanup = read_member(stage, files, 'root-updater/cleanup_tail.js')
        bundle = json.loads(read_member(stage, files, 'root-updater/bundle.json'))
        if hashlib.sha256(cleanup).hexdigest() != bundle['files']['cleanup_tail.js']:
            raise ValueError('Root handoff cleanup closure changed')
        gate = read_member(stage, files, 'installer-support/lifecycle-gate')
        installer._verified_root_handoff_support = cleanup.decode('utf-8'), gate
    return installer


def inspect_candidate(installer, pin):
    reader = edition_reader()
    if reader.decision(reader.LocalReads()) != 'external_no_root':
        return answer('unavailable', 'root-admission-changed')
    installer.require_fresh_single_tile()
    installer.check_no_root_alternative(allow_clean_root_handoff=True)
    # Actual local pairing facility is a prerequisite to presenting setup.
    if not pairing_reader().available():
        return answer('unavailable', 'pairing-unavailable')
    manifest = installer.manifest
    graphics = installer.tv_info['graphics_resolution']
    versions = {'home': manifest['home_version'], 'helper': manifest['helper_version']}
    if 'screensaver' in manifest:
        versions['screensaver'] = manifest['screensaver_version']
    _, files = manifest_at(installer.payload.parent, pin)
    members = worker_members(files)
    storage = os.statvfs(installer.payload.parent)
    if storage.f_bavail * storage.f_frsize < sum(files[name]['size'] for name in members):
        return answer('unavailable', 'tv-storage-full')
    supervisor = json.loads(read_member(installer.payload.parent, files, 'supervisor/bundle.json'))
    if supervisor.get('product_schema') != 2:
        return answer('unavailable', 'no-root-payload-invalid')
    reviewed = {'schema': 1, 'payload_sha256': pin, 'edition': 'no-root',
                'graphics': graphics, 'versions': versions, 'system_updates': True}
    predecessor = getattr(installer, '_root_handoff', None)
    if predecessor is not None:
        reviewed['clean_root_predecessor'] = predecessor
    candidate = hashlib.sha256(no_root_observer.canonical(reviewed).encode()).hexdigest()
    return answer('eligible', 'no-root-eligible', candidate_sha256=candidate,
                  graphics=graphics, versions=versions)


def reserve_setup(coordinator, stage, pin, operation, candidate):
    predecessor = coordinator.current()
    if predecessor is not None:
        removal = predecessor.get('removal')
        if (predecessor['operation'] == operation or not removal or not removal_completed(removal)):
            raise UserError('The original setup still owns this TV.', reason_code='existing-installation')
        installer = make_installer(coordinator, stage, pin)
        approved = inspect_candidate(installer, pin)
        handoff = getattr(installer, '_root_handoff', None)
        if (approved.get('candidate_sha256') != candidate or not handoff
                or handoff.get('removal') != removal or not removal_completed(removal)):
            raise UserError('Reviewed setup changed.', reason_code='root-admission-changed')
        try:
            retire_worker(coordinator.path(predecessor['operation']) / 'payload', predecessor['payload_sha256'])
        except (KeyError, OSError, RuntimeError, ValueError, TypeError):
            # Drift in old staging is kept with the retired operation; it
            # cannot substitute for evidence against this new review.
            pass
    with tempfile.TemporaryDirectory(prefix='.setup-', dir=coordinator.root) as temporary:
        snapshot = Path(temporary)
        copy_worker(stage, snapshot / 'payload', pin)
        return coordinator.reserve(operation, pin, candidate, snapshot, predecessor=predecessor)


def verify_packages(installer, completion):
    if not completion:
        raise ValueError('Missing original package completion')
    previous = completion['previous']
    installed = {app['id']: app.get('version') for app in installer.installed_apps()}
    if any(installed.get(app) != version for app, version in previous['versions'].items()):
        raise ValueError('Installed packages changed')
    no_root_observer.files_match(installer, previous['expected'])


def current_setup(installer, record):
    if not record.get('supervisor_id'):
        return False
    status = installer.system_updater_cleanup('status')
    return (
        status.get('present') is True and status.get('bootstrap_complete') is True
        and status.get('ownership_verified') is True and status.get('disabled') is False
        and status.get('edition') == 'no-root' and status.get('product_schema') == 2
        and status.get('setup_id') == record['supervisor_id']
        and status.get('bootstrap_digest') == record.get('supervisor_digest')
    )


WORKING_INVENTORY = """import json,sys
sys.path.insert(0, '/var/lib/clean-your-tv-system-updater/code')
from system_updater.bootstrap import Bootstrap, pinned_integrity
pinned_integrity()
runtime = Bootstrap()
if runtime.active_transition():
    raise ValueError('System engine transition is active')
result = runtime.call(runtime.slots.active(), 'engine-state', {'edition':'no-root'})
print(json.dumps(result))
"""


def working_inventory(installer):
    # The caller must first bind this private code to the original supervisor
    # setup ID and bootstrap digest. The existing engine verifies current
    # signed release provenance and installed files, including after updates.
    args = [installer._python(), '-I', '-B', '-']
    value = json.loads(installer.remote.run(installer._python_command(args),
                                           data=WORKING_INVENTORY.encode(), timeout=45))
    version = re.compile(r'[0-9]{1,8}(?:\.[0-9]{1,8}){2}')
    if (not isinstance(value, dict) or value.get('edition') != 'no-root'
            or not isinstance(value.get('release'), str) or not value['release'].startswith('v')
            or not version.fullmatch(value['release'][1:])
            or value.get('resolution') not in ('1920x1080', '1280x720')):
        raise ValueError('Invalid working installation')
    components = value.get('components')
    if (not isinstance(components, list) or len(components) != 2
            or any(not isinstance(item, dict) or not isinstance(item.get('version'), str)
                   or not version.fullmatch(item['version']) for item in components)
            or {item.get('name') for item in components} != {'home', 'helper'}):
        raise ValueError('Invalid working components')
    return {'edition': 'no-root', 'release': value['release'], 'resolution': value['resolution'],
            'components': [{'name': item['name'], 'version': item['version']} for item in components]}


def helper_observation(installer):
    try:
        state = installer.helper_state(timeout=5)
    except (OSError, RuntimeError, ValueError):
        state = None
    if state == 'running':
        return 'running'
    return 'not-observed' if state in ('stopped', 'stale') else 'unverified'


class WorkerStore(Store):
    def __init__(self, root, coordinator, record):
        super().__init__(root)
        self.coordinator = coordinator
        self.record = record

    def begin(self, profile, action, **values):
        super().begin(profile, action, **values)
        if action == 'enable-system-updates':
            self.remember_supervisor(self.pending(profile))

    def remember_supervisor(self, pending):
        setup, pin = pending['diagnostic_id'], pending['bootstrap_digest']
        if (not ID.fullmatch(setup) or not PIN.fullmatch(pin)
                or self.record.get('supervisor_id', setup) != setup
                or self.record.get('supervisor_digest', pin) != pin):
            raise ValueError('Original supervisor receipt changed')
        self.record.update(supervisor_id=setup, supervisor_digest=pin)
        self.coordinator.write(self.record)


def recovery_code(error):
    code = getattr(error, 'code', None) or getattr(error, 'reason_code', None)
    return code if code in ERROR_CODES else 'original-work-unverified'


def perform(coordinator, root, record, *, resume):
    pin, operation = record['payload_sha256'], record['operation']
    installer = make_installer(coordinator, root, pin, operation)
    store = WorkerStore(installer.store.root, coordinator, record)
    installer.store = store

    def checkpoint(stage, **evidence):
        record.pop('code', None)
        record.update(stage=stage, **evidence)
        coordinator.write(record)

    def recheck_admission():
        approved = inspect_candidate(installer, pin)
        if approved.get('candidate_sha256') != record['candidate_sha256']:
            reason = approved.get('code')
            raise UserError('Reviewed setup changed.', reason_code=reason)

    pending = store.pending(PROFILE)
    result = None
    needs_fresh_pairing = (record['stage'] in ('reserved', 'pairing') or record['stage'] == 'packages'
                           and pending is None and package_completion(store) is None)
    if not resume or needs_fresh_pairing:
        if pending is not None:
            raise ValueError('Original package operation remains unresolved')
        recheck_admission()
        checkpoint('pairing')
        _, files = manifest_at(root, pin)
        inventory, key = pairing_reader().collect(read_member(root, files, 'no-root/fallback.png'),
                                                  allow_missing_inputs=installer.may_omit_no_root_inputs)
        # Pairing and inventory transfer can yield to another client. Repeat all
        # admission checks with fresh graphics and current firmware evidence.
        installer.__dict__.pop('_graphics_paths', None)
        recheck_admission()
        def before_staging():
            reader = edition_reader()
            if reader.decision(reader.LocalReads()) != 'external_no_root':
                raise UserError('Root admission changed.', reason_code='root-admission-changed')
            installer.prepare_install_helper(False)

        installer.before_no_root_staging = before_staging
        checkpoint('packages')
        result = installer.install(inventory, ssap_key=key)
    elif record['stage'] == 'packages' and pending:
        if pending.get('action') != 'install' or pending.get('recovery_protocol') != no_root_observer.PROTOCOL:
            raise ValueError('Original stream cannot resume')
        # Only an explicit resume may stage the native gate and authenticate
        # the original Root lease before inspecting the original package stream.
        if no_root_observer.observe(installer, pending).get('no_root_ready') is not True:
            raise UserError('Original package outcome is still unverified.',
                            reason_code='original-terminal-unverified')
        result = installer.continue_no_root(pending)

    verify_packages(installer, package_completion(store))
    if record['stage'] != 'updates':
        checkpoint('updates', launch_requested=bool(result and result.get('launch_requested')),
                   activation_cancelled=bool(result and result.get('activation_cancelled')))
    pending = store.pending(PROFILE)
    original_bootstrap = (pending and pending.get('action') == 'enable-system-updates'
                          and pending.get('stage') in ('upload', 'setup'))
    if original_bootstrap:
        store.remember_supervisor(pending)
    try:
        supervisor_ready = current_setup(installer, record)
    except (OSError, RuntimeError, ValueError):
        if not original_bootstrap:
            raise
        supervisor_ready = False
    if supervisor_ready:
        if pending:
            installer.status()
            if store.pending(PROFILE) is not None:
                raise ValueError('Original update operation remains unresolved')
    else:
        if not pending and record.get('supervisor_id'):
            raise ValueError('Original supervisor completion cannot be verified')
        installer.enable_system_updates()
    if not current_setup(installer, record):
        raise ValueError('Original supervisor completion cannot be verified')
    helper = helper_observation(installer)
    checkpoint('complete', result={
        'installed': 'no-root', 'packages_verified': True, 'configuration_verified': True,
        'launch_requested': record['launch_requested'], 'activation_cancelled': record['activation_cancelled'],
        'helper_running': helper == 'running', 'helper_observation': helper,
        'system_updates': True, 'hardware_verified': False,
    })


def launch_worker(coordinator, root, record, fd, *, resume):
    operation, pin = record['operation'], record['payload_sha256']
    verify_worker(root, pin)
    args = [sys.executable, '-E', '-s', '-B', str(root / 'edition/no_root.py'),
            'resume' if resume else 'start', '--payload', str(root), '--payload-sha256', pin,
            '--operation', operation, '--worker-fd', str(fd)]
    if not resume:
        args.extend(['--candidate', record['candidate_sha256']])
    subprocess.Popen(args, pass_fds=(fd,), start_new_session=True, env=ENV,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return answer('pending', 'no-root-operation-pending', operation=operation, stage=record['stage'])


def live_status(coordinator, operation):
    result = coordinator.status(operation)
    if result.get('code') == 'no-root-removal-pending' and removal_completed(result['removal'], require_current=False):
        if operation is None:
            return answer('unknown', 'no-root-operation-unknown')
        return answer('removed', 'no-root-removal-verified', operation=operation, removal=result['removal'],
                      stage='verified-clean', current=removal_completed(result['removal']), can_resume=False)
    if result['state'] == 'recovery_required' and result['stage'] == 'packages' and result['can_resume']:
        store = coordinator.store(result['operation'])
        pending = store.pending(PROFILE)
        if pending is not None:
            try:
                record = coordinator.current()
                retained = coordinator.path(result['operation']) / 'payload'
                installer = make_installer(coordinator, retained, record['payload_sha256'], result['operation'])
                observation = no_root_observer.observe(installer, pending, read_only=True)
                if observation.get('no_root_locked_observation') is True:
                    # The capsule is verified. The explicit resume still has
                    # to observe the original transaction under its native locks.
                    return result
                ready = observation.get('no_root_ready') is True
            except (KeyError, OSError, RuntimeError, ValueError, TypeError):
                ready = False
            if not ready:
                return {**result, 'code': 'original-terminal-unverified', 'can_resume': False}
    if result['state'] != 'complete':
        return result
    try:
        record = coordinator.current()
        if not record or record['operation'] != result['operation']:
            raise ValueError('Original operation changed')
        installer = make_installer(coordinator, operation=result['operation'])
        if not current_setup(installer, record):
            raise ValueError('Original updater no longer verified')
        result['result']['working_inventory'] = working_inventory(installer)
        helper = helper_observation(installer)
        result['result'].update(helper_running=helper == 'running', helper_observation=helper, hardware_verified=False)
        if coordinator.current() != record:
            raise ValueError('Original operation changed')
    except (KeyError, OSError, RuntimeError, ValueError, TypeError):
        return answer('recovery_required', 'current-state-unverified', operation=result['operation'],
                      stage=result['stage'], can_resume=False)
    return {**result, 'current': True}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('inspect', 'start', 'status', 'resume', 'prepare-remove', 'retire-payload'))
    parser.add_argument('--payload', type=Path)
    parser.add_argument('--payload-sha256', required=True)
    parser.add_argument('--operation')
    parser.add_argument('--candidate')
    parser.add_argument('--removal')
    parser.add_argument('--worker-fd', type=int, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if (os.geteuid() != 0 or not PIN.fullmatch(args.payload_sha256)
            or (args.payload is None) != (args.action == 'retire-payload')
            or (args.operation is not None and not ID.fullmatch(args.operation))
            or (args.action in ('start', 'resume', 'retire-payload') and args.operation is None)
            or (args.action == 'start') != bool(args.candidate and PIN.fullmatch(args.candidate))
            or (args.candidate is not None and args.action != 'start')
            or (args.action == 'prepare-remove') != bool(args.removal and ID.fullmatch(args.removal))
            or (args.removal is not None and args.action != 'prepare-remove')
            or (args.worker_fd is not None and args.action not in ('start', 'resume'))):
        parser.error('Invalid installer request')
    coordinator = Coordinator()
    record = None
    try:
        if args.action == 'prepare-remove':
            return prepare_remove(coordinator, args.removal, args.operation)
        if args.action == 'retire-payload':
            return retire_payload(coordinator, args.operation, args.payload_sha256)
        if args.worker_fd is not None:
            record = coordinator.current()
            lock = coordinator.root / 'worker.lock'
            proof = os.fstat(args.worker_fd)
            path = lock.lstat()
            if ((proof.st_dev, proof.st_ino) != (path.st_dev, path.st_ino) or not record
                    or record['operation'] != args.operation or record['payload_sha256'] != args.payload_sha256
                    or args.payload != coordinator.path(args.operation) / 'payload'
                    or 'removal' in record
                    or args.action == 'start' and (record['candidate_sha256'] != args.candidate or record['stage'] != 'reserved')):
                raise ValueError('Worker request changed')
            fcntl.flock(args.worker_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            verify_worker(args.payload, args.payload_sha256)
            try:
                perform(coordinator, args.payload, record, resume=args.action == 'resume')
            except (KeyError, OSError, RuntimeError, ValueError, TypeError) as error:
                record['code'] = recovery_code(error)
                coordinator.write(record)
            else:
                try:
                    retire_worker(args.payload, args.payload_sha256)
                except (KeyError, OSError, RuntimeError, ValueError, TypeError):
                    record['payload_retirement'] = 'retained'
                    coordinator.write(record)
            return None
        if args.action == 'status':
            return live_status(coordinator, args.operation)
        if args.action == 'inspect':
            result = live_status(coordinator, args.operation)
            if result['state'] != 'unknown' or args.operation:
                return result
            return inspect_candidate(make_installer(coordinator, args.payload, args.payload_sha256),
                                     args.payload_sha256)
        if args.action == 'start':
            current = coordinator.current()
            if current is not None and current['operation'] == args.operation:
                return live_status(coordinator, args.operation)
        with coordinator.lock(create=True) as fd:
            if fd is None:
                return coordinator.status(args.operation)
            if args.action == 'start':
                record = reserve_setup(coordinator, args.payload, args.payload_sha256,
                                       args.operation, args.candidate)
                root = coordinator.path(args.operation) / 'payload'
            else:
                record = coordinator.current()
                if not record or record['operation'] != args.operation:
                    return answer('unknown', 'no-root-operation-unknown')
                if record['payload_sha256'] != args.payload_sha256 or not coordinator.resumable(record):
                    return answer('recovery_required', 'original-work-unverified', operation=args.operation,
                                  stage=record['stage'], can_resume=False)
                root = coordinator.path(args.operation) / 'payload'
            return launch_worker(coordinator, root, record, fd, resume=args.action == 'resume')
    except (KeyError, OSError, RuntimeError, ValueError, TypeError) as error:
        if record and args.action in ('start', 'resume'):
            return answer('recovery_required', recovery_code(error), operation=record['operation'],
                          stage=record['stage'], can_resume=False)
        return answer('unavailable', recovery_code(error))


if __name__ == '__main__':
    result = main()
    if result is not None:
        print(json.dumps(result))
