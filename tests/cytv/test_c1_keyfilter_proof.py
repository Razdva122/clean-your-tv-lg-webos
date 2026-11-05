"""A mount-free route needs explicit filter ownership, not a fake mount proof."""
import unittest
from cytv import root_gate
from cytv.operations import Installer


class KeyfilterProofTests(unittest.TestCase):
    def device(self, active):
        effective = dict(returnValue=True, backend='c1-native-gate',
            routing='compositor-keyfilter-v1', profiles=None, mounted=False,
            filter_installed=active, routing_active=active, healthy=active,
            stock_verified=not active, stopped=not active, guardian_pid=123 if active else 0,
            state='armed' if active else 'stopped', token='a'*32)
        return dict(backend='c1-native-gate', effective=effective,
            intent=dict(enabled=active, phase='active' if active else 'disabled', token='a'*32),
            recovery=dict(integrity_verified=True))

    def test_active_route_requires_owned_filter_and_live_guard_without_mount(self):
        device = self.device(True)
        self.assertIsNotNone(root_gate.native_proof(device))
        self.assertTrue(Installer.root_active(device))
        self.assertFalse(root_gate.stock_proof(device))
        for change in ({'mounted':True}, {'filter_installed':False},
                       {'routing_active':False}, {'guardian_pid':0}, {'stopped':True},
                       {'routing':'unknown'}, {'stock_verified':True}):
            with self.subTest(change=change):
                invalid = dict(device, effective=dict(device['effective'], **change))
                self.assertIsNone(root_gate.native_proof(invalid))
                self.assertFalse(Installer.root_active(invalid))

    def test_stock_proof_rejects_an_inert_but_still_installed_filter(self):
        device = self.device(False)
        self.assertTrue(root_gate.stock_proof(device))
        self.assertTrue(Installer.root_setup_inactive(device))
        device['effective']['filter_installed'] = True
        self.assertFalse(root_gate.stock_proof(device))
        self.assertFalse(Installer.root_setup_inactive(device))
