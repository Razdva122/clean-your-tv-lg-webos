"""Host preflight uses the retained Root read contract, not model guesses."""
import ast
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from cytv import state
from cytv.checks import CheckList

SETTINGS={'returnValue':True,'settings':{'defaultApps':{}}}
PROFILES={'returnValue':True,'profiles':{'defaultApps':{'categories':{'home':'com.webos.app.home'}},
          'idleApp':{'appId':'com.webos.app.home','support':False}}}


class CapabilityTests(unittest.TestCase):
    def verify(self, settings=SETTINGS, profiles=PROFILES):
        from cytv.root_capabilities import verify
        remote=Mock();remote.luna.side_effect=[copy.deepcopy(settings),copy.deepcopy(profiles)]
        info={};checks=CheckList()
        verify(remote, checks, info)
        return remote,checks,info

    def test_absent_settings_override_and_false_support_match_runtime_contract(self):
        remote, checks, info=self.verify()
        self.assertEqual([x['status'] for x in checks.results.values()],['pass','pass'])
        self.assertEqual(info['root_capabilities'],{'home-settings':'readable','home-profiles':'readable'})
        self.assertTrue(all(c.kwargs['timeout']==5 for c in remote.luna.call_args_list))
        self.assertNotIn('com.webos.app.home', str(info))

    def test_invalid_readback_is_not_a_capability(self):
        from cytv.errors import UserError
        for settings, profiles in [({},PROFILES),(SETTINGS,{}),
            ({'returnValue':False,'settings':{'defaultApps':{}}},PROFILES),
            (SETTINGS,{'returnValue':True,'profiles':{'defaultApps':{'categories':{'home':' ' }},'idleApp':{'appId':'com.webos.app.home','support':True}}})]:
            with self.subTest(settings=settings,profiles=profiles),self.assertRaises(UserError):self.verify(settings,profiles)

    def test_denied_timedout_and_malformed_calls_keep_fixed_reasons_only(self):
        from cytv.root_capabilities import verify
        from cytv.errors import TVRejected, UserError
        for error,reason in [(TVRejected('PRIVATE-KEY',{'errorCode':-1}),'rejected'),
                             (TimeoutError('PRIVATE-IP'),'unconfirmed')]:
            remote=Mock();remote.luna.side_effect=[error,copy.deepcopy(PROFILES)]
            info={};checks=CheckList()
            with self.assertRaises(UserError):verify(remote,checks,info)
            self.assertEqual(info['root_capabilities']['home-settings'],reason)
            self.assertEqual(checks.results['home-profiles']['status'],'pass')
            self.assertNotIn('PRIVATE',str(info))

    def test_error_codes_are_retained_but_routes_and_untrusted_fields_are_not_exported(self):
        from cytv.root_capabilities import verify
        from cytv.diagnostic_context import tv_summary
        from cytv.errors import TVRejected, UserError
        remote=Mock();remote.luna.side_effect=[TVRejected('PRIVATE',{'returnValue':False,'errorCode':-1}),copy.deepcopy(PROFILES)]
        info={}
        with self.assertRaises(UserError):verify(remote,CheckList(),info)
        self.assertEqual(tv_summary(info)['root_capability_codes'],{'home-settings':-1})
        info['root_capability_codes'].update({'home-profiles':True,'PRIVATE':123})
        self.assertEqual(tv_summary(info)['root_capability_codes'],{'home-settings':-1})
        self.assertNotIn('PRIVATE',str(tv_summary(info)))

    def test_queries_and_validation_stay_aligned_with_current_root_contract(self):
        from cytv.root_capabilities import CALLS
        tree=ast.parse((Path(__file__).resolve().parents[2]/'root-edition/provision.py').read_text())
        rpc=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='rpc')
        calls=next(ast.literal_eval(n.value) for n in rpc.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='home_calls' for x in n.targets))
        self.assertEqual(CALLS['home-settings'],calls['home-read'])
        self.assertEqual(CALLS['home-profiles'],calls['home-profiles'])
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='require_home_interfaces')
        scope={'rpc':lambda method:copy.deepcopy(SETTINGS if method=='home-read' else PROFILES)}
        exec(compile(ast.Module(body=[function],type_ignores=[]),'root-home-contract','exec'),scope)
        scope['require_home_interfaces']()
        self.verify()

    def test_interface_failure_precedes_private_python_and_any_install_submission(self):
        from cytv.operations import Installer
        from tests.cytv.test_operations import Remote
        from cytv.errors import UserError
        class TV(Remote):
            def luna(self,uri,payload,**kwargs):
                if uri=='com.webos.service.systemprofile/getProfiles':
                    return {'returnValue':False,'errorCode':-1}
                if uri=='com.webos.settingsservice/getSystemSettings':return copy.deepcopy(SETTINGS)
                return super().luna(uri,payload,**kwargs)
        with tempfile.TemporaryDirectory() as tmp:
            remote=TV();profile=state.target('192.0.2.10','root');store=state.Store(tmp)
            inst=Installer(remote,store,profile,Path(tmp),{})
            with patch.object(inst,'_python',return_value='/usr/bin/python3'),patch.object(inst,'_select_python') as prepare:
                # Force only Python missing, which previously permitted provisioning.
                run=remote.run
                remote.run=lambda command,**kw:'CYTV_ROOT_MISSING' if 'CYTV_ROOT_READY' in command and '/usr/bin/python3' in command else run(command,**kw)
                with self.assertRaises(UserError):inst.preflight(install=True,home_interfaces=True)
                prepare.assert_not_called()
            self.assertIsNone(store.pending(profile))
            self.assertFalse(any(c[0]=='upload' for c in remote.calls))
            self.assertFalse(any(c[0]=='luna' and c[1].endswith(('/install','/launch')) for c in remote.calls))

    def test_reinstall_gate_precedes_removal_or_new_submission(self):
        from cytv.operations import Installer
        from tests.cytv.test_operations import Remote
        from cytv.errors import UserError
        remote=Remote();luna=remote.luna
        def reject(uri,payload,**kwargs):
            if uri=="com.webos.service.systemprofile/getProfiles":return {'returnValue':False}
            return luna(uri,payload,**kwargs)
        remote.luna=reject
        with tempfile.TemporaryDirectory() as tmp:
            profile=state.target('192.0.2.10','root');store=state.Store(tmp)
            inst=Installer(remote,store,profile,tmp,{})
            with patch.object(inst,'select_graphics'),patch.object(inst,'install_root') as submit:
                with self.assertRaises(UserError):inst.install({'apps':[{'id':'youtube','title':'YouTube','icon':'data:image/png;base64,AA=='}],'inputs':[]},reinstall='installed')
                submit.assert_not_called()
            self.assertIsNone(store.pending(profile))
            self.assertFalse(any(c[0]=='upload' for c in remote.calls))

    def test_default_maintenance_preflight_does_not_add_home_queries(self):
        from cytv.operations import Installer
        from tests.cytv.test_operations import Remote
        with tempfile.TemporaryDirectory() as tmp:
            remote=Remote();inst=Installer(remote,state.Store(tmp),state.target('192.0.2.10','root'),tmp,{})
            inst.preflight()
            self.assertFalse(any(c[0]=='luna' for c in remote.calls))

    def test_doctor_only_adds_home_queries_when_no_operation_is_pending(self):
        from cytv import cli
        for pending in (False,True):
            with self.subTest(pending=pending),tempfile.TemporaryDirectory() as tmp,patch('cytv.cli.Installer') as cls:
                profile=state.target('192.0.2.10','root');store=state.Store(tmp)
                if pending:store.begin(profile,'install')
                cls.return_value.status.return_value={}
                code=cli.main(['doctor','--host',profile['host'],'--edition','root','--data-dir',tmp],
                              connect=lambda *a:Mock(),write=lambda _:None)
                self.assertEqual(code,0)
                if pending:cls.return_value.preflight.assert_called_once_with()
                else:cls.return_value.preflight.assert_called_once_with(home_interfaces=True)
