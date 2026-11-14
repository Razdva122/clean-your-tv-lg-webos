"""Installer -> trusted adapter -> real detached Node -> simulated vendor process."""
import json
import hashlib
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from cytv import no_root_observer as observer, operations, state, package
from tests.cytv.test_operations import Remote, split_observer_command
from tests.cytv import test_operations as operations_fixture


class ProcessRemote(Remote):
    def __init__(self, root):
        super().__init__()
        self.root_path=root
        self.cut=False
        self.omit=set()
        self.boot = "11111111-1111-1111-1111-111111111111"
        self.cut_after_cleanup=None
        self.transform_cleanup=lambda source: source
        self.close=lambda: None
        self.sender=root/'sender'
        self.sender.write_text('''#!/usr/bin/env python3
import json,sys,os,select
from pathlib import Path
sys.path.insert(0, REPOSITORY)
from cytv import package
root=Path(ROOT)
request=json.loads(sys.argv[-1]); app=request['id']
with (root/'requests').open('a') as stream: stream.write(app+'\\n')
if select.select([sys.stdin],[],[],.05)[0]: sys.exit(12)
apps=json.loads((root/'installed.json').read_text()) if (root/'installed.json').exists() else {}
if sys.argv[-2].endswith('/install'):
 for name,data in package.data_files(Path(request['ipkUrl']).read_bytes()).items():
  destination=root/'apps'/name; destination.parent.mkdir(parents=True,exist_ok=True); destination.write_bytes(data)
 info=json.loads((root/'apps/usr/palm/applications'/app/'appinfo.json').read_text())
 apps[app]=info['version']; terminal='installed'
 if app=='com.local.nativehome':
  state=root/'apps/usr/palm/applications'/app/'state';state.mkdir(exist_ok=True);os.chown(state,-1,os.getgid())
else:
 import shutil
 for kind,suffix in [('applications',''),('packages',''),('services','.renewal' if app=='com.gathin.tvhome' else '.service')]:
  shutil.rmtree(root/'apps/usr/palm'/kind/(app+suffix),ignore_errors=True)
 apps.pop(app,None); terminal='removed'
(root/'installed.json').write_text(json.dumps(apps))
print(json.dumps({'returnValue':True,'details':{'state':terminal}}),flush=True)
sys.stdin.read()
'''.replace('REPOSITORY',repr(str(Path(__file__).resolve().parents[2]))).replace('ROOT',repr(str(root))))
        self.sender.chmod(0o700)

    def run(self, command, data=None, timeout=30):
        if 'CYTV_FRESH_ROOT' in command:
            return 'CYTV_FRESH_ROOT'
        if 'CYTV_NODE_READY' in command:
            return super().run(command,data,timeout)
        if 'CYTV_STOP_RETAINED' in command:
            return subprocess.run(['sh','-c',command],capture_output=True,check=True).stdout.decode()
        if command.startswith('if [ -f ') and '/usr/bin/node || exit 1' in command:
            # Run the actual shell/no-op guard; its PID '-e' predicate is not
            # a Node '-e' argument. The trusted program travels on stdin.
            command=command.replace('/usr/bin/node',shutil.which('node'))
            source=data.replace(b'/media/developer/apps/usr/palm/applications/com.local.nativehome/state',operations.HELPER_STATE.encode())
            result=subprocess.run(['sh','-c',command],input=source,capture_output=True,timeout=timeout)
            if result.returncode:raise RuntimeError(result.stderr.decode())
            return result.stdout.decode()
        if command == '/usr/bin/node' and data.startswith(b'process.argv.push('):
            value, _ = json.JSONDecoder().raw_decode(data.decode()[len('process.argv.push('):])
            request = json.loads(value)
            source = data.decode().replace('/media/developer/apps', str(self.root_path / 'apps'))
            source = source.replace('/var/palm/ls2-dev', str(self.root_path / 'legacy-bus'))
            source = source.replace('/var/lib', str(self.root_path / 'varlib'))
            source = source.replace('/var/webos-profile', str(self.root_path / 'profiles'))
            source = source.replace('/media/developer/temp', str(self.root_path / 'public'))
            source = source.replace('/tmp/.cytv-installer', str(self.root_path / 'private'))
            source = source.replace("'/proc/'", repr(str(self.root_path / 'proc') + '/'))
            boot_id = self.root_path / 'boot'
            boot_id.write_text(self.boot)
            source = source.replace('/proc/sys/kernel/random/boot_id', str(boot_id))
            tmp_root = self.root_path / 'volatile'
            tmp_root.mkdir(exist_ok=True)
            tmp_root.chmod(0o111)
            source = source.replace("'/tmp'", repr(str(tmp_root)))
            source = ('var fixtureFs=require("fs"),lstat=fixtureFs.lstatSync;'
                      'fixtureFs.lstatSync=function(p){var s=lstat(p);if(p===' +
                      json.dumps(str(tmp_root)) + ')s.uid=0;return s;};\n') + source
            result = subprocess.run([os.environ.get('NODE_EXEC') or shutil.which('node')], input=self.transform_cleanup(source).encode(),
                                    capture_output=True, timeout=timeout)
            if result.returncode:
                raise RuntimeError(result.stderr.decode())
            if self.cut_after_cleanup is not None:
                self.cut_after_cleanup(request, json.loads(result.stdout))
            return result.stdout.decode()
        words=split_observer_command(command)
        if '/usr/bin/node' in words and words[words.index('/usr/bin/node')+1:][:1]==['-e']:

            code=words[words.index('-e')+1]
            argument=words[-1]
            if observer.PROGRAM in code or observer.ROOT_PROGRAM in code or observer.STORAGE_SELECT in code:
                request=json.loads(argument)
                request['sender']=str(self.sender)
                request['timeout']=3000
                argument=json.dumps(request)
                self.calls.append(('observer',request['command'],request.get('slot')))
            result=subprocess.run([shutil.which('node'),'-e',code]+words[words.index('-e')+2:-1]+[argument],input=data,capture_output=True,timeout=timeout)
            if result.returncode: raise RuntimeError(result.stderr.decode())
            reply=result.stdout.decode()
            if (observer.PROGRAM in code or observer.ROOT_PROGRAM in code) and self.cut and request['command']=='status':
                value=json.loads(reply)
                if value['slots'][0]['terminal']=='success':
                    self.cut=False
                    raise RuntimeError('simulated host disconnect after durable Helper terminal')
            return reply
        if command.startswith('if ') and 'CYTV_REMAINS' in command:
            paths=[Path(word) for word in words if word.startswith(str(self.root_path))]
            return 'CYTV_REMAINS' if any(path.exists() or path.is_symlink() for path in paths) else ''
        return super().run(command,data,timeout)

    def upload(self,path,data,mode=0o600):
        super().upload(path,data,mode)
        if not str(path).startswith(str(self.root_path)+'/'):
            raise RuntimeError('new bound observer staging required')
        from cytv.transport import SSH
        command=SSH._upload_command(path,hashlib.sha256(data).hexdigest(),mode)
        self.run_upload(command,data)

    def run_upload(self,command,data):
        result=subprocess.run(['sh','-c',command],input=data,capture_output=True,timeout=10)
        if result.returncode:raise RuntimeError(result.stderr.decode())
        return result.stdout.decode()

    def luna(self,uri,payload,**kwargs):
        if uri == 'com.webos.appInstallService/status':
            from cytv.errors import TVRejected
            raise TVRejected('Denied', {'returnValue': False, 'errorCode': -1}, uri)
        if uri.endswith('/dev/remove'):
            self.calls.append(('luna', uri, payload))
            source = self.root_path / 'installed.json'
            apps = json.loads(source.read_text())
            app = payload['id']
            apps.pop(app)
            source.write_text(json.dumps(apps))
            (self.root_path/'legacy-bus/services/pub'/(app+'.service.service')).unlink(missing_ok=True)
            for kind, name in [('applications', app), ('packages', app),
                               ('services', app + ('.renewal' if app == operations.HOME else '.service'))]:
                shutil.rmtree(self.root_path / 'apps/usr/palm' / kind / name, ignore_errors=True)
            return {'returnValue': True, 'id': app, 'details': {'state': 'removed'}}
        if uri.endswith('/dev/listApps'):
            source=self.root_path/'installed.json'
            self.installed=[{'id':app,'version':version} for app,version in json.loads(source.read_text()).items() if app not in self.omit] if source.exists() else []
        return super().luna(uri,payload,**kwargs)


