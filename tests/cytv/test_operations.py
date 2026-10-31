"""Exercise real orchestration; only the remote SSH boundary is simulated."""
import json
import shlex
from pathlib import Path
import tempfile
import unittest

from cytv import operations, package, state


class Remote:
    def __init__(self, fail=None):
        self.calls, self.fail = [], fail
        self.uploads = {}
        self.installed = []
        self.active = {'recovery': {'integrity_verified': True}, 'intent': {'enabled': True, 'phase': 'active'}, 'guardian_active': True, 'effective': {'sam_home': package.ROOT_APP, 'profiles': {'idleApp': {'appId': package.ROOT_APP}, 'defaultApps': {'categories': {'home': package.ROOT_APP}}}}}

    def run(self, command, data=None, timeout=30):
        self.calls.append(('run', command))
        if 'CYTV_NODE_READY' in command: return 'CYTV_NODE_READY'
        if 'CYTV_HELPER_IDLE' in command: return 'CYTV_HELPER_IDLE'
        if command == 'uname -m':
            return 'armv7l'
        if command == 'LC_ALL=C od -An -v -t u1 -N 20 /bin/sh':
            return '127 69 76 70 1 1 1 0 0 0 0 0 0 0 0 0 2 0 40 0'
        if 'CYTV_ROOT_STATE' in command:
            return ''
        if 'CYTV_ROOT_READY' in command:
            return 'CYTV_ROOT_READY'
        if 'install_driver.py' in command:
            words=shlex.split(command)
            action=words[next(i for i,w in enumerate(words) if w.endswith('/install_driver.py'))+1]
            operation=words[words.index('--operation')+1] if '--operation' in words else None
            if action=='inspect': return json.dumps({'operation':None,'state':'fresh','installation':{'state':'fresh','can_maintain':False}})
            if self.fail=='deploy': raise RuntimeError('connection interrupted')
            if self.fail=='updater': return json.dumps({'operation':operation,'state':'recovery_required','stage':'root-updater','code':'installation_requires_recovery'})
            payload=words[words.index('--payload')+1] if '--payload' in words else next(path[:-len('/root/bundle.json')] for path in self.uploads if path.endswith('/root/bundle.json'))
            manifest=json.loads(self.uploads[payload+'/root/bundle.json'])
            import hashlib
            baseline=hashlib.sha256(self.uploads[payload+'/root/'+manifest['package']]).hexdigest()
            return json.dumps({'operation':operation,'current':True,'state':'complete','stage':'complete','code':'verified','result':{'installed':package.ROOT_APP,'home_changed':False,'verified':True,'baseline_sha':baseline}})
        if 'setup-updater.py' in command:
            if self.fail == 'updater': raise RuntimeError('updater setup interrupted')
            return json.dumps({'installed': True})
        if 'CYTV_UPDATER_VERIFIED' in command: return 'CYTV_UPDATER_VERIFIED'
        if 'deploy.py' in command:
            if self.fail == 'deploy':
                raise RuntimeError('connection interrupted')
            if command.endswith(' enable'):
                if self.fail == 'enable': raise RuntimeError('lost enable acknowledgement')
                return json.dumps({'returnValue': True, 'result': {'persistent': True}})
            if command.endswith(' status'):
                return json.dumps({'returnValue': True, 'result': self.active})
            return json.dumps({'returnValue': True, 'installed': package.ROOT_APP, 'home_changed': False})
        return ''

    def upload(self, path, data, mode=0o600):
        self.calls.append(('upload', path, mode))
        self.uploads[path]=data

    def luna(self, uri, payload, terminal=None, timeout=30, app_id=None):
        self.calls.append(('luna', uri, payload))
        if uri == 'com.cleanyourtv.root.updater.service/status':
            if self.fail == 'updater-service': raise RuntimeError('updater service unavailable')
            return {'returnValue': True, 'result': None}
        if uri.endswith('/dev/listApps'):
            return {'returnValue': True, 'apps': list(self.installed)}
        if uri.endswith('/install'):
            if self.fail == payload['id']:
                raise RuntimeError('no terminal reply')
            self.installed.append({'id': payload['id'], 'version': '0.6.13' if payload['id'] == operations.HELPER else '1.2.2'})
            return {'returnValue': True, 'details': {'state': 'installed'}}
        if uri.endswith('/disable'):
            return {'returnValue': True, 'cancel': {'returnValue': True}}
        return {'returnValue': True}


