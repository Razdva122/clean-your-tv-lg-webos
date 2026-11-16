"""Interpreter selection at the SSH orchestration boundary."""
import json
import os
import unittest
from unittest.mock import patch
from cytv.operations import Installer, ROOT_STATE, _RETAINED_PYTHON_CHECK
from cytv.errors import UserError

MANAGED='/var/lib/clean-your-tv-python/4a71641c8d5536175e404a961624e8656eba30e97b5026f6bd7dc31e4bbeaaea/bin/python3.13'

class Remote:
    def __init__(self, failed=(), bound=False):
        self.failed=failed; self.bound=bound; self.calls=[]
    def run(self, command, **kwargs):
        self.calls.append(command)
        if 'CYTV_PYTHON_BOUND' in command:
            return 'CYTV_PYTHON_BOUND' if self.bound else ''
        if 'CYTV_ROOT_READY' in command:
            missing=any(v in command for v in self.failed)
            if '/usr/bin/python3' in command: missing=True
            return 'CYTV_ROOT_MISSING' if missing else 'CYTV_ROOT_READY'
        if 'install_driver.py inspect' in command:
            return json.dumps({'operation': None, 'state': 'installed', 'installation': {}})
        if 'deploy.py' in command:return json.dumps({'returnValue':True})
        return ''

