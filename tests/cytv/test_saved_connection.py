"""Pending work must reconnect with its saved identity before any network I/O."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from cytv import state


class SavedConnectionTests(unittest.TestCase):
    def test_ambiguous_original_operation_refuses_before_connection(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=state.Store(tmp);original=state.target('tv.local','root')
            for profile in (original,state.target('other.local','root')):
                store.save(profile);store.begin(profile,'install',product_operation='a'*32)
                (store.device_dir(profile)/'known_hosts').write_bytes(b'original pin')
            with self.assertRaisesRegex(RuntimeError,'original saved'):
                store.connection_profile(original)
    def test_partial_selector_never_assumes_the_readable_port_or_connection_type(self):
        from cytv import cli
        cases = [
            (state.target('tv.local', 'root', 2222),
             state.target('tv.local', 'root', 22), []),
            (state.target('tv.local', 'no-root', 9922, connection='root-ssh'),
             state.target('tv.local', 'no-root', 9922), ['--port', '9922']),
        ]
        for blocked, readable, port in cases:
            with self.subTest(blocked=blocked), tempfile.TemporaryDirectory() as tmp:
                store = state.Store(tmp)
                for profile in (blocked, readable):
                    store.save(profile)
                denied = store.device_dir(blocked) / 'profile.json'
                original = Path.read_text

                def read(path, *args, **kwargs):
                    if path == denied:
                        raise PermissionError('PRIVATE path')
                    return original(path, *args, **kwargs)

                io = self.forbidden_io()
                with patch.object(Path, 'read_text', read):
                    code = cli.main(['status', '--host', 'TV.LOCAL', '--edition', readable['edition'],
                                     *port, '--non-interactive', '--data-dir', tmp, '--language', 'en'],
                                    ask=io, search=io, inspect=io, connect=io, write=lambda _: None)
                self.assertEqual(code, 2)
                io.assert_not_called()

    def test_exact_or_confirmed_observation_keeps_saved_credentials_and_pin(self):
        from cytv import cli
        with tempfile.TemporaryDirectory() as tmp:
            store = state.Store(tmp)
            picked = state.target('tv.local', 'root', 2222, identity=Path(tmp) / 'saved-key')
            store.save(picked)
            directory = store.device_dir(picked)
            (directory / 'known_hosts').write_bytes(b'original pin')
            # Preserve exact bytes, including harmless formatting.
            (directory / 'profile.json').write_text(json.dumps(picked, indent=2))
            before = {path.name: path.read_bytes() for path in directory.iterdir()}
            other = state.target('tv.local', 'root', 22)
            store.save(other)
            denied = store.device_dir(other) / 'profile.json'
            original = Path.read_text

            def read(path, *args, **kwargs):
                if path == denied:
                    raise PermissionError('PRIVATE path')
                return original(path, *args, **kwargs)

            io = self.forbidden_io()
            host_answers, menu_answers = iter(('1',)), iter(('', '1'))
            choices = [
                (['--host', 'TV.LOCAL', '--edition', 'root', '--port', '2222', '--non-interactive'], io),
                (['--host', 'TV.LOCAL', '--edition', 'root'], lambda _: next(host_answers)),
                ([], lambda _: next(menu_answers)),
            ]
            remote = Mock()
            remote.luna.return_value = {'returnValue': True, 'modelName': 'OLED65C1PSA'}
            remote.run.return_value = 'CYTV_NODE_VERSION v8.12.0'
            for selector, ask in choices:
                with self.subTest(selector=selector):
                    connected = []
                    messages = []

                    def connect(profile, data, secret, trust, *, persist=True):
                        connected.append((profile, data, persist, trust('different fingerprint', True)))
                        return remote

                    with patch.object(Path, 'read_text', read), patch('cytv.cli.Installer') as installer:
                        code = cli.main(['status', *selector, '--data-dir', tmp, '--language', 'en'],
                                        ask=ask, connect=connect, search=io, inspect=io, write=messages.append)
                    self.assertEqual(code, 0, messages)
                    io.assert_not_called()
                    installer.assert_not_called()
                    self.assertEqual(connected, [(picked, directory, False, False)])
                    self.assertEqual({path.name: path.read_bytes() for path in directory.iterdir()
                                      if path.is_file()}, before)
                    if ask is not io:
                        self.assertIn('tv.local:2222', ' '.join(messages))

            store.begin(picked, 'install', product_operation='a' * 32)
            receipt = directory / 'operation.json'
            before['operation.json'] = receipt.read_bytes()
            identity_override = Path(tmp) / 'explicit-key'
            with patch.object(Path, 'read_text', read), patch('cytv.cli.Installer') as installer:
                for action in ('status', 'doctor'):
                    with self.subTest(action=action):
                        connected.clear()
                        code = cli.main([action, *choices[0][0], '--data-dir', tmp, '--language', 'en',
                                         '--identity', str(identity_override)],
                                        ask=io, connect=connect, search=io, inspect=io, write=messages.append)
                        self.assertEqual(code, 0)
                        self.assertEqual(connected, [(dict(picked, identity=str(identity_override.resolve())),
                                                      directory, False, False)])
                installer.assert_not_called()
                io.assert_not_called()
                code = cli.main(['recover', *choices[0][0], '--data-dir', tmp, '--language', 'en'],
                                ask=io, connect=io, search=io, inspect=io, write=lambda _: None)
                self.assertEqual(code, 2)
                io.assert_not_called()
            self.assertEqual({path.name: path.read_bytes() for path in directory.iterdir()
                              if path.is_file()}, before)
            reports = [json.loads(path.read_text()) for path in (Path(tmp) / 'reports').glob('*.json')]
            observed = [report for report in reports if report['phase'] == 'partial-tv-observation']
            self.assertEqual(len(observed), 5)
            for report in observed:
                self.assertEqual(report['checks'], {'ssh': 'pass'})
                self.assertEqual(report['tv']['modelName'], 'OLED65C1PSA')
                self.assertNotIn('recovery', report)
                self.assertNotIn('removal', report)
            self.assertEqual(sum(report['pending'] == {'action': 'install', 'stage': 'pending'}
                                 for report in observed), 2)
            self.assertIn('recovery details are unavailable', ' '.join(' '.join(messages).split()).lower())
            from cytv.graphics import URI
            self.assertEqual(remote.luna.call_count, 5)
            self.assertTrue(all(call.args == (URI, {'keys': ['modelName', 'firmwareVersion', 'sdkVersion']})
                                for call in remote.luna.call_args_list))
            self.assertEqual(remote.run.call_count, 5)
            self.assertTrue(all('/usr/bin/node --version' in call.args[0] for call in remote.run.call_args_list))
            remote.upload.assert_not_called()
            self.assertEqual(remote.close.call_count, 5)

    def test_partial_observation_failure_never_offers_recovery_or_updates_removal_receipt(self):
        from cytv import cli
        from cytv.desktop import DesktopConsole
        with tempfile.TemporaryDirectory() as tmp:
            store = state.Store(tmp)
            picked = state.target('tv.local', 'root')
            store.save(picked)
            store.request_clean_removal(picked)
            directory = store.device_dir(picked)
            (directory / 'known_hosts').write_bytes(b'original pin')
            before = {path: path.read_bytes() for path in directory.iterdir()}
            other = state.target('other.example', 'root')
            store.save(other)
            denied = store.device_dir(other) / 'profile.json'
            original = Path.read_text

            def read(path, *args, **kwargs):
                if path == denied:
                    raise PermissionError('PRIVATE path')
                return original(path, *args, **kwargs)

            io = self.forbidden_io()
            events = []
            with patch.object(Path, 'read_text', read):
                code = cli.main(['status', '--host', 'tv.local', '--edition', 'root', '--port', '22',
                                 '--data-dir', tmp, '--language', 'en'],
                                ask=io, search=io, inspect=io,
                                connect=Mock(side_effect=ConnectionError('lost connection')),
                                write=DesktopConsole(lambda *event: events.append(event)))
            self.assertEqual(code, 1)
            self.assertFalse(any(kind in ('recovery', 'recovery-plan') for kind, _ in events))
            self.assertEqual({path: path.read_bytes() for path in directory.iterdir()}, before)
            report_path, = (Path(tmp) / 'reports').glob('*.json')
            report = json.loads(report_path.read_text())
            self.assertEqual(report['phase'], 'ssh-connect')
            self.assertNotIn('removal', report)
            self.assertNotIn('recovery', report)

    def test_cli_exports_unobserved_status_and_recovery_without_rereading_denied_profile(self):
        from cytv import cli
        with tempfile.TemporaryDirectory() as tmp:
            store = state.Store(tmp)
            profile = state.target('private.tv.local', 'root', 2222, identity=Path(tmp) / 'private-key')
            store.save(profile)
            directory = store.device_dir(profile)
            (directory / 'known_hosts').write_bytes(b'original pin')
            store.begin(profile, 'activate-root', stage='enable')
            files = {path: path.read_bytes() for path in directory.iterdir()}
            original = Path.read_text
            reads = []

            def read(path, *args, **kwargs):
                if path in files:
                    reads.append(path.name)
                if path == directory / 'profile.json':
                    raise PermissionError('PRIVATE Windows path')
                return original(path, *args, **kwargs)

            io = self.forbidden_io()
            for action in ('status', 'recover'):
                with self.subTest(action=action), patch.object(Path, 'read_text', read), \
                        patch.object(state, 'platform', 'win32'), patch.object(state, 'sleep'):
                    reads.clear()
                    code = cli.main([action, '--host', 'private.tv.local', '--edition', 'root',
                                     '--port', '2222', '--data-dir', tmp, '--language', 'en'],
                                    ask=io, connect=io, search=io, inspect=io, write=lambda _: None)
                    self.assertEqual(code, 2)
                    self.assertEqual(reads, ['profile.json'] * 3)
            io.assert_not_called()
            self.assertEqual({path: path.read_bytes() for path in directory.iterdir()}, files)
            reports = list((Path(tmp) / 'reports').glob('*.json'))
            self.assertEqual(len(reports), 2)
            for report_path in reports:
                report = json.loads(report_path.read_text())
                self.assertEqual(report['phase'], 'select-tv')
                self.assertEqual(report['local_recovery'], {'reason': 'profile-access', 'location': 'profile'})
                self.assertNotIn('recovery', report)
                self.assertIsNone(report['pending'])
                self.assertIsNone(report['edition'])
                self.assertEqual(report['tv'], {})
                self.assertEqual(report['checks'], {})
                for private in ('PRIVATE', 'private.tv.local', 'private-key', tmp):
                    self.assertNotIn(private, report_path.read_text())

    def test_profiles_detect_root_enumeration_and_child_traversal_failures(self):
        import os
        from cytv.errors import LocalRecoveryError
        with tempfile.TemporaryDirectory() as tmp:
            store = state.Store(tmp)
            hidden = state.target('blocked.example', 'no-root')
            kept = state.target('visible.example', 'no-root')
            for profile in (hidden, kept):
                store.save(profile)
            with patch.object(Path, 'iterdir', side_effect=PermissionError('PRIVATE root')):
                with self.assertRaises(LocalRecoveryError) as failure:
                    store.profiles()
                self.assertEqual(failure.exception.local_recovery['reason'], 'profile-access')
            if os.name != 'nt' and os.geteuid() != 0:
                directory = store.device_dir(hidden)
                directory.chmod(0)
                try:
                    with self.assertRaises(LocalRecoveryError) as failure:
                        store.profiles()
                    self.assertEqual(failure.exception.local_recovery['reason'], 'profile-access')
                finally:
                    directory.chmod(0o700)

    def test_recover_never_adds_a_target_when_its_saved_directory_is_inaccessible(self):
        import os
        from cytv import cli
        if os.name == 'nt' or os.geteuid() == 0:
            self.skipTest('Requires POSIX directory permissions under an ordinary account')
        with tempfile.TemporaryDirectory() as tmp:
            store = state.Store(tmp)
            profile = state.target('tv.local', 'root', 2222)
            store.save(profile)
            directory = store.device_dir(profile)
            directory.chmod(0)
            io = self.forbidden_io()
            try:
                code = cli.main(['recover', '--host', 'tv.local', '--edition', 'root',
                                 '--port', '2222', '--data-dir', tmp, '--language', 'en'],
                                ask=io, connect=io, search=io, inspect=io, write=lambda _: None)
            finally:
                directory.chmod(0o700)
            self.assertEqual(code, 2)
            io.assert_not_called()

    def test_missing_and_disappearing_profiles_differ_from_invalid_profile_json(self):
        from cytv.errors import LocalRecoveryError
        with tempfile.TemporaryDirectory() as tmp:
            store = state.Store(tmp)
            missing = state.target('missing.example', 'root')
            store.device_dir(missing)
            saved = state.target('saved.example', 'root')
            store.save(saved)
            path = store.device_dir(saved) / 'profile.json'
            original = Path.read_text

            def disappear(candidate, *args, **kwargs):
                if candidate == path:
                    candidate.unlink()
                return original(candidate, *args, **kwargs)

            denied = self.forbidden_io()
            with patch.object(Path, 'read_text', disappear):
                self.assertEqual(store.profiles(on_access_denied=denied), [])
            denied.assert_not_called()

            path.write_text('{')
            with self.assertRaises(LocalRecoveryError) as failure:
                store.profiles(on_access_denied=denied)
            self.assertEqual(failure.exception.local_recovery['reason'], 'profile-invalid')
            denied.assert_not_called()

    def test_exact_status_can_probe_saved_profile_when_root_listing_is_denied(self):
        from cytv import cli
        with tempfile.TemporaryDirectory() as tmp:
            store = state.Store(tmp)
            picked = state.target('tv.local', 'root', 2222, identity=Path(tmp) / 'saved-key')
            store.save(picked)
            connected = []
            io = self.forbidden_io()

            def connect(profile, data, secret, trust, *, persist=True):
                connected.append((profile, persist))
                return Mock()

            with patch.object(Path, 'iterdir', side_effect=PermissionError('PRIVATE root')):
                code = cli.main(['status', '--host', 'tv.local', '--edition', 'root', '--port', '2222',
                                 '--data-dir', tmp, '--language', 'en', '--non-interactive'],
                                ask=io, search=io, inspect=io, connect=connect, write=lambda _:None)
            self.assertEqual(code, 0)
            self.assertEqual(connected, [(picked, False)])
            io.assert_not_called()

    def forbidden_io(self):
        return Mock(side_effect=AssertionError('unexpected prompt or device I/O'))

    def test_windows_sharing_violation_retries_the_same_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = state.Store(tmp)
            profile = state.target('tv.local', 'root')
            store.save(profile)
            for winerror in (None, 32, 33):
                with self.subTest(winerror=winerror):
                    error = PermissionError('sharing violation')
                    if winerror is not None:
                        error.winerror = winerror
                    with patch.object(state, 'platform', 'win32'), patch.object(state, 'sleep') as sleep, \
                            patch.object(Path, 'read_text', side_effect=[error, json.dumps(profile)]) as read:
                        self.assertEqual(store.profiles(), [profile])
                        self.assertEqual(read.call_count, 2)
                        sleep.assert_called_once_with(0.05)
            with patch.object(state, 'platform', 'win32'), patch.object(state, 'sleep'), \
                    patch.object(Path, 'read_text', side_effect=PermissionError('denied')) as read:
                with self.assertRaisesRegex(RuntimeError, 'saved TV connections'):
                    store.profiles()
                self.assertEqual(read.call_count, 3)

    def test_cli_recovery_uses_original_profile_without_metadata_or_persistence(self):
        from cytv import cli
        with tempfile.TemporaryDirectory() as tmp:
            store=state.Store(tmp);original=state.target('tv.local','root',identity='/original/key')
            store.save(original);store.begin(original,'install',stage='coordinator-submitted',product_operation='a'*32)
            (store.device_dir(original)/'known_hosts').write_bytes(b'original pin')
            before={p.name:p.read_bytes() for p in store.device_dir(original).iterdir()}
            remote=Mock();calls=[]
            def connect(profile,directory,secret,trust,**kwargs):
                calls.append((profile,kwargs));self.assertFalse(trust('replacement',True));return remote
            result=cli.main(['recover','--host','tv.local','--edition','root','--identity','/replacement/key','--data-dir',tmp,'--language','en'],
                            ask=lambda _: 'n',write=lambda *_:None,connect=connect)
            self.assertEqual(result,0)
            self.assertEqual(calls,[(original,{'persist':False})])
            self.assertEqual({name:(store.device_dir(original)/name).read_bytes() for name in before},before)
            remote.luna.assert_not_called();remote.run.assert_not_called();remote.upload.assert_not_called()

    def test_pending_identity_is_original_and_invalid_records_refuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = state.Store(tmp)
            original = state.target('tv.local', 'root', identity='/original/key')
            selected = state.target('tv.local', 'root', identity='/replacement/key')
            store.save(original); store.begin(original, 'install')
            directory = store.device_dir(original)
            (directory/'known_hosts').write_bytes(b'original pin')
            self.assertEqual(store.connection_profile(selected), (original, True))
            for data in (b'{', b'{}', json.dumps(state.target('foreign.local', 'root')).encode()):
                (directory/'profile.json').write_bytes(data)
                with self.assertRaisesRegex(RuntimeError, 'original saved'):
                    store.connection_profile(selected)
            (directory/'profile.json').unlink()
            with self.assertRaisesRegex(RuntimeError, 'original saved'):
                store.connection_profile(selected)

    def test_no_root_nonpersistent_never_fetches_or_replaces_developer_key(self):
        import paramiko
        from cytv.transport import SSH
        with tempfile.TemporaryDirectory() as tmp:
            profile=state.target('tv.local', 'no-root')
            key=paramiko.RSAKey.generate(1024)
            known=paramiko.HostKeys(); known.add('[tv.local]:9922',key.get_name(),key)
            known.save(str(Path(tmp)/'known_hosts'))
            before=(Path(tmp)/'known_hosts').read_bytes()
            with patch('cytv.transport.developer_key') as fetch, patch('paramiko.SSHClient') as client:
                with self.assertRaisesRegex(RuntimeError,'saved Developer Mode key'):
                    SSH.connect(profile,tmp,lambda _: 'secret',lambda *_:True,persist=False)
                fetch.assert_not_called(); client.return_value.connect.assert_not_called()
                key.write_private_key_file(str(Path(tmp)/'developer-key.pem'))
                SSH.connect(profile,tmp,lambda _: self.fail('secret requested'),lambda *_:self.fail('trust requested'),persist=False)
                client.return_value.connect.assert_called_once()
            self.assertEqual((Path(tmp)/'known_hosts').read_bytes(),before)
