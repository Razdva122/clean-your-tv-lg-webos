"""Eligibility is conservative inspection, never a trial resume."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'root-edition'))
from updater.store import Store
from installation import Ownership
import install_driver

class ContinuationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=Store(Path(self.temp.name).resolve()/'state',uid=os.getuid());self.owner=Ownership(self.store);self.identifier='a'*32
        with self.owner.operation('product','product-'+self.identifier+'.json') as lease:self.lease=lease.copy()
        self.record=dict(operation=self.identifier,lease=self.lease['id'],action='install',stage='readback',state='recovery_required',code='installation_requires_recovery')
        self.store.write('request-'+self.identifier,self.record);self.store.write('submission-'+self.identifier,dict(operation=self.identifier,action='install'))
    def check(self,**overrides):
        from unittest.mock import Mock
        device=Mock();device.verify_resume.return_value={'migrate':False,'prepare_supervisor':False};device.continuation_ready.return_value=True
        for key,value in overrides.items():setattr(device,key,value)
        return install_driver.continuation_status(self.identifier,self.store,device)
    def test_final_readback_proof_and_snapshot_allow_explicit_continuation_without_writes(self):
        import io
        from contextlib import redirect_stderr
        from install_device import LocalDevice
        with patch.object(sys,'path',[str(Path(__file__).resolve().parents[2]/'root-edition/tests')]+sys.path):
            from install_fixture import CurrentInstallation
        with CurrentInstallation() as fixture:
            device=LocalDevice();driver=install_driver.Coordinator(device,fixture.owner)
            with redirect_stderr(io.StringIO()),patch.object(device,'readback',side_effect=ValueError('interrupted final readback')):
                driver.install(self.identifier,fixture.payload)
            snapshot=fixture.snapshot(self.identifier)
            candidate=install_driver.candidate_digest(snapshot,install_driver._verified_payload(snapshot,False))
            for kind in ('submission','request'):
                record=fixture.owner.store.read(kind+'-'+self.identifier);record['candidate_sha256']=candidate
                fixture.owner.store.write(kind+'-'+self.identifier,record)
            def state():return {str(p.relative_to(fixture.state)):(p.read_bytes(),p.stat().st_mtime_ns) for p in fixture.state.rglob('*') if p.is_file()}
            before=state()
            with patch('subprocess.Popen',side_effect=AssertionError('inspection spawned worker')),patch.object(Store,'write',side_effect=AssertionError('inspection wrote record')):
                proof=install_driver.continuation_status(self.identifier,fixture.owner.store,device)
                self.assertEqual(proof,{'can_resume':True,'resume_reason':'original_final_readback_verified'})
            self.assertEqual(before,state());fixture.assert_preserved(self)

    def test_incomplete_legacy_snapshot_does_not_allow_continuation(self):
        self.assertEqual(self.check(),{'can_resume':False,'resume_reason':'original-snapshot-unverified'})
    def test_unknown_submission_foreign_owner_and_live_worker_are_blocked(self):
        from unittest.mock import Mock
        probe=Mock(return_value=False);self.assertFalse(self.check(continuation_ready=probe)['can_resume'])
        lease=self.owner.status();lease['journal']='product-'+('b'*32)+'.json';self.store.write('operation',lease);self.assertFalse(self.check()['can_resume'])
        self.store.write('operation',self.lease)
        with self.owner.operation('product','product-'+self.identifier+'.json',resume=self.lease['id']):self.assertFalse(self.check()['can_resume'])
    def test_absent_store_is_not_created(self):
        from install_device import checked_store
        absent=Path(self.temp.name)/'absent';self.assertFalse(install_driver.continuation_status(self.identifier,checked_store(absent))['can_resume']);self.assertFalse(absent.exists())
    def test_removal_final_proof_requires_each_original_terminal(self):
        from install_device import LocalDevice, APP
        device=LocalDevice();record=dict(self.record,action='remove',stage='removal-readback')
        updater='com.cleanyourtv.root.updater'
        def terminal(app):return {'completed':True,'event':{'id':app,'details':{'packageId':app,'state':'removed'}}}
        removals={app:{'state':'absent-before-submission'} for app in (updater,'com.cleanyourtv.updater','com.local.nativehome','com.gathin.tvhome','com.cleanyourtv.system.updater')}
        removals[updater]={'state':'terminal','evidence':terminal(updater)}
        journal={'schema':1,'initial_apps':[APP,updater],'removals':removals};self.store.write('removal-'+record['lease'],journal)
        with patch.object(device,'root_journal',return_value={'evidence':terminal(APP)}),patch.object(device,'verify_removed') as verified:
            self.assertTrue(device.continuation_ready(record,{},self.store));verified.assert_called_once()
            journal['removals'][updater]={'state':'submitted'};self.store.write('removal-'+record['lease'],journal)
            self.assertFalse(device.continuation_ready(record,{},self.store));self.assertEqual(verified.call_count,1)
        journal['removals'][updater]={'state':'terminal','evidence':terminal(updater)};self.store.write('removal-'+record['lease'],journal)
        with patch.object(device,'root_journal',return_value={'stage':'remove-submitting'}),patch.object(device,'verify_removed') as verified:
            self.assertFalse(device.continuation_ready(record,{},self.store));verified.assert_not_called()

    def test_device_proof_requires_final_stage_and_current_components(self):
        from install_device import LocalDevice
        device=LocalDevice();record=dict(self.record)
        with patch.object(device,'inspect',return_value={'state':'installed'}),patch.object(device,'readback',return_value={'verified':True}) as readback:
            self.assertTrue(device.continuation_ready(record,{},self.store))
            for stage in ('root-deploy','install-submitting','install-accepted','root-updater'):
                record['stage']=stage;self.assertFalse(device.continuation_ready(record,{},self.store))
            self.assertEqual(readback.call_count,1)
        record['stage']='readback'
        with patch.object(device,'inspect',return_value={'state':'recovery_required'}):self.assertFalse(device.continuation_ready(record,{},self.store))

if __name__=='__main__':unittest.main()
