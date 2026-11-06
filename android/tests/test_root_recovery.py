"""Android recovery uses original app-private records, never a desktop profile."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from cytv import i18n, state

SOURCE = Path(__file__).resolve().parents[1] / 'app/src/main/python/android_bridge.py'


class AndroidRootRecoveryTests(unittest.TestCase):
    def test_failed_passive_authentication_exports_current_blocker_without_replacing_first_failure(self):
        from paramiko import AuthenticationException
        from cytv import diagnostics
        from cytv.errors import TVCommandError
        diagnostics.create_report(self.store, 'install', self.profile, 'install-root', TVCommandError(127))
        before = self.records()
        with patch.object(self.bridge.SSH, 'connect', side_effect=AuthenticationException('PRIVATE')):
            self.assertEqual(self.run_bridge(), 2)
        report = next(json.loads(p.read_text()) for p in (self.store.root / 'reports').glob('*.json')
                      if json.loads(p.read_text())['action'] == 'recover')
        self.assertEqual(report['observation_failure']['guidance']['code'], 'ssh-auth-root')
        self.assertEqual(report['first_failure']['ssh_command']['exit_status'], 127)
        self.assertEqual(self.records(), before)
        help_event = next(e for e in self.native.events if e['kind'] == 'failure-help')
        self.assertEqual(help_event['code'], 'ssh-auth-root')
        self.assertFalse(help_event['canEditConnection'])
        self.assertNotIn('PRIVATE', json.dumps(self.native.events))

    def setUp(self):
        self.addCleanup(i18n.set_language, 'en')
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        spec = importlib.util.spec_from_file_location('android_recovery_bridge', SOURCE)
        self.bridge = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.bridge)
        self.store = state.Store(self.root / 'profiles')
        self.key = self.root / 'original-imported-key'; self.key.write_bytes(b'PRIVATE KEY')
        self.profile = state.target('192.0.2.10', 'root', identity=self.key)
        self.store.save(self.profile)
        self.directory = self.store.device_dir(self.profile)
        (self.directory / 'known_hosts').write_bytes(b'original pin is never replaced')
        self.operation = 'a' * 32
        self.store.begin(self.profile, 'install', stage='coordinator-submitted',
                         product_operation=self.operation)
        self.config = {'host': '192.0.2.10', 'port': 22, 'edition': 'root',
                       'action': 'recover', 'language': 'en', 'useImportedKey': False}
        class Native:
            answer = 'y'
            def __init__(self): self.events = []
            def emit(self, raw): self.events.append(json.loads(raw))
            def request(self, raw):
                self.events.append(json.loads(raw)); return self.answer
        self.native = Native()

    def records(self):
        return {p: p.read_bytes() for p in [self.key, self.directory / 'profile.json',
                self.directory / 'known_hosts', self.directory / 'operation.json'] if p.exists()}

    def run_bridge(self):
        return self.bridge.run(json.dumps(self.config), str(self.store.root), '/unused-payload',
                               '/replacement-ui-key', self.native)

    def test_reopened_android_recovery_reads_original_operation_without_profile_or_trust_writes(self):
        before = self.records()
        remote = Mock()
        def read(command, *, data, timeout):
            self.assertEqual(command, 'env -u NODE_OPTIONS -u NODE_PATH /usr/bin/node')
            self.assertIn(self.operation.encode(), data)
            return json.dumps({'schema': 1, 'status': 'read', 'operation': 'consistent-not-admission',
                               'worker': 'exception-recorded', 'python': 'system-default-unverified'})
        remote.run.side_effect = read
        with patch.object(self.bridge.cli, 'main', side_effect=AssertionError('ordinary recovery used')), \
             patch.object(self.bridge.SSH, 'connect', return_value=remote) as connect:
            self.assertEqual(self.run_bridge(), 2)  # Inspection never claims a recovered installation.
        self.assertEqual(connect.call_count, 1)
        self.assertEqual(connect.call_args.args[0], self.profile)
        self.assertFalse(connect.call_args.kwargs['persist'])
        self.assertFalse(connect.call_args.args[3]('new host pin', True))
        self.assertEqual(self.records(), before)
        remote.run.assert_called_once(); remote.close.assert_called_once()
        remote.luna.assert_not_called(); remote.upload.assert_not_called()
        reports = list((self.store.root / 'reports').glob('diagnostic-*.json'))
        self.assertEqual(len(reports), 1)
        report = json.loads(reports[0].read_text())
        self.assertEqual(report['status']['product']['passive']['worker'], 'exception-recorded')
        self.assertEqual(report['status']['product']['state'], 'recovery_required')
        self.assertFalse(report['status']['can_resume_root_setup'])
        self.assertEqual(report['recovery']['reason'], 'observation-unverified')
        for private in ('192.0.2.10', self.operation, str(self.key), 'PRIVATE KEY'):
            self.assertNotIn(private, reports[0].read_text())
        self.assertTrue(any(e['kind'] == 'report-ready' for e in self.native.events))
        question = next(e for e in self.native.events if e['kind'] == 'question')
        self.assertTrue(question['defaultNo'])

    def test_declining_inspection_does_not_connect_or_change_original_records(self):
        self.native.answer = 'n'; before = self.records()
        with patch.object(self.bridge.cli, 'main', side_effect=AssertionError('ordinary recovery used')), \
             patch.object(self.bridge.SSH, 'connect') as connect:
            self.assertIn(self.run_bridge(), (0, 130))
        connect.assert_not_called(); self.assertEqual(self.records(), before)

    def test_passive_authentication_keeps_key_and_root_types_in_every_locale(self):
        from cytv.transport import load_identity, root_auth
        before = self.records()
        def request(raw):
            event = json.loads(raw); self.native.events.append(event)
            return 'PRIVATE-TEST-SECRET' if event['kind'] == 'secret' else 'y'
        self.native.request = request
        remote = Mock()
        remote.run.return_value = json.dumps({'schema': 1, 'status': 'missing'})
        def authenticate(profile, directory, secret, trust, *, persist):
            self.assertEqual(profile, self.profile)
            self.assertFalse(persist)
            self.assertFalse(trust('untrusted', True))
            def typed_secret(prompt):
                self.assertIsInstance(prompt, str)
                self.assertIn(prompt.credential_type, ('key', 'root'))
                return secret(prompt)
            with patch('paramiko.PKey.from_path', side_effect=[ValueError('encrypted'), 'key']):
                load_identity(self.key, typed_secret)
            source = next(root_auth(typed_secret, automatic=False).get_sources())
            source.password_getter()
            return remote
        for language in set(i18n.LANGUAGES) - {'auto'}:
            with self.subTest(language=language):
                self.config['language'] = language; self.native.events.clear()
                with patch.object(self.bridge.SSH, 'connect', side_effect=authenticate):
                    self.assertEqual(self.run_bridge(), 2)
                events = [e for e in self.native.events if e['kind'] == 'secret']
                self.assertEqual([e['secretType'] for e in events], ['key', 'root'])
                self.assertEqual(self.records(), before)
                self.assertNotIn('PRIVATE-TEST-SECRET', json.dumps(self.native.events))
                for path in self.root.rglob('*'):
                    if path.is_file():
                        self.assertNotIn(b'PRIVATE-TEST-SECRET', path.read_bytes())

    def test_missing_original_profile_or_operation_stops_before_network(self):
        for missing in ('profile.json', 'operation.json'):
            with self.subTest(missing=missing):
                path = self.directory / missing; original = path.read_bytes(); path.unlink()
                with patch.object(self.bridge.cli, 'main', return_value=0) as cli, \
                     patch.object(self.bridge.SSH, 'connect') as connect:
                    self.assertEqual(self.run_bridge(), 2)
                cli.assert_not_called(); connect.assert_not_called()
                self.assertTrue(any(e['kind'] == 'error' and 'Original Android recovery records' in e['text']
                                    for e in self.native.events))
                self.assertFalse(path.exists()); path.write_bytes(original)

    def test_missing_pin_invalid_uuid_or_duplicate_original_operation_never_connects(self):
        known = self.directory / 'known_hosts'; pin = known.read_bytes()
        for kind in ('pin', 'uuid', 'duplicate'):
            with self.subTest(kind=kind):
                if kind == 'pin': known.unlink()
                if kind == 'uuid': self.store.checkpoint(self.profile, product_operation='not-a-uuid')
                if kind == 'duplicate':
                    other = state.target('192.0.2.11', 'root')
                    self.store.save(other)
                    self.store.begin(other, 'install', stage='coordinator-submitted', product_operation=self.operation)
                with patch.object(self.bridge.cli, 'main', side_effect=AssertionError('ordinary recovery used')),                      patch.object(self.bridge.SSH, 'connect') as connect:
                    self.assertEqual(self.run_bridge(), 2)
                connect.assert_not_called()
                if kind == 'pin': known.write_bytes(pin)
                if kind == 'uuid': self.store.checkpoint(self.profile, product_operation=self.operation)

    def test_profile_changed_while_waiting_for_lock_is_refused_before_connecting(self):
        from contextlib import contextmanager
        original_lock = state.Store.lock
        before_pending = (self.directory / 'operation.json').read_bytes()
        @contextmanager
        def changed(store, profile):
            with original_lock(store, profile):
                replacement = dict(self.profile, identity=str(self.root / 'changed-key'))
                state.private_write(self.directory / 'profile.json', json.dumps(replacement).encode())
                yield
        with patch.object(state.Store, 'lock', changed),              patch.object(self.bridge.SSH, 'connect') as connect:
            self.assertEqual(self.run_bridge(), 2)
        connect.assert_not_called()
        self.assertEqual((self.directory / 'operation.json').read_bytes(), before_pending)

    def test_inspection_confirmation_is_localized_and_defaults_to_no(self):
        for language in set(i18n.LANGUAGES) - {'en', 'auto'}:
            with self.subTest(language=language):
                self.config['language'] = language; self.native.answer = 'n'; self.native.events.clear()
                with patch.object(self.bridge.SSH, 'connect') as connect:
                    self.assertEqual(self.run_bridge(), 130)
                connect.assert_not_called()
                question = next(e for e in self.native.events if e['kind'] == 'question')
                self.assertTrue(question['defaultNo'])
                self.assertNotIn('Check recovery options?', question['text'])
                self.assertNotIn('Read the original Root installation state only.', question['context'])

    def test_corrupt_or_unknown_pending_never_falls_back_to_an_ordinary_connection(self):
        path = self.directory / 'operation.json'
        for value in (b'{', b'{"action":"foreign","stage":"pending"}'):
            with self.subTest(value=value):
                path.write_bytes(value)
                with patch.object(self.bridge.cli, 'main', return_value=0) as cli,                      patch.object(self.bridge.SSH, 'connect') as connect:
                    self.assertEqual(self.run_bridge(), 2)
                cli.assert_not_called(); connect.assert_not_called()
                self.assertEqual(path.read_bytes(), value)

    def test_authentication_cancellation_keeps_pin_identity_and_operation_without_retry(self):
        from cytv.transport import root_auth
        before = self.records()
        def request(raw):
            event = json.loads(raw); self.native.events.append(event)
            return None if event['kind'] == 'secret' else 'y'
        self.native.request = request
        def authenticate(profile, directory, secret, trust, *, persist):
            source = next(root_auth(secret, automatic=False).get_sources())
            source.password_getter()
        with patch.object(self.bridge.cli, 'main', side_effect=AssertionError('ordinary recovery used')), \
             patch.object(self.bridge.SSH, 'connect', side_effect=authenticate) as connect:
            self.assertEqual(self.run_bridge(), 130)
        self.assertEqual(connect.call_count, 1); self.assertEqual(self.records(), before)
        events = [e for e in self.native.events if e['kind'] == 'secret']
        self.assertEqual([e['secretType'] for e in events], ['root'])


if __name__ == '__main__': unittest.main()