@unittest.skipIf(os.name=='nt','The TV observer requires a POSIX process fixture')
class OriginalOperationIntegration(unittest.TestCase):
    def setUp(self):
        from tests.cytv.test_no_root_observer import PROCESS_TMP
        fixture=operations_fixture.OperationTests()
        with patch('tempfile.tempdir',PROCESS_TMP):fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.root=fixture.root.resolve()
        self.root.chmod(0o755)
        self.store=state.Store(self.root/'state')
        self.profile=state.target('test-tv','no-root')
        self.remote=ProcessRemote(self.root)
        (self.root/'public').mkdir()
        self.base=str(self.root/'apps/usr/palm')
        for target,value in ((observer,'ROOT'),(observer,'PUBLIC_ROOT')):
            patcher=patch.object(target,value,str(self.root/('private' if value=='ROOT' else 'public')))
            patcher.start();self.addCleanup(patcher.stop)
        for name,value in (('BASE',self.base),('HELPER_STATE',self.base+'/applications/'+operations.HELPER+'/state')):
            patcher=patch.object(operations,name,value);patcher.start();self.addCleanup(patcher.stop)
        self.installer=operations.Installer(self.remote,self.store,self.profile,fixture.payload,fixture.manifest,lambda *_:None)
        self.inventory=fixture.inventory

    def test_removal_review_checks_binding_without_touching_evidence(self):
        from cytv.desktop import DesktopConsole
        from cytv.diagnostic_context import status_summary
        from cytv.errors import UserError
        from cytv.recovery import recover

        run = self.remote.run
        def interrupt(command, data=None, timeout=30):
            if data and data.startswith(b'!<arch>'):
                raise OSError('simulated upload interruption')
            return run(command, data, timeout)

        self.remote.run = interrupt
        with self.assertRaises(UserError):
            self.installer.install(self.inventory, 'fixture')
        self.remote.run = run
        (self.root / 'proc').mkdir()
        stage, = (self.root / 'public').glob('cytv-*')
        stage.chmod(0o777)
        pending = self.store.request_clean_removal(self.profile)
        capsule = self.store._capsule_path(self.profile, pending['previous']['observer_operation'])

        def evidence():
            return {str(path): path.read_bytes()
                    for root in (self.root / 'private', self.store.root)
                    for path in root.rglob('*') if path.is_file()}

        before = evidence()
        status = self.installer.observe_recovery()
        self.assertEqual(status_summary(status)['removal_binding'],
                         {'capsule': 'verified', 'reservation': 'matched'})
        self.assertEqual(evidence(), before)
        capsule.unlink()
        without_capsule = evidence()
        status = self.installer.observe_recovery()
        self.assertEqual(status_summary(status)['removal_binding'],
                         {'capsule': 'capsule-missing', 'reservation': 'matched'})
        self.assertEqual(evidence(), without_capsule)
        console = DesktopConsole(lambda *_: None)
        recover(self.installer, lambda _: 'n', console, initial_observation=status)
        self.assertEqual(evidence(), without_capsule)

        # Even after a successful review, removal must recheck the TV plan.
        plan_path = self.root / 'private/operations' / pending['previous']['observer_operation'] / 'plan.json'
        original = plan_path.read_bytes()
        plan = json.loads(original)
        plan['diagnostic_id'] = '0' * 32
        plan_path.write_text(observer.canonical(plan))
        with self.assertRaisesRegex(UserError, 'reservation could not be verified'):
            recover(self.installer, lambda _: 'y', console, initial_observation=status)
        self.assertFalse((self.root / 'private/active/cancel-removal.json').exists())
        self.assertFalse((self.root / 'requests').exists())
        plan_path.write_bytes(original)

        active = self.root / 'private/active'
        owner, = active.iterdir()
        competing_owner = active / ('owner-' + '0' * 32 + '.json')
        owner.rename(competing_owner)
        before_conflict = evidence()
        conflict = self.installer.observe_recovery()
        self.assertEqual(conflict['removal_binding']['reservation'], 'conflict')
        self.assertNotIn('continue-removal', conflict['assessment']['actions'])
        self.assertEqual(evidence(), before_conflict)
        competing_owner.rename(owner)

        recover(self.installer, lambda _: 'y', console)
        self.assertIsNone(self.store.pending(self.profile))
        self.assertFalse((self.root / 'private' / 'active').exists())
        self.assertFalse(capsule.exists())
        self.assertFalse((self.root / 'requests').exists())
        self.assertTrue(self.installer.install(self.inventory, 'fresh-secret')['launch_requested'])
        self.assertEqual((self.root / 'requests').read_text().splitlines(), list(observer.APPS))

    def test_missing_capsule_with_incomplete_history_requires_only_live_reservation_proof(self):
        from cytv.errors import UserError

        run = self.remote.run

        def interrupt(command, data=None, timeout=30):
            if data and data.startswith(b'!<arch>'):
                raise OSError('simulated upload interruption')
            return run(command, data, timeout)

        self.remote.run = interrupt
        with self.assertRaises(UserError):
            self.installer.install(self.inventory, 'fixture')
        self.remote.run = run
        (self.root / 'proc').mkdir()
        pending = self.store.request_clean_removal(self.profile)
        operation = pending['previous']['observer_operation']
        self.store._capsule_path(self.profile, operation).unlink()
        private = self.root / 'private'
        operation_dir = private / 'operations' / operation
        (operation_dir / 'plan.json').unlink()

        active = private / 'active'
        prepared = operation_dir / 'reservation'
        for reservation in (active, prepared):
            with self.subTest(reservation=reservation.name):
                binding = self.installer.observe_recovery()['removal_binding']
                self.assertEqual(binding, {'capsule': 'capsule-missing', 'reservation': 'unverified'})
                with self.assertRaisesRegex(UserError, 'reservation could not be verified'):
                    self.installer.continue_clean_removal(self.store.pending(self.profile))
                self.assertFalse((reservation / 'cancel-removal.json').exists())
                self.assertFalse((self.root / 'requests').exists())
                if reservation == active:
                    active.rename(prepared)

        shutil.rmtree(prepared)
        binding = self.installer.observe_recovery()['removal_binding']
        self.assertEqual(binding, {'capsule': 'capsule-missing', 'reservation': 'absent'})
        self.assertTrue(self.installer.uninstall_project()['verified_clean'])
        self.assertIsNone(self.store.pending(self.profile))
        self.assertFalse((self.root / 'requests').exists())

    def test_cli_cancels_owned_partial_install_and_can_install_fresh(self):
        from cytv import cli
        (self.root / 'proc').mkdir()
        self.remote.cut = True
        with self.store.lock(self.profile), self.assertRaises(RuntimeError):
            self.installer.install(self.inventory, 'original-secret')
        old = self.store.pending(self.profile)
        plan = observer.capsule(self.installer, old)['plan']
        directory = self.store.device_dir(self.profile)
        original = (directory / 'operation.json').read_bytes()
        self.store.save(self.profile)
        (directory / 'known_hosts').write_text('trusted-by-fixture\n')
        args = ['uninstall', '--host', self.profile['host'], '--edition', 'no-root',
                '--data-dir', str(self.store.root), '--yes', '--non-interactive', '--language', 'en']
        output = []

        def remove():
            with patch('cytv.cli.package.verify_payload', return_value=self.installer.manifest):
                return cli.main(args, write=output.append, connect=lambda *_: self.remote,
                                payload_root=self.installer.payload)

        with self.store.lock(self.profile):
            self.assertNotEqual(remove(), 0)
        self.assertEqual((directory / 'operation.json').read_bytes(), original)
        self.assertEqual(remove(), 0, output)
        self.assertIsNone(self.store.pending(self.profile), output)
        self.assertEqual((self.root / 'requests').read_text().splitlines(), [operations.HELPER])
        self.assertFalse((self.root / 'private/active').exists())
        self.assertEqual([call[2]['id'] for call in self.remote.calls if call[1].endswith('/dev/remove')],
                         [operations.HELPER])
        finished = json.loads((directory / 'clean-removal.json').read_text())
        self.assertEqual((directory / finished['original_receipt']).read_bytes(), original)
        self.assertEqual(finished['previous']['observer_operation'], plan['operation'])
        self.installer.install(self.inventory, 'fresh-secret')
        self.assertEqual((self.root / 'requests').read_text().splitlines(), [operations.HELPER, *observer.APPS])

    def test_owned_fence_survives_lost_acknowledgement_and_blocks_old_attach(self):
        from cytv.errors import UserError
        (self.root / 'proc').mkdir()
        self.remote.cut = True
        with self.assertRaises(RuntimeError):
            self.installer.install(self.inventory, 'original-secret')
        plan = observer.capsule(self.installer, self.store.pending(self.profile))['plan']
        original_source = self.root / 'private/operations' / plan['operation'] / 'observer.js'
        source_bytes = original_source.read_bytes()
        observed = []

        def disconnect_once(request, reply):
            if not observed and reply.get('cancellation', {}).get('reservation'):
                observed.append(request['removal'])
                raise UserError('Connection interrupted', reason_code='connection-interrupted')

        self.remote.cut_after_cleanup = disconnect_once
        with self.assertRaises(UserError):
            self.installer.uninstall_project()
        active = self.root / 'private/active'
        self.assertEqual(sorted(p.name for p in active.iterdir()),
                         ['cancel-removal.json', 'owner-' + plan['operation'] + '.json'])
        self.assertEqual(original_source.read_bytes(), source_bytes)
        with self.assertRaises(UserError):
            observer.invoke(self.remote, plan, 'attach')
        self.installer.store = state.Store(self.store.root)
        self.assertTrue(self.installer.uninstall_project()['verified_clean'])
        finished = json.loads((self.store.device_dir(self.profile) / 'clean-removal.json').read_text())
        self.assertEqual(observed, [finished['removal_operation']])
        self.assertEqual((self.root / 'requests').read_text().splitlines(), [operations.HELPER])

    def test_interrupted_two_link_fence_publication_is_resumable(self):
        (self.root / 'proc').mkdir()
        self.remote.cut = True
        with self.assertRaises(RuntimeError):
            self.installer.install(self.inventory, 'original-secret')
        old = self.store.pending(self.profile)
        self.remote.transform_cleanup = lambda code: code.replace(
            'fs.linkSync(tmp,fence);', 'fs.linkSync(tmp,fence);process.exit(79);')
        with self.assertRaises(RuntimeError):
            self.installer.uninstall_project()
        goal = self.store.pending(self.profile)['removal_operation']
        marker = self.root / 'private/active/cancel-removal.json'
        self.assertEqual(marker.stat().st_nlink, 2)
        self.remote.transform_cleanup = lambda code: code
        observation = self.installer.observe_recovery()
        self.assertEqual(observation['removal_binding'],
                         {'capsule': 'verified', 'reservation': 'interrupted'})
        self.assertIn('continue-removal', observation['assessment']['actions'])
        self.assertEqual(marker.stat().st_nlink, 2)
        self.store._capsule_path(self.profile, old['observer_operation']).unlink()
        plan_path = self.root / 'private/operations' / old['observer_operation'] / 'plan.json'
        self.remote.transform_cleanup = lambda code: code.replace(
            'if(stat)remove(opdir,stat);',
            'if(stat){fs.unlinkSync(opdir+"/plan.json");process.exit(79);}')
        self.installer.store = state.Store(self.store.root)
        with self.assertRaises(RuntimeError):
            self.installer.uninstall_project()
        self.assertFalse(plan_path.exists())
        self.assertTrue(plan_path.parent.exists())
        self.assertEqual(self.store.pending(self.profile)['stage'], 'verified-clean')
        self.remote.transform_cleanup = lambda code: code
        self.installer.store = state.Store(self.store.root)
        self.assertEqual(self.installer.observe_recovery()['removal_binding'],
                         {'capsule': 'capsule-missing', 'reservation': 'absent'})
        self.assertTrue(self.installer.uninstall_project()['verified_clean'])
        self.assertFalse(marker.exists())
        self.assertEqual((self.root / 'requests').read_text().splitlines(), [operations.HELPER])
        finished = json.loads((self.store.device_dir(self.profile) / 'clean-removal.json').read_text())
        self.assertEqual(finished['removal_operation'], goal)
        self.assertEqual(finished['previous'], old)
        self.installer.install(self.inventory, 'fresh-secret')
        self.assertEqual((self.root / 'requests').read_text().splitlines(), [operations.HELPER, *observer.APPS])

    def test_worker_admitted_before_fence_can_publish_claim_during_drain(self):
        from concurrent.futures import ThreadPoolExecutor
        from time import monotonic, sleep

        self.remote.cut = True
        with self.assertRaises(RuntimeError):
            self.installer.install(self.inventory, 'original-secret')
        original = observer.capsule(self.installer, self.store.pending(self.profile))
        plan = original['plan']
        observer.readback(self.installer, original, 0)
        observer.invoke(self.remote, plan, 'readback', 0)
        opdir = self.root / 'private/operations' / plan['operation']
        ready = self.root / 'worker-attached'
        resume = self.root / 'release-worker'
        sender = self.remote.sender.read_text()
        late_sender = self.root / 'late-sender'
        late_sender.write_text(sender.replace(
            "print(json.dumps({'returnValue':True,'details':{'state':terminal}}),flush=True)",
            "sys.exit(0)"))
        late_sender.chmod(0o700)
        data = {'root': str(self.root / 'private'), 'public_root': str(self.root / 'public'),
                'plan': plan, 'command': 'worker', 'slot': 1, 'sender': str(late_sender), 'timeout': 3000}
        # Instrument the bundled observer in memory to hold the real worker just
        # after attached(), before the exclusive package claim. On-disk bytes stay exact.
        hold = 'fs.writeFileSync(' + json.dumps(str(ready)) + ', "ready");' + (
            'while(!exists(' + json.dumps(str(resume)) + ')){}')
        worker = observer.PROGRAM.replace('attached();predecessor(i);', 'attached();' + hold + 'predecessor(i);')
        child = subprocess.Popen([shutil.which('node'), '-e', worker, json.dumps(data)], stderr=subprocess.DEVNULL)
        self.addCleanup(lambda: (child.kill(), child.wait()) if child.poll() is None else None)
        fake_proc = self.root / 'proc' / str(child.pid)
        fake_proc.mkdir(parents=True)
        (fake_proc / 'cmdline').write_text('/usr/bin/node\0' + str(opdir / 'observer.js') + '\0')
        deadline = monotonic() + 5
        while not ready.exists() and child.poll() is None and monotonic() < deadline:
            sleep(.01)
        self.assertTrue(ready.exists())
        self.assertFalse((opdir / 'claim-1.json').exists())
        self.store._capsule_path(self.profile, plan['operation']).unlink()

        def release_after_poll_starts():
            deadline = monotonic() + 5
            polling = self.root / 'idle-first-sample'
            while not polling.exists() and monotonic() < deadline:
                sleep(.01)
            resume.touch()
            self.assertTrue(polling.exists())
            self.assertEqual(child.wait(timeout=5), 0)
            shutil.rmtree(fake_proc)

        self.remote.transform_cleanup = lambda code: code.replace(
            'setTimeout(checkIdle,250);return;',
            'fs.writeFileSync(' + json.dumps(str(self.root / 'idle-first-sample')) +
            ',"polling");setTimeout(checkIdle,250);return;')
        with ThreadPoolExecutor(max_workers=1) as executor:
            released = executor.submit(release_after_poll_starts)
            result = self.installer.uninstall_project()
            released.result()
        self.assertEqual((self.root / 'requests').read_text().splitlines(), list(observer.APPS))
        self.assertTrue(result.get('restart_required'), result)
        self.assertTrue((opdir / 'claim-1.json').exists())
        self.assertEqual([call[2]['id'] for call in self.remote.calls if call[1].endswith('/dev/remove')],
                         list(observer.APPS))
        self.assertEqual(json.loads((self.root / 'installed.json').read_text()), {})
        self.assertFalse((opdir / 'terminal-1.json').exists())
        self.assertEqual(self.store.pending(self.profile)['cleanup_restart_triggers'], ['original-package-unverified'])

        luna = self.remote.luna
        def idle(uri, payload, **options):
            if uri.endswith('/status'):
                return {'returnValue': True, 'status': {'apps': []}}
            return luna(uri, payload, **options)

        self.remote.luna = idle
        self.assertTrue(self.installer.uninstall_project()['verified_clean'])
        self.assertIsNone(self.store.pending(self.profile))
        self.installer.install(self.inventory, 'fresh-secret')
        self.assertEqual((self.root / 'requests').read_text().splitlines(), list(observer.APPS)*2)

    def test_legacy_omitted_helper_removes_and_supports_fresh_install(self):
        from cytv.errors import UserError

        for lost in (False, True):
            with self.subTest(lost=lost):
                case = OriginalOperationIntegration()
                case.setUp()
                try:
                    case.run_legacy_omitted_helper_history(lost, UserError)
                finally:
                    case.doCleanups()

    def run_legacy_omitted_helper_history(self, lost, error_type):
        (self.root/'proc').mkdir()
        (self.root/'legacy-bus/services/pub').mkdir(parents=True)
        self.remote.cut = True
        with self.assertRaises(RuntimeError):
            self.installer.install(self.inventory, 'original-secret')
        app = operations.HELPER
        self.remote.omit.add(app)
        (self.root/'legacy-bus/services/pub'/(app+'.service.service')).write_text('[D-BUS Service]\n')
        goal = self.store.request_clean_removal(self.profile)['removal_operation']
        original_luna = self.remote.luna

        def luna(uri, payload, **kwargs):
            if uri.endswith('/dev/remove'):
                reply = original_luna(uri,payload,**kwargs)
                if lost:
                    raise error_type('Connection interrupted', reason_code='connection-interrupted')
                return reply
            if uri.endswith('/getAppInfo'):
                from cytv.errors import TVRejected
                raise TVRejected('Denied',{'returnValue':False,'errorCode':-1},uri)
            return original_luna(uri,payload,**kwargs)

        self.remote.luna = luna
        if lost:
            with self.assertRaises(error_type):
                self.installer.uninstall_project()
            pending = self.store.pending(self.profile)
            self.assertEqual(pending['removal_operation'],goal)
            self.assertEqual(pending['removals'],{app:'submitted'})
            self.installer.store = state.Store(self.store.root)

            def idle(uri, payload, **kwargs):
                if uri.endswith('/status'):
                    return {'returnValue':True,'status':{'apps':[]}}
                return luna(uri,payload,**kwargs)
            self.remote.luna = idle
        self.assertTrue(self.installer.uninstall_project()['verified_clean'])
        self.assertIsNone(self.store.pending(self.profile))
        self.assertEqual([call[2]['id'] for call in self.remote.calls if call[1].endswith('/dev/remove')],[app])
        completed = json.loads((self.store.device_dir(self.profile)/'clean-removal.json').read_text())
        self.assertEqual(completed['removal_operation'],goal)
        self.remote.omit.clear()
        self.installer.install(self.inventory,'fresh-secret')
        self.assertEqual((self.root/'requests').read_text().splitlines(),[app,*observer.APPS])

    def test_unanswered_optional_monitor_allows_supported_remove_and_fresh_install(self):
        for mode in ('empty', 'timeout'):
            with self.subTest(mode=mode):
                case = OriginalOperationIntegration()
                case.setUp()
                try:
                    case.unanswered_monitor_history(mode)
                finally:
                    case.doCleanups()

    def unanswered_monitor_history(self, mode):
        from unittest.mock import Mock
        from cytv.errors import UserError
        from cytv.transport import SSH

        (self.root/'proc').mkdir()
        self.remote.cut = True
        app = operations.HELPER
        with self.assertRaises(RuntimeError):
            self.installer.install(self.inventory, 'original-secret')
        installed = self.root/'installed.json'
        self.assertEqual(set(json.loads(installed.read_text())), {app})
        self.installer.store = self.store = state.Store(self.store.root)
        original = self.remote.luna
        monitor = object.__new__(SSH)
        monitor.root = False
        channel = Mock()
        monitor.channel = Mock(return_value=channel)
        monitor.chunks = (lambda channel, timeout: iter(())) if mode == 'empty' else (
            lambda channel, timeout: SSH.chunks(monitor, channel, 0))
        uri = 'com.webos.appInstallService/status'
        goal = self.store.request_clean_removal(self.profile)
        idle = False
        removals = []

        def luna(endpoint, payload, **options):
            if endpoint == uri:
                if idle:
                    return {'returnValue':True, 'status':{'apps':[]}}
                return monitor.luna(endpoint, payload, **options)
            if endpoint.endswith('/dev/remove'):
                removals.append(payload['id'])
            return original(endpoint, payload, **options)

        self.remote.luna = luna
        with self.assertRaises(UserError) as strict:
            operations.require_removal_idle(monitor, self.profile, goal)
        expected = 'user-error' if mode == 'empty' else 'operation-timeout'
        self.assertEqual(strict.exception.reason_code, expected)
        channel.close.reset_mock()

        self.assertTrue(self.installer.uninstall_project()['verified_clean'])
        channel.close.assert_called_once()
        self.assertEqual(removals, [app])
        self.assertEqual(json.loads(installed.read_text()), {})
        self.assertIsNone(self.store.pending(self.profile))
        self.installer.install(self.inventory, 'fresh-secret')
        self.assertIsNone(self.store.pending(self.profile))

        # An already submitted vendor request still needs independent settlement.
        remove = self.remote.luna
        def lose_vendor_reply(endpoint, payload, **options):
            reply = remove(endpoint, payload, **options)
            if endpoint.endswith('/dev/remove') and payload['id'] == app:
                raise UserError('Connection interrupted', reason_code='connection-interrupted')
            return reply

        self.remote.luna = lose_vendor_reply
        with self.assertRaisesRegex(UserError, 'Connection interrupted'):
            self.installer.uninstall_project()
        pending = self.store.pending(self.profile)
        self.assertEqual(pending['removals'], {app:'submitted'})
        self.remote.luna = luna
        self.assertTrue(self.installer.uninstall_project()['restart_required'])
        self.assertEqual(removals.count(app), 2)
        idle = True
        self.assertTrue(self.installer.uninstall_project()['verified_clean'])
        self.assertEqual(removals.count(app), 2)
        completed = json.loads((self.store.device_dir(self.profile)/'clean-removal.json').read_text())
        self.assertEqual(completed['removal_operation'], pending['removal_operation'])

    def test_second_lost_vendor_reply_needs_proof_newer_than_second_request(self):
        from cytv.errors import UserError

        (self.root / 'proc').mkdir()
        self.remote.cut = True
        with self.assertRaises(RuntimeError):
            self.installer.install(self.inventory, 'original-secret')
        app = operations.HELPER
        residue = Path(self.base) / 'applications' / app / 'appinfo.json'
        registered = self.root / 'installed.json'
        original_luna = self.remote.luna
        submissions = []

        def luna(uri, payload, **kwargs):
            if uri.endswith('/dev/remove'):
                submissions.append((self.remote.boot, payload['id']))
                if len(submissions) == 2:
                    registered.write_text('{}')
                raise UserError('Connection interrupted', reason_code='connection-interrupted')
            return original_luna(uri, payload, **kwargs)

        self.remote.luna = luna
        goal = self.store.request_clean_removal(self.profile)['removal_operation']
        first_kernel = self.remote.boot
        with self.assertRaises(UserError):
            self.installer.uninstall_project()
        self.assertTrue(self.installer.uninstall_project()['restart_required'])
        self.assertEqual(self.store.pending(self.profile)['cleanup_boot_proof']['kernel'], first_kernel)

        self.remote.boot = second_kernel = '22222222-2222-2222-2222-222222222222'
        with self.assertRaises(UserError):
            self.installer.uninstall_project()
        self.assertEqual(json.loads(registered.read_text()), {})
        self.assertEqual(submissions, [(first_kernel, app), (second_kernel, app)])
        self.assertEqual(self.store.pending(self.profile)['removals'], {app: 'submitted'})
        self.assertTrue(self.installer.uninstall_project().get('restart_required'))
        self.assertTrue(residue.exists())
        self.assertEqual(self.store.pending(self.profile)['cleanup_boot_proof']['kernel'], second_kernel)
        with self.assertRaises(UserError) as waiting:
            self.installer.uninstall_project()
        self.assertEqual(waiting.exception.reason_code, 'removal-terminal-unknown')
        self.assertTrue(residue.exists())

        self.remote.boot = '33333333-3333-3333-3333-333333333333'
        self.assertTrue(self.installer.uninstall_project()['verified_clean'])
        self.assertFalse(residue.exists())
        self.assertEqual(submissions, [(first_kernel, app), (second_kernel, app)])
        completed = json.loads((self.store.device_dir(self.profile) / 'clean-removal.json').read_text())
        self.assertEqual(completed['removal_operation'], goal)
        self.installer.install(self.inventory, 'fresh-secret')
        self.assertEqual((self.root / 'requests').read_text().splitlines(), [app, *observer.APPS])

    def test_mixed_removal_keeps_original_eim_settlement_after_vendor_reply_loss(self):
        from cytv import cli
        from cytv.errors import UserError

        (self.root / 'proc').mkdir()
        status_idle = False
        lose_eim = True
        inputs = set()
        removals = []
        actions = []
        original_luna = self.remote.luna

        def luna(uri, payload, **options):
            if uri.endswith('/status') and status_idle:
                return {'returnValue': True, 'status': {'apps': []}}
            if uri.endswith('/addDevice'):
                inputs.add(payload['appId'])
                if lose_eim:
                    raise UserError('Connection interrupted during EIM reply', reason_code='connection-interrupted')
            if uri.endswith('/getAllInputStatus'):
                return {'returnValue': True, 'devices': [{'appId': app} for app in sorted(inputs)]}
            if uri.endswith('/deleteDevice'):
                inputs.discard(payload['appId'])
            if uri.endswith('/dev/remove'):
                removals.append((self.remote.boot, payload['id']))
                terminal = original_luna(uri, payload, **options)
                if payload['id'] == operations.HELPER:
                    raise UserError('Connection interrupted during vendor reply', reason_code='connection-interrupted')
                return terminal
            return original_luna(uri, payload, **options)

        def remove():
            self.installer.store = self.store = state.Store(self.store.root)
            with self.store.lock(self.profile):
                return self.installer.uninstall_project()

        self.remote.luna = luna
        self.remote.cut_after_cleanup = lambda request, reply: actions.append(request['action'])
        with self.store.lock(self.profile), self.assertRaisesRegex(UserError, 'EIM reply'):
            self.installer.install(self.inventory, 'original-secret')
        old = self.store.pending(self.profile)
        opdir = self.root / 'private/operations' / old['observer_operation']
        self.assertTrue((opdir / 'config-claim-eim.json').exists())
        self.assertFalse((opdir / 'config-result-eim.json').exists())
        self.assertEqual(inputs, {operations.HOME})

        self.assertTrue(remove()['restart_required'])
        first = self.store.pending(self.profile)
        self.assertEqual(first['cleanup_restart_triggers'], ['original-configuration-unverified'])
        self.assertEqual(first['cleanup_boot_proof']['kernel'], self.remote.boot)
        with self.assertRaises(UserError) as waiting:
            remove()
        self.assertEqual(waiting.exception.reason_code, 'removal-terminal-unknown')
        self.assertFalse(removals)

        self.remote.boot = kernel_b = '22222222-2222-2222-2222-222222222222'
        checkpoint = state.Store.checkpoint

        def lose_checkpoint_ack(store, profile, **fields):
            checkpoint(store, profile, **fields)
            if 'cleanup_original_configuration_settled' in fields:
                raise OSError('Host interrupted after configuration settlement')

        with patch.object(state.Store, 'checkpoint', lose_checkpoint_ack):
            with self.assertRaisesRegex(OSError, 'after configuration settlement'):
                remove()
        self.assertFalse(removals)
        self.assertEqual(inputs, {operations.HOME})
        with self.assertRaisesRegex(UserError, 'vendor reply'):
            remove()
        self.assertEqual(self.store.pending(self.profile)['removals'], {operations.HELPER: 'submitted'})
        self.assertEqual(removals, [(kernel_b, operations.HELPER)])
        self.assertFalse(inputs)
        self.assertTrue(remove()['restart_required'])
        second = self.store.pending(self.profile)
        self.assertEqual(second['cleanup_restart_triggers'], ['package-removal-unverified'])
        self.assertEqual(second['cleanup_boot_proof']['kernel'], kernel_b)
        with self.assertRaises(UserError) as waiting:
            remove()
        self.assertEqual(waiting.exception.reason_code, 'removal-terminal-unknown')
        self.assertEqual(removals, [(kernel_b, operations.HELPER)])
        self.assertFalse((opdir / 'config-result-eim.json').exists())

        status_idle = True
        self.store.save(self.profile)
        (self.store.device_dir(self.profile) / 'known_hosts').write_text('trusted-by-fixture\n')
        args = ['uninstall', '--host', self.profile['host'], '--edition', 'no-root',
                '--data-dir', str(self.store.root), '--yes', '--non-interactive', '--language', 'en']
        output = []
        before = len(actions)
        with patch('cytv.cli.package.verify_payload', return_value=self.installer.manifest):
            self.assertEqual(cli.main(args, write=output.append, connect=lambda *_: self.remote,
                                      payload_root=self.installer.payload), 0, output)
        self.assertIsNone(self.store.pending(self.profile), output)
        self.assertNotIn('boot-create', actions[before:])
        self.assertEqual(removals, [(kernel_b, operations.HELPER), (kernel_b, operations.HOME)])
        self.assertEqual(json.loads((self.root / 'installed.json').read_text()), {})
        self.assertFalse((self.root / 'private/active').exists())
        self.assertFalse(inputs)
        finished = json.loads((self.store.device_dir(self.profile) / 'clean-removal.json').read_text())
        self.assertEqual(finished['removal_operation'], first['removal_operation'])

        lose_eim = False
        with self.store.lock(self.profile):
            self.installer.install(self.inventory, 'fresh-secret')
        self.assertEqual(inputs, {operations.HOME})
        self.assertEqual((self.root / 'requests').read_text().splitlines(), list(observer.APPS) * 2)
        self.assertIsNone(self.store.pending(self.profile))

    def test_closed_release_cut_with_missing_historical_launch_result_allows_removal(self):
        from cytv.errors import UserError
        (self.root / 'proc').mkdir()
        invoke = observer.invoke
        cut = []

        def lose_release(remote, plan, command, *args, **kwargs):
            if command == 'release' and not cut:
                cut.append(plan)
                installed = self.root / 'private/operations' / plan['operation']
                active = self.root / 'private/active'
                owner = active / ('owner-' + plan['operation'] + '.json')
                # Run the real producer through durable closure, before its
                # owner unlink (equivalent to loss of power or SSH here).
                source = observer.PROGRAM.replace(
                    "if(exists(active+'/'+marker)){",
                    "throw Error('synthetic release cut');if(exists(active+'/'+marker)){", 1)
                original_run = remote.run

                def run(command, **options):
                    words = split_observer_command(command)
                    code = words[words.index('-e') + 1].replace(observer.PROGRAM, source)
                    return original_run('/usr/bin/node -e ' + shlex.quote(code) + ' ' +
                                        shlex.quote(words[-1]), **options)

                with patch.object(remote, 'run', side_effect=run):
                    with self.assertRaises(UserError):
                        invoke(remote, plan, command, *args, **kwargs)
                self.assertTrue(owner.exists())
                self.assertTrue((installed / 'closed.json').exists())
                (installed / 'config-result-launch.json').unlink()
                raise UserError('Connection interrupted', reason_code='connection-interrupted')
            return invoke(remote, plan, command, *args, **kwargs)

        with patch.object(observer, 'invoke', side_effect=lose_release):
            with self.assertRaises(UserError):
                self.installer.install(self.inventory, 'original-secret')
        self.assertTrue(self.installer.uninstall_project()['verified_clean'])
        self.assertFalse((self.root / 'private/active').exists())
        self.assertEqual([call[2]['id'] for call in self.remote.calls if call[1].endswith('/dev/remove')],
                         list(observer.APPS))

    @unittest.skipIf(getattr(os,'getuid',lambda:0)()==0,'Requires an unprivileged Developer Mode user')
    def test_execute_only_tmp_uses_owned_jail_storage_and_resumes_pinned_operation(self):
        jail=self.root/'jail';jail.mkdir(mode=0o755)
        blocked=self.root/'blocked-tmp';blocked.mkdir(mode=0o111)
        self.addCleanup(blocked.chmod,0o755)
        private=str(jail/'.cytv-installer')
        self.remote.cut=True
        with patch.object(observer,'ROOT',str(blocked/'.cytv-installer')), \
             patch.object(observer,'JAIL_ROOT',private,create=True):
            with self.assertRaises(RuntimeError):self.installer.install(self.inventory,'original-secret')
            pending=self.store.pending(self.profile)
            self.assertIsNotNone(pending)
            saved=observer.capsule(self.installer,pending)
            self.assertEqual(saved['plan']['private_root'],private)
            self.assertEqual(Path(private).stat().st_mode&0o777,0o700)
            self.assertEqual((self.root/'requests').read_text().splitlines(),[operations.HELPER])
            # Continuation must use the original owned leaf even when its
            # parent loses write access, without selecting another root.
            jail.chmod(0o555);self.addCleanup(jail.chmod,0o755)
            before=len(self.remote.calls)
            self.installer.continue_no_root(pending)
            self.assertFalse(any(call[:2]==('observer','storage-select') for call in self.remote.calls[before:]))
            self.assertIsNone(self.store.pending(self.profile))
            self.assertEqual((self.root/'requests').read_text().splitlines(),list(observer.APPS))
            self.assertTrue((Path(private)/'operations'/pending['observer_operation']/'closed.json').exists())
            self.assertEqual(list((self.root/'public').iterdir()),[])

    def test_existing_legacy_storage_is_not_bypassed_for_a_new_jail_root(self):
        (self.root/'private').mkdir(mode=0o755)  # Unsafe private leaf; never repair it.
        jail=self.root/'jail';jail.mkdir(mode=0o755)
        with patch.object(observer,'JAIL_ROOT',str(jail/'.cytv-installer'),create=True):
            with self.assertRaises(RuntimeError):self.installer.install(self.inventory,'original-secret')
        self.assertIsNone(self.store.pending(self.profile))
        self.assertFalse((jail/'.cytv-installer').exists())
        self.assertEqual((self.root/'private').stat().st_mode&0o777,0o755)
        self.assertFalse((self.root/'requests').exists())

    def test_two_existing_private_roots_refuse_setup_without_repair_or_submission(self):
        (self.root/'private').mkdir(mode=0o700)
        jail=self.root/'jail';jail.mkdir(mode=0o755)
        alternative=jail/'.cytv-installer';alternative.mkdir(mode=0o700)
        evidence=alternative/'retained';evidence.write_bytes(b'keep')
        with patch.object(observer,'JAIL_ROOT',str(alternative),create=True):
            with self.assertRaises(RuntimeError):self.installer.install(self.inventory,'original-secret')
        self.assertIsNone(self.store.pending(self.profile))
        self.assertFalse((self.root/'requests').exists())
        self.assertEqual(evidence.read_bytes(),b'keep')

    def test_legacy_capsule_stays_bound_and_foreign_private_root_is_rejected(self):
        self.remote.cut=True
        with self.assertRaises(RuntimeError):self.installer.install(self.inventory,'original-secret')
        pending=self.store.pending(self.profile)
        original=observer.capsule(self.installer,pending)
        self.assertNotIn('private_root',original['plan'])
        self.assertEqual(observer.private_root(original['plan']),str(self.root/'private'))
        before=len(self.remote.calls)
        for root in ('/media/developer/temp/foreign',None,{},[]):
            changed=dict(original,plan=dict(original['plan'],private_root=root))
            with self.subTest(root=root), patch.object(self.store,'read_capsule',return_value=changed):
                with self.assertRaises(RuntimeError):observer.capsule(self.installer,pending)
        self.assertEqual(len(self.remote.calls),before)
        self.assertEqual((self.root/'requests').read_text().splitlines(),[operations.HELPER])
        self.assertEqual(self.store.pending(self.profile),pending)

    def test_devmode_ramfs_allows_install_only_when_developer_storage_fits(self):
        jail=self.root/'jail';jail.mkdir(mode=0o755)
        private=jail/'.cytv-installer';private.mkdir(mode=0o700)
        original=self.remote.run
        def run(command,**kwargs):
            if command == "LC_ALL=C stat -f -c '%t' /tmp":
                return fs_magic
            if command=='LC_ALL=C df -Pk /tmp':
                return 'Filesystem 1024-blocks Used Available Capacity Mounted on\n' + tmp_row
            if command=='LC_ALL=C df -Pk /media/developer':
                return 'Filesystem 1024-blocks Used Available Capacity Mounted on\n' + developer_row
            return original(command,**kwargs)
        self.remote.run=run
        developer_available = '/dev/apps 10000000 0 10000000 0% /media/developer'
        developer_full = '/dev/apps 10000000 10000000 0 100% /media/developer'
        tmp_zero = 'tmp 0 0 0 0% /tmp'
        for tmp_row, fs_magic, developer_row, full_path in (
            ('/dev/tmp 1024 1024 0 100% /tmp', '1021994', developer_available, '/tmp'),
            (tmp_zero, '', developer_available, '/tmp'),
            (tmp_zero, '858458f6', developer_full, '/media/developer'),
        ):
            with self.subTest(tmp=tmp_row, fs_magic=fs_magic, full_path=full_path), \
                 patch.object(observer, 'JAIL_ROOT', str(private)):
                with self.assertRaises(RuntimeError) as caught:
                    self.installer.install(self.inventory, 'original-secret')
                self.assertEqual(caught.exception.reason_code, 'tv-storage-full')
                self.assertIn(f'({full_path})', str(caught.exception))
                self.assertIsNone(self.store.pending(self.profile))
                self.assertFalse(any(call[:2] == ('observer', 'storage-select')
                                     for call in self.remote.calls))
                self.assertFalse((self.root/'requests').exists())
                self.assertEqual(list(private.iterdir()), [])

        tmp_row, fs_magic, developer_row = tmp_zero, '858458f6', developer_available
        with patch.object(observer, 'JAIL_ROOT', str(private)):
            self.installer.install(self.inventory, 'original-secret')
        launcher_apps = Path(self.base) / 'applications' / operations.HOME / 'apps.js'
        self.assertIn('window.CYTVNoRootConnection = "developer-mode";', launcher_apps.read_text())
        self.assertEqual((self.root/'requests').read_text().splitlines(), list(observer.APPS))
        self.assertIsNone(self.store.pending(self.profile))

    def test_root_ssh_observer_install_and_remove_keep_original_receipts(self):
        # Host fixture substitutes UID and fixed TV paths only. Run the actual
        # root-transport observer, its private sender and durable package stream.
        self.profile.update(connection='root-ssh', port=22)
        self.remote.root=True
        root_private=str(self.root/'root-private')
        root_public=str(self.root/'root-public')
        source=observer.ROOT_PROGRAM.replace("uid!==0||root!==", 'uid!=='+str(os.geteuid())+'||root!==')
        source=source.replace('/tmp/.cytv-installer-root',root_private).replace('/var/lib/clean-your-tv-installer',root_public)
        ownership_log=str(self.root/'configuration-owners')
        source=source.replace('var uid=process.getuid()',
            'var originalChown=fs.fchownSync;fs.fchownSync=function(fd,uid,gid){fs.appendFileSync('+json.dumps(ownership_log)+',uid+":"+gid+"\\n");return originalChown(fd,uid,gid);};var uid=process.getuid()')
        # ProcessRemote supplies the fixture sender instead of the TV binary.
        source=source.replace("input.sender!=='/usr/bin/luna-send'", 'input.sender!=='+json.dumps(str(self.remote.sender)))
        with patch.object(observer,'ROOT_PROGRAM',source), patch.object(observer,'ROOT_SSH_PRIVATE',root_private), \
             patch.object(observer,'ROOT_SSH_PUBLIC',root_public):
            self.installer.install(self.inventory,'original-secret')
            launcher_apps = Path(self.base) / 'applications' / operations.HOME / 'apps.js'
            self.assertIn('window.CYTVNoRootConnection = "root-ssh";', launcher_apps.read_text())
            self.assertIsNone(self.store.pending(self.profile))
            self.assertEqual((self.root/'requests').read_text().splitlines(),list(observer.APPS))
            owner=Path(operations.HELPER_STATE).stat()
            self.assertEqual(Path(ownership_log).read_text().splitlines(),[str(owner.st_uid)+':'+str(owner.st_gid)]*2,
                             'Both configuration files must inherit the checked sandbox owner/group')
            self.installer.uninstall()
            self.assertIsNone(self.store.pending(self.profile))
            self.assertEqual((self.root/'requests').read_text().splitlines(),list(observer.APPS)*2)
            self.assertEqual(list(Path(root_public).iterdir()),[])

    def test_storage_failure_before_journal_does_not_block_another_setup(self):
        # A valid private namespace, but no writable/usable staging parent.
        with patch.object(observer, 'PUBLIC_ROOT', str(self.root/'missing'/'public')):
            with self.assertRaises(RuntimeError):
                self.installer.install(self.inventory, 'original-secret')
        self.assertIsNone(self.store.pending(self.profile))
        self.assertFalse(list(self.store.device_dir(self.profile).glob('capsule-*.json')))
        self.assertFalse((self.root/'requests').exists())
        self.installer.install(self.inventory, 'original-secret')
        self.assertEqual((self.root/'requests').read_text().splitlines(), list(observer.APPS))

    def test_removal_transport_loss_cannot_be_sealed_by_empty_eim_inventory(self):
        self.installer.install(self.inventory,'original-secret')
        (self.root/'requests').write_text('')
        original=self.remote.luna;deletions=[]
        def luna(uri,payload,**kwargs):
            if uri.endswith('/deleteDevice'):
                deletions.append(payload)
                raise RuntimeError('transport timeout after possible delete submission')
            if uri.endswith('/getAllInputStatus'):return {'returnValue':True,'devices':[]}
            return original(uri,payload,**kwargs)
        self.remote.luna=luna
        with self.assertRaises(RuntimeError):self.installer.uninstall()
        pending=self.store.pending(self.profile)
        self.assertIsNotNone(pending)
        with self.assertRaises(RuntimeError):self.installer.continue_no_root(pending)
        self.assertEqual(len(deletions),1)
        self.assertEqual((self.root/'requests').read_text(),'')
        observed=self.installer.observe_recovery()
        self.assertNotIn('continue-no-root',observed['assessment']['actions'])

    def publish_stop(self, name='blocked'):
        from cytv.tv_sources import node_adapter
        program=node_adapter('state-permissions',"contract.publishStopGeneration(process.argv[process.argv.length-1]);")
        self.remote.run('/usr/bin/node -e '+shlex.quote(program)+' '+shlex.quote(operations.HELPER_STATE))
        (Path(operations.HELPER_STATE)/name).write_bytes(b'explicit-stop')

    def test_running_helper_upgrade_restarts_only_from_its_own_stop(self):
        from cytv.helper_stop import INSTALL_PROGRAM
        self.installer.install(self.inventory, 'original-secret')
        state_dir = Path(operations.HELPER_STATE)
        original = self.remote.run

        for race in ('none', 'before-publication', 'before-capsule', 'after-capsule', 'watchdog'):
            with self.subTest(race=race):
                active = True
                interrupted = False

                def run(command, data=None, timeout=30):
                    nonlocal active, interrupted
                    if command == '/usr/bin/node' and data == INSTALL_PROGRAM.encode():
                        source = data.replace(b'/media/developer/apps/usr/palm/applications/com.local.nativehome/state',
                                              operations.HELPER_STATE.encode())
                        if race == 'before-publication':
                            self.publish_stop()
                        result = subprocess.run(['node'], input=source, capture_output=True)
                        active = False
                        if result.returncode:
                            self.assertEqual(race, 'before-publication')
                            self.assertEqual((state_dir / 'blocked').read_bytes(), b'explicit-stop')
                            raise RuntimeError('a Stop already exists')
                        if race == 'before-capsule':
                            self.publish_stop()
                        return result.stdout.decode()
                    words = split_observer_command(command)
                    if (not interrupted and race in ('after-capsule', 'watchdog') and '-e' in words
                            and observer.PROGRAM in words[words.index('-e')+1]
                            and json.loads(words[-1])['command'] == 'start'):
                        interrupted = True
                        if race == 'after-capsule':
                            self.publish_stop()
                        else:
                            (state_dir / 'watchdog').write_bytes(b'watchdog')
                    return original(command, data, timeout)

                self.remote.run = run
                self.installer.helper_state = lambda timeout=None: 'running' if active else 'stopped'
                before = len(self.remote.calls)
                result = self.installer.install(self.inventory, 'original-secret')
                self.assertEqual(result['launch_requested'], race == 'none')
                generation = (state_dir / 'stop-generation').read_text()
                self.assertRegex(generation, r'^S[a-f0-9]{32}$')
                launches = [row[2].get('params') for row in self.remote.calls[before:]
                            if row[0] == 'luna' and row[1].endswith('/launch')]
                self.assertEqual(launches, [{'nativeHomeSetup': generation}] if race == 'none' else [])
                self.assertIsNone(self.store.pending(self.profile))
                # The fixture's Luna endpoint acknowledges launch without running native.js.
                (state_dir / 'blocked').unlink(missing_ok=True)
                (state_dir / 'watchdog').unlink(missing_ok=True)

    def test_status_retries_during_the_first_write_of_a_slot_claim(self):
        original = self.remote.run
        sampled = False

        def run(command, data=None, timeout=30):
            nonlocal sampled
            words = split_observer_command(command)
            if '-e' in words and observer.PROGRAM in words[words.index('-e') + 1]:
                request = json.loads(words[-1])
                if request['command'] == 'status' and not sampled:
                    # Present a partial claim to one status read, without changing
                    # what the worker writes or allowing a second submission.
                    code = words[words.index('-e') + 1]
                    hook = ("var originalJson=json;json=function(name){"
                            "if(name.slice(-13)==='/claim-0.json')JSON.parse('');"
                            "return originalJson(name);};")
                    probe = "function claimName(i)"
                    code = code.replace(probe, hook + probe, 1)
                    result = subprocess.run([shutil.which('node'), '-e', code, words[-1]],
                                            capture_output=True, check=True, timeout=timeout)
                    reply = json.loads(result.stdout)
                    error = reply.get('observer_error')
                    if error:
                        self.assertEqual(error['exception_name'], 'SyntaxError')
                        sampled = True
                        return json.dumps(reply)
            return original(command, data, timeout)

        self.remote.run = run
        self.installer.install(self.inventory, 'original-secret')
        self.assertTrue(sampled)
        self.assertIsNone(self.store.pending(self.profile))
        self.assertEqual((self.root / 'requests').read_text().splitlines(), list(observer.APPS))

    def test_status_retries_while_terminal_hardlink_is_being_published(self):
        original = self.remote.run
        sampled = False

        def run(command, data=None, timeout=30):
            nonlocal sampled
            words = split_observer_command(command)
            if '-e' in words and observer.PROGRAM in words[words.index('-e') + 1]:
                request = json.loads(words[-1])
                if request['command'] == 'status' and not sampled:
                    op = request['plan']['operation']
                    journal = self.root / 'private' / 'operations' / op
                    terminal = journal / 'terminal-0.json'
                    if terminal.is_file():
                        # atomicNew briefly leaves two links to the terminal inode.
                        temporary = journal / ('.pending-' + 'a' * 32)
                        os.link(terminal, temporary)
                        try:
                            reply = json.loads(original(command, data, timeout))
                            self.assertEqual(reply['observer_error']['observer_reason'],
                                             'unsafe-file')
                            sampled = True
                            return json.dumps(reply)
                        finally:
                            temporary.unlink()
            return original(command, data, timeout)

        self.remote.run = run
        self.installer.install(self.inventory, 'original-secret')
        self.assertTrue(sampled)
        self.assertIsNone(self.store.pending(self.profile))
        self.assertEqual((self.root / 'requests').read_text().splitlines(), list(observer.APPS))

    def test_reinstall_preserves_explicit_stop_and_legacy_latches(self):
        self.installer.install(self.inventory,'original-secret')
        directory=Path(operations.HELPER_STATE)
        for name in ('blocked', 'watchdog'):
            with self.subTest(name=name):
                self.publish_stop(name)
                generation=directory/'stop-generation'
                if name=='watchdog':
                    generation.unlink()
                else:
                    generation.chmod(0o775)
                (directory/name).chmod(0o775)
                expected=generation.read_bytes() if generation.exists() else None
                before=len(self.remote.calls)
                result=self.installer.install(self.inventory,'original-secret')
                self.assertIsNone(self.store.pending(self.profile))
                self.assertTrue(result['activation_cancelled'])
                self.assertFalse(result['launch_requested'])
                self.assertEqual((directory/name).read_bytes(),b'explicit-stop')
                self.assertEqual((directory/name).stat().st_mode & 0o7777, 0o775)
                self.assertEqual(generation.read_bytes() if generation.exists() else None,expected)
                self.assertFalse(any(row[0]=='luna' and row[1].endswith('/launch') and
                                     row[2]['id']==operations.HELPER for row in self.remote.calls[before:]))
                (directory/name).unlink()
        self.assertEqual((self.root/'requests').read_text().splitlines(),list(observer.APPS)*3)

    def test_new_stop_cancels_bound_setup_even_after_latch_disappears(self):
        self.installer.install(self.inventory,'original-secret')
        self.publish_stop();(Path(operations.HELPER_STATE)/'blocked').unlink()
        self.remote.cut=True
        with self.assertRaises(RuntimeError):self.installer.install(self.inventory,'original-secret')
        pending=self.store.pending(self.profile);saved=observer.capsule(self.installer,pending)
        captured = saved['plan']['setup_start']['generation']
        self.assertRegex(captured, r'^S[a-f0-9]{32}$')
        generation = Path(operations.HELPER_STATE)/'stop-generation'
        generation.chmod(0o775)
        self.publish_stop()
        self.assertNotEqual(generation.read_text(), captured)
        self.assertEqual(generation.stat().st_mode & 0o7777, 0o664)
        (generation.parent/'blocked').unlink()
        before=len(self.remote.calls)
        result=self.installer.continue_no_root(pending)
        self.assertTrue(result['activation_cancelled'])
        self.assertFalse(result['launch_requested'])
        self.assertIsNone(self.store.pending(self.profile))
        self.assertFalse(any(row[0]=='luna' and row[1].endswith('/launch') for row in self.remote.calls[before:]))
        self.assertEqual((self.root/'requests').read_text().splitlines(),list(observer.APPS)*2)

    def test_closed_setup_retry_does_not_repeat_launch_or_reinstall(self):
        self.installer.install(self.inventory,'original-secret')
        original=self.remote.run
        def cut(command,data=None,timeout=30):
            words=split_observer_command(command)
            if '-e' in words and observer.PROGRAM in words[words.index('-e')+1] and json.loads(words[-1])['command']=='retire':
                raise RuntimeError('lost retire acknowledgement')
            return original(command,data,timeout)
        self.remote.run=cut
        with self.assertRaises(RuntimeError):self.installer.install(self.inventory,'original-secret')
        self.remote.run=original;pending=self.store.pending(self.profile)
        requests=(self.root/'requests').read_bytes();before=len(self.remote.calls)
        self.installer.continue_no_root(pending)
        self.assertEqual((self.root/'requests').read_bytes(),requests)
        self.assertFalse(any(row[0]=='luna' and row[1].endswith('/launch') for row in self.remote.calls[before:]))
        self.assertIsNone(self.store.pending(self.profile))

    def test_lost_profile_setup_keeps_foreign_reservation_and_offers_verified_removal(self):
        from cytv.failure_help import for_error
        self.remote.cut=True
        with self.assertRaises(RuntimeError):self.installer.install(self.inventory,'original-secret')
        before={str(p.relative_to(self.root/'private')):p.read_bytes() for p in (self.root/'private').rglob('*') if p.is_file()}
        requests=(self.root/'requests').read_bytes()
        other=operations.Installer(self.remote,state.Store(self.root/'new-computer'),self.profile,
                                  self.installer.payload,self.installer.manifest,lambda *_:None)
        with self.assertRaises(RuntimeError) as caught:other.install(self.inventory,'new-pairing')
        guide=for_error(caught.exception,'install-packages',self.profile,other.store.pending(self.profile))
        self.assertEqual(guide['code'],'no-root-reservation')
        self.assertIsNone(other.store.pending(self.profile))
        self.assertEqual((self.root/'requests').read_bytes(),requests)
        self.assertEqual({str(p.relative_to(self.root/'private')):p.read_bytes() for p in (self.root/'private').rglob('*') if p.is_file()},before)

    def test_stop_during_release_is_reported_as_cancelled_activation(self):
        original=self.remote.run;stopped=False
        def run(command,data=None,timeout=30):
            nonlocal stopped
            result=original(command,data,timeout)
            words=split_observer_command(command)
            if not stopped and '-e' in words and observer.PROGRAM in words[words.index('-e')+1] and json.loads(words[-1])['command']=='release':
                stopped=True;self.publish_stop()
            return result
        self.remote.run=run
        result=self.installer.install(self.inventory,'original-secret')
        self.assertTrue(stopped)
        self.assertTrue(result['activation_cancelled'])
        self.assertTrue(result['launch_requested'])
        self.assertEqual(self.installer.outcome.values['startup'],'stopped-during-setup')
        self.assertIsNone(self.store.pending(self.profile))

    def test_invalidated_generation_during_release_never_reports_normal_completion(self):
        original=self.remote.run
        def run(command,data=None,timeout=30):
            result=original(command,data,timeout)
            words=split_observer_command(command)
            if '-e' in words and observer.PROGRAM in words[words.index('-e')+1] and json.loads(words[-1])['command']=='release':
                (Path(operations.HELPER_STATE)/'stop-generation').write_bytes(b'')
            return result
        self.remote.run=run
        with self.assertRaises(RuntimeError):self.installer.install(self.inventory,'original-secret')
        self.assertEqual(self.installer.outcome.values['packages'],'verified')
        self.assertEqual(self.installer.outcome.values['home_button'],'not-tested')
        self.assertIsNone(self.store.pending(self.profile))

    def test_invalid_setup_generation_stops_before_package_requests(self):
        self.installer.install(self.inventory,'original-secret')
        (Path(operations.HELPER_STATE)/'stop-generation').write_text('invalid')
        requests=(self.root/'requests').read_bytes()
        with self.assertRaises(RuntimeError):self.installer.install(self.inventory,'original-secret')
        self.assertEqual((self.root/'requests').read_bytes(),requests)
        self.assertIsNone(self.store.pending(self.profile))

    def test_reinstall_repairs_vendor_stop_generation_mode_before_setup_start(self):
        self.installer.install(self.inventory, 'original-secret')
        generation = Path(operations.HELPER_STATE)/'stop-generation'
        original = generation.read_text()
        generation.chmod(0o775)

        result = self.installer.install(self.inventory, 'original-secret')

        repaired = generation.read_text()
        self.assertRegex(repaired, r'^S[a-f0-9]{32}$')
        self.assertNotEqual(repaired, original)
        self.assertEqual(generation.stat().st_mode & 0o7777, 0o664)
        self.assertTrue(result['launch_requested'])
        self.assertFalse(result.get('activation_cancelled', False))
        self.assertIsNone(self.store.pending(self.profile))
        self.assertEqual((self.root/'requests').read_text().splitlines(), list(observer.APPS)*2)

    def test_update_repairs_vendor_key_mode_before_setup_start(self):
        self.installer.install(self.inventory,'original-secret')
        directory=Path(operations.HELPER_STATE);key=directory/'ssap-key.json'
        key.chmod(0o775);(directory/'apps.json').chmod(0o775)
        result=self.installer.install(self.inventory,'original-secret')
        self.assertEqual(key.stat().st_mode&0o777,0o640)
        self.assertTrue(result['launch_requested'])
        self.assertIsNone(self.store.pending(self.profile))

    def test_reinstall_after_vendor_mode_drift_across_helper_state(self):
        self.installer.install(self.inventory, 'original-secret')
        directory = Path(operations.HELPER_STATE)
        # The simulated vendor installs the packages but does not run Helper.
        # Populate ordinary runtime files that can be left by a previous run.
        runtime_records = {
            'bootstrap.log': 'BOOTSTRAP\n',
            'controller.lock': '',
            'controller.log': '{"event":"controller-start"}\n',
            'controller.log.previous': '{"event":"controller-stop"}\n',
            'controller.pid': '2147483647',
            'control.json': '{}',
            'home-control.json': '{"enabled":true}',
            'relay.lock': '',
        }
        for name, contents in runtime_records.items():
            (directory/name).write_text(contents)
        generation = directory/'stop-generation'
        original_generation = generation.read_bytes()
        key = directory/'ssap-key.json'
        original_key = key.read_bytes()
        for path in (directory, *directory.rglob('*')):
            path.chmod(0o775)

        result = self.installer.install(self.inventory, 'original-secret')

        self.assertTrue(result['launch_requested'])
        self.assertFalse(result.get('activation_cancelled', False))
        self.assertEqual(self.installer.outcome.values['packages'], 'verified')
        self.assertIsNone(self.store.pending(self.profile))
        self.assertEqual((self.root/'requests').read_text().splitlines(), list(observer.APPS)*2)
        self.assertEqual(directory.stat().st_mode & 0o7777, 0o770)
        self.assertEqual(generation.stat().st_mode & 0o7777, 0o664)
        self.assertNotEqual(generation.read_bytes(), original_generation)
        self.assertEqual(key.stat().st_mode & 0o7777, 0o640)
        self.assertEqual(key.read_bytes(), original_key)
        self.assertEqual((directory/'apps.json').stat().st_mode & 0o7777, 0o644)
        for name, contents in runtime_records.items():
            self.assertEqual((directory/name).read_text(), contents, name)

    def test_pending_update_reclaims_capsule_matched_helper_key_without_package_replay(self):
        self.installer.install(self.inventory,'original-secret')
        directory=Path(operations.HELPER_STATE);os.chown(directory,-1,os.getgid())
        key=directory/'ssap-key.json';os.chown(key,-1,os.getgid());key.chmod(0o640)
        inode=key.stat().st_ino
        # The UID double identifies this inode. Keep it allocated after rename
        # so Linux cannot recycle its number for unrelated observer evidence.
        retained_key=key.open('rb');self.addCleanup(retained_key.close)
        blocked=directory/'blocked'
        original=self.remote.run
        interrupted=True
        def run(command,data=None,timeout=30):
            nonlocal interrupted
            words=split_observer_command(command)
            if '-e' in words and '/usr/bin/node' in words:
                i=words.index('-e')+1
                if observer.STATE_CHECK in words[i] and interrupted:
                    interrupted=False
                    raise RuntimeError('original installer refused Helper-owned key')
                prefix="var fs=require('fs');['lstatSync','fstatSync'].forEach(function(name){var original=fs[name];fs[name]=function(){var s=original.apply(fs,arguments);if(s.ino===INO)s.uid=5509;return s;};});".replace('INO',str(inode))
                words[i]=prefix+words[i];command=' '.join(shlex.quote(x) for x in words)
            return original(command,data=data,timeout=timeout)
        self.remote.run=run
        with self.assertRaises(RuntimeError):self.installer.install(self.inventory,'original-secret')
        pending=self.store.pending(self.profile);saved=observer.capsule(self.installer,pending)
        self.publish_stop()
        before=(self.root/'requests').read_bytes()
        self.assertTrue(self.installer.continue_no_root(pending)['activation_cancelled'])
        self.assertEqual(blocked.read_bytes(),b'explicit-stop')
        self.assertNotEqual(key.stat().st_ino,inode)
        self.assertEqual(key.stat().st_mode&0o777,0o640)
        self.assertEqual(key.read_text(),json.dumps({'key':'original-secret'}))
        observed=observer.snapshot(self.installer,saved)
        self.assertEqual(observed['configuration']['files'],'complete')
        self.assertEqual(observed['configuration']['launch'],'complete')
        self.assertIsNone(self.store.pending(self.profile))
        self.assertEqual((self.root/'requests').read_bytes(),before)
        # Only a separately modeled explicit owner resume removes the latch.
        blocked.unlink()
        self.assertIsNone(self.store.pending(self.profile))
        self.assertEqual((self.root/'requests').read_bytes(),before)

    def test_closed_retry_requires_original_configuration_readback(self):
        original=self.remote.run
        def cut(command,data=None,timeout=30):
            words=split_observer_command(command)
            if '-e' in words:
                if observer.PROGRAM in words[words.index('-e')+1] and json.loads(words[-1])['command']=='retire':
                    raise RuntimeError('lost retire acknowledgement')
            return original(command,data,timeout)
        self.remote.run=cut
        with self.assertRaises(RuntimeError):self.installer.install(self.inventory,'original-secret')
        self.remote.run=original
        pending=self.store.pending(self.profile)
        self.assertTrue((self.root/'private/operations'/pending['observer_operation']/'closed.json').exists())
        before=len(self.remote.calls)
        for name in ('ssap-key.json','apps.json'):
            with self.subTest(name=name):
                path=Path(operations.HELPER_STATE)/name;raw=path.read_bytes();path.write_bytes(b'changed')
                self.assertNotIn('continue-no-root',self.installer.observe_recovery()['assessment']['actions'])
                with self.assertRaises(RuntimeError):self.installer.continue_no_root(pending)
                self.assertEqual(self.store.pending(self.profile),pending)
                path.write_bytes(raw)
        self.assertFalse(any(call[0]=='luna' and not call[1].endswith('/listApps') for call in self.remote.calls[before:]))
        self.installer.continue_no_root(pending)
        self.assertIsNone(self.store.pending(self.profile))

    def test_state_substitution_at_actual_upload_cannot_disclose_key(self):
        original_run=self.remote.run;original_upload=self.remote.run_upload
        destination=self.root/'foreign-state';destination.mkdir();swapped=[]
        def substitute(command,data):
            if data and b'original-secret' in data and not data.startswith(b'!<arch>') and 'ssap-key.json' in command and not swapped:
                target=Path(operations.HELPER_STATE);target.rename(target.with_name('original-state'))
                target.symlink_to(destination,target_is_directory=True);swapped.append(True)
        def run(command,data=None,timeout=30):
            substitute(command,data);return original_run(command,data,timeout)
        def upload(command,data):
            substitute(command,data);return original_upload(command,data)
        self.remote.run=run;self.remote.run_upload=upload
        with self.assertRaises(RuntimeError):self.installer.install(self.inventory,'original-secret')
        self.assertEqual(swapped,[True])
        self.assertEqual(list(destination.iterdir()),[])
        self.assertIsNotNone(self.store.pending(self.profile))

    def test_delayed_archive_upload_never_replaces_claimed_payload(self):
        original_run=self.remote.run;original_upload=self.remote.run_upload
        def interrupt(command,data=None,timeout=30):
            if data and data.startswith(b'!<arch>'):raise RuntimeError('interrupted before staging')
            return original_run(command,data,timeout)
        def interrupt_upload(command,data):raise RuntimeError('interrupted before staging')
        self.remote.run=interrupt;self.remote.run_upload=interrupt_upload
        with self.assertRaises(RuntimeError):self.installer.install(self.inventory,'original-secret')
        self.remote.run=original_run;self.remote.run_upload=original_upload
        pending=self.store.pending(self.profile);saved=observer.capsule(self.installer,pending)
        destination=Path(json.loads(saved['plan']['slots'][0]['request'])['ipkUrl']);before=[]
        def competing_host(command,data):
            if data and data.startswith(b'!<arch>') and not before:
                before.append(None)
                observer.stage_remaining(self.installer,saved)
                observer.invoke(self.remote,saved['plan'],'start',0)
                import time
                deadline=time.monotonic()+5
                while observer.snapshot(self.installer,saved)['slots'][0]['terminal']=='none' and time.monotonic()<deadline:time.sleep(.02)
                self.assertTrue((self.root/'private/operations'/pending['observer_operation']/'claim-0.json').exists())
                before[0]=(destination.stat().st_ino,destination.read_bytes())
        def run(command,data=None,timeout=30):
            competing_host(command,data);return original_run(command,data,timeout)
        def upload(command,data):
            competing_host(command,data);return original_upload(command,data)
        self.remote.run=run;self.remote.run_upload=upload
        observer.stage_remaining(self.installer,saved)
        self.assertEqual((destination.stat().st_ino,destination.read_bytes()),before[0])
        self.assertEqual((self.root/'requests').read_text().splitlines(),[operations.HELPER])

    def test_host_loss_resumes_only_original_home_and_configuration_after_upgrade(self):
        self.remote.cut=True
        with self.assertRaises(RuntimeError): self.installer.install(self.inventory,'original-secret')
        pending=self.store.pending(self.profile)
        self.assertIsNotNone(pending, 'interruption must preserve an original operation')
        self.assertEqual(pending.get('recovery_protocol'),'no-root-original-stream-v1')
        self.assertEqual((self.root/'requests').read_text().splitlines(),[operations.HELPER])
        self.installer.manifest=dict(self.installer.manifest,helper_version='9.9.9',home_version='9.9.9')
        before=(self.store.device_dir(self.profile)/'operation.json').read_bytes()
        observed=self.installer.observe_recovery()
        self.assertIn('continue-no-root',observed['assessment']['actions'])
        self.assertEqual((self.store.device_dir(self.profile)/'operation.json').read_bytes(),before)
        self.installer.continue_no_root(pending)
        self.assertIsNone(self.store.pending(self.profile))
        self.assertEqual((self.root/'requests').read_text().splitlines(),list(observer.APPS))
        self.assertEqual(json.loads((Path(operations.HELPER_STATE)/'ssap-key.json').read_text()),{'key':'original-secret'})
        self.assertEqual(list((self.root/'public').iterdir()),[])
        self.assertTrue((self.root/'private/operations'/pending['observer_operation']/'claim-0.json').exists())
        self.assertFalse((self.store.device_dir(self.profile)/('capsule-'+pending['observer_operation']+'.json')).exists())
        self.assertFalse(any(call[0]=='luna' and call[1].endswith('appInstallService/status') for call in self.remote.calls))

    def test_recovery_finishes_configuration_with_unusable_staging(self):
        from cytv.desktop import DesktopConsole
        from cytv.recovery import recover

        original_run = self.remote.run

        def disconnect_after_packages(command, data=None, timeout=30):
            reply = original_run(command, data, timeout)
            words = split_observer_command(command)
            if '-e' in words and observer.PROGRAM in words[words.index('-e') + 1]:
                if json.loads(words[-1])['command'] == 'status':
                    if all(slot['terminal'] == 'success' for slot in json.loads(reply)['slots']):
                        raise RuntimeError('disconnected after both package installs')
            return reply

        with patch.object(self.remote, 'run', disconnect_after_packages):
            with self.assertRaises(RuntimeError):
                self.installer.install(self.inventory, 'original-secret')
        pending = self.store.pending(self.profile)
        self.assertEqual((self.root / 'requests').read_text().splitlines(), list(observer.APPS))
        staging = self.root / 'public' / ('cytv-' + pending['observer_operation'])
        staging.chmod(0o775)
        staged = {file.name: file.read_bytes() for file in staging.iterdir()}
        self.assertFalse((Path(operations.HELPER_STATE) / 'ssap-key.json').exists())
        installed = Path(self.base) / 'applications' / operations.HOME / 'appinfo.json'
        original = installed.read_bytes()
        installed.write_bytes(b'{}')
        self.assertNotIn('continue-no-root', self.installer.observe_recovery()['assessment']['actions'])
        with self.assertRaisesRegex(RuntimeError, 'changed-content'):
            self.installer.continue_no_root(pending)
        self.assertEqual(self.store.pending(self.profile), pending)
        self.assertFalse((Path(operations.HELPER_STATE) / 'ssap-key.json').exists())
        installed.write_bytes(original)
        observation = self.installer.observe_recovery()
        self.assertIn('continue-no-root', observation['assessment']['actions'])
        before = len(self.remote.calls)
        recover(self.installer, lambda _: 'y', DesktopConsole(lambda *_: None),
                initial_observation=observation)
        calls = self.remote.calls[before:]
        self.assertFalse(any(call[0] == 'observer' and call[1] in
                             ('prepare', 'artifacts', 'upload-artifact', 'start') for call in calls))
        self.assertEqual((self.root / 'requests').read_text().splitlines(), list(observer.APPS))
        self.assertEqual(json.loads((Path(operations.HELPER_STATE) / 'ssap-key.json').read_text()),
                         {'key': 'original-secret'})
        self.assertIsNone(self.store.pending(self.profile))
        self.assertEqual(staging.stat().st_mode & 0o777, 0o775)
        self.assertEqual({file.name: file.read_bytes() for file in staging.iterdir()}, staged)
        archives = (json.loads(file.read_text()) for file in
                    self.store.device_dir(self.profile).glob('recovery-*.json'))
        archive = next(entry for entry in archives if entry['action'] == 'finish-no-root-operation')
        self.assertEqual(archive['staging_cleanup']['observer_reason'], 'writable-directory')

    def test_new_removal_uses_null_artifact_and_resumes_only_home(self):
        self.installer.install(self.inventory,'original-secret')
        (self.root/'requests').write_text('')
        self.remote.cut=True
        with self.assertRaises(RuntimeError):self.installer.uninstall()
        pending=self.store.pending(self.profile)
        self.assertEqual(pending.get('recovery_protocol'),observer.PROTOCOL)
        saved=observer.capsule(self.installer,pending)
        self.assertTrue(all(slot['artifact_sha256'] is None for slot in saved['plan']['slots']))
        self.installer.continue_no_root(pending)
        self.assertEqual((self.root/'requests').read_text().splitlines(),list(observer.APPS))
        self.assertEqual(json.loads((self.root/'installed.json').read_text()),{})
        self.assertIsNone(self.store.pending(self.profile))

    def test_changed_capsule_or_current_files_never_submit_home(self):
        self.remote.cut=True
        with self.assertRaises(RuntimeError):self.installer.install(self.inventory,'original-secret')
        pending=self.store.pending(self.profile)
        source=self.root/'private/operations'/pending['observer_operation']/'observer.js'
        original=source.read_bytes();source.write_bytes(b'changed')
        with self.assertRaises(RuntimeError):self.installer.continue_no_root(pending)
        source.write_bytes(original)
        installed=Path(self.base)/'applications'/operations.HELPER/'appinfo.json'
        installed.write_text('{}')
        with self.assertRaises(RuntimeError):self.installer.continue_no_root(pending)
        capsule=self.store.device_dir(self.profile)/('capsule-'+pending['observer_operation']+'.json')
        capsule.write_text('{}')
        with self.assertRaises(RuntimeError):self.installer.continue_no_root(pending)
        self.assertEqual((self.root/'requests').read_text().splitlines(),[operations.HELPER])
        self.assertEqual(self.store.pending(self.profile),pending)

    def test_changed_trusted_reader_refuses_original_source_without_remote_effects(self):
        self.remote.cut=True
        with self.assertRaises(RuntimeError):self.installer.install(self.inventory,'original-secret')
        pending=self.store.pending(self.profile);before=len(self.remote.calls)
        with patch.object(observer,'PROGRAM',observer.PROGRAM+'\n// changed reader'):
            with self.assertRaises(RuntimeError):self.installer.continue_no_root(pending)
        self.assertEqual(len(self.remote.calls),before)
        self.assertEqual(self.store.pending(self.profile),pending)
        self.assertEqual((self.root/'requests').read_text().splitlines(),[operations.HELPER])

    def test_lost_volatile_observer_does_not_authorize_resubmission(self):
        self.remote.cut=True
        with self.assertRaises(RuntimeError):self.installer.install(self.inventory,'original-secret')
        pending=self.store.pending(self.profile)
        shutil.rmtree(self.root/'private')  # A boot may clear /tmp evidence.
        with self.assertRaises(RuntimeError):self.installer.continue_no_root(pending)
        self.assertEqual(self.store.pending(self.profile),pending)
        self.assertEqual((self.root/'requests').read_text().splitlines(),[operations.HELPER])

    def test_failed_first_stop_publication_cannot_be_adopted_as_initialization(self):
        self.remote.cut=True
        with self.assertRaises(RuntimeError):self.installer.install(self.inventory,'original-secret')
        pending=self.store.pending(self.profile)
        marker=Path(operations.HELPER_STATE)/'blocked';marker.write_bytes(b'new-stop')
        self.assertFalse((marker.parent/'stop-generation').exists())
        result=self.installer.continue_no_root(pending)
        self.assertTrue(result['activation_cancelled'])
        self.assertFalse(result['launch_requested'])
        self.assertEqual(marker.read_bytes(),b'new-stop')

    def test_new_stop_prevents_recovery_launch(self):
        self.remote.cut=True
        with self.assertRaises(RuntimeError):self.installer.install(self.inventory,'original-secret')
        pending=self.store.pending(self.profile)
        self.publish_stop()
        result=self.installer.continue_no_root(pending)
        self.assertTrue(result['activation_cancelled'])
        self.assertEqual((Path(operations.HELPER_STATE)/'blocked').read_bytes(),b'explicit-stop')
        self.assertFalse(any(row[0]=='luna' and row[1].endswith('/launch') for row in self.remote.calls))
        self.assertIsNone(self.store.pending(self.profile))

    def test_foreign_reservation_blocks_removal_restore_before_any_effect(self):
        self.remote.cut=True
        with self.assertRaises(RuntimeError):self.installer.install(self.inventory,'original-secret')
        other=operations.Installer(self.remote,state.Store(self.root/'second-computer'),self.profile,
                                   self.installer.payload,self.installer.manifest,lambda *_:None)
        with self.assertRaises(RuntimeError):other.uninstall()
        pending=other.store.pending(self.profile)
        before=len(self.remote.calls)
        with self.assertRaises(RuntimeError):other.continue_no_root(pending)
        self.assertFalse(any(call[0] in ('upload','luna') for call in self.remote.calls[before:]),self.remote.calls[before:])

    def test_original_capsule_completes_interrupted_staging_before_any_request(self):
        run=self.remote.run
        def interrupted(command,data=None,timeout=30):
            if data and data.startswith(b'!<arch>'):raise RuntimeError('upload interrupted')
            return run(command,data,timeout)
        self.remote.run=interrupted
        with self.assertRaises(RuntimeError):self.installer.install(self.inventory,'original-secret')
        pending=self.store.pending(self.profile)
        self.assertFalse((self.root/'requests').exists())
        self.remote.run=run
        saved=observer.capsule(self.installer,pending)
        observer.stage_remaining(self.installer,saved)
        self.installer.continue_no_root(pending)
        self.assertEqual((self.root/'requests').read_text().splitlines(),list(observer.APPS))
        self.assertIsNone(self.store.pending(self.profile))

    def test_recovery_requires_explicit_confirmation_and_status_has_no_writes(self):
        from cytv.recovery import recover
        from cytv.desktop import DesktopConsole
        self.remote.cut=True
        with self.assertRaises(RuntimeError):self.installer.install(self.inventory,'original-secret')
        def evidence():return {str(path):path.read_bytes() for root in (self.root/'private',self.store.root) for path in root.rglob('*') if path.is_file()}
        before=evidence();result=self.installer.observe_recovery()
        events=[];console=DesktopConsole(lambda kind,value:events.append((kind,value)))
        recover(self.installer,lambda _: '',console,initial_observation=result)
        self.assertEqual(evidence(),before)
        self.assertEqual((self.root/'requests').read_text().splitlines(),[operations.HELPER])
        recover(self.installer,lambda _: 'y',console,initial_observation=result)
        self.assertIsNone(self.store.pending(self.profile))
        self.assertEqual((self.root/'requests').read_text().splitlines(),list(observer.APPS))

    def test_native_entry_preserves_stop_arriving_after_host_guard(self):
        original=self.remote.luna
        def luna(uri,payload,**kwargs):
            if uri.endswith('/launch') and payload.get('id')==operations.HELPER:
                self.publish_stop()
                source=Path(__file__).resolve().parents[2]/'native/app'
                script=r"""
var fs=require('fs'),vm=require('vm'),path=require('path'),source=process.argv[1],local=process.argv[2],params=JSON.parse(process.argv[3]),captured;
vm.runInNewContext(fs.readFileSync(source+'/helper-entry.js','utf8'),{require:function(name){if(name!=='child_process')throw Error('unexpected');return {spawn:function(binary,args){captured=JSON.parse(args[0]);return {on:function(){},unref:function(){}};}};},process:{argv:['node','entry',JSON.stringify(params)],exit:function(){throw Error('unexpected exit');}}});
if(!captured||captured.nativeHomeSetup!==params.nativeHomeSetup)throw Error('lost setup generation');
var native=fs.readFileSync(source+'/native.js','utf8').replace('/media/developer/apps/usr/palm/applications/com.local.nativehome',path.dirname(local)),exited=false;
try{vm.runInNewContext(native,{require:function(name){
 if(name==='fs')return fs;if(name==='child_process')return {};
 if(name==='./runtime-policy'||name==='./state-permissions')return require(source+'/'+name.slice(2));
 throw Error('unexpected dependency after stop '+name);
},process:{argv:['node','native',JSON.stringify(captured)],exit:function(code){if(code!==0)throw Error('failed');exited=true;throw 'STOP';}},Buffer:Buffer});}catch(e){if(e!=='STOP')throw e;}
if(!exited||fs.readFileSync(local+'/blocked','utf8')!=='explicit-stop')throw Error('stop lost');
"""
                result=subprocess.run([shutil.which('node'),'-e',script,str(source),operations.HELPER_STATE,json.dumps(payload['params'])],capture_output=True,timeout=5)
                self.assertEqual(result.returncode,0,result.stderr.decode())
            return original(uri,payload,**kwargs)
        self.remote.luna=luna
        self.assertTrue(self.installer.install(self.inventory,'original-secret')['activation_cancelled'])
        self.assertEqual((Path(operations.HELPER_STATE)/'blocked').read_bytes(),b'explicit-stop')

    def test_copied_capsule_cannot_duplicate_delayed_configuration(self):
        import threading
        self.remote.cut=True
        with self.assertRaises(RuntimeError):self.installer.install(self.inventory,'original-secret')
        pending=self.store.pending(self.profile)
        other_root=self.root/'other-host';shutil.copytree(self.store.root,other_root)
        other=operations.Installer(self.remote,state.Store(other_root),self.profile,self.installer.payload,self.installer.manifest,lambda *_:None)
        entered=threading.Event();release=threading.Event();effects=[];failures=[]
        luna=self.remote.luna
        def delayed(uri,payload,**kwargs):
            if uri.endswith('/addDevice'):
                effects.append('eim')
                if len(effects)>1:raise RuntimeError('duplicate EIM submission')
                entered.set()
                if not release.wait(10):raise RuntimeError('test barrier timeout')
            return luna(uri,payload,**kwargs)
        self.remote.luna=delayed
        def first():
            try:self.installer.continue_no_root(pending)
            except Exception as error:failures.append(error)
        thread=threading.Thread(target=first);thread.start()
        try:
            self.assertTrue(entered.wait(8))
            with self.assertRaises(RuntimeError):other.continue_no_root(other.store.pending(self.profile))
            self.assertEqual(effects,['eim'])
        finally:release.set();thread.join(10)
        self.assertFalse(thread.is_alive());self.assertEqual(failures,[])

    def test_configuration_symlink_cannot_receive_private_key(self):
        self.remote.cut=True
        with self.assertRaises(RuntimeError):self.installer.install(self.inventory,'original-secret')
        destination=self.root/'foreign-state';destination.mkdir()
        Path(operations.HELPER_STATE).rmdir()
        Path(operations.HELPER_STATE).symlink_to(destination,target_is_directory=True)
        pending=self.store.pending(self.profile)
        with self.assertRaises(RuntimeError):self.installer.continue_no_root(pending)
        self.assertEqual(list(destination.iterdir()),[])

    def test_terminal_removal_can_finish_only_empty_owned_package_metadata(self):
        self.installer.install(self.inventory,'original-secret')
        sender=self.remote.sender.read_text().replace("apps.pop(app,None); terminal='removed'",
            "apps.pop(app,None); terminal='removed'\n (root/'apps/usr/palm/packages'/app).mkdir(parents=True,exist_ok=True)")
        self.remote.sender.write_text(sender);self.remote.cut=True
        with self.assertRaises(RuntimeError):self.installer.uninstall()
        pending=self.store.pending(self.profile)
        status=self.installer.observe_recovery()
        self.assertIn('continue-no-root',status['assessment']['actions'])
        self.installer.continue_no_root(pending)
        self.assertIsNone(self.store.pending(self.profile))
