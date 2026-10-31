"""Host pending changes only after a verified device cancellation disposition."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
from cytv import state

SOURCE=Path(__file__).resolve().parents[2]/'scripts/root-install-recovery.py'

class HostCancellationTests(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('root_install_recovery_tool',SOURCE)
        self.tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.tool)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=state.Store(self.tmp.name);self.profile=state.target('fixture.local','root')
        self.identifier='a'*32;self.proof='b'*64
        self.store.begin(self.profile,'install',stage='coordinator-submitted',product_operation=self.identifier,product_payload='/tmp/fixture',requires_updater=True,migrate=False)
        self.original=self.store.pending(self.profile)
        self.disposition=dict(operation=self.identifier,state='cancelled-and-removed',lease_terminal=True,proof_sha256=self.proof,home_changed=False)
    def test_verified_cancel_retains_host_history_before_finishing_pending(self):
        inspect=Mock(return_value=self.disposition)
        result=self.tool.reconcile(self.store,self.profile,self.identifier,'c'*64,self.proof,inspect)
        self.assertEqual(result['state'],'cancelled-and-removed');self.assertIsNone(self.store.pending(self.profile))
        import json
        history=list(self.store.device_dir(self.profile).glob('recovery-*.json'));self.assertEqual(len(history),1)
        value=json.loads(history[0].read_text());self.assertEqual(value['previous'],self.original)
        self.assertEqual(value['disposition'],self.disposition)
        inspect.assert_called_once_with(self.identifier,'c'*64)
    def test_unknown_wrong_operation_or_proof_preserves_pending(self):
        for change in ({'lease_terminal':False},{'state':'remove-submitting'},{'operation':'d'*32},{'proof_sha256':'d'*64},{'home_changed':True}):
            with self.subTest(change=change),self.assertRaises(ValueError):
                self.tool.reconcile(self.store,self.profile,self.identifier,'c'*64,self.proof,lambda *args:{**self.disposition,**change})
            self.assertEqual(self.store.pending(self.profile),self.original)
    def test_internal_recovery_staging_keeps_tv_parents_posix_on_windows(self):
        import contextlib,hashlib,io,json,sys
        from pathlib import PureWindowsPath
        from unittest.mock import patch
        from tests.cytv.test_remote_directories import RemoteTree
        self.store.save(self.profile)
        folder=Path(self.tmp.name)/'code';files={'install_driver.py':b'driver','system_updater/support/core.py':b'core'}
        for name,raw in files.items():
            target=folder/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
        manifest={'files':{n:hashlib.sha256(raw).hexdigest() for n,raw in files.items()}}
        (folder/'bundle.json').write_text(json.dumps(manifest))
        class Remote(RemoteTree):
            def run(remote,command,**kwargs):
                if '/usr/bin/node -e ' in command:return '/usr/bin/python3'
                if 'cancel_install.py inspect' in command:
                    self.assertIn("-I -B -c",command)
                    self.assertNotIn("--candidate",command)
                    return '{"state":"admissible"}'
                if command.startswith('rm -rf -- '):return ''
                return super().run(command,**kwargs)
            def close(remote):pass
        remote=Remote()
        def inventory(bundle):
            # argparse has already made a real LOCAL bundle Path; only later
            # remote parent conversions should see simulated Windows semantics.
            self.tool.Path=PureWindowsPath
            return manifest,{'cancel_install.py':b'recovery','cancel_provision.py':b'provision'},'c'*64
        argv=['recovery','inspect','--code-bundle',str(folder),'--operation',self.identifier,'--code-sha256','c'*64]
        with patch.object(self.tool.state,'Store',return_value=self.store),patch.object(self.tool,'Path',Path), \
             patch.object(self.tool,'code_inventory',side_effect=inventory),patch.object(sys,'argv',argv), \
             patch('cytv.transport.SSH.connect',return_value=remote),patch('cytv.operations.Installer._python',side_effect=AssertionError('retained binding executed')),contextlib.redirect_stdout(io.StringIO()):
            self.tool.main()
        self.assertEqual(remote.uploads,{'install_driver.py','system_updater/support/core.py','bundle.json','cancel_install.py','cancel_provision.py'})
        self.assertEqual(self.store.pending(self.profile),self.original)

    def test_inspect_can_obtain_candidate_from_original_receipt(self):
        import contextlib,io,sys
        from unittest.mock import patch
        # Parsing must reach saved-profile validation without a candidate, not
        # ask the owner to extract or upload a private request manually.
        argv=['recovery','inspect','--code-bundle','/unused','--operation',self.identifier,'--code-sha256','c'*64]
        with patch.object(sys,'argv',argv),patch.object(self.tool,'code_inventory',return_value=({}, {}, 'c'*64)), \
             patch.object(self.tool.state,'Store',return_value=self.store),self.assertRaisesRegex(ValueError,'exactly_one_matching_saved_root_profile_required'):
            self.tool.main()

    def test_isolated_entry_uses_staged_binding_and_ignores_pythonpath(self):
        import json,os,subprocess,sys
        stage=Path(self.tmp.name)/'stage';stage.mkdir()
        (stage/'python_binding.py').write_text('import sys\ndef verify_binding(state): return sys.executable\n')
        (stage/'cancel_install.py').write_text('import json,sys; print(json.dumps(dict(argv=sys.argv,isolated=sys.flags.isolated,bytecode=sys.dont_write_bytecode)))')
        shadow=Path(self.tmp.name)/'shadow';shadow.mkdir()
        (shadow/'python_binding.py').write_text('raise RuntimeError("retained or environment code executed")')
        result=subprocess.run([sys.executable,'-I','-B','-c',self.tool.RECOVERY_ENTRY,str(stage),str(stage/'cancel_install.py'),'inspect'],
                              env={**os.environ,'PYTHONPATH':str(shadow)},cwd=shadow,capture_output=True,text=True,check=True)
        value=json.loads(result.stdout)
        self.assertEqual(value,dict(argv=[str(stage/'cancel_install.py'),'inspect'],isolated=1,bytecode=True))
        self.assertFalse(list(stage.rglob('__pycache__')))

    def test_recovery_interpreter_only_accepts_verified_literals(self):
        from cytv.python_runtime import RUNTIME_ROOT,SHA256
        from unittest.mock import Mock
        for selection,wanted in (('/usr/bin/python3','/usr/bin/python3'),
                                 ('/var/lib/clean-your-tv-root/python-launcher',RUNTIME_ROOT+'/'+SHA256+'/bin/python3.13')):
            remote=Mock();remote.run.return_value=selection
            self.assertEqual(self.tool.recovery_python(remote),wanted)
            command=remote.run.call_args.args[0]
            self.assertIn('env -u NODE_OPTIONS -u NODE_PATH /usr/bin/node -e',command)
            self.assertNotIn('runpy.run_path',command)
        remote.run.return_value='/tmp/foreign-python'
        with self.assertRaisesRegex(ValueError,'verified_recovery_interpreter_required'):self.tool.recovery_python(remote)

    def test_actual_node_selector_accepts_absent_and_refuses_incomplete_binding(self):
        import shlex,shutil,subprocess
        root=Path(self.tmp.name)/'root';root.mkdir()
        test=self
        class LocalNode:
            def run(remote,command):
                args=shlex.split(command)
                test.assertEqual(args[:7],['env','-u','NODE_OPTIONS','-u','NODE_PATH','/usr/bin/node','-e'])
                test.assertEqual(args[-1],'/var/lib/clean-your-tv-root')
                args[5]=shutil.which('node')
                args[-1]=str(root)  # No access to actual retained TV/host paths.
                return subprocess.run(args,check=True,capture_output=True,text=True).stdout
        self.assertEqual(self.tool.recovery_python(LocalNode()),'/usr/bin/python3')
        (root/'python-launcher').write_text('foreign launcher must never execute')
        with self.assertRaises(subprocess.CalledProcessError):self.tool.recovery_python(LocalNode())
        (root/'python-runtime.json').write_text('{}')
        with self.assertRaises(subprocess.CalledProcessError):self.tool.recovery_python(LocalNode())

    def test_isolated_entry_refuses_changed_binding_before_inspection(self):
        import subprocess,sys
        stage=Path(self.tmp.name)/'stage';stage.mkdir()
        (stage/'python_binding.py').write_text('def verify_binding(state): return "/tmp/foreign-python"\n')
        (stage/'cancel_install.py').write_text('raise AssertionError("inspection started")')
        result=subprocess.run([sys.executable,'-I','-B','-c',self.tool.RECOVERY_ENTRY,str(stage),str(stage/'cancel_install.py'),'inspect'],
                              capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('recovery_interpreter_binding_changed',result.stderr)
        self.assertNotIn('AssertionError',result.stderr)

    def test_mutation_still_requires_explicit_original_candidate_before_connecting(self):
        import contextlib,io,sys
        from unittest.mock import patch
        for action in ('remove','reconcile'):
            argv=['recovery',action,'--code-bundle','/unused','--operation',self.identifier,
                  '--code-sha256','c'*64,'--proof-sha256',self.proof,'--confirm-lg-home']
            with patch.object(sys,'argv',argv),patch.object(self.tool,'code_inventory',return_value=({}, {}, 'c'*64)), \
                 patch('cytv.transport.SSH.connect') as connect,contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
                self.tool.main()
            connect.assert_not_called()

    def test_other_host_operation_does_not_even_request_reconciliation(self):
        inspect=Mock();self.store.checkpoint(self.profile,product_operation='d'*32)
        with self.assertRaises(ValueError):self.tool.reconcile(self.store,self.profile,self.identifier,'c'*64,self.proof,inspect)
        inspect.assert_not_called();self.assertIsNotNone(self.store.pending(self.profile))

    def test_removal_requires_fresh_control_confirmation_before_connecting(self):
        import contextlib,io,sys
        from unittest.mock import patch
        with patch.object(sys,'argv',['recovery','remove','--code-bundle','/unused']), \
             patch('cytv.transport.SSH.connect') as connect,contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
            self.tool.main()
        connect.assert_not_called();self.assertEqual(self.store.pending(self.profile),self.original)

if __name__=='__main__':unittest.main()
