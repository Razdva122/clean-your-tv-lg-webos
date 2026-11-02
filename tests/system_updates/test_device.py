"""Real bounded archive and fixed-path device effects, without a TV bus."""
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from test_core import Store

def digest(raw):return hashlib.sha256(raw).hexdigest()
def tar(files):
    output=io.BytesIO()
    with tarfile.open(fileobj=output,mode='w:gz') as archive:
        for name,raw in files.items():
            info=tarfile.TarInfo(name);info.size=len(raw);info.mode=0o600;archive.addfile(info,io.BytesIO(raw))
    return output.getvalue()
def ipk(app='com.gathin.tvhome',foreign=False):
    prefix='usr/palm/applications/'+app+'/'
    files={prefix+'appinfo.json':json.dumps({'id':app,'version':'1.0.0','type':'web','main':'index.html','systemUpdateProtocol':1}).encode(),prefix+'index.html':b'Home','usr/palm/packages/'+app+'/packageinfo.json':json.dumps({'id':app,'app':app,'version':'1.0.0','services':[]}).encode()}
    if foreign:files['etc/passwd']=b'bad'
    parts={'debian-binary':b'2.0\n','control.tar.gz':tar({'control':('Package: '+app+'\nVersion: 1.0.0\n').encode()}),'data.tar.gz':tar(files)};out=b'!<arch>\n'
    for name,data in parts.items():out+=(name+'/').ljust(16).encode()+b'0           0     0     100644  '+str(len(data)).ljust(10).encode()+b'`\n'+data+(b'\n' if len(data)%2 else b'')
    return out

class DeviceBase(unittest.TestCase):
    def setUp(self):
        try:self.mod=importlib.import_module('system_updater.device')
        except ModuleNotFoundError:self.fail('fixed device adapter is missing')
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(os.path.realpath(self.tmp.name));self.store=Store(self.root/'state',uid=os.getuid());(self.root/'state/cache').mkdir();(self.root/'code').mkdir()
        self.store.write('legacy-lockdown',{'schema':1,'files':{}})
        self.device=self.mod.Device(self.store,code=self.root/'code',root_state=self.root/'root',root_updater=self.root/'root-updater',installed=self.root/'installed',uid=os.getuid())
        # These focused effects tests supply presence; real private owner/phase
        # authentication is exercised by test_package_identity and shared setup.
        self.device.require_components=lambda:None
        # These cases isolate existing ownership/recovery boundaries; graphics has separate real-adapter fixtures.
        self.device.graphics_resolution=lambda:'1920x1080'
        self.device.require_graphics=lambda *args:None
        for app in ('com.cleanyourtv.system.updater','com.cleanyourtv.root.preview','com.cleanyourtv.root.updater'):
            path=self.root/('installed/usr/palm/applications/'+app+'/appinfo.json');path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps({'id':app}))
    def tearDown(self):self.tmp.cleanup()
    def baseline(self,value):
        c=next(c for c in value['components'] if c['name']=='root-infrastructure')
        (self.root/'code/infrastructure-paths.json').write_text(json.dumps(sorted(set(c['files'])|set(c.get('absent',[])))))
        self.store.write('baseline',value)

