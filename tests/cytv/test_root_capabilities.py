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
    def test_normal_and_beta_share_preflight_selection_and_refusal_before_python(self):
        import struct
        from cytv.operations import Installer
        from cytv.root_capabilities import NATIVE_HEADERS, RootCapabilityError
        from cytv.root_runtime import VENDOR_PROBE
        from tests.cytv.test_operations import Remote
        missing = {'returnValue':False,'errorCode':-1,'errorText':'Service does not exist: com.webos.service.systemprofile.'}
        header = struct.pack('<16sHHIIIIIHHHHHH', b'\x7fELF\x01\x01\x01', 3, 40, 1, 64, 52, 0, 0, 52, 32, 2, 0, 0, 0)
        dump = ' '.join(str(n) for n in header)
        observed = '0 1 755 50684\n'+dump+'\nCYTV_HOME_ELF\n'+dump
        chain = [{'file':'/usr/lib/qt5/qml/KeyFilters/systemUi.js','handler':'handleSystemKeys'}]
        for beta in (False, True):
            for case in ('profiles', 'keyfilters', 'sdk3', 'sdk5', 'denied', 'unknown-chain', 'missing-native'):
                with self.subTest(beta=beta,case=case), tempfile.TemporaryDirectory() as folder:
                    class TV(Remote):
                        prepared = False
                        def run(self, command, **kwargs):
                            if command == VENDOR_PROBE: return 'CYTV_VENDOR_READY'
                            if command == NATIVE_HEADERS: return '' if case=='missing-native' else observed
                            if 'CYTV_ROOT_READY' in command and '/usr/bin/python3' in command and not self.prepared:
                                return 'CYTV_ROOT_MISSING'
                            return super().run(command, **kwargs)
                        def luna(self, uri, payload, **kwargs):
                            if 'systemprofile' in uri:
                                return copy.deepcopy(PROFILES if case=='profiles' else dict(missing,errorText='Access denied') if case=='denied' else missing)
                            if 'getSystemInfo' in uri:
                                return dict(returnValue=True,modelName='55NANO77SRA',firmwareVersion='23.25.55',sdkVersion={'sdk3':'3.9.0','sdk5':'5.6.2'}.get(case,'9.2.2'))
                            if 'getConfigs' in uri:
                                return {'returnValue':True,'configs':{'com.webos.surfacemanager.keyFilters':[] if case=='unknown-chain' else chain}}
                            if 'getSystemSettings' in uri: return copy.deepcopy(SETTINGS)
                            return super().luna(uri,payload,**kwargs)
                    remote=TV();root=Path(folder)
                    profile=state.target('192.0.2.10','root',**({'root_variant':'node012-beta'} if beta else {}))
                    manifest={'root_backends':{'c1-native-gate':{'admission_schema':3}}}
                    with patch('cytv.root_runtime.select_payload',return_value=(root,manifest)):
                        installer=Installer(remote,state.Store(root/'host'),profile,root,manifest)
                    def provision(**kwargs):
                        self.assertEqual(kwargs,{'provision':True})
                        self.assertEqual(installer.tv_info['home_backend'],'system-profile' if case=='profiles' else 'c1-native-gate')
                        remote.prepared=True
                        return '/usr/bin/python3'
                    with patch.object(installer,'_python',return_value='/usr/bin/python3'), patch.object(installer,'_select_python',side_effect=provision) as prepare:
                        if case in ('profiles','keyfilters','sdk3','sdk5'):
                            installer.preflight(install=True,home_interfaces=True)
                            prepare.assert_called_once_with(provision=True)
                            if case!='profiles': self.assertEqual(installer.tv_info['home_backend_schema'],3)
                        else:
                            with self.assertRaises(RootCapabilityError):
                                installer.preflight(install=True,home_interfaces=True)
                            prepare.assert_not_called()
                    self.assertIsNone(installer.store.pending(profile))
                    self.assertEqual(remote.uploads,{})

    def test_generic_compositor_admission_is_capability_based_not_model_list(self):
        import struct
        from cytv.root_capabilities import verify
        missing = {'returnValue':False, 'errorCode':-1, 'errorText':'Service does not exist: com.webos.service.systemprofile.'}
        header = struct.pack('<16sHHIIIIIHHHHHH', b'\x7fELF\x01\x01\x01', 3, 40, 1, 64, 52, 0, 0, 52, 32, 2, 0, 0, 0)
        dump = ' '.join(str(n) for n in header)
        observed = '0 1 755 50684\n'+dump+'\nCYTV_HOME_ELF\n'+dump
        chain = [{'file':'/usr/lib/qt5/qml/KeyFilters/systemUi.js','handler':'handleSystemKeys'}]
        for model,sdk,firmware in (('55NANO77SRA','9.2.2','23.25.55'),('OLED55C37LA','8.3.0','13.40.90'),('55UP7000PUA','6.5.3','03.53.45'),('60UJ6050-UA','3.9.0','06.10.55'),('OLED55CXPUA','5.6.2','04.64.00'),('future-native-qt','12.0.0','01.00.00')):
            def luna(uri, payload, **kw):
                if 'systemprofile' in uri: return missing
                if 'getSystemInfo' in uri: return dict(returnValue=True, modelName=model, firmwareVersion=firmware, sdkVersion=sdk)
                if 'getConfigs' in uri: return {'returnValue':True,'configs':{'com.webos.surfacemanager.keyFilters':chain}}
                raise AssertionError(uri)
            remote=Mock();remote.luna.side_effect=luna;remote.run.return_value=observed
            info={}
            self.assertEqual(verify(remote,CheckList(),info,allow_c1=True,allow_compositor=True),'c1-native-gate')
            self.assertEqual(info['home_backend_schema'],3)
            self.assertNotIn('home-profiles',info['root_requirements'])

    def test_generic_compositor_refuses_unknown_chain_or_invalid_identity(self):
        from cytv.root_capabilities import compositor_device
        for sdk,chain in [('11.2.0',[]),('9.2.2',[]),('invalid',[]),('9.2.2',[{'file':'/foreign/home.js','handler':'handleSystemKeys'}])]:
            remote=Mock()
            remote.luna.side_effect=[dict(returnValue=True,modelName='55NANO77SRA',firmwareVersion='23.25.55',sdkVersion=sdk),
                {'returnValue':True,'configs':{'com.webos.surfacemanager.keyFilters':chain}}]
            self.assertFalse(compositor_device(remote))

    def test_generic_permission_denial_never_enters_native_admission(self):
        from cytv.root_capabilities import verify,RootCapabilityError
        remote=Mock();remote.luna.return_value={'returnValue':False,'errorCode':-1,'errorText':'Access denied'}
        with self.assertRaises(RootCapabilityError): verify(remote,CheckList(),{},allow_c1=True,allow_compositor=True)
        remote.run.assert_not_called()

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

    def test_common_beta_selects_only_confirmed_native_c1(self):
        import struct
        from cytv.root_capabilities import verify
        from cytv.root_capabilities import RootCapabilityError
        missing = {'returnValue':False, 'errorCode':-1, 'errorText':'Service does not exist: com.webos.service.systemprofile.'}
        info = {'returnValue':True, 'modelName':'OLED65C14LB', 'firmwareVersion':'03.51.15', 'sdkVersion':'6.5.3-47'}
        header = struct.pack('<16sHHIIIIIHHHHHH', b'\x7fELF\x01\x01\x01', 3, 40, 1, 64, 52, 0, 0, 52, 32, 2, 0, 0, 0)
        dump = ' '.join(str(n) for n in header)
        observed = '0 1 755 50684\n' + dump + '\nCYTV_HOME_ELF\n' + dump
        remote = Mock()
        for reply, device, observed_elf, accepted in (
                (missing, info, observed, True), (missing, dict(info,modelName='55UP7000PUA'),observed,False),
                (missing, dict(info,sdkVersion='7.0.0'),observed,False), (missing,info,observed.replace('127','128'),False),
                (missing,info,observed.replace('0 1 755','0 1 777'),False),
                (dict(missing,errorText='Access denied'),info,observed,False),
                (dict(missing,errorText='Service does not exist: com.example.other.'),info,observed,False),
                (TimeoutError(),info,observed,False)):
            with self.subTest(reply=reply,device=device):
                remote.reset_mock()
                remote.luna.side_effect = [reply,device]
                remote.run.return_value = observed_elf
                summary = {'home_backend':'stale'}
                if accepted:
                    self.assertEqual(verify(remote,CheckList(),summary,allow_c1=True),'c1-native-gate')
                    self.assertEqual(summary['root_capabilities']['home-profiles'],'service-absent')
                    self.assertNotIn('home-profiles',summary['root_requirements'])
                    self.assertEqual(summary['home_backend'],'c1-native-gate')
                    self.assertFalse(any('getSystemSettings' in str(c) for c in remote.luna.call_args_list))
                else:
                    with self.assertRaises(RootCapabilityError):
                        verify(remote,CheckList(),summary,allow_c1=True)
                    self.assertNotIn('home_backend',summary)

    def test_real_ssh_transport_preserves_only_the_exact_missing_profile_flag(self):
        from cytv.errors import TVRejected
        from cytv.transport import terminal_reply
        from cytv.root_capabilities import verify
        uri='com.webos.service.systemprofile/getProfiles'
        reply={'returnValue':False,'errorCode':-1,'errorText':'Service does not exist: com.webos.service.systemprofile.'}
        for target, value, expected in ((uri,reply,True),(uri,dict(reply,errorCode='-1'),False),
                (uri,dict(reply,errorText='denied'),False),('com.example.service/query',reply,False)):
            with self.subTest(target=target,value=value), self.assertRaises(TVRejected) as rejected:
                terminal_reply(value, uri=target)
            self.assertIs(rejected.exception.systemprofile_missing, expected)
            self.assertNotIn('errorText',rejected.exception.luna)
            if expected:
                remote=Mock()
                remote.luna.side_effect=rejected.exception
                with patch('cytv.root_capabilities.c1_device', return_value=True):
                    self.assertEqual(verify(remote,CheckList(),{},allow_c1=True),'c1-native-gate')

    def test_detected_profile_prefers_normal_product_without_native_probe(self):
        from cytv.root_capabilities import verify
        remote=Mock()
        remote.luna.side_effect=[PROFILES, SETTINGS]
        info={}
        self.assertEqual(verify(remote,CheckList(),info,allow_c1=True), 'system-profile')
        remote.run.assert_not_called()
        self.assertEqual(info['home_backend'],'system-profile')

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
                if pending:
                    store.begin(profile,'install');store.save(profile)
                    (store.device_dir(profile)/'known_hosts').write_bytes(b'original pin')
                cls.return_value.status.return_value={}
                code=cli.main(['doctor','--host',profile['host'],'--edition','root','--data-dir',tmp],
                              connect=lambda *a:Mock(),write=lambda _:None)
                self.assertEqual(code,0)
                if pending:cls.return_value.preflight.assert_called_once_with()
                else:cls.return_value.preflight.assert_called_once_with(home_interfaces=True)
