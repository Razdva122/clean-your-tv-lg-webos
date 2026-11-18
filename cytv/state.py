"""Per-TV private profiles and durable operation receipts."""
from contextlib import contextmanager
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import stat
from sys import platform
import tempfile
from time import sleep
from typing import NamedTuple, Optional
import uuid
from .errors import UserError, LocalRecoveryError, is_storage_full


class RootReinstall(NamedTuple):
    stage: str
    payload: str
    operation: str
    variant: Optional[str]
    pin: str


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


def _read_with_windows_retry(read):
    for attempt in range(3):
        try:
            return read()
        except PermissionError as error:
            # Windows file opens can report sharing violations as plain EACCES.
            if platform != 'win32' or getattr(error, 'winerror', None) not in (None, 32, 33) or attempt == 2:
                raise
            sleep(0.05 * (attempt + 1))


SSH_IDENTITY_REVIEW = 'ssh-identity-review.json'
ACTIVE_AFTER_RESET = 'active-after-reset'


def require_original_ssh_identity(directory):
    # Even an unreadable review must hold the profile. A verified new host key
    # does not establish continuity of the original installation.
    try:
        (Path(directory) / SSH_IDENTITY_REVIEW).lstat()
    except FileNotFoundError:
        return
    raise UserError('The earlier uninstall remains blocked. Keep the saved SSH and recovery records.',
                    reason_code='ssh-identity-unverified')


