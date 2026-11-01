import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from cytv import package
ROOT=Path(__file__).resolve().parents[2]

def load(path):
    spec=importlib.util.spec_from_file_location('release_'+path.stem,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

class ReleaseTests(unittest.TestCase):
    def test_android_versions_accept_stable_and_historical_preview_only(self):
        prepare = load(ROOT / 'scripts/prepare-release.py')
        base = {key: '1.0.0' for key in ('cytv', 'home', 'helper', 'root', 'updater')}
        for value in ('0.4.0', '0.3.0-preview'):
            prepare.validate_versions({**base, 'android': value, 'android_version_code': 13})
        for value in ('0.4', '0.4.0-beta', '0.4.0-preview-extra', '0.4.0\n', None):
            with self.subTest(version=value), self.assertRaises(ValueError):
                prepare.validate_versions({**base, 'android': value, 'android_version_code': 13})
        for code in (None, True, 0, '13'):
            with self.subTest(code=code), self.assertRaises(ValueError):
                prepare.validate_versions({**base, 'android': '0.4.0', 'android_version_code': code})

    def test_final_assets_produce_both_exact_release_sets(self):
        build=load(ROOT/'system-updater/build.py');prepare=load(ROOT/'scripts/prepare-release.py')
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp).resolve();payload=path/'payload';payload.mkdir();(payload/'root').mkdir();(payload/'root-updater').mkdir()
            versions={}
            for name,app in build.APPS.items():
                version='1.0.0';versions[name]=version
                files={'usr/palm/applications/'+app+'/appinfo.json':json.dumps({'id':app,'version':version}).encode()}
                if name=='root':
                    for service_file in ('service.js','startup-diagnostics.js','app-inventory.js','handlers.js','services.json','package.json','activity.json','boot-recover.sh'):files['usr/palm/services/'+app+'.service/'+service_file]=('final '+service_file).encode()
                raw=package.ipk(app,version,files)
                target={'home':'launcher.ipk','helper':'helper.ipk','updater':'updater.ipk','root':'root/root.ipk','root-updater':'root-updater/root-updater.ipk'}[name]
                (payload/target).write_bytes(raw)
            (payload/'root/python_binding.py').write_bytes(b'fixed binding');(payload/'root/python_boot.js').write_bytes(b'fixed boot');(payload/'root/runtime').mkdir();(payload/'root/runtime/cli.py').write_bytes(b'fixed runtime')
            for name in ('package_data.py','package_identity.py','updater/store.py','updater/package.py','startup_guard.py'):
                target=payload/'root'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b'fixed '+name.encode())
            (payload/'root-updater/service.js').write_bytes(b'fixed updater')
            (payload/'root/bundle.json').write_text(json.dumps({'package':'root.ipk','files':{'runtime/cli.py':build.digest(b'fixed runtime'),'python_binding.py':build.digest(b'fixed binding'),'python_boot.js':build.digest(b'fixed boot'),**{name:build.digest(b'fixed '+name.encode()) for name in ('package_data.py','package_identity.py','updater/store.py','updater/package.py','startup_guard.py')}}}))
            (payload/'root-updater/bundle.json').write_text(json.dumps({'files':{'service.js':build.digest(b'fixed updater'),'root-updater.ipk':build.digest((payload/'root-updater/root-updater.ipk').read_bytes())}}))
            output=path/'release';manifests=build.prepare_release(payload,output,'v1.0.3','Changes')
            self.assertEqual(manifests['root']['minimumSupervisorVersion'],'1.1.1')
            self.assertNotIn('minimumSupervisorVersion',manifests['no-root'])
            files={p.name:p.read_bytes() for p in output.iterdir()}
            prepare.verify_system_assets(manifests,{'tag':'v1.0.3','versions':versions},files)
            self.assertEqual({c['name'] for c in manifests['root']['components']},{'root','root-updater','root-infrastructure'})
            self.assertEqual({c['name'] for c in manifests['no-root']['components']},{'home','helper','updater'})
            import io,tarfile
            infra=next(c for c in manifests['root']['components'] if c['name']=='root-infrastructure')
            with tarfile.open(fileobj=io.BytesIO(files[infra['url'].rsplit('/',1)[1]]),mode='r:gz') as archive:
                service_files={m.name:archive.extractfile(m).read() for m in archive if m.name.startswith('service/')}
            self.assertEqual(len(service_files),8)
            self.assertEqual(service_files['service/startup-diagnostics.js'],b'final startup-diagnostics.js')
            self.assertEqual(service_files['service/service.js'],b'final service.js')
            self.assertEqual(files['com.gathin.tvhome_1.0.0_all.ipk'],(payload/'launcher.ipk').read_bytes())
            import shutil
            shutil.copytree(payload/'root',payload/'root-720p')
            for source,target,app in [('launcher.ipk','launcher-720p.ipk',build.APPS['home']),('root/root.ipk','root-720p/root.ipk',build.APPS['root'])]:
                entries=package.data_files((payload/source).read_bytes());name='usr/palm/applications/'+app+'/appinfo.json'
                info=json.loads(entries[name]);info['resolution']='1280x720';entries[name]=json.dumps(info).encode()
                (payload/target).write_bytes(package.ipk(app,info['version'],entries))
            all_manifests=build.prepare_release(payload,output,'v1.0.3','Changes')
            self.assertEqual(set(all_manifests),{'root','no-root','root-720p','no-root-720p'})
            all_files={p.name:p.read_bytes() for p in output.iterdir()}
            prepare.verify_system_assets(all_manifests,{'tag':'v1.0.3','versions':versions},all_files)
            hd_infra=next(c for c in all_manifests['root-720p']['components'] if c['name']=='root-infrastructure')
            self.assertEqual(hd_infra,infra,'Identical infrastructure must share the exact public artifact')
            self.assertEqual(all_files['com.gathin.tvhome_1.0.0_720p_all.ipk'],(payload/'launcher-720p.ipk').read_bytes())
            bad=json.loads(json.dumps(all_manifests));bad['root-720p']=bad['root']
            with self.assertRaisesRegex(ValueError,'resolution'):
                prepare.verify_system_assets(bad,{'tag':'v1.0.3','versions':versions},all_files)

            import copy
            for bad in (None,'1.1.0','bad'):
                changed=copy.deepcopy(manifests)
                if bad is None:changed['root'].pop('minimumSupervisorVersion')
                else:changed['root']['minimumSupervisorVersion']=bad
                with self.assertRaisesRegex(ValueError,'supervisor'):
                    prepare.verify_system_assets(changed,{'tag':'v1.0.3','versions':versions},files)
            first=manifests['root']['components'][0]['url'].rsplit('/',1)[1]
            with self.assertRaisesRegex(ValueError,'hash'):
                prepare.verify_system_assets(manifests,{'tag':'v1.0.3','versions':versions},{**files,first:b'wrong'})
            with self.assertRaisesRegex(ValueError,'version'):
                prepare.verify_system_assets(manifests,{'tag':'v1.0.3','versions':{**versions,'home':'2.0.0'}},files)
