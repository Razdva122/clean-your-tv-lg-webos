"""Real adapter → transport → retained standard-report contract evidence."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from cytv import contract_events as events, diagnostic_context, diagnostics, state, tv_sources
from cytv.errors import TVCommandError
from cytv.transport import SSH

ROOT = Path(__file__).resolve().parents[2]

def fact(**changes):
    return dict(dict(schema=1, component='storage', operation='inspect', phase='validate',
                     field='apps', expected='trusted-owner', actual={'uid':123, 'mode':420},
                     decision='refuse', count=1), **changes)

class ContractReportTests(unittest.TestCase):
    def failed(self, raw, status=17):
        remote = SSH.__new__(SSH)
        remote.channel = Mock(return_value=Mock())
        def chunks(*_):
            yield raw
            raise TVCommandError(status)
        remote.chunks = chunks
        try:
            remote.run('fixed command')
        except TVCommandError as error:
            return error
        self.fail('failed command passed')

    def test_storage_adapter_supplies_where_rule_and_safe_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp).resolve()/'state'
            directory.mkdir(mode=0o770)
            (directory/'apps.json').symlink_to('/PRIVATE-CREDENTIAL')
            code=tv_sources.node_adapter('state-permissions',
                "contract.inspectConfiguration(process.argv[1]);")
            result=subprocess.run(['node','-e',code,str(directory)],capture_output=True)
            self.assertEqual(result.returncode,1)
            envelope=json.loads(result.stdout)
            self.assertEqual(envelope['error'],'contract-error')
            self.assertTrue(envelope['events'])
            event=envelope['events'][0]
            self.assertEqual(event['field'],'apps')
            self.assertEqual(event['expected'],'single-regular-file')
            self.assertEqual(event['phase'],'read')
            self.assertEqual(event['operation'],'inspect')
            self.assertEqual(event['decision'],'refuse')
            self.assertNotIn('PRIVATE',json.dumps(envelope))
            store=state.Store(Path(tmp)/'host');profile={'host':'PRIVATE','edition':'no-root'}
            with self.assertRaises(TVCommandError):
                with diagnostic_context.operation_context(store,profile):
                    store.begin(profile,'install')
                    error=self.failed(result.stdout,1)
                    raise error
            report=json.loads(diagnostics.create_report(store,'install',profile,'configure-helper',error).read_text())
            self.assertEqual(report['first_failure']['contract_events'],envelope['events'])


    def test_adapter_diagnostic_failure_still_emits_fixed_empty_error(self):
        original=tv_sources.trusted_source
        def source(name):
            if name=='contract-events':
                return "module.exports={safeEvents:function(){throw Error('PRIVATE-emitter');}};"
            return original(name)
        with patch.object(tv_sources,'trusted_source',side_effect=source):
            code=tv_sources.node_adapter('state-permissions',"throw Error('PRIVATE-original');")
        result=subprocess.run(['node','-e',code],capture_output=True,text=True)
        self.assertEqual(result.stdout,json.dumps({'schema':1,'error':'contract-error','events':[]},separators=(',',':')))
        self.assertEqual(result.returncode,1)
        self.assertNotIn('PRIVATE',result.stdout+result.stderr)

    def test_checked_runtime_log_rotation_collection_counts_and_unsafe_replacement(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = r"""
