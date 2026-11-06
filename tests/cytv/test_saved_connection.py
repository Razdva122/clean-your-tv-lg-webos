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
