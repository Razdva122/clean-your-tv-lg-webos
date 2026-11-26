"""Root deployment to System baseline with the actual personalized Home IPK."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from cytv import package
from test_build import load, ROOT
from test_core import Store, IO, profile

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

class SingleTileOriginTests(unittest.TestCase):
    def run_signed_update_and_undo(self, top, system, device, baseline):
        # Package installation and the TV bus are simulated. The engine uses
        # real signed descriptors, cached archives, disk journals and readback.
        from system_updater.core import Manager
        build=load('build')
        payload=top/'candidate';payload.mkdir()
        subprocess.run([sys.executable,str(ROOT/'root-edition/build.py'),'--single-tile',
                        '--output',str(payload/'root'),'--version','1.1.0'],check=True,stdout=subprocess.PIPE)
        candidate,raws=build.release_set(payload,'root','v1.1.0',local=False,single_tile=True)
        sign="""const fs=require('fs'),crypto=require('crypto');
        const raw=fs.readFileSync(0),key=crypto.generateKeyPairSync('rsa',{modulusLength:2048});
        console.log(JSON.stringify({key:key.publicKey.export({type:'spki',format:'pem'}),
          proof:{payload:raw.toString('base64'),signature:crypto.sign('RSA-SHA256',raw,key.privateKey).toString('base64')}}));"""
        signed=json.loads(subprocess.check_output(['node','-e',sign],input=json.dumps(candidate).encode()))
        candidate['proof']=signed['proof']
        def verify(method,data):
            self.assertEqual(method,'verify')
            script="""const fs=require('fs'),p=JSON.parse(fs.readFileSync(0,'utf8'));
            console.log(JSON.stringify(require(process.argv[1]).verify(p.proof,p.key,2)));"""
            return json.loads(subprocess.check_output(['node','-e',script,str(system/'system_updater/policy.js')],
                              input=json.dumps(dict(data,key=signed['key'])).encode()))
        device.fetch=verify
        def prepare(target,prior):
            for release in (prior,target):
                device._verify_release(release,'root')
                for c in release['components']:
                    if release==target:device.cached(c).write_bytes(raws[c['name']])
                    device.inspect(device.cache_bytes(c),c)
        def install(c,submitted,terminal,intent):
            intent();submitted({'sha256':c['sha256']})
            raw=device.cache_bytes(c)
            if c['kind']=='ipk':
                for name,data in package.data_files(raw).items():
                    dest=device.installed_root/name
                    dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
            else:
                for name,data in load('setup').entries(raw).items():
                    dest=device._infra_path(name)
                    dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
            terminal({'success':True})
        io=IO()
        io.offer=lambda edition:dict(prior=baseline,candidate=candidate,canInstall=True)
        io.prepare=prepare;io.install=install
        io.verify_baseline=device.verify_baseline;io.verify_installed=device.verify_installed
        manager=Manager(device.store,io)
        def advance(phase):
            for _ in range(30):
                tx=manager.run()
                if tx['phase']==phase:return tx
                if tx['phase'] in ('recovery-required','aborted'):self.fail(tx.get('error',tx['phase']))
            self.fail(manager.status())
        tx=manager.install('root','v1.1.0',profile())
        advance('verifying');manager.healthy('root',tx['id'],'1.1.0');advance('complete')
        self.assertEqual(device.owner_identity(package.ROOT_APP)['version'],'1.1.0')
        self.assertTrue(device.verify_baseline(device._baseline('root')))
        manager.rollback()
        advance('verifying-rollback');manager.healthy('root',tx['id'],'1.0.0');advance('rolled-back')
        self.assertEqual(device.owner_identity(package.ROOT_APP)['version'],'1.0.0')
        self.assertEqual(device._baseline('root'),baseline)
        self.assertTrue(device.verify_baseline(baseline))

    def test_deployed_original_is_the_only_root_rollback_baseline(self):
        import package_identity
        build, setup = load('build'), load('setup')
        with tempfile.TemporaryDirectory() as tmp:
            top = Path(tmp).resolve()
            root, system = top/'root', top/'supervisor'
            installed, legacy = top/'installed', top/'legacy'
            subprocess.run([sys.executable, str(ROOT/'root-edition/build.py'), '--single-tile',
                            '--output', str(root), '--version', '1.0.0'], check=True, stdout=subprocess.PIPE)
            build.build(system, single_tile=True)
            package.personalize_root(root, {'apps':[{'id':'com.webos.app.home','title':'LG Home'}], 'inputs':[]})
            manifest = json.loads((root/'bundle.json').read_bytes())
            original = (root/manifest['package']).read_bytes()
            (root/package_identity.SINGLE_TILE_ORIGINAL).write_bytes(original)
            app = package_identity.ROOT
            store = Store(root, uid=os.geteuid())
            store.write('deploy', {'app':app,'stage':'installed-recovery-only'})
            terminal = {'completed':True,'event':{'id':app,'statusValue':30,
                'details':{'packageId':app,'client':'com.webos.lunasend-99',
                           'ipkFile':'/var/lib/clean-your-tv-installer/cytv-root-install-fixture/package.ipk'}}}
            store.write('install-terminal', terminal)
            files = package.data_files(original)
            for name, data in files.items():
                target = installed/name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            shutil.copytree(installed/('usr/palm/services/'+app+'.service'), root/'service')
            roots = dict(runtime=root/'runtime', service=root/'service', updater=legacy/'code')
            output = setup.snapshot(system, 'root', top/'baseline', installed=installed, **roots)
            baseline = setup.verify_baseline(output, system)
            home, infra = baseline['components']
            self.assertEqual((home['name'], infra['name']), ('root','root-infrastructure'))
            self.assertEqual((output/'cache'/home['sha256']).read_bytes(), original)
            self.assertFalse(any(name.startswith('updater/') for name in infra['files']))
            # Use the same durable caches and owner-identity entry points as the
            # product engine; installed SDK bytes alone cannot supply a baseline.
            from system_updater.device import Device
            active=Store(top/'active-system', uid=os.geteuid())
            shutil.copytree(output/'cache',Path(active.root)/'cache')
            for key in ('baseline','current-root'):active.write(key,baseline)
            device=Device(active, code=system, root_state=root, root_updater=legacy,
                          installed=installed, uid=os.geteuid())
            self.assertTrue(device.verify_baseline(device._baseline('root')))
            self.assertEqual(device.owner_identity(app)['version'],'1.0.0')
            origin = setup.require_transition_home
            destination = setup.infrastructure_destination
            def local_home(sdk, edition, schema):
                return origin(sdk, edition, schema, root=root)
            def local_infra(name):
                return destination(name, **roots)
            state=top/'system-state'
            with patch.object(setup, 'require_transition_home', side_effect=local_home), \
                    patch.object(setup,'infrastructure_destination',side_effect=local_infra):
                self.assertEqual(setup.preflight(system, output, state, installed, top/'ls2', top/'hook')[1], baseline)
                # Valid package, same installed files, changed archive modes. It
                # cannot replace the private original that rollback must install.
                alternate=package.ipk(app, home['version'], files)
                self.assertNotEqual(alternate, original)
                home.update(sha256=digest(alternate),size=len(alternate))
                (output/'cache'/home['sha256']).write_bytes(alternate)
                (output/'baseline.json').write_text(json.dumps(baseline))
                with self.assertRaisesRegex(ValueError,'original personalized'):
                    setup.preflight(system, output, state, installed, top/'ls2', top/'hook')
            self.run_signed_update_and_undo(top,system,device,active.read('baseline'))
            self.assertFalse(state.exists())
            self.assertFalse(legacy.exists())
            evidence=store.read('install-terminal')
            store.write('install-terminal',{'completed':True})
            with self.assertRaisesRegex(ValueError,'original|Original'):
                setup.require_transition_home(installed, 'root', 2, root=root)
            store.write('install-terminal',evidence)
            (installed/('usr/palm/applications/'+app+'/apps.js')).write_bytes(b'changed')
            with self.assertRaises(ValueError):
                setup.snapshot(system,'root',top/'tampered',installed=installed,**roots)
