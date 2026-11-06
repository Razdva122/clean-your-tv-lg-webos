"""Failed finalize cancellation never needs a working recovery/profile service."""
import hashlib
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import test_cancel_install as cases


class PendingProvisionCancellationTests(unittest.TestCase):
    def setUp(self):
        self.case=cases.CancellationTests('runTest');self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.f=self.case.f;self.recovery=self.case.recovery
        self.p=self.f.provision;self.files={}
        base=self.case.system/'var/luna-service2-dev'
        for key,folder,suffix in (('service','services.d','.service'),('role','roles.d','.service.json'),
                                  ('client','client-permissions.d','.service.json'),('api','api-permissions.d','.api.json')):
            path=base/folder/(self.p.NAME+suffix);path.parent.mkdir(parents=True,exist_ok=True)
            self.files[key]=path
        from updater.package import safe_bytes
        for name,value in (('STATE',self.f.root),('RUNTIME',self.f.root/'runtime'),('PRIVATE_SERVICE',self.f.root/'service'),('RUNNER',self.f.root/'run-recovery-service'),('FILES',self.files),('secure',lambda path:safe_bytes(path,uid=os.getuid()))):
            context=patch.object(self.p,name,value);context.start();self.addCleanup(context.stop)
        self.original={
            'service':'[D-BUS Service]\nName='+self.p.NAME+'\nExec=/usr/bin/run-js-service -n '+str(self.p.SERVICE)+'\n',
            'role':json.dumps({'appId':self.p.NAME,'allowedNames':[self.p.NAME],'permissions':[]}),
            'client':'{}','api':'{}'}
        updated=self.p.plan(self.original);entries={}
        for key,path in self.files.items():
            path.write_bytes(updated[key]);path.chmod(0o644);info=path.stat()
            entries[str(path)]={'original':self.original[key],'original_sha256':self.p.sha(self.original[key].encode()),
                               'installed_sha256':self.p.sha(updated[key]),'mode':0o644,'uid':info.st_uid,'gid':info.st_gid}
        self.saved={'version':1,'service':self.p.NAME,'files':entries}
        self.f.root_store.write('ls2-provision-snapshot',self.saved)
        (self.f.root/'service').mkdir()
        for name in self.p.PRIVATE_FILES:
            source=self.f.installed/'usr/palm/services'/self.p.NAME/name
            target=self.f.root/'service'/name;target.write_bytes(source.read_bytes());target.chmod(0o700 if name=='boot-recover.sh' else 0o600)
        (self.f.root/'run-recovery-service').write_bytes(self.p.runner_bytes());(self.f.root/'run-recovery-service').chmod(0o700)
        # This independently names the private closure expected on the TV.
        paths=[self.f.root/'run-recovery-service',*(self.f.root/'service'/n for n in self.p.PRIVATE_FILES),
               *(self.f.root/'runtime').glob('*.py')]
        paths+=[self.f.root/n for n in ('python_binding.py','python_boot.js','package_data.py','package_identity.py','startup_guard.py','updater/store.py','updater/package.py','python-launcher','python-runtime.json') if (self.f.root/n).exists()]
        pending={'version':1,'mode':'recovery-only','boot_callback':str(self.f.root/'service/boot-recover.sh'),
                 'files':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
        (self.f.root/'recovery-provision.pending.json').write_text(json.dumps(pending))
        self.f.root_store.write('recovery-failure',{'schema':1,'phase':'stock-home','reason':'negative-reply','luna_reason':'service-missing','startup_state':'unavailable'})
        self.f.root_store.write('deploy',{'version':1,'app':self.case.deploy.APP,'stage':'provision-finalize-starting'})
        self.methods=[];self.refreshes=[];self.activities=[]
        def rpc(method,payload):
            self.methods.append(method)
            if method.endswith('getSystemSettings'):return {'returnValue':True,'settings':{'defaultApps':{'unrelated':'keep'}}}
            if method.endswith('activitymanager/list'):return {'returnValue':True,'activities':self.activities}
            if method.endswith('getProfiles'):raise RuntimeError('systemprofile missing')
            return self.case.rpc(method,payload)
        self.case.device.rpc=rpc
        # New install compatibility must stay strict; cancellation must not call it.
        context=patch.object(self.p,'require_home_interfaces',side_effect=RuntimeError('systemprofile missing'))
        context.start();self.addCleanup(context.stop)
        context=patch.object(self.p,'refresh',side_effect=lambda:self.refreshes.append('scan') or {'returnValue':True})
        context.start();self.addCleanup(context.stop)

    def inspect(self):return self.case.inspect()

    def test_receiver_capability_cancellation_restores_original_registration(self):
        self.assert_receiver_capability_cancellation(['theme-receiver-v1'])

    def test_wallpaper_capability_cancellation_restores_original_registration(self):
        self.assert_receiver_capability_cancellation(['theme-receiver-v1','wallpaper-media-v1'])

    def assert_receiver_capability_cancellation(self,capabilities):
        self.saved['capabilities']=capabilities
        updated=self.p.plan(self.original,self.saved['capabilities'])
        for key,path in self.files.items():
            path.write_bytes(updated[key])
            self.saved['files'][str(path)]['installed_sha256']=self.p.sha(updated[key])
        self.f.root_store.write('ls2-provision-snapshot',self.saved)
        proof=self.inspect();self.assertEqual(proof['state'],'admissible')
        with patch('observed_install.remove',side_effect=self.remove):
            result=self.recovery.remove(self.case.identifier,self.case.candidate,proof['proof_sha256'])
        self.assertEqual(result['state'],'cancelled-and-removed')
        self.assertEqual(self.f.root_store.read('ls2-provision-snapshot'),self.saved)

    def test_compositor_alias_cancellation_restores_original_registration(self):
        self.assert_receiver_capability_cancellation(self.p.COMPOSITOR_CAPABILITIES)

    def test_unknown_receiver_capability_is_not_admitted(self):
        self.saved['capabilities']=['unknown']
        self.f.root_store.write('ls2-provision-snapshot',self.saved)
        with self.assertRaisesRegex(ValueError,'Unknown recovery capabilities'):self.inspect()

    def remove(self,*args,**kwargs):
        self.assertEqual(self.refreshes,['scan'])
        for key,path in self.files.items():self.assertEqual(path.read_text(),self.original[key])
        result=self.case.remove(*args,**kwargs)
        for path in self.files.values():path.unlink()
        return result

    def test_inspect_proves_finalize_without_systemprofile_or_any_writes(self):
        before={str(p):p.read_bytes() for p in self.f.base.rglob('*') if p.is_file()}
        status=self.inspect();self.assertEqual(status['state'],'admissible')
        self.assertEqual(before,{str(p):p.read_bytes() for p in self.f.base.rglob('*') if p.is_file()})
        self.assertFalse(any('systemprofile' in m for m in self.methods));self.assertEqual(self.refreshes,[])
        submission=self.f.owner.store.read('submission-'+self.case.identifier)
        with self.assertRaisesRegex(RuntimeError,'systemprofile missing'):
            self.case.device.verify_resume(self.case.snapshot,submission)

    def test_cancel_restores_exact_ls2_before_one_remove_and_retains_evidence(self):
        proof=self.inspect()
        with patch('observed_install.remove',side_effect=self.remove):
            result=self.recovery.remove(self.case.identifier,self.case.candidate,proof['proof_sha256'])
        self.assertEqual(result['state'],'cancelled-and-removed');self.assertEqual(len(self.case.calls),1)
        self.assertEqual(self.f.root_store.read('ls2-provision-snapshot'),self.saved)
        self.assertEqual(self.inspect()['state'],'cancelled-and-removed')
        self.case.assert_original()
        self.assertFalse(any('systemprofile' in m for m in self.methods))

    def test_status_failure_and_quiet_stale_startup_record_are_admissible(self):
        self.f.root_store.write('recovery-failure',{'schema':1,'phase':'status','reason':'negative-reply','startup_state':'starting'})
        self.f.root_store.write('recovery-service',{'schema':1,'phase':'starting','pid':54321,'attempt':'old'})
        self.assertEqual(self.inspect()['state'],'admissible')

    def test_v140_separate_audio_runtime_is_verified_as_data_only(self):
        import install_driver
        raw=b'raise RuntimeError("retained code must never execute")\n'
        relative='runtime/audio_recovery.py';sha=hashlib.sha256(raw).hexdigest()
        source=self.case.snapshot/'root';manifest=json.loads((source/'bundle.json').read_text())
        manifest['files'][relative]=sha
        for root in (source,self.f.root):
            (root/relative).write_bytes(raw);(root/relative).chmod(0o600)
            (root/'bundle.json').write_text(json.dumps(manifest))
        inventories={'root':manifest,'root-updater':json.loads((self.case.snapshot/'root-updater/bundle.json').read_text())}
        self.case.candidate=install_driver.candidate_digest(self.case.snapshot,inventories)
        submission=self.f.owner.store.read('submission-'+self.case.identifier)
        submission['candidate_sha256']=self.case.candidate;submission['root_static'][relative]=sha
        self.f.owner.store.write('submission-'+self.case.identifier,submission)
        request=self.f.owner.store.read('request-'+self.case.identifier);request['candidate_sha256']=self.case.candidate
        self.f.owner.store.write('request-'+self.case.identifier,request)
        pending=self.f.root/'recovery-provision.pending.json';value=json.loads(pending.read_text())
        value['files'][str(self.f.root/relative)]=sha;pending.write_text(json.dumps(value))
        try:status=self.inspect()
        except ValueError as error:self.fail('historical v1.4.0 cancellation was rejected: '+str(error))
        self.assertEqual(status['state'],'admissible')
        # Current installation remains bound to the current exact inventory.
        with self.assertRaises(ValueError):self.case.deploy.verify_bundle(source)

    def test_activation_readiness_activity_or_stock_write_never_admitted(self):
        for name in ('recovery-provision','profile-trial','activity-registration','stock-home-initialization','persistent-intent','startup-hook'):
            self.f.root_store.write(name,{'unexpected':True})
            with self.subTest(name=name),self.assertRaises((ValueError,OSError)):self.inspect()
            (self.f.root/(name+'.json')).unlink()
        self.activities=[{'name':self.p.NAME+'.recovery'}]
        with self.assertRaises(ValueError):self.inspect()
        self.assertEqual(self.case.calls,[])

    def test_changed_registration_or_private_service_is_rejected_before_writes(self):
        path=self.files['role'];raw=path.read_bytes();path.write_bytes(b'foreign')
        with self.assertRaises(ValueError):self.inspect()
        path.write_bytes(raw)
        service=self.f.root/'service/handlers.js';service.write_bytes(service.read_bytes()+b'\n')
        with self.assertRaises(ValueError):self.inspect()
        self.assertEqual(self.refreshes,[]);self.assertEqual(self.case.calls,[])

    def test_interrupted_ls2_restoration_resumes_without_replaying_package_remove(self):
        import cancel_provision
        proof=self.inspect();real=cancel_provision.write_registration
        def interrupted(path,entry):
            if path==self.files['role']:raise OSError('power loss')
            return real(path,entry)
        with patch.object(cancel_provision,'write_registration',side_effect=interrupted),patch('observed_install.remove',side_effect=self.remove):
            with self.assertRaises(OSError):self.recovery.remove(self.case.identifier,self.case.candidate,proof['proof_sha256'])
        self.assertEqual(self.case.calls,[]);self.assertFalse(self.f.owner.status()['terminal'])
        with patch('observed_install.remove',side_effect=self.remove):
            self.recovery.remove(self.case.identifier,self.case.candidate,proof['proof_sha256'])
        self.assertEqual(len(self.case.calls),1)

    def test_unknown_removal_never_replays_after_ls2_restore(self):
        proof=self.inspect()
        with patch('observed_install.remove',side_effect=TimeoutError('lost reply')) as remove:
            with self.assertRaises(TimeoutError):self.recovery.remove(self.case.identifier,self.case.candidate,proof['proof_sha256'])
            with self.assertRaises(ValueError):self.recovery.remove(self.case.identifier,self.case.candidate,proof['proof_sha256'])
            self.assertEqual(remove.call_count,1)
        self.assertFalse(self.f.owner.status()['terminal'])

    def test_host_device_digest_pins_both_separately_staged_modules(self):
        import importlib.util
        import cancel_install
        from updater.package import safe_bytes
        project=Path(__file__).resolve().parents[2]
        spec=importlib.util.spec_from_file_location('root_recovery_digest_tool',project/'scripts/root-install-recovery.py')
        tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)
        bundle=self.f.payload/'root-updater'
        _,modules,pin=tool.code_inventory(bundle)
        for name,raw in modules.items():(bundle/name).write_bytes(raw)
        with patch.object(cancel_install,'safe_bytes',side_effect=lambda path,**kw:safe_bytes(path,uid=os.getuid())):
            self.assertEqual(cancel_install.trusted_code_digest(bundle),pin)
            (bundle/'cancel_provision.py').write_bytes(b'changed')
            self.assertNotEqual(cancel_install.trusted_code_digest(bundle),pin)


if __name__=='__main__':unittest.main()
