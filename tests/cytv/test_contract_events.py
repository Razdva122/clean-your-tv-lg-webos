"""Literal wire contracts and hostile-input checks for non-authoritative events."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
BASE = dict(schema=1, component='storage', operation='inspect', phase='read',
            field='mode', expected='private', actual={'mode': 420}, decision='refuse', count=1)

class ContractEventsTests(unittest.TestCase):
    def test_literal_metadata_and_rejection_vectors_match_raw_legacy_js(self):
        from cytv import contract_events as events
        vectors = [BASE, dict(BASE, actual={'type':'SECRET', 'category':'SECRET', 'path':'SECRET',
                    'mode':True, 'size':-1, 'uid':0, 'nested':{'token':'SECRET'}}),
                   dict(BASE, decision='SECRET'), dict(BASE, field='../SECRET'),
                   dict(BASE, actual={'type':'string','length':6,'code':-13,'errno':13}),
                   dict(BASE, actual={'mode':4096,'size':2**54})]
        expected = [BASE, dict(BASE, actual={'uid':0}), None, None,
                    dict(BASE, actual={'type':'string','length':6,'code':-13,'errno':13}),
                    dict(BASE, actual={})]
        self.assertEqual([events.normalize(v) for v in vectors], expected)
        for runtime in dict.fromkeys(filter(None, ['node', os.getenv('NODE010'), os.getenv('NODE01025'), os.getenv('NODE012')])):
            code = "var e=require('./native/app/contract-events');var v=JSON.parse(process.argv[1]);console.log(JSON.stringify(v.map(e.normalize)));"
            raw = subprocess.check_output([runtime, '-e', code, json.dumps(vectors)], cwd=ROOT, text=True)
            self.assertEqual(json.loads(raw), expected)
            self.assertNotIn('SECRET', raw)

    def test_exact_builtin_summary_does_not_invoke_hostile_hooks(self):
        from cytv import contract_events as events
        class Hostile(dict):
            def __len__(self): raise AssertionError('called')
            def __str__(self): raise AssertionError('called')
        self.assertEqual(events.describe(Hostile(token='SECRET')), {'type':'unknown'})
        self.assertEqual(events.describe('🔐'), {'type':'string','length':2})
        self.assertEqual(events.describe({'secret':1}), {'type':'object','length':1})
        self.assertEqual(events.describe(True), {'type':'boolean'})

    def test_recorder_retains_first_and_recent_aggregates_and_swallows_emit_failure(self):
        from cytv import contract_events as events
        def fail(value): raise RuntimeError('SECRET')
        recorder = events.Recorder(fail)
        recorder.record(BASE)
        for _ in range(50): recorder.record(BASE)
        for i in range(100): recorder.record(dict(BASE, field='field'+str(i)))
        snapshot = recorder.snapshot()
        self.assertEqual(snapshot['events'][0]['count'], 51)
        self.assertEqual(snapshot['events'][-1]['field'], 'field99')
        self.assertEqual(len(snapshot['events']), 32)
        self.assertEqual(snapshot['dropped'], 69)
        self.assertLessEqual(len(json.dumps(snapshot).encode()), 16384)
        self.assertTrue(all(len(json.dumps(e).encode()) <= 512 for e in snapshot['events']))
        self.assertNotIn('SECRET', json.dumps(snapshot))
        snapshot['events'][0]['actual']['mode'] = 999
        self.assertEqual(recorder.snapshot()['events'][0]['actual'], {'mode':420})
        self.assertEqual(events.safe_events([BASE, dict(BASE, decision='SECRET')]), [BASE])

    def test_hostile_js_objects_and_emitters_cannot_escape(self):
        code = """var a=require('assert'),e=require('./native/app/contract-events');
        var bad={};Object.defineProperty(bad,'schema',{get:function(){throw Error('SECRET');}});
        a.equal(e.normalize(bad),null);a.deepEqual(e.describe(new String('SECRET')),{type:'unknown'});
        var r=e.create(function(){throw Error('SECRET');});var base=JSON.parse(process.argv[1]);
        r.record(base);for(var i=0;i<100;i++){r.record(base);}for(i=0;i<100;i++){base.field='field'+i;r.record(base);}
        var s=r.snapshot();a.equal(s.events[0].count,101);a.equal(s.events.length,32);a.equal(s.dropped,69);
        a.ok(JSON.stringify(s).length<=16384);s.events.forEach(function(v){a.ok(JSON.stringify(v).length<=512);});
        a.equal(e.safeEvents({schema:1,events:[bad]}).length,0);"""
        for runtime in dict.fromkeys(filter(None, ['node', os.getenv('NODE010'), os.getenv('NODE01025'), os.getenv('NODE012')])):
            subprocess.run([runtime,'-e',code,json.dumps(BASE)], cwd=ROOT, check=True)
        subprocess.run(['node','-e', "require('acorn').parse(require('fs').readFileSync('native/app/contract-events.js','utf8'),{ecmaVersion:5})"], cwd=ROOT, check=True)

class TrustedSourcesTests(unittest.TestCase):
    def test_allowlist_and_packaged_missing_fail_closed(self):
        from cytv import tv_sources
        self.assertEqual(tv_sources.trusted_source('contract-events'), (ROOT/'native/app/contract-events.js').read_text())
        with self.assertRaises(ValueError): tv_sources.trusted_source('../../SECRET')
        with tempfile.TemporaryDirectory() as tmp, patch.object(tv_sources,'__file__',str(Path(tmp)/'cytv/tv_sources.py')), patch.object(sys,'frozen',True,create=True):
            with self.assertRaises(FileNotFoundError): tv_sources.trusted_source('contract-events')

    def test_staged_and_source_bytes_are_identical_and_adapter_is_self_contained(self):
        from cytv import tv_sources
        with tempfile.TemporaryDirectory() as tmp:
            tv_sources.stage_sources(Path(tmp)/'cytv/tv')
            for name in ('contract-events','state-permissions'):
                self.assertEqual((Path(tmp)/'cytv/tv'/ (name+'.js')).read_bytes(), (ROOT/'native/app'/(name+'.js')).read_bytes())
        code = tv_sources.node_adapter('contract-events', "console.log(JSON.stringify(contract.describe('SECRET')));")
        # Send the full adapter over stdin, as on the TV, without Windows argv limits.
        result = subprocess.check_output(['node'],input=code,cwd=tempfile.gettempdir(),text=True)
        self.assertEqual(json.loads(result), {'type':'string','length':6})
        code = tv_sources.node_adapter('contract-events', "throw new Error('SECRET');")
        result = subprocess.run(['node'],input=code,capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertNotIn('SECRET', result.stdout+result.stderr)
        self.assertEqual(json.loads(result.stdout)['schema'],1)

class ResourceDeliveryTests(unittest.TestCase):
    def test_helper_app_and_service_ship_event_dependency(self):
        import runpy
        from cytv import package
        build = runpy.run_path(str(ROOT/'scripts/build-cytv.py'))
        app = {'appinfo.json': b'{"id":"com.local.nativehome","version":"0.6.18","type":"native"}',
               'state-permissions.js': (ROOT/'native/app/state-permissions.js').read_bytes(),
               'contract-events.js': (ROOT/'native/app/contract-events.js').read_bytes()}
        service = {'services.json':(ROOT/'native/service/services.json').read_bytes()}
        files = package.data_files(build['pack_app'](app,service,helper=True))
        self.assertEqual(files['usr/palm/applications/com.local.nativehome/contract-events.js'],
                         files['usr/palm/services/com.local.nativehome.service/contract-events.js'])

    def test_android_stages_exact_host_resources(self):
        import runpy
        stage = runpy.run_path(str(ROOT/'android/stage.py'))
        with tempfile.TemporaryDirectory() as tmp:
            project=Path(tmp)
            (project/'cytv').mkdir();(project/'cytv/__init__.py').write_text('')
            (project/'lgtv.py').write_text('');(project/'release-versions.json').write_text('{}')
            payload=project/'build/cytv/payload';payload.mkdir(parents=True);(payload/'payload.json').write_text('{}')
            with patch.dict(stage['main'].__globals__, {'ROOT':project,'verify_payload':lambda _: {'files':{}}}), patch('subprocess.check_output',return_value='fixture'):
                stage['main']()
            for name in ('contract-events','state-permissions'):
                self.assertEqual((project/'android/app/build/generated/python/cytv/tv'/(name+'.js')).read_bytes(),
                                 (ROOT/'native/app'/(name+'.js')).read_bytes())

    def test_cli_freezer_stages_and_passes_both_trusted_resources(self):
        import runpy
        build=runpy.run_path(str(ROOT/'scripts/build-cytv.py'))
        with tempfile.TemporaryDirectory() as tmp:
            project=Path(tmp)
            def run(command, **kwargs):
                if 'PyInstaller' in command:
                    specs=[command[i+1] for i,v in enumerate(command) if v=='--add-data']
                    spec=next(v for v in specs if v.endswith(os.pathsep+'cytv/tv'))
                    staged=Path(spec.rsplit(os.pathsep,1)[0])
                    for name in ('contract-events','state-permissions'):
                        self.assertEqual((staged/(name+'.js')).read_bytes(),(ROOT/'native/app'/(name+'.js')).read_bytes())
            with patch.dict(build['main'].__globals__, {'ROOT':project,'build_payload':lambda:project/'payload'}), patch.object(sys,'argv',['build']), patch('subprocess.run',side_effect=run):
                build['main']()

class EventBoundaryTests(unittest.TestCase):
    def test_repeat_growth_cannot_drop_first_or_exceed_wire_budget(self):
        from cytv import contract_events as events
        # Fixed metadata starts within the 512-byte limit; repeat counts grow.
        event=dict(BASE, component='c'*32, operation='o'*32, phase='p'*32,
                   field='f'*64, expected='e'*32, actual={'type':'object','length':9007199254740991,
                   'uid':2147483647,'gid':2147483647,'mode':4095,'size':9007199254740991,
                   'limit':9007199254740991,'code':-2147483648,'errno':4095}, first=9007199254740991,count=9999999)
        recorder=events.Recorder()
        recorder.record(event)
        for _ in range(100):recorder.record(event)
        for i in range(40):recorder.record(dict(event,field='f'*62+str(i).zfill(2)))
        snapshot=recorder.snapshot()
        code="var e=require('./native/app/contract-events'),r=e.create(),v=JSON.parse(process.argv[1]);r.record(v);for(var i=0;i<100;i++)r.record(v);for(i=0;i<40;i++){var c=JSON.parse(JSON.stringify(v));c.field=new Array(63).join('f')+('0'+i).slice(-2);r.record(c);}console.log(JSON.stringify(r.snapshot()));"
        for runtime in dict.fromkeys(filter(None,['node',os.getenv('NODE010'),os.getenv('NODE01025'),os.getenv('NODE012')])):
            actual=json.loads(subprocess.check_output([runtime,'-e',code,json.dumps(event)],cwd=ROOT,text=True))
            self.assertEqual(actual,snapshot)
        self.assertEqual(snapshot['events'][0]['field'],'f'*64)
        self.assertLessEqual(len(json.dumps(snapshot,separators=(',',':')).encode()),16384)
        self.assertTrue(all(len(json.dumps(e,separators=(',',':')).encode())<=512 for e in snapshot['events']))

    def test_adapter_refuses_untrusted_modules_and_packaged_resource_matches_source(self):
        from cytv import tv_sources
        with tempfile.TemporaryDirectory() as tmp:
            package=Path(tmp)/'cytv';tv_sources.stage_sources(package/'tv')
            with patch.object(tv_sources,'__file__',str(package/'tv_sources.py')):
                self.assertEqual(tv_sources.trusted_source('contract-events'), (ROOT/'native/app/contract-events.js').read_text())
        # Test the resolver through a canonical factory rather than host code.
        source="module.exports=require('/tmp/SECRET');"
        with patch.object(tv_sources,'trusted_source',return_value=source):code=tv_sources.node_adapter('contract-events','contract();')
        result=subprocess.run(['node','-e',code],capture_output=True,text=True)
        self.assertEqual(result.returncode,1)
        self.assertNotIn('SECRET',result.stdout+result.stderr)

class AndroidMissingResourceTests(unittest.TestCase):
    def test_android_missing_bundle_never_uses_even_present_repository_source(self):
        from cytv import tv_sources
        with patch.object(sys,'getandroidapilevel',lambda:24,create=True):
            with self.assertRaises(FileNotFoundError):tv_sources.trusted_source('contract-events')

class ChangingGetterPrivacyTests(unittest.TestCase):
    def test_each_normalized_input_is_captured_once_before_validation(self):
        code = """var a=require('assert'),e=require('./native/app/contract-events');
        var base=JSON.parse(process.argv[1]);base.first=123;base.last=456;
        function fixture(field, metadata) {
          var value=JSON.parse(JSON.stringify(base)),target=metadata?value.actual:value;
          var good=target[field],reads=0;
          Object.defineProperty(target,field,{enumerable:true,get:function(){
            reads++;return reads===1?good:{token:'SECRET_RAW',toJSON:function(){throw Error('serialized raw input');}};
          }});
          return {value:value,reads:function(){return reads;}};
        }
        ['schema','component','operation','phase','field','expected','actual','decision','count','first','last'].forEach(function(field){
          ['normalize','safeEvents'].forEach(function(method){
            var f=fixture(field,false),clean=method==='normalize'?e.normalize(f.value):e.safeEvents({schema:1,events:[f.value]})[0];
            a.deepEqual(clean,base,method+': '+field);a.equal(f.reads(),1,method+': '+field+' read count');
            a.equal(JSON.stringify(clean).indexOf('SECRET_RAW'),-1);
          });
        });
        var f=fixture('mode',true);a.deepEqual(e.normalize(f.value),base);a.equal(f.reads(),1);
        """
        for runtime in dict.fromkeys(filter(None,['node',os.getenv('NODE010'),os.getenv('NODE01025'),os.getenv('NODE012')])):
            subprocess.run([runtime,'-e',code,json.dumps(BASE)],cwd=ROOT,check=True)
