"""Ordinary removal, interrupted setup, reconnect, and full-restart completion."""
import json
import base64
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
        self.os_cleanup=False;self.cut_boot_create=False;self.command_limit=None;self.commands=[]
        self.boot='11111111-1111-1111-1111-111111111111'

    def run(self, command, data=None, timeout=30):
        from cytv import no_root_cleanup
        self.commands.append(command)
        if self.command_limit is not None and len(command.encode())>self.command_limit:
            raise AssertionError('SSH exec command exceeds the TV command limit')
        words=shlex.split(command)
        stdin=words==['/usr/bin/node']
        self.assert_program=data.decode() if stdin else words[words.index('-e')+1]
        if stdin:
            encoded,_=json.JSONDecoder().raw_decode(self.assert_program[len('process.argv.push('):])
            request=json.loads(encoded)
        else:request=json.loads(words[-1])
        code=self.assert_program.replace('/media/developer',str(self.root/'developer')).replace('/var/luna-service2-dev',str(self.root/'bus'))
        code=code.replace('/var/lib',str(self.root/'varlib')).replace('/var/webos-profile',str(self.root/'profiles'))
        code=code.replace('/proc/sys/kernel/random/boot_id',str(self.root/'boot'))
        code=code.replace("'/proc/'",json.dumps(str(self.root/'proc')+'/'))
        # Adapt only the fixed volatile root and its root UID for this host fixture.
        volatile=self.root/'volatile';volatile.mkdir(exist_ok=True);volatile.chmod(0o1777)
        code=code.replace('/tmp/.cytv-installer',str(volatile/'.cytv-installer'))
        code=code.replace("'/.cytv-installer'",json.dumps(str(self.root/'jail-private')))
        code=code.replace('function ancestry(p){',
            'var hostLstat=fs.lstatSync;fs.lstatSync=function(p){var s=hostLstat(p);if(p==='+json.dumps(str(volatile))+')s.uid=0;return s;};\nfunction ancestry(p){')
        code=code.replace("var bootRoot='/tmp';",'var bootRoot='+json.dumps(str(volatile))+';var bootLstat=fs.lstatSync;fs.lstatSync=function(p){var s=bootLstat(p);if(path.resolve(p)===bootRoot)s.uid=0;return s;};')
        (self.root/'boot').write_text(self.boot)
        node=os.environ.get('NODE_EXEC') or shutil.which('node')
        result=subprocess.run([node] if stdin else [node,'-e',self.transform(code),words[-1]],
                              input=self.transform(code).encode() if stdin else data,capture_output=True,timeout=timeout)
        if result.returncode:raise RuntimeError(result.stderr.decode())
        if request['action']=='boot-create' and self.cut_boot_create:
            self.cut_boot_create=False;raise UserError('Connection to the TV was interrupted.')
        return result.stdout.decode()

    def luna(self, uri, payload, **kwargs):
        self.calls.append((uri,payload))
        if uri.endswith('/disable') and isinstance(self.broken_service,UserError):raise self.broken_service
        if uri.endswith('/disable') and self.broken_service:raise TVRejected('Service failed to start.',{'returnValue':False,'errorCode':-1},uri)
        if uri.endswith('/dev/listApps'):
            result=[]
            for app in sorted(self.apps):
                file=self.root/'developer/apps/usr/palm/applications'/app/'appinfo.json'
                try:info=json.loads(file.read_text())
                except (FileNotFoundError,PermissionError):info={'id':app}
                result.append(info)
            return {'returnValue':True,'apps':result}
        if uri.endswith('/getAllInputStatus'):return {'returnValue':True,'devices':[]}
        if uri.endswith('/dev/remove'):
            app=payload['id']
            if self.reject:
                reason=self.reject;self.reject=None;raise TVRejected('TV rejected removal.',reason,uri)
            self.apps.discard(app)
            if self.os_cleanup:
                service='com.gathin.tvhome.renewal' if app=='com.gathin.tvhome' else app+'.service'
                for kind,name in [('applications',app),('packages',app),('services',service)]:
                    directory=self.root/'developer/apps/usr/palm'/kind/name
                    if directory.exists():
                        directory.chmod(0o755)
                        for parent,dirs,files in os.walk(directory):
                            for name in dirs:(Path(parent)/name).chmod(0o755)
                        shutil.rmtree(directory)
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
            if self.os_cleanup:
                app=payload['id'];service='com.gathin.tvhome.renewal' if app=='com.gathin.tvhome' else app+'.service'
                for kind,name in [('applications',app),('packages',app),('services',service)]:
                    directory=self.root/'developer/apps/usr/palm'/kind/name
                    if directory.exists():directory.chmod(0o755)
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

    def legacy_home(self, foreground='com.webos.app.livetv'):
        original=self.remote.luna
        state={'foreground':foreground}
        def luna(uri,payload,**kwargs):
            if uri.endswith('/launch') and payload['id']=='com.webos.app.home':
                self.remote.calls.append((uri,payload))
                raise TVRejected('App not found',{'returnValue':False,'errorCode':-101},uri)
            if uri.endswith('/getForegroundAppInfo'):
                self.remote.calls.append((uri,payload))
                return {'returnValue':True,'appId':state['foreground']}
            if uri.endswith('/launch') and payload['id']=='com.webos.app.livetv':
                state['foreground']='com.webos.app.livetv'
            return original(uri,payload,**kwargs)
        self.remote.luna=luna
        return state

    def test_legacy_home_bar_removes_installed_packages_and_completes_after_restart(self):
        self.remote.apps=set(self.cleanup.APPS[:2])
        self.own_file('apps/usr/palm/applications/com.gathin.tvhome/appinfo.json','{"id":"com.gathin.tvhome"}')
        foreground=self.legacy_home('com.gathin.tvhome')
        try:result=self.remove()
        except UserError as error:self.fail('Legacy Home must not block removal: '+str(error))
        self.assertTrue(result['restart_required'])
        self.assertFalse(self.remote.apps)
        self.assertEqual(foreground['foreground'],'com.webos.app.livetv')
        self.reboot()
        self.assertTrue(self.remove()['verified_clean'])
        self.assertIsNone(self.store.pending(self.profile))

    def test_manually_removed_packages_with_stock_hdmi_foreground_finish_without_stock_home_app(self):
        (self.root/'proc').mkdir()
        self.legacy_home('com.webos.app.hdmi2')
        self.assertTrue(self.remove()['verified_clean'])
        self.assertIsNone(self.store.pending(self.profile))
        self.assertFalse(any(uri.endswith('/dev/remove') for uri,_ in self.remote.calls))
        self.assertFalse(any(uri.endswith('/launch') and body['id']=='com.webos.app.livetv'
                             for uri,body in self.remote.calls))

    def test_stock_source_launch_waits_for_fresh_foreground_confirmation(self):
        self.remote.apps=set(self.cleanup.APPS[:2]);state=self.legacy_home('com.gathin.tvhome')
        original=self.remote.luna
        reads=[]
        def luna(uri,payload,**kwargs):
            if uri.endswith('/getForegroundAppInfo'):
                reads.append(True)
                if len(reads)<3:return {'returnValue':True,'appId':'com.gathin.tvhome'}
            return original(uri,payload,**kwargs)
        self.remote.luna=luna
        self.assertTrue(self.remove()['restart_required'])
        self.assertGreaterEqual(len(reads),3)
        self.assertFalse(self.remote.apps)

    def test_missing_home_does_not_accept_unrelated_foreground_or_unconfirmed_stock_launch(self):
        (self.root/'proc').mkdir()
        self.legacy_home('third.party.app')
        original=self.remote.luna
        def luna(uri,payload,**kwargs):
            if uri.endswith('/launch') and payload['id']=='com.webos.app.livetv':
                self.remote.calls.append((uri,payload))
                return {'returnValue':True}  # Acknowledged launch without foreground change.
            return original(uri,payload,**kwargs)
        self.remote.luna=luna
        with self.assertRaises(UserError):self.remove()
        self.assertIsNotNone(self.store.pending(self.profile))

    def test_missing_home_with_malformed_foreground_never_launches_another_app_or_removes_packages(self):
        original=self.remote.luna
        for reply in ({'returnValue':True}, {'returnValue':True,'appId':[]},
                      {'returnValue':False,'appId':'com.webos.app.livetv'}, None):
            with self.subTest(reply=reply):
                self.remote.apps=set(self.cleanup.APPS[:2]);self.remote.calls=[]
                def luna(uri,payload,**kwargs):
                    if uri.endswith('/launch'):
                        self.remote.calls.append((uri,payload))
                        raise TVRejected('App not found',{'returnValue':False,'errorCode':-101},uri)
                    if uri.endswith('/getForegroundAppInfo'):return reply
                    return original(uri,payload,**kwargs)
                self.remote.luna=luna
                with self.assertRaises(UserError):self.remove()
                self.assertEqual([body['id'] for uri,body in self.remote.calls if uri.endswith('/launch')],
                                 ['com.webos.app.home'])
                self.assertFalse(any(uri.endswith('/dev/remove') for uri,_ in self.remote.calls))

    def test_missing_home_does_not_hide_foreground_connection_loss(self):
        self.remote.apps=set(self.cleanup.APPS[:2]);self.legacy_home()
        original=self.remote.luna
        def luna(uri,payload,**kwargs):
            if uri.endswith('/getForegroundAppInfo'):
                raise UserError('Lost connection',reason_code='connection-interrupted')
            return original(uri,payload,**kwargs)
        self.remote.luna=luna
        with self.assertRaises(UserError) as caught:self.remove()
        self.assertEqual(caught.exception.reason_code,'connection-interrupted')
        self.assertTrue(self.remote.apps)
        self.assertFalse(any(uri.endswith('/dev/remove') for uri,_ in self.remote.calls))

    def test_other_stock_home_launch_errors_and_connection_loss_still_stop_before_package_remove(self):
        original=self.remote.luna
        for error in (TVRejected('Security',{'returnValue':False,'errorCode':-103},
                                 'com.webos.applicationManager/launch'),
                      UserError('Lost connection',reason_code='connection-interrupted')):
            with self.subTest(error=type(error).__name__):
                self.remote.apps=set(self.cleanup.APPS[:2])
                self.remote.calls=[]
                def luna(uri,payload,**kwargs):
                    if uri.endswith('/launch'):raise error
                    return original(uri,payload,**kwargs)
                self.remote.luna=luna
                with self.assertRaises(type(error)):self.remove()
                self.assertFalse(any(uri.endswith('/dev/remove') for uri,_ in self.remote.calls))
                self.assertTrue(self.remote.apps)

    def test_empty_tv_with_verified_idle_processes_needs_no_restart(self):
        (self.root/'proc').mkdir()
        result=self.remove()
        self.assertTrue(result['verified_clean'])
        self.assertIsNone(self.store.pending(self.profile))
        self.assertFalse(any(uri.endswith('/dev/remove') for uri,_ in self.remote.calls))

    def test_empty_files_with_live_or_unreadable_processes_still_need_restart(self):
        proc=self.root/'proc'/'123';proc.mkdir(parents=True)
        for argv in ('/usr/bin/node\0/media/developer/apps/usr/palm/services/com.gathin.tvhome.renewal/service.js\0',
                     '/usr/bin/node\0-e\0setInterval(function(){},1000)\0',
                     '/usr/bin/node\0--eval=setInterval(function(){},1000)\0',
                     '/usr/bin/node\0--eval\0setInterval(function(){},1000)\0',
                     '/usr/bin/node\0--max-old-space-size=64\0',
                     '/usr/bin/python3\0-cimport time; time.sleep(60)\0argument\0',
                     '/usr/bin/python3\0-icprint(1)\0argument\0', None):
            with self.subTest(argv=argv):
                if self.store.pending(self.profile):self.store.finish(self.profile)
                (self.store.device_dir(self.profile)/'clean-removal.json').unlink(missing_ok=True)
                if argv is not None:(proc/'cmdline').write_text(argv.replace('/media/developer',str(self.root/'developer')))
                elif (proc/'cmdline').exists():(proc/'cmdline').unlink()
                self.assertTrue(self.remove()['restart_required'])

    def test_foreign_absolute_script_does_not_force_restart_on_empty_tv(self):
        proc=self.root/'proc'/'123';proc.mkdir(parents=True)
        (proc/'cmdline').write_text('/usr/bin/node\0/usr/palm/services/org.foreign/service.js\0')
        self.assertTrue(self.remove()['verified_clean'])

    def test_relative_script_in_deleted_project_cwd_still_requires_restart(self):
        proc=self.root/'proc'/'123';proc.mkdir(parents=True)
        (proc/'cmdline').write_text('/usr/bin/node\0service.js\0')
        (proc/'cwd').symlink_to(self.root/'developer/apps/usr/palm/services/com.gathin.tvhome.renewal')
        self.assertTrue(self.remove()['restart_required'])

    def test_empty_files_with_unresolved_installation_do_not_skip_restart(self):
        (self.root/'proc').mkdir()
        self.store.begin(self.profile,'install',stage='submitted')
        self.assertTrue(self.remove()['restart_required'])

    def test_input_read_failure_uses_owned_delete_and_finishes_after_restart(self):
        self.remote.apps={'com.gathin.tvhome'}
        original=self.remote.luna
        def luna(uri,payload,**kwargs):
            if uri.endswith('/getAllInputStatus'):
                raise TVRejected('Unavailable',{'returnValue':False,'errorCode':-1},uri)
            return original(uri,payload,**kwargs)
        self.remote.luna=luna
        self.assertTrue(self.remove()['restart_required'])
        self.assertFalse(self.remote.apps)
        self.assertIn(('com.webos.service.eim/deleteDevice',{'appId':'com.gathin.tvhome'}),self.remote.calls)
        self.reboot()
        self.assertTrue(self.remove()['verified_clean'])

    def test_input_service_failure_defers_only_registration_and_never_claims_clean(self):
        self.remote.apps={'com.gathin.tvhome'}
        original=self.remote.luna
        def luna(uri,payload,**kwargs):
            if uri.startswith('com.webos.service.eim/'):
                raise TVRejected('Unavailable',{'returnValue':False,'errorCode':-1},uri)
            return original(uri,payload,**kwargs)
        self.remote.luna=luna
        self.assertTrue(self.remove()['restart_required'])
        self.assertFalse(self.remote.apps)
        self.reboot()
        with self.assertRaisesRegex(UserError,'input shortcuts'):
            self.remove()
        self.assertIsNotNone(self.store.pending(self.profile))
        self.remote.luna=original
        self.assertTrue(self.remove()['verified_clean'])

    def test_input_timeout_or_malformed_reply_does_not_block_package_cleanup(self):
        for error in (UserError('TV command ended without a confirmed result. Run cytv status.'),
                      UserError('TV operation timed out. Run cytv status before retrying.',reason_code='operation-timeout'),
                      ValueError('Invalid TV response')):
            with self.subTest(error=str(error)):
                if self.store.pending(self.profile):self.store.finish(self.profile)
                self.remote.apps={'com.gathin.tvhome'}
                original=self.remote.luna
                def luna(uri,payload,**kwargs):
                    if uri.startswith('com.webos.service.eim/'):raise error
                    return original(uri,payload,**kwargs)
                self.remote.luna=luna
                try:
                    self.assertTrue(self.remove()['restart_required'])
                    self.assertFalse(self.remote.apps)
                    self.assertTrue(self.store.pending(self.profile)['cleanup_inputs_pending'])
                finally:self.remote.luna=original

    def test_input_connection_loss_is_not_hidden_as_an_optional_service_error(self):
        self.remote.apps={'com.gathin.tvhome'}
        original=self.remote.luna
        def luna(uri,payload,**kwargs):
            if uri.endswith('/getAllInputStatus'):
                raise UserError('Lost connection',reason_code='connection-interrupted')
            return original(uri,payload,**kwargs)
        self.remote.luna=luna
        with self.assertRaises(UserError) as caught:self.remove()
        self.assertEqual(caught.exception.reason_code,'connection-interrupted')
        self.assertTrue(self.remote.apps)

    def reboot(self):
        self.remote.boot='22222222-2222-2222-2222-222222222222'
        for p in (self.root/'volatile').glob('cytv-removal-*.boot'):p.unlink()

    def boot_marker(self):
        goal=self.store.pending(self.profile)['removal_operation']
        return self.root/'volatile'/('cytv-removal-'+goal+'.boot')

    def test_unchanged_kernel_with_cleared_volatile_marker_finishes(self):
        first=self.remove();self.assertTrue(first['restart_required'])
        marker=self.boot_marker();self.assertTrue(marker.exists())
        proof=self.store.pending(self.profile)['cleanup_boot_proof']
        self.assertEqual(proof['kernel'],self.remote.boot)
        self.assertTrue(self.remove()['restart_required']);self.assertTrue(marker.exists())
        marker.unlink()  # Model the measured C3 volatile reset, kernel UUID reused.
        self.assertTrue(self.remove()['verified_clean'])
        (self.root/'proc').mkdir(exist_ok=True)  # Current idle proof for a new explicit goal.
        self.assertTrue(self.remove()['verified_clean']);self.assertFalse(marker.exists())

    def test_legacy_observer_prepare_failure_uses_confirmed_removal_and_keeps_capsule(self):
        from cytv import recovery, no_root_observer
        from cytv.desktop import DesktopConsole
        operation='a'*32
        self.store.begin(self.profile,'install',recovery_protocol=no_root_observer.PROTOCOL,
                         observer_operation=operation,expected={},versions={})
        digest=self.store.save_capsule(self.profile,operation,{'source':'legacy-source','plan':{}})
        self.store.checkpoint(self.profile,capsule_sha256=digest)
        directory=self.store.device_dir(self.profile)
        original=(directory/'operation.json').read_bytes()
        capsule=(directory/('capsule-'+operation+'.json')).read_bytes()
        self.installer.tv_info={}
        events=[];write=DesktopConsole(lambda kind,value:events.append((kind,value)))
        answers=iter(['y','n'])
        recovery.recover(self.installer,lambda _:next(answers),write)
        self.assertEqual((directory/'operation.json').read_bytes(),original)
        self.assertEqual(self.remote.commands,[])  # No retained source execution.
        answers=iter(['y','y'])
        recovery.recover(self.installer,lambda _:next(answers),write)
        pending=self.store.pending(self.profile)
        self.assertEqual(pending['recovery_protocol'],'clean-removal-v1')
        self.assertEqual((directory/pending['original_receipt']).read_bytes(),original)
        self.reboot()
        self.assertTrue(self.remove()['verified_clean'])
        self.assertIsNone(self.store.pending(self.profile))
        self.assertEqual((directory/('capsule-'+operation+'.json')).read_bytes(),capsule)
        self.assertFalse(any(uri.endswith(('/dev/install','/dev/remove','appInstallService/status')) for uri,_ in self.remote.calls))

    def test_new_private_observer_is_included_in_explicit_removal(self):
        private=self.root/'volatile/.cytv-installer/operations'/('a'*32)
        private.mkdir(parents=True);(private/'prepared.json').write_text('owned evidence')
        self.assertTrue(self.remove()['restart_required'])
        self.assertTrue(private.exists())  # A full boot fences the old worker first.
        self.reboot()
        self.assertTrue(self.remove()['verified_clean'])
        self.assertFalse(private.exists())

    def test_root_transport_project_staging_is_removed_after_restart(self):
        # Substitute only the unavailable host root UID branch; fixed project
        # directory, restart fence and real file sweep remain production code.
        original=self.remote.transform
        self.remote.transform=lambda code:original(code).replace('if(uid===0)installerRoots.push',
            'if(uid==='+str(os.getuid())+')installerRoots.push')
        private=self.root/'varlib/clean-your-tv-installer'
        private.mkdir(mode=0o755)
        artifact=private/('cytv-'+'a'*32)/'launcher.ipk';artifact.parent.mkdir();artifact.write_bytes(b'private project staging')
        operation=self.root/'volatile/.cytv-installer-root/operations'/('a'*32)
        operation.mkdir(parents=True)
        (operation/'prepared.json').write_text('retained original observer')
        self.assertTrue(self.remove()['restart_required'])
        self.assertTrue(artifact.exists())
        self.reboot()
        self.assertTrue(self.remove()['verified_clean'])
        self.assertFalse(private.exists())

    @unittest.skipIf(getattr(os,'getuid',lambda:0)()==0,'Requires an unprivileged Developer Mode user')
    def test_jail_private_observer_is_preserved_until_restart_then_removed(self):
        private=self.root/'jail-private';private.mkdir(mode=0o700)
        operation=private/'operations'/('a'*32);operation.mkdir(parents=True)
        evidence=operation/'prepared.json';evidence.write_text('original evidence')
        self.assertTrue(self.remove()['restart_required'])
        self.assertEqual(evidence.read_text(),'original evidence')
        self.reboot()
        self.assertTrue(self.remove()['verified_clean'])
        self.assertFalse(private.exists())

    @unittest.skipIf(getattr(os,'getuid',lambda:0)()==0,'Requires an unprivileged Developer Mode user')
    def test_unsafe_jail_private_leaf_is_never_deleted_or_repaired(self):
        private=self.root/'jail-private';private.mkdir(mode=0o755)
        evidence=private/'foreign';evidence.write_text('keep')
        with self.assertRaises((RuntimeError,UserError)):self.remove()
        self.assertEqual(evidence.read_text(),'keep')
        self.assertEqual(private.stat().st_mode&0o777,0o755)

    def test_changed_kernel_retires_valid_marker_only_after_boot_proof(self):
        self.remove();marker=self.boot_marker();proof=self.store.pending(self.profile)['cleanup_boot_proof']
        with self.assertRaises((RuntimeError,UserError)):
            self.cleanup._device(self.installer,'boot-retire',proof=proof)
        self.assertTrue(marker.exists())
        self.remote.boot='22222222-2222-2222-2222-222222222222'
        self.assertTrue(self.remove()['verified_clean']);self.assertFalse(marker.exists())

    def test_lost_marker_create_response_reuses_same_goal_before_effects(self):
        self.remote.cut_boot_create=True
        with self.assertRaisesRegex(UserError,'interrupted'):self.remove()
        marker=self.boot_marker();before=marker.stat()
        self.assertIsNone(self.store.pending(self.profile).get('cleanup_boot_proof'))
        self.assertFalse(any(uri.endswith('/disable') or uri.endswith('/dev/remove') for uri,_ in self.remote.calls))
        self.assertTrue(self.remove()['restart_required'])
        self.assertEqual((before.st_dev,before.st_ino),(marker.stat().st_dev,marker.stat().st_ino))
        marker.unlink();self.assertTrue(self.remove()['verified_clean'])

    def test_missing_legacy_baseline_seeds_marker_instead_of_proving_restart(self):
        self.store.request_clean_removal(self.profile)
        self.store.checkpoint(self.profile,cleanup_boot_id='00000000-0000-0000-0000-000000000000',stage='restart-required')
        self.assertTrue(self.remove()['restart_required']);self.assertTrue(self.boot_marker().exists())
        self.boot_marker().unlink();self.assertTrue(self.remove()['verified_clean'])

    def test_marker_tampering_never_proves_restart_or_removes_foreign_data(self):
        for kind in ('contents','mode','hardlink','symlink','replacement'):
            with self.subTest(kind=kind):
                self.store=Store(self.root/('host-'+kind));self.installer.store=self.store
                self.remove();marker=self.boot_marker();original=marker.read_bytes()
                foreign=self.root/('foreign-'+kind);foreign.write_text('preserve')
                if kind=='contents':marker.write_text('changed')
                elif kind=='mode':marker.chmod(0o644)
                elif kind=='hardlink':os.link(marker,self.root/'extra-link')
                elif kind=='symlink':marker.unlink();marker.symlink_to(foreign)
                else:
                    old=marker.with_suffix('.old');marker.rename(old);marker.write_bytes(original);marker.chmod(0o600)
                start=len(self.remote.calls)
                with self.assertRaises((RuntimeError,UserError)):self.remove()
                self.assertFalse(any(uri.endswith('/disable') or uri.endswith('/dev/remove') for uri,_ in self.remote.calls[start:]))
                self.assertEqual(foreign.read_text(),'preserve')


    def test_readonly_inventory_and_unseeded_probe_never_create_a_marker(self):
        self.store.request_clean_removal(self.profile)
        self.cleanup._device(self.installer,'inventory')
        marker=self.boot_marker();self.assertFalse(marker.exists())
        with self.assertRaises((RuntimeError,UserError)):
            self.cleanup._device(self.installer,'boot-probe')
        self.assertFalse(marker.exists())
        marker.write_text('foreign existing file');marker.chmod(0o600)
        with self.assertRaises((RuntimeError,UserError)):self.remove()
        self.assertEqual(marker.read_text(),'foreign existing file')

    def test_durable_boot_proof_precedes_control_and_package_effects(self):
        self.remote.apps={'com.local.nativehome'}
        key=self.own_file('apps/usr/palm/applications/com.local.nativehome/state/ssap-key.json')
        run=self.remote.run
        def checked(command,**kwargs):
            encoded,_=json.JSONDecoder().raw_decode(kwargs['data'].decode()[len('process.argv.push('):])
            action=json.loads(encoded)['action']
            if action in ('stop','sweep'):
                self.assertIn('cleanup_boot_proof',self.store.pending(self.profile))
            return run(command,**kwargs)
        self.remote.run=checked
        self.assertTrue(self.remove()['restart_required']);self.assertFalse(key.exists())

    def test_forged_or_mixed_kernel_proof_cannot_retire_same_boot_marker(self):
        self.remove();marker=self.boot_marker();proof=self.store.pending(self.profile)['cleanup_boot_proof']
        for value in (self.remote.boot,dict(proof,kernel='22222222-2222-2222-2222-222222222222'),dict(proof,goal='a'*32)):
            with self.subTest(proof=value):
                with self.assertRaises((RuntimeError,UserError)):
                    self.cleanup._device(self.installer,'boot-retire',proof=value)
                self.assertTrue(marker.exists())

    def test_all_cleanup_actions_use_small_ssh_command_and_real_node_stdin(self):
        self.remote.command_limit=8192
        self.store.request_clean_removal(self.profile)
        self.store.checkpoint(self.profile,cleanup_staging_ids=[format(n,'032x') for n in range(128)])
        self.cleanup._device(self.installer,'inventory')
        self.assertTrue(self.remove()['restart_required'])
        self.reboot();self.assertTrue(self.remove()['verified_clean'])
        self.assertTrue(self.remote.commands)
        self.assertEqual(set(self.remote.commands),{'/usr/bin/node'})

    def test_stdin_carrier_request_publishes_exact_binary_bytes_and_rejects_corruption(self):
        self.remote.command_limit=8192
        self.store.request_clean_removal(self.profile)
        identifier=self.store.pending(self.profile)['removal_operation']
        raw=bytes(range(256))*257
        request={'action':'stage-carrier','app':'com.local.nativehome','removal':identifier,
                 'size':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'carrier':base64.b64encode(raw).decode('ascii')}
        self.remote.run('/usr/bin/node',data=self.cleanup._program(request),timeout=90)
        file=self.root/'developer/temp'/('cytv-'+identifier)/'helper.ipk'
        self.assertEqual(file.read_bytes(),raw)
        self.remote.run('/usr/bin/node',data=self.cleanup._program(request),timeout=90)
        self.assertEqual(file.read_bytes(),raw,'exact same staged bytes can be read back on Retry')
        for bad in (dict(request,carrier=request['carrier'][:-4]),dict(request,sha256='0'*64)):
            with self.subTest(size=bad['size'],hash=bad['sha256']):
                with self.assertRaises(RuntimeError):self.remote.run('/usr/bin/node',data=self.cleanup._program(bad),timeout=90)
                self.assertEqual(file.read_bytes(),raw)
        self.assertEqual(set(self.remote.commands),{'/usr/bin/node'})

    def model_owners(self, owners):
        # Keep actual POSIX modes/inodes and Node filesystem operations; adapt
        # only ownership that an unprivileged host cannot reproduce with chown.
        prefix=('var reportedOwners='+json.dumps({str(p):ids for p,ids in owners.items()})+';'
                'var actualLstat=fs.lstatSync;fs.lstatSync=function(p){var s=actualLstat(p),owner=reportedOwners[path.resolve(p)];'
                'if(owner){s.uid=owner[0];s.gid=owner[1];}return s;};')
        self.remote.transform=lambda code:code.replace('var base=',prefix+'var base=')

    def test_reported_sdk_shared_ancestry_allows_inventory_stop_and_clean_retry(self):
        developer=self.root/'developer';base=developer/'apps/usr/palm'
        parents=[developer,developer/'apps',developer/'apps/usr',base,
                 base/'applications',base/'packages',base/'services',developer/'temp']
        owners={p:(0,0) for p in parents}
        for kind in ('packages','services'):owners[base/kind]=(501,20)
        for app,service in [('com.local.nativehome','com.local.nativehome.service'),('com.gathin.tvhome','com.gathin.tvhome.renewal')]:
            for directory in (base/'applications'/app,base/'services'/service):
                directory.mkdir(parents=True,exist_ok=True);directory.chmod(0o777);owners[directory]=(0,0)
                state=directory/'state';state.mkdir();state.chmod(0o777);owners[state]=(5999,5000)
                (state/'private.json').write_text('remove own fixture data')
            (base/'services'/service/'service.js').write_text('published fixture source')
        foreign=self.own_file('apps/usr/palm/services/org.foreign/keep.json','preserve')
        stage=developer/'temp'/('cytv-'+'a'*32);stage.mkdir(parents=True)
        (stage/'helper.ipk').write_bytes(package.ipk('com.local.nativehome','0.7.4',{},architecture='arm'))
        for directory in parents:directory.mkdir(parents=True,exist_ok=True);directory.chmod(0o777)
        self.model_owners(owners)
        inventory=self.cleanup._device(self.installer,'inventory')
        self.assertEqual(inventory['blocked'],[])
        self.assertEqual(set(inventory['startup_services']),{'com.local.nativehome.service','com.gathin.tvhome.renewal'})
        self.assertTrue(self.remove()['restart_required'])
        self.assertFalse((base/'applications/com.local.nativehome').exists())
        self.assertFalse(stage.exists())
        self.reboot();self.assertTrue(self.remove()['verified_clean'])
        self.assertEqual(foreign.read_text(),'preserve')

    def test_shared_sdk_services_symlink_does_not_admit_foreign_tree(self):
        foreign=self.root/'foreign';service=foreign/'com.local.nativehome.service'
        service.mkdir(parents=True);keep=service/'service.js';keep.write_text('preserve')
        base=self.root/'developer/apps/usr/palm';base.mkdir(parents=True)
        shared=base/'services';shared.symlink_to(foreign,target_is_directory=True)
        self.model_owners({shared:(0,0)})
        with self.assertRaises(UserError):self.remove()
        self.assertEqual(keep.read_text(),'preserve')
        self.assertFalse(any(uri.endswith('/dev/remove') for uri,_ in self.remote.calls))

    def test_shared_sdk_ancestry_exception_does_not_admit_writable_uuid_stage(self):
        identifier='a'*32
        own=self.own_file('temp/cytv-'+identifier+'/helper.ipk','partial upload')
        stage=own.parent;stage.chmod(0o777);stage.parent.chmod(0o777)
        self.model_owners({stage:(0,0),stage.parent:(0,0)})
        self.store.request_clean_removal(self.profile)
        self.store.checkpoint(self.profile,cleanup_staging_ids=[identifier])
        result=self.cleanup._device(self.installer,'sweep')
        self.assertIn({'scope':'installer-staging','reason':'unsafe-path'},result['blocked'])
        self.assertEqual(own.read_text(),'partial upload')

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
        (self.root/'proc').mkdir(exist_ok=True)
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

    def test_shared_container_exception_does_not_cover_foreign_applications_owner(self):
        own=self.own_file('apps/usr/palm/applications/com.local.nativehome/keep.json')
        own.parent.parent.chmod(0o777)
        self.model_owners({own.parent.parent:(4242,4242)})
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
        self.boot_marker().unlink()  # New volatile lifetime, same kernel UUID.
        self.assertTrue(self.remove()['restart_required']);self.assertTrue(pid.exists())
        self.assertTrue(self.boot_marker().exists(),'a still-running controller requires a new captured restart baseline')
        self.assertTrue(self.remove()['restart_required']);self.assertTrue(pid.exists())
        pid.unlink();self.reboot();self.assertTrue(self.remove()['verified_clean'])

    def test_lost_rearm_create_reply_keeps_retry_seedable_without_adopting_a_mismatch(self):
        pid=self.own_file('apps/usr/palm/applications/com.local.nativehome/state/controller.pid',str(os.getpid()))
        proc=self.root/'proc'/str(os.getpid());proc.mkdir(parents=True);(proc/'cmdline').write_text(str(pid.parent.parent/'native.js')+'\0')
        self.remote.transform=lambda code:code.replace('Date.now()+8000','Date.now()+100')
        self.remove();marker=self.boot_marker()
        with marker.open('rb') as held_old_inode:
            marker.unlink()  # Keep the fixture inode distinct from the next marker.
            self.remote.cut_boot_create=True
            with self.assertRaisesRegex(UserError,'interrupted'):self.remove()
            self.assertTrue(marker.exists())
            self.assertTrue(self.remove()['restart_required'])
            self.assertTrue(pid.exists())
        pid.unlink();marker.unlink();self.assertTrue(self.remove()['verified_clean'])

    def test_stale_pid_of_foreign_process_does_not_force_endless_restart(self):
        pid=self.own_file('apps/usr/palm/applications/com.local.nativehome/state/controller.pid',str(os.getpid()))
        proc=self.root/'proc'/str(os.getpid());proc.mkdir(parents=True);(proc/'cmdline').write_text('/usr/bin/foreign\0')
        self.assertTrue(self.remove()['restart_required']);self.assertFalse(pid.exists())
        self.reboot();self.assertTrue(self.remove()['verified_clean'])

    def test_legacy_writable_helper_state_is_stopped_and_removed(self):
        key=self.own_file('apps/usr/palm/applications/com.local.nativehome/state/ssap-key.json','private')
        key.parent.chmod(0o777)
        self.assertTrue(self.remove()['restart_required'])
        self.assertFalse(key.exists())
        self.reboot();self.assertTrue(self.remove()['verified_clean'])

    @unittest.skipIf(getattr(os,'getuid',lambda:-1)()==0,'unprivileged SDK permission model')
    def test_protected_no_root_namespaces_use_os_removal_or_one_carrier(self):
        self.carrier_payload();self.remote.os_cleanup=True
        for registered in (False,True):
            for kind,name,mode in [('applications','com.local.nativehome',0o555),
                                   ('applications','com.local.nativehome',0o000),
                                   ('applications','com.local.nativehome/state',0o555),
                                   ('services','com.local.nativehome.service',0o000),
                                   ('packages','com.local.nativehome',0o555)]:
                with self.subTest(registered=registered,kind=kind):
                    self.store.begin(self.profile,'install');self.store.finish(self.profile)
                    own=self.own_file('apps/usr/palm/'+kind+'/'+name+'/private.json','partial NoRoot data')
                    directory=own.parent;directory.chmod(mode)
                    self.addCleanup(lambda p=directory:p.chmod(0o755) if p.exists() else None)
                    foreign=self.own_file('apps/usr/palm/'+kind+'/org.foreign/keep.json','preserve')
                    self.remote.apps={'com.local.nativehome'} if registered else set()
                    start=len(self.remote.calls)
                    first=self.remove();self.assertTrue(first['restart_required']);self.assertFalse(first['verified_clean'])
                    self.remote.boot=('33333333-3333-3333-3333-333333333333' if self.remote.boot!=
                                      '33333333-3333-3333-3333-333333333333' else '44444444-4444-4444-4444-444444444444')
                    self.assertTrue(self.remove()['verified_clean'])
                    self.assertFalse(directory.exists());self.assertEqual(foreign.read_text(),'preserve')
                    calls=self.remote.calls[start:]
                    self.assertEqual(sum(uri.endswith('/dev/install') for uri,_ in calls),0 if registered else 1)
                    self.assertEqual(sum(uri.endswith('/dev/remove') for uri,_ in calls),1)

    def test_legacy_state_symlink_does_not_write_into_foreign_directory(self):
        foreign=self.root/'foreign';foreign.mkdir();(foreign/'keep').write_text('preserve')
        app=self.root/'developer/apps/usr/palm/applications/com.local.nativehome';app.mkdir(parents=True)
        (app/'state').symlink_to(foreign,target_is_directory=True)
        with self.assertRaises(UserError):self.remove()
        self.assertEqual(sorted(p.name for p in foreign.iterdir()),['keep'])
