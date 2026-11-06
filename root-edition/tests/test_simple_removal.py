"""Practical full removal: present components, reboot, fresh readback."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

import test_clean_removal
from clean_removal import APPS, remove_packages, retire_tree


class SimpleRemoval(unittest.TestCase):
    fixture = test_clean_removal.PartialDeviceRemoval.fixture

    def prepare(self, **kwargs):
        fixture=self.fixture(**kwargs)
        self.boot='11111111-1111-1111-1111-111111111111'
        fixture[0].device.boot_id=lambda:self.boot
        return fixture

    def test_partial_removal_requires_full_boot_then_fresh_sweep(self):
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
        self.assertEqual(driver.clean_remove(identifier)['stage'],'verified-clean')
        self.assertFalse((root/'state/ssap.json').exists())
        driver.device.payload=None
        self.assertEqual(driver.clean_remove(identifier)['stage'],'verified-clean')
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
            remove_packages(device,record,lambda stage:None,lambda app:False)
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


if __name__=='__main__':unittest.main()