class Store:
    def __init__(self, root=None):
        # Canonicalize the caller-selected root once (including macOS /var).
        # Capsule members and subsequently introduced links are still rejected.
        self.root = (Path(root) if root else default_dir()).resolve()

    def original_device_path(self, profile):
        normalized = target(**profile)
        key = ':'.join(str(normalized[k]) for k in ('host', 'port', 'edition'))
        if normalized.get('connection'):
            key += ':' + normalized['connection']
        return self.root / hashlib.sha256(key.encode()).hexdigest()[:24]

    @staticmethod
    def active_device_path(original):
        selection = original / ACTIVE_AFTER_RESET
        try:
            metadata = selection.lstat()
        except FileNotFoundError:
            return original
        except OSError:
            raise LocalRecoveryError('profile-access', 'profile') from None
        try:
            if not stat.S_ISREG(metadata.st_mode) or original.is_symlink():
                raise ValueError('Invalid saved connection selection')
            name = selection.read_text(encoding='ascii')
            if not re.fullmatch(r'after-reset-[a-f0-9]{32}', name):
                raise ValueError('Invalid saved connection directory')
            active = original / name
            if not stat.S_ISDIR(active.lstat().st_mode) or not stat.S_ISREG((active / 'profile.json').lstat().st_mode):
                raise ValueError('Invalid active saved profile')
            return active
        except (FileNotFoundError, ValueError):
            raise LocalRecoveryError('profile-invalid', 'profile') from None
        except OSError:
            raise LocalRecoveryError('profile-access', 'profile') from None

    def device_path(self, profile):
        return self.active_device_path(self.original_device_path(profile))

    def device_dir(self, profile):
        path = self.device_path(profile)
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        return path

    def save(self, profile):
        private_write(self.device_dir(profile) / 'profile.json', json.dumps(target(**profile)).encode())

    def _capsule_path(self, profile, operation, *, create=True):
        if not isinstance(operation, str) or not re.fullmatch('[a-f0-9]{32}', operation):
            raise LocalRecoveryError('operation-invalid', 'operation')
        try:
            directory = self.device_dir(profile) if create else self.device_path(profile)
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
            except FileNotFoundError:
                reason = 'capsule-missing' if not create and parent == directory else 'directory-access'
                raise LocalRecoveryError(reason, location) from None
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
            path = self._capsule_path(profile, operation, create=False)
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

    def connection_profile(self, selected, *, expected_pin=None):
        """Resolve pending work to its original saved identity, before connecting."""
        directory = self.device_dir(selected)
        require_original_ssh_identity(directory)
        _, pending = self._read_operation(directory / 'operation.json', require_access=True)
        if pending is None and expected_pin is None:
            return selected, False
        pending = pending or {}
        try:
            path = directory / 'profile.json'
            known = directory / 'known_hosts'
            if (expected_pin is None and pending.get('recovery_protocol')=='clean-removal-v1' and pending.get('connection_pending') is True
                    and 'previous' not in pending and not path.is_symlink() and not known.is_symlink() and not known.exists()):
                original=self._read_profile(path)
                if any(original[k]!=selected[k] for k in ('host','edition','port')):raise ValueError('foreign profile')
                return original,False  # First connection still requires explicit normal host-key trust.
            if path.is_symlink() or known.is_symlink() or not (pins := known.read_bytes()):
                raise ValueError('missing trust')
            if expected_pin is not None and hashlib.sha256(pins).hexdigest() != expected_pin:
                raise ValueError('missing trust')
            original = self._read_profile(path)
            if any(original[k] != selected[k] for k in ('host', 'edition', 'port')):
                raise ValueError('foreign profile')
            profiles=self.profiles()
            matches = [p for p in profiles if all(p.get(k) == original.get(k) for k in ('host','edition','port','connection'))]
            if matches != [original]:
                raise ValueError('ambiguous profile')
            operation=pending.get('product_operation')
            if operation and [p for p in profiles if (self.pending(p) or {}).get('product_operation')==operation] != [original]:
                raise ValueError('ambiguous operation')
            return original, True
        except (OSError, ValueError, TypeError, KeyError):
            raise UserError('The original saved TV connection and host key are required for recovery. Recovery data was kept.',
                            reason_code='ssh-identity-unverified') from None

    @staticmethod
    def _read_profile(path):
        try:
            raw = _read_with_windows_retry(path.read_text)
        except PermissionError:
            raise LocalRecoveryError('profile-access', 'profile') from None
        saved = json.loads(raw)
        if (type(saved) is not dict or type(saved.get('host')) is not str
                or type(saved.get('edition')) is not str or type(saved.get('port')) is not int
                or any(key in saved and type(saved[key]) is not str
                       for key in ('identity', 'connection', 'root_variant'))):
            raise ValueError('Invalid saved profile fields')
        return target(**saved)

    def _saved_profile(self, directory):
        path = directory / 'profile.json'
        try:
            if not stat.S_ISREG(path.stat().st_mode):
                raise ValueError('Invalid profile file')
            profile = self._read_profile(path)
            if self.device_path(profile) != directory:
                raise ValueError('Profile in the wrong directory')
            return profile
        except FileNotFoundError:
            return None
        except OSError:
            raise LocalRecoveryError('profile-access', 'profile') from None
        except (ValueError, TypeError):
            raise LocalRecoveryError('profile-invalid', 'profile') from None

    def saved_profile(self, selector):
        """Read an exact saved connection key without creating its directory."""
        return self._saved_profile(self.device_path(selector))

    def profiles(self, *, on_profile_error=None, already_read=None):
        def report_error(error):
            if on_profile_error is None:
                raise error from None
            on_profile_error(error)

        # Unlike a glob, explicit enumeration and probes surface a denied root
        # listing or child traversal. Probe only the saved-profile namespace.
        try:
            directories = sorted(self.root.iterdir())
        except FileNotFoundError:
            return []
        except OSError:
            report_error(LocalRecoveryError('profile-access', 'profile'))
            return []
        result = []
        for directory in directories:
            if not re.fullmatch('[a-f0-9]{24}', directory.name):
                continue
            try:
                active = self.active_device_path(directory)
                profile = already_read[1] if already_read and active == already_read[0] else self._saved_profile(active)
            except LocalRecoveryError as error:
                report_error(error)
            else:
                if profile is not None:
                    result.append(profile)
        return sorted(result, key=lambda p: (p['host'], p['port'], p['edition']))

    @staticmethod
    def _read_operation(path, *, require_access=False):
        unknown = {'action': 'unknown', 'stage': 'corrupt-receipt; retain evidence and inspect TV'}
        try:
            raw = _read_with_windows_retry(path.read_bytes)
        except FileNotFoundError:
            return None, None
        except OSError as error:
            if require_access:
                raise LocalRecoveryError('operation-access', 'operation',
                                         storage_full=is_storage_full(error)) from None
            return None, unknown
        try:
            result = json.loads(raw)
            if not isinstance(result, dict) or not isinstance(result.get('action'), str):
                raise ValueError('Invalid receipt')
        except ValueError:
            return raw, unknown
        return raw, result

    def pending(self, profile):
        return self._read_operation(self.device_path(profile) / 'operation.json')[1]

    def root_reinstall(self, profile):
        """Return the host's saved reinstall step and payload, never TV authority."""
        if profile['edition'] != 'root':
            return None
        pending = self.pending(profile)
        receipt = pending
        if receipt is None:
            path = self.device_path(profile) / 'clean-removal.json'
            if path.is_symlink():
                return None
            _, receipt = self._read_operation(path)
        if not receipt:
            return None
        payload = receipt.get('root_reinstall_payload')
        variant = receipt.get('root_reinstall_variant')
        pin = receipt.get('root_reinstall_pin')
        installing = pending and pending['action'] in ('install', 'activate-root')
        native = (installing and pending.get('home_backend') == 'c1-native-gate'
                  and pending.get('requires_updater') is False and 'recovery_protocol' not in pending
                  and (pending['action'] == 'activate-root' or pending.get('stage') in ('upload', 'setup')))
        operation = receipt.get('product_operation' if installing else 'removal_operation')
        if native and 'product_operation' not in receipt:
            # An upload receipt has a host identity before it has a device operation.
            operation = receipt.get('diagnostic_id')
        if (not isinstance(payload, str) or not re.fullmatch('[a-f0-9]{64}', payload)
                or variant not in (None, 'node012-beta')
                or not isinstance(pin, str) or not re.fullmatch('[a-f0-9]{64}', pin)
                or not isinstance(operation, str) or not re.fullmatch('[a-f0-9]{32}', operation)):
            return None
        if installing and (native or pending.get('recovery_protocol') == 'root-final-readback-v1'):
            return RootReinstall('installing', payload, operation, variant, pin)
        if (receipt['action'] != 'uninstall' or receipt.get('recovery_protocol') != 'clean-removal-v1'
                or receipt.get('full_project') is not True):
            return None
        result = receipt.get('result')
        if (receipt.get('stage') == 'verified-clean' and isinstance(result, dict)
                and result.get('removed') is True and result.get('verified_clean') is True
                and result.get('restart_required') is not True):
            return RootReinstall('verified' if pending else 'removed', payload, operation, variant, pin)
        return RootReinstall('removing', payload, operation, variant, pin) if pending else None

    def root_reinstall_lineage(self, profile, payload):
        if payload is None:
            return {}
        saved = self.root_reinstall(profile)
        if not saved or saved.stage != 'removed' or saved.payload != payload:
            raise UserError('The saved Root reinstallation changed. Return to the start screen and check again.')
        return {'root_reinstall_payload': saved.payload, 'root_reinstall_variant': saved.variant,
                'root_reinstall_pin': saved.pin}

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

    def request_clean_removal(self, profile, *, root_reinstall_payload=None):
        """Record desired absence under the host lock, without TV authority."""
        directory = self.device_path(profile)
        operation_path = directory / 'operation.json'
        original_bytes, previous = self._read_operation(operation_path, require_access=True)
        if previous and previous.get('recovery_protocol') == 'clean-removal-v1':
            return previous
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
        if root_reinstall_payload is not None:
            if profile['edition'] != 'root' or not re.fullmatch('[a-f0-9]{64}', root_reinstall_payload):
                raise ValueError('Invalid Root reinstall payload')
            known = directory / 'known_hosts'
            require_original_ssh_identity(directory)
            try:
                if known.is_symlink() or not (pins := known.read_bytes()):
                    raise ValueError('missing trust')
            except (OSError, ValueError):
                raise UserError('The original saved TV connection and host key are required for recovery. Recovery data was kept.',
                                reason_code='ssh-identity-unverified') from None
            value['root_reinstall_payload'] = root_reinstall_payload
            value['root_reinstall_variant'] = profile.get('root_variant')
            value['root_reinstall_pin'] = hashlib.sha256(pins).hexdigest()
        if previous is None and not (directory/'known_hosts').exists():value['connection_pending']=True
        if previous is not None:
            original = 'removal-original-' + identifier + '.json'
            private_write(directory / original, original_bytes)
            value.update(previous=previous, original_receipt=original)
            # Original selector/lease; the new ID identifies intent, not a lock bypass.
            current = previous
            while isinstance(current, dict):
                operation = current.get('product_operation')
                if isinstance(operation, str) and re.fullmatch('[a-f0-9]{32}', operation):
                    value['product_operation'] = operation
                    break
                current = current.get('previous')
        private_write(operation_path, json.dumps(value).encode())
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
