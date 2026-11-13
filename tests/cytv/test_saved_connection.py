"""Pending work must reconnect with its saved identity before any network I/O."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
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
    def test_cli_can_select_readable_profile_when_another_file_is_denied(self):
        from cytv import cli
        from cytv.terminal import Console
        with tempfile.TemporaryDirectory() as tmp:
            store = state.Store(tmp)
            good = state.target('tv.local', 'root')
            bad = state.target('other.local', 'root')
            for profile in (good, bad):
                store.save(profile)
            denied = store.device_dir(bad) / 'profile.json'
            original = Path.read_text

            def read(path, *args, **kwargs):
                if path == denied:
                    raise PermissionError('PRIVATE Windows path')
                return original(path, *args, **kwargs)

            args = cli.parser().parse_args(['status'])
            messages = []
            with patch.object(Path, 'read_text', read):
                chosen = cli.choose_profile(args, store, lambda _: '1', Console(messages.append),
                                            lambda: self.fail('unexpected discovery'), None)
                self.assertEqual(chosen, good)
                explicit = cli.parser().parse_args(['status', '--host', 'TV.LOCAL', '--edition', 'root'])
                self.assertEqual(cli.choose_profile(explicit, store, lambda _: self.fail('unexpected prompt'),
                                                    Console(messages.append), None, None), good)
                with self.assertRaisesRegex(RuntimeError, 'saved TV connections'):
                    cli.choose_profile(cli.parser().parse_args(['status', '--host', 'other.local', '--edition', 'root']),
                                       store, lambda _: self.fail('unexpected prompt'), Console(messages.append),
                                       lambda: self.fail('unexpected discovery'), None)
                store.begin(good, 'install')
                (store.device_dir(good) / 'known_hosts').write_bytes(b'original pin')
                with self.assertRaisesRegex(RuntimeError, 'saved TV connections'):
                    store.connection_profile(good)
            self.assertNotIn('PRIVATE', ' '.join(messages))

    def test_cli_status_reports_local_access_failure_before_connecting(self):
        from cytv import cli
        with tempfile.TemporaryDirectory() as tmp:
            store = state.Store(tmp)
            store.save(state.target('tv.local', 'root'))
            original = Path.read_text

            def read(path, *args, **kwargs):
                if path.name == 'profile.json':
                    raise PermissionError('PRIVATE Windows path')
                return original(path, *args, **kwargs)

            with patch.object(Path, 'read_text', read):
                code = cli.main(['status', '--data-dir', tmp, '--language', 'en'],
                                ask=lambda _: self.fail('unexpected prompt'), write=lambda _: None,
                                connect=lambda *_: self.fail('unexpected connection'))
            self.assertEqual(code, 2)
            report_path, = (Path(tmp) / 'reports').glob('*.json')
            report = json.loads(report_path.read_text())
            self.assertEqual(report['phase'], 'select-tv')
            self.assertEqual(report.get('local_recovery'), {'reason': 'profile-access', 'location': 'profile'})
            self.assertNotIn('PRIVATE', report_path.read_text())

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
        from unittest.mock import Mock
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
