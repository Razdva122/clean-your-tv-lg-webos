"""Portable SSH, bounded Luna replies and verified atomic file transfer."""
import base64
import codecs
import hashlib
import http.client
import io
import json
import os
from pathlib import Path
import shlex
import stat
import time
import urllib.request

from .state import private_write
from .errors import reports_storage_full, UserError, TVRejected, DeveloperKeyError, TVCommandError


class AgentLoginFailed(UserError):
    """An automatic agent attempt needs an explicit fresh manual connection."""


class CredentialPrompt(str):
    """A string-compatible secret prompt with a language-independent type."""
    def __new__(cls, text, credential_type):
        if credential_type not in ('key', 'root', 'developer'):
            raise ValueError('Unsupported credential type')
        prompt = super().__new__(cls, text)
        prompt.credential_type = credential_type
        return prompt


def inspection_secret(prompt):
    import getpass
    import warnings
    # Refuse getpass's echoed fallback, including in frozen console builds.
    with warnings.catch_warnings():
        warnings.simplefilter('error', getpass.GetPassWarning)
        return getpass.getpass(prompt)


class JsonReplies:
    def __init__(self):
        self.text = ''
        self.utf8 = codecs.getincrementaldecoder('utf-8')()

    def feed(self, data):
        self.text += self.utf8.decode(data)
        if len(self.text) > 1024 * 1024:
            raise ValueError('Oversized TV response')
        result, decoder = [], json.JSONDecoder()
        while self.text.strip():
            self.text = self.text.lstrip()
            try:
                value, offset = decoder.raw_decode(self.text)
            except ValueError:
                break
            if not isinstance(value, dict):
                raise ValueError('Invalid TV response')
            result.append(value)
            self.text = self.text[offset:]
        return result


def terminal_reply(reply, terminal=None, uri=None):
    details = reply.get('details', {})
    if not isinstance(details, dict) or reply.get('returnValue') is False or 'errorCode' in reply or 'errorCode' in details:
        raise TVRejected('TV rejected the operation. Run cytv doctor; no automatic retry was attempted.', reply, uri)
    status = str(details.get('state', '')).lower()
    if 'fail' in status or 'error' in status:
        raise TVRejected('TV package operation failed. Run cytv status before retrying.', reply, uri)
    if terminal:
        return status in (terminal, 'success')
    return reply.get('returnValue') is True


def fingerprint(key):
    return 'SHA256:' + base64.b64encode(hashlib.sha256(key.asbytes()).digest()).decode().rstrip('=')


def trusted_host_keys(known, host, port, standard=None):
    """Reuse exact OpenSSH host/port records without replacing a cytv pin."""
    import paramiko
    from paramiko.hostkeys import HostKeyEntry
    keys = paramiko.HostKeys(str(known)) if Path(known).exists() else paramiko.HostKeys()
    name = host if port == 22 else f'[{host}]:{port}'
    pinned = keys.lookup(name) is not None
    standard = Path(standard) if standard is not None else Path.home() / '.ssh/known_hosts'
    if not standard.exists():
        return keys
    def matches(pattern):
        if pattern == name:
            return True
        if pattern.startswith('|1|'):
            try:
                return paramiko.HostKeys.hash_host(name, pattern) == pattern
            except (ValueError, AssertionError):
                pass
        return False

    with standard.open(encoding='utf-8', errors='replace') as stream:
        for line in stream:
            fields = line.split()
            if not fields or fields[0].startswith('#'):
                continue
            marker = fields.pop(0) if fields[0].startswith('@') else None
            if not fields or not any(matches(pattern) for pattern in fields[0].split(',')):
                continue
            if marker:
                raise UserError('This TV has a revoked or unsupported SSH trust record. Verify it through your existing trusted SSH setup before continuing.', reason_code='ssh-trust-record')
            try:
                entry = HostKeyEntry.from_line(' '.join(fields))
            except (paramiko.SSHException, paramiko.hostkeys.InvalidHostKey, ValueError):
                raise UserError('The saved SSH key for this TV could not be read. Verify the entry through your existing trusted SSH setup before continuing.', reason_code='ssh-trust-record') from None
            if entry is None:
                raise UserError('The saved SSH key for this TV is unsupported. Verify it through your existing trusted SSH setup before continuing.', reason_code='ssh-trust-record')
            if not pinned:
                keys.add(name, entry.key.get_name(), entry.key)
    return keys


def save_host_keys(keys, path):
    stream = io.StringIO()
    for name, values in keys.items():
        for kind, value in values.items():
            stream.write(f'{name} {kind} {value.get_base64()}\n')
    private_write(path, stream.getvalue().encode())


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise DeveloperKeyError('Key Server redirected unexpectedly. Check the TV address and Key Server.', 'response-redirect')


