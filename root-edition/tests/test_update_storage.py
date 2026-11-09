"""Real filesystem retention: terminal proof, cross-store references and safe deletion."""
import hashlib
import io
from contextlib import redirect_stderr
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from updater import store as storage


class RetentionTests(unittest.TestCase):
    def setUp(self):
        self.syslog=Mock()
        logger=patch.dict(sys.modules,{"syslog":SimpleNamespace(LOG_INFO=6,syslog=self.syslog)})
        logger.start();self.addCleanup(logger.stop)
        self.stderr=io.StringIO();capture=redirect_stderr(self.stderr);capture.__enter__()
        self.addCleanup(capture.__exit__,None,None,None)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()
        self.stores=[storage.Store(self.root/name,uid=os.getuid()) for name in ('system','legacy')]
        for store in self.stores:
            (Path(store.root)/'cache').mkdir()
            store.write('bootstrap',{'phase':'complete'})
        self.terminal()

    def terminal(self,phase='aborted'):
        self.stores[0].write('transaction',{'schema':1,'id':'a'*32,'phase':phase,
            'homeResumePhase':phase,'rollbackAttempted':False,'created':1,'updated':2,
            'profile':'profile-'+'a'*32,'profileDigest':'e'*64,'candidate':{'sha256':'a'*64},'prior':{'sha256':'b'*64},
            'installEvidence':{'submitted':None,'terminal':None},
            'rollbackEvidence':{'submitted':None,'terminal':None}})

    def package(self,store,raw,suffix=''):
        digest=hashlib.sha256(raw).hexdigest();path=Path(store.root)/'cache'/(digest+suffix)
        path.write_bytes(raw);path.chmod(0o600);return path

    def prune(self):return storage.prune_update_caches(self.stores)

    def summary(self,scope,reason,removed):
        message='cytv-retention scope='+scope+' reason='+reason+' removed='+str(removed)
        self.assertIn(message,self.stderr.getvalue())
        self.assertTrue(any(call.args[-1]==message for call in self.syslog.call_args_list))

    def test_diagnostics_distinguish_noop_refusal_and_changed_proof(self):
        self.assertEqual(self.prune(),0);self.summary('cache','complete',0)
        self.stderr.truncate(0);self.stderr.seek(0)
        self.stores[1].write('private-secret-record',{'secret':'token'})
        self.assertEqual(self.prune(),0);self.summary('cache','admission-refused',0)
        self.assertNotIn('private-secret-record',self.stderr.getvalue())
        self.assertNotIn(str(self.root),self.stderr.getvalue())
        (Path(self.stores[1].root)/'private-secret-record.json').unlink()
        old=self.package(self.stores[0],b'private package');original=self.stores[0].read;calls=[]
        def read(name):
            if name=='transaction':
                calls.append(name)
                if len(calls)==2:self.stores[0].write('current-root',{'sha256':old.name})
            return original(name)
        with patch.object(self.stores[0],'read',side_effect=read):self.assertEqual(self.prune(),0)
        self.summary('cache','proof-changed',0);self.assertTrue(old.exists())
        self.assertNotIn(old.name,self.stderr.getvalue())

    def test_diagnostics_count_unlinks_before_fsync_failure_and_survive_sink_errors(self):
        old=self.package(self.stores[0],b'private package')
        with patch.object(storage.os,'fsync',side_effect=OSError('private /path token')):
            self.assertEqual(self.prune(),1)
        self.assertFalse(old.exists());self.summary('cache','filesystem-error',1)
        self.assertNotIn('private /path token',self.stderr.getvalue())
        self.package(self.stores[0],b'next package')
        with patch('syslog.syslog',side_effect=RuntimeError('private sink')), patch('sys.stderr',None):
            self.assertEqual(self.prune(),1)

    def test_absent_syslog_keeps_stderr_observable_and_return_unchanged(self):
        old=self.package(self.stores[0],b'private package')
        with patch.dict(sys.modules,{'syslog':None}):self.assertEqual(self.prune(),1)
        self.assertFalse(old.exists())
        self.assertIn('scope=cache reason=complete removed=1',self.stderr.getvalue())

    def test_later_unlink_failure_reports_partial_progress(self):
        files=[self.package(self.stores[0],raw) for raw in (b'first',b'second')]
        original=os.unlink;calls=[]
        def unlink(name,**kwargs):
            calls.append(name)
            if len(calls)==2:raise OSError('private filename credential')
            return original(name,**kwargs)
        with patch.object(storage.os,'unlink',side_effect=unlink):self.assertEqual(self.prune(),1)
        self.summary('cache','filesystem-error',1)
        self.assertEqual(sum(path.exists() for path in files),1)
        self.assertNotIn('private filename credential',self.stderr.getvalue())

    def test_new_unknown_record_during_revalidation_reports_proof_change(self):
        old=self.package(self.stores[0],b'private package');original=self.stores[0].read;calls=[]
        def read(name):
            if name=='transaction':
                calls.append(name)
                if len(calls)==2:self.stores[1].write('new-private-record',{'secret':'token'})
            return original(name)
        with patch.object(self.stores[0],'read',side_effect=read):self.assertEqual(self.prune(),0)
        self.summary('cache','proof-changed',0);self.assertTrue(old.exists())

    def test_peer_admission_error_is_observable(self):
        peer=self.root/'private-peer';peer.symlink_to(self.root/'missing')
        self.assertEqual(storage.prune_peer_caches(self.stores[0],peer),0)
        self.summary('cache-peer','filesystem-error',0)
        self.assertNotIn('private-peer',self.stderr.getvalue())

    def test_terminal_sweep_preserves_union_of_all_store_references(self):
        current=self.package(self.stores[0],b'current');rollback=self.package(self.stores[0],b'rollback')
        cross=self.package(self.stores[0],b'legacy-current');old=self.package(self.stores[0],b'obsolete')
        self.stores[0].write('current-root',{'components':[{'sha256':current.name}]})
        self.stores[0].write('baseline',{'components':[{'sha256':rollback.name}]})
        self.stores[1].write('current',{'sha256':cross.name})
        journal=(Path(self.stores[0].root)/'transaction.json').read_bytes()
        self.assertEqual(self.prune(),1)
        self.assertFalse(old.exists());self.assertTrue(all(p.exists() for p in (current,rollback,cross)))
        self.assertEqual((Path(self.stores[0].root)/'transaction.json').read_bytes(),journal)

    def test_real_startup_receipts_and_legacy_ipk_names_allow_retention(self):
        self.stores[0].write('startup-hook',{'version':3,'owner':'system'})
        previous=Path(self.stores[0].root)/'startup-hook.previous.json'
        previous.write_text('{"version":1}');previous.chmod(0o600)
        old=self.package(self.stores[1],b'legacy obsolete',suffix='.ipk')
        self.assertEqual(self.prune(),1);self.assertFalse(old.exists());self.assertTrue(previous.exists())

    def test_legacy_finish_sweeps_only_after_home_receipt_is_saved(self):
        from updater.device import Device
        old=self.package(self.stores[0],b'obsolete')
        tx=self.stores[0].read('transaction');tx.pop('homeResumePhase');self.stores[0].write('transaction',tx)
        device=Device(self.stores[0]);device.require_components=lambda:None
        def runtime(*args):
            self.assertTrue(old.exists());return {'status':'skipped'}
        device.runtime=runtime
        self.assertEqual(device.finish(tx),{'status':'skipped'})
        self.assertFalse(old.exists());self.assertEqual(self.stores[0].read('transaction')['homeResumePhase'],'aborted')

    def test_latest_transaction_candidate_and_prior_remain_available(self):
        candidate=self.package(self.stores[0],b'candidate');prior=self.package(self.stores[0],b'prior')
        old=self.package(self.stores[0],b'obsolete')
        tx=self.stores[0].read('transaction');tx['candidate']['sha256']=candidate.name;tx['prior']['sha256']=prior.name
        self.stores[0].write('transaction',tx)
        self.assertEqual(self.prune(),1)
        self.assertTrue(candidate.exists());self.assertTrue(prior.exists());self.assertFalse(old.exists())

    def test_repeated_terminal_updates_are_bounded(self):
        for index in range(15):
            old=self.package(self.stores[0],str(index-1).encode())
            current=self.package(self.stores[0],str(index).encode())
            self.stores[0].write('current-root',{'sha256':current.name})
            self.stores[0].write('baseline',{'sha256':old.name})
            self.prune()
            self.assertLessEqual(len(list((Path(self.stores[0].root)/'cache').iterdir())),2)

    def test_verified_product_completion_can_retire_cache_without_ota_journal(self):
        (Path(self.stores[0].root)/'transaction.json').unlink()
        old=self.package(self.stores[0],b'obsolete')
        self.assertEqual(storage.prune_update_caches(self.stores,product_complete=True),1)
        self.assertFalse(old.exists())

    def test_pending_unknown_or_malformed_records_prevent_any_deletion(self):
        old=self.package(self.stores[0],b'obsolete')
        for phase in ('downloading','recovery-required','unknown','complete'):
            self.terminal(phase);self.assertEqual(self.prune(),0);self.assertTrue(old.exists())
        self.terminal();self.stores[1].write('future-journal',{'phase':'complete'})
        self.assertEqual(self.prune(),0);self.assertTrue(old.exists())

    def test_malformed_terminal_metadata_cannot_authorize_a_sweep(self):
        old=self.package(self.stores[0],b'obsolete')
        tx=self.stores[0].read('transaction');tx.pop('profile')
        self.stores[0].write('transaction',tx)
        self.assertEqual(self.prune(),0);self.assertTrue(old.exists())

    def test_unsafe_entries_prevent_entire_sweep(self):
        old=self.package(self.stores[0],b'obsolete');other=self.package(self.stores[0],b'unsafe')
        other.unlink();other.symlink_to(old)
        self.assertEqual(self.prune(),0);self.assertTrue(old.exists());other.unlink()
        os.link(old,other)
        self.assertEqual(self.prune(),0);self.assertTrue(old.exists())

    def test_reference_change_before_delete_fails_closed(self):
        old=self.package(self.stores[0],b'obsolete');original=self.stores[0].read;calls=[]
        def read(name):
            if name=='transaction':
                calls.append(name)
                if len(calls)==2:self.stores[0].write('current-root',{'sha256':old.name})
            return original(name)
        with patch.object(self.stores[0],'read',side_effect=read):self.assertEqual(self.prune(),0)
        self.assertTrue(old.exists())

    def test_bad_digest_and_cache_symlink_are_preserved(self):
        bad=Path(self.stores[0].root)/'cache'/('c'*64);bad.write_bytes(b'wrong bytes')
        self.assertEqual(self.prune(),0);self.assertTrue(bad.exists())
        bad.unlink();cache=bad.parent;cache.rmdir();cache.symlink_to(Path(self.stores[1].root)/'cache',target_is_directory=True)
        self.assertEqual(self.prune(),0)


