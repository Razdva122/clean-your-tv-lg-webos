"""Host-only compositor routing and ownership tests; no TV acceptance."""
import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'runtime'), str(ROOT)]


class RuntimeTests(unittest.TestCase):
    def test_old_sdk_probe_and_saved_selection_use_capabilities_end_to_end(self):
        import struct
        target=self.root/'native-home'
        header=struct.pack('<16sHHIIIIIHHHHHH',b'\x7fELF\x01\x01\x01',3,40,1,64,52,0,0,52,32,2,0,0,0)
        target.write_bytes(header);target.chmod(0o700)
        real_secure=self.k.legacy.secure
        def read(path,*args,**kwargs):
            if Path(path)==target:return header
            return real_secure(path,*args,**kwargs)
        for sdk in ('3.9.0','4.4.3','5.6.2','12.0.0'):
            with self.subTest(sdk=sdk),patch.object(self.k.legacy,'TARGET',target),patch.object(self.k.os,'geteuid',return_value=0),patch.object(self.k.sys,'platform','linux'),patch.object(self.k.legacy,'secure',side_effect=read),patch('struct.calcsize',return_value=4),patch.object(self.k,'luna',return_value=dict(returnValue=True,modelName='capability-admitted',firmwareVersion='06.10.55',sdkVersion=sdk)),patch.object(self.k,'require_generic_environment') as environment,patch.object(self.k,'read_chain',return_value=[]):
                observed=self.k.probe()
                self.assertEqual(observed['webos'],sdk)
                self.assertTrue(self.k.admission_valid(observed))
                environment.assert_called_once_with()
                self.admission=observed
                marker=self.prepare()
                self.assertEqual(marker['schema'],3)
                self.assertEqual(self.k.legacy.selection(self.root,self.uid),marker)
                (self.root/'home-backend.json').unlink()
                import shutil
                shutil.rmtree(self.root/'c1-keyfilter')

    def test_vendor_qt5_alias_is_read_only_and_cannot_resolve_outside_vendor_tree(self):
        allowed=Path('/usr/lib/qml/KeyFilters/systemUi.js')
        with patch.object(Path,'resolve',return_value=allowed),patch.object(self.k,'secure',return_value=b'vendor') as read:
            self.assertEqual(self.k.vendor_script('/usr/lib/qt5/qml/KeyFilters/systemUi.js'),b'vendor')
            read.assert_called_once_with(allowed,limit=256*1024)
        with patch.object(Path,'resolve',return_value=Path('/foreign/systemUi.js')),patch.object(self.k,'secure') as read:
            with self.assertRaises(ValueError): self.k.vendor_script('/usr/lib/qt5/qml/KeyFilters/systemUi.js')
            read.assert_not_called()

    def generic(self):
        return dict(self.admission,model='55NANO77SRA',firmware='23.25.55',webos='9.2.2')

    def test_generic_environment_refuses_takeover_and_requires_exact_absence(self):
        missing={'returnValue':False,'errorCode':-1,'errorText':'Service does not exist: com.webos.service.systemprofile.'}
        vendor={'file':'/usr/lib/qt5/qml/KeyFilters/systemUi.js','handler':'handleSystemKeys'}
        app={'id':'com.webos.app.home','type':'native','main':'file:///usr/bin/com.webos.app.home'}
        mountinfo=self.root/'mountinfo';mountinfo.write_text('1 0 0:1 / / rw - squashfs /dev/root ro\n')
        appinfo=self.root/'appinfo.json';appinfo.write_text(json.dumps(app));appinfo.chmod(0o600)
        other=self.root/'other-home'
        bindings=self.root/'bindings.json'
        import emergency_reader
        keys=bytearray(128)
        for code in (773,412):keys[code//8]|=1<<(code%8)
        def reader():
            fd=os.open(os.devnull,os.O_RDONLY);return fd
        real_secure=self.k.secure
        def secure(path,*args,**kw):
            if str(path)==vendor['file']:return b'function handleSystemKeys() { return Qt.Key_Super_L; }'
            if str(path)=='/usr/palm/applications/com.webos.app.home/appinfo.json':return json.dumps(app).encode()
            return real_secure(path,self.uid,*args,**kw)
        with patch.object(self.k,'STOCK_APPINFO',appinfo),patch.object(self.k,'MOUNTINFO',mountinfo),patch.object(self.k,'OTHER_HOME_STATE',(other,)),patch.object(self.k,'INPUT_BINDINGS',bindings),patch.object(self.k,'secure',side_effect=secure),patch.object(self.k,'vendor_script',side_effect=lambda path:secure(Path(path))),patch.object(self.k,'luna',return_value=missing),patch.object(self.k,'read_chain',return_value=[vendor]),patch.object(emergency_reader,'open_remote',side_effect=reader),patch.object(emergency_reader,'query',return_value=keys):
            self.k.require_generic_environment()
            # A separate, whole read-only system image is not a Home takeover.
            stock_mount='2 1 179:27 / /usr ro,relatime - squashfs /dev/mmcblk0p27 ro\n'
            from types import SimpleNamespace
            with patch.object(self.k,'STOCK_APPINFO',Path('/usr/palm/applications/com.webos.app.home/appinfo.json')),patch.object(self.k.legacy,'TARGET',Path('/usr/bin/com.webos.app.home')),patch.object(self.k.os,'stat',return_value=SimpleNamespace(st_dev=os.makedev(179,27))):
                mountinfo.write_text(stock_mount)
                self.k.require_generic_environment()
                for invalid in (
                    stock_mount.replace(' / /usr ', ' /foreign /usr '),
                    stock_mount.replace('/usr ro,', '/usr rw,'),
                    stock_mount.replace('p27 ro\n', 'p27 rw\n'),
                    stock_mount.replace('squashfs', 'overlay'),
                    stock_mount.replace('179:27', '179:28'),
                    stock_mount.replace('/dev/mmcblk0p27', '/dev/loop0'),
                    stock_mount+stock_mount.replace('2 1 ', '3 1 '),
                    stock_mount+'3 2 0:2 / /usr/bin ro - tmpfs tmpfs ro\n',
                    stock_mount+'3 2 0:2 / /usr/bin/com.webos.app.home ro - tmpfs tmpfs ro\n',
                    stock_mount+'3 2 0:2 / /usr/palm/applications/com.webos.app.home ro - tmpfs tmpfs ro\n',
                ):
                    with self.subTest(mounts=invalid):
                        mountinfo.write_text(invalid)
                        with self.assertRaises(ValueError):self.k.require_generic_environment()
            mountinfo.write_text('1 0 0:1 / / rw - squashfs /dev/root ro\n')
            for invalid in (dict(app,type='flutter'),dict(app,type='web'),dict(app,main='ribbon.qml')):
                appinfo.write_text(json.dumps(invalid))
                with self.assertRaisesRegex(ValueError,'manifest'): self.k.require_generic_environment()
            appinfo.write_text(json.dumps(app))
            bindings.write_text('{"773":{"action":"launch","id":"foreign.home"}}');bindings.chmod(0o600)
            with self.assertRaises(ValueError):self.k.require_generic_environment()
            bindings.unlink()
            with patch.object(emergency_reader,'query',return_value=bytearray(128)),self.assertRaises(ValueError):self.k.require_generic_environment()
            other.mkdir()
            with self.assertRaises(ValueError):self.k.require_generic_environment()
            other.rmdir()
            mountinfo.write_text('2 1 0:1 /foreign '+str(appinfo.parent)+' rw - tmpfs tmpfs rw\n')
            with self.assertRaises(ValueError):self.k.require_generic_environment()
            mountinfo.write_text('1 0 0:1 / / rw - squashfs /dev/root ro\n')
            for reply in (dict(missing,errorText='Access denied'),dict(missing,errorCode='-1'),{'returnValue':True}):
                with patch.object(self.k,'luna',return_value=reply),self.assertRaises(ValueError):self.k.require_generic_environment()
            with patch.object(emergency_reader,'open_remote',side_effect=ValueError('unknown ABI')),self.assertRaises(ValueError):self.k.require_generic_environment()
            with patch.object(self.k,'read_chain',return_value=[dict(vendor,file='/foreign/home.js')]),self.assertRaises(ValueError):self.k.require_generic_environment()

    def test_schema3_admits_capabilities_without_expanding_legacy_c1_schema(self):
        for sdk in ('3.9.0','4.4.3','5.6.2','10.3.1','12.0.0'):
            value=dict(self.generic(),webos=sdk)
            self.assertTrue(self.k.admission_valid(value))
            self.assertFalse(self.k.legacy.admission_valid(value))
        for model in ('55NANO77SRA','OLED55C37LA','55UP7000PUA'):
            value=dict(self.generic(),model=model)
            self.assertTrue(self.k.admission_valid(value))
            self.assertFalse(self.k.legacy.admission_valid(value))
        self.admission=self.generic()
        marker=self.prepare()
        self.assertEqual(marker['schema'],3)
        self.assertEqual(self.k.legacy.selection(self.root,self.uid),marker)
        marker['schema']=2
        self.k.atomic(self.root/'home-backend.json',marker,self.uid)
        with self.assertRaises(ValueError): self.k.selection(self.root,self.uid)

    def test_schema3_writes_volatile_and_preserves_foreign_chain_on_restore(self):
        self.admission=self.generic();self.prepare()
        vendor={'file':'/usr/lib/qt5/qml/KeyFilters/systemUi.js','handler':'handleSystemKeys'}
        foreign={'file':'/foreign/buttons.js','handler':'buttons','extra':42}
        chain=[vendor];effects=[]
        def rpc(uri,payload,**kw):
            if uri.endswith('getConfigs'): return {'returnValue':True,'configs':{self.k.KEY:list(chain)}}
            self.assertTrue((self.root/'c1-keyfilter/pending.json').exists())
            effects.append(payload)
            chain[:]=payload['configs'][self.k.KEY]
            return {'returnValue':True}
        with patch.object(self.k,'luna',side_effect=rpc):
            self.k.change_chain(self.root,True,self.uid)
            chain.append(foreign)
            self.k.change_chain(self.root,False,self.uid)
        self.assertEqual(chain,[vendor,foreign])
        self.assertEqual([v.get('volatile') for v in effects],[True,True])
        self.assertFalse((self.root/'c1-keyfilter/pending.json').exists())

    def test_schema3_refuses_foreign_filter_added_between_probe_and_enable(self):
        self.admission=self.generic();self.prepare()
        chain=[{'file':'/foreign/home.js','handler':'home'}]
        with patch.object(self.k,'read_chain',return_value=chain),patch.object(self.k,'write_chain') as write:
            with self.assertRaises(ValueError): self.k.change_chain(self.root,True,self.uid)
        write.assert_not_called()
        self.assertFalse((self.root/'c1-keyfilter/pending.json').exists())

    def test_generic_unknown_identity_is_refused(self):
        for change in ({'model':''},{'webos':'invalid'},{'firmware':'unknown'},{'target_sha256':'x'*64}):
            self.assertFalse(self.k.admission_valid(dict(self.generic(),**change)))

    def test_schema3_interrupted_write_is_recoverable_after_firmware_change(self):
        self.admission=self.generic();self.prepare();vendor={'file':'/usr/lib/qt5/qml/KeyFilters/systemUi.js','handler':'handleSystemKeys'};chain=[vendor]
        def write(value,**kw): chain[:]=value;raise TimeoutError('outcome unknown')
        with patch.object(self.k,'read_chain',side_effect=lambda:list(chain)),patch.object(self.k,'write_chain',side_effect=write):
            with self.assertRaises(TimeoutError): self.k.change_chain(self.root,True,self.uid)
        self.assertTrue((self.root/'c1-keyfilter/pending.json').exists())
        with patch.object(self.k,'native',return_value=self.proof()),patch.object(self.k,'probe',side_effect=AssertionError('restore must not re-admit')),patch.object(self.k,'read_chain',side_effect=lambda:list(chain)),patch.object(self.k,'write_chain',side_effect=lambda v,**kw:chain.__setitem__(slice(None),v)):
            self.k.execute('boot',root=self.root,uid=self.uid)
        self.assertEqual(chain,[vendor])
        self.assertFalse(self.k.read_intent(self.root,self.uid)['enabled'])

    def test_schema3_previous_boot_controller_pid_is_never_followed(self):
        self.admission=self.generic();self.prepare()
        record=self.root/'c1-keyfilter/controller.json'
        self.k.atomic(record,dict(pid=123,start=456,token='1'*32,boot='00000000-0000-0000-0000-000000000001'),self.uid)
        with patch.object(self.k,'process_start',side_effect=AssertionError('previous boot PID must not be inspected')):
            self.k.stop_controller(self.root,self.uid)
        self.assertFalse(record.exists())

    def test_schema3_configd_reset_cancels_lifecycle_return_without_reinstalling(self):
        self.admission=self.generic();self.prepare()
        self.k.write_intent(self.root,True,'1'*32,'active',self.uid)
        proof=self.proof();proof.update(healthy=True,stopped=False,state='armed',guardian_pid=123,stock_verified=False)
        replies=[{'returnValue':True,'state':'Active'},{'returnValue':True,'foregroundAppInfo':[]},{'returnValue':True,'appId':''}]
        with patch.object(self.k,'luna',side_effect=replies),patch.object(self.k,'native',return_value=proof),patch.object(self.k,'read_chain',return_value=[]),patch.object(self.k,'write_chain',side_effect=AssertionError('must not reinstall')):
            self.assertFalse(self.k.return_ready(self.root,self.uid,'1'*32,lambda:False))

    def test_schema3_changed_home_can_release_filter_without_claiming_stock_proof(self):
        self.admission=self.generic();self.prepare();own=self.k.filter_entry(self.root);chain=[own]
        self.k.atomic(self.root/'c1-keyfilter/ownership.json',dict(schema=1,entry=own,token='1'*32),self.uid)
        stopped=self.proof();stopped['stock_verified']=False
        with patch.object(self.k,'native',return_value=stopped),patch.object(self.k,'read_chain',side_effect=lambda:list(chain)),patch.object(self.k,'write_chain',side_effect=lambda v,**kw:chain.__setitem__(slice(None),v)):
            with self.assertRaisesRegex(ValueError,'identity'): self.k.execute('restore',root=self.root,uid=self.uid)
        self.assertEqual(chain,[])
        self.assertFalse(self.k.read_intent(self.root,self.uid)['enabled'])
        self.assertEqual(self.k.read_intent(self.root,self.uid)['phase'],'recovering')

    def setUp(self):
        try: self.k = importlib.import_module('c1_keyfilter')
        except ModuleNotFoundError: self.fail('schema2 runtime missing')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.uid = os.getuid()
        boot=patch.object(self.k,'boot_identity',return_value='12345678-1234-1234-1234-123456789abc')
        boot.start(); self.addCleanup(boot.stop)
        self.admission = dict(model='OLED65C14LB', firmware='03.51.15', webos='6.5.0',
                              target_sha256='b'*64, target=dict(dev=1, ino=2, size=52, mtime_ns=3))

    def prepare(self):
        return self.k.prepare(self.root, 'a'*64, self.admission, self.uid)

    def proof(self, **kw):
        return dict(returnValue=True, backend='c1-native-gate', routing='compositor-keyfilter-v1',
                    state='stopped', mounted=False, healthy=False, stock_verified=True,
                    stopped=True, token='1'*32, guardian_pid=0, reason='', profiles=None, **kw)

    def test_prepare_exact_marker_and_seven_line_config(self):
        self.prepare()
        self.assertEqual(self.k.selection(self.root, self.uid)['schema'], 2)
        lines = (self.root/'c1-keyfilter/config').read_text().splitlines()
        self.assertEqual(len(lines), 7)
        self.assertEqual(lines[0], 'CYTV-C1-KEYFILTER-1')
        self.assertEqual((self.root/'c1-keyfilter').stat().st_mode & 0o777, 0o700)

    def test_no_selection_has_no_effect_and_no_checkpoint_dependency(self):
        with patch.object(self.k, 'luna', side_effect=AssertionError('effect')):
            self.assertIsNone(self.k.selection(self.root, self.uid))
        self.assertEqual(list(self.root.iterdir()), [])
        # An unrelated world writable subtree must never be inspected.
        other = self.root/'checkpoint'; other.mkdir(mode=0o777); other.chmod(0o777)
        self.prepare()

    def test_chain_preserves_foreign_entries_and_requires_exact_owned_identity(self):
        foreign = [{'file':'/foreign', 'handler':'other', 'opaque':{'x':[1, True, None]}}]
        own = self.k.filter_entry(self.root)
        self.assertEqual(self.k.reconcile(foreign, self.root, True), [own]+foreign)
        self.assertEqual(self.k.reconcile([own]+foreign, self.root, False), foreign)
        for chain in ([dict(own, handler='changed')], [dict(own, extra=True)], [own, own]):
            with self.assertRaises(ValueError): self.k.reconcile(chain, self.root, False)
        for chain in (None, {}, ['opaque'], [{'file':1,'handler':'x'}]):
            with self.assertRaises(ValueError): self.k.reconcile(chain, self.root, False)

    def test_pending_durable_before_write_and_readback_failure_retains_evidence(self):
        self.prepare(); chain=[]
        def read(): return list(chain)
        def write(value):
            pending=json.loads((self.root/'c1-keyfilter/pending.json').read_text())
            self.assertEqual(pending['before'], [])
            self.assertEqual(pending['after'], value)
            # Simulate configd acknowledging but not applying its write.
        with patch.object(self.k,'read_chain',side_effect=read), patch.object(self.k,'write_chain',side_effect=write):
            with self.assertRaises(ValueError): self.k.change_chain(self.root, True, self.uid)
        self.assertTrue((self.root/'c1-keyfilter/pending.json').exists())

    def test_stock_projection_requires_absent_filter(self):
        self.prepare()
        with patch.object(self.k,'native',return_value=self.proof()), patch.object(self.k,'verify_ready',return_value={'integrity_verified':True}):
            with patch.object(self.k,'read_chain',return_value=[self.k.filter_entry(self.root)]):
                self.assertFalse(self.k.status(self.root,self.uid)['effective']['stock_verified'])
            with patch.object(self.k,'read_chain',return_value=[]):
                self.assertTrue(self.k.status(self.root,self.uid)['effective']['stock_verified'])

    def test_restore_stops_native_before_removing_filter(self):
        self.prepare(); calls=[]; chain=[self.k.filter_entry(self.root)]
        self.k.atomic(self.root/'c1-keyfilter/ownership.json',dict(schema=1,entry=chain[0],token='1'*32),self.uid)
        def native(args,*a): calls.append(args[0]); return self.proof()
        def write(value): calls.append('chain'); chain[:]=value
        with patch.object(self.k,'native',side_effect=native), patch.object(self.k,'read_chain',side_effect=lambda:list(chain)), patch.object(self.k,'write_chain',side_effect=write):
            self.assertEqual(self.k.execute('restore',root=self.root,uid=self.uid),'restored')
        self.assertLess(calls.index('--restore'),calls.index('chain'))

    def test_lifecycle_replay_cancel_and_unknown_visibility(self):
        policy=self.k.ReturnPolicy('1'*32)
        card=lambda app,event='foreground':dict(event=event,appId=app,windowType='_WEBOS_WINDOW_TYPE_CARD')
        policy.event(card('content'),0)
        policy.event(card('content','stop'),1)
        self.assertFalse(policy.due(1.4))
        self.assertTrue(policy.due(2))
        policy.event(card('new-content'),2.1)
        self.assertFalse(policy.due(3))
        policy.event(card('com.webos.app.home'),3)
        home={'returnValue':True,'foregroundAppInfo':[dict(appId='com.webos.app.home',windowType='_WEBOS_WINDOW_TYPE_CARD')]}
        proof=self.proof(); proof.update(healthy=True,stopped=False,state='armed',guardian_pid=123,stock_verified=False)
        self.assertTrue(self.k.can_return(home,{'returnValue':True,'state':'Active'},proof,'1'*32,{'returnValue':True,'appId':self.k.STOCK}))
        home['foregroundAppInfo'].append(dict(appId=self.k.APP,windowType='_WEBOS_WINDOW_TYPE_OVERLAY'))
        self.assertFalse(self.k.can_return(home,{'returnValue':True,'state':'Active'},proof,'1'*32))
        for value in ({}, {'returnValue':True,'foregroundAppInfo':[]}, {'returnValue':True,'foregroundAppInfo':[{}]}):
            self.assertFalse(self.k.can_return(value,{'returnValue':True,'state':'Active'},proof,'1'*32))
        policy.event({'event':'unknown'},3.1)
        self.assertFalse(policy.due(4))

    def test_return_to_confirmed_empty_requires_both_views_and_active_intent(self):
        proof=self.proof(); proof.update(healthy=True,stopped=False,state='armed',guardian_pid=123,stock_verified=False)
        power={'returnValue':True,'state':'Active'}
        empty={'returnValue':True,'foregroundAppInfo':[]}
        self.assertTrue(self.k.can_return(empty,power,proof,'1'*32,{'returnValue':True,'appId':''}))
        self.assertFalse(self.k.can_return(empty,power,proof,'1'*32,{'returnValue':True,'appId':'new-content'}))
        self.assertFalse(self.k.can_return(empty,{},proof,'1'*32,{'returnValue':True,'appId':''}))
        policy=self.k.ReturnPolicy('1'*32)
        policy.event(dict(event='stop',appId='background',windowType='_WEBOS_WINDOW_TYPE_CARD'),1)
        self.assertFalse(policy.due(2))

    def test_modified_owned_entry_restore_retains_native_stop_and_evidence(self):
        self.prepare()
        changed=dict(self.k.filter_entry(self.root),handler='foreign')
        with patch.object(self.k,'native',return_value=self.proof()) as native, patch.object(self.k,'read_chain',return_value=[changed]), patch.object(self.k,'write_chain') as write:
            with self.assertRaises(ValueError): self.k.execute('restore',root=self.root,uid=self.uid)
        self.assertEqual(native.call_args_list[0].args[0],['--restore'])
        write.assert_not_called()

    def test_unknown_exact_owned_entry_is_not_destructively_removed(self):
        self.prepare()
        with patch.object(self.k,'read_chain',return_value=[self.k.filter_entry(self.root)]), patch.object(self.k,'write_chain') as write:
            with self.assertRaises(ValueError): self.k.change_chain(self.root,False,self.uid)
        write.assert_not_called()

    def test_probe_is_independent_of_legacy_checkpoint_probe(self):
        target=self.root/'home'; target.write_bytes(b'ELF')
        with patch.object(self.k.legacy,'TARGET',target), patch.object(self.k.os,'geteuid',return_value=0), patch.object(self.k.sys,'platform','linux'), patch.object(self.k.legacy,'probe',side_effect=AssertionError('legacy checkpoint probe')), patch.object(self.k.legacy,'secure',return_value=b'ELF'), patch.object(self.k.legacy,'admit',return_value={k:self.admission[k] for k in ('model','firmware','webos')}), patch.object(self.k,'luna',return_value={'returnValue':True}), patch.object(self.k,'read_chain',return_value=[]),patch.object(self.k,'require_generic_environment') as environment:
            target.chmod(0o700)
            observed=self.k.probe()
        self.assertEqual(observed['target']['size'],3)
        environment.assert_called_once_with()
        self.assertEqual(observed['model'],self.admission['model'])

    def test_restore_clears_interrupted_prewrite_intent_after_absence_readback(self):
        self.prepare()
        own=self.k.filter_entry(self.root)
        pending=self.root/'c1-keyfilter/pending.json'
        self.k.atomic(pending,dict(schema=1,before=[],after=[own],entry=own),self.uid)
        with patch.object(self.k,'read_chain',return_value=[]): self.k.change_chain(self.root,False,self.uid)
        self.assertFalse(pending.exists())

    def test_native_selfcheck_accepts_only_exact_success_shape(self):
        from types import SimpleNamespace
        value=dict(returnValue=True,backend=self.k.BACKEND,routing=self.k.ROUTING,selfcheck=True)
        with patch.object(self.k,'binary',return_value=Path('/fake')), patch.object(self.k.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=json.dumps(value).encode())):
            self.assertEqual(self.k.native(['--selfcheck'],self.root,self.uid),value)
        for bad in (dict(value,selfcheck=False),dict(value,extra=True),dict(value,routing='old')):
            with patch.object(self.k,'binary',return_value=Path('/fake')), patch.object(self.k.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=json.dumps(bad).encode())):
                with self.assertRaises(ValueError): self.k.native(['--selfcheck'],self.root,self.uid)

    def test_cold_package_import_without_runtime_search_path(self):
        import subprocess
        result=subprocess.run([sys.executable,'-c','from runtime import c1_keyfilter, emergency_reader; assert c1_keyfilter.ROUTING == "compositor-keyfilter-v1"; assert callable(emergency_reader.open_remote)'],cwd=ROOT,env=dict(os.environ,PYTHONPATH=''),capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_controller_retirement_never_signals_a_pid_after_identity_check(self):
        self.prepare()
        record=self.root/'c1-keyfilter/controller.json'
        self.k.atomic(record,dict(pid=123,start=456,token='1'*32),self.uid)
        with patch.object(self.k,'process_start',side_effect=[456,FileNotFoundError()]), patch.object(Path,'read_bytes',return_value=str(self.root/'runtime/c1_keyfilter.py').encode()+b'\0--watch\0'+b'1'*32+b'\0'), patch.object(self.k.os,'kill',side_effect=AssertionError('unsafe PID signal')):
            self.k.stop_controller(self.root,self.uid)
        self.assertFalse(record.exists())

    def test_delayed_return_cancels_on_event_after_each_rpc(self):
        self.prepare()
        self.k.write_intent(self.root,True,'1'*32,'active',self.uid)
        proof=self.proof(); proof.update(healthy=True,stopped=False,state='armed',guardian_pid=123,stock_verified=False)
        replies=[{'returnValue':True,'state':'Active'},{'returnValue':True,'foregroundAppInfo':[]},{'returnValue':True,'appId':''}]
        for stage in range(4):
            with patch.object(self.k,'luna',side_effect=replies), patch.object(self.k,'native',return_value=proof):
                changes=iter([False]*stage+[True])
                self.assertFalse(self.k.return_ready(self.root,self.uid,'1'*32,lambda:next(changes)))

    def test_return_dispatch_uses_only_fixed_native_home_barrier(self):
        proof=self.proof(); proof.update(healthy=True,stopped=False,state='armed',guardian_pid=123,stock_verified=False)
        with patch.object(self.k,'native',return_value=proof) as native, patch.object(self.k,'luna',side_effect=AssertionError('raw launch bypass')):
            self.k.launch_return(self.root,self.uid,'1'*32)
        native.assert_called_once_with(['--home','1'*32],self.root,self.uid,timeout=2.5)
        stopped=self.proof()
        for value in (stopped,dict(proof,token='2'*32)):
            with patch.object(self.k,'native',return_value=value):
                with self.assertRaises(ValueError): self.k.launch_return(self.root,self.uid,'1'*32)

    def test_stock_surface_does_not_override_conflicting_or_unknown_sam(self):
        proof=self.proof(); proof.update(healthy=True,stopped=False,state='armed',guardian_pid=123,stock_verified=False)
        power={'returnValue':True,'state':'Active'}
        stock={'returnValue':True,'foregroundAppInfo':[dict(appId=self.k.STOCK,windowType=self.k.CARD)]}
        for foreground in ({'returnValue':True,'appId':'netflix'},None,{}, {'returnValue':True}, {'returnValue':False,'appId':self.k.STOCK}, {'returnValue':True,'appId':None}, {'returnValue':True,'appId':[]}):
            with self.subTest(foreground=foreground):
                self.assertFalse(self.k.can_return(stock,power,proof,'1'*32,foreground))
        for app in ('',self.k.STOCK):
            self.assertTrue(self.k.can_return(stock,power,proof,'1'*32,{'returnValue':True,'appId':app}))

    def test_native_rejects_mount_or_inconsistent_lease(self):
        proof=self.proof(); proof['opaque']=True
        with self.assertRaises(ValueError): self.k.validate_native(proof)
        proof=self.proof(); proof['mounted']=True
        with self.assertRaises(ValueError): self.k.validate_native(proof)
        proof=self.proof(); proof['healthy']=True
        with self.assertRaises(ValueError): self.k.validate_native(proof)


    def test_enable_chain_failure_restores_and_does_not_retry(self):
        self.prepare()
        (self.root/'runtime').mkdir()
        (self.root/'runtime/c1-home-filter.js').write_text('filter')
        (self.root/'runtime/c1-home-filter.js').chmod(0o600)
        with patch.object(self.k,'verify_ready',return_value={'integrity_verified':True}), patch.object(self.k,'native',return_value=self.proof()), patch.object(self.k,'probe',return_value=self.admission), patch.object(self.k,'read_chain',return_value=[]), patch.object(self.k,'binary',return_value=Path('/fake')), patch('helper_bridge.require_idle'), patch.object(self.k,'change_chain',side_effect=RuntimeError('write')) as chain, patch.object(self.k,'restore_locked') as restore:
            with self.assertRaises(RuntimeError): self.k.execute('enable',root=self.root,uid=self.uid)
        self.assertEqual(chain.call_count,1)
        restore.assert_called_once()


    def test_enable_controller_failure_restores_without_native_guard_launch(self):
        self.prepare()
        (self.root/'runtime').mkdir()
        script=self.root/'runtime/c1-home-filter.js'; script.write_text('filter'); script.chmod(0o600)
        with patch.object(self.k,'verify_ready',return_value={'integrity_verified':True}), patch.object(self.k,'native',return_value=self.proof()), patch.object(self.k,'probe',return_value=self.admission), patch.object(self.k,'read_chain',return_value=[]), patch.object(self.k,'binary',return_value=Path('/fake')), patch('helper_bridge.require_idle'), patch.object(self.k,'change_chain'), patch.object(self.k,'start_controller',side_effect=RuntimeError('controller startup')), patch.object(self.k,'restore_locked') as restore, patch.object(self.k.subprocess,'Popen') as popen:
            with self.assertRaises(RuntimeError): self.k.execute('enable',root=self.root,uid=self.uid)
        restore.assert_called_once()
        popen.assert_not_called()


if __name__=='__main__': unittest.main()
