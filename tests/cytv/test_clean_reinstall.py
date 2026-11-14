"""Regression for verified clean removal followed by normal Root installation."""
import os
import unittest
from unittest.mock import Mock
from tests.cytv import test_operations
from cytv.errors import ExistingRoot

CLEAN={'state':'fresh','reason':'verified_removal','can_install':True,
       'can_maintain':False,'clean_removal_verified':True}

class CleanReinstallTests(unittest.TestCase):
    setUp=test_operations.OperationTests.setUp
    installer=test_operations.OperationTests.installer

    def fixture(self):
        remote=test_operations.Remote();run=remote.run
        remote.run=lambda command,**kw: 'CYTV_EXISTING_ROOT' if 'CYTV_EXISTING_ROOT' in command else ('{"stage":"cancellation-admitted"}' if 'deploy.json' in command else run(command,**kw))
        inst=self.installer(remote,'root');inst.root_installation=Mock(return_value=dict(CLEAN))
        return inst,remote

    def test_blocked_shared_inspection_has_fixed_error_not_key_error(self):
        inst,remote=self.fixture()
        del inst.root_installation
        inst.product_action=Mock(return_value={'state':'recovery_required','stage':'blocked'})
        from cytv.errors import UserError
        with self.assertRaises(UserError) as caught:inst.root_installation()
        self.assertEqual(caught.exception.reason_code,'root-operation-unconfirmed')

    def test_reinstalled_project_apps_explain_cleanup_without_retired_execution(self):
        inst,remote=self.fixture();del inst.root_installation
        inst.product_action=Mock(return_value={'state':'recovery_required','stage':'blocked','reason':'project-apps-remain'})
        inst.root_action=Mock(side_effect=AssertionError('retired driver'))
        from cytv.errors import UserError
        for operation in (inst.root_installation,inst.status,lambda:inst.preflight(install=True),inst.restore_device):
            with self.subTest(operation=operation),self.assertRaises(UserError) as caught:operation()
            self.assertEqual(caught.exception.reason_code,'project-apps-remain')
            self.assertIn('Uninstall Clean Your TV',str(caught.exception))
            self.assertIn('No-root Home and Helper',str(caught.exception))
            self.assertIn('back up',str(caught.exception))
            self.assertIsNone(self.store.pending(inst.profile))
        inst.root_action.assert_not_called()

    def test_stale_support_requests_restart_without_retired_restore(self):
        inst,remote=self.fixture();del inst.root_installation
        inst.product_action=Mock(return_value={'state':'recovery_required','stage':'blocked','reason':'restart-required'})
        inst.root_action=Mock(side_effect=AssertionError('retired driver'))
        from cytv.errors import UserError
        for operation in (lambda:inst.preflight(install=True),inst.restore_device):
            with self.subTest(operation=operation),self.assertRaises(UserError) as caught:operation()
            self.assertEqual(caught.exception.reason_code,'restart-required')
        inst.root_action.assert_not_called()

    def test_preflight_accepts_only_current_verified_clean_removal(self):
        inst,remote=self.fixture();inst.preflight(install=True,home_interfaces=True)
        self.assertIsNone(self.store.pending(inst.profile))
        inst.root_installation.return_value=dict(CLEAN,clean_removal_verified=False)
        with self.assertRaises(ExistingRoot):inst.preflight(install=True,home_interfaces=True)

    def native_fixture(self):
        from cytv.root_capabilities import NATIVE_HEADERS
        inst, remote = self.fixture()
        inst.manifest['root_backends'] = {'c1-native-gate': {'admission_schema': 3}}
        luna, run = remote.luna, remote.run
        elf = ('127 69 76 70 1 1 1 0 0 0 0 0 0 0 0 0 3 0 40 0 1 0 0 0 217 218 '
               '0 0 52 0 0 0 164 98 10 0 0 2 0 5 52 0 32 0 9 0 40 0 29 0 28 0')

        def read(uri, payload, **kwargs):
            if uri.endswith('/getProfiles'):
                return {'returnValue': False, 'errorCode': -1,
                        'errorText': 'Service does not exist: com.webos.service.systemprofile.'}
            if uri.endswith('/getSystemInfo') and 'modelName' in payload.get('keys', []):
                return {'returnValue': True, 'modelName': 'OLED55C1PUB',
                        'firmwareVersion': '03.50.25', 'sdkVersion': '6.3.0'}
            return luna(uri, payload, **kwargs)

        remote.luna = read
        remote.run = lambda command, **kw: (
            f'0 1 755 7582\n{elf}\nCYTV_HOME_ELF\n{elf}\n'
            if command == NATIVE_HEADERS else run(command, **kw))
        return inst, remote

    def test_native_beta_accepts_only_verified_clean_handoff_before_effects(self):
        inst,remote=self.native_fixture()
        inst.preflight(install=True, home_interfaces=True)
        inst.root_installation.assert_called_once_with(for_install=True)
        self.assertTrue(inst._native_clean_install)
        self.assertIsNone(self.store.pending(inst.profile))
        inst.root_installation.return_value=dict(CLEAN,clean_removal_verified=False)
        with self.assertRaises(ExistingRoot):inst.preflight(install=True, home_interfaces=True)

    def test_native_verified_clean_ownership_without_root_directory_still_hands_off(self):
        inst,remote=self.native_fixture()
        original=remote.run
        def run(command,**kwargs):
            if 'CYTV_EXISTING_ROOT' in command:
                return 'CYTV_EXISTING_ROOT' if '/var/lib/clean-your-tv-installation/operation.json' in command else ''
            return original(command,**kwargs)
        remote.run=run
        inst.preflight(install=True, home_interfaces=True)
        self.assertTrue(inst._native_clean_install)

    def test_unowned_foreign_cover_refuses_repeated_restore_before_receipt_or_staging(self):
        from cytv.errors import UserError
        from cytv.root_capabilities import NATIVE_HEADERS, NATIVE_HOME_MOUNT_PROBE
        inst, remote = self.fixture()
        shell = ('127 69 76 70 1 1 1 0 0 0 0 0 0 0 0 0 3 0 40 0 1 0 0 0 217 218 '
                 '0 0 52 0 0 0 164 98 10 0 0 2 0 5 52 0 32 0 9 0 40 0 29 0 28 0')
        native = f'0 1 755 7582\n{shell}\nCYTV_HOME_ELF\n35 33\nCYTV_HOME_FS\nef53\n'
        calls = []

        def run(command, **kwargs):
            calls.append(command)
            if 'CYTV_ROOT_FOOTPRINT_ABSENT' in command:
                return 'CYTV_ROOT_FOOTPRINT_ABSENT'
            if command == NATIVE_HEADERS:
                return native
            if command == NATIVE_HOME_MOUNT_PROBE:
                return 'file-and-parent-mounts'
            self.fail('Unexpected TV command')

        remote.run = run
        for _ in range(2):
            with self.assertRaises(UserError) as caught:
                inst.restore()
            self.assertEqual(caught.exception.reason_code, 'foreign-home-handoff-required')
        self.assertEqual(calls[1:3], [NATIVE_HEADERS, NATIVE_HOME_MOUNT_PROBE])
        self.assertEqual(calls[:3], calls[3:])
        inst.root_installation.assert_not_called()
        self.assertIsNone(self.store.pending(inst.profile))
        self.assertEqual(list(self.store.device_dir(inst.profile).glob('recovery-*.json')), [])

        from cytv.diagnostics import create_report
        report_path = create_report(self.store, 'restore', inst.profile, 'restore', caught.exception, inst.tv_info)
        import json
        report = json.loads(report_path.read_text())
        self.assertEqual(report['phase'], 'restore')
        self.assertEqual(report['reason_code'], 'foreign-home-handoff-required')
        self.assertEqual(report['guidance']['code'], 'foreign-home-handoff-required')
        self.assertEqual(report['tv']['root_native_home_mount'], 'file-and-parent-mounts')
        self.assertNotIn('/usr/bin/com.webos.app.home', report_path.read_text())

    def test_unowned_restore_preserves_guard_failures_without_receipt(self):
        from cytv.errors import TVCommandError
        from cytv.root_capabilities import NATIVE_HEADERS, NATIVE_HOME_MOUNT_PROBE
        inst, remote = self.fixture()
        shell = ('127 69 76 70 1 1 1 0 0 0 0 0 0 0 0 0 3 0 40 0 1 0 0 0 217 218 '
                 '0 0 52 0 0 0 164 98 10 0 0 2 0 5 52 0 32 0 9 0 40 0 29 0 28 0')
        native = f'0 1 755 7582\n{shell}\nCYTV_HOME_ELF\n35 33\n'
        for index in range(3):
            for error in (TimeoutError('private'), TVCommandError(42 if index == 1 else 127)):
                with self.subTest(index=index, error=type(error)):
                    replies = ['CYTV_ROOT_FOOTPRINT_ABSENT', native][:index] + [error]
                    remote.run = Mock(side_effect=replies)
                    with self.assertRaises(type(error)) as caught:
                        inst.restore()
                    self.assertIs(caught.exception, error)
                    self.assertEqual(remote.run.call_count, index + 1)
                    self.assertIsNone(self.store.pending(inst.profile))
                    self.assertFalse(list(self.store.device_dir(inst.profile).glob('recovery-*.json')))
                    inst.root_installation.assert_not_called()
                    if index:
                        self.assertIn(remote.run.call_args.args[0], (NATIVE_HEADERS, NATIVE_HOME_MOUNT_PROBE))

    def test_possible_root_footprint_and_malformed_evidence_keep_authenticated_restore(self):
        inst, remote = self.fixture()
        for footprint in ('CYTV_ROOT_FOOTPRINT_RETAINED', 'CYTV_ROOT_FOOTPRINT_UNCERTAIN',
                          '', 'CYTV_ROOT_FOOTPRINT_ABSENT\nprivate'):
            with self.subTest(footprint=footprint):
                remote.run = Mock(return_value=footprint)
                self.assertTrue(inst.restore()['already_removed'])
                self.assertEqual(remote.run.call_count, 1)
        self.assertEqual(inst.root_installation.call_count, 4)

    def test_local_recovery_evidence_preserves_existing_restore(self):
        inst, remote = self.fixture()
        remote.run = Mock(side_effect=AssertionError('No fresh footprint probe'))
        directory = self.store.device_dir(inst.profile)
        for name in ('installation.json', 'clean-removal.json', 'recovery-local.json'):
            with self.subTest(name=name):
                receipt = directory / name
                receipt.write_text('{"action":"restore","stage":"pending"}')
                self.assertTrue(inst.restore()['already_removed'])
                receipt.unlink()
        self.store.begin(inst.profile, 'activate-root')
        self.assertTrue(inst.restore()['already_removed'])
        self.assertIsNone(self.store.pending(inst.profile))

    @unittest.skipUnless(os.name == 'posix', 'POSIX TV filesystem paths')
    def test_footprint_script_distinguishes_missing_from_indirect_or_unreadable_paths(self):
        import json
        from pathlib import Path
        import shutil
        import subprocess
        import tempfile
        from cytv.root_restore_footprint import _FOOTPRINT_SCRIPT, _ROOT_MARKERS

        node = shutil.which('node')
        if node is None:
            self.skipTest('Node unavailable')
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp).resolve()
            target = directory / 'profile' / 'override' / 'clean-your-tv-root.json'

            def probe(prefix=''):
                return subprocess.check_output(
                    [node, '-e', prefix + _FOOTPRINT_SCRIPT, json.dumps([str(target)])],
                    text=True, timeout=5)

            self.assertIn('/var/webos-profile/override/clean-your-tv-root.json', _ROOT_MARKERS)
            self.assertEqual(probe(), 'CYTV_ROOT_FOOTPRINT_ABSENT')
            target.parent.mkdir(parents=True)
            self.assertEqual(probe(), 'CYTV_ROOT_FOOTPRINT_ABSENT')
            target.touch()
            self.assertEqual(probe(), 'CYTV_ROOT_FOOTPRINT_RETAINED')
            target.unlink()
            target.parent.rmdir()
            target.parent.symlink_to(directory, target_is_directory=True)
            self.assertEqual(probe(), 'CYTV_ROOT_FOOTPRINT_UNCERTAIN')
            target.parent.unlink()
            target.parent.touch()
            self.assertEqual(probe(), 'CYTV_ROOT_FOOTPRINT_UNCERTAIN')
            deny = """
var lstat = require('fs').lstatSync;
require('fs').lstatSync = function (path) {
    if (path.endsWith('/profile')) throw Object.assign(Error('private'), {code: 'EACCES'});
    return lstat(path);
};
"""
            self.assertEqual(probe(deny), 'CYTV_ROOT_FOOTPRINT_UNCERTAIN')
            target.parent.unlink()
            change = """
var lstat = require('fs').lstatSync, visits = 0;
require('fs').lstatSync = function (path) {
    var result = lstat(path);
    if (path.endsWith('/profile')) return {ino: visits++, dev: result.dev, isDirectory: () => true};
    return result;
};
"""
            self.assertEqual(probe(change), 'CYTV_ROOT_FOOTPRINT_RETAINED')

    def test_unverified_clean_restore_keeps_existing_recovery_path(self):
        inst,remote=self.fixture()
        inst.root_installation.return_value=dict(CLEAN,clean_removal_verified=False)
        inst.root_action=Mock(return_value={'restored':True})
        self.assertEqual(inst.restore_device(),{'restored':True})
        inst.root_action.assert_called_once_with('restore')

    def test_status_and_restore_do_not_execute_retired_driver(self):
        inst,remote=self.fixture();inst.root_action=Mock(side_effect=AssertionError('retired driver'))
        self.assertEqual(inst.status()['deployment_stage'],'verified-clean')
        self.assertTrue(inst.restore_device()['already_removed'])
        inst.root_action.assert_not_called()

