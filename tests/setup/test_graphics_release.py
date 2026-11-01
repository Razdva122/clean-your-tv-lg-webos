import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from cytv import package

ROOT = Path(__file__).resolve().parents[2]
def load(name):
    spec = importlib.util.spec_from_file_location(name.replace('/', '_'), ROOT / name)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

def ipk(app, version, resolution):
    return package.ipk(app, version, {'usr/palm/applications/'+app+'/appinfo.json':json.dumps({'id':app,'version':version,'resolution':resolution}).encode()})

class GraphicsRelease(unittest.TestCase):
    def test_variant_packages_are_validated_and_first_hd_requires_both_version_bumps(self):
        release = load('scripts/prepare-release.py')
        apps = release.APPS
        def packages(home, root):
            result = {kind:ipk(app, {'home':home,'root':root,'helper':'1.0.0'}[kind], '1920x1080') for kind, app in apps.items()}
            result.update({kind+'-720p':ipk(apps[kind], {'home':home,'root':root}[kind], '1280x720') for kind in ('home','root')})
            return result
        current = {'tag':'v2.0.0','versions':{'home':'2.0.0','root':'2.0.0','helper':'1.0.0'}}
        prior = {'tag':'v1.0.0','versions':{'home':'1.0.0','root':'1.0.0','helper':'1.0.0'}}
        old = {k:v for k,v in packages('1.0.0','1.0.0').items() if '-720p' not in k}
        # Legacy Home rollback has a minimum 1.2.0 version.
        prior['versions']['home']='1.2.0';old['home']=ipk(apps['home'],'1.2.0','1920x1080')
        manifests, files = release.prepare_manifests('v2.0.0',current,packages('2.0.0','2.0.0'),prior,old)
        self.assertIn('root-720p',manifests)
        self.assertNotIn('home-720p',manifests)
        self.assertTrue(manifests['root-720p']['url'].endswith('_720p_all.ipk'))
        bad=packages('2.0.0','2.0.0');bad['root-720p']=bad['root']
        with self.assertRaisesRegex(ValueError,'resolution'):
            release.prepare_manifests('v2.0.0',current,bad,prior,old)
        same=copy.deepcopy(prior);same['tag']='v2.0.0';same['versions']['home']='2.0.0'
        with self.assertRaisesRegex(ValueError,'first HD|First HD'):
            release.prepare_manifests('v2.0.0',same,packages('2.0.0','1.0.0'),prior,old)

    def test_established_hd_lineage_preserves_bytes_and_exact_published_rollback(self):
        release=load('scripts/prepare-release.py')
        def packages(v):
            result={kind:ipk(app,'1.0.0' if kind=='helper' else v,'1920x1080') for kind,app in release.APPS.items()}
            result.update({kind+'-720p':ipk(release.APPS[kind],v,'1280x720') for kind in ('home','root')})
            return result
        prior={'tag':'v2.0.0','versions':{'home':'2.0.0','root':'2.0.0','helper':'1.0.0'}}
        current={'tag':'v3.0.0','versions':{'home':'3.0.0','root':'3.0.0','helper':'1.0.0'}}
        old=packages('2.0.0')
        manifests,files=release.prepare_manifests('v3.0.0',current,packages('3.0.0'),prior,old)
        self.assertEqual(manifests['previous-720p']['home'],'2.0.0')
        self.assertEqual(files['com.gathin.tvhome_2.0.0_720p_all.ipk'],old['home-720p'])
        same=copy.deepcopy(prior);same['tag']='v3.0.0'
        rollback=({'home':'1.2.0','helper':'1.0.0'},ipk(release.APPS['home'],'1.2.0','1920x1080'))
        changed=packages('2.0.0');entries=package.data_files(changed['root-720p']);entries['changed.js']=b'changed'
        changed['root-720p']=package.ipk(release.APPS['root'],'2.0.0',entries)
        with self.assertRaisesRegex(ValueError,'without version bump'):
            release.prepare_manifests('v3.0.0',same,changed,prior,old,rollback)
        bad=copy.deepcopy(old);bad['home-720p']=old['home']
        with self.assertRaisesRegex(ValueError,'resolution'):
            release.prepare_manifests('v3.0.0',current,packages('3.0.0'),prior,bad)

    def test_unchanged_home_carries_existing_hd_channel_and_exact_rollback(self):
        release=load('scripts/prepare-release.py')
        def packages(v):
            result={kind:ipk(app,'1.0.0' if kind=='helper' else v,'1920x1080') for kind,app in release.APPS.items()}
            result.update({kind+'-720p':ipk(release.APPS[kind],v,'1280x720') for kind in ('home','root')})
            return result
        old=packages('2.0.0');current=copy.deepcopy(old)
        prior={'tag':'v2.0.0','versions':{'home':'2.0.0','root':'2.0.0','helper':'1.0.0'},'no_root_ota_720p':{'version':'2.0.0'}}
        build={**prior,'tag':'v2.0.1'}
        rollback=({'home':'1.2.0','helper':'1.0.0'},ipk(release.APPS['home'],'1.2.0','1920x1080'))
        raw=ipk(release.APPS['home'],'1.2.0','1280x720')
        proof={'home':'1.2.0','helper':'1.0.0','sha256':release.digest(raw)}
        with self.assertRaisesRegex(ValueError,'HD.*rollback'):
            release.prepare_manifests('v2.0.1',build,current,prior,old,rollback)
        manifests,files=release.prepare_manifests('v2.0.1',build,current,prior,old,rollback,rollback_hd=(proof,raw))
        self.assertEqual(manifests['home-720p']['home'],'2.0.0')
        self.assertEqual(manifests['previous-720p']['home'],'1.2.0')
        self.assertEqual(files['com.gathin.tvhome_1.2.0_720p_all.ipk'],raw)
        bad=ipk(release.APPS['home'],'1.2.0','1920x1080')
        with self.assertRaisesRegex(ValueError,'resolution|digest'):
            release.prepare_manifests('v2.0.1',build,current,prior,old,rollback,rollback_hd=(proof,bad))

    def test_published_hd_adapter_verifies_signed_envelopes_hashes_and_resolution(self):
        import subprocess
        from unittest.mock import patch
        release=load('scripts/prepare-release.py')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();(root/'updater-service').mkdir()
            (root/'updater-service/policy.js').write_bytes((ROOT/'updater-service/policy.js').read_bytes())
            def channel(resolution):
                raws={v:ipk(release.APPS['home'],v,resolution) for v in ('2.0.0','1.2.0')}
                records={v:{'schema':1,'release':'v2.0.0','home':v,'helper':'1.0.0','notes':'Exact published HD','sha256':release.digest(raw),'url':release.URL+'v2.0.0/com.gathin.tvhome_'+v+'_720p_all.ipk'} for v,raw in raws.items()}
                spec=root/'input.json';spec.write_text(json.dumps(records))
                subprocess.run(['node','-e',"const fs=require('fs'),c=require('crypto'),m=JSON.parse(fs.readFileSync(process.argv[1])),keys=c.generateKeyPairSync('rsa',{modulusLength:2048});fs.writeFileSync(process.argv[2]+'/updater-service/release-public.pem',keys.publicKey.export({type:'spki',format:'pem'}));function sign(m){const b=Buffer.from(JSON.stringify(m));return {payload:b.toString('base64'),signature:c.sign('RSA-SHA256',b,keys.privateKey).toString('base64')}}const p=sign(m['1.2.0']);fs.writeFileSync(process.argv[2]+'/previous-update-720p.json',JSON.stringify(p));fs.writeFileSync(process.argv[2]+'/update-720p.json',JSON.stringify({...sign(m['2.0.0']),previous:p}));",str(spec),str(root)],check=True)
                assets={name:(root/name).read_bytes() for name in ('update-720p.json','previous-update-720p.json')}
                assets.update({'com.gathin.tvhome_'+v+'_720p_all.ipk':raw for v,raw in raws.items()})
                return raws,assets
            raws,assets=channel('1280x720')
            def download(meta,name,folder):
                folder=Path(folder);folder.mkdir(parents=True,exist_ok=True);raw=assets[name];(folder/name).write_bytes(raw);return raw
            with patch.object(release,'ROOT',root),patch.object(release,'download',side_effect=download),patch.object(release,'release_metadata',return_value={'draft':False,'prerelease':False}):
                result=release.verified_hd_home_rollback({},root/'good',{'home':'2.0.0','helper':'1.0.0'},raws['2.0.0'])
                self.assertEqual(result[1],raws['1.2.0'])
                assets['com.gathin.tvhome_1.2.0_720p_all.ipk']=b'tampered'
                with self.assertRaisesRegex(ValueError,'digest'):
                    release.verified_hd_home_rollback({},root/'tampered',{'home':'2.0.0','helper':'1.0.0'},raws['2.0.0'])
                envelope=json.loads(assets['update-720p.json']);envelope['signature']='AAAA';assets['update-720p.json']=json.dumps(envelope).encode()
                with self.assertRaises(subprocess.CalledProcessError):
                    release.verified_hd_home_rollback({},root/'bad-signature',{'home':'2.0.0','helper':'1.0.0'},raws['2.0.0'])
                raws,assets=channel('1920x1080')
                with self.assertRaisesRegex(ValueError,'resolution'):
                    release.verified_hd_home_rollback({},root/'wrong-resolution',{'home':'2.0.0','helper':'1.0.0'},raws['2.0.0'])

    def test_embedded_validation_rejects_wrong_variant_resolution(self):
        release=load('scripts/assemble-release.py')
        versions={'home':'2.0.0','root':'2.0.0','helper':'1.0.0'}
        files={'launcher.ipk':ipk('com.gathin.tvhome','2.0.0','1920x1080'),
               'launcher-720p.ipk':ipk('com.gathin.tvhome','2.0.0','1920x1080'),
               'helper.ipk':ipk('com.local.nativehome','1.0.0','1920x1080')}
        for folder,resolution in [('root','1920x1080'),('root-720p','1280x720')]:
            files[folder+'/app.ipk']=ipk('com.cleanyourtv.root.preview','2.0.0',resolution)
            files[folder+'/bundle.json']=json.dumps({'package':'app.ipk'}).encode()
            files[folder+'/release.json']=json.dumps({'version':'2.0.0'}).encode()
        import hashlib
        files['payload.json']=json.dumps({'home_version':'2.0.0','helper_version':'1.0.0',
            'graphics':{'1920x1080':{'launcher':'launcher.ipk','root':'root'},'1280x720':{'launcher':'launcher-720p.ipk','root':'root-720p'}},
            'files':{n:hashlib.sha256(b).hexdigest() for n,b in files.items()}}).encode()
        with self.assertRaisesRegex(ValueError,'resolution'):
            release.verify_embedded(files.__getitem__,versions)

    def test_hd_release_set_selects_exact_package_and_signed_filename(self):
        build=load('system-updater/build.py')
        with tempfile.TemporaryDirectory() as tmp:
            payload=Path(tmp).resolve()
            for name in ('helper','updater'):
                (payload/(name+'.ipk')).write_bytes(ipk(build.APPS[name],'2.0.0','1920x1080'))
            (payload/'launcher.ipk').write_bytes(ipk(build.APPS['home'],'2.0.0','1920x1080'))
            (payload/'launcher-720p.ipk').write_bytes(ipk(build.APPS['home'],'2.0.0','1280x720'))
            manifest,raws=build.release_set(payload,'no-root','v2.0.0',local=False,graphics='1280x720')
            home=manifest['components'][0]
            self.assertEqual(raws['home'],(payload/'launcher-720p.ipk').read_bytes())
            self.assertTrue(home['url'].endswith('_720p_all.ipk'))
            self.assertEqual(manifest['edition'],'no-root')
            self.assertNotIn('graphics',manifest)
