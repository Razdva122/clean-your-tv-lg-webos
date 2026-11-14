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
from unittest.mock import patch

from cytv import operations
from cytv import package
from cytv.errors import TVRejected, UserError
from cytv.state import Store, target


class Remote:
    def __init__(self, root):
        self.root=root;self.apps=set();self.calls=[];self.cut=None;self.broken_service=False;self.reject=None;self.transform=lambda code:code
        self.os_cleanup=False;self.legacy_vendor=set();self.leave_executable=False;self.leave_registration=False;self.sam={};self.cut_boot_create=False;self.command_limit=None;self.commands=[]
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
        code=code.replace('/var/palm/ls2-dev',str(self.root/'legacy-bus'))
        code=code.replace('/var/lib',str(self.root/'varlib')).replace('/var/webos-profile',str(self.root/'profiles'))
        code=code.replace('/proc/sys/kernel/random/boot_id',str(self.root/'boot'))
        code=code.replace("'/proc/'",json.dumps(str(self.root/'proc')+'/'))
        if request.get('wait_for_idle'):
            code = code.replace('idleDeadline=Date.now()+8000', 'idleDeadline=Date.now()+500')
        # Adapt only the fixed volatile root and its root UID for this host fixture.
        volatile=self.root/'volatile';volatile.mkdir(exist_ok=True);volatile.chmod(getattr(self,'volatile_mode',0o1777))
        code=code.replace('/tmp/.cytv-installer',str(volatile/'.cytv-installer'))
        code=code.replace("'/.cytv-installer'",json.dumps(str(self.root/'jail-private')))
        code=code.replace("'/tmp'",json.dumps(str(volatile)))
        code=('var fixtureFs=require("fs"),fixturePath=require("path"),fixtureLstat=fixtureFs.lstatSync;'
              'fixtureFs.lstatSync=function(p){var s=fixtureLstat(p);if(fixturePath.resolve(p)==='
              +json.dumps(str(volatile))+')s.uid=0;return s;};\n')+code
        if request.get('connection') == 'root-ssh':
            code = 'process.getuid=function(){return 0;};\n' + code
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
        if uri == 'com.webos.appInstallService/status':return {'returnValue':True,'status':{'apps':[]}}
        if uri.endswith('/getAllInputStatus'):return {'returnValue':True,'devices':[]}
        if uri.endswith('/getAppInfo'):
            if self.sam is None:
                raise TVRejected('Denied', {'returnValue':False,'errorCode':-1},uri)
            return self.sam.get(payload['id'], {'returnValue':False})
        if uri.endswith('/dev/remove'):
            app=payload['id']
            if self.reject:
                reason=self.reject;self.reject=None;raise TVRejected('TV rejected removal.',reason,uri)
            self.apps.discard(app)
            service='com.gathin.tvhome.renewal' if app=='com.gathin.tvhome' else app+'.service'
            if app in self.legacy_vendor:
                self.legacy_vendor.remove(app)
                if self.sam is not None:
                    self.sam.pop(app, None)
                registration = self.root/'legacy-bus/services/pub'/(service+'.service')
                if registration.is_file() and not self.leave_registration:
                    registration.parent.chmod(0o755)  # The vendor has write access.
                    registration.unlink()
            if self.os_cleanup:
                for kind,name in [('applications',app),('packages',app),('services',service)]:
                    directory=self.root/'developer/apps/usr/palm'/kind/name
                    if directory.exists() and not (self.leave_executable and kind=='services'):
                        directory.chmod(0o755)
                        for parent,dirs,files in os.walk(directory):
                            for name in dirs:(Path(parent)/name).chmod(0o755)
                        shutil.rmtree(directory)
            roles=self.root/'bus/roles.d'
            if roles.exists():
                # Model package-manager privilege; SDK sweep itself cannot chmod.
                roles.chmod(0o755)
                for name in (app+'.json',app+'.app.json',service+'.json'):
                    (roles/name).unlink(missing_ok=True)
            if self.cut==app:self.cut=None;raise UserError('Connection to the TV was lost. Reconnect and choose Retry.')
            return {'returnValue':True,'id':app,'details':{'state':'removed'}}
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

    def test_inherited_removal_uses_paired_foreground_when_public_luna_refuses(self):
        (self.root / 'proc').mkdir()
        self.store.begin(self.profile, 'install', stage='pending')
        self.legacy_home()
        original = self.remote.luna

        def luna(uri, payload, **kwargs):
            if uri.endswith('/getForegroundAppInfo'):
                raise TVRejected('Rejected', {'returnValue': False, 'errorCode': -1}, uri)
            return original(uri, payload, **kwargs)

        self.remote.luna = luna
        key_file = self.store.device_dir(self.profile) / 'ssap.json'
        saved_key = '{"key":"saved-key"}\n'
        key_file.write_text(saved_key)
        requests = []

        class Socket:
            denied = True

            def send(self, raw):
                self.request = json.loads(raw)
                requests.append(self.request)

            def recv(self, timeout):
                request_id = self.request['id']
                if self.request['type'] == 'register':
                    return json.dumps({'id': request_id, 'type': 'registered',
                                       'payload': {'client-key': 'saved-key'}})
                payload = {'appId': 'com.webos.app.livetv'}
                if self.denied:
                    payload['returnValue'] = False
                return json.dumps({'id': request_id, 'type': 'response', 'payload': payload})

            def close(self):
                pass

        socket = Socket()
        with patch('websockets.sync.client.connect', return_value=socket) as connect:
            with self.assertRaises(UserError) as caught:
                self.remove()
            self.assertEqual(caught.exception.reason_code, 'controls-unverified')
            self.assertEqual(self.store.pending(self.profile)['stage'], 'requested')
            self.assertFalse(any(uri.endswith('/dev/remove') for uri, _ in self.remote.calls))
            socket.denied = False
            self.assertTrue(self.remove()['verified_clean'])

        self.assertIsNone(self.store.pending(self.profile))
        self.assertEqual(key_file.read_text(), saved_key)
        self.assertEqual([call.args[0] for call in connect.call_args_list], ['wss://tv.local:3001'] * 2)
        for register, read in zip(requests[::2], requests[1::2]):
            self.assertEqual(register['payload']['client-key'], 'saved-key')
            self.assertNotIn('pairingType', register['payload'])
            self.assertEqual(read['uri'], 'ssap://com.webos.applicationManager/getForegroundAppInfo')

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

    def test_installed_packages_finish_without_restart_after_verified_process_absence(self):
        (self.root/'proc').mkdir()
        self.remote.apps=set(self.cleanup.APPS)
        self.own_file('apps/usr/palm/applications/com.local.nativehome/state/ssap-key.json')
        result=self.remove()
        self.assertTrue(result['verified_clean'])
        self.assertFalse(result.get('restart_required',False))
        self.assertFalse(self.remote.apps)
        self.assertIsNone(self.store.pending(self.profile))
        self.assertFalse(list((self.root/'volatile').glob('cytv-removal-*.boot')))

    def test_broken_optional_startup_does_not_block_registered_package_removal(self):
        (self.root / 'proc').mkdir()
        self.remote.apps = {'com.local.nativehome'}
        self.remote.broken_service = True
        self.own_file('apps/usr/palm/services/com.local.nativehome.service/service.js')
        self.assertTrue(self.remove()['verified_clean'])
        self.assertFalse(self.remote.apps)
        self.assertFalse(list((self.root / 'volatile').glob('cytv-removal-*.boot')))

    def test_removal_waits_for_package_manager_and_continues_without_second_request(self):
        (self.root / 'proc').mkdir()
        self.store.begin(self.profile, 'install', stage='submitted')
        self.remote.apps = {'com.local.nativehome'}
        luna = self.remote.luna
        states = iter([['com.local.nativehome'], []])

        def status(uri, payload, **kwargs):
            if uri == 'com.webos.appInstallService/status':
                return {'returnValue': True, 'status': {'apps': next(states)}}
            return luna(uri, payload, **kwargs)

        self.remote.luna = status
        with patch.object(self.cleanup, 'sleep') as wait:
            self.assertTrue(self.remove()['verified_clean'])
        wait.assert_called_once()
        self.assertIsNone(self.store.pending(self.profile))

    def test_invalid_helper_stop_record_recovers_only_after_new_boot_and_idle(self):
        for name, contents in (('control.json', None), ('controller.pid', None), ('controller.pid', 'invalid')):
            with self.subTest(name=name, contents=contents):
                case = SimpleRemoval()
                self.addCleanup(case.doCleanups)
                case.setUp()
                proc = case.root / 'proc'
                proc.mkdir()
                app = 'com.local.nativehome'
                case.remote.apps = {app}
                state = case.own_file(f'apps/usr/palm/applications/{app}/state/blocked', 'stopped').parent
                invalid = state / name
                if contents is None:
                    invalid.mkdir()
                    (invalid / 'retained').write_text('fixture')
                else:
                    invalid.write_text(contents)
                service = case.own_file(f'apps/usr/palm/services/{app}.service/service.js')
                case.remote.transform = lambda code: code.replace('idleDeadline=Date.now()+8000', 'idleDeadline=Date.now()+50')
                remove_uri = 'com.webos.appInstallService/dev/remove'

                self.assertTrue(case.remove()['restart_required'])
                self.assertEqual(case.store.pending(case.profile)['cleanup_restart_triggers'],
                                 ['invalid-helper-stop-record'])
                case.boot_marker().unlink()
                self.assertTrue(case.remove()['restart_required'])
                self.assertTrue(invalid.exists())
                self.assertFalse(any(uri == remove_uri for uri, _ in case.remote.calls))

                case.reboot()
                case.remote.broken_service = True
                with self.assertRaises(UserError):
                    case.remove()
                self.assertTrue(invalid.exists())
                self.assertFalse(any(uri == remove_uri for uri, _ in case.remote.calls))

                case.remote.broken_service = False
                live = proc / '123'
                live.mkdir()
                (live / 'cmdline').write_bytes(app.encode() + bytes([0]))
                with self.assertRaises(UserError):
                    case.remove()
                self.assertTrue(invalid.exists())
                self.assertFalse(any(uri == remove_uri for uri, _ in case.remote.calls))

                shutil.rmtree(live)
                foreign = proc / '124'
                foreign.mkdir()
                (foreign / 'cmdline').write_bytes(bytes([0]).join(
                    (b'node', b'/usr/bin/run-js-service', b'com.webos.foreign.service')))

                denied = ("var read=fs.readFileSync;fs.readFileSync=function(file){"
                          "if(file===" + json.dumps(str(foreign / 'cmdline')) + "){"
                          "var error=Error('denied');error.code='EACCES';throw error;}"
                          "return read.apply(fs,arguments);};")
                fast_timeout = case.remote.transform
                case.remote.transform = lambda code: fast_timeout(code).replace("if(input.action==='idle'){",
                                                                                "if(input.action==='idle'){" + denied)
                with self.assertRaises(UserError):
                    case.remove()
                self.assertTrue(invalid.exists())
                self.assertFalse(any(uri == remove_uri for uri, _ in case.remote.calls))

                # The /disable reply can arrive before its short-lived service
                # process exits. Link restrictions for foreign processes still apply.
                transient = proc / '125'
                transient.mkdir()
                (transient / 'cmdline').write_bytes(str(service).encode())
                kernel = proc / '2'
                kernel.mkdir()
                (kernel / 'cmdline').touch()
                (kernel / 'stat').write_text('2 (kernel thread) S 0 0 0 0 -1 2097152')
                denied_links = json.dumps([str(foreign), str(kernel)])
                model = ("var link=fs.readlinkSync;fs.readlinkSync=function(file){"
                         "if(" + denied_links + ".indexOf(path.dirname(file))>=0){"
                         "var error=Error('denied');error.code='EACCES';throw error;}"
                         "return link.apply(fs,arguments);};"
                         "var read=fs.readFileSync, polls=0;fs.readFileSync=function(file){"
                         "if(file===" + json.dumps(str(transient / 'cmdline')) + "&&polls++)return '';"
                         "return read.apply(fs,arguments);};")
                case.remote.transform = lambda code: code.replace("if(input.action==='idle'){", "if(input.action==='idle'){" + model)
                disable_uri = app + '.service/disable'
                disable_count = sum(uri == disable_uri for uri, _ in case.remote.calls)
                self.assertTrue(case.remove()['verified_clean'])
                self.assertEqual(sum(uri == disable_uri for uri, _ in case.remote.calls), disable_count + 1)
                self.assertFalse(invalid.exists())
                calls = [uri for uri, _ in case.remote.calls]
                self.assertIn(disable_uri, calls[:calls.index(remove_uri)])

    def test_live_project_process_blocks_package_removal(self):
        proc=self.root/'proc'/'123';proc.mkdir(parents=True)
        (proc/'cmdline').write_text('/usr/bin/node\0'+str(self.root/'developer/apps/usr/palm/services/com.gathin.tvhome.renewal/service.js')+'\0')
        self.remote.apps={'com.gathin.tvhome'}
        with self.assertRaises(UserError) as error:
            self.remove()
        self.assertEqual(error.exception.reason_code, 'cleanup-check-failed')
        self.assertEqual(self.remote.apps, {'com.gathin.tvhome'})
        self.assertFalse(self.boot_marker().exists())

    def test_removal_waits_for_project_process_despite_denied_foreign_proc_links(self):
        proc = self.root / 'proc'
        foreign, project = proc / '123', proc / '124'
        foreign.mkdir(parents=True)
        project.mkdir()
        (foreign / 'cmdline').write_bytes(b'/usr/bin/sam\0')
        (project / 'cmdline').write_bytes(b'com.local.nativehome.service\0')
        self.remote.apps = {'com.local.nativehome'}
        self.own_file('apps/usr/palm/services/com.local.nativehome.service/service.js')
        model = (
            "var link=fs.readlinkSync, read=fs.readFileSync, polls=0;"
            "fs.readlinkSync=function(file){if(path.dirname(file)===" + json.dumps(str(foreign)) +
            "){var denied=Error();denied.code='EACCES';throw denied;}return link.apply(fs,arguments);};"
            "fs.readFileSync=function(file){if(file===" + json.dumps(str(project / 'cmdline')) +
            "&&polls++)return '';return read.apply(fs,arguments);};"
        )
        self.remote.transform = lambda code: code.replace("if(input.action==='idle'){",
                                                          "if(input.action==='idle'){" + model)
        self.assertTrue(self.remove()['verified_clean'])
        calls = [uri for uri, _ in self.remote.calls]
        self.assertEqual(calls.count('com.local.nativehome.service/disable'), 1)
        self.assertEqual(calls.count('com.webos.appInstallService/dev/remove'), 1)
        self.assertFalse(list((self.root / 'volatile').glob('cytv-removal-*.boot')))
        self.assertIsNone(self.store.pending(self.profile))

    def test_reconnect_reconciles_vendor_and_history_replies_under_one_goal(self):
        (self.root / 'proc').mkdir()
        app = 'com.local.nativehome'
        self.remote.apps.add(app)
        self.remote.os_cleanup = True
        journal = self.own_file('.cytv-installer/operations/' + 'a' * 32 + '/journal.json')
        self.remote.cut = app
        pending = self.store.request_clean_removal(self.profile)
        with self.assertRaises(UserError):
            self.remove()
        self.assertFalse(self.remote.apps)

        original = self.remote.run
        cuts = ['sweep', 'boot-release', 'history']
        def run(command, data=None, **options):
            result = original(command, data, **options)
            if data and cuts:
                value, _ = json.JSONDecoder().raw_decode(data.decode()[len('process.argv.push('):])
                if json.loads(value)['action'] == cuts[0]:
                    cuts.pop(0)
                    raise UserError('Connection interrupted', reason_code='connection-interrupted')
            return result

        proof = self.cleanup._device(self.installer, 'boot-create')['boot_proof']
        self.store.checkpoint(self.profile, cleanup_boot_proof=proof)
        self.remote.run = run
        for _ in range(3):
            self.installer.store = Store(self.store.root)
            with self.assertRaises(UserError):
                self.remove()
            self.assertEqual(self.store.pending(self.profile)['removal_operation'], pending['removal_operation'])
            self.store = self.installer.store
        self.assertTrue(self.remove()['verified_clean'])
        self.assertFalse(cuts)
        self.assertFalse(journal.exists())
        self.assertEqual([body['id'] for uri, body in self.remote.calls if uri.endswith('/dev/remove')], [app])
        self.assertIsNone(self.store.pending(self.profile))

    def test_denied_monitor_waits_for_real_lost_request_then_finishes(self):
        (self.root / 'proc').mkdir()
        app = 'com.local.nativehome'
        self.remote.apps.add(app)
        self.remote.os_cleanup = True
        self.remote.cut = app
        original = self.remote.luna
        monitor = 'denied'

        def luna(uri, payload, **kwargs):
            if uri.endswith('/status') and monitor == 'denied':
                raise TVRejected('Denied', {'returnValue': False, 'errorCode': -1}, uri)
            return original(uri, payload, **kwargs)

        self.remote.luna = luna
        pending = self.store.request_clean_removal(self.profile)
        with self.assertRaises(UserError):
            self.remove()
        self.assertTrue(self.remove()['restart_required'])
        proof = self.store.pending(self.profile)['cleanup_boot_proof']
        with self.assertRaises(UserError) as waiting:
            self.remove()
        self.assertEqual(waiting.exception.reason_code, 'removal-terminal-unknown')
        self.assertEqual(self.store.pending(self.profile)['cleanup_boot_proof'], proof)
        monitor = 'idle'
        self.assertTrue(self.remove()['verified_clean'])
        self.assertEqual([body['id'] for uri, body in self.remote.calls if uri.endswith('/dev/remove')], [app])
        completed = json.loads((self.store.device_dir(self.profile) / 'clean-removal.json').read_text())
        self.assertEqual(completed['removal_operation'], pending['removal_operation'])
        self.assertEqual(self.remote.boot, proof['kernel'])

    def test_lost_vendor_reply_with_absent_target_accepts_new_kernel_and_malformed_status(self):
        (self.root / 'proc').mkdir()
        app = 'com.local.nativehome'
        self.remote.apps.add(app)
        self.remote.os_cleanup = True
        self.remote.cut = app
        original = self.remote.luna

        def luna(uri, payload, **kwargs):
            if uri.endswith('/status'):
                return {'returnValue': True, 'status': {}}
            return original(uri, payload, **kwargs)

        self.remote.luna = luna
        pending = self.store.request_clean_removal(self.profile)
        with self.assertRaises(UserError):
            self.remove()
        self.assertFalse(self.remote.apps)
        self.assertTrue(self.remove()['restart_required'])
        with self.assertRaises(UserError):
            self.remove()
        self.reboot()
        self.assertTrue(self.remove()['verified_clean'])
        self.assertEqual([body['id'] for uri, body in self.remote.calls if uri.endswith('/dev/remove')], [app])
        completed = json.loads((self.store.device_dir(self.profile) / 'clean-removal.json').read_text())
        self.assertEqual(completed['removal_operation'], pending['removal_operation'])

    def test_malformed_negative_stream_keeps_submitted_until_observed_idle(self):
        from unittest.mock import Mock
        from cytv.transport import SSH

        (self.root / 'proc').mkdir()
        app = 'com.local.nativehome'
        self.remote.apps.add(app)
        original = self.remote.luna
        ssh = object.__new__(SSH)
        ssh.root = False
        ssh.channel = Mock()
        ssh.chunks = Mock(return_value=iter((
            b'{"returnValue":true,"details":{"state":"removing"}}',
            b'{"returnValue":true,"details":[]}',
        )))
        settled = False
        vendor_calls = []

        def luna(uri, payload, **kwargs):
            if uri.endswith('/status') and not settled:
                raise TVRejected('Denied', {'returnValue': False, 'errorCode': -1}, uri)
            if uri.endswith('/dev/remove'):
                vendor_calls.append(payload['id'])
                if len(vendor_calls) == 1:
                    return ssh.luna(uri, payload, **kwargs)
            return original(uri, payload, **kwargs)

        self.remote.luna = luna
        with self.assertRaises(TVRejected):
            self.remove()
        self.assertEqual(self.store.pending(self.profile)['removals'], {app: 'submitted'})
        self.assertTrue(self.remove()['restart_required'])
        self.assertEqual(vendor_calls, [app])
        settled = True
        self.assertTrue(self.remove()['verified_clean'])
        self.assertEqual(vendor_calls, [app, app])
        self.assertIsNone(self.store.pending(self.profile))

    def test_lost_same_boot_marker_release_never_proves_a_restart(self):
        (self.root/'proc').mkdir()
        self.remote.apps={'com.gathin.tvhome'}
        self.store.request_clean_removal(self.profile)
        proof = self.cleanup._device(self.installer, 'boot-create')['boot_proof']
        self.store.checkpoint(self.profile, cleanup_boot_proof=proof)
        run=self.remote.run
        lost=[]
        def interrupted(command,**kwargs):
            result=run(command,**kwargs)
            encoded,_=json.JSONDecoder().raw_decode(self.remote.assert_program[len('process.argv.push('):])
            if json.loads(encoded)['action']=='boot-release' and not lost:
                lost.append(True)
                proc=self.root/'proc/123';proc.mkdir()
                (proc/'cmdline').write_text('/usr/bin/node\0'+str(self.root/'developer/apps/usr/palm/services/com.gathin.tvhome.renewal/service.js')+'\0')
                raise UserError('Connection to the TV was interrupted.',reason_code='connection-interrupted')
            return result
        self.remote.run=interrupted
        with self.assertRaises(UserError):self.remove()
        self.assertTrue(lost)
        with self.assertRaisesRegex(UserError, 'process did not stop'):
            self.remove()
        self.assertIsNotNone(self.store.pending(self.profile))

    def test_lost_host_completion_after_verified_restart_does_not_request_second_restart(self):
        from unittest.mock import patch
        (self.root/'proc').mkdir()
        self.seed_pending_restart()
        self.reboot()
        with patch.object(self.store,'finish_clean_removal',side_effect=OSError('host interruption')):
            with self.assertRaises(OSError):self.remove()
        self.assertEqual(self.store.pending(self.profile)['stage'],'verified-clean')
        (self.root / 'proc').rmdir()
        self.assertTrue(self.remove()['verified_clean'])

    def test_saved_restart_proof_does_not_hide_a_reappeared_process(self):
        from unittest.mock import patch
        (self.root/'proc').mkdir()
        self.seed_pending_restart()
        self.reboot()
        with patch.object(self.store,'finish_clean_removal',side_effect=OSError('host interruption')):
            with self.assertRaises(OSError):self.remove()
        proc=self.root/'proc/123';proc.mkdir()
        (proc/'cmdline').write_text('/usr/bin/node\0'+str(self.root/'developer/apps/usr/palm/services/com.gathin.tvhome.renewal/service.js')+'\0')
        with self.assertRaisesRegex(UserError, 'process did not stop'):
            self.remove()
        self.assertIsNotNone(self.store.pending(self.profile))

    def test_empty_files_with_live_or_unreadable_processes_still_block_removal(self):
        proc=self.root/'proc'/'123';proc.mkdir(parents=True)
        for argv in ('/usr/bin/node\0/media/developer/apps/usr/palm/services/com.gathin.tvhome.renewal/service.js\0',
                     '/bin/sh\0-c\0sleep 1; /usr/bin/node /media/developer/apps/usr/palm/services/com.gathin.tvhome.renewal/service.js\0',
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
                if argv and 'com.gathin.tvhome.renewal' in argv:
                    with self.assertRaisesRegex(UserError, 'process did not stop'):
                        self.remove()
                else:
                    self.assertTrue(self.remove()['restart_required'])

    def test_foreign_absolute_script_does_not_force_restart_on_empty_tv(self):
        proc=self.root/'proc'/'123';proc.mkdir(parents=True)
        (proc/'cmdline').write_text('/usr/bin/node\0/usr/palm/services/org.foreign/service.js\0')
        self.assertTrue(self.remove()['verified_clean'])

    def test_relative_script_in_deleted_project_cwd_still_blocks_removal(self):
        proc=self.root/'proc'/'123';proc.mkdir(parents=True)
        (proc/'cmdline').write_text('/usr/bin/node\0service.js\0')
        (proc/'cwd').symlink_to(self.root/'developer/apps/usr/palm/services/com.gathin.tvhome.renewal')
        with self.assertRaisesRegex(UserError, 'process did not stop'):
            self.remove()

    def test_legacy_partial_install_with_idle_package_manager_needs_no_restart(self):
        (self.root/'proc').mkdir()
        self.store.begin(self.profile,'install')
        own = self.own_file('apps/usr/palm/applications/com.local.nativehome/state/settings.json')
        self.remote.boot = 'not-readable-as-a-boot-id'
        self.assertTrue(self.remove()['verified_clean'])
        self.assertFalse(own.exists())
        self.assertIsNone(self.store.pending(self.profile))

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
        with self.assertRaises(UserError) as caught:
            self.remove()
        self.assertEqual(caught.exception.reason_code, 'controls-unverified')
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

    def seed_pending_restart(self):
        self.store.request_clean_removal(self.profile)
        proof = self.cleanup._device(self.installer, 'boot-create')['boot_proof']
        self.store.checkpoint(self.profile, stage='restart-required', cleanup_boot_proof=proof)

    def reboot(self):
        self.remote.boot='22222222-2222-2222-2222-222222222222'
        for p in (self.root/'volatile').glob('cytv-removal-*.boot'):p.unlink()

    def boot_marker(self):
        goal=self.store.pending(self.profile)['removal_operation']
        return self.root/'volatile'/('cytv-removal-'+goal+'.boot')

    def test_ordinary_removal_completes_without_a_usable_boot_marker_directory(self):
        self.remote.volatile_mode = 0o755
        (self.root / 'proc').mkdir()
        self.remote.apps = {'com.local.nativehome', 'com.gathin.tvhome'}
        helper_state = self.own_file('apps/usr/palm/applications/com.local.nativehome/state/ssap-key.json')
        with patch.object(self.cleanup, '_device', wraps=self.cleanup._device) as device:
            self.assertEqual(self.remove(), {'removed': True, 'verified_clean': True})
        self.assertFalse(any(call.args[1].startswith('boot-') for call in device.call_args_list))
        self.assertFalse(self.remote.apps)
        self.assertFalse(helper_state.exists())
        self.assertTrue(any(uri.endswith('/launch') and data == {'id': 'com.webos.app.home'}
                            for uri, data in self.remote.calls))

    def test_ordinary_removal_waits_for_the_helper_service_to_exit(self):
        proc = self.root / 'proc/123'
        proc.mkdir(parents=True)
        service = self.own_file('apps/usr/palm/services/com.local.nativehome.service/service.js')
        cmdline = proc / 'cmdline'
        cmdline.write_bytes(b'/usr/bin/node\0' + os.fsencode(service) + b'\0')
        self.remote.apps = {'com.local.nativehome'}
        # The first process sample sees the service, which exits before the next.
        self.remote.transform = lambda code: (
            'var fixtureFs = require("fs"), fixtureRead = fixtureFs.readFileSync; fixtureFs.readFileSync = function(p) {'
            'var value = fixtureRead.apply(this, arguments);'
            'if (p === ' + json.dumps(str(cmdline)) + ') { fixtureFs.unlinkSync(p);'
            'fixtureFs.rmdirSync(' + json.dumps(str(proc)) + '); } return value; };\n' + code)
        original_luna = self.remote.luna

        def luna(uri, payload, **kwargs):
            if uri.endswith('/dev/remove'):
                self.assertFalse(proc.exists(), 'package removal must follow process shutdown')
            return original_luna(uri, payload, **kwargs)

        self.remote.luna = luna
        self.assertEqual(self.remove(), {'removed': True, 'verified_clean': True})

    def test_restricted_tmp_completes_process_verified_removal_without_marker(self):
        self.remote.volatile_mode=0o111
        (self.root/'proc').mkdir()
        self.remote.apps=set(self.cleanup.APPS)
        self.own_file('apps/usr/palm/applications/com.local.nativehome/state/ssap-key.json')
        try:result=self.remove()
        except UserError as error:self.fail('Known Developer Mode tmp layout blocked removal: '+str(error))
        self.assertTrue(result['verified_clean'])
        self.assertFalse(self.remote.apps)
        self.assertFalse(list((self.root/'volatile').glob('cytv-removal-*')))
        self.assertEqual((self.root/'volatile').stat().st_mode&0o7777,0o111)

    def test_marker_based_retry_finishes_after_startup_recovers_without_reboot(self):
        (self.root / 'proc').mkdir()
        self.remote.apps = {'com.local.nativehome'}
        self.own_file('apps/usr/palm/services/com.local.nativehome.service/service.js')
        self.seed_pending_restart()
        pending = self.store.pending(self.profile)
        self.assertEqual(pending['cleanup_boot_proof']['schema'], 1)
        self.remote.broken_service = False

        with patch.object(self.cleanup, '_device', wraps=self.cleanup._device) as device:
            self.assertTrue(self.remove()['verified_clean'])
        actions = [call.args[1] for call in device.call_args_list]
        self.assertIn('idle', actions[:actions.index('sweep')])
        self.assertEqual(actions[actions.index('sweep') + 1:], ['inventory', 'idle', 'inventory', 'boot-release', 'history'])
        self.assertIsNone(self.store.pending(self.profile))

    def test_restricted_tmp_rechecks_legacy_restart_request_after_startup_recovers(self):
        self.remote.volatile_mode = 0o111
        (self.root / 'proc').mkdir()
        self.remote.apps = {'com.local.nativehome', 'com.gathin.tvhome'}
        service = self.own_file('apps/usr/palm/services/com.local.nativehome.service/service.js')
        self.seed_pending_restart()
        pending = self.store.pending(self.profile)
        proc = self.root / 'proc/123'
        proc.mkdir()
        cmdline = proc / 'cmdline'
        cmdline.write_bytes(b'/usr/bin/node\0' + os.fsencode(service) + b'\0')
        with self.assertRaisesRegex(UserError, 'process did not stop'):
            self.remove()
        self.assertTrue(service.exists())
        self.assertEqual(len(self.remote.apps), 2)

        cmdline.unlink()
        proc.rmdir()
        self.assertTrue(self.remove()['verified_clean'])
        self.assertFalse(service.exists())
        self.assertFalse(self.remote.apps)
        receipt = json.loads((self.store.device_dir(self.profile) / 'clean-removal.json').read_text())
        self.assertEqual(receipt['removal_operation'], pending['removal_operation'])
        self.assertIsNot(receipt.get('cleanup_boot_verified'), True)
        self.assertEqual(receipt['cleanup_boot_proof']['kernel'], self.remote.boot)

    def test_restricted_tmp_rechecks_resident_installer_after_package_manager_becomes_idle(self):
        self.remote.volatile_mode = 0o111
        (self.root / 'proc').mkdir()
        self.remote.apps = {'com.local.nativehome'}
        journal = self.own_file('.cytv-installer/operations/' + 'a' * 32 + '/journal.json')
        original_luna = self.remote.luna
        busy = True

        def luna(uri, payload, **kwargs):
            if uri == 'com.webos.appInstallService/status' and busy:
                return {'returnValue': True, 'status': {'apps': ['com.local.nativehome']}}
            return original_luna(uri, payload, **kwargs)

        self.remote.luna = luna
        self.seed_pending_restart()
        with patch.object(self.cleanup, 'monotonic', side_effect=(0, 20)), self.assertRaises(UserError) as failure:
            self.remove()
        self.assertEqual(failure.exception.reason_code, 'original-writer-active')
        self.assertEqual(self.store.pending(self.profile)['stage'], 'requested')
        self.assertTrue(journal.exists())
        self.assertEqual(self.remote.apps, {'com.local.nativehome'})

        busy = False
        proc = self.root / 'proc/123'
        proc.mkdir()
        (proc / 'cmdline').write_bytes(b'/usr/bin/node\0' + os.fsencode(journal.with_name('observer.js')) + b'\0')
        with self.assertRaisesRegex(UserError, 'original TV operation is still running'):
            self.remove()
        self.assertTrue(journal.exists())
        self.assertFalse(any(uri.endswith('/dev/remove') for uri, _ in self.remote.calls))
        shutil.rmtree(proc)

        self.assertTrue(self.remove()['verified_clean'])
        self.assertFalse(journal.exists())
        self.assertFalse(self.remote.apps)
        receipt = json.loads((self.store.device_dir(self.profile) / 'clean-removal.json').read_text())
        self.assertIsNot(receipt.get('cleanup_boot_verified'), True)
        self.assertEqual(receipt['cleanup_boot_proof']['kernel'], self.remote.boot)

    def test_denied_optional_monitor_and_unreadable_history_allow_vendor_removal(self):
        self.remote.volatile_mode = 0o111
        (self.root / 'proc').mkdir()
        app = 'com.local.nativehome'
        self.remote.apps.add(app)
        self.store.begin(self.profile, 'install',
                         recovery_protocol='no-root-original-stream-v1', observer_operation='a' * 32)
        journal = self.own_file('.cytv-installer/operations/' + 'a' * 32 + '/journal.json')
        journal.parent.chmod(0o000)
        self.addCleanup(lambda: journal.parent.chmod(0o700) if journal.parent.exists() else None)
        original = self.remote.luna

        def denied(uri, payload, **kwargs):
            if uri.endswith('/status'):
                raise TVRejected('Denied', {'returnValue': False, 'errorCode': -1}, uri)
            return original(uri, payload, **kwargs)

        self.remote.luna = denied
        self.assertTrue(self.remove()['verified_clean'])
        self.assertEqual([body['id'] for uri, body in self.remote.calls if uri.endswith('/dev/remove')], [app])
        self.assertIsNone(self.store.pending(self.profile))

    def test_malformed_optional_monitor_allows_first_supported_vendor_remove(self):
        (self.root / 'proc').mkdir()
        app = 'com.local.nativehome'
        self.remote.apps.add(app)
        self.own_file('.cytv-installer/operations/' + 'a' * 32 + '/journal.json')
        original = self.remote.luna
        interrupted = True

        def luna(uri, payload, **kwargs):
            if uri.endswith('/status'):
                if interrupted:
                    raise UserError('Connection interrupted', reason_code='connection-interrupted')
                return {'returnValue': True, 'status': {}}
            return original(uri, payload, **kwargs)

        self.remote.luna = luna
        with self.assertRaises(UserError) as disconnected:
            self.remove()
        self.assertEqual(disconnected.exception.reason_code, 'connection-interrupted')
        self.assertFalse(any(uri.endswith('/dev/remove') for uri, _ in self.remote.calls))
        interrupted = False
        self.assertTrue(self.remove()['verified_clean'])
        self.assertEqual([body['id'] for uri, body in self.remote.calls if uri.endswith('/dev/remove')], [app])
        self.assertIsNone(self.store.pending(self.profile))

    def test_foreign_active_reservation_arriving_at_stop_preserves_controls(self):
        (self.root / 'proc').mkdir()
        self.remote.apps.add('com.local.nativehome')
        owner = self.root / 'developer/.cytv-installer/active/owner-foreign.json'
        original = self.remote.run

        def run(command, data=None, **options):
            if data and json.loads(json.JSONDecoder().raw_decode(data.decode()[len('process.argv.push('):])[0])['action'] == 'stop' and not appeared:
                appeared.append(True)
                owner.parent.mkdir(parents=True)
                owner.write_text('foreign')
            return original(command, data, **options)

        appeared = []
        self.remote.run = run
        with self.assertRaises(UserError):
            self.remove()
        self.assertEqual(owner.read_text(), 'foreign')
        self.assertFalse(any(uri.endswith(('/deleteDevice', '/launch', '/dev/remove')) for uri, _ in self.remote.calls))
        owner.unlink()
        self.assertTrue(self.remove()['verified_clean'])

    def test_restricted_tmp_keeps_unresolved_install_when_package_status_is_denied(self):
        from cytv.diagnostics import create_report

        self.remote.volatile_mode = 0o111
        (self.root / 'proc').mkdir()
        self.store.begin(self.profile, 'install', stage='submitted')
        luna = self.remote.luna

        def denied(uri, payload, **kwargs):
            if uri == 'com.webos.appInstallService/status':
                raise TVRejected('Denied', {'returnValue': False, 'errorCode': -1}, uri)
            return luna(uri, payload, **kwargs)

        self.remote.luna = denied
        self.remote.cut_boot_create = True
        with self.assertRaises(UserError):
            self.remove()
        self.assertIsNone(self.store.pending(self.profile).get('cleanup_boot_proof'))
        self.assertTrue(self.remove()['restart_required'])
        pending = self.store.pending(self.profile)
        self.assertEqual(pending['cleanup_boot_proof'], {'schema': 2, 'kind': 'kernel-only',
            'goal': pending['removal_operation'], 'kernel': self.remote.boot})
        self.assertTrue(self.remove()['restart_required'])
        report = json.loads(create_report(self.store, 'status', self.profile, 'status', None).read_text())
        self.assertEqual(report['removal']['restart_triggers'], ['prior-operation-unresolved'])
        self.reboot()
        self.assertTrue(self.remove()['verified_clean'])

    def test_kernel_only_proof_never_uses_marker_absence_or_retires_same_boot(self):
        self.remote.volatile_mode=0o111
        self.store.request_clean_removal(self.profile)
        try:proof=self.cleanup._device(self.installer,'boot-create')['boot_proof']
        except UserError as error:self.fail('Could not capture kernel-only baseline: '+str(error))
        self.remote.volatile_mode=0o1777
        self.assertFalse(self.cleanup._device(self.installer,'boot-probe',proof=proof)['boot_restarted'])
        with self.assertRaises(UserError):self.cleanup._device(self.installer,'boot-retire',proof=proof)
        self.cleanup._device(self.installer,'boot-release',proof=proof)
        self.assertFalse(self.cleanup._device(self.installer,'boot-probe',proof=proof)['boot_restarted'])
        for bad in (dict(proof,goal='a'*32),dict(proof,kind='marker'),dict(proof,schema=True),dict(proof,extra=True)):
            with self.subTest(proof=bad),self.assertRaises(UserError):
                self.cleanup._device(self.installer,'boot-probe',proof=bad)

    def test_root_ssh_nonsticky_tmp_requires_a_changed_kernel_boot_id(self):
        self.profile.update(connection='root-ssh', port=22)
        self.remote.volatile_mode = 0o777
        self.store.request_clean_removal(self.profile)
        proof = self.cleanup._device(self.installer, 'boot-create')['boot_proof']
        self.assertEqual(proof['kind'], 'kernel-only')
        self.assertFalse(self.cleanup._device(self.installer, 'boot-probe', proof=proof)['boot_restarted'])
        with self.assertRaises(UserError):
            self.cleanup._device(self.installer, 'boot-retire', proof=proof)
        self.remote.boot = '22222222-2222-2222-2222-222222222222'
        self.assertTrue(self.cleanup._device(self.installer, 'boot-retire', proof=proof)['boot_restarted'])
        self.assertFalse(list((self.root / 'volatile').iterdir()))

    def test_captured_marker_proof_cannot_switch_to_kernel_only_when_tmp_changes(self):
        self.store.request_clean_removal(self.profile)
        proof=self.cleanup._device(self.installer,'boot-create')['boot_proof']
        self.remote.volatile_mode=0o111
        self.remote.boot='22222222-2222-2222-2222-222222222222'
        with self.assertRaises(UserError):self.cleanup._device(self.installer,'boot-probe',proof=proof)
        self.assertTrue(self.boot_marker().exists())

    def test_boot_root_refusal_exports_safe_context_before_package_removal(self):
        from cytv import diagnostics
        self.remote.volatile_mode=0o755
        self.remote.apps={'com.local.nativehome'}
        process = self.root / 'proc/123'
        process.mkdir(parents=True)
        (process / 'cmdline').write_bytes(b'/usr/bin/node\0-e\0')
        self.own_file('.cytv-installer/operations/' + 'a' * 32 + '/journal.json')
        self.store.request_clean_removal(self.profile)
        self.store.checkpoint(self.profile, cleanup_boot_proof=None)
        with self.assertRaises(RuntimeError) as caught:self.remove()
        self.assertIsInstance(caught.exception,UserError,'cleanup failure lost its safe diagnostic envelope')
        detail=caught.exception.no_root_cleanup
        self.assertEqual(detail['action'],'boot-create')
        self.assertEqual(detail['step'],'boot-root')
        self.assertEqual(detail['reason'],'unsafe-path')
        self.assertEqual(detail['directory_mode'],'0755')
        self.assertEqual(detail['directory_owner'],'root')
        self.assertEqual(detail['directory_type'],'directory')
        self.assertFalse(any(uri.endswith('/dev/remove') for uri,_ in self.remote.calls))
        self.assertEqual(self.store.pending(self.profile)['stage'],'restart-required')
        report=json.loads(diagnostics.create_report(self.store,'uninstall',self.profile,'uninstall',caught.exception).read_text())
        self.assertEqual(report['no_root_cleanup'],detail)
        self.assertEqual(report['first_failure']['no_root_cleanup'],detail)
        self.assertNotIn(str(self.root),json.dumps(report))
        self.assertNotIn(self.remote.boot,json.dumps(report))

    def test_boot_root_symlink_is_reported_and_never_followed_for_cleanup(self):
        destination=self.root/'foreign';destination.mkdir()
        evidence=destination/'keep';evidence.write_text('preserve')
        (self.root/'volatile').symlink_to(destination,target_is_directory=True)
        self.store.begin(self.profile, 'install', stage='submitted')
        with self.assertRaises(UserError) as caught:self.remove()
        self.assertEqual(caught.exception.no_root_cleanup['step'],'boot-root')
        self.assertEqual(caught.exception.no_root_cleanup['directory_type'],'symlink')
        self.assertEqual(evidence.read_text(),'preserve')
        self.assertFalse(list(destination.glob('cytv-removal-*')))

    def test_boot_storage_failure_preserves_existing_space_guidance(self):
        self.store.begin(self.profile, 'install', stage='submitted')
        self.remote.transform=lambda code:code.replace('fs.fsyncSync(out);',
            "var injected=Error('No space left on device: PRIVATE-PATH');injected.code='ENOSPC';injected.syscall='fsync';throw injected;")
        with self.assertRaises(UserError) as caught:self.remove()
        self.assertEqual(caught.exception.reason_code,'tv-storage-full')
        self.assertEqual(caught.exception.no_root_cleanup['exception_code'],'ENOSPC')
        self.assertNotIn('PRIVATE',str(caught.exception))

    def test_boot_error_envelope_cannot_be_accepted_as_a_success_reply(self):
        from unittest.mock import patch
        for detail in (None,{'step':'PRIVATE-PATH','exception_code':'PRIVATE-TOKEN'}):
            reply={'schema':1,'present':[],'blocked':[],'root_present':[],
                   'boot_proof':{'schema':1},'boot_restarted':True,'cleanup_error':detail}
            with self.subTest(detail=detail),patch.object(self.remote,'run',return_value=json.dumps(reply)):
                with self.assertRaises(UserError) as caught:
                    self.cleanup._device(self.installer,'boot-create')
                self.assertEqual(caught.exception.no_root_cleanup['action'],'boot-create')
                self.assertNotIn('PRIVATE',json.dumps(caught.exception.no_root_cleanup))

    def test_boot_transport_failure_retains_typed_error_and_action(self):
        from cytv.errors import TVCommandError
        from unittest.mock import patch
        error=TVCommandError(1)
        with patch.object(self.remote,'run',side_effect=error):
            with self.assertRaises(TVCommandError) as caught:
                self.cleanup._device(self.installer,'boot-create')
        self.assertIs(caught.exception,error)
        self.assertEqual(error.no_root_cleanup['action'],'boot-create')
        self.assertEqual(error.no_root_cleanup['failure'],'command-failed')
        self.assertEqual(error.exit_status,1)

    def test_boot_fsync_failure_keeps_fixed_error_and_retryable_marker(self):
        from cytv import diagnostics
        self.remote.transform=lambda code:code.replace('fs.fsyncSync(out);',
            "var injected=Error('PRIVATE-TOKEN-PATH');injected.code='EINVAL';injected.syscall='fsync';injected.path='PRIVATE-PATH';throw injected;")
        with self.assertRaises(RuntimeError) as caught:self.remove()
        self.assertIsInstance(caught.exception,UserError,'cleanup failure lost its safe diagnostic envelope')
        detail=caught.exception.no_root_cleanup
        self.assertEqual(detail['step'],'boot-create')
        self.assertEqual(detail['exception_code'],'EINVAL')
        self.assertEqual(detail['filesystem_operation'],'fsync')
        self.assertEqual(detail['reason'],'unknown')
        self.assertTrue(self.boot_marker().exists())
        self.assertIsNone(self.store.pending(self.profile).get('cleanup_boot_proof'))
        report=diagnostics.create_report(self.store,'uninstall',self.profile,'uninstall',caught.exception).read_text()
        self.assertNotIn('PRIVATE',report)
        self.remote.transform=lambda code:code
        self.assertTrue(self.remove()['restart_required'])

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
        from cytv import diagnostics
        diagnostics.create_report(self.store,'recovery',self.profile,'recovery',None)
        self.assertEqual(self.remote.commands,[])  # Report export is local too.
        answers=iter(['y','y'])
        recovery.recover(self.installer,lambda _:next(answers),write)
        pending=self.store.pending(self.profile)
        self.assertEqual(pending['recovery_protocol'],'clean-removal-v1')
        self.assertEqual((directory/pending['original_receipt']).read_bytes(),original)
        self.reboot()
        self.assertTrue(self.remove()['verified_clean'])
        self.assertIsNone(self.store.pending(self.profile))
        self.assertEqual((directory/('capsule-'+operation+'.json')).read_bytes(),capsule)
        self.assertFalse(any(uri.endswith(('/dev/install','/dev/remove')) for uri,_ in self.remote.calls))

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
        (self.root / 'proc').mkdir()
        self.assertTrue(self.remove()['temporary_files_retained'])
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
        self.store.begin(self.profile, 'install', stage='submitted')
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

    def test_cleanup_failed_generation_publication_invalidates_baseline_and_stops(self):
        for existing in (False,True):
            with self.subTest(existing=existing):
                marker=self.own_file('apps/usr/palm/applications/com.local.nativehome/state/blocked','stopped')
                generation=marker.parent/'stop-generation'
                if existing:generation.write_text('I'+'a'*32);generation.chmod(0o664)
                elif generation.exists():generation.unlink()
                self.remote.transform=lambda code:code.replace("var token = 'S' + crypto.randomBytes(16)", "var token = 'S' + (function(){throw Error('entropy unavailable');})()")
                result=self.cleanup._device(self.installer,'stop')
                self.assertTrue(result['blocked'])
                self.assertEqual(generation.read_bytes(),b'')
                self.assertEqual(marker.read_text(),'stopped')
                self.assertEqual(json.loads((marker.parent/'control.json').read_text()),{'cmd':'stop'})

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

    def model_owners(self, owners):
        # Keep actual POSIX modes/inodes and Node filesystem operations; adapt
        # only ownership that an unprivileged host cannot reproduce with chown.
        prefix=('var reportedOwners='+json.dumps({str(p):ids for p,ids in owners.items()})+';'
                'var actualLstat=fs.lstatSync;fs.lstatSync=function(p){var s=actualLstat(p),owner=reportedOwners[path.resolve(p)];'
                'if(owner){s.uid=owner[0];s.gid=owner[1];}return s;};'
                # Model the packaged owner and group on both the path and
                # pinned FD. Actual permissions, inode and writes stay POSIX.
                'var groups=process.getgroups;process.getgroups=function(){return groups.call(process).concat([5000]);};'
                'var openedPaths={},ownersByInode={},actualOpen=fs.openSync,actualClose=fs.closeSync,actualFstat=fs.fstatSync;'
                'fs.openSync=function(p){var fd=actualOpen.apply(fs,arguments);openedPaths[fd]=path.resolve(p);return fd;};'
                'fs.closeSync=function(fd){delete openedPaths[fd];return actualClose.apply(fs,arguments);};'
                'var actualFchown=fs.fchownSync;fs.fchownSync=function(fd,uid,gid){'
                'if(gid!==5000)return actualFchown.apply(fs,arguments);var s=actualFstat(fd);ownersByInode[s.ino]=gid;};'
                'fs.fstatSync=function(fd){var s=actualFstat(fd),owner=reportedOwners[openedPaths[fd]];'
                'if(owner){s.uid=owner[0];s.gid=owner[1];}if(ownersByInode[s.ino])s.gid=ownersByInode[s.ino];return s;};'
                'var modelledLstat=fs.lstatSync;fs.lstatSync=function(p){var s=modelledLstat(p);'
                'if(ownersByInode[s.ino])s.gid=ownersByInode[s.ino];return s;};')
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

    def removal_payload(self):
        app='com.local.nativehome';service=app+'.service';version='0.7.4'
        files={'usr/palm/applications/'+app+'/appinfo.json':json.dumps({'id':app,'version':version,'main':'detach'}).encode(),
               'usr/palm/packages/'+app+'/packageinfo.json':json.dumps({'id':app,'app':app,'version':version,'services':[service]}).encode(),
               'usr/palm/services/'+service+'/services.json':json.dumps({'id':service,'services':[{'name':service}]}).encode()}
        payload=self.root/'payload';payload.mkdir()
        (payload/'helper.ipk').write_bytes(package.ipk(app,version,files,architecture='arm'))
        self.installer.payload=payload
        self.installer.manifest={'helper':'helper.ipk','files':{str(p.relative_to(payload)):hashlib.sha256(p.read_bytes()).hexdigest() for p in payload.rglob('*') if p.is_file()}}

    def test_partial_setup_removal_archives_original_receipt(self):
        (self.root / 'proc').mkdir()
        self.store.begin(self.profile, 'install', components={}, failure={'reason': 'unknown'}, stage='install-packages')
        directory = self.store.device_dir(self.profile)
        original = (directory / 'operation.json').read_bytes()
        key = self.own_file('apps/usr/palm/applications/com.local.nativehome/state/ssap-key.json')
        self.assertTrue(self.remove()['verified_clean'])
        self.assertFalse(key.exists())
        completed = json.loads((directory / 'clean-removal.json').read_text())
        self.assertEqual((directory / completed['original_receipt']).read_bytes(), original)

    def test_recovery_of_legacy_install_when_global_package_status_is_denied(self):
        from cytv.diagnostics import create_report
        from cytv.recovery import recover
        from cytv.terminal import Console
        from cytv.transport import terminal_reply

        (self.root / 'proc').mkdir()
        self.store.begin(self.profile, 'install')
        original = self.store.pending(self.profile)
        receipt = self.store.device_dir(self.profile) / 'operation.json'
        original_bytes = receipt.read_bytes()
        report = create_report(self.store, 'install', self.profile, 'install-packages', Exception())
        first_failure = json.loads(report.read_text())['first_failure']
        self.remote.apps = {operations.HELPER}
        status_uri = 'com.webos.appInstallService/status'
        luna = self.remote.luna

        def deny_status(uri, payload, **kwargs):
            if uri == status_uri:
                self.remote.calls.append((uri, payload))
                terminal_reply({'returnValue': False, 'errorCode': -1}, uri=uri)
            return luna(uri, payload, **kwargs)

        self.remote.luna = deny_status
        self.removal_payload()
        (self.installer.payload / 'payload.json').write_text(json.dumps(self.installer.manifest))
        self.installer.manifest = {}
        self.installer.tv_info = {}
        write = Console(self.progress.append)
        plans = []
        write.recovery_plan = plans.append

        def run(*answers):
            answers = iter(answers)
            recover(self.installer, lambda _: next(answers), write)

        with patch.object(self.installer, 'observe_recovery',
                          return_value={'device': {'apps': [{'id': operations.HELPER}]}}), \
             patch('cytv.package.verify_payload', wraps=package.verify_payload) as verify_payload:
            run('y', '')
            self.assertEqual(plans[-1]['state'], 'ready')
            self.assertEqual(receipt.read_bytes(), original_bytes)
            self.assertEqual(self.remote.calls, [(status_uri, {'subscribe': True})])
            self.assertEqual(self.remote.commands, [])
            verify_payload.assert_not_called()

            self.remote.reject = {'returnValue': False, 'errorCode': -7}
            with self.assertRaises(TVRejected) as busy:
                run('y', 'y')
            self.assertEqual(busy.exception.luna['operation'], 'package-remove')
            self.assertEqual(busy.exception.luna['error_code'], -7)
            self.assertEqual(self.remote.apps, {operations.HELPER})
            self.assertEqual(plans[-1]['state'], 'blocked')
            pending = self.store.pending(self.profile)
            self.assertEqual(pending['previous'], original)
            self.assertEqual((receipt.parent / pending['original_receipt']).read_bytes(), original_bytes)
            verify_payload.assert_called_once_with(self.installer.payload)

            with self.assertRaises(UserError):
                run('y', 'y')
            self.assertFalse(self.remote.apps)
            self.assertTrue(plans[-1]['restart_required'])
            self.assertFalse(plans[-1]['verified_clean'])
            self.reboot()
            run('y', 'y')

        self.assertTrue(plans[-1]['verified_clean'])
        self.assertIsNone(self.store.pending(self.profile))
        self.assertEqual((receipt.parent / pending['original_receipt']).read_bytes(), original_bytes)
        report = create_report(self.store, 'recover', self.profile, 'recover')
        self.assertEqual(json.loads(report.read_text())['first_failure'], first_failure)
        self.assertEqual(sum(uri == status_uri for uri, _ in self.remote.calls), 5)
        self.assertFalse(any(uri.endswith('/dev/install') for uri, _ in self.remote.calls))

    def test_issue_307_unregistered_partial_helper_requires_verified_restart(self):
        from cytv.diagnostics import create_report
        from cytv.recovery import recover
        from cytv.terminal import Console
        from cytv.transport import terminal_reply

        helper = operations.HELPER
        service = helper + '.service'
        app_info = self.own_file(f'apps/usr/palm/applications/{helper}/appinfo.json',
                                 json.dumps({'id': helper, 'version': '0.6.22'}))
        state = self.own_file(f'apps/usr/palm/applications/{helper}/state/settings.json', '{}')
        package_info = self.own_file(f'apps/usr/palm/packages/{helper}/packageinfo.json',
                                     json.dumps({'id': helper, 'services': [service]}))
        files = {file: file.read_bytes() for file in (app_info, state, package_info)}
        self.assertFalse((self.root / 'developer/apps/usr/palm/services').exists())
        self.assertEqual(list((self.root / 'bus').iterdir()), [])
        self.remote.apps = {'com.limelight.webos'}
        self.store.begin(self.profile, 'install')
        directory = self.store.device_dir(self.profile)
        receipt = directory / 'operation.json'
        original = receipt.read_bytes()
        failure = TVRejected('Install failed', {'statusValue': 24, 'details': {'errorCode': -1}},
                             'com.webos.appInstallService/dev/install')
        report = create_report(self.store, 'install', self.profile, 'install-packages', failure)
        first_failure = json.loads(report.read_text())['first_failure']
        self.assertEqual(first_failure['luna']['status_value'], 24)
        history = directory / 'diagnostic-failures'
        retained = {file.name: file.read_bytes() for file in history.iterdir()}

        status_uri = 'com.webos.appInstallService/status'
        denied = {'returnValue': False, 'errorCode': -1}
        active = {'returnValue': True, 'status': {'apps': [helper]}}
        ambiguous = {'returnValue': True, 'status': {}}
        contradictory = dict(denied, status=active['status'])
        status = denied
        luna = self.remote.luna

        def package_status(uri, payload, **kwargs):
            if uri == status_uri:
                self.remote.calls.append((uri, payload))
                terminal_reply(status, uri=uri)
                return status
            return luna(uri, payload, **kwargs)

        self.remote.luna = package_status
        self.removal_payload()
        (self.installer.payload / 'payload.json').write_text(json.dumps(self.installer.manifest))
        self.installer.manifest = {}
        self.installer.tv_info = {}
        write = Console(self.progress.append)
        plans = []
        write.recovery_plan = plans.append

        def run(*answers):
            answers = iter(answers)
            recover(self.installer, lambda _: next(answers), write)

        def assert_files_kept():
            self.assertEqual({file: file.read_bytes() for file in files}, files)
            self.assertEqual({file.name: file.read_bytes() for file in history.iterdir()}, retained)
            self.assertTrue(all(uri in (status_uri, 'com.webos.applicationManager/dev/listApps')
                                for uri, _ in self.remote.calls))

        with patch.object(self.installer, 'observe_recovery', return_value={'device': {'apps': []}}):
            for status in (active, ambiguous):
                with self.subTest(status=status), self.assertRaisesRegex(UserError, 'not confirmed idle'):
                    run('y')
                self.assertEqual(receipt.read_bytes(), original)
                self.assertEqual(self.remote.commands, [])
                assert_files_kept()

            status = contradictory
            with self.assertRaises(TVRejected):
                run('y')
            self.assertEqual(receipt.read_bytes(), original)
            assert_files_kept()

            status = denied
            run('y', '')
            self.assertEqual(receipt.read_bytes(), original)
            self.assertEqual(self.remote.commands, [])
            assert_files_kept()

            run('y', 'y')
            self.assertTrue(plans[-1]['restart_required'])
            self.assertFalse(plans[-1]['verified_clean'])
            archived = directory / self.store.pending(self.profile)['original_receipt']
            self.assertEqual(archived.read_bytes(), original)
            assert_files_kept()

            with self.assertRaises(UserError) as same_boot:
                run('y', 'y')
            self.assertEqual(same_boot.exception.reason_code, 'pending-operation')
            self.assertTrue(plans[-1]['restart_required'])
            self.assertFalse(plans[-1]['verified_clean'])
            assert_files_kept()

            self.boot_marker().unlink()
            with self.assertRaises(UserError):
                run('y', 'y')
            self.assertTrue(plans[-1]['restart_required'])
            assert_files_kept()

            self.reboot()
            status = active
            with patch.object(self.cleanup, 'monotonic', side_effect=(0, 20)), self.assertRaises(UserError) as failure:
                run('y', 'y')
            self.assertEqual(failure.exception.reason_code, 'original-writer-active')
            self.assertIsNotNone(self.store.pending(self.profile))
            self.assertFalse(plans[-1]['verified_clean'])
            self.assertFalse(plans[-1]['restart_required'])
            assert_files_kept()

            status = ambiguous
            (self.root / 'proc').mkdir()
            with patch.object(self.store, 'finish_clean_removal', side_effect=OSError('host interruption')):
                with self.assertRaisesRegex(OSError, 'host interruption'):
                    run('y', 'y')
            self.assertEqual(self.store.pending(self.profile)['stage'], 'verified-clean')
            self.assertFalse(plans[-1]['verified_clean'])
            run('y', 'y')

        self.assertTrue(plans[-1]['verified_clean'])
        self.assertIsNone(self.store.pending(self.profile))
        self.assertTrue(all(not file.exists() for file in files))
        self.assertEqual(self.remote.apps, {'com.limelight.webos'})
        self.assertFalse(any(uri.endswith(('/dev/install', '/dev/remove', '/disable')) for uri, _ in self.remote.calls))
        self.assertEqual(archived.read_bytes(), original)
        self.assertEqual({file.name: file.read_bytes() for file in history.iterdir()}, retained)
        report = create_report(self.store, 'recover', self.profile, 'recover')
        self.assertEqual(json.loads(report.read_text())['first_failure'], first_failure)

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

    def test_unregistered_broken_service_can_be_deleted_after_restart(self):
        broken = self.own_file('apps/usr/palm/services/com.local.nativehome.service/service.js',
                               "require('missing dependency');")
        self.remote.broken_service = True
        self.assertTrue(self.remove()['restart_required'])
        self.assertTrue(broken.exists())
        self.assertEqual(self.store.pending(self.profile)['cleanup_restart_triggers'], ['startup-disable-unverified'])
        self.reboot()
        self.assertTrue(self.remove()['verified_clean'])
        self.assertFalse(broken.exists())

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

    def test_repeat_clean_and_fresh_quiescent_removal_finish_without_new_restart(self):
        self.remove();self.reboot();self.assertTrue(self.remove()['verified_clean'])
        (self.root/'proc').mkdir(exist_ok=True)
        self.assertTrue(self.remove()['verified_clean'])
        self.store.begin(self.profile,'install');self.store.finish(self.profile)
        self.remote.apps={'com.gathin.tvhome'}
        self.assertTrue(self.remove()['verified_clean'])

    def test_known_root_installation_requests_root_access(self):
        root=self.root/'varlib/clean-your-tv-root';root.mkdir();(root/'config.json').write_text('root configuration')
        with self.assertRaisesRegex(UserError,'Root access'):self.remove()
        self.assertTrue(root.exists());self.assertIsNotNone(self.store.pending(self.profile))

    @unittest.skipIf(getattr(os, 'getuid', lambda: -1)() == 0, 'unprivileged SDK model')
    def test_no_root_removal_does_not_require_listing_foreign_ls2_roles(self):
        (self.root / 'proc').mkdir()
        directory = self.root / 'bus/roles.d'
        directory.mkdir()
        foreign = directory / 'org.foreign.app.json'
        foreign.write_text('{}')
        directory.chmod(0o111)
        self.addCleanup(directory.chmod, 0o755)

        self.assertTrue(self.remove()['verified_clean'])

        self.assertTrue(foreign.exists())
        self.assertIsNone(self.store.pending(self.profile))

    def test_public_staging_requires_owned_package_identity_and_preserves_foreign(self):
        own=self.root/'developer/temp'/('cytv-'+'a'*32);own.mkdir(parents=True)
        foreign=self.root/'developer/temp'/('cytv-'+'b'*32);foreign.mkdir()
        (own/'helper.ipk').write_bytes(package.ipk('com.local.nativehome','0.7.4',{},architecture='arm'))
        (foreign/'helper.ipk').write_bytes(package.ipk('org.foreign.app','1.0.0',{},architecture='arm'))
        (foreign/'notes.txt').write_text('owner file')
        self.remove();self.assertFalse(own.exists());self.assertTrue((foreign/'helper.ipk').exists())
        self.reboot();self.assertTrue(self.remove()['verified_clean']);self.assertEqual((foreign/'notes.txt').read_text(),'owner file')

    @unittest.skipIf(getattr(os, 'getuid', lambda: -1)() == 0, 'unprivileged SDK model')
    def test_removal_finishes_when_only_temporary_ipks_cannot_be_deleted(self):
        (self.root / 'proc').mkdir()
        self.remote.apps = set(self.cleanup.APPS[:2])
        stage = self.root / 'developer/temp' / ('cytv-' + 'a' * 32)
        stage.mkdir(parents=True)
        ipk = stage / 'helper.ipk'
        ipk.write_bytes(package.ipk('com.local.nativehome', '0.7.4', {}, architecture='arm'))
        stage.chmod(0o555)
        self.addCleanup(stage.chmod, 0o755)

        result = self.remove()

        self.assertEqual(result, {'removed': True, 'verified_clean': True, 'temporary_files_retained': True})
        self.assertFalse(self.remote.apps)
        self.assertTrue(ipk.is_file())
        self.assertIsNone(self.store.pending(self.profile))
        receipt = json.loads((self.store.device_dir(self.profile) / 'clean-removal.json').read_text())
        self.assertEqual(receipt['result'], result)

    def test_directory_replacement_is_not_traversed_or_deleted(self):
        own=self.root/'developer/apps/usr/palm/applications/com.local.nativehome';(own/'child').mkdir(parents=True)
        foreign=self.root/'foreign';foreign.mkdir();(foreign/'valuable').write_text('preserve')
        replacement='if(item.isDirectory()){if(child==="child"){fs.renameSync("child",'+json.dumps(str(self.root/'old-child'))+');fs.renameSync('+json.dumps(str(foreign))+',"child");}walk'
        self.remote.transform=lambda code:code.replace('if(item.isDirectory()){walk',replacement)
        with self.assertRaises(UserError):self.remove()
        self.assertEqual((own/'child/valuable').read_text(),'preserve')

    def test_observed_homebrew_sender_blocks_sweep_after_it_exits_until_restart(self):
        (self.root / 'proc').mkdir()
        app = 'com.local.nativehome'
        self.remote.apps.add(app)
        residue = self.own_file('apps/usr/palm/applications/' + app + '/appinfo.json', json.dumps({'id': app}))
        process = self.root / 'proc/123'
        process.mkdir()
        (process / 'cmdline').write_bytes(
            b'/usr/bin/luna-send-pub\0-i\0luna://org.webosbrew.hbchannel.service/install\0'
            b'{"id":"com.local.nativehome"}\0')
        with self.assertRaises(UserError):
            self.remove()
        self.assertTrue(residue.exists())
        self.assertFalse(any(uri.endswith('/dev/remove') for uri, _ in self.remote.calls))
        shutil.rmtree(process)
        self.remote.cut = app
        original = self.remote.luna
        idle = False

        def luna(uri, payload, **kwargs):
            if uri.endswith('/status') and not idle:
                raise TVRejected('Denied', {'returnValue': False, 'errorCode': -1}, uri)
            return original(uri, payload, **kwargs)

        self.remote.luna = luna
        with self.assertRaises(UserError):
            self.remove()
        self.assertTrue(self.remove()['restart_required'])
        self.assertFalse(self.remote.apps)
        self.assertTrue(residue.exists())
        idle = True
        with self.assertRaises(UserError):
            self.remove()
        self.assertTrue(residue.exists())
        self.reboot()
        self.assertTrue(self.remove()['verified_clean'])
        self.assertFalse(residue.exists())

    def test_stale_updater_transaction_is_not_current_work(self):
        (self.root / 'proc').mkdir()
        record=self.own_file('apps/usr/palm/services/com.cleanyourtv.updater.service/state/transaction.json',json.dumps({'schema':1,'status':'installing'}))
        self.assertTrue(self.remove()['verified_clean'])
        self.assertFalse(record.exists())
        receipt=json.loads((self.store.device_dir(self.profile)/'clean-removal.json').read_text())
        self.assertEqual(receipt['previous_update_status'],'installing')

    def test_old_resident_installer_moves_restart_before_package_removal(self):
        source=self.own_file('.cytv-installer/operations/'+'a'*32+'/changed-private-data.json','old unknown data')
        self.remote.apps={'com.local.nativehome'}
        self.assertTrue(self.remove()['restart_required'])
        self.assertEqual(self.store.pending(self.profile)['cleanup_restart_triggers'], ['process-idle-unverified'])
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
    def test_unlisted_package_with_protected_registration_reports_partial_cleanup(self):
        from cytv import diagnostics

        self.removal_payload()
        app = 'com.local.nativehome'
        directory = self.root / 'bus/roles.d'
        directory.mkdir()
        role = directory / (app + '.service.json')
        role.write_text('{}')
        directory.chmod(0o555)
        self.addCleanup(directory.chmod, 0o755)

        with self.assertRaises(UserError) as caught:
            self.remove()

        self.assertEqual(caught.exception.reason_code, 'root-access-required')
        pending = self.store.pending(self.profile)
        self.assertEqual(pending['stage'], 'private-cleanup')
        self.assertEqual(pending['removal_reason'], 'root-access-required')
        self.assertTrue(role.exists())
        self.assertFalse(any(uri.endswith(('/dev/install', '/dev/remove')) for uri, _ in self.remote.calls))
        report = diagnostics.create_report(self.store, 'uninstall', self.profile, 'uninstall', caught.exception)
        details = {'action': 'sweep', 'blocked_areas': ['ls2-registration']}
        failure = json.loads(report.read_text())
        self.assertEqual(failure['no_root_cleanup'], details)
        self.assertEqual(failure['first_failure']['no_root_cleanup'], details)
        self.assertNotIn(role.name, json.dumps(failure))

    def legacy_paths(self):
        (self.root/'proc').mkdir()
        public = self.root/'legacy-bus/services/pub'
        public.mkdir(parents=True)
        self.addCleanup(lambda: public.chmod(0o755) if public.exists() else None)
        return public

    def legacy_package(self, metadata=None):
        app = self.cleanup.APPS[1]
        self.remote.os_cleanup = True
        self.remote.legacy_vendor.add(app)
        self.remote.sam = None
        public = self.legacy_paths()
        registration = public/'com.gathin.tvhome.renewal.service'
        registration.write_text('[D-BUS Service]\nName=com.gathin.tvhome.renewal\n'
                                'Exec=/usr/bin/run-js-service com.gathin.tvhome.renewal\n')
        public.chmod(0o555)
        source = self.own_file('apps/usr/palm/services/com.gathin.tvhome.renewal/service.js')
        source.parent.chmod(0o555)
        if metadata is not None:
            packageinfo = self.own_file('apps/usr/palm/packages/'+app+'/packageinfo.json',metadata)
            if metadata == 'unreadable':
                packageinfo.chmod(0)
        return app, source, registration

    def vendor_removals(self):
        return [body['id'] for uri, body in self.remote.calls if uri.endswith('/dev/remove')]

    @unittest.skipIf(getattr(os,'getuid',lambda:-1)()==0,'unprivileged SDK model')
    def test_legacy_omitted_target_uses_vendor_with_missing_or_inaccessible_optional_metadata(self):
        for metadata in (None, 'not json', 'unreadable'):
            with self.subTest(metadata=metadata):
                case = SimpleRemoval()
                case.setUp()
                try:
                    app, source, registration = case.legacy_package(metadata)
                    case.model_owners({source.parent:(0,0),source.parent.parent:(501,20)})
                    if metadata is None:
                        # The readable legacy registry is not needed for nomination.
                        registration.parent.chmod(0o755)
                        shutil.rmtree(registration.parent)
                        case.remote.leave_registration = True
                    role = case.root/'bus/roles.d'/(app+'.foreign.json')
                    role.parent.mkdir()
                    role.write_text('preserve')
                    result = case.remove()
                    self.assertTrue(result['verified_clean'])
                    self.assertEqual(case.vendor_removals(),[app])
                    self.assertFalse(source.exists())
                    self.assertFalse(registration.exists())
                    self.assertEqual(role.read_text(),'preserve')
                    self.assertEqual(result.get('legacy_registrations_unverified',False),metadata is not None)
                finally:
                    case.doCleanups()

    @unittest.skipIf(getattr(os,'getuid',lambda:-1)()==0,'unprivileged SDK model')
    def test_legacy_terminal_does_not_certify_visible_executable_or_registration_remnants(self):
        for remaining in ('executable','registration'):
            with self.subTest(remaining=remaining):
                case = SimpleRemoval()
                case.setUp()
                try:
                    app, source, registration = case.legacy_package()
                    case.remote.leave_executable = remaining == 'executable'
                    case.remote.leave_registration = remaining == 'registration'
                    with self.assertRaises(UserError) as caught:
                        case.remove()
                    pending = case.store.pending(case.profile)
                    self.assertEqual(pending['removals'],{app:'terminal'})
                    self.assertEqual(caught.exception.reason_code,'cleanup-check-failed')
                    self.assertEqual(caught.exception.no_root_cleanup['blocked_areas'],
                                     ['service' if remaining == 'executable' else 'ls2-registration'])
                    self.assertTrue((source if remaining == 'executable' else registration).exists())
                finally:
                    case.doCleanups()

    def test_legacy_vendor_rejection_keeps_the_actual_failure(self):
        app, source, _ = self.legacy_package()
        independent = self.cleanup.APPS[2]
        self.remote.apps.add(independent)
        self.remote.reject = {'returnValue':False,'errorCode':-102}
        with self.assertRaises(TVRejected) as caught:
            self.remove()
        self.assertEqual(caught.exception.reason_code,'removal-failed')
        self.assertEqual(self.vendor_removals(),[app,independent])
        self.assertEqual(self.store.pending(self.profile)['removals'],{independent:'terminal'})
        self.assertTrue(source.exists())
        self.assertTrue(self.remove()['verified_clean'])
        self.assertEqual(self.vendor_removals(),[app,independent,app])

    @unittest.skipIf(getattr(os,'getuid',lambda:-1)()==0,'unprivileged SDK model')
    def test_unsearchable_legacy_parent_never_nominates_a_target_or_verifies_absence(self):
        self.legacy_paths()
        for real_leaf in (False, True):
            with self.subTest(real_leaf=real_leaf):
                apps = self.root/'developer/apps/usr/palm/applications'
                apps.mkdir(parents=True,exist_ok=True)
                if real_leaf:
                    (apps/self.cleanup.APPS[1]).mkdir()
                apps.chmod(0)
                try:
                    with self.assertRaises(UserError) as caught:
                        self.remove()
                    self.assertEqual(caught.exception.reason_code,'cleanup-check-failed')
                    self.assertEqual(self.vendor_removals(),[])
                    self.assertFalse(self.store.pending(self.profile).get('cleanup_boot_proof'))
                finally:
                    apps.chmod(0o755)

    def test_legacy_exact_sam_can_nominate_but_different_path_cannot(self):
        public = self.legacy_paths()
        app = self.cleanup.APPS[1]
        self.remote.legacy_vendor.add(app)
        info = {'id':app,'folderPath':'/usr/palm/applications/'+app}
        self.remote.sam[app] = {'returnValue':True,'appId':app,'appInfo':info}
        with self.assertRaises(UserError):
            self.remove()
        self.assertEqual(self.vendor_removals(),[])
        info['folderPath'] = '/media/developer/apps/usr/palm/applications/'+app
        self.assertTrue(self.remove()['verified_clean'])
        self.assertEqual(self.vendor_removals(),[app])
        self.assertTrue(public.exists())

    def test_previous_cleanup_package_is_removed_as_a_registered_app(self):
        app = 'com.local.nativehome'
        info = {'id': app, 'title': 'Clean Your TV cleanup', 'visible': False}
        self.own_file('apps/usr/palm/applications/' + app + '/appinfo.json', json.dumps(info))
        self.remote.apps.add(app)
        self.remote.os_cleanup = True
        self.store.request_clean_removal(self.profile)
        self.store.checkpoint(self.profile, cleanup_carriers={app: 'installed'})

        result = self.remove()
        if result['restart_required']:
            self.reboot()
            result = self.remove()

        self.assertTrue(result['verified_clean'])
        self.assertIsNone(self.store.pending(self.profile))
        self.assertEqual([(uri.rsplit('/', 1)[-1], body['id']) for uri, body in self.remote.calls
                          if uri.endswith(('/dev/install', '/dev/remove'))], [('remove', app)])

    def test_controller_stop_finishes_before_its_files_are_removed(self):
        native=self.own_file('apps/usr/palm/applications/com.local.nativehome/native.js',
            "var fs=require('fs'),p=__dirname+'/state/';fs.writeFileSync(p+'controller.pid',String(process.pid));"
            "setInterval(function(){if(fs.existsSync(p+'control.json')){setTimeout(function(){"
            "var proc=require('path').dirname(process.argv[2])+'/proc/'+process.pid;"
            "fs.writeFileSync(process.argv[2],'keys released');fs.unlinkSync(p+'controller.pid');"
            "fs.unlinkSync(proc+'/cmdline');fs.rmdirSync(proc);process.exit(0);},250);}},50);")
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
        self.assertTrue(self.remove()['verified_clean'])
        child.wait(timeout=3);self.assertEqual(released.read_text(),'keys released');self.assertFalse(native.exists())

    def test_unresponsive_controller_times_out_before_file_deletion(self):
        pid=self.own_file('apps/usr/palm/applications/com.local.nativehome/state/controller.pid',str(os.getpid()))
        proc=self.root/'proc'/str(os.getpid());proc.mkdir(parents=True);(proc/'cmdline').write_text(str(pid.parent.parent/'native.js')+'\0')
        self.remote.transform=lambda code:code.replace('Date.now()+8000','Date.now()+100')
        with self.assertRaisesRegex(UserError, 'process did not stop'):
            self.remove()
        self.assertTrue(pid.exists())
        self.assertFalse(self.boot_marker().exists())
        self.assertFalse(any(uri.endswith('/dev/remove') for uri, _ in self.remote.calls))
        pid.unlink();shutil.rmtree(proc);self.assertTrue(self.remove()['verified_clean'])

    def test_lost_rearm_create_reply_keeps_retry_seedable_without_adopting_a_mismatch(self):
        proc=self.root/'proc/123';proc.mkdir(parents=True)
        (proc/'cmdline').write_bytes(b'/usr/bin/node\0-e\0')
        self.remote.transform=lambda code:code.replace('Date.now()+8000','Date.now()+100')
        self.remove();marker=self.boot_marker()
        with marker.open('rb') as held_old_inode:
            marker.unlink()  # Keep the fixture inode distinct from the next marker.
            self.store.checkpoint(self.profile, cleanup_boot_verified=True)
            self.remote.cut_boot_create=True
            with self.assertRaisesRegex(UserError,'interrupted'):self.remove()
            self.assertTrue(marker.exists())
            self.assertTrue(self.remove()['restart_required'])
            self.assertTrue(proc.exists())
        shutil.rmtree(proc);marker.unlink();self.assertTrue(self.remove()['verified_clean'])

    def test_stale_pid_of_foreign_process_does_not_force_endless_restart(self):
        pid=self.own_file('apps/usr/palm/applications/com.local.nativehome/state/controller.pid',str(os.getpid()))
        proc=self.root/'proc'/str(os.getpid());proc.mkdir(parents=True);(proc/'cmdline').write_text('/usr/bin/foreign\0')
        self.assertTrue(self.remove()['verified_clean']);self.assertFalse(pid.exists())

    def test_legacy_writable_helper_state_is_stopped_and_removed(self):
        key=self.own_file('apps/usr/palm/applications/com.local.nativehome/state/ssap-key.json','private')
        key.parent.chmod(0o777)
        self.assertTrue(self.remove()['restart_required'])
        self.assertFalse(key.exists())
        self.reboot();self.assertTrue(self.remove()['verified_clean'])

    @unittest.skipIf(getattr(os,'getuid',lambda:-1)()==0,'unprivileged SDK permission model')
    def test_registered_packages_use_os_removal_for_protected_namespaces(self):
        self.remote.os_cleanup=True
        (self.root/'proc').mkdir()
        for kind,name,mode in [('applications','com.local.nativehome',0o555),
                               ('applications','com.local.nativehome',0o000),
                               ('applications','com.local.nativehome/state',0o555),
                               ('services','com.local.nativehome.service',0o000),
                               ('packages','com.local.nativehome',0o555)]:
            with self.subTest(kind=kind,mode=mode):
                self.store.begin(self.profile,'install');self.store.finish(self.profile)
                own=self.own_file('apps/usr/palm/'+kind+'/'+name+'/private.json','partial NoRoot data')
                directory=own.parent;directory.chmod(mode)
                self.addCleanup(lambda p=directory:p.chmod(0o755) if p.exists() else None)
                foreign=self.own_file('apps/usr/palm/'+kind+'/org.foreign/keep.json','preserve')
                self.remote.apps={'com.local.nativehome'}
                start=len(self.remote.calls)
                self.assertTrue(self.remove()['verified_clean'])
                self.assertFalse(directory.exists());self.assertEqual(foreign.read_text(),'preserve')
                calls=self.remote.calls[start:]
                self.assertEqual(sum(uri.endswith('/dev/install') for uri,_ in calls),0)
                self.assertEqual(sum(uri.endswith('/dev/remove') for uri,_ in calls),1)

    def test_legacy_state_symlink_does_not_write_into_foreign_directory(self):
        foreign=self.root/'foreign';foreign.mkdir();(foreign/'keep').write_text('preserve')
        app=self.root/'developer/apps/usr/palm/applications/com.local.nativehome';app.mkdir(parents=True)
        (app/'state').symlink_to(foreign,target_is_directory=True)
        with self.assertRaises(UserError):self.remove()
        self.assertEqual(sorted(p.name for p in foreign.iterdir()),['keep'])

    def test_cleanup_repairs_firmware_expanded_stop_without_clearing_latch(self):
        marker = self.own_file('apps/usr/palm/applications/com.local.nativehome/state/blocked', 'stopped')
        directory = marker.parent
        generation = directory / 'stop-generation'
        generation.write_text('I' + 'a' * 32)
        for path in (directory, marker, generation):
            os.chown(path, -1, os.getgid())
            path.chmod(0o777)
        original_inode = marker.stat().st_ino
        result = self.cleanup._device(self.installer, 'stop')
        self.assertEqual(result['blocked'], [])
        self.assertFalse(result['controller_running'])
        self.assertEqual(marker.stat().st_ino, original_inode)
        self.assertEqual(marker.read_text(), 'stopped')
        self.assertRegex(generation.read_text(), r'^S[a-f0-9]{32}$')
        self.assertEqual(generation.stat().st_mode & 0o777, 0o664)
        self.assertEqual(directory.stat().st_mode & 0o777, 0o770)

    def test_original_removal_finishes_after_firmware_expands_stop_on_cold_boot(self):
        app = 'com.local.nativehome'
        self.remote.apps = {app}
        self.remote.broken_service = True
        self.own_file('apps/usr/palm/services/' + app + '.service/service.js', 'published source')
        marker = self.own_file('apps/usr/palm/applications/' + app + '/state/blocked', 'stopped')
        self.seed_pending_restart()
        self.cleanup._device(self.installer, 'stop')
        self.assertIsNotNone(self.store.pending(self.profile))
        generation = marker.parent / 'stop-generation'
        for path in (marker.parent, marker, generation):
            os.chown(path, -1, os.getgid())
            path.chmod(0o777)
        self.reboot()
        self.assertTrue(self.remove()['verified_clean'])
        self.assertIsNone(self.store.pending(self.profile))
        self.assertFalse(marker.exists())
        self.assertEqual(sum(uri.endswith('/dev/remove') for uri, _ in self.remote.calls), 1)

    def test_cleanup_stop_always_advances_generation_even_with_existing_latch(self):
        marker=self.own_file('apps/usr/palm/applications/com.local.nativehome/state/blocked','stopped')
        self.cleanup._device(self.installer,'stop')
        generation=marker.parent/'stop-generation'
        self.assertTrue(generation.exists())
        first=generation.read_text()
        self.assertRegex(first,r'^S[a-f0-9]{32}$')
        self.cleanup._device(self.installer,'stop')
        self.assertNotEqual(generation.read_text(),first)
        self.assertEqual(marker.read_text(),'stopped')
