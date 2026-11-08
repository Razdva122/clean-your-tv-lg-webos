"""Computer bootstrap orchestration; only SSH is replaced by an in-memory TV."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from cytv import operations, state
from cytv.errors import UserError


class Remote:
    def __init__(self, root=True, confirmed=True):
        self.root, self.confirmed, self.calls = root, confirmed, []

    def run(self, command, **kwargs):
        self.calls.append(('run', command))
        if 'CYTV_PYTHON_READY' in command:return 'CYTV_PYTHON_READY'
        if 'CYTV_SYSTEM_ROOT_READY' in command:
            return 'CYTV_SYSTEM_ROOT_READY' if self.root else ''
        if 'setup-system-updater.py' in command:
            return json.dumps({'installed': self.confirmed})
        return ''

    def upload(self, path, raw, mode=0o600):
        self.calls.append(('upload', path, raw, mode))

    def luna(self, uri, payload, **kwargs):
        self.calls.append(('luna', uri, payload))
        return {'returnValue':True, 'result':None}


class SystemBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name).resolve()
        self.payload = self.path/'payload'
        bundle = self.payload/'system-updater'
        bundle.mkdir(parents=True)
        files={'setup-system-updater.py':b'# setup', 'system-updater.ipk':b'ipk', 'system_updater/core.py':b'# core'}
        for name, raw in files.items():
            target=bundle/name;target.parent.mkdir(parents=True, exist_ok=True);target.write_bytes(raw)
        (bundle/'bundle.json').write_text(json.dumps({'schema':1,'supervisor':1,'files':{n:hashlib.sha256(b).hexdigest() for n,b in files.items()}}))
        self.store=state.Store(self.path/'state')
        self.profile=state.target('192.0.2.10','root')

    def installer(self, remote):
        return operations.Installer(remote,self.store,self.profile,self.payload,{},progress=lambda _:None)

    def test_native_bootstrap_does_not_leave_bytecode_in_verified_staging(self):
        import shlex,subprocess,sys
        from unittest.mock import patch
        work=self.path/'native-stage';work.mkdir()
        (work/'dependency.py').write_text('value=True')
        entry=work/'setup-system-updater.py'
        entry.write_text("import json,sys;from pathlib import Path;sys.path.insert(0,str(Path(__file__).parent));import dependency;print(json.dumps({'installed':dependency.value}))")
        remote=Remote();original=remote.run
        def run(command,**kwargs):
            if 'setup-system-updater.py' not in command:return original(command,**kwargs)
            args=shlex.split(command);index=next(i for i,a in enumerate(args) if a.endswith('/setup-system-updater.py'))
            return subprocess.check_output([*args[:index],str(entry)],text=True)
        remote.run=run
        installer=self.installer(remote)
        with patch.object(installer,'_python',return_value=sys.executable):
            self.assertTrue(installer.enable_system_updates()['installed'])
        self.assertFalse((work/'__pycache__').exists(),'Native bootstrap created an unclassified cache that blocks full removal')

    def test_bootstrap_uploads_verified_bundle_without_reinstalling_home(self):
        remote=Remote();result=self.installer(remote).enable_system_updates()
        self.assertTrue(result['installed'])
        uploads=[c for c in remote.calls if c[0]=='upload']
        self.assertEqual(len(uploads),4)
        self.assertTrue(all(c[3]==0o600 for c in uploads))
        command=next(c[1] for c in remote.calls if c[0]=='run' and 'setup-system-updater.py' in c[1])
        self.assertIn('--edition root --device --apply',command)
        self.assertFalse(any(c[0]=='luna' and '/install' in c[1] for c in remote.calls))
        self.assertIsNone(self.store.pending(self.profile))

    def test_explicit_disabled_completion_unlocks_separate_bootstrap_and_keeps_original(self):
        from unittest.mock import MagicMock
        self.store.begin(self.profile,'activate-root',stage='enable',product_operation='a'*32,baseline_sha='b'*64)
        original=self.store.pending(self.profile)
        remote=Remote();inst=self.installer(remote)
        with self.assertRaisesRegex(UserError,'unresolved'):inst.enable_system_updates()
        self.assertEqual(remote.calls,[])
        # Eligibility itself is exercised with real journals/locks in Root proof tests.
        inst.observe_recovery=MagicMock(return_value={'can_resume_root_setup':True})
        self.assertEqual(inst.finish_root_setup_disabled()['home_control'],'disabled')
        self.assertEqual(remote.calls,[])
        archived=list(self.store.device_dir(self.profile).glob('recovery-*.json'))
        self.assertEqual(json.loads(archived[0].read_text())['previous'],original)
        self.assertTrue(inst.enable_system_updates()['installed'])
        self.assertIsNone(self.store.pending(self.profile))
        self.assertEqual(json.loads(archived[0].read_text())['previous'],original)
        self.assertFalse(any(c[0]=='luna' or c[0]=='run' and ' enable' in c[1] for c in remote.calls))

    def test_unrooted_or_corrupt_bundle_never_uploads(self):
        remote=Remote(root=False)
        with self.assertRaisesRegex(UserError,'root'):self.installer(remote).enable_system_updates()
        self.assertFalse(any(c[0]=='upload' for c in remote.calls))
        (self.payload/'system-updater/system_updater/core.py').write_bytes(b'tampered')
        remote=Remote()
        with self.assertRaisesRegex(UserError,'integrity'):self.installer(remote).enable_system_updates()
        self.assertFalse(remote.calls)

    @unittest.skipUnless(os.name == 'posix', 'macOS/POSIX payload aliases')
    def test_packaged_payload_root_alias_is_supported(self):
        # PyInstaller uses a Frameworks -> Resources alias in macOS apps;
        # one-file extraction may also use macOS /var -> /private/var.
        framework = self.path/'Frameworks'
        framework.mkdir()
        alias = framework/'payload'
        alias.symlink_to(self.payload, target_is_directory=True)
        remote = Remote()
        installer = operations.Installer(remote, self.store, self.profile, alias, {}, progress=lambda _: None)
        self.assertTrue(installer.enable_system_updates()['installed'])
        self.assertTrue(any(c[0] == 'upload' for c in remote.calls))

    @unittest.skipUnless(os.name == 'posix', 'POSIX symlink tampering')
    def test_link_inside_payload_is_rejected_before_tv_access(self):
        target = self.payload/'system-updater/system_updater/core.py'
        external = self.path/'external.py'
        external.write_bytes(target.read_bytes())
        target.unlink()
        target.symlink_to(external)
        remote = Remote()
        with self.assertRaisesRegex(UserError, 'integrity'):
            self.installer(remote).enable_system_updates()
        self.assertFalse(remote.calls)

    def test_unconfirmed_bootstrap_retains_receipt_and_blocks_retry(self):
        remote=Remote(confirmed=False)
        with self.assertRaisesRegex(UserError,'confirmed'):self.installer(remote).enable_system_updates()
        self.assertEqual(self.store.pending(self.profile)['action'],'enable-system-updates')
        before=len(remote.calls)
        with self.assertRaisesRegex(UserError,'unresolved'):self.installer(remote).enable_system_updates()
        self.assertEqual(len(remote.calls),before)

    def test_lost_bootstrap_reply_reconciles_only_verified_complete_setup(self):
        from unittest.mock import MagicMock
        for complete in (False,True):
            with self.subTest(complete=complete):
                self.store.begin(self.profile,'enable-system-updates',stage='setup')
                inst=self.installer(Remote())
                inst.system_updater_cleanup=MagicMock(return_value={'present':True,'bootstrap_complete':complete,'disabled':False})
                result=inst.status()
                self.assertEqual(result['reconciled'],'system-updater-bootstrap-verified' if complete else None)
                self.assertEqual(self.store.pending(self.profile) is None,complete)
                if not complete:self.store.finish(self.profile)

    def test_verified_not_started_bootstrap_releases_local_receipt(self):
        from unittest.mock import MagicMock
        self.store.begin(self.profile,'enable-system-updates',stage='setup')
        inst=self.installer(Remote())
        inst.system_updater_cleanup=MagicMock(return_value={'present':False})
        result=inst.status()
        self.assertEqual(result['reconciled'],'system-updater-not-started')
        self.assertIsNone(self.store.pending(self.profile))
