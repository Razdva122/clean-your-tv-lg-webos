"""Engine recovery uses real disk journals/ownership; only device/network I/O is replaced."""
import hashlib
import importlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_core import Store, profile
import test_activation

class BootstrapFixture(unittest.TestCase):
    def setUp(self):
        test_activation.ActivationTests.setUp(self)
        self.bootstrap = importlib.import_module('system_updater.bootstrap')
        self.installation = importlib.import_module('installation')
        self.runtime = self.bootstrap.Bootstrap(self.root/'system', uid=os.getuid())
        self.runtime.product.write('bootstrap-bundle',{'bundle':{'engine_version':'1.2.11'}})
        self.runtime.slots.verify = lambda proof: self.catalog
        self.owner = self.installation.Ownership(Store(self.root/'owner', uid=os.getuid()))
        self.identifier = 'a'*32
        data = profile()
        self.runtime.store.write('profile-'+self.identifier, data)
        self.runtime.store.write('transaction', dict(schema=1,id=self.identifier,edition='no-root',release='v2.0.0',
            variant='no-root',proof={},profile='profile-'+self.identifier,
            profileDigest=hashlib.sha256(self.bootstrap.encode(data)).hexdigest(),previousTransaction=None,phase='preparing'))
        with self.owner.operation('system-engine','transaction.json') as lease:
            tx=self.runtime.store.read('transaction');tx['lease']=lease['id'];self.runtime.store.write('transaction',tx)
        self.patches=[patch.object(self.installation,'Ownership',return_value=self.owner),
                      patch.object(self.installation,'pending_journals'),
                      patch.object(self.runtime,'wake')]
        for p in self.patches:p.start()
    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        test_activation.ActivationTests.tearDown(self)

