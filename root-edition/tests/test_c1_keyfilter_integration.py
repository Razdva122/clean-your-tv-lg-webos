"""Build and LS2 boundaries of the mount-free C1 routing mode."""
import json
import os
from contextlib import ExitStack, contextmanager
from unittest.mock import patch
from pathlib import Path
import tempfile
import unittest
from test_c1_gate_bundle import load, static_arm


class KeyfilterIntegrationTests(unittest.TestCase):
    def test_new_bundle_selects_only_compositor_assets_and_guard(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            helper = root / 'guardian'
            helper.write_bytes(static_arm())
            load('build').build(root / 'bundle', experimental_c1_keyfilter=helper)
            manifest = load('deploy').verify_bundle(root / 'bundle', allow_experimental=True)
            release = json.loads((root / 'bundle/release.json').read_bytes())
            self.assertEqual(release['routing'], 'compositor-keyfilter-v1')
            self.assertEqual(release['compositor_admission'],3)
            self.assertIn('c1-keyfilter-v1', release['capabilities'])
            for name in ('c1-keyfilter-guard', 'c1_keyfilter.py', 'c1-home-filter.js', 'c1_gate.py'):
                self.assertIn('runtime/' + name, manifest['files'])
            self.assertNotIn('runtime/c1-home-gate', manifest['files'])
            from cytv.package import data_files
            package = next((root/'bundle').glob('*.ipk'))
            contents=data_files(package.read_bytes())
            self.assertFalse('usr/palm/services/com.cleanyourtv.root.preview.service/c1-lease.js' in contents,'private service inventory remains compatible with retained OTA workers')
            self.assertNotIn(b"require('./c1-lease')",contents['usr/palm/services/com.cleanyourtv.root.preview.service/service.js'])
            services = json.loads(contents['usr/palm/services/com.cleanyourtv.root.preview.service/services.json'])
            self.assertEqual(services['services'], [{'name':'com.cleanyourtv.root.preview.service'}], 'developer IPK must only advertise application-prefixed services')
            with self.assertRaises(ValueError):
                load('deploy').verify_bundle(root / 'bundle')

    def test_lease_permission_is_only_for_compositor_and_only_in_new_mode(self):
        provision = load('provision')
        original = {'service':'[D-BUS Service]\nName='+provision.NAME+'\nExec=/usr/bin/run-js-service -n ' + str(provision.SERVICE),
                    'role':json.dumps({'appId':provision.NAME}).encode()}
        normal = provision.plan(original, ['theme-receiver-v1','wallpaper-media-v1'])
        self.assertNotIn('com.webos.surfacemanager', json.loads(normal['client']))
        revised = provision.plan(original, ['theme-receiver-v1','wallpaper-media-v1','c1-keyfilter-v1'])
        client, api = (json.loads(revised[key]) for key in ('client','api'))
        self.assertEqual(client['com.webos.surfacemanager'], [provision.NAME+'.c1lease'])
        self.assertEqual(api[provision.NAME+'.c1lease'], [provision.LEASE_NAME+'/c1Lease',provision.LEASE_NAME+'/c1Home'])
        self.assertIn('Name='+provision.NAME+';'+provision.LEASE_NAME, revised['service'].decode())
        self.assertNotIn('lease_service',revised)
        self.assertNotIn('com.webos.surfacemanager', json.loads(revised['role'])['allowedNames'])
        self.assertNotIn(provision.NAME+'.control', client['com.webos.surfacemanager'])


class PrivateAliasProvisionTests(unittest.TestCase):
    @contextmanager
    def fixture(self):
        provision = load('provision')
        with tempfile.TemporaryDirectory() as folder, ExitStack() as stack:
            root=Path(folder); state=root/'state';state.mkdir();base=root/'ls2';service=state/'service';service.mkdir()
            files={key:base/sub/(provision.NAME+suffix) for key,sub,suffix in (('service','services.d','.service'),('role','roles.d','.service.json'),('client','client-permissions.d','.service.json'),('api','api-permissions.d','.api.json'))}
            original={'service':'[D-BUS Service]\nName='+provision.NAME+'\nExec=/usr/bin/run-js-service -n '+str(provision.SERVICE)+'\n','role':json.dumps({'appId':provision.NAME}),'client':'{}','api':'{}'}
            for key,path in files.items():path.parent.mkdir(parents=True,exist_ok=True);path.write_text(original[key]);path.chmod(0o600)
            (service/'services.json').write_text(json.dumps({'id':provision.NAME}))
            (state/'release.json').write_text(json.dumps({'capabilities':provision.COMPOSITOR_CAPABILITIES}))
            for name,value in {'STATE':state,'BASE':base,'FILES':files,'PRIVATE_SERVICE':service,'RUNNER':state/'run-recovery-service'}.items():stack.enter_context(patch.object(provision,name,value))
            stack.enter_context(patch.object(provision,'secure',side_effect=lambda path:path.read_bytes()))
            stack.enter_context(patch.object(provision,'prepare_private_service'))
            stack.enter_context(patch.object(provision,'manifest',return_value={'version':1}))
            stack.enter_context(patch.object(provision.os,'geteuid',return_value=0))
            stack.enter_context(patch.object(provision.os,'chown'))
            yield provision,state,base/'services.d'/(provision.LEASE_NAME+'.service'),original,files

    def test_shared_activation_is_snapshotted_and_exactly_restored(self):
        with self.fixture() as (p,state,alias,original,files):
            p.apply();saved=json.loads((state/'ls2-provision-snapshot.json').read_text())
            self.assertEqual(set(saved['files']),{str(path) for path in files.values()})
            self.assertEqual(saved['files'][str(files['service'])]['original'],original['service'])
            self.assertIn('Name='+p.NAME+';'+p.LEASE_NAME,files['service'].read_text());self.assertFalse(alias.exists())
            with patch.object(p,'disable_trials'),patch.object(p,'rpc',return_value={'returnValue':True,'result':{'returnValue':True,'result':'restored'}}),patch('system_permissions.remove'),patch('startup_hook.remove'):
                p.rollback();self.assertTrue(p.rollback()['already_rolled_back'])
            for key,path in files.items():self.assertEqual(path.read_text(),original[key])

    def test_shared_activation_pending_repair_uses_original_four_file_contract(self):
        with self.fixture() as (p,state,alias,original,files):
            p.apply();files['service'].write_text(original['service']);p.repair_pending(allow_original=True)
            self.assertIn('Name='+p.NAME+';'+p.LEASE_NAME,files['service'].read_text());self.assertFalse(alias.exists());p.repair_pending()

    def test_foreign_activation_names_or_changed_record_are_never_overwritten(self):
        with self.fixture() as (p,state,alias,original,files):
            foreign=original['service'].replace('Name='+p.NAME,'Name='+p.NAME+';foreign.service')
            files['service'].write_text(foreign)
            with self.assertRaises(ValueError):p.apply()
            self.assertEqual(files['service'].read_text(),foreign)
            files['service'].write_text(original['service']);p.apply();files['service'].write_text('concurrent edit')
            with patch.object(p,'rpc') as rpc,self.assertRaises(ValueError):p.rollback()
            rpc.assert_not_called();self.assertEqual(files['service'].read_text(),'concurrent edit')

    def test_updater_repairs_shared_activation_after_package_replacement(self):
        from types import SimpleNamespace
        from updater.device import Device
        with self.fixture() as (p,state,alias,original,files):
            p.apply();files['service'].write_text(original['service'])
            device=Device.__new__(Device);device.code=Path(__file__).parents[1];device.root_state=state
            spec=SimpleNamespace(loader=SimpleNamespace(exec_module=lambda module:None))
            with patch('importlib.util.spec_from_file_location',return_value=spec),patch('importlib.util.module_from_spec',return_value=p),patch('updater.device.safe_bytes',side_effect=lambda path,**kwargs:path.read_bytes()),patch.object(p,'refresh'),patch.object(p,'rpc',return_value={'root':True}):
                device.repair_registration()
            self.assertIn('Name='+p.NAME+';'+p.LEASE_NAME,files['service'].read_text());self.assertFalse(alias.exists())
