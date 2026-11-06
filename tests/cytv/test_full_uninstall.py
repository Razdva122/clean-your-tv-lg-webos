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
        def run(command,**kwargs):
            if '/install_driver.py ' not in command:return ''
            words=shlex.split(command);action=words[next(i for i,w in enumerate(words) if w.endswith('/install_driver.py'))+1]
            operation=words[words.index('--operation')+1];calls.append((action,operation))
            if terminal=='lost' and action=='clean-remove':raise RuntimeError('lost SSH reply')
            return json.dumps({'operation':operation,'stage':'verified-clean' if terminal=='complete' else 'package-removal',
                               'state':'complete' if terminal=='complete' else 'recovery_required','code':'verified','current':terminal=='complete',
                               'result':{'removed':True,'applications_services_startup_removed':True,'private_cleanup_verified':True}})
        remote.run.side_effect=run
        inst=Installer(remote,store,profile,root,{},lambda *_:None);inst._selected_python='/usr/bin/python3'
        inst._select_python=MagicMock(return_value='/usr/bin/python3')
        inst.prepare_root_helper_removal=MagicMock(return_value={'mode':'absent'})
        return inst,remote,store,profile,calls

    def test_full_removal_is_one_device_operation_and_no_host_luna_mutation(self):
        inst,remote,store,profile,calls=self.fixture()
        result=inst.uninstall(full_project=True)
        self.assertTrue(result['removed']);self.assertTrue(result['verified_clean'])
        self.assertEqual([action for action,_ in calls],['clean-remove'])
        remote.luna.assert_not_called();self.assertIsNone(store.pending(profile))

    def test_uncertain_shared_remove_keeps_same_device_cleanup_selector(self):
        inst,remote,store,profile,calls=self.fixture('lost')
        with self.assertRaisesRegex(RuntimeError,'lost SSH'):inst.uninstall(full_project=True)
        pending=store.pending(profile);identifier=pending['product_operation']
        inst.installed_apps=MagicMock(return_value=[]);inst.verify_absent=MagicMock()
        with self.assertRaisesRegex(RuntimeError,'lost SSH'):inst.uninstall(full_project=True)
        self.assertEqual(calls,[('clean-remove',identifier),('clean-remove',identifier)])
        self.assertEqual(store.pending(profile)['product_operation'],identifier)
        remote.luna.assert_not_called();inst.verify_absent.assert_not_called()

    def test_terminal_status_completes_without_repeating_remove(self):
        inst,remote,store,profile,calls=self.fixture()
        store.begin(profile,'uninstall',full_project=True,product_operation='a'*32)
        self.assertTrue(inst.uninstall(full_project=True)['removed'])
        self.assertEqual(calls,[('clean-remove','a'*32)]);self.assertIsNone(store.pending(profile));remote.luna.assert_not_called()

    def test_ambiguous_legacy_host_receipts_are_retained_without_package_requests(self):
        for extra in ({'root_submitted':True},{'removals':{UPDATER_APP:'submitted'}},{'removals':{UPDATER_APP:'done'}}):
            with self.subTest(extra=extra):
                inst,remote,store,profile,calls=self.fixture()
                store.begin(profile,'uninstall',full_project=True,updater_archive='/var/lib/clean-your-tv-root-updater.archive-'+'a'*32,**extra)
                with self.assertRaisesRegex(RuntimeError,'Recovery'):inst.uninstall(full_project=True)
                self.assertIsNotNone(store.pending(profile));self.assertEqual(calls,[]);remote.luna.assert_not_called()

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

    def test_package_reappearance_does_not_clear_historical_removal_or_replay(self):
        inst,remote,store,profile,calls=self.fixture()
        original=remote.run.side_effect
        def stale(command,**kwargs):
            raw=original(command,**kwargs)
            if '/install_driver.py ' in command:
                event=json.loads(raw);event['current']=False;return json.dumps(event)
            return raw
        remote.run.side_effect=stale
        store.begin(profile,'uninstall',full_project=True,product_operation='a'*32)
        self.assertIsNotNone(inst.status()['pending'])
        with self.assertRaisesRegex(RuntimeError,'progress'):inst.uninstall(full_project=True)
        self.assertEqual([action for action,_ in calls],['status','clean-remove'])
        self.assertIsNotNone(store.pending(profile));remote.luna.assert_not_called()
