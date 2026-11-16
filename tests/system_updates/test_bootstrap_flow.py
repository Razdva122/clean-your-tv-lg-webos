"""Real slot, own-package journal, generation and handoff; TV transports are fixtures."""
import copy
import importlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import test_bootstrap
from test_core import IO, release, profile
from test_device import ipk, tar, digest

class Dispatched(BaseException):pass

class BootstrapFlowTests(test_bootstrap.BootstrapFixture):

    def execute(self,edition='no-root',engine_only=False,repair=False,crash_handoff=False,unknown_install=False,crash_terminal=False):
        concrete=importlib.import_module('system_updater.supervisor_io')
        cli=importlib.import_module('system_updater.cli')
        observed=importlib.import_module('observed_install')
        device_module=importlib.import_module('system_updater.device')
        prior=ipk(concrete.APP,version='1.0.0')
        current=ipk(concrete.APP,version='1.0.0' if repair else '1.1.0')
        old={'version':'1.0.0','sha256':digest(prior),'size':len(prior)}
        original_terminal={'completed':True,'event':{'id':concrete.APP,'statusValue':30,'details':{'packageId':concrete.APP,
            'client':'com.webos.lunasend-40','ipkFile':'/var/lib/clean-your-tv-installer/cytv-root-install-old/package.ipk'}}}
        self.runtime.product.write('installed-package',{'schema':1,'package':dict(old,local=True),'files':{n:digest(v) for n,v in concrete.package_files(prior,old).items()}})
        self.runtime.product.write('installed-terminal',original_terminal)
        cache=self.runtime.state/'cache';cache.mkdir();(cache/(old['sha256']+'.ipk')).write_bytes(prior)
        installed=self.root/'installed'
        for name,value in concrete.package_files(prior,old).items():
            target=installed/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(value)
        service=concrete.SERVICE
        permission={'role.json':{'appId':service,'type':'regular','allowedNames':[service],
            'permissions':[{'service':service,'inbound':['com.gathin.tvhome'],'outbound':[]}]},
            'client.json':{'com.gathin.tvhome':[service+'.ui']},'api.json':{service+'.ui':[service+'/status']}}
        files={'engine-entry.py':b'# fixture executable\n','system-updater.ipk':current,'permissions.json':json.dumps(permission).encode()}
        raw=tar(dict(files,**{'engine.json':json.dumps({'schema':1,'version':'1.2.11','files':{n:digest(v) for n,v in files.items()}}).encode()}))
        self.catalog['engine'].update(sha256=digest(raw),size=len(raw))
        self.raw=raw
        base=self.root/'ls2';entries={}
        for key,(folder,name) in {'service':('services.d',service+'.service'),'role':('roles.d',service+'.service.json'),
                                 'client':('client-permissions.d',service+'.service.json'),'api':('api-permissions.d',service+'.api.json')}.items():
            target=base/folder/name;target.parent.mkdir(parents=True,exist_ok=True)
            original='Exec=/usr/bin/run-js-service -n '+str(installed/'usr/palm/services'/service)+'\n' if key=='service' else json.dumps({'appId':service}) if key=='role' else '{}'
            target.write_text(original);entries[str(target)]={'original':original,'installed':original}
        self.runtime.product.write('registration',{'files':entries})
        tx=self.runtime.transaction();tx.update(edition=edition,variant=edition,release='v1.1.0',engineOnly=engine_only or repair,repair=repair,previousGeneration=None)
        self.runtime.store.write('transaction',tx)
        product_io=IO()
        if edition=='root':
            for value in (product_io.current,product_io.candidate):
                value['edition']='root'
                for component,(name,app) in zip(value['components'],(('root','com.cleanyourtv.root.preview'),('root-updater','com.cleanyourtv.root.updater'),('root-infrastructure',None))):
                    component.update(name=name,application=app,kind='infrastructure' if app is None else 'ipk')
        original_offer=product_io.offer
        product_io.offer=lambda edition:dict(original_offer(edition),release=product_io.candidate['release'])
        product_io.integrity=lambda **kw:None;product_io._baseline=lambda edition:product_io.current
        product_io.verify_baseline=lambda baseline:True
        product_io.fetch=lambda method,payload:product_io.candidate
        calls=[]
        def install(app,path,timeout,on_ready,on_accepted):
            calls.append(app);on_ready()
            event=copy.deepcopy(original_terminal['event']);event['details'].update(client='com.webos.lunasend-41',ipkFile='/var/lib/clean-your-tv-installer/cytv-root-install-new/package.ipk')
            event['statusValue']=37;on_accepted(event)
            if unknown_install:raise observed.OutcomeUnknown('connection lost after submission')
            descriptor={'version':'1.0.0' if repair else '1.1.0','sha256':digest(current),'size':len(current)}
            for name,value in concrete.package_files(Path(path).read_bytes(),descriptor).items():
                target=installed/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(value)
            event['statusValue']=30
            return {'completed':True,'event':event}
        interrupted=[]
        def child(code,method,payload):
            result=cli.engine_request(method,payload,self.runtime.product,product_io)
            if crash_handoff and method=='engine-reserve' and not interrupted:
                interrupted.append(True);raise KeyboardInterrupt('power loss after child reservation')
            return result
        factory=concrete.SupervisorIO
        iterdir=Path.iterdir
        def directories(path):return iter(()) if str(path)=='/proc' else iterdir(path)
        def transport(args,**kw):
            self.assertEqual(args[0],'/usr/bin/luna-send')
            return SimpleNamespace(stdout=json.dumps({'returnValue':True,'result':{'id':self.identifier}}).encode())
        contexts=[patch.object(self.bootstrap,'policy',side_effect=lambda method,*args,**kwargs:self.raw if method=='package' else self.catalog),
                  patch.object(self.bootstrap,'Bootstrap',return_value=self.runtime),
                  patch.object(self.runtime,'call',side_effect=child),
                  patch.object(concrete,'SupervisorIO',side_effect=lambda runtime,slot:factory(runtime,slot,installed,base)),
                  patch.object(observed,'install',side_effect=install),patch.object(device_module.Device,'scan_services'),
                  patch.object(Path,'iterdir',directories),patch.object(concrete.subprocess,'run',side_effect=transport),
                  patch.object(self.bootstrap.os,'execv',side_effect=Dispatched)]
        for context in contexts:context.start()
        try:
            if crash_terminal:
                original_stage=self.owner.stage
                def interrupted(record,phase,terminal=False):
                    if terminal:raise KeyboardInterrupt('power loss before terminal lease')
                    return original_stage(record,phase,terminal)
                with patch.object(self.owner,'stage',side_effect=interrupted):
                    with self.assertRaises(KeyboardInterrupt):self.runtime.worker()
                self.assertEqual(self.runtime.transaction()['phase'],'complete')
                self.assertFalse(self.owner.status()['terminal'])
            if unknown_install:
                self.runtime.worker()
                self.assertEqual(self.runtime.transaction()['phase'],'recovery-required')
                self.assertFalse(self.runtime.handle('status',{})['canRollback'])
                self.runtime.handle('reconcile',{});self.runtime.worker()
                self.assertEqual(self.runtime.transaction()['phase'],'recovery-required')
                self.assertEqual(calls,[concrete.APP])
                self.assertIsNone(self.runtime.product.read('transaction'))
                return
            if crash_handoff:
                with self.assertRaises(KeyboardInterrupt):self.runtime.worker()
                self.assertEqual(self.runtime.transaction()['phase'],'handoff')
                self.assertEqual(self.owner.status()['owner'],'system-engine')
            if engine_only or repair:self.runtime.worker()
            else:
                try:self.runtime.worker()
                except Dispatched:pass
            actual=self.runtime.transaction()
            self.assertEqual(actual['phase'],'complete',actual.get('error'))
            self.assertEqual(self.runtime.slots.active().name,'a')
            self.assertEqual(self.runtime.store.read('supervisor-migration')['phase'],'complete')
            self.assertEqual(concrete.generation_inventory(self.runtime.state,os.getuid()),self.runtime.store.read('supervisor-generation')['files'])
            self.assertEqual(calls,[concrete.APP])
            self.assertTrue((self.runtime.state/'engine-state/cache'/(digest(current)+'.ipk')).exists())
            if engine_only or repair:
                self.assertIsNone(self.runtime.product.read('transaction'))
                self.assertTrue(self.owner.status()['terminal'])
            else:
                self.assertEqual(self.runtime.product.read('transaction')['id'],self.identifier)
                self.assertEqual(self.owner.status()['owner'],'system-update')
                self.assertFalse(self.owner.status()['terminal'])
                self.assertEqual(self.runtime.product.read('profile-'+self.identifier),profile())
                manager = cli.Manager(self.runtime.product, product_io)

                def advance(expected):
                    for _ in range(40):
                        state = manager.run()
                        if state['phase'] == expected:
                            return
                    self.fail(state)

                advance('verifying')
                self.assertEqual(manager.restore_profile(edition)['profile'], profile())
                manager.healthy(edition, self.identifier, '1.1.0')
                advance('complete')
                self.assertTrue(manager.status()['canRollback'])
                manager.rollback()
                advance('verifying-rollback')
                self.assertEqual(manager.restore_profile(edition)['profile'], profile())
                manager.healthy(edition, self.identifier, '1.0.0')
                advance('rolled-back')
                self.assertTrue(all(c['version'] == '1.0.0' for c in product_io.current['components']))
                self.assertEqual(self.runtime.slots.active().name, 'a')
                self.assertEqual(calls, [concrete.APP])
        finally:
            for context in reversed(contexts):context.stop()
    def test_no_root_update_all_hands_off_same_owner_after_self_update(self):self.execute()
    def test_root_update_all_hands_off_same_owner_after_self_update(self):self.execute('root')
    def test_engine_only_release_finishes_without_product_installer(self):self.execute(engine_only=True)
    def test_explicit_repair_reinstalls_same_signed_own_package(self):self.execute(repair=True)
    def test_root_repair_reinstalls_same_signed_own_package(self):self.execute('root', repair=True)
    def test_interrupted_handoff_resumes_exact_child_without_reinstalling_supervisor(self):self.execute(crash_handoff=True)
    def test_unknown_supervisor_installer_result_is_never_replayed(self):self.execute(unknown_install=True)
    def test_completed_engine_journal_closes_original_lease_after_power_loss(self):self.execute(engine_only=True,crash_terminal=True)
