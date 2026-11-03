import importlib.util,json,tempfile,unittest,subprocess,os
from pathlib import Path
from unittest.mock import patch
from scripts.theme_receiver import inject
spec=importlib.util.spec_from_file_location('private_provision',Path(__file__).parents[1]/'provision.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)

class PrivateServiceTests(unittest.TestCase):
 def test_explicit_receiver_capability_keeps_legacy_plan_unchanged(self):
  original={'service':'Exec=/usr/bin/run-js-service -n '+str(p.SERVICE),'role':json.dumps({'appId':p.NAME}),'client':'{}','api':'{}'}
  legacy=p.plan(original)
  fresh=p.plan(original, ['theme-receiver-v1'])
  methods=json.loads(fresh['api'])[p.NAME+'.control']
  for method in ('Start','Status','Read','Stop'):
   self.assertIn(p.NAME+'/themeReceiver'+method,methods)
   self.assertNotIn(p.NAME+'/themeReceiver'+method,json.loads(legacy['api'])[p.NAME+'.control'])
  self.assertEqual(p.plan(original),legacy)
  with self.assertRaises(ValueError):p.plan(original,['unknown'])
 def test_malformed_capabilities_are_rejected_and_old_snapshots_are_legacy(self):
  self.assertEqual(p.snapshot_capabilities({'version':1}),[])
  for invalid in (None,'theme-receiver-v1',{},['unknown'],['theme-receiver-v1','theme-receiver-v1']):
   with self.subTest(capabilities=invalid),self.assertRaises(ValueError):p.snapshot_capabilities({'capabilities':invalid})
 def test_fresh_apply_records_receiver_contract_for_future_repair(self):
  with tempfile.TemporaryDirectory() as tmp:
   state=Path(tmp);paths={key:state/key for key in ('service','role','client','api')}
   original={'service':'Exec=/usr/bin/run-js-service -n '+str(p.SERVICE),'role':json.dumps({'appId':p.NAME}),'client':'{}','api':'{}'}
   for key,path in paths.items():path.write_text(original[key])
   release={'capabilities':['theme-receiver-v1']}
   (state/'release.json').write_text(json.dumps(release))
   (state/'private').mkdir();(state/'private/services.json').write_text(json.dumps({'id':p.NAME}))
   with patch.object(p,'STATE',state),patch.object(p,'PRIVATE_SERVICE',state/'private'),patch.object(p,'FILES',paths),patch.object(p,'prepare_private_service'),patch.object(p,'manifest',return_value={'version':1}),patch.object(p,'secure',side_effect=lambda path:path.read_bytes()),patch.object(p.os,'geteuid',return_value=0),patch.object(p.os,'chown'):
    p.apply()
    saved=json.loads((state/'ls2-provision-snapshot.json').read_text())
    self.assertEqual(saved['capabilities'],['theme-receiver-v1'])
    before=(state/'ls2-provision-snapshot.json').read_bytes()
    p.repair_pending()
    self.assertEqual((state/'ls2-provision-snapshot.json').read_bytes(),before)
   expected=p.plan(original,['theme-receiver-v1'])
   for key,path in paths.items():self.assertEqual(path.read_bytes(),expected[key])
 def test_fresh_private_receiver_can_register_without_repository_imports(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp).resolve();src=root/'installed';src.mkdir();state=root/'state';state.mkdir()
   contents={name:(name+' fixture').encode() for name in p.PRIVATE_FILES}
   contents['service.js']=b"module.exports = require('./theme-receiver');\n"
   contents=inject(contents,standalone=True)
   contents['package.json']=b'{"name":"private-service-fixture","type":"commonjs"}'
   release={'files':{'usr/palm/services/'+p.NAME+'/'+name:p.sha(data) for name,data in contents.items()}}
   for name,data in contents.items():(src/name).write_bytes(data)
   (state/'release.json').write_text(json.dumps(release))
   with patch.object(p,'STATE',state),patch.object(p,'SERVICE',src),patch.object(p,'PRIVATE_SERVICE',state/'service'),patch.object(p,'RUNNER',state/'run-service'),patch.object(p,'SYSTEM_FILES',()),patch.object(p,'secure',side_effect=lambda path:path.read_bytes()):
    p.prepare_private_service();p.prepare_private_service()
   self.assertEqual(set(path.name for path in (state/'service').iterdir()),set(p.PRIVATE_FILES))
   # Load the actual copied closure, with no service files outside its private tree.
   js="require(process.argv[2]);var names=[];var receiver=require(process.argv[1])({register:function(n){names.push(n)}},{appId:'com.test',port:0});var expected=['themeReceiverRead','themeReceiverStart','themeReceiverStatus','themeReceiverStop','wallpaperCacheStart','wallpaperCacheWrite','wallpaperCacheCommit','wallpaperCacheKeepAlive','wallpaperCacheStop'];if(names.sort().join(',')!==expected.sort().join(','))throw Error('Private receiver method closure mismatch: '+names.join(','));receiver.start().then(function(s){if(receiver.status(s.sessionId).state!=='waiting')throw Error('not waiting');return receiver.stop(s.sessionId);}).catch(function(e){console.error(e);process.exit(1);});"
   for node in dict.fromkeys(['node']+([os.environ['NODE012']] if os.environ.get('NODE012') else [])):
    result=subprocess.run([node,'-e',js,str(state/'service/service.js'),str(Path('node_modules/core-js-bundle/minified.js').resolve())],capture_output=True,text=True,timeout=30)
    self.assertEqual(result.returncode,0,result.stderr)
 def test_exec_uses_private_bootstrap_not_homebrew(self):
  original={'service':'Exec=/usr/bin/run-js-service -n '+str(p.SERVICE),'role':json.dumps({'appId':p.NAME}),'client':'{}','api':'{}'}
  result=p.plan(original)['service'].decode()
  self.assertNotIn('org.webosbrew',result)
  self.assertIn('/var/lib/clean-your-tv-root/',result)
  self.assertNotIn(' -n '+str(p.SERVICE),result)
 def test_private_copy_checks_hashes_and_is_idempotent(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp).resolve();src=root/'installed';src.mkdir();state=root/'state';state.mkdir()
   files={}
   for name in (*p.PRIVATE_FILES, 'app-inventory.js'):
    data=(name+' fixture').encode();(src/name).write_bytes(data)
    files['usr/palm/services/'+p.NAME+'/'+name]=p.sha(data)
   (state/'release.json').write_text(json.dumps({'files':files}))
   with patch.object(p,'STATE',state),patch.object(p,'SERVICE',src),patch.object(p,'PRIVATE_SERVICE',state/'service'),patch.object(p,'RUNNER',state/'run-service'),patch.object(p,'SYSTEM_FILES',()),patch.object(p,'secure',side_effect=lambda path:path.read_bytes()):
    p.prepare_private_service();p.prepare_private_service()
    self.assertEqual((state/'service/service.js').read_bytes(),(src/'service.js').read_bytes())
    inventory=state/'service/app-inventory.js'
    self.assertTrue(inventory.is_file(), 'Privileged service inventory dependency must be copied')
    self.assertEqual(inventory.read_bytes(),(src/'app-inventory.js').read_bytes())
    self.assertEqual((state/'run-service').stat().st_mode & 0o777,0o700)
    inventory.write_text('changed')
    with self.assertRaises(ValueError):p.prepare_private_service()
 def test_hash_mismatch_creates_no_runner(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp).resolve();src=root/'installed';src.mkdir();state=root/'state';state.mkdir()
   (state/'release.json').write_text(json.dumps({'files':{}}))
   with patch.object(p,'STATE',state),patch.object(p,'SERVICE',src),patch.object(p,'PRIVATE_SERVICE',state/'service'),patch.object(p,'RUNNER',state/'run-service'),patch.object(p,'SYSTEM_FILES',()):
    with self.assertRaises((ValueError,FileNotFoundError)):p.prepare_private_service()
    self.assertFalse((state/'run-service').exists())
