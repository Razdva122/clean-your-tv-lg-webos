"""Installer -> trusted adapter -> real detached Node -> simulated vendor process."""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from cytv import no_root_observer as observer, operations, state, package
from tests.cytv.test_operations import Remote
from tests.cytv import test_operations as operations_fixture


class ProcessRemote(Remote):
    def __init__(self, root):
        super().__init__()
        self.root_path=root
        self.cut=False
        self.sender=root/'sender'
        self.sender.write_text('''#!/usr/bin/env python3
import json,sys,os,select
from pathlib import Path
sys.path.insert(0, REPOSITORY)
from cytv import package
root=Path(ROOT)
request=json.loads(sys.argv[-1]); app=request['id']
with (root/'requests').open('a') as stream: stream.write(app+'\\n')
if select.select([sys.stdin],[],[],.05)[0]: sys.exit(12)
apps=json.loads((root/'installed.json').read_text()) if (root/'installed.json').exists() else {}
if sys.argv[-2].endswith('/install'):
 for name,data in package.data_files(Path(request['ipkUrl']).read_bytes()).items():
  destination=root/'apps'/name; destination.parent.mkdir(parents=True,exist_ok=True); destination.write_bytes(data)
 info=json.loads((root/'apps/usr/palm/applications'/app/'appinfo.json').read_text())
 apps[app]=info['version']; terminal='installed'
 if app=='com.local.nativehome':(root/'apps/usr/palm/applications'/app/'state').mkdir(exist_ok=True)
else:
 import shutil
 for kind,suffix in [('applications',''),('packages',''),('services','.renewal' if app=='com.gathin.tvhome' else '.service')]:
  shutil.rmtree(root/'apps/usr/palm'/kind/(app+suffix),ignore_errors=True)
 apps.pop(app,None); terminal='removed'
(root/'installed.json').write_text(json.dumps(apps))
print(json.dumps({'returnValue':True,'details':{'state':terminal}}),flush=True)
sys.stdin.read()
'''.replace('REPOSITORY',repr(str(Path(__file__).resolve().parents[2]))).replace('ROOT',repr(str(root))))
        self.sender.chmod(0o700)

    def run(self, command, data=None, timeout=30):
        if 'CYTV_NODE_READY' in command:
            return super().run(command,data,timeout)
        if 'CYTV_STOP_RETAINED' in command:
            return subprocess.run(['sh','-c',command],capture_output=True,check=True).stdout.decode()
        words=shlex.split(command)
        if '-e' in words and '/usr/bin/node' in words:
            code=words[words.index('-e')+1]
            argument=words[-1]
            if code==observer.PROGRAM:
                request=json.loads(argument)
                request['sender']=str(self.sender)
                request['timeout']=3000
                argument=json.dumps(request)
                self.calls.append(('observer',request['command'],request.get('slot')))
            result=subprocess.run([shutil.which('node'),'-e',code,argument],capture_output=True,timeout=timeout)
            if result.returncode: raise RuntimeError(result.stderr.decode())
            reply=result.stdout.decode()
            if code==observer.PROGRAM and self.cut and request['command']=='status':
                value=json.loads(reply)
                if value['slots'][0]['terminal']=='success':
                    self.cut=False
                    raise RuntimeError('simulated host disconnect after durable Helper terminal')
            return reply
        if command.startswith('if ') and 'CYTV_REMAINS' in command:
            paths=[Path(word) for word in words if word.startswith(str(self.root_path))]
            return 'CYTV_REMAINS' if any(path.exists() or path.is_symlink() for path in paths) else ''
        return super().run(command,data,timeout)

    def upload(self,path,data,mode=0o600):
        super().upload(path,data,mode)
        if not str(path).startswith(str(self.root_path)+'/'):
            raise RuntimeError('new bound observer staging required')
        target=Path(path); target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(data);target.chmod(mode)

    def luna(self,uri,payload,**kwargs):
        if uri.endswith('/dev/listApps'):
            source=self.root_path/'installed.json'
            self.installed=[{'id':app,'version':version} for app,version in json.loads(source.read_text()).items()] if source.exists() else []
        return super().luna(uri,payload,**kwargs)


