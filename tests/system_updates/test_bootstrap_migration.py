"""Crash boundaries for replacing the registered System Updater package."""
import copy
import importlib
import os
from pathlib import Path
import tempfile
import unittest
from test_core import Store


def descriptor(version, sha):
    return {'version': version, 'sha256': sha * 64, 'size': 100}


class Effects:
    def __init__(self):
        self.prior = descriptor('1.2.11', 'a')
        self.candidate = descriptor('1.2.12', 'b')
        self.installed = copy.deepcopy(self.prior)
        self.calls = []
        self.crash = None
        self.prepared = True
        self.readback = True

    def prepare(self, candidate, prior):
        self.calls.append('prepare')
        if not self.prepared:
            raise ValueError('cache unavailable')

    def install(self, target, on_intent, on_accepted, on_terminal):
        on_intent()
        self.calls.append(('install', target['version']))
        on_accepted({'id': 'original', 'sha256': target['sha256']})
        self.installed = copy.deepcopy(target)
        if self.crash == 'submission':
            raise KeyboardInterrupt('power loss')
        on_terminal({'completed': True, 'sha256': target['sha256']})
        if self.crash == 'terminal':
            raise KeyboardInterrupt('power loss')

    def terminal(self, evidence, target):
        return evidence == {'completed': True, 'sha256': target['sha256']}

    def verify_installed(self, target):
        return self.readback and self.installed == target

    def publish(self, tx):
        self.calls.append(('publish', tx['rollback']))
        if self.crash == 'publication':
            raise KeyboardInterrupt('power loss')

    def activate(self, tx):
        self.calls.append(('activate', tx['rollback']))
        if self.crash == 'activation':
            raise KeyboardInterrupt('power loss')


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name).resolve(), uid=os.getuid())
        self.io = Effects()
        self.Migration = importlib.import_module('system_updater.bootstrap_migration').Migration
        self.migration = self.Migration(self.store, self.io)

    def tearDown(self):
        self.tmp.cleanup()

    def reserve(self):
        return self.migration.begin('a' * 32, self.io.candidate, self.io.prior)

    def test_prepare_and_verified_terminal_precede_publication(self):
        self.reserve()
        self.assertEqual(self.io.calls, [])
        self.assertEqual(self.migration.run()['phase'], 'complete')
        self.assertEqual(self.io.calls, ['prepare', ('install', '1.2.12'),
                                       ('publish', False), ('activate', False)])

    def test_submission_crash_never_replays_even_if_candidate_bytes_match(self):
        self.reserve()
        self.io.crash = 'submission'
        with self.assertRaises(KeyboardInterrupt):
            self.migration.run()
        restarted = self.Migration(self.store, self.io)
        self.assertEqual(restarted.run()['phase'], 'recovery-required')
        self.assertFalse(restarted.status()['canRollback'])
        with self.assertRaises(ValueError):
            restarted.rollback()
        self.assertEqual([c for c in self.io.calls if isinstance(c, tuple)],
                         [('install', '1.2.12')])

    def test_terminal_crash_resumes_readback_without_resubmission(self):
        self.reserve()
        self.io.crash = 'terminal'
        with self.assertRaises(KeyboardInterrupt):
            self.migration.run()
        self.io.crash = None
        restarted = self.Migration(self.store, self.io)
        self.assertEqual(restarted.run()['phase'], 'complete')
        self.assertEqual(self.io.calls.count(('install', '1.2.12')), 1)

    def test_publication_and_activation_can_resume_idempotently(self):
        for point in ('publication', 'activation'):
            with self.subTest(point=point):
                self.store = Store(Path(self.tmp.name).resolve()/point, uid=os.getuid())
                self.io = Effects()
                self.migration = self.Migration(self.store, self.io)
                self.reserve()
                self.io.crash = point
                with self.assertRaises(KeyboardInterrupt):
                    self.migration.run()
                self.io.crash = None
                self.assertEqual(self.Migration(self.store, self.io).run()['phase'], 'complete')
                self.assertEqual(self.io.calls.count(('install', '1.2.12')), 1)

    def test_known_completed_migration_can_restore_exact_prior(self):
        self.reserve()
        self.migration.run()
        self.migration.rollback()
        self.assertEqual(self.migration.run()['phase'], 'rolled-back')
        self.assertEqual(self.io.installed, self.io.prior)
        self.assertEqual(self.io.calls[-2:], [('publish', True), ('activate', True)])

    def test_readback_failure_cannot_publish_or_activate(self):
        self.reserve()
        self.io.readback = False
        self.assertEqual(self.migration.run()['phase'], 'recovery-required')
        self.assertNotIn(('publish', False), self.io.calls)
        self.assertNotIn(('activate', False), self.io.calls)

    def test_cache_failure_retries_without_package_intent(self):
        self.reserve()
        self.io.prepared = False
        self.assertEqual(self.migration.run()['phase'], 'recovery-required')
        self.assertTrue(self.migration.status()['canRollback'])
        self.io.prepared = True
        self.assertEqual(self.migration.run()['phase'], 'complete')
        self.assertEqual(self.io.calls.count(('install', '1.2.12')), 1)

    def test_original_operation_and_descriptor_cannot_be_replaced(self):
        self.reserve()
        with self.assertRaises(ValueError):
            self.migration.begin('b' * 32, self.io.candidate, self.io.prior)
        with self.assertRaises(ValueError):
            self.migration.begin('a' * 32, self.io.prior, self.io.candidate)
        self.assertEqual(self.reserve()['phase'], 'prepared')

    def test_service_only_migration_restores_registration_without_package_install(self):
        self.io.candidate = copy.deepcopy(self.io.prior)
        self.reserve()
        self.assertEqual(self.migration.run()['phase'], 'complete')
        self.assertFalse(any(isinstance(c, tuple) and c[0] == 'install' for c in self.io.calls))
        self.migration.rollback()
        self.assertEqual(self.migration.run()['phase'], 'rolled-back')
        self.assertEqual(self.io.calls[-2:], [('publish', True), ('activate', True)])

    def test_explicit_repair_reinstalls_identical_signed_package(self):
        self.io.candidate = copy.deepcopy(self.io.prior)
        self.migration.begin('a' * 32, self.io.candidate, self.io.prior, repair=True)
        self.assertEqual(self.migration.run()['phase'], 'complete')
        self.assertEqual(self.io.calls.count(('install', '1.2.11')), 1)
        with self.assertRaises(ValueError):
            self.migration.begin('a' * 32, self.io.candidate, self.io.prior, repair=False)

    def test_advanced_journal_without_terminal_cannot_publish_matching_bytes(self):
        self.reserve()
        self.io.installed = copy.deepcopy(self.io.candidate)
        tx = self.store.read('supervisor-migration')
        tx['phase'] = tx['resume'] = 'publishing'
        self.store.write('supervisor-migration', tx)
        self.assertEqual(self.migration.run()['phase'], 'recovery-required')
        self.assertEqual(self.io.calls, [])


if __name__ == '__main__':
    unittest.main()
