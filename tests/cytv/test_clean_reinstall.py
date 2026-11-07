"""Regression for verified clean removal followed by normal Root installation."""
import unittest
from unittest.mock import Mock
from tests.cytv import test_operations
from cytv.errors import ExistingRoot

CLEAN={'state':'fresh','reason':'verified_removal','can_install':True,
       'can_maintain':False,'clean_removal_verified':True}

class CleanReinstallTests(unittest.TestCase):
    setUp=test_operations.OperationTests.setUp
    installer=test_operations.OperationTests.installer
    root_bundle=test_operations.OperationTests.root_bundle

    def fixture(self):
        self.root_bundle();remote=test_operations.Remote();run=remote.run
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

    def test_native_beta_keeps_fresh_only_guard_before_effects(self):
        inst,remote=self.fixture();inst.tv_info['home_backend']='c1-native-gate'
        with self.assertRaises(ExistingRoot):inst.preflight(install=True)
        self.assertIsNone(self.store.pending(inst.profile))

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
        remote=Mock();remote.run.return_value=json.dumps(result)
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
    """Run the installer's actual Node program and reader; fake only Luna I/O."""
    fixture=RootInventoryTests.fixture

    def runtime(self, apps, inputs):
        import json,subprocess
        from pathlib import Path
        from cytv.errors import TVCommandError
        inst,remote=self.fixture(None)
        stage=inst.payload
        reader=Path(__file__).resolve().parents[2]/'root-edition/service/app-inventory.js'
        (stage/'app-inventory.js').write_text(
            'var reader=require('+json.dumps(str(reader))+');\n'
            'var replies='+json.dumps({'apps':apps,'inputs':inputs})+';\n'
            "function exec(file,args,options,cb){"
            "if(file!=='/usr/bin/luna-send'||args[0]!=='-n'||args[1]!=='1'||args[3]!=='{}')throw Error('Unexpected command');"
            "var kind=args[2]==='luna://com.webos.applicationManager/listApps'?'apps':"
            "args[2]==='luna://com.webos.service.eim/getAllInputStatus'?'inputs':null;"
            "if(!kind)throw Error('Unexpected URI');"
            "setImmediate(function(){var reply=replies[kind];"
            "if(reply==='timeout')cb(Error('PRIVATE TIMEOUT'),'', 'PRIVATE STDERR');"
            "else cb(null,JSON.stringify(reply));});}\n"
            "module.exports=function(){return reader(exec,function(){return 0;});};"
            "module.exports.inputs=function(){return reader.inputs(exec,function(){return 0;});};")
        inst.coordinator_code.return_value=str(stage)
        def run(command,*,data,timeout):
            self.assertEqual(command,'/usr/bin/node')
            reply=subprocess.run(['node'],input=data,capture_output=True,timeout=timeout)
            if reply.returncode:raise TVCommandError(reply.returncode)
            return reply.stdout.decode()
        remote.run.side_effect=run
        messages=[];inst.progress=messages.append
        return inst,messages

    def test_unavailable_inputs_do_not_block_valid_applications(self):
        from cytv import diagnostics
        apps={'returnValue':True,'apps':[{'id':'video','title':'Video'}]}
        for inputs in ({'returnValue':False,'errorCode':-1,'errorText':'PRIVATE'},
                       {'returnValue':True,'devices':[None]},'timeout'):
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

    def test_successful_input_snapshot_is_preserved(self):
        inst,messages=self.runtime({'returnValue':True,'apps':[{'id':'video','title':'Video'}]},
            {'returnValue':True,'devices':[{'appId':'hdmi','label':'HDMI 1'}]})
        result=inst.root_inventory(b'fallback')
        self.assertEqual(result['inputs'],[{'appId':'hdmi','label':'HDMI 1'}])
        self.assertEqual(inst.tv_info.get('root_inventory'),{'applications':'read','inputs':'read'})
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
                              write=DesktopConsole(lambda kind,value:events.append((kind,value))))
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
