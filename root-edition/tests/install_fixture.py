"""Real on-disk current package/protocol fixture; only OS paths/UID are adapted."""
import hashlib,json,os,subprocess,sys,tempfile
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

class CurrentInstallation:
    def __enter__(self):
        self.stack=ExitStack();self.temp=self.stack.enter_context(tempfile.TemporaryDirectory())
        self.base=Path(self.temp).resolve();project=Path(__file__).resolve().parents[2]
        sys.path.insert(0,str(project/'root-edition'))
        import installation,install_device,python_binding,deploy,package_data,package_identity
        processes=self.base/'continuation-proc';processes.mkdir()
        self.stack.enter_context(patch.object(install_device,'PROC',processes))
        from updater import device as updater_device,package as updater_package
        from updater.store import Store,encode
        from cytv import package
        self.installation=installation;self.device_module=install_device
        import importlib.util
        spec=importlib.util.spec_from_file_location('fixture_root_provision',project/'root-edition/provision.py')
        self.provision=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.provision)
        self.stack.enter_context(patch.dict(sys.modules,{'provision':self.provision}))
        def home_bus(method):
            if method=='home-read':return {'returnValue':True,'settings':{'defaultApps':{'home':'com.webos.app.home'}}}
            if method=='home-profiles':return {'returnValue':True,'profiles':{'defaultApps':{'categories':{'home':'com.webos.app.home'}},'idleApp':{'appId':'com.webos.app.home','support':True}}}
            raise AssertionError('Unexpected Home bus mutation: '+method)
        self.stack.enter_context(patch.object(self.provision,'rpc',side_effect=home_bus))
        self.payload=self.base/'payload';self.payload.mkdir()
        for script,folder in (('root-edition/build.py','root'),('root-edition/build_updater.py','root-updater')):
            subprocess.run([sys.executable,str(project/script),'--output',str(self.payload/folder)],check=True,capture_output=True)
        package.personalize_root(self.payload/'root',{'apps':[{'id':'fixture.app','title':'Fixture','icon':'data:image/png;base64,AA=='}],'inputs':[]})
        self.lib=self.base/'lib';self.lib.mkdir();self.root=self.lib/'clean-your-tv-root';self.updater=self.lib/'clean-your-tv-root-updater';self.state=self.lib/'clean-your-tv-installation';self.installed=self.base/'installed'
        self.root.mkdir();self.updater.mkdir();(self.updater/'cache').mkdir();(self.updater/'code').mkdir()
        root_manifest=json.loads((self.payload/'root/bundle.json').read_text());up_manifest=json.loads((self.payload/'root-updater/bundle.json').read_text())
        for name in (*deploy.SUPPORT_FILES,*('runtime/'+n for n in deploy.RUNTIME_FILES),'bundle.json','release.json'):
            target=self.root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((self.payload/'root'/name).read_bytes());target.chmod(0o600)
        for folder,filename in (('root',root_manifest['package']),('root-updater','root-updater.ipk')):
            raw=(self.payload/folder/filename).read_bytes()
            import io,tarfile
            with tarfile.open(fileobj=io.BytesIO(package.read_ar(raw)['data.tar.gz']),mode='r:gz') as tar:
                for member in tar:
                    if not member.isfile():continue
                    target=self.installed/member.name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(tar.extractfile(member).read());target.chmod(0o755 if member.mode&0o111 else 0o644)
        for shared in (self.installed,self.installed/'usr',self.installed/'usr/palm',*(self.installed/'usr/palm'/kind for kind in ('applications','services','packages'))):shared.chmod(0o777)
        proof={'version':1,'mode':'recovery-only','files':{str(self.root/'runtime'/name):hashlib.sha256((self.root/'runtime'/name).read_bytes()).hexdigest() for name in deploy.RUNTIME_FILES}}
        self.root_store=Store(self.root,uid=os.getuid());self.root_store.write('recovery-provision',proof)
        self.root_store.write('deploy',{'app':deploy.APP,'stage':'installed-recovery-only'})
        from updater.bootstrap import persistent_code
        code=persistent_code(up_manifest)
        for name in code:
            target=self.updater/'code'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((self.payload/'root-updater'/name).read_bytes());target.chmod(0o600)
        self.up_store=Store(self.updater,uid=os.getuid());self.up_store.write('infrastructure',{'schema':1,'runtime':1,'updater':1,'code':code,'recovery_sha256':hashlib.sha256((self.root/'recovery-provision.json').read_bytes()).hexdigest()})
        self.up_store.write('bootstrap',{'phase':'complete'})
        raw=(self.payload/'root'/root_manifest['package']).read_bytes();digest=hashlib.sha256(raw).hexdigest();(self.updater/'cache'/(digest+'.ipk')).write_bytes(raw)
        self.up_store.write('current',{'version':json.loads((self.payload/'root/release.json').read_text())['version'],'size':len(raw),'sha256':digest,'local':True})
        up_raw=(self.payload/'root-updater/root-updater.ipk').read_bytes();files=package.data_files(up_raw)
        self.up_store.write('installed-package',{'schema':1,'files':{n:hashlib.sha256(b).hexdigest() for n,b in files.items()},'executable':[n for n in files if n.endswith('/startup.sh')]})
        profile={'schema':1,'inventory':{'apps':[{'id':'fixture.app','title':'Saved profile','icon':'data:image/png;base64,AA=='}],'inputs':[]},'config':{'columns':5,'dockApps':['fixture.app'],'hiddenApps':[]},'settings':{'tvhome.language':'en'}}
        self.up_store.write('profile-'+'f'*32,profile)
        prior=self.up_store.read('current');parts=prior['version'].split('.');parts[-1]=str(int(parts[-1])+1)
        self.up_store.write('transaction',{'schema':1,'id':'f'*32,'phase':'aborted','homeResumePhase':'aborted','prior':prior,'candidate':{'version':'.'.join(parts),'local':True,'sha256':'f'*64,'size':1},'created':1,'updated':2,'oldRoute':None,'rollbackAttempted':False,'installEvidence':{'submitted':None,'terminal':None},'rollbackEvidence':{'submitted':None,'terminal':None},'profile':'profile-'+'f'*32,'profileDigest':hashlib.sha256(encode(profile)).hexdigest()})
        from updater.core import Manager
        assert Manager(self.up_store,None).status()['phase']=='aborted'
        self.off=self.root/'persistent-intent.json';self.off.write_text(json.dumps({'version':1,'generation':7,'phase':'disabled','enabled':False,'boot':'fixture-boot','token':'fixture-off'}));self.before_off=self.off.read_bytes();self.before_profile=(self.updater/('profile-'+'f'*32+'.json')).read_bytes()
        uid=os.getuid()
        class FixtureStore(Store):
            def _walk(self,path):self.uid=uid;return super()._walk(path)
        original_safe=updater_package.safe_bytes
        def safe(path,limit=32*1024*1024,uid=None):return original_safe(path,limit=limit,uid=os.getuid() if uid==0 else uid)
        original_package_read=package_data.read_verified
        def package_read(path,**kw):return original_package_read(path,**{**kw,'uid':os.getuid(),'installed':self.installed})
        self.stack.enter_context(patch.object(package_data,'read_verified',side_effect=package_read))
        self.stack.enter_context(patch.object(package_identity,'read_verified',side_effect=package_read))
        self.stack.enter_context(patch.object(package_identity,'STATES',{package_identity.ROOT:self.root,package_identity.UPDATER:self.updater,package_identity.SYSTEM:self.lib/'clean-your-tv-system-updater'}))
        self.stack.enter_context(patch.object(package_identity,'Store',FixtureStore))
        original_identity=package_identity.identity
        self.stack.enter_context(patch.object(package_identity,'identity',side_effect=lambda *a,**kw:original_identity(*a,**{**kw,'uid':os.getuid()})))
        real_path=Path
        def path(value):
            raw=str(value)
            if raw=='/media/developer/apps':return self.installed
            if raw.startswith('/var/lib/clean-your-tv-'):return self.lib/raw.split('/')[-1]
            return real_path(value)
        journals={name:(self.lib/p.parent.name/p.name,field,finished) for name,(p,field,finished) in installation.JOURNALS.items()}
        for obj,name,value in ((installation,'Store',FixtureStore),(installation,'Path',path),(installation,'STATE',self.state),(installation,'JOURNALS',journals),
          (install_device,'Store',FixtureStore),(install_device,'ROOT',self.root),(install_device,'UPDATER',self.updater),(install_device,'SUPERVISOR',self.lib/'clean-your-tv-system-updater'),(install_device,'INSTALLED',self.installed),
          (install_device,'safe_bytes',safe),(updater_device,'safe_bytes',safe),(python_binding,'_read',safe),
          (deploy,'STATE',self.root),(deploy,'INSTALLED',self.installed),(deploy,'require_device',lambda:None),(deploy,'require_node',lambda:None)):
            self.stack.enter_context(patch.object(obj,name,value))
        self.stack.enter_context(patch.object(install_device.sys,'platform','linux'))
        self.stack.enter_context(patch.object(install_device.platform,'machine',return_value='armv7l'))
        elf=bytearray(40);elf[:6]=b'\x7fELF\x01\x01';elf[18]=40;elf[39]=5
        previous_safe=install_device.safe_bytes
        self.stack.enter_context(patch.object(install_device,'safe_bytes',side_effect=lambda path,*a,**kw: bytes(elf) if path==Path('/bin/sh').resolve() else previous_safe(path,*a,**kw)))
        self.stack.enter_context(patch.object(install_device.sys,'executable','/usr/bin/python3'))
        self.owner=installation.Ownership(Store(self.state,uid=os.getuid()))
        self.stack.enter_context(patch('observed_install.install',side_effect=AssertionError('package submission during maintenance')))
        self.stack.enter_context(patch('observed_install.remove',side_effect=AssertionError('package removal during maintenance')))
        return self
    def retain(self,identifier,stage='root-deploy'):
        record=self.owner.store.read('request-'+identifier)
        with self.owner.operation('product',self.owner.status()['journal'],resume=record['lease']) as lease:self.owner.stage(lease,stage,terminal=False)
        record.update(state='pending',stage=stage,code='operation_pending');self.owner.store.write('request-'+identifier,record)

    def snapshot(self,identifier,action='install'):
        import shutil
        target=self.state/('request-'+identifier);shutil.copytree(self.payload,target)
        root_manifest=json.loads((target/'root/bundle.json').read_text())
        from install_driver import root_review_binding
        receipt={'root_binding':root_review_binding(target,{'root':root_manifest}),'operation':identifier,'action':action,'candidate_sha256':'0'*64,'options':{'migrate':False,'prepare_supervisor':False},
          'worker_sha256':hashlib.sha256((target/'root-updater/bundle.json').read_bytes()).hexdigest(),
          'root_static':{n:d for n,d in root_manifest['files'].items() if n not in (root_manifest['package'],'release.json','SHA256SUMS')}}
        self.owner.store.write('submission-'+identifier,receipt)
        return target

    def assert_preserved(self,test):
        test.assertEqual(self.off.read_bytes(),self.before_off);test.assertEqual((self.updater/('profile-'+'f'*32+'.json')).read_bytes(),self.before_profile)
        startup=self.installed/'usr/palm/applications/com.cleanyourtv.root.preview/startup.sh'
        test.assertEqual(startup.stat().st_mode&0o777,0o755)
    def __exit__(self,*args):return self.stack.__exit__(*args)


def altered_bootstrap_bundle(source,target,package_name,code=False):
    """A self-consistent alternate bundle: same IPK identity, changed payload bytes."""
    import shutil,io,tarfile
    from cytv import package
    shutil.copytree(source,target)
    if code:
        (target/'service.js').write_bytes((target/'service.js').read_bytes()+b'\n// alternate bundle\n')
        name='service.js'
    else:
        name=package_name
        raw=(target/name).read_bytes();parts=package.read_ar(raw);files=package.data_files(raw)
        index=next(n for n in files if n.endswith('/index.html'))
        files[index]+=b'<!-- alternate same-version bytes -->'
        with tarfile.open(fileobj=io.BytesIO(parts['data.tar.gz']),mode='r:gz') as archive:
            executable={m.name for m in archive if m.isfile() and m.mode&0o111}
        parts['data.tar.gz']=package.tgz(files,executable=executable,directories=False)
        (target/name).write_bytes(package.ar(parts))
    manifest=json.loads((target/'bundle.json').read_text())
    manifest['files'][name]=hashlib.sha256((target/name).read_bytes()).hexdigest()
    (target/'bundle.json').write_text(json.dumps(manifest))
    return target
