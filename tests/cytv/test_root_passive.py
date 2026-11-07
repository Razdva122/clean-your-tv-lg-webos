"""Passive original-operation selection with actual files and read-only Node APIs."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from cytv import root_passive


@unittest.skipIf(os.name == 'nt', 'TV file modes are POSIX')
class PassiveBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.identifier='a'*32
        self.base='/var/lib/clean-your-tv-installation'
        self.worker=self.base+'/request-'+self.identifier
        self.manifests={}
        for component in ('root','root-updater'):
            raw=json.dumps({'files':{'install_driver.py':hashlib.sha256(b'NEVER EXECUTE').hexdigest()}}).encode()
            self.write(self.worker+'/'+component+'/bundle.json',raw)
            self.manifests[component]=hashlib.sha256(raw).hexdigest()
        self.write(self.worker+'/root-updater/install_driver.py',b'NEVER EXECUTE')
        candidate=hashlib.sha256(json.dumps(self.manifests,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        self.request={'operation':self.identifier,'action':'install','state':'recovery_required','stage':'root-deploy','candidate_sha256':candidate}
        self.submission={**self.request,'stage':'submitted','worker_sha256':self.manifests['root-updater']}
        self.records()
        self.write(self.worker+'/worker.log',b'PRIVATE PASSWORD ADDRESS\nsubprocess.CalledProcessError: secret\n')

    def write(self,path,data):
        p=self.root/path.lstrip('/');p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(data);p.chmod(0o600);return p

    def records(self):
        for kind,value in (('request',self.request),('submission',self.submission)):
            self.write(self.base+'/'+kind+'-'+self.identifier+'.json',json.dumps(value).encode())

    def collect(self,foreign=False):
        harness=r'''
var fs=require('fs'),vm=require('vm'),path=require('path'),c=require('constants');
var fixture=JSON.parse(process.argv[1]),code=JSON.parse(process.argv[2]),foreign=process.argv[3]==='true';
function local(p){if(typeof p!=='string'||p[0]!=='/'||p.indexOf('..')>=0)throw Error('unexpected-path');return path.join(fixture,p);}
function stat(s){s.uid=foreign&&s.isFile()?123:0;return s;}
var ro={lstatSync:function(p){return stat(fs.lstatSync(local(p)));},
 openSync:function(p,flags){if((flags&3)!==0||!(flags&c.O_NOFOLLOW))throw Error('not-read-only');return fs.openSync(local(p),flags);},
 fstatSync:function(fd){return stat(fs.fstatSync(fd));},readSync:fs.readSync.bind(fs),closeSync:fs.closeSync.bind(fs)};
var output=[];
vm.runInNewContext(code,{Buffer:Buffer,console:{log:function(s){output.push(s);}},process:{getuid:function(){return 0;}},
 require:function(n){if(n==='fs')return ro;if(n==='constants'||n==='crypto')return require(n);throw Error('unexpected-module');}});
process.stdout.write(JSON.stringify(output));
'''
        before={str(p):(p.read_bytes(),p.stat().st_mode) for p in self.root.rglob('*') if p.is_file() and not p.is_symlink()}
        run=subprocess.run([os.environ.get('ROOT_DIAGNOSTIC_NODE','node'),'-e',harness,json.dumps(str(self.root)),
                            json.dumps(root_passive.program(self.identifier)),str(foreign).lower()],capture_output=True,text=True,check=True)
        output=json.loads(run.stdout);self.assertEqual(len(output),1)
        for secret in ('PRIVATE','PASSWORD','ADDRESS',self.identifier,self.worker):self.assertNotIn(secret,run.stdout)
        after={str(p):(p.read_bytes(),p.stat().st_mode) for p in self.root.rglob('*') if p.is_file() and not p.is_symlink()}
        self.assertEqual(before,after)
        return json.loads(output[0])

    @unittest.skipUnless(os.environ.get('NODE012'), 'Exact NODE012 not supplied')
    def test_legacy_node_reads_retained_records_without_executing_them(self):
        from unittest.mock import patch
        with patch.dict(os.environ, {'ROOT_DIAGNOSTIC_NODE':os.environ['NODE012']}):
            self.assertEqual(self.collect()['status'], 'read')
            self.assertEqual(self.collect(foreign=True)['status'], 'unsafe')

    def test_reads_only_exact_original_operation_and_never_executes_worker(self):
        got=self.collect();self.assertEqual(got['status'],'read')
        self.assertEqual(got['operation'],'consistent-not-admission')
        self.assertEqual(got['python'],'system-default-unverified')
        self.write(self.base+'/request-'+'b'*32+'.json',b'foreign malformed request')
        self.assertEqual(self.collect(),got)

    def test_complete_first_worker_line_is_classified_but_tail_fragments_are_not(self):
        self.write(self.worker+'/worker.log',b'RuntimeError: PRIVATE PASSWORD\n')
        self.assertEqual(self.collect()['worker'],'exception-recorded')
        self.write(self.worker+'/worker.log',b'x'*9000+b'RuntimeError: PRIVATE PASSWORD\n')
        self.assertEqual(self.collect()['worker'],'unclassified')

    def test_uuid_candidate_submission_and_snapshot_mismatch_refuse(self):
        for record,key,value in ((self.request,'operation','b'*32),(self.request,'candidate_sha256','b'*64),
                                 (self.submission,'worker_sha256','b'*64),(self.submission,'action','remove')):
            old=record[key];record[key]=value;self.records()
            self.assertEqual(self.collect()['status'],'inconsistent')
            record[key]=old;self.records()

    def test_blocked_request_or_absent_worker_does_not_guess_another_path(self):
        self.request['stage']='blocked';self.records()
        self.assertEqual(self.collect()['status'],'unavailable')
        self.request['stage']='root-deploy';self.records()
        (self.root/(self.worker+'/worker.log').lstrip('/')).unlink()
        self.assertEqual(self.collect()['status'],'missing')

    def test_unsafe_file_ownership_links_modes_and_oversize_refuse(self):
        path=self.root/(self.base+'/request-'+self.identifier+'.json').lstrip('/')
        original=path.read_bytes()
        for kind in ('symlink','hardlink','foreign','mode','oversize','truncated'):
            with self.subTest(kind=kind):
                extra=path.with_suffix('.private')
                if kind=='symlink':path.rename(extra);path.symlink_to(extra)
                if kind=='hardlink':os.link(path,extra)
                if kind=='mode':path.chmod(0o666)
                if kind=='oversize':path.write_bytes(b'x'*65537)
                if kind=='truncated':path.write_bytes(b'{')
                self.assertEqual(self.collect(foreign=kind=='foreign')['status'],'unsafe')
                if path.is_symlink():path.unlink()
                if extra.exists():extra.unlink()
                self.write(str(path.relative_to(self.root)),original)

    def test_private_binding_is_read_as_pinned_data_never_run(self):
        pin='4a71641c8d5536175e404a961624e8656eba30e97b5026f6bd7dc31e4bbeaaea'
        runtime='/var/lib/clean-your-tv-python/'+pin
        executable=runtime+'/bin/python3.13'
        binary=self.write(executable,b'PRIVATE executable must not run');binary.chmod(0o700)
        inventory=json.dumps({'schema':1,'archive_sha256':pin,'files':{'bin/python3.13':hashlib.sha256(binary.read_bytes()).hexdigest()}}).encode()
        self.write(runtime+'/.cytv-runtime.json',inventory).chmod(0o644)
        state='/var/lib/clean-your-tv-root'
        self.write(state+'/python-runtime.json',json.dumps({'schema':1,'archive_sha256':pin,'executable':executable,'inventory_sha256':hashlib.sha256(inventory).hexdigest()}).encode())
        launcher=self.write(state+'/python-launcher',('#!/bin/sh\nunset PYTHONHOME PYTHONPATH\nexport PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1\nexec '+executable+' "$@"\n').encode());launcher.chmod(0o700)
        self.assertEqual(self.collect()['python'],'private-bytes-match-unexecuted')
        binary.write_bytes(b'changed')
        self.assertEqual(self.collect()['status'],'inconsistent')
        launcher.write_bytes(b'exec /tmp/foreign');launcher.chmod(0o700)
        self.assertEqual(self.collect()['status'],'inconsistent')

    def test_updater_binding_is_not_misreported_as_system_default(self):
        self.write('/var/lib/clean-your-tv-root-updater/python-launcher',b'foreign launcher must not run')
        self.assertEqual(self.collect()['status'],'inconsistent')

    def test_remote_output_cannot_export_arbitrary_text(self):
        from unittest.mock import Mock
        for value in ({'schema':1,'status':'PRIVATE PASSWORD'},
                      {'schema':1,'status':'read','operation':'consistent-not-admission','worker':'unclassified','python':'system-default-unverified','extra':'PRIVATE'}):
            remote=Mock();remote.run.return_value=json.dumps(value)
            self.assertEqual(root_passive.collect(remote,self.identifier),{'schema':1,'status':'unsafe'})

    def test_host_rejects_invalid_uuid_before_any_remote_command(self):
        from unittest.mock import Mock
        remote=Mock()
        with self.assertRaises(ValueError):root_passive.collect(remote,'../../foreign')
        remote.run.assert_not_called()


class HostPassiveSelectionTests(unittest.TestCase):
    def test_original_profile_is_required_and_success_retains_pending_and_trust(self):
        import contextlib
        import importlib.util
        import io
        import sys
        from unittest.mock import Mock,patch
        from cytv import state
        source=Path(__file__).resolve().parents[2]/'scripts/root-passive-inspection.py'
        spec=importlib.util.spec_from_file_location('root_passive_inspection',source)
        tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)
        with tempfile.TemporaryDirectory() as tmp:
            store=state.Store(tmp);profile=state.target('fixture.invalid','root');store.save(profile)
            store.begin(profile,'install',stage='coordinator-submitted',product_operation='a'*32)
            known=store.device_dir(profile)/'known_hosts';known.write_bytes(b'ORIGINAL PIN')
            original=store.pending(profile)
            remote=Mock();remote.run.return_value='{"schema":1,"status":"missing"}'
            output=io.StringIO()
            with patch.object(sys,'argv',['passive','--operation','a'*32]),patch.object(tool.state,'Store',return_value=store), \
                 patch('cytv.transport.SSH.connect',return_value=remote) as connect,contextlib.redirect_stdout(output):
                tool.main()
            self.assertEqual(json.loads(output.getvalue()),{'schema':1,'status':'missing'})
            self.assertFalse(connect.call_args.kwargs['persist']);remote.close.assert_called_once()
            self.assertEqual(store.pending(profile),original);self.assertEqual(known.read_bytes(),b'ORIGINAL PIN')
            remote.run.assert_called_once()
            self.assertEqual(remote.run.call_args.args[0],'env -u NODE_OPTIONS -u NODE_PATH /usr/bin/node')
            with patch.object(sys,'argv',['passive','--operation','b'*32]),patch.object(tool.state,'Store',return_value=store), \
                 patch('cytv.transport.SSH.connect') as connect,self.assertRaisesRegex(ValueError,'exactly_one_matching'):
                tool.main()
            connect.assert_not_called()

    def test_archive_paths_must_come_from_the_matching_original_receipt(self):
        pending={'action':'install','product_operation':'a'*32,'archive':'/var/lib/clean-your-tv-root.archive-'+'b'*32}
        self.assertIn(pending['archive'],root_passive.program('a'*32,pending))
        for change in ({'product_operation':'b'*32},{'archive':'/tmp/latest'},{'archive':'/var/lib/clean-your-tv-root.archive-'+'../'*8}):
            with self.assertRaises(ValueError):root_passive.program('a'*32,{**pending,**change})