class RootInventoryTests(unittest.TestCase):
    def fixture(self, result):
        import tempfile,json
        from pathlib import Path
        from cytv.operations import Installer
        from cytv.state import Store,target
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        remote=Mock();remote.run.return_value=json.dumps(result+[{}] if isinstance(result,list) and len(result)==2 else result)
        from types import SimpleNamespace
        remote.channel.side_effect=lambda command:SimpleNamespace(command=command,close=lambda:None)
        remote.chunks.side_effect=lambda channel,timeout:[json.dumps({'returnValue':True,
            'apps':[{'id':'video','title':'Video'}]} if 'listApps' in channel.command else
            {'returnValue':True,'devices':[]}).encode()]
        inst=Installer(remote,Store(t.name),target('192.0.2.10','root'),Path(t.name),{})
        inst.coordinator_code=Mock(return_value='/tmp/cytv-coordinator-'+'a'*32)
        return inst,remote

    def test_root_reads_current_fixed_catalog_and_inputs_without_ssap(self):
        app={'id':'video','title':'Video','icon':'','iconColor':'red','hidden':False}
        inst,remote=self.fixture([[app,dict(app,title='duplicate'),dict(app,id='hidden',hidden=True)],{'returnValue':True,'devices':[{'appId':'hdmi','label':'HDMI'}]}])
        result=inst.root_inventory(b'fallback')
        self.assertEqual(len(result['apps']),1)
        self.assertTrue(result['apps'][0]['icon'].startswith('data:image/png;base64,'))
        self.assertEqual(result['inputs'],[{'appId':'hdmi','label':'HDMI'}]);self.assertNotIn('iconColor',result['apps'][0])
        self.assertEqual(remote.run.call_args.args[0],'/usr/bin/node')
        self.assertIn(b'/app-inventory.js',remote.run.call_args.kwargs['data'])
        self.assertIsNone(inst.store.pending(inst.profile))

    def test_invalid_input_envelope_does_not_misclassify_unchecked_apps(self):
        from cytv.errors import UserError
        inst,remote=self.fixture([[{'id':'video','title':'Video'}],{'returnValue':False}])
        with self.assertRaises(UserError):inst.root_inventory(b'fallback')
        self.assertEqual(inst.tv_info.get('root_inventory'),{'applications':'unknown','inputs':'invalid'})
        self.assertIsNone(inst.store.pending(inst.profile))

    def test_invalid_or_empty_root_catalog_stops_before_install(self):
        for result in [[],[[],{'returnValue':True,'devices':[]}],[[{'id':None,'title':'bad'}],{'returnValue':True,'devices':[]}],[[],{'returnValue':False}]]:
            inst,remote=self.fixture(result)
            with self.subTest(result=result),self.assertRaises((ValueError,RuntimeError)):inst.root_inventory(b'fallback')
            self.assertIsNone(inst.store.pending(inst.profile))

