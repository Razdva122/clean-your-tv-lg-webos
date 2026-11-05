"""Normal update infrastructure must refuse experimental routing before effects."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class UpdateGuardTests(unittest.TestCase):
    def test_root_updater_refuses_experiment_before_loading_resume_runtime(self):
        from updater.device import Device
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for evidence in ('home-backend.json', 'c1-gate', 'c1-keyfilter', 'runtime/c1_gate.py', 'runtime/c1_keyfilter.py', 'runtime/c1-home-gate', 'runtime/c1-keyfilter-guard'):
                path=root/evidence;path.parent.mkdir(exist_ok=True);path.touch()
                with self.subTest(evidence=evidence), self.assertRaisesRegex(ValueError, '[Ee]xperimental'):
                    Device.require_home_resume_runtime(root)
                path.unlink()

    def test_system_setup_rejects_actual_device_evidence_before_inputs(self):
        from unittest.mock import patch
        spec=importlib.util.spec_from_file_location('c1_system_setup', ROOT.parent/'system-updater/setup.py')
        setup=importlib.util.module_from_spec(spec);spec.loader.exec_module(setup)
        for name,args in (('preflight',('missing','missing')),('provision',('missing','missing')),
                          ('finish_registration',('missing','missing')),('resume',('missing',)),
                          ('snapshot',('missing','no-root','missing'))):
            with self.subTest(entry=name), patch.object(setup,'require_normal_root',side_effect=ValueError('Experimental C1')) as guard:
                with self.assertRaisesRegex(ValueError,'Experimental C1'):getattr(setup,name)(*args)
                guard.assert_called_once()

    def test_system_setup_refuses_each_orphaned_keyfilter_artifact(self):
        spec=importlib.util.spec_from_file_location('c1_system_setup_orphans', ROOT.parent/'system-updater/setup.py')
        setup=importlib.util.module_from_spec(spec);spec.loader.exec_module(setup)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for evidence in ('c1-keyfilter','runtime/c1_keyfilter.py','runtime/c1-keyfilter-guard'):
                path=root/evidence;path.parent.mkdir(exist_ok=True);path.touch()
                with self.subTest(evidence=evidence),self.assertRaisesRegex(ValueError,'Experimental'):
                    setup.require_normal_root(root)
                path.unlink()

    def test_failed_c1_admission_does_not_reserve_installation(self):
        from unittest.mock import patch
        import deploy
        from installation import device_operation, Ownership
        from updater.store import Store
        fresh=dict(supported=True, packages_match=False, receipts_match=False,
                   pending=False, retained=False, complete=False, migration_supported=False)
        with tempfile.TemporaryDirectory() as folder:
            owner=Ownership(Store(Path(folder).resolve()/'ownership',uid=os.getuid()))
            with patch('installation.device_snapshot',return_value=fresh), patch('runtime.c1_gate.probe',side_effect=ValueError('unsupported C1')):
                with self.assertRaisesRegex(ValueError,'unsupported C1'):
                    with device_operation('deploy',ownership=owner,read=lambda path:None,check=deploy.experimental_admission):
                        self.fail('admission allowed device mutation')
            self.assertIsNone(owner.status())
            self.assertFalse((Path(folder)/'ownership/operation.json').exists())

    def test_c1_admission_rejects_orphan_components_before_probe(self):
        from unittest.mock import patch
        import deploy
        retained=dict(supported=True, packages_match=False, receipts_match=False,
                      pending=False, retained=True, complete=False, migration_supported=False)
        with patch('installation.device_snapshot',return_value=retained), patch('runtime.c1_gate.probe') as probe:
            with self.assertRaisesRegex(ValueError,'completely fresh'):deploy.experimental_admission()
            probe.assert_not_called()

    def test_experimental_runtime_refuses_ota_before_reservation_or_profiles(self):
        sys.path.insert(0, str(ROOT / 'runtime'))
        try:
            import c1_gate
            with tempfile.TemporaryDirectory() as folder:
                for mode in ('suspend-update', 'finish-update', 'abort-update', 'confirm'):
                    with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, 'does not support'):
                        c1_gate.execute(mode, 'a' * 32, Path(folder))
                self.assertEqual(list(Path(folder).iterdir()), [])
        finally:
            sys.path.remove(str(ROOT / 'runtime'))


if __name__ == '__main__':
    unittest.main()