class StagingTests(unittest.TestCase):
    def setUp(self):
        from installation import Ownership
        self.syslog=Mock()
        logger=patch.dict(sys.modules,{"syslog":SimpleNamespace(LOG_INFO=6,syslog=self.syslog)})
        logger.start();self.addCleanup(logger.stop)
        self.stderr=io.StringIO();capture=redirect_stderr(self.stderr);capture.__enter__()
        self.addCleanup(capture.__exit__,None,None,None)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=storage.Store(Path(self.tmp.name).resolve()/'installation',uid=os.getuid())
        self.owner=Ownership(self.store);self.identifier='d'*32
        self.tree=Path(self.store.root)/('request-'+self.identifier)
        (self.tree/'root').mkdir(parents=True);(self.tree/'root-updater').mkdir()
        self.files={'root/app.ipk':b'package','root-updater/worker.py':b'worker'}
        for name,raw in self.files.items():(self.tree/name).write_bytes(raw)
        (self.tree/'worker.log').write_bytes(b'private log')

    def records(self,lease,state='complete'):
        self.record={'operation':self.identifier,'action':'install','stage':state,'state':state,'code':'verified','lease':lease['id'],'result':{'verified':True}}
        self.store.write('request-'+self.identifier,self.record)
        self.store.write('submission-'+self.identifier,{'operation':self.identifier,'action':'install','stage':'submitted',
            'staging':{n:hashlib.sha256(raw).hexdigest() for n,raw in self.files.items()}})

    def retire(self):
        import install_driver
        return install_driver.retire_staging(self.store,self.identifier,self.owner)

    def summary(self,reason,removed):
        message='cytv-retention scope=staging reason='+reason+' removed='+str(removed)
        self.assertIn(message,self.stderr.getvalue())
        self.assertTrue(any(call.args[-1]==message for call in self.syslog.call_args_list))
        self.assertNotIn(self.identifier,self.stderr.getvalue())
        self.assertNotIn(str(self.tree),self.stderr.getvalue())
        self.assertNotIn('app.ipk',self.stderr.getvalue())

    def test_staging_diagnostics_distinguish_refusal_missing_inventory_and_noop(self):
        self.assertEqual(self.retire(),0);self.summary('admission-refused',0)
        with self.owner.operation('product','product-'+self.identifier+'.json') as lease:
            self.records(lease);self.owner.stage(lease,'complete',terminal=True)
            submission=self.store.read('submission-'+self.identifier);submission.pop('staging')
            self.store.write('submission-'+self.identifier,submission)
            self.assertEqual(self.retire(),0);self.summary('missing-inventory',0)
            self.records(lease)
            self.assertEqual(self.retire(),2);self.summary('complete',2)
            self.assertEqual(self.retire(),0);self.summary('complete',0)

    def test_staging_changed_proof_and_partial_filesystem_failure_are_observable(self):
        expected={n:hashlib.sha256(raw).hexdigest() for n,raw in self.files.items()}
        self.assertEqual(storage.retire_verified_files(self.store,'request-'+self.identifier,expected,lambda:False),0)
        self.summary('proof-changed',0)
        with patch.object(storage.os,'fsync',side_effect=OSError('secret private path')):
            self.assertEqual(storage.retire_verified_files(self.store,'request-'+self.identifier,expected,lambda:True),1)
        self.summary('filesystem-error',1)
        self.assertEqual(sum((self.tree/name).exists() for name in self.files),1)
        self.assertNotIn('secret private path',self.stderr.getvalue())

    def test_post_retirement_peer_error_preserves_actual_removed_count(self):
        with self.owner.operation('product','product-'+self.identifier+'.json') as lease:
            self.records(lease);self.owner.stage(lease,'complete',terminal=True)
            with patch('install_device.UPDATER',self.tree/'private-peer'), patch('install_device.SUPERVISOR',self.tree/'missing'):
                (self.tree/'private-peer').symlink_to(self.tree/'missing')
                self.assertEqual(self.retire(),2)
            self.summary('filesystem-error',2)

    def test_terminal_staging_retires_payload_preserving_log_and_journals(self):
        with self.owner.operation('product','product-'+self.identifier+'.json') as lease:
            self.records(lease);self.owner.stage(lease,'complete',terminal=True)
            self.assertEqual(self.retire(),2)
            self.assertFalse((self.tree/'root/app.ipk').exists())
            self.assertEqual((self.tree/'worker.log').read_bytes(),b'private log')
            self.assertEqual(self.store.read('request-'+self.identifier),self.record)
            self.assertEqual(self.retire(),0)

    def test_complete_label_without_final_readback_proof_preserves_payload(self):
        with self.owner.operation('product','product-'+self.identifier+'.json') as lease:
            self.records(lease);self.owner.stage(lease,'complete',terminal=True)
            self.record['result']={'verified':False};self.store.write('request-'+self.identifier,self.record)
            self.assertEqual(self.retire(),0);self.assertTrue((self.tree/'root/app.ipk').exists())

    def test_unknown_outcome_and_unsafe_trees_are_preserved(self):
        with self.owner.operation('product','product-'+self.identifier+'.json') as lease:
            self.records(lease,state='pending');self.assertEqual(self.retire(),0)
            self.records(lease);self.owner.stage(lease,'complete',terminal=True)
            (self.tree/'root/extra').symlink_to('/etc/passwd')
            self.assertEqual(self.retire(),0)
            self.assertTrue((self.tree/'root/app.ipk').exists())

    def test_coordinator_retires_only_after_actual_final_readback(self):
        import install_driver
        from types import SimpleNamespace
        self.store.write('submission-'+self.identifier,{'operation':self.identifier,'action':'install','stage':'submitted',
            'candidate_sha256':'e'*64,'staging':{n:hashlib.sha256(raw).hexdigest() for n,raw in self.files.items()}})
        def readback():
            self.assertTrue((self.tree/'root/app.ipk').exists());return {'verified':True}
        device=SimpleNamespace(preflight=lambda *args:None,inspect=lambda:{'state':'installed'},
            require_selected_runtime=lambda *args:None,readback=readback)
        result=install_driver.Coordinator(device,self.owner,read=lambda path:None).install(self.identifier,'/verified')
        self.assertEqual(result['state'],'complete');self.assertFalse((self.tree/'root/app.ipk').exists())
        self.assertTrue((self.tree/'worker.log').exists())

    def test_hardlink_or_changed_terminal_receipt_preserves_payload(self):
        with self.owner.operation('product','product-'+self.identifier+'.json') as lease:
            self.records(lease);self.owner.stage(lease,'complete',terminal=True)
            source=self.tree/'root/app.ipk';alias=self.tree/'root-updater/worker.py'
            alias.unlink();os.link(source,alias)
            self.assertEqual(self.retire(),0);self.assertTrue(source.exists())

    def test_staging_receipt_race_prevents_deletion(self):
        with self.owner.operation('product','product-'+self.identifier+'.json') as lease:
            self.records(lease);self.owner.stage(lease,'complete',terminal=True)
            original=self.store.read;calls=[]
            def read(name):
                if name=='request-'+self.identifier:
                    calls.append(name)
                    if len(calls)==2:return dict(self.record,state='pending')
                return original(name)
            with patch.object(self.store,'read',side_effect=read):self.assertEqual(self.retire(),0)
            self.assertTrue((self.tree/'root/app.ipk').exists())

    def test_complete_resume_reads_receipt_without_replaying_retired_worker(self):
        import install_driver
        with self.owner.operation('product','product-'+self.identifier+'.json') as lease:
            self.records(lease);self.owner.stage(lease,'complete',terminal=True);self.retire()
        with patch('install_device.LocalDevice.verify_resume',side_effect=AssertionError('must not replay')):
            self.assertEqual(install_driver.resume_submit(self.identifier,self.owner),self.record)

if __name__=='__main__':unittest.main()
