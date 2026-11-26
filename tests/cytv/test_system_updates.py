"""Computer bootstrap orchestration; only SSH is replaced by an in-memory TV."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from cytv import operations, package, state
from cytv.errors import UserError


class Remote:
    def __init__(self, root=True, confirmed=True):
        self.root, self.confirmed, self.calls = root, confirmed, []

    def run(self, command, **kwargs):
        self.calls.append(('run', command))
        if command == "LC_ALL=C stat -f -c '%t' /tmp":return 'ef53'
        if command.startswith('LC_ALL=C df -Pk '):
            return 'Filesystem 1024-blocks Used Available Capacity Mounted on\n/dev/test 10000000 0 10000000 0% /shared'
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
    def test_cleanup_streams_fixed_source_without_exceeding_ssh_command_limit(self):
        from unittest.mock import MagicMock
        from cytv.system_updater_remove import SCRIPT, COMMAND
        remote = Remote()
        remote.run = MagicMock(return_value='{"present":false}')
        installer = self.installer(remote)
        installer._python = lambda: '/opt/bin/python3'
        self.assertEqual(installer.system_updater_cleanup('status'), {'present':False})
        args, options = remote.run.call_args
        self.assertLess(len(args[0]), 8000)
        self.assertIn('/opt/bin/python3', args[0])
        self.assertEqual(options['data'], SCRIPT.encode())
        self.assertEqual(options['timeout'], 60)
        self.assertLess(len(COMMAND), 1024)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name).resolve()
        self.payload = self.path/'payload'
        bundle = self.payload/'system-updater'
        bundle.mkdir(parents=True)
        files={'setup-system-updater.py':b'# setup', 'system-updater.ipk':package.ipk('com.cleanyourtv.system.updater', '0.0.1', {'usr/palm/applications/com.cleanyourtv.system.updater/appinfo.json': b'{}'}), 'system_updater/core.py':b'# core'}
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

    def test_ramfs_low_ram_stops_before_receipt_or_upload(self):
        remote = Remote()
        original = remote.run
        def run(command, **kwargs):
            if command == "LC_ALL=C stat -f -c '%t' /tmp":return '858458f6'
            if command == "LC_ALL=C stat -f -c '%t' /var/lib":return 'ef53'
            if command == 'LC_ALL=C df -Pk /tmp':
                return 'Filesystem 1024-blocks Used Available Capacity Mounted on\nramfs 0 0 0 0% /tmp'
            if command == 'LC_ALL=C cat /proc/meminfo':return 'MemAvailable: 1 kB\n'
            if 'CYTV_ROOT_STAGE_READY' in command:return 'CYTV_ROOT_STAGE_READY'
            return original(command, **kwargs)
        remote.run = run
        with self.assertRaises(UserError) as caught:
            self.installer(remote).enable_system_updates()
        self.assertEqual(caught.exception.reason_code, 'tv-storage-full')
        self.assertIsNone(self.store.pending(self.profile))
        self.assertFalse(any(call[0] == 'upload' for call in remote.calls))
        self.assertFalse(any(call[0] == 'run' and 'setup-system-updater.py' in call[1] for call in remote.calls))

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

    def test_single_tile_rooted_no_root_resumes_only_unchanged_original(self):
        from unittest.mock import patch
        self.profile=state.target('192.0.2.10','no-root',connection='root-ssh')
        metadata=self.payload/'system-updater/bundle.json'
        fields=json.loads(metadata.read_text());fields['product_schema']=2
        metadata.write_text(json.dumps(fields))
        remote=Remote(confirmed=False)
        inst=self.installer(remote);inst.manifest['single_tile']={'version':'2.0.0'}
        with self.assertRaisesRegex(UserError,'confirmed'):inst.enable_system_updates()
        prior=self.store.pending(self.profile)
        self.assertEqual(prior['bootstrap_digest'],hashlib.sha256(json.dumps(fields,sort_keys=True,separators=(',',':')).encode()).hexdigest())
        before=len(remote.calls)
        original=remote.run
        def continued(command,**options):
            if 'setup-system-updater.py' in command:
                self.assertIn('--resume',command)
                self.assertIn(prior['support_upload'],command)
                if not remote.confirmed:raise RuntimeError('unknown submission outcome')
                return '{"installed":true,"edition":"no-root"}'
            return original(command,**options)
        remote.run=continued
        with patch('cytv.system_bootstrap.retained_stage',return_value=prior['support_upload']):
            with self.assertRaisesRegex(RuntimeError,'unknown submission'):
                inst.enable_system_updates()
            self.assertEqual(self.store.pending(self.profile),prior)
            metadata.write_text(json.dumps(dict(fields,engine_version='2.0.1')))
            with self.assertRaisesRegex(UserError,'integrity'):inst.enable_system_updates()
            metadata.write_text(json.dumps(fields))
            remote.confirmed=True
            self.assertTrue(inst.enable_system_updates()['installed'])
        self.assertIsNone(self.store.pending(self.profile))
        self.assertFalse(any(call[0]=='upload' for call in remote.calls[before:]))

    def test_reused_root_upload_rejects_changed_bytes_extra_files_and_links(self):
        import subprocess,sys
        from cytv.system_bootstrap import VERIFY
        # Non-root host fixture substitutes only the TV UID and parent chain.
        verify=VERIFY.replace('os.geteuid()!=0','False').replace('info.st_uid!=0','info.st_uid!=os.geteuid()')
        verify=verify.replace('reversed(stage.parents)','[stage.parent]')
        stage=self.path/'retained';stage.mkdir(mode=0o700)
        child=stage/'code';child.mkdir(mode=0o700)
        file=child/'setup';file.write_bytes(b'expected')
        expected=json.dumps({'code/setup':[8,hashlib.sha256(b'expected').hexdigest()]}).encode()
        def check():return subprocess.run([sys.executable,'-I','-B','-c',verify,str(stage)],input=expected,capture_output=True)
        self.assertEqual(check().stdout,b'verified\n')
        file.write_bytes(b'modified')
        self.assertNotEqual(check().returncode,0)
        file.write_bytes(b'expected');(stage/'extra').mkdir(mode=0o700)
        self.assertNotEqual(check().returncode,0)
        (stage/'extra').rmdir();(stage/'link').symlink_to(file)
        self.assertNotEqual(check().returncode,0)
        (stage/'link').unlink();file.unlink();child.rmdir();stage.rmdir()
        self.assertEqual(check().stdout,b'absent\n')

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

    def test_single_tile_host_reconciles_only_its_own_verified_bootstrap(self):
        from unittest.mock import Mock
        self.profile=state.target('192.0.2.10','no-root',connection='root-ssh')
        inst=self.installer(Remote())
        self.store.begin(self.profile,'enable-system-updates',stage='setup',bootstrap_digest='b'*64)
        report=dict(present=True,bootstrap_complete=True,disabled=False,ownership_verified=True,
                    edition='no-root',product_schema=2,bootstrap_digest='b'*64)
        for bad in (dict(report,edition='root'),dict(report,bootstrap_digest='e'*64),dict(report,product_schema=1)):
            inst.system_updater_cleanup=Mock(return_value=bad)
            self.assertIsNone(inst.status()['reconciled'])
            self.assertTrue(self.store.pending(self.profile))
        inst.system_updater_cleanup=Mock(return_value=report)
        self.assertEqual(inst.status()['reconciled'],'system-updater-bootstrap-verified')
        self.assertIsNone(self.store.pending(self.profile))

    def test_verified_not_started_bootstrap_releases_local_receipt(self):
        from unittest.mock import MagicMock
        self.store.begin(self.profile,'enable-system-updates',stage='setup')
        inst=self.installer(Remote())
        inst.system_updater_cleanup=MagicMock(return_value={'present':False})
        result=inst.status()
        self.assertEqual(result['reconciled'],'system-updater-not-started')
        self.assertIsNone(self.store.pending(self.profile))
