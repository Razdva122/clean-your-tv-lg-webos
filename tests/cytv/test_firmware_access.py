"""Real registration changes preserve published updater and removal contracts."""
import ast
import hashlib
import json
import os
from pathlib import Path
import tarfile
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
from cytv import firmware_access

if os.name != 'posix':
    raise unittest.SkipTest('TV firmware registration requires POSIX locks and filesystem semantics')

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'root-edition'))
LEGACY=types.ModuleType('legacy_firmware_provision')
archive=ROOT/'tests/system_updates/fixtures/public-1.3.0-supervisor.tar.gz'
provenance=json.loads(archive.with_suffix('.provenance.json').read_bytes())
assert hashlib.sha256(archive.read_bytes()).hexdigest()==provenance['sha256']
with tarfile.open(archive) as stream:
    frozen=stream.extractfile('infrastructure/updater/provision.py').read()
assert hashlib.sha256(frozen).hexdigest()==provenance['files']['infrastructure/updater/provision.py']
exec(frozen.decode(),LEGACY.__dict__)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def encode(value):return (json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
APP='com.cleanyourtv.root.preview';SERVICE=APP+'.service';GROUP=SERVICE+'.control'

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT);self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name);self.root=self.base/'root';self.bus=self.base/'bus';self.apps=self.base/'apps';self.install=self.base/'installation';self.bundle=self.base/'bundle'
        for p in (self.root,self.bus,self.apps,self.install,self.bundle):p.mkdir(mode=0o700)
        (self.bundle/'runtime').mkdir();source=(ROOT/'root-edition/runtime/cli.py').read_bytes();(self.bundle/'runtime/cli.py').write_bytes(source)
        (self.bundle/'bundle.json').write_bytes(encode({'files':{'runtime/cli.py':sha(source)}}))
        code=firmware_access.program(self.bundle);tree=ast.parse(code);ns={};exec(ast.get_source_segment(code,tree.body[0]),ns);self.function=ns['firmware_access']
        self.paths={key:self.bus/folder/(SERVICE+suffix) for key,folder,suffix in [('service','services.d','.service'),('role','roles.d','.service.json'),('client','client-permissions.d','.service.json'),('api','api-permissions.d','.api.json')]}
        self.original={'service':'[D-BUS Service]\nName='+SERVICE+'\nExec=/usr/bin/run-js-service -n '+str(LEGACY.SERVICE)+'\n','role':json.dumps({'appId':SERVICE,'allowedNames':['*'],'permissions':[{'outbound':['*']}]}),'client':'{}','api':'{}'}
        raw=LEGACY.plan(self.original);files={}
        for key,path in self.paths.items():
            path.parent.mkdir(mode=0o700,exist_ok=True);path.write_bytes(raw[key]);path.chmod(0o600)
            files[str(path)]={'original':self.original[key],'original_sha256':sha(self.original[key].encode()),'installed_sha256':sha(raw[key]),'mode':0o600,'uid':os.getuid(),'gid':os.getgid()}
        self.snapshot=self.root/'ls2-provision-snapshot.json';self.snapshot.write_bytes(encode({'version':1,'service':SERVICE,'files':files}));self.snapshot.chmod(0o600)
        code=self.root/'runtime/cli.py';code.parent.mkdir(mode=0o700);code.write_bytes(b'trusted old runtime');code.chmod(0o600)
        self.proof=self.root/'recovery-provision.json';self.proof.write_bytes(encode({'version':1,'mode':'recovery-only','files':{str(code):sha(code.read_bytes())}}));self.proof.chmod(0o600)
        (self.root/'deploy.json').write_bytes(encode({'stage':'installed-recovery-only'}));(self.root/'deploy.json').chmod(0o600)
        info=self.apps/'applications'/APP/'appinfo.json';info.parent.mkdir(parents=True);info.write_bytes(encode({'id':APP,'version':'0.4.0'}));info.chmod(0o600)
        self.manifest=self.bus/'manifests.d'/(APP+'.json');self.manifest.parent.mkdir(mode=0o700)
        self.normal={'version':'0.4.0','id':APP,'serviceFiles':[str(self.paths['service'])],'apiPermissionFiles':[str(self.paths['api'])],'roleFiles':[str(self.paths['role']),str(self.bus/'roles.d'/(APP+'.app.json'))],'clientPermissionFiles':[str(self.paths['client']),str(self.bus/'client-permissions.d'/(APP+'.app.json'))]}
        self.manifest.write_bytes(encode(self.normal));self.manifest.chmod(0o640)
        self.api=self.root/'permissions/homebrew-configuration.api.json';self.receipt=self.root/'firmware-permissions.json';self.events=[]
    def grant(self,enable=True,lock_product=True):
        return self.function(self.root,self.bus,self.apps,self.install,enable=enable,lock_product=lock_product,refresh=lambda:self.events.append('scan'),uid=os.getuid())
    def test_shared_compositor_activation_preserves_active_registration_proof(self):
        path=self.paths['service'];raw=path.read_bytes().replace(('Name='+SERVICE).encode(),('Name='+SERVICE+';com.webos.cleanyourtv.root.lease').encode());path.write_bytes(raw)
        saved=json.loads(self.snapshot.read_bytes());saved['capabilities']=['theme-receiver-v1','wallpaper-media-v1','c1-keyfilter-v1']
        saved['files'][str(path)]['installed_sha256']=sha(raw);self.snapshot.write_bytes(encode(saved))
        self.assertTrue(self.grant()['permissions_installed'])
        path.write_bytes(b'changed')
        with self.assertRaises(ValueError):self.grant()

    def test_explicit_repair_runs_only_after_protected_checks_then_strict_readback(self):
        info=self.apps/'applications'/APP/'appinfo.json';info.parent.chmod(0o777)
        before=self.manifest.read_bytes();calls=[]
        def repair(version):
            calls.append(version);info.parent.chmod(0o755)
        damaged=dict(self.normal,apiPermissionFiles=['foreign']);self.manifest.write_bytes(encode(damaged))
        with self.assertRaises(ValueError):
            self.function(self.root,self.bus,self.apps,self.install,repair=repair,uid=os.getuid(),refresh=lambda:None)
        self.assertEqual(calls,[]);self.assertEqual(info.parent.stat().st_mode&0o777,0o777)
        self.manifest.write_bytes(before)
        result=self.function(self.root,self.bus,self.apps,self.install,repair=repair,uid=os.getuid(),refresh=lambda:self.events.append('scan'))
        self.assertEqual(calls,['0.4.0']);self.assertTrue(result['permissions_installed'])
        info.parent.chmod(0o777)
        with self.assertRaises(ValueError):
            self.function(self.root,self.bus,self.apps,self.install,repair=lambda version:None,uid=os.getuid(),refresh=lambda:None)

    def test_repair_is_never_automatic_or_part_of_revocation(self):
        for enable,automatic in [(False,False),(True,True)]:
            calls=[]
            with self.assertRaises(ValueError):
                self.function(self.root,self.bus,self.apps,self.install,enable=enable,automatic=automatic,repair=lambda version:calls.append(version),uid=os.getuid())
            self.assertFalse(calls);self.assertFalse(self.receipt.exists())

    def test_repair_stream_authenticates_and_executes_real_private_inventory_modules(self):
        import subprocess,sys
        from cytv.package import ipk
        modules={'updater/store.py','updater/package.py','package_data.py','package_identity.py','installation.py'}
        manifest=json.loads((self.bundle/'bundle.json').read_text())
        for name in modules:
            target=self.bundle/name;target.parent.mkdir(exist_ok=True);raw=(ROOT/'root-edition'/name).read_bytes();target.write_bytes(raw);manifest['files'][name]=sha(raw)
        (self.bundle/'bundle.json').write_bytes(encode(manifest))
        sdk=self.base/'sdk';prefix='usr/palm/applications/'+APP+'/'
        files={prefix+'appinfo.json':encode({'id':APP,'version':'0.4.0','type':'web'}),prefix+'index.html':b'owned',
               'usr/palm/packages/'+APP+'/packageinfo.json':encode({'id':APP,'app':APP,'version':'0.4.0'}),
               'usr/palm/services/'+SERVICE+'/service.js':b'owned'}
        raw=ipk(APP,'0.4.0',files);updater=self.base/'clean-your-tv-root-updater';(updater/'cache').mkdir(parents=True,mode=0o700)
        (updater/'cache'/(sha(raw)+'.ipk')).write_bytes(raw);(updater/'cache'/(sha(raw)+'.ipk')).chmod(0o600)
        (updater/'current.json').write_bytes(encode({'version':'0.4.0','sha256':sha(raw),'size':len(raw),'local':True}));(updater/'current.json').chmod(0o600)
        for name,data in files.items():
            target=sdk/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);target.chmod(0o777);target.parent.chmod(0o777)
        source=firmware_access.program(self.bundle,repair=True)
        states={APP:str(self.root),'com.cleanyourtv.root.updater':str(updater),'com.cleanyourtv.system.updater':str(self.base/'clean-your-tv-system-updater')}
        source=source.replace('repair_sdk_permissions(version=version)', 'repair_sdk_permissions(installed='+repr(str(sdk))+',states='+repr(states)+',uid='+str(os.getuid())+',version=version)')
        source=source.replace('firmware_access(repair=lambda', 'firmware_access(root='+repr(str(self.root))+',base='+repr(str(self.bus))+',installed='+repr(str(sdk/'usr/palm'))+',installation='+repr(str(self.install))+',uid='+str(os.getuid())+',refresh=lambda:None,repair=lambda')
        result=subprocess.run([sys.executable,'-I','-'],input=source,text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr);self.assertTrue(json.loads(result.stdout)['permissions_installed'])
        self.assertFalse((sdk/prefix/'appinfo.json').stat().st_mode&0o022)
        dependency=self.bundle/'package_identity.py';dependency.write_bytes(b'changed')
        with self.assertRaises(ValueError):firmware_access.program(self.bundle,repair=True)

    def test_only_configuration_api_and_legacy_updater_bytes_unchanged(self):
        before={p:p.read_bytes() for p in [self.snapshot,self.proof,*self.paths.values()]}
        self.grant();self.grant()
        self.assertEqual(json.loads(self.api.read_bytes()),{GROUP:['org.webosbrew.hbchannel.service/getConfiguration','org.webosbrew.hbchannel.service/setConfiguration']})
        self.assertEqual(json.loads(self.manifest.read_bytes())['apiPermissionFiles'],[str(self.paths['api']),str(self.api)])
        for p,raw in before.items():self.assertEqual(p.read_bytes(),raw)
        # This is the exact computation used by the retained updater's
        # repair_registration; changing snapshot hashes alone is unsafe.
        planned=LEGACY.plan(self.original);entries=json.loads(self.snapshot.read_bytes())['files']
        for key,path in self.paths.items():self.assertEqual(sha(planned[key]),entries[str(path)]['installed_sha256'])
    def test_revoke_restores_manifest_and_original_rollback_revokes_clients(self):
        original=self.manifest.read_bytes();self.grant();self.grant(False)
        self.assertEqual(self.manifest.read_bytes(),original);self.assertFalse(self.api.exists());self.assertEqual(json.loads(self.receipt.read_bytes())['phase'],'disabled')
        self.grant()
        original_clients=json.loads(json.loads(self.snapshot.read_bytes())['files'][str(self.paths['client'])]['original'])
        self.assertFalse(any(GROUP in groups for groups in original_clients.values()),'old provision.rollback removes the grant from every Home client')
    def test_drift_pending_and_poisoned_code_prevent_registration(self):
        for bad in ('drift','link','lease','transaction','proof','manifest'):
            with self.subTest(bad=bad):
                target=self.paths['client'];old=target.read_bytes();normal=self.manifest.read_bytes()
                if bad=='drift':target.write_bytes(b'foreign')
                if bad=='link':target.unlink();target.symlink_to(self.paths['api'])
                if bad=='lease':(self.install/'operation.json').write_bytes(encode({'schema':1,'terminal':False}))
                if bad=='transaction':(self.root.parent/'clean-your-tv-root-updater').mkdir(exist_ok=True);(self.root.parent/'clean-your-tv-root-updater/transaction.json').write_bytes(b'{')
                if bad=='proof':(self.root/'runtime/cli.py').write_bytes(b'tampered')
                if bad=='manifest':self.manifest.write_bytes(encode(dict(self.normal,apiPermissionFiles=['foreign'])))
                with self.assertRaises((ValueError,OSError)):self.grant()
                self.assertFalse(self.api.exists());self.assertFalse(self.receipt.exists())
                if target.is_symlink():target.unlink()
                target.write_bytes(old);target.chmod(0o600);self.manifest.write_bytes(normal)
                (self.install/'operation.json').unlink(missing_ok=True);(self.root.parent/'clean-your-tv-root-updater/transaction.json').unlink(missing_ok=True)
                (self.root/'runtime/cli.py').write_bytes(b'trusted old runtime')
    def test_each_interrupted_write_resumes(self):
        baseline=self.manifest.read_bytes();replace=os.replace
        for cut in range(1,5):
            with self.subTest(cut=cut):
                counter=0
                def crash(src,dst):
                    nonlocal counter
                    replace(src,dst);counter+=1
                    if counter==cut:raise OSError('power loss')
                with patch('os.replace',side_effect=crash),self.assertRaises(OSError):self.grant()
                self.grant();self.assertEqual(json.loads(self.receipt.read_bytes())['phase'],'enabled')
                self.grant(False);self.assertEqual(self.manifest.read_bytes(),baseline)
    def test_new_sdk_version_reconciles_without_changing_retained_snapshot(self):
        self.grant();before=self.snapshot.read_bytes()
        next_manifest=dict(self.normal,version='0.4.1');self.manifest.write_bytes(encode(next_manifest))
        info=self.apps/'applications'/APP/'appinfo.json';info.write_bytes(encode({'id':APP,'version':'0.4.1'}))
        self.grant(lock_product=False)
        self.assertIn(str(self.api),json.loads(self.manifest.read_bytes())['apiPermissionFiles'])
        self.assertEqual(self.snapshot.read_bytes(),before)
        self.grant(False);self.assertEqual(json.loads(self.manifest.read_bytes()),next_manifest)
    def test_scan_failure_is_resumable_and_manifest_metadata_is_preserved(self):
        metadata=self.manifest.stat();self.assertEqual(self.grant()['permissions_installed'],True)
        self.assertEqual((self.manifest.stat().st_uid,self.manifest.stat().st_gid,self.manifest.stat().st_mode),(metadata.st_uid,metadata.st_gid,metadata.st_mode))
        self.grant(False)
        def fail():raise OSError('scan failed')
        with self.assertRaises(OSError):self.function(self.root,self.bus,self.apps,self.install,refresh=fail,uid=os.getuid())
        self.grant();self.assertEqual(json.loads(self.receipt.read_bytes())['phase'],'enabled')
    def test_explicit_revoke_stays_off_during_automatic_registration(self):
        self.grant();self.grant(False)
        self.function(self.root,self.bus,self.apps,self.install,automatic=True,lock_product=False,refresh=lambda:self.events.append('scan'),uid=os.getuid())
        self.assertFalse(self.api.exists());self.assertEqual(json.loads(self.manifest.read_bytes()),self.normal)
        self.grant();self.assertTrue(self.api.exists())

    def test_revoke_does_not_trust_or_require_installed_appinfo(self):
        info=self.apps/'applications'/APP/'appinfo.json';original=info.read_bytes()
        protected=[self.snapshot,self.proof,*self.paths.values()]
        intent=self.root/'persistent-intent.json';intent.write_bytes(b'{"enabled":false}');intent.chmod(0o600);protected.append(intent)
        before={p:p.read_bytes() for p in protected};metadata=self.manifest.stat()
        for damage in ('writable-directory','missing-info','invalid-info'):
            with self.subTest(damage=damage):
                info.parent.chmod(0o755);info.write_bytes(original);info.chmod(0o600)
                self.grant()
                if damage=='writable-directory':info.parent.chmod(0o777)
                elif damage=='missing-info':info.unlink()
                else:info.write_bytes(b'not trusted metadata')
                self.grant(False)
                self.assertFalse(self.api.exists());self.assertEqual(self.manifest.read_bytes(),encode(self.normal))
                self.assertEqual(json.loads(self.receipt.read_bytes())['phase'],'disabled')
                after=self.manifest.stat();self.assertEqual((after.st_uid,after.st_gid,after.st_mode),(metadata.st_uid,metadata.st_gid,metadata.st_mode))
                for path,raw in before.items():self.assertEqual(path.read_bytes(),raw)
                disabled=self.receipt.read_bytes()
                with self.assertRaises((ValueError,OSError)):self.grant()
                with self.assertRaises((ValueError,OSError)):
                    self.function(self.root,self.bus,self.apps,self.install,automatic=True,lock_product=False,refresh=lambda:None,uid=os.getuid())
                self.assertFalse(self.api.exists());self.assertEqual(self.receipt.read_bytes(),disabled)
                info.parent.chmod(0o755);info.write_bytes(original);info.chmod(0o600)

    def test_revoke_regenerated_manifest_uses_protected_version_without_sdk_metadata(self):
        self.grant();normal=dict(self.normal,version='0.4.1')
        granted=dict(normal,apiPermissionFiles=[str(self.paths['api']),str(self.api)])
        self.manifest.write_bytes(encode(granted));(self.apps/'applications'/APP/'appinfo.json').unlink()
        self.grant(False)
        self.assertEqual(json.loads(self.manifest.read_bytes()),normal);self.assertFalse(self.api.exists())

    def test_interrupted_revoke_resumes_without_sdk_metadata(self):
        self.grant();(self.apps/'applications'/APP/'appinfo.json').unlink()
        def fail():raise OSError('scan failed')
        with self.assertRaises(OSError):
            self.function(self.root,self.bus,self.apps,self.install,enable=False,refresh=fail,uid=os.getuid())
        self.assertEqual(json.loads(self.receipt.read_bytes())['phase'],'disabling')
        self.assertEqual(json.loads(self.manifest.read_bytes()),self.normal);self.assertTrue(self.api.exists())
        self.grant(False)
        self.assertEqual(json.loads(self.receipt.read_bytes())['phase'],'disabled');self.assertFalse(self.api.exists())

    def test_revoke_keeps_manifest_receipt_and_api_guards_without_sdk_metadata(self):
        self.grant();(self.apps/'applications'/APP/'appinfo.json').unlink()
        original={p:p.read_bytes() for p in (self.manifest,self.receipt,self.api)}
        for damage in ('version','shape','unsafe-manifest','missing-receipt','api-drift','enabling'):
            with self.subTest(damage=damage):
                if damage in ('version','shape'):
                    value=json.loads(original[self.manifest]);value['version' if damage=='version' else 'foreign']='invalid';self.manifest.write_bytes(encode(value))
                elif damage=='unsafe-manifest':self.manifest.chmod(0o666)
                elif damage=='missing-receipt':self.receipt.unlink()
                elif damage=='api-drift':self.api.write_bytes(b'foreign')
                else:self.receipt.write_bytes(encode(dict(json.loads(original[self.receipt]),phase='enabling')))
                before={p:p.read_bytes() if p.exists() else None for p in original}
                with self.assertRaises((ValueError,OSError)):self.grant(False)
                self.assertEqual({p:p.read_bytes() if p.exists() else None for p in original},before)
                for path,raw in original.items():path.write_bytes(raw)
                self.manifest.chmod(0o640);self.receipt.chmod(0o600)
    def test_runtime_registration_failure_never_blocks_home_or_update_finish(self):
        raw=(ROOT/'root-edition/runtime/cli.py').read_text();tree=ast.parse(raw)
        selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('execute','reconcile_firmware_access')]
        calls=[]
        def failure(**kwargs):calls.append(kwargs);raise ValueError('permission conflict')
        d=types.SimpleNamespace(STATE=self.root,EXPECTED_UID=os.getuid(),main=lambda mode:{'home':'safe'})
        ns={'d':d,'os':os,'firmware_access':failure,'gate_backend':lambda:None}
        for node in selected:exec(ast.get_source_segment(raw,node),ns)
        intent=types.SimpleNamespace(boot=lambda:None)
        updates=types.SimpleNamespace(finish=lambda *args:{'finished':True},suspend=lambda *args:None,abort=lambda *args:None)
        with patch.dict(sys.modules,{'intent_runtime':intent,'update_guard':updates}):
            self.assertEqual(ns['execute']('boot'),{'home':'safe'})
            self.assertEqual(ns['execute']('finish-update','tx'),{'finished':True})
        self.assertEqual(calls,[{'lock_product':False,'automatic':True,'feature':f} for _ in range(2) for f in ('firmware','theme-receiver')]+[{'lock_product':False,'automatic':True,'feature':'weather'}])

    def test_wallpaper_startup_prepares_only_own_apis_before_backend_dispatch(self):
        raw=(ROOT/'root-edition/runtime/cli.py').read_text();tree=ast.parse(raw);calls=[]
        ns={'firmware_access':lambda **kw:calls.append(kw) or {'returnValue':True},
            'gate_backend':lambda: self.fail('Wallpaper permission setup must precede backend dispatch')}
        for name in ('execute',):
            node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
            exec(ast.get_source_segment(raw,node),ns)
        self.assertTrue(ns['execute']('provision-wallpaper-access')['returnValue'])
        self.assertEqual(calls,[{'lock_product':False,'automatic':True,'feature':feature} for feature in ('theme-receiver','wallpaper-media','weather')])

    def test_host_streams_verified_source_instead_of_a_long_ssh_command(self):
        from cytv.operations import Installer
        from unittest.mock import MagicMock
        calls=[]
        class Remote:
            root=True
            def run(remote,command,data=None,timeout=30):
                calls.append((command,data,timeout));return json.dumps({'returnValue':True,'permissions_installed':True})
        store=MagicMock();store.pending.return_value=None
        import shutil
        payload=self.base/'payload';payload.mkdir();shutil.copytree(self.bundle,payload/'root')
        installer=Installer(Remote(),store,{'edition':'root'},payload,{},lambda *_:None)
        with patch.object(installer,'_python',return_value='/usr/bin/python3'):
            installer.configure_firmware_access(True)
        self.assertLess(len(calls[0][0]),512,'TV SSH servers limit the exec request size')
        self.assertIn('-I -',calls[0][0]);self.assertIn(b'def firmware_access(',calls[0][1])

    def test_sdk_world_writable_containers_are_read_only_and_exactly_scoped(self):
        virtual=self.base/'virtual-media';app=virtual/'developer/apps/usr/palm/applications'/APP
        app.mkdir(parents=True);info=app/'appinfo.json';info.write_bytes(encode({'id':APP,'version':'0.4.0'}));info.chmod(0o600)
        for parent in (app.parent,*list(app.parents)[1:6]):parent.chmod(0o777)
        app.chmod(0o755);virtual.chmod(0o755)
        real_lstat,real_stat,real_open=Path.lstat,Path.stat,os.open
        def translate(path):
            value=str(path)
            return virtual/value[len('/media/'):] if value.startswith('/media/') else virtual if value=='/media' else path
        def mapped_stat(path,*args,**kwargs):return real_stat(translate(path),*args,**kwargs)
        def mapped_open(path,*args,**kwargs):return real_open(translate(path),*args,**kwargs)
        for mode in ('normal','unsafe-app','symlink-container'):
            with self.subTest(mode=mode):
                def mapped_lstat(path):
                    value=real_lstat(translate(path))
                    if mode=='symlink-container' and str(path)=='/media/developer/apps':
                        fields=list(value);fields[0]=0o120777;return os.stat_result(fields)
                    return value
                if mode=='unsafe-app':app.chmod(0o777)
                with patch.object(Path,'lstat',mapped_lstat),patch.object(Path,'stat',mapped_stat),patch('os.open',side_effect=mapped_open):
                    call=lambda enabled:self.function(self.root,self.bus,Path('/media/developer/apps/usr/palm'),self.install,enable=enabled,refresh=lambda:None,uid=os.getuid())
                    if mode=='normal':call(True);self.assertTrue(self.api.exists());call(False)
                    else:
                        with self.assertRaises(ValueError):call(True)
                        self.assertFalse(self.api.exists())
                app.chmod(0o755)

    def test_nondefault_sdk_manifest_gid_is_preserved(self):
        gids=[gid for gid in os.getgroups() if gid!=os.getegid()]
        if not gids:self.skipTest('No alternate permitted group on this host')
        os.chown(self.manifest,-1,gids[0]);before=self.manifest.stat()
        self.grant();self.grant(False)
        after=self.manifest.stat()
        self.assertEqual((after.st_uid,after.st_gid,after.st_mode),(before.st_uid,before.st_gid,before.st_mode))

    def test_completed_registration_does_not_rescan_or_rewrite_on_boot(self):
        self.grant();count=len(self.events);before=self.receipt.stat().st_mtime_ns
        self.function(self.root,self.bus,self.apps,self.install,automatic=True,lock_product=False,refresh=lambda:self.events.append('scan'),uid=os.getuid())
        self.assertEqual(len(self.events),count);self.assertEqual(self.receipt.stat().st_mtime_ns,before)

    def receiver(self, enable=True):
        return self.function(self.root,self.bus,self.apps,self.install,feature='theme-receiver',enable=enable,refresh=lambda:self.events.append('scan'),uid=os.getuid())

    def media(self, enable=True):
        return self.function(self.root,self.bus,self.apps,self.install,feature='wallpaper-media',enable=enable,refresh=lambda:self.events.append('scan'),uid=os.getuid())

    def protect_media_worker(self):
        service=self.root/'service';service.mkdir()
        package=service/'package.json';package.write_bytes(encode({'name':SERVICE,'wallpaperMediaProtocol':1}));package.chmod(0o600)
        worker=service/'service.js';worker.write_bytes(b'verified media worker');worker.chmod(0o600)
        proof=json.loads(self.proof.read_bytes())
        proof['files'].update({str(path):sha(path.read_bytes()) for path in (package,worker)})
        self.proof.write_bytes(encode(proof))

    def weather(self, enable=True):
        return self.function(self.root,self.bus,self.apps,self.install,feature='weather',enable=enable,refresh=lambda:self.events.append('scan'),uid=os.getuid())

    def test_weather_attachment_requires_protected_worker_and_preserves_existing_receipts(self):
        before=self.manifest.read_bytes()
        with self.assertRaises(ValueError):self.weather()
        self.assertEqual(self.manifest.read_bytes(),before)
        self.protect_media_worker()
        with self.assertRaises(ValueError):self.weather()
        package=self.root/'service/package.json'
        package.write_bytes(encode({'name':SERVICE,'wallpaperMediaProtocol':1,'weatherForecastProtocol':1}))
        proof=json.loads(self.proof.read_bytes());proof['files'][str(package)]=sha(package.read_bytes());self.proof.write_bytes(encode(proof))
        block=self.root/'update-block.json';block.write_bytes(encode({'transaction':'a'*32}));block.chmod(0o600)
        with self.assertRaises(ValueError):self.weather()
        block.unlink()
        self.receiver();self.media()
        receipts={p:p.read_bytes() for p in (self.root/'theme-receiver-permissions.json',self.root/'wallpaper-media-permissions.json',self.snapshot,self.proof,*self.paths.values())}
        self.weather();self.receiver();self.media()
        api=self.root/'permissions/weather.api.json'
        self.assertEqual(json.loads(api.read_bytes()),{GROUP:[SERVICE+'/weatherForecast',SERVICE+'/weatherForecastCancel']})
        for path,raw in receipts.items():self.assertEqual(path.read_bytes(),raw)
        self.weather(False);self.media(False);self.receiver(False)
        self.assertEqual(json.loads(self.manifest.read_bytes()),self.normal)
        self.assertFalse(api.exists())
        self.assertFalse((self.root/'weather-permissions.json').exists(), 'old removal must see no unknown receipt')

    def test_weather_suspend_reverts_grant_before_older_code_is_installed(self):
        self.protect_media_worker()
        package=self.root/'service/package.json';package.write_bytes(encode({'name':SERVICE,'weatherForecastProtocol':1,'wallpaperMediaProtocol':1}))
        proof=json.loads(self.proof.read_bytes());proof['files'][str(package)]=sha(package.read_bytes());self.proof.write_bytes(encode(proof))
        self.receiver();self.media();before=self.manifest.read_bytes()
        siblings={p:p.read_bytes() for p in (self.root/'theme-receiver-permissions.json',self.root/'wallpaper-media-permissions.json',self.snapshot,*self.paths.values())}
        self.weather()
        raw=(ROOT/'root-edition/runtime/cli.py').read_text();tree=ast.parse(raw)
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='execute')
        events=[]
        def suspend(*args):events.append('suspend');return 'restored'
        def access(**kw):
            self.assertEqual(events,['suspend'])
            self.assertEqual(kw,{'lock_product':False,'enable':False,'feature':'weather'})
            return self.weather(False)
        gate=types.SimpleNamespace(execute=lambda *args:suspend())
        ns={'d':types.SimpleNamespace(STATE=self.root,EXPECTED_UID=os.getuid()),'os':os,'gate_backend':lambda:gate,'firmware_access':access}
        exec(ast.get_source_segment(raw,node),ns)
        self.assertEqual(ns['execute']('suspend-update','a'*32),'restored')
        self.assertEqual(self.manifest.read_bytes(),before)
        self.assertFalse((self.root/'permissions/weather.api.json').exists())
        self.assertFalse((self.root/'weather-permissions.json').exists())
        for path,value in siblings.items():self.assertEqual(path.read_bytes(),value)
        # An older runtime knows these exact sibling receipts; its normal call remains valid.
        self.receiver();self.media()
        self.weather();events.clear()
        api=self.root/'permissions/weather.api.json';api.write_bytes(b'foreign drift')
        with self.assertRaises(ValueError):ns['execute']('suspend-update','b'*32)
        self.assertTrue((self.root/'weather-permissions.json').exists())
        self.assertEqual(api.read_bytes(),b'foreign drift')


    def test_media_attachment_requires_protected_worker_capability_and_preserves_legacy_contract(self):
        before=self.manifest.read_bytes()
        with self.assertRaises(ValueError):self.media()
        self.assertEqual(self.manifest.read_bytes(),before)
        self.protect_media_worker();self.receiver();receiver=(self.root/'theme-receiver-permissions.json').read_bytes()
        unchanged={p:p.read_bytes() for p in (self.snapshot,self.proof,*self.paths.values())}
        self.media();self.grant();self.receiver();self.media()
        api=self.root/'permissions/wallpaper-media.api.json'
        self.assertEqual(json.loads(api.read_bytes()),{GROUP:[SERVICE+'/'+name for name in ('wallpaperCacheStart','wallpaperCacheWrite','wallpaperCacheCommit','wallpaperCacheKeepAlive','wallpaperCacheStop')]})
        self.assertEqual((self.root/'theme-receiver-permissions.json').read_bytes(),receiver)
        for p,raw in unchanged.items():self.assertEqual(p.read_bytes(),raw)
        self.media(False);self.receiver(False);self.grant(False)
        self.assertEqual(json.loads(self.manifest.read_bytes()),self.normal)

    def test_media_capability_cannot_be_inferred_from_unprotected_package_or_release(self):
        self.protect_media_worker()
        proof=json.loads(self.proof.read_bytes());proof['files'].pop(str(self.root/'service/package.json'));self.proof.write_bytes(encode(proof))
        (self.root/'release.json').write_bytes(encode({'capabilities':['theme-receiver-v1','wallpaper-media-v1']}))
        before=self.manifest.read_bytes()
        with self.assertRaises(ValueError):self.media()
        self.assertEqual(self.manifest.read_bytes(),before)

    def test_receiver_upgrade_preserves_legacy_contract_and_independent_firmware_choice(self):
        before={p:p.read_bytes() for p in [self.snapshot,self.proof,*self.paths.values()]}
        self.grant();self.grant(False)
        old_receipt=self.receipt.read_bytes()
        self.receiver();receiver=self.root/'permissions/theme-receiver.api.json'
        self.assertEqual(json.loads(receiver.read_bytes()),{GROUP:[SERVICE+'/'+m for m in ('themeReceiverStart','themeReceiverStatus','themeReceiverRead','themeReceiverStop')]})
        self.assertEqual(json.loads(self.manifest.read_bytes())['apiPermissionFiles'],[str(self.paths['api']),str(receiver)])
        self.assertEqual(self.receipt.read_bytes(),old_receipt)
        self.grant();self.assertEqual(json.loads(self.manifest.read_bytes())['apiPermissionFiles'],[str(self.paths['api']),str(self.api),str(receiver)])
        self.grant(False);self.assertIn(str(receiver),json.loads(self.manifest.read_bytes())['apiPermissionFiles'])
        self.receiver(False);self.assertEqual(json.loads(self.manifest.read_bytes()),self.normal)
        self.assertFalse(receiver.exists())
        for path,raw in before.items():self.assertEqual(path.read_bytes(),raw)

    def test_legacy_receiver_repair_does_not_infer_media_support_from_new_release(self):
        # A new package on disk does not replace the protected old worker or its snapshot.
        release=self.root/'release.json'
        release.write_bytes(encode({'capabilities':['theme-receiver-v1','wallpaper-media-v1']}));release.chmod(0o600)
        before={path:path.read_bytes() for path in [self.snapshot,self.proof,*self.paths.values()]}
        self.receiver()
        receiver=self.root/'permissions/theme-receiver.api.json'
        self.assertEqual(json.loads(receiver.read_bytes()),{GROUP:[SERVICE+'/'+name for name in ('themeReceiverStart','themeReceiverStatus','themeReceiverRead','themeReceiverStop')]})
        for path,raw in before.items():self.assertEqual(path.read_bytes(),raw)

    def test_receiver_and_firmware_reconcile_after_package_replacement(self):
        self.grant();old_receipt=json.loads(self.receipt.read_bytes());self.receiver()
        normal=dict(self.normal,version='0.6.0')
        self.manifest.write_bytes(encode(normal));(self.apps/'applications'/APP/'appinfo.json').write_bytes(encode({'id':APP,'version':'0.6.0'}))
        self.grant();self.receiver();self.grant();self.receiver()
        self.assertEqual(json.loads(self.manifest.read_bytes())['apiPermissionFiles'],[str(self.paths['api']),str(self.api),str(self.root/'permissions/theme-receiver.api.json')])
        self.assertEqual(json.loads(self.receipt.read_bytes())['api_sha256'],old_receipt['api_sha256'])
        self.receiver(False);self.grant(False);self.assertEqual(json.loads(self.manifest.read_bytes()),normal)

    def test_receiver_uses_protected_manifest_without_trusting_sdk_identity(self):
        info=self.apps/'applications'/APP/'appinfo.json';info.parent.chmod(0o777);info.write_bytes(b'not identity authority')
        self.receiver()
        self.assertEqual(info.read_bytes(),b'not identity authority');self.assertEqual(info.parent.stat().st_mode&0o777,0o777)
        with self.assertRaises(ValueError):self.grant()
        raw=self.manifest.read_bytes();self.manifest.chmod(0o666)
        with self.assertRaises(ValueError):self.receiver()
        self.assertEqual(self.manifest.read_bytes(),raw)

    def test_receiver_registration_rejects_drift_before_other_permission_writes(self):
        self.grant();self.receiver()
        receiver=self.root/'permissions/theme-receiver.api.json';receiver.write_bytes(b'foreign')
        before={p:p.read_bytes() for p in (self.manifest,self.receipt,receiver)}
        for action in (self.receiver,self.grant):
            with self.assertRaises(ValueError):action()
        for path,raw in before.items():self.assertEqual(path.read_bytes(),raw)

    def test_legacy_runtime_accepts_firmware_receipt_after_receiver_downgrade(self):
        fixture=ROOT/'tests/cytv/fixtures/firmware-access-7fb6986f.py'
        self.assertEqual(sha(fixture.read_bytes()),'3298256c4d4f2598f18474aa08d70376d0a84fcba441a3608051674753ba7eec')
        source=fixture.read_text();tree=ast.parse(source);node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='firmware_access')
        ns={};exec(ast.get_source_segment(source,node),ns)
        # Receiver-first must not taint the historical firmware receipt.
        self.receiver();self.grant()
        self.manifest.write_bytes(encode(self.normal))  # Actual IPK replacement regenerates the SDK manifest.
        result=ns['firmware_access'](self.root,self.bus,self.apps,self.install,refresh=lambda:None,uid=os.getuid())
        self.assertTrue(result['permissions_installed'])
        self.assertNotIn(str(self.root/'permissions/theme-receiver.api.json'),json.loads(self.manifest.read_bytes())['apiPermissionFiles'])
        ns['firmware_access'](self.root,self.bus,self.apps,self.install,enable=False,refresh=lambda:None,uid=os.getuid())
        self.assertEqual(json.loads(self.manifest.read_bytes()),self.normal)

    def test_receiver_each_interrupted_write_resumes(self):
        replace=os.replace
        for cut in range(1,5):
            with self.subTest(cut=cut):
                counter=0
                def crash(src,dst):
                    nonlocal counter
                    replace(src,dst);counter+=1
                    if counter==cut:raise OSError('power loss')
                with patch('os.replace',side_effect=crash),self.assertRaises(OSError):self.receiver()
                self.receiver();self.grant();self.receiver(False);self.grant(False)
                self.assertEqual(json.loads(self.manifest.read_bytes()),self.normal)

    def test_executable_program_requires_verified_bundle(self):
        (self.bundle/'runtime/cli.py').write_bytes(b'poisoned')
        with self.assertRaises(ValueError):firmware_access.program(self.bundle)
