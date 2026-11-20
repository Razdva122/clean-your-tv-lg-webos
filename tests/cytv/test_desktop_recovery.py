"""Exercise the desktop recovery journey with real CLI/state and simulated TV IO."""
import json
import hashlib
import itertools
import os
import shlex
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from cytv import cli, debloat, install_settings, package, state, i18n
from cytv.errors import TVRejected
from tests.cytv.test_operations import Remote
try:
    from PySide6.QtWidgets import QApplication, QComboBox, QPushButton
    from cytv.gui import Wizard
    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, 'Desktop build dependencies are optional for CLI tests')
class DesktopRecoveryTests(unittest.TestCase):
    def test_root_setup_offers_one_choice_to_review_the_original_no_root_removal(self):
        self.store.finish(self.profile)
        original = state.target(self.profile['host'], 'no-root', 2222, connection='root-ssh')
        self.store.save(original)
        (self.store.device_dir(original) / 'known_hosts').write_bytes(b'original pin')
        pending = self.store.request_clean_removal(original)
        w = self.window()
        w.start('install', state.target(original['host'], 'root'))
        self.pump(lambda: w.pending is not None or not w.running)
        self.assertEqual(self.connections, [])
        review = self.button(w, 'Review recovery options')
        self.assertIsNotNone(review, w.details.toPlainText())
        self.assertTrue(self.button(w, 'Cancel').isDefault())
        review.click()
        self.pump(lambda: w.pending is not None or not w.running)
        self.assertEqual(self.connections, [original])
        self.assertEqual(w.recovery_profile, original)
        self.assertEqual(w.pending.title, 'Continue removing Clean Your TV?')
        w.submit('n')
        self.pump(lambda: not w.running)
        self.assertEqual(self.store.pending(original), pending)
        self.assertEqual(self.remote.uploads, {})

    def test_storage_preflight_retries_only_failed_check_before_install_confirmation(self):
        read = ('storage-check', True)
        writable = ('storage-check', False)
        selected = ('storage-select', True)
        decisions = ('cancel-retry', 'cancel-install', 'pending', 'late-pending', 'legacy-uninstall',
                     'identity', 'check-fails-again', 'install')
        for failed_check, decision in itertools.product((read, writable), decisions):
            with self.subTest(failed_check=failed_check, decision=decision):
                self.store.finish(self.profile)
                self.remote = Remote()
                self.remote.close = lambda: None
                original = self.remote.run
                checks = []
                before_retry = [selected, read] if failed_check == read else [selected, read, writable]
                failure_count = 2 if decision == 'check-fails-again' else 1
                def run(command, **kwargs):
                    if command.startswith('unset NODE_OPTIONS NODE_PATH && /usr/bin/node -e '):
                        args = shlex.split(command)
                        request = json.loads(args[-1]) if args[-1].startswith('{') else {}
                        action = request.get('command')
                        if action in ('storage-select', 'storage-check'):
                            read_only = "case 'storage-check':result=storageCheck();break;" not in args[-2]
                            checks.append((action, read_only))
                            if checks[-1] == failed_check and checks.count(failed_check) <= failure_count:
                                if failed_check == writable or decision == 'check-fails-again':
                                    return json.dumps({
                                        'operation': request['plan']['operation'],
                                        'observer_error': {'exception_code': 'EACCES',
                                                           'filesystem_operation': 'lstat' if read_only else 'mkdir',
                                                           'storage_area': 'private-storage'},
                                    })
                                return 'MALFORMED'
                    return original(command, **kwargs)
                self.remote.run = run

                w = self.window()
                w.start('install', self.profile)
                for expected in ('Connect to check installed versions?', 'Install these versions?'):
                    self.pump(lambda: w.pending is not None or not w.running)
                    self.assertIsNotNone(w.pending, w.details.toPlainText())
                    self.assertEqual(w.pending.title, expected)
                    w.submit('y')
                self.pump(lambda: self.button(w, 'Retry storage check') is not None or not w.running)
                retry = self.button(w, 'Retry storage check')
                self.assertIsNotNone(retry, w.details.toPlainText())
                self.assertEqual(checks, before_retry)
                self.assertIsNone(self.store.pending(self.profile))
                self.assertEqual(self.remote.observers, {})
                self.assertEqual(self.remote.uploads, {})
                if decision == 'cancel-retry':
                    w.submit('n')
                elif decision in ('pending', 'legacy-uninstall'):
                    self.store.begin(self.profile, 'uninstall' if decision == 'legacy-uninstall' else 'install', stage='pending')
                    retry.click()
                elif decision == 'identity':
                    (self.store.device_dir(self.profile) / 'known_hosts').write_bytes(b'different pin')
                    retry.click()
                elif decision == 'check-fails-again' and failed_check == read:
                    self.assertIn('verify that its SSH account can access', w.content.toPlainText())
                    retry.click()
                else:
                    retry.click()
                    self.pump(lambda: w.pending is not None or not w.running)
                    self.assertIsNotNone(w.pending, w.details.toPlainText())
                    self.assertEqual(w.pending.title, 'Install these versions?')
                    self.assertEqual(w.pending.default, 'n')
                    self.assertEqual(checks, before_retry + [read])
                    self.assertEqual(self.remote.observers, {})
                    self.assertEqual(self.remote.uploads, {})
                    if decision == 'late-pending':
                        self.store.begin(self.profile, 'install', stage='pending')
                    w.submit('y' if decision in ('install', 'late-pending', 'check-fails-again') else 'n')
                    if decision == 'install':
                        # This leg runs both package installs before the next prompt.
                        self.pump(lambda: w.pending is not None or not w.running, timeout=30)
                        if w.pending:
                            w.submit(None)
                self.pump(lambda: not w.running)
                installs = [c for c in self.remote.calls if c[:2] == ('luna', 'com.webos.appInstallService/dev/install')]
                self.assertEqual(len(installs), 2 if decision == 'install' else 0)
                self.assertFalse(any(c[0] == 'luna' and c[1].endswith('/remove') for c in self.remote.calls))
                self.assertEqual(self.connections[-1], self.profile)
                if decision != 'install':
                    self.assertEqual(self.remote.observers, {})
                    self.assertEqual(self.remote.uploads, {})
                if decision in ('pending', 'late-pending', 'legacy-uninstall'):
                    self.assertIsNotNone(self.button(w, 'Review recovery options'))
                    self.assertEqual(self.store.pending(self.profile)['stage'], 'pending')
                else:
                    self.assertIsNone(self.store.pending(self.profile))
                if decision == 'check-fails-again':
                    self.assertEqual(w.failure_help['code'], 'tv-storage-unavailable')
                if decision == 'identity':
                    self.assertEqual(w.failure_help['code'], 'ssh-identity')
                    (self.store.device_dir(self.profile) / 'known_hosts').write_bytes(b'original pin')
                if decision in ('cancel-retry', 'pending', 'legacy-uninstall', 'identity'):
                    self.assertEqual(checks, before_retry)
                elif decision == 'install' or decision == 'check-fails-again' and failed_check == writable:
                    self.assertEqual(checks, before_retry + [read, writable])
                else:
                    self.assertEqual(checks, before_retry + [read])
                self.assertIsNone(self.button(w, 'Retry storage check'))
                w.close()

    def test_root_reinstall_resumes_after_restart_ssh_refusal_and_reopening(self):
        import errno
        from paramiko.ssh_exception import NoValidConnectionsError
        from cytv.errors import ExistingRoot
        from cytv.operations import Installer
        self.store.finish(self.profile)
        self.profile = state.target('192.0.2.10', 'root', 2222)
        self.store.save(self.profile)
        (self.store.device_dir(self.profile) / 'known_hosts').write_bytes(b'original pin')
        cleanup_calls, installs, auth = [], [], []
        online = True

        def connect(profile, directory, secret, trust, *, persist=True):
            auth.append((profile, directory, persist, trust(None, None) if not persist else None))
            if not online:
                socket_error = ConnectionRefusedError(errno.ECONNREFUSED, 'SSH still starting')
                raise NoValidConnectionsError({(profile['host'], profile['port']):socket_error})
            return self.remote

        self.connect = connect

        def cleanup(installer, pending):
            cleanup_calls.append(pending['removal_operation'])
            if len(cleanup_calls) <= 2:
                installer.store.checkpoint(installer.profile, stage='restart-required', removal_reason='restart-required',
                                           cleanup_restart_triggers=['controller-still-running'])
                return {'restart_required':True}
            if len(cleanup_calls) != 3:
                self.fail('Already verified cleanup was repeated')
            result = {'removed':True, 'verified_clean':True}
            installer.store.checkpoint(installer.profile, stage='verified-clean', removal_reason='removal-verified', result=result)
            installer.store.finish_clean_removal(installer.profile)
            return result

        def preflight(installer, install=False, **kwargs):
            if install and len(cleanup_calls) != 3:
                raise ExistingRoot('Existing Root')

        def install(installer, inventory, key, migrate, reinstall=None):
            if reinstall:
                installer.prepare_root_reinstall()
            self.assertEqual(len(cleanup_calls), 3)
            self.assertIsNone(installer.store.pending(installer.profile))
            self.assertEqual(installer.profile, self.profile)
            installs.append(installer.profile)
            return {}

        with (
            patch.object(Installer, 'continue_clean_removal', cleanup),
            patch.object(Installer, 'preflight', preflight),
            patch.object(Installer, 'select_graphics'),
            patch.object(Installer, 'version_summary', return_value=[]),
            patch.object(Installer, 'root_inventory', return_value=self.inventory),
            patch.object(Installer, 'install', install),
            patch('cytv.cli.sleep'),
        ):
            w = self.window()
            w.start('install', self.profile)
            self.pump(lambda: w.pending is not None)
            self.assertEqual(w.pending.title, 'Connect to check installed versions?')
            w.submit('y')
            self.pump(lambda: w.pending is not None or not w.running)
            self.assertIsNotNone(w.pending, w.details.toPlainText())
            self.assertEqual(w.pending.title, 'Reinstall Root?')
            w.submit('y')
            self.pump(lambda: not w.running)
            self.assertIn('Disconnect the TV from power', w.subtitle.text())
            label = 'I restarted the TV — check and continue'
            for attempt in (1, 2):
                self.assertEqual(len(cleanup_calls), attempt)
                expected = 'Restart the TV to finish removal' if attempt == 1 else 'The TV still needs a full restart'
                self.assertEqual(w.title.text(), expected)
                self.assertNotEqual(w.title.property('state'), 'error')
                self.assertNotIn('Could not complete this step', w.details.toPlainText())
                self.assertNotIn('choose Try again', w.details.toPlainText())
                self.assertIsNone(self.button(w, 'Open an issue'))
                self.assertIsNone(self.button(w, 'Try again'))
                self.assertTrue(self.button(w, label).isDefault())
                self.assertEqual(installs, [])
                report = json.loads(w.report.read_text())
                self.assertIsNone(report['error_type'])
                self.assertEqual(report['removal']['restart_triggers'], ['controller-still-running'])
                if attempt == 1:
                    self.button(w, label).click()
                    self.pump(lambda: not w.running)
            w.close()

            # A separate host attempt before the TV's SSH service has come back.
            online = False
            w = self.window()
            continuation = self.button(w, 'Continue Root reinstallation')
            self.assertIsNotNone(continuation)
            continuation.click()
            self.pump(lambda: not w.running)
            self.assertEqual(len(cleanup_calls), 2)
            self.assertEqual(w.failure_help['code'], 'ssh-refused')
            self.assertNotIn('Restart the TV', w.subtitle.text())
            self.assertEqual(w.rail_title.text(), 'Reinstall Root using this installer')
            self.assertIsNotNone(self.button(w, 'Continue Root reinstallation'))
            w.close()

            online = True
            w = self.window()
            self.button(w, 'Continue Root reinstallation').click()
            self.pump(lambda: w.pending is not None)
            self.assertEqual(w.pending.title, 'Continue Root installation?')
            self.assertEqual(cleanup_calls, [cleanup_calls[0]] * 3)
            self.assertEqual(installs, [])
            w.submit(None)  # Close the installer at the boundary between removal and install.
            self.pump(lambda: not w.running)
            w.close()

            with patch('cytv.cli.package.verify_payload', return_value=dict(self.manifest, home_version='changed')):
                attempts = len(auth)
                w = self.window()
                self.button(w, 'Continue Root reinstallation').click()
                self.pump(lambda: not w.running)
                self.assertIn('same installer build', w.content.toPlainText())
                self.assertEqual(len(auth), attempts)
                w.close()

            pin = self.store.device_dir(self.profile) / 'known_hosts'
            pin.write_bytes(b'different pin')
            w = self.window()
            self.button(w, 'Continue Root reinstallation').click()
            self.pump(lambda: not w.running)
            self.assertEqual(w.failure_help['code'], 'ssh-identity')
            self.assertEqual(len(auth), attempts)
            w.close()
            pin.write_bytes(b'original pin')
            # A separate inspection may change the saved runtime preference.
            self.store.save(dict(self.profile, root_variant='node012-beta'))

            w = self.window()
            self.button(w, 'Continue Root reinstallation').click()
            self.pump(lambda: w.pending is not None)
            self.assertEqual(w.pending.title, 'Continue Root installation?')
            self.button(w, 'Continue Root installation').click()
            self.pump(lambda: w.pending is not None)
            self.assertEqual(len(installs), 1)
            self.assertEqual(cleanup_calls, [cleanup_calls[0]] * 3)
            self.assertTrue(all(row == (self.profile, self.store.device_dir(self.profile), False, False)
                                for row in auth[1:]))
            w.channel.answer(None)
            self.pump(lambda: not w.running)

    def test_uninstall_waits_for_the_same_tv_and_preserves_the_confirmed_removal(self):
        from paramiko import BadHostKeyException
        from cytv.operations import Installer

        old_boot = '00000000-0000-0000-0000-000000000001'
        new_boot = '00000000-0000-0000-0000-000000000002'
        for outcome in ('ready', 'already-online', 'legacy-reconnect', 'timeout', 'same-boot',
                        'cancel', 'changed-tv', 'changed-pin', 'stale-operation', 'root'):
            with self.subTest(outcome=outcome):
                self.store.finish(self.profile)
                if outcome == 'root':
                    self.profile = state.target(self.profile['host'], 'root', 2222)
                    self.store.save(self.profile)
                pin = self.store.device_dir(self.profile) / 'known_hosts'
                pin.write_bytes(b'original pin')
                self.connections.clear()
                cleanup_calls, connections, reads = [], [], []
                started, release = threading.Event(), threading.Event()
                self.addCleanup(release.set)

                def cleanup(installer, pending):
                    cleanup_calls.append(pending['removal_operation'])
                    if len(cleanup_calls) == 1:
                        installer.store.checkpoint(installer.profile, stage='restart-required',
                            removal_reason='restart-required',
                            cleanup_boot_proof=None if outcome in ('root', 'legacy-reconnect') else {'kernel':old_boot},
                            cleanup_boot_id=old_boot if outcome == 'root' else None)
                        return {'restart_required':True}
                    result = {'removed':True, 'verified_clean':True}
                    installer.store.checkpoint(installer.profile, stage='verified-clean',
                                               removal_reason='removal-verified', result=result)
                    installer.store.finish_clean_removal(installer.profile)
                    return result

                class Probe:
                    def run(probe, command, *, timeout):
                        reads.append(command)
                        self.assertEqual(command, 'cat /proc/sys/kernel/random/boot_id')
                        return old_boot if outcome == 'same-boot' or (
                            len(reads) == 1 and outcome != 'already-online') else new_boot

                    def close(probe):
                        pass

                def connect(profile, directory, secret, trust, *, persist):
                    self.assertEqual(profile, self.profile)
                    self.assertEqual(directory, self.store.device_path(self.profile))
                    self.assertFalse(persist)
                    self.assertFalse(trust(None, None))
                    connections.append(profile)
                    started.set()
                    if outcome == 'changed-tv':
                        raise BadHostKeyException(profile['host'], None, None)
                    if outcome == 'cancel':
                        release.wait(2)
                        return Probe()
                    if outcome == 'timeout' or outcome in ('ready', 'legacy-reconnect') and len(connections) == 1:
                        raise TimeoutError('SSH did not answer')
                    return Probe()

                with (patch.object(Installer, 'continue_clean_removal', cleanup),
                      patch('cytv.transport.SSH.connect', side_effect=connect),
                      patch('cytv.gui.REMOVAL_RECONNECT_SECONDS', 0.15 if outcome in ('timeout', 'same-boot') else 2),
                      patch('cytv.recovery.REMOVAL_RECONNECT_INTERVAL', 0.01)):
                    w = self.window()
                    w.start('uninstall', self.profile)
                    self.pump(lambda: w.pending is not None or not w.running)
                    self.assertIsNotNone(w.pending)
                    w.submit('y')
                    self.pump(lambda: started.is_set() or not w.running)
                    self.assertTrue(started.is_set(), 'No background observation started after the restart request')
                    original = self.store.pending(self.profile)
                    if outcome == 'cancel':
                        observed = w.worker
                        self.assertTrue(w.cancel.isEnabled())
                        self.assertEqual(w.cancel.text(), 'Cancel')
                        w.cancel.click()
                        self.assertFalse(w.running)
                        release.set()
                        observed.join(2)
                        self.assertFalse(observed.is_alive())
                        self.app.processEvents()
                        self.assertEqual(connections, [self.profile])
                        self.assertEqual(reads, [])
                    else:
                        self.pump(lambda: not w.running)
                    self.assertEqual(self.store.pending(self.profile), original)
                    self.assertEqual(cleanup_calls, [original['removal_operation']])
                    self.assertEqual(self.remote.calls, [])
                    self.assertEqual(self.connections, [self.profile])

                    if outcome in ('ready', 'already-online', 'legacy-reconnect', 'changed-pin', 'stale-operation', 'root'):
                        action = self.button(w, 'Continue removal')
                        self.assertIsNotNone(action, w.subtitle.text())
                        self.assertEqual(len(reads), {'already-online':1, 'legacy-reconnect':0}.get(outcome, 2))
                        if outcome == 'changed-pin':
                            pin.write_bytes(b'replacement pin')
                        if outcome == 'stale-operation':
                            self.store.finish(self.profile)
                        action.click()
                        self.pump(lambda: w.pending is not None or not w.running)
                        self.assertIsNone(w.pending)
                        if outcome in ('changed-pin', 'stale-operation'):
                            self.assertEqual(self.connections, [self.profile])
                            self.assertEqual(cleanup_calls, [original['removal_operation']])
                            if outcome == 'changed-pin':
                                self.assertEqual(w.failure_help['code'], 'ssh-identity')
                            else:
                                self.assertIn('Removal evidence changed.', w.content.toPlainText())
                                self.assertIsNone(self.store.pending(self.profile))
                        else:
                            self.assertEqual(self.connections, [self.profile] * 2)
                            self.assertEqual(cleanup_calls, [original['removal_operation']] * 2)
                            self.assertEqual(w.title.text(), 'Clean Your TV removal is verified.')
                    else:
                        self.assertIsNone(self.button(w, 'Continue removal'))
                        self.assertIsNotNone(self.button(w, 'Try again'))
                        if outcome == 'changed-tv':
                            self.assertEqual(connections, [self.profile])
                            self.assertEqual(reads, [])
                        if outcome in ('timeout', 'same-boot'):
                            self.assertGreater(len(connections), 1)
                            self.assertIn('Try again', w.subtitle.text())
                    w.close()

    def test_root_reinstall_finalizes_verified_checkpoint_without_touching_the_tv(self):
        import hashlib
        from cytv.operations import Installer
        self.store.finish(self.profile)
        self.profile = state.target('192.0.2.10', 'root')
        self.store.save(self.profile)
        (self.store.device_dir(self.profile) / 'known_hosts').write_bytes(b'original pin')
        digest = hashlib.sha256(json.dumps([None, self.manifest], sort_keys=True).encode()).hexdigest()
        self.store.request_clean_removal(self.profile, root_reinstall_payload=digest)
        self.store.checkpoint(self.profile, stage='verified-clean', result={'removed':True, 'verified_clean':True})
        with patch.object(Installer, 'continue_clean_removal') as cleanup, patch.object(Installer, 'preflight') as preflight:
            w = self.window()
            self.button(w, 'Continue Root reinstallation').click()
            self.pump(lambda: w.pending is not None or not w.running)
            self.assertIsNotNone(w.pending, w.details.toPlainText())
            self.assertEqual(w.pending.title, 'Continue Root installation?')
            self.assertEqual(self.store.root_reinstall(self.profile).stage, 'removed')
            self.assertIsNone(self.store.pending(self.profile))
            w.submit('n')
            self.pump(lambda: not w.running)
            cleanup.assert_not_called()
            preflight.assert_not_called()

    def test_doctor_success_routes_real_cli_result_to_details_and_preserves_selected_tv(self):
        self.store.finish(self.profile)
        w = self.window()
        self.check(w)
        self.assertEqual(w.title.text(), 'Connected to your TV')
        self.assertNotIn('helper_state', w.content.toPlainText())
        self.assertIn('helper_state', w.details.toPlainText())
        self.assertTrue(w.details.isHidden())
        self.button(w, 'Continue setup').click()
        self.pump(lambda: w.pending is not None)
        self.assertEqual(w.selected_profile, self.profile)
        self.assertIn('Connect to check installed versions', w.pending.title)
        w.submit('n')
        self.pump(lambda: not w.running)
        self.assertEqual(w.title.text(), 'Cancelled')
        self.assertNotEqual(w.step_rows[-1].property('state'), 'complete')
        self.assertEqual(self.connections, [self.profile])

    def test_doctor_continues_to_version_review_and_cancel_keeps_tv_unchanged(self):
        self.store.finish(self.profile)
        current = [{'id': 'com.gathin.tvhome', 'version': '1.2.2'},
                   {'id': 'com.local.nativehome', 'version': '0.6.13'}]
        original = self.remote.run

        def run(command, **kwargs):
            if self.remote.installed and 'CYTV_HELPER_IDLE' in command:
                self.remote.calls.append(('run', command))
                return 'CYTV_HELPER_ACTIVE'
            return original(command, **kwargs)

        self.remote.run = run
        for installed, expected in (([], 'Home: Not installed → 1.2.2 (Install)'),
                                    (current, 'Home: 1.2.2 → 1.2.2 (Reinstall)')):
            with self.subTest(installed=bool(installed)):
                self.remote.installed = list(installed)
                self.remote.calls.clear()
                self.connections.clear()
                w = self.window()
                self.check(w)
                self.assertEqual(w.title.text(), 'Connected to your TV')
                self.assertNotIn('packages', w.check_results)
                self.button(w, 'Continue setup').click()
                self.pump(lambda: w.pending is not None)
                self.assertEqual(w.pending.title, 'Connect to check installed versions?')
                w.submit('y')
                self.pump(lambda: w.pending is not None or not w.running)
                self.assertIsNotNone(w.pending, w.content.toPlainText())
                self.assertEqual(w.pending.title, 'Install these versions?')
                self.assertIn(expected, w.content.toPlainText())
                self.button(w, 'No, go back / cancel this operation').click()
                self.pump(lambda: not w.running)
                self.assertEqual(w.title.text(), 'Cancelled')
                self.assertNotEqual(w.step_rows[-1].property('state'), 'complete')
                self.assertEqual(self.connections, [self.profile, self.profile])
                self.assertEqual(self.remote.installed, installed)
                self.assertEqual(self.remote.uploads, {})
                self.assertFalse(any(c[0] == 'luna' and c[1].endswith(('/install', '/remove', '/launch'))
                                     for c in self.remote.calls))
                self.assertIsNone(self.store.pending(self.profile))
                w.close()

    def test_doctor_continues_to_root_reinstall_review_and_cancel_keeps_root(self):
        self.store.finish(self.profile)
        self.profile = state.target('192.0.2.10', 'root', 2222)
        self.store.save(self.profile)
        (self.store.device_dir(self.profile) / 'known_hosts').write_bytes(b'original pin')
        original = self.remote.run

        def run(command, **kwargs):
            if 'deploy.json' in command:
                return '{"stage":"installed-recovery-only"}'
            if 'CYTV_EXISTING_ROOT' in command:
                return 'CYTV_EXISTING_ROOT'
            return original(command, **kwargs)

        self.remote.run = run
        with (patch.object(cli.Installer, 'select_graphics'),
              patch.object(cli.Installer, 'version_summary', return_value=['Root: 1.2.2 → 1.2.2 (Reinstall)'])):
            w = self.window()
            self.check(w)
            self.assertEqual(w.title.text(), 'Connected to your TV', w.details.toPlainText())
            self.button(w, 'Continue setup').click()
            self.pump(lambda: w.pending is not None)
            self.button(w, 'Continue').click()
            self.pump(lambda: w.pending is not None or not w.running)
            self.assertIsNotNone(w.pending, w.content.toPlainText())
            self.assertEqual(w.pending.title, 'Reinstall Root?')
            self.button(w, 'No, go back / cancel this operation').click()
            self.pump(lambda: not w.running)
        self.assertEqual(w.title.text(), 'Cancelled')
        self.assertNotEqual(w.step_rows[-1].property('state'), 'complete')
        self.assertEqual(self.connections, [self.profile, self.profile])
        self.assertIsNone(self.store.pending(self.profile))
        self.assertIsNone(self.store.root_reinstall(self.profile))
        self.assert_no_root_mutation()

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.store = state.Store(self.root)
        self.profile = state.target('192.0.2.10', 'no-root', 9923)
        self.store.save(self.profile)
        (self.store.device_dir(self.profile)/'known_hosts').write_bytes(b'original pin')
        self.store.save(state.target('192.0.2.11', 'no-root'))
        self.store.begin(self.profile, 'uninstall', eim_registered=False)
        self.payload = self.root / 'payload'
        self.payload.mkdir()
        (self.payload / 'fallback.png').write_bytes(b'icon')
        self.manifest = {'files': {}, 'launcher': 'launcher.ipk', 'helper': 'helper.ipk',
                         'home_version': '1.2.2', 'helper_version': '0.6.13',
                         'graphics': {'1920x1080': {'launcher': 'launcher.ipk', 'root': 'root'},
                                      '1280x720': {'launcher': 'launcher-720p.ipk', 'root': 'root-720p'}}}
        for app, name, version in [('com.gathin.tvhome', 'launcher.ipk', '1.2.2'),
                                   ('com.local.nativehome', 'helper.ipk', '0.6.13'),
                                   ('com.gathin.tvhome', 'launcher-720p.ipk', '1.2.2')]:
            (self.payload / name).write_bytes(package.ipk(app, version, {
                'usr/palm/applications/' + app + '/appinfo.json': json.dumps({'id': app, 'version': version, 'resolution': '1280x720' if name == 'launcher-720p.ipk' else '1920x1080'}).encode()}))
            self.manifest['files'][name] = hashlib.sha256((self.payload / name).read_bytes()).hexdigest()
        self.remote = Remote()
        self.remote.close = lambda: None
        original = self.remote.luna
        def luna(uri, payload, **kwargs):
            if uri == 'com.webos.appInstallService/status':
                self.remote.calls.append(('luna', uri, payload))
                return {'returnValue': True, 'status': {'apps': []}}
            return original(uri, payload, **kwargs)
        self.remote.luna = luna
        self.connections = []
        def connect(profile, *args):
            self.connections.append(profile)
            return self.remote
        self.connect = connect
        self.inventory = {'apps': [{'id': 'youtube', 'title': 'YouTube',
                                   'icon': 'data:image/png;base64,AA=='}], 'inputs': []}
        from types import SimpleNamespace
        ssap = SimpleNamespace(key='PRIVATE-PAIRING-KEY', inventory=lambda icon, *, allow_missing_inputs=False: self.inventory)
        for target, kwargs in [
            ('cytv.state.default_dir', {'return_value': self.root}),
            ('cytv.i18n.system_languages', {'return_value': ['en']}),
            ('cytv.cli.package.verify_payload', {'return_value': self.manifest}),
            ('cytv.tv.SSAP', {}),
        ]:
            mock = patch(target, **kwargs)
            result = mock.start()
            self.addCleanup(mock.stop)
            if target == 'cytv.tv.SSAP':
                result.return_value.__enter__.return_value = ssap
        self.addCleanup(i18n.set_language, 'en')

    def pump(self, predicate, *, timeout=5):
        deadline = time.monotonic() + timeout
        while not predicate() and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.005)
        self.assertTrue(predicate())

    def window(self):
        def runner(argv, **kwargs):
            if argv[0] != 'install':
                argv += ['--host', self.profile['host'], '--edition', self.profile['edition'],
                         '--port', str(self.profile['port'])]
            return cli.main(argv + ['--data-dir', str(self.root)],
                            payload_root=self.payload, connect=self.connect, **kwargs)
        w = Wizard(run=runner)
        def close():
            if w.running:
                w.channel.answer(None)
                w.worker.join(5)
                self.pump(lambda: not w.running)
            w.close()
        self.addCleanup(close)
        return w

    def button(self, w, text):
        return next((b for b in w.form.findChildren(QPushButton) if b.text() == text), None)

    def check(self, w, command='doctor'):
        # Explicit initial target; the continuation must retain it with multiple profiles.
        w.start(command)
        if command == 'restore':
            self.pump(lambda: w.pending is not None)
            w.submit('y')
        self.pump(lambda: not w.running)

    def prepare_root_recovery(self, action='activate-root'):
        self.profile = state.target('192.0.2.10', 'root')
        self.store.save(self.profile)
        (self.store.device_dir(self.profile)/'known_hosts').write_bytes(b'original pin')
        self.store.begin(self.profile, action, stage='enable' if action == 'activate-root' else 'removing',
                         requires_updater=True, updates_ready=True, baseline_sha='a'*64,
                         release_sha='b'*64, bundle_sha='c'*64, product_operation='d'*32)
        self.remote.active = {'recovery': {'integrity_verified': True}, 'journal_exists': True,
            'journal': {'state': 'restored'}, 'intent': {'enabled': False, 'phase': 'disabled'},
            'guardian_active': False, 'effective': {'sam_home': 'com.webos.app.home', 'profiles': {
                'defaultApps': {'categories': {'home': 'com.webos.app.home'}},
                'idleApp': {'appId': 'com.webos.app.home'}}}}
        original_run = self.remote.run
        def run(command, **kwargs):
            if 'deploy.json' in command:
                reply = '{"stage":"installed-recovery-only"}'
            elif 'install_driver.py' in command:
                args = shlex.split(command)
                self.assertIn('status', args)
                self.assertIn('--verify-current', args)
                self.assertEqual(args[args.index('--operation') + 1], 'd'*32)
                reply = json.dumps({'operation': 'd'*32, 'state': 'complete', 'current': True,
                    'result': {'baseline_sha': 'a'*64, 'home_changed': False, 'verified': True}})
            elif 'CYTV_ROOT_FILES_OK' in command:
                reply = 'CYTV_ROOT_FILES_OK'
            elif 'CYTV_ACTIVATION_RECOVERABLE' in command:
                reply = 'CYTV_ACTIVATION_RECOVERABLE'
            else:
                return original_run(command, **kwargs)
            self.remote.calls.append(('run', command))
            return reply
        self.remote.run = run
        # Runtime/proof code delivery is covered separately; keep the actual
        # proof readers, CLI, Store, recovery orchestration and Qt bridge here.
        for name, value in (('_python', '/usr/bin/python3'),
                            ('coordinator_code', '/verified/root-updater')):
            fixture = patch.object(cli.Installer, name, return_value=value)
            fixture.start(); self.addCleanup(fixture.stop)
        return self.store.device_dir(self.profile) / 'operation.json'

    def open_root_review(self):
        w = self.window()
        w.start('recover')
        self.pump(lambda: w.pending is not None)
        self.assertEqual(w.pending.default, 'n')
        self.assertTrue(self.button(w, 'No, go back / cancel this operation').isDefault())
        self.button(w, 'Continue').click()
        self.pump(lambda: w.pending is not None)
        return w

    def root_choice(self, w):
        self.assertEqual(w.pending.kind, 'choice')
        self.assertEqual(w.pending.default, '0')
        choices = w.form.findChild(QComboBox)
        self.assertIsNotNone(choices)
        self.assertEqual(choices.currentData(), '0')
        self.assertEqual([choices.itemData(i) for i in range(choices.count())], ['0', '1', '2'])
        self.assertEqual(choices.itemText(choices.findData('2')),
                         'Finish setup with LG Home and Home control off')
        return choices

    def assert_no_root_mutation(self):
        self.assertTrue(self.connections)
        self.assertTrue(all(profile == self.profile for profile in self.connections))
        for call in self.remote.calls:
            self.assertNotEqual(call[0], 'upload')
            if call[0] == 'run':
                self.assertFalse(call[1].endswith((' enable', ' restore', ' uninstall')))
            if call[0] == 'luna':
                self.assertFalse(call[1].endswith(('/install', '/remove', '/launch', '/disable')))

    def test_root_menu_defaults_to_retaining_receipt_without_activation(self):
        receipt = self.prepare_root_recovery()
        before = receipt.read_bytes()
        w = self.open_root_review()
        self.root_choice(w)
        self.button(w, 'Continue').click()  # Actual combo-box default is retain.
        self.pump(lambda: not w.running)
        self.assertEqual(receipt.read_bytes(), before)
        self.assertEqual(list(receipt.parent.glob('recovery-*.json')), [])
        self.assert_no_root_mutation()

    def test_cancelled_recovery_auth_keeps_original_records_and_shows_cancelled(self):
        from cytv.transport import CredentialPrompt
        receipt = self.prepare_root_recovery()
        directory = receipt.parent
        before = {name:(directory/name).read_bytes() for name in ('operation.json','profile.json','known_hosts')}
        def connect(profile, directory, secret, trust, **kwargs):
            secret(CredentialPrompt('Root SSH password (hidden): ', 'root'))
            raise AssertionError('Cancelled authentication must stop before connection')
        self.connect = connect
        w = self.window()
        w.start('recover')
        self.pump(lambda: w.pending is not None)
        self.assertEqual(w.pending.credential_type, 'root')
        self.assertEqual(w.title.text(), 'Root SSH password (hidden)')
        w.channel.answer(None)
        self.pump(lambda: not w.running)
        self.assertEqual(w.title.text(), 'Cancelled')
        self.assertFalse(any(row.property('state') == 'complete' for row in w.step_rows))
        self.assertEqual(before, {name:(directory/name).read_bytes() for name in before})
        self.assertEqual(self.remote.calls, [])

    def test_uninstall_zero_exit_without_verified_cleanup_is_review(self):
        w = self.window()
        w.command = 'uninstall'
        w.receive('done', 0)
        self.assertEqual(w.title.text(), 'Removal is not finished yet.')
        self.assertEqual(w.badge.text(), w.title.text())
        self.assertIn('Removal could not be verified.', w.subtitle.text())
        w.receive('recovery-plan', {'state':'waiting','disposition':'clean-removal',
                                  'summary':'Removal has been requested.',
                                  'next_step':'Connect to the TV to continue cleanup.'})
        w.receive('done', 130)
        self.assertEqual(w.title.text(), 'Cancelled')
        self.assertEqual(w.badge.text(), 'Cancelled')

    def test_explicit_uninstall_requires_clean_disposition_and_true_proof(self):
        for disposition in (None, 'home-off', 'clean-removal'):
            for proof in (None, False, True):
                with self.subTest(disposition=disposition, verified_clean=proof):
                    def runner(argv, **kwargs):
                        plan = {'state':'complete', 'removed':True, 'summary':'Completion received',
                                'next_step':'Read the result below before continuing.'}
                        if disposition is not None: plan['disposition'] = disposition
                        if proof is not None: plan['verified_clean'] = proof
                        kwargs['write'].recovery_plan(plan)
                        return 0
                    w = self.window()
                    w.run = runner
                    w.start('uninstall', self.profile)
                    self.pump(lambda: not w.running)
                    complete = disposition == 'clean-removal' and proof is True
                    self.assertEqual(w.title.text(), 'Completion received' if complete else 'Removal is not finished yet.')
                    self.assertEqual(w.badge.text(), w.title.text())
                    w.close()

    def test_root_clean_removal_cli_completes_only_after_device_proof(self):
        from tests.cytv.clean_removal_fixture import prepare
        original = prepare(self)
        w = self.window()
        w.start('uninstall')
        self.pump(lambda: w.pending is not None)
        self.assertIn('saved preferences will be removed.', w.content.toPlainText())
        w.submit('y')
        self.pump(lambda: not w.running)
        self.assertEqual(w.title.text(), 'Clean Your TV removal is verified.', w.content.toPlainText())
        self.assertTrue(w.recovery_plan['verified_clean'])
        self.assertIsNone(self.store.pending(self.profile))
        self.assertIsNone(self.store.root_reinstall(self.profile))
        self.assertIsNone(self.button(w, 'Continue Root reinstallation'))
        self.assertTrue(self.button(w, 'Back to start').isDefault())
        self.assertFalse(self.button(w, 'Set up my TV').isDefault())
        self.assertEqual(self.connections, [self.profile])
        self.assertEqual(self.device_removals, ['d'*32])
        receipt = json.loads((self.store.device_dir(self.profile)/'clean-removal.json').read_bytes())
        self.assertEqual(receipt['previous'], json.loads(original))
        self.assertIsNotNone(w.report)
        self.assertEqual(json.loads(w.report.read_bytes())['frontend'], 'desktop')

    def test_recover_clean_removal_publishes_proof_accepted_by_strict_ui(self):
        from tests.cytv.clean_removal_fixture import prepare
        self.store.finish(self.profile)
        original=prepare(self)
        self.store.request_clean_removal(self.profile)
        w=self.window()
        w.start('recover',self.profile)
        self.pump(lambda:w.pending is not None)
        self.assertIn('Check recovery options?',w.pending.label)
        w.submit('y')
        self.pump(lambda:w.pending is not None and 'Continue removing' in w.pending.label)
        w.submit('y')
        self.pump(lambda:not w.running)
        self.assertIsNone(self.store.pending(self.profile))
        self.assertEqual(self.device_removals,['d'*32])
        receipt=json.loads((self.store.device_dir(self.profile)/'clean-removal.json').read_bytes())
        self.assertEqual(receipt['previous'],json.loads(original))
        self.assertEqual(w.title.text(),'Clean Your TV removal is verified.',w.content.toPlainText())
        self.assertIs(w.recovery_plan.get('removed'),True)
        self.assertIs(w.recovery_plan.get('verified_clean'),True)
        self.assertIsNot(w.recovery_plan.get('restart_required'),True)
        self.assertIsNone(self.button(w,'Try again'))
        setup = self.button(w, 'Set up my TV')
        self.assertIsNotNone(setup)
        self.assertEqual(self.connections, [self.profile])
        setup.click()
        self.pump(lambda: w.pending is not None)
        self.assertEqual(w.selected_profile, self.profile)
        self.assertEqual(w.pending.title, 'Connect to check installed versions?')
        w.submit('n')
        self.pump(lambda: not w.running)
        self.assertEqual(w.title.text(), 'Cancelled')
        self.assertEqual(self.connections, [self.profile])
        self.assertEqual(self.device_removals, ['d'*32])

    def test_cleanup_reviews_recovery_even_with_old_advisory_actions(self):
        def runner(argv, **kwargs):
            write = kwargs['write']
            write.recovery(self.profile)
            write.recovery_plan({'state':'blocked','disposition':'clean-removal',
                'summary':'Removal is still in progress.','next_step':'Continue the remaining cleanup for this TV.',
                'actions':['continue-removal','retain-evidence'],
                'removal':{'stage':'private-cleanup','reason':'private-cleanup-incomplete'}})
            return 2
        w = self.window()
        w.run = runner
        w.start('uninstall', self.profile)
        self.pump(lambda: not w.running)
        self.assertEqual(w.title.text(), 'Finish Clean Your TV cleanup')
        self.assertIsNone(self.button(w, 'Set up my TV'))
        self.assertNotEqual(w.title.property('state'), 'error')
        self.assertIn('Verifying removal…', w.subtitle.text())
        self.assertIn('Final cleanup could not be verified.', w.subtitle.text())
        self.assertIsNone(self.button(w, 'Try again'))
        self.assertIsNotNone(self.button(w, 'Review recovery options'))
        w.recovery_plan['actions'] = ['retain-evidence']
        w.receive('done', 2)
        self.assertIsNone(self.button(w, 'Try again'))
        self.assertIsNotNone(self.button(w, 'Review recovery options'))

    def test_recovery_review_finishes_existing_root_private_cleanup(self):
        from tests.cytv.clean_removal_fixture import prepare

        outcomes = iter(('cleanup-check-failed', 'complete'))
        prepare(self, lambda: next(outcomes))
        # The saved removal predates this installer session, as in #588.
        self.store.request_clean_removal(self.profile)
        self.store.checkpoint(self.profile, stage='private-cleanup', removal_reason='cleanup-check-failed')
        original = self.store.pending(self.profile)
        w = self.window()
        w.start('uninstall', self.profile)
        self.pump(lambda: not w.running or w.pending is not None)
        self.assertIsNone(w.pending, 'An existing cleanup must not ask for approval again')
        self.assertEqual(w.title.text(), 'Finish Clean Your TV cleanup')

        review = self.button(w, 'Review recovery options')
        self.assertIsNotNone(review)
        review.click()
        self.pump(lambda: w.pending is not None)
        self.assertIn('Check recovery options?', w.pending.label)
        self.assertEqual(self.device_removals, [original['product_operation']])
        w.submit('y')
        self.pump(lambda: w.pending is not None and 'Continue removing' in w.pending.label)
        self.assertEqual(self.device_removals, [original['product_operation']])
        w.submit('y')
        self.pump(lambda: not w.running)

        self.assertIsNone(w.pending)
        self.assertEqual(w.title.text(), 'Clean Your TV removal is verified.', w.content.toPlainText())
        self.assertEqual(self.device_removals, [original['product_operation']] * 2)
        self.assertIsNone(self.store.pending(self.profile))
        receipt = json.loads((self.store.device_dir(self.profile) / 'clean-removal.json').read_bytes())
        self.assertEqual(receipt['removal_operation'], original['removal_operation'])
        self.assertTrue(receipt['result']['verified_clean'])

    def test_root_partial_cleanup_shows_current_phase_and_retains_original_failure(self):
        from tests.cytv.clean_removal_fixture import prepare
        original = prepare(self, 'partial')
        w = self.window()
        w.start('uninstall')
        self.pump(lambda: w.pending is not None)
        w.submit('y')
        self.pump(lambda: not w.running)
        self.assertEqual(w.title.text(), 'Finish Clean Your TV cleanup')
        self.assertNotEqual(w.title.property('state'), 'error')
        self.assertEqual(self.store.pending(self.profile)['stage'], 'private-cleanup')
        self.assertEqual(self.store.pending(self.profile)['previous'], json.loads(original))
        self.assertIn('Verifying removal…', w.subtitle.text())
        self.assertIn('Final cleanup could not be verified.', w.subtitle.text())
        self.assertEqual(w.recovery_profile, self.profile)
        report = json.loads(w.report.read_bytes())
        self.assertEqual(report['frontend'], 'desktop')
        self.assertEqual(report['first_failure']['phase'], 'install-packages')
        self.assertEqual(report['first_failure']['reason_code'], 'unknown')
        self.assertNotIn('PRIVATE ORIGINAL ERROR', w.report.read_text())

    def test_root_home_off_is_directly_selectable_and_declining_keeps_receipt(self):
        receipt = self.prepare_root_recovery()
        before = receipt.read_bytes()
        w = self.open_root_review()
        choices = self.root_choice(w)
        choices.setCurrentIndex(choices.findData('2'))
        self.button(w, 'Continue').click()
        self.pump(lambda: w.pending is not None)
        self.assertIn('Home control off?', w.pending.label)
        self.assertEqual(w.pending.default, 'n')
        no = self.button(w, 'No, go back / cancel this operation')
        self.assertTrue(no.isDefault())
        self.assertFalse(self.button(w, 'Continue').isDefault())
        no.click()
        self.pump(lambda: not w.running)
        self.assertEqual(receipt.read_bytes(), before)
        self.assertEqual(list(receipt.parent.glob('recovery-*.json')), [])
        self.assert_no_root_mutation()

    def test_root_home_off_confirmation_archives_original_and_completes(self):
        receipt = self.prepare_root_recovery()
        original = json.loads(receipt.read_bytes())
        w = self.open_root_review()
        choices = self.root_choice(w)
        choices.setCurrentIndex(choices.findData('2'))
        self.button(w, 'Continue').click()
        self.pump(lambda: w.pending is not None)
        self.assertIn('Home control off?', w.pending.label)
        self.assertEqual(w.pending.default, 'n')
        self.button(w, 'Continue').click()
        self.pump(lambda: not w.running)
        saved = [json.loads(path.read_bytes()) for path in receipt.parent.glob('recovery-*.json')]
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]['action'], 'finish-root-setup-disabled')
        self.assertEqual(saved[0]['previous'], original)
        self.assertFalse(receipt.exists())
        self.assertIn('Root setup finished with LG Home', w.content.toPlainText())
        self.assertEqual(w.title.text(), 'Root setup finished with LG Home and Home control off.')
        self.assertEqual(w.badge.text(), w.title.text())
        self.assert_no_root_mutation()

    def test_root_reconciliation_defaults_no_then_archives_before_explicit_clear(self):
        receipt = self.prepare_root_recovery('uninstall')
        before = receipt.read_bytes()
        w = self.open_root_review()
        self.assertIn('Finish the verified recovery record?', w.pending.label)
        self.assertEqual(w.pending.kind, 'confirm')
        self.assertEqual(w.pending.default, 'n')
        self.assertEqual(receipt.read_bytes(), before)
        self.assertEqual(list(receipt.parent.glob('recovery-*.json')), [])
        no = self.button(w, 'No, go back / cancel this operation')
        self.assertTrue(no.isDefault())
        no.click()
        self.pump(lambda: not w.running)
        self.assertEqual(receipt.read_bytes(), before)
        self.assertEqual(list(receipt.parent.glob('recovery-*.json')), [])

        w = self.open_root_review()
        original_finish = state.Store.finish
        finishes = []
        def finish(store, profile):
            self.assertEqual(receipt.read_bytes(), before)
            saved = [json.loads(path.read_bytes()) for path in receipt.parent.glob('recovery-*.json')]
            self.assertEqual(len(saved), 1)
            self.assertEqual(saved[0]['action'], 'reconcile-recovery')
            self.assertEqual(saved[0]['reason'], 'product-removal-verified')
            self.assertEqual(saved[0]['previous'], json.loads(before))
            finishes.append(profile)
            return original_finish(store, profile)
        with patch.object(state.Store, 'finish', finish):
            self.button(w, 'Continue').click()
            self.pump(lambda: not w.running)
        self.assertEqual(finishes, [self.profile])
        self.assertFalse(receipt.exists())
        self.assertIn('Original evidence was archived', w.content.toPlainText())
        self.assert_no_root_mutation()

    def test_status_doctor_and_restore_offer_recovery_without_mutating_the_receipt(self):
        for command in ('status', 'doctor', 'restore'):
            with self.subTest(command=command):
                w = self.window()
                self.check(w, command)
                action = self.button(w, 'Review recovery options')
                self.assertIsNotNone(action)
                self.assertTrue(action.isDefault())
                self.assertEqual(self.store.pending(self.profile)['stage'], 'pending')
                self.assertFalse(any(c[0] == 'upload' for c in self.remote.calls))
                w.close()

    def test_interrupted_install_uses_the_same_guarded_recovery_journey(self):
        self.store.finish(self.profile)
        self.store.begin(self.profile, 'install')
        self.test_recovery_uses_same_tv_and_default_no_then_stops_after_verified_removal()

    def test_interrupted_install_recovery_offers_removal_when_package_status_is_denied(self):
        self.store.finish(self.profile)
        self.store.begin(self.profile, 'install', expected={'saved': 'proof'})
        original = self.store.pending(self.profile)
        status_uri = 'com.webos.appInstallService/status'
        luna = self.remote.luna

        def deny_status(uri, payload, **kwargs):
            if uri == status_uri:
                self.remote.calls.append(('luna', uri, payload))
                raise TVRejected('Denied', {'returnValue': False, 'errorCode': -1}, uri)
            return luna(uri, payload, **kwargs)

        self.remote.luna = deny_status
        w = self.window()
        self.check(w)
        self.button(w, 'Review recovery options').click()
        self.pump(lambda: w.pending is not None)
        w.submit('y')
        self.pump(lambda: w.pending is not None)
        self.assertIn('Remove remaining', w.pending.label)
        self.assertEqual(w.pending.default, 'n')
        w.submit('n')
        self.pump(lambda: not w.running)

        self.assertEqual(self.store.pending(self.profile), original)
        self.assertEqual(sum(c[1] == status_uri for c in self.remote.calls), 1)
        self.assertFalse(any(c[0] == 'upload' or c[1].endswith(('/dev/remove', '/dev/install'))
                             for c in self.remote.calls))

    def test_declining_interrupted_install_recovery_retains_original_receipt(self):
        self.store.finish(self.profile)
        self.store.begin(self.profile, 'install', expected={'saved': 'proof'})
        original = self.store.pending(self.profile)
        self.test_declining_recovery_retains_receipt_and_does_not_offer_automatic_retry()
        self.assertEqual(self.store.pending(self.profile), original)

    def test_recovery_uses_same_tv_and_default_no_then_stops_after_verified_removal(self):
        self.remote.installed = [{'id': 'com.local.nativehome', 'version': '0.6.13'},
                                 {'id': 'com.gathin.tvhome', 'version': '1.2.2'}]
        original = self.remote.luna
        def remove(uri, payload, **kwargs):
            if uri == 'com.webos.appInstallService/dev/remove':
                self.remote.installed = [app for app in self.remote.installed if app['id'] != payload['id']]
            return original(uri, payload, **kwargs)
        self.remote.luna = remove
        w = self.window()
        self.check(w)
        self.button(w, 'Review recovery options').click()
        self.assertEqual(w.rail_title.text(), 'Review recovery options')
        self.pump(lambda: w.pending is not None)
        w.submit('y')  # Connect to check this TV.
        self.pump(lambda: w.pending is not None)
        self.assertIn('Remove remaining', w.pending.label)
        self.assertEqual(w.pending.default, 'n')
        self.assertIsNotNone(self.button(w, 'Continue'))
        self.assertFalse(any(c[0] == 'upload' for c in self.remote.calls))
        w.submit('y')
        self.pump(lambda: not w.running)
        self.assertEqual(w.title.text(), w.recovery_plan['summary'], w.content.toPlainText())
        self.assertIsNone(self.store.pending(self.profile))
        self.assertTrue(all(p == self.profile for p in self.connections))
        calls = [c for c in self.remote.calls if c[0] == 'luna']
        restored = next(i for i,c in enumerate(calls) if c[1].endswith('/launch') and c[2]['id'] == 'com.webos.app.home')
        removals = [(i,c[2]['id']) for i,c in enumerate(calls) if c[1].endswith('/dev/remove')]
        installs = [(i,c[2]['id']) for i,c in enumerate(calls) if c[1].endswith('/install')]
        self.assertEqual([app for _,app in removals], ['com.local.nativehome', 'com.gathin.tvhome'])
        self.assertEqual(installs, [])
        self.assertLess(restored, removals[0][0])
        self.assertFalse(any(c[0] == 'upload' for c in self.remote.calls))

    def test_no_root_uninstall_connection_loss_keeps_intent_before_device_work(self):
        from cytv import diagnostics
        self.store.finish(self.profile)
        self.store.begin(self.profile, 'install', stage='pending', components={})
        original = self.store.pending(self.profile)
        first_report = diagnostics.create_report(self.store, 'install', self.profile, 'install-packages', Exception('PRIVATE FIRST FAILURE'))
        first = json.loads(first_report.read_bytes())['first_failure']
        def disconnected(profile, *args, **kwargs):
            self.connections.append(profile)
            raise TimeoutError('PRIVATE CONNECTION')
        self.connect = disconnected
        w = self.window()
        w.start('uninstall')
        self.pump(lambda: w.pending is not None)
        w.submit('y')
        self.pump(lambda: not w.running)
        self.assertEqual(w.title.text(), 'Check the TV connection to continue removal')
        self.assertIsNotNone(self.button(w, 'Save diagnostic report…'))
        pending = self.store.pending(self.profile)
        self.assertEqual(pending['recovery_protocol'], 'clean-removal-v1')
        self.assertEqual(pending['stage'], 'requested')
        self.assertEqual(pending['previous'], original)
        self.assertEqual(self.remote.calls, [])
        report = json.loads(w.report.read_bytes())
        self.assertEqual(report['frontend'], 'desktop')
        original_failure = self.store.device_dir(self.profile)/'diagnostic-failures'/(original['diagnostic_id']+'.json')
        self.assertEqual(json.loads(original_failure.read_bytes()), first)
        self.assertEqual(report['guidance']['code'], 'ssh-timeout')
        self.assertNotIn('PRIVATE', w.report.read_text())

    def test_unstarted_removal_gui_recovers_without_monitor_permission(self):
        original = self.remote.luna
        def deny_monitor(uri, payload, **kwargs):
            if uri == 'com.webos.appInstallService/status':
                raise TVRejected('Denied', {'returnValue': False, 'errorCode': -1}, uri)
            return original(uri, payload, **kwargs)
        self.remote.luna = deny_monitor
        self.test_recovery_uses_same_tv_and_default_no_then_stops_after_verified_removal()

    def test_failed_recovery_offers_original_failure_report_without_retry_or_install(self):
        if self.store.pending(self.profile)['action'] == 'uninstall':
            self.store.checkpoint(self.profile, stage='removing')
        before = self.store.pending(self.profile)
        w = self.window()
        self.check(w)
        doctor_report = w.report
        original = self.remote.luna
        def reject(uri, payload, **kwargs):
            if uri == 'com.webos.appInstallService/status':
                self.remote.calls.append(('luna', uri, payload))
                error=TVRejected('TV rejected the operation. Run cytv doctor; no automatic retry was attempted.', {'returnValue': False, 'errorCode': -1,
                    'errorText': 'PRIVATE-DIAGNOSTICS'}, uri)
                error.contract_events=[{'schema':1,'component':'storage','operation':'inspect','phase':'read',
                    'field':'apps','expected':'single-regular-file','actual':{'mode':511},'decision':'refuse','count':1}]
                raise error
            return original(uri, payload, **kwargs)
        self.remote.luna = reject
        self.button(w, 'Review recovery options').click()
        self.pump(lambda: w.pending is not None)
        w.submit('y')
        self.pump(lambda: not w.running)
        self.assertEqual(w.title.text(), 'Review recovery options')
        self.assertNotEqual(w.report, doctor_report)
        report = json.loads(w.report.read_text())
        self.assertEqual(report['phase'], 'recover')
        self.assertEqual(report['luna']['operation'], 'package-status')
        self.assertTrue(any(e['field']=='apps' for e in report['contract_events']))
        self.assertTrue(report['trace'])
        for private in ('PRIVATE-DIAGNOSTICS', 'PRIVATE-PAIRING-KEY', '192.0.2.10'):
            self.assertNotIn(private, w.report.read_text())
        self.assertEqual(self.store.pending(self.profile), before)
        self.assertEqual(len([c for c in self.remote.calls if c[1] == 'com.webos.appInstallService/status']), 1)
        self.assertFalse(any(c[0] == 'upload' for c in self.remote.calls))
        self.assertNotIn('cytv doctor', w.content.toPlainText())
        save = self.button(w, 'Save diagnostic report…')
        self.assertTrue(save.isDefault())
        self.assertIsNone(self.button(w, 'Review recovery options'))
        destination = self.root / 'saved.json'
        with patch('cytv.gui.QFileDialog.getSaveFileName', return_value=(str(destination), 'JSON (*.json)')):
            save.click()
        self.assertEqual(destination.read_bytes(), w.report.read_bytes())

    def test_declining_recovery_retains_receipt_and_does_not_offer_automatic_retry(self):
        w = self.window()
        self.check(w, 'status')
        self.button(w, 'Review recovery options').click()
        self.pump(lambda: w.pending is not None)
        w.submit('n')
        self.pump(lambda: not w.running)
        self.assertIsNotNone(self.store.pending(self.profile))
        self.assertEqual(w.badge.text(), 'Review recovery options')
        self.assertFalse(any(row.property('state') == 'complete' for row in w.step_rows))
        self.assertFalse(any(c[0] == 'upload' or c[1] == 'com.webos.appInstallService/status' for c in self.remote.calls))

    def test_install_collects_explicit_home_result_without_reinstalling(self):
        self.store.finish(self.profile)
        launched = False
        original_luna, original_run = self.remote.luna, self.remote.run
        def luna(uri, payload, **kwargs):
            nonlocal launched
            if uri.endswith('/launch') and payload['id'] == 'com.local.nativehome':
                launched = True
            return original_luna(uri, payload, **kwargs)
        def run(command, **kwargs):
            if launched and 'CYTV_HELPER_IDLE' in command:
                return 'CYTV_HELPER_ACTIVE'
            return original_run(command, **kwargs)
        self.remote.luna, self.remote.run = luna, run
        w = self.window()
        w.start('install', self.profile)
        for _ in range(2):
            self.pump(lambda: w.pending is not None)
            w.submit('y')
        self.pump(lambda: w.pending is not None)
        self.assertEqual(w.pending.label, debloat.SELECT)
        self.remote.root = False
        with patch.object(debloat, 'SSAP', side_effect=TimeoutError):
            w.submit('["homePromotion"]')
            self.pump(lambda: w.pending is not None)
            self.assertEqual(w.pending.label, debloat.REVIEW, w.content.toPlainText())
        w.submit('1')
        self.pump(lambda: w.pending is not None)
        self.assertEqual(w.pending.label, install_settings.PROMPT)
        w.submit('{}')  # Skip optional customization.
        self.pump(lambda: w.pending is not None)
        self.assertIn('Home button result', w.pending.label)
        self.assertEqual(w.pending.default, '4')
        self.assertEqual([key for key, _, _ in w.pending.options], ['1','2','3','4'])
        self.assertEqual(w.check_results['packages']['status'], 'pass')
        self.assertEqual(w.check_results['home-button']['status'], 'unknown')
        w.submit('2')
        self.pump(lambda: not w.running)
        self.assertIsNone(self.store.pending(self.profile))
        self.assertEqual(w.title.text(), 'Review TV checks')
        self.assertTrue(self.button(w, 'Save diagnostic report…').isDefault())
        report = json.loads(w.report.read_text())
        self.assertIsNone(report['error_type'])
        self.assertEqual(report['debloat'], {'homePromotion': 'pairing-unavailable'})
        self.assertEqual(report['tv']['setup_outcome']['home_button'], 'not-working')
        self.assertEqual(report['checks']['packages'], 'pass')
        self.assertEqual(report['checks']['startup'], 'pass')
        self.assertEqual(report['tv']['setup_outcome']['startup'], 'process-observed')
        self.assertEqual(report['checks']['home-button'], 'fail')
        installs = [c for c in self.remote.calls if c[0]=='luna' and c[1].endswith('/install')]
        self.assertEqual(len(installs),2)
        self.assertTrue(all(profile == self.profile for profile in self.connections))
        self.assertNotIn('PRIVATE-PAIRING-KEY', w.report.read_text())
        self.assertEqual(report['tv']['setup_outcome']['home_destination'], 'lg-home')
        self.assertEqual(w.content.toPlainText().count('physical TV remote'), 1)
        self.assertIn('Open an app or TV input', w.content.toPlainText())
        original_report = w.report
        connections = list(self.connections)
        calls = list(self.remote.calls)
        self.button(w, 'Home button diagnostics').click()
        self.assertEqual(w.title.text(), 'Home button diagnostics')
        self.assertIn('already recorded', w.subtitle.text())
        self.assertEqual(w.report, original_report)
        self.assertIsNone(w.pending)
        self.assertEqual(self.connections, connections)
        self.assertEqual(self.remote.calls, calls)


    def test_skipped_home_check_is_saved_as_untested_after_successful_packages(self):
        self.store.finish(self.profile)
        w = self.window(); w.start('install', self.profile)
        for _ in range(2):
            self.pump(lambda: w.pending is not None); w.submit('y')
        self.pump(lambda: w.pending is not None)
        self.assertEqual(w.pending.label, debloat.SELECT)
        w.submit('[]')  # Skip optional Debloat.
        self.pump(lambda: w.pending is not None)
        self.assertEqual(w.pending.label, install_settings.PROMPT)
        w.submit('{}')  # Skip optional customization.
        self.pump(lambda: w.pending is not None)
        w.submit('')
        self.pump(lambda: not w.running)
        report = json.loads(w.report.read_text())
        self.assertEqual(report['tv']['setup_outcome']['home_button'], 'not-tested')
        self.assertEqual(w.check_results['home-button']['status'], 'unknown')
        self.assertEqual(w.title.text(), 'Review TV checks')
        self.assertIsNone(self.store.pending(self.profile))

    def test_delegated_recovery_hides_install_steps_and_names_actual_action(self):
        w = self.window()
        w.command = 'install'
        w.steps.show()
        w.receive('recovery-plan', {'state':'review', 'summary':'Review recovery options',
                                  'next_step':'Recovery data kept. Installation has not restarted.'})
        self.assertTrue(w.steps.isHidden())
        self.assertEqual(w.rail_title.text(), 'Review recovery options')
        w.receive('done', 0)
        self.assertEqual(w.title.text(), 'Review recovery options')

    def test_report_event_offers_save_even_without_a_diagnostic_filename_in_log_text(self):
        w = self.window()
        report = self.root / 'failure.json'
        report.write_text('{"phase":"uninstall"}')
        w.receive('report', str(report))
        w.receive('done', 2)
        save = self.button(w, 'Save diagnostic report…')
        self.assertIsNotNone(save)
        self.assertTrue(save.isDefault())
        self.assertEqual(w.report, report)
        with patch('cytv.gui.QFileDialog.getSaveFileName', return_value=('', '')):
            save.click()
        self.assertEqual(w.report.read_text(), '{"phase":"uninstall"}')
        with patch('cytv.gui.QFileDialog.getSaveFileName', return_value=(str(self.root / 'missing' / 'copy.json'), '')), \
                patch.object(w, 'error_dialog') as error:
            save.click()
        error.assert_called_once()
        self.assertTrue(w.report.is_file())

    def test_no_recovery_offer_for_completed_removal_or_other_pending_operations(self):
        for action, stage in ((None, None), ('unknown', 'pending')):
            with self.subTest(action=action, stage=stage):
                if self.store.pending(self.profile):
                    self.store.finish(self.profile)
                if action:
                    self.store.begin(self.profile, action, stage=stage)
                w = self.window()
                self.check(w, 'status')
                self.assertEqual(self.button(w, 'Review recovery options') is not None, action is not None)
                self.assertFalse(any(c[0] == 'upload' for c in self.remote.calls))
                w.close()

    def test_retained_removing_journal_offers_explicit_recovery_without_mutation(self):
        # Empty app inventories no longer prove an unfinished uninstall terminal.
        self.store.finish(self.profile)
        self.store.begin(self.profile, 'uninstall', stage='removing')
        before = self.store.pending(self.profile)
        w = self.window()
        self.check(w, 'status')
        self.assertIsNotNone(self.button(w, 'Review recovery options'))
        self.assertEqual(self.store.pending(self.profile), before)
        self.assertFalse(any(c[0] == 'upload' or c[1] in (
            'com.webos.appInstallService/dev/install', 'com.webos.appInstallService/dev/remove')
            for c in self.remote.calls))
        w.close()

    def test_missing_report_shows_help_and_cannot_reuse_a_previous_attempts_report(self):
        w = self.window()
        self.check(w)
        previous_report = w.report
        def reject(*args, **kwargs):
            raise OSError('PRIVATE-FAILURE')
        self.connect = reject
        with patch('cytv.diagnostics.create_report', side_effect=OSError('PRIVATE-PATH')):
            self.button(w, 'Review recovery options').click()
            self.pump(lambda: not w.running)
        self.assertTrue(previous_report.is_file())
        self.assertIsNone(w.report)
        self.assertIsNone(self.button(w, 'Save diagnostic report…'))
        self.assertIn('could not be created', w.subtitle.text())
        self.assertIsNotNone(self.button(w, 'Open an issue'))
        self.assertNotIn('PRIVATE-', w.content.toPlainText())

    def test_contextual_connection_confirmation_does_not_offer_ssh_trust_details(self):
        from cytv.desktop import Prompt
        w = self.window()
        w.show_prompt(Prompt('Connect to check installed versions? [Y/n]: '))
        self.assertIsNone(self.button(w, 'Connection details'))
        self.assertIsNone(self.button(w, 'Connect and remember'))
        self.assertIsNotNone(self.button(w, 'Continue'))
        w.show_prompt(Prompt('Connect and remember this TV? [Y/n]: '))
        self.assertIsNotNone(self.button(w, 'Connection details'))
        self.assertIsNotNone(self.button(w, 'Connect and remember'))

