import importlib.util
import json
from pathlib import Path
import unittest
import tempfile
import os
from contextlib import ExitStack, contextmanager
from unittest.mock import patch, MagicMock
spec = importlib.util.spec_from_file_location('root_provision',Path(__file__).parents[1]/'provision.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)

class RecoveryManifestTests(unittest.TestCase):
    @contextmanager
    def fixture(self, schema, embedded=False):
        with tempfile.TemporaryDirectory() as folder, ExitStack() as stack:
            state = Path(folder)
            runtime = state/'runtime'; runtime.mkdir()
            service = state/'service'; service.mkdir()
            runner = state/'run-recovery-service'; runner.write_bytes(b'runner')
            for name in p.PRIVATE_FILES:
                (service/name).write_bytes(b'/var/lib/clean-your-tv-root/runtime/cli.py boot' if name == 'boot-recover.sh' else b'service')
            for name in ('cli.py', 'c1-home-filter.js', 'c1-keyfilter-guard'):
                (runtime/name).write_bytes(name.encode())
            (state/'home-backend.json').write_bytes(b'selection')
            if embedded:
                for name in ('embedded-home.qml', 'embedded-home.js'):
                    (runtime/name).write_bytes(name.encode())
            selected = {'schema': schema, 'routing': 'compositor-keyfilter-v1',
                        'native_sha256': p.sha((runtime/'c1-keyfilter-guard').read_bytes())}
            for name, value in {'STATE':state, 'RUNTIME':runtime, 'PRIVATE_SERVICE':service, 'RUNNER':runner}.items():
                stack.enter_context(patch.object(p, name, value))
            stack.enter_context(patch.object(p, 'secure', side_effect=lambda path:path.read_bytes()))
            stack.enter_context(patch.object(p, 'verify_binding'))
            stack.enter_context(patch('runtime.c1_gate.selection', return_value=selected))
            yield runtime

    def test_historical_compositor_manifest_does_not_require_embedded_assets(self):
        for schema in (2, 3):
            with self.subTest(schema=schema), self.fixture(schema) as runtime:
                files = p.manifest()['files']
                self.assertNotIn(str(runtime/'embedded-home.qml'), files)
                self.assertNotIn(str(runtime/'embedded-home.js'), files)
                self.assertIn(str(runtime/'c1-home-filter.js'), files)

    def test_embedded_assets_are_hash_bound_for_each_compositor_selection(self):
        for schema in (2, 3, 4):
            for name in ('embedded-home.qml', 'embedded-home.js'):
                with self.subTest(schema=schema, asset=name), self.fixture(schema, embedded=True) as runtime:
                    original = p.manifest()
                    for asset in ('embedded-home.qml', 'embedded-home.js'):
                        self.assertEqual(original['files'][str(runtime/asset)], p.sha(asset.encode()))
                    (runtime/name).write_bytes(b'changed adapter')
                    self.assertNotEqual(p.manifest(), original)

    def test_embedded_selection_and_partial_bundles_require_both_assets(self):
        with self.fixture(4), self.assertRaises(FileNotFoundError):
            p.manifest()
        for schema in (2, 3, 4):
            for missing in ('embedded-home.qml', 'embedded-home.js'):
                with self.subTest(schema=schema, missing=missing), self.fixture(schema, embedded=True) as runtime:
                    (runtime/missing).unlink()
                    with self.assertRaises(FileNotFoundError):
                        p.manifest()

class ProvisionTests(unittest.TestCase):
    def setUp(self):
        # Stock-route initialization has its own real journal/readback fixture.
        self.real_firmware_registration=p.register_firmware_access
        firmware=patch.object(p,'register_firmware_access',return_value=True);firmware.start();self.addCleanup(firmware.stop)
        context=patch.object(p,'prepare_stock_home')
        context.start();self.addCleanup(context.stop)

    def original(self):
        return {'service':'[D-BUS Service]\nName='+p.NAME+'\nExec=/usr/bin/run-js-service -n '+str(p.SERVICE)+'\n',
                'role':json.dumps({'appId':p.NAME,'allowedNames':['*'],'permissions':[{'outbound':['*']}]}),
                'client':'{}','api':'{}'}
    def test_narrow_rules(self):
        result=p.plan(self.original())
        self.assertIn(str(p.RUNNER).encode(),result['service'])
        role=json.loads(result['role'])
        self.assertEqual(role['allowedNames'],[p.NAME])
        self.assertNotIn('*',role['permissions'][0]['outbound'])
        api=json.loads(result['api'])
        self.assertEqual(api['activities.callbacks'],[p.NAME+'/boot'])
        self.assertEqual(json.loads(result['client']),{p.NAME:['activity.operation'], 'com.cleanyourtv.root.preview':[p.NAME+'.control'], 'com.cleanyourtv.root.preview-*':[p.NAME+'.control']})
        self.assertEqual(api[p.NAME+'.control'],[p.NAME+'/'+x for x in ('status','restore','enable','confirm','listApps')])
        self.assertIn('com.cleanyourtv.root.preview', json.loads(result['role'])['permissions'][0]['inbound'])
        self.assertIn('com.cleanyourtv.root.preview-*', json.loads(result['role'])['permissions'][0]['inbound'])
        self.assertNotIn(p.NAME+'/trial',str(api))
    def test_unexpected_launcher_and_app_refused(self):
        original=self.original();original['service']=original['service'].replace('/usr/bin/run-js-service','/bin/sh')
        with self.assertRaises(ValueError):p.plan(original)
        original=self.original();original['role']='{"appId":"other"}'
        with self.assertRaises(ValueError):p.plan(original)
    def test_no_manifest_before_registration(self):
        data={'version':1}
        with patch.object(p,'secure',return_value=json.dumps(data).encode()),patch.object(p,'manifest',return_value=data),patch.object(p,'rpc',return_value={'returnValue':True,'root':False}),patch.object(p,'write') as write:
            with self.assertRaises(ValueError):p.finalize()
            self.assertNotIn(p.STATE/'recovery-provision.json', [call.args[0] for call in write.call_args_list])
    def test_finalize_owned_registration(self):
        data={'version':1}
        with patch.object(p,'secure',return_value=json.dumps(data).encode()),patch.object(p,'manifest',return_value=data),patch.object(p,'rpc',return_value={'root':True,'registered':True,'activityName':p.NAME+'.recovery'}),patch.object(p,'write') as write,patch('startup_hook.install') as hook:
            p.finalize()
            hook.assert_called_once_with(p.secure,p.write)
            self.assertEqual(write.call_args[0][0],p.STATE/'recovery-provision.json')
            p.register_firmware_access.assert_called_once_with()
    def test_firmware_registration_reads_runtime_cli_envelope(self):
        from types import SimpleNamespace
        for outer,nested,granted,want in [(True,True,True,True),(True,True,False,False),(False,True,True,False),(True,False,True,False)]:
            with self.subTest(outer=outer,nested=nested,granted=granted),patch('python_binding.command',return_value='/usr/bin/python3'),patch.object(p.subprocess,'run',return_value=SimpleNamespace(stdout=json.dumps({'returnValue':outer,'result':{'returnValue':nested,'permissions_installed':granted}}).encode())):
                self.assertEqual(self.real_firmware_registration(),want)

    def test_optional_firmware_grant_failure_preserves_core_recovery_readiness(self):
        data={'version':1}
        with patch.object(p,'secure',return_value=b'{}'),patch.object(p,'manifest',return_value={}),patch.object(p,'rpc',return_value={'root':True,'registered':True,'activityName':p.NAME+'.recovery'}),patch.object(p,'write') as write,patch('startup_hook.install'),patch.object(p,'register_firmware_access',side_effect=ValueError('unsupported SDK ownership')):
            result=p.finalize()
            self.assertTrue(result['returnValue']);self.assertFalse(result['firmware_permissions_registered'])
            self.assertEqual(write.call_args[0][0],p.STATE/'recovery-provision.json')

    def test_runtime_drift_refuses_registration(self):
        with patch.object(p,'secure',return_value=b'{}'),patch.object(p,'manifest',return_value={'changed':True}),patch.object(p,'rpc') as rpc:
            with self.assertRaises(ValueError):p.finalize()
            rpc.assert_not_called()
    def test_stale_embedded_adapter_permission_blocks_beta_package_removal(self):
        rpc = MagicMock(return_value={'returnValue':True, 'api':{'/c1AdapterStatus':[p.LEASE_NAME+'.adapter-status']}})
        with patch.object(p, 'refresh') as refresh, patch.object(p.time, 'monotonic', side_effect=[0, 4]):
            with self.assertRaisesRegex(ValueError, 'LS2 registration restore unverified'):
                p.verify_beta_removal_registration(rpc)
        refresh.assert_called_once_with()
        self.assertEqual(rpc.call_count, 2)
        rpc.assert_called_with('com.webos.service.bus/queryServicePermissions', {'service':p.LEASE_NAME})

    def test_embedded_removal_requires_snapshot_and_exact_live_activation_absence(self):
        from runtime import c1_gate, transport
        missing = {'returnValue': False, 'errorCode': -1,
                   'errorText': 'Service does not exist: '+p.LEASE_NAME+'.'}
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder)
            (state/'home-backend.json').write_text('trusted fixture selection')
            with patch.object(p, 'STATE', state), patch.object(c1_gate, 'selection', return_value={'schema':4}), patch.object(p, 'verify_restored_files') as verify, patch.object(p, 'refresh') as refresh, patch.object(transport, 'call', return_value=missing) as call:
                with self.assertRaisesRegex(ValueError, 'snapshot'):
                    p.verify_beta_removal_registration(MagicMock())
                call.assert_not_called()
                saved = {'phase':'rolled-back'}
                p.verify_beta_removal_registration(MagicMock(), saved)
                verify.assert_called_with(saved)
                refresh.assert_called_once_with()
                self.assertEqual(call.call_args.args, ('luna://'+p.LEASE_NAME+'/c1AdapterStatus', {}))
                self.assertTrue(call.call_args.kwargs['named'])
                self.assertTrue(call.call_args.kwargs['allow_failure'])

    def test_embedded_removal_rejects_denied_malformed_and_resident_alias(self):
        from runtime import c1_gate, transport
        for reply in ({'returnValue':False,'errorCode':-1,'errorText':'Permission denied'},
                      {'returnValue':True,'adapter':'embedded-qml-v1','attached':False},
                      {'returnValue':False,'errorCode':False,'errorText':'Service does not exist: '+p.LEASE_NAME+'.'},
                      {'returnValue':False,'errorCode':-1,'errorText':'Service does not exist: '+p.LEASE_NAME+'.','extra':True}):
            with self.subTest(reply=reply), tempfile.TemporaryDirectory() as folder:
                state = Path(folder)
                (state/'home-backend.json').write_text('trusted fixture selection')
                with patch.object(p, 'STATE', state), patch.object(c1_gate, 'selection', return_value={'schema':4}), patch.object(p, 'verify_restored_files'), patch.object(p, 'refresh'), patch.object(transport, 'call', return_value=reply), patch.object(p.time, 'monotonic', side_effect=[0,0,4]), patch.object(p.time, 'sleep'):
                    with self.assertRaisesRegex(ValueError, 'activation retirement unverified'):
                        p.verify_beta_removal_registration(MagicMock(), {'phase':'rolled-back'})

    def test_retained_schema1_keeps_legacy_permission_verification(self):
        from runtime import c1_gate
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder)
            (state/'home-backend.json').write_text('trusted fixture selection')
            rpc = MagicMock(return_value={'returnValue':True, 'api':{}})
            with patch.object(p, 'STATE', state), patch.object(c1_gate, 'selection', return_value={'schema':1}), patch.object(p, 'verify_embedded_activation_retired') as embedded:
                p.verify_beta_removal_registration(rpc)
            embedded.assert_not_called()
            rpc.assert_called_once_with('com.webos.service.bus/queryServicePermissions', {'service':p.LEASE_NAME})

    def test_rollback_drift_before_mutation(self):
        entries={str(path):{'original':'x','original_sha256':p.sha(b'x'),'installed_sha256':p.sha(b'y')} for path in p.FILES.values()}
        saved={'version':1,'service':p.NAME,'files':entries}
        with patch.object(p,'secure',side_effect=[json.dumps(saved).encode(),b'drift']),patch.object(p,'rpc') as rpc,patch.object(p,'write') as write:
            with self.assertRaises(ValueError):p.rollback()
            rpc.assert_not_called();write.assert_not_called()

    def test_restore_pending_keeps_activity(self):
        entries={str(path):{'original':'x','original_sha256':p.sha(b'x'),'installed_sha256':p.sha(b'y')} for path in p.FILES.values()}
        saved={'version':1,'service':p.NAME,'files':entries}
        for state in ('recovering','conflict','superseded'):
            with patch.object(p,'disable_trials'),patch.object(p,'secure',side_effect=[json.dumps(saved).encode()]+[b'y']*4),patch.object(p,'rpc',return_value={'returnValue':True,'result':{'returnValue':True,'result':state}}) as rpc,patch.object(p,'write') as write:
                with self.assertRaises(ValueError):p.rollback()
                rpc.assert_called_once_with('restore');write.assert_not_called()
    def test_rpc_keeps_stdin_open_until_reply(self):
        child=MagicMock(); child.poll.return_value=None
        def read(*args):
            child.stdin.close.assert_not_called()
            return b'{"returnValue":true}'
        with patch.object(p.subprocess,'Popen',return_value=child) as popen,patch.object(p.select,'select',return_value=([child.stdout],[],[])),patch.object(p.os,'read',side_effect=read):
            self.assertTrue(p.rpc('status')['returnValue'])
            self.assertIs(popen.call_args.kwargs['stdin'],p.subprocess.PIPE)
            child.terminate.assert_called_once()
            child.wait.assert_called_once_with(timeout=1)
            child.communicate.assert_not_called()
            child.stdin.close.assert_called_once()
    def test_refresh_fixed_scan(self):
        with patch.object(p.Path,'is_file',return_value=True),patch.object(p.subprocess,'run') as run:
            self.assertTrue(p.refresh()['returnValue'])
            self.assertEqual(run.call_args.args[0],['/usr/bin/ls-control','scan-services'])

    def test_home_rpcs_have_fixed_uris_and_payloads(self):
        cases = (
            ('home-read','com.webos.settingsservice/getSystemSettings',{'category':'general','keys':['defaultApps']}),
            ('home-profiles','com.webos.service.systemprofile/getProfiles',{'names':['defaultApps','idleApp'],'subscribe':False}),
            ('home-stock','com.webos.service.applicationmanager/setDefaultApp',{'category':'home','appId':'com.webos.app.home'}),
        )
        for method,uri,payload in cases:
            child=MagicMock();child.poll.return_value=None
            with self.subTest(method=method), patch.object(p.subprocess,'Popen',return_value=child) as popen, patch.object(p.select,'select',return_value=([child.stdout],[],[])), patch.object(p.os,'read',return_value=b'{"returnValue":true}'):
                p.rpc(method)
                argv=popen.call_args.args[0]
                self.assertEqual(argv[:4],['/usr/bin/luna-send','-n','1','luna://'+uri])
                self.assertEqual(json.loads(argv[4]),payload)
        with patch.object(p.subprocess,'Popen') as popen, self.assertRaises(ValueError): p.rpc('setDefaultApp')
        popen.assert_not_called()

    def test_repeated_rollback_checks_restored_hashes_without_rpc(self):
        entries={str(path):{'original':'x','original_sha256':p.sha(b'x'),'installed_sha256':p.sha(b'y'),'mode':0o644,'uid':0,'gid':0} for path in p.FILES.values()}
        saved={'version':1,'service':p.NAME,'phase':'rolled-back','files':entries}
        info=MagicMock(st_mode=0o100644,st_uid=0,st_gid=0)
        # Keep stat mocked only for restored LS2 metadata. Cleanup ownership is
        # covered in its own suites; a global stat mock makes receipt.exists()
        # true on Linux even when no receipt exists on this test host.
        with patch.object(p,'secure',side_effect=[json.dumps(saved).encode()]+[b'x']*4),patch.object(p.Path,'stat',return_value=info),patch.object(p.os.path,'lexists',return_value=False),patch.object(p,'rpc') as rpc,patch.object(p,'write') as write,patch('system_permissions.remove') as permissions,patch('startup_hook.remove') as hook:
            self.assertTrue(p.rollback()['already_rolled_back'])
            rpc.assert_not_called();write.assert_not_called()
            permissions.assert_called_once_with(p.secure)
            hook.assert_called_once_with(p.secure)
        with patch.object(p,'secure',side_effect=[json.dumps(saved).encode(),b'drift']),patch.object(p.os.path,'lexists',return_value=False),patch.object(p,'rpc') as rpc:
            with self.assertRaises(ValueError):p.rollback()
            rpc.assert_not_called()

    def test_partial_restoration_resumes_without_service(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            paths={name:root/name for name in ('service','role','client','api')}
            entries={}
            for path in paths.values():
                path.write_bytes(b'installed');path.chmod(0o644)
                info=path.stat()
                entries[str(path)]={'original':'original','original_sha256':p.sha(b'original'),'installed_sha256':p.sha(b'installed'),'mode':0o644,'uid':info.st_uid,'gid':info.st_gid}
            snapshot=root/'ls2-provision-snapshot.json'
            snapshot.write_text(json.dumps({'version':1,'service':p.NAME,'files':entries}))
            real_write=p.write
            def interrupted(path,data,mode=0o600):
                if path == paths['role']:raise OSError('simulated power loss')
                real_write(path,data,mode)
            with patch.object(p,'STATE',root),patch.object(p,'FILES',paths),patch.object(p,'secure',side_effect=lambda path:path.read_bytes()),patch.object(p,'disable_trials'),patch.object(p.os,'chown'),patch.object(p,'rpc',side_effect=[{'result':{'returnValue':True,'result':'restored'}},{'returnValue':True}]) as rpc,patch.object(p,'write',side_effect=interrupted):
                with self.assertRaises(OSError):p.rollback()
                self.assertEqual(json.loads(snapshot.read_text())['phase'],'restoring')
                self.assertEqual(rpc.call_count,2)
            with patch.object(p,'STATE',root),patch.object(p,'FILES',paths),patch.object(p,'secure',side_effect=lambda path:path.read_bytes()),patch.object(p.os,'chown'),patch.object(p,'rpc') as rpc:
                self.assertTrue(p.rollback()['returnValue'])
                rpc.assert_not_called()
                self.assertTrue(p.rollback()['already_rolled_back'])
                self.assertTrue(all(path.read_bytes()==b'original' for path in paths.values()))



    def test_pending_permission_repair_is_journaled_and_resumable(self):
        original=self.original(); old={key:value.encode() for key,value in original.items()}
        saved={'version':1,'service':p.NAME,'files':{str(file):{'original':original[key],'original_sha256':p.sha(old[key]),'installed_sha256':p.sha(old[key]),'mode':0o644,'uid':0,'gid':0} for key,file in p.FILES.items()}}
        snapshot=p.STATE/'ls2-provision-snapshot.json'
        data={file:old[key] for key,file in p.FILES.items()};data[snapshot]=p.encoded(saved)
        writes=[]
        def write(path,content,mode=0o600):
            writes.append(path);data[path]=content
            if len(writes)==2: raise OSError('simulated interruption')
        with patch.object(p,'secure',side_effect=lambda path:data[path]),patch.object(p.os.path,'lexists',return_value=False),patch.object(p,'write',side_effect=write),patch.object(p.os,'chown'):
            with self.assertRaises(OSError):p.repair_pending()
            self.assertEqual(writes[0],snapshot)
            writes.append(None)
            self.assertTrue(p.repair_pending()['repaired_pending'])
        for key,file in p.FILES.items():self.assertEqual(data[file],p.plan(original)[key])

    def test_pending_repair_refuses_active_ready_state(self):
        with patch.object(p.os.path,'lexists',return_value=True),patch.object(p,'write') as write:
            with self.assertRaises(ValueError):p.repair_pending()
            write.assert_not_called()

    def test_explicit_pending_resume_accepts_only_recorded_original_or_owned_partial_writes(self):
        original=self.original();updated=p.plan(original)
        files=list(p.FILES.items())
        saved={'version':1,'service':p.NAME,'files':{str(path):{'original':original[key],'original_sha256':p.sha(original[key].encode()),'installed_sha256':p.sha(updated[key]),'mode':0o644,'uid':0,'gid':0} for key,path in files}}
        snapshot=p.STATE/'ls2-provision-snapshot.json';data={path:(original[key].encode() if i%2 else updated[key]) for i,(key,path) in enumerate(files)};data[snapshot]=p.encoded(saved)
        def write(path,raw,mode=0o600):data[path]=raw
        with patch.object(p,'secure',side_effect=lambda path:data[path]),patch.object(p.os.path,'lexists',return_value=False),patch.object(p,'manifest',return_value={'version':1,'mode':'recovery-only'}),patch.object(p,'write',side_effect=write),patch.object(p.os,'chown'):
            self.assertTrue(p.resume_pending()['repaired_pending'])
            self.assertTrue(all(data[path]==updated[key] for key,path in files))
            self.assertIn(p.STATE/'recovery-provision.pending.json',data)
            data[files[0][1]]=b'foreign edit'
            with self.assertRaisesRegex(ValueError,'drift'):p.resume_pending()