var fs=require('fs'),a=require('assert'),p=require('./native/app/state-permissions'),e=require('./native/app/contract-events'),d=process.argv[1];
a.throws(function(){p.appendLog(d,new Array(50001).join('€'));});a.equal(fs.readdirSync(d).length,0);
var f={schema:1,component:'power',operation:'observe',phase:'normalize',field:'processing',expected:'firmware-processing',actual:{type:'string',length:12},decision:'retain'};
var r=e.create();for(var i=0;i<70;i++)r.record(f);
p.appendLog(d,JSON.stringify({event:'contract-snapshot',contract:r.snapshot()}));
p.appendLog(d,JSON.stringify({event:'contract-snapshot',contract:r.snapshot()}));
r.record(f);p.appendLog(d,JSON.stringify({event:'contract-snapshot',contract:r.snapshot()}));
var v=p.readLogEvents(d);a.equal(v.telemetry,'read');a.equal(v.events[0].count,71);
f.field='PrivateCredentialMarker';p.appendLog(d,JSON.stringify({event:'contract-event',contract:f}));
p.appendLog(d,JSON.stringify({event:'raw',key:'PRIVATE'}));
a.equal(JSON.stringify(p.readLogEvents(d)).indexOf('PRIVATE'),-1);
a.equal(JSON.stringify(p.readLogEvents(d)).indexOf('PrivateCredentialMarker'),-1);
for(i=0;i<200;i++)p.appendLog(d,new Array(1000).join('x'));
a.ok(fs.statSync(d+'/controller.log').size<=131072);a.ok(fs.statSync(d+'/controller.log.previous').size<=131072);
var before=fs.readFileSync(d+'/controller.log','utf8');fs.unlinkSync(d+'/controller.log.previous');fs.symlinkSync(d+'/victim',d+'/controller.log.previous');
fs.writeFileSync(d+'/victim','retained');a.throws(function(){p.appendLog(d,new Array(130000).join('x'));});
a.equal(fs.readFileSync(d+'/controller.log','utf8'),before);a.equal(fs.readFileSync(d+'/victim','utf8'),'retained');
a.equal(p.readLogEvents(d).telemetry,'unavailable');
fs.unlinkSync(d+'/controller.log.previous');fs.unlinkSync(d+'/controller.log');fs.symlinkSync(d+'/victim',d+'/controller.log');
a.throws(function(){p.appendLog(d,'unsafe');});a.equal(fs.readFileSync(d+'/victim','utf8'),'retained');
fs.unlinkSync(d+'/controller.log');fs.writeFileSync(d+'/controller.log','prior');
var open=fs.openSync,swapped=false;
fs.openSync=function(name,flags){if(name==='controller.log' && !swapped){swapped=true;fs.unlinkSync(name);fs.symlinkSync(d+'/victim',name);}return open.apply(fs,arguments);};
a.throws(function(){p.appendLog(d,'unsafe-race');});a.equal(fs.readFileSync(d+'/victim','utf8'),'retained');

"""
            result=subprocess.run(['node','-e',code,str(Path(tmp).resolve())],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)

    def test_storage_write_errno_keeps_original_error_and_fixed_stage_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            code=r"""
var fs=require('fs'),a=require('assert'),p=require('./native/app/state-permissions'),d=process.argv[1],write=fs.writeSync;
fs.writeSync=function(){var e=Error('PRIVATE');e.code='EACCES';e.errno=-13;throw e;};
try {p.atomicRecord(d,'control','{}');a.fail('write succeeded');}
catch(error) {
 a.equal(error.code,'EACCES');var v=error.contractEvents[0];
 a.equal(v.field,'staging');a.equal(v.phase,'write');a.equal(v.actual.errno,13);
 a.equal(v.operation,'record');a.equal(v.expected,'storage-io');
 a.equal(JSON.stringify(error.contractEvents).indexOf('PRIVATE'),-1);
}
a.equal(fs.readdirSync(d).length,0);
"""
            result=subprocess.run(['node','-e',code,str(Path(tmp).resolve())],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)

    def test_storage_retained_warning_and_staging_guard_keep_actual_decision_phase(self):
        with tempfile.TemporaryDirectory() as tmp:
            code=r"""