class RootInventoryRuntimeTests(unittest.TestCase):
    """Execute the real reader with Node subprocess loading forbidden; fake SSH I/O."""
    fixture=RootInventoryTests.fixture

    def runtime(self, apps, inputs, icon=None):
        import json,subprocess,shlex
        from pathlib import Path
        from types import SimpleNamespace
        from cytv.errors import TVCommandError,UserError
        inst,remote=self.fixture(None)
        stage=inst.payload
        reader=Path(__file__).resolve().parents[2]/'root-edition/service/app-inventory.js'
        (stage/'app-inventory.js').write_text(
            'var reader=require('+json.dumps(str(reader))+');\n'
            "module.exports=function(exec){return reader(exec,function(){return 0;});};"
            "module.exports.inputs=function(exec){return reader.inputs(exec,function(){return 0;});};")
        inst.coordinator_code.return_value=str(stage)
        replies={'luna://com.webos.applicationManager/listApps':apps,
                 'luna://com.webos.service.eim/getAllInputStatus':inputs}
        channels=[]
        def channel(command):
            args=shlex.split(command)
            self.assertEqual(args[:5],['/usr/bin/luna-send','-n','1','-w','8000'])
            self.assertEqual(args[6:],[ '{}'])
            self.assertIn(args[5],replies)
            current=SimpleNamespace(uri=args[5],closed=False)
            current.close=lambda:setattr(current,'closed',True)
            current.shutdown_write=lambda:self.fail('EOF sent before Luna reply')
            channels.append(current)
            return current
        def chunks(current,timeout):
            self.assertEqual(timeout,8)
            reply=replies[current.uri]
            if reply=='timeout':raise UserError('PRIVATE TIMEOUT',reason_code='operation-timeout')
            if reply=='disconnect':raise UserError('PRIVATE CONNECTION',reason_code='connection-interrupted')
            if reply=='missing-client':raise TVCommandError(127)
            if reply=='denied-client':raise TVCommandError(126)
            if reply=='oversized':yield b' '*(1048577 if 'listApps' in current.uri else 262145)
            elif reply=='malformed':yield b'PRIVATE INVALID JSON'
            elif reply in ('trailing','second-reply','truncated-utf8','oversized-tail','late-exit'):
                yield b'{"returnValue":true,"apps":[{"id":"video","title":"Video"}]}'
                if reply=='trailing':yield b'PRIVATE INVALID TAIL'
                elif reply=='second-reply':yield b'{}'
                elif reply=='truncated-utf8':yield b'\xe2'
                elif reply=='late-exit':raise TVCommandError(1)
                else:yield b' '*(1024*1024)
            else:
                raw=json.dumps(reply,ensure_ascii=False).encode()
                for offset in range(0,len(raw),7):yield raw[offset:offset+7]
        remote.channel.side_effect=channel
        remote.chunks.side_effect=chunks
        remote.catalog_channels=channels
        self.addCleanup(lambda:self.assertTrue(all(channel.closed for channel in channels)))
        def run(command,*,data,timeout):
            self.assertEqual(command,'/usr/bin/node')
            guard=("var Module=require('module'),load=Module._load;"
                   "Module._load=function(name){if(name==='child_process')throw Error('Forbidden child_process');"
                   "var loaded=load.apply(this,arguments);"
                   "return name==='path'?loaded.posix:loaded;};\n").encode()
            if icon is not None:
                guard+=("var originalLoad=Module._load;Module._load=function(name){"
                    "if(name==='fs')return {realpathSync:function(file){return file;},"
                    "statSync:function(){return {isFile:function(){return true;},size:"+str(len(icon))+"};},"
                    "readFileSync:function(){return Buffer.from("+json.dumps(icon.hex())+",'hex');}};"
                    "return originalLoad.apply(this,arguments);};\n").encode()
            reply=subprocess.run(['node'],input=guard+data,capture_output=True,timeout=timeout)
            if reply.returncode:raise TVCommandError(reply.returncode)
            return reply.stdout.decode()
        remote.run.side_effect=run
        messages=[];inst.progress=messages.append
        return inst,messages

    def test_unavailable_inputs_do_not_block_valid_applications(self):
        from cytv import diagnostics
        apps={'returnValue':True,'apps':[{'id':'video','title':'Video'}]}
        for inputs in ({'returnValue':False,'errorCode':-1,'errorText':'PRIVATE'},
                       {'returnValue':True,'devices':[None]},'timeout','malformed','oversized'):
            with self.subTest(inputs=inputs):
                inst,messages=self.runtime(apps,inputs)
                try:result=inst.root_inventory(b'fallback')
                except RuntimeError as error:self.fail('Unavailable inputs blocked valid applications: '+str(error))
                self.assertEqual([app['id'] for app in result['apps']],['video'])
                self.assertEqual(result['inputs'],[])
                self.assertIn('Warning: TV inputs could not be read. Continuing with applications only.',messages)
                report=diagnostics.context.tv_summary(inst.tv_info)
                self.assertEqual(report['root_inventory'],{'applications':'read','inputs':'unavailable'})
                self.assertNotIn('PRIVATE',str(report)+str(messages))
                self.assertIsNone(inst.store.pending(inst.profile))

    def test_failed_application_query_still_blocks_installation(self):
        from cytv.errors import UserError
        inst,messages=self.runtime({'returnValue':False,'errorText':'PRIVATE'},
                                   {'returnValue':True,'devices':[]})
        with self.assertRaises(UserError) as caught:inst.root_inventory(b'fallback')
        self.assertEqual(caught.exception.reason_code,'inventory-unavailable')
        self.assertEqual(inst.tv_info.get('root_inventory'),{'applications':'unavailable','inputs':'read'})
        self.assertEqual(messages,[])
        self.assertIsNone(inst.store.pending(inst.profile))

    def test_input_fallback_cannot_hide_missing_or_invalid_apps(self):
        from cytv.errors import UserError
        for apps,expected in [({'returnValue':False},'unavailable'),
                              ({'returnValue':True,'apps':[]},'invalid'),
                              ({'returnValue':True,'apps':[{'id':None,'title':'Bad'}]},'invalid')]:
            with self.subTest(apps=apps):
                inst,messages=self.runtime(apps,{'returnValue':False})
                with self.assertRaises(UserError):inst.root_inventory(b'fallback')
                self.assertEqual(inst.tv_info.get('root_inventory'),{'applications':expected,'inputs':'unavailable'})
                self.assertEqual(messages,[])
                self.assertIsNone(inst.store.pending(inst.profile))

    def test_failed_queries_export_bounded_independent_causes(self):
        from cytv import diagnostics
        from cytv.errors import UserError
        cases=[
            ({'returnValue':False,'errorCode':-1,'errorText':'Permission denied PRIVATE'},
             {'reason':'permission-denied','error_code':-1}),
            ({'returnValue':False,'errorCode':-1,'errorText':'Service does not exist: PRIVATE'},
             {'reason':'service-missing','error_code':-1}),
            ({'returnValue':False,'errorCode':-1,'errorText':'Unknown method PRIVATE'},
             {'reason':'method-missing','error_code':-1}),
            ({'returnValue':False,'errorCode':True,'errorText':'PRIVATE'},
             {'reason':'negative-reply'}),
            ({'returnValue':True,'apps':None},{'reason':'malformed-reply'}),
            ('timeout',{'reason':'timeout'}),
            ('malformed',{'reason':'malformed-reply'}),
            ('oversized',{'reason':'oversized-reply'}),
            ('missing-client',{'reason':'client-start-failed'}),
            ('denied-client',{'reason':'client-start-failed'})]
        for apps,expected in cases:
            with self.subTest(expected=expected):
                inst,messages=self.runtime(apps,'timeout')
                with self.assertRaises(UserError) as caught:inst.root_inventory(b'fallback')
                self.assertEqual(caught.exception.reason_code,'inventory-unavailable')
                report=diagnostics.context.tv_summary(inst.tv_info)
                self.assertEqual(report.get('root_inventory_failures'),
                    {'applications':expected,'inputs':{'reason':'timeout'}})
                self.assertNotIn('PRIVATE',str(report)+str(messages))
                self.assertIsNone(inst.store.pending(inst.profile))

    def test_successful_input_snapshot_is_preserved(self):
        inst,messages=self.runtime({'returnValue':True,'apps':[{'id':'video','title':'Video'}]},
            {'returnValue':True,'devices':[{'appId':'hdmi','label':'HDMI 1'}]})
        result=inst.root_inventory(b'fallback')
        self.assertEqual(result['inputs'],[{'appId':'hdmi','label':'HDMI 1'}])
        self.assertEqual(inst.tv_info.get('root_inventory'),{'applications':'read','inputs':'read'})
        self.assertEqual(messages,[])
        self.assertEqual(len(inst.remote.catalog_channels),2)

    def test_connection_loss_during_optional_input_read_is_fatal(self):
        from cytv.errors import UserError
        inst,messages=self.runtime({'returnValue':True,'apps':[{'id':'video','title':'Video'}]},'disconnect')
        with self.assertRaises(UserError) as caught:inst.root_inventory(b'fallback')
        self.assertEqual(caught.exception.reason_code,'connection-interrupted')
        self.assertEqual(messages,[])

    def test_direct_reply_keeps_original_icon_and_metadata(self):
        import base64
        icon=bytes.fromhex('89504e470d0a1a0a0000000000000000')
        inst,messages=self.runtime({'returnValue':True,'apps':[{
            'id':'video','title':'Video','folderPath':'/usr/palm/applications/video',
            'extraLargeIcon':'icon.png','iconColor':'#123456'}]},
            {'returnValue':True,'devices':[]},icon=icon)
        result=inst.root_inventory(b'fallback')
        self.assertEqual(result['apps'],[{'id':'video','title':'Video','iconColor':'#123456',
            'icon':'data:image/png;base64,'+base64.b64encode(icon).decode()}])

    def test_captured_reply_is_data_even_with_script_like_titles(self):
        title='Video 雪\u2028";require("child_process"); //'
        inst,messages=self.runtime({'returnValue':True,'apps':[{'id':'video','title':title}]},
                                   {'returnValue':True,'devices':[]})
        result=inst.root_inventory(b'fallback')
        self.assertEqual(result['apps'][0]['title'],title)

    def test_valid_prefix_cannot_hide_trailing_or_failed_response(self):
        from cytv.errors import UserError
        for mode,reason in [('trailing','malformed-reply'),('second-reply','malformed-reply'),
                            ('truncated-utf8','malformed-reply'),('oversized-tail','oversized-reply'),
                            ('late-exit','client-error')]:
            with self.subTest(mode=mode):
                inst,messages=self.runtime(mode,{'returnValue':True,'devices':[]})
                with self.assertRaises(UserError):inst.root_inventory(b'fallback')
                self.assertEqual(inst.tv_info.get('root_inventory_failures'),{'applications':{'reason':reason}})
                self.assertEqual(messages,[])

