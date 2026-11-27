import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from cytv.system_updater_remove import SCRIPT, COMMAND

namespace={'__name__':'system_remove_test'}
exec(SCRIPT,namespace)
APP='com.cleanyourtv.system.updater';SERVICE=APP+'.service'

def digest(raw):return hashlib.sha256(raw).hexdigest()

class RemovalTests(unittest.TestCase):
    def fixture(self,root):
        state=root/'state';state.mkdir(mode=0o700);code=state/'code';code.mkdir();(state/'cache').mkdir()
        (code/'run-system-updater.py').write_bytes(b'fixed supervisor')
        (state/'bootstrap.json').write_text('{"phase":"complete","edition":"no-root"}')
        (state/'infrastructure.json').write_text(json.dumps({'schema':1,'code':{'run-system-updater.py':digest(b'fixed supervisor')}}))
        components=[]
        for name in ('home','helper','updater'):
            raw=name.encode();sha=digest(raw);(state/'cache'/sha).write_bytes(raw)
            components.append({'name':name,'size':len(raw),'sha256':sha,'local':True})
        (state/'legacy-lockdown.json').write_text('{"schema":1,"files":{}}')
        (state/'baseline.json').write_text(json.dumps({'schema':1,'edition':'no-root','supervisor':1,'components':components}))
        base=root/'bus';base.mkdir();installed=root/'apps';installed.mkdir();proc=root/'proc';proc.mkdir()
        registration={}
        for folder,suffix in (('services.d','.service'),('roles.d','.service.json'),('client-permissions.d','.service.json'),('api-permissions.d','.api.json')):
            (base/folder).mkdir();path=base/folder/(SERVICE+suffix)
            path.write_text(folder);registration[str(path)]={'installed':folder,'original':'original'}
        (state/'registration.json').write_text(json.dumps({'files':registration}))
        (base/'manifests.d').mkdir()
        manifest={'id':APP,'version':'1.0.0','serviceFiles':[str(base/'services.d'/(SERVICE+'.service'))], 'apiPermissionFiles':[str(base/'api-permissions.d'/(SERVICE+'.api.json'))], 'roleFiles':[str(base/'roles.d'/(SERVICE+'.service.json')),str(base/'roles.d'/(APP+'.app.json'))], 'clientPermissionFiles':[str(base/'client-permissions.d'/(SERVICE+'.service.json')),str(base/'client-permissions.d'/(APP+'.app.json'))]}
        (base/'manifests.d'/(APP+'.json')).write_text(json.dumps(manifest))
        role={'appId':APP,'type':'regular','allowedNames':[APP+'-*'],'trustLevel':'public','permissions':[{'service':APP+'-*','outbound':['*']}]}
        (base/'roles.d'/(APP+'.app.json')).write_text(json.dumps(role));(base/'client-permissions.d'/(APP+'.app.json')).write_text(json.dumps({APP+'-*':[]}))
        hook=root/'boot';hook.write_text('#!/bin/sh\n/usr/bin/python3 '+str(state/'code/run-system-updater.py')+' worker </dev/null >/dev/null 2>&1 &\n')
        return dict(state=state,base=base,hook=hook,installed=installed,proc=proc,refresh=lambda:None,stop_processes=lambda _:None)


    def link_fixture(self,root):
        import sys
        sys.path.insert(0,str(Path(__file__).parents[2]/'root-edition'))
        import startup_hook
        args=self.fixture(root);state=args['state'];hook=args['hook'];app=APP
        target=args['installed']/'applications'/app/'startup.sh';target.parent.mkdir(parents=True)
        target.write_bytes(startup_hook.packaged_content(app));(target.parent/'appinfo.json').write_text(json.dumps({'id':app}))
        hook.unlink();hook.symlink_to(target)
        (state/'startup-hook.json').write_text(json.dumps(dict(version=2,path=str(hook),target=str(target),owner_app=app,target_sha256=hashlib.sha256(target.read_bytes()).hexdigest())))
        return args,target

    def test_single_tile_status_authenticates_the_two_component_origin(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=self.fixture(Path(tmp).resolve());state=args['state']
            code=state/'code';marker='system_updater/product-generation.json'
            (code/'system_updater').mkdir()
            (code/marker).write_bytes(b'2\n');(code/'root-provision.py').write_bytes(b'provision')
            inventory={path.relative_to(code).as_posix():digest(path.read_bytes()) for path in code.rglob('*') if path.is_file()}
            (state/'infrastructure.json').write_text(json.dumps({'schema':1,'code':inventory}))
            bundle={'schema':1,'supervisor':1,'product_schema':2,'files':dict(inventory,**{'setup-system-updater.py':'c'*64,'system-updater.ipk':'d'*64})}
            (state/'bootstrap-bundle.json').write_text(json.dumps({'schema':1,'bundle':bundle}))
            baseline=json.loads((state/'baseline.json').read_text());baseline.update(schema=2,components=baseline['components'][:2])
            (state/'baseline.json').write_text(json.dumps(baseline))
            report=namespace['operate']('status',**args)
            self.assertTrue(report['ownership_verified']);self.assertEqual(report['product_schema'],2)
            self.assertEqual(report['bootstrap_digest'],digest(json.dumps(bundle,sort_keys=True,separators=(',',':')).encode()))
            bundle['files'][marker]='a'*64
            (state/'bootstrap-bundle.json').write_text(json.dumps({'schema':1,'bundle':bundle}))
            with self.assertRaisesRegex(ValueError,'origin'):namespace['operate']('status',**args)

    def test_owned_link_survives_interrupted_disable_and_missing_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            args,target=self.link_fixture(Path(tmp).resolve())
            self.assertTrue(namespace['operate']('status',**args)['ownership_verified'])
            def interrupt():raise OSError('scan interrupted')
            args['refresh']=interrupt
            with self.assertRaises(OSError):namespace['operate']('disable',**args)
            target.unlink();(target.parent/'appinfo.json').unlink();target.parent.rmdir()
            args['refresh']=lambda:None
            self.assertTrue(namespace['operate']('disable',**args)['disabled'])
            self.assertTrue((args['state']/'removed-registration/hook').is_symlink())
            self.assertTrue(namespace['operate']('archive',**args)['removed'])

    def test_repeat_disable_accepts_exact_receipted_root_archival_link(self):
        from unittest.mock import patch
        import startup_hook
        with tempfile.TemporaryDirectory() as tmp:
            args=self.fixture(Path(tmp).resolve());namespace['operate']('disable',**args)
            root,api,after=self.root_removal_fixture(args);hook=Path('/var/lib/webosbrew/init.d/51-clean-your-tv-root-updater')
            app='com.cleanyourtv.root.updater';target=Path('/media/developer/apps/usr/palm/applications')/app/'startup.sh'
            saved=root/'removed-registration/hook';saved.unlink();saved.symlink_to(target)
            (root/'startup-hook.json').write_text(json.dumps(dict(version=2,path=str(hook),target=str(target),owner_app=app,target_sha256=hashlib.sha256(startup_hook.packaged_content(app)).hexdigest())))
            with patch.dict(namespace,ROOT_UPDATER=root):namespace['operate']('disable',**args)
            self.assertEqual((root/'registration.json').read_text(),after)
            self.assertTrue(saved.is_symlink())

    def test_managed_hook_requires_literal_owned_binding(self):
        managed='/var/lib/clean-your-tv-python/4a71641c8d5536175e404a961624e8656eba30e97b5026f6bd7dc31e4bbeaaea/bin/python3.13'
        with tempfile.TemporaryDirectory() as tmp:
            args=self.fixture(Path(tmp).resolve())
            state=args['state'];hook=args['hook']
            launcher=state/'python-launcher'
            launcher.write_text('#!/bin/sh\nunset PYTHONHOME PYTHONPATH\nexport PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1\nexec '+managed+' "$@"\n');launcher.chmod(0o700)
            (state/'python-runtime.json').write_text(json.dumps({'schema':1,'executable':managed,'archive_sha256':managed.split('/')[-3],'inventory_sha256':'a'*64}))
            hook.write_text('#!/bin/sh\nunset NODE_OPTIONS NODE_PATH\n/usr/bin/node '+str(state/'code/python_boot.js')+' '+str(state)+' '+str(state/'code/run-system-updater.py')+' worker </dev/null >/dev/null 2>&1 &\n')
            self.assertTrue(namespace['operate']('status',**args))
            launcher.write_text('#!/bin/sh\nexec /tmp/evil "$@"\n')
            with self.assertRaises(ValueError):namespace['operate']('status',**args)

    def test_status_is_read_only_and_proves_bootstrap_code_and_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=self.fixture(Path(tmp).resolve());root=Path(tmp)
            before={str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()}
            value=namespace['operate']('status',**args)
            self.assertTrue(value['present']);self.assertTrue(value['bootstrap_complete'])
            self.assertEqual(before,{str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()})
            (args['state']/'code/run-system-updater.py').write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError,'integrity'):namespace['operate']('status',**args)

    def test_disable_retry_and_archive_retain_cache_and_owned_registrations(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=self.fixture(Path(tmp).resolve());state=args['state']
            archive=str(state)+'.archive-'+'a'*32
            first=namespace['operate']('disable',destination=archive,**args)
            self.assertTrue(first['disabled']);self.assertFalse(args['hook'].exists())
            self.assertTrue(namespace['operate']('disable',destination=archive,**args)['disabled'])
            package=args['installed']/'applications'/APP;package.mkdir(parents=True)
            with self.assertRaisesRegex(ValueError,'package'):namespace['operate']('archive',destination=archive,**args)
            package.rmdir();value=namespace['operate']('archive',destination=archive,**args)
            self.assertFalse(state.exists());self.assertTrue(value['removed'])
            self.assertTrue((Path(archive)/'cache').is_dir());self.assertTrue((Path(archive)/'removed-registration/hook').exists())
            self.assertFalse(namespace['operate']('status',**args)['present'])

    def test_conflicts_partial_setup_and_unknown_outcome_never_change_files(self):
        for case in ('hook','receipt','transaction','cache','bootstrap','symlink'):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as tmp:
                args=self.fixture(Path(tmp).resolve());state=args['state']
                if case=='hook':args['hook'].write_text('someone else')
                if case=='receipt':(state/'registration.json').write_text('{"files":{"/foreign":{"installed":"x"}}}')
                if case=='transaction':(state/'transaction.json').write_text('{"schema":1,"phase":"installing"}')
                if case=='cache':next((state/'cache').iterdir()).write_bytes(b'bad')
                if case=='bootstrap':(state/'bootstrap.json').write_text('{"phase":"submitting-supervisor"}')
                if case=='symlink':args['hook'].unlink();args['hook'].symlink_to(state/'bootstrap.json')
                before={str(p):p.read_bytes() for p in Path(tmp).resolve().rglob('*') if p.is_file()}
                with self.assertRaises((ValueError,OSError)):namespace['operate']('disable',**args)
                self.assertEqual(before,{str(p):p.read_bytes() for p in Path(tmp).resolve().rglob('*') if p.is_file()})

    def test_unknown_supervisor_removal_journal_never_mutates(self):
        for raw in ('null','[]','{}','{"phase":"disabled","archive":"bad","extra":1}'):
            with self.subTest(raw=raw),tempfile.TemporaryDirectory() as tmp:
                args=self.fixture(Path(tmp).resolve());(args['state']/'cytv-removal.json').write_text(raw)
                before={str(p):p.read_bytes() for p in Path(tmp).resolve().rglob('*') if p.is_file()}
                with self.assertRaises(ValueError):namespace['operate']('disable',**args)
                self.assertEqual(before,{str(p):p.read_bytes() for p in Path(tmp).resolve().rglob('*') if p.is_file()})

    def test_locked_worker_and_exact_running_worker_block_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=self.fixture(Path(tmp).resolve());lock=args['state']/'daemon.lock'
            with lock.open('w') as stream:
                fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
                with self.assertRaisesRegex(ValueError,'worker'):namespace['operate']('status',**args)
            proc=args['proc']/'123';proc.mkdir();(proc/'cmdline').write_bytes(b'/usr/bin/python3\0'+str(args['state']/'code/run-system-updater.py').encode()+b'\0worker\0')
            (proc/'stat').write_text('123 (python) '+ ' '.join(['0']*19+['1234']))
            with self.assertRaisesRegex(ValueError,'worker'):namespace['operate']('status',**args)

    def test_absent_is_noop_but_orphan_artifacts_refuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=self.fixture(Path(tmp).resolve())
            namespace['operate']('disable',**args);namespace['operate']('archive',**args)
            self.assertEqual(namespace['operate']('status',**args),{'present':False})
            args['hook'].write_text('orphan')
            with self.assertRaisesRegex(ValueError,'ownership'):namespace['operate']('status',**args)

    def test_command_fits_ssh_limit_and_is_self_contained(self):
        import shlex
        self.assertLess(len(shlex.join(['/usr/bin/python3','-c',COMMAND,'status'])),8000)
        self.assertIn('operate',namespace)

    def test_process_matching_is_exact_and_includes_service_wrapper(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();code=root/'state/code';proc=root/'proc';proc.mkdir()
            for pid,args in ((101,['/bin/sh',str(code.parent/'run-service')]),(102,['/usr/bin/node','unrelated.js',str(code)]),(103,['/usr/bin/python3',str(code/'run-system-updater.py'),'worker'])):
                path=proc/str(pid);path.mkdir();(path/'cmdline').write_bytes(b'\0'.join(a.encode() for a in args)+b'\0');(path/'stat').write_text(str(pid)+' (process) '+ ' '.join(['0']*19+['1234']))
            matches=namespace['processes'](code,proc)
            self.assertEqual({p[0] for p in matches},{101,103})
            self.assertEqual([p[2] for p in matches if p[0]==103],[True])

    def test_disable_restores_only_receipted_legacy_grants(self):
        for conflict in (False,True):
            with self.subTest(conflict=conflict),tempfile.TemporaryDirectory() as tmp:
                args=self.fixture(Path(tmp).resolve());state=args['state'];api=args['base']/'api-permissions.d/com.cleanyourtv.updater.permissions.json'
                original='{ "ui": ["legacy/install"] }';disabled='{ "ui": [] }';api.write_text(disabled)
                record={'schema':1,'files':{str(api):{'original':original,'disabled':disabled,'mode':0o600}}}
                (state/'legacy-lockdown.json').write_text(json.dumps(record))
                if conflict:api.write_text('other owner')
                if conflict:
                    with self.assertRaisesRegex(ValueError,'lockdown'):namespace['operate']('disable',**args)
                    self.assertTrue(args['hook'].exists());self.assertEqual(api.read_text(),'other owner')
                else:
                    namespace['operate']('disable',**args);self.assertEqual(api.read_text(),original)
                    self.assertTrue(namespace['operate']('disable',**args)['disabled'])

    def test_completed_disable_preserves_later_owned_legacy_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=self.fixture(Path(tmp).resolve());api=args['base']/'api-permissions.d/com.cleanyourtv.updater.permissions.json'
            api.write_text('disabled')
            (args['state']/'legacy-lockdown.json').write_text(json.dumps({'schema':1,'files':{str(api):{'original':'original','disabled':'disabled','mode':0o600}}}))
            namespace['operate']('disable',**args)
            api.write_text('disabled')
            before={str(p):p.read_bytes() for p in Path(tmp).resolve().rglob('*') if p.is_file()}
            namespace['operate']('disable',**args)
            self.assertEqual(before,{str(p):p.read_bytes() for p in Path(tmp).resolve().rglob('*') if p.is_file()})

    def root_removal_fixture(self,args):
        root=args['state'].parent/'root-updater';root.mkdir();saved=root/'removed-registration';saved.mkdir()
        app='com.cleanyourtv.root.updater';service=app+'.service';base=args['base']
        paths={key:base/folder/(service+suffix) for key,folder,suffix in (('service','services.d','.service'),('role','roles.d','.service.json'),('client','client-permissions.d','.service.json'),('api','api-permissions.d','.api.json'))}
        api=paths['api'];original=json.dumps({'ui':[service+'/status',service+'/install']});disabled=json.dumps({'ui':[service+'/status']})
        registration={'files':{str(path):{'original':None,'installed':original if key=='api' else key} for key,path in paths.items()}}
        before=json.dumps(registration);registration['files'][str(api)]['installed']=disabled;after=json.dumps(registration)
        (root/'registration.json').write_text(before)
        for key in paths:(saved/key).write_text(disabled if key=='api' else key)
        (saved/'hook').write_text('#!/bin/sh\n/usr/bin/python3 '+str(root/'code/run-updater.py')+' worker </dev/null >/dev/null 2>&1 &\n')
        manifest={'id':app,'version':'1.0.0','serviceFiles':[str(paths['service'])],'apiPermissionFiles':[str(api)],'roleFiles':[str(paths['role']),str(base/'roles.d'/(app+'.app.json'))],'clientPermissionFiles':[str(paths['client']),str(base/'client-permissions.d'/(app+'.app.json'))]}
        (saved/'manifest').write_text(json.dumps(manifest))
        (root/'cytv-removal.json').write_text(json.dumps({'phase':'disabled','archive':str(root)+'.archive-'+'b'*32}))
        legacy={str(api):{'original':original,'disabled':disabled,'mode':0o600},str(root/'registration.json'):{'original':before,'disabled':after,'mode':0o600}}
        (args['state']/'legacy-lockdown.json').write_text(json.dumps({'schema':1,'files':legacy}))
        return root,api,after

    def test_repeat_disable_reconciles_only_exact_owned_root_removal(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            args=self.fixture(Path(tmp).resolve());namespace['operate']('disable',**args)
            root,api,after=self.root_removal_fixture(args)
            before={str(p):p.read_bytes() for p in Path(tmp).resolve().rglob('*') if p.is_file()}
            with patch.dict(namespace,ROOT_UPDATER=root):
                namespace['operate']('status',**args)
                self.assertEqual(before,{str(p):p.read_bytes() for p in Path(tmp).resolve().rglob('*') if p.is_file()})
                namespace['operate']('disable',**args)
                before[str(root/'registration.json')]=after.encode()
                self.assertEqual(before,{str(p):p.read_bytes() for p in Path(tmp).resolve().rglob('*') if p.is_file()})
                namespace['operate']('disable',**args)
                self.assertEqual((root/'registration.json').read_text(),after);self.assertFalse(api.exists())

    def test_repeat_disable_preserves_root_removal_after_initial_restore(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            args=self.fixture(Path(tmp).resolve());namespace['operate']('disable',**args)
            root,api,_=self.root_removal_fixture(args)
            legacy=json.loads((args['state']/'legacy-lockdown.json').read_text())['files']
            (root/'removed-registration/api').write_text(legacy[str(api)]['original'])
            before={str(p):p.read_bytes() for p in Path(tmp).resolve().rglob('*') if p.is_file()}
            with patch.dict(namespace,ROOT_UPDATER=root):namespace['operate']('disable',**args)
            self.assertEqual(before,{str(p):p.read_bytes() for p in Path(tmp).resolve().rglob('*') if p.is_file()})

    def test_root_reconciliation_conflicts_are_read_only(self):
        from unittest.mock import patch
        for case in ('journal','archive','saved-api','saved-service','snapshot','foreign-inventory','link','live-api','unknown-journal'):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as tmp:
                args=self.fixture(Path(tmp).resolve());namespace['operate']('disable',**args)
                root,api,after=self.root_removal_fixture(args)
                if case=='journal':(root/'cytv-removal.json').write_text('{"phase":"disabling"}')
                if case=='unknown-journal':(root/'cytv-removal.json').write_text(json.dumps({'phase':'disabled','archive':str(root)+'.archive-'+'b'*32,'extra':True}))
                if case=='archive':Path(str(root)+'.archive-'+'b'*32).mkdir()
                if case=='saved-api':(root/'removed-registration/api').write_text('foreign')
                if case=='saved-service':(root/'removed-registration/service').write_text('foreign')
                if case=='live-api':api.write_text('foreign')
                if case=='link':raw=(root/'removed-registration/api').read_bytes();(root/'api-copy').write_bytes(raw);(root/'removed-registration/api').unlink();(root/'removed-registration/api').symlink_to(root/'api-copy')
                if case in ('snapshot','foreign-inventory'):
                    legacy=json.loads((args['state']/'legacy-lockdown.json').read_text());entry=legacy['files'][str(root/'registration.json')];value=json.loads(entry['disabled'])
                    if case=='snapshot':value['files'][str(args['base']/'services.d/com.cleanyourtv.root.updater.service.service')]['installed']='other'
                    else:value['files']['/foreign']={'installed':'foreign','original':None}
                    entry['disabled']=json.dumps(value);(args['state']/'legacy-lockdown.json').write_text(json.dumps(legacy))
                before={str(p):p.read_bytes() for p in Path(tmp).resolve().rglob('*') if p.is_file()}
                with patch.dict(namespace,ROOT_UPDATER=root):
                    with self.assertRaises((ValueError,OSError)):namespace['operate']('disable',**args)
                self.assertEqual(before,{str(p):p.read_bytes() for p in Path(tmp).resolve().rglob('*') if p.is_file()})

    def test_archive_allows_owned_legacy_cleanup_after_confirmed_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=self.fixture(Path(tmp).resolve());api=args['base']/'api-permissions.d/com.cleanyourtv.updater.permissions.json';api.write_text('disabled')
            (args['state']/'legacy-lockdown.json').write_text(json.dumps({'schema':1,'files':{str(api):{'original':'original','disabled':'disabled','mode':0o600}}}))
            namespace['operate']('disable',**args);self.assertEqual(api.read_text(),'original')
            api.unlink()
            self.assertTrue(namespace['operate']('archive',**args)['removed'])

    def test_absent_status_refuses_exact_device_bootstrap_until_it_exits(self):
        for middle in ('','system-updater/','bundle/'):
            with self.subTest(middle=middle),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp).resolve();state=root/'state';base=root/'bus';base.mkdir();installed=root/'apps';installed.mkdir();proc=root/'proc';proc.mkdir()
                args=dict(state=state,base=base,hook=root/'boot',installed=installed,proc=proc)
                process=proc/'321';process.mkdir()
                script='/tmp/cytv-system-updater-'+'a'*32+'/'+middle+'setup-system-updater.py'
                argv=['/usr/bin/python3',script,'--bundle','/tmp/bundle','--edition','root','--device','--apply']
                (process/'cmdline').write_bytes(b'\0'.join(a.encode() for a in argv)+b'\0');(process/'stat').write_text('321 (python) '+ ' '.join(['0']*19+['9876']))
                self.assertEqual(namespace['processes'](state/'code',proc),[(321,'9876',True)])
                with self.assertRaisesRegex(ValueError,'bootstrap|worker'):namespace['operate']('status',**args)
                (process/'cmdline').unlink();(process/'stat').unlink();process.rmdir()
                self.assertEqual(namespace['operate']('status',**args),{'present':False})

    def test_unrelated_or_preview_bootstrap_arguments_are_not_owned_workers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();proc=root/'proc';proc.mkdir();code=root/'state/code'
            for pid,script,flags in ((201,'/tmp/cytv-system-updater-'+'a'*31+'/setup-system-updater.py',['--device','--apply']), (202,'/tmp/cytv-system-updater-'+'a'*32+'/other.py',['--device','--apply']), (203,'/tmp/cytv-system-updater-'+'a'*32+'/setup-system-updater.py',['--device'])):
                process=proc/str(pid);process.mkdir();argv=['/usr/bin/python3',script]+flags
                (process/'cmdline').write_bytes(b'\0'.join(a.encode() for a in argv)+b'\0');(process/'stat').write_text(str(pid)+' (python) '+ ' '.join(['0']*19+['1234']))
            self.assertEqual(namespace['processes'](code,proc),[])
