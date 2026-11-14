"""Retained activation evidence must survive product checks and failed enable."""
import json
import os
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


    @unittest.skipUnless(os.name == 'posix', 'TV filesystem metadata requires POSIX')
    def test_connected_status_exports_retained_cause_without_journal_or_lifecycle_python(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            store = state.Store(base / 'host')
            profile = state.target('tv.local', 'root')
            store.begin(profile, 'install', stage='enable')
            first = json.loads(diagnostics.create_report(
                store, 'install', profile, 'activate-root', TVCommandError(1)).read_text())
            root = base / 'root'
            directory = root / 'c1-keyfilter'
            directory.mkdir(parents=True, mode=0o700)
            kernel_boot = base / 'boot'
            boot = '12345678-1234-1234-1234-123456789abc'
            token = 'a'*32
            kernel_boot.write_text(boot+'\n')
            values = {
                'config': f'CYTV-C1-KEYFILTER-1\ntoken {token}\nboot {boot}\ndev 1\nino 2\nsize 3\nmtime_ns 4\n',
                'intent.json': json.dumps(dict(schema=1, enabled=False, phase='disabled', token=token, boot=boot)),
                'stopped': f'{token} broker_expired\n',
                'native.log': json.dumps(dict(returnValue=False, backend='c1-native-gate',
                    routing='compositor-keyfilter-v1', state='stopped', mounted=False, healthy=False,
                    stock_verified=True, stopped=True, token=token, guardian_pid=0,
                    reason='ui_release_failed', profiles=None))+'\n',
            }
            for name, raw in values.items():
                path = directory / name
                path.write_text(raw)
                path.chmod(0o600)

            commands = []
            read_error = TVCommandError(1)
            fail_readback = False
            def run(command, *, timeout=None, data=None):
                commands.append(command)
                if '/usr/bin/node --version' in command:
                    return 'CYTV_NODE_VERSION v0.12.2'
                if 'CYTV_C1_GATE' in command:
                    return 'CYTV_C1_GATE'
                if 'deploy.json' in command:
                    if fail_readback:
                        raise read_error
                    return '{"stage":"incomplete-state"}'
                if command.endswith("/usr/bin/python3 -I -B - null") and data is not None:
                    namespace = {'__name__':'fixture'}
                    exec(data, namespace)
                    namespace['BOOT'] = kernel_boot
                    return json.dumps(namespace['snapshot'](root, base/'apps', os.getuid()))
                raise AssertionError(command)

            remote = MagicMock()
            remote.run.side_effect = run
            inst = operations.Installer(remote, store, profile, base, {})
            # The initial activation receipt is present, but the TV runtime
            # and host cleanup journals were never necessary for discovery.
            result = inst.status()
            self.assertEqual(result['deployment_stage'], 'incomplete-state')
            expected = {'status':'read', 'scope':'retained', 'original_stop':'broker_expired',
                        'guardian_release':'ui_release_failed'}
            self.assertEqual(inst.tv_info['root_diagnostics'].get('compositor'), expected)
            fail_readback = True
            with self.assertRaises(TVCommandError) as caught:
                inst.status()
            self.assertIs(caught.exception, read_error)
            self.assertEqual(inst.tv_info['root_diagnostics']['compositor'], expected)
            removal = store.request_clean_removal(profile)
            def terminal_cleanup(pending):
                inst.tv_info['status'] = {'device':{'product':{'last_failure':{
                    'exception_type':'ValueError','stage':'original-writers-fenced','cleanup_step':'runtime-restore',
                    'cleanup_probe':{'exception_type':'ValueError','native_reason':'effect_busy'}}}}}
                raise read_error
            inst._continue_clean_removal = terminal_cleanup
            with self.assertRaises(TVCommandError):
                inst.continue_clean_removal(removal)
            report = json.loads(diagnostics.create_report(store, 'uninstall', profile, 'uninstall',
                read_error, inst.tv_info, status=inst.tv_info['status']).read_text())
            self.assertEqual(report['tv']['root_diagnostics']['compositor'], expected)
            self.assertEqual(report['first_failure'], first['first_failure'])
            self.assertEqual(report['status']['product']['last_failure']['cleanup_probe']['native_reason'], 'effect_busy')
            for private in (token, boot, str(base)):
                self.assertNotIn(private, json.dumps(report))
            self.assertFalse(hasattr(inst, '_selected_python'))
            self.assertEqual((directory/'stopped').read_text(), values['stopped'])
            fail_readback = False
            fresh_store = state.Store(base / 'no-receipt')
            recovery_installer = operations.Installer(remote, fresh_store, profile, base, {})
            recovery = recovery_installer.observe_recovery()
            self.assertIsNone(recovery['pending'])
            recovery_report = json.loads(diagnostics.create_report(fresh_store, 'recover', profile,
                'recover', tv_info=recovery_installer.tv_info, status=recovery).read_text())
            self.assertEqual(recovery_report['tv'].get('root_diagnostics', {}).get('compositor'), expected)
            self.assertIsNone(fresh_store.pending(profile))
            (directory/'intent.json').unlink()
            recovery = inst.status()
            self.assertEqual(recovery['removal']['state'], 'cleanup-in-progress')
            self.assertEqual(inst.tv_info['root_diagnostics']['compositor'], {'status':'missing'})
            self.assertEqual(sum('/usr/bin/python3 -I -B - null' in cmd for cmd in commands), 5)
            self.assertEqual(store.pending(profile), removal)
