"""Local developer safety checks; never connects to a TV."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def module():
    path = ROOT / 'scripts/tv-dev.py'
    assert path.is_file(), 'TV developer entrypoint is missing'
    spec = importlib.util.spec_from_file_location('tv_dev', path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class TVDevTests(unittest.TestCase):
    def test_ui_stage_compiles_separate_identity_and_keeps_failed_rebuild_intact(self):
        dev = module()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'ui'
            calls = []
            def compile_files(files):
                calls.append(files)
                return dict(files, **{'compiled-proof.txt': b'compiled'})
            dev.stage_ui(output, compiler=compile_files)
            info = json.loads((output / 'appinfo.json').read_text())
            self.assertEqual(info['id'], 'com.cleanyourtv.dev.ui')
            self.assertNotIn('appCategory', info)
            self.assertEqual(info['requiredACG'], [])
            self.assertTrue((output / 'compiled-proof.txt').is_file())
            self.assertTrue(calls)
            original = (output / 'index.html').read_bytes()
            def fail(_): raise RuntimeError('compile refused')
            with self.assertRaisesRegex(RuntimeError, 'compile refused'):
                dev.stage_ui(output, compiler=fail)
            self.assertEqual((output / 'index.html').read_bytes(), original)
            self.assertFalse(any(p.name.endswith('.service') for p in output.rglob('*')))

    def test_rejects_sources_existing_unmanaged_directory_and_symlinks(self):
        dev = module()
        for output in (ROOT, ROOT / 'launcher', ROOT / 'root-edition/ui'):
            with self.assertRaises(ValueError): dev.stage_ui(output, compiler=lambda value: value)
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / 'unmanaged'
            directory.mkdir()
            (directory / 'personal').write_text('retain')
            with self.assertRaises(ValueError): dev.stage_ui(directory, compiler=lambda value: value)
            link = Path(tmp) / 'linked'
            link.symlink_to(directory, target_is_directory=True)
            with self.assertRaises(ValueError): dev.stage_ui(link, compiler=lambda value: value)
            self.assertEqual((directory / 'personal').read_text(), 'retain')

    def test_bridge_blocks_native_service_and_namespaces_storage_in_runtime(self):
        dev = module()
        files = dev.ui_files()
        program = r'''
const vm=require('vm'),fs=require('fs'),f=JSON.parse(fs.readFileSync(0,'utf8'));
let actualCalls=0,store={production:'secret'},databases=[];
const storage={getItem:k=>Object.prototype.hasOwnProperty.call(store,k)?store[k]:null,setItem:(k,v)=>store[k]=String(v),removeItem:k=>delete store[k]};
const window={TV_APPS:{apps:[]},indexedDB:{open:name=>databases.push(name)},localStorage:storage,PalmServiceBridge:function(){actualCalls++;},webOS:{service:{request:()=>actualCalls++}}};
const context={window,document:{getElementById:()=>null},setTimeout:fn=>{fn();return 1;},clearTimeout:()=>{}};
vm.createContext(context);vm.runInContext(f['dev-bridge.js'],context);vm.runInContext(f['bridge.js'],context);vm.runInContext(f['dev-lock.js'],context);
window.CYTV_DEV_STORAGE.setItem('production','dev');
window.CYTV_DEV_INDEXEDDB.open('ctv-themes-v1',1);
if(databases.join()!=='cytv.dev.ui.ctv-themes-v1')throw Error('IDB escaped namespace');
if(store.production!=='secret'||window.CYTV_DEV_STORAGE.getItem('production')!=='dev')throw Error('storage escaped');
new window.PalmServiceBridge().call('luna://com.cleanyourtv.root.preview.service/enable','{}');
window.webOS.service.request('luna://com.cleanyourtv.root.preview.service/enable',{});
try{window.PalmServiceBridge=function(){actualCalls++;};}catch(_){}
new window.PalmServiceBridge().call('luna://com.webos.applicationManager/launch','{}');
if(actualCalls!==0)throw Error('native service reached');
'''
        subprocess.run(['node', '-e', program], input=json.dumps({k:v.decode() for k,v in files.items() if k in ('dev-bridge.js','bridge.js','dev-lock.js')}), text=True, check=True)
        self.assertIn(b"connect-src 'self'", files['index.html'])
        for name, raw in files.items():
            if name.endswith('.js') and name not in ('dev-bridge.js','dev-entry.js'): self.assertNotIn(b'localStorage', raw, name)

    def test_watcher_detects_shared_compatibility_input_changes(self):
        dev=module()
        with tempfile.TemporaryDirectory() as tmp, patch.object(dev,'ROOT',Path(tmp)):
            manifest=Path(tmp)/'package.json'
            manifest.write_text('{"browserslist":["Chrome 38"]}')
            before=dev.source_revision()
            manifest.write_text('{"browserslist":["Chrome 38", "Chrome 53"]}')
            self.assertNotEqual(dev.source_revision(),before)

    def test_hosted_command_rejects_cli_option_injection_and_requires_owner(self):
        dev = module()
        self.assertEqual(dev.hosted_command(Path('/tmp/ui'), 'lgtv'), ['ares-launch', '--hosted', '/tmp/ui', '-d', 'lgtv'])
        for device in ('', '-d', 'tv;evil', 'tv name'):
            with self.assertRaises(ValueError): dev.hosted_command(Path('/tmp/ui'), device)
        with self.assertRaisesRegex(ValueError, 'owner'): dev.require_device_consent(False)

    def test_acceptance_request_preserves_exact_envelope_and_profile(self):
        dev = module()
        raw = b'{"payload":"exact", "signature":"bytes"}\n'
        manifest = {'release':'v1.4.2','components':[{'name':'root','url':'https://example/a.ipk'}]}
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            (folder/'system-update-root.json').write_bytes(raw)
            (folder/'a.ipk').write_bytes(b'package')
            profile={'apps':[{'id':'private'}], 'configuration':{'columns':7}}
            request=dev.acceptance_request(folder,manifest,'install',profile)
            self.assertEqual(request['profile'],profile)
            self.assertEqual(request['envelopeSha256'],hashlib.sha256(raw).hexdigest())
            self.assertEqual(request['packages'],{'root':'cGFja2FnZQ=='})
            with self.assertRaises(ValueError): dev.acceptance_request(folder,manifest,'install',None)

    def test_remote_admission_uses_pinned_interpreter_without_uploading_code(self):
        dev=module()
        class Remote:
            def __init__(self): self.calls=[]
            def run(self,command,data=None,timeout=30):
                self.calls.append((command,data,timeout))
                return '{"returnValue":true,"result":{"phase":"preflight"}}'
        remote=Remote()
        with patch.object(dev,'select_installed_python',return_value='/usr/bin/python3'):
            result=dev.admit(remote,{}, {'action':'preflight'},None)
        self.assertEqual(result,{'phase':'preflight'})
        self.assertEqual(len(remote.calls),1)
        command,data,_=remote.calls[0]
        self.assertTrue(command.startswith('/usr/bin/python3 -I -B -c '))
        self.assertEqual(json.loads(data),{'action':'preflight'})
        with patch.object(dev,'select_installed_python',return_value='/usr/bin/python3'):
            with patch.object(remote,'run',return_value='{"returnValue":false}'):
                with self.assertRaises(ValueError): dev.admit(remote,{}, {},None)



class TVDevArtifactTests(unittest.TestCase):
    def test_native_bridge_is_disabled_even_when_preview_bridge_does_not_load(self):
        dev=module()
        source=dev.ui_files()['dev-bridge.js']
        subprocess.run(['node','-e', r'''
const vm=require('vm'),fs=require('fs');let calls=0;
const window={localStorage:{getItem:()=>null,setItem:()=>{},removeItem:()=>{}},PalmServiceBridge:function(){calls++;this.call=()=>calls++;}};
vm.runInNewContext(fs.readFileSync(0,'utf8'),{window});
new window.PalmServiceBridge().call('luna://com.cleanyourtv.root.preview.service/enable','{}');
if(calls)throw Error('Native bridge remained reachable after mock load failure');
'''],input=source,check=True,capture_output=True)

    def test_product_scripts_never_start_when_native_isolation_cannot_be_locked(self):
        dev=module()
        files=dev.ui_files()
        self.assertIn('dev-entry.js', list(files), 'Product scripts need one fail-closed bootstrap')
        program=r'''
const vm=require('vm'),fs=require('fs'),source=fs.readFileSync(0,'utf8');
for(const property of ['PalmServiceBridge','webOS','PalmSystem','webOSSystem']){
 let starts=0,calls=0;
 const window={localStorage:{getItem:()=>null,setItem:()=>{},removeItem:()=>{}},PalmServiceBridge:function(){calls++;}};
 Object.defineProperty(window,property,{value:property==='PalmServiceBridge'?window.PalmServiceBridge:{native:true},writable:false,configurable:false});
 try{vm.runInNewContext(source,{window,document:{write:()=>starts++,getElementById:()=>null}});}catch(_){}
 if(starts||calls)throw Error('Product started after failed isolation: '+property);
}
'''
        subprocess.run(['node','-e',program],input=files['dev-entry.js'],check=True,capture_output=True)
        import re
        self.assertEqual(re.findall(rb'<script src="([^"]+)"',files['index.html']),[b'dev-entry.js'])

    def test_signed_manifest_rejects_version_drift_and_package_tampering(self):
        dev=module()
        signing=r'''
const crypto=require('crypto'),fs=require('fs'),input=JSON.parse(fs.readFileSync(0,'utf8'));
const key=crypto.generateKeyPairSync('rsa',{modulusLength:2048});
const raw=Buffer.from(JSON.stringify(input));
process.stdout.write(JSON.stringify({publicKey:key.publicKey.export({type:'spki',format:'pem'}),envelope:{payload:raw.toString('base64'),signature:crypto.sign('RSA-SHA256',raw,key.privateKey).toString('base64')}}));
'''
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'system-updater').mkdir(); (root/'updater-service').mkdir()
            (root/'system-updater/policy.js').write_bytes((ROOT/'system-updater/policy.js').read_bytes())
            folder=root/'bundle'; folder.mkdir()
            meta={'schema':1,'direct_tv':True,'preliminary':True,'workflow':'.github/workflows/tv-candidate.yml','release':'v1.4.2','source':'a'*40,'run_id':42,'attempt':1,'artifact':{'sha256':'b'*64},'package_job':{'id':3},'versions':{'root':'1.2.3','updater':'0.1.6'},'files':{}}
            notes='Bound preliminary QA source and artifact'
            manifest={'schema':1,'edition':'root','release':'v1.4.2','supervisor':1,'notes':notes,'components':[]}
            for name,version,filename,kind,application in [('root','1.2.4','root.ipk','ipk','com.cleanyourtv.root.preview'),('root-updater','0.1.6','updater.ipk','ipk','com.cleanyourtv.root.updater'),('root-infrastructure','1.2.3','infrastructure.tar.gz','infrastructure',None)]:
                raw=(name+' bytes').encode(); (folder/filename).write_bytes(raw)
                component={'name':name,'version':version,'url':'https://github.com/Razdva122/clean-your-tv-lg-webos/releases/download/v1.4.2/'+filename,'kind':kind,'size':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
                if application: component['application']=application
                manifest['components'].append(component); meta['files'][filename]=component['sha256']
            signed=json.loads(subprocess.check_output(['node','-e',signing],input=json.dumps(manifest).encode()))
            (root/'updater-service/release-public.pem').write_text(signed['publicKey'])
            meta['public_key_sha256']=hashlib.sha256(signed['publicKey'].encode()).hexdigest()
            (folder/'PROVENANCE.json').write_text(json.dumps(meta))
            (folder/'manifest.json').write_text(json.dumps(manifest))
            (folder/'system-update-root.json').write_text(json.dumps(signed['envelope']))
            with patch.object(dev,'ROOT',root), patch.object(dev.runpy,'run_path',return_value={'notes_for':lambda _:notes}):
                with self.assertRaisesRegex(ValueError,'version'):
                    dev.verify_bundle(folder,meta)
                meta['versions']['root']='1.2.4'
                manifest['components'][2]['version']='1.2.4'
                signed=json.loads(subprocess.check_output(['node','-e',signing],input=json.dumps(manifest).encode()))
                (root/'updater-service/release-public.pem').write_text(signed['publicKey'])
                meta['public_key_sha256']=hashlib.sha256(signed['publicKey'].encode()).hexdigest()
                (folder/'PROVENANCE.json').write_text(json.dumps(meta))
                (folder/'manifest.json').write_text(json.dumps(manifest))
                (folder/'system-update-root.json').write_text(json.dumps(signed['envelope']))
                self.assertEqual(dev.verify_bundle(folder,meta),manifest)
                (folder/'root.ipk').write_bytes(b'tampered bytes')
                with self.assertRaisesRegex(ValueError,'digest'): dev.verify_bundle(folder,meta)

    def test_signed_artifact_rejects_missing_digest_attempt_and_source_changes(self):
        dev=module()
        run={'id':12,'run_attempt':2,'head_sha':'a'*40}
        metadata={'run_id':90,'attempt':3}
        good={'id':34,'name':'signed-root-candidate-90-3','expired':False,'size_in_bytes':10,'digest':'sha256:'+'b'*64,'workflow_run':{'id':12,'head_sha':'a'*40}}
        with patch.object(dev,'api',return_value={'artifacts':[good]}): self.assertEqual(dev.signed_artifact(run,metadata),good)
        for field,value in [('digest',None),('name','signed-root-candidate-90-2'),('workflow_run',{'id':12,'head_sha':'c'*40})]:
            bad=dict(good,**{field:value})
            with patch.object(dev,'api',return_value={'artifacts':[bad]}):
                with self.assertRaises(ValueError): dev.signed_artifact(run,metadata)


if __name__ == '__main__': unittest.main()
