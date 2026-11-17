"""System self-replacement never turns shared package bytes into authority."""
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import test_package_identity as fixtures
import package_identity as p
import startup_guard as guard


class EngineIdentityTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.IdentityTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.state = self.fixture.states[p.SYSTEM]
        self.store = self.fixture.stores[p.SYSTEM]

    def provision_helper(self):
        code = self.state/'code'
        files = {'python_boot.js': b'fixed binding', 'run-system-updater.py': b'fixed entry',
                 'system_updater/bootstrap.py': b'fixed bootstrap', 'other-import.py': b'fixed import'}
        for name, raw in files.items():
            path = code/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
        self.store.write('infrastructure', {'schema': 1, 'code': {name: p.digest(raw) for name,raw in files.items()}})

    def test_private_helper_verifies_every_pinned_import_before_execution(self):
        self.provision_helper()
        reply = SimpleNamespace(returncode=0, stdout=b'{"returnValue":true,"result":true}')
        with patch.object(p.subprocess, 'run', return_value=reply) as run:
            self.assertTrue(p.system_helper(self.state, 'engine-recovery', uid=os.getuid()))
            self.assertEqual(run.call_args.args[0], ['/usr/bin/node', str(self.state/'code/python_boot.js'),
                str(self.state), str(self.state/'code/run-system-updater.py'), 'engine-recovery'])
            self.assertEqual(run.call_args.kwargs['env']['PYTHONDONTWRITEBYTECODE'], '1')
            (self.state/'code/other-import.py').write_bytes(b'changed')
            run.reset_mock()
            with self.assertRaises(ValueError):
                p.system_helper(self.state, 'engine-recovery', uid=os.getuid())
            run.assert_not_called()

    def test_helper_rejects_paths_and_unrecognized_response(self):
        self.provision_helper()
        with patch.object(p.subprocess, 'run') as run:
            with self.assertRaises(ValueError): p.system_helper(self.state, '../worker', uid=os.getuid())
            run.assert_not_called()
        reply = SimpleNamespace(returncode=0, stdout=b'{"returnValue":true,"result":true,"extra":1}')
        with patch.object(p.subprocess, 'run', return_value=reply):
            with self.assertRaises(ValueError): p.system_helper(self.state, 'engine-recovery', uid=os.getuid())

    def test_active_engine_fences_standalone_updater_even_without_product_transaction(self):
        engine = self.state/'engine-state'; engine.mkdir()
        (engine/'transaction.json').write_text(json.dumps({'schema': 1, 'id': 'a'*32, 'phase': 'staging'}))
        self.assertFalse(p.worker_allowed(p.UPDATER, states=self.fixture.states, uid=os.getuid()))
        self.assertTrue(p.worker_allowed(p.ROOT, states=self.fixture.states, uid=os.getuid()))

    def test_signed_generation_selects_package_but_shared_bytes_still_require_readback(self):
        engine = self.state/'engine-state'; engine.mkdir()
        (engine/'supervisor-generation.json').write_text('{}')
        candidate = self.fixture.package(p.SYSTEM, '1.1.0')
        self.fixture.install(p.SYSTEM, candidate)
        with patch.object(p, 'system_helper', return_value=candidate[2]) as helper:
            self.assertEqual(self.fixture.identity(p.SYSTEM, full=True)['version'], '1.1.0')
            helper.assert_called_with(self.state, 'own-package', uid=os.getuid())
            (self.fixture.installed/'usr/palm/applications'/p.SYSTEM/'index.html').write_bytes(b'changed')
            with self.assertRaises(ValueError): self.fixture.identity(p.SYSTEM, full=True)
        with patch.object(p, 'system_helper', return_value=None):
            with self.assertRaisesRegex(ValueError, 'generation'): self.fixture.identity(p.SYSTEM)

    def test_migration_readback_window_is_worker_only_and_requires_proven_ownership(self):
        original = self.fixture.packages[p.SYSTEM]
        self.store.write('bootstrap-bundle', {'schema':1,
            'package':{key:original[0][key] for key in ('sha256','size')}})
        self.store.write('bootstrap', {'phase':'complete'})
        self.store.write('installed-package', {'schema':1,'package':original[0],'files':original[2]})
        terminal = {'completed':True,'event':{'id':p.SYSTEM,'statusValue':30,'details':{
            'packageId':p.SYSTEM,'client':'com.webos.lunasend-99',
            'ipkFile':'/var/lib/clean-your-tv-installer/cytv-root-install-fixture/package.ipk'}}}
        self.store.write('installed-terminal', terminal)
        self.fixture.install(p.SYSTEM, self.fixture.package(p.SYSTEM, '1.1.0'))
        with patch.object(p, 'system_recovery_allowed', return_value=True):
            with self.assertRaises(p.TransitionUnknown): self.fixture.identity(p.SYSTEM, purpose='worker')
            with self.assertRaises(ValueError) as caught: self.fixture.identity(p.SYSTEM, purpose='admission')
            self.assertNotIsInstance(caught.exception, p.TransitionUnknown)
        with patch.object(p, 'system_recovery_allowed', return_value=False):
            with self.assertRaises(ValueError) as caught: self.fixture.identity(p.SYSTEM, purpose='worker')
            self.assertNotIsInstance(caught.exception, p.TransitionUnknown)

    def test_only_exact_owned_system_recovery_can_boot_with_uncertain_own_package(self):
        with patch.object(guard, 'worker_allowed', return_value=True), \
                patch.object(guard, 'present', return_value=False), \
                patch.object(guard, 'identity', side_effect=ValueError('own package uncertain')), \
                patch.object(guard, 'system_recovery_allowed', return_value=True) as allowed, \
                patch.object(guard.subprocess, 'Popen') as spawn:
            self.assertTrue(guard.start(p.SYSTEM))
            allowed.assert_called_once_with(guard.OWNERS[p.SYSTEM])
            self.assertEqual(spawn.call_args.args[0][-1], 'worker')
        with patch.object(guard, 'worker_allowed', return_value=True), \
                patch.object(guard, 'present', return_value=False), \
                patch.object(guard, 'identity', side_effect=ValueError('unowned')), \
                patch.object(guard, 'system_recovery_allowed', return_value=False), \
                patch.object(guard.subprocess, 'Popen') as spawn:
            self.assertFalse(guard.start(p.SYSTEM)); spawn.assert_not_called()


if __name__ == '__main__': unittest.main()