class RootInventoryCheckTests(unittest.TestCase):
    def test_unavailable_input_read_is_not_displayed_as_passed(self):
        import tempfile
        from unittest.mock import patch,MagicMock
        from pathlib import Path
        from cytv import cli
        from cytv.desktop import DesktopConsole
        for inputs,expected in [('read','pass'),('unavailable','unknown')]:
            with self.subTest(inputs=inputs),tempfile.TemporaryDirectory() as tmp, \
                    patch('cytv.cli.payload_dir',return_value=Path(tmp)), \
                    patch('cytv.cli.Installer') as cls, \
                    patch('cytv.cli.package.verify_payload',return_value={}):
                (Path(tmp)/'fallback.png').write_bytes(b'fallback')
                cls.return_value.tv_info={'root_inventory':{'applications':'read','inputs':inputs}}
                cls.return_value.root_inventory.return_value={'apps':[{'id':'video','title':'Video'}],'inputs':[]}
                events=[]
                code=cli.main(['install','--host','192.0.2.10','--edition','root','--data-dir',tmp,
                               '--yes','--language','en'],connect=lambda *a:MagicMock(),
                              ask=lambda _: '{}', write=DesktopConsole(lambda kind,value:events.append((kind,value))))
                self.assertEqual(code,0,str(events))
                rows=[value for kind,value in events if kind=='check' and value['id']=='inventory']
                self.assertEqual(rows[-1]['status'],expected)

class RootInventoryCLITests(unittest.TestCase):
    def test_root_install_uses_ssh_catalog_without_ssap_pairing(self):
        import tempfile
        from tests.cytv.test_cli import CLITests
        from unittest.mock import patch,MagicMock
        from pathlib import Path
        inventory={'apps':[{'id':'video','title':'Video'}],'inputs':[]}
        with tempfile.TemporaryDirectory() as tmp,patch('cytv.cli.payload_dir',return_value=Path(tmp)),patch('cytv.cli.Installer') as cls,patch('cytv.cli.package.verify_payload',return_value={}),patch('cytv.tv.SSAP') as ssap:
            (Path(tmp)/'fallback.png').write_bytes(b'fallback')
            cls.return_value.root_inventory.return_value=inventory
            code,output,_=CLITests.run_cli(self,['install','--host','192.0.2.10','--edition','root','--data-dir',tmp,'--yes'],remote=MagicMock())
            self.assertEqual(code,0,output);ssap.assert_not_called()
            cls.return_value.install.assert_called_once_with(inventory,None,False)

if __name__=='__main__':unittest.main()
