"""Advisory setup choices cannot bypass classification or current removal proof."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from cytv import state
from cytv.desktop import DesktopConsole
from cytv.errors import UserError
from cytv.recovery import recover
from cytv.terminal import Console


class RecoveryActionTests(unittest.TestCase):
    def test_setup_projection_obeys_assessment_priority(self):
        from cytv.recovery_state import setup_actions
        root = {'edition':'root'}
        cases = [
            ({'action':'activate-root'}, {'device':{'result':{}}}, ['continue-setup','finish-home-off']),
            ({'action':'activate-root','product_operation':'a'*32}, {'device':{'result':{}}}, ['continue-setup','finish-home-off']),
            ({'action':'activate-root','home_backend':'c1-native-gate'}, {'device':{'result':{}}}, ['continue-setup']),
            ({'action':'install','product_operation':'a'*32}, {'device':{'product':{
                'operation':'a'*32,'state':'complete','current':True,'result':{
                    'installed':'com.cleanyourtv.root.preview','home_changed':False,'verified':True,'baseline_sha':'b'*64}}}},
             ['continue-setup','finish-home-off']),
            ({'action':'install','product_operation':'a'*32}, {'device':{'result':{}}}, []),
            ({'action':'install','product_operation':'a'*32}, {'device':{'product':{
                'operation':'a'*32,'state':'recovery_required','current':False}}}, []),
            ({'action':'install','product_operation':'a'*32}, {'device':{'product':{
                'operation':'a'*32,'state':'failed','current':False}}}, []),
            ({'action':'install','product_operation':'a'*32}, {'device':{'product':{
                'operation':'a'*32,'state':'complete','current':False}}}, []),
            ({'action':'install','product_operation':'a'*32}, {'device':{'product':{
                'operation':'a'*32,'state':'complete'}}}, []),
            ({'action':'setup-root-updater','product_operation':'a'*32}, {'device':{'result':{}}}, ['continue-setup']),
            ({'action':'uninstall'}, {'device':{'result':{}}}, []),
            ({'action':'uninstall','product_operation':'a'*32}, {'device':{'product':{
                'operation':'a'*32,'state':'complete','current':True}}}, []),
            ({'action':'setup-root-updater'}, {'device':{'result':{}}}, ['continue-setup']),
            ({'action':'activate-root'}, {}, []),
            ({'action':'activate-root','previous':{}}, {'device':{'result':{}}}, []),
            ({'action':'unknown'}, {'device':{'result':{}}}, []),
            (None, {'device':{'result':{}}}, []),
            ({'action':'activate-root'}, {'active_operation':'PRIVATE','device':{'result':{}}}, []),
            ({'action':'install','product_operation':'a'*32}, {'device':{'product':{'operation':'b'*32}}}, []),
            ({'action':'install','product_operation':'a'*32}, {'device':{'product':{'operation':'a'*32,'state':'pending'}}}, []),
            ({'action':'install','stage':'coordinator-submitted'}, {'device':{'product':{'passive':{}}}}, []),
        ]
        for pending, observation, expected in cases:
            with self.subTest(pending=pending, observation=observation):
                observation['can_resume_root_setup'] = True
                self.assertEqual(setup_actions(root,pending,observation), expected)
                self.assertEqual(setup_actions({'edition':'no-root'},pending,observation), [])

    def test_failed_product_readiness_is_blocked_and_returns_fixed_pure_diagnostic(self):
        from cytv.contract_events import Recorder, current_recorder
        from cytv.recovery_state import assess, observation_diagnostics
        observed={'can_resume_root_setup':True,'device':{'product':{
            'operation':'PRIVATE','state':'recovery_required','current':False}}}
        pending={'action':'install','product_operation':'PRIVATE'}
        recorder=Recorder(); token=current_recorder.set(recorder)
        self.addCleanup(current_recorder.reset,token)
        self.assertEqual(assess({'edition':'root'},pending,observed),{
            'state':'blocked','reason':'observation-unverified','actions':['check','retain-evidence']})
        facts=observation_diagnostics(observed)
        self.assertEqual(len(facts),1)
        self.assertEqual(facts[0]['field'],'device.product')
        self.assertEqual(facts[0]['expected'],'setup-product-current-complete')
        self.assertEqual(facts[0]['actual'],{'type':'object','length':3,'category':'mismatch'})
        self.assertNotIn('PRIVATE',json.dumps(facts))
        self.assertEqual(recorder.snapshot()['events'],[])
        self.assertEqual(assess({'edition':'root'},{'action':'uninstall','product_operation':'a'*32},{
            'can_resume_root_setup':True,'reconciliation':'product-removal-verified',
            'device':{'product':{'operation':'a'*32,'state':'complete','current':True}}}),{
                'state':'terminal-verified','reason':'removal-verified','actions':['reconcile','retain-evidence']})

    def test_cli_desktop_android_never_offer_setup_from_blocked_raw_flag(self):
        bridge_path = Path(__file__).resolve().parents[2] / 'android/app/src/main/python/android_bridge.py'
        spec = importlib.util.spec_from_file_location('recovery_actions_bridge', bridge_path)
        bridge = importlib.util.module_from_spec(spec); spec.loader.exec_module(bridge)
        for frontend in ('cli','desktop','android'):
            for fields, observation in [
                ({'previous':{}}, {'device':{'result':{}}}),
                ({'action':'unknown'}, {'device':{'result':{}}}),
                ({}, {}),
                ({}, {'active_operation':'PRIVATE','device':{'result':{}}}),
                ({'product_operation':'a'*32}, {'device':{'product':{'operation':'a'*32,'state':'pending'}}}),
                ({'product_operation':'a'*32}, {'device':{'product':{'operation':'b'*32,'state':'complete'}}}),
                ({'product_operation':'a'*32}, {'device':{'product':{'operation':'a'*32,'state':'recovery_required','current':False}}}),
                ({'product_operation':'a'*32}, {'device':{'product':{'operation':'a'*32,'state':'failed','current':False}}}),
                ({'action':'uninstall','product_operation':'a'*32}, {'device':{'product':{'operation':'a'*32,'state':'complete','current':True}}}),
            ]:
                with self.subTest(frontend=frontend,fields=fields), tempfile.TemporaryDirectory() as tmp:
                    store=state.Store(tmp); profile=state.target('tv.local','root')
                    store.begin(profile,'install'); store.checkpoint(profile,**fields)
                    before=store.pending(profile)
                    observation['can_resume_root_setup']=True
                    installer=Mock(store=store,profile=profile)
                    installer.observe_recovery.return_value=observation
                    output=[]
                    if frontend=='cli': write=Console(output.append)
                    elif frontend=='desktop': write=DesktopConsole(lambda kind,value:output.append((kind,value)))
                    else:
                        native=Mock(); native.emit.side_effect=lambda raw:output.append(json.loads(raw))
                        write=bridge.AndroidConsole(bridge.Callbacks(native))
                    answers=[]
                    def ask(prompt):
                        answers.append(str(prompt))
                        return '0'  # Exit an unsafe menu, so its unexpected appearance fails promptly.
                    with self.assertRaises(UserError):
                        recover(installer,ask,write,initial_observation=observation)
                    self.assertEqual(answers,[])
                    self.assertNotIn('Continue setup and turn on Home control',str(output))
                    self.assertEqual(store.pending(profile),before)
                    installer.resume_root_setup.assert_not_called()
                    installer.finish_root_setup_disabled.assert_not_called()

    def test_permitted_setup_actions_reach_all_frontends_without_new_home_off_path(self):
        bridge_path = Path(__file__).resolve().parents[2] / 'android/app/src/main/python/android_bridge.py'
        spec = importlib.util.spec_from_file_location('permitted_actions_bridge', bridge_path)
        bridge = importlib.util.module_from_spec(spec); spec.loader.exec_module(bridge)
        for frontend in ('cli','desktop','android'):
            for backend, expected in [('existing',['continue-setup','finish-home-off','retain-evidence']),
                                      ('c1-native-gate',['continue-setup','retain-evidence']),
                                      ('product',['continue-setup','finish-home-off','retain-evidence'])]:
                with self.subTest(frontend=frontend,backend=backend), tempfile.TemporaryDirectory() as tmp:
                    store=state.Store(tmp); profile=state.target('tv.local','root')
                    if backend=='product': store.begin(profile,'install',product_operation='a'*32)
                    else: store.begin(profile,'activate-root',home_backend=backend)
                    installer=Mock(store=store,profile=profile)
                    output=[]; plans=[]
                    if frontend=='cli': write=Console(output.append)
                    elif frontend=='desktop': write=DesktopConsole(lambda kind,value:output.append((kind,value)))
                    else:
                        native=Mock(); native.emit.side_effect=lambda raw:output.append(json.loads(raw))
                        write=bridge.AndroidConsole(bridge.Callbacks(native))
                    original_plan=write.recovery_plan
                    def capture(value):
                        plans.append(value); original_plan(value)
                    write.recovery_plan=capture
                    observation={'can_resume_root_setup':True,'device':{'result':{}}}
                    if backend=='product':
                        observation['device']={'product':{'operation':'a'*32,'state':'complete','current':True,
                            'result':{'installed':'com.cleanyourtv.root.preview','home_changed':False,
                                      'verified':True,'baseline_sha':'b'*64}}}
                    recover(installer,lambda prompt:'0',write,initial_observation=observation)
                    self.assertEqual(plans[-1]['actions'],expected)
                    visible = str(write.options) if frontend=='desktop' else str(output)
                    self.assertEqual('Finish setup with LG Home and Home control off' in visible,
                                     backend!='c1-native-gate')
                    installer.resume_root_setup.assert_not_called()
                    installer.finish_root_setup_disabled.assert_not_called()

    def test_saved_clean_removal_requires_current_backend_result(self):
        from cytv.recovery_state import assess, removal_summary
        from cytv.recovery_ui import removal_details
        with tempfile.TemporaryDirectory() as tmp:
            store=state.Store(tmp); profile=state.target('tv.local','root')
            store.request_clean_removal(profile)
            store.checkpoint(profile,stage='verified-clean',removal_reason='removal-verified',
                             result={'removed':True,'verified_clean':True})
            pending=store.pending(profile)
            from cytv import diagnostics
            report=json.loads(diagnostics.create_report(store,'recover',profile,'recover').read_text())
            self.assertEqual(report['recovery']['state'],'cleanup-in-progress')
            self.assertEqual(report['recovery']['reason'],'removal-recheck-required')
            self.assertEqual(report['removal']['reason'],'removal-recheck-required')
            self.assertEqual(assess(profile,pending), {'state':'cleanup-in-progress',
                'reason':'removal-recheck-required','actions':['continue-removal','retain-evidence']})
            self.assertEqual(removal_summary(pending)['reason'],'removal-recheck-required')
            self.assertEqual(removal_details({'disposition':'clean-removal','removal':removal_summary(pending)})['stage_text'],
                             'Verifying removal…')
            for current in (False,True):
                with self.subTest(current=current):
                    installer=Mock(store=store,profile=profile)
                    def continue_removal(expected_pending):
                        if current: store.finish_clean_removal(profile)
                        return {'removed':current,'verified_clean':current}
                    installer.continue_clean_removal.side_effect=continue_removal
                    plans=[]; write=Console(lambda text:None); write.recovery_plan=plans.append
                    if current:
                        recover(installer,lambda prompt:'y',write,initial_observation={})
                        self.assertEqual(plans[-1]['state'],'complete')
                        self.assertIs(plans[-1]['verified_clean'],True)
                        report=json.loads(diagnostics.create_report(store,'recover',profile,'recover',
                            status={'removed':True,'verified_clean':True}).read_text())
                        self.assertEqual(report['recovery']['state'],'idle')
                        self.assertEqual(report['status'],{'removed':True,'verified_clean':True})
                    else:
                        with self.assertRaises(UserError):
                            recover(installer,lambda prompt:'y',write,initial_observation={})
                        self.assertNotEqual(plans[-1]['state'],'complete')
                        self.assertIs(plans[-1]['verified_clean'],False)
                    installer.continue_clean_removal.assert_called_once_with(pending)

    def test_unexpected_observation_diagnostics_are_pure_fixed_and_optional(self):
        from cytv.contract_events import Recorder, current_recorder
        from cytv.recovery_state import assess, observation_diagnostics
        recorder=Recorder(); token=current_recorder.set(recorder)
        self.addCleanup(current_recorder.reset,token)
        observed={'device':{'product':'PRIVATE'},'can_resume_root_setup':'PRIVATE'}
        facts=observation_diagnostics(observed)
        self.assertEqual([e['field'] for e in facts],['device.product','can_resume_root_setup'])
        self.assertNotIn('PRIVATE',json.dumps(facts))
        self.assertEqual(facts[0]['actual'],{'type':'string','length':7})
        self.assertEqual(observation_diagnostics({}),[])
        self.assertEqual(observation_diagnostics(None),[])
        assess({'edition':'root'},{'action':'install'},observed)
        self.assertEqual(recorder.snapshot()['events'],[])
        with tempfile.TemporaryDirectory() as tmp:
            store=state.Store(tmp); profile=state.target('tv.local','root'); store.begin(profile,'install')
            installer=Mock(store=store,profile=profile)
            with self.assertRaises(UserError):
                recover(installer,lambda prompt:'y',Console(lambda text:None),initial_observation=observed)
        self.assertEqual(len(recorder.snapshot()['events']),2)
        self.assertNotIn('PRIVATE',json.dumps(recorder.snapshot()))
