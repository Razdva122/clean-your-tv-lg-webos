"""No reinstall is needed to observe the current native admission failure."""
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PROJECT=Path(__file__).resolve().parents[2]


class NativeInspectionTests(unittest.TestCase):
    def module(self):
        try:return importlib.import_module('cytv.root_native_inspection')
        except ImportError:self.fail('Missing original-operation native read-only inspection')

    def fixture(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        root=Path(temporary.name).resolve();state=root/'state';state.mkdir(mode=0o700)
        identifier='a'*32
        lease={'schema':1,'id':'b'*32,'owner':'product','journal':'product-'+identifier+'.json',
               'stage':'root-deploy','terminal':False}
        request={'operation':identifier,'action':'install','stage':'root-deploy','state':'recovery_required',
                 'home_changed':False,'lease':lease['id'],'failure':{'exception_type':'CalledProcessError','exit_status':1}}
        for name,value in (('operation',lease),('request-'+identifier,request)):
            path=state/(name+'.json');path.write_text(json.dumps(value));path.chmod(0o600)
        (state/'ownership.lock').touch(mode=0o600)
        return root,state,identifier,request

    def run_inspection(self,root,state,identifier,fail=True,mutate=False):
        module=self.module();program=module.program(PROJECT,identifier)
        # Real checked Store, fd mutex, loader and result producer. Adapt only
        # fixed OS paths/UID and the hardware-only probe inside this host process.
        adapter="""
from pathlib import Path
import os,json
STATE=Path(%r)
ROOT=Path(%r)/'absent-root'
from updater.store import Store
check=Store._check
Store._check=lambda self,info: (setattr(self,'uid',os.getuid()),check(self,info))[-1]
walk=Store._walk
Store._walk=lambda self,path:(setattr(self,'uid',os.getuid()),walk(self,path))[-1]
import runtime.c1_keyfilter as backend
def probe():
    %s
backend.probe=probe
""" % (str(state),str(root),
    "STATE.joinpath('request-'+operation+'.json').write_text('{}');return {}" if mutate else
    "raise PermissionError(13,'PRIVATE password/path')" if fail else "return {}")
        program=program.replace('def observe():',adapter+'\ndef observe():',1)
        before={str(p):(p.read_bytes(),p.stat().st_mode,p.stat().st_ino) for p in root.rglob('*') if p.is_file()}
        result=subprocess.run([sys.executable,'-I','-B','-'],input=program,capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        value=json.loads(result.stdout)
        after={str(p):(p.read_bytes(),p.stat().st_mode,p.stat().st_ino) for p in root.rglob('*') if p.is_file()}
        if not mutate:self.assertEqual(before,after)
        for private in ('PRIVATE',str(root),identifier):self.assertNotIn(private,result.stdout)
        return value

    @unittest.skipUnless(os.name=='posix','TV fd/mutex inspection requires POSIX')
    def test_original_request_observation_is_read_only_and_carries_current_probe_cause(self):
        root,state,identifier,request=self.fixture()
        value=self.run_inspection(root,state,identifier)
        self.assertEqual(value['status'],'observed')
        self.assertEqual(value['admission'],'failed')
        self.assertEqual(value['failure']['exception_type'],'PermissionError')
        self.assertEqual(value['failure']['errno'],13)
        self.assertEqual(value['deployment_stage'],'absent')
        self.assertEqual(self.run_inspection(root,state,identifier,fail=False)['admission'],'passed')

    @unittest.skipUnless(os.name=='posix','TV fd/mutex inspection requires POSIX')
    def test_foreign_lease_activated_or_changed_request_never_yields_probe_proof(self):
        root,state,identifier,request=self.fixture()
        for key,value in (('lease','c'*32),('home_changed',True),('state','pending')):
            bad=dict(request);bad[key]=value
            (state/('request-'+identifier+'.json')).write_text(json.dumps(bad))
            self.assertEqual(self.run_inspection(root,state,identifier)['status'],'refused')
        (state/('request-'+identifier+'.json')).write_text(json.dumps(request))
        self.assertEqual(self.run_inspection(root,state,identifier,mutate=True)['status'],'refused')

    @unittest.skipUnless(os.name=='posix','TV fd/mutex inspection requires POSIX')
    def test_missing_mutex_is_not_created(self):
        root,state,identifier,request=self.fixture()
        (state/'ownership.lock').unlink()
        self.assertEqual(self.run_inspection(root,state,identifier)['status'],'refused')
        self.assertFalse((state/'ownership.lock').exists())

    @unittest.skipUnless(os.name=='posix','TV fd/mutex inspection requires POSIX')
    def test_busy_original_mutex_is_not_replaced_or_released(self):
        import fcntl
        root,state,identifier,request=self.fixture()
        with (state/'ownership.lock').open('rb') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            self.assertEqual(self.run_inspection(root,state,identifier)['status'],'refused')

    def test_host_uses_original_pin_preserves_profile_and_never_provisions_or_uploads(self):
        from unittest.mock import Mock,patch
        from cytv import state,python_runtime
        module=self.module()
        with tempfile.TemporaryDirectory() as folder:
            store=state.Store(folder);profile=state.target('fixture.invalid','root');store.save(profile)
            store.begin(profile,'install',stage='setup',home_backend='c1-native-gate',product_operation='a'*32)
            known=store.device_dir(profile)/'known_hosts';known.write_bytes(b'ORIGINAL PIN')
            before={str(p):p.read_bytes() for p in store.device_dir(profile).rglob('*') if p.is_file()}
            remote=Mock();remote.run.return_value=json.dumps({'schema':1,'status':'observed',
                'admission':'failed','deployment_stage':'absent','failure':{'exception_type':'TimeoutError',
                'frames':[{'file':'c1_keyfilter.py','line':175}],'message':'PRIVATE'}})
            pin=module.source_pin(PROJECT)
            patcher=patch.object(module,'sources',side_effect=AssertionError('sources reread after connection'))
            self.addCleanup(patcher.stop)
            with patch('cytv.transport.SSH.connect',return_value=remote) as connect, \
                 patch.object(python_runtime,'prime_cache',return_value=Path('/host/cache')), \
                 patch.object(python_runtime,'_verified_bytes',return_value=b'pinned'), \
                 patch.object(python_runtime,'normalize_to_file',return_value={'files':{}}), \
                 patch.object(python_runtime,'_verify',side_effect=lambda *_: patcher.start()) as verify, \
                 patch.object(python_runtime,'_smoke') as smoke:
                result=module.inspect_saved(store,profile,'a'*32,lambda _:None,PROJECT,pin)
            self.assertFalse(connect.call_args.kwargs['persist'])
            verify.assert_called_once();smoke.assert_not_called();remote.upload.assert_not_called()
            self.assertIn('-I -B -',remote.run.call_args.args[0])
            self.assertNotIn('PRIVATE',json.dumps(result))
            self.assertEqual(result['failure']['exception_type'],'TimeoutError')
            self.assertEqual(before,{str(p):p.read_bytes() for p in store.device_dir(profile).rglob('*') if p.is_file()})
            remote.close.assert_called_once()
            patcher.stop()
            with patch('cytv.transport.SSH.connect') as connect:
                with self.assertRaises(ValueError):module.inspect_saved(store,profile,'a'*32,lambda _:None,PROJECT,'0'*64)
                with self.assertRaises(ValueError):module.inspect_saved(store,profile,'b'*32,lambda _:None,PROJECT,pin)
                connect.assert_not_called()

    def test_source_pin_and_selector_require_exact_reviewed_sources(self):
        module=self.module();pin=module.source_pin(PROJECT)
        self.assertRegex(pin,'^[a-f0-9]{64}$')
        self.assertEqual(pin,module.source_pin(PROJECT))
        with self.assertRaises(ValueError):module.program(PROJECT,'../PRIVATE')