class BootstrapRecoveryTests(BootstrapFixture):
    def test_tile_recovery_is_bound_to_generation_edition_and_exact_transaction(self):
        from test_core import release
        current=release('1.0.0');current.update(schema=2,components=current['components'][:2])
        candidate=dict(current,release='v2.0.0')
        self.runtime.product.write('baseline',current)
        self.runtime.product.write('bootstrap-bundle',{'bundle':{'product_schema':2,'engine_version':'2.0.0'}})
        self.runtime.product.write('bootstrap',{'phase':'complete','edition':'no-root'})
        self.catalog.update(schema=2,releases={'no-root':candidate})
        active={'edition':'no-root','transaction':self.identifier}
        with self.assertRaisesRegex(ValueError,'matching single-tile'):
            self.runtime.handle('rollback',dict(active,edition='root'))
        with self.assertRaisesRegex(ValueError,'transaction changed'):
            self.runtime.handle('rollback',dict(active,transaction='c'*32))
        self.runtime.product.write('transaction',{'edition':'no-root','prior':release('1.0.0'),'candidate':release('2.0.0')})
        with self.assertRaisesRegex(ValueError,'another product'):
            self.runtime.handle('rollback',active)
        self.assertFalse(self.owner.status()['terminal'])
        (self.runtime.state/'transaction.json').unlink()
        status=self.runtime.handle('status',{'edition':'no-root'})
        self.assertEqual(status['id'],active['transaction'])
        self.runtime.handle('rollback',active)
        self.assertTrue(self.owner.status()['terminal'])

    def test_download_failure_can_retry_same_offer_and_profile(self):
        with patch.object(self.bootstrap,'policy',side_effect=lambda method,*a: self.catalog if method=='verify' else (_ for _ in ()).throw(OSError('offline'))):
            self.runtime.worker()
        failed=self.runtime.transaction()
        self.assertEqual(failed['phase'],'recovery-required')
        self.runtime.handle('reconcile',{})
        resumed=self.runtime.transaction()
        self.assertEqual(resumed['phase'],'staging')
        self.assertEqual(resumed['proof'],failed['proof'])
        self.assertEqual(resumed['profileDigest'],failed['profileDigest'])
        self.assertFalse(self.owner.status()['terminal'])
    def test_cancel_failed_readiness_restores_prior_engine_and_releases_owner(self):
        slot=self.runtime.slots.stage({},self.raw)
        self.runtime.slots.begin(self.identifier,slot)
        self.runtime.slots.confirm(self.identifier)
        tx=self.runtime.transaction();tx.update(phase='recovery-required',resumePhase='ready')
        self.runtime.store.write('transaction',tx)
        self.runtime.handle('rollback',{})
        self.assertEqual(self.runtime.slots.active(),self.runtime.code)
        self.assertEqual(self.runtime.transaction()['phase'],'aborted')
        self.assertTrue(self.owner.status()['terminal'])
    def test_cancel_refuses_after_child_reservation(self):
        tx=self.runtime.transaction();tx.update(phase='recovery-required',resumePhase='handoff')
        self.runtime.store.write('transaction',tx)
        self.runtime.product.write('transaction',{'id':self.identifier,'phase':'preparing'})
        with self.assertRaises(ValueError):self.runtime.handle('rollback',{})
        self.assertFalse(self.owner.status()['terminal'])

    def test_offer_uses_active_engine_normalized_state_not_legacy_product_parser(self):
        # Deliberately unreadable to the old product parser: only the active
        # engine owns this future storage schema.
        from types import SimpleNamespace
        self.runtime.product.write('baseline',{'schema':99,'opaque':'future'})
        catalog={'engine':{'version':'1.2.12','minimumPython':'3.9.0','minimumNode':8},
                 'releases':{'no-root':{'release':'v2.0.0','notes':'next','components':[{'name':'home','version':'2.0.0'}]}}}
        current={'edition':'no-root','release':'v1.0.0','resolution':'1920x1080','components':[{'name':'home','version':'1.0.0'}]}
        def call(code,method,payload):
            self.assertEqual(method,'engine-state')
            return current
        with patch.object(self.runtime,'call',side_effect=call),patch.object(self.bootstrap,'policy',return_value={'catalog':catalog,'proof':{}}),patch.object(self.bootstrap.subprocess,'run',return_value=SimpleNamespace(stdout=b'v22.0.0')):
            offer=self.runtime.offer('no-root')
        self.assertTrue(offer['canInstall'])
        self.assertFalse(offer['canRepair'])

    def test_repair_cannot_install_a_new_engine_without_product_update(self):
        with patch.object(self.runtime, 'active_transition', return_value=None), \
                patch.object(self.runtime, 'reconcile_terminal'), \
                patch.object(self.runtime, 'offer', return_value={'canRepair': False}):
            with self.assertRaisesRegex(ValueError, 'same-version'):
                self.runtime.handle('repair', {'edition': 'no-root', 'profile': profile()})

    def test_aborted_journal_closes_original_lease_after_power_loss(self):
        original=self.owner.stage
        def interrupted(record,phase,terminal=False):
            if terminal:raise KeyboardInterrupt('power loss before lease completion')
            return original(record,phase,terminal)
        with patch.object(self.owner,'stage',side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt):self.runtime.handle('rollback',{})
        self.assertEqual(self.runtime.transaction()['phase'],'aborted')
        self.assertFalse(self.owner.status()['terminal'])
        with patch.object(self.bootstrap.os,'execv',side_effect=AssertionError('must reconcile owner before product dispatch')):
            self.runtime.worker()
        self.assertTrue(self.owner.status()['terminal'])
        self.assertEqual(self.owner.status()['stage'],'aborted')

    def test_terminal_engine_only_status_preserves_retained_product_rollback(self):
        product={'id':'b'*32,'edition':'no-root','phase':'complete','canRollback':True}
        self.runtime.product.write('transaction',product)
        for phase in ('complete','aborted'):
            with self.subTest(phase=phase):
                tx=self.runtime.transaction();tx.update(phase=phase,engineOnly=True,repair=True)
                self.runtime.store.write('transaction',tx)
                with patch.object(self.runtime,'call',return_value=dict(product)):
                    status=self.runtime.handle('status',{})
                self.assertEqual(status['id'],product['id'])
                self.assertTrue(status['canRollback'])
                self.assertFalse(status.get('engineUpdate',False))
    def test_terminal_engine_only_status_without_product_keeps_own_result(self):
        tx=self.runtime.transaction();tx.update(phase='complete',engineOnly=True,repair=True)
        self.runtime.store.write('transaction',tx)
        with patch.object(self.runtime,'call',return_value=None):
            status=self.runtime.handle('status',{})
        self.assertEqual(status['id'],tx['id'])
        self.assertTrue(status['engineUpdate'])
        self.assertFalse(status['canRollback'])

    def test_reconcile_terminal_lease_keeps_product_rollback_in_its_reply(self):
        product={'id':'b'*32,'edition':'no-root','phase':'complete','canRollback':True}
        self.runtime.product.write('transaction',product)
        tx=self.runtime.transaction()
        tx.update(phase='aborted',engineOnly=True,repair=True,previousTransaction=product)
        self.runtime.store.write('transaction',tx)
        with patch.object(self.runtime,'call',return_value=dict(product)):
            status=self.runtime.handle('reconcile',{})
        self.assertTrue(self.owner.status()['terminal'])
        self.assertEqual(status['id'],product['id'])
        self.assertTrue(status['canRollback'])
