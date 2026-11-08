"""Per-TV private profiles and durable operation receipts."""
from contextlib import contextmanager
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import uuid
from .errors import UserError, LocalRecoveryError, is_storage_full


def sync_directory(path):
    if os.name != 'nt':
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def target(host, edition, port=None, identity=None, connection=None, root_variant=None):
    host = host.strip().lower()
    if not re.fullmatch(r'[a-z0-9][a-z0-9.-]{0,252}', host) or '..' in host:
        raise ValueError('Enter a TV IPv4 address or hostname, without a URL or SSH options.')
    if re.fullmatch(r'[0-9.]+', host):
        ipaddress.IPv4Address(host)
    if edition not in ('root', 'no-root'):
        raise ValueError('Choose root or no-root.')
    if connection is not None and (connection != 'root-ssh' or edition != 'no-root'):
        raise ValueError('Invalid SSH connection for this edition.')
    if root_variant is not None and (root_variant != 'node012-beta' or edition != 'root'):
        raise ValueError('Invalid Root runtime variant.')
    port = int(port if port is not None else 22 if edition == 'root' or connection == 'root-ssh' else 9922)
    if not 1 <= port <= 65535:
        raise ValueError('SSH port must be between 1 and 65535.')
    profile = {'host': host, 'edition': edition, 'port': port}
    if connection is not None:
        profile['connection'] = connection
    if root_variant is not None:
        profile['root_variant'] = root_variant
    if identity:
        profile['identity'] = str(Path(identity).expanduser().resolve())
    return profile


def default_dir():
    if os.name == 'nt':
        return Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'CleanYourTV'
    if __import__('sys').platform == 'darwin':
        return Path.home() / 'Library/Application Support/CleanYourTV'
    return Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'cleanyourtv'


