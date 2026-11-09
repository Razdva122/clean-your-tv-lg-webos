"""Selected installer bytes, rather than old self-consistent receipts, authorize enable."""
import hashlib
import importlib
import json
import os
from pathlib import Path
import shlex
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


class RuntimeContractWire(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.payload=Path(self.folder.name).resolve()
        self.names=('deploy.py','python_binding.py','runtime/cli.py','runtime/device_adapter.py',
                    'runtime/persistent_health.py','runtime/emergency_trial.py')
        files={}
        for name in self.names:
            path=self.payload/'root'/name;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text('selected '+name);files[name]=hashlib.sha256(path.read_bytes()).hexdigest()
        manifest=self.payload/'root/bundle.json';manifest.write_text(json.dumps({'package':'root.ipk','files':files}))
        outer={'root/'+name:digest for name,digest in files.items()}
        outer['root/bundle.json']=hashlib.sha256(manifest.read_bytes()).hexdigest()
        self.installer=SimpleNamespace(payload=self.payload,manifest={'files':outer},profile={'edition':'root'},tv_info={},
            remote=Mock(),_python=Mock(return_value='/usr/bin/python3'),_python_command=shlex.join)
        self.installer.select_graphics=Mock(side_effect=lambda:setattr(self.installer,'_graphics_paths',{'root':'root'}))

    def verify(self):
        module=importlib.import_module('cytv.root_runtime_contract')
        return module.verify(self.installer)

    def test_only_verified_selected_bytes_are_sent_to_isolated_python(self):
        self.installer.remote.run.return_value='CYTV_SELECTED_RUNTIME_VERIFIED\n'
        self.assertIsNone(self.verify())
        self.installer.select_graphics.assert_called_once()
        self.installer._python.assert_called_once_with()
        command=self.installer.remote.run.call_args.args[0]
        self.assertEqual(shlex.split(command),['/usr/bin/python3','-I','-B','-'])
        source=self.installer.remote.run.call_args.kwargs['data'].decode()
        self.assertIn(hashlib.sha256(b'selected runtime/emergency_trial.py').hexdigest(),source)
        self.assertNotIn('import deploy',source)
        self.assertNotIn('sys.path',source)

    @unittest.skipUnless(os.name=='posix','TV isolated process requires POSIX metadata')
    def test_wire_executes_real_isolated_stdlib_reader_and_refuses_old_bytes(self):
        import subprocess
        import sys
        from cytv.errors import UserError
        installed=self.payload/'tv';installed.mkdir(mode=0o700)
        for name in self.names:
            path=installed/name;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes((self.payload/'root'/name).read_bytes());path.chmod(0o600)
        def run(command, data, timeout):
            source=data.decode().replace("root='/var/lib/clean-your-tv-root', uid=0",'root='+repr(str(installed))+', uid='+str(os.getuid()))
            result=subprocess.run([sys.executable,'-I','-B','-'],input=source.encode(),capture_output=True,timeout=timeout,check=True)
            return result.stdout.decode()
        self.installer.remote.run.side_effect=run
        self.assertIsNone(self.verify())
        path=installed/'runtime/persistent_health.py';path.write_text('old valid runtime')
        with self.assertRaises(UserError) as caught:self.verify()
        self.assertEqual(caught.exception.reason_code,'installer-runtime-mismatch')
        self.assertEqual(path.read_text(),'old valid runtime')

    def test_changed_local_support_refuses_before_network(self):
        from cytv.errors import UserError
        (self.payload/'root/runtime/emergency_trial.py').write_text('changed')
        with self.assertRaises(UserError):self.verify()
        self.installer.remote.run.assert_not_called()

    def test_verified_private_python_is_reused_without_system_only_selection(self):
        selected = '/var/lib/clean-your-tv-python/verified/bin/python3.13'
        self.installer._python.return_value = selected
        self.installer._select_python = Mock(side_effect=AssertionError('System-only selection rejects private Python'))
        self.installer.remote.run.return_value = 'CYTV_SELECTED_RUNTIME_VERIFIED'
        self.verify()
        self.assertEqual(shlex.split(self.installer.remote.run.call_args.args[0]), [selected, '-I', '-B', '-'])
        self.installer._select_python.assert_not_called()

    def test_actual_mismatch_is_typed_and_transport_failure_is_preserved(self):
        from cytv.errors import UserError, TVCommandError
        self.installer.remote.run.return_value='CYTV_SELECTED_RUNTIME_MISMATCH\n'
        with self.assertRaises(UserError) as caught:self.verify()
        self.assertEqual(caught.exception.reason_code,'installer-runtime-mismatch')
        error=TVCommandError(1,storage_full=True);self.installer.remote.run.side_effect=error
        with self.assertRaises(TVCommandError) as caught:self.verify()
        self.assertIs(caught.exception,error)


@unittest.skipUnless(os.name=='posix','Fixed TV metadata reader requires POSIX')
class RuntimeContractReader(unittest.TestCase):
    def test_old_receipts_do_not_replace_selected_bytes_and_no_retained_code_executes(self):
        module=importlib.import_module('cytv.root_runtime_contract');namespace={}
        exec(module.PROGRAM,namespace)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();runtime=root/'runtime';runtime.mkdir(mode=0o700)
            marker=root/'executed';path=runtime/'emergency_trial.py'
            original=('open('+repr(str(marker))+',"w").write("bad")').encode()
            path.write_bytes(original);path.chmod(0o600)
            expected={'runtime/emergency_trial.py':hashlib.sha256(original).hexdigest()}
            self.assertTrue(namespace['matches'](expected,root,os.getuid()))
            path.write_bytes(b'old runtime')
            (root/'recovery-provision.json').write_text(json.dumps({'files':{str(path):hashlib.sha256(b'old runtime').hexdigest()}}))
            self.assertFalse(namespace['matches'](expected,root,os.getuid()))
            self.assertFalse(marker.exists());self.assertEqual(path.read_bytes(),b'old runtime')
            path.unlink();path.symlink_to(root/'recovery-provision.json')
            self.assertFalse(namespace['matches'](expected,root,os.getuid()))