class SelectionTests(unittest.TestCase):
    def test_install_selects_managed_python_and_rechecks_requirements(self):
        remote=Remote();installer=Installer(remote,None,{'edition':'root'},'.',{})
        with patch.object(installer,'_select_python',return_value=MANAGED,create=True) as select:
            installer.preflight(install=True)
        select.assert_called_once_with(provision=True)
        self.assertTrue(all(v=='pass' for v in installer.tv_info['root_requirements'].values()))
        installer.root_action('status')
        self.assertTrue(MANAGED+' ' in remote.calls[-1])
    def test_missing_node_never_provisions_python(self):
        installer=Installer(Remote(('/usr/bin/node',)),None,{'edition':'root'},'.',{})
        with patch.object(installer,'_select_python',create=True) as select:
            with self.assertRaises(UserError):installer.preflight(install=True)
        select.assert_not_called()
    def test_maintenance_prefers_existing_binding_without_provisioning(self):
        remote=Remote(bound=True);installer=Installer(remote,None,{'edition':'root'},'.',{})
        with (patch.object(installer, '_select_python', create=True) as select,
              patch.object(installer, 'coordinator_code', return_value='/tmp/cytv-coordinator')):
            installer.restore_device()
        select.assert_not_called()
        self.assertIn('"$cytv_state" restore', remote.calls[0])
        self.assertIn(MANAGED + ' -B /tmp/cytv-coordinator/install_driver.py inspect', remote.calls[1])
        self.assertIn(MANAGED + ' /var/lib/clean-your-tv-root/deploy.py restore', remote.calls[2])

    def test_restore_does_not_inspect_or_execute_a_rejected_binding(self):
        remote = Remote()
        remote.run = lambda *_args, **_kwargs: 'CYTV_PYTHON_INVALID'
        installer = Installer(remote, None, {'edition':'root'}, '.', {})
        with (patch.object(installer, 'root_installation') as inspect,
              patch.object(installer, 'root_action') as restore):
            with self.assertRaisesRegex(UserError, 'Retained Python binding'):
                installer.restore_device()
        inspect.assert_not_called()
        restore.assert_not_called()
    def test_diagnostics_do_not_provision_missing_python(self):
        installer=Installer(Remote(),None,{'edition':'root'},'.',{})
        with patch.object(installer,'_select_python',create=True) as select:
            with self.assertRaises(UserError):installer.preflight()
        select.assert_not_called()

    def test_reconnected_removal_uses_its_archived_binding(self):
        from types import SimpleNamespace
        archive='/var/lib/clean-your-tv-system-updater.archive-'+'a'*32
        remote=Remote();original=remote.run
        def run(command,**kwargs):
            if 'CYTV_PYTHON_BOUND' in command and archive in command:return 'CYTV_PYTHON_BOUND'
            return original(command,**kwargs)
        remote.run=run
        store=SimpleNamespace(pending=lambda profile:{'action':'uninstall','system_updater_archive':archive})
        installer=Installer(remote,store,{'edition':'no-root'},'.',{})
        with patch.object(installer,'_select_python',create=True) as select:
            self.assertEqual(installer._python(),MANAGED)
        select.assert_not_called()

    def test_system_module_or_process_failure_triggers_install_fallback(self):
        remote=Remote();original=remote.run
        def run(command,**kwargs):
            if 'CYTV_ROOT_READY' in command:
                return 'CYTV_ROOT_MISSING' if 'cytv-child' in command and '/usr/bin/python3' in command else 'CYTV_ROOT_READY'
            return original(command,**kwargs)
        remote.run=run;installer=Installer(remote,None,{'edition':'root'},'.',{})
        with patch.object(installer,'_select_python',return_value=MANAGED) as select:
            installer.preflight(install=True)
        select.assert_called_once_with(provision=True)

    @unittest.skipUnless(os.name == 'posix', 'TV validator fixture requires POSIX paths and shell')
    def test_modified_retained_interpreter_never_executes_before_hash_check(self):
        import hashlib
        import shutil
        import shlex
        import subprocess
        import tempfile
        from pathlib import Path
        from types import SimpleNamespace
        node=shutil.which('node')
        if node is None:self.skipTest('Node is required for the TV binding validator')
        for archived in (False,True):
            with self.subTest(archived=archived),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp).resolve();state=root/'state';state.mkdir(mode=0o700)
                executable=root/'runtime'/MANAGED.split('/')[-3]/'bin/python3.13';executable.parent.mkdir(parents=True)
                original=b'original pinned interpreter bytes';executable.write_bytes(original);executable.chmod(0o700)
                inventory=json.dumps({'schema':1,'archive_sha256':MANAGED.split('/')[-3],'files':{'bin/python3.13':hashlib.sha256(original).hexdigest()}}).encode()
                (executable.parents[1]/'.cytv-runtime.json').write_bytes(inventory)
                (state/'python-launcher').write_text('#!/bin/sh\nunset PYTHONHOME PYTHONPATH\nexport PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1\nexec '+str(executable)+' "$@"\n');(state/'python-launcher').chmod(0o700)
                (state/'python-runtime.json').write_text(json.dumps({'schema':1,'executable':str(executable),'archive_sha256':MANAGED.split('/')[-3],'inventory_sha256':hashlib.sha256(inventory).hexdigest()}))
                helper=state/'python_binding.py';helper.write_bytes((Path(__file__).resolve().parents[2]/'root-edition/python_binding.py').read_bytes())
                marker=root/'executed'
                executable.write_text('#!/bin/sh\ntouch '+shlex.quote(str(marker))+'\nprintf CYTV_PYTHON_BOUND\n')
                # Only root ownership metadata is virtualized. Node still reads and
                # hashes the actual receipt, inventory and substituted executable.
                bootstrap=root/'root-metadata.js'
                bootstrap.write_text("var f=require('fs'),s=f.lstatSync;f.lstatSync=function(p){var v=s.apply(f,arguments);v.uid=0;if(!String(p).startsWith("+json.dumps(str(root))+"))v.mode&=~18;return v;};")
                wrapper=root/'node';wrapper.write_text('#!/bin/sh\nexec '+shlex.quote(node)+' --require '+shlex.quote(str(bootstrap))+' "$@"\n');wrapper.chmod(0o700)
                location=ROOT_STATE+'.archive-'+'a'*32 if archived else ROOT_STATE
                class LocalRemote:
                    def run(self,command,**kwargs):
                        if location not in command:return ''
                        command=command.replace(MANAGED,str(executable)).replace('/var/lib/clean-your-tv-python',str(root/'runtime')).replace(location,str(state)).replace('/usr/bin/node',shlex.quote(str(wrapper)))
                        metadata='stat() { case "$2" in %u) printf 0;; %a) printf 700;; %h) printf 1;; esac; }; '
                        result=subprocess.run(['sh','-c',metadata+command],capture_output=True,text=True,check=True)
                        return result.stdout
                store=SimpleNamespace(pending=lambda profile:{'action':'archive-root-state','archive':location}) if archived else None
                installer=Installer(LocalRemote(),store,{'edition':'root'},'.',{})
                try:
                    installer._python();rejected=False
                except UserError:
                    rejected=True
                self.assertFalse(marker.exists(),'unverified retained interpreter ran before its hash was checked')
                self.assertTrue(rejected,'modified retained interpreter was not rejected')
                # Control: identical safe metadata with matching bytes reaches the
                # executable, proving rejection above came from pre-execution hashing.
                allowed=json.loads(inventory);allowed['files']['bin/python3.13']=hashlib.sha256(executable.read_bytes()).hexdigest()
                allowed_raw=json.dumps(allowed).encode();(executable.parents[1]/'.cytv-runtime.json').write_bytes(allowed_raw)
                receipt=state/'python-runtime.json';saved=json.loads(receipt.read_bytes());saved['inventory_sha256']=hashlib.sha256(allowed_raw).hexdigest();receipt.write_text(json.dumps(saved))
                self.assertEqual(installer._python(),MANAGED)
                self.assertTrue(marker.exists(),'valid matching fixture never reached its interpreter')


    @unittest.skipUnless(os.name == 'posix', 'TV validator fixture requires POSIX paths')
    def test_restore_retires_only_generated_cache_from_verified_runtime(self):
        import hashlib
        import shutil
        import subprocess
        import tempfile
        from pathlib import Path

        node = shutil.which('node')
        if node is None:
            self.skipTest('Node is required for the TV binding validator')
        pin = MANAGED.split('/')[-3]
        for scenario in ('passive', 'restore', 'changed', 'missing', 'foreign', 'symlink', 'hardlink'):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                state = root / 'state'
                state.mkdir()
                slot = root / 'runtime' / pin
                files = {'bin/python3.13': b'fixture', 'lib/module.py': b'pass'}
                for name, content in files.items():
                    path = slot / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(content)
                inventory = json.dumps({
                    'schema': 1, 'archive_sha256': pin,
                    'files': {name: hashlib.sha256(content).hexdigest() for name, content in files.items()},
                }).encode()
                (slot / '.cytv-runtime.json').write_bytes(inventory)
                executable = slot / 'bin/python3.13'
                launcher = state / 'python-launcher'
                launcher.write_text('#!/bin/sh\nunset PYTHONHOME PYTHONPATH\n'
                    'export PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1\n'
                    f'exec {executable} "$@"\n')
                launcher.chmod(0o700)
                (state / 'python-runtime.json').write_text(json.dumps({
                    'schema': 1, 'archive_sha256': pin, 'executable': str(executable),
                    'inventory_sha256': hashlib.sha256(inventory).hexdigest(),
                }))
                cache = slot / 'lib/__pycache__/module.cpython-313.pyc'
                cache.parent.mkdir()
                if scenario == 'symlink':
                    cache.symlink_to(slot / 'lib/module.py')
                elif scenario == 'hardlink':
                    os.link(slot / 'lib/module.py', cache)
                else:
                    cache.write_bytes(b'generated cache')
                if scenario == 'changed':
                    (slot / 'lib/module.py').write_bytes(b'changed')
                if scenario == 'missing':
                    (slot / 'lib/module.py').unlink()
                if scenario == 'foreign':
                    (cache.parent / 'unknown.cpython-313.pyc').touch()
                bootstrap = """var fs=require('fs'),stat=fs.lstatSync;
fs.lstatSync=function(p){var item=stat.apply(fs,arguments);
item.uid=0;if(String(p).indexOf(ROOT)!==0)item.mode&=~18;return item;};
""".replace('ROOT', json.dumps(str(root)))
                source = bootstrap + _RETAINED_PYTHON_CHECK.replace('/var/lib/clean-your-tv-python', str(root / 'runtime'))
                args = [node, '-e', source, str(state)]
                if scenario != 'passive':
                    args.append('restore')
                result = subprocess.run(args, capture_output=True)
                self.assertEqual(result.returncode, 0 if scenario in ('passive', 'restore') else 1)
                self.assertEqual(cache.exists(), scenario != 'restore')
                if scenario == 'restore':
                    subprocess.run(args, check=True, capture_output=True)
                    for name, content in files.items():
                        self.assertEqual((slot / name).read_bytes(), content)
