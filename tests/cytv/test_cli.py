import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cytv import cli, state


class CLITests(unittest.TestCase):
    def test_root_node_failure_can_complete_no_root_using_the_same_ssh(self):
        from tests.cytv.test_operations import OperationTests, Remote
        from cytv import no_root_observer
        import shlex
        fixture=OperationTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.root_bundle()
        (fixture.payload/'fallback.png').write_bytes(b'fallback')
        class LegacyTV(Remote):
            root=True
            def close(self): pass
            def run(self, command, data=None, timeout=30):
                if command == '/usr/bin/node --version':return 'v0.12.2'
                if 'CYTV_FRESH_ROOT' in command:return 'CYTV_FRESH_ROOT'
                if 'process.versions.node.split' in command and 'CYTV_ROOT_READY' in command:return 'CYTV_ROOT_MISSING'
                words=shlex.split(command)
                if '-e' in words and no_root_observer.ROOT_PROGRAM in words[words.index('-e')+1]:
                    index=words.index('-e')+1
                    words[index]=words[index].replace(no_root_observer.ROOT_PROGRAM,no_root_observer.PROGRAM)
                    command=shlex.join(words)
                return super().run(command,data,timeout)
        remote=LegacyTV()
        output=[]
        with patch('cytv.cli.package.verify_payload',return_value=fixture.manifest), patch('cytv.tv.SSAP') as ssap:
            ssap.return_value.__enter__.return_value.inventory.return_value=fixture.inventory
            ssap.return_value.__enter__.return_value.key='PRIVATE-PAIRING'
            code=cli.main(['install','--host','192.0.2.10','--edition','root','--yes','--language','en',
                           '--data-dir',str(fixture.root/'cli-state')],
                          connect=lambda *_:remote, ask=lambda prompt:'1' if 'Alternative edition' in prompt else '',
                          write=output.append, payload_root=fixture.payload)
        self.assertEqual(code,0,'\n'.join(output))
        profiles=state.Store(fixture.root/'cli-state').profiles()
        selected=next(p for p in profiles if p['edition']=='no-root')
        self.assertEqual(selected['connection'],'root-ssh')
        self.assertEqual(selected['port'],22)
        self.assertNotIn('PRIVATE-PAIRING','\n'.join(output))
        submitted=[call[2]['id'] for call in remote.calls if call[0]=='luna' and call[1].endswith('/dev/install')]
        self.assertEqual(submitted,['com.local.nativehome','com.gathin.tvhome'])

    def test_unknown_graphics_stops_no_root_before_pairing(self):
        from unittest.mock import MagicMock
        from cytv.errors import UserError
        with tempfile.TemporaryDirectory() as tmp, patch('cytv.cli.Installer') as cls, patch('cytv.cli.package.verify_payload', return_value={}), patch('cytv.tv.SSAP') as ssap:
            cls.return_value.select_graphics.side_effect = UserError('TV graphics capability could not be verified')
            code, output, _ = self.run_cli(['install', '--host', '192.0.2.10', '--edition', 'no-root', '--data-dir', tmp, '--yes'], remote=MagicMock())
            self.assertEqual(code, 2, output)
            ssap.assert_not_called()
            cls.return_value.install.assert_not_called()

    def test_unknown_graphics_stops_root_before_runtime_provisioning(self):
        from unittest.mock import MagicMock
        from cytv.errors import UserError
        with tempfile.TemporaryDirectory() as tmp, patch('cytv.cli.Installer') as cls, patch('cytv.cli.package.verify_payload', return_value={}):
            cls.return_value.select_graphics.side_effect = UserError('TV graphics capability could not be verified')
            code, output, _ = self.run_cli(['install', '--host', '192.0.2.10', '--edition', 'root', '--data-dir', tmp, '--yes'], remote=MagicMock())
            self.assertEqual(code, 2, output)
            cls.return_value.preflight.assert_not_called()
            cls.return_value.install.assert_not_called()

    def test_system_updater_replacement_preserves_root_and_rejects_pending_work(self):
        from unittest.mock import MagicMock
        for pending in [None]:
            with tempfile.TemporaryDirectory() as tmp, patch('cytv.cli.Installer') as installer, patch('cytv.cli.package.verify_payload', return_value={}):
                if pending: state.Store(tmp).begin(state.target('192.0.2.10', 'root'), pending)
                code, output, _ = self.run_cli(['replace-system-updater', '--host', '192.0.2.10', '--edition', 'root', '--data-dir', tmp, '--yes'], remote=MagicMock())
                self.assertEqual(code, 0, output)
                installer.return_value.replace_system_updater.assert_called_once_with()
                installer.return_value.install.assert_not_called(); installer.return_value.uninstall.assert_not_called()
        for edition, pending in [('no-root', None), ('root', 'install'), ('root', 'replace-system-updater')]:
            with tempfile.TemporaryDirectory() as tmp, patch('cytv.cli.Installer') as installer:
                if pending: state.Store(tmp).begin(state.target('192.0.2.10', edition), pending)
                code, _, calls = self.run_cli(['replace-system-updater', '--host', '192.0.2.10', '--edition', edition, '--data-dir', tmp, '--yes'])
                self.assertEqual(code, 2); self.assertFalse(calls); installer.assert_not_called()

    def test_system_updater_replacement_confirmation_defaults_to_no(self):
        with tempfile.TemporaryDirectory() as tmp, patch('cytv.cli.Installer') as installer:
            code, _, calls = self.run_cli(['replace-system-updater', '--host', '192.0.2.10', '--edition', 'root', '--data-dir', tmp], [''])
            self.assertEqual(code, 0); self.assertFalse(calls); installer.assert_not_called()

    def test_explicit_system_rollback_recovery_never_starts_installation(self):
        from unittest.mock import MagicMock
        with tempfile.TemporaryDirectory() as tmp, patch('cytv.cli.Installer') as installer, patch('cytv.cli.package.verify_payload', return_value={}):
            code, output, _ = self.run_cli(['recover-system-rollback', '--host', '192.0.2.10', '--edition', 'root', '--data-dir', tmp, '--yes'], remote=MagicMock())
            self.assertEqual(code, 0, output)
            installer.return_value.recover_system_rollback.assert_called_once_with()
            installer.return_value.install.assert_not_called()
        for edition, pending in [('no-root', False), ('root', True)]:
            with tempfile.TemporaryDirectory() as tmp, patch('cytv.cli.Installer') as installer:
                if pending: state.Store(tmp).begin(state.target('192.0.2.10', edition), 'install')
                code, _, calls = self.run_cli(['recover-system-rollback', '--host', '192.0.2.10', '--edition', edition, '--data-dir', tmp, '--yes'])
                self.assertEqual(code, 2)
                self.assertFalse(calls)
                installer.return_value.recover_system_rollback.assert_not_called()

    def test_new_recovery_attempt_is_explicit_and_scoped_to_recovery(self):
        from unittest.mock import MagicMock
        with tempfile.TemporaryDirectory() as tmp, patch('cytv.cli.Installer') as installer:
            code, output, _ = self.run_cli(['recover-system-rollback', '--new-recovery-attempt', '--host', '192.0.2.10', '--edition', 'root', '--data-dir', tmp, '--yes'], remote=MagicMock())
            self.assertEqual(code, 0, output)
            installer.return_value.recover_system_rollback.assert_called_once_with(new_attempt=True)
        for command in ['install', 'status', 'restore']:
            with tempfile.TemporaryDirectory() as tmp, patch('cytv.cli.Installer') as installer:
                code, _, calls = self.run_cli([command, '--new-recovery-attempt', '--host', '192.0.2.10', '--edition', 'root', '--data-dir', tmp, '--yes'])
                self.assertEqual(code, 2); self.assertFalse(calls); installer.assert_not_called()

    def test_system_rollback_recovery_confirmation_defaults_to_no(self):
        with tempfile.TemporaryDirectory() as tmp, patch('cytv.cli.Installer') as installer:
            code, _, calls = self.run_cli(['recover-system-rollback', '--host', '192.0.2.10', '--edition', 'root', '--data-dir', tmp], [''])
            self.assertEqual(code, 0)
            self.assertFalse(calls)
            installer.assert_not_called()

    def test_firmware_access_command_checks_root_pending_and_uses_no_install(self):
        from unittest.mock import MagicMock
        for command,enabled in [('enable-firmware-access',True),('disable-firmware-access',False)]:
            with self.subTest(command=command),tempfile.TemporaryDirectory() as tmp,patch('cytv.cli.Installer') as installer,patch('cytv.cli.package.verify_payload',return_value={}):
                remote=MagicMock();code,output,_=self.run_cli([command,'--host','192.0.2.10','--edition','root','--data-dir',tmp,'--yes'],remote=remote)
                self.assertEqual(code,0,output);installer.return_value.configure_firmware_access.assert_called_once_with(enabled)
                installer.return_value.install.assert_not_called()
        for edition,pending in [('no-root',False),('root',True)]:
            with self.subTest(edition=edition),tempfile.TemporaryDirectory() as tmp,patch('cytv.cli.Installer') as installer:
                if pending:state.Store(tmp).begin(state.target('192.0.2.10',edition),'install')
                code,_,calls=self.run_cli(['enable-firmware-access','--host','192.0.2.10','--edition',edition,'--data-dir',tmp,'--yes'])
                self.assertEqual(code,2);self.assertFalse(calls);installer.return_value.configure_firmware_access.assert_not_called()

    def test_sdk_permission_repair_flag_is_explicit_and_enable_only(self):
        from unittest.mock import MagicMock
        with tempfile.TemporaryDirectory() as tmp,patch('cytv.cli.Installer') as installer,patch('cytv.cli.package.verify_payload',return_value={}):
            code,output,_=self.run_cli(['enable-firmware-access','--repair-package-permissions','--host','192.0.2.10','--edition','root','--data-dir',tmp,'--yes'],remote=MagicMock())
            self.assertEqual(code,0,output)
            installer.return_value.configure_firmware_access.assert_called_once_with(True,repair=True)
        for command in ['install','disable-firmware-access','status']:
            with tempfile.TemporaryDirectory() as tmp,patch('cytv.cli.Installer') as installer:
                code,output,calls=self.run_cli([command,'--repair-package-permissions','--host','192.0.2.10','--edition','root','--data-dir',tmp,'--yes'])
                self.assertEqual(code,2,output);self.assertFalse(calls)

    def test_wam_cache_cleanup_has_default_no_consent_even_with_yes(self):
        from unittest.mock import MagicMock
        for choice, cleared in [('n', False), ('', False), ('y', True)]:
            with self.subTest(choice=choice), tempfile.TemporaryDirectory() as tmp, \
                 patch('cytv.wam_cleanup.inspect', return_value={'bytes': 1024, 'available_kib': 511948}), \
                 patch('cytv.wam_cleanup.clean') as clean, patch('cytv.cli.Installer') as installer, \
                 patch('cytv.cli.package.verify_payload') as payload:
                prompts, output = [], []
                remote = MagicMock()
                code = cli.main(['clean-wam-cache', '--host', '192.0.2.10', '--edition', 'root',
                    '--data-dir', tmp, '--yes'], ask=lambda label: (prompts.append(label), choice)[1],
                    write=output.append, connect=lambda *args: remote)
                self.assertEqual(code, 0)
                text = ' '.join(' '.join(output).split())
                self.assertIn('free space yourself', text)
                self.assertIn('next app launch may be slower', text)
                self.assertIn('Session Storage, cookies, Local Storage, Service Worker and databases are excluded', text)
                self.assertIn('docs/WAM-CLEANUP.md', text)
                self.assertEqual(len(prompts), 1)
                self.assertIn('[y/N]', prompts[0])
                self.assertEqual(clean.call_count, int(cleared))
                if cleared: clean.assert_called_once_with(remote)
                installer.return_value.install.assert_not_called()
                payload.assert_not_called()

    def test_wam_cleanup_rechecks_pending_receipt_after_acquiring_lock(self):
        from contextlib import contextmanager
        from unittest.mock import MagicMock
        original = state.Store.lock
        @contextmanager
        def lock(store, profile):
            with original(store, profile):
                store.begin(profile, 'install')
                yield
        with tempfile.TemporaryDirectory() as tmp, patch.object(state.Store, 'lock', lock), \
             patch('cytv.wam_cleanup.inspect') as inspect:
            code, output, calls = self.run_cli(['clean-wam-cache', '--host', '192.0.2.10',
                '--edition', 'root', '--data-dir', tmp, '--yes'], ['y', 'y'], remote=MagicMock())
            self.assertEqual(code, 2, output)
            inspect.assert_not_called()
            self.assertFalse(calls)

    def test_wam_cleanup_refuses_noninteractive_no_root_and_pending_operations(self):
        from unittest.mock import MagicMock
        for mode in ('noninteractive', 'no-root', 'pending'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp, \
                 patch('cytv.wam_cleanup.inspect') as inspect, patch('cytv.wam_cleanup.clean') as clean:
                edition = 'no-root' if mode == 'no-root' else 'root'
                if mode == 'pending':
                    state.Store(tmp).begin(state.target('192.0.2.10', edition), 'install')
                flags = ['--non-interactive'] if mode == 'noninteractive' else []
                code, output, _ = self.run_cli(['clean-wam-cache', '--host', '192.0.2.10',
                    '--edition', edition, '--data-dir', tmp, '--yes'] + flags, remote=MagicMock())
                self.assertEqual(code, 2, output)
                inspect.assert_not_called()
                clean.assert_not_called()

    def test_system_update_bootstrap_is_a_separate_maintenance_action(self):
        from unittest.mock import MagicMock
        with tempfile.TemporaryDirectory() as tmp, \
                patch('cytv.cli.Installer') as cls, \
                patch('cytv.cli.package.verify_payload', return_value={'files': {'system-updater/bundle.json': 'hash'}}), \
                patch('cytv.tv.SSAP') as ssap:
            cls.return_value.enable_system_updates.return_value = {'installed': True}
            code, output, _ = self.run_cli(['enable-system-updates', '--host', '192.0.2.10',
                '--edition', 'root', '--data-dir', tmp, '--yes'], [], remote=MagicMock())
            self.assertEqual(code, 0, output)
            cls.return_value.enable_system_updates.assert_called_once_with()
            cls.return_value.install.assert_not_called()
            ssap.assert_not_called()

    def test_failed_inline_removal_keeps_receipt_and_reports_uninstall_phase(self):
        from unittest.mock import MagicMock
        from cytv.errors import UserError
        with tempfile.TemporaryDirectory() as tmp, \
             patch('cytv.cli.package.verify_payload', return_value={}), \
             patch('cytv.cli.Installer') as cls, patch('cytv.tv.SSAP') as ssap:
            store = state.Store(tmp)
            profile = state.target('192.0.2.10', 'no-root')
            store.begin(profile, 'uninstall')
            store.save(profile);(store.device_dir(profile)/'known_hosts').write_bytes(b'original pin')
            inst = cls.return_value
            inst.store, inst.profile = store, profile
            inst.remote.luna.return_value = {'returnValue': True, 'status': {'apps': []}}
            inst.observe_recovery.return_value = {'can_resume_root_setup': False}
            inst.uninstall.side_effect = UserError('Removal remains unconfirmed')
            code, output, _ = self.run_cli(['--host', profile['host'], '--edition', 'no-root',
                '--data-dir', tmp, '--yes'], ['y', 'y'], remote=MagicMock())
            self.assertEqual(code, 2, output)
            self.assertIsNotNone(store.pending(profile))
            report = json.loads(next(Path(tmp).glob('reports/*.json')).read_text())
            self.assertEqual(report['phase'], 'recover')
            inst.version_summary.assert_not_called()
            inst.install.assert_not_called()
            ssap.assert_not_called()

    def test_install_offers_to_finish_no_root_removal_with_explicit_consent(self):
        from unittest.mock import MagicMock
        for action, choice in ((a, c) for a in ('install', 'uninstall')
                               for c in ('y', 'n', 'q', 'non-interactive')):
            with self.subTest(action=action, choice=choice), tempfile.TemporaryDirectory() as tmp, \
                 patch('cytv.cli.package.verify_payload', return_value={}), \
                 patch('cytv.cli.Installer') as cls, patch('cytv.tv.SSAP') as ssap:
                store = state.Store(tmp)
                profile = state.target('192.0.2.10', 'no-root')
                store.begin(profile, action)
                store.save(profile);(store.device_dir(profile)/'known_hosts').write_bytes(b'original pin')
                inst = cls.return_value
                inst.store, inst.profile = store, profile
                inst.remote.luna.return_value = {'returnValue': True, 'status': {'apps': []}}
                inst.observe_recovery.return_value = {'can_resume_root_setup': False}
                inst.uninstall.side_effect = lambda: store.finish(profile)
                inst.version_summary.return_value = []
                flags = ['--yes', '--non-interactive'] if choice == 'non-interactive' else [] if choice == 'y' else ['--yes']
                code, output, _ = self.run_cli(['--host', profile['host'], '--edition', 'no-root',
                    '--data-dir', tmp] + flags,
                    ['y', 'y', 'y'] if choice == 'y' else [] if choice == 'non-interactive' else [choice], remote=MagicMock())
                self.assertEqual(inst.uninstall.call_count, int(choice == 'y'), output)
                self.assertIn('Review recovery options', output)
                if choice == 'y':
                    self.assertIsNone(store.pending(profile))
                    inst.version_summary.assert_not_called()
                else:
                    self.assertIsNotNone(store.pending(profile))
                    inst.version_summary.assert_not_called()
                self.assertEqual(code, 2 if choice == 'non-interactive' else 130 if choice == 'q' else 0, output)
                inst.install.assert_not_called()
                ssap.assert_not_called()

    def test_pending_root_install_never_offers_no_root_removal(self):
        from unittest.mock import MagicMock
        with tempfile.TemporaryDirectory() as tmp, \
             patch('cytv.cli.package.verify_payload', return_value={}), \
             patch('cytv.cli.Installer') as cls:
            store = state.Store(tmp)
            profile = state.target('192.0.2.10', 'root')
            store.begin(profile, 'install')
            cls.return_value.store, cls.return_value.profile = store, profile
            cls.return_value.observe_recovery.return_value = {'can_resume_root_setup': False}
            code, output, _ = self.run_cli(['--host', profile['host'], '--edition', 'root',
                '--data-dir', tmp, '--yes'], ['y'], remote=MagicMock())
            self.assertEqual(code, 2, output)
            self.assertEqual(store.pending(profile)['action'], 'install')
            cls.return_value.uninstall.assert_not_called()
            cls.return_value.install.assert_not_called()

    def test_each_maintenance_command_reaches_its_operation_without_installing(self):
        from unittest.mock import MagicMock
        for command in ('status', 'doctor', 'restore', 'uninstall'):
            with self.subTest(command=command), tempfile.TemporaryDirectory() as tmp, \
                    patch('cytv.cli.Installer') as installer, \
                    patch('cytv.cli.package.verify_payload') as verify:
                operation = installer.return_value
                operation.status.return_value = {}
                operation.restore.return_value = {}
                operation.uninstall.return_value = {}
                code, output, calls = self.run_cli(
                    [command, '--host', '192.0.2.10', '--data-dir', tmp, '--yes'],
                    ['1'], remote=MagicMock())
                self.assertEqual(code, 0, output)
                self.assertTrue(calls)
                if command=='uninstall':verify.assert_called_once()
                else:verify.assert_not_called()
                operation.install.assert_not_called()
                if command == 'doctor':
                    operation.preflight.assert_called_once_with()
                    operation.status.assert_called_once_with()
                elif command == 'uninstall':
                    operation.uninstall.assert_called_once_with(full_project=True)
                else:
                    getattr(operation, command).assert_called_once_with()

    def test_maintenance_chooses_connection_without_installation_steps(self):
        from cytv.desktop import DesktopConsole
        for command in ('status', 'doctor', 'restore', 'uninstall'):
            with self.subTest(command=command), tempfile.TemporaryDirectory() as tmp:
                events = []
                args = cli.parser().parse_args([command, '--host', '192.0.2.10'])
                profile = cli.choose_profile(args, state.Store(tmp), lambda _: '1',
                    DesktopConsole(lambda *event: events.append(event)),
                    lambda: [], lambda *args: {'developer_ssh': True})
                self.assertEqual(profile['edition'], 'no-root')
                self.assertIn(('step', (2, 'Choose how you normally connect to this TV.', True)), events)
                self.assertFalse(any(event[0] == 'step' and event[1][1] == 'Choose your edition' for event in events))

    def test_connected_version_review_can_cancel_before_install_or_pairing(self):
        class Remote:
            def luna(self, uri, payload, timeout=30):
                return {'apps': [{'id': 'com.gathin.tvhome', 'version': '1.2.1'}]}
            def close(self): pass
        with tempfile.TemporaryDirectory() as tmp, \
             patch('cytv.cli.package.verify_payload', return_value={'home_version': '1.2.2', 'helper_version': '0.6.13'}), \
             patch('cytv.operations.Installer.install') as install, patch('cytv.tv.SSAP') as ssap:
            code, output, calls = self.run_cli(['--host', '192.0.2.10', '--edition', 'no-root', '--data-dir', tmp], ['y', 'n'], remote=Remote())
            self.assertEqual(code, 0, output)
            self.assertTrue(calls)
            self.assertIn('Home: 1.2.1 → 1.2.2 (Update)', output)
            self.assertLess(output.index('Connecting to the TV'), output.index('1.2.1 → 1.2.2'))
            install.assert_not_called()
            ssap.assert_not_called()

    def test_unreadable_versions_stop_even_with_yes_before_install(self):
        class Remote:
            def luna(self, uri, payload, timeout=30): return {'returnValue': True}
            def close(self): pass
        with tempfile.TemporaryDirectory() as tmp, \
             patch('cytv.cli.package.verify_payload', return_value={'home_version': '1.2.2', 'helper_version': '0.6.13'}), \
             patch('cytv.operations.Installer.install') as install, patch('cytv.tv.SSAP') as ssap:
            code, output, _ = self.run_cli(['--host', '192.0.2.10', '--edition', 'no-root', '--data-dir', tmp, '--yes'], remote=Remote())
            self.assertEqual(code, 2, output)
            self.assertIn('Could not read installed applications', output)
            install.assert_not_called()
            ssap.assert_not_called()

    def test_interrupted_removal_explains_how_to_continue_in_the_app(self):
        from unittest.mock import MagicMock
        from cytv.errors import UserError
        with tempfile.TemporaryDirectory() as tmp, patch('cytv.cli.Installer') as installer, \
                patch('cytv.cli.package.verify_payload',return_value={}):
            profile = state.target('192.0.2.10', 'root')
            store = state.Store(tmp)
            store.save(profile)
            (store.device_dir(profile)/'known_hosts').write_bytes(b'original pin')
            store.begin(profile, 'uninstall', full_project=True, root_submitted=True)
            installer.return_value.uninstall.side_effect = UserError('connection lost')
            code, output, _ = self.run_cli(['uninstall', '--data-dir', tmp], ['y'], remote=MagicMock())
            self.assertEqual(code, 2, output)
            self.assertIn('Check TV and continue removal?', output)
            self.assertNotIn('choose Remove again', output)
            self.assertIn('Continue the remaining cleanup for this TV.', output)
            self.assertTrue(store.pending(profile)['previous']['root_submitted'])

    def setUp(self):
        from cytv import i18n
        i18n.set_language('en')
        self.addCleanup(i18n.set_language, 'en')
        language = patch('cytv.i18n.system_languages', return_value=['en'])
        language.start()
        self.addCleanup(language.stop)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        preferences = patch('cytv.state.default_dir', return_value=Path(directory.name))
        preferences.start()
        self.addCleanup(preferences.stop)

    def test_existing_root_can_be_left_unchanged_without_pairing_or_issue_report(self):
        class Remote:
            def __init__(self): self.calls = []
            def run(self, command, **kwargs):
                self.calls.append(command)
                if 'CYTV_PYTHON_BOUND' in command:return ''
                if 'CYTV_ROOT_READY' in command: return 'CYTV_ROOT_READY'
                if 'CYTV_EXISTING_ROOT' in command: return 'CYTV_EXISTING_ROOT'
                if 'CYTV_EXISTING_UPDATER' in command: return ''
                if 'CYTV_C1_GATE' in command: return ''
                if 'deploy.json' in command: return '{"stage":"installed-recovery-only"}'
                if 'deploy.py status' in command:
                    return '{"returnValue":true,"result":{"recovery":{"integrity_verified":true},"intent":null}}'
                raise AssertionError('Unexpected remote command: '+command)
            def luna(self,uri,payload,**kwargs):
                from tests.cytv.test_root_capabilities import SETTINGS, PROFILES
                if uri=='com.webos.settingsservice/getSystemSettings':return SETTINGS
                if uri=='com.webos.service.systemprofile/getProfiles':return PROFILES
                return {'returnValue':True}
            def close(self): pass
        with tempfile.TemporaryDirectory() as tmp, \
             patch('cytv.cli.package.verify_payload', return_value={}), \
             patch('cytv.cli.payload_dir', return_value=Path(tmp)/'unbuilt-payload'), patch('cytv.cli.Installer.select_graphics'), \
             patch('cytv.cli.Installer.version_summary', return_value=['Root: 0.1.4 → 0.1.5 (Update)']), \
             patch('cytv.tv.SSAP') as ssap:
            remote = Remote()
            code, output, calls = self.run_cli(['--host', '192.0.2.10', '--edition', 'root', '--data-dir', tmp], ['', ''], remote=remote)
            self.assertEqual(code, 0, output)
            self.assertIn('Reinstall Root using this installer', output)
            self.assertIn('left unchanged', output)
            self.assertFalse(list(Path(tmp).glob('reports/*.json')))
            self.assertIsNone(state.Store(tmp).pending(state.target('192.0.2.10','root')))
            ssap.assert_not_called()
            self.assertFalse(any('uninstall' in command for command in remote.calls))
        for flags, answers, expected in [(['--yes'], [''], 0), (['--yes','--non-interactive'], [], 2)]:
            with self.subTest(flags=flags), tempfile.TemporaryDirectory() as tmp, \
                 patch('cytv.cli.Installer.version_summary', return_value=['Root: 0.1.4 → 0.1.5 (Update)']), \
                 patch('cytv.cli.package.verify_payload', return_value={}), \
                 patch('cytv.cli.payload_dir', return_value=Path(tmp)/'unbuilt-payload'), patch('cytv.cli.Installer.select_graphics'), patch('cytv.tv.SSAP') as ssap:
                remote=Remote()
                code, output, _ = self.run_cli(['--host','192.0.2.10','--edition','root','--data-dir',tmp]+flags, answers, remote=remote)
                self.assertEqual(code, expected, output)
                ssap.assert_not_called()
                self.assertFalse(any('uninstall' in command for command in remote.calls))

    def test_install_checks_pending_state_and_offers_inline_completion(self):
        from unittest.mock import MagicMock
        for resolved, resume, accept in ((True, False, False), (False, True, True), (False, True, False), (False, False, False)):
            with self.subTest(resolved=resolved, resume=resume, accept=accept), tempfile.TemporaryDirectory() as tmp, \
                 patch('cytv.cli.package.verify_payload', return_value={}), \
                 patch('cytv.cli.Installer') as cls, patch('cytv.tv.SSAP') as ssap:
                store = state.Store(tmp); profile = state.target('192.0.2.10', 'root')
                store.begin(profile, 'setup-root-updater', stage='verify', requires_updater=True)
                store.save(profile);(store.device_dir(profile)/'known_hosts').write_bytes(b'original pin')
                inst = cls.return_value
                inst.store, inst.profile = store, profile
                def status():
                    if resolved: store.finish(profile)
                    return {'can_resume_root_setup': resume, 'deployment_stage':'installed-recovery-only', 'device':{'result':{'recovery':{'integrity_verified':True}}}}
                inst.observe_recovery.side_effect = status
                if resolved:
                    from cytv.errors import ExistingRoot
                    inst.preflight.side_effect = ExistingRoot('existing')
                inst.resume_root_setup.return_value = {'updates_ready':True}
                code, output, _ = self.run_cli(['--host','192.0.2.10','--edition','root','--data-dir',tmp], ['', 'y'] + (['1', 'y'] if accept else ['']), remote=MagicMock())
                self.assertEqual(code, 0 if resolved or resume else 2, output)
                inst.observe_recovery.assert_called()
                self.assertEqual(inst.resume_root_setup.call_count, int(resume and accept))
                if resume: inst.select_graphics.assert_not_called()
                inst.install.assert_not_called()
                ssap.assert_not_called()
                if not resolved and not (resume and accept): self.assertIsNotNone(store.pending(profile))

    def test_first_question_explains_how_to_find_the_tv_address(self):
        with tempfile.TemporaryDirectory() as tmp:
            messages = []
            before_question = []
            def ask(prompt):
                before_question.append('\n'.join(messages))
                raise EOFError
            code = cli.main(['--data-dir', tmp], ask=ask, write=messages.append, search=lambda: [])
            self.assertEqual(code, 130)
            for detail in ('Settings', 'Wi-Fi', 'Ethernet', '192.168.'):
                self.assertIn(detail, before_question[0])
            self.assertFalse(list(Path(tmp).glob('reports/*.json')))

    def test_secret_prompt_explains_hidden_tv_passphrase_without_echoing_it(self):
        from cytv.errors import UserError
        with tempfile.TemporaryDirectory() as tmp:
            output, before_secret = [], []
            def secret(prompt):
                before_secret.append('\n'.join(output))
                return 'PRIVATE-TEST-PASSPHRASE'
            def connect(profile, directory, secret, trust):
                secret('Developer Mode passphrase: ')
                raise UserError('Connection cancelled for this test.')
            code = cli.main(['status', '--host', 'tv.local', '--edition', 'no-root', '--data-dir', tmp],
                            write=output.append, connect=connect, secret=secret)
            self.assertEqual(code, 2)
            self.assertIn('hidden', before_secret[0])
            self.assertIn('Key Server', before_secret[0])
            self.assertNotIn('PRIVATE-TEST-PASSPHRASE', '\n'.join(output))

    def test_mistyped_address_and_menu_choice_can_be_corrected_without_issue_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, output, calls = self.run_cli(['--data-dir', tmp], ['', '?', '192.168.1.999', '192.0.2.10', '7', '1', 'maybe', 'n'])
            self.assertEqual(code, 0, output)
            self.assertIn('Cancelled', output)
            self.assertFalse(calls)
            self.assertFalse(list(Path(tmp).glob('reports/*.json')))

    def test_saved_tv_can_be_replaced_in_interactive_install_wizard(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = state.Store(tmp)
            store.save(state.target('192.0.2.10', 'no-root'))
            code, output, calls = self.run_cli(['--data-dir', tmp], ['0', '192.0.2.20', '1', 'n'])
            self.assertEqual(code, 0, output)
            self.assertIn('192.0.2.20', output)
            self.assertFalse(calls)

    def test_discovered_tv_is_selected_without_entering_an_address(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, output, calls = self.run_cli(['--data-dir', tmp], ['', '1', 'n'],
                search=lambda: [{'host': '192.0.2.20', 'name': 'Living room (OLED C3)'}])
            self.assertEqual(code, 0, output)
            self.assertIn('Living room (OLED C3)', output)
            self.assertIn('TV: 192.0.2.20', output)
            self.assertNotIn('Find the IP address', output)
            self.assertFalse(calls)

    def test_search_can_be_repeated_then_a_different_tv_selected(self):
        with tempfile.TemporaryDirectory() as tmp:
            results = iter([[], [{'host': '192.0.2.21', 'name': 'Bedroom'}]])
            code, output, calls = self.run_cli(['--data-dir', tmp], ['r', '', '1', 'n'], search=lambda: next(results))
            self.assertEqual(code, 0, output)
            self.assertIn('TV: 192.0.2.21', output)
            self.assertFalse(calls)

    def test_discovery_network_failure_has_manual_fallback_without_error_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            def denied(): raise PermissionError('private network details')
            code, output, calls = self.run_cli(['--data-dir', tmp], ['192.0.2.10', '1', 'n'], search=denied)
            self.assertEqual(code, 0, output)
            self.assertIn('Local Network', output)
            self.assertNotIn('private network details', output)
            self.assertFalse(calls)
            self.assertFalse(list(Path(tmp).glob('reports/*.json')))

    def test_explicit_host_noninteractive_and_disabled_search_do_not_broadcast(self):
        with tempfile.TemporaryDirectory() as tmp:
            def forbidden(): raise AssertionError('must not search')
            for flags, answers, expected in [
                (['--host', '192.0.2.10'], ['1', 'n'], 0),
                (['--non-interactive'], [], 2),
                (['--no-discovery'], ['192.0.2.10', '1', 'n'], 0),
            ]:
                with self.subTest(flags=flags):
                    code, output, calls = self.run_cli(flags + ['--data-dir', tmp], answers, search=forbidden)
                    self.assertEqual(code, expected, output)
                    self.assertFalse(calls)

    def test_discovered_list_always_offers_manual_address_and_validates_choice(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, output, calls = self.run_cli(['--data-dir', tmp], ['9', '0', '192.0.2.50', '1', 'n'],
                search=lambda: [{'host': '192.0.2.20', 'name': 'Living room'}])
            self.assertEqual(code, 0, output)
            self.assertIn('TV: 192.0.2.50', output)
            self.assertFalse(calls)

    def test_root_connection_sets_current_choice_without_ranking_editions(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, output, calls = self.run_cli(['--host', '192.0.2.10', '--data-dir', tmp], ['', 'n'],
                inspect=lambda host, port: {'root_ssh': True, 'developer_ssh': False, 'root_port': 22})
            self.assertEqual(code, 0, output)
            self.assertIn('Root SSH detected', output)
            self.assertIn('Enter = current choice', output)
            self.assertIn("No-root uses LG's Developer Mode app.", output)
            self.assertIn('Root requires administrator access', output)
            self.assertNotIn('recommended', output)
            self.assertNotIn('Unsure?', output)
            self.assertIn('Edition: Root', output)
            self.assertNotIn('Root Preview', output)
            self.assertFalse(calls)

    def test_root_install_does_not_ask_for_key_before_connecting(self):
        from cytv.errors import UserError
        with tempfile.TemporaryDirectory() as tmp:
            questions, output = [], []
            answers = iter([''])
            def ask(prompt):
                questions.append(prompt)
                return next(answers)
            def connect(profile, directory, secret, trust):
                self.assertNotIn('identity', profile)
                raise UserError('Stop before TV changes')
            code = cli.main(['--host', '192.0.2.10', '--edition', 'root', '--data-dir', tmp],
                            ask=ask, write=output.append, connect=connect)
            self.assertEqual(code, 2, '\n'.join(output))
            self.assertEqual(len(questions), 1, questions)
            self.assertIn('[Y/n]', questions[0])
            self.assertNotIn('Your existing SSH key', '\n'.join(output))

    def test_first_tv_identity_uses_plain_confirmation_not_fingerprint_entry(self):
        from cytv.errors import UserError
        with tempfile.TemporaryDirectory() as tmp:
            output, questions = [], []
            answers = iter(['?', 'y'])
            def ask(prompt):
                questions.append(prompt)
                return next(answers)
            def connect(profile, directory, secret, trust):
                self.assertTrue(trust('SHA256:test-public-key', True))
                raise UserError('Stop before TV changes')
            code = cli.main(['status', '--host', '192.0.2.10', '--edition', 'root', '--data-dir', tmp],
                            ask=ask, write=output.append, connect=connect)
            self.assertEqual(code, 2)
            self.assertTrue(all('Connect and remember' in prompt for prompt in questions))
            self.assertNotIn('Verified SHA256 fingerprint', '\n'.join(output))
            self.assertIn('SHA256:test-public-key', '\n'.join(output))

    def test_sleeping_tv_waits_for_user_before_retry_and_never_starts_install_on_cancel(self):
        from cytv.errors import TVNotReady
        class Remote:
            def close(self): self.closed = True
        remote = Remote()
        with tempfile.TemporaryDirectory() as tmp, \
             patch('cytv.cli.package.verify_payload', return_value={}), \
             patch('cytv.tv.SSAP') as ssap, patch('cytv.cli.Installer') as installer:
            ssap.return_value.__enter__.side_effect = TVNotReady()
            code, output, calls = self.run_cli(['--host', '192.0.2.10', '--edition', 'no-root', '--data-dir', tmp], ['', '', '', 'q'], remote=remote)
            self.assertEqual(code, 130, output)
            self.assertIn('Turn on your TV', output)
            self.assertIn('Installation has not started', output)
            self.assertEqual(ssap.call_count, 1)
            installer.return_value.install.assert_not_called()
            self.assertIsNone(state.Store(tmp).pending(state.target('192.0.2.10', 'no-root')))
            self.assertFalse(list(Path(tmp).glob('reports/*.json')))
            self.assertTrue(remote.closed)

    def test_noninteractive_sleeping_tv_reports_clear_reason_without_retry(self):
        from cytv.errors import TVNotReady
        class Remote:
            def close(self): pass
        with tempfile.TemporaryDirectory() as tmp, \
             patch('cytv.cli.package.verify_payload', return_value={}), \
             patch('cytv.tv.SSAP') as ssap, patch('cytv.cli.Installer') as installer:
            ssap.return_value.__enter__.side_effect = TVNotReady()
            code, output, calls = self.run_cli(['--host', '192.0.2.10', '--edition', 'no-root', '--data-dir', tmp,
                                               '--non-interactive', '--yes'], remote=Remote())
            self.assertEqual(code, 2, output)
            self.assertIn('Installation has not started', output)
            self.assertEqual(ssap.call_count, 1)
            installer.return_value.install.assert_not_called()
            report=json.loads(next(Path(tmp).glob('reports/*.json')).read_text())
            self.assertEqual(report['phase'], 'pair-tv')
            self.assertEqual(report['connection'], {'protocol': 'ssap', 'close_code': 1008, 'reason_code': 'tv-not-ready'})

    def test_waking_tv_retries_only_reading_before_single_install(self):
        from cytv.errors import TVNotReady
        class Remote:
            def close(self): pass
        with tempfile.TemporaryDirectory() as tmp, \
             patch('cytv.cli.package.verify_payload', return_value={}), \
             patch('cytv.cli.payload_dir', return_value=Path(tmp)), \
             patch('cytv.tv.SSAP') as ssap, patch('cytv.cli.Installer') as installer:
            (Path(tmp)/'fallback.png').write_bytes(b'test-fallback')
            inventory = {'apps': [], 'inputs': []}
            session = ssap.return_value
            session.key = None
            session.inventory.return_value = inventory
            session.icon_diagnostics = {'schema': 1, 'status': 'complete', 'fallback': 3}
            session.__enter__.side_effect = [TVNotReady(), session]
            code, output, calls = self.run_cli(['--host', '192.0.2.10', '--edition', 'no-root', '--data-dir', tmp],
                                               ['', '', 'Aashiyaan', ''], remote=Remote())
            self.assertEqual(code, 0, output)
            self.assertEqual(len(calls), 1)
            self.assertEqual(ssap.call_count, 2)
            session.inventory.assert_called_once_with(b'test-fallback')
            installer.return_value.install.assert_called_once_with(inventory, None, False)
            self.assertEqual(installer.return_value.tv_name, 'Aashiyaan')
            installer.return_value.trial.assert_not_called()
            self.assertIn('Packages installed; Home Helper launch requested.', output)
            report = json.loads(next(Path(tmp).glob('reports/*.json')).read_text())
            self.assertEqual(report['tv'].get('icon_inventory'), session.icon_diagnostics)
            self.assertNotRegex(output.lower(), r'trial|countdown|keep using|preview release')

    def test_installation_failure_is_never_caught_as_inventory_retry(self):
        from cytv.errors import TVNotReady
        class Remote:
            def close(self): pass
        with tempfile.TemporaryDirectory() as tmp, \
             patch('cytv.cli.package.verify_payload', return_value={}), \
             patch('cytv.cli.payload_dir', return_value=Path(tmp)), \
             patch('cytv.tv.SSAP') as ssap, patch('cytv.cli.Installer') as installer:
            (Path(tmp)/'fallback.png').write_bytes(b'test-fallback')
            ssap.return_value.__enter__.return_value.inventory.return_value = {'apps': [], 'inputs': []}
            installer.return_value.install.side_effect = TVNotReady()
            code, output, calls = self.run_cli(['--host', '192.0.2.10', '--edition', 'no-root', '--data-dir', tmp, '--yes'], remote=Remote())
            self.assertEqual(code, 2, output)
            self.assertEqual(ssap.call_count, 1)
            installer.return_value.install.assert_called_once()
            report=json.loads(next(Path(tmp).glob('reports/*.json')).read_text())
            self.assertEqual(report['phase'], 'install-packages')
            self.assertNotIn('Installation has not started', output)

    def test_no_root_listener_is_not_presented_as_proven_unrooted(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, output, calls = self.run_cli(['--host', '192.0.2.10', '--data-dir', tmp], ['', 'n'],
                inspect=lambda host, port: {'root_ssh': False, 'developer_ssh': True, 'root_port': 22})
            self.assertEqual(code, 0, output)
            self.assertIn('Root access not confirmed', output)
            self.assertIn('Enter = current choice', output)
            self.assertNotIn('recommended', output)
            self.assertIn('Edition: No-root', output)
            self.assertNotIn('TV is not rooted', output)
            self.assertIn('SSH port: 9922', output)
            self.assertFalse(calls)

    def test_invalid_target_and_explicit_edition_never_run_connection_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            def forbidden(*args): raise AssertionError('must not inspect')
            code, output, _ = self.run_cli(['--host', '192.0.2.10', '--port', '99999', '--data-dir', tmp], inspect=forbidden)
            self.assertEqual(code, 2, output)
            self.assertIn('Invalid TV address or port', output)
            code, output, _ = self.run_cli(['--host', '192.0.2.10', '--edition', 'no-root', '--data-dir', tmp], ['n'], inspect=forbidden)
            self.assertEqual(code, 0, output)
            self.assertNotIn('Checking TV connections', output)

    def run_cli(self, argv, answers=(), remote=None, search=lambda: [], inspect=lambda host, port: {}):
        output, iterator = io.StringIO(), iter(answers)
        calls = []
        def connect(*args):
            calls.append(args)
            if remote is None:
                raise AssertionError('must not connect')
            return remote
        code = cli.main(argv, ask=lambda _: next(iterator), write=lambda message: output.write(str(message) + '\n'), connect=connect, search=search, inspect=inspect)
        return code, output.getvalue(), calls

    def test_help_and_version_need_no_payload_or_dependencies(self):
        code, output, calls = self.run_cli(['--version'])
        self.assertEqual(code, 0)
        self.assertRegex(output, r'cytv \d+\.\d+\.\d+')
        self.assertFalse(calls)

    def test_wizard_cancel_stops_before_connecting_or_creating_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, output, calls = self.run_cli(['--data-dir', tmp], ['192.0.2.10', '1', 'n'])
            self.assertEqual(code, 0)
            self.assertIn('Cancelled', output)
            self.assertFalse(calls)
            self.assertEqual(state.Store(tmp).profiles(), [])

    def test_missing_target_in_noninteractive_input_fails_before_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, output, calls = self.run_cli(['status', '--non-interactive', '--data-dir', tmp])
        self.assertEqual(code, 2)
        self.assertIn('--host', output)
        self.assertFalse(calls)

    def test_saved_profile_is_reused_for_read_only_status(self):
        class Remote:
            def run(self, command):
                return 'CYTV_HELPER_IDLE'
            def luna(self, *args, **kwargs):
                return {'returnValue': True, 'apps': [{'id': 'com.gathin.tvhome', 'version': '1.2.2'}]}
            def close(self):
                self.closed = True
        with tempfile.TemporaryDirectory() as tmp:
            store = state.Store(tmp)
            store.save(state.target('192.0.2.10', 'no-root'))
            remote = Remote()
            code, output, calls = self.run_cli(['status', '--data-dir', tmp], remote=remote)
            self.assertEqual(code, 0)
            self.assertIn('1.2.2', output)
            self.assertEqual(calls[0][0]['port'], 9922)
            self.assertTrue(remote.closed)

    def test_unknown_error_never_prints_secrets_or_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = []
            def bad(*args):
                raise RuntimeError('private-password-123')
            code = cli.main(['status', '--host', 'tv.local', '--edition', 'root', '--data-dir', tmp],
                            ask=lambda _: '', write=output.append, connect=bad)
            self.assertEqual(code, 1)
            self.assertNotIn('private-password-123', '\n'.join(output))
            self.assertNotIn('Traceback', '\n'.join(output))


if __name__ == '__main__':
    unittest.main()
