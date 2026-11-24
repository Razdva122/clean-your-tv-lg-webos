import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from cytv import state
from cytv.beta_startup_migration import run
from cytv.errors import UserError


class StartupMigrationHostTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = state.Store(self.tmp.name)
        self.profile = state.target('192.0.2.20', 'root', root_variant='node012-beta')
        self.store.save(self.profile)
        (self.store.device_dir(self.profile)/'known_hosts').write_bytes(b'original pin')
        self.installer = Mock(store=self.store, profile=self.profile, tv_info={})
        self.installer.remote.run.side_effect = lambda command, **kwargs: ('ef53' if command == "LC_ALL=C stat -f -c '%t' /tmp" else '')
        self.write = Mock()
        self.reply = {'returnValue': True, 'phase': 'complete', 'application_preserved': True,
                      'preferences_preserved': True, 'home_changed': False}

    def test_decline_has_no_device_or_receipt_writes(self):
        self.assertIsNone(run(self.installer, lambda _: 'n', self.write))
        self.installer.remote.run.assert_not_called()
        self.installer.remote.upload.assert_not_called()
        self.assertIsNone(self.store.pending(self.profile))

    def test_preserved_unstarted_removal_is_archived_only_after_verified_success(self):
        pending = self.store.request_clean_removal(self.profile)
        original = (self.store.device_dir(self.profile)/'operation.json').read_bytes()
        source = {'bundle.json': b'{}', 'beta_startup_migration.py': b'script', 'runtime/c1-keyfilter-guard': b'guard', 'own.ipk': b'package'}
        with patch('cytv.root_gate.source_bundle', return_value=source), \
                patch('cytv.root_install_recovery.run', return_value=json.dumps(self.reply)) as device:
            self.assertEqual(run(self.installer, lambda _: 'y', self.write), self.reply)
        self.assertIsNone(self.store.pending(self.profile))
        archive = self.store.device_dir(self.profile)/('beta-startup-preserved-'+pending['removal_operation']+'.json')
        self.assertEqual(archive.read_bytes(), original)
        self.assertTrue(device.call_args.args[1].startswith('/tmp/cytv-c1-root-'))
        args = device.call_args.args[3]
        self.assertEqual(args[-3:], ['--preserve-removal', pending['product_operation'], pending['removal_operation']])
        self.installer.uninstall_project.assert_not_called()
        self.assertTrue(any(call.args[0].endswith('own.ipk') for call in self.installer.remote.upload.call_args_list))

    def test_failed_or_inconsistent_device_reply_keeps_original_request(self):
        pending = self.store.request_clean_removal(self.profile)
        for reply in (dict(self.reply, preferences_preserved=False), dict(self.reply, phase='writing')):
            with patch('cytv.root_gate.source_bundle', return_value={'beta_startup_migration.py': b'script'}), \
                    patch('cytv.root_install_recovery.run', return_value=json.dumps(reply)):
                with self.assertRaises(UserError):
                    run(self.installer, lambda _: 'y', self.write)
            self.assertEqual(self.store.pending(self.profile), pending)

    def test_ramfs_migration_retains_private_stage_and_original_request_on_lost_reply(self):
        from cytv.root_staging import ROOT
        pending = self.store.request_clean_removal(self.profile)
        def remote_run(command, **kwargs):
            if command == "LC_ALL=C stat -f -c '%t' /tmp":return '858458f6'
            if command == "LC_ALL=C stat -f -c '%t' /var/lib":return 'ef53'
            if command == 'LC_ALL=C df -Pk /var/lib':return 'Filesystem 1024-blocks Used Available Capacity Mounted on\n/dev/test 10000000 0 10000000 0% /shared'
            if 'CYTV_ROOT_STAGE_READY' in command:return 'CYTV_ROOT_STAGE_READY'
            return ''
        self.installer.remote.run.side_effect = remote_run
        with patch('cytv.root_gate.source_bundle', return_value={'beta_startup_migration.py': b'script'}), \
                patch('cytv.root_install_recovery.run', side_effect=OSError('lost reply')) as device, \
                patch('cytv.root_passive.collect_beta', return_value={}):
            with self.assertRaisesRegex(OSError, 'lost reply'):
                run(self.installer, lambda _: 'y', self.write)
        stage = device.call_args.args[1]
        self.assertTrue(stage.startswith(ROOT+'/cytv-c1-root-'))
        self.installer.remote.upload.assert_called_once_with(stage+'/beta_startup_migration.py', b'script', mode=0o600)
        self.assertEqual(self.store.pending(self.profile), pending)
        self.assertFalse(any(call.args[0].startswith('rm ') for call in self.installer.remote.run.call_args_list))

    def test_ramfs_migration_success_retires_exact_uploaded_inventory(self):
        from cytv import root_staging
        data = {'beta_startup_migration.py': b'script', 'runtime/c1-keyfilter-guard': b'guardian'}
        def remote_run(command, **kwargs):
            if command == "LC_ALL=C stat -f -c '%t' /tmp":return '858458f6'
            if command == "LC_ALL=C stat -f -c '%t' /var/lib":return 'ef53'
            if command == 'LC_ALL=C df -Pk /var/lib':return 'Filesystem 1024-blocks Used Available Capacity Mounted on\n/dev/test 10000000 0 10000000 0% /shared'
            if 'CYTV_ROOT_STAGE_READY' in command:return 'CYTV_ROOT_STAGE_READY'
            return ''
        self.installer.remote.run.side_effect = remote_run
        with patch('cytv.root_gate.source_bundle', return_value=data), \
                patch('cytv.root_install_recovery.run', return_value=json.dumps(self.reply)) as device, \
                patch('cytv.root_passive.collect_beta', return_value={}), \
                patch.object(root_staging, 'retire', wraps=root_staging.retire) as retire:
            self.assertEqual(run(self.installer, lambda _: 'y', self.write), self.reply)
        stage = device.call_args.args[1]
        self.assertTrue(stage.startswith(root_staging.ROOT+'/cytv-c1-root-'))
        retire.assert_called_once_with(self.installer.remote, stage, data)
        uploaded = {call.args[0][len(stage)+1:]: call.args[1] for call in self.installer.remote.upload.call_args_list}
        self.assertEqual(uploaded, data)
        nested = [call.args[0] for call in self.installer.remote.run.call_args_list if 'mkdir -p' in call.args[0]]
        self.assertTrue(nested)
        self.assertTrue(all(command.startswith('umask 077; mkdir -p ') for command in nested))

    def test_ramfs_migration_unsafe_staging_refuses_before_upload(self):
        pending = self.store.request_clean_removal(self.profile)
        def remote_run(command, **kwargs):
            if command == "LC_ALL=C stat -f -c '%t' /tmp":return '858458f6'
            if command == "LC_ALL=C stat -f -c '%t' /var/lib":return 'ef53'
            if command == 'LC_ALL=C df -Pk /var/lib':return 'Filesystem 1024-blocks Used Available Capacity Mounted on\n/dev/test 10000000 0 10000000 0% /shared'
            return ''
        self.installer.remote.run.side_effect = remote_run
        with patch('cytv.root_gate.source_bundle', return_value={'beta_startup_migration.py': b'script'}), \
                patch('cytv.root_install_recovery.run') as device:
            with self.assertRaises(UserError) as caught:
                run(self.installer, lambda _: 'y', self.write)
        self.assertEqual(caught.exception.reason_code, 'tv-storage-unavailable')
        self.installer.remote.upload.assert_not_called()
        device.assert_not_called()
        self.assertEqual(self.store.pending(self.profile), pending)

    def test_bundle_without_migration_script_is_refused_before_upload(self):
        with patch('cytv.root_gate.source_bundle', return_value={'bundle.json': b'{}'}):
            with self.assertRaisesRegex(UserError, 'Root runtime support is missing'):
                run(self.installer, lambda _: 'y', self.write)
        self.installer.remote.run.assert_not_called()
        self.installer.remote.upload.assert_not_called()

    def test_cli_normal_entry_dispatches_only_dedicated_migration(self):
        from cytv import cli
        from cytv.terminal import Console
        remote = Mock()
        with patch('cytv.cli.package.verify_payload', return_value={'files':{}}),                 patch('cytv.cli.Installer', return_value=self.installer),                 patch('cytv.beta_startup_migration.run', return_value=self.reply) as migrate:
            result = cli.main(['migrate-root-beta','--host',self.profile['host'],'--edition','root',
                               '--root-variant','node012-beta','--language','en','--data-dir',str(self.store.root)],
                              ask=lambda _: 'y', write=Console(lambda _:None), connect=lambda *args,**kwargs:remote,
                              payload_root=Path(self.tmp.name))
        self.assertEqual(result,0)
        migrate.assert_called_once()
        self.installer.uninstall_project.assert_not_called()
        self.installer.install_root.assert_not_called()

    def test_changed_removal_stage_refuses_before_prompt_or_ssh(self):
        self.store.request_clean_removal(self.profile)
        self.store.checkpoint(self.profile, stage='package-removal')
        with self.assertRaises(UserError):
            run(self.installer, lambda _: self.fail('prompt'), self.write)
        self.installer.remote.run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
