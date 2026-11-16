import importlib
import json
import os
from unittest.mock import patch
from test_device import DeviceBase, ipk, digest
from test_core import Store

class SupervisorPackageTests(DeviceBase):
    def test_own_package_rejects_scripts_foreign_identity_and_hash_change(self):
        mod=importlib.import_module('system_updater.supervisor_io')
        raw=ipk('com.cleanyourtv.system.updater')
        descriptor={'version':'1.0.0','sha256':digest(raw),'size':len(raw)}
        files=mod.package_files(raw,descriptor)
        self.assertIn('usr/palm/applications/com.cleanyourtv.system.updater/appinfo.json',files)
        with self.assertRaises(ValueError):mod.package_files(raw+b'x',descriptor)
        bad=ipk('com.gathin.tvhome');descriptor.update(sha256=digest(bad),size=len(bad))
        with self.assertRaises(ValueError):mod.package_files(bad,descriptor)
    def test_registration_plan_is_bounded_to_system_service(self):
        mod=importlib.import_module('system_updater.supervisor_io')
        service='com.cleanyourtv.system.updater.service'
        plan={'role.json':{'appId':service,'type':'regular','allowedNames':[service],
                'permissions':[{'service':service,'inbound':['com.gathin.tvhome'],'outbound':[]}]},
              'client.json':{'com.gathin.tvhome':[service+'.ui']},
              'api.json':{service+'.ui':[service+'/status']}}
        self.assertEqual(mod.permissions(plan),plan)
        plan['api.json'][service+'.ui']=['com.webos.applicationManager/launch']
        with self.assertRaises(ValueError):mod.permissions(plan)

    def test_generation_does_not_adopt_an_unrelated_successful_install(self):
        mod=importlib.import_module('system_updater.supervisor_io')
        runtime=importlib.import_module('system_updater.bootstrap').Bootstrap(self.root/'state',uid=os.getuid())
        raw=ipk('com.cleanyourtv.system.updater')
        descriptor={'version':'1.0.0','sha256':digest(raw),'size':len(raw)}
        files={name:digest(value) for name,value in mod.package_files(raw,descriptor).items()}
        (self.root/'state/cache'/(descriptor['sha256']+'.ipk')).write_bytes(raw)
        event={'completed':True,'event':{'id':mod.APP,'statusValue':30,'details':{'packageId':mod.APP,
            'client':'com.webos.lunasend-42','ipkFile':'/var/lib/clean-your-tv-installer/cytv-root-install-fixture/package.ipk'}}}
        runtime.product.write('installed-package',{'package':descriptor,'files':files})
        runtime.product.write('installed-terminal',event)
        generation=dict(schema=1,operation='a'*32,package=descriptor,files=files,terminal=event,slot=None)
        runtime.store.write('supervisor-generation',generation)
        self.assertEqual(mod.generation_inventory(runtime.state,os.getuid()),files)
        changed=json.loads(json.dumps(event));changed['event']['details']['client']='com.webos.lunasend-77'
        runtime.store.write('supervisor-generation',dict(generation,terminal=changed))
        with self.assertRaises(ValueError):mod.generation_inventory(runtime.state,os.getuid())