var fs=require('fs'),a=require('assert'),p=require('./native/app/state-permissions'),d=process.argv[1],chmod=fs.fchmodSync,stat=fs.fstatSync,logs=[];
fs.chmodSync(d,511);fs.fchmodSync=function(){var e=Error('PRIVATE');e.code='EPERM';e.errno=-1;throw e;};
a.equal(p(d,function(v){logs.push(v);},false),true);
a.equal(logs[0].contract.decision,'retain');a.equal(logs[0].contract.actual.mode,511);
fs.fchmodSync=chmod;fs.chmodSync(d,504);
fs.fstatSync=function(fd){var s=stat(fd);if(s.isFile())s.nlink=2;return s;};
try {p.atomicRecord(d,'control','{}');a.fail('unsafe stage passed');}
catch(error) {a.equal(error.contractEvents[0].field,'staging');a.equal(error.contractEvents[0].phase,'write');}
"""
            result=subprocess.run(['node','-e',code,str(Path(tmp).resolve())],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)

    def test_real_transport_context_first_failure_later_export_all_frontends(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=state.Store(Path(tmp))
            profile={'edition':'no-root','host':'PRIVATE-ADDRESS'}
            with self.assertRaises(TVCommandError):
                with diagnostic_context.operation_context(store, profile):
                    store.begin(profile,'install')
                    error=self.failed(json.dumps({'schema':1,'error':'contract-error','events':[fact()]}).encode())
                    raise error
            for frontend in ('console','desktop','android'):
                first=json.loads(diagnostics.create_report(store,'install',profile,'configure-helper',error,
                                                          {'frontend':frontend}).read_text())
                self.assertEqual(first['contract_events'],[])
                self.assertEqual(first['first_failure']['contract_events'],[fact()])
                self.assertEqual(first['ssh_command'],{'exit_status':17})
                with self.assertRaises(TVCommandError):
                    with diagnostic_context.operation_context(store,profile):
                        raise self.failed(b'PRIVATE status unavailable',23)
                later=json.loads(diagnostics.create_report(store,'status',profile,'status',TVCommandError(23),
                                                          {'frontend':frontend}).read_text())
                self.assertEqual(later['first_failure'],first['first_failure'])
                self.assertNotIn('PRIVATE',json.dumps(later))
            self.assertIsNone(events.current_recorder.get())

    def test_remote_envelope_is_exact_bounded_and_fixed_vocabulary(self):
        good={'schema':1,'error':'contract-error','events':[fact()]}
        large=dict(good,events=[fact(actual={'uid':i,'size':9007199254740991,'limit':9007199254740991,
                    'gid':2147483647,'mode':4095,'type':'object','length':9007199254740991}) for i in range(32)])
        self.assertGreater(len(json.dumps(large).encode()),4096)
        self.assertEqual(len(self.failed(json.dumps(large).encode()).contract_events),32)

        self.assertEqual(self.failed(json.dumps(good).encode()).contract_events,[fact()])
        bad=[dict(good,private='PRIVATE'),dict(good,schema=True),
             dict(good,events=[fact(field='PrivateCredentialMarker')]),
             dict(good,events=[dict(fact(),private='PRIVATE')]),
             dict(good,events=[fact(actual={'uid':123,'path':'PRIVATE'})]),
             dict(good,events=[fact()]*33)]
        for value in bad:
            with self.subTest(value=value):
                error=self.failed(json.dumps(value).encode())
                self.assertFalse(getattr(error,'contract_events',[]))
                self.assertEqual(error.exit_status,17)
                self.assertNotIn('PRIVATE',json.dumps(error.__dict__))
        huge=self.failed(json.dumps(dict(good,events=[fact()]*32,private='PRIVATE'*5000)).encode())
        self.assertFalse(getattr(huge,'contract_events',[]))

    def test_persisted_projection_rejects_identifiers_and_merges_one_global_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=state.Store(Path(tmp));profile={'edition':'no-root','host':'PRIVATE'}
            store.contract_events=[fact(actual={'uid':i}) for i in range(100)]
            error=TVCommandError(9);error.contract_events=[fact(actual={'uid':100+i}) for i in range(32)]
            report=json.loads(diagnostics.create_report(store,'install',profile,'configure-helper',error).read_text())
            projected=report['previous_attempt_failure']['contract_events']
            self.assertLessEqual(len(projected),32)
            self.assertLessEqual(len(json.dumps(projected).encode()),16384)
            self.assertEqual(projected[0]['actual'],{'uid':100})
            self.assertFalse(diagnostic_context.failure_summary({'contract_events':[fact(field='PrivateCredentialMarker')]}).get('contract_events'))

    def test_retained_flood_and_current_context_share_one_export_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=state.Store(Path(tmp));profile={'edition':'no-root','host':'PRIVATE'}
            store.begin(profile,'install')
            first=TVCommandError(7);first.contract_events=[fact(actual={'uid':i}) for i in range(32)]
            diagnostics.create_report(store,'install',profile,'configure-helper',first)
            current=TVCommandError(9);current.contract_events=[fact(actual={'uid':100})]
            report=json.loads(diagnostics.create_report(store,'status',profile,'status',current).read_text())
            nodes=[report,report['first_failure'],report['observation_failure']]
            all_events=[event for node in nodes for event in node.get('contract_events',[])]
            self.assertLessEqual(len(all_events),32)
            self.assertLessEqual(len(json.dumps(all_events).encode()),16384)
            self.assertIn(fact(actual={'uid':0}),all_events)
            self.assertIn(fact(actual={'uid':100}),all_events)
            self.assertEqual(len({json.dumps(e,sort_keys=True) for e in all_events}),len(all_events))
            retained=next((store.device_dir(profile)/'diagnostic-failures').glob('*.json'))
            self.assertEqual(len(json.loads(retained.read_text())['contract_events']),32)
            self.assertLess(retained.stat().st_size,65536)

    def test_runtime_collector_reads_only_fixed_projection_and_unavailable_is_explicit(self):
        remote=Mock()
        runtime=fact(component='power',operation='observe',phase='normalize',field='processing',
                     expected='firmware-processing',decision='retain',actual={'type':'string','length':12})
        remote.run.return_value=json.dumps({'schema':1,'telemetry':'read','events':[runtime]})
        info={}
        diagnostic_context.collect_contract_events(remote,info)
        self.assertEqual(info['contract_events'],[runtime])
        self.assertEqual(info['contract_telemetry'],'read')
        self.assertNotIn('tail ',remote.run.call_args.args[0])
        remote.run.side_effect=OSError('PRIVATE')
        diagnostic_context.collect_contract_events(remote,info)
        self.assertEqual(info['contract_telemetry'],'unavailable')
        self.assertEqual(info['contract_events'],[])
        remote.run.side_effect=None
        remote.run.return_value=json.dumps({'schema':1,'telemetry':'legacy','events':[]})
        diagnostic_context.collect_contract_events(remote,info)
        self.assertEqual(info['contract_telemetry'],'legacy')


    def test_real_runtime_probe_to_standard_report_preserves_safe_outcomes(self):
        import shlex
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp).resolve()
            source=r"""
