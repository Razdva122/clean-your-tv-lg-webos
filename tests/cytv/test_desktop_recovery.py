"""Exercise the desktop recovery journey with real CLI/state and simulated TV IO."""
import json
import hashlib
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from cytv import cli, package, state, i18n
from cytv.errors import TVRejected
from tests.cytv.test_operations import Remote
try:
    from PySide6.QtWidgets import QApplication, QPushButton
    from cytv.gui import Wizard
    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, 'Desktop build dependencies are optional for CLI tests')
class DesktopRecoveryTests(unittest.TestCase):
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
        ssap = SimpleNamespace(key='PRIVATE-PAIRING-KEY', inventory=lambda icon: self.inventory)
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

    def pump(self, predicate):
        deadline = time.monotonic() + 5
        while not predicate() and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.005)
        self.assertTrue(predicate())

    def window(self):
        def runner(argv, **kwargs):
            if argv[0] != 'install':
                argv += ['--host', self.profile['host'], '--edition', 'no-root', '--port', '9923']
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

    def test_interrupted_install_recovery_checks_tv_idle_and_saves_failure_without_reinstall(self):
        self.store.finish(self.profile)
        self.store.begin(self.profile, 'install', expected={'saved': 'proof'})
        original = self.store.pending(self.profile)
        self.test_failed_recovery_offers_original_failure_report_without_retry_or_install()
        self.assertEqual(self.store.pending(self.profile), original)

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
        self.assertEqual(w.title.text(), 'Review recovery options', w.content.toPlainText())
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

    def test_failed_recovery_offers_original_failure_report_without_retry_or_install(self):
        w = self.window()
        self.check(w)
        doctor_report = w.report
        original = self.remote.luna
        def reject(uri, payload, **kwargs):
            if uri == 'com.webos.appInstallService/status':
                self.remote.calls.append(('luna', uri, payload))
                raise TVRejected('TV rejected the operation. Run cytv doctor; no automatic retry was attempted.', {'returnValue': False, 'errorCode': -1,
                    'errorText': 'PRIVATE-DIAGNOSTICS'}, uri)
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
        self.assertTrue(report['trace'])
        for private in ('PRIVATE-DIAGNOSTICS', 'PRIVATE-PAIRING-KEY', '192.0.2.10'):
            self.assertNotIn(private, w.report.read_text())
        self.assertEqual(self.store.pending(self.profile)['stage'], 'pending')
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
        self.assertIn('Home button result', w.pending.label)
        self.assertEqual(w.pending.default, '3')
        self.assertEqual([key for key, _, _ in w.pending.options], ['1','2','3'])
        self.assertEqual(w.check_results['packages']['status'], 'pass')
        self.assertEqual(w.check_results['home-button']['status'], 'unknown')
        w.submit('2')
        self.pump(lambda: not w.running)
        self.assertIsNone(self.store.pending(self.profile))
        self.assertEqual(w.title.text(), 'Review TV checks')
        self.assertTrue(self.button(w, 'Save diagnostic report…').isDefault())
        report = json.loads(w.report.read_text())
        self.assertIsNone(report['error_type'])
        self.assertEqual(report['tv']['setup_outcome']['home_button'], 'not-working')
        self.assertEqual(report['checks']['packages'], 'pass')
        self.assertEqual(report['checks']['startup'], 'pass')
        self.assertEqual(report['tv']['setup_outcome']['startup'], 'process-observed')
        self.assertEqual(report['checks']['home-button'], 'fail')
        installs = [c for c in self.remote.calls if c[0]=='luna' and c[1].endswith('/install')]
        self.assertEqual(len(installs),2)
        self.assertTrue(all(profile == self.profile for profile in self.connections))
        self.assertNotIn('PRIVATE-PAIRING-KEY', w.report.read_text())

    def test_skipped_home_check_is_saved_as_untested_after_successful_packages(self):
        self.store.finish(self.profile)
        w = self.window(); w.start('install', self.profile)
        for _ in range(2):
            self.pump(lambda: w.pending is not None); w.submit('y')
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

