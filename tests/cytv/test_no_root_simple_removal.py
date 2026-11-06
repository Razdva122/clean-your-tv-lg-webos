"""Ordinary removal, interrupted setup, reconnect, and full-restart completion."""
import json
import os
import hashlib
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import time
import unittest

from cytv import operations
from cytv import package
from cytv.errors import TVRejected, UserError
from cytv.state import Store, target


class Remote:
    def __init__(self, root):
        self.root=root;self.apps=set();self.calls=[];self.cut=None;self.cut_install=False;self.reject_install=False;self.broken_service=False;self.reject=None;self.transform=lambda code:code
        self.boot='11111111-1111-1111-1111-111111111111'

    def run(self, command, data=None, timeout=30):
        from cytv import no_root_cleanup
        words=shlex.split(command)
        self.assert_program=words[words.index('-e')+1]
        code=self.assert_program.replace('/media/developer',str(self.root/'developer')).replace('/var/luna-service2-dev',str(self.root/'bus'))
        code=code.replace('/var/lib',str(self.root/'varlib')).replace('/var/webos-profile',str(self.root/'profiles'))
        code=code.replace('/proc/sys/kernel/random/boot_id',str(self.root/'boot'))
        code=code.replace("'/proc/'",json.dumps(str(self.root/'proc')+'/'))
        (self.root/'boot').write_text(self.boot)
        result=subprocess.run([os.environ.get('NODE_EXEC') or shutil.which('node'),'-e',self.transform(code),words[-1]],input=data,capture_output=True,timeout=timeout)
        if result.returncode:raise RuntimeError(result.stderr.decode())
        return result.stdout.decode()

    def luna(self, uri, payload, **kwargs):
        self.calls.append((uri,payload))
        if uri.endswith('/disable') and isinstance(self.broken_service,UserError):raise self.broken_service
        if uri.endswith('/disable') and self.broken_service:raise TVRejected('Service failed to start.',{'returnValue':False,'errorCode':-1},uri)
        if uri.endswith('/dev/listApps'):
            result=[]
            for app in sorted(self.apps):
                file=self.root/'developer/apps/usr/palm/applications'/app/'appinfo.json'
                result.append(json.loads(file.read_text()) if file.exists() else {'id':app})
            return {'returnValue':True,'apps':result}
        if uri.endswith('/getAllInputStatus'):return {'returnValue':True,'devices':[]}
        if uri.endswith('/dev/remove'):
            app=payload['id']
            if self.reject:
                reason=self.reject;self.reject=None;raise TVRejected('TV rejected removal.',reason,uri)
            self.apps.discard(app)
            roles=self.root/'bus/roles.d'
            if roles.exists():
                # Model package-manager privilege; SDK sweep itself cannot chmod.
                roles.chmod(0o755)
                for file in roles.glob(app+'.*'):file.unlink()
            if self.cut==app:self.cut=None;raise UserError('Connection to the TV was lost. Reconnect and choose Retry.')
            return {'returnValue':True,'id':app,'details':{'state':'removed'}}
        if uri.endswith('/dev/install'):
            if self.reject_install:
                self.reject_install=False;raise TVRejected('Package manager busy.',{'returnValue':False,'errorCode':-7},uri)
            source=Path(payload['ipkUrl'].replace('/media/developer',str(self.root/'developer')))
            for name,raw in package.data_files(source.read_bytes()).items():
                destination=self.root/'developer/apps'/name;destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(raw)
            self.apps.add(payload['id'])
            if self.cut_install:self.cut_install=False;raise UserError('Connection to the TV was interrupted.')
            return {'returnValue':True,'id':payload['id'],'details':{'state':'installed'}}
        if uri=='com.gathin.tvhome.renewal/disable':return {'returnValue':True,'state':{'enabled':False}}
        if uri=='com.local.nativehome.service/disable':return {'returnValue':True,'cancel':{'returnValue':True}}
        return {'returnValue':True}


