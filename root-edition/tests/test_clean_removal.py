import os
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from installation import Ownership, Busy
from updater.store import Store
from install_driver import Coordinator


class Device:
    def __init__(self): self.calls = []; self.fail = None
    def clean_remove(self, record, save):
        for stage in ('original-writers-fenced', 'controls-restored', 'package-removal', 'private-cleanup'):
            if stage not in record['done']:
                save(stage)
                self.calls.append(stage)
                if stage == self.fail: raise OSError('PRIVATE')
                record['done'].append(stage)
                save(stage)
        return {'removed':True, 'applications_services_startup_removed':True, 'private_cleanup_verified':True}
    def verify_clean(self, record): self.calls.append('verify'); return True


class CoordinatorCleanRemoval(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.owner = Ownership(Store(Path(self.tmp.name).resolve()/'installation', uid=os.getuid()))
        self.device = Device(); self.id = 'a'*32
        self.driver = Coordinator(self.device, self.owner, read=lambda path:None)

    def original(self):
        with self.owner.operation('product', 'product-'+self.id+'.json') as lease:
            self.owner.stage(lease, 'root-updater')
            original = dict(operation=self.id, action='install', stage='root-updater', state='recovery_required',
                            lease=lease['id'], candidate_sha256='b'*64, failure={'exit_status':127})
            self.owner.store.write('request-'+self.id, original)
        return original

    def test_partial_install_uses_original_lease_and_preserves_first_failure(self):
        original = self.original()
        result = self.driver.clean_remove(self.id)
        self.assertEqual(result['stage'], 'verified-clean')
        self.assertEqual(result['original']['request'], original)
        self.assertEqual(result['lease'], original['lease'])
        self.assertEqual(self.owner.store.read('request-'+self.id), original)
        with self.assertRaises(Busy):
            with self.owner.operation('product', 'product-'+self.id+'.json', resume=original['lease']): pass

    def test_before_first_lease_late_original_worker_cannot_acquire(self):
        result = self.driver.clean_remove(self.id)
        with self.assertRaises(Busy):
            with self.owner.operation('product', 'product-'+self.id+'.json'): pass
        self.assertEqual(result['original']['request'], None)

    def test_private_cleanup_interruption_resumes_without_package_replay(self):
        self.original(); self.device.fail = 'private-cleanup'
        first = self.driver.clean_remove(self.id)
        self.assertEqual(first['stage'], 'private-cleanup')
        self.assertEqual(first['reason'], 'private-cleanup-incomplete')
        self.device.fail = None
        result = self.driver.clean_remove(self.id)
        self.assertEqual(result['stage'], 'verified-clean')
        self.assertEqual(self.device.calls.count('package-removal'), 1)
        self.driver.clean_remove(self.id)
        self.assertEqual(self.device.calls.count('package-removal'), 1)

    def test_other_live_ownership_lock_blocks_before_any_effect(self):
        self.original()
        with self.owner.operation('product', 'product-'+self.id+'.json', resume=self.owner.status()['id']):
            with self.assertRaises(Busy): self.driver.clean_remove(self.id)
        self.assertEqual(self.device.calls, [])

    def test_verified_removal_fresh_install_then_new_removal_keeps_old_fence(self):
        first=self.driver.clean_remove(self.id)
        new='b'*32
        self.device.prepare_clean_install=lambda record:self.device.calls.append('handoff')
        result=self.driver._run(new,'install',lambda checkpoint:{'verified':True})
        self.assertEqual(result['state'],'complete')
        self.assertNotEqual(result['lease'],first['lease'])
        self.assertEqual(self.device.calls.count('handoff'),1)
        before=list(self.device.calls)
        old=self.driver._run(self.id,'install',lambda checkpoint:self.fail('old worker executed'))
        self.assertEqual(old['code'],'clean_removal_requested')
        self.assertEqual(self.device.calls,before)
        second=self.driver.clean_remove(new)
        self.assertEqual(second['stage'],'verified-clean')
        self.assertNotEqual(second['lease'],first['lease'])

    def test_pending_removal_cannot_handoff_to_new_install(self):
        self.device.fail='private-cleanup';self.driver.clean_remove(self.id)
        with self.assertRaises(Busy):self.driver._run('b'*32,'install',lambda checkpoint:self.fail('executed'))

    def test_parent_never_rewrites_receipt_after_tail_retirement_started(self):
        def tail(record):
            self.device.cleanup_tail_started=True
            final=dict(record,stage='verified-clean',state='complete',current=True)
            self.owner.store.write('clean-removal-'+self.id,final)
            raise OSError('parent interpreter stopped reading its retired runtime')
        self.device.finish_clean_tail=tail
        reply=self.driver.clean_remove(self.id)
        self.assertFalse(reply['current'])
        persisted=self.owner.store.read('clean-removal-'+self.id)
        self.assertEqual(persisted['stage'],'verified-clean')
        self.assertTrue(persisted['current'])

    def test_final_tv_audit_keeps_first_failure_and_hashes_without_private_nested_data(self):
        original=self.original()
        original.update(config={'ssap':'PRIVATE_SECRET'},raw_error='PRIVATE_SECRET')
        self.owner.store.write('request-'+self.id,original)
        self.driver.read=lambda path:{'phase':'recovery-required','error':'PRIVATE_SECRET','profile':{'key':'PRIVATE_SECRET'}}
        result=self.driver.clean_remove(self.id)
        self.assertEqual(result['stage'],'verified-clean')
        self.assertTrue(result['audit_compacted'])
        self.assertNotIn('PRIVATE_SECRET',str(result))
        self.assertEqual(result['original']['request']['failure'],{'exit_status':127})
        self.assertEqual(len(result['original_digests']['request']),64)
        self.assertNotIn('PRIVATE_SECRET',str(self.owner.store.read('request-'+self.id)))


class ConfinedCleanup(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()/'owned';self.root.mkdir(mode=0o700)

    def test_changed_owned_preferences_are_deleted_but_lock_inode_stays(self):
        from clean_removal import retire_tree
        (self.root/'state').mkdir();(self.root/'state/key.json').write_text('changed private key')
        (self.root/'provision.lock').touch();inode=(self.root/'provision.lock').stat().st_ino
        self.assertEqual(retire_tree(self.root,{'state'},{'provision.lock'},os.getuid()),2)
        self.assertEqual((self.root/'provision.lock').stat().st_ino,inode)
        self.assertEqual(retire_tree(self.root,{'state'},{'provision.lock'},os.getuid()),0)

    def test_symlink_and_unclassified_data_prevent_all_deletions(self):
        from clean_removal import retire_tree
        foreign=self.root.parent/'foreign';foreign.write_text('keep')
        (self.root/'config.json').write_text('private')
        (self.root/'code').symlink_to(foreign)
        retire_tree(self.root,{'config.json','code'},uid=os.getuid())
        self.assertFalse((self.root/'code').exists());self.assertEqual(foreign.read_text(),'keep')
        (self.root/'config.json').write_text('private')
        (self.root/'unknown').write_text('do not classify by prefix')
        with self.assertRaises(ValueError):retire_tree(self.root,{'config.json'},uid=os.getuid())
        self.assertTrue((self.root/'config.json').exists())

    def test_interrupted_cleanup_never_recreates_deleted_private_bytes(self):
        from clean_removal import retire_tree
        for name in ('key.json','code.py'):(self.root/name).write_text('private')
        real=os.unlink;calls=[]
        def interrupted(name,**kwargs):
            calls.append(name)
            if name=='key.json':raise OSError('storage failure')
            return real(name,**kwargs)
        with patch('clean_removal.os.unlink',side_effect=interrupted):
            with self.assertRaises(OSError):retire_tree(self.root,{'key.json','code.py'},uid=os.getuid())
        self.assertEqual(calls,['code.py','key.json']);self.assertFalse((self.root/'code.py').exists())
        self.assertEqual(retire_tree(self.root,{'key.json','code.py'},uid=os.getuid()),1)

    def test_partial_registration_restore_checks_foreign_bytes_before_any_write(self):
        import clean_removal
        base=self.root.parent/'bus';app='com.cleanyourtv.root.updater';files={}
        for folder,suffix in (('services.d','.service'),('roles.d','.service.json'),('client-permissions.d','.service.json'),('api-permissions.d','.api.json')):
            (base/folder).mkdir(parents=True)
            path=base/folder/(app+'.service'+suffix);path.write_text('installed')
            files[str(path)]={'original':'original','installed':'installed'}
        Store(self.root,uid=os.getuid()).write('registration',{'files':files})
        victim=Path(sorted(files)[-1]);victim.write_text('foreign')
        with self.assertRaisesRegex(ValueError,'ownership_conflict'):
            clean_removal.restore_registrations(self.root,app,base,os.getuid())
        self.assertEqual(victim.read_text(),'foreign')
        self.assertTrue(all(Path(name).read_text()=='installed' for name in files if name!=str(victim)))
        victim.write_text('original')
        clean_removal.restore_registrations(self.root,app,base,os.getuid())
        self.assertTrue(all(Path(name).read_text()=='original' for name in files))

    def test_current_native_restore_selects_only_verified_new_bundle_executable(self):
        import hashlib
        import clean_removal
        from unittest.mock import Mock
        payload=self.root/'bundle';(payload/'runtime').mkdir(parents=True)
        native=payload/'runtime/c1-home-gate';native.write_bytes(b'current native');native.chmod(0o600)
        backend=Mock();backend.STATE=self.root/'old';backend.selection.return_value={'routing':'mount-v1','native_sha256':'0'*64}
        cli=Mock();cli.gate_backend.return_value=backend
        def restore(mode):
            self.assertEqual(mode,'restore');self.assertEqual(backend.binary(backend.STATE,os.getuid()),native)
            return 'restored'
        cli.main.side_effect=restore
        with patch.dict(sys.modules,{'cli':cli}),patch('deploy.verify_bundle',return_value={'files':{'runtime/c1-home-gate':hashlib.sha256(native.read_bytes()).hexdigest()}}),patch('deploy.checked_file',return_value=native.read_bytes()):
            before=list(sys.path)
            try:self.assertEqual(clean_removal.runtime_restore(payload,os.getuid())['result'],'restored')
            finally:sys.path[:]=before
        self.assertEqual(native.stat().st_mode&0o777,0o700)


class PackageRemoval(unittest.TestCase):
    def test_old_unknown_is_separate_from_new_remove_terminal(self):
        import clean_removal
        from unittest.mock import Mock
        app=clean_removal.APPS[0];present={app};calls=[]
        device=Mock();device.apps.side_effect=lambda:set(present)
        def absent(identity,terminal=None):self.assertNotIn(identity,present)
        device.absent.side_effect=absent
        def remove(identity,timeout):
            calls.append(identity);present.remove(identity)
            return {'completed':True,'event':{'id':identity,'details':{'packageId':identity,'state':'removed'}}}
        record={'packages':{},'original':{'outcome':'unknown'}}
        with patch('observed_install.remove',side_effect=remove):
            clean_removal.remove_packages(device,record,lambda stage:None,lambda app:True)
            clean_removal.remove_packages(device,record,lambda stage:None,lambda app:True)
        self.assertEqual(calls,[app]);self.assertEqual(record['original']['outcome'],'unknown')

    def test_retry_skips_absent_package_after_connection_loss(self):
        import clean_removal
        from unittest.mock import Mock
        app=clean_removal.APPS[0];device=Mock();device.apps.return_value={app}
        record={'packages':{}}
        with patch('observed_install.remove',side_effect=OSError('lost')) as remove:
            with self.assertRaises(OSError):clean_removal.remove_packages(device,record,lambda stage:None,lambda app:True)
            device.apps.return_value=set()
            clean_removal.remove_packages(device,record,lambda stage:None,lambda app:True)
        self.assertEqual(remove.call_count,1)


class PartialDeviceRemoval(unittest.TestCase):
    def fixture(self, unknown=False, missing_profiles=False):
        import install_device, clean_removal, deploy, startup_hook
        from contextlib import ExitStack
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        base=Path(tmp.name).resolve();root=base/'root';root.mkdir(mode=0o700)
        updater=base/'root-updater';updater.mkdir(mode=0o700)
        supervisor=base/'system';installed=base/'apps';bus=base/'bus';bus.mkdir()
        init=base/'init';init.mkdir();proc=base/'proc';proc.mkdir()
        payload=base/'support';(payload/'root/runtime').mkdir(parents=True);(payload/'root-updater').mkdir()
        (payload/'root/runtime/cli.py').write_text('current source')
        (payload/'root-updater/bundle.json').write_text('{"files":{"install_driver.py":"fixture","package.json":"fixture","services.json":"fixture"}}')
        (root/'state').mkdir();(root/'state/ssap.json').write_text('changed key')
        (root/'runtime').mkdir();(root/'runtime/cli.py').write_text('old executable')
        (root/'updater').mkdir();(root/'updater/store.py').write_text('old support')
        (updater/'code').mkdir();(updater/'code/run-updater.py').write_text('old executable')
        Store(root,uid=os.getuid()).write('deploy',{'version':1,'app':install_device.APP,'stage':'install-submitting' if unknown else 'install-observed'})
        Store(updater,uid=os.getuid()).write('bootstrap',{'phase':'prepared'})
        present={install_device.APP};calls=[]
        class Model(install_device.LocalDevice):
            def rpc(self,method,data):
                calls.append(method)
                if method.endswith('/status'):return {'returnValue':True,'status':{'apps':[]}}
                if method=='com.palm.activitymanager/list':return {'returnValue':True,'activities':[]}
                if method.endswith('/getAllInputStatus'):return {'returnValue':True,'devices':[]}
                if method.endswith('/getSystemSettings'):return {'returnValue':True,'settings':{'defaultApps':{'home':'third.party.home'}}}
                if method.endswith('/getProfiles'):
                    if missing_profiles:return {'returnValue':False,'errorCode':-1}
                    return {'returnValue':True,'profiles':{'defaultApps':{'categories':{'home':'third.party.home'}},'idleApp':{'appId':'third.party.home'}}}
                raise AssertionError(method)
            def apps(self):return set(present)
            def cleanup(self,name,*args):calls.append('cleanup-'+name);return True
        device=Model();device.payload=payload
        device.shared_cleanup=lambda action,record,**kwargs:{'schema':1,'present':[],'blocked':[],'root_present':[]}
        device.current_boot="11111111-1111-1111-1111-111111111111"
        device.boot_id=lambda:device.current_boot
        owner=Ownership(Store(base/'installation',uid=os.getuid()))
        identifier='c'*32
        with owner.operation('product','product-'+identifier+'.json') as lease:
            original={'operation':identifier,'action':'install','stage':'root-deploy','state':'recovery_required','lease':lease['id']}
            owner.store.write('request-'+identifier,original)
        stack=ExitStack();self.addCleanup(stack.close)
        # Discovery also loads runtime/provision.py under the same short name.
        # Production runs coordinator support in its own interpreter; bind that
        # actual source only for this fixture, restoring the runtime module after.
        spec=importlib.util.spec_from_file_location('coordinator_provision_fixture',Path(__file__).resolve().parents[1]/'provision.py')
        provision=importlib.util.module_from_spec(spec);spec.loader.exec_module(provision)
        stack.enter_context(patch.dict(sys.modules,{'provision':provision}))
        temporary=base/'tmp';temporary.mkdir()
        for key,value in {'ROOT':root,'UPDATER':updater,'SUPERVISOR':supervisor,'INSTALLED':installed,'BUS':bus,'INIT':init,'PROC':proc,'TEMP':temporary}.items():stack.enter_context(patch.object(install_device,key,value))
        from installation import _optional_record
        stack.enter_context(patch.object(install_device,'read_journal',side_effect=lambda p:_optional_record(install_device.checked_store(p.parent,os.getuid()),p.name)))
        stack.enter_context(patch.object(startup_hook,'STATE',root));stack.enter_context(patch.object(startup_hook,'HOOK',init/'50-clean-your-tv-root'))
        def current_restore(args):
            calls.append('current-restore');self.assertEqual(args[1:4],['-I','-B','-c'])
            self.assertIn(repr(str(payload/'root-updater')),args[4])
            self.assertIn(repr(str(payload/'root')),args[4])
            return {'returnValue':True,'result':'absent'}
        stack.enter_context(patch.object(deploy,'command',side_effect=current_restore))
        def remove(app,timeout):
            calls.append('remove-'+app);present.remove(app)
            return {'completed':True,'event':{'details':{'state':'removed'}}}
        stack.enter_context(patch('observed_install.remove',side_effect=remove))
        def read(path):
            actual={'deploy':root/'deploy.json','root-bootstrap':updater/'bootstrap.json'}
            import installation
            key=next(k for k,(known,_,_) in installation.JOURNALS.items() if known==path)
            p=actual.get(key)
            return json.loads(p.read_text()) if p and p.exists() else None
        import json
        return Coordinator(device,owner,read),identifier,root,updater,payload,calls,present

    def test_real_partial_trees_clean_without_finishing_install_or_changing_foreign_home(self):
        driver,identifier,root,updater,payload,calls,present=self.fixture()
        self.assertEqual(driver.clean_remove(identifier)['stage'],'restart-required')
        driver.device.current_boot='22222222-2222-2222-2222-222222222222'
        result=driver.clean_remove(identifier)
        self.assertEqual(result['stage'],'verified-clean',result)
        self.assertEqual(set(p.name for p in root.iterdir()),{'deploy.json','provision.lock'})
        self.assertEqual(set(p.name for p in updater.iterdir()),{'bootstrap.json','daemon.lock','worker.lock'})
        self.assertEqual(list(payload.iterdir()),[])
        self.assertEqual(calls.count('remove-com.cleanyourtv.root.preview'),1)
        self.assertLess(calls.index('current-restore'),calls.index('remove-com.cleanyourtv.root.preview'))
        self.assertFalse(any('setDefault' in name or 'launch' in name for name in calls))
        driver.device.payload=None
        self.assertEqual(driver.clean_remove(identifier)['stage'],'verified-clean')
        self.assertEqual(calls.count('remove-com.cleanyourtv.root.preview'),1)

    def test_unknown_old_outcome_does_not_prevent_owned_file_cleanup(self):
        driver,identifier,root,updater,payload,calls,present=self.fixture(unknown=True)
        present.clear()
        result=driver.clean_remove(identifier)
        self.assertEqual(result['stage'],'restart-required')
        self.assertEqual(result['state'],'recovery_required')
        self.assertFalse((root/'state/ssap.json').exists())
        self.assertFalse(any(name.startswith('remove-') for name in calls))

    def test_stale_submitted_receipt_does_not_prevent_retry_cleanup(self):
        driver,identifier,root,updater,payload,calls,present=self.fixture()
        from unittest.mock import patch
        with patch.object(driver.device,'retire_clean_private',side_effect=OSError('interrupted')):
            first=driver.clean_remove(identifier)
        self.assertIn('package-removal',first['done'])
        first['packages']['com.cleanyourtv.root.preview']={'state':'submitted'}
        driver.store.write('clean-removal-'+identifier,first)
        result=driver.clean_remove(identifier)
        self.assertEqual(result['state'],'recovery_required')
        self.assertEqual(result['stage'],'restart-required')
        self.assertFalse((root/'state/ssap.json').exists())
        self.assertEqual(calls.count('remove-com.cleanyourtv.root.preview'),1)

    def test_live_owner_inverse_records_preserved_without_product_secrets(self):
        driver,identifier,root,updater,payload,calls,present=self.fixture()
        (root/'system-permissions.json').write_text('{"original":"foreign permission"}')
        (updater/'registration.json').write_text('{"original":"foreign registration"}')
        driver.device.ownership=driver.ownership
        driver.device.preserve_routing_inverse({'operation':identifier})
        saved=driver.ownership.store.read('routing-backup-'+identifier)
        self.assertIn('system-permissions.json',saved)
        self.assertIn('root-updater/registration.json',saved)
        self.assertNotIn('ssap',str(saved))

    def test_helper_missing_from_sam_with_live_process_requires_full_boot(self):
        import install_device
        driver,identifier,root,updater,payload,calls,present=self.fixture()
        process=install_device.PROC/'12345';process.mkdir()
        (process/'cmdline').write_bytes(str(install_device.INSTALLED/'usr/palm/applications/com.local.nativehome/relay').encode()+b'\0')
        result=driver.clean_remove(identifier)
        self.assertEqual(result['stage'],'restart-required')
        self.assertFalse(result['current'])
        self.assertTrue((root/'state/ssap.json').exists())
        self.assertTrue(any(name.startswith('remove-') for name in calls))

    def test_fresh_install_moves_minimal_fences_without_replacing_lock_inodes(self):
        driver,identifier,root,updater,payload,calls,present=self.fixture()
        self.assertEqual(driver.clean_remove(identifier)['stage'],'restart-required')
        driver.device.current_boot='22222222-2222-2222-2222-222222222222'
        first=driver.clean_remove(identifier);self.assertEqual(first['stage'],'verified-clean')
        inodes={path:path.stat().st_ino for path in (root/'provision.lock',updater/'worker.lock')}
        original=driver.owner if hasattr(driver,'owner') else driver.ownership
        before=original.store.read('request-'+identifier)
        second=driver._run('d'*32,'install',lambda checkpoint:{'verified':True})
        self.assertEqual(second['state'],'complete',second)
        self.assertFalse(root.exists());self.assertFalse(updater.exists())
        archived=Path(original.store.root)/('component-fences-'+identifier)
        for path,inode in inodes.items():self.assertEqual((archived/path.parent.name/path.name).stat().st_ino,inode)
        self.assertEqual(original.store.read('request-'+identifier),before)

    def test_never_activated_partial_can_clean_when_profile_interface_unavailable(self):
        driver,identifier,root,updater,payload,calls,present=self.fixture(missing_profiles=True)
        self.assertEqual(driver.clean_remove(identifier)['stage'],'restart-required')
        driver.device.current_boot='22222222-2222-2222-2222-222222222222'
        result=driver.clean_remove(identifier)
        self.assertEqual(result['stage'],'verified-clean',result)
        self.assertEqual(result['routes'],{'mode':'never-applied','home':'third.party.home'})
        self.assertTrue(result['routing_never_applied'])
        self.assertFalse(any('setSystem' in name or 'setProfiles' in name for name in calls))

    def test_possible_old_activation_cannot_claim_missing_profile_interface_is_clean(self):
        driver,identifier,root,updater,payload,calls,present=self.fixture(missing_profiles=True)
        Store(root,uid=os.getuid()).write('deploy',{'version':1,'app':'com.cleanyourtv.root.preview','stage':'installed-recovery-only'})
        result=driver.clean_remove(identifier)
        self.assertEqual(result['stage'],'original-writers-fenced')
        self.assertFalse(result['routing_never_applied'])
        self.assertTrue((root/'state/ssap.json').exists())
        self.assertFalse(any(name.startswith('remove-') for name in calls))


if __name__ == '__main__': unittest.main()
