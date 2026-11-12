"""Recover the old standalone Updater journal with the real manager and leases."""
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT.parent), str(ROOT / 'runtime')]
from installation import Busy, Ownership
from runtime import update_guard
import test_update_core
from test_update_core import profile
from updater.device import Device
from updater.store import Store


class RollbackReadinessTests(unittest.TestCase):
    def setUp(self):
        fixture = test_update_core.UpdateTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        self.store, self.device, self.manager = fixture.store, fixture.io, fixture.m
        self.root = Path(self.store.root)
        self.owner = Ownership(Store(self.root / 'clean-your-tv-installation', uid=os.getuid()))
        self.app = 'com.cleanyourtv.root.preview'
        self.device.cached = lambda item: self.root / 'cache' / (item['sha256'] + '.ipk')
        self.device.integrity = lambda: None
        self.device.require_components = lambda: None
        self.device.descriptor = lambda item: item
        self.device.install = self.install_package
        self.device.prior['size'] = self.device.candidate['size'] = 10
        self.device.prior['local'] = True
        self.manager.install('1.1.0', profile())
        fixture.advance('verifying')
        self.device.time += 120
        fixture.advance('verifying-rollback')
        self.device.time += 120
        self.original = self.manager.run()
        with self.owner.operation('root-update', 'transaction.json') as lease:
            self.owner.stage(lease, 'recovery-required')
        self.runtime = self.root / 'clean-your-tv-root'
        self.runtime.mkdir()
        self.archives = self.root / 'readiness-recovery'
        update_guard.atomic(self.runtime / 'update-home-resume.json', dict(
            transaction=self.original['id'], ticket='a' * 32, outcome={'status': 'skipped'}))
        self.device.runtime = lambda mode, identifier: update_guard.finish(
            identifier, self.runtime, uid=os.getuid())
        self.device.state = self.root
        self.device.finish = Device.finish.__get__(self.device)

    def install_package(self, manifest, submit, terminal):
        path = str(self.device.cached(manifest))
        submit(dict(package=path, version=manifest['version']))
        self.device.calls.append('install:' + manifest['version'])
        self.device.version = manifest['version']
        terminal(dict(success=True, event=dict(id=self.app, statusValue=30, details=dict(
            packageId=self.app, client='com.webos.lunasend-23',
            ipkFile=f'/var/lib/clean-your-tv-installer/cytv-root-install-{len(self.device.calls)}/package.ipk'))))

    def recover(self, launch, sleep=None):
        from cytv.root_rollback_recovery import SCRIPT
        namespace = {}
        exec(compile(SCRIPT, 'root-rollback-recovery', 'exec'), namespace)
        return namespace['recover'](
            self.manager, self.device, self.store, self.owner, lambda: None,
            self.app, launch,
            sleep=sleep or (lambda _: None))

    def test_fresh_receipt_unlocks_updates_and_home(self):
        self.assertEqual('recovery-required', self.original['phase'])
        with self.assertRaisesRegex(ValueError, 'unfinished update'):
            self.manager.install('1.1.0', profile())
        with self.assertRaisesRegex(RuntimeError, 'needs recovery'):
            with update_guard.control(self.runtime, uid=os.getuid()):
                pass

        def launch():
            current = self.manager.status()
            self.assertEqual('verifying-rollback', current['phase'])
            self.assertEqual(current['launched'] + 120, current['deadline'])
            self.assertGreaterEqual(current['launched'], self.original['deadline'])
            self.assertIsNone(self.store.read('ready-rollback-' + current['id']))
            # Removal cannot take the lease during the launcher RPC.
            competitor = Ownership(self.owner.store)
            with self.assertRaises(Busy):
                with competitor.removal('b' * 32, expected=self.owner.status()['id']):
                    pass

        def ready(_):
            # The launcher signals readiness after the launch RPC returns.
            with self.owner.operation('root-update', 'transaction.json',
                                      resume=self.owner.status()['id']):
                self.manager.ready(self.manager.status()['id'], '1.0.0')

        result = self.recover(launch, ready)
        self.assertEqual('rolled-back', result['phase'])
        self.assertEqual('rolled-back', result['homeResumePhase'])
        self.assertEqual({'status': 'skipped'}, result['homeResume'])
        self.assertEqual(self.original, Store(self.archives, uid=os.getuid()).read(result['readinessRecovery']))
        self.assertEqual(self.original['rollbackEvidence'], result['rollbackEvidence'])
        self.assertEqual('1.0.0', self.store.read('current')['version'])
        self.assertEqual(['install:1.1.0', 'install:1.0.0'],
                         [call for call in self.device.calls if call.startswith('install:')])
        self.assertTrue(self.owner.status()['terminal'])
        with update_guard.control(self.runtime, uid=os.getuid()):
            pass
        self.assertEqual(result, self.recover(lambda: self.fail('relaunch after completion')))
        self.assertEqual('preparing', self.manager.install('1.1.0', profile())['phase'])

    def test_retry_without_readiness_keeps_recovery_gate(self):
        def expire(_):
            self.device.time += 120
        result = self.recover(lambda: None, expire)
        self.assertEqual('recovery-required', result['phase'])
        self.assertFalse(self.owner.status()['terminal'])
        self.assertIsNone(self.store.read('ready-rollback-' + result['id']))
        self.assertEqual(self.original, Store(self.archives, uid=os.getuid()).read(result['readinessRecovery']))

    def test_wrong_package_evidence_keeps_original_journal(self):
        bad = self.manager.status()
        bad['rollbackEvidence']['terminal']['event']['details']['ipkFile'] = '/wrong.ipk'
        self.store.write('transaction', bad)
        with self.assertRaisesRegex(ValueError, 'terminal'):
            self.recover(lambda: self.fail('unverified rollback launched'))
        self.assertEqual(bad, self.manager.status())
        self.assertFalse(self.owner.status()['terminal'])


    def test_interrupted_relaunch_keeps_same_window(self):
        def interrupted():
            raise RuntimeError('launcher restart interrupted')

        with self.assertRaisesRegex(RuntimeError, 'interrupted'):
            self.recover(interrupted)
        armed = self.manager.status()
        self.device.time += 30

        def ready():
            self.assertEqual(armed, self.manager.status())
            self.manager.ready(armed['id'], '1.0.0')

        self.assertEqual('rolled-back', self.recover(ready)['phase'])
        self.assertEqual(1, len(list(self.archives.glob('*.json'))))

    def test_retry_rearms_expired_window_and_launches_in_same_run(self):
        def interrupted(_):
            raise ConnectionError('SSH disconnected while waiting for readiness')

        with self.assertRaises(ConnectionError):
            self.recover(lambda: None, interrupted)
        expired = self.manager.status()
        self.device.time = expired['deadline']
        self.assertEqual('verifying-rollback', expired['phase'])
        self.assertEqual('verifying-rollback', self.owner.status()['stage'])

        def launch():
            armed = self.manager.status()
            self.assertEqual('verifying-rollback', armed['phase'])
            self.assertEqual(expired['deadline'], armed['launched'])
            self.assertEqual(armed['launched'] + 120, armed['deadline'])
            self.assertEqual(expired, Store(self.archives, uid=os.getuid()).read(armed['readinessRecovery']))
            self.assertIsNone(self.store.read('ready-rollback-' + armed['id']))

        def ready(_):
            self.manager.ready(expired['id'], '1.0.0')

        result = self.recover(launch, ready)
        self.assertEqual('rolled-back', result['phase'])
        self.assertEqual(expired['rollbackEvidence'], result['rollbackEvidence'])
        self.assertTrue(self.owner.status()['terminal'])
        self.assertEqual(2, len(list(self.archives.glob('*.json'))))

    def test_expired_window_with_saved_readiness_finishes_without_relaunch(self):
        def interrupted(_):
            self.manager.ready(self.manager.status()['id'], '1.0.0')
            raise ConnectionError('SSH disconnected before finalization')

        with self.assertRaises(ConnectionError):
            self.recover(lambda: None, interrupted)
        armed = self.manager.status()
        self.device.time = armed['deadline']

        result = self.recover(lambda: self.fail('existing readiness should finalize the rollback'))
        self.assertEqual('rolled-back', result['phase'])
        self.assertEqual(armed['deadline'], result['deadline'])
        self.assertEqual(1, len(list(self.archives.glob('*.json'))))
