"""Practical full removal: present components, reboot, fresh readback."""
import os
from pathlib import Path
import tempfile
import json
import hashlib
import subprocess
import sys
import unittest
from unittest.mock import patch, Mock

import test_clean_removal
from clean_removal import APPS, remove_packages, retire_tree


class SimpleRemoval(unittest.TestCase):
    fixture = test_clean_removal.PartialDeviceRemoval.fixture

    def prepare(self, **kwargs):
        fixture=self.fixture(**kwargs)
        self.boot='11111111-1111-1111-1111-111111111111'
        fixture[0].device.boot_id=lambda:self.boot+':session-'+self.boot[0]*32
        return fixture

    def restage(self,driver,payload):
        # Normal host dispatch uploads current support for each new goal; the
        # previous full removal deliberately retired this model's old copy.
        (payload/'root/runtime').mkdir(parents=True,exist_ok=True)
        (payload/'root/runtime/cli.py').write_text('current source')
        (payload/'root-updater').mkdir(exist_ok=True)
        (payload/'root-updater/bundle.json').write_text('{"files":{"install_driver.py":"fixture","package.json":"fixture","services.json":"fixture"}}')
        driver.device.payload=payload

    def test_partial_removal_requires_boot_and_completed_goal_cannot_sweep_new_residue(self):
        driver,identifier,root,updater,payload,calls,present=self.prepare()
        first=driver.clean_remove(identifier)
        self.assertEqual(first['stage'],'restart-required',first)
        self.assertFalse(first['result']['removed'])
        self.assertTrue(first['result']['restart_required'])
        self.assertEqual(driver.clean_remove(identifier)['stage'],'restart-required')
        self.boot='22222222-2222-2222-2222-222222222222'
        final=driver.clean_remove(identifier)
        self.assertEqual(final['stage'],'verified-clean',final)
        self.assertEqual(calls.count('remove-'+APPS[0]),1)
        self.assertFalse((root/'state/ssap.json').exists())
        driver.device.payload=None
        (root/'state').mkdir();(root/'state/ssap.json').write_text('reappeared at boot')
        with self.assertRaisesRegex(ValueError,'private_members_remain'):
            driver.clean_remove(identifier)
        self.assertTrue((root/'state/ssap.json').exists())
        self.restage(driver,payload)
        target=driver.removal_target('e'*32)
        new=driver.clean_remove(target['target_operation'],intent='e'*32,expected_lease=target['target_lease'])
        self.assertEqual(new['stage'],'restart-required',new)
        self.boot='33333333-3333-3333-3333-333333333333'
        self.assertEqual(driver.clean_remove('e'*32,intent='e'*32)['stage'],'verified-clean')
        self.assertFalse((root/'state/ssap.json').exists())
        self.assertEqual(calls.count('remove-'+APPS[0]),1)

    def test_unknown_old_install_does_not_block_owned_residue_cleanup(self):
        driver,identifier,root,updater,payload,calls,present=self.prepare(unknown=True)
        present.clear()
        first=driver.clean_remove(identifier)
        self.assertEqual(first['stage'],'restart-required',first)
        self.assertFalse((root/'state/ssap.json').exists())
        self.boot='22222222-2222-2222-2222-222222222222'
        self.assertEqual(driver.clean_remove(identifier)['stage'],'verified-clean')
        self.assertFalse(any(name.startswith('remove-') for name in calls))

    def test_retry_uses_current_presence_not_stale_submitted_json(self):
        device=Mock();device.apps.return_value=set()
        record={'packages':{APPS[0]:{'state':'submitted'}}}
        with patch('observed_install.remove') as remove:
            remove_packages(device,record,lambda stage:None)
        remove.assert_not_called()
        self.assertEqual(record['packages'][APPS[0]]['state'],'absent')

    def test_missing_paths_and_owned_symlink_do_not_touch_foreign_target(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp).resolve();root=base/'owned';root.mkdir(mode=0o700)
            foreign=base/'foreign';foreign.write_text('keep')
            (root/'state').symlink_to(foreign)
            self.assertEqual(retire_tree(root,{'state'},uid=os.getuid()),1)
            self.assertEqual(foreign.read_text(),'keep')
            self.assertEqual(retire_tree(base/'absent',{'state'},uid=os.getuid()),0)

    def test_vendor_error_still_cleans_unregistered_owned_residues(self):
        driver,identifier,root,updater,payload,calls,present=self.prepare()
        with patch('observed_install.remove',side_effect=RuntimeError('vendor_busy')):
            first=driver.clean_remove(identifier)
        self.assertEqual(first['state'],'recovery_required')
        self.assertFalse((root/'state/ssap.json').exists())
        self.assertNotEqual(first['stage'],'verified-clean')
        self.assertTrue((payload/'root-updater/bundle.json').exists())
        self.assertEqual(driver.clean_remove(identifier)['stage'],'restart-required')
        self.boot='22222222-2222-2222-2222-222222222222'
        self.assertEqual(driver.clean_remove(identifier)['stage'],'verified-clean')

    def test_stale_other_product_selector_does_not_block_explicit_removal(self):
        driver,identifier,root,updater,payload,calls,present=self.prepare()
        target=driver.removal_target('e'*32)
        self.assertEqual(target['target_operation'],identifier)
        result=driver.clean_remove(target['target_operation'],intent='e'*32,expected_lease=target['target_lease'])
        self.assertEqual(result['stage'],'restart-required',result)
        self.assertEqual(result['original']['operation'],identifier)

    def test_current_target_change_is_rejected_before_effects(self):
        from installation import Busy
        driver,identifier,root,updater,payload,calls,present=self.prepare()
        target=driver.removal_target('e'*32)
        changed=driver.ownership.status();changed['id']='f'*32
        driver.store.write('operation',changed)
        with self.assertRaises(Busy):
            driver.clean_remove(target['target_operation'],intent='e'*32,expected_lease=target['target_lease'])
        self.assertEqual(calls,[])

    def test_fresh_explicit_remove_selects_new_goal_without_replacing_history(self):
        driver,identifier,root,updater,payload,calls,present=self.prepare()
        driver.clean_remove(identifier,intent='d'*32)
        self.boot='22222222-2222-2222-2222-222222222222'
        completed=driver.clean_remove(identifier,intent='d'*32)
        self.restage(driver,payload)
        target=driver.removal_target('e'*32)
        self.assertEqual(target['target_operation'],'e'*32)
        self.assertIsNone(target['target_removal'])
        result=driver.clean_remove(target['target_operation'],intent='e'*32,expected_lease=target['target_lease'])
        self.assertEqual(result['stage'],'restart-required',result)
        self.boot='33333333-3333-3333-3333-333333333333'
        result=driver.clean_remove('e'*32,intent='e'*32)
        self.assertEqual(result['state'],'complete')
        self.assertEqual(driver.store.read('clean-removal-'+identifier),completed)

    def test_current_removal_goal_drift_is_rejected_under_original_lock(self):
        from installation import Busy
        driver,identifier,root,updater,payload,calls,present=self.prepare()
        driver.clean_remove(identifier,intent='d'*32)
        target=driver.removal_target('e'*32)
        record=driver.store.read('clean-removal-'+identifier);record['removal']='f'*32
        driver.store.write('clean-removal-'+identifier,record)
        before=list(calls)
        with self.assertRaises(Busy):driver.clean_remove(identifier,intent=target['target_removal'],expected_lease=target['target_lease'])
        self.assertEqual(calls,before)

    def test_missing_sam_entry_still_removes_owned_activity_and_input(self):
        driver,identifier,root,updater,payload,calls,present=self.prepare()
        rpc=driver.device.rpc;remaining={'input':True,'activity':True}
        foreign={'name':'foreign.job','activityId':8,'callback':{'method':'luna://org.foreign/tick'}}
        def actual(method,data):
            if method.endswith('/getAllInputStatus'):
                return {'returnValue':True,'devices':[{'appId':'com.gathin.tvhome'}] if remaining['input'] else []}
            if method.endswith('/deleteDevice'):remaining['input']=False;return {'returnValue':True}
            if method=='com.palm.activitymanager/list':
                return {'returnValue':True,'activities':[foreign]+([{'name':'com.local.nativehome.boot','activityId':7,
                    'callback':{'method':'luna://com.local.nativehome.service/tick'}}] if remaining['activity'] else [])}
            if method=='com.palm.activitymanager/cancel':
                self.assertEqual(data,{'activityId':7});remaining['activity']=False;return {'returnValue':True}
            return rpc(method,data)
        driver.device.rpc=actual
        driver.clean_remove(identifier)
        self.assertFalse(remaining['input']);self.assertFalse(remaining['activity'])

    def test_known_partial_archive_does_not_require_old_success_phase(self):
        from updater.store import Store
        driver,identifier,root,updater,payload,calls,present=self.prepare()
        archive=root.parent/(root.name+'.archive-'+'a'*32)
        Store(archive,uid=os.getuid()).write('deploy',{'app':APPS[0],'stage':'install-submitting'})
        (archive/'state').mkdir();(archive/'state/key.json').write_text('old private key')
        result=driver.clean_remove(identifier)
        self.assertEqual(result['stage'],'restart-required',result)
        self.assertFalse(archive.exists())

    def test_partial_updater_archive_preserves_owner_inverse_without_success_phase(self):
        from updater.store import Store
        driver,identifier,root,updater,payload,calls,present=self.prepare()
        archive=updater.parent/(updater.name+'.archive-'+'a'*32)
        store=Store(archive,uid=os.getuid())
        store.write('cytv-removal',{'archive':str(archive),'phase':'disabling'})
        inverse={'original':{'appId':'third.party.home'}}
        store.write('registration',inverse)
        (archive/'code').mkdir();(archive/'code/private-key').write_text('remove private bytes')
        result=driver.clean_remove(identifier)
        self.assertEqual(result['stage'],'restart-required',result)
        self.assertFalse(archive.exists())
        backup=driver.store.read('archive-backup-'+identifier+'-0')
        self.assertEqual(backup,{'registration':inverse})

    def test_foreign_archive_is_preserved_with_explicit_failure(self):
        from updater.store import Store
        driver,identifier,root,updater,payload,calls,present=self.prepare()
        archive=root.parent/(root.name+'.archive-'+'a'*32)
        Store(archive,uid=os.getuid()).write('deploy',{'app':'org.foreign.app','stage':'uninstalled-state-retained'})
        foreign=archive/'config.json';foreign.write_text('keep')
        result=driver.clean_remove(identifier)
        self.assertEqual(result['state'],'recovery_required',result)
        self.assertNotEqual(result['stage'],'verified-clean')
        self.assertEqual(foreign.read_text(),'keep')

    def test_live_published_controller_moves_restart_before_package_or_file_deletion(self):
        driver,identifier,root,updater,payload,calls,present=self.prepare()
        running=True
        def shared(action,record,**kwargs):
            return {'schema':1,'present':[],'blocked':[],'root_present':[],
                    'controller_running':running if action=='stop' else False}
        driver.device.shared_cleanup=shared
        first=driver.clean_remove(identifier)
        self.assertEqual(first['stage'],'restart-required',first)
        self.assertEqual(calls.count('remove-'+APPS[0]),0)
        self.assertTrue((root/'state/ssap.json').exists())
        name='clean-removal-'+identifier;record=driver.ownership.store.read(name)
        record['cleanup_verified_boot_id']='11111111-1111-1111-1111-111111111111:session-'+'b'*32
        driver.ownership.store.write(name,record)
        self.boot='22222222-2222-2222-2222-222222222222'
        self.assertEqual(driver.clean_remove(identifier)['stage'],'restart-required')
        self.assertNotIn('cleanup_verified_boot_id',driver.ownership.store.read(name))
        self.assertEqual(calls.count('remove-'+APPS[0]),0)
        running=False
        self.assertEqual(driver.clean_remove(identifier)['stage'],'restart-required')
        self.boot='33333333-3333-3333-3333-333333333333'
        self.assertEqual(driver.clean_remove(identifier)['stage'],'verified-clean')

    def test_held_original_lock_blocks_other_selector_before_effects(self):
        from installation import Busy
        driver,identifier,root,updater,payload,calls,present=self.prepare()
        lease=driver.ownership.status()
        target=driver.removal_target('e'*32)
        with driver.ownership.operation('product','product-'+identifier+'.json',resume=lease['id']):
            with self.assertRaises(Busy):driver.clean_remove(target['target_operation'],intent='e'*32,expected_lease=target['target_lease'])
        self.assertEqual(calls,[])

    def test_expected_empty_ownership_does_not_adopt_new_operation(self):
        from installation import Busy
        driver,identifier,root,updater,payload,calls,present=self.prepare()
        with self.assertRaises(Busy):driver.clean_remove(identifier,expected_lease='-')
        self.assertEqual(calls,[])

    def test_busy_worker_lock_reports_immediately(self):
        from updater.store import Store
        driver,identifier,root,updater,payload,calls,present=self.prepare()
        other=Store(driver.store.root,uid=os.getuid())
        with other.lock():
            with self.assertRaises(BlockingIOError):
                with driver.store.lock(blocking=False):self.fail('acquired active worker')

    def test_shared_private_cleanup_restarts_before_old_resident_and_cleans_after_boot(self):
        from cytv.no_root_cleanup import PRIVATE_CLEANUP_PROGRAM
        driver,identifier,root,updater,payload,calls,present=self.prepare()
        base=root.parent
        for name in ('developer','bus-private','varlib','profiles'):(base/name).mkdir()
        private=base/'developer/.cytv-installer/operations'/('a'*32)
        private.mkdir(parents=True);(private/'unknown.json').write_text('{"old":"unknown"}')
        source=PRIVATE_CLEANUP_PROGRAM.replace('/media/developer',str(base/'developer')).replace('/var/luna-service2-dev',str(base/'bus-private'))
        source=source.replace('/var/lib',str(base/'varlib')).replace('/var/webos-profile',str(base/'profiles')).replace('/proc/sys/kernel/random/boot_id',str(base/'boot'))
        # macOS fixture keeps its actual filesystem UID; Linux runs the real UID0 gate.
        if os.getuid()!=0:source=source.replace('if(uid!==0||','if(false||')
        script=payload/'root-updater/cleanup_no_root_private.js';script.write_text(source)
        manifest=payload/'root-updater/bundle.json';value=json.loads(manifest.read_text());value['files'][script.name]=hashlib.sha256(script.read_bytes()).hexdigest();manifest.write_text(json.dumps(value))
        if 'shared_cleanup' in driver.device.__dict__:del driver.device.shared_cleanup
        run=subprocess.run
        def actual(args,**kwargs):
            if args[0]=='/usr/bin/node':
                (base/'boot').write_text(self.boot)
                args=[os.environ.get('NODE8','node'),*args[1:]]
            return run(args,**kwargs)
        with patch('install_device.subprocess.run',side_effect=actual):
            first=driver.clean_remove(identifier)
            self.assertEqual(first['stage'],'restart-required',first)
            self.assertTrue(private.exists())
            self.assertEqual(calls.count('remove-'+APPS[0]),0)
            self.boot='22222222-2222-2222-2222-222222222222'
            final=driver.clean_remove(identifier)
            self.assertEqual(final['stage'],'verified-clean',final)
            self.assertFalse(private.exists())

    @unittest.skipUnless(sys.platform=='linux' and os.getuid()==0,'real UID1001 fixture needs disposable Linux Root')
    def test_real_root_deletes_only_owned_packages_through_uid1001_shared_containers(self):
        from cytv.no_root_cleanup import PRIVATE_CLEANUP_PROGRAM
        driver,identifier,root,updater,payload,calls,present=self.prepare()
        base=root.parent;developer=base/'developer';sdk=developer/'apps/usr/palm'
        foreign=base/'foreign';foreign.write_text('never follow')
        owned=[];siblings=[]
        for kind,name in (('services',APPS[0]+'.service'),('packages',APPS[0]),('applications',APPS[0])):
            container=sdk/kind;container.mkdir(parents=True,exist_ok=True)
            if kind!='applications':os.chown(container,1001,1001);container.chmod(0o777)
            path=container/name;path.mkdir();(path/'changed-owned-data').write_text('partial bytes')
            (path/'link').symlink_to(foreign);owned.append(path)
            sibling=container/'org.foreign.app';sibling.mkdir();(sibling/'keep').write_text('keep');siblings.append(sibling)
        source=PRIVATE_CLEANUP_PROGRAM.replace('/media/developer',str(developer))
        script=payload/'root-updater/cleanup_no_root_private.js';script.write_text(source)
        manifest=payload/'root-updater/bundle.json';value=json.loads(manifest.read_text());value['files'][script.name]=hashlib.sha256(script.read_bytes()).hexdigest();manifest.write_text(json.dumps(value))
        del driver.device.shared_cleanup
        driver.device.ownership=driver.ownership
        run=subprocess.run
        def actual(args,**kwargs):return run([os.environ.get('NODE8','node'),*args[1:]],**kwargs)
        with patch('install_device.subprocess.run',side_effect=actual):
            result=driver.device.shared_cleanup('root-package',{},app=APPS[0])
        self.assertEqual(result['present'],[]);self.assertEqual(result['blocked'],[])
        self.assertTrue(all(not p.exists() for p in owned))
        self.assertTrue(all((p/'keep').read_text()=='keep' for p in siblings))
        self.assertEqual(foreign.read_text(),'never follow')
        self.assertEqual((sdk/'services').stat().st_uid,1001)


if __name__=='__main__':unittest.main()