def private_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(prefix='.cytv-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        sync_directory(path.parent)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class Store:
    def __init__(self, root=None):
        # Canonicalize the caller-selected root once (including macOS /var).
        # Capsule members and subsequently introduced links are still rejected.
        self.root = (Path(root) if root else default_dir()).resolve()

    def device_dir(self, profile):
        normalized = target(**profile)
        key = ':'.join(str(normalized[k]) for k in ('host', 'port', 'edition'))
        if normalized.get('connection'):
            key += ':' + normalized['connection']
        path = self.root / hashlib.sha256(key.encode()).hexdigest()[:24]
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        return path

    def save(self, profile):
        private_write(self.device_dir(profile) / 'profile.json', json.dumps(target(**profile)).encode())

    def _capsule_path(self, profile, operation):
        if not isinstance(operation, str) or not re.fullmatch('[a-f0-9]{32}', operation):
            raise LocalRecoveryError('operation-invalid', 'operation')
        try:
            directory = self.device_dir(profile)
        except OSError as error:
            raise LocalRecoveryError('directory-access', 'profile', storage_full=is_storage_full(error)) from None
        # Reuse the existing Chaquopy context proof for Android's system-owned
        # /data ancestors; desktop roots retain the full ancestry check.
        from .python_runtime import _android_cache_anchor
        try:
            android_anchor=_android_cache_anchor(directory)
        except (UserError, OSError):
            raise LocalRecoveryError('directory-access', 'ancestor') from None
        parents=(directory,*directory.parents)
        if android_anchor:
            directory,anchor=android_anchor
            parents=[];parent=directory
            while parent!=anchor:
                parents.append(parent);parent=parent.parent
        for parent in parents:
            location = 'profile' if parent == directory else 'ancestor'
            try:
                info = parent.lstat()
            except OSError:
                raise LocalRecoveryError('directory-access', location) from None
            details = dict(location=location, mode=format(info.st_mode & 0o7777, '04o'))
            if os.name != 'nt':
                details['owner'] = 'root' if info.st_uid == 0 else 'current-user' if info.st_uid == os.getuid() else 'other'
            if not stat.S_ISDIR(info.st_mode):
                raise LocalRecoveryError('directory-type', **details)
            if os.name != 'nt' and info.st_uid not in (0, os.getuid()):
                raise LocalRecoveryError('directory-owner', **details)
            if os.name != 'nt' and (info.st_mode & 0o022 and not (info.st_uid == 0 and info.st_mode & stat.S_ISVTX)
                                   or parent == directory and info.st_mode & 0o077):
                raise LocalRecoveryError('directory-permissions', **details)
        return directory / ('capsule-' + operation + '.json')

    def check_capsule_storage(self, profile, operation):
        """Exercise private local writes before recording an operation or contacting its observer."""
        path = self._capsule_path(profile, operation)
        try:
            with tempfile.TemporaryFile(dir=path.parent) as stream:
                stream.write(b'CYTV')
                stream.flush()
                os.fsync(stream.fileno())
            sync_directory(path.parent)
        except OSError as error:
            raise LocalRecoveryError('storage-unavailable', 'profile', storage_full=is_storage_full(error)) from None

    def save_capsule(self, profile, operation, value):
        """Exclusive original bytes, durable before any remote effect."""
        path = self._capsule_path(profile, operation)
        raw = json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        sync_directory(path.parent)
        return hashlib.sha256(raw).hexdigest()

    def read_capsule(self, profile, operation, digest):
        try:
            path = self._capsule_path(profile, operation)
            before = path.lstat()
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > 192*1024*1024:
                raise LocalRecoveryError('capsule-unsafe')
            if os.name != 'nt' and (before.st_uid != os.getuid() or before.st_mode & 0o777 != 0o600):
                raise LocalRecoveryError('capsule-permissions', mode=format(before.st_mode & 0o7777, '04o'),
                                         owner='root' if before.st_uid == 0 else 'current-user' if before.st_uid == os.getuid() else 'other')
            fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
            with os.fdopen(fd, 'rb') as stream:
                opened = os.fstat(stream.fileno())
                if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
                    raise LocalRecoveryError('capsule-changed')
                raw = stream.read(192*1024*1024+1)
            if len(raw) > 192*1024*1024 or hashlib.sha256(raw).hexdigest() != digest:
                raise LocalRecoveryError('capsule-changed')
            return json.loads(raw)
        except FileNotFoundError:
            raise LocalRecoveryError('capsule-missing') from None
        except OSError:
            raise LocalRecoveryError('capsule-access') from None
        except (ValueError, TypeError):
            raise LocalRecoveryError('capsule-invalid') from None

    def retire_capsule(self, profile, operation, digest):
        """Retire only exact original bytes after the caller archived completion."""
        path=self._capsule_path(profile,operation)
        before=path.lstat()
        self.read_capsule(profile,operation,digest)
        after=path.lstat()
        if (before.st_dev,before.st_ino)!=(after.st_dev,after.st_ino):
            raise UserError('The original private recovery data is missing or changed. Recovery data was kept.')
        path.unlink()
        sync_directory(path.parent)

    def connection_profile(self, selected):
        """Resolve pending work to its original saved identity, before connecting."""
        if self.pending(selected) is None:
            return selected, False
        directory = self.device_dir(selected)
        try:
            path = directory / 'profile.json'
            known = directory / 'known_hosts'
            pending=self.pending(selected) or {}
            if (pending.get('recovery_protocol')=='clean-removal-v1' and pending.get('connection_pending') is True
                    and 'previous' not in pending and not path.is_symlink() and not known.is_symlink() and not known.exists()):
                original=target(**json.loads(path.read_text()))
                if any(original[k]!=selected[k] for k in ('host','edition','port')):raise ValueError('foreign profile')
                return original,False  # First connection still requires explicit normal host-key trust.
            if path.is_symlink() or known.is_symlink() or not known.read_bytes():
                raise ValueError('missing trust')
            original = target(**json.loads(path.read_text()))
            if any(original[k] != selected[k] for k in ('host', 'edition', 'port')):
                raise ValueError('foreign profile')
            profiles=self.profiles()
            matches = [p for p in profiles if all(p.get(k) == original.get(k) for k in ('host','edition','port','connection'))]
            if matches != [original]:
                raise ValueError('ambiguous profile')
            operation=(self.pending(original) or {}).get('product_operation')
            if operation and [p for p in profiles if (self.pending(p) or {}).get('product_operation')==operation] != [original]:
                raise ValueError('ambiguous operation')
            return original, True
        except (OSError, ValueError, TypeError, KeyError):
            raise UserError('The original saved TV connection and host key are required for recovery. Recovery data was kept.',
                            reason_code='ssh-identity-unverified') from None

    def profiles(self):
        result = []
        if self.root.exists():
            for path in sorted(self.root.glob('*/profile.json')):
                result.append(target(**json.loads(path.read_text())))
        return sorted(result, key=lambda p: (p['host'], p['port'], p['edition']))

    def pending(self, profile):
        path = self.device_dir(profile) / 'operation.json'
        if not path.exists():
            return None
        try:
            result = json.loads(path.read_text())
            if not isinstance(result, dict) or not isinstance(result.get('action'), str):
                raise ValueError('Invalid receipt')
            return result
        except (ValueError, OSError):
            return {'action': 'unknown', 'stage': 'corrupt-receipt; retain evidence and inspect TV'}

    def begin(self, profile, action, **values):
        path = self.device_dir(profile) / 'operation.json'
        diagnostic_id = uuid.uuid4().hex
        data = json.dumps({'action': action, 'stage': 'pending', **values, 'diagnostic_id': diagnostic_id}).encode('utf-8')
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            raise UserError('Previous operation is unresolved. Run cytv status or cytv restore; do not retry installation.', reason_code='pending-operation') from None
        self.diagnostic_created = diagnostic_id
        self.diagnostic_action = action
        # Android forbids hard links. Exclusive creation never replaces evidence;
        # interrupted writes remain as blocking receipts, even if empty/corrupt.
        # Callers must wait for both syncs before mutating the TV.
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        sync_directory(path.parent)
        if action == 'install':
            completed = path.parent / 'clean-removal.json'
            if completed.exists():
                private_write(path.parent / ('clean-removal-history-'+diagnostic_id+'.json'), completed.read_bytes())
                completed.unlink()
                sync_directory(path.parent)

    def finish(self, profile):
        path = self.device_dir(profile) / 'operation.json'
        path.unlink(missing_ok=True)
        sync_directory(path.parent)

    def request_clean_removal(self, profile):
        """Record desired absence under the host lock, without TV authority."""
        previous = self.pending(profile)
        if previous and previous.get('recovery_protocol') == 'clean-removal-v1':
            return previous
        directory = self.device_dir(profile)
        completed = directory / 'clean-removal.json'
        if previous is None and completed.exists():
            value = json.loads(completed.read_text())
            if value.get('recovery_protocol') != 'clean-removal-v1' or value.get('stage') != 'verified-clean':
                raise UserError('Removal evidence changed. Recovery data was kept.')
            # A new explicit Remove is a new goal. Try again retains the active
            # pending above; a completed goal never regains destructive power.
            private_write(directory / ('clean-removal-history-'+uuid.uuid4().hex+'.json'), completed.read_bytes())
        identifier = uuid.uuid4().hex
        value = {'action':'uninstall', 'full_project':True,
                 'recovery_protocol':'clean-removal-v1', 'removal_operation':identifier,
                 'product_operation':identifier, 'diagnostic_id':uuid.uuid4().hex,
                 'stage':'requested', 'removal_reason':'removal-requested'}
        if previous is None and not (directory/'known_hosts').exists():value['connection_pending']=True
        if previous is not None:
            original = 'removal-original-' + identifier + '.json'
            private_write(directory / original, (directory / 'operation.json').read_bytes())
            value.update(previous=previous, original_receipt=original)
            # Original selector/lease; the new ID identifies intent, not a lock bypass.
            current = previous
            while isinstance(current, dict):
                operation = current.get('product_operation')
                if isinstance(operation, str) and re.fullmatch('[a-f0-9]{32}', operation):
                    value['product_operation'] = operation
                    break
                current = current.get('previous')
        private_write(directory / 'operation.json', json.dumps(value).encode())
        self.diagnostic_created=value['diagnostic_id']
        self.diagnostic_action='uninstall'
        return value

    def finish_clean_removal(self, profile):
        value = self.pending(profile)
        if (not value or value.get('recovery_protocol') != 'clean-removal-v1' or value.get('stage') != 'verified-clean'
                or value.get('result',{}).get('removed') is not True or value.get('result',{}).get('verified_clean') is not True
                or value.get('result',{}).get('restart_required') is True):
            raise UserError('Removal is not verified. Recovery data was kept.')
        private_write(self.device_dir(profile) / 'clean-removal.json', json.dumps(value).encode())
        self.finish(profile)
        self.diagnostic_removal=value

    def recovery(self, profile, action):
        path = self.device_dir(profile) / ('recovery-' + uuid.uuid4().hex + '.json')
        private_write(path, json.dumps({'action': action, 'stage': 'pending'}).encode())
        return path

    def checkpoint(self, profile, **values):
        current = self.pending(profile)
        if current is None:
            raise UserError('No operation receipt exists')
        current.update({key: value for key, value in values.items() if key != 'diagnostic_id'})
        private_write(self.device_dir(profile) / 'operation.json', json.dumps(current).encode())

    @contextmanager
    def lock(self, profile):
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        name = 'session-' + hashlib.sha256(profile['host'].encode()).hexdigest()[:24] + '.lock'
        with (self.root / name).open('a+b') as stream:
            stream.seek(0)
            if os.name == 'nt':
                import msvcrt
                # Windows denies reads of a byte locked by another session.
                # Inspect its size without reading before attempting the lock.
                if os.fstat(stream.fileno()).st_size == 0:
                    stream.write(b'0'); stream.flush()
                stream.seek(0)
                try:
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                except OSError:
                    raise UserError('Another cytv session is using this TV.') from None
            else:
                import fcntl
                try:
                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError:
                    raise UserError('Another cytv session is using this TV.') from None
            try:
                yield
            finally:
                if os.name == 'nt':
                    stream.seek(0); msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream, fcntl.LOCK_UN)