def developer_key(host, passphrase):
    import paramiko
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(f'http://{host}:9991/webos_rsa', timeout=10) as response:
            data = response.read(65537)
    except (OSError, http.client.HTTPException):
        raise DeveloperKeyError('Could not reach Key Server. Check the TV address, network and Key Server switch.', 'key-server-unavailable') from None
    if len(data) > 65536:
        raise DeveloperKeyError('Key Server returned an oversized response. Check the TV address and Key Server.', 'response-size')
    try:
        text = data.decode('utf-8')
    except UnicodeError:
        text = ''
    if not any(line in text.splitlines() for line in ('-----BEGIN RSA PRIVATE KEY-----', '-----BEGIN OPENSSH PRIVATE KEY-----')):
        raise DeveloperKeyError('Key Server did not return a supported private key. Check the TV address and Key Server.', 'response-format')
    try:
        key = paramiko.RSAKey.from_private_key(io.StringIO(text), password=passphrase)
    except (ValueError, paramiko.SSHException):
        raise DeveloperKeyError('Could not unlock the TV key. Enter the current six-character passphrase exactly, including letter case. The key may also be damaged or unsupported.', 'key-unlock') from None
    result = io.StringIO()
    key.write_private_key(result)
    return key, result.getvalue().encode()


def load_identity(path, secret):
    import paramiko
    try:
        return paramiko.PKey.from_path(path)
    except (TypeError, ValueError, paramiko.PasswordRequiredException):
        return paramiko.PKey.from_path(path, passphrase=secret(CredentialPrompt('SSH key passphrase: ', 'key')).encode())


def root_auth(secret, profile=None, identity_prompt=None, automatic=True, password_fallback=False):
    import paramiko
    from paramiko.auth_strategy import AuthResult, AuthStrategy, InMemoryPrivateKey, NoneAuth, OnDiskPrivateKey, Password, SourceResult
    if profile is None:
        profile = {}

    class RootAuth(AuthStrategy):
        def get_sources(self):
            if profile.get('identity'):
                path = Path(profile['identity'])
                yield OnDiskPrivateKey('root', 'python-config', path, load_identity(path, secret))
                if not password_fallback:
                    return
            elif automatic:
                yield NoneAuth(username='root')
                try:
                    self.agent = paramiko.Agent()
                    keys = self.agent.get_keys()
                except (OSError, paramiko.SSHException):
                    keys = ()
                # Bound automatic key attempts to avoid exhausting server auth limits.
                for key in keys[:3]:
                    yield InMemoryPrivateKey(username='root', pkey=key)
            path = identity_prompt() if identity_prompt else None
            if path:
                yield OnDiskPrivateKey('root', 'python-config', Path(path), load_identity(Path(path), secret))
            else:
                yield Password(username='root', password_getter=lambda: secret(CredentialPrompt('Root SSH password (hidden): ', 'root')))

        def authenticate(self, transport):
            self.agent = None
            overall = AuthResult(strategy=self)
            try:
                for source in self.get_sources():
                    try:
                        result = source.authenticate(transport)
                    except paramiko.AuthenticationException as exc:
                        # Paramiko 3.5 also uses this exception for timeout/EOF.
                        # Only a resolved negative reply permits another method.
                        event = getattr(getattr(transport, 'auth_handler', None), 'auth_event', None)
                        if (not transport.is_active() or event is None or not event.is_set()
                                or transport.is_authenticated()):
                            raise
                        overall.append(SourceResult(source, exc))
                        continue
                    except paramiko.SSHException:
                        if isinstance(source, InMemoryPrivateKey):
                            raise AgentLoginFailed('Automatic agent sign-in was interrupted. Retry interactively with a password or --identity.') from None
                        raise
                    if result:
                        raise UserError('TV requires additional SSH authentication. Use your existing trusted SSH setup; no installation was submitted.')
                    overall.append(SourceResult(source, result))
                    if isinstance(source, OnDiskPrivateKey):
                        profile['identity'] = str(source.path)
                    return overall
                raise paramiko.AuthenticationException('Root SSH authentication failed')
            finally:
                if self.agent is not None:
                    self.agent.close()

    return RootAuth(ssh_config=None)