@unittest.skipIf(os.name=='nt' or not shutil.which('node'),'POSIX TV filesystem model requires Node')
class SimpleRemoval(unittest.TestCase):
    def setUp(self):
        from cytv import no_root_cleanup
        self.cleanup=no_root_cleanup
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name).resolve()
        (self.root/'developer').mkdir();(self.root/'bus').mkdir();(self.root/'varlib').mkdir();(self.root/'profiles').mkdir()
        self.store=Store(self.root/'host');self.profile=target('tv.local','no-root');self.remote=Remote(self.root)
        self.installer=operations.Installer.__new__(operations.Installer)
        self.installer.store=self.store;self.installer.profile=self.profile;self.installer.remote=self.remote
        self.progress=[];self.installer.progress=self.progress.append

    def own_file(self, relative, value='private'):
        p=self.root/'developer'/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(value);return p

    def remove(self):return self.installer.uninstall(full_project=True)

    def reboot(self):self.remote.boot='22222222-2222-2222-2222-222222222222'

    def carrier_payload(self):
        app='com.local.nativehome';service=app+'.service';version='0.7.4'
        files={'usr/palm/applications/'+app+'/appinfo.json':json.dumps({'id':app,'version':version,'main':'detach'}).encode(),
               'usr/palm/packages/'+app+'/packageinfo.json':json.dumps({'id':app,'app':app,'version':version,'services':[service]}).encode(),
               'usr/palm/services/'+service+'/services.json':json.dumps({'id':service,'services':[{'name':service}]}).encode()}
        payload=self.root/'payload';payload.mkdir();(payload/'installer-support').mkdir()
        (payload/'helper.ipk').write_bytes(package.ipk(app,version,files,architecture='arm'))
        (payload/'installer-support/cleanup-noop').write_bytes(b'\x7fELFfixture of authenticated support')
        self.installer.payload=payload
        self.installer.manifest={'helper':'helper.ipk','files':{str(p.relative_to(payload)):hashlib.sha256(p.read_bytes()).hexdigest() for p in payload.rglob('*') if p.is_file()}}

    def test_partial_setup_is_removed_without_original_success_then_final_sweep_after_restart(self):
        self.store.begin(self.profile,'install',components={},failure={'reason':'unknown'},stage='install-packages')
        original=(self.store.device_dir(self.profile)/'operation.json').read_bytes()
        key=self.own_file('apps/usr/palm/applications/com.local.nativehome/state/ssap-key.json','changed private key')
        first=self.remove();self.assertFalse(first['verified_clean']);self.assertTrue(first['restart_required']);self.assertFalse(key.exists())
        pending=self.store.pending(self.profile)
        self.assertEqual((self.store.device_dir(self.profile)/pending['original_receipt']).read_bytes(),original)
        self.assertTrue(self.remove()['restart_required'])
        late=self.own_file('apps/usr/palm/applications/com.local.nativehome/state/late.json')
        self.reboot();self.assertTrue(self.remove()['verified_clean']);self.assertFalse(late.exists());self.assertIsNone(self.store.pending(self.profile))

    def test_disconnect_retry_rechecks_presence_and_continues_remaining_packages(self):
        self.remote.apps={'com.local.nativehome','com.gathin.tvhome'};self.remote.cut='com.local.nativehome'
        with self.assertRaises(UserError):self.remove()
        self.assertIsNotNone(self.store.pending(self.profile));self.assertTrue(self.remove()['restart_required'])
        requests=[payload['id'] for uri,payload in self.remote.calls if uri.endswith('/dev/remove')]
        self.assertEqual(requests.count('com.local.nativehome'),1);self.assertEqual(requests.count('com.gathin.tvhome'),1)
        self.reboot();self.assertTrue(self.remove()['removed'])

    def test_busy_is_reported_and_user_retry_can_remove_present_app(self):
        self.remote.apps={'com.local.nativehome'};self.remote.reject={'returnValue':False,'errorCode':-7}
        with self.assertRaises(TVRejected) as caught:self.remove()
        self.assertEqual(caught.exception.luna['error_code'],-7)
        self.assertTrue(self.remove()['restart_required']);self.reboot();self.assertTrue(self.remove()['verified_clean'])

    def test_registered_partial_app_without_service_skips_unavailable_disable(self):
        self.remote.apps={'com.local.nativehome','com.gathin.tvhome'}
        self.assertTrue(self.remove()['restart_required'])
        self.assertFalse(any(uri.endswith('/disable') for uri,_ in self.remote.calls))

    def test_present_functional_services_use_normal_disable(self):
        self.remote.apps={'com.local.nativehome','com.gathin.tvhome'}
        for service in ('com.local.nativehome.service','com.gathin.tvhome.renewal'):
            self.own_file('apps/usr/palm/services/'+service+'/service.js','published source')
        self.assertTrue(self.remove()['restart_required'])
        self.assertEqual(sum(uri.endswith('/disable') for uri,_ in self.remote.calls),2)

    def test_legacy_writable_own_service_directory_does_not_block_removal(self):
        service=self.own_file('apps/usr/palm/services/com.local.nativehome.service/service.js','source')
        service.parent.chmod(0o777)
        self.assertTrue(self.remove()['restart_required']);self.assertFalse(service.exists())
        self.reboot();self.assertTrue(self.remove()['verified_clean'])

    def test_broken_service_requires_restart_then_can_be_deleted_without_starting_it(self):
        for registered in (True,False):
            with self.subTest(registered=registered):
                if registered:self.remote.apps={'com.local.nativehome'}
                broken=self.own_file('apps/usr/palm/services/com.local.nativehome.service/service.js',"require('missing dependency');")
                self.remote.broken_service=True
                self.assertTrue(self.remove()['restart_required']);self.assertTrue(broken.exists())
                self.remote.boot='33333333-3333-3333-3333-333333333333' if registered else '44444444-4444-4444-4444-444444444444'
                self.assertTrue(self.remove()['verified_clean']);self.assertFalse(broken.exists())

    def test_optional_service_disconnect_is_reported_without_turning_into_restart_hint(self):
        self.remote.apps={'com.local.nativehome'}
        self.own_file('apps/usr/palm/services/com.local.nativehome.service/service.js','source')
        self.remote.broken_service=UserError('TV connection interrupted. Run cytv status before retrying.')
        with self.assertRaisesRegex(UserError,'connection interrupted'):self.remove()
        self.assertNotIn('cleanup_startup_unavailable',self.store.pending(self.profile))

    def test_foreign_app_and_symlink_target_are_preserved(self):
        foreign=self.root/'foreign';foreign.write_text('preserve')
        app=self.root/'developer/apps/usr/palm/applications/com.local.nativehome';app.mkdir(parents=True)
        (app/'link').symlink_to(foreign)
        unrelated=self.own_file('apps/usr/palm/applications/org.foreign.app/state/prefs','foreign')
        self.remove();self.reboot();self.remove()
        self.assertEqual(foreign.read_text(),'preserve');self.assertEqual(unrelated.read_text(),'foreign')

    def test_repeat_clean_is_noop_but_fresh_install_requires_new_restart(self):
        self.remove();self.reboot();self.assertTrue(self.remove()['verified_clean'])
        self.assertTrue(self.remove()['verified_clean'])
        self.store.begin(self.profile,'install');self.store.finish(self.profile)
        self.remote.apps={'com.gathin.tvhome'}
        self.assertTrue(self.remove()['restart_required'])

    def test_known_root_installation_requests_root_access(self):
        root=self.root/'varlib/clean-your-tv-root';root.mkdir();(root/'config.json').write_text('root configuration')
        with self.assertRaisesRegex(UserError,'Root access'):self.remove()
        self.assertTrue(root.exists());self.assertIsNotNone(self.store.pending(self.profile))

    def test_public_staging_requires_owned_package_identity_and_preserves_foreign(self):
        own=self.root/'developer/temp'/('cytv-'+'a'*32);own.mkdir(parents=True)
        foreign=self.root/'developer/temp'/('cytv-'+'b'*32);foreign.mkdir()
        (own/'helper.ipk').write_bytes(package.ipk('com.local.nativehome','0.7.4',{},architecture='arm'))
        (foreign/'helper.ipk').write_bytes(package.ipk('org.foreign.app','1.0.0',{},architecture='arm'))
        (foreign/'notes.txt').write_text('owner file')
        self.remove();self.assertFalse(own.exists());self.assertTrue((foreign/'helper.ipk').exists())
        self.reboot();self.assertTrue(self.remove()['verified_clean']);self.assertEqual((foreign/'notes.txt').read_text(),'owner file')

    def test_directory_replacement_is_not_traversed_or_deleted(self):
        own=self.root/'developer/apps/usr/palm/applications/com.local.nativehome';(own/'child').mkdir(parents=True)
        foreign=self.root/'foreign';foreign.mkdir();(foreign/'valuable').write_text('preserve')
        replacement='if(item.isDirectory()){if(child==="child"){fs.renameSync("child",'+json.dumps(str(self.root/'old-child'))+');fs.renameSync('+json.dumps(str(foreign))+',"child");}walk'
        self.remote.transform=lambda code:code.replace('if(item.isDirectory()){walk',replacement)
        with self.assertRaises(UserError):self.remove()
        self.assertEqual((own/'child/valuable').read_text(),'preserve')

    def test_stale_updater_transaction_requires_restart_but_not_old_success(self):
        record=self.own_file('apps/usr/palm/services/com.cleanyourtv.updater.service/state/transaction.json',json.dumps({'schema':1,'status':'installing'}))
        self.assertTrue(self.remove()['restart_required'])
        self.assertTrue(record.exists())
        self.reboot();self.assertTrue(self.remove()['verified_clean']);self.assertFalse(record.exists())
        receipt=json.loads((self.store.device_dir(self.profile)/'clean-removal.json').read_text())
        self.assertEqual(receipt['previous_update_status'],'installing')

    def test_old_resident_installer_moves_restart_before_package_removal(self):
        source=self.own_file('.cytv-installer/operations/'+'a'*32+'/changed-private-data.json','old unknown data')
        self.remote.apps={'com.local.nativehome'}
        self.assertTrue(self.remove()['restart_required'])
        self.assertTrue(source.exists())
        self.assertFalse(any(uri.endswith('/dev/remove') for uri,_ in self.remote.calls))
        self.reboot();self.assertTrue(self.remove()['verified_clean']);self.assertFalse(source.exists())

    @unittest.skipIf(getattr(os,'getuid',lambda:-1)()==0,'permission boundary requires an unprivileged SDK model')
    def test_actual_registration_permission_denial_requests_root_access(self):
        directory=self.root/'bus/roles.d';directory.mkdir();role=directory/'com.local.nativehome.service.json';role.write_text('{}')
        directory.chmod(0o555)
        try:
            with self.assertRaisesRegex(UserError,'Root access'):self.remove()
            self.assertTrue(role.exists())
        finally:directory.chmod(0o755)

    def test_known_partial_upload_is_removed_after_restart_without_valid_archive(self):
        identifier='a'*32
        self.own_file('.cytv-installer/operations/'+identifier+'/private.json','changed old data')
        partial=self.own_file('temp/cytv-'+identifier+'/helper.ipk','interrupted upload')
        foreign=self.own_file('temp/cytv-'+'b'*32+'/helper.ipk','unrelated unknown file')
        self.assertTrue(self.remove()['restart_required']);self.reboot()
        original=self.remote.transform
        self.remote.transform=lambda code:code.replace('function next(){if(!stages.length)',"if(input.action==='sweep')throw Error('connection interrupted after private sweep');function next(){if(!stages.length)")
        with self.assertRaises(RuntimeError):self.remove()
        self.remote.transform=original
        self.assertTrue(self.remove()['verified_clean']);self.assertFalse(partial.exists());self.assertTrue(foreign.exists())

    @unittest.skipUnless(getattr(os,'getuid',lambda:-1)()==501,'legacy501 shared-container ownership model')
    def test_legacy_shared_package_service_containers_do_not_block_own_cleanup(self):
        for kind,name in [('packages','com.local.nativehome'),('services','com.local.nativehome.service')]:
            self.own_file('apps/usr/palm/'+kind+'/'+name+'/own.json')
            foreign=self.own_file('apps/usr/palm/'+kind+'/org.foreign.app/keep.json','preserve')
            (self.root/'developer/apps/usr/palm'/kind).chmod(0o777)
        self.remove();self.reboot();self.assertTrue(self.remove()['verified_clean'])
        self.assertEqual(foreign.read_text(),'preserve')

    def test_shared_container_exception_does_not_cover_applications_parent(self):
        own=self.own_file('apps/usr/palm/applications/com.local.nativehome/keep.json')
        own.parent.parent.chmod(0o777)
        try:
            with self.assertRaises(UserError):self.remove()
            self.assertTrue(own.exists())
        finally:own.parent.parent.chmod(0o755)

    @unittest.skipIf(getattr(os,'getuid',lambda:-1)()==0,'tests unprivileged rejection')
    def test_root_package_action_rejects_unprivileged_call_and_arbitrary_id(self):
        own=self.own_file('apps/usr/palm/applications/com.cleanyourtv.root.preview/appinfo.json')
        for app in ('com.cleanyourtv.root.preview','org.foreign.app','../../foreign'):
            command='/usr/bin/node -e '+shlex.quote(self.cleanup.PRIVATE_CLEANUP_PROGRAM)+' '+shlex.quote(json.dumps({'action':'root-package','app':app}))
            with self.subTest(app=app),self.assertRaises(RuntimeError):self.remote.run(command)
        self.assertTrue(own.exists())

    @unittest.skipIf(getattr(os,'getuid',lambda:-1)()==0,'unprivileged SDK model')
    def test_missing_sam_protected_registration_uses_one_inert_carrier_then_remove(self):
        self.carrier_payload();directory=self.root/'bus/roles.d';directory.mkdir();role=directory/'com.local.nativehome.service.json';role.write_text('{}');directory.chmod(0o555)
        try:
            self.assertTrue(self.remove()['restart_required']);self.assertFalse(role.exists())
            installs=[p for uri,p in self.remote.calls if uri.endswith('/dev/install')]
            removals=[p for uri,p in self.remote.calls if uri.endswith('/dev/remove')]
            self.assertEqual(len(installs),1);self.assertEqual(len(removals),1);self.assertEqual(installs[0]['id'],removals[0]['id'])
            self.reboot();self.assertTrue(self.remove()['verified_clean'])
        finally:directory.chmod(0o755)

    @unittest.skipIf(getattr(os,'getuid',lambda:-1)()==0,'unprivileged SDK model')
    def test_disconnect_after_carrier_install_rechecks_registered_app_without_reinstall(self):
        self.carrier_payload();directory=self.root/'bus/roles.d';directory.mkdir();(directory/'com.local.nativehome.service.json').write_text('{}');directory.chmod(0o555)
        self.remote.cut_install=True
        try:
            with self.assertRaises(UserError):self.remove()
            self.assertTrue(self.remove()['restart_required'])
            self.assertEqual(sum(uri.endswith('/dev/install') for uri,_ in self.remote.calls),1)
            self.reboot();self.assertTrue(self.remove()['verified_clean'])
        finally:directory.chmod(0o755)

    @unittest.skipIf(getattr(os,'getuid',lambda:-1)()==0,'unprivileged SDK model')
    def test_rejected_carrier_has_no_automatic_loop_and_explicit_retry_can_try_again(self):
        self.carrier_payload();directory=self.root/'bus/roles.d';directory.mkdir();role=directory/'com.local.nativehome.service.json';role.write_text('{}');directory.chmod(0o555)
        self.remote.reject_install=True
        try:
            with self.assertRaises(TVRejected):self.remove()
            self.assertTrue(role.exists());self.assertEqual(sum(uri.endswith('/dev/install') for uri,_ in self.remote.calls),1)
            self.assertTrue(self.remove()['restart_required']);self.assertFalse(role.exists())
            self.assertEqual(sum(uri.endswith('/dev/install') for uri,_ in self.remote.calls),2)
        finally:directory.chmod(0o755)

    def test_controller_stop_finishes_before_its_files_are_removed(self):
        native=self.own_file('apps/usr/palm/applications/com.local.nativehome/native.js',
            "var fs=require('fs'),p=__dirname+'/state/';fs.writeFileSync(p+'controller.pid',String(process.pid));"
            "setInterval(function(){if(fs.existsSync(p+'control.json')){setTimeout(function(){fs.writeFileSync(process.argv[2],'keys released');fs.unlinkSync(p+'controller.pid');process.exit(0);},250);}},50);")
        state=native.parent/'state';state.mkdir();released=self.root/'released'
        child=subprocess.Popen([shutil.which('node'),str(native),str(released)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        def retire():
            if child.poll() is None:child.kill()
            child.wait(timeout=3)
        self.addCleanup(retire)
        deadline=time.monotonic()+5
        while not (state/'controller.pid').exists() and time.monotonic()<deadline:time.sleep(.01)
        self.assertTrue((state/'controller.pid').exists())
        proc=self.root/'proc'/str(child.pid);proc.mkdir(parents=True);(proc/'cmdline').write_text(str(native)+'\0')
        self.remote.transform=lambda code:code.replace("var base=", "if(input.action==='sweep'&&!fs.existsSync("+json.dumps(str(released))+"))throw Error('cleanup before keys released');var base=")
        self.assertTrue(self.remove()['restart_required'])
        child.wait(timeout=3);self.assertEqual(released.read_text(),'keys released');self.assertFalse(native.exists())

    def test_unresponsive_controller_requires_restart_before_file_deletion(self):
        pid=self.own_file('apps/usr/palm/applications/com.local.nativehome/state/controller.pid',str(os.getpid()))
        proc=self.root/'proc'/str(os.getpid());proc.mkdir(parents=True);(proc/'cmdline').write_text(str(pid.parent.parent/'native.js')+'\0')
        self.remote.transform=lambda code:code.replace('Date.now()+8000','Date.now()+100')
        self.assertTrue(self.remove()['restart_required']);self.assertTrue(pid.exists())
        pid.unlink();self.reboot();self.assertTrue(self.remove()['verified_clean'])

    def test_stale_pid_of_foreign_process_does_not_force_endless_restart(self):
        pid=self.own_file('apps/usr/palm/applications/com.local.nativehome/state/controller.pid',str(os.getpid()))
        proc=self.root/'proc'/str(os.getpid());proc.mkdir(parents=True);(proc/'cmdline').write_text('/usr/bin/foreign\0')
        self.assertTrue(self.remove()['restart_required']);self.assertFalse(pid.exists())
        self.reboot();self.assertTrue(self.remove()['verified_clean'])
