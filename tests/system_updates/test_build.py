import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

from cytv import package
ROOT = Path(__file__).resolve().parents[2]

def load(name):
    spec=importlib.util.spec_from_file_location('system_'+name, ROOT/'system-updater'/ (name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def fixture(root):
    for name, app, version in [('launcher','com.gathin.tvhome','1.3.8'),('helper','com.local.nativehome','0.6.18'),('updater','com.cleanyourtv.updater','0.1.6')]:
        files={'usr/palm/applications/'+app+'/appinfo.json':json.dumps({'id':app,'version':version,**({'systemUpdateProtocol':1} if name=='launcher' else {})}).encode()}
        (root/(name+'.ipk')).write_bytes(package.ipk(app,version,files))

class BuildTests(unittest.TestCase):
    def test_registration_refresh_restarts_launcher_without_enabling_home(self):
        setup=load('setup')
        for edition,app in [('root','com.cleanyourtv.root.preview'),('no-root','com.gathin.tvhome')]:
            calls=[]
            def rpc(uri,payload):
                calls.append((uri,payload));return {'returnValue':True}
            setup.restart_registered_launcher(edition,rpc)
            self.assertEqual(calls,[('luna://com.webos.applicationManager/closeByAppId',{'id':app}),
                                    ('luna://com.webos.applicationManager/launch',{'id':app})])

    def test_registration_refresh_continues_after_previous_close_and_failed_launch(self):
        setup=load('setup');calls=[];attempt=[0]
        def rpc(uri,payload):
            calls.append(uri)
            if uri.endswith('/closeByAppId'):
                if attempt[0]:
                    error=RuntimeError('Bus operation rejected');error.stopped_launcher=payload['id'];raise error
                return {'returnValue':True}
            attempt[0]+=1
            return {'returnValue':attempt[0]>1}
        with self.assertRaisesRegex(ValueError,'launch'):setup.restart_registered_launcher('root',rpc)
        setup.restart_registered_launcher('root',rpc)
        self.assertEqual(len(calls),4)

    def test_only_exact_owned_close_reply_identifies_stopped_launcher(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('qa_luna',ROOT/'root-edition/updater/luna.py')
        luna=importlib.util.module_from_spec(spec);spec.loader.exec_module(luna)
        uri='luna://com.webos.applicationManager/closeByAppId'
        for app in ('com.cleanyourtv.root.preview','com.gathin.tvhome'):
            reply=dict(returnValue=False,errorCode=40,errorText=app+' is not running')
            error=luna.context(RuntimeError(),uri,'negative-reply',reply)
            self.assertEqual(getattr(error,'stopped_launcher',None),app)
            for changed in (dict(reply,errorCode=-1),dict(reply,errorText=app+' denied'),dict(reply,errorCode=True)):
                self.assertIsNone(getattr(luna.context(RuntimeError(),uri,'negative-reply',changed),'stopped_launcher',None))
            self.assertIsNone(getattr(luna.context(RuntimeError(),uri.replace('/closeByAppId','/launch'),'negative-reply',reply),'stopped_launcher',None))

    def test_registration_refresh_refusal_does_not_launch_or_report_success(self):
        setup=load('setup');calls=[]
        def rpc(uri,payload):
            calls.append(uri);return {'returnValue':False}
        with self.assertRaisesRegex(ValueError,'closeByAppId'):
            setup.restart_registered_launcher('root',rpc)
        self.assertEqual(len(calls),1)
        with self.assertRaises(ValueError):setup.restart_registered_launcher('unknown',rpc)
        self.assertEqual(len(calls),1)

    def test_baseline_keeps_exact_personalized_packages_and_readback(self):
        build=load('build');setup=load('setup')
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp).resolve();fixture(path)
            out=path/'baseline';build.prepare_baseline(path,'no-root',out,release='v1.0.3')
            manifest=setup.verify_baseline(out)
            self.assertEqual([c['name'] for c in manifest['components']],['home','helper','updater'])
            for component in manifest['components']:
                self.assertTrue(component['local'])
                raw=(out/'cache'/component['sha256']).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(),component['sha256'])
                self.assertEqual(raw,(path/({'home':'launcher'}.get(component['name'],component['name'])+'.ipk')).read_bytes())
            next((out/'cache').iterdir()).write_bytes(b'bad')
            with self.assertRaisesRegex(ValueError,'hash'):setup.verify_baseline(out)

    def test_bundle_is_reproducible_independent_and_complete(self):
        build=load('build');setup=load('setup')
        with tempfile.TemporaryDirectory() as tmp:
            a=Path(tmp).resolve()/'a';b=Path(tmp).resolve()/'b';build.build(a);build.build(b)
            self.assertEqual({p.relative_to(a).as_posix():p.read_bytes() for p in a.rglob('*') if p.is_file()}, {p.relative_to(b).as_posix():p.read_bytes() for p in b.rglob('*') if p.is_file()})
            manifest=setup.verify_bundle(a)
            self.assertEqual(manifest['health_lock_wait_seconds'],10)
            self.assertIn('system_updater/support/store.py',manifest['files'])
            self.assertIn('observed_install.py',manifest['files'])
            self.assertIn('installation.py',manifest['files'])
            import subprocess,sys
            result=subprocess.run([sys.executable,'-I','-B','-c',
                'import sys;sys.path.insert(0,sys.argv[1]);import installation,package_data,startup_guard;'
                'assert installation.Store.__module__ == "system_updater.support.store"',str(a)],
                cwd=Path(tmp),capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('python_binding.py',manifest['files'])
            self.assertIn('python_boot.js',manifest['files'])
            inventory=json.loads((a/'infrastructure-paths.json').read_text())
            self.assertIn('support/python_binding.py',inventory)
            self.assertIn('support/python_boot.js',inventory)
            files=package.data_files((a/'system-updater.ipk').read_bytes())
            service='usr/palm/services/com.cleanyourtv.system.updater.service/'
            self.assertEqual(json.loads(files[service+'services.json'])['id'],'com.cleanyourtv.system.updater.service')
            self.assertEqual(build.VERSION,'1.2.8')
            self.assertEqual(json.loads(files[service+'package.json'])['version'],build.VERSION)
            self.assertEqual(json.loads(files['usr/palm/applications/com.cleanyourtv.system.updater/appinfo.json'])['version'],build.VERSION)
            policy_version=subprocess.check_output(['node','-p','require(process.argv[1]).supervisorVersion',str(ROOT/'system-updater/policy.js')],text=True).strip()
            self.assertEqual(policy_version,build.VERSION)
            self.assertNotIn(service+'system_updater/core.py',files)
            permissions=setup.permission_plan()
            self.assertNotIn('*',permissions['client.json'])
            self.assertIn('com.gathin.tvhome-*',permissions['client.json'])

    def test_setup_refuses_existing_state_before_any_effect(self):
        setup=load('setup')
        with tempfile.TemporaryDirectory() as tmp:
            state=Path(tmp)/'state';state.mkdir()
            with self.assertRaisesRegex(FileExistsError,'exists'):
                setup.provision(Path(tmp)/'bundle',Path(tmp)/'baseline',state=state)

    def test_setup_installs_owned_permissions_and_reads_captured_baseline(self):
        build=load('build');setup=load('setup')
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp).resolve();payload=path/'payload';payload.mkdir();fixture(payload)
            installed=path/'apps';installed.mkdir();base=path/'ls2';base.mkdir();hooks=path/'hooks';hooks.mkdir()
            for kind in ('services.d','roles.d','client-permissions.d','api-permissions.d'):(base/kind).mkdir()
            for name,app,service in [('launcher','com.gathin.tvhome','com.gathin.tvhome.renewal'),('helper','com.local.nativehome','com.local.nativehome.service'),('updater','com.cleanyourtv.updater','com.cleanyourtv.updater.service')]:
                raw=(payload/(name+'.ipk')).read_bytes();files=package.data_files(raw)
                info=json.loads(next(iter(files.values())))
                files['usr/palm/packages/'+app+'/packageinfo.json']=json.dumps({'id':app,'version':info['version'],'app':app,'services':[service]}).encode()
                files['usr/palm/services/'+service+'/service.js']=b'original bytes'
                for filename,data in files.items():
                    target=installed/filename;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
            mutable=installed/'usr/palm/services/com.local.nativehome.service/state/preferences.json';mutable.parent.mkdir();mutable.write_text('private preferences')
            channel=installed/'usr/palm/services/com.gathin.tvhome.renewal/state/home-control'
            channel.mkdir(parents=True);(channel/'.keep').write_bytes(b'')
            (channel/'home-request.json').write_text('private transient request')
            bundle=path/'bundle';build.build(bundle)
            baseline=setup.snapshot(bundle,'no-root',path/'baseline',installed=installed)
            manifest=setup.verify_baseline(baseline)
            self.assertEqual([c['version'] for c in manifest['components']],['1.3.8','0.6.18','0.1.6'])
            for item in manifest['components']:
                raw=(baseline/'cache'/item['sha256']).read_bytes()
                files=package.data_files(raw)
                public_channel='usr/palm/services/com.gathin.tvhome.renewal/state/home-control/.keep'
                self.assertFalse(any('/state/' in n and n!=public_channel for n in files))
                if item['name']=='home':
                    self.assertEqual(files[public_channel],b'')
                    with tarfile.open(fileobj=io.BytesIO(package.read_ar(raw)['data.tar.gz']), mode='r:gz') as archive:
                        for name in ('state','state/home-control'):
                            entry=archive.getmember('usr/palm/services/com.gathin.tvhome.renewal/'+name)
                            self.assertEqual((entry.uid,entry.gid,entry.mode),(5999,5000,0o2770))
            sentinel=channel/'.keep'
            for invalid in ('nonempty','symlink'):
                with self.subTest(channel_sentinel=invalid):
                    sentinel.unlink()
                    if invalid=='nonempty':sentinel.write_text('private data')
                    else:sentinel.symlink_to(channel/'home-request.json')
                    with self.assertRaises(ValueError):
                        setup.snapshot(bundle,'no-root',path/('rejected-'+invalid),installed=installed)
            sentinel.unlink();sentinel.write_bytes(b'')
            def install(app,filename,timeout,on_ready,on_accepted):
                original=Path(filename).read_bytes()
                self.assertEqual((state/'cache'/(hashlib.sha256(original).hexdigest()+'.ipk')).read_bytes(),original)
                self.assertFalse((state/'installed-package.json').exists())
                on_ready();on_accepted({'confirmed':True})
                for name,data in package.data_files(Path(filename).read_bytes()).items():
                    target=installed/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
                    if name.endswith('/startup.sh'):target.chmod(0o755)
                service=setup.SERVICE
                (base/'services.d'/(service+'.service')).write_text('[Luna Service]\nName='+service+'\nExec=/usr/bin/run-js-service -n '+str(installed/'usr/palm/services'/service)+'\n')
                (base/'roles.d'/(service+'.service.json')).write_text(json.dumps({'appId':service,'type':'regular'}))
                (base/'client-permissions.d'/(service+'.service.json')).write_text('{}')
                (base/'api-permissions.d'/(service+'.api.json')).write_text('{}')
                return {'completed':True,'event':{'id':app,'statusValue':30,'returnValue':True,'details':{'packageId':app,'client':'com.webos.lunasend-99','ipkFile':'/var/lib/clean-your-tv-installer/cytv-root-install-fixture/package.ipk'}}}
            state=path/'state';hook=hooks/'52-system'
            import startup_hook,os
            from unittest.mock import patch
            def trusted(path):
                for parent in (path,*path.parents):
                    if parent==path_root.parent:break
                    info=parent.lstat()
                    if not __import__('stat').S_ISDIR(info.st_mode) or info.st_mode&0o022:raise ValueError('Unsafe fixture path')
            path_root=path
            with patch.object(startup_hook,'EXPECTED_UID',os.getuid()),patch.object(startup_hook,'INSTALLED',installed),patch.object(startup_hook,'trusted_directory',side_effect=trusted):
                from installation import Ownership,device_operation,Busy
                from updater.store import Store
                owner=Ownership(Store(path/'global',uid=os.getuid()))
                read=lambda p: json.loads((state/'bootstrap.json').read_text()) if p.name=='bootstrap.json' and 'system-updater' in str(p) and (state/'bootstrap.json').exists() else None
                def eligible():setup.preflight(bundle,baseline,state,installed,base,hook)
                def interrupted():raise RuntimeError('scanner interrupted after terminal')
                with self.assertRaisesRegex(RuntimeError,'scanner interrupted'):
                    with device_operation('system-bootstrap',ownership=owner,read=read,check=eligible):
                        setup.provision(bundle,baseline,state=state,installed=installed,base=base,hook=hook,install=install,refresh=interrupted)
                pending=owner.status()['id']
                self.assertFalse(owner.status()['terminal'])
                with self.assertRaises(Busy):
                    with owner.operation('deploy','deploy.json'):pass
                with patch('observed_install.install',side_effect=AssertionError('known terminal resubmitted')):
                    with device_operation('system-bootstrap',recovery=True,ownership=owner,read=read) as lease:
                        self.assertEqual(lease['id'],pending)
                        with patch.object(setup.Path,'is_file',return_value=True),patch.object(setup.subprocess,'run') as scan,patch.object(setup,'restart_registered_launcher') as restart:
                            result=setup.resume(bundle,state,installed,base,hook)
                        self.assertEqual(scan.call_args.args[0][-1],'scan-services')
                        restart.assert_called_once_with('no-root')
                self.assertTrue(owner.status()['terminal'])
                own=json.loads((state/'installed-package.json').read_text())
                self.assertEqual((state/'cache'/(own['package']['sha256']+'.ipk')).read_bytes(),(bundle/'system-updater.ipk').read_bytes())
                self.assertEqual(own['files'],{n:hashlib.sha256(b).hexdigest() for n,b in package.data_files((bundle/'system-updater.ipk').read_bytes()).items()})
                completed=owner.status()
                with self.assertRaises(FileExistsError):
                    with device_operation('system-bootstrap',ownership=owner,read=read,check=eligible):pass
                self.assertEqual(owner.status(),completed)
                # An accepted package without its exact terminal remains blocked.
                (state/'installed-terminal.json').unlink()
                (state/'bootstrap.json').write_text('{"phase":"accepted-supervisor"}')
                with patch('observed_install.install',side_effect=AssertionError('unknown submission replayed')):
                    with self.assertRaisesRegex(ValueError,'outcome unknown'):
                        with device_operation('system-bootstrap',recovery=True,ownership=owner,read=read):
                            setup.resume(bundle,state,installed,base,hook,refresh=lambda:None)
                self.assertFalse(owner.status()['terminal'])
                (state/'bootstrap.json').write_text('{"phase":"complete"}')
            self.assertFalse(hook.is_symlink())
            self.assertTrue(result['installed'])
            self.assertEqual(json.loads((state/'bootstrap.json').read_text())['phase'],'complete')
            self.assertEqual(json.loads((state/'current-no-root.json').read_text()),manifest)
            self.assertEqual((state/'code/system_updater/core.py').stat().st_mode&0o777,0o600)
            self.assertFalse(hook.is_symlink())
            self.assertIn(str(state/'run-service'),(base/'services.d'/(setup.SERVICE+'.service')).read_text())
            self.assertEqual(hook.read_text(),startup_hook.private_content(setup.APP).decode())
            self.assertEqual(mutable.read_text(),'private preferences')
            with self.assertRaises(FileExistsError):setup.provision(bundle,baseline,state=state)

    def test_bootstrap_rejects_ambiguous_legacy_installer_state(self):
        setup=load('setup')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();journal=root/'transaction.json'
            journal.write_text('{"phase":"installing"}')
            with self.assertRaisesRegex(ValueError,'legacy'):setup.require_legacy_idle([journal])
            journal.write_text('{"phase":"complete"}')
            setup.require_legacy_idle([journal])
            journal.write_text('{"status":"recovery-required"}')
            with self.assertRaisesRegex(ValueError,'legacy'):setup.require_legacy_idle([journal])

    def test_host_transfer_contains_only_verified_bundle_inventory(self):
        build=load('build');setup=load('setup')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();bundle=root/'bundle';build.build(bundle)
            (bundle/'private-extra.txt').write_text('local private data')
            transfers=[]
            def run(argv,**kwargs):
                if argv[0]=='scp':
                    paths=[Path(p) for p in argv if Path(p).is_dir()]
                    self.assertEqual(len(paths),1)
                    transfers.extend(p.relative_to(paths[0]).as_posix() for p in paths[0].rglob('*') if p.is_file())
            setup.execute(bundle,None,'test-tv',run=run,edition='root')
            self.assertNotIn('private-extra.txt',transfers)
            self.assertIn('bundle.json',transfers)
            self.assertIn('setup-system-updater.py',transfers)

    def test_old_home_is_rejected_before_baseline_or_state_is_written(self):
        build=load('build');setup=load('setup')
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp).resolve();bundle=path/'bundle';build.build(bundle)
            installed=path/'installed';home=installed/'usr/palm/applications/com.gathin.tvhome';home.mkdir(parents=True)
            (home/'appinfo.json').write_text('{"id":"com.gathin.tvhome","version":"1.0.0"}')
            with self.assertRaisesRegex(ValueError,'transition Home'):
                setup.snapshot(bundle,'no-root',path/'baseline',installed=installed)
            self.assertFalse((path/'baseline').exists())

    def test_lockdown_disables_only_legacy_mutation_and_updates_owned_receipts(self):
        setup=load('setup')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();base=root/'ls2';(base/'api-permissions.d').mkdir(parents=True)
            state=root/'state';state.mkdir();updater=root/'root-updater';updater.mkdir()
            api=base/'api-permissions.d/com.cleanyourtv.updater.permissions.json'
            methods=['com.cleanyourtv.updater.service/'+m for m in ('check','install','rollback','reconcile','healthy')]+['org.webosbrew.hbchannel.service/install']
            original=json.dumps({'legacy':methods})+'\n';api.write_text(original)
            entries=[]
            for folder in ('api-permissions.d','client-permissions.d','manifests.d'):
                path=base/folder/'com.cleanyourtv.updater.permissions.json';path.parent.mkdir(exist_ok=True)
                if path!=api:path.write_text('{}')
                raw=path.read_text();entries.append({'path':str(path),'content':raw,'sha256':hashlib.sha256(raw.encode()).hexdigest()})
            ownership=base/'com.cleanyourtv.updater.permissions.receipt.json';ownership.write_text(json.dumps({'schema':1,'files':entries}))
            root_api=base/'api-permissions.d/com.cleanyourtv.root.updater.service.api.json'
            root_api.write_text(json.dumps({'root':['com.cleanyourtv.root.updater.service/'+m for m in ('check','status','install','rollback','reconcile','restoreProfile','ready','confirm')]}))
            registration=updater/'registration.json';registration.write_text(json.dumps({'files':{str(root_api):{'original':'{}','installed':root_api.read_text()}}}))
            setup.apply_legacy_lockdown(state,bases=[base],root_updater=updater)
            remaining=json.loads(api.read_text())['legacy'];self.assertEqual(remaining,['com.cleanyourtv.updater.service/check','com.cleanyourtv.updater.service/healthy'])
            self.assertEqual(json.loads(root_api.read_text())['root'],['com.cleanyourtv.root.updater.service/check','com.cleanyourtv.root.updater.service/status','com.cleanyourtv.root.updater.service/restoreProfile'])
            self.assertEqual(json.loads(registration.read_text())['files'][str(root_api)]['installed'],root_api.read_text())
            self.assertEqual(next(e for e in json.loads(ownership.read_text())['files'] if e['path']==str(api))['content'],api.read_text())
            receipt=json.loads((state/'legacy-lockdown.json').read_text());self.assertEqual(receipt['files'][str(api)]['original'],original)
            api.write_text('conflict')
            with self.assertRaisesRegex(ValueError,'changed'):setup.apply_legacy_lockdown(state,bases=[base],root_updater=updater)

    def test_bootstrap_requires_legacy_root_home_resume_receipt(self):
        from unittest.mock import patch
        setup=load('setup')
        with tempfile.TemporaryDirectory() as tmp:
            journal=Path(tmp).resolve()/'transaction.json';journal.write_text('{"schema":1,"phase":"complete"}')
            with patch.object(setup,'ROOT_UPDATER_TRANSACTION',journal,create=True):
                with self.assertRaisesRegex(ValueError,'legacy Root Home'):setup.require_legacy_idle([journal])
                journal.write_text('{"schema":1,"phase":"complete","homeResumePhase":"complete"}')
                setup.require_legacy_idle([journal])

    def test_missing_pinned_infrastructure_is_explicit_and_cannot_expand_destinations(self):
        from unittest.mock import patch
        build=load('build');setup=load('setup')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();bundle=root/'bundle';build.build(bundle)
            names=json.loads((bundle/'infrastructure-paths.json').read_text())
            roots={'runtime':root/'lib/clean-your-tv-root/runtime','service':root/'lib/clean-your-tv-root/service','updater':root/'lib/clean-your-tv-root-updater/code'}
            missing={'updater/updater/ca-bundle.crt','updater/updater/ca-LICENSE.txt'}
            self.assertTrue(missing<=set(names))
            for name in names:
                if name in missing:continue
                kind,relative=name.split('/',1);path=(roots['runtime'].parent if kind=='support' else roots[kind])/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(name.encode())
            files,absent=setup.capture_infrastructure(names,**roots)
            self.assertEqual(set(absent),missing);self.assertEqual(set(files)|set(absent),set(names))
            installed=root/'installed'
            originals={}
            for kind,app in (('root','com.cleanyourtv.root.preview'),('root-updater','com.cleanyourtv.root.updater')):
                appdir=installed/'usr/palm/applications'/app;appdir.mkdir(parents=True)
                (appdir/'appinfo.json').write_text(json.dumps({'id':app,'version':'1.0.0','systemUpdateProtocol':1,'main':'index.html','type':'web'}));(appdir/'index.html').write_text('Home')
                (appdir/'startup.sh').write_text('#!/bin/sh\nexit 0\n');(appdir/'startup.sh').chmod(0o755)
                package_dir=installed/'usr/palm/packages'/app;package_dir.mkdir(parents=True);(package_dir/'packageinfo.json').write_text(json.dumps({'id':app,'app':app,'version':'1.0.0','services':[app+'.service']}))
                service_dir=installed/'usr/palm/services'/(app+'.service');service_dir.mkdir(parents=True);(service_dir/'service.js').write_text('service')
                # Independently constructed original IPKs/receipts precede the
                # writable SDK fixture; capture cannot invent authority from it.
                prefix='usr/palm/applications/'+app+'/'
                original={prefix+'appinfo.json':json.dumps({'id':app,'version':'1.0.0','systemUpdateProtocol':1,'main':'index.html','type':'web'}).encode(),prefix+'index.html':b'Home',prefix+'startup.sh':b'#!/bin/sh\nexit 0\n','usr/palm/packages/'+app+'/packageinfo.json':json.dumps({'id':app,'app':app,'version':'1.0.0','services':[app+'.service']}).encode(),'usr/palm/services/'+app+'.service/service.js':b'service'}
                originals[kind]=(package.ipk(app,'1.0.0',original,executable={prefix+'startup.sh'}),original)
            from updater.store import Store
            import os
            store=Store(roots['updater'].parent,uid=os.getuid());(roots['updater'].parent/'cache').mkdir()
            raw=originals['root'][0];pin=hashlib.sha256(raw).hexdigest();(roots['updater'].parent/'cache'/(pin+'.ipk')).write_bytes(raw)
            store.write('current',{'version':'1.0.0','sha256':pin,'size':len(raw),'local':True})
            own=originals['root-updater'][1]
            store.write('installed-package',{'schema':1,'files':{n:hashlib.sha256(b).hexdigest() for n,b in own.items()},'executable':['usr/palm/applications/com.cleanyourtv.root.updater/startup.sh']})
            for target in installed.rglob('*'):target.chmod(0o777)
            baseline=setup.snapshot(bundle,'root',root/'baseline',installed=installed,**roots)
            manifest=setup.verify_baseline(baseline,bundle)
            import io,tarfile
            from cytv.package import read_ar
            for item in manifest['components']:
                if item['kind']!='ipk':continue
                raw=(baseline/'cache'/item['sha256']).read_bytes()
                with tarfile.open(fileobj=io.BytesIO(read_ar(raw)['data.tar.gz']),mode='r:gz') as archive:
                    self.assertEqual(archive.getmember('usr/palm/applications/'+item['application']+'/startup.sh').mode,0o755)
            captured=next(c for c in manifest['components'] if c['name']=='root-infrastructure')
            self.assertEqual(set(captured['absent']),missing)
            self.assertEqual(set(captured['files']),set(names)-missing)
            captured['absent'].append('runtime/arbitrary.py');(baseline/'baseline.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'pinned bootstrap inventory'):setup.verify_baseline(baseline,bundle)
            descriptor={'kind':'infrastructure','files':{n:hashlib.sha256(b).hexdigest() for n,b in files.items()},'absent':absent}
            setup.verify_infrastructure_inventory(descriptor,files,names)
            with self.assertRaisesRegex(ValueError,'inventory'):
                setup.verify_infrastructure_inventory({**descriptor,'absent':absent+['runtime/arbitrary.py']},files,names)
            with self.assertRaisesRegex(ValueError,'inventory'):
                setup.verify_infrastructure_inventory({**descriptor,'absent':absent+absent},files,names)
            target=roots['updater']/'updater/ca-bundle.crt';target.symlink_to(root/'nonexistent')
            with self.assertRaisesRegex(ValueError,'Indirect'):setup.capture_infrastructure(names,**roots)

    def test_root_supervisor_resume_uses_exact_terminal_and_owned_registration_after_scanner_loss(self):
        import sys,shutil,functools
        from unittest.mock import patch
        sys.path.insert(0,str(ROOT/'root-edition/tests'));sys.path.insert(0,str(ROOT/'root-edition'))
        from install_fixture import CurrentInstallation,altered_bootstrap_bundle
        from installation import terminal_install
        build=load('build');setup=load('setup')
        with CurrentInstallation() as fixture:
            bundle=fixture.base/'supervisor-bundle';build.build(bundle)
            roots={'runtime':fixture.root/'runtime','updater':fixture.updater/'code','service':fixture.root/'service'}
            baseline=setup.snapshot(bundle,'root',fixture.base/'super-baseline',installed=fixture.installed,**roots)
            state=fixture.base/'super-state';shutil.copytree(baseline,state);(state/'code').mkdir()
            manifest=setup.verify_bundle(bundle)
            for name in setup.CODE:
                target=state/'code'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((bundle/name).read_bytes())
            def record(name,value):(state/(name+'.json')).write_text(json.dumps(value))
            record('infrastructure',{'schema':1,'code':{name:manifest['files'][name] for name in sorted(setup.CODE)}})
            binding={'schema':1,'bundle':manifest,'package':{'sha256':manifest['files']['system-updater.ipk'],'size':(bundle/'system-updater.ipk').stat().st_size}}
            record('bootstrap-bundle',binding)
            record('bootstrap',{'phase':'accepted-supervisor','edition':'root'})
            base=fixture.base/'super-ls2';hook=fixture.base/'hooks/52';hook.parent.mkdir()
            with patch.object(setup,'ROOT_UPDATER_TRANSACTION',fixture.updater/'transaction.json'),patch.object(setup,'INSTALLED',fixture.installed),patch.object(setup,'finish_registration',wraps=setup.finish_registration) as finish:
                with self.assertRaisesRegex(ValueError,'outcome unknown'):setup.resume(bundle,state=state,installed=fixture.installed,base=base,hook=hook)
                finish.assert_not_called()
            record('bootstrap',{'phase':'installing-supervisor','edition':'root'})
            with patch('observed_install.install',return_value={'completed':True,'event':{'id':setup.APP,'statusValue':30,'details':{'packageId':setup.APP,'client':'com.webos.lunasend-99','ipkFile':'/var/lib/clean-your-tv-installer/cytv-root-install-fixture/package.ipk'}}}) as install,patch.object(setup,'finish_registration',return_value={'installed':True}) as finish:
                for code in (False,True):
                    alternate=altered_bootstrap_bundle(bundle,fixture.base/('alternate-super-'+str(code)),'system-updater.ipk',code=code)
                    setup.verify_bundle(alternate)
                    with self.assertRaisesRegex(ValueError,'original bootstrap bundle'):setup.resume(alternate,state,fixture.installed,base,hook)
                    install.assert_not_called();finish.assert_not_called()
                    self.assertEqual(json.loads((state/'bootstrap.json').read_text())['phase'],'installing-supervisor')
                (state/'bootstrap-bundle.json').unlink()
                with self.assertRaisesRegex(ValueError,'original bootstrap bundle'):setup.resume(bundle,state,fixture.installed,base,hook)
                install.assert_not_called();finish.assert_not_called()
                record('bootstrap-bundle',binding)
                self.assertTrue(setup.resume(bundle,state,fixture.installed,base,hook)['installed'])
                self.assertEqual(Path(install.call_args.args[1]).read_bytes(),(bundle/'system-updater.ipk').read_bytes())
                self.assertEqual(json.loads((state/'bootstrap-bundle.json').read_text()),binding)
            terminal={'completed':True,'event':{'id':setup.APP,'statusValue':30,'details':{'packageId':setup.APP,'client':'com.webos.lunasend-99','ipkFile':'/var/lib/clean-your-tv-installer/cytv-root-install-fixture/package.ipk'}}}
            self.assertTrue(terminal_install(terminal,setup.APP));record('installed-terminal',terminal);record('bootstrap',{'phase':'provisioning','edition':'root'})
            for name,raw in setup.package_files((bundle/'system-updater.ipk').read_bytes()).items():
                target=fixture.installed/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);target.chmod(0o755 if name.endswith('/startup.sh') else 0o644)
            original={'service':('[D-BUS Service]\nName='+setup.SERVICE+'\nExec=/usr/bin/run-js-service -n '+str(fixture.installed/'usr/palm/services'/setup.SERVICE)+'\n').encode(),'role':json.dumps({'appId':setup.SERVICE}).encode(),'client':b'{}','api':b'{}'}
            for key,folder,suffix in (('service','services.d','.service'),('role','roles.d','.service.json'),('client','client-permissions.d','.service.json'),('api','api-permissions.d','.api.json')):
                target=base/folder/(setup.SERVICE+suffix);target.parent.mkdir(parents=True);target.write_bytes(original[key])
            def atomic(path,raw,mode=0o600):
                if isinstance(raw,str):raw=raw.encode()
                path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw);path.chmod(mode)
            destination=functools.partial(setup.infrastructure_destination,**roots)
            lockdown=functools.partial(setup.apply_legacy_lockdown,bases=[base,fixture.base/'unused-ls2'],root_updater=fixture.updater)
            scans=[0]
            def refresh():
                scans[0]+=1
                if scans[0]==1:raise RuntimeError('scanner disconnected after terminal')
            with patch.object(setup,'ROOT_UPDATER_TRANSACTION',fixture.updater/'transaction.json'),patch.object(setup,'INSTALLED',fixture.installed),patch.object(setup,'BASE',base),patch.object(setup,'atomic',atomic),patch.object(setup,'infrastructure_destination',destination),patch.object(setup,'apply_legacy_lockdown',lockdown),patch('startup_hook.install_link'):
                from installation import device_operation
                read=lambda path: json.loads((state/'bootstrap.json').read_text()) if path.name=='bootstrap.json' and 'system-updater' in str(path) else None
                with self.assertRaisesRegex(RuntimeError,'scanner'):
                    with device_operation('system-bootstrap',ownership=fixture.owner,read=read):setup.resume(bundle,state=state,installed=fixture.installed,base=base,hook=hook,refresh=refresh)
                original=fixture.owner.status()['id']
                self.assertFalse(fixture.owner.status()['terminal'])
                saved=(state/'registration.json').read_bytes()
                with device_operation('system-bootstrap',recovery=True,ownership=fixture.owner,read=read) as lease:
                    self.assertEqual(lease['id'],original)
                    self.assertTrue(setup.resume(bundle,state=state,installed=fixture.installed,base=base,hook=hook,refresh=refresh)['installed'])
                self.assertTrue(fixture.owner.status()['terminal'])
                self.assertEqual((state/'registration.json').read_bytes(),saved)
                self.assertEqual(json.loads((state/'bootstrap.json').read_text())['phase'],'complete')
            fixture.assert_preserved(self)
