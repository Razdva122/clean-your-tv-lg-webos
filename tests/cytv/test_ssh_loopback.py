"""Real SSH handshake against loopback only; never uses TV credentials or discovery."""
import importlib.util
import io
import logging
from pathlib import Path
import socket
import tempfile
import threading
import unittest
from unittest.mock import patch

from cytv import state
from cytv.transport import SSH


@unittest.skipUnless(importlib.util.find_spec('paramiko'), 'Requires SSH build dependencies')
class SSHLoopbackTests(unittest.TestCase):
    def test_no_root_authenticates_with_legacy_rsa_server_and_reuses_saved_key(self):
        import paramiko
        key = paramiko.RSAKey.generate(2048)
        host_key = paramiko.RSAKey.generate(2048)
        raw = io.StringIO()
        key.write_private_key(raw)
        raw = raw.getvalue().encode()

        class Server(paramiko.ServerInterface):
            def get_allowed_auths(self, username):
                return 'publickey'

            def check_auth_publickey(self, username, supplied):
                if username == 'prisoner' and supplied == key:
                    return paramiko.AUTH_SUCCESSFUL
                return paramiko.AUTH_FAILED

        with tempfile.TemporaryDirectory() as tmp, \
                patch('cytv.transport.Path.home', return_value=Path(tmp)/'home'), \
                patch('cytv.transport.developer_key', return_value=(key, raw)) as fetch:
            listener = socket.socket()
            self.addCleanup(listener.close)
            listener.bind(('127.0.0.1', 0))
            listener.listen(1)
            listener.settimeout(5)
            profile = state.target('127.0.0.1', 'no-root', listener.getsockname()[1])
            trusted = []
            for cached in (False, True):
                with self.subTest(cached=cached):
                    done = threading.Event()
                    errors = []

                    def serve():
                        transport = None
                        try:
                            connection, _ = listener.accept()
                            # Model a TV accepting ssh-rsa without advertising
                            # server-sig-algs, so SHA-2 auth cannot succeed.
                            transport = paramiko.Transport(connection, server_sig_algs=False,
                                disabled_algorithms={'pubkeys': ['rsa-sha2-512', 'rsa-sha2-256']})
                            transport.add_server_key(host_key)
                            transport.start_server(server=Server())
                            done.wait(5)
                        except Exception as exc:
                            errors.append(exc)
                        finally:
                            if transport is not None:
                                transport.close()

                    thread = threading.Thread(target=serve, daemon=True)
                    thread.start()
                    try:
                        remote = SSH.connect(profile, tmp, lambda _: 'test-passphrase',
                                             lambda *args: trusted.append(args) or True)
                        try:
                            self.assertTrue(remote.client.get_transport().is_authenticated())
                        finally:
                            remote.close()
                    finally:
                        done.set()
                        thread.join(timeout=6)
                    self.assertFalse(thread.is_alive())
                    self.assertEqual(errors, [])
                    self.assertEqual((Path(tmp)/'developer-key.pem').read_bytes(), raw)
            fetch.assert_called_once_with('127.0.0.1', 'test-passphrase')
            self.assertEqual(len(trusted), 1)
            self.assertFalse(trusted[0][1])

    def test_persisted_pin_reconnects_and_changed_key_is_rejected_before_auth(self):
        import paramiko
        logger = logging.getLogger('paramiko.transport')
        previous_handlers, previous_propagate = list(logger.handlers), logger.propagate
        logger.handlers, logger.propagate = [logging.NullHandler()], False
        def restore_logging():
            logger.handlers, logger.propagate = previous_handlers, previous_propagate
        self.addCleanup(restore_logging)
        public_key = [None]
        auth_events = []
        class Server(paramiko.ServerInterface):
            def __init__(self):
                self.executed = threading.Event()
            def check_auth_none(self, username):
                auth_events.append('none')
                return paramiko.AUTH_SUCCESSFUL if username == 'root' and public_key[0] is None else paramiko.AUTH_FAILED
            def get_allowed_auths(self, username):
                return 'publickey,password'
            def check_auth_publickey(self, username, key):
                auth_events.append('publickey')
                return paramiko.AUTH_SUCCESSFUL if username == 'root' and key == public_key[0] else paramiko.AUTH_FAILED
            def check_auth_password(self, username, password):
                auth_events.append('password')
                return paramiko.AUTH_SUCCESSFUL if username == 'root' and password == 'loopback-test-password' else paramiko.AUTH_FAILED
            def check_channel_request(self, kind, channel):
                return paramiko.OPEN_SUCCEEDED if kind == 'session' else paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED
            def check_channel_exec_request(self, channel, command):
                self.command = command
                self.executed.set()
                return True
        listener = socket.socket()
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(('127.0.0.1', 0))
        listener.listen(4)
        listener.settimeout(0.2)
        self.addCleanup(listener.close)
        stop = threading.Event()
        self.addCleanup(stop.set)
        current = [paramiko.RSAKey.generate(2048)]
        def serve():
            while not stop.is_set():
                try:
                    connection, _ = listener.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break
                # Root connections must retain RSA SHA-2 authentication.
                transport = paramiko.Transport(connection, disabled_algorithms={'pubkeys': ['ssh-rsa']})
                try:
                    transport.add_server_key(current[0])
                    server = Server()
                    transport.start_server(server=server)
                    channel = transport.accept(3)
                    if channel and server.executed.wait(3):
                        if server.command == b'printf CYTV_LOOPBACK_OK':
                            channel.sendall(b'CYTV_LOOPBACK_OK')
                            channel.send_exit_status(0)
                        else:
                            channel.send_exit_status(1)
                        channel.shutdown_write()
                        # The client closes after consuming the terminal status.
                        channel.closed or channel.status_event.wait(1)
                except (EOFError, OSError, paramiko.SSHException):
                    pass  # Expected when the changed-host-key connection is rejected.
                finally:
                    transport.close()
        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        self.addCleanup(lambda: thread.join(timeout=5))
        with tempfile.TemporaryDirectory() as tmp, patch('cytv.transport.Path.home', return_value=Path(tmp)/'home'):
            profile = state.target('127.0.0.1', 'root', listener.getsockname()[1])
            prompts = []
            def trust(value, root):
                prompts.append((value, root))
                return True
            def no_password(_):
                self.fail('Loopback root login must use none auth')
            for _ in range(2):
                client = SSH.connect(profile, Path(tmp), no_password, trust)
                try:
                    self.assertEqual(client.run('printf CYTV_LOOPBACK_OK'), 'CYTV_LOOPBACK_OK')
                finally:
                    client.close()
            self.assertEqual(len(prompts), 1)
            self.assertTrue(prompts[0][1])
            # A matching key from ordinary OpenSSH trust suppresses first-use
            # confirmation and is pinned only for this TV/port after login.
            home = Path(tmp)/'home'
            (home/'.ssh').mkdir(parents=True)
            name = f"[127.0.0.1]:{profile['port']}"
            standard = paramiko.HostKeys()
            standard.add(paramiko.HostKeys.hash_host(name), current[0].get_name(), current[0])
            standard.add('unrelated.example', current[0].get_name(), current[0])
            standard.save(str(home/'.ssh/known_hosts'))
            imported = Path(tmp)/'imported'
            imported.mkdir()
            client = SSH.connect(profile, imported, no_password,
                                 lambda *_: self.fail('Matching OpenSSH key asked for confirmation'))
            client.close()
            self.assertTrue((imported/'known_hosts').is_file())
            self.assertNotIn('unrelated.example', (imported/'known_hosts').read_text())
            # An agent key signs a real SSH challenge; no credential question is
            # allowed when this automatic login succeeds.
            public_key[0] = paramiko.RSAKey.generate(2048)
            class Agent:
                closed = False
                def get_keys(self): return (public_key[0],)
                def close(self): self.closed = True
            agent = Agent()
            with patch.object(paramiko, 'Agent', return_value=agent):
                client = SSH.connect(profile, Path(tmp), no_password, trust,
                                     identity_prompt=lambda: self.fail('Key path requested before agent login'))
                try:
                    self.assertEqual(client.run('printf CYTV_LOOPBACK_OK'), 'CYTV_LOOPBACK_OK')
                finally:
                    client.close()
            self.assertTrue(agent.closed)
            self.assertIn('publickey', auth_events)
            self.assertEqual(len(prompts), 1)

            # Inspect-only auth must use the original local pin and leave its
            # bytes/mode/inode unchanged even after password fallback succeeds.
            pinned = Path(tmp)/'known_hosts'
            before = (pinned.read_bytes(), pinned.stat().st_mode, pinned.stat().st_ino)
            profile_before = dict(profile)
            with patch.object(paramiko, 'Agent') as factory:
                factory.return_value.get_keys.return_value = ()
                client = SSH.connect(profile, Path(tmp), lambda _: 'loopback-test-password',
                                     lambda *_: self.fail('Inspect asked for new trust'), persist=False)
                self.assertEqual(client.run('printf CYTV_LOOPBACK_OK'), 'CYTV_LOOPBACK_OK')
                client.close()
            self.assertEqual(before, (pinned.read_bytes(), pinned.stat().st_mode, pinned.stat().st_ino))
            self.assertEqual(profile, profile_before)
            from cytv.errors import UserError
            with self.assertRaisesRegex(UserError,'SSH host key was not verified'):
                SSH.connect(profile, Path(tmp)/'missing-pin',
                            lambda _: self.fail('Missing pin asked for a secret'),
                            lambda *_: self.fail('Missing pin asked for trust'), persist=False)

            # A locked/confirmation-denied agent fails inside Paramiko's signing
            # thread. Offer a manual choice only after closing that connection.
            class RefusingKey:
                def __getattr__(self, name): return getattr(public_key[0], name)
                def sign_ssh_data(self, *args): raise paramiko.SSHException('key cannot be used for signing')
            class RefusingAgent:
                closed = False
                def get_keys(self): return (RefusingKey(),)
                def close(self): self.closed = True
            refusing = RefusingAgent()
            choices = []
            def choose_password():
                self.assertTrue(refusing.closed)
                choices.append('password')
                return None
            with patch.object(paramiko, 'Agent', return_value=refusing) as factory:
                client = SSH.connect(profile, Path(tmp), lambda _: 'loopback-test-password', trust,
                                     identity_prompt=choose_password)
                try:
                    self.assertEqual(client.run('printf CYTV_LOOPBACK_OK'), 'CYTV_LOOPBACK_OK')
                finally:
                    client.close()
            factory.assert_called_once()
            self.assertEqual(choices, ['password'])
            self.assertEqual(auth_events.count('password'), 2)
            self.assertEqual(len(prompts), 1)
            from cytv.transport import AgentLoginFailed
            with patch.object(paramiko,'Agent',return_value=RefusingAgent()),self.assertRaises(AgentLoginFailed):
                SSH.connect(profile,Path(tmp),lambda _:self.fail('Interrupted agent asked for password'),trust,
                            identity_prompt=lambda:self.fail('Inspect reconnected'),persist=False)

            # An explicitly configured key is loaded lazily after host trust.
            keyfile = Path(tmp) / 'test-root-key'
            public_key[0].write_private_key_file(str(keyfile))
            profile['identity'] = str(keyfile)
            client = SSH.connect(profile, Path(tmp), no_password, trust)
            client.close()
            pinned = (Path(tmp) / 'known_hosts').read_bytes()
            current[0] = paramiko.RSAKey.generate(2048)
            # A changed global record cannot override the installer's saved pin.
            standard.add(name, current[0].get_name(), current[0])
            standard.save(str(home/'.ssh/known_hosts'))
            auth_count = len(auth_events)
            with self.assertRaises(paramiko.BadHostKeyException):
                SSH.connect(profile, Path(tmp), no_password, trust)
            with self.assertRaises(paramiko.BadHostKeyException):
                SSH.connect(profile, Path(tmp), no_password, trust, persist=False)
            self.assertEqual(len(auth_events), auth_count)
            self.assertEqual(len(prompts), 1)
            self.assertEqual((Path(tmp) / 'known_hosts').read_bytes(), pinned)
        stop.set()


if __name__ == '__main__':
    unittest.main()