class OperationTests(unittest.TestCase):
    def test_new_recovery_attempt_reaches_only_explicit_program(self):
        from unittest.mock import MagicMock, patch
        remote = MagicMock(); remote.root = True
        remote.run.return_value = json.dumps({'returnValue':True, 'result':{'phase':'rolled-back', 'homeResumePhase':'rolled-back'}})
        store = MagicMock(); store.pending.return_value = None
        installer = operations.Installer(remote, store, {'edition':'root'}, Path('/unused'), {}, lambda *_:None)
        with patch.object(installer, '_python', return_value='/verified/python'), patch('cytv.system_rollback_recovery.program', return_value='explicit new attempt') as program:
            installer.recover_system_rollback(new_attempt=True)
        program.assert_called_once_with(new_attempt=True)
        self.assertEqual(remote.run.call_args.kwargs['data'], b'explicit new attempt')

    def test_system_rollback_recovery_streams_trusted_program_and_requires_complete_reply(self):
        from unittest.mock import MagicMock, patch
        from cytv.errors import UserError
        remote = MagicMock(); remote.root = True
        store = MagicMock(); store.pending.return_value = None
        installer = operations.Installer(remote, store, {'edition':'root'}, Path('/unused'), {}, lambda *_:None)
        for reply, accepted in [({'returnValue':True,'result':{'phase':'rolled-back','homeResumePhase':'rolled-back'}},True), ({'returnValue':True,'result':{'phase':'recovery-required'}},False), ({'returnValue':False},False)]:
            with self.subTest(reply=reply), patch.object(installer, '_python', return_value='/verified/python') as python:
                remote.run.return_value = json.dumps(reply)
                if accepted: installer.recover_system_rollback()
                else:
                    with self.assertRaises(UserError): installer.recover_system_rollback()
                python.assert_called_once_with(operations.SYSTEM_UPDATER_STATE)
                args, kwargs = remote.run.call_args
                self.assertLess(len(args[0]), 512)
                self.assertIn('-I -B -', args[0])
                self.assertIn(b'def recover(', kwargs['data'])
                self.assertGreaterEqual(kwargs['timeout'], 180)
        remote.reset_mock(); store.pending.return_value = {'phase':'unknown'}
        with self.assertRaises(UserError): installer.recover_system_rollback()
        remote.run.assert_not_called()
        store.pending.return_value = None; remote.root = False
        with self.assertRaises(UserError): installer.recover_system_rollback()
        remote.run.assert_not_called()

    def test_failed_python_provisioning_stops_before_the_root_install_receipt(self):
        import subprocess, sys
        remote = Remote()
        original_run = remote.run
        def run(command, **kwargs):
            if 'CYTV_PYTHON_BOUND' in command:return ''
            if 'CYTV_ROOT_READY' in command and 'version_info' in command:
                args = shlex.split(command)
                snippet = args[args.index('-c')+1]
                result = subprocess.run([sys.executable, '-c',
                    'import sys; sys.version_info=(3,8,10); exec('+repr(snippet)+')'], capture_output=True)
                return 'CYTV_ROOT_READY' if result.returncode == 0 else 'CYTV_ROOT_MISSING'
            return original_run(command, **kwargs)
        remote.run = run
        installer = self.installer(remote, 'root')
        from unittest.mock import patch
        with patch.object(installer,'_select_python',side_effect=RuntimeError('python-version unavailable')), self.assertRaisesRegex(RuntimeError,'python-version'):
            installer.install(self.inventory)
        self.assertIsNone(self.store.pending(installer.profile))
        self.assertFalse(any(c[0] == 'upload' for c in remote.calls))

    def test_missing_python_root_install_uses_selected_python_through_activation(self):
        from unittest.mock import patch
        self.root_bundle()
        remote=Remote();original=remote.run
        selected='/var/lib/clean-your-tv-python/4a71641c8d5536175e404a961624e8656eba30e97b5026f6bd7dc31e4bbeaaea/bin/python3.13'
        def run(command,**kwargs):
            if 'CYTV_ROOT_READY' in command and '/usr/bin/python3' in command:return 'CYTV_ROOT_MISSING'
            return original(command,**kwargs)
        remote.run=run;installer=self.installer(remote,'root')
        with patch.object(installer,'_select_python',return_value=selected) as select:
            result=installer.install(self.inventory)
        select.assert_called_once_with(provision=True)
        self.assertTrue(result['updates_ready'])
        commands=[call[1] for call in remote.calls if call[0]=='run' and any(marker in call[1] for marker in ('deploy.py','setup-updater.py','CYTV_UPDATER_VERIFIED','require_idle'))]
        self.assertTrue(commands)
        self.assertTrue(all(selected in command and 'PYTHONDONTWRITEBYTECODE=1' in command for command in commands))
        self.assertIsNone(self.store.pending(installer.profile))

    def test_no_root_rejects_node_below_01025_before_creating_a_receipt(self):
        import subprocess
        remote = Remote()
        original_run = remote.run
        def run(command, **kwargs):
            if 'CYTV_PYTHON_BOUND' in command:return ''
            if 'CYTV_NODE_READY' in command:
                args = shlex.split(command)
                snippet = args[args.index('-e')+1]
                result = subprocess.run(['node', '-e',
                    "Object.defineProperty(process.versions,'node',{value:'0.10.24'});"+snippet], capture_output=True)
                return 'CYTV_NODE_READY' if result.returncode == 0 else ''
            return original_run(command, **kwargs)
        remote.run = run
        installer = self.installer(remote)
        with self.assertRaisesRegex(RuntimeError, 'Node.js 0.10.25'):
            installer.install(self.inventory, 'secret')
        self.assertIsNone(self.store.pending(installer.profile))
        self.assertFalse(any(c[0] == 'upload' for c in remote.calls))

    def test_helper_node_gate_accepts_01025_and_later(self):
        import subprocess
        for version, allowed in [('0.8.28', False), ('0.10.24', False), ('0.10.25', True),
                                 ('0.10.48', True), ('0.12.0', True), ('0.12.2', True),
                                 ('0.12.18', True), ('8.12.0', True), ('10.24.1', True)]:
            with self.subTest(version=version):
                remote = Remote()
                original_run = remote.run
                def run(command, **kwargs):
                    if 'CYTV_NODE_READY' in command:
                        args = shlex.split(command)
                        snippet = args[args.index('-e')+1]
                        result = subprocess.run(['node', '-e',
                            "Object.defineProperty(process.versions,'node',{value:"+repr(version)+"});"+snippet], capture_output=True)
                        return 'CYTV_NODE_READY' if result.returncode == 0 else ''
                    return original_run(command, **kwargs)
                remote.run = run
                installer = self.installer(remote)
                if allowed:
                    installer.preflight(install=True)
                else:
                    with self.assertRaisesRegex(RuntimeError, 'Node.js 0.10.25'):
                        installer.preflight(install=True)

    @unittest.skipIf(__import__('os').name == 'nt', 'TV staging uses a POSIX shell')
    def test_install_staging_is_readable_by_a_separate_installer_uid(self):
        import subprocess
        from cytv.transport import SSH
        remote = Remote()
        original_run = remote.run
        temp = self.root / 'developer-temp'
        temp.mkdir(mode=0o700)  # May have been created by an older installer.
        def execute(command, data=None, timeout=30):
            result = subprocess.run(['sh', '-c', command.replace('/media/developer/temp', str(temp))],
                                    input=data, capture_output=True, check=True)
            return result.stdout.decode()
        def run(command, **kwargs):
            if 'CYTV_PYTHON_BOUND' in command:return ''
            if '/media/developer/temp' in command:
                return execute(command, **kwargs)
            return original_run(command, **kwargs)
        remote.run = run
        ssh = object.__new__(SSH)
        ssh.run = execute
        original_upload = remote.upload
        def upload(path, data, mode=0o600):
            if path.startswith('/media/developer/temp/'):
                ssh.upload(path, data, mode)
            else:
                original_upload(path, data, mode)
        remote.upload = upload
        original_luna = remote.luna
        def luna(uri, payload, **kwargs):
            if uri.endswith('/install'):
                path = Path(payload['ipkUrl'].replace('/media/developer/temp', str(temp)))
                self.assertTrue(path.is_file())
                for directory in (temp, path.parent):
                    mode = directory.stat().st_mode & 0o777
                    self.assertTrue(mode & 0o001, 'backend UID cannot traverse '+str(directory))
                    self.assertEqual(mode & 0o022, 0, 'staging must not be writable by other users')
                self.assertTrue(path.stat().st_mode & 0o004, 'backend UID cannot read IPK')
            return original_luna(uri, payload, **kwargs)
        remote.luna = luna
        self.installer(remote).install(self.inventory, 'secret')
        self.assertEqual(list(temp.iterdir()), [])

    def test_pending_no_root_removal_resumes_after_restore_interruption(self):
        installer = self.installer(Remote())
        self.store.begin(installer.profile, 'uninstall')
        self.assertIsNotNone(installer.status()['pending'])
        original = installer.remote.luna
        def luna(uri, payload, **kwargs):
            if uri == 'com.webos.appInstallService/status':
                return {'returnValue': True, 'status': {'apps': []}}
            return original(uri, payload, **kwargs)
        installer.remote.luna = luna
        installer.uninstall()
        self.assertIsNone(self.store.pending(installer.profile))
        self.assertTrue(any(call[0] == 'luna' and call[1].endswith('/launch')
                            and call[2]['id'] == 'com.webos.app.home' for call in installer.remote.calls))

    def test_denied_helper_disable_restores_then_resumes_pending_removal(self):
        from cytv.errors import TVRejected
        remote = Remote()
        remote.installed = [{'id': operations.HELPER}, {'id': operations.HOME}]
        original_luna, original_run = remote.luna, remote.run
        def luna(uri, payload, **kwargs):
            if uri.endswith('/disable'):
                raise TVRejected('denied', {'returnValue': False, 'errorCode': -1}, uri)
            if uri == 'com.webos.appInstallService/status':
                return {'returnValue': True, 'status': {'apps': []}}
            if uri.endswith('/dev/remove'):
                remote.calls.append(('luna', uri, payload))
                remote.installed = [app for app in remote.installed if app['id'] != payload['id']]
                return {'returnValue': True, 'details': {'state': 'removed'}}
            return original_luna(uri, payload, **kwargs)
        def run(command, data=None, **kwargs):
            if command == '/usr/bin/node':
                self.assertIn(b'CYTV_HELPER_STOP_REQUESTED', data)
                return 'CYTV_HELPER_STOP_REQUESTED'
            return original_run(command, **kwargs)
        remote.luna, remote.run = luna, run
        installer = self.installer(remote)
        self.store.begin(installer.profile, 'uninstall')
        self.assertTrue(installer.restore()['restored'])
        self.assertEqual(self.store.pending(installer.profile)['action'], 'uninstall')
        installer.uninstall()
        self.assertIsNone(self.store.pending(installer.profile))
        removals = [c[2]['id'] for c in remote.calls if c[0] == 'luna' and c[1].endswith('/dev/remove')]
        self.assertEqual(removals, [operations.HELPER, operations.HOME])

    def test_version_review_distinguishes_update_reinstall_downgrade_and_missing(self):
        for current, expected in [('1.2.1', '1.2.1 → 1.2.2 (Update)'),
                                  ('1.2.2', '1.2.2 → 1.2.2 (Reinstall)'),
                                  ('1.10.0', '1.10.0 → 1.2.2 (Downgrade)'),
                                  (None, 'Not installed → 1.2.2 (Install)'),
                                  ('', 'Unknown version → 1.2.2 (Version change)')]:
            with self.subTest(current=current):
                remote = Remote()
                if current is not None:
                    remote.installed = [{'id': operations.HOME, 'version': current}]
                rows = self.installer(remote).version_summary()
                self.assertIn('Home: ' + expected, rows)
                self.assertIn('Home Helper: Not installed → 0.6.13 (Install)', rows)
                self.assertTrue(all(call[0] == 'luna' and call[1].endswith('/listApps') for call in remote.calls))

    def test_root_version_review_reads_versions_from_bundled_packages(self):
        installer = self.installer(Remote(), 'root')
        root = self.payload / 'root'
        root.mkdir(exist_ok=True)
        (root / 'release.json').write_text('{"version":"0.1.5"}')
        updater = self.payload / 'root-updater'
        updater.mkdir(exist_ok=True)
        app = operations.UPDATER_APP
        (updater / 'root-updater.ipk').write_bytes(package.ipk(app, '0.1.6', {
            'usr/palm/applications/' + app + '/appinfo.json': b'{"version":"0.1.6"}'}))
        installer.remote.installed = [{'id': package.ROOT_APP, 'version': '0.1.4'},
                                      {'id': app, 'version': '0.1.5'}]
        self.assertEqual(installer.version_summary(), ['Root: 0.1.4 → 0.1.5 (Update)',
                                                     'Root Updater: 0.1.5 → 0.1.6 (Update)'])

    def test_doctor_requirements_allow_a_running_helper(self):
        remote = Remote()
        run = remote.run
        remote.run = lambda command, **kwargs: 'CYTV_HELPER_ACTIVE' if '/controller.pid' in command else run(command, **kwargs)
        self.installer(remote).preflight()

    def test_existing_root_is_refused_before_creating_new_receipt(self):
        remote = Remote()
        run = remote.run
        remote.run = lambda command, **kwargs: 'CYTV_EXISTING_ROOT' if 'CYTV_EXISTING_ROOT' in command else run(command, **kwargs)
        installer = self.installer(remote, 'root')
        with self.assertRaisesRegex(RuntimeError, 'already installed'):
            installer.install(self.inventory)
        self.assertIsNone(self.store.pending(installer.profile))

    def test_root_reinstall_rejects_bad_inventory_before_removing_old_root(self):
        remote = Remote()
        installer = self.installer(remote, 'root')
        with self.assertRaisesRegex(ValueError, 'No usable apps'):
            installer.install({'apps':[], 'inputs':[]}, reinstall='installed')
        self.assertEqual(remote.calls, [])
        self.assertIsNone(self.store.pending(installer.profile))

    def test_root_reinstall_cannot_defer_migration_validation_until_after_removal(self):
        remote=Remote()
        installer=self.installer(remote, 'root')
        with self.assertRaisesRegex(RuntimeError, 'migrate-home'):
            installer.install(None, migrate=True, reinstall='installed')
        self.assertEqual(remote.calls, [])
        self.assertIsNone(self.store.pending(installer.profile))

    def test_archive_receipt_can_be_reconciled_without_repeating_rename(self):
        installer = self.installer(Remote(), 'root')
        self.store.begin(installer.profile, 'archive-root-state', archive=operations.ROOT_STATE+'.archive-'+'a'*32,
                         identity={'device':1, 'inode':2, 'journal':'b'*64})
        commands=[]
        def run(command, **kwargs):
            if 'CYTV_PYTHON_BOUND' in command:return ''
            commands.append(command)
            args = shlex.split(command)
            if args[:1] == ['env'] and args[1].startswith('CYTV_ROOT_INSTALL_ATTEMPT='):
                self.assertRegex(args[1], r'^CYTV_ROOT_INSTALL_ATTEMPT=[a-f0-9]{32}$')
                args = args[2:]
            if len(args)>3 and args[:2] == ['/usr/bin/python3','-c'] and 'CYTV_UPDATER_VERIFIED' not in command:
                self.assertEqual(args[3], 'reconcile')
                return '{"state":"archived"}'
            return '{"stage":"absent"}'
        installer.remote.run = run
        result = installer.status()
        self.assertIsNone(self.store.pending(installer.profile))
        self.assertEqual(result['reconciled'], 'root-archive-archived')
        self.assertFalse(any(' uninstall' in command for command in commands))

    def test_terminal_removal_can_finish_empty_package_cleanup_on_resume(self):
        remote = Remote()
        installer = self.installer(remote)
        self.store.begin(installer.profile, 'uninstall')
        self.store.checkpoint(installer.profile, stage='removing', removals={operations.HELPER: 'terminal', operations.HOME: 'done'}, eim_registered=False)
        cleaned = []
        def run(command, **kwargs):
            if 'CYTV_PYTHON_BOUND' in command:return ''
            if 'rmdir ' + operations.BASE + '/packages/' + operations.HELPER in command:
                cleaned.append(True)
            if 'CYTV_REMAINS' in command and operations.HELPER in command and not cleaned:
                return 'CYTV_REMAINS'
            return ''
        remote.run = run
        original = remote.luna
        remote.luna = lambda uri, payload, **kwargs: ({'returnValue': True, 'status': {'apps': []}} if uri == 'com.webos.appInstallService/status' else original(uri, payload, **kwargs))
        installer.uninstall()
        self.assertTrue(cleaned)
        self.assertIsNone(self.store.pending(installer.profile))

    def test_partial_uninstall_resumes_only_package_not_previously_submitted(self):
        remote = Remote()
        installer = self.installer(remote)
        remote.installed = [{'id': operations.HOME, 'version': '1.2.2'}]
        self.store.begin(installer.profile, 'uninstall')
        self.store.checkpoint(installer.profile, stage='removing', removals={operations.HELPER: 'done'}, eim_registered=False)
        original = remote.luna
        def luna(uri, payload, **kwargs):
            if uri == 'com.webos.appInstallService/status':
                return {'returnValue': True, 'status': {'apps': []}}
            if uri.endswith('/remove'):
                self.assertEqual(payload['id'], operations.HOME)
                remote.installed = []
            return original(uri, payload, **kwargs)
        remote.luna = luna
        installer.uninstall()
        self.assertIsNone(self.store.pending(installer.profile))
        self.assertEqual(len([c for c in remote.calls if c[0] == 'luna' and c[1].endswith('/remove')]), 1)

    def test_uncertain_package_removal_is_never_submitted_twice(self):
        remote = Remote()
        installer = self.installer(remote)
        remote.installed = [{'id': operations.HELPER, 'version': '0.6.13'}]
        self.store.begin(installer.profile, 'uninstall')
        self.store.checkpoint(installer.profile, stage='removing', removals={operations.HELPER: 'submitted'}, eim_registered=False)
        original = remote.luna
        remote.luna = lambda uri, payload, **kwargs: ({'returnValue': True, 'status': {'apps': []}} if uri == 'com.webos.appInstallService/status' else original(uri, payload, **kwargs))
        with self.assertRaisesRegex(RuntimeError, 'unknown'):
            installer.uninstall()
        self.assertFalse(any(c[0] == 'luna' and c[1].endswith('/remove') for c in remote.calls))

    def test_restore_uses_newer_eim_evidence_and_does_not_delete_twice(self):
        remote = Remote()
        installer = self.installer(remote)
        from cytv.state import private_write
        private_write(self.store.device_dir(installer.profile) / 'installation.json', b'{"eim_registered":false}')
        self.store.begin(installer.profile, 'install')
        self.store.checkpoint(installer.profile, eim_registered=True)
        installer.restore()
        installer.restore()
        self.assertEqual(len([c for c in remote.calls if c[0] == 'luna' and c[1].endswith('/deleteDevice')]), 1)

    def test_home_removal_checks_actual_renewal_service_path(self):
        remote = Remote()
        installer = self.installer(remote)
        installer.verify_absent(operations.HOME)
        command = remote.calls[-1][1]
        self.assertIn('/services/com.gathin.tvhome.renewal', command)

    def test_existing_active_helper_is_not_replaced(self):
        remote = Remote()
        run = remote.run
        remote.run = lambda command, **kwargs: 'CYTV_HELPER_ACTIVE' if '/controller.pid' in command else run(command, **kwargs)
        installer = self.installer(remote)
        with self.assertRaisesRegex(RuntimeError, 'Home.*two seconds'):
            installer.install(self.inventory, 'key')
        self.assertIsNone(self.store.pending(installer.profile))
        self.assertFalse(any(c[0] == 'upload' for c in remote.calls))

    def test_removal_readback_rejects_leftover_service(self):
        installer = self.installer(Remote())
        installer.remote.run = lambda *args, **kwargs: 'CYTV_REMAINS'
        with self.assertRaisesRegex(RuntimeError, 'remain'):
            installer.verify_absent(operations.HELPER)

    def test_root_completed_install_receipt_is_reconciled_from_driver_and_recovery(self):
        installer = self.installer(Remote(), 'root')
        self.store.begin(installer.profile, 'install')
        self.store.checkpoint(installer.profile, release_sha='a' * 64, bundle_sha='b' * 64, migrate=False)
        def run(command, **kwargs):
            if 'CYTV_PYTHON_BOUND' in command:return ''
            if 'deploy.json' in command:
                return '{"stage":"installed-recovery-only"}'
            if 'CYTV_ROOT_FILES_OK' in command:
                return 'CYTV_ROOT_FILES_OK'
            return '{"returnValue":true,"result":{"recovery":{"integrity_verified":true}}}'
        installer.remote.run = run
        result = installer.status()
        self.assertIsNone(result['pending'])
        self.assertEqual(result['reconciled'], 'root-installation-verified')

    def test_root_old_installation_does_not_certify_new_bundle(self):
        installer = self.installer(Remote(), 'root')
        self.store.begin(installer.profile, 'install')
        installer._selected_python='/usr/bin/python3'
        installer.remote.run = lambda command, **kwargs: ('{"stage":"installed-recovery-only"}' if 'deploy.json' in command else '{"returnValue":true,"result":{"recovery":{"integrity_verified":true}}}')
        result = installer.status()
        self.assertIsNotNone(result['pending'])
        self.assertIsNone(result['reconciled'])

    def test_optional_eim_failure_does_not_block_restore_or_removal(self):
        remote = Remote()
        installer = self.installer(remote)
        from cytv.state import private_write
        private_write(self.store.device_dir(installer.profile) / 'installation.json', b'{"eim_registered":false}')
        original = remote.luna
        def luna(uri, payload, **kwargs):
            if uri.endswith('/deleteDevice'):
                self.fail('EIM was never registered')
            return original(uri, payload, **kwargs)
        remote.luna = luna
        installer.restore()
        self.assertTrue(any(c[0] == 'luna' and c[2].get('id') == 'com.webos.app.home' for c in remote.calls))

    def test_restore_records_attempt_without_overwriting_uncertain_install(self):
        installer = self.installer(Remote())
        self.store.begin(installer.profile, 'install')
        installer.restore()
        attempts = list(self.store.device_dir(installer.profile).glob('recovery-*.json'))
        self.assertEqual(len(attempts), 1)
        self.assertEqual(json.loads(attempts[0].read_text())['stage'], 'complete')
        self.assertEqual(self.store.pending(installer.profile)['action'], 'install')

    def test_completed_no_root_install_can_be_reconciled_after_lost_acknowledgment(self):
        remote = Remote()
        installer = self.installer(remote)
        remote.installed = [{'id': operations.HOME, 'version': '1.2.2'}, {'id': operations.HELPER, 'version': '0.6.13'}]
        self.store.begin(installer.profile, 'install')
        files = {operations.BASE + '/applications/com.gathin.tvhome/apps.js': 'a' * 64}
        self.store.checkpoint(installer.profile, expected=files)
        remote.run = lambda *args, **kwargs: 'a' * 64 + '  ' + next(iter(files)) + '\n'
        result = installer.status()
        self.assertIsNone(self.store.pending(installer.profile))
        self.assertEqual(result['reconciled'], 'installed-files-verified; helper launch requires TV check')

    def test_partial_install_can_be_explicitly_removed_only_after_installer_is_idle(self):
        remote = Remote()
        installer = self.installer(remote)
        self.store.begin(installer.profile, 'install')
        with self.assertRaisesRegex(RuntimeError, 'idle'):
            installer.uninstall()
        self.assertEqual(self.store.pending(installer.profile)['action'], 'install')

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.store = state.Store(self.root / 'state')
        self.payload = self.root / 'payload'
        self.payload.mkdir()
        self.inventory = {'apps': [{'id': 'youtube', 'title': 'YouTube', 'icon': 'data:image/png;base64,AA=='}], 'inputs': []}
        self.manifest = {'files': {}, 'launcher': 'launcher.ipk', 'helper': 'helper.ipk',
                         'home_version': '1.2.2', 'helper_version': '0.6.13'}
        for app, name, version in [(operations.HOME, 'launcher.ipk', '1.2.2'), (operations.HELPER, 'helper.ipk', '0.6.13')]:
            (self.payload / name).write_bytes(package.ipk(app, version, {'usr/palm/applications/' + app + '/appinfo.json': json.dumps({'id': app, 'version': version}).encode()}))

    def installer(self, remote, edition='no-root'):
        tv = state.target('192.0.2.10', edition)
        return operations.Installer(remote, self.store, tv, self.payload, self.manifest, lambda _: None)

    def test_no_root_installs_helper_then_home_and_verifies_before_launch(self):
        remote = Remote()
        installer = self.installer(remote)
        installer.install(self.inventory, 'secret-ssap-key')
        calls = [c for c in remote.calls if c[0] == 'luna']
        installs = [c[2]['id'] for c in calls if c[1].endswith('/install')]
        self.assertEqual(installs, ['com.local.nativehome', 'com.gathin.tvhome'])
        self.assertEqual(calls[-1][1:], ('com.webos.applicationManager/launch', {'id': 'com.local.nativehome', 'params': {'nativeHomeStart': True}}))
        self.assertTrue(any(c[1].endswith('/dev/listApps') for c in calls[:-1]))
        self.assertTrue(any(c[0] == 'upload' and c[1].endswith('ssap-key.json') and c[2] == 0o640 for c in remote.calls))
        self.assertIsNone(self.store.pending(installer.profile))

    def test_failed_helper_install_does_not_install_home_or_launch_and_blocks_retry(self):
        remote = Remote(fail=operations.HELPER)
        installer = self.installer(remote)
        with self.assertRaises(RuntimeError):
            installer.install(self.inventory, 'secret')
        count = len(remote.calls)
        with self.assertRaisesRegex(RuntimeError, 'status'):
            installer.install(self.inventory, 'secret')
        self.assertEqual(len(remote.calls), count)
        self.assertFalse(any(c[0] == 'luna' and c[1].endswith('/launch') for c in remote.calls))
        self.assertEqual(self.store.pending(installer.profile)['action'], 'install')

    def root_bundle(self):
        import hashlib
        import runpy
        build = runpy.run_path(str(Path(__file__).resolve().parents[2] / "root-edition/build_updater.py"))
        build["build"]((self.payload / "root-updater").resolve())
        root = self.payload / 'root'
        root.mkdir()
        name = package.ROOT_APP + '_0.0.1_all.ipk'
        (root / name).write_bytes(package.ipk(package.ROOT_APP, '0.0.1', {'usr/palm/applications/' + package.ROOT_APP + '/apps.js': b'empty'}))
        (root / 'release.json').write_text(json.dumps({'application_id': package.ROOT_APP, 'files': {}}))
        (root / 'deploy.py').write_bytes(b'original device driver')
        (root / 'SHA256SUMS').write_text('old')
        (root / 'bundle.json').write_text(json.dumps({'package': name, 'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in root.iterdir()}}))
        return root

    def test_root_installs_updater_with_same_baseline_before_activation(self):
        self.root_bundle()
        remote = Remote()
        result = self.installer(remote, 'root').install(self.inventory)
        commands = [c[1] for c in remote.calls if c[0] == 'run']
        install = next(c for c in commands if '/install_driver.py install ' in c)
        self.assertIn('--payload ',install)
        self.assertFalse(any('setup-updater.py --device' in c or 'deploy.py install' in c for c in commands))
        self.assertLess(commands.index(install),next(i for i,c in enumerate(commands) if c.endswith(' enable')))
        self.assertTrue(result['updates_ready'])
        self.assertTrue(any(c[0] == 'luna' and c[1] == 'com.cleanyourtv.root.updater.service/status' for c in remote.calls))

    def test_updater_failure_keeps_receipt_and_never_activates(self):
        for failure in ('updater', 'updater-service'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as tmp:
                if not (self.payload / 'root').exists(): self.root_bundle()
                self.store = state.Store(Path(tmp) / 'state')
                remote = Remote(fail=failure)
                installer = self.installer(remote, 'root')
                with self.assertRaises(RuntimeError):
                    installer.install(self.inventory)
                self.assertEqual(self.store.pending(installer.profile)['action'], 'install')
                self.assertRegex(self.store.pending(installer.profile)['product_operation'],'^[a-f0-9]{32}$')
                self.assertFalse(any(c[0] == 'run' and c[1].endswith(' enable') for c in remote.calls))

    def test_bad_rollback_format_stops_before_removing_existing_root(self):
        import hashlib, io, tarfile
        root = self.root_bundle()
        manifest_path = root/'bundle.json'
        manifest = json.loads(manifest_path.read_text())
        target = root/manifest['package']
        parts = package.read_ar(target.read_bytes())
        output = io.BytesIO()
        unsafe_directory = False
        with tarfile.open(fileobj=io.BytesIO(parts['data.tar.gz'])) as source, tarfile.open(fileobj=output, mode='w:gz') as archive:
            for member in source:
                if member.isdir():
                    member.mode = 0o777
                    unsafe_directory = True
                archive.addfile(member, source.extractfile(member) if member.isfile() else None)
        self.assertTrue(unsafe_directory)
        parts['data.tar.gz'] = output.getvalue()
        target.write_bytes(package.ar(parts))
        manifest['files'][target.name] = hashlib.sha256(target.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest))
        remote = Remote()
        installer = self.installer(remote, 'root')
        # Migration retains the supplied package; secure own directories are valid,
        # so this fixture must contain genuinely unsafe writable directory modes.
        with self.assertRaisesRegex(ValueError, 'rollback'):
            installer.install_root(self.inventory, migrate=True, reinstall='installed')
        self.assertIsNone(self.store.pending(installer.profile))
        self.assertFalse(any(c[0] == 'upload' or ' uninstall' in c[1] for c in remote.calls))

    def test_corrupt_updater_stops_before_removing_existing_root(self):
        self.root_bundle()
        (self.payload / 'root-updater/root-updater.ipk').write_bytes(b'corrupt')
        remote = Remote()
        installer = self.installer(remote, 'root')
        with self.assertRaisesRegex(RuntimeError, 'Updater'):
            installer.install(self.inventory, reinstall='installed')
        self.assertIsNone(self.store.pending(installer.profile))
        self.assertFalse(any(c[0] == 'upload' or ' uninstall' in c[1] for c in remote.calls))

    def test_status_does_not_clear_incomplete_combined_install(self):
        remote = Remote()
        run = remote.run
        remote.run = lambda command, **kwargs: '{"stage":"installed-recovery-only"}' if 'deploy.json' in command else run(command, **kwargs)
        installer = self.installer(remote, 'root')
        installer.root_files_match = lambda pending: True
        for action in ('install', 'setup-root-updater'):
            with self.subTest(action=action):
                if self.store.pending(installer.profile): self.store.finish(installer.profile)
                self.store.begin(installer.profile, action, requires_updater=True)
                self.assertIsNone(installer.status()['reconciled'])
                self.assertIsNotNone(self.store.pending(installer.profile))

    def test_missing_updater_stops_before_installation(self):
        self.root_bundle()
        import shutil
        shutil.rmtree(self.payload / 'root-updater')
        remote = Remote()
        installer = self.installer(remote, 'root')
        with self.assertRaisesRegex((ValueError, RuntimeError), 'Updater'):
            installer.install(self.inventory)
        self.assertIsNone(self.store.pending(installer.profile))
        self.assertFalse(any(c[0] == 'upload' for c in remote.calls))

    def test_existing_updater_blocks_reinstall_before_removing_root(self):
        self.root_bundle()
        remote = Remote()
        run = remote.run
        remote.run = lambda command, **kwargs: 'CYTV_EXISTING_UPDATER' if 'CYTV_EXISTING_UPDATER' in command else run(command, **kwargs)
        installer = self.installer(remote, 'root')
        with self.assertRaisesRegex(RuntimeError, 'Updater'):
            installer.install(self.inventory, reinstall='installed')
        self.assertFalse(any(c[0] == 'upload' or ' uninstall' in c[1] for c in remote.calls))

    def test_root_installs_then_enables_and_launches(self):
        self.root_bundle()
        remote = Remote()
        installer = self.installer(remote, 'root')
        installer.install(self.inventory, None)
        commands = [c[1] for c in remote.calls if c[0] == 'run']
        self.assertEqual(sum('/install_driver.py install --operation' in cmd for cmd in commands),1)
        self.assertTrue(any(cmd.endswith(' enable') for cmd in commands))
        self.assertEqual(remote.calls[-2][1:], ('com.webos.applicationManager/launch', {'id': package.ROOT_APP}))
        self.assertTrue(remote.calls[-1][1].endswith(' status'))
        self.assertIsNone(self.store.pending(installer.profile))

    def test_root_stops_helper_before_enabling(self):
        self.root_bundle()
        remote = Remote()
        remote.installed = [{'id': operations.HELPER}]
        self.installer(remote, 'root').install(self.inventory)
        disable = next(i for i,c in enumerate(remote.calls) if c[0]=='luna' and c[1].endswith('/disable'))
        stop = next(i for i,c in enumerate(remote.calls) if c[0]=='run' and '/control.json' in c[1])
        enable = next(i for i,c in enumerate(remote.calls) if c[0]=='run' and c[1].endswith(' enable'))
        self.assertLess(disable, stop)
        self.assertLess(stop, enable)

    def test_root_enable_disconnect_retains_activation_receipt_without_retry(self):
        self.root_bundle()
        remote=Remote(fail='enable')
        installer=self.installer(remote,'root')
        with self.assertRaisesRegex(RuntimeError, 'activation'):
            installer.install(self.inventory)
        self.assertEqual(self.store.pending(installer.profile)['action'], 'activate-root')
        self.assertEqual(sum(c[0]=='run' and c[1].endswith(' enable') for c in remote.calls), 1)
        self.assertFalse(any(c[0]=='luna' and c[1].endswith('/launch') for c in remote.calls))

    def test_root_failed_readback_does_not_report_success(self):
        self.root_bundle()
        remote=Remote()
        remote.active['guardian_active']=False
        installer=self.installer(remote,'root')
        with self.assertRaisesRegex(RuntimeError, 'Recovery'):
            installer.install(self.inventory)
        self.assertIsNotNone(self.store.pending(installer.profile))

    def test_root_failed_recovery_verification_never_stops_helper_or_enables(self):
        self.root_bundle()
        remote=Remote()
        remote.active['recovery']['integrity_verified']=False
        installer=self.installer(remote,'root')
        with self.assertRaisesRegex(RuntimeError, 'recovery could not be verified'):
            installer.install(self.inventory)
        self.assertFalse(any(c[0]=='luna' or (c[0]=='run' and '/control.json' in c[1]) for c in remote.calls))

    def test_root_launch_disconnect_keeps_receipt_without_repeating_launch(self):
        self.root_bundle()
        remote=Remote()
        original=remote.luna
        launches=[]
        def luna(uri, payload, **kwargs):
            if uri.endswith('/launch'):
                launches.append(payload)
                raise RuntimeError('lost launch acknowledgement')
            return original(uri,payload,**kwargs)
        remote.luna=luna
        installer=self.installer(remote,'root')
        with self.assertRaisesRegex(RuntimeError, 'opening Home'):
            installer.install(self.inventory)
        self.assertEqual(launches, [{'id':package.ROOT_APP}])
        pending=self.store.pending(installer.profile)
        self.assertEqual(pending['stage'], 'launch')
        self.assertNotIn('launch_requested', pending)

    def test_helper_failure_offers_retry_and_never_enables_before_idle(self):
        self.root_bundle()
        remote=Remote()
        original=remote.run
        attempts=[]
        def run(command, **kwargs):
            if 'CYTV_PYTHON_BOUND' in command:return ''
            if 'CYTV_HELPER_IDLE' in command:
                attempts.append(command)
                if len(attempts)==1: raise RuntimeError('relay still running')
            return original(command, **kwargs)
        remote.run=run
        installer=self.installer(remote,'root')
        retries=[]
        installer.helper_retry=lambda: retries.append(True) or True
        installer.install(self.inventory)
        self.assertEqual(len(retries), 1)
        self.assertEqual(len(attempts), 2)
        self.assertIsNone(self.store.pending(installer.profile))

    def test_helper_failure_cannot_enable_root_or_kill_processes(self):
        self.root_bundle()
        remote=Remote()
        original=remote.run
        def run(command, **kwargs):
            if 'CYTV_PYTHON_BOUND' in command:return ''
            if 'CYTV_HELPER_IDLE' in command: raise RuntimeError('busy')
            return original(command, **kwargs)
        remote.run=run
        installer=self.installer(remote,'root')
        with self.assertRaisesRegex(RuntimeError, 'Home.*two seconds'):
            installer.install(self.inventory)
        self.assertFalse(any(c[0]=='run' and (' enable' in c[1] or 'kill' in c[1]) for c in remote.calls))
        self.assertEqual(self.store.pending(installer.profile)['stage'], 'stop-helper')

    def test_activation_readback_can_finish_pending_receipt(self):
        remote=Remote()
        original=remote.run
        remote.run=lambda command, **kwargs: '{"stage":"installed-recovery-only"}' if 'deploy.json' in command else original(command, **kwargs)
        installer=self.installer(remote,'root')
        self.store.begin(installer.profile,'activate-root',launch_requested=True)
        self.assertEqual(installer.status()['reconciled'], 'root-activation-verified')
        self.assertIsNone(self.store.pending(installer.profile))

    def test_lost_enable_reply_reconciles_active_root_without_repeating_enable(self):
        remote=Remote()
        original=remote.run
        remote.run=lambda command, **kwargs: '{"stage":"installed-recovery-only"}' if 'deploy.json' in command else original(command, **kwargs)
        installer=self.installer(remote,'root')
        self.store.begin(installer.profile,'activate-root',stage='enable')
        result=installer.status()
        self.assertIn('screen launch unconfirmed', result['reconciled'])
        self.assertIsNone(self.store.pending(installer.profile))
        self.assertFalse(any(c[0]=='luna' or c[1].endswith(' enable') for c in remote.calls))

    def test_incomplete_idle_routing_keeps_activation_receipt(self):
        remote=Remote()
        remote.active['effective']['profiles']['idleApp']['appId']='com.webos.app.home'
        original=remote.run
        remote.run=lambda command, **kwargs: '{"stage":"installed-recovery-only"}' if 'deploy.json' in command else original(command, **kwargs)
        installer=self.installer(remote,'root')
        self.store.begin(installer.profile,'activate-root',launch_requested=True)
        self.assertIsNone(installer.status()['reconciled'])
        self.assertIsNotNone(self.store.pending(installer.profile))

    def test_root_restore_clears_activation_but_not_install_receipt(self):
        installer=self.installer(Remote(),'root')
        self.store.begin(installer.profile,'activate-root')
        installer.restore()
        self.assertIsNone(self.store.pending(installer.profile))

    def test_root_reinstall_prepares_replacement_before_removing_old_package(self):
        root = self.root_bundle()
        (root/'deploy.py').write_bytes(b'corrupt replacement driver')
        remote = Remote()
        installer = self.installer(remote, 'root')
        with self.assertRaisesRegex(ValueError, 'integrity mismatch'):
            installer.install(self.inventory, reinstall='installed')
        self.assertFalse(any('uninstall' in call[1] or call[0]=='upload' for call in remote.calls))
        self.assertIsNone(self.store.pending(installer.profile))

    def test_root_reinstall_removes_archives_then_installs_exactly_once(self):
        self.root_bundle()
        remote = Remote()
        original = remote.run
        actions=[]
        def run(command, **kwargs):
            if 'CYTV_PYTHON_BOUND' in command:return ''
            args = shlex.split(command)
            if args[:1] == ['env'] and args[1].startswith('CYTV_ROOT_INSTALL_ATTEMPT='):
                self.assertRegex(args[1], r'^CYTV_ROOT_INSTALL_ATTEMPT=[a-f0-9]{32}$')
                args = args[2:]
            if len(args)>3 and args[:2] == ['/usr/bin/python3','-c'] and 'CYTV_UPDATER_VERIFIED' not in command:
                action=args[3]
                actions.append(action)
                if action=='inspect': return json.dumps({'identity':{'device':1,'inode':2,'journal':'a'*64},'busy':False})
                if action=='archive': return json.dumps({'archived':args[4]})
                self.fail('Unexpected archive action '+action)
            if len(args)>2 and args[1].endswith('/deploy.py'):
                actions.append(args[2])
                if args[2]=='uninstall': return json.dumps({'returnValue':True,'removed':package.ROOT_APP,'state_retained':operations.ROOT_STATE})
            return original(command, **kwargs)
        remote.run=run
        installer=self.installer(remote, 'root')
        result=installer.install(self.inventory, reinstall='installed')
        self.assertEqual(result['installed'], package.ROOT_APP)
        self.assertEqual(actions, ['uninstall','inspect','archive','status','status','enable','status'])
        self.assertIsNone(self.store.pending(installer.profile))

    def test_no_root_accepts_arm32_userspace_on_aarch64_kernel(self):
        remote = Remote()
        original = remote.run
        remote.run = lambda command, **kwargs: 'aarch64' if command == 'uname -m' else original(command, **kwargs)
        installer = self.installer(remote)
        installer.preflight(install=True)
        self.assertEqual(installer.tv_info, {
            'kernel_arch': 'aarch64', 'userland_abi': 'arm32', 'arm32_supported': True})
        self.assertFalse(any(c[0] == 'upload' for c in remote.calls))

    def test_no_root_requires_valid_little_endian_arm32_elf_before_mutation(self):
        valid = [127, 69, 76, 70, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 40, 0]
        arm64 = valid.copy(); arm64[4] = 2; arm64[18] = 183
        x86 = valid.copy(); x86[18] = 3
        big_endian = valid.copy(); big_endian[5] = 2
        bad_magic = valid.copy(); bad_magic[0] = 0
        for data, abi in [(arm64, 'arm64'), (x86, 'other'), (big_endian, 'unknown'),
                          (bad_magic, 'unknown'), (valid[:19], 'unknown'), ([], 'unknown'),
                          (['PRIVATE-UNEXPECTED-OUTPUT'], 'unknown')]:
            with self.subTest(data=data):
                remote = Remote()
                original = remote.run
                def run(command, **kwargs):
                    if 'CYTV_PYTHON_BOUND' in command:return ''
                    if command == 'uname -m': return 'aarch64'
                    if command == 'LC_ALL=C od -An -v -t u1 -N 20 /bin/sh':
                        return ' '.join(map(str, data))
                    return original(command, **kwargs)
                remote.run = run
                installer = self.installer(remote)
                with self.assertRaisesRegex(RuntimeError, 'ARM32'):
                    installer.install(self.inventory, 'key')
                self.assertEqual(installer.tv_info['userland_abi'], abi)
                self.assertFalse(installer.tv_info['arm32_supported'])
                self.assertFalse(any(c[0] in ('upload', 'luna') for c in remote.calls))
                self.assertIsNone(self.store.pending(installer.profile))

    def test_restore_does_not_clear_uncertain_install_receipt(self):
        remote = Remote()
        installer = self.installer(remote)
        self.store.begin(installer.profile, 'install')
        installer.restore()
        self.assertEqual(self.store.pending(installer.profile)['action'], 'install')

    def test_root_refuses_false_success_from_driver(self):
        remote = Remote()
        remote.run = lambda *args, **kwargs: json.dumps({'returnValue': False, 'error': 'conflict'})
        installer = self.installer(remote, 'root')
        with self.assertRaises(RuntimeError):
            installer.restore()


if __name__ == '__main__':
    unittest.main()