class Tests(DeviceBase):
    def test_package_foreign_paths_and_identity_rejected(self):
        raw=ipk();descriptor={'name':'home','application':'com.gathin.tvhome','version':'1.0.0','sha256':digest(raw),'size':len(raw),'kind':'ipk'};self.assertTrue(self.device.inspect(raw,descriptor))
        raw=ipk(foreign=True);descriptor.update(sha256=digest(raw),size=len(raw))
        with self.assertRaises(ValueError):self.device.inspect(raw,descriptor)
    def test_infrastructure_exact_baseline_allowlist_and_no_symlinks(self):
        raw=tar({'runtime/cli.py':b'new','updater/service.js':b'code'});c={'name':'root-infrastructure','version':'1.0.0','kind':'infrastructure','sha256':digest(raw),'size':len(raw),'files':{'runtime/cli.py':digest(b'new'),'updater/service.js':digest(b'code')},'local':True}
        self.baseline({'edition':'root','components':[c]});self.assertEqual(set(self.device.inspect(raw,c)),set(c['files']))
        bad=tar({'runtime/cli.py':b'new','updater/service.js':b'code','runtime/../outside':b'bad'});c.update(sha256=digest(bad),size=len(bad))
        with self.assertRaises(ValueError):self.device.inspect(bad,c)
    def test_supervisor_integrity_detects_code_change(self):
        p=self.root/'code/fixed.py';p.write_bytes(b'trusted');self.store.write('infrastructure',{'schema':1,'code':{'fixed.py':digest(b'trusted')}});self.device.integrity();p.write_bytes(b'tampered')
        with self.assertRaises(ValueError):self.device.integrity()
    def test_removal_journal_blocks_integrity_before_legacy_writes(self):
        from unittest.mock import patch
        p=self.root/'code/fixed.py';p.write_bytes(b'trusted')
        self.store.write('infrastructure',{'schema':1,'code':{'fixed.py':digest(b'trusted')}})
        for raw in ('{"phase":"disabled"}','{','null'):
            with self.subTest(raw=raw):
                (self.root/'state/cytv-removal.json').write_text(raw)
                before={str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
                with patch.object(self.device,'enforce_legacy_lockdown') as enforce:
                    with self.assertRaisesRegex(ValueError,'removal'):self.device.integrity()
                    enforce.assert_not_called()
                with self.assertRaisesRegex(ValueError,'removal'):self.device.enforce_legacy_lockdown()
                self.assertEqual(before,{str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_cached_bytes_are_rechecked_before_mutation(self):
        raw=ipk();c={'name':'home','application':'com.gathin.tvhome','version':'1.0.0','kind':'ipk','sha256':digest(raw),'size':len(raw),'local':True};(self.root/'state/cache'/c['sha256']).write_bytes(b'tampered')
        with self.assertRaises(ValueError):self.device.inspect(self.device.cache_bytes(c),c)
    def test_unknown_legacy_transaction_blocks(self):
        self.device.legacy_states=[self.root/'legacy.json'];self.device.legacy_states[0].write_text('{"phase":"installing"}')
        with self.assertRaises(ValueError):self.device.check_legacy()
        self.device.legacy_states[0].write_text('{"phase":"complete"}');self.device.check_legacy()

if __name__=='__main__':unittest.main()

class ExistingPackageTests(DeviceBase):
    def test_public_ordinary_package_directory_entries_are_supported(self):
        import sys
        sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
        from cytv.package import ipk as build_ipk, data_files
        files=data_files(ipk());raw=build_ipk('com.gathin.tvhome','1.0.0',files)
        c={'name':'home','application':'com.gathin.tvhome','version':'1.0.0','kind':'ipk','sha256':digest(raw),'size':len(raw)}
        self.assertTrue(self.device.inspect(raw,c))
    def test_helper_empty_state_marker_is_compatible_but_preferences_are_forbidden(self):
        from cytv.package import ipk as build_ipk, data_files
        app='com.local.nativehome';files=data_files(ipk(app));files['usr/palm/applications/'+app+'/state/.keep']=b''
        raw=build_ipk(app,'1.0.0',files);c={'name':'helper','application':app,'version':'1.0.0','kind':'ipk','sha256':digest(raw),'size':len(raw)}
        self.assertTrue(self.device.inspect(raw,c));files['usr/palm/applications/'+app+'/state/blocked']=b'';raw=build_ipk(app,'1.0.0',files);c.update(sha256=digest(raw),size=len(raw))
        with self.assertRaises(ValueError):self.device.inspect(raw,c)

class PreferenceBase(DeviceBase):
    def setUp(self):
        super().setUp()
        self.events=[]
        self.device.boot=lambda:'boot-one'
        self.device._stop_renewal=lambda:self.events.append('stop')
        self.device._cancel_renewal=lambda:self.events.append('cancel')
        self.device.rpc=lambda uri,payload:self.events.append(uri) or {'returnValue':True,'state':{'enabled':True}}
        self.settings=self.root/'installed/usr/palm/services/com.gathin.tvhome.renewal/state/settings.json';self.settings.parent.mkdir(parents=True);self.settings.write_text('{"enabled":true,"preferenceTouched":true}')
        self.tx={'id':'a'*32,'edition':'no-root','phase':'complete'};self.store.write('transaction',self.tx)

class PreferenceTests(PreferenceBase):
    def test_renewal_is_durably_paused_before_replacement(self):
        self.device._pause_renewal(self.tx);state=json.loads(self.settings.read_bytes());self.assertFalse(state['enabled']);self.assertTrue(state['updatePause']['wasEnabled']);self.assertEqual(self.events,['stop','cancel']);self.assertTrue(self.store.read('renewal-pause-'+self.tx['id'])['confirmed'])
    def test_explicit_renewal_disable_during_update_wins(self):
        self.device._pause_renewal(self.tx);state=json.loads(self.settings.read_bytes());state['updatePause']['wasEnabled']=False;self.settings.write_text(json.dumps(state));result=self.device._finish_renewal(self.tx)
        self.assertEqual(result['status'],'skipped');self.assertFalse(json.loads(self.settings.read_bytes())['enabled']);self.assertNotIn('updatePause',json.loads(self.settings.read_bytes()));self.assertFalse(any(isinstance(e,str) and e.endswith('/enable') for e in self.events))
    def test_renewal_resume_is_attempted_once_and_bound_to_boot(self):
        self.device._pause_renewal(self.tx);self.assertEqual(self.device._finish_renewal(self.tx)['status'],'restored');self.device._finish_renewal(self.tx)
        self.assertEqual(sum(isinstance(e,str) and e.endswith('/enable') for e in self.events),1)
    def test_changed_boot_keeps_renewal_disabled(self):
        self.device._pause_renewal(self.tx);self.device.boot=lambda:'boot-two';self.assertEqual(self.device._finish_renewal(self.tx)['status'],'skipped');self.assertFalse(json.loads(self.settings.read_bytes())['enabled'])
    def test_mutable_restore_never_overwrites_newer_emergency_latch(self):
        latch=self.root/'installed/usr/palm/applications/com.local.nativehome/state/blocked';latch.parent.mkdir(parents=True);latch.write_bytes(b'older');self.device.snapshot_mutable();latch.write_bytes(b'new emergency');self.device.restore_mutable();self.assertEqual(latch.read_bytes(),b'new emergency')

class InfraTransitionTests(DeviceBase):
    def test_local_resume_accepts_only_prior_or_candidate_file_hashes(self):
        old=tar({'runtime/cli.py':b'old'});new=tar({'runtime/cli.py':b'new'})
        a={'name':'root-infrastructure','kind':'infrastructure','version':'1.0.0','size':len(old),'sha256':digest(old),'files':{'runtime/cli.py':digest(b'old')},'local':True};b={k:v for k,v in {**a,'version':'1.1.0','size':len(new),'sha256':digest(new)}.items() if k not in ('local','files')}
        self.baseline({'edition':'root','components':[a]});self.store.write('transaction',{'edition':'root','prior':{'components':[a]},'candidate':{'components':[b]}})
        (self.root/'state/cache'/a['sha256']).write_bytes(old);(self.root/'state/cache'/b['sha256']).write_bytes(new);runtime=self.root/'root/runtime';runtime.mkdir(parents=True);(runtime/'cli.py').write_bytes(b'old')
        self.device.validate_infrastructure_transition();(runtime/'cli.py').write_bytes(b'new');self.device.validate_infrastructure_transition();(runtime/'cli.py').write_bytes(b'foreign')
        with self.assertRaises(ValueError):self.device.validate_infrastructure_transition()

class LegacyBaselineTests(DeviceBase):
    def test_completed_root_release_seeds_legacy_recovery_cache(self):
        raw=ipk('com.cleanyourtv.root.preview');c={'name':'root','application':'com.cleanyourtv.root.preview','version':'1.0.0','kind':'ipk','sha256':digest(raw),'size':len(raw),'local':True};(self.root/'state/cache'/c['sha256']).write_bytes(raw)
        own_raw=ipk('com.cleanyourtv.root.updater');own={'name':'root-updater','application':'com.cleanyourtv.root.updater','version':'1.0.0','kind':'ipk','sha256':digest(own_raw),'size':len(own_raw),'local':True}
        (self.root/'state/cache'/own['sha256']).write_bytes(own_raw)
        for name,data in self.mod.package_archive(self.mod.members(own_raw)['data.tar.gz']).items():
            path=self.root/'installed'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        self.device.sync_root_baseline({'id':'a'*32,'edition':'root','phase':'complete','candidate':{'components':[c,own]}})
        legacy=Store(self.root/'root-updater',uid=os.getuid());saved=legacy.read('current');self.assertEqual(saved['version'],'1.0.0');self.assertEqual((self.root/'root-updater/cache'/(c['sha256']+'.ipk')).read_bytes(),raw)
    def test_root_legacy_terminal_without_resume_cleanup_blocks(self):
        self.root.joinpath('root-updater').mkdir();self.root.joinpath('root-updater/transaction.json').write_text('{"phase":"complete"}')
        with self.assertRaises(ValueError):self.device.check_legacy()
        self.root.joinpath('root-updater/transaction.json').write_text('{"phase":"complete","homeResumePhase":"complete"}');self.device.check_legacy()

class ProcessSafetyTests(DeviceBase):
    def test_permission_error_while_enumerating_proc_never_means_idle(self):
        from unittest.mock import patch
        class Entry:
            name='123'
            def __truediv__(self,name):return self
            def read_bytes(self):raise PermissionError('proc is unreadable')
        with patch.object(self.mod.Path,'iterdir',return_value=iter([Entry()])):
            with self.assertRaises(PermissionError):self.device._helper_processes()
    def test_rewritten_root_service_title_is_stopped_only_with_matching_identity(self):
        from unittest.mock import patch
        entry=self.root/'123';entry.mkdir();target=self.device.root_state/'service';target.mkdir(parents=True)
        (entry/'cmdline').write_bytes(b'com.cleanyourtv.root.preview.service\0')
        (entry/'cwd').symlink_to(target);(entry/'exe').symlink_to('/usr/bin/node')
        self.device._process_start=lambda pid:'original-start'
        signals=[];self.device._signal_checked=lambda *args:signals.append(args)
        for mismatch in ('none','cwd','exe','title','owner'):
            with self.subTest(mismatch=mismatch):
                signals.clear()
                (entry/'cwd').unlink();(entry/'cwd').symlink_to(self.root if mismatch=='cwd' else target)
                (entry/'exe').unlink();(entry/'exe').symlink_to('/bin/sh' if mismatch=='exe' else '/usr/bin/node')
                (entry/'cmdline').write_bytes(b'foreign\0' if mismatch=='title' else b'com.cleanyourtv.root.preview.service\0')
                self.device.uid=os.getuid()+1 if mismatch=='owner' else os.getuid()
                with patch.object(self.mod.Path,'iterdir',return_value=iter([entry])):
                    self.device._stop_service_processes(str(target))
                self.assertEqual(signals,[(123,'original-start',self.mod.signal.SIGSTOP),(123,'original-start',self.mod.signal.SIGKILL)] if mismatch=='none' else [])

    def test_process_reuse_during_service_identity_inspection_is_never_signalled(self):
        from unittest.mock import patch
        entry=self.root/'123';entry.mkdir();target=self.device.root_state/'service';target.mkdir(parents=True)
        (entry/'cmdline').write_bytes(b'com.cleanyourtv.root.preview.service\0')
        (entry/'cwd').symlink_to(target);(entry/'exe').symlink_to('/usr/bin/node')
        starts=iter(['original-start','reused-start']);self.device._process_start=lambda pid:next(starts)
        signals=[];self.device._signal_checked=lambda *args:signals.append(args)
        with patch.object(self.mod.Path,'iterdir',return_value=iter([entry])),self.assertRaisesRegex(ValueError,'process changed'):
            self.device._stop_service_processes(str(target))
        self.assertEqual(signals,[])

    def test_reused_process_id_is_never_signalled(self):
        from unittest.mock import patch
        self.device._process_start=lambda pid:'newer-start'
        with patch.object(self.mod.os,'kill') as kill:
            with self.assertRaises(ValueError):self.device._signal_checked(42,'original-start',self.mod.signal.SIGKILL)
            kill.assert_not_called()

class RetainedCycleTests(PreferenceBase):
    def test_retained_rollback_has_new_preference_pause_and_resume_cycle(self):
        self.device._pause_renewal(self.tx);self.device._finish_renewal(self.tx)
        self.settings.write_text('{"enabled":true,"preferenceTouched":true}')
        rollback={**self.tx,'phase':'rolled-back','resumeCycle':'rollback'};self.store.write('transaction',rollback)
        self.device._pause_renewal(rollback);state=json.loads(self.settings.read_bytes());self.assertEqual(state['updatePause']['id'],self.tx['id']+'-rollback')
        self.assertEqual(self.device._finish_renewal(rollback)['status'],'restored');self.assertNotIn('updatePause',json.loads(self.settings.read_bytes()));self.assertEqual(sum(isinstance(e,str) and e.endswith('/enable') for e in self.events),2)


class LockdownTests(DeviceBase):
    def test_legacy_lockdown_preflights_every_file_before_changes(self):
        first=self.root/'legacy-api.json';second=self.root/'legacy-receipt.json';first.write_text('original');second.write_text('foreign')
        self.store.write('legacy-lockdown',{'schema':1,'files':{str(p):{'original':'original','disabled':'disabled','mode':0o600} for p in (first,second)}})
        from unittest.mock import patch
        with patch.object(self.device,'_legacy_lockdown_paths',return_value={str(first),str(second)}):
            with self.assertRaises(ValueError):self.device.enforce_legacy_lockdown()
            self.assertEqual(first.read_text(),'original')
            second.write_text('original');scans=[];self.device.scan_services=lambda:scans.append(True);self.device.enforce_legacy_lockdown();self.assertEqual(first.read_text(),'disabled');self.assertEqual(second.read_text(),'disabled');self.assertEqual(scans,[True]);self.device.enforce_legacy_lockdown();self.assertEqual(scans,[True])
    def test_foreign_legacy_lockdown_path_is_rejected(self):
        self.store.write('legacy-lockdown',{'schema':1,'files':{'/etc/passwd':{'original':'before','disabled':'after','mode':0o600}}})
        with self.assertRaises(ValueError):self.device.enforce_legacy_lockdown()

class HelperBootPauseTests(DeviceBase):
    def setUp(self):
        super().setUp();self.device._helper_processes=lambda:[];self.device.boot=lambda:'boot-one';self.device.rpc=lambda uri,payload:{'returnValue':True}
        self.tx={'id':'b'*32,'edition':'no-root','phase':'complete'};self.store.write('transaction',self.tx)
        self.startup=self.root/'installed/usr/palm/services/com.local.nativehome.service/state/startup-state.json';self.startup.parent.mkdir(parents=True);self.original=b'{"enabled":true,"schema":3,"boot":"boot-one"}';self.startup.write_bytes(self.original)
    def test_helper_boot_is_paused_during_transaction_and_restored_on_same_boot(self):
        self.device._suspend_helper(self.tx);self.assertFalse(json.loads(self.startup.read_bytes())['enabled']);self.device.finish(self.tx);self.assertEqual(self.startup.read_bytes(),self.original)
    def test_explicit_disable_during_pause_wins(self):
        self.device._suspend_helper(self.tx);self.startup.write_bytes(b'{"enabled":false}');self.device.finish(self.tx);self.assertEqual(self.startup.read_bytes(),b'{"enabled":false}')
    def test_reboot_never_reenables_helper_boot_implicitly(self):
        self.device._suspend_helper(self.tx);self.device.boot=lambda:'boot-two';self.device.finish(self.tx);self.assertFalse(json.loads(self.startup.read_bytes())['enabled'])

class PrivateServiceTests(DeviceBase):
    def test_private_recovery_service_has_fixed_destination_and_receipts(self):
        files={'runtime/cli.py':b'runtime','service/service.js':b'new-service','updater/service.js':b'updater'}
        raw=tar(files);c={'name':'root-infrastructure','kind':'infrastructure','version':'1.1.0','sha256':digest(raw),'size':len(raw),'local':True,'files':{n:digest(v) for n,v in files.items()}}
        self.baseline({'edition':'root','components':[c]})
        self.assertEqual(self.device.inspect(raw,c),c['files'])
        for name,data in files.items():
            path=self.device._infra_path(name);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        proof={'mode':'recovery-only','files':{str(self.device._infra_path(n)):digest(b'old') for n in files if not n.startswith('updater/')}};proof_path=self.root/'root/recovery-provision.json';proof_path.write_text(json.dumps(proof))
        legacy=Store(self.root/'root-updater',uid=os.getuid());legacy.write('infrastructure',{'schema':1,'code':{'service.js':digest(b'old')},'recovery_sha256':digest(proof_path.read_bytes())})
        self.device._refresh_root_receipts(c['files']);updated=json.loads(proof_path.read_bytes());self.assertEqual(updated['files'][str(self.root/'root/service/service.js')],digest(b'new-service'));self.assertEqual(legacy.read('infrastructure')['recovery_sha256'],digest(proof_path.read_bytes()))
        old_hashes={n:digest(b'old') for n in files};self.device._refresh_root_receipts(old_hashes);self.assertEqual(json.loads(proof_path.read_bytes())['files'][str(self.root/'root/service/service.js')],digest(b'old'))

class StateDirectoryTests(DeviceBase):
    def test_missing_state_directory_restores_owned_writable_metadata(self):
        self.store.write('transaction',{'id':'c'*32,'edition':'no-root'})
        state=self.root/'installed/usr/palm/services/com.gathin.tvhome.renewal/state';state.mkdir(parents=True);os.chmod(state,0o700);settings=state/'settings.json';settings.write_bytes(b'{"enabled":false}')
        self.device.snapshot_mutable();settings.unlink();state.rmdir();self.device.restore_mutable()
        self.assertEqual(state.stat().st_mode&0o777,0o700);self.assertEqual(state.stat().st_uid,os.getuid());self.assertEqual(settings.read_bytes(),b'{"enabled":false}');(state/'write-check').write_bytes(b'writable')

class ProfileProtocolTests(DeviceBase):
    def test_launcher_releases_cannot_drop_profile_health_protocol(self):
        import sys
        sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
        from cytv.package import ipk as build_ipk, data_files
        files=data_files(ipk());name='usr/palm/applications/com.gathin.tvhome/appinfo.json';app=json.loads(files[name]);app.pop('systemUpdateProtocol',None);files[name]=json.dumps(app).encode();raw=build_ipk('com.gathin.tvhome','1.0.0',files)
        c={'name':'home','application':'com.gathin.tvhome','version':'1.0.0','kind':'ipk','sha256':digest(raw),'size':len(raw)}
        with self.assertRaises(ValueError):self.device.inspect(raw,c)

class SignedInfrastructureTests(DeviceBase):
    def test_signed_private_service_upgrade_and_rollback_update_real_bytes_and_receipts(self):
        import subprocess
        import shutil
        from test_core import ROOT
        old_files={'runtime/cli.py':b'old runtime','service/service.js':b'old service','updater/service.js':b'old updater'}
        new_files={name:value.replace(b'old',b'new') for name,value in old_files.items()};new_files.update(getattr(self,'extra_candidate_files',{}));old=tar(old_files);new=tar(new_files)
        def infra(raw,version,local=False):
            c={'name':'root-infrastructure','kind':'infrastructure','version':version,'sha256':digest(raw),'size':len(raw)}
            if local:c.update(local=True,files={n:digest(b) for n,b in old_files.items()},absent=sorted(set(new_files)-set(old_files)))
            else:c['url']='https://github.com/Razdva122/clean-your-tv-lg-webos/releases/download/v1.1.0/infrastructure.tar.gz'
            return c
        previous=infra(old,'1.0.0',True);candidate=infra(new,'1.1.0')
        components=[{'name':name,'application':app,'kind':'ipk','version':'1.1.0','sha256':'a'*64,'size':1,'url':'https://github.com/Razdva122/clean-your-tv-lg-webos/releases/download/v1.1.0/'+name+'.ipk'} for name,app in [('root','com.cleanyourtv.root.preview'),('root-updater','com.cleanyourtv.root.updater')]]+[candidate]
        release={'schema':1,'edition':'root','release':'v1.1.0','supervisor':1,'notes':'Signed infrastructure fixture','components':components}
        js="const c=require('crypto'),fs=require('fs'),m=fs.readFileSync(0),k=c.generateKeyPairSync('rsa',{modulusLength:2048});process.stdout.write(JSON.stringify({proof:{payload:m.toString('base64'),signature:c.sign('RSA-SHA256',m,k.privateKey).toString('base64')},key:k.publicKey.export({type:'spki',format:'pem'})}));"
        signed=json.loads(subprocess.run(['node','-e',js],input=json.dumps(release).encode(),stdout=subprocess.PIPE,check=True).stdout);release['proof']=signed['proof']
        baseline={**release,'release':'v1.0.0','components':[{k:v for k,v in c.items() if k!='url'} for c in components]};baseline.pop('proof');baseline['components'][-1]=previous
        for c in baseline['components'][:-1]:c.update(version='1.0.0',local=True)
        self.baseline(baseline);self.store.write('transaction',{'edition':'root','prior':baseline,'candidate':release})
        for c,raw in ((previous,old),(candidate,new)):(self.root/'state/cache'/c['sha256']).write_bytes(raw)
        code=self.root/'code/system_updater';code.mkdir();shutil.copyfile(ROOT/'system-updater/policy.js',code/'policy.js');(code/'release-public.pem').write_text(signed['key'])
        self.store.write('infrastructure',{'schema':1,'code':{str(p.relative_to(self.root/'code')):digest(p.read_bytes()) for p in code.iterdir()}})
        for name,data in old_files.items():
            p=self.device._infra_path(name);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        proof=self.root/'root/recovery-provision.json';proof.write_text(json.dumps({'mode':'recovery-only','files':{str(self.device._infra_path(n)):digest(v) for n,v in old_files.items() if not n.startswith('updater/')}}))
        # A real binding fixture keeps runtime verification active through migration.
        import python_binding
        from unittest.mock import patch
        original_directory=python_binding._directory
        for context in (patch.object(python_binding,'MANAGED_ROOT',self.root/'python'),patch.object(python_binding,'EXPECTED_UID',os.getuid()),patch.object(python_binding,'_directory',side_effect=lambda path:original_directory(path) if path.is_relative_to(self.root) else None)):
            context.start();self.addCleanup(context.stop)
        executable=self.root/'python'/python_binding.ARCHIVE_SHA256/'bin/python3.13';executable.parent.mkdir(parents=True);executable.write_bytes(b'fixture interpreter');executable.chmod(0o755)
        (executable.parents[1]/'.cytv-runtime.json').write_text(json.dumps({'schema':1,'archive_sha256':python_binding.ARCHIVE_SHA256,'files':{'bin/python3.13':digest(executable.read_bytes())}}))
        retained={self.root/'root/python-launcher':python_binding.launcher_bytes(str(executable)),self.root/'root/python-runtime.json':json.dumps(python_binding._runtime(str(executable))).encode()}
        for path,data in retained.items():path.write_bytes(data)
        (self.root/'root/python-launcher').chmod(0o700)
        original_proof=json.loads(proof.read_bytes());original_proof['files'].update({str(path):digest(data) for path,data in retained.items()});proof.write_text(json.dumps(original_proof))
        legacy=Store(self.root/'root-updater',uid=os.getuid());legacy.write('infrastructure',{'schema':1,'code':{'service.js':digest(old_files['updater/service.js'])},'recovery_sha256':digest(proof.read_bytes())})
        def local_verifier(method,payload=None,binary=False):
            result=subprocess.run(['node',str(code/'policy.js'),method],input=json.dumps(payload or {}).encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
            return result.stdout if binary else json.loads(result.stdout)
        self.device.fetch=local_verifier
        self.device._stop_service_processes=lambda target:None;self.device.repair_registrations=lambda:None;self.device.rpc=lambda uri,payload:{'returnValue':True,'root':True}
        # Actual Node signature verification, bounded archive parsing, fixed-file
        # replacement and root-owned receipt writes run; only TV bus/process IO is substituted.
        for c,expected in ((candidate,new_files),(previous,old_files)):
            terminal=[];self.device.install(c,lambda value:None,terminal.append,lambda:None);self.assertTrue(terminal[0]['success'])
            for name,data in expected.items():self.assertEqual(self.device._infra_path(name).read_bytes(),data)
            if c is previous:
                for name in set(new_files)-set(old_files):self.assertFalse(os.path.lexists(self.device._infra_path(name)))
            for path,data in retained.items():
                self.assertEqual(path.read_bytes(),data)
                self.assertEqual(json.loads(proof.read_bytes())['files'][str(path)],digest(data))
            if 'support/python_binding.py' in expected:self.assertEqual(json.loads(proof.read_bytes())['files'][str(self.root/'root/python_binding.py')],digest(expected['support/python_binding.py']))
            updater_hashes={n.split('/',1)[1]:digest(b) for n,b in expected.items() if n.startswith('updater/')}
            self.assertEqual(legacy.read('infrastructure')['code'],updater_hashes)
            self.assertEqual(json.loads(proof.read_bytes())['files'][str(self.root/'root/service/service.js')],digest(expected['service/service.js']));self.assertEqual(legacy.read('infrastructure')['recovery_sha256'],digest(proof.read_bytes()))

class RepeatedHelperPauseTests(HelperBootPauseTests):
    def test_automatic_rollback_respects_newer_explicit_disable(self):
        self.device._suspend_helper(self.tx);self.startup.write_bytes(b'{"enabled":false}');self.device._suspend_helper(self.tx);self.device.finish(self.tx);self.assertEqual(self.startup.read_bytes(),b'{"enabled":false}')


class SignedMissingCaMigrationTests(SignedInfrastructureTests):
    extra_candidate_files={'updater/updater/ca-bundle.crt':b'pinned CA fixture','updater/updater/ca-LICENSE.txt':b'license fixture'}

class AbsentPathTests(DeviceBase):
    def test_prior_absence_must_be_actual_absence_and_foreign_bytes_are_not_deleted(self):
        old=tar({'updater/service.js':b'old'});new=tar({'updater/service.js':b'new','updater/updater/ca-bundle.crt':b'CA'})
        a={'name':'root-infrastructure','kind':'infrastructure','version':'1.0.0','size':len(old),'sha256':digest(old),'local':True,'files':{'updater/service.js':digest(b'old')},'absent':['updater/updater/ca-bundle.crt']};b={'name':'root-infrastructure','kind':'infrastructure','version':'1.1.0','size':len(new),'sha256':digest(new)}
        self.baseline({'edition':'root','components':[a]});self.store.write('transaction',{'edition':'root','prior':{'components':[a]},'candidate':{'components':[b]}})
        for c,raw in ((a,old),(b,new)):(self.root/'state/cache'/c['sha256']).write_bytes(raw)
        path=self.device._infra_path('updater/service.js');path.parent.mkdir(parents=True);path.write_bytes(b'old');self.assertTrue(self.device.verify_installed(a));self.device.validate_infrastructure_transition()
        ca=self.device._infra_path('updater/updater/ca-bundle.crt');ca.parent.mkdir();ca.write_bytes(b'foreign')
        self.assertFalse(self.device.verify_installed(a))
        with self.assertRaises(ValueError):self.device.validate_infrastructure_transition()
        self.assertEqual(ca.read_bytes(),b'foreign')

class ComponentOfferTests(DeviceBase):
    def test_new_release_without_component_version_changes_is_current(self):
        from test_core import release
        prior=release('2.0.0');candidate=release('2.0.0');candidate['release']='v2.1.0'
        self.device.integrity=lambda:None;self.device.fetch=lambda method,payload:{'candidate':candidate};self.device._verify_release=lambda value,edition:value;self.device._baseline=lambda edition:prior;self.device.installed=lambda app:'2.0.0'
        self.device.check_legacy=lambda:None;self.device.verify_baseline=lambda value:True;self.device.cache_bytes=lambda c:b'cached';self.device.inspect=lambda raw,c:{}
        offer=self.device.check('no-root')
        self.assertFalse(offer['canInstall']);self.assertEqual(offer['reason'],'current')
        candidate['components'][2]['version']='2.0.1'
        offer=self.device.check('no-root')
        self.assertTrue(offer['canInstall']);self.assertEqual(offer['reason'],'available')

    def test_newer_release_with_older_helper_is_not_installable(self):
        from test_core import release
        prior=release('2.0.0');prior['release']='v0.0.0';candidate=release('2.1.0');candidate['components'][1]['version']='1.9.0'
        self.device.integrity=lambda:None;self.device.fetch=lambda method,payload:{'candidate':candidate};self.device._verify_release=lambda value,edition:value;self.device._baseline=lambda edition:prior;self.device.installed=lambda app:'2.0.0'
        offer=self.device.offer('no-root');self.assertFalse(offer['canInstall']);self.assertEqual(offer['reason'],'component-downgrade')

class SignedPythonBindingMigrationTests(SignedInfrastructureTests):
    extra_candidate_files={'support/python_binding.py':b'pinned binding helper','support/python_boot.js':b'pinned boot helper'}

class OfferUnavailableTests(DeviceBase):
    def setUp(self):
        super().setUp()
        from test_core import release
        self.prior=release('1.0.0');self.prior['edition']='root'
        for c,name in zip(self.prior['components'],('root','root-updater','root-infrastructure')):
            c['name']=name;c['application']=self.mod.IDENTITIES[name];c['kind']='infrastructure' if name=='root-infrastructure' else 'ipk'
            if c['kind']=='infrastructure':c['files']={}
        self.store.write('baseline',self.prior)
        self.device.integrity=lambda:None
        self.device.owner_identity=lambda app,purpose='worker':json.loads((self.root/('installed/usr/palm/applications/'+app+'/appinfo.json')).read_bytes())
        for app in ('com.cleanyourtv.root.preview','com.cleanyourtv.root.updater'):
            path=self.root/('installed/usr/palm/applications/'+app+'/appinfo.json');path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(json.dumps({'id':app,'version':'1.0.2'}))
    def failure(self,code):
        return self.mod.subprocess.CalledProcessError(1,['/usr/bin/node','/private/internal/policy.js','offer'],output=json.dumps({'error':code}).encode(),stderr=b'/private/internal details')
    def test_missing_offer_and_transport_use_verified_baseline_without_transaction(self):
        from unittest.mock import patch
        for code in ('feed-unavailable','connection-error'):
            with self.subTest(code=code),patch.object(self.mod.subprocess,'run',side_effect=self.failure(code)):
                self.assertEqual(self.device.check('root'),{'edition':'root','release':None,'notes':'','components':[{'name':'root','installed':'1.0.2','version':None},{'name':'root-updater','installed':'1.0.2','version':None},{'name':'root-infrastructure','installed':'1.0.0','version':None}],'canInstall':False,'reason':code})
                self.assertIsNone(self.store.read('transaction'))
    def test_offer_subprocess_timeout_is_connection_empty_state(self):
        from unittest.mock import patch
        with patch.object(self.mod.subprocess,'run',side_effect=self.mod.subprocess.TimeoutExpired(['/private/internal/policy.js'],80)):
            self.assertEqual(self.device.check('root')['reason'],'connection-error')
    def test_unverified_offer_and_unknown_subprocess_errors_are_safe_and_fail_closed(self):
        from unittest.mock import patch
        failures=[self.failure('verification-error'),self.failure('made-up'),self.mod.subprocess.CalledProcessError(1,['/private/internal/policy.js'],output=b'bad JSON',stderr=b'secret'),self.mod.subprocess.CompletedProcess([],0,stdout=b'broken')]
        for failure in failures:
            with self.subTest(failure=failure),patch.object(self.mod.subprocess,'run',**({'return_value':failure} if isinstance(failure,self.mod.subprocess.CompletedProcess) else {'side_effect':failure})):
                with self.assertRaisesRegex(ValueError,r'^Update information could not be verified\. Nothing was installed\.$'):self.device.check('root')
                self.assertIsNone(self.store.read('transaction'))
    def test_missing_feed_does_not_make_untrusted_baseline_displayable(self):
        from unittest.mock import patch
        self.prior['components'][0].pop('local');self.store.write('baseline',self.prior)
        with patch.object(self.mod.subprocess,'run',side_effect=self.failure('feed-unavailable')):
            with self.assertRaises(ValueError):self.device.check('root')
    def test_install_offer_never_falls_back_to_baseline(self):
        from unittest.mock import patch
        with patch.object(self.mod.subprocess,'run',side_effect=self.failure('feed-unavailable')):
            with self.assertRaisesRegex(ValueError,r'^Update information is not available yet\. Nothing was installed\.$'):self.device.offer('root')
        self.assertIsNone(self.store.read('transaction'))
    def test_package_errors_are_safe_and_never_binary_results(self):
        from unittest.mock import patch
        with patch.object(self.mod.subprocess,'run',side_effect=self.failure('connection-error')):
            with self.assertRaisesRegex(ValueError,r'^Could not connect to the update server\. Nothing was installed\.$'):self.device.fetch('package',binary=True)

class RootRollbackDataTests(DeviceBase):
    def test_original_system_worker_rolls_back_partial_root_data_once(self):
        import copy
        from unittest.mock import patch
        from test_core import release,profile
        from system_updater.core import Manager
        from system_updater.support.store import encode
        prior=release('1.0.0');prior['edition']='root'
        for c,name in zip(prior['components'],('root','root-updater','root-infrastructure')):
            c.update(name=name,application=self.mod.IDENTITIES[name],kind='infrastructure' if name=='root-infrastructure' else 'ipk')
            if c['kind']=='ipk':
                raw=ipk(c['application']);c.update(sha256=digest(raw),size=len(raw))
                (self.root/'state/cache'/c['sha256']).write_bytes(raw)
        candidate=copy.deepcopy(prior);candidate['release']='v1.1.0'
        for c in candidate['components']:c['version']='1.1.0'
        self.store.write('baseline',prior)
        snapshot=profile();self.store.write('profile-'+'a'*32,snapshot)
        tx=dict(schema=1,id='a'*32,edition='root',phase='rolling-back',created=1,updated=2,release='v1.1.0',profile='profile-'+'a'*32,profileDigest=digest(encode(snapshot)),rollbackAttempted=True,prior=prior,candidate=candidate,components=[])
        for c in candidate['components']:
            tx['components'].append({'name':c['name'],'version':c['version'],'installEvidence':{'intent':c['name']=='root','submitted':{'original':'request'} if c['name']=='root' else None,'terminal':{'success':False} if c['name']=='root' else None},'rollbackEvidence':{'intent':False,'submitted':None,'terminal':None}})
        self.store.write('transaction',tx)
        # Static private supervisor proof is supplied at this effects boundary;
        # real self-cache/terminal authentication has separate all-owner coverage.
        checked=[];self.device.owner_identity=lambda owner,**kw:checked.append(owner) or {'id':owner}
        self.device.require_components=lambda:self.mod.Device.require_components(self.device)
        self.device.integrity=lambda **kw:None;self.device.routing_safe=lambda:True;self.device.now=lambda:1000;self.device.launch=lambda edition:None
        self.device.snapshot_mutable=lambda:None;self.device.restore_mutable=lambda:None;self.device.repair_registrations=lambda:None
        actual=self.device.verify_installed
        self.device.verify_installed=lambda c:actual(c) if c['name']=='root' else True
        (self.root/'installed/usr/palm/applications/com.cleanyourtv.root.preview/appinfo.json').unlink()
        def install(owner,path,**kw):
            self.assertEqual(owner,'com.cleanyourtv.root.preview');kw['on_ready']()
            for name,data in self.mod.package_archive(self.mod.members(Path(path).read_bytes())['data.tar.gz']).items():
                target=self.root/'installed'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);target.chmod(0o777)
            return {'completed':True,'event':{'statusValue':30}}
        with patch('observed_install.install',side_effect=install) as submit:
            manager=Manager(self.store,self.device);result=manager.run()
            self.assertTrue(result['components'][0]['rollbackEvidence']['terminal']['success']);self.assertEqual(submit.call_count,1)
            self.assertEqual(manager.run()['phase'],'verifying-rollback')
            manager.healthy('root',tx['id'],'1.0.0');self.assertEqual(manager.run()['phase'],'rolled-back')
            self.assertEqual(submit.call_count,1);self.assertEqual(set(checked),{'com.cleanyourtv.system.updater','com.cleanyourtv.root.preview','com.cleanyourtv.root.updater'})

class OriginalPreflightOrderTests(DeviceBase):
    def test_changed_private_supervisor_blocks_before_executing_release_verifier(self):
        from test_core import release
        from unittest.mock import patch
        candidate=release('1.1.0');candidate['proof']={'original':'fixture-signature'}
        c=candidate['components'][0];raw=ipk();c.update(version='1.0.0',sha256=digest(raw),size=len(raw))
        self.store.write('transaction',{'edition':'no-root','candidate':candidate,'prior':candidate})
        (self.root/'code/policy.js').write_bytes(b'original verifier')
        self.store.write('infrastructure',{'schema':1,'code':{'policy.js':digest(b'original verifier')}})
        (self.root/'code/policy.js').write_bytes(b'changed verifier')
        with patch.object(self.device,'fetch',side_effect=AssertionError('unverified policy executed')) as verifier,patch.object(self.device,'enforce_legacy_lockdown') as lockdown,patch('observed_install.install') as submit:
            with self.assertRaisesRegex(ValueError,'Supervisor infrastructure changed'):
                self.device.install(c,self.fail,self.fail,self.fail)
            self.assertEqual(verifier.call_count,0);self.assertEqual(lockdown.call_count,0);self.assertEqual(submit.call_count,0)

class InfrastructureOfferTests(DeviceBase):
    def offer(self, new_files, corrupt=False):
        old=tar({'runtime/cli.py':b'old'});new=tar(new_files)
        root=ipk('com.cleanyourtv.root.preview');updater=ipk('com.cleanyourtv.root.updater')
        def component(name,app,raw):return {'name':name,'application':app,'version':'1.0.0','kind':'ipk','sha256':digest(raw),'size':len(raw),'local':True}
        previous={'name':'root-infrastructure','kind':'infrastructure','version':'1.0.0','sha256':digest(old),'size':len(old),'files':{'runtime/cli.py':digest(b'old')},'local':True,'absent':[]}
        prior={'schema':1,'supervisor':1,'edition':'root','release':'v1.0.0','notes':'fixture','components':[component('root','com.cleanyourtv.root.preview',root),component('root-updater','com.cleanyourtv.root.updater',updater),previous]}
        self.baseline(prior)
        for c,raw in zip(prior['components'],[root,updater,old]):(self.root/'state/cache'/c['sha256']).write_bytes(raw)
        target={'name':'root-infrastructure','kind':'infrastructure','version':'1.1.0','sha256':digest(new),'size':len(new)}
        candidate={**prior,'release':'v1.1.0','components':[*prior['components'][:2],target],'proof':{'payload':'fixture','signature':'fixture'}}
        self.device.integrity=lambda:None;self.device.check_legacy=lambda:None;self.device.verify_baseline=lambda value:True
        self.device._verify_release=lambda value,edition:value;self.device.installed=lambda app:'1.0.0'
        def fetch(method,payload=None,binary=False):
            if method=='offer':return {'candidate':candidate}
            if method=='package' and binary and payload=={'proof':candidate['proof'],'name':'root-infrastructure'}:return b'bad' if corrupt else new
            raise AssertionError('unexpected external request')
        self.device.fetch=fetch
        result=self.device.offer('root')
        self.assertIsNone(self.store.read('transaction'))
        return result

    def test_incompatible_candidate_is_not_offered_before_installation(self):
        result=self.offer({'runtime/cli.py':b'new','runtime/new.py':b'foreign'})
        self.assertFalse(result['canInstall'])
        self.assertIn('computer migration',result['reason'])

    def test_compatible_candidate_is_still_offered(self):
        self.assertTrue(self.offer({'runtime/cli.py':b'new'})['canInstall'])

    def test_downloaded_candidate_hash_mismatch_is_not_offered(self):
        self.assertFalse(self.offer({'runtime/cli.py':b'new'},corrupt=True)['canInstall'])
