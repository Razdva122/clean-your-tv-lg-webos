"""Common installer native proofs and dispatch never coerce profile fields."""
import json
import unittest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from cytv.operations import Installer
from cytv import state
from cytv.errors import UserError


class NativeOperationsTests(unittest.TestCase):
    def active(self):
        return dict(backend='c1-native-gate', recovery={'integrity_verified':True},
            intent={'phase':'active','enabled':True,'token':'a'*32},
            effective=dict(returnValue=True,backend='c1-native-gate',profiles=None,state='armed',mounted=True,
                           healthy=True,stock_verified=False,stopped=False,token='a'*32,guardian_pid=123))

    def test_active_requires_native_attempt_and_lease_proof(self):
        self.assertTrue(Installer.root_active(self.active()))
        for change in ({'healthy':False},{'token':'b'*32},{'profiles':{}},{'stopped':True},{'guardian_pid':0}):
            value=self.active();value['effective'].update(change)
            with self.subTest(change=change):self.assertFalse(Installer.root_active(value))

    def test_stock_native_proof_is_not_an_active_route(self):
        value=self.active()
        value['intent'].update(phase='disabled',enabled=False)
        value['effective'].update(state='stopped',healthy=False,mounted=False,stock_verified=True,guardian_pid=0,stopped=True)
        self.assertTrue(Installer.root_setup_inactive(value))
        self.assertFalse(Installer.root_active(value))
        value['effective']['mounted']=True
        self.assertFalse(Installer.root_setup_inactive(value))

    def test_install_flag_is_internal_and_does_not_select_control_modes(self):
        remote=MagicMock();remote.run.return_value=json.dumps({'returnValue':True,'installed':'ok'})
        installer=Installer(remote,None,{'edition':'root'},'.',{})
        installer._selected_python='/usr/bin/python3'
        installer.root_action('install',bundle='/tmp/verified-bundle',experimental=True)
        self.assertIn('--experimental-c1-gate',remote.run.call_args.args[0])
        with self.assertRaises(ValueError):installer.root_action('enable',experimental=True)

    def test_full_removal_selects_current_native_bundle_for_shared_cleanup(self):
        import hashlib
        from tests.cytv.test_full_uninstall import FullUninstallTests
        installer,remote,store,profile,calls,device=FullUninstallTests.fixture(self)
        native=installer.payload/'root-c1';native.mkdir()
        source=b'current trusted native restore driver'
        (native/'install_driver.py').write_bytes(source)
        (native/'bundle.json').write_text(json.dumps({'files':{
            'install_driver.py':hashlib.sha256(source).hexdigest()}}))
        installer.native_root_present=MagicMock(return_value=True)
        upload=installer.upload_product
        with patch.object(installer,'upload_product',wraps=upload) as bundled, \
             patch('cytv.root_gate.remove_project',side_effect=AssertionError('legacy removal bypass')) as legacy:
            result=installer.uninstall_project()
            self.assertIs(result['removed'],True);self.assertIs(result['verified_clean'],True)
            bundled.assert_called_once_with(native,clean_removal=True)
            legacy.assert_not_called()
        roots=[call.args[1] for call in remote.upload.call_args_list if call.args[0].endswith('/root/install_driver.py')]
        self.assertEqual(roots,[source])
        self.assertEqual([action for action,_ in calls],['clean-target','clean-remove'])
        self.assertIsNone(store.pending(profile));remote.luna.assert_not_called()

    def test_native_cleanup_refuses_missing_or_foreign_current_bundle_before_device_request(self):
        import hashlib
        from tests.cytv.test_full_uninstall import FullUninstallTests
        for foreign in (False,True):
            with self.subTest(foreign=foreign):
                installer,remote,store,profile,calls,device=FullUninstallTests.fixture(self)
                installer.native_root_present=MagicMock(return_value=True)
                target=installer.payload/'foreign';target.write_bytes(b'preserve foreign bytes')
                if foreign:
                    native=installer.payload/'root-c1';native.mkdir()
                    (native/'install_driver.py').symlink_to(target)
                    (native/'bundle.json').write_text(json.dumps({'files':{
                        'install_driver.py':hashlib.sha256(target.read_bytes()).hexdigest()}}))
                with self.assertRaises(UserError):installer.uninstall_project()
                self.assertEqual(calls,[])
                self.assertIsNotNone(store.pending(profile))
                self.assertEqual(target.read_bytes(),b'preserve foreign bytes')
                remote.upload.assert_not_called();remote.luna.assert_not_called()

    def test_interrupted_native_handoff_without_root_files_uses_compositor_cleanup(self):
        import hashlib
        from tests.cytv.test_full_uninstall import FullUninstallTests
        installer, remote, store, profile, calls, device = FullUninstallTests.fixture(self)
        native = installer.payload/'root-c1'
        native.mkdir()
        (native/'bundle.json').write_text(json.dumps({'files': {'release.json': hashlib.sha256(b'{}').hexdigest()}}))
        (native/'release.json').write_bytes(b'{}')
        operation = device['target_operation']
        stage = '/tmp/cytv-product-' + 'a' * 32
        store.begin(profile, 'install', stage='setup', product_operation=operation,
                    product_payload=stage, home_backend='c1-native-gate', requires_updater=False)
        original = store.pending(profile)
        installer.native_root_present = MagicMock(return_value=False)
        with patch.object(installer, 'upload_product', wraps=installer.upload_product) as upload:
            result = installer.uninstall_project()
            self.assertTrue(result['verified_clean'])
            upload.assert_called_once_with(native, clean_removal=True)
        self.assertEqual(calls, [('clean-target', operation), ('clean-remove', operation)])
        self.assertIn('--retire-stage ' + stage, remote.run.call_args.args[0])
        receipt = json.loads((store.device_dir(profile)/'clean-removal.json').read_bytes())
        self.assertEqual(receipt['previous'], original)
        self.assertIsNone(store.pending(profile))

    def test_uncertain_install_submission_stays_pending_when_root_files_are_absent(self):
        with tempfile.TemporaryDirectory() as folder:
            store=state.Store(folder);profile=state.target('tv.local','root')
            store.begin(profile,'install',home_backend='c1-native-gate',stage='setup',requires_updater=False)
            original=store.pending(profile)
            remote=MagicMock();remote.run.return_value='{"stage":"absent"}'
            installer=Installer(remote,store,profile,'.',{})
            installer.verify_absent=MagicMock()
            result=installer.status()
            self.assertEqual(result['pending'],original)
            self.assertIsNone(result['reconciled'])
            installer.verify_absent.assert_not_called()

    def test_recovery_only_install_can_resume_without_claiming_activation_complete(self):
        with tempfile.TemporaryDirectory() as folder:
            store=state.Store(folder);profile=state.target('tv.local','root')
            store.begin(profile,'install',home_backend='c1-native-gate',stage='setup',requires_updater=False)
            remote=MagicMock();remote.run.return_value='{"stage":"installed-recovery-only"}'
            installer=Installer(remote,store,profile,'.',{})
            device=self.active();device['intent'].update(enabled=False,phase='disabled')
            device['effective'].update(healthy=False,mounted=False,stock_verified=True,guardian_pid=0,state='stopped',stopped=True)
            installer.root_action=MagicMock(return_value={'returnValue':True,'result':device})
            installer.root_files_match=MagicMock(return_value=True)
            result=installer.status()
            self.assertIsNotNone(store.pending(profile))
            self.assertTrue(result['can_resume_root_setup'])
            self.assertIsNone(result['reconciled'])

    def test_native_version_review_uses_matching_variant_without_updater(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'root-c1').mkdir()
            (root/'root-c1/release.json').write_text('{"version":"0.9.0"}')
            installer=Installer(None,None,{'edition':'root'},root,
                {'root_backends':{'c1-native-gate':{'graphics':{'1920x1080':'root-c1'}}}},
                tv_info={'home_backend':'c1-native-gate','graphics_resolution':'1920x1080'})
            installer.installed_apps=MagicMock(return_value=[])
            rows=installer.version_summary()
            self.assertEqual(len(rows),1);self.assertIn('C1 Beta',rows[0]);self.assertIn('0.9.0',rows[0])

    def test_registration_readback_requires_hooks_and_ls2_absent_without_profile_calls(self):
        remote=MagicMock();remote.run.return_value=''
        installer=Installer(remote,None,{'edition':'root'},'.',{})
        installer._selected_python='/usr/bin/python3'
        with self.assertRaises(UserError):installer.verify_project_startup_removed()
        command=remote.run.call_args.args[0]
        self.assertIn('51-clean-your-tv-root-updater',command)
        self.assertIn('client-permissions.d',command)
        remote.luna.assert_not_called()
