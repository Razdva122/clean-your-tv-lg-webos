import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from cytv.transport import JsonReplies, terminal_reply, SSH


class RejectedAuthTransport:
    auth_handler = SimpleNamespace(auth_event=SimpleNamespace(is_set=lambda: True))
    def is_active(self): return True
    def is_authenticated(self): return False


class TransportTests(unittest.TestCase):
    def test_diagnostic_command_captures_both_streams_and_nonzero_exit(self):
        from unittest.mock import Mock

        channel = Mock(closed=True)
        channel.recv_ready.side_effect = [True, False]
        channel.recv_stderr_ready.side_effect = [True, False]
        channel.recv.return_value = b'out\n'
        channel.recv_stderr.return_value = b'err\xff\n'
        channel.exit_status_ready.return_value = True
        channel.recv_exit_status.return_value = 42
        ssh = SSH(Mock())
        ssh.channel = Mock(return_value=channel)
        command = "printf 'out\\n'\nprintf 'err\\n' >&2\nexit 42"
        result = ssh.run_command(command)
        self.assertEqual((result.stdout, result.stderr, result.exit_code), ('out\n', 'err�\n', 42))
        self.assertFalse(result.truncated)
        ssh.channel.assert_called_once_with(command)
        channel.shutdown_write.assert_called_once_with()
        channel.close.assert_called_once_with()

    def test_diagnostic_command_timeout_keeps_partial_output(self):
        from unittest.mock import Mock

        channel = Mock(closed=False, eof_received=False)
        channel.recv_ready.side_effect = [True, False]
        channel.recv_stderr_ready.return_value = False
        channel.recv.return_value = b'x' * (256 * 1024 + 1)
        ssh = SSH(Mock())
        ssh.channel = Mock(return_value=channel)
        with patch('cytv.transport.time.monotonic', side_effect=[0, 0, 1, 30]), patch('cytv.transport.time.sleep'):
            result = ssh.run_command('diagnose')
        self.assertEqual(result.stdout, 'x' * (256 * 1024))
        self.assertEqual(result.stderr, '')
        self.assertIsNone(result.exit_code)
        self.assertTrue(result.truncated)
        self.assertIn('Timed out', result.error)
        channel.close.assert_called_once_with()

    def test_failed_command_preserves_only_fixed_space_category(self):
        from cytv.errors import TVCommandError
        from unittest.mock import Mock
        for parts in ([b'PRIVATE: No space left on ', b'device: PRIVATE'],
                      [b'Disk quota exceeded: PRIVATE'], [b'Permission denied: PRIVATE']):
            channel = Mock()
            channel.recv_ready.return_value = False
            channel.recv_stderr_ready.side_effect = [True] * len(parts) + [False]
            channel.recv_stderr.side_effect = parts
            channel.exit_status_ready.return_value = True
            channel.recv_exit_status.return_value = 1
            with self.assertRaises(TVCommandError) as caught:
                list(SSH.__new__(SSH).chunks(channel, 1))
            expected = 'user-error' if b'Permission' in parts[0] else 'tv-storage-full'
            self.assertEqual(caught.exception.reason_code, expected)
            self.assertNotIn('PRIVATE', str(caught.exception))

    def test_inspection_secret_refuses_echo_fallback_and_propagates_cancel(self):
        import getpass
        import warnings
        from cytv.transport import inspection_secret
        def echoed(_):
            warnings.warn('Cannot hide input',getpass.GetPassWarning)
            self.fail('Echoed secret input was reached')
        with patch('getpass.getpass',side_effect=echoed),self.assertRaises(getpass.GetPassWarning):
            inspection_secret('hidden: ')
        for error in (EOFError,KeyboardInterrupt):
            with patch('getpass.getpass',side_effect=error),self.assertRaises(error):inspection_secret('hidden: ')

    def test_developer_authentication_requests_typed_string_without_persisting_on_cancel(self):
        prompts = []
        def secret(prompt):
            self.assertIsInstance(prompt, str)
            self.assertTrue(prompt.startswith('Developer Mode'))
            self.assertEqual(prompt.credential_type, 'developer')
            prompts.append(prompt)
            return 'PRIVATE-SECRET'
        with tempfile.TemporaryDirectory() as tmp, \
             patch('paramiko.SSHClient') as client, \
             patch('cytv.transport.developer_key', return_value=('key', b'PRIVATE-KEY')):
            client.return_value.connect.side_effect = EOFError
            with self.assertRaises(EOFError):
                SSH.connect({'host': '192.0.2.10', 'port': 9922, 'edition': 'no-root'},
                            tmp, secret, lambda *_: False)
            self.assertEqual(len(prompts), 1)
            self.assertFalse(list(Path(tmp).iterdir()))
            client.return_value.close.assert_called_once()

    def test_developer_key_diagnostics_distinguish_response_from_unlock_failure(self):
        import paramiko
        from cytv.transport import developer_key
        from cytv.errors import UserError
        key = paramiko.RSAKey.generate(2048)
        encrypted = io.StringIO()
        key.write_private_key(encrypted, password='Ab1234')
        cases = [('response-format', b'<html>PRIVATE-RESPONSE</html>', 'Ab1234'),
                 ('response-format', b'\xff', 'Ab1234'),
                 ('response-size', b'x' * 65537, 'Ab1234'),
                 ('key-unlock', encrypted.getvalue().encode(), 'WRONG-SECRET')]
        for reason, data, password in cases:
            with self.subTest(reason=reason), patch('cytv.transport.urllib.request.build_opener') as build:
                build.return_value.open.return_value.__enter__.return_value.read.return_value = data
                with self.assertRaises(UserError) as caught:
                    developer_key('mock-tv.invalid', password)
                self.assertEqual(getattr(caught.exception, 'reason_code', None), reason)
                self.assertNotIn('PRIVATE-RESPONSE', str(caught.exception))
                self.assertNotIn('WRONG-SECRET', str(caught.exception))
        with patch('cytv.transport.urllib.request.build_opener') as build:
            build.return_value.open.return_value.__enter__.return_value.read.return_value = encrypted.getvalue().encode()
            actual, raw = developer_key('mock-tv.invalid', 'Ab1234')
            self.assertEqual(actual.asbytes(), key.asbytes())
            self.assertEqual(paramiko.RSAKey.from_private_key(io.StringIO(raw.decode())).asbytes(), key.asbytes())

    def test_developer_key_fetch_failure_is_safe_and_actionable(self):
        from cytv.transport import developer_key
        from cytv.errors import UserError
        with patch('cytv.transport.urllib.request.build_opener') as build:
            build.return_value.open.side_effect = OSError('PRIVATE-HOST')
            with self.assertRaises(UserError) as caught:
                developer_key('mock-tv.invalid', 'PRIVATE-SECRET')
            self.assertEqual(getattr(caught.exception, 'reason_code', None), 'key-server-unavailable')
            self.assertNotIn('PRIVATE-', str(caught.exception))

    def test_developer_key_redirect_is_rejected_without_following_location(self):
        from cytv.errors import DeveloperKeyError
        from cytv.transport import NoRedirect
        with self.assertRaises(DeveloperKeyError) as caught:
            NoRedirect().redirect_request(None, None, 302, 'PRIVATE-MESSAGE', {}, 'http://private.invalid')
        self.assertEqual(caught.exception.reason_code, 'response-redirect')
        self.assertNotIn('PRIVATE', str(caught.exception))

    def test_developer_key_http_protocol_and_read_failures_have_safe_reason(self):
        import http.client
        from cytv.errors import UserError
        from cytv.transport import developer_key
        for error in (http.client.BadStatusLine('PRIVATE-STATUS'),
                      http.client.IncompleteRead(b'PRIVATE-KEY')):
            with self.subTest(error=type(error).__name__), patch('cytv.transport.urllib.request.build_opener') as build:
                build.return_value.open.return_value.__enter__.return_value.read.side_effect = error
                with self.assertRaises(UserError) as caught:
                    developer_key('mock-tv.invalid', 'PRIVATE-SECRET')
                self.assertEqual(caught.exception.reason_code, 'key-server-unavailable')
                self.assertNotIn('PRIVATE-', str(caught.exception))

    def test_updater_status_uses_root_application_identity(self):
        import shlex
        commands = []
        ssh = object.__new__(SSH)
        ssh.root = True
        ssh.channel = lambda command: commands.append(shlex.split(command)) or SimpleNamespace(close=lambda: None)
        ssh.chunks = lambda connection, timeout: [b'{"returnValue":true,"result":null}']
        ssh.luna('com.cleanyourtv.root.updater.service/status', {}, app_id='com.cleanyourtv.root.preview')
        self.assertEqual(commands[0][3:7], ['-a', 'com.cleanyourtv.root.preview', '-m', 'com.cleanyourtv.root.preview-cytv'])

    def test_luna_keeps_stdin_open_until_reply(self):
        class Channel:
            eof = False
            def shutdown_write(self):
                self.eof = True
            def close(self):
                pass
        ssh, channel = object.__new__(SSH), Channel()
        ssh.root = True
        ssh.channel = lambda _: channel
        ssh.chunks = lambda connection, timeout: [] if channel.eof else [b'{"returnValue":true}']
        self.assertTrue(ssh.luna('test/status', {})['returnValue'])

    def test_luna_legacy_readback_requires_opt_in_and_still_rejects_errors(self):
        from cytv.errors import TVRejected, UserError
        ssh = object.__new__(SSH)
        ssh.root = True
        ssh.channel = lambda _: SimpleNamespace(close=lambda: None)
        body = b'{"homeUIState":[{"uiType":"home","visibility":false}]}'
        ssh.chunks = lambda *_: [body]
        with self.assertRaises(UserError):
            ssh.luna('test/status', {})
        self.assertIn('homeUIState', ssh.luna('test/status', {}, allow_missing_return=True))
        body = b'{"returnValue":false,"errorCode":-1}'
        with self.assertRaises(TVRejected):
            ssh.luna('test/status', {}, allow_missing_return=True)

    @unittest.skipUnless(__import__('importlib.util').util.find_spec('paramiko'), 'Requires SSH build dependencies')
    def test_passwordless_root_does_not_request_or_log_password(self):
        from cytv.transport import root_auth
        class Transport:
            def auth_none(self, username):
                self.username = username
                return []
        transport = Transport()
        root_auth(lambda _: self.fail('Password was requested')).authenticate(transport)
        self.assertEqual(transport.username, 'root')

    def test_root_agent_login_precedes_all_credential_questions_and_closes_agent(self):
        import paramiko
        from cytv.transport import root_auth
        calls = []
        class Transport(RejectedAuthTransport):
            def auth_none(self, username):
                calls.append('none')
                raise paramiko.BadAuthenticationType('key required', ['publickey'])
            def auth_publickey(self, username, key):
                calls.append(('key', key))
                return []
        class Agent:
            def get_keys(self): return ('agent-key',)
            def close(self): calls.append('agent-close')
        with patch.object(paramiko, 'Agent', return_value=Agent()):
            root_auth(lambda _: self.fail('Password requested'),
                      identity_prompt=lambda: self.fail('Key path requested')).authenticate(Transport())
        self.assertEqual(calls, ['none', ('key', 'agent-key'), 'agent-close'])

    def test_root_fallback_key_is_requested_only_after_automatic_attempts(self):
        import paramiko
        from cytv.transport import root_auth
        calls, profile = [], {'edition': 'root'}
        class Transport(RejectedAuthTransport):
            def auth_none(self, username):
                calls.append('none'); raise paramiko.AuthenticationException()
            def auth_publickey(self, username, key):
                calls.append(key)
                if key != 'selected-key': raise paramiko.AuthenticationException()
                return []
        class Agent:
            def get_keys(self): return ('agent-key',)
            def close(self): calls.append('agent-close')
        def choose():
            calls.append('choose-key'); return '/chosen/private-key'
        with patch.object(paramiko, 'Agent', return_value=Agent()), \
             patch('cytv.transport.load_identity', return_value='selected-key'):
            root_auth(lambda _: self.fail('Password requested'), profile=profile,
                      identity_prompt=choose).authenticate(Transport())
        self.assertEqual(calls, ['none', 'agent-key', 'choose-key', 'selected-key', 'agent-close'])
        self.assertEqual(profile['identity'], str(Path('/chosen/private-key')))

    def test_root_failed_agent_then_password_and_cancel_are_not_swallowed(self):
        import paramiko
        from cytv.transport import root_auth
        class Transport(RejectedAuthTransport):
            def auth_none(self, username): raise paramiko.AuthenticationException()
            def auth_password(self, username, password):
                self.password = password; return []
        class Agent:
            closed = False
            def get_keys(self): return ()
            def close(self): self.closed = True
        agent, connection = Agent(), Transport()
        with patch.object(paramiko, 'Agent', return_value=agent):
            root_auth(lambda _: 'test-secret', identity_prompt=lambda: None).authenticate(connection)
        self.assertEqual(connection.password, 'test-secret')
        self.assertTrue(agent.closed)
        def cancel(): raise EOFError
        with patch.object(paramiko, 'Agent', return_value=agent), self.assertRaises(EOFError):
            root_auth(lambda _: self.fail('Password requested after cancel'), identity_prompt=cancel).authenticate(Transport())

    def test_root_does_not_continue_after_network_failure_or_partial_auth(self):
        import paramiko
        from cytv.transport import root_auth
        from cytv.errors import UserError
        class Broken:
            def auth_none(self, username): raise OSError('test-only network failure')
        with patch.object(paramiko, 'Agent') as agent, self.assertRaises(OSError):
            root_auth(lambda _: self.fail('Password requested')).authenticate(Broken())
        agent.assert_not_called()
        class Partial:
            def auth_none(self, username): return ['password']
        with self.assertRaises(UserError):
            root_auth(lambda _: self.fail('Password requested')).authenticate(Partial())

    def test_rejected_key_is_not_saved_and_automatic_attempts_are_bounded(self):
        import paramiko
        from cytv.transport import root_auth
        tried, profile = [], {}
        class Transport(RejectedAuthTransport):
            def auth_none(self, username): raise paramiko.AuthenticationException()
            def auth_publickey(self, username, key):
                tried.append(key); raise paramiko.AuthenticationException()
        class Agent:
            def get_keys(self): return tuple(range(10))
            def close(self): pass
        with patch.object(paramiko, 'Agent', return_value=Agent()), \
             patch('cytv.transport.load_identity', return_value='selected-key'), \
             self.assertRaises(paramiko.AuthenticationException):
            root_auth(lambda _: self.fail('Unexpected password retry'), profile=profile,
                      identity_prompt=lambda: '/rejected-key').authenticate(Transport())
        self.assertEqual(tried, [0, 1, 2, 'selected-key'])
        self.assertNotIn('identity', profile)

    def test_paramiko_auth_timeout_and_eof_do_not_advance_to_more_credentials(self):
        import paramiko
        from paramiko.auth_handler import AuthHandler
        import threading
        from cytv.transport import root_auth
        class Transport:
            auth_timeout = 0.01
            def __init__(self, active):
                self.active = active
                self.auth_handler = AuthHandler(self)
                self.auth_handler.auth_event = threading.Event()
            def is_active(self): return self.active
            def is_authenticated(self): return False
            def get_exception(self): return None
            def auth_none(self, username):
                return self.auth_handler.wait_for_response(self.auth_handler.auth_event)
        for active in (True, False):
            with self.subTest(active=active), patch.object(paramiko, 'Agent') as agent, \
                 self.assertRaises(paramiko.AuthenticationException):
                root_auth(lambda _: self.fail('Password requested after network failure'),
                          identity_prompt=lambda: self.fail('Key requested after network failure')).authenticate(Transport(active))
            agent.assert_not_called()

    def test_inspection_can_prompt_after_resolved_rejection_of_original_identity(self):
        import paramiko
        from cytv.transport import root_auth
        profile={'identity':'/original/key'}
        original=dict(profile)
        calls=[]
        class Transport(RejectedAuthTransport):
            def auth_publickey(self,username,key):
                calls.append('key');raise paramiko.AuthenticationException()
            def auth_password(self,username,password):
                calls.append('password');return []
        with patch('cytv.transport.load_identity',return_value='original-key'):
            root_auth(lambda _: 'test-secret',profile=profile,password_fallback=True).authenticate(Transport())
        self.assertEqual(calls,['key','password'])
        self.assertEqual(profile,original)

    @unittest.skipUnless(__import__('importlib.util').util.find_spec('paramiko'), 'Requires SSH build dependencies')
    def test_encrypted_root_identity_is_unlocked_with_hidden_passphrase(self):
        import paramiko
        from cytv.transport import load_identity
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'id_rsa'
            original = paramiko.RSAKey.generate(2048)
            original.write_private_key_file(str(path), password='private-test-passphrase')
            prompts = []
            key = load_identity(path, lambda prompt: prompts.append(prompt) or 'private-test-passphrase')
            self.assertEqual(key.asbytes(), original.asbytes())
            self.assertEqual(len(prompts), 1)
            self.assertIsInstance(prompts[0], str)
            self.assertEqual(prompts[0].credential_type, 'key')

    def test_json_stream_handles_split_utf8_and_multiple_events(self):
        replies = JsonReplies()
        raw = '{"returnValue":true,"label":"ТВ"}\n{"details":{"state":"installed"}}'.encode()
        events = []
        for byte in raw:
            events.extend(replies.feed(bytes([byte])))
        self.assertEqual(events, [{'returnValue': True, 'label': 'ТВ'}, {'details': {'state': 'installed'}}])
        with self.assertRaises(ValueError):
            replies.feed(b'x' * 1048577)

    def test_package_subscription_requires_terminal_event_and_closes_on_uncertainty(self):
        import shlex
        from cytv.errors import UserError
        for action, terminal in (('install', 'installed'), ('remove', 'removed')):
            for outcome in ('terminal', 'denied', 'interrupted', 'timeout'):
                with self.subTest(action=action, outcome=outcome):
                    commands, closed = [], []
                    ssh = object.__new__(SSH)
                    ssh.root = False
                    ssh.channel = lambda cmd: commands.append(shlex.split(cmd)) or SimpleNamespace(close=lambda: closed.append(True))
                    def chunks(channel, timeout):
                        yield b'{"returnValue":true,"subscribed":true}'
                        yield json.dumps({'details': {'state': 'installing' if action == 'install' else 'removing'}}).encode()
                        if outcome == 'terminal':
                            yield json.dumps({'returnValue': True, 'details': {'state': terminal}}).encode()
                        elif outcome == 'denied':
                            yield b'{"returnValue":false,"errorCode":-1}'
                        elif outcome == 'timeout':
                            raise UserError('Timed out')
                    ssh.chunks = chunks
                    uri = 'com.webos.appInstallService/dev/' + action
                    if outcome == 'terminal':
                        self.assertEqual(ssh.luna(uri, {'subscribe': True}, terminal=terminal)['details']['state'], terminal)
                    else:
                        with self.assertRaises(UserError):
                            ssh.luna(uri, {'subscribe': True}, terminal=terminal)
                    self.assertEqual(commands[0][:3], ['/usr/bin/luna-send-pub', '-i', 'luna://' + uri])
                    self.assertEqual(json.loads(commands[0][3]), {'subscribe': True})
                    self.assertEqual(closed, [True])

    def test_acceptance_is_not_terminal_and_failure_is_never_success(self):
        self.assertFalse(terminal_reply({'returnValue': True}, 'installed'))
        self.assertFalse(terminal_reply({'details': {'state': 'installing'}}, 'installed'))
        self.assertTrue(terminal_reply({'details': {'state': 'installed'}}, 'installed'))
        self.assertTrue(terminal_reply({'details': {'state': 'SUCCESS'}}, 'removed'))
        with self.assertRaises(RuntimeError):
            terminal_reply({'returnValue': False, 'details': {'state': 'installed'}}, 'installed')
        with self.assertRaises(RuntimeError):
            terminal_reply({'details': {'state': 'FAILED'}}, 'installed')

    @unittest.skipIf(__import__('os').name == 'nt', 'TV upload script is POSIX, desktop need not be')
    def test_upload_script_atomically_replaces_only_after_hash_and_mode_checks(self):
        # Run the actual TV upload script against a local temp directory, not a shell mock.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'ssap-key.json'
            path.write_bytes(b'old')
            ssh = object.__new__(SSH)
            def execute(command, data=None, timeout=30):
                result = subprocess.run(['sh', '-c', command], input=data, capture_output=True)
                if result.returncode:
                    raise RuntimeError('upload failed')
                return result.stdout.decode()
            ssh.run = execute
            # BSD stat has a different interface; use the portable mode readback through ls.
            ssh.upload(str(path), b'{"key":"private"}', mode=0o640)
            self.assertEqual(path.read_bytes(), b'{"key":"private"}')
            self.assertEqual(path.stat().st_mode & 0o777, 0o640)
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), ['ssap-key.json'])


if __name__ == '__main__':
    unittest.main()