@unittest.skipIf(os.name=='nt','The TV observer requires a POSIX process fixture')
class OriginalOperationIntegration(unittest.TestCase):
    def setUp(self):
        from tests.cytv.test_no_root_observer import PROCESS_TMP
        fixture=operations_fixture.OperationTests()
        with patch('tempfile.tempdir',PROCESS_TMP):fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.root=fixture.root.resolve()
        self.root.chmod(0o755)
        self.store=state.Store(self.root/'state')
        self.profile=state.target('test-tv','no-root')
        self.remote=ProcessRemote(self.root)
        (self.root/'public').mkdir()
        self.base=str(self.root/'apps/usr/palm')
        for target,value in ((observer,'ROOT'),(observer,'PUBLIC_ROOT')):
            patcher=patch.object(target,value,str(self.root/('private' if value=='ROOT' else 'public')))
            patcher.start();self.addCleanup(patcher.stop)
        for name,value in (('BASE',self.base),('HELPER_STATE',self.base+'/applications/'+operations.HELPER+'/state')):
            patcher=patch.object(operations,name,value);patcher.start();self.addCleanup(patcher.stop)
        self.installer=operations.Installer(self.remote,self.store,self.profile,fixture.payload,fixture.manifest,lambda *_:None)
        self.inventory=fixture.inventory

    def test_host_loss_resumes_only_original_home_and_configuration_after_upgrade(self):
        self.remote.cut=True
        with self.assertRaises(RuntimeError): self.installer.install(self.inventory,'original-secret')
        pending=self.store.pending(self.profile)
        self.assertIsNotNone(pending, 'interruption must preserve an original operation')
        self.assertEqual(pending.get('recovery_protocol'),'no-root-original-stream-v1')
        self.assertEqual((self.root/'requests').read_text().splitlines(),[operations.HELPER])
        self.installer.manifest=dict(self.installer.manifest,helper_version='9.9.9',home_version='9.9.9')
        before=(self.store.device_dir(self.profile)/'operation.json').read_bytes()
        observed=self.installer.observe_recovery()
        self.assertIn('continue-no-root',observed['assessment']['actions'])
        self.assertEqual((self.store.device_dir(self.profile)/'operation.json').read_bytes(),before)
        self.installer.continue_no_root(pending)
        self.assertIsNone(self.store.pending(self.profile))
        self.assertEqual((self.root/'requests').read_text().splitlines(),list(observer.APPS))
        self.assertEqual(json.loads((Path(operations.HELPER_STATE)/'ssap-key.json').read_text()),{'key':'original-secret'})
        self.assertEqual(list((self.root/'public').iterdir()),[])
        self.assertTrue((self.root/'private/operations'/pending['observer_operation']/'claim-0.json').exists())
        self.assertFalse((self.store.device_dir(self.profile)/('capsule-'+pending['observer_operation']+'.json')).exists())
        self.assertFalse(any(call[0]=='luna' and call[1].endswith('appInstallService/status') for call in self.remote.calls))

    def test_new_removal_uses_null_artifact_and_resumes_only_home(self):
        self.installer.install(self.inventory,'original-secret')
        (self.root/'requests').write_text('')
        self.remote.cut=True
        with self.assertRaises(RuntimeError):self.installer.uninstall()
        pending=self.store.pending(self.profile)
        self.assertEqual(pending.get('recovery_protocol'),observer.PROTOCOL)
        saved=observer.capsule(self.installer,pending)
        self.assertTrue(all(slot['artifact_sha256'] is None for slot in saved['plan']['slots']))
        self.installer.continue_no_root(pending)
        self.assertEqual((self.root/'requests').read_text().splitlines(),list(observer.APPS))
        self.assertEqual(json.loads((self.root/'installed.json').read_text()),{})
        self.assertIsNone(self.store.pending(self.profile))

    def test_changed_capsule_or_current_files_never_submit_home(self):
        self.remote.cut=True
        with self.assertRaises(RuntimeError):self.installer.install(self.inventory,'original-secret')
        pending=self.store.pending(self.profile)
        source=self.root/'private/operations'/pending['observer_operation']/'observer.js'
        original=source.read_bytes();source.write_bytes(b'changed')
        with self.assertRaises(RuntimeError):self.installer.continue_no_root(pending)
        source.write_bytes(original)
        installed=Path(self.base)/'applications'/operations.HELPER/'appinfo.json'
        installed.write_text('{}')
        with self.assertRaises(RuntimeError):self.installer.continue_no_root(pending)
        capsule=self.store.device_dir(self.profile)/('capsule-'+pending['observer_operation']+'.json')
        capsule.write_text('{}')
        with self.assertRaises(RuntimeError):self.installer.continue_no_root(pending)
        self.assertEqual((self.root/'requests').read_text().splitlines(),[operations.HELPER])
        self.assertEqual(self.store.pending(self.profile),pending)

    def test_emergency_marker_prevents_recovery_launch(self):
        self.remote.cut=True
        with self.assertRaises(RuntimeError):self.installer.install(self.inventory,'original-secret')
        pending=self.store.pending(self.profile)
        marker=Path(operations.HELPER_STATE)/'blocked';marker.parent.mkdir(parents=True,exist_ok=True);marker.write_text('stopped')
        with self.assertRaisesRegex(RuntimeError,'safety control'):self.installer.continue_no_root(pending)
        self.assertEqual(marker.read_text(),'stopped')
        self.assertFalse(any(call[0]=='luna' and call[1].endswith('/launch') for call in self.remote.calls))
        self.assertIsNotNone(self.store.pending(self.profile))

    def test_foreign_reservation_blocks_removal_restore_before_any_effect(self):
        self.remote.cut=True
        with self.assertRaises(RuntimeError):self.installer.install(self.inventory,'original-secret')
        other=operations.Installer(self.remote,state.Store(self.root/'second-computer'),self.profile,
                                   self.installer.payload,self.installer.manifest,lambda *_:None)
        with self.assertRaises(RuntimeError):other.uninstall()
        pending=other.store.pending(self.profile)
        before=len(self.remote.calls)
        with self.assertRaises(RuntimeError):other.continue_no_root(pending)
        self.assertFalse(any(call[0] in ('upload','luna') for call in self.remote.calls[before:]),self.remote.calls[before:])

    def test_original_capsule_completes_interrupted_staging_before_any_request(self):
        upload=self.remote.upload
        def interrupted(path,raw,mode=0o600):
            if path.endswith('helper.ipk'):raise RuntimeError('upload interrupted')
            return upload(path,raw,mode)
        self.remote.upload=interrupted
        with self.assertRaises(RuntimeError):self.installer.install(self.inventory,'original-secret')
        pending=self.store.pending(self.profile)
        self.assertFalse((self.root/'requests').exists())
        self.remote.upload=upload
        saved=observer.capsule(self.installer,pending)
        observer.stage_remaining(self.installer,saved)
        self.installer.continue_no_root(pending)
        self.assertEqual((self.root/'requests').read_text().splitlines(),list(observer.APPS))
        self.assertIsNone(self.store.pending(self.profile))

    def test_recovery_requires_explicit_confirmation_and_status_has_no_writes(self):
        from cytv.recovery import recover
        from cytv.desktop import DesktopConsole
        self.remote.cut=True
        with self.assertRaises(RuntimeError):self.installer.install(self.inventory,'original-secret')
        def evidence():return {str(path):path.read_bytes() for root in (self.root/'private',self.store.root) for path in root.rglob('*') if path.is_file()}
        before=evidence();result=self.installer.observe_recovery()
        events=[];console=DesktopConsole(lambda kind,value:events.append((kind,value)))
        recover(self.installer,lambda _: '',console,initial_observation=result)
        self.assertEqual(evidence(),before)
        self.assertEqual((self.root/'requests').read_text().splitlines(),[operations.HELPER])
        recover(self.installer,lambda _: 'y',console,initial_observation=result)
        self.assertIsNone(self.store.pending(self.profile))
        self.assertEqual((self.root/'requests').read_text().splitlines(),list(observer.APPS))

    def test_native_entry_preserves_stop_arriving_after_host_guard(self):
        original=self.remote.luna
        def luna(uri,payload,**kwargs):
            if uri.endswith('/launch') and payload.get('id')==operations.HELPER:
                marker=Path(operations.HELPER_STATE)/'blocked';marker.parent.mkdir(parents=True,exist_ok=True);marker.write_text('concurrent-stop')
                source=Path(__file__).resolve().parents[2]/'native/app'
                script=r'''
var fs=require('fs'),vm=require('vm'),path=require('path'),source=process.argv[1],local=process.argv[2],params=JSON.parse(process.argv[3]),captured;
var entry=fs.readFileSync(source+'/helper-entry.js','utf8');
vm.runInNewContext(entry,{require:function(name){if(name!=='child_process')throw Error('unexpected');return {spawn:function(binary,args){captured=JSON.parse(args[0]);return {on:function(){},unref:function(){}};}};},process:{argv:['node','entry',JSON.stringify(params)],exit:function(){throw Error('unexpected exit');}}});
if(!captured||captured.nativeHomeAuto!==true)throw Error('lost automatic safety flag');
var native=fs.readFileSync(source+'/native.js','utf8'),exited=false;
try{vm.runInNewContext(native,{require:function(name){
 if(name==='fs')return {existsSync:function(p){return fs.existsSync(p.replace('/media/developer/apps/usr/palm/applications/com.local.nativehome/state',local));}};
 if(name==='child_process')return {};
 if(name==='./runtime-policy')return require(source+'/runtime-policy');
 throw Error('unexpected dependency after stop '+name);
},process:{argv:['node','native',JSON.stringify(captured)],exit:function(code){if(code!==0)throw Error('failed');exited=true;throw 'STOP';}},Buffer:Buffer});}catch(e){if(e!=='STOP')throw e;}
if(!exited||fs.readFileSync(local+'/blocked','utf8')!=='concurrent-stop')throw Error('stop lost');
'''
                result=subprocess.run([shutil.which('node'),'-e',script,str(source),operations.HELPER_STATE,json.dumps(payload['params'])],capture_output=True,timeout=5)
                self.assertEqual(result.returncode,0,result.stderr.decode())
            return original(uri,payload,**kwargs)
        self.remote.luna=luna
        self.installer.install(self.inventory,'original-secret')
        self.assertEqual((Path(operations.HELPER_STATE)/'blocked').read_text(),'concurrent-stop')

    def test_copied_capsule_cannot_duplicate_delayed_configuration(self):
        import threading
        self.remote.cut=True
        with self.assertRaises(RuntimeError):self.installer.install(self.inventory,'original-secret')
        pending=self.store.pending(self.profile)
        other_root=self.root/'other-host';shutil.copytree(self.store.root,other_root)
        other=operations.Installer(self.remote,state.Store(other_root),self.profile,self.installer.payload,self.installer.manifest,lambda *_:None)
        entered=threading.Event();release=threading.Event();effects=[];failures=[]
        luna=self.remote.luna
        def delayed(uri,payload,**kwargs):
            if uri.endswith('/addDevice'):
                effects.append('eim')
                if len(effects)>1:raise RuntimeError('duplicate EIM submission')
                entered.set()
                if not release.wait(10):raise RuntimeError('test barrier timeout')
            return luna(uri,payload,**kwargs)
        self.remote.luna=delayed
        def first():
            try:self.installer.continue_no_root(pending)
            except Exception as error:failures.append(error)
        thread=threading.Thread(target=first);thread.start()
        try:
            self.assertTrue(entered.wait(8))
            with self.assertRaises(RuntimeError):other.continue_no_root(other.store.pending(self.profile))
            self.assertEqual(effects,['eim'])
        finally:release.set();thread.join(10)
        self.assertFalse(thread.is_alive());self.assertEqual(failures,[])

    def test_configuration_symlink_cannot_receive_private_key(self):
        self.remote.cut=True
        with self.assertRaises(RuntimeError):self.installer.install(self.inventory,'original-secret')
        destination=self.root/'foreign-state';destination.mkdir()
        Path(operations.HELPER_STATE).rmdir()
        Path(operations.HELPER_STATE).symlink_to(destination,target_is_directory=True)
        pending=self.store.pending(self.profile)
        with self.assertRaises(RuntimeError):self.installer.continue_no_root(pending)
        self.assertEqual(list(destination.iterdir()),[])

    def test_terminal_removal_can_finish_only_empty_owned_package_metadata(self):
        self.installer.install(self.inventory,'original-secret')
        sender=self.remote.sender.read_text().replace("apps.pop(app,None); terminal='removed'",
            "apps.pop(app,None); terminal='removed'\n (root/'apps/usr/palm/packages'/app).mkdir(parents=True,exist_ok=True)")
        self.remote.sender.write_text(sender);self.remote.cut=True
        with self.assertRaises(RuntimeError):self.installer.uninstall()
        pending=self.store.pending(self.profile)
        status=self.installer.observe_recovery()
        self.assertIn('continue-no-root',status['assessment']['actions'])
        self.installer.continue_no_root(pending)
        self.assertIsNone(self.store.pending(self.profile))