class SSH:
    def __init__(self, client, root=False):
        self.client = client
        self.root = root

    @classmethod
    def connect(cls, profile, directory, secret, trust, identity_prompt=None, automatic=True, persist=True):
        import paramiko
        root_ssh = profile['edition'] == 'root' or profile.get('connection') == 'root-ssh'
        directory = Path(directory)
        known = directory / 'known_hosts'
        if not persist:
            # Internal inspection requires the original cytv pin, never TOFU or
            # importing a replacement from the user's current OpenSSH config.
            name = profile['host'] if profile['port'] == 22 else f"[{profile['host']}]:{profile['port']}"
            if not known.is_file() or not paramiko.HostKeys(str(known)).lookup(name):
                raise UserError('SSH host key was not verified. Connection cancelled.', reason_code='ssh-identity-unverified')
            profile = dict(profile)
        client = paramiko.SSHClient()
        keys = trusted_host_keys(known, profile['host'], profile['port'])
        for name, values in keys.items():
            for kind, value in values.items():
                client.get_host_keys().add(name, kind, value)

        class PinnedPolicy(paramiko.MissingHostKeyPolicy):
            def missing_host_key(self, connection, hostname, key):
                if not persist or not trust(fingerprint(key), root_ssh):
                    raise UserError('SSH host key was not verified. Connection cancelled.', reason_code='ssh-identity-unverified')
                connection.get_host_keys().add(hostname, key.get_name(), key)
                save_host_keys(connection.get_host_keys(), known)

        client.set_missing_host_key_policy(PinnedPolicy())
        options = dict(hostname=profile['host'], port=profile['port'],
                       username='root' if root_ssh else 'prisoner',
                       timeout=10, banner_timeout=10, auth_timeout=15,
                       allow_agent=False, look_for_keys=False)
        if not root_ssh:
            # Developer Mode SSH servers may accept only ssh-rsa and omit
            # server-sig-algs; Paramiko otherwise attempts an RSA SHA-2 signature.
            options['disabled_algorithms'] = {'pubkeys': ['rsa-sha2-512', 'rsa-sha2-256']}
            keyfile = directory / 'developer-key.pem'
            if keyfile.exists():
                options['pkey'] = paramiko.RSAKey.from_private_key_file(str(keyfile))
            elif not persist:
                client.close()
                raise UserError('The saved Developer Mode key is required for recovery. Recovery data was kept.', reason_code='ssh-identity-unverified')
            else:
                key, raw = developer_key(profile['host'], secret(CredentialPrompt('Developer Mode passphrase: ', 'developer')))
                options['pkey'] = key
                # Store only after a successful SSH authentication.
        else:
            options['auth_strategy'] = root_auth(secret, profile, identity_prompt, automatic, password_fallback=not persist)
        try:
            client.connect(**options)
            if persist:
                save_host_keys(client.get_host_keys(), known)
            if persist and not root_ssh and not keyfile.exists():
                private_write(keyfile, raw)
            return cls(client, root=root_ssh)
        except AgentLoginFailed:
            client.close()
            if not persist or not automatic or identity_prompt is None:
                raise
            # Signing refusal can close Paramiko's transport. The user explicitly
            # chooses a manual retry; its new connection verifies the pin again.
            path = identity_prompt()
            retry = dict(profile)
            if path:
                retry['identity'] = path
            remote = cls.connect(retry, directory, secret, trust, automatic=False)
            profile.update(retry)
            return remote
        except BaseException:
            client.close()
            raise

    def close(self):
        self.client.close()

    def channel(self, command):
        transport = self.client.get_transport()
        if transport is None or not transport.is_active():
            raise UserError('TV SSH connection closed. Run cytv status before retrying.',reason_code='connection-interrupted')
        channel = transport.open_session(timeout=10)
        channel.settimeout(30)
        channel.exec_command(command)
        return channel

    def chunks(self, channel, timeout):
        deadline, total = time.monotonic() + timeout, 0
        stderr_tail, storage_full = b'', False
        while time.monotonic() < deadline:
            if channel.recv_ready():
                data = channel.recv(65536)
                total += len(data)
                if total > 8 * 1024 * 1024:
                    raise UserError('TV response exceeded the size limit.')
                yield data
            elif channel.recv_stderr_ready():
                data = channel.recv_stderr(65536)
                total += len(data)
                stderr_tail = (stderr_tail + data)[-65536:]
                storage_full = storage_full or reports_storage_full(stderr_tail)
                stderr_tail = stderr_tail[-64:]
                if total > 8 * 1024 * 1024:
                    raise UserError('TV response exceeded the size limit.')
            elif channel.exit_status_ready():
                status = channel.recv_exit_status()
                if status != 0:
                    raise TVCommandError(status, storage_full=storage_full)
                return
            elif channel.closed:
                raise UserError('TV connection interrupted. Run cytv status before retrying.',reason_code='connection-interrupted')
            else:
                time.sleep(0.02)
        raise UserError('TV operation timed out. Run cytv status before retrying.', reason_code='operation-timeout')

    def run(self, command, data=None, timeout=30):
        # Some TV SSH servers disconnect on large exec requests. A builtin read
        # consumes only the command header; binary stdin stays on the channel.
        if len(command.encode('utf-8')) > 4096:
            data = base64.b64encode(command.encode('utf-8')) + b'\n' + (data or b'')
            command = ('IFS= read -r cytv_ssh_source || exit 1; '
                       'cytv_ssh_source=$(printf %s "$cytv_ssh_source" | base64 -d && printf .) || exit 1; '
                       'exec /bin/sh -c "${cytv_ssh_source%.}"')
        channel = self.channel(command)
        try:
            if data is not None:
                channel.sendall(data)
            channel.shutdown_write()
            return b''.join(self.chunks(channel, timeout)).decode('utf-8')
        finally:
            channel.close()

    @staticmethod
    def _upload_command(path, digest, mode):
        if mode not in (0o600, 0o640, 0o644, 0o755):
            raise ValueError('Unsupported TV file mode')
        path = str(path)
        permissions = {0o600: '-rw-------', 0o640: '-rw-r-----', 0o644: '-rw-r--r--', 0o755: '-rwxr-xr-x'}[mode]
        parent = path.rsplit('/', 1)[0]
        return (
            'set -e; umask 077; tmp=$(mktemp ' + shlex.quote(parent + '/.cytv.XXXXXX') + '); '
            'trap \'rm -f "$tmp"\' EXIT; cat > "$tmp"; '
            f'chmod {mode:o} "$tmp"; '
            '[ "$(LC_ALL=C ls -ld "$tmp" | cut -c1-10)" = ' + shlex.quote(permissions) + ' ]; '
            '[ "$(sha256sum "$tmp" | cut -d " " -f 1)" = ' + shlex.quote(digest) + ' ]; '
            'mv -f "$tmp" ' + shlex.quote(path) + '; printf CYTV_UPLOAD_OK')
    def upload(self, path, data, mode=0o600):
        command = self._upload_command(path, hashlib.sha256(data).hexdigest(), mode)
        if self.run(command, data=data, timeout=90).strip() != 'CYTV_UPLOAD_OK':
            raise UserError('TV upload could not be verified. Existing destination was not confirmed.')

    def upload_file(self, path, source, mode=0o600, timeout=600):
        """Transfer a large verified asset without keeping another copy in memory."""
        source = Path(source)
        info = source.lstat()
        if not stat.S_ISREG(info.st_mode):
            raise ValueError('Upload source must be a regular file')
        fd = os.open(source, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
        with os.fdopen(fd, 'rb') as stream:
            opened = os.fstat(stream.fileno())
            if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
                raise ValueError('Upload source changed')
            digest = hashlib.sha256()
            for chunk in iter(lambda: stream.read(256 * 1024), b''):
                digest.update(chunk)
            command = self._upload_command(path, digest.hexdigest(), mode)
            stream.seek(0)
            deadline = time.monotonic() + timeout
            channel = self.channel(command)
            try:
                for chunk in iter(lambda: stream.read(256 * 1024), b''):
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise UserError('TV operation timed out. Run cytv status before retrying.')
                    channel.settimeout(min(30, remaining))
                    channel.sendall(chunk)
                channel.shutdown_write()
                remaining = max(0, deadline - time.monotonic())
                reply = b''.join(self.chunks(channel, remaining)).decode('utf-8').strip()
                if reply != 'CYTV_UPLOAD_OK':
                    raise UserError('TV upload could not be verified. Existing destination was not confirmed.')
            finally:
                channel.close()

    def luna(self, uri, payload, terminal=None, timeout=30, app_id=None):
        args = ['/usr/bin/luna-send' if self.root else '/usr/bin/luna-send-pub', '-i' if terminal else '-n', *([] if terminal else ['1']),
                *(['-a', app_id, '-m', app_id + '-cytv'] if app_id else []),
                'luna://' + uri, json.dumps(payload, separators=(',', ':'))]
        channel, parser = self.channel(shlex.join(args)), JsonReplies()
        try:
            # On the tested TV luna-send exits before replying if stdin receives EOF.
            for chunk in self.chunks(channel, timeout):
                for reply in parser.feed(chunk):
                    if terminal_reply(reply, terminal, uri):
                        return reply
            raise UserError('TV command ended without a confirmed result. Run cytv status.')
        finally:
            channel.close()