var p=require('./native/app/state-permissions'),e=require('./native/app/contract-events'),r=e.create(),d=process.argv[1];
var power=require('./native/app/power-policy')().observe({state:'Active',processing:'PRIVATE'},1);
power.diagnostics.forEach(function(v){r.record(v);});
r.record(e.runtimeOutcome(31,31,null,false));
p.appendLog(d,JSON.stringify({event:'contract-snapshot',contract:r.snapshot()}));
"""
            subprocess.run(['node','-e',source,str(directory)],cwd=ROOT,check=True)
            class LocalProbe:
                def run(self,command,**kwargs):
                    args=shlex.split(command.split(' && ',1)[1])
                    code=args[2].replace('/media/developer/apps/usr/palm/applications/com.local.nativehome/state',str(directory))
                    result=subprocess.run(['node','-e',code],cwd=ROOT,capture_output=True,text=True,check=True)
                    return result.stdout
            info={};diagnostic_context.collect_contract_events(LocalProbe(),info)
            self.assertEqual(info['contract_telemetry'],'read')
            store=state.Store(directory/'host')
            report=json.loads(diagnostics.create_report(store,'status',None,'status',tv_info=info).read_text())
            self.assertEqual(len(report['contract_events']),2)
            self.assertTrue(any(e['actual'].get('os_code')==31 for e in report['contract_events']))
            self.assertTrue(any(e['actual'].get('length')==7 for e in report['contract_events']))
            self.assertNotIn('PRIVATE',json.dumps(report))

    def test_host_recovery_facts_and_emitter_failure_are_best_effort(self):
        from cytv.recovery import _assessment
        with tempfile.TemporaryDirectory() as tmp:
            store=state.Store(Path(tmp))
            with diagnostic_context.operation_context(store,{'host':'PRIVATE','edition':'no-root'}):
                _assessment({},None,{'can_resume_root_setup':'PRIVATE'})
            self.assertEqual(store.contract_events[0]['field'],'can_resume_root_setup')
            self.assertNotIn('PRIVATE',json.dumps(store.contract_events))
            recorder=events.Recorder(emit=lambda _: (_ for _ in ()).throw(OSError('PRIVATE')))
            recorder.record(fact())
            self.assertEqual(recorder.snapshot()['events'],[fact()])

if __name__=='__main__':unittest.main()
