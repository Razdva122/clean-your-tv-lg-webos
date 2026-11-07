"""Exercise the desktop recovery journey with real CLI/state and simulated TV IO."""
import json
import hashlib
import os
import shlex
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
    from PySide6.QtWidgets import QApplication, QComboBox, QPushButton
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
        self.assertIn('Removal could not be confirmed.', w.subtitle.text())
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
        w.submit('y')
        self.pump(lambda: not w.running)
        self.assertEqual(w.title.text(), 'Clean Your TV removal is verified.', w.content.toPlainText())
        self.assertTrue(w.recovery_plan['verified_clean'])
        self.assertIsNone(self.store.pending(self.profile))
        self.assertEqual(self.device_removals, ['d'*32])
        receipt = json.loads((self.store.device_dir(self.profile)/'clean-removal.json').read_bytes())
        self.assertEqual(receipt['previous'], json.loads(original))
        self.assertIsNotNone(w.report)
        self.assertEqual(json.loads(w.report.read_bytes())['frontend'], 'desktop')

    def test_recover_clean_removal_publishes_proof_accepted_by_strict_ui(self):
        from tests.cytv.clean_removal_fixture import prepare
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

    def test_cleanup_retry_rechecks_same_goal_even_with_old_advisory_actions(self):
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
        self.assertEqual(w.title.text(), 'Removal is not finished yet.')
        self.assertIn('Removing private setup data…', w.subtitle.text())
        self.assertIn('Some project files remain.', w.subtitle.text())
        self.assertIsNotNone(self.button(w, 'Try again'))
        w.recovery_plan['actions'] = ['retain-evidence']
        w.receive('done', 2)
        self.assertIsNotNone(self.button(w, 'Try again'))

    def test_root_partial_cleanup_shows_current_phase_and_retains_original_failure(self):
        from tests.cytv.clean_removal_fixture import prepare
        original = prepare(self, 'partial')
        w = self.window()
        w.start('uninstall')
        self.pump(lambda: w.pending is not None)
        w.submit('y')
        self.pump(lambda: not w.running)
        self.assertEqual(w.title.text(), 'Removal is not finished yet.')
        self.assertEqual(self.store.pending(self.profile)['stage'], 'private-cleanup')
        self.assertEqual(self.store.pending(self.profile)['previous'], json.loads(original))
        self.assertIn('Removing private setup data…', w.subtitle.text())
        self.assertIn('Some project files remain.', w.subtitle.text())
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
        self.assertEqual(w.title.text(), 'Removal is not finished yet.')
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

