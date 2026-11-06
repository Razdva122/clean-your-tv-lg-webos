"""Cancellation uses original evidence and one real remove, never install/resume."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from install_fixture import CurrentInstallation

class CancellationTests(unittest.TestCase):
    def test_packaged_entry_refuses_unsupported_runtime_before_inspection_or_removal(self):
        import contextlib,io
        output=io.StringIO()
        argv=['cancel_install.py','inspect','--operation',self.identifier,'--code-sha256','c'*64,'--report-refusal']
        with patch.object(sys,'argv',argv),patch.object(self.module,'trusted_code_digest',return_value='c'*64), \
             patch.object(self.module,'checked_store',return_value=self.f.owner.store), \
             patch.object(self.deploy,'require_node',side_effect=RuntimeError('Root requires TV Node.js 8+')), \
             patch.object(self.module.Recovery,'inspect',return_value={'state':'admissible'}) as inspect, \
             contextlib.redirect_stdout(output):
            self.module.main()
        self.assertEqual(json.loads(output.getvalue())['state'],'blocked')
        self.assertEqual(json.loads(output.getvalue())['reason'],'recovery-code-incompatible')
        inspect.assert_not_called();self.assertEqual(self.calls,[])
    def test_missing_home_interfaces_have_fixed_refusal_and_submit_nothing(self):
        original=self.device.rpc
        self.device.rpc=lambda method,payload: {} if method.endswith('getProfiles') else original(method,payload)
        with self.assertRaises(ValueError) as caught:self.inspect()
        self.assertEqual(self.module.refusal_code(caught.exception),'stock-routing-unverified')
        self.assertEqual(self.calls,[]);self.assert_original()
    def test_host_cancellation_uses_real_device_proofs_and_archives_original_receipt(self):
        from cytv import state,operations
        from cytv.root_install_recovery import RECOVERY_ENTRY
        import shlex
        host=state.Store(self.f.base/'host');profile=state.target('fixture.local','root')
        host.begin(profile,'install',stage='coordinator-submitted',product_operation=self.identifier)
        original=host.pending(profile)
        bundle=self.f.payload/'root-updater'
        manifest=json.loads((bundle/'bundle.json').read_text())
        pin=self.module.digest(dict(bundle=manifest,recovery={name:hashlib.sha256((bundle/name).read_bytes()).hexdigest()
            for name in self.module.RECOVERY_FILES}))
        self.recovery.code_sha256=pin
        calls=[];uploads={};test=self
        class Remote:
            def upload(self,path,data,mode=0o600):uploads[path]=data
            def run(self,command,**kwargs):
                words=shlex.split(command)
                if '/usr/bin/node' in words:return '/usr/bin/python3'
                if command.startswith(('umask ','mkdir ')):return ''
                test.assertIn(RECOVERY_ENTRY,words);test.assertIn('-I',words)
                test.assertEqual(host.pending(profile),original)
                action=words[words.index(RECOVERY_ENTRY)+3];calls.append(action)
                test.assertEqual(words[words.index('--operation')+1],test.identifier)
                test.assertEqual(words[words.index('--code-sha256')+1],pin)
                if action=='inspect':return json.dumps(test.inspect())
                test.assertEqual(action,'remove')
                candidate=words[words.index('--candidate')+1]
                proof=words[words.index('--proof-sha256')+1]
                # Preserve the real device reply exactly across the JSON/SSH
                # boundary: no host-side enrichment of missing binding fields.
                return json.dumps(test.recovery.remove(test.identifier,candidate,proof))
        installer=operations.Installer(Remote(),host,profile,self.f.payload,{})
        with patch('observed_install.remove',side_effect=self.remove):
            reviewed=installer.inspect_root_cancellation(original)
            installer.cancel_root_product(original,reviewed)
        self.assertEqual(calls,['inspect','inspect','remove','inspect'])
        self.assertEqual(len(self.calls),1);self.assert_original()
        self.assertIsNone(host.pending(profile))
        archive=json.loads(next(host.device_dir(profile).glob('recovery-*.json')).read_text())
        self.assertEqual(archive['previous'],original)
        self.assertEqual(archive['disposition']['state'],'cancelled-and-removed')
        self.assertEqual(archive['disposition']['code_sha256'],pin)
        self.assertTrue(any(path.endswith('/bundle.json') for path in uploads))

    def test_refusal_categories_distinguish_missing_terminal_and_foreign_routing(self):
        (self.f.root/'install-terminal.json').unlink()
        with self.assertRaises(ValueError) as caught:self.inspect()
        self.assertEqual(self.module.refusal_code(caught.exception),'package-terminal-unverified')
        self.f.root_store.write('install-terminal',self.terminal)
        with patch.object(self.recovery,'baseline',side_effect=ValueError('lg_home_routing_unconfirmed')):
            with self.assertRaises(ValueError) as caught:self.inspect()
        self.assertEqual(self.module.refusal_code(caught.exception),'stock-routing-unverified')
        self.assertEqual(self.module.refusal_code(ValueError('PRIVATE arbitrary path')),'recovery-evidence-unverified')
        self.assertEqual(self.calls,[]);self.assert_original()

    def test_recovery_modules_are_packaged_and_previous_inventory_is_inspect_only(self):
        from updater.bootstrap import verify_bundle
        bundle=self.snapshot/'root-updater'
        manifest=json.loads((bundle/'bundle.json').read_text())
        self.assertTrue({'cancel_install.py','cancel_provision.py'} <= manifest['files'].keys())
        for name in ('cancel_install.py','cancel_provision.py','clean_removal.py','cleanup_tail.js','cleanup_no_root_private.js'):
            del manifest['files'][name];(bundle/name).unlink()
        (bundle/'bundle.json').write_text(json.dumps(manifest))
        with self.assertRaises(ValueError):verify_bundle(bundle)
        self.assertEqual(verify_bundle(bundle,allow_legacy_recovery=True),manifest)
        del manifest['files']['install_driver.py']
        (bundle/'bundle.json').write_text(json.dumps(manifest))
        with self.assertRaises(ValueError):verify_bundle(bundle,allow_legacy_recovery=True)

    def setUp(self):
        self.fixture=CurrentInstallation();self.f=self.fixture.__enter__();self.addCleanup(self.fixture.__exit__,None,None,None)
        import cancel_install,deploy,install_driver
        from install_device import LocalDevice
        from updater.store import encode
        self.module=cancel_install;self.deploy=deploy;self.identifier='a'*32
        shutil.rmtree(self.f.updater)
        for path in LocalDevice.package_paths('com.cleanyourtv.root.updater'):shutil.rmtree(path)
        for name in ('recovery-provision.json','persistent-intent.json'):(self.f.root/name).unlink()
        self.original_deploy={'version':1,'app':deploy.APP,'stage':'install-observed'}
        self.f.root_store.write('deploy',self.original_deploy)
        self.terminal={'completed':True,'event':{'id':deploy.APP,'statusValue':30,'details':{'packageId':deploy.APP,'client':'com.webos.lunasend-123','ipkFile':'/var/lib/clean-your-tv-installer/cytv-root-install-test/package.ipk'}}}
        self.f.root_store.write('install-terminal',self.terminal)
        self.snapshot=self.f.snapshot(self.identifier)
        inventories=install_driver._verified_payload(self.snapshot,False)
        self.candidate=install_driver.candidate_digest(self.snapshot,inventories)
        receipt=self.f.owner.store.read('submission-'+self.identifier);receipt['candidate_sha256']=self.candidate;receipt['stage']='submitted';receipt['state']='pending';self.f.owner.store.write('submission-'+self.identifier,receipt)
        with self.f.owner.operation('product','product-'+self.identifier+'.json') as lease:
            self.record={'operation':self.identifier,'action':'install','state':'recovery_required','stage':'root-deploy','lease':lease['id'],'candidate_sha256':self.candidate,'home_changed':False,'code':'installation_requires_recovery'}
            self.f.owner.store.write('request-'+self.identifier,self.record);self.f.owner.stage(lease,'root-deploy')
        self.proc=self.f.base/'proc';self.proc.mkdir();self.system=self.f.base/'system';self.system.mkdir()
        self.device=LocalDevice();self.device.log=lambda error:None;self.apps={deploy.APP};self.calls=[]
        self.device.rpc=self.rpc;self.device.apps=lambda:set(self.apps)
        self.recovery=cancel_install.Recovery(self.device,self.f.owner,root=self.f.root,system=self.system,proc=self.proc,code_sha256='c'*64)
        self.before={name:(self.f.state/(name+'.json')).read_bytes() for name in ('request-'+self.identifier,'submission-'+self.identifier)}
    def rpc(self,method,payload):
        if method.endswith('appInstallService/status'):return {'status':{'apps':[]}}
        if method.endswith('getSystemSettings'):return {'settings':{'defaultApps':{'home':'com.webos.app.home'}}}
        if method.endswith('getProfiles'):return {'profiles':{'defaultApps':{'categories':{'home':'com.webos.app.home'}},'idleApp':{'appId':'com.webos.app.home'}}}
        raise AssertionError(method)
    def remove(self,*args,**kw):
        self.calls.append(args)
        saved=self.f.owner.store.read('cancellation-'+self.identifier)
        self.assertEqual(saved['stage'],'remove-submitting');self.assertFalse(self.f.owner.status()['terminal'])
        for path in self.device.package_paths(self.deploy.APP):shutil.rmtree(path)
        self.apps.clear()
        return {'completed':True,'event':{'id':self.deploy.APP,'details':{'packageId':self.deploy.APP,'state':'removed'}}}
    def inspect(self):return self.recovery.inspect(self.identifier,self.candidate)
    def cancel(self):
        proof=self.inspect()
        with patch('observed_install.remove',side_effect=self.remove):
            return self.recovery.remove(self.identifier,self.candidate,proof['proof_sha256'])
    def assert_original(self):
        for name,raw in self.before.items():self.assertEqual((self.f.state/(name+'.json')).read_bytes(),raw)
        self.assertEqual(self.f.root_store.read('install-terminal'),self.terminal)
    def test_inspection_has_no_device_writes_and_proves_every_original_byte(self):
        before=sorted(str(p.relative_to(self.f.base)) for p in self.f.base.rglob('*'))
        proof=self.inspect();self.assertEqual(proof['state'],'admissible')
        expected=json.loads((self.snapshot/'root/release.json').read_text())['files']
        self.assertEqual(proof['payload_files'],len(expected))
        names={Path(name).name for name in expected}
        self.assertTrue({'theme-policy.js','theme-runtime.js','home-layout.js','layout-panel.js','layout-panel.css','theme-defaults.css'}.issubset(names))
        self.assertEqual(before,sorted(str(p.relative_to(self.f.base)) for p in self.f.base.rglob('*')))
        self.assert_original()
    def test_saved_candidate_is_read_only_and_full_admission_still_checks_submission(self):
        candidate=self.recovery.saved_candidate(self.identifier)
        self.assertEqual(candidate,self.candidate)
        proof=self.recovery.inspect(self.identifier,candidate)
        self.assertEqual(proof['candidate_sha256'],candidate)
        self.assertEqual(proof['code_sha256'],'c'*64)
        self.assert_original()
        record=self.f.owner.store.read('submission-'+self.identifier)
        record['candidate_sha256']='d'*64;self.f.owner.store.write('submission-'+self.identifier,record)
        with self.assertRaisesRegex(ValueError,'original_failed_install_required'):
            self.recovery.inspect(self.identifier,self.recovery.saved_candidate(self.identifier))
        self.assertEqual(self.calls,[])

    def test_missing_or_malformed_saved_candidate_does_not_write_evidence(self):
        for value in (None,'',{'sha256':self.candidate},'A'*64):
            self.f.owner.store.write('request-'+self.identifier,{**self.record,'candidate_sha256':value})
            before=(self.f.state/('request-'+self.identifier+'.json')).read_bytes()
            with self.subTest(value=value),self.assertRaisesRegex(ValueError,'original_candidate_required'):
                self.recovery.saved_candidate(self.identifier)
            self.assertEqual((self.f.state/('request-'+self.identifier+'.json')).read_bytes(),before)
            self.assertEqual(self.calls,[])

    def test_one_remove_preserves_original_and_terminalizes_cancellation(self):
        result=self.cancel();self.assertEqual(result['state'],'cancelled-and-removed');self.assertEqual(len(self.calls),1)
        self.assertTrue(self.f.owner.status()['terminal']);self.assertEqual(self.f.owner.status()['stage'],'cancelled-and-removed')
        self.assertEqual(self.f.root_store.read('deploy')['stage'],'uninstalled-state-retained');self.assert_original()
        # The unchanged OLD coordinator takes its terminal branch, never install.
        import install_driver
        self.device.validate_completion=lambda *args:False
        self.device.resume_install=lambda *args:(_ for _ in ()).throw(AssertionError('old resume mutated'))
        install_driver.Coordinator(self.device,self.f.owner).resume(self.identifier,self.snapshot)
        self.assertTrue(self.f.owner.status()['terminal'])
        self.assertEqual(self.inspect()['state'],'cancelled-and-removed')
    def test_changed_original_or_provisioning_never_admitted(self):
        for name in ('profile-trial.json','persistent-intent.json','ls2-provision-snapshot.json','recovery-provision.pending.json','service','run-recovery-service','personalization.json'):
            path=self.f.root/name;path.symlink_to('missing')
            with self.subTest(name=name),self.assertRaises((ValueError,OSError)):self.inspect()
            path.unlink()
        target=self.f.root/'package_data.py';raw=target.read_bytes();target.write_bytes(raw+b'\n')
        with self.assertRaises(ValueError):self.inspect()
        target.write_bytes(raw)
        with self.assertRaises(ValueError):self.recovery.inspect(self.identifier,'0'*64)
        self.assertFalse(self.f.owner.status()['terminal']);self.assertEqual(self.calls,[])
    def test_installer_activity_live_worker_and_stale_proof_rejected(self):
        worker=self.proc/'123';worker.mkdir();(worker/'cmdline').write_bytes(str(self.snapshot/'root-updater/install_driver.py').encode()+b'\0')
        with self.assertRaises(ValueError):self.inspect()
        shutil.rmtree(worker)
        proof=self.inspect();self.device.rpc=lambda *args:{'status':{'apps':[{}]}}
        with self.assertRaises(ValueError):self.recovery.remove(self.identifier,self.candidate,proof['proof_sha256'])
        self.assertEqual(self.calls,[])
    def test_unknown_removal_outcome_is_retained_and_never_replayed(self):
        proof=self.inspect()
        with patch('observed_install.remove',side_effect=TimeoutError('lost reply')) as remove:
            with self.assertRaises(TimeoutError):self.recovery.remove(self.identifier,self.candidate,proof['proof_sha256'])
            with self.assertRaises(ValueError):self.recovery.remove(self.identifier,self.candidate,proof['proof_sha256'])
            self.assertEqual(remove.call_count,1)
        self.assertFalse(self.f.owner.status()['terminal']);self.assert_original()
        self.assertEqual(self.f.root_store.read('deploy')['stage'],'cancellation-admitted')
    def test_crash_before_separate_receipt_already_blocks_old_resume(self):
        proof=self.inspect();write=self.f.owner.store.write
        def crash(name,value):
            if name=='cancellation-'+self.identifier:raise OSError('power loss before receipt')
            return write(name,value)
        with patch.object(self.f.owner.store,'write',side_effect=crash):
            with self.assertRaises(OSError):self.recovery.remove(self.identifier,self.candidate,proof['proof_sha256'])
        self.assertEqual(self.f.root_store.read('deploy')['stage'],'cancellation-admitted')
        import install_driver
        with patch.object(self.deploy,'command',side_effect=AssertionError('provision attempted')) as command:
            install_driver.Coordinator(self.device,self.f.owner).resume(self.identifier,self.snapshot)
            command.assert_not_called()
        # Old resume may write its own failure record, so recovery must reject
        # changed original evidence, never silently bless the new request.
        with self.assertRaises(ValueError):self.inspect()

    def test_crash_after_atomic_admission_recovers_without_separate_receipt(self):
        proof=self.inspect();write=self.f.owner.store.write
        def crash(name,value):
            if name=='cancellation-'+self.identifier:raise OSError('power loss before receipt')
            return write(name,value)
        with patch.object(self.f.owner.store,'write',side_effect=crash):
            with self.assertRaises(OSError):self.recovery.remove(self.identifier,self.candidate,proof['proof_sha256'])
        with patch('observed_install.remove',side_effect=self.remove):
            result=self.recovery.remove(self.identifier,self.candidate,proof['proof_sha256'])
        self.assertEqual(result['state'],'cancelled-and-removed');self.assert_original()

    def test_crash_after_final_deploy_write_can_finish_original_lease(self):
        proof=self.inspect();write=self.f.owner.store.write
        def crash(name,value):
            if name=='cancellation-'+self.identifier and value.get('stage')=='cancelled-and-removed':raise OSError('power loss')
            return write(name,value)
        with patch('observed_install.remove',side_effect=self.remove),patch.object(self.f.owner.store,'write',side_effect=crash):
            with self.assertRaises(OSError):self.recovery.remove(self.identifier,self.candidate,proof['proof_sha256'])
        self.assertFalse(self.f.owner.status()['terminal'])
        with patch('observed_install.remove',side_effect=AssertionError('replayed remove')):
            self.recovery.remove(self.identifier,self.candidate,proof['proof_sha256'])
        self.assertTrue(self.f.owner.status()['terminal']);self.assert_original()

    def test_cancelled_record_without_terminal_lease_does_not_announce_disposition(self):
        proof=self.inspect()
        with patch('observed_install.remove',side_effect=self.remove),patch.object(self.f.owner,'stage',side_effect=OSError('power loss before lease terminal')):
            with self.assertRaises(OSError):self.recovery.remove(self.identifier,self.candidate,proof['proof_sha256'])
        self.assertEqual(self.inspect()['state'],'cancellation-terminal-pending')
        with patch('observed_install.remove',side_effect=AssertionError('replayed remove')):
            self.recovery.remove(self.identifier,self.candidate,proof['proof_sha256'])
        self.assertEqual(self.inspect()['state'],'cancelled-and-removed');self.assert_original()

    def test_cancelled_inspect_never_cleans_up_package_remainders(self):
        self.cancel()
        package=self.device.package_paths(self.deploy.APP)[1];package.mkdir()
        with self.assertRaises(ValueError):self.inspect()
        self.assertTrue(package.is_dir())

    def test_saved_terminal_readback_finishes_without_replay_after_crash(self):
        proof=self.inspect();real=self.recovery.verify_absent
        with patch('observed_install.remove',side_effect=self.remove),patch.object(self.recovery,'verify_absent',side_effect=OSError('readback unavailable')):
            with self.assertRaises(OSError):self.recovery.remove(self.identifier,self.candidate,proof['proof_sha256'])
        with patch('observed_install.remove',side_effect=AssertionError('replayed remove')):
            self.recovery.remove(self.identifier,self.candidate,proof['proof_sha256'])
        self.assertTrue(self.f.owner.status()['terminal']);self.assert_original()

if __name__=='__main__':unittest.main()
