"""Synthetic private writers and real writable SDK bytes; no installed adoption."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import package_identity as p
from updater.store import Store
from cytv.package import ipk

class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name).resolve();self.uid=os.getuid()
        self.states={owner:self.base/name for owner,name in ((p.ROOT,'root'),(p.UPDATER,'updater'),(p.SYSTEM,'system'))}
        self.stores={owner:Store(path,uid=self.uid) for owner,path in self.states.items()}
        self.installed=self.base/'apps';self.packages={};p._CACHE.clear()
        for owner in self.states:(self.states[owner]/'cache').mkdir(mode=0o700)
        for owner in self.states:
            self.packages[owner]=self.package(owner,'1.0.0');self.install(owner,self.packages[owner])
        self.prior=self.packages[p.ROOT][0];self.candidate=self.package(p.ROOT,'1.1.0')[0]
        self.stores[p.UPDATER].write('current',self.prior)
        self.stores[p.UPDATER].write('installed-package',{'schema':1,'files':self.packages[p.UPDATER][2],'executable':[]})
    def tearDown(self):self.temp.cleanup()
    def package(self,owner,version):
        ap='usr/palm/applications/'+owner+'/';pkg='usr/palm/packages/'+owner+'/packageinfo.json'
        files={ap+'appinfo.json':json.dumps({'id':owner,'version':version,'type':'web','main':'index.html',**({'systemUpdateProtocol':1} if owner==p.ROOT else {})}).encode(),ap+'index.html':version.encode(),pkg:json.dumps({'id':owner,'app':owner,'version':version,'services':[owner+'.service']}).encode()}
        raw=ipk(owner,version,files);descriptor={'version':version,'sha256':p.digest(raw),'size':len(raw),'local':True}
        target=self.states[p.UPDATER] if owner==p.ROOT else self.states[owner]
        (target/'cache'/(descriptor['sha256']+'.ipk')).write_bytes(raw)
        return descriptor,files,{n:p.digest(b) for n,b in files.items()},raw
    def install(self,owner,package):
        for name,raw in package[1].items():
            target=self.installed/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);target.chmod(0o777)
            current=target.parent
            while current!=self.base:current.chmod(0o777);current=current.parent
    def identity(self,owner=p.ROOT,purpose='current',full=False):
        return p.identity(owner,states=self.states,installed=self.installed,uid=self.uid,purpose=purpose,full=full)
    def tx(self,phase='preparing'):
        return dict(schema=1,created=1,updated=2,id='a'*32,profile='profile-'+'a'*32,profileDigest='b'*64,phase=phase,rollbackAttempted=False,prior=self.prior,candidate=self.candidate,installEvidence={'submitted':None,'terminal':None},rollbackEvidence={'submitted':None,'terminal':None})
    def save(self,tx):self.stores[p.UPDATER].write('transaction',tx)
    def success(self):return {'submitted':{'request':'original'},'terminal':{'success':True}}
    def test_all_owner_data_accepts_only_private_originals(self):
        own=self.packages[p.SYSTEM];descriptor=own[0]
        terminal={'completed':True,'event':{'id':p.SYSTEM,'statusValue':30,'details':{'packageId':p.SYSTEM,'client':'com.webos.lunasend-99','ipkFile':'/var/lib/clean-your-tv-installer/cytv-root-install-fixture/package.ipk'}}}
        self.stores[p.SYSTEM].write('bootstrap-bundle',{'schema':1,'package':{k:descriptor[k] for k in ('sha256','size')}})
        self.stores[p.SYSTEM].write('bootstrap',{'phase':'complete'})
        self.stores[p.SYSTEM].write('installed-terminal',terminal)
        self.stores[p.SYSTEM].write('installed-package',{'schema':1,'package':descriptor,'files':own[2]})
        for owner in self.states:self.assertEqual(self.identity(owner,full=True)['version'],'1.0.0')
        self.stores[p.SYSTEM].write('installed-terminal',{'completed':True})
        with self.assertRaises(ValueError):self.identity(p.SYSTEM)
    def test_cache_is_bound_to_reread_private_anchor_and_installed_bytes(self):
        with patch.object(p,'members',wraps=p.members) as parse:
            self.identity();self.identity();self.assertEqual(parse.call_count,1)
            raw=self.packages[p.ROOT][1]['usr/palm/applications/'+p.ROOT+'/appinfo.json']
            path=self.installed/'usr/palm/applications'/p.ROOT/'appinfo.json'
            path.write_bytes(raw.replace(b'1.0.0',b'9.0.0'))
            with self.assertRaises(ValueError):self.identity()
            path.write_bytes(raw);self.identity()
            target=self.states[p.UPDATER]/'cache'/(self.prior['sha256']+'.ipk');target.write_bytes(b'x'*self.prior['size'])
            with self.assertRaises(ValueError):self.identity()
    def test_candidate_requires_original_terminal_and_normal_rearm_waits(self):
        tx=self.tx('installing');tx['installEvidence']={'submitted':{'request':'original'},'terminal':None};self.save(tx)
        self.install(p.ROOT,self.package(p.ROOT,'1.1.0'))
        for purpose in ('current','worker','admission','live'):
            with self.assertRaises(p.TransitionUnknown):self.identity(purpose=purpose)
        tx['installEvidence']=self.success();tx['phase']='verifying';self.save(tx)
        self.assertEqual(self.identity(purpose='worker')['version'],'1.1.0')
        self.assertEqual(self.identity(purpose='admission')['version'],'1.1.0')
        with self.assertRaises(p.TransitionUnknown):self.identity(purpose='live')
        with self.assertRaises(p.TransitionUnknown):self.identity()
        tx['phase']='complete';self.save(tx)
        with self.assertRaises(ValueError):self.identity()
        self.stores[p.UPDATER].write('current',self.candidate);self.assertEqual(self.identity()['version'],'1.1.0')
    def test_proved_rollback_health_selects_prior_only(self):
        tx=self.tx('verifying-rollback');tx['rollbackAttempted']=True;tx['installEvidence']=self.success();tx['rollbackEvidence']=self.success();self.save(tx)
        self.assertEqual(self.identity(purpose='worker')['version'],'1.0.0')
        with self.assertRaises(p.TransitionUnknown):self.identity(purpose='live')
        self.install(p.ROOT,self.package(p.ROOT,'1.1.0'))
        with self.assertRaises(ValueError):self.identity(purpose='worker')
    def test_missing_private_cache_and_writable_private_receipt_never_adopt_sdk(self):
        target=self.states[p.UPDATER]/'cache'/(self.prior['sha256']+'.ipk');target.unlink()
        with self.assertRaises((ValueError,OSError)):self.identity()
        self.package(p.ROOT,'1.0.0');(self.states[p.UPDATER]/'current.json').chmod(0o777)
        with self.assertRaises(ValueError):self.identity()
    def test_external_deletion_remains_absent_despite_private_cache(self):
        (self.installed/'usr/palm/applications'/p.ROOT/'appinfo.json').unlink()
        with self.assertRaises(FileNotFoundError):self.identity()
    def system_tx(self,phase='installing'):
        tx=self.tx(phase);tx['edition']='root';tx['prior']={'schema':1,'edition':'root','components':[]};tx['candidate']=copy.deepcopy(tx['prior']);tx['components']=[]
        for name,owner in (('root',p.ROOT),('root-updater',p.UPDATER),('root-infrastructure',None)):
            prior=self.prior if owner==p.ROOT else self.packages[p.UPDATER][0]
            candidate=self.candidate if owner==p.ROOT else self.package(p.UPDATER,'1.1.0')[0]
            for key,desc in (('prior',prior),('candidate',candidate)):
                tx[key]['components'].append(dict(desc,name=name,application=owner,kind='ipk' if owner else 'infrastructure'))
                if owner:
                    source=self.states[p.UPDATER]/'cache'/(desc['sha256']+'.ipk')
                    (self.states[p.SYSTEM]/'cache'/desc['sha256']).write_bytes(source.read_bytes())
            tx['components'].append(dict(name=name,version=candidate['version'],installEvidence={'intent':False,'submitted':None,'terminal':None},rollbackEvidence={'intent':False,'submitted':None,'terminal':None}))
        return tx
    def completed_rollback(self):
        tx=self.system_tx('rolling-back');tx.update(homeResumePhase='complete',resumeCycle='rollback')
        for c in tx['components']:c['installEvidence']=dict(self.success(),intent=True)
        self.stores[p.SYSTEM].write('transaction',tx)
        self.stores[p.UPDATER].write('current',dict(self.candidate,writer={'owner':'system-update','id':tx['id']}))
        self.install(p.ROOT,self.package(p.ROOT,'1.1.0'))
        return tx

    def test_retained_rollback_does_not_revoke_live_health_before_suspension(self):
        # Real package selector -> device presence -> health context. A declared
        # rollback has not changed any installed byte or captured Home intent.
        import device_adapter as d, intent_runtime, persistent_health
        from persistent_store import Store as IntentStore
        from persistent_recovery import Coordinator
        tx=self.completed_rollback();root=self.states[p.ROOT]
        with patch.object(p,'STATES',self.states),patch.object(d,'STATE',root),patch.object(d,'EXPECTED_UID',self.uid),patch.object(d,'APPLICATIONS',self.installed/'usr/palm/applications'),patch.object(d,'FAILSAFE',self.base/'failsafe'),patch.object(intent_runtime,'boot_identity',return_value='boot:1'):
            store=IntentStore(root);initial=store.read()
            trial,_=store.apply(initial,dict(kind='enable',generation=0,boot='boot:1',token='attempt'))
            active,_=store.apply(trial,dict(kind='confirmed',generation=1,token='attempt'))
            Coordinator(store).write_binding(dict(version=1,generation=1,token='attempt',transaction='route',restored=False))
            self.assertTrue(d.home_present(purpose='live'),'pre-ticket rollback cannot synthesize package removal')
            self.assertTrue(persistent_health.authorized('route'),'real health authority must survive until updater captures intent')
            self.assertEqual(store.read(),active)
            with self.assertRaises(p.TransitionUnknown):self.identity(purpose='current')
            # Once suspension completes, mutation still revokes live authority.
            tx['rollbackAttempted']=True;self.stores[p.SYSTEM].write('transaction',tx)
            self.assertFalse(persistent_health.authorized('route'))

    def test_retained_rollback_live_exception_requires_committed_untouched_owner(self):
        for damage in ('no-cycle','no-completion','attempted','failed-install','unknown-install',
                       'rollback-intent','writer','sdk','cache'):
            with self.subTest(damage=damage):
                tx=self.completed_rollback()
                if damage=='no-cycle':tx.pop('resumeCycle')
                elif damage=='no-completion':tx.pop('homeResumePhase')
                elif damage=='attempted':tx['rollbackAttempted']=True
                elif damage=='failed-install':tx['components'][1]['installEvidence']['terminal']['success']=False
                elif damage=='unknown-install':tx['components'][2]['installEvidence']['terminal']=None
                elif damage=='rollback-intent':tx['rollbackAttempted']=True;tx['components'][0]['rollbackEvidence']['intent']=True
                elif damage=='writer':self.stores[p.UPDATER].write('current',dict(self.candidate,writer={'owner':'system-update','id':'c'*32}))
                elif damage=='sdk':(self.installed/'usr/palm/applications'/p.ROOT/'index.html').unlink()
                else:(self.states[p.SYSTEM]/'cache'/self.candidate['sha256']).write_bytes(b'corrupt')
                self.stores[p.SYSTEM].write('transaction',tx)
                with self.assertRaises((ValueError,OSError)):self.identity(purpose='live')

    def test_system_per_component_phase_and_stale_baseline_cannot_override(self):
        tx=self.system_tx();tx['components'][0]['installEvidence']=dict(self.success(),intent=True)
        self.stores[p.SYSTEM].write('transaction',tx);self.install(p.ROOT,self.package(p.ROOT,'1.1.0'))
        self.assertEqual(self.identity(purpose='worker')['version'],'1.1.0')
        self.assertEqual(self.identity(p.UPDATER,purpose='worker')['version'],'1.0.0')
        tx['components'][1]['installEvidence']={'intent':True,'submitted':None,'terminal':None};self.stores[p.SYSTEM].write('transaction',tx)
        with self.assertRaises(p.TransitionUnknown):self.identity(p.UPDATER,purpose='worker')
        (self.states[p.SYSTEM]/'transaction.json').unlink()
        self.stores[p.SYSTEM].write('baseline',tx['prior']);self.stores[p.UPDATER].write('current',self.candidate)
        self.assertEqual(self.identity()['version'],'1.1.0')

    def test_missing_current_never_falls_back_to_old_root_release(self):
        (self.states[p.UPDATER]/'current.json').unlink()
        self.stores[p.ROOT].write('release',{'application_id':p.ROOT,'files':self.packages[p.ROOT][2]})
        with self.assertRaises(ValueError):self.identity()

    def test_system_writer_blocks_standalone_startup_and_committed_conflicts(self):
        tx=self.system_tx();self.stores[p.SYSTEM].write('transaction',tx)
        self.assertFalse(p.worker_allowed(p.UPDATER,states=self.states,uid=self.uid))
        tx['phase']='complete';tx['homeResumePhase']='complete'
        for c in tx['components']:c['installEvidence']=dict(self.success(),intent=True)
        self.stores[p.SYSTEM].write('transaction',tx)
        self.assertTrue(p.worker_allowed(p.UPDATER,states=self.states,uid=self.uid))
        with self.assertRaisesRegex(ValueError,'current disagree'):self.identity()
        self.stores[p.UPDATER].write('current',dict(self.candidate,writer={'owner':'system-update','id':tx['id']}))
        self.install(p.ROOT,self.package(p.ROOT,'1.1.0'))
        self.assertEqual(self.identity()['version'],'1.1.0')
        newer=self.package(p.ROOT,'1.2.0');standalone=self.tx('complete')
        standalone.update(prior=dict(self.candidate,writer={'owner':'system-update','id':tx['id']}),candidate=newer[0],installEvidence=self.success(),homeResumePhase='complete')
        standalone['phase']='preparing';standalone['installEvidence']={'submitted':None,'terminal':None};self.save(standalone)
        with self.assertRaises(p.TransitionUnknown):self.identity()
        self.assertEqual(self.identity(purpose='worker')['version'],'1.1.0')
        standalone.update(phase='verifying',installEvidence=self.success());self.save(standalone);self.install(p.ROOT,newer)
        self.assertEqual(self.identity(purpose='worker')['version'],'1.2.0')
        with self.assertRaises(p.TransitionUnknown):self.identity()
        standalone['phase']='complete'
        self.save(standalone);self.stores[p.UPDATER].write('current',dict(newer[0],writer={'owner':'root-update','id':standalone['id'],'system':tx['id']}));self.install(p.ROOT,newer)
        self.assertEqual(self.identity()['version'],'1.2.0')

        newest=self.package(p.ROOT,'1.3.0');standalone.update(id='c'*32,profile='profile-'+'c'*32,prior=self.stores[p.UPDATER].read('current'),candidate=newest[0])
        self.save(standalone);self.stores[p.UPDATER].write('current',dict(newest[0],writer={'owner':'root-update','id':standalone['id'],'system':tx['id']}));self.install(p.ROOT,newest)
        self.assertEqual(self.identity()['version'],'1.3.0')

    def test_original_failed_install_can_rollback_partial_sdk_without_replay(self):
        from updater.core import Manager
        from updater.device import Device
        from updater.store import encode
        from test_update_core import profile
        tx=self.tx('rolling-back');tx['installEvidence']={'submitted':{'original':'request'},'terminal':{'success':False}}
        snapshot=profile();self.stores[p.UPDATER].write(tx['profile'],snapshot);tx['profileDigest']=p.digest(encode(snapshot));self.save(tx)
        (self.installed/'usr/palm/applications'/p.ROOT/'appinfo.json').unlink()
        device=Device(self.stores[p.UPDATER],root_state=self.states[p.ROOT],installed=self.installed)
        device.integrity=lambda:None;device.repair_registration=lambda:None;device.restore_route=lambda:None;device.routing_status=lambda:{'active':False,'safe':True};device.launch=lambda:None;device.now=lambda:1000
        def install(owner,path,**kw):
            self.assertEqual(owner,p.ROOT);self.assertEqual(Path(path).name,self.prior['sha256']+'.ipk')
            kw['on_ready']();self.install(p.ROOT,self.packages[p.ROOT]);return {'completed':True,'event':{'statusValue':30}}
        from updater.package import safe_bytes
        with patch('updater.device.safe_bytes',side_effect=lambda path,**kw:safe_bytes(path,**{**kw,'uid':self.uid})),patch('observed_install.install',side_effect=install) as submit:
            with self.assertRaises(p.TransitionUnknown):device.components_present()
            manager=Manager(self.stores[p.UPDATER],device);result=manager.run()
            self.assertEqual(result['phase'],'verifying-rollback');self.assertEqual(submit.call_count,1)
            manager.ready(tx['id'],self.prior['version']);self.assertEqual(manager.run()['phase'],'rolled-back')
            self.assertEqual(self.identity()['version'],'1.0.0')
            self.assertEqual(submit.call_count,1)

    def test_captured_prior_archive_bytes_differ_but_private_payloads_agree(self):
        from cytv.package import read_ar,ar,tgz
        tx=self.system_tx('preparing');raw=self.packages[p.ROOT][3];parts=read_ar(raw)
        parts['control.tar.gz']=tgz({'control':('Package: '+p.ROOT+'\nVersion: 1.0.0\nDescription: Explicit captured baseline\n').encode()})
        captured=ar(parts);prior=tx['prior']['components'][0];prior.update(sha256=p.digest(captured),size=len(captured))
        (self.states[p.SYSTEM]/'cache'/prior['sha256']).write_bytes(captured);self.stores[p.SYSTEM].write('transaction',tx)
        self.assertNotEqual(prior['sha256'],self.prior['sha256'])
        self.assertEqual(self.identity(purpose='worker')['version'],'1.0.0')
        with self.assertRaises(p.TransitionUnknown):self.identity()
        tx['phase']='complete'
        for c in tx['components']:c['installEvidence']=dict(self.success(),intent=True)
        self.stores[p.SYSTEM].write('transaction',tx);self.install(p.ROOT,self.package(p.ROOT,'1.1.0'))
        self.assertEqual(self.identity(purpose='worker')['version'],'1.1.0')
        with self.assertRaises(p.TransitionUnknown):self.identity()

    def test_original_bootstrap_is_explicit_and_never_normal_current_fallback(self):
        root=self.states[p.ROOT];version=self.prior['version']
        self.stores[p.ROOT].write('deploy',{'app':p.ROOT,'stage':'installed-recovery-only'})
        self.stores[p.ROOT].write('release',{'application_id':p.ROOT,'version':version,'files':self.packages[p.ROOT][2]})
        self.stores[p.ROOT].write('bundle',{'package':p.ROOT+'_'+version+'_all.ipk','files':{'release.json':p.digest((root/'release.json').read_bytes())}})
        self.stores[p.ROOT].write('install-terminal',{'completed':True,'event':{'id':p.ROOT,'statusValue':30,'details':{'packageId':p.ROOT,'client':'com.webos.lunasend-99','ipkFile':'/var/lib/clean-your-tv-installer/cytv-root-install-fixture/package.ipk'}}})
        self.assertEqual(p.bootstrap_inventory(root,uid=self.uid),self.packages[p.ROOT][2])
        (self.states[p.UPDATER]/'current.json').unlink()
        with self.assertRaises(ValueError):self.identity()
        self.stores[p.ROOT].write('install-terminal',{'completed':True})
        with self.assertRaises(ValueError):p.bootstrap_inventory(root,uid=self.uid)

    def test_aborted_later_system_transaction_preserves_prior_published_owners(self):
        tx=self.system_tx();tx.update(phase='aborted',homeResumePhase='aborted',id='d'*32,profile='profile-'+'d'*32)
        root=self.package(p.ROOT,'1.1.0');updater=self.package(p.UPDATER,'1.1.0')
        for release in ('prior','candidate'):
            tx[release]['components'][0].update(root[0]);tx[release]['components'][1].update(updater[0])
        for c,target in zip(tx['components'],tx['candidate']['components']):c['version']=target['version']
        self.stores[p.SYSTEM].write('transaction',tx)
        self.stores[p.UPDATER].write('current',dict(root[0],writer={'owner':'system-update','id':'c'*32}))
        self.stores[p.UPDATER].write('installed-package',{'schema':1,'files':updater[2],'executable':[]})
        self.install(p.ROOT,root);self.install(p.UPDATER,updater)
        old=self.tx('complete');old['installEvidence']=self.success();self.save(old)
        self.assertEqual(self.identity()['version'],'1.1.0')
        self.assertEqual(self.identity(p.UPDATER)['version'],'1.1.0')

    def test_external_deletion_of_untouched_owner_is_not_a_transition_escape(self):
        tx=self.system_tx();tx['components'][0]['installEvidence']=dict(self.success(),intent=True)
        self.stores[p.SYSTEM].write('transaction',tx)
        (self.installed/'usr/palm/applications'/p.UPDATER/'appinfo.json').unlink()
        with self.assertRaises(FileNotFoundError):self.identity(p.UPDATER,purpose='worker')
        (self.states[p.SYSTEM]/'transaction.json').unlink();self.save(self.tx('preparing'))
        (self.installed/'usr/palm/applications'/p.ROOT/'appinfo.json').unlink()
        with self.assertRaises(FileNotFoundError):self.identity(purpose='worker')
