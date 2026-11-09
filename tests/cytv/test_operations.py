"""Exercise real orchestration; only the remote SSH boundary is simulated."""
import json
import os
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
        self.observers = {}
        self.active = {'recovery': {'integrity_verified': True}, 'intent': {'enabled': True, 'phase': 'active'}, 'guardian_active': True, 'effective': {'sam_home': package.ROOT_APP, 'profiles': {'idleApp': {'appId': package.ROOT_APP}, 'defaultApps': {'categories': {'home': package.ROOT_APP}}}}}

    def run(self, command, data=None, timeout=30):
        self.calls.append(('run', command))
        if data and b'CYTV_SELECTED_RUNTIME_VERIFIED' in data:
            return 'CYTV_SELECTED_RUNTIME_VERIFIED'
        if 'CYTV_SYSTEM_PYTHON' in command and 'CYTV_ROOT_READY' not in command:
            return 'CYTV_SYSTEM_PYTHON'
        if 'CYTV_NODE_VERSION' in command and '/usr/bin/node --version' in command:
            return 'CYTV_NODE_VERSION v8.12.0'
        from cytv import no_root_observer
        if '/usr/bin/node -e ' in command:
            args=shlex.split(command)
            code=args[args.index('-e')+1]
            if no_root_observer.STORAGE_SELECT in code:
                request=json.loads(args[-1])
                return json.dumps({'operation':request['plan']['operation'],'root':request['root']})
            if no_root_observer.PROGRAM in code:
                import hashlib
                request=json.loads(args[-1]);plan=request['plan'];action=request['command'];index=request.get('slot')
                operation=plan['operation']
                if action=='storage-check':return json.dumps({'operation':operation})
                if action=='prepare':
                    self.observers.setdefault(operation,{'protocol':no_root_observer.PROTOCOL,'operation':operation,'plan_sha256':hashlib.sha256(no_root_observer.canonical(plan).encode()).hexdigest(),
                         'reservation':'active','closed':None,'configuration':{step:'prepared' for step in (('files','eim','launch') if plan['action']=='install' else ('restore',))},
                         'slots':[{'submission':'prepared','terminal':'none','readback':'not-checked','reason':None} for _ in range(2)]})
                result=self.observers[operation]
                if action=='upload-artifact':
                    self.upload(json.loads(plan['slots'][index]['request'])['ipkUrl'],data,mode=0o644)
                if action=='upload-configuration':
                    proof=request['proof']
                    self.upload(proof['directory']+'/'+proof['name'],data,mode=0o640 if proof['name']=='ssap-key.json' else 0o644)
                if action=='config-claim':
                    won=result['configuration'][index]=='prepared'
                    if won:result['configuration'][index]='unknown'
                    return json.dumps({'operation':operation,'won':won,'nonce':'f'*64 if won else None,'state':result['configuration'][index]})
                if action=='config-result':result['configuration'][index]='complete'
                if action=='artifacts':
                    return json.dumps({'operation':operation,'missing':[index for index,slot in enumerate(plan['slots']) if json.loads(slot['request'])['ipkUrl'] not in self.uploads]})
                if action=='start' and result['slots'][index]['submission']=='prepared':
                    slot=result['slots'][index];slot['submission']='claimed-possibly-submitted'
                    try:
                        self.luna(plan['slots'][index]['method'],json.loads(plan['slots'][index]['request']),terminal='installed' if plan['action']=='install' else 'removed',timeout=150)
                        slot['terminal']='success'
                    except Exception as error:
                        from cytv.errors import TVRejected
                        if isinstance(error,TVRejected):
                            slot['terminal']='failure'
                            slot['reply']={'statusValue':error.luna['status_value'],'errorCode':error.luna['error_code'],
                                           'details':{'state':error.luna['state']}}
                        else:slot['reason']='stream-ended'
                if action=='readback':result['slots'][index]['readback']='matches'
                if action=='seal':result['slots'][index]['submission']='sealed'
                if action=='release':result['closed']={'result':'verified'};result['reservation']='closed'
                return json.dumps(result)
            if code==no_root_observer.FILE_CHECK:
                import hashlib
                expected=json.loads(args[-1]);files=dict(self.uploads)
                for name,raw in self.uploads.items():
                    if name.endswith('.ipk'):
                        files.update({'/media/developer/apps/'+name:data for name,data in package.data_files(raw).items()})
                return 'CYTV_ORIGINAL_FILES_VERIFIED' if all(name in files and hashlib.sha256(files[name]).hexdigest()==digest for name,digest in expected.items()) else ''
            if code==no_root_observer.STATE_CHECK:return 'CYTV_CONFIGURATION_PRIVATE'
        if 'CYTV_STOP_RETAINED' in command:return 'CYTV_START_ALLOWED'
        if command.startswith('LC_ALL=C df -Pk '):
            return 'Filesystem 1024-blocks Used Available Capacity Mounted on\n/dev/test 10000000 0 10000000 0% /shared'
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
        if uri == 'com.webos.settingsservice/getSystemSettings':
            return {'returnValue':True,'settings':{'defaultApps':{}}}
        if uri == 'com.webos.service.systemprofile/getProfiles':
            return {'returnValue':True,'profiles':{'defaultApps':{'categories':{'home':'com.webos.app.home'}},'idleApp':{'appId':'com.webos.app.home','support':True}}}
        if uri == 'com.webos.service.tv.systemproperty/getSystemInfo':
            return {'returnValue': True, 'UHD': True}
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
        self.root_bundle()
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

    def test_no_root_rejects_node_below_01015_before_creating_a_receipt(self):
        import subprocess
        remote = Remote()
        original_run = remote.run
        def run(command, **kwargs):
            if 'CYTV_PYTHON_BOUND' in command:return ''
            if 'CYTV_NODE_READY' in command:
                args = shlex.split(command)
                snippet = args[args.index('-e')+1]
                result = subprocess.run(['node', '-e',
                    "Object.defineProperty(process.versions,'node',{value:'0.10.14'});"+snippet], capture_output=True)
                return 'CYTV_NODE_READY' if result.returncode == 0 else ''
            return original_run(command, **kwargs)
        remote.run = run
        installer = self.installer(remote)
        with self.assertRaisesRegex(RuntimeError, 'Node.js 0.10.15'):
            installer.install(self.inventory, 'secret')
        self.assertIsNone(self.store.pending(installer.profile))
        self.assertFalse(any(c[0] == 'upload' for c in remote.calls))

    def test_helper_node_gate_accepts_01015_and_later(self):
        import subprocess
        for version, allowed in [('0.8.28', False), ('0.10.14', False), ('0.10.15', True), ('0.10.24', True), ('0.10.25', True),
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
                    with self.assertRaisesRegex(RuntimeError, 'Node.js 0.10.15'):
                        installer.preflight(install=True)

    @unittest.skipIf(__import__('os').name == 'nt', 'TV staging uses a POSIX shell')
    def test_install_staging_is_readable_by_a_separate_installer_uid(self):
        from tests.cytv.test_no_root_observer import Harness, PROCESS_TMP
        with tempfile.TemporaryDirectory(dir=PROCESS_TMP) as directory:
            observer=Harness(directory)
            observer.prepare()
            stage=observer.root/'public'/('cytv-'+observer.plan['operation'])
            for directory in (observer.root/'public',stage):
                self.assertEqual(directory.stat().st_mode & 0o777,0o755)
            for archive in stage.iterdir():self.assertEqual(archive.stat().st_mode & 0o777,0o644)
            self.assertEqual(observer.directory.stat().st_mode & 0o777,0o700)
            observer.finish();observer.call('release');observer.call('retire')
            self.assertEqual(list((observer.root/'public').iterdir()),[])

    def test_new_helper_failure_recovery_keeps_original_evidence_without_monitor(self):
        from cytv import diagnostics
        from cytv.desktop import DesktopConsole
        from cytv.errors import TVRejected
        from cytv.recovery import recover
        for inherited in (False, True):
            with self.subTest(inherited=inherited):
                remote = Remote()
                installer = self.installer(remote)
                self.store.finish(installer.profile)
                original = remote.luna
                rejected = TVRejected('TV rejected the operation. Run cytv doctor; no automatic retry was attempted.',
                    {'returnValue': False, 'errorCode': -1, 'errorText': 'PRIVATE'},
                    'com.webos.appInstallService/status')
                def luna(uri, payload, **kwargs):
                    if uri.endswith('/dev/install'):
                        remote.calls.append(('luna', uri, payload))
                        self.assertEqual(payload['id'], operations.HELPER)
                        remote.installed = [{'id': operations.HELPER, 'version': '0.6.13'}]
                        raise TVRejected('Install failed', {'statusValue': 24,
                            'details': {'state': 'install failed', 'errorCode': -1, 'reason': 'PRIVATE'}}, uri)
                    if uri == 'com.webos.appInstallService/status':
                        remote.calls.append(('luna', uri, payload))
                        raise rejected
                    return original(uri, payload, **kwargs)
                remote.luna = luna
                with self.assertRaises(TVRejected) as first:
                    installer.install(self.inventory, 'PRIVATE-KEY')
                first_report = json.loads(diagnostics.create_report(self.store, 'install', installer.profile,
                    'install-helper', first.exception).read_text())
                self.assertEqual(first_report['first_failure']['luna']['status_value'], 24)
                if inherited:
                    self.store.checkpoint(installer.profile, previous=self.store.pending(installer.profile),
                                          action='uninstall', stage='pending')
                receipt = self.store.device_dir(installer.profile)/'operation.json'
                before = receipt.read_bytes()
                directory = self.store.device_dir(installer.profile)/'diagnostic-failures'
                retained = {p.name: p.read_bytes() for p in directory.iterdir()}
                remote.calls.clear()
                events = []
                recover(installer, lambda question: 'n' if 'Remove remaining' in question else 'y',
                        DesktopConsole(lambda k,v: events.append((k,v))))
                report = diagnostics.create_report(self.store, 'recover', installer.profile, 'recover')
                current = json.loads(report.read_text())
                self.assertEqual(current['first_failure'], first_report['first_failure'])
                self.assertEqual(receipt.read_bytes(), before)
                self.assertEqual({p.name:p.read_bytes() for p in directory.iterdir()}, retained)
                self.assertFalse(any(c[0]=='upload' for c in remote.calls))
                self.assertEqual([c[1] for c in remote.calls if c[0]=='luna'],
                    [])
                self.assertTrue(any(k=='recovery-plan' and v['state']=='ready' for k,v in events))
                self.assertNotIn('PRIVATE', report.read_text())
                self.assertNotIn('PRIVATE', str(events))
                self.assertNotIn('cytv doctor', str(events))

    def test_unstarted_no_root_removal_does_not_require_denied_monitor(self):
        from cytv.errors import TVRejected
        from cytv.recovery import recover
        from cytv.terminal import Console
        for journey in ('uninstall', 'recover'):
            with self.subTest(journey=journey):
                remote = Remote()
                remote.installed = [{'id': operations.HELPER}, {'id': operations.HOME}]
                installer = self.installer(remote)
                self.store.finish(installer.profile)  # Independent synthetic journeys.
                self.store.begin(installer.profile, 'uninstall', eim_registered=False)
                original = remote.luna
                def luna(uri, payload, **kwargs):
                    if uri == 'com.webos.appInstallService/status':
                        raise TVRejected('Denied', {'returnValue': False, 'errorCode': -1}, uri)
                    if uri.endswith('/dev/remove'):
                        # The write-ahead receipt must exist before the first mutation.
                        self.assertEqual(self.store.pending(installer.profile)['removals'][payload['id']], 'submitted')
                        self.assertEqual(kwargs['terminal'], 'removed')
                        remote.installed = [a for a in remote.installed if a['id'] != payload['id']]
                        original(uri, payload, **kwargs)
                        return {'returnValue': True, 'details': {'state': 'removed'}}
                    return original(uri, payload, **kwargs)
                remote.luna = luna
                if journey == 'recover':
                    answers = iter(('y', 'y'))
                    recover(installer, lambda _: next(answers), Console(lambda _: None))
                else:
                    installer.uninstall()
                self.assertIsNone(self.store.pending(installer.profile))
                calls = [c for c in remote.calls if c[0] == 'luna']
                self.assertEqual([c[2]['id'] for c in calls if c[1].endswith('/dev/remove')], [operations.HELPER, operations.HOME])
                launch = next(i for i,c in enumerate(calls) if c[1].endswith('/launch') and c[2]['id'] == 'com.webos.app.home')
                self.assertLess(launch, next(i for i,c in enumerate(calls) if c[1].endswith('/dev/remove')))
                self.assertFalse(any(c[1].endswith('/install') for c in calls))
                # A subsequent, explicitly started setup is now possible.
                installer.install(self.inventory, 'secret')
                self.assertIsNone(self.store.pending(installer.profile))

    def test_unstarted_removal_recovery_decline_keeps_receipt_without_monitor(self):
        from cytv.recovery import recover
        from cytv.terminal import Console
        remote = Remote()
        installer = self.installer(remote)
        self.store.begin(installer.profile, 'uninstall')
        path = self.store.device_dir(installer.profile) / 'operation.json'
        before = path.read_bytes()
        answers = iter(('y', 'n'))
        recover(installer, lambda _: next(answers), Console(lambda _: None))
        self.assertEqual(path.read_bytes(), before)
        self.assertFalse(any(c[0] == 'luna' and c[1] != 'com.webos.applicationManager/dev/listApps' for c in remote.calls))

    def test_uncertain_receipts_do_not_gain_unstarted_removal_exemption(self):
        from cytv.errors import TVRejected
        for fields in ({'previous': {'action': 'install'}}, {'previous': None},
                       {'expected': {}}, {'stage': 'removing'}, {'stage': 'unknown'},
                       {'removals': {operations.HELPER: 'submitted'}},
                       {'removals': None}, {'product_operation': 'a' * 32}):
            with self.subTest(fields=fields):
                remote = Remote()
                installer = self.installer(remote)
                self.store.begin(installer.profile, 'uninstall', **fields)
                receipt = self.store.device_dir(installer.profile) / 'operation.json'
                before = receipt.read_bytes()
                def deny(uri, payload, **kwargs):
                    remote.calls.append(('luna', uri, payload))
                    self.assertEqual(uri, 'com.webos.appInstallService/status')
                    raise TVRejected('Denied', {'returnValue': False, 'errorCode': -1}, uri)
                remote.luna = deny
                with self.assertRaises(TVRejected): installer.uninstall()
                self.assertEqual(receipt.read_bytes(), before)
                self.assertEqual(len(remote.calls), 1)
                receipt.unlink()  # Independent synthetic receipts only.

    def test_false_idle_reply_cannot_authorize_pending_removal(self):
        installer = self.installer(Remote())
        self.store.begin(installer.profile, 'uninstall', stage='removing')
        original = installer.remote.luna
        def luna(uri, payload, **kwargs):
            if uri == 'com.webos.appInstallService/status':
                return {'returnValue': False, 'status': {'apps': []}}
            return original(uri, payload, **kwargs)
        installer.remote.luna = luna
        with self.assertRaisesRegex(RuntimeError, 'not confirmed idle'):
            installer.uninstall()
        self.assertEqual(installer.remote.calls, [])
        self.assertIsNotNone(self.store.pending(installer.profile))

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
                raise TVRejected('denied', {'returnValue': False, 'errorCode': -1}, uri)
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
        self.root_bundle()
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

    def test_submitted_root_status_never_stages_or_executes_retained_python(self):
        installer=self.installer(Remote(),'root')
        self.store.begin(installer.profile,'install',stage='coordinator-submitted',product_operation='a'*32)
        original=self.store.pending(installer.profile)
        installer.coordinator_code=lambda:self.fail('Status attempted coordinator staging')
        def run(command,**kwargs):
            self.assertEqual(command,'env -u NODE_OPTIONS -u NODE_PATH /usr/bin/node')
            self.assertIn(b'clean-your-tv-installation',kwargs['data'])
            return '{"schema":1,"status":"missing"}'
        installer.remote.run=run
        result=installer.status()
        self.assertFalse(result['can_resume_root_setup'])
        self.assertIsNone(result['reconciled'])
        self.assertEqual(result['device']['product']['state'],'recovery_required')
        self.assertEqual(self.store.pending(installer.profile),original)
        self.assertFalse(any(c[0]=='upload' for c in installer.remote.calls))

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

    def test_c2_pending_install_keeps_receipt_despite_matching_versions_and_hashes(self):
        remote = Remote()
        installer = self.installer(remote)
        remote.installed = [{'id': operations.HOME, 'version': '1.2.2'},
                            {'id': operations.HELPER, 'version': '0.6.13'}]
        self.store.begin(installer.profile, 'install')
        files = {operations.BASE + '/applications/com.gathin.tvhome/apps.js': 'a' * 64}
        self.store.checkpoint(installer.profile, expected=files)
        remote.run = lambda *args, **kwargs: 'a' * 64 + '  ' + next(iter(files)) + '\n'
        receipt = self.store.device_dir(installer.profile) / 'operation.json'
        original = receipt.read_bytes()
        result = installer.status()
        self.assertTrue(receipt.exists(), 'Status must retain an unresolved journal')
        self.assertEqual(receipt.read_bytes(), original)
        self.assertIsNone(result['reconciled'])
        self.assertEqual(result['pending']['action'], 'install')
        self.assertFalse((receipt.parent / 'installation.json').exists())

    def test_uk6400_absent_packages_do_not_prove_pending_removal_terminated(self):
        installer = self.installer(Remote())
        self.store.begin(installer.profile, 'uninstall', previous={'action': 'install'})
        self.store.checkpoint(installer.profile, stage='removing',
                              removals={operations.HELPER: 'submitted'})
        receipt = self.store.device_dir(installer.profile) / 'operation.json'
        original = receipt.read_bytes()
        result = installer.status()
        self.assertTrue(receipt.exists(), 'Status must retain an unresolved journal')
        self.assertEqual(receipt.read_bytes(), original)
        self.assertIsNone(result['reconciled'])
        self.assertEqual(result['pending']['action'], 'uninstall')

    def test_both_issue201_actions_retain_journal_when_idle_is_unavailable(self):
        from cytv.errors import TVRejected, UserError
        for action in ('install', 'uninstall'):
            for outcome in ('denied', 'timeout', 'active', 'unknown'):
                with self.subTest(action=action, outcome=outcome):
                    remote = Remote()
                    installer = self.installer(remote)
                    self.store.begin(installer.profile, action, previous={'action': 'install'})
                    receipt = self.store.device_dir(installer.profile) / 'operation.json'
                    original = receipt.read_bytes()
                    def luna(uri, payload, **kwargs):
                        remote.calls.append(('luna', uri, payload))
                        self.assertEqual(uri, 'com.webos.appInstallService/status')
                        self.assertEqual(payload, {'subscribe': True})
                        if outcome == 'denied':
                            raise TVRejected('Rejected', {'returnValue': False, 'errorCode': -1}, uri)
                        if outcome == 'timeout':
                            raise UserError('Timed out')
                        return {'returnValue': True, 'status': {'apps': [{}]}} if outcome == 'active' else {'returnValue': True}
                    remote.luna = luna
                    with self.assertRaises(UserError):
                        installer.uninstall()
                    self.assertEqual(receipt.read_bytes(), original)
                    self.assertEqual(len(remote.calls), 1)
                    # Clear only this synthetic test receipt between independent cases.
                    receipt.unlink()

    def test_source_shaped_live_terminal_cannot_replace_original_operation_proof(self):
        fixture = json.loads((Path(__file__).parent / 'fixtures/no-root-terminal-authority.json').read_text())
        for case in fixture['cases']:
            with self.subTest(action=case['action']):
                remote = Remote()
                installer = self.installer(remote)
                receipt = self.store.device_dir(installer.profile) / 'operation.json'
                state.private_write(receipt, json.dumps(case['journal']).encode())
                original = receipt.read_bytes()
                def luna(uri, payload, **kwargs):
                    remote.calls.append(('luna', uri, payload))
                    self.assertEqual(uri, 'com.webos.appInstallService/status')
                    self.assertEqual(kwargs['timeout'], 10)
                    return case['unbound_live_terminal']
                remote.luna = luna
                # Even the right package's live success is not an idle response
                # or a receipt bound to this legacy host operation.
                with self.assertRaisesRegex(RuntimeError, 'not confirmed idle'):
                    installer.uninstall()
                self.assertEqual(receipt.read_bytes(), original)
                self.assertEqual(len(remote.calls), 1)
                receipt.unlink()

    def test_late_snapshot_does_not_replay_or_reconcile_legacy_operations(self):
        fixture = json.loads((Path(__file__).parent / 'fixtures/no-root-terminal-authority.json').read_text())
        for case in fixture['cases']:
            with self.subTest(action=case['action']):
                remote = Remote()
                installer = self.installer(remote)
                receipt = self.store.device_dir(installer.profile) / 'operation.json'
                state.private_write(receipt, json.dumps(case['journal']).encode())
                original = receipt.read_bytes()
                from cytv.transport import terminal_reply
                snapshot = case['late_status_snapshot']
                self.assertTrue(terminal_reply(snapshot))  # Acknowledgment only.
                terminal = 'installed' if case['action'] == 'install' else 'removed'
                self.assertFalse(terminal_reply(snapshot, terminal=terminal))
                luna = remote.luna
                def read_only(uri, payload, **kwargs):
                    self.assertEqual(uri, 'com.webos.applicationManager/dev/listApps')
                    return luna(uri, payload, **kwargs)
                remote.luna = read_only
                result = installer.status()
                self.assertEqual(receipt.read_bytes(), original)
                self.assertIsNone(result['reconciled'])
                self.assertEqual(result['pending'], case['journal'])
                self.assertFalse(any(call[0] == 'upload' for call in remote.calls))
                receipt.unlink()

    def test_denied_listapps_is_distinct_from_denied_dev_listapps(self):
        from cytv.errors import TVRejected
        for denied in ('com.webos.applicationManager/listApps',
                       'com.webos.applicationManager/dev/listApps'):
            with self.subTest(denied=denied):
                remote = Remote()
                original = remote.luna
                def luna(uri, payload, **kwargs):
                    if uri == denied:
                        raise TVRejected('Rejected', {'returnValue': False, 'errorCode': -1}, uri)
                    return original(uri, payload, **kwargs)
                remote.luna = luna
                installer = self.installer(remote)
                self.store.begin(installer.profile, 'install', expected={})
                receipt = self.store.device_dir(installer.profile) / 'operation.json'
                original_receipt = receipt.read_bytes()
                if denied.endswith('/dev/listApps'):
                    with self.assertRaises(TVRejected):
                        installer.status()
                else:
                    self.assertEqual(installer.status()['device']['apps'], [])
                self.assertEqual(receipt.read_bytes(), original_receipt)
                receipt.unlink()

    def test_partial_stale_and_corrupt_receipts_are_not_inferred_complete(self):
        for record in (b'{',
                       b'{"action":"install","stage":"pending","expected":{}}',
                       b'{"action":"install","stage":"pending","versions":{"wrong":"9.9.9"},"expected":{"stale":"bad-hash"}}',
                       b'{"action":"uninstall","stage":"removing","removals":{}}'):
            with self.subTest(record=record):
                remote = Remote()
                remote.installed = [{'id': operations.HOME, 'version': '1.2.2'}]
                installer = self.installer(remote)
                receipt = self.store.device_dir(installer.profile) / 'operation.json'
                state.private_write(receipt, record)
                self.assertIsNone(installer.status()['reconciled'])
                self.assertEqual(receipt.read_bytes(), record)
                self.assertTrue(all(call[0] == 'luna' and call[1].endswith('/dev/listApps')
                                    or call[0] == 'run' and 'CYTV_HELPER_' in call[1]
                                    or call[0] == 'run' and 'CYTV_NODE_VERSION' in call[1]
                                       and '/usr/bin/node --version' in call[1]
                                    for call in remote.calls))
                receipt.unlink()

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
            (self.payload / name).write_bytes(package.ipk(app, version, {'usr/palm/applications/' + app + '/appinfo.json': json.dumps({'id': app, 'version': version, 'resolution': '1920x1080'}).encode()}))
        self.manifest['graphics'] = {'1920x1080': {'launcher': 'launcher.ipk', 'root': 'root'},
                                     '1280x720': {'launcher': 'launcher-720p.ipk', 'root': 'root-720p'}}
        import hashlib
        self.manifest['files'].update({p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.payload.iterdir()})

    def installer(self, remote, edition='no-root'):
        tv = state.target('192.0.2.10', edition)
        return operations.Installer(remote, self.store, tv, self.payload, self.manifest, lambda _: None)

    @unittest.skipIf(os.name == 'nt', 'macOS bundle requires POSIX symlinks')
    def test_macos_payload_alias_accepts_verified_packages(self):
        self.root_bundle()
        contents = self.root / 'cytv.app/Contents'
        resources, frameworks = contents / 'Resources', contents / 'Frameworks'
        resources.mkdir(parents=True)
        frameworks.mkdir()
        self.payload.rename(resources / 'payload')
        self.payload = frameworks / 'payload'
        self.payload.symlink_to('../Resources/payload', target_is_directory=True)
        for edition in ('no-root', 'root'):
            with self.subTest(edition=edition):
                remote = Remote()
                installer = self.installer(remote, edition)
                installer.select_graphics()
                self.assertEqual(installer.tv_info['graphics_resolution'], '1920x1080')
                self.assertEqual(remote.calls, [('luna', 'com.webos.service.tv.systemproperty/getSystemInfo', {'keys': ['UHD']})])
                self.assertIsNone(self.store.pending(installer.profile))

    @unittest.skipIf(os.name == 'nt', 'macOS bundle requires POSIX symlinks')
    def test_graphics_alias_still_rejects_linked_package_and_bundle_directory(self):
        self.root_bundle()
        alias = self.root / 'payload-alias'
        alias.symlink_to(self.payload, target_is_directory=True)
        for name, edition in [('launcher.ipk', 'no-root'), ('root', 'root')]:
            with self.subTest(name=name):
                original = self.payload / name
                outside = self.root / name
                original.rename(outside)
                original.symlink_to(outside, target_is_directory=outside.is_dir())
                try:
                    remote = Remote()
                    installer = self.installer(remote, edition)
                    installer.payload = alias
                    with self.assertRaisesRegex(RuntimeError, 'graphics packages'):
                        installer.install(self.inventory, 'secret')
                    self.assertFalse(any(c[0] in ('run', 'upload') for c in remote.calls))
                    self.assertIsNone(self.store.pending(installer.profile))
                finally:
                    original.unlink()
                    outside.rename(original)

    def test_graphics_preselection_is_reused_by_install(self):
        remote = Remote()
        installer = self.installer(remote)
        installer.select_graphics()
        installer.install(self.inventory, 'secret')
        probes = [c for c in remote.calls if c[0] == 'luna' and c[1].endswith('/getSystemInfo')]
        self.assertEqual(len(probes), 1)

    def test_hd_capability_selects_hd_bytes_before_personalization(self):
        import hashlib
        info = {'id': operations.HOME, 'version': '1.2.2', 'resolution': '1280x720'}
        raw = package.ipk(operations.HOME, '1.2.2', {'usr/palm/applications/'+operations.HOME+'/appinfo.json': json.dumps(info).encode()})
        (self.payload/'launcher-720p.ipk').write_bytes(raw)
        self.manifest['files']['launcher-720p.ipk'] = hashlib.sha256(raw).hexdigest()
        remote = Remote()
        original = remote.luna
        remote.luna = lambda uri, payload, **kw: {'returnValue': True, 'UHD': False} if uri.endswith('/getSystemInfo') else original(uri, payload, **kw)
        self.installer(remote).install(self.inventory, 'secret')
        installed = next(data for path, data in remote.uploads.items() if path.endswith('/launcher.ipk'))
        files = package.data_files(installed)
        self.assertEqual(json.loads(files['usr/palm/applications/'+operations.HOME+'/appinfo.json'])['resolution'], '1280x720')

    def test_hd_root_selection_preserves_baseline_bytes_and_hashes(self):
        import hashlib, shutil
        source = self.root_bundle()
        target = self.payload/'root-720p'
        shutil.copytree(source, target)
        manifest = json.loads((target/'bundle.json').read_text())
        name = manifest['package']
        files = package.data_files((target/name).read_bytes())
        appinfo = 'usr/palm/applications/'+package.ROOT_APP+'/appinfo.json'
        info = json.loads(files[appinfo]); info['resolution'] = '1280x720'
        files[appinfo] = json.dumps(info).encode()
        (target/name).write_bytes(package.ipk(package.ROOT_APP, '0.0.1', files))
        manifest['files'] = {p.relative_to(target).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in target.rglob('*') if p.is_file() and p.name != 'bundle.json'}
        (target/'bundle.json').write_text(json.dumps(manifest))
        self.manifest['files'].update({p.relative_to(self.payload).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in target.rglob('*') if p.is_file()})
        remote = Remote()
        original = remote.luna
        probes = []
        def luna(uri, payload, **kwargs):
            if uri.endswith('/getSystemInfo'):
                probes.append((uri, payload))
                return {'returnValue': True, 'UHD': 'false'}
            return original(uri, payload, **kwargs)
        remote.luna = luna
        self.installer(remote, 'root').install(self.inventory)
        uploaded = next(raw for path, raw in remote.uploads.items() if path.endswith('/root/'+name))
        self.assertEqual(json.loads(package.data_files(uploaded)[appinfo])['resolution'], '1280x720')
        self.assertEqual(probes, [('com.webos.service.tv.systemproperty/getSystemInfo', {'keys': ['UHD']})])
        uploaded_release = json.loads(next(raw for path, raw in remote.uploads.items() if path.endswith('/root/release.json')))
        self.assertEqual(uploaded_release['files']['usr/palm/applications/'+package.ROOT_APP+'/apps.js'], hashlib.sha256(package.inventory_script(self.inventory)).hexdigest())

    def test_unknown_capability_stops_before_preflight_or_receipt(self):
        remote = Remote()
        remote.luna = lambda *args, **kwargs: {'returnValue': True}
        installer = self.installer(remote, 'root')
        with self.assertRaisesRegex(RuntimeError, 'graphics'):
            installer.install(self.inventory)
        self.assertEqual(remote.calls, [])
        self.assertIsNone(self.store.pending(installer.profile))

    def test_invalid_graphics_payload_stops_before_upload(self):
        for problem in ('legacy', 'path', 'hash', 'resolution', 'version', 'identity'):
            with self.subTest(problem=problem):
                import copy
                manifest = copy.deepcopy(self.manifest)
                if problem == 'legacy': manifest.pop('graphics')
                elif problem == 'path': manifest['graphics']['1920x1080']['launcher'] = '../launcher.ipk'
                elif problem == 'hash': manifest['files']['launcher.ipk'] = '0'*64
                else:
                    import hashlib
                    info = {'id': operations.HOME, 'version': '1.2.2', 'resolution': '1920x1080'}
                    info[{'resolution': 'resolution', 'version': 'version', 'identity': 'id'}[problem]] = {'resolution': '1280x720', 'version': '9.0.0', 'identity': 'another.app'}[problem]
                    raw = package.ipk(operations.HOME, '1.2.2', {'usr/palm/applications/'+operations.HOME+'/appinfo.json': json.dumps(info).encode()})
                    (self.payload/'launcher.ipk').write_bytes(raw)
                    manifest['files']['launcher.ipk'] = hashlib.sha256(raw).hexdigest()
                remote = Remote()
                installer = self.installer(remote)
                installer.manifest = manifest
                with self.assertRaisesRegex(RuntimeError, 'graphics'):
                    installer.install(self.inventory, 'secret')
                self.assertFalse(any(c[0] in ('run', 'upload') for c in remote.calls))
                self.assertIsNone(self.store.pending(installer.profile))

    def test_package_and_launch_success_do_not_certify_startup_or_home(self):
        installer = self.installer(Remote())
        installer.install(self.inventory, 'private-pairing')
        outcome = installer.tv_info['setup_outcome']
        self.assertEqual(outcome, {'packages':'verified','launch_request':'accepted',
                                  'startup':'not-observed','home_button':'not-tested'})
        self.assertIsNone(self.store.pending(installer.profile))

    def test_launch_failure_preserves_verified_packages_and_pending_receipt(self):
        remote = Remote(); original = remote.luna
        def luna(uri, payload, **kwargs):
            if uri.endswith('/launch'): raise RuntimeError('lost launch response')
            return original(uri, payload, **kwargs)
        remote.luna = luna
        installer = self.installer(remote)
        with self.assertRaises(RuntimeError): installer.install(self.inventory, 'private-pairing')
        outcome = installer.tv_info['setup_outcome']
        self.assertEqual(outcome['packages'], 'verified')
        self.assertEqual(outcome['launch_request'], 'submitted-unconfirmed')
        self.assertEqual(outcome['home_button'], 'not-tested')
        self.assertIsNotNone(self.store.pending(installer.profile))

    def test_optional_startup_probe_failure_cannot_undo_successful_install(self):
        remote = Remote(); original, luna = remote.run, remote.luna
        launched = False
        def launch(uri, payload, **kwargs):
            nonlocal launched
            if uri.endswith('/launch'): launched = True
            return luna(uri, payload, **kwargs)
        def run(command, **kwargs):
            if launched and 'CYTV_HELPER_IDLE' in command:
                self.assertEqual(kwargs.get('timeout'), 5)
                raise TimeoutError('private transport text')
            return original(command, **kwargs)
        remote.luna, remote.run = launch, run
        installer = self.installer(remote)
        installer.install(self.inventory, 'private-pairing')
        self.assertEqual(installer.tv_info['setup_outcome']['startup'], 'unverified')
        self.assertIsNone(self.store.pending(installer.profile))

    def test_root_existing_runtime_readback_is_separate_from_home_observation(self):
        self.root_bundle()
        installer = self.installer(Remote(), 'root')
        installer.install(self.inventory)
        self.assertEqual(installer.tv_info['setup_outcome'],
            {'packages':'verified','launch_request':'accepted',
             'startup':'root-state-verified','home_button':'not-tested'})

    def test_install_waits_for_catalog_without_resubmitting_packages(self):
        from unittest.mock import patch
        for delayed, version in ((operations.HOME, None), (operations.HOME, '1.0.0'),
                                 (operations.HELPER, None), (operations.HELPER, '0.1.0')):
            with self.subTest(delayed=delayed, version=version):
                self.store.finish(self.installer(Remote()).profile)
                remote = Remote()
                original = remote.luna
                snapshots = []
                def luna(uri, payload, **kwargs):
                    reply = original(uri, payload, **kwargs)
                    if uri.endswith('/dev/listApps'):
                        if not snapshots:
                            reply['apps'] = [dict(a, version=version) if a['id'] == delayed else a
                                             for a in reply['apps'] if a['id'] != delayed or version]
                        snapshots.append(reply['apps'])
                    return reply
                remote.luna = luna
                installer = self.installer(remote)
                clock = [0.0]
                with patch('cytv.operations.time.monotonic', side_effect=lambda: clock[0]), \
                     patch('cytv.operations.time.sleep', side_effect=lambda seconds: clock.__setitem__(0, clock[0] + seconds)):
                    installer.install(self.inventory, 'synthetic-key')
                self.assertEqual(len(snapshots), 5 if delayed == operations.HELPER else 4)
                self.assertIsNone(self.store.pending(installer.profile))
                self.assertEqual(installer.tv_info['components'], {'home': '1.2.2', 'helper': '0.6.13'})
                calls = [c for c in remote.calls if c[0] == 'luna']
                self.assertEqual([c[2]['id'] for c in calls if c[1].endswith('/dev/install')],
                                 [operations.HELPER, operations.HOME])
                last_read = max(i for i, c in enumerate(remote.calls) if c[0] == 'luna' and c[1].endswith('/dev/listApps'))
                config = next(i for i, c in enumerate(remote.calls) if c[0] == 'upload' and c[1].endswith('/ssap-key.json'))
                self.assertLess(last_read, config)

    def test_catalog_mismatch_uses_one_deadline_and_keeps_unconfigured_journal(self):
        from unittest.mock import patch
        from cytv.errors import UserError
        remote = Remote()
        installer = self.installer(remote)
        original = remote.luna
        clock, timeouts, receipt_before = [0.0], [], []
        receipt = self.store.device_dir(installer.profile) / 'operation.json'
        def luna(uri, payload, **kwargs):
            reply = original(uri, payload, **kwargs)
            if uri.endswith('/dev/listApps'):
                receipt_before.append(receipt.read_bytes())
                timeouts.append(kwargs.get('timeout', 30))
                clock[0] += 0.25  # Include time spent reading, not just sleeps.
                reply['apps'] = [a for a in reply['apps'] if a['id'] != operations.HOME]
            return reply
        remote.luna = luna
        with patch('cytv.operations.time.monotonic', side_effect=lambda: clock[0]), \
             patch('cytv.operations.time.sleep', side_effect=lambda seconds: clock.__setitem__(0, clock[0] + seconds)):
            with self.assertRaises(UserError) as caught:
                installer.install(self.inventory, 'synthetic-key')
        self.assertEqual(caught.exception.reason_code, 'version-mismatch')
        self.assertEqual(clock[0], 10.25)  # Helper readback precedes Home's own bounded deadline.
        self.assertGreater(len(timeouts), 1)
        self.assertTrue(all(0 < timeout <= 10 for timeout in timeouts))
        self.assertEqual(timeouts, sorted(timeouts, reverse=True))
        self.assertEqual(receipt.read_bytes(), receipt_before[0])
        self.assertEqual(installer.tv_info['components'], {'helper': '0.6.13'})
        self.assertFalse(any(c[0] == 'upload' and c[1].endswith('/ssap-key.json') for c in remote.calls))
        self.assertFalse(any(c[0] == 'luna' and (c[1].endswith('/launch') or c[1].endswith('/dev/remove')) for c in remote.calls))
        self.assertEqual(installer.tv_info['setup_outcome']['packages'], 'not-verified')

    def test_catalog_success_after_deadline_cannot_start_helper(self):
        from unittest.mock import patch
        from cytv.errors import UserError
        remote = Remote()
        original = remote.luna
        clock = [0.0]
        def luna(uri, payload, **kwargs):
            reply = original(uri, payload, **kwargs)
            if uri.endswith('/dev/listApps'):
                clock[0] = 11.0  # Transport setup can consume the polling budget.
            return reply
        remote.luna = luna
        installer = self.installer(remote)
        with patch('cytv.operations.time.monotonic', side_effect=lambda: clock[0]), self.assertRaises(UserError):
            installer.install(self.inventory, 'synthetic-key')
        self.assertIsNotNone(self.store.pending(installer.profile))
        self.assertFalse(any(c[0] == 'upload' and c[1].endswith('/ssap-key.json') for c in remote.calls))
        self.assertFalse(any(c[0] == 'luna' and c[1].endswith('/launch') for c in remote.calls))

    def test_catalog_errors_stop_without_polling_or_configuring(self):
        from unittest.mock import patch
        from cytv.errors import TVRejected, UserError
        for failure in ('denied', 'malformed', 'timeout'):
            with self.subTest(failure=failure):
                self.store.finish(self.installer(Remote()).profile)
                remote = Remote()
                installer = self.installer(remote)
                original = remote.luna
                def luna(uri, payload, **kwargs):
                    if uri.endswith('/dev/listApps'):
                        remote.calls.append(('luna', uri, payload))
                        if failure == 'denied':
                            raise TVRejected('Synthetic denial', {'returnValue': False, 'errorCode': -1}, uri)
                        if failure == 'timeout':
                            raise TimeoutError('Synthetic timeout')
                        return {'returnValue': True, 'apps': None}
                    return original(uri, payload, **kwargs)
                remote.luna = luna
                with patch('cytv.operations.time.sleep') as sleep, self.assertRaises((UserError, TimeoutError)):
                    installer.install(self.inventory, 'synthetic-key')
                sleep.assert_not_called()
                self.assertIsNotNone(self.store.pending(installer.profile))
                self.assertEqual(len([c for c in remote.calls if c[0] == 'luna' and c[1].endswith('/dev/listApps')]), 1)
                self.assertFalse(any(c[0] == 'upload' and c[1].endswith('/ssap-key.json') for c in remote.calls))

    def test_no_root_installs_helper_then_home_and_verifies_before_launch(self):
        remote = Remote()
        installer = self.installer(remote)
        installer.install(self.inventory, 'secret-ssap-key')
        calls = [c for c in remote.calls if c[0] == 'luna']
        installs = [c[2]['id'] for c in calls if c[1].endswith('/install')]
        self.assertEqual(installs, ['com.local.nativehome', 'com.gathin.tvhome'])
        self.assertEqual(calls[-1][1:], ('com.webos.applicationManager/launch', {'id': 'com.local.nativehome', 'params': {'nativeHomeAuto': True}}))
        self.assertEqual(len([c for c in calls if c[1].endswith('/dev/listApps')]), 4)
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
        (root / name).write_bytes(package.ipk(package.ROOT_APP, '0.0.1', {'usr/palm/applications/' + package.ROOT_APP + '/apps.js': b'empty',
            'usr/palm/applications/' + package.ROOT_APP + '/appinfo.json': json.dumps({'id': package.ROOT_APP, 'version': '0.0.1', 'resolution': '1920x1080'}).encode()}))
        (root / 'release.json').write_text(json.dumps({'application_id': package.ROOT_APP, 'version': '0.0.1', 'files': {}}))
        (root / 'deploy.py').write_bytes(b'original device driver')
        source = Path(__file__).resolve().parents[2] / 'root-edition'
        for support_name in ('python_binding.py', 'runtime/cli.py', 'runtime/device_adapter.py',
                     'runtime/persistent_health.py', 'runtime/emergency_trial.py'):
            path = root / support_name
            path.parent.mkdir(exist_ok=True)
            path.write_bytes((source / support_name).read_bytes())
        (root / 'SHA256SUMS').write_text('old')
        (root / 'bundle.json').write_text(json.dumps({'package': name, 'files': {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}}))
        self.manifest['files'].update({p.relative_to(self.payload).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()})
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
            installer._graphics_paths = {'root': 'root'}
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

    def test_activation_failures_keep_typed_evidence_without_replaying(self):
        from cytv.errors import TVCommandError, TVRejected
        from cytv.diagnostics import create_report
        self.root_bundle()
        cases = (
            ('enable', TVCommandError(1), 'ssh_command',
             {'exit_status': 1, 'root_action': 'enable', 'root_boundary': 'driver'}),
            ('launch', TVRejected('PRIVATE TV reply',
                {'returnValue': False, 'errorCode': -1, 'errorText': 'PRIVATE'},
                'com.webos.applicationManager/launch'), 'luna',
             {'operation': 'application-launch', 'error_code': -1,
              'details_error_code': None, 'status_value': None,
              'state': 'unknown', 'return_value': False}),
        )
        for step, failure, field, expected in cases:
            with self.subTest(step=step):
                remote = Remote()
                run, luna = remote.run, remote.luna
                def fail_enable(command, **kwargs):
                    if step == 'enable' and command.endswith(' enable'):
                        remote.calls.append(('run', command))
                        raise failure
                    return run(command, **kwargs)
                def fail_launch(uri, payload, **kwargs):
                    if uri == 'com.webos.applicationManager/launch':
                        remote.calls.append(('luna', uri, payload))
                        raise failure
                    return luna(uri, payload, **kwargs)
                remote.run, remote.luna = fail_enable, fail_launch
                installer = self.installer(remote, 'root')
                with self.assertRaises(operations.UserError) as caught:
                    installer.install(self.inventory)
                pending = self.store.pending(installer.profile)
                report = json.loads(create_report(self.store, 'install', installer.profile,
                                                  'activate-root', caught.exception).read_text())
                self.store.finish(installer.profile)  # Isolate the next failure scenario.
                self.assertIs(caught.exception, failure)
                self.assertEqual((pending['action'], pending['stage']), ('activate-root', step))
                self.assertEqual(report[field], expected)
                self.assertEqual(report['first_failure'][field], expected)
                self.assertNotIn('PRIVATE', json.dumps(report))
                self.assertEqual(sum(c[0] == 'run' and c[1].endswith(' enable') for c in remote.calls), 1)
                self.assertEqual(sum(c[0] == 'luna' and c[1].endswith('/launch') for c in remote.calls),
                                 0 if step == 'enable' else 1)

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
        self.assertFalse(any((c[0]=='luna' and c[1] not in ('com.webos.service.tv.systemproperty/getSystemInfo','com.webos.settingsservice/getSystemSettings','com.webos.service.systemprofile/getProfiles')) or (c[0]=='run' and '/control.json' in c[1]) for c in remote.calls))

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

    def test_failed_activation_recovers_only_after_explicit_confirmation_without_installing_again(self):
        from cytv.recovery import recover
        from cytv.terminal import Console
        self.root_bundle();remote=Remote(fail='enable');installer=self.installer(remote,'root')
        with self.assertRaises(RuntimeError):installer.install(self.inventory)
        previous=self.store.pending(installer.profile)
        remote.active={'recovery':{'integrity_verified':True},'guardian_active':False,
            'intent':{'enabled':False,'phase':'disabled'},'journal':{'state':'restored'},
            'effective':{'sam_home':'com.webos.app.home','profiles':{
                'defaultApps':{'categories':{'home':'com.webos.app.home'}},'idleApp':{'appId':'com.webos.app.home'}}}}
        original=remote.run
        def run(command,**kwargs):
            if 'deploy.json' in command:return '{"stage":"installed-recovery-only"}'
            for marker in ('CYTV_ROOT_FILES_OK','CYTV_ACTIVATION_RECOVERABLE'):
                if marker in command:
                    remote.calls.append(('run',command));return marker
            if command.endswith(' enable'):
                remote.fail=None
                remote.active={'recovery':{'integrity_verified':True},'guardian_active':True,
                    'intent':{'enabled':True,'phase':'active'},'effective':{'sam_home':package.ROOT_APP,'profiles':{
                        'defaultApps':{'categories':{'home':package.ROOT_APP}},'idleApp':{'appId':package.ROOT_APP}}}}
            return original(command,**kwargs)
        remote.run=run;checkpoint=len(remote.calls)
        answers=iter(('y',''))
        recover(installer,lambda _:next(answers),Console(lambda *_:None))
        self.assertEqual(self.store.pending(installer.profile),dict(previous,
            activation_restore_pending=False,activation_restore='verified'))
        previous=self.store.pending(installer.profile)
        self.assertFalse(any(c[0]=='run' and c[1].endswith(' enable') for c in remote.calls[checkpoint:]))
        answers=iter(('y','1','y','3'))
        recover(installer,lambda _:next(answers),Console(lambda *_:None))
        self.assertIsNone(self.store.pending(installer.profile))
        later=remote.calls[checkpoint:]
        self.assertEqual(sum(c[0]=='run' and c[1].endswith(' enable') for c in later),1)
        self.assertFalse(any(c[0]=='upload' or '/dev/install' in c[1] or '/dev/remove' in c[1] for c in later))
        saved=list(self.store.device_dir(installer.profile).glob('recovery-*.json'))
        self.assertEqual(len(saved),1);self.assertEqual(json.loads(saved[0].read_text())['previous'],previous)

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
        with self.assertRaisesRegex(RuntimeError, 'graphics packages'):
            installer.install(self.inventory, reinstall='installed')
        self.assertFalse(any('uninstall' in call[1] or call[0]=='upload' for call in remote.calls))
        self.assertIsNone(self.store.pending(installer.profile))

    def test_no_root_accepts_arm32_userspace_on_aarch64_kernel(self):
        remote = Remote()
        original = remote.run
        remote.run = lambda command, **kwargs: 'aarch64' if command == 'uname -m' else original(command, **kwargs)
        installer = self.installer(remote)
        installer.preflight(install=True)
        self.assertEqual(installer.tv_info, {
            'node_version': '8.12.0', 'node_version_status': 'read',
            'kernel_arch': 'aarch64', 'userland_abi': 'arm32', 'arm32_supported': True,
            'helper_state': 'stopped'})
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
                self.assertFalse(any(c[0] == 'upload' or (c[0] == 'luna' and not c[1].endswith('/getSystemInfo')) for c in remote.calls))
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
