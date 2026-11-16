"""Start a fresh Developer Mode connection after an explicitly confirmed reset."""
import json
import shutil
import stat
import uuid

from .errors import UserError
from .state import ACTIVE_AFTER_RESET, private_write, sync_directory
from .transport import fingerprint


def original_pins(store, profile):
    import paramiko

    if profile['edition'] != 'no-root' or profile.get('connection') or profile.get('identity'):
        raise UserError('The original saved TV connection and host key are required for recovery.')
    directory = store.device_path(profile)
    try:
        if directory.is_symlink() or store.original_device_path(profile).is_symlink():
            raise ValueError('Linked TV profile')
        if store.saved_profile(profile) != profile:
            raise ValueError('Missing or different saved profile')
        for name in ('profile.json', 'known_hosts', 'operation.json'):
            path = directory / name
            if name == 'operation.json' and not path.exists() and not path.is_symlink():
                continue
            if not stat.S_ISREG(path.lstat().st_mode):
                raise ValueError('Invalid saved connection file')
        pin = paramiko.HostKeys(str(directory / 'known_hosts')).lookup(
            profile['host'] if profile['port'] == 22 else f"[{profile['host']}]:{profile['port']}")
        if not pin:
            raise ValueError('Missing saved SSH key')
    except (OSError, ValueError, paramiko.SSHException, paramiko.hostkeys.InvalidHostKey):
        raise UserError('The original saved TV connection and host key are required for recovery.') from None
    _, pending = store._read_operation(directory / 'operation.json', require_access=True)
    if pending is not None and pending['action'] != 'uninstall':
        raise UserError('An earlier operation is unresolved. Choose Review recovery options or run cytv recover with the original TV connection.')
    return next(iter(pin)), {fingerprint(key) for key in pin.values()}


def reconnect(store, profile, connect, trust, old_pins):
    # The caller holds the TV's session lock. Legacy readers still see the
    # original files and never apply the old uninstall to the new connection.
    original = store.original_device_path(profile)
    stage = original / ('after-reset-' + uuid.uuid4().hex)
    stage.mkdir(mode=0o700)
    remote = None

    def confirm(value, root):
        if value in old_pins:
            raise UserError('The TV still uses its saved SSH key. Continue with the existing connection.')
        return trust(value, root)

    try:
        remote = connect(stage, confirm)
        if not all((stage / name).is_file() for name in ('known_hosts', 'developer-key.pem')):
            raise UserError('The original saved TV connection and host key are required for recovery.')
        private_write(stage / 'profile.json', json.dumps(profile).encode())
        sync_directory(original)
    except BaseException:
        if remote is not None:
            remote.close()
        shutil.rmtree(stage, ignore_errors=True)
        raise
    try:
        # Publish only after SSH authentication and all new files are durable.
        private_write(original / ACTIVE_AFTER_RESET, stage.name.encode('ascii'))
    except BaseException:
        remote.close()
        raise
    return remote
