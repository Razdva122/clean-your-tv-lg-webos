"""Retained activation evidence must survive product checks and failed enable."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock
from cytv import diagnostics, operations, state
from cytv.errors import TVCommandError


class RetainedDiagnosticTests(unittest.TestCase):
    def test_product_readback_keeps_runtime_and_recovery_observations(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=state.Store(tmp); profile=state.target('tv.local','root')
            remote=MagicMock();remote.run.return_value=json.dumps({'operation':'a'*32,'state':'complete','current':True})
            info={'status':{'can_resume_root_setup':True,'deployment_stage':'installed-recovery-only',
                'device':{'result':{'intent':{'enabled':False,'phase':'disabled'},
                'recovery':{'integrity_verified':True},'guardian_active':False}}}}
            inst=operations.Installer(remote,store,profile,Path(tmp),{},tv_info=info)
            inst.coordinator_code=lambda:'/verified';inst._python=lambda *args:'/usr/bin/python3'
            inst.product_action('status','a'*32,verify_current=True)
            report=json.loads(diagnostics.create_report(store,'recover',profile,'recover',TVCommandError(1),info,status=info['status']).read_text())
            self.assertIs(report['status'].get('home_enabled'),False)
            self.assertIs(report['status'].get('recovery_integrity_verified'),True)
            self.assertIs(report['status'].get('can_resume_root_setup'),True)
            self.assertEqual(report['status']['product']['state'],'complete')

    def test_root_activation_is_not_classified_as_other_edition(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=state.Store(tmp);profile=state.target('tv.local','root')
            store.begin(profile,'activate-root',stage='enable')
            report=json.loads(diagnostics.create_report(store,'recover',profile,'recover',TVCommandError(1)).read_text())
            self.assertEqual(report['recovery']['category'],'root-activation-pending')
            self.assertEqual(report['recovery']['next_action'],'review-recovery')

    def test_snapshot_is_revalidated_in_reports_and_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=state.Store(tmp);profile=state.target('tv.local','root')
            store.begin(profile,'install',stage='enable')
            info={'root_diagnostics':{'runtime_release':'0.8.4','components':{'root':'0.8.4','private':'PRIVATE'},
                'component_reads':{'root':'read','system_updater':'missing'},
                'health_log':{'status':'read','scope':'since-enable','health_refusal':'boot-mismatch',
                    'supervisor_error':True,'transaction':'PRIVATE'},'cursor':{'token':'PRIVATE'}}}
            report=json.loads(diagnostics.create_report(store,'install',profile,'activate-root',TVCommandError(1),info).read_text())
            self.assertEqual(report['tv'].get('root_diagnostics',{}).get('runtime_release'),'0.8.4')
            self.assertEqual(report['first_failure']['tv']['root_diagnostics']['health_log']['health_refusal'],'boot-mismatch')
            self.assertNotIn('PRIVATE',json.dumps(report))
            info['root_diagnostics']['health_log']['health_refusal']={'secret':'PRIVATE'}
            report=json.loads(diagnostics.create_report(store,'doctor',profile,'doctor-complete',tv_info=info).read_text())
            self.assertEqual(report['tv']['root_diagnostics']['health_log']['health_refusal'],'unknown')
            self.assertNotIn('PRIVATE',json.dumps(report))

    def test_failed_enable_exports_only_new_observation_without_masking_error(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            store=state.Store(tmp);profile=state.target('tv.local','root');remote=MagicMock()
            failure=TVCommandError(1);remote.run.side_effect=failure
            inst=operations.Installer(remote,store,profile,Path(tmp),{})
            inst._python=lambda *args:'/usr/bin/python3'
            inst.tv_info['status']={'can_resume_root_setup':True}
            before={'cursor':{'inode':1},'health_log':{'status':'read','scope':'historical-tail','health_refusal':'generic'}}
            after={'health_log':{'status':'read','scope':'since-enable','health_refusal':'phase-inactive'}}
            with patch('cytv.root_activation_diagnostics.collect',side_effect=[before,after]):
                with self.assertRaises(TVCommandError) as caught:inst.root_action('enable')
            self.assertIs(caught.exception,failure)
            report=json.loads(diagnostics.create_report(store,'recover',profile,'recover',caught.exception,inst.tv_info,status=inst.tv_info['status']).read_text())
            self.assertEqual(report['status'].get('observation_phase'),'before-enable')
            self.assertEqual(report['tv']['root_diagnostics']['health_log']['health_refusal'],'phase-inactive')
            self.assertNotIn('cursor',json.dumps(report))
            with patch('cytv.root_activation_diagnostics.collect',side_effect=RuntimeError('PRIVATE')):
                with self.assertRaises(TVCommandError) as caught:inst.root_action('enable')
            self.assertIs(caught.exception,failure)
            self.assertEqual(inst.tv_info['root_diagnostics']['health_log']['status'],'unavailable')
