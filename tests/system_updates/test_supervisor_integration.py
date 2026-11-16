"""Real own-package/cache/registration effects with only TV transport replaced."""
import hashlib
import importlib
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from test_core import Store
from test_device import ipk, tar, digest


class SupervisorIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.mod = importlib.import_module('system_updater.supervisor_io')
        self.bootstrap = importlib.import_module('system_updater.bootstrap')
        self.migration = importlib.import_module('system_updater.bootstrap_migration')
        self.device = importlib.import_module('system_updater.device')
        activation = importlib.import_module('system_updater.activation')
        state = self.root/'state'; product = Store(state, uid=os.getuid())
        store = Store(state/'engine-state', uid=os.getuid()); (state/'cache').mkdir()
        code = state/'code'; code.mkdir(); self.installed = self.root/'installed'
        self.base = self.root/'bus'; self.identifier = 'a'*32
        self.plan = self.permissions('status')
        (code/'permissions.json').write_text(json.dumps(self.plan))
        self.prior_raw = ipk(self.mod.APP, version='1.0.0')
        self.candidate_raw = ipk(self.mod.APP, version='1.1.0')
        self.prior = self.descriptor(self.prior_raw, '1.0.0')
        self.candidate = self.descriptor(self.candidate_raw, '1.1.0')
        (state/'cache'/(self.prior['sha256']+'.ipk')).write_bytes(self.prior_raw)
        self.original_terminal = self.terminal(self.prior)
        self.original_terminal.pop('package')
        product.write('installed-package', {'schema':1, 'package':dict(self.prior, local=True),
            'files':{name:digest(raw) for name,raw in self.mod.package_files(self.prior_raw,self.prior).items()}})
        product.write('installed-terminal', self.original_terminal)
        self.install_bytes(self.prior_raw, self.prior)
        payload = {'engine-entry.py':b'# verified engine\n', 'system-updater.ipk':self.candidate_raw,
                   'permissions.json':json.dumps(self.permissions('repair')).encode()}
        payload['engine.json'] = json.dumps({'schema':1,'version':'1.2.12',
            'files':{name:digest(raw) for name,raw in payload.items()}}).encode()
        raw = tar(payload); catalog = {'engine':{'version':'1.2.12','size':len(raw),'sha256':digest(raw)}}
        slots = activation.Slots(store, code, lambda proof:catalog)
        slot = slots.stage({}, raw); slots.begin(self.identifier,slot); slots.confirm(self.identifier)
        self.outer = {'id':self.identifier,'edition':'no-root','previousGeneration':None}
        self.runtime = SimpleNamespace(state=state,code=code,store=store,product=product,
                                       slots=slots,transaction=lambda:self.outer)
        self.io = self.mod.SupervisorIO(self.runtime,slot,installed=self.installed,base=self.base)
        registration = {}
        for key,folder,suffix in (('service','services.d','.service'),('role','roles.d','.service.json'),
                ('client','client-permissions.d','.service.json'),('api','api-permissions.d','.api.json')):
            path = self.base/folder/(self.mod.SERVICE+suffix); path.parent.mkdir(parents=True,exist_ok=True)
            original = ('Exec=/usr/bin/run-js-service -n '+str(self.installed/'usr/palm/services'/self.mod.SERVICE)+'\n') if key=='service' else '{}'
            installed = original.replace('Exec=/usr/bin/run-js-service -n '+str(self.installed/'usr/palm/services'/self.mod.SERVICE), 'Exec='+str(state/'run-service')) if key=='service' else json.dumps(self.plan[key+'.json'])
            registration[str(path)] = {'original':original,'installed':installed}; path.write_text(installed)
        product.write('registration', {'files':registration})
        self.old_receipt = product.read('installed-package'); self.installs = []; self.bus = []
        self.wrong_terminal = False
        original_iterdir = Path.iterdir
        def safe_iterdir(path):
            if path == Path('/proc'): return iter(())
            return original_iterdir(path)
        def bus(argv,**kwargs):
            self.bus.append(argv)
            return SimpleNamespace(stdout=json.dumps({'returnValue':True,'result':{'id':self.identifier}}).encode())
        patches = [patch.object(self.bootstrap,'Bootstrap',return_value=self.runtime),
                   patch('observed_install.install',side_effect=self.submit),
                   patch.object(Path,'iterdir',safe_iterdir),
                   patch.object(self.device.Device,'scan_services'),
                   patch.object(self.mod.subprocess,'run',side_effect=bus)]
        for item in patches: item.start(); self.addCleanup(item.stop)
        self.manager = self.migration.Migration(store,self.io)

    def permissions(self, method):
        service = self.mod.SERVICE
        return {'role.json':{'appId':service,'type':'regular','allowedNames':[service],
                'permissions':[{'service':service,'inbound':['com.gathin.tvhome'],'outbound':[]}]},
            'client.json':{'com.gathin.tvhome':[service+'.ui']},
            'api.json':{service+'.ui':[service+'/'+method]}}

    def descriptor(self,raw,version):
        return dict(version=version,sha256=digest(raw),size=len(raw))

    def terminal(self,target):
        return {'completed':True,'package':target,'event':{'id':self.mod.APP,'statusValue':30,
            'details':{'packageId':self.mod.APP,'client':'com.webos.lunasend-42',
                'ipkFile':'/var/lib/clean-your-tv-installer/cytv-root-install-fixture/package.ipk'}}}

    def install_bytes(self,raw,descriptor):
        for name,data in self.mod.package_files(raw,descriptor).items():
            path = self.installed/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(data)

    def submit(self,app,path,timeout,on_ready,on_accepted):
        raw = Path(path).read_bytes()
        target = self.candidate if digest(raw)==self.candidate['sha256'] else self.prior
        on_ready(); self.installs.append(target['version'])
        event = self.terminal(target)
        on_accepted({'details':event['event']['details']})
        self.install_bytes(raw,target)
        if self.wrong_terminal: event['event']['details'] = dict(event['event']['details'],client='com.webos.lunasend-99')
        return event

    def begin(self):
        self.manager.begin(self.identifier,*self.io.descriptors())

    def assert_registration(self):
        receipt = self.runtime.product.read('registration')
        for name,record in receipt['files'].items():
            self.assertEqual(Path(name).read_text(),record['installed'])

    def test_real_migration_publishes_signed_generation_and_restores_original(self):
        self.begin(); self.assertEqual(self.manager.run()['phase'],'complete')
        self.assertEqual(self.runtime.product.read('installed-package'),self.old_receipt)
        self.assertEqual(self.mod.generation_inventory(self.runtime.state,os.getuid()),
            {name:digest(raw) for name,raw in self.mod.package_files(self.candidate_raw,self.candidate).items()})
        self.assert_registration(); self.assertEqual(len(self.bus),1)
        self.manager.rollback(); self.assertEqual(self.manager.run()['phase'],'rolled-back')
        self.assertEqual(self.installs,['1.1.0','1.0.0']); self.assert_registration()
        self.assertEqual(self.runtime.store.read('supervisor-generation')['slot'],None)

    def test_unrelated_terminal_never_publishes_matching_installed_candidate(self):
        self.begin(); self.wrong_terminal=True
        self.assertEqual(self.manager.run()['phase'],'recovery-required')
        self.assertFalse(self.manager.status()['canRollback'])
        self.assertIsNone(self.runtime.store.read('supervisor-generation'))
        self.assertEqual(self.bus,[])

    def test_partial_registration_retries_exact_plan_without_install_replay(self):
        self.begin(); original = self.device.Device.atomic; writes = []
        def interrupted(device,path,raw,*args,**kwargs):
            original(device,path,raw,*args,**kwargs); writes.append(str(path))
            if len(writes)==1: raise KeyboardInterrupt('power loss')
        with patch.object(self.device.Device,'atomic',interrupted):
            with self.assertRaises(KeyboardInterrupt): self.manager.run()
        self.assertEqual(self.manager.run()['phase'],'complete')
        self.assertEqual(self.installs,['1.1.0']); self.assert_registration()


if __name__ == '__main__': unittest.main()
