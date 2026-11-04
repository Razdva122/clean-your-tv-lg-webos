"""Common installer native proofs and dispatch never coerce profile fields."""
import json
import unittest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from cytv.operations import Installer
from cytv import state


class NativeOperationsTests(unittest.TestCase):
    def active(self):
        return dict(backend='c1-native-gate', recovery={'integrity_verified':True},
            intent={'phase':'active','enabled':True,'token':'a'*32},
            effective=dict(backend='c1-native-gate',profiles=None,state='armed',mounted=True,
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

    def test_full_removal_uses_native_restore_driver_before_normal_coordinator(self):
        remote=MagicMock();remote.run.return_value='CYTV_C1_GATE'
        installer=Installer(remote,None,{'edition':'root'},'.',{})
        installer.product_action=MagicMock(side_effect=AssertionError('normal coordinator'))
        with patch('cytv.root_gate.remove_project', return_value={'removed':True}) as remove:
            self.assertEqual(installer.uninstall_project(),{'removed':True})
            remove.assert_called_once_with(installer)

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
