"""Verify a changed Root SSH identity without inheriting removal authority."""
import hashlib
import json
import re
import socket
import stat

from .errors import UserError
from .state import SSH_IDENTITY_REVIEW, private_write, target
from .transport import fingerprint, trusted_host_keys


FULL_FINGERPRINT = re.compile(r'SHA256:[A-Za-z0-9+/]{43}')


def read_record(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError('Expected an original local record')
    return path.read_bytes()


def original_evidence(directory):
    return {name: read_record(directory / name)
            for name in ('profile.json', 'operation.json', 'known_hosts')}


def presented_key(host, port, preferred_type):
    import paramiko
    try:
        with socket.create_connection((host, port), timeout=10) as connection:
            with paramiko.Transport(connection) as session:
                session.banner_timeout = 10
                # Negotiate with the same preference as the original pinned login.
                security = session.get_security_options()
                security.key_types = (preferred_type, *(kind for kind in security.key_types if kind != preferred_type))
                session.start_client(timeout=10)
                return session.get_remote_server_key()
    except (EOFError, OSError, paramiko.SSHException):
        raise UserError('Could not verify the current SSH host key. Check the saved TV address and SSH port.') from None


def review(store, selected, ask, write):
    host, port = selected['host'], selected['port']
    with store.lock(selected):
        directory = store.device_dir(selected)
        if directory.is_symlink():
            raise ValueError('Linked profile')
        evidence = original_evidence(directory)
        saved = target(**json.loads(evidence['profile.json']))
        pending = json.loads(evidence['operation.json'])
        if (any(saved.get(key) != selected.get(key) for key in ('host', 'port', 'edition', 'connection'))
                or not isinstance(pending, dict) or pending.get('action') != 'uninstall'):
            raise ValueError('Expected a saved Root uninstall')
        name = host if port == 22 else f'[{host}]:{port}'
        known = directory / 'known_hosts'
        # An OpenSSH fallback cannot supply the original pin for this profile.
        import paramiko
        try:
            original_keys = paramiko.HostKeys(str(known)).lookup(name)
            if not original_keys:
                raise ValueError('Missing original host pin')
            trusted_host_keys(known, host, port)  # Honor OpenSSH revoked/unsupported records.
        except (paramiko.hostkeys.InvalidHostKey, paramiko.SSHException):
            raise UserError('The saved SSH pin could not be read. Keep the recovery records.') from None

        review_path = directory / SSH_IDENTITY_REVIEW
        binding = {name: hashlib.sha256(data).hexdigest() for name, data in evidence.items()}
        try:
            record = json.loads(read_record(review_path))
        except FileNotFoundError:
            record = {'original': binding, 'verified_fingerprint': ''}
        else:
            if (not isinstance(record, dict) or record.get('original') != binding
                    or not FULL_FINGERPRINT.fullmatch(record.get('verified_fingerprint', ''))):
                raise ValueError('Review belongs to different evidence')

        write.selected_profile(saved)
        write('Verify the new SSH fingerprint through a trusted local or on-device method before entering it.')
        write('This confirms the SSH server identity. The earlier uninstall remains blocked.')
        expected = ask('Full verified SHA256 fingerprint (Enter to cancel): ').strip()
        if not expected:
            raise EOFError
        if not FULL_FINGERPRINT.fullmatch(expected):
            raise UserError('Enter the full OpenSSH SHA256 host-key fingerprint.')
        key = presented_key(host, port, next(iter(original_keys)))
        if fingerprint(key) != expected:
            raise UserError('The independently verified fingerprint did not match the current SSH host key.')
        if key == original_keys.get(key.get_name()):
            raise UserError('The endpoint presented an original trusted key. No changed key was recorded.')
        if original_evidence(directory) != evidence:
            raise ValueError('Original evidence changed during review')
        new = {'original': binding, 'verified_fingerprint': expected}
        if record != new:
            private_write(review_path, json.dumps(new, sort_keys=True).encode())
    write('New SSH identity verified and recorded. The earlier uninstall remains blocked.')


def run(args, store, ask, write):
    try:
        if args.non_interactive or not args.host or args.edition == 'no-root' or args.connection or args.identity or args.root_variant:
            raise UserError('Use trust-root-ssh interactively with --host and the saved Root SSH port.')
        review(store, target(args.host, 'root', args.port), ask, write)
    except (EOFError, KeyboardInterrupt, StopIteration):
        write('SSH identity review cancelled.')
        return 130
    except UserError as error:
        write.error(str(error))
        return 2
    except (OSError, ValueError, TypeError):
        write.error('The original saved Root profile, SSH pin and pending uninstall receipt are required. Keep the recovery records.')
        return 2
    return 0
