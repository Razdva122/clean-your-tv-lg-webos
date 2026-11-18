from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from cytv.errors import LocalRecoveryError, UserError
from cytv.no_root_reconnect import reconnect
from cytv.state import Store, target


class NoRootReconnectTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.store = Store(self.directory.name)
        self.profile = target('tv.local', 'no-root')
        self.store.save(self.profile)
        self.original = self.store.device_path(self.profile)
        self.store.begin(self.profile, 'uninstall', stage='restart-required')
        (self.original / 'known_hosts').write_bytes(b'old pin')
        (self.original / 'developer-key.pem').write_bytes(b'old client key')
        self.before = self.contents(self.original)

    @staticmethod
    def contents(directory):
        return {p.name: p.read_bytes() for p in directory.iterdir() if p.is_file()
                and p.name != 'active-after-reset'}

    def test_success_preserves_original_records_and_selects_new_profile(self):
        def connect(stage, trust):
            self.assertTrue(trust('SHA256:new', False))
            (stage / 'known_hosts').write_bytes(b'new pin')
            (stage / 'developer-key.pem').write_bytes(b'new client key')
            return 'connected'

        result = reconnect(self.store, self.profile, connect, lambda *_: True, {'SHA256:old'})
        self.assertEqual(result, 'connected')
        self.assertEqual(self.contents(self.original), self.before)
        self.assertEqual(self.store.profiles(), [self.profile])
        self.assertIsNone(self.store.pending(self.profile))
        self.assertEqual((self.store.device_path(self.profile) / 'known_hosts').read_bytes(), b'new pin')

    def test_failure_and_cancel_preserve_active_profile(self):
        for error in (EOFError, OSError):
            with self.subTest(error=error):
                def connect(stage, trust):
                    (stage / 'known_hosts').write_bytes(b'uncommitted pin')
                    raise error()

                with self.assertRaises(error):
                    reconnect(self.store, self.profile, connect, lambda *_: True, {'SHA256:old'})
                self.assertEqual(self.store.device_path(self.profile), self.original)
                self.assertEqual(self.contents(self.original), self.before)
                self.assertFalse(list(self.original.glob('after-reset-*')))

    def test_invalid_active_selection_does_not_reopen_the_old_operation(self):
        (self.original / 'active-after-reset').write_text('after-reset-' + '1' * 32)
        with self.assertRaises(LocalRecoveryError):
            self.store.connection_profile(self.profile)
        self.assertEqual(self.contents(self.original), self.before)

    def test_same_key_cannot_discard_pending_uninstall(self):
        def connect(stage, trust):
            trust('SHA256:old', False)
            self.fail('Old host key accepted for a new connection')

        with self.assertRaises(UserError):
            reconnect(self.store, self.profile, connect, lambda *_: True, {'SHA256:old'})
        self.assertEqual(self.store.pending(self.profile)['stage'], 'restart-required')

    def test_installer_continues_to_install_confirmation_instead_of_old_removal(self):
        import paramiko

        from cytv.cli import main
        from cytv import i18n
        from cytv.transport import fingerprint

        self.addCleanup(i18n.set_language, i18n.language_choice())
        old_key = paramiko.RSAKey.generate(2048)
        new_key = paramiko.RSAKey.generate(2048)
        (self.original / 'known_hosts').write_text(
            f'[tv.local]:9922 {old_key.get_name()} {old_key.get_base64()}\n')
        before = self.contents(self.original)
        remote = Mock()
        prompts = []
        output = []
        args = ['install', '--host', self.profile['host'], '--edition', 'no-root',
                '--no-discovery', '--language', 'en', '--data-dir', str(self.store.root)]

        def ask(prompt):
            label = str(prompt)
            prompts.append(label)
            return 'n' if 'Install these versions?' in label else 'y'

        def connect(profile, directory, secret, trust):
            self.assertEqual(profile, self.profile)
            self.assertNotEqual(directory, self.original)
            self.assertTrue(trust(fingerprint(new_key), False))
            (directory / 'known_hosts').write_text(
                f'[tv.local]:9922 {new_key.get_name()} {new_key.get_base64()}\n')
            (directory / 'developer-key.pem').write_bytes(b'new client key')
            return remote

        with patch('cytv.package.verify_payload', return_value={}), \
                patch('cytv.diagnostic_context.collect_metadata'), \
                patch('cytv.cli.Installer') as installer, \
                patch('cytv.recovery.recover') as recover:
            changed_key = Mock(side_effect=paramiko.BadHostKeyException(self.profile['host'], new_key, old_key))
            self.assertEqual(main(args + ['--yes'], ask=ask, connect=changed_key, write=output.append), 1)
            changed_key.assert_called_once()
            self.assertEqual(changed_key.call_args.args[:2], (self.profile, self.original))
            self.assertEqual(changed_key.call_args.kwargs, {'persist': False})
            self.assertTrue(any('TV identity changed since the last trusted connection' in line for line in output))

            reset_args = args + ['--reconnect-after-reset']
            no_connection = Mock()
            self.assertEqual(main(reset_args, ask=lambda _: '', connect=no_connection, write=output.append), 130)
            no_connection.assert_not_called()
            self.assertEqual(self.store.device_path(self.profile), self.original)
            self.assertEqual(self.contents(self.original), before)

            code = main(reset_args, ask=ask, connect=connect, write=output.append)
        self.assertEqual(code, 0, prompts)
        self.assertTrue(any('Start a new No-root connection after a factory reset?' in p for p in prompts))
        self.assertTrue(any('Connect and remember this TV?' in p for p in prompts))
        self.assertTrue(any('Install these versions?' in p for p in prompts))
        recover.assert_not_called()
        installer.return_value.install.assert_not_called()
        remote.close.assert_called_once()
        self.assertEqual(self.contents(self.original), before)
        self.assertIsNone(self.store.pending(self.profile))
