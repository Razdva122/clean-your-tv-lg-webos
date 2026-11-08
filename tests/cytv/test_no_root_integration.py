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
from tests.cytv.test_operations import Remote
from tests.cytv import test_operations as operations_fixture


class ProcessRemote(Remote):
    def __init__(self, root):
        super().__init__()
        self.root_path=root
        self.cut=False
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
 if app=='com.local.nativehome':(root/'apps/usr/palm/applications'/app/'state').mkdir(exist_ok=True)
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
        words=shlex.split(command)
        if '-e' in words and '/usr/bin/node' in words:
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
        if uri.endswith('/dev/listApps'):
            source=self.root_path/'installed.json'
            self.installed=[{'id':app,'version':version} for app,version in json.loads(source.read_text()).items()] if source.exists() else []
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

    def test_zero_tmp_budget_still_stops_before_private_storage_selection(self):
        # A writable private evidence root does not establish vendor scratch
        # capacity. Preserve the earlier per-filesystem admission boundary.
        jail=self.root/'jail';jail.mkdir(mode=0o755)
        private=jail/'.cytv-installer';private.mkdir(mode=0o700)
        original=self.remote.run
        def run(command,**kwargs):
            if command=='LC_ALL=C df -Pk /tmp':
                return 'Filesystem 1024-blocks Used Available Capacity Mounted on\n/dev/tmp 1024 1024 0 100% /tmp'
            if command=='LC_ALL=C df -Pk /media/developer':
                return 'Filesystem 1024-blocks Used Available Capacity Mounted on\n/dev/apps 10000000 0 10000000 0% /media/developer'
            return original(command,**kwargs)
        self.remote.run=run
        with patch.object(observer,'JAIL_ROOT',str(private)):
            with self.assertRaises(RuntimeError) as caught:self.installer.install(self.inventory,'original-secret')
        self.assertEqual(caught.exception.reason_code,'tv-storage-full')
        self.assertIn('(/tmp)',str(caught.exception))
        self.assertIsNone(self.store.pending(self.profile))
        self.assertFalse(any(call[:2]==('observer','storage-select') for call in self.remote.calls))
        self.assertFalse((self.root/'requests').exists())
        self.assertEqual(list(private.iterdir()),[])

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

    def test_update_repairs_vendor_key_mode_without_replaying_packages_or_clearing_stop(self):
        self.installer.install(self.inventory,'original-secret')
        directory=Path(operations.HELPER_STATE)
        key=directory/'ssap-key.json';key.chmod(0o775)
        (directory/'apps.json').chmod(0o775)
        blocked=directory/'blocked';blocked.write_bytes(b'retained-emergency-stop')
        # Configuration may proceed, but the existing emergency stop must still
        # block automatic launch before its claim is consumed.
        with self.assertRaises(RuntimeError):self.installer.install(self.inventory,'original-secret')
        self.assertEqual(key.stat().st_mode&0o777,0o640)
        self.assertEqual(blocked.read_bytes(),b'retained-emergency-stop')
        pending=self.store.pending(self.profile)
        saved=observer.capsule(self.installer,pending)
        observed=observer.snapshot(self.installer,saved)
        self.assertEqual(observed['configuration']['files'],'complete')
        self.assertEqual(observed['configuration']['launch'],'prepared')
        self.assertEqual((self.root/'requests').read_text().splitlines(),list(observer.APPS)*2)
        # Model a later explicit user review of the stop latch, then continue
        # the same transaction without submitting either package again.
        blocked.unlink()
        self.installer.continue_no_root(pending)
        self.assertIsNone(self.store.pending(self.profile))
        self.assertEqual((self.root/'requests').read_text().splitlines(),list(observer.APPS)*2)

    def test_closed_retry_requires_original_configuration_readback(self):
        original=self.remote.run
        def cut(command,data=None,timeout=30):
            if '-e' in shlex.split(command):
                words=shlex.split(command)
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

    def test_emergency_marker_prevents_recovery_launch(self):
        self.remote.cut=True
        with self.assertRaises(RuntimeError):self.installer.install(self.inventory,'original-secret')
        pending=self.store.pending(self.profile)
        marker=Path(operations.HELPER_STATE)/'blocked';marker.parent.mkdir(parents=True,exist_ok=True);marker.write_text('stopped')
        with self.assertRaisesRegex(RuntimeError,'safety control'):self.installer.continue_no_root(pending)
        self.assertEqual(marker.read_text(),'stopped')
        self.assertFalse(any(call[0]=='luna' and call[1].endswith('/launch') for call in self.remote.calls))
        self.assertIsNotNone(self.store.pending(self.profile))

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
                marker=Path(operations.HELPER_STATE)/'blocked';marker.parent.mkdir(parents=True,exist_ok=True);marker.write_text('concurrent-stop')
                source=Path(__file__).resolve().parents[2]/'native/app'
                script=r'''
var fs=require('fs'),vm=require('vm'),path=require('path'),source=process.argv[1],local=process.argv[2],params=JSON.parse(process.argv[3]),captured;
var entry=fs.readFileSync(source+'/helper-entry.js','utf8');
vm.runInNewContext(entry,{require:function(name){if(name!=='child_process')throw Error('unexpected');return {spawn:function(binary,args){captured=JSON.parse(args[0]);return {on:function(){},unref:function(){}};}};},process:{argv:['node','entry',JSON.stringify(params)],exit:function(){throw Error('unexpected exit');}}});
if(!captured||captured.nativeHomeAuto!==true)throw Error('lost automatic safety flag');
var native=fs.readFileSync(source+'/native.js','utf8'),exited=false;
try{vm.runInNewContext(native,{require:function(name){
 if(name==='fs')return {existsSync:function(p){return fs.existsSync(p.replace('/media/developer/apps/usr/palm/applications/com.local.nativehome/state',local));}};
 if(name==='child_process')return {};
 if(name==='./runtime-policy')return require(source+'/runtime-policy');
 throw Error('unexpected dependency after stop '+name);
},process:{argv:['node','native',JSON.stringify(captured)],exit:function(code){if(code!==0)throw Error('failed');exited=true;throw 'STOP';}},Buffer:Buffer});}catch(e){if(e!=='STOP')throw e;}
if(!exited||fs.readFileSync(local+'/blocked','utf8')!=='concurrent-stop')throw Error('stop lost');
'''
                result=subprocess.run([shutil.which('node'),'-e',script,str(source),operations.HELPER_STATE,json.dumps(payload['params'])],capture_output=True,timeout=5)
                self.assertEqual(result.returncode,0,result.stderr.decode())
            return original(uri,payload,**kwargs)
        self.remote.luna=luna
        self.installer.install(self.inventory,'original-secret')
        self.assertEqual((Path(operations.HELPER_STATE)/'blocked').read_text(),'concurrent-stop')

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
