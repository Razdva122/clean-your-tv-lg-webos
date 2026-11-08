"""Host removal consumes authoritative device records; effects live on the TV.

The former host sequence's ordering, every-boundary failures, exact terminal
receipts and process-exit tests now exercise LocalDevice.remove in
root-edition/tests/test_install_driver.py. Permission/recovery helper filesystem
regressions remain in their dedicated existing test modules.
"""
import hashlib
import json
from pathlib import Path
import shlex
import tempfile
import unittest
from unittest.mock import MagicMock
from cytv.operations import Installer, UPDATER_APP
from cytv import state, package
from cytv.errors import UserError

class FullUninstallTests(unittest.TestCase):
    def fixture(self, terminal='complete'):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        root=Path(temp.name);store=state.Store(root/'host');profile=state.target('tv.local','root')
        for component in ('root','root-updater'):
            bundle=root/component;bundle.mkdir()
            (bundle/'install_driver.py').write_bytes(b'fixed trusted driver')
            manifest={'files':{'install_driver.py':hashlib.sha256(b'fixed trusted driver').hexdigest()}}
            (bundle/'bundle.json').write_text(json.dumps(manifest))
        remote=MagicMock();calls=[]
        device={'outcome':terminal,'present':True,'requests':[],
                'target_operation':'b'*32,'target_lease':'c'*32,'target_removal':'e'*32}
        def run(command,**kwargs):
            if '/install_driver.py ' not in command:return ''
            words=shlex.split(command);action=words[next(i for i,w in enumerate(words) if w.endswith('/install_driver.py'))+1]
            operation=words[words.index('--operation')+1];calls.append((action,operation))
            if action=='clean-target':
                return json.dumps(dict(operation=operation,state='fresh',
                    **{key:device[key] for key in ('target_operation','target_lease','target_removal')}))
            if action=='clean-remove':
                self.assertEqual(operation,device['target_operation'])
                intent=words[words.index('--removal-intent')+1]
                lease=words[words.index('--removal-lease')+1]
                self.assertEqual((intent,lease),(device['target_removal'],device['target_lease']))
                device['requests'].append((operation,intent,lease))
                if device['outcome']=='lost':raise RuntimeError('lost SSH reply')
                if device['outcome']=='complete':device['present']=False
            complete=device['outcome']=='complete' and not device['present']
            return json.dumps({'operation':operation,'stage':'verified-clean' if complete else 'package-removal',
                               'state':'complete' if complete else 'recovery_required','code':'verified','current':complete,
                               'cleanup_error':None if device['outcome']!='package-failed' else 'removal-failed',
                               'result':{'removed':complete,'applications_services_startup_removed':complete,'private_cleanup_verified':complete}})
        remote.run.side_effect=run
        inst=Installer(remote,store,profile,root,{},lambda *_:None);inst._selected_python='/usr/bin/python3'
        inst._select_python=MagicMock(return_value='/usr/bin/python3')
        inst.prepare_root_helper_removal=MagicMock(return_value={'mode':'absent'})
        return inst,remote,store,profile,calls,device

    def test_full_removal_is_one_device_operation_and_no_host_luna_mutation(self):
        inst,remote,store,profile,calls,device=self.fixture()
        result=inst.uninstall(full_project=True)
        self.assertTrue(result['removed']);self.assertTrue(result['verified_clean'])
        self.assertEqual([action for action,_ in calls],['clean-target','clean-remove'])
        remote.luna.assert_not_called();self.assertIsNone(store.pending(profile))

    def test_uncertain_shared_remove_keeps_same_device_cleanup_selector(self):
        inst,remote,store,profile,calls,device=self.fixture('lost')
        with self.assertRaisesRegex(RuntimeError,'lost SSH'):inst.uninstall(full_project=True)
        pending=store.pending(profile);identifier=pending['product_operation']
        inst.installed_apps=MagicMock(return_value=[]);inst.verify_absent=MagicMock()
        with self.assertRaisesRegex(RuntimeError,'lost SSH'):inst.uninstall(full_project=True)
        self.assertEqual(calls,[('clean-target',identifier),('clean-remove','b'*32)]*2)
        self.assertEqual(device['requests'],[('b'*32,'e'*32,'c'*32)]*2)
        self.assertEqual(store.pending(profile)['removal_target_operation'],'b'*32)
        self.assertEqual(store.pending(profile)['removal_target_intent'],'e'*32)
        self.assertEqual(store.pending(profile)['product_operation'],identifier)
        remote.luna.assert_not_called();inst.verify_absent.assert_not_called()

    def test_existing_host_selector_and_original_history_stay_separate_from_device_goal(self):
        inst,remote,store,profile,calls,device=self.fixture()
        store.begin(profile,'uninstall',full_project=True,product_operation='a'*32)
        original=store.pending(profile)
        self.assertTrue(inst.uninstall(full_project=True)['removed'])
        self.assertEqual(calls,[('clean-target','a'*32),('clean-remove','b'*32)])
        receipt=json.loads((store.device_dir(profile)/'clean-removal.json').read_bytes())
        self.assertEqual(receipt['previous'],original)
        self.assertEqual(receipt['product_operation'],'a'*32)
        self.assertEqual(receipt['removal_target_operation'],'b'*32)
        self.assertEqual(receipt['removal_target_intent'],'e'*32)
        self.assertIsNone(store.pending(profile));remote.luna.assert_not_called()

    def test_ambiguous_legacy_receipts_are_preserved_while_current_cleanup_runs(self):
        for extra in ({'root_submitted':True},{'removals':{UPDATER_APP:'submitted'}},{'removals':{UPDATER_APP:'done'}}):
            with self.subTest(extra=extra):
                inst,remote,store,profile,calls,device=self.fixture()
                store.begin(profile,'uninstall',full_project=True,updater_archive='/var/lib/clean-your-tv-root-updater.archive-'+'a'*32,**extra)
                original=store.pending(profile)
                self.assertTrue(inst.uninstall(full_project=True)['verified_clean'])
                receipt=json.loads((store.device_dir(profile)/'clean-removal.json').read_bytes())
                self.assertEqual(receipt['previous'],original)
                self.assertEqual([action for action,_ in calls],['clean-target','clean-remove'])
                self.assertIsNone(store.pending(profile));remote.luna.assert_not_called()

    def test_package_failure_keeps_goal_and_original_failure_for_normal_retry(self):
        from cytv import diagnostics
        from cytv.errors import TVCommandError
        inst,remote,store,profile,calls,device=self.fixture('package-failed')
        store.begin(profile,'install',stage='pending',product_operation='a'*32)
        report=diagnostics.create_report(store,'install',profile,'install-helper',TVCommandError(127))
        first=json.loads(report.read_bytes())['first_failure']
        original=store.pending(profile)
        with self.assertRaisesRegex(UserError,'could not finish removing a package'):
            inst.uninstall(full_project=True)
        pending=store.pending(profile)
        self.assertEqual(pending['previous'],original)
        self.assertEqual(pending['removal_reason'],'removal-failed')
        device['outcome']='complete'
        self.assertTrue(inst.uninstall(full_project=True)['verified_clean'])
        self.assertEqual(device['requests'],[('b'*32,'e'*32,'c'*32)]*2)
        receipt=json.loads((store.device_dir(profile)/'clean-removal.json').read_bytes())
        self.assertEqual(receipt['previous'],original)
        later=diagnostics.create_report(store,'uninstall',profile,'uninstall',status={'removed':True,'verified_clean':True})
        self.assertEqual(json.loads(later.read_bytes())['first_failure'],first)
        self.assertIsNone(store.pending(profile));remote.luna.assert_not_called()

    def test_malformed_current_target_cannot_submit_cleanup(self):
        for field,value in (('target_operation','../foreign'),('target_lease','bad'),('target_removal','bad')):
            with self.subTest(field=field):
                inst,remote,store,profile,calls,device=self.fixture()
                device[field]=value
                with self.assertRaisesRegex(UserError,'Removal evidence changed'):
                    inst.uninstall(full_project=True)
                self.assertEqual([action for action,_ in calls],['clean-target'])
                self.assertEqual(device['requests'],[])
                self.assertIsNotNone(store.pending(profile));remote.luna.assert_not_called()

    def test_final_verification_checks_registrations_even_without_root_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            remote=MagicMock();remote.run.return_value=''
            inst=Installer(remote,state.Store(tmp),state.target('tv.local','root'),Path(tmp),{},lambda *_:None)
            with self.assertRaisesRegex(RuntimeError,'registrations remain'):inst.verify_project_removed()
            remote.luna.assert_not_called()
            command=remote.run.call_args.args[0]
            self.assertIn('50-clean-your-tv-root',command)
            self.assertIn('clean-your-tv-root.json',command)

    def test_status_never_finishes_partial_full_uninstall(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=state.Store(tmp);profile=state.target('tv.local','root');remote=MagicMock()
            remote.run.return_value='{"stage":"uninstalled-state-retained"}'
            inst=Installer(remote,store,profile,Path(tmp),{},lambda *_:None)
            inst._selected_python='/usr/bin/python3';inst.verify_absent=MagicMock()
            store.begin(profile,'uninstall',full_project=True)
            self.assertIsNotNone(inst.status()['pending'])
            self.assertIsNotNone(store.pending(profile))

    def test_stale_final_device_proof_cannot_finish_current_cleanup(self):
        inst,remote,store,profile,calls,device=self.fixture()
        original_run=remote.run.side_effect
        def stale(command,**kwargs):
            raw=original_run(command,**kwargs)
            if '/install_driver.py clean-remove ' in command:
                event=json.loads(raw);event['current']=False;return json.dumps(event)
            return raw
        remote.run.side_effect=stale
        store.begin(profile,'install',stage='pending',product_operation='a'*32)
        original=store.pending(profile)
        with self.assertRaisesRegex(UserError,'Some Clean Your TV files or settings remain'):
            inst.uninstall(full_project=True)
        self.assertEqual(store.pending(profile)['previous'],original)
        self.assertFalse((store.device_dir(profile)/'clean-removal.json').exists())
        self.assertEqual(calls,[('clean-target','a'*32),('clean-remove','b'*32)])
        remote.luna.assert_not_called()

    def test_new_explicit_goal_removes_reappeared_package_without_reusing_completed_authority(self):
        inst,remote,store,profile,calls,device=self.fixture()
        store.begin(profile,'uninstall',full_project=True,product_operation='a'*32)
        self.assertTrue(inst.uninstall(full_project=True)['verified_clean'])
        receipt=json.loads((store.device_dir(profile)/'clean-removal.json').read_bytes())
        device['present']=True
        pending=store.request_clean_removal(profile)
        self.assertNotEqual(pending['removal_operation'],receipt['removal_operation'])
        device.update(target_operation=pending['product_operation'],target_removal=pending['removal_operation'],target_lease='f'*32)
        self.assertIsNotNone(inst.status()['pending'])
        self.assertTrue(device['present'])
        self.assertTrue(inst.uninstall(full_project=True)['verified_clean'])
        self.assertFalse(device['present'])
        self.assertEqual(calls,[('clean-target','a'*32),('clean-remove','b'*32),
            ('clean-target',pending['product_operation']),('clean-remove',pending['product_operation'])])
        self.assertEqual(device['requests'],[('b'*32,'e'*32,'c'*32),
            (pending['product_operation'],pending['removal_operation'],'f'*32)])
        again=json.loads((store.device_dir(profile)/'clean-removal.json').read_bytes())
        self.assertNotIn('previous',again)
        history=list(store.device_dir(profile).glob('clean-removal-history-*.json'))
        self.assertTrue(any(json.loads(path.read_text())==receipt for path in history))
        self.assertIsNone(store.pending(profile));remote.luna.assert_not_called()
