"""Private state and package boundaries: no network or TV required."""
import errno
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

from cytv import package, state


class StateTests(unittest.TestCase):
    def test_windows_busy_lock_does_not_read_the_locked_byte(self):
        from unittest.mock import patch, MagicMock
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp:
            store=state.Store(tmp)
            profile=state.target('192.0.2.10','root')
            stream=MagicMock()
            stream.__enter__.return_value=stream
            stream.read.side_effect=PermissionError('Windows denies reads of locked byte')
            locking=MagicMock(side_effect=PermissionError(errno.EACCES, 'already locked'))
            module=SimpleNamespace(locking=locking,LK_NBLCK=1,LK_UNLCK=0)
            with patch.object(state.os,'name','nt'), patch.dict('sys.modules',msvcrt=module), \
                 patch.object(Path,'open',return_value=stream), \
                 patch.object(state.os,'fstat',return_value=SimpleNamespace(st_size=1)):
                with self.assertRaisesRegex(state.UserError,'Another cytv session'):
                    with store.lock(profile):self.fail('busy lock entered')
            stream.read.assert_not_called()

    def test_windows_lock_file_write_error_is_not_a_busy_tv(self):
        from types import SimpleNamespace
        from unittest.mock import MagicMock, patch
        with tempfile.TemporaryDirectory() as tmp:
            store = state.Store(tmp)
            profile = state.target('tv.local', 'no-root')
            stream = MagicMock()
            stream.__enter__.return_value = stream
            stream.write.side_effect = PermissionError(errno.EACCES, 'read-only local storage')
            with patch.object(state.os, 'name', 'nt'), patch.dict('sys.modules', msvcrt=MagicMock()), \
                    patch.object(Path, 'open', return_value=stream), \
                    patch.object(state.os, 'fstat', return_value=SimpleNamespace(st_size=0)):
                with self.assertRaises(state.LocalRecoveryError) as caught:
                    with store.lock(profile, allow_observation=True):
                        self.fail('local write failure entered observation')
                self.assertTrue(caught.exception.write_precheck)

    def test_same_tv_cannot_run_root_and_no_root_sessions_at_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = state.Store(tmp)
            a = state.target('tv.local', 'root')
            b = state.target('tv.local', 'no-root')
            with store.lock(a):
                with self.assertRaisesRegex(RuntimeError, 'Another'):
                    with store.lock(b):
                        self.fail('Both editions obtained the TV lock')

    def test_corrupt_receipt_remains_inspectable_without_unlocking_mutations(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = state.Store(tmp)
            profile = state.target('tv.local', 'root')
            (store.device_dir(profile) / 'operation.json').write_text('{')
            self.assertEqual(store.pending(profile)['action'], 'unknown')
            with self.assertRaises(RuntimeError):
                store.begin(profile, 'install')

    def test_target_validation_and_device_isolation(self):
        for host in ('-oProxyCommand=bad', 'tv;reboot', '../tv', 'http://tv', '999.1.1.1'):
            with self.subTest(host=host), self.assertRaises(ValueError):
                state.target(host, 'root', 22)
        with tempfile.TemporaryDirectory() as tmp:
            store = state.Store(Path(tmp))
            a = state.target('192.0.2.10', 'root', 22)
            b = state.target('192.0.2.10', 'no-root', 9922)
            store.save(a)
            store.save(b)
            self.assertNotEqual(store.device_dir(a), store.device_dir(b))
            self.assertEqual(store.profiles(), [a, b])

    def test_uncertain_mutation_blocks_retry_and_keeps_recovery_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = state.Store(Path(tmp))
            tv = state.target('tv.local', 'root', 22)
            store.begin(tv, 'install')
            with self.assertRaisesRegex(RuntimeError, 'status'):
                store.begin(tv, 'install')
            self.assertEqual(store.pending(tv)['action'], 'install')
            store.finish(tv)
            self.assertIsNone(store.pending(tv))
            store.begin(tv, 'uninstall')


class PackageTests(unittest.TestCase):
    def test_gzip_metadata_is_canonical_across_build_hosts(self):
        files = {'z.txt': b'last', 'a.txt': b'first'}
        packed = package.tgz(files)
        self.assertEqual(packed, package.tgz(dict(reversed(list(files.items())))))
        parts = package.read_ar(package.ipk('app', '1.0.0', files))
        control = {'control': b'Package: app\nVersion: 1.0.0\nArchitecture: all\nMaintainer: Clean Your TV\nDescription: Clean Your TV\n'}
        for compressed, expected in ((packed, files), (parts['control.tar.gz'], control), (parts['data.tar.gz'], files)):
            # Deflate, no filename/flags, epoch mtime, level 9, unknown OS.
            self.assertEqual(compressed[:10], b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x02\xff')
            with tarfile.open(fileobj=io.BytesIO(gzip.decompress(compressed)), mode='r:') as archive:
                self.assertEqual({item.name: archive.extractfile(item).read() for item in archive}, expected)

    def test_personalized_ipks_have_modern_reproducible_tar_dates(self):
        for app in ('com.gathin.tvhome', package.ROOT_APP):
            with self.subTest(app=app):
                raw = package.ipk(app, '1.0.0', {'usr/palm/applications/'+app+'/index.html': b'home'})
                inventory = {'apps': [{'id': 'youtube'}]}
                first, _ = package.personalize(raw, app, inventory)
                second, _ = package.personalize(raw, app, inventory)
                self.assertEqual(first, second)
                for name in ('control.tar.gz', 'data.tar.gz'):
                    with tarfile.open(fileobj=io.BytesIO(package.read_ar(first)[name]), mode='r:gz') as archive:
                        for member in archive:
                            self.assertGreaterEqual(member.mtime, 1577836800, member.name)
                            self.assertLessEqual(member.mtime, 1767225600, member.name)

    def test_ipk_has_executable_and_writable_helper_state(self):
        data = package.ipk('com.local.nativehome', '0.6.13', {
            'usr/palm/applications/com.local.nativehome/relay': b'ELF',
            'usr/palm/applications/com.local.nativehome/state/.keep': b'',
            'usr/palm/services/com.local.nativehome.service/state/.keep': b'',
        }, executable={'usr/palm/applications/com.local.nativehome/relay'}, helper_state=True)
        parts = package.read_ar(data)
        with tarfile.open(fileobj=io.BytesIO(parts['data.tar.gz']), mode='r:gz') as archive:
            self.assertEqual(archive.getmember('usr/palm/applications/com.local.nativehome/relay').mode, 0o755)
            for name in ('applications/com.local.nativehome', 'services/com.local.nativehome.service'):
                member = archive.getmember('usr/palm/' + name + '/state')
                self.assertEqual((member.uid, member.gid, member.mode), (5999, 5000, 0o770))

    def test_personalization_rehashes_root_payload_and_keeps_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app = 'com.cleanyourtv.root.preview'
            name = app + '_0.0.1_all.ipk'
            (root / name).write_bytes(package.ipk(app, '0.0.1', {
                'usr/palm/applications/' + app + '/apps.js': b'old',
                'usr/palm/applications/' + app + '/config.js': b'config',
            }))
            (root / 'deploy.py').write_bytes(b'unchanged recovery')
            (root / 'release.json').write_text(json.dumps({'application_id': app, 'version': '0.0.1', 'files': {}}))
            (root / 'SHA256SUMS').write_text('old')
            names = [name, 'deploy.py', 'release.json', 'SHA256SUMS']
            (root / 'bundle.json').write_text(json.dumps({'package': name, 'files': {
                n: hashlib.sha256((root / n).read_bytes()).hexdigest() for n in names}}))
            inventory = {'apps': [{'id': 'youtube.leanback.v4', 'title': 'YouTube', 'icon': 'data:image/png;base64,AA=='}], 'inputs': []}
            package.personalize_root(root, inventory)
            self.assertEqual((root / 'deploy.py').read_bytes(), b'unchanged recovery')
            parts = package.read_ar((root / name).read_bytes())
            with tarfile.open(fileobj=io.BytesIO(parts['data.tar.gz']), mode='r:gz') as archive:
                content = archive.extractfile('usr/palm/applications/' + app + '/apps.js').read()
                self.assertIn(b'youtube.leanback.v4', content)
                self.assertEqual(json.loads((root / 'release.json').read_text())['files']['usr/palm/applications/' + app + '/apps.js'], hashlib.sha256(content).hexdigest())
            for n, digest in json.loads((root / 'bundle.json').read_text())['files'].items():
                self.assertEqual(hashlib.sha256((root / n).read_bytes()).hexdigest(), digest)

    def test_rejects_paths_and_tampered_payload(self):
        with self.assertRaises(ValueError):
            package.ipk('app', '1.0.0', {'../escape': b'bad'})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'helper.ipk').write_bytes(b'changed')
            (root / 'payload.json').write_text(json.dumps({'files': {'helper.ipk': '0' * 64}}))
            with self.assertRaisesRegex(ValueError, 'integrity'):
                package.verify_payload(root)


if __name__ == '__main__':
    unittest.main()
