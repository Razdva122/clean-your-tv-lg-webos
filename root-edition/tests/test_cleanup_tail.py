"""Real-file Node tail tests with TV RPC and Linux fd-path translation adapters.

The macOS adapter resolves /proc/self/fd paths to stationary fixture paths. It
tests inventories, retries and receipts, NOT Linux rename-race confinement; that
requires the unchanged source on a Linux runner. Production has no test hooks.
"""
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch


SOURCE=Path(__file__).resolve().parents[1]/'cleanup_tail.js'
RUNTIME='/var/lib/clean-your-tv-python/4a71641c8d5536175e404a961624e8656eba30e97b5026f6bd7dc31e4bbeaaea'
STATE='/var/lib/clean-your-tv-installation'
ID='a'*32
APPS=('com.cleanyourtv.root.preview','com.cleanyourtv.root.updater','com.cleanyourtv.system.updater','com.cleanyourtv.updater','com.local.nativehome','com.gathin.tvhome')
def packages():
    return {app:{'state':'absent','readback':{'app':app,'absent':True}} for app in APPS}
HARNESS=r'''
var real=require('fs'),vm=require('vm'),base=process.argv[2],source=process.argv[3],paths={},calls=[],profileReads=0;
function path(p){
 if(typeof p!=='string')return p;
 if(p==='/')return base;
 var match=/^\/proc\/self\/fd\/(\d+)(.*)$/.exec(p);
 if(match)return process.env.CYTV_REAL_PROC_FD==='1'?p:paths[match[1]]+match[2];
 return /^\/(home|usr|var|media|tmp|proc)(\/|$)/.test(p)?base+p:p;
}
var fs=Object.create(real);
fs.openSync=function(p,flags,mode){var fd=real.openSync(path(p),flags,mode);paths[fd]=path(p);return fd;};
fs.fstatSync=function(fd){var info=real.fstatSync(fd);if(process.env.TMP_OWNER && paths[fd]===base+'/tmp')info.uid=Number(process.env.TMP_OWNER);if(process.env.SYSTEM_DEVICE&&paths[fd].indexOf(base+'/usr/')===0)info.dev=45851;return info;};
['lstatSync','readFileSync','readlinkSync','realpathSync','readdirSync','rmdirSync','unlinkSync'].forEach(function(name){fs[name]=function(p){
 if(name==='readdirSync' && process.env.SWAP_RUNTIME && process.env.CYTV_REAL_PROC_FD==='1' && /^\/proc\/self\/fd\/\d+$/.test(p)){
  var held=real.readlinkSync(p);
  if(/\/clean-your-tv-python\/[a-f0-9]{64}$/.test(held) && !real.existsSync(held+'-moved')){
   real.renameSync(held,held+'-moved');real.mkdirSync(held,448);real.writeFileSync(held+'/foreign','preserve replacement');
  }
 }
 if(name==='unlinkSync'||name==='rmdirSync'){
  var target=path(p),descriptor=/^\/proc\/self\/fd\/(\d+)(.*)$/.exec(target);
  calls.push([name,descriptor?real.readlinkSync('/proc/self/fd/'+descriptor[1])+descriptor[2]:target]);
  if(process.env.FAIL_MEMBER && path(p).slice(-process.env.FAIL_MEMBER.length)===process.env.FAIL_MEMBER)throw Error('injected storage interruption');
 }
 var value=real[name].apply(real,[path(p)].concat(Array.prototype.slice.call(arguments,1)));
 if(name==='lstatSync'&&process.env.SYSTEM_DEVICE&&path(p).indexOf(base+'/usr/')===0)value.dev=45851;
 if(name==='realpathSync'&&value.indexOf(base+'/usr/')===0)return value.slice(base.length);
 return value;
};});
fs.renameSync=function(a,b){
 var value;try{value=JSON.parse(real.readFileSync(path(a),'utf8'));}catch(e){}
 if(value&&value.final_fence&&process.env.FAIL_FINAL_COMPLETE&&value.stage==='verified-clean')throw Error('interrupted final receipt');
 if(value&&value.stage==='final-fence-pending'&&process.env.FAIL_FINAL_OWNER)throw Error('interrupted fence publication');
 if(value&&value.stage==='verified-clean'&&value.owner==='clean-removal'&&process.env.FAIL_FINAL_VERIFIED)throw Error('interrupted verified owner');
 return real.renameSync(path(a),path(b));
};
var lock=process.env.OWNERSHIP_FD?Number(process.env.OWNERSHIP_FD):fs.openSync('/var/lib/clean-your-tv-installation/ownership.lock','r+');
var promotion=process.env.PROMOTION_FD?Number(process.env.PROMOTION_FD):fs.openSync('/var/lib/clean-your-tv-python/.install.lock','r+');
var worker=process.env.WORKER_FD?Number(process.env.WORKER_FD):fs.openSync('/var/lib/clean-your-tv-installation/worker.lock','r+');
var fake={getuid:process.getuid,pid:999999,ppid:999998,argv:['node','-',process.env.MODE||'finish','aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',process.env.TAIL_STAGE||'-',String(lock),String(promotion),String(worker),process.env.GATE_SHA||'-',process.env.REMOVAL||'dddddddddddddddddddddddddddddddd'],stdout:process.stdout,stderr:process.stderr};
function fixtureReply(command,args,options){
 if(command==='/proc/self/fd/3')return require('child_process').spawnSync(command,args,options);
 if(command==='/usr/bin/node'&&args[0]==='-e'){
  if(JSON.parse(args[2]).action!=='inventory')throw Error('Unexpected private cleanup effect');
  return {status:0,stdout:Buffer.from?Buffer.from('{"schema":1,"present":[],"blocked":[]}'):new Buffer('{"schema":1,"present":[],"blocked":[]}')};
 }
 var method=args[2],value={returnValue:true};
 if(method.indexOf('listApps')!==-1){if(process.env.PRIVATE_ERROR)throw Error(process.env.PRIVATE_ERROR);if(process.env.ALL_CATALOGS_DENIED || process.env.DEV_CATALOG_DENIED && method.indexOf('/dev/')!==-1)value.returnValue=false;if(process.env.CATALOG_MALFORMED && method.indexOf('/dev/')!==-1)delete value.returnValue;value.apps=[];}
 else if(method.indexOf('getSystemSettings')!==-1){if(process.env.NO_HOME_APIS)throw Error('Home APIs unavailable');value.settings={defaultApps:{home:process.env.SETTINGS_HOME||(process.env.FOREIGN_ROUTE?'changed':'third.party.home')}};}
 else if(method.indexOf('getProfiles')!==-1){if(process.env.FAIL_FINAL_READBACK && ++profileReads===2)throw Error('injected final readback failure');if(process.env.MISSING_PROFILES){value.returnValue=false;if(process.env.PROFILE_ERROR)value=JSON.parse(process.env.PROFILE_ERROR);}else value.profiles={defaultApps:{categories:{home:'third.party.home'}},idleApp:{appId:'third.party.home'}};}
 else if(method.indexOf('activitymanager')!==-1){
  if(process.env.ACTIVITY_BOTH_UNAVAILABLE || process.env.ACTIVITY_LIST_UNAVAILABLE && method.indexOf('/list')!==-1)return {status:1,stdout:new Buffer('')};
  value.activities=JSON.parse(process.env.ACTIVITIES||'[]');
  if(process.env.ACTIVITY_MALFORMED && method.indexOf('/list')!==-1)value.activities={};
 }
 else if(method.indexOf('getAllInputStatus')!==-1)value.devices=[];
 else if(method.indexOf('getConfigs')!==-1)value.configs={'com.webos.surfacemanager.keyFilters':JSON.parse(process.env.FILTER_CHAIN||'[{"file":"/usr/lib/qml/KeyFilters/systemUi.js","handler":"handleSystemKeys"}]')};
 else throw Error('Unexpected RPC '+method);
 return {status:0,stdout:Buffer.from?Buffer.from(JSON.stringify(value)):new Buffer(JSON.stringify(value))};
}
var cp={spawnSync:function(command,args,options){if(process.env.NO_SYNC)throw Error('sync child unsupported');return fixtureReply(command,args,options);},spawn:function(command,args,options){
 var E=require('events').EventEmitter,child=new E();child.stdout=new E();child.stderr=new E();child.stdin=new E();child.kill=function(){process.nextTick(function(){child.emit('close',null,'SIGKILL');});};
 process.nextTick(function(){try{var reply=fixtureReply(command,args,options);child.stdout.emit('data',reply.stdout);child.emit('close',reply.status,null);}catch(error){child.emit('error',error);child.emit('close',1,null);}});return child;
}};
fake.versions=process.versions;fake.env=process.env;fake.platform=process.platform;fake.nextTick=process.nextTick;
var context={require:function(name){return name==='fs'?fs:name==='child_process'?cp:require(name);},process:fake,Buffer:Buffer,console:console,setTimeout:setTimeout,clearTimeout:clearTimeout,setImmediate:setImmediate,clearImmediate:clearImmediate};context.global=context;
function finished(){real.closeSync(lock);real.writeFileSync(process.env.MUTATION_LOG||base+'/mutations.json',JSON.stringify(calls));process.exitCode=fake.exitCode||0;}
var outcome=vm.runInNewContext(real.readFileSync(source,'utf8'),context);
if(outcome&&typeof outcome.then==='function')outcome.then(finished,function(error){console.error(error);fake.exitCode=1;finished();});else finished();
'''


class CleanupTail(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name).resolve()
        self.runtime=self.base/RUNTIME.lstrip('/');self.runtime.mkdir(parents=True,mode=0o700)
        self.state=self.base/STATE.lstrip('/');self.state.mkdir(parents=True,mode=0o700)
        (self.base/'proc/sys/kernel/random').mkdir(parents=True)
        (self.base/'proc/sys/kernel/random/boot_id').write_text('22222222-2222-2222-2222-222222222222')
        (self.base/'tmp').mkdir()
        for name in ('bin/python3.13','lib/secret.py'):
            p=self.runtime/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('owned '+name)
        files={str(p.relative_to(self.runtime)):hashlib.sha256(p.read_bytes()).hexdigest() for p in self.runtime.rglob('*') if p.is_file()}
        self.record=dict(schema=1,protocol='clean-removal-v1',operation=ID,removal='d'*32,lease='b'*32,stage='private-cleanup',
            state='recovery_required',cleanup_boot_id='11111111-1111-1111-1111-111111111111:session-'+'a'*32,cleanup_verified_boot_id='11111111-1111-1111-1111-111111111111:session-'+'b'*32,routes=['third.party.home']*3,support_stages=[],packages=packages(),
            done=['original-writers-fenced','controls-restored','package-removal','private-cleanup'],
            runtime_cleanup=dict(root=RUNTIME,files=files),result=dict(removed=True,applications_services_startup_removed=True,private_cleanup_verified=False))
        self.write('clean-removal-'+ID+'.json',self.record)
        self.write('operation.json',dict(schema=1,id='b'*32,owner='clean-removal',journal='product-'+ID+'.json',terminal=False,stage='private-cleanup'))
        (self.state/'ownership.lock').touch(mode=0o600)
        (self.state/'worker.lock').touch(mode=0o600)
        (self.runtime.parent/'.install.lock').touch(mode=0o600)
        self.harness=self.base/'harness.js';self.harness.write_text(HARNESS)

    def write(self,name,value):
        path=self.state/name;path.write_text(json.dumps(value));path.chmod(0o600)

    def run_tail(self,**environment):
        node=os.environ.get('NODE8','node')
        result=subprocess.run([node,str(self.harness),str(self.base),str(SOURCE)],capture_output=True,text=True,
            env={**os.environ,**environment},timeout=15)
        self.assertTrue(result.stdout,result.stderr)
        return result,json.loads(result.stdout)

    def test_legacy_tv_cleanup_uses_async_children_and_activity_fallback(self):
        result,reply=self.run_tail(NO_SYNC='1',ACTIVITY_LIST_UNAVAILABLE='1')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(reply['stage'],'verified-clean')
        self.assertFalse(self.runtime.exists())
        result,reply=self.run_tail(NO_SYNC='1',ACTIVITY_LIST_UNAVAILABLE='1',MODE='verify')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(reply['state'],'verified-clean')

    def test_activity_fallback_never_accepts_missing_or_malformed_inventory(self):
        for flags in ({'ACTIVITY_BOTH_UNAVAILABLE':'1'},{'ACTIVITY_MALFORMED':'1'},
                      {'ACTIVITY_LIST_UNAVAILABLE':'1','ACTIVITIES':'[null]'},
                      {'ACTIVITY_LIST_UNAVAILABLE':'1','ACTIVITIES':'[{"callback":{"method":"luna://com.local.nativehome.service/tick"}}]'}):
            with self.subTest(flags=flags):
                result,reply=self.run_tail(**flags)
                self.assertEqual(result.returncode,1)
                self.assertTrue(self.runtime.exists())
                self.assertNotEqual(reply.get('state'),'complete')

    def test_inert_system_staging_does_not_block_final_removal_or_recheck(self):
        stage=self.base/'tmp'/('cytv-system-updater-'+'c'*32);stage.mkdir(mode=0o700)
        (stage/'unknown-diagnostic.txt').write_text('retain without execution')
        info=stage.stat()
        self.record['retained_temporary_stages']=[dict(path='/tmp/'+stage.name,dev=info.st_dev,ino=info.st_ino)]
        self.record['result']['temporary_files_retained']=True
        self.write('clean-removal-'+ID+'.json',self.record)
        result,reply=self.run_tail()
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue(reply['result']['temporary_files_retained'])
        self.assertTrue((stage/'unknown-diagnostic.txt').exists())
        result,reply=self.run_tail(MODE='verify')
        self.assertEqual(result.returncode,0,result.stderr)
        process=self.base/'proc/99991';process.mkdir()
        (process/'cmdline').write_bytes(('/usr/bin/python3\0/tmp/'+stage.name+'/setup-system-updater.py\0').encode())
        result,reply=self.run_tail(MODE='verify')
        self.assertEqual(reply.get('cleanup_error'),'owned-process-still-used')
        (process/'cmdline').unlink();process.rmdir()
        saved=json.loads((self.state/('clean-removal-'+ID+'.json')).read_text())
        saved['retained_temporary_stages'][0]['ino']+=1
        self.write('clean-removal-'+ID+'.json',saved)
        result,reply=self.run_tail(MODE='verify')
        self.assertEqual(reply['cleanup_error'],'support-stage-remains')

    def test_finalizer_accepts_fallback_catalog_and_still_checks_package_paths(self):
        owned=self.base/'media/developer/apps/usr/palm/applications/com.local.nativehome'
        owned.mkdir(parents=True)
        result,reply=self.run_tail(DEV_CATALOG_DENIED='1')
        self.assertEqual(reply['cleanup_error'],'package-remains')
        self.assertTrue((self.runtime/'bin/python3.13').exists())
        owned.rmdir()
        result,reply=self.run_tail(DEV_CATALOG_DENIED='1')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(reply['stage'],'verified-clean')

    def test_verified_removal_admission_is_read_only_and_rechecks_live_state(self):
        result,reply=self.run_tail()
        self.assertEqual(result.returncode,0,result.stderr)
        before={p.name:p.read_bytes() for p in self.state.iterdir() if p.is_file()}
        result,reply=self.run_tail(MODE='verify')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(reply['state'],'verified-clean')
        self.assertEqual(reply['lease'],json.loads((self.state/'operation.json').read_text())['id'])
        self.assertNotEqual(reply['lease'],'b'*32)
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.state.iterdir() if p.is_file()})
        self.assertEqual(json.loads((self.base/'mutations.json').read_text()),[])
        owned=self.base/'media/developer/apps/usr/palm/applications/com.local.nativehome'
        owned.mkdir(parents=True)
        result,reply=self.run_tail(MODE='verify')
        self.assertEqual(result.returncode,1)
        self.assertEqual(reply['cleanup_error'],'package-remains')
        result,reply=self.run_tail(MODE='finish')
        self.assertEqual(result.returncode,1)
        self.assertTrue(owned.exists())
        self.assertEqual(json.loads((self.base/'mutations.json').read_text()),[])

    def test_legacy_completed_removal_finalizes_without_sweeping_and_then_stays_read_only(self):
        result,_=self.run_tail();self.assertEqual(result.returncode,0,result.stderr)
        record=json.loads((self.state/('clean-removal-'+ID+'.json')).read_text())
        record.pop('final_fence');record.pop('final_original_lease')
        self.write('clean-removal-'+ID+'.json',record)
        self.write('operation.json',dict(schema=1,id='b'*32,owner='clean-removal',journal='product-'+ID+'.json',stage='verified-clean',terminal=False))
        result,reply=self.run_tail(MODE='finalize')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertNotEqual(reply['lease'],'b'*32)
        self.assertEqual(json.loads((self.base/'mutations.json').read_text()),[])
        before={p.name:p.read_bytes() for p in self.state.iterdir() if p.is_file()}
        result,_=self.run_tail(MODE='finalize')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.state.iterdir() if p.is_file()})

    def test_completed_legacy_receipt_reconciles_after_retiring_own_scratch_directories(self):
        result,_=self.run_tail();self.assertEqual(result.returncode,0,result.stderr)
        record=json.loads((self.state/('clean-removal-'+ID+'.json')).read_text())
        record.pop('final_fence');record.pop('final_original_lease')
        self.write('clean-removal-'+ID+'.json',record)
        self.write('operation.json',dict(schema=1,id='b'*32,owner='clean-removal',journal='product-'+ID+'.json',stage='verified-clean',terminal=False))
        stage='/tmp/cytv-root-tail-'+'c'*32
        directory=self.base/stage.lstrip('/');directory.mkdir(mode=0o700)
        (directory/'gate').write_bytes(b'current gate')
        (directory/'gate').chmod(0o700)
        old='/tmp/cytv-root-tail-'+'e'*32
        old_directory=self.base/old.lstrip('/');old_directory.mkdir(mode=0o700)
        (old_directory/'gate').write_bytes(b'previous installer gate')
        (old_directory/'gate').chmod(0o700)
        (old_directory/'.cytv.ABC123').write_bytes(b'interrupted atomic upload')
        (old_directory/'cache').mkdir(mode=0o700)
        (old_directory/'cache/partial').write_bytes(b'owned temporary bytes')
        result,reply=self.run_tail(MODE='finish',TAIL_STAGE=old+','+stage,GATE_SHA=hashlib.sha256(b'current gate').hexdigest())
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(reply['state'],'complete')
        saved=json.loads((self.state/('clean-removal-'+ID+'.json')).read_text())
        self.assertEqual(saved['tail_stages'],record['tail_stages'],'completed cleanup must not acquire another destructive stage')
        self.assertNotEqual(saved['final_fence'],'b'*32)
        before={p.name:p.read_bytes() for p in self.state.iterdir() if p.is_file()}
        result,reply=self.run_tail(MODE='finish')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.state.iterdir() if p.is_file()})

    def test_completed_readback_removes_own_scratch_tree_without_following_links(self):
        result,_=self.run_tail();self.assertEqual(result.returncode,0,result.stderr)
        before={p.name:p.read_bytes() for p in self.state.iterdir() if p.is_file()}
        stage='/tmp/cytv-root-tail-'+'c'*32
        directory=self.base/stage.lstrip('/');directory.mkdir(mode=0o700)
        (directory/'gate').write_bytes(b'old or partial inert gate')
        cache=directory/'cache';cache.mkdir(mode=0o700)
        (cache/'partial-upload').write_bytes(b'owned temporary bytes')
        foreign=self.base/'foreign';foreign.mkdir(mode=0o700)
        (foreign/'keep').write_text('preserve')
        (directory/'outside').symlink_to(foreign,target_is_directory=True)
        result,reply=self.run_tail(MODE='finish',TAIL_STAGE=stage,GATE_SHA='f'*64)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertFalse(directory.exists())
        self.assertEqual((foreign/'keep').read_text(),'preserve')
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.state.iterdir() if p.is_file()})

    def test_completed_readback_preserves_unsafe_or_redirected_scratch_root(self):
        for kind in ('writable','redirected','hardlink'):
            with self.subTest(kind=kind):
                case=CleanupTail();case.setUp()
                try:
                    result,_=case.run_tail();self.assertEqual(result.returncode,0,result.stderr)
                    before={p.name:p.read_bytes() for p in case.state.iterdir() if p.is_file()}
                    stage='/tmp/cytv-root-tail-'+'c'*32
                    directory=case.base/stage.lstrip('/')
                    foreign=case.base/'foreign';foreign.mkdir(mode=0o700)
                    (foreign/'keep').write_text('preserve')
                    if kind=='redirected':directory.symlink_to(foreign,target_is_directory=True)
                    else:
                        directory.mkdir(mode=0o700)
                        if kind=='writable':directory.chmod(0o777)
                        else:os.link(foreign/'keep',directory/'gate')
                    result,reply=case.run_tail(MODE='finish',TAIL_STAGE=stage,GATE_SHA='f'*64)
                    self.assertEqual(result.returncode,1)
                    self.assertTrue(directory.exists())
                    self.assertEqual((foreign/'keep').read_text(),'preserve')
                    self.assertEqual(before,{p.name:p.read_bytes() for p in case.state.iterdir() if p.is_file()})
                finally:case.doCleanups()

    def test_incomplete_removal_cannot_be_admitted_or_finished_by_verification(self):
        before=(self.state/('clean-removal-'+ID+'.json')).read_bytes()
        result,reply=self.run_tail(MODE='verify')
        self.assertEqual(result.returncode,1)
        self.assertEqual(before,(self.state/('clean-removal-'+ID+'.json')).read_bytes())
        self.assertTrue((self.runtime/'bin/python3.13').exists())

    def test_final_fence_crashes_resume_same_uuid_without_repeating_cleanup(self):
        for point in ('FAIL_FINAL_OWNER','FAIL_FINAL_COMPLETE','FAIL_FINAL_VERIFIED'):
            with self.subTest(point=point):
                # A separate real-file fixture for each publication boundary.
                case=CleanupTail();case.setUp()
                try:
                    result,reply=case.run_tail(**{point:'1'})
                    self.assertEqual(result.returncode,1)
                    record=json.loads((case.state/('clean-removal-'+ID+'.json')).read_text())
                    planned=record['final_fence']
                    result,reply=case.run_tail(MODE='verify')
                    self.assertEqual(result.returncode,1,'Incomplete publication was admitted')
                    result,reply=case.run_tail()
                    self.assertEqual(result.returncode,0,result.stderr)
                    self.assertEqual(json.loads((case.state/'operation.json').read_text())['id'],planned)
                    result,reply=case.run_tail()
                    self.assertEqual(result.returncode,0,result.stderr)
                    self.assertEqual(json.loads((case.base/'mutations.json').read_text()),[])
                finally:case.doCleanups()

    def test_successor_allows_read_only_absence_but_fences_old_cleanup(self):
        result,_=self.run_tail();self.assertEqual(result.returncode,0,result.stderr)
        name='no-root-'+'e'*32+'.json'
        final=json.loads((self.state/'operation.json').read_text())['id']
        self.write(name,dict(schema=1,protocol='no-root-root-handoff-v1',lease='f'*32,
            predecessor=dict(operation=ID,removal='d'*32,lease=final)))
        self.write('operation.json',dict(schema=1,id='f'*32,owner='no-root',journal=name,stage='reserved',terminal=False))
        before=(self.state/'operation.json').read_bytes()
        result,reply=self.run_tail(MODE='verify')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(reply['state'],'verified-clean')
        result,reply=self.run_tail(MODE='finish')
        self.assertEqual(result.returncode,1)
        self.assertEqual((self.state/'operation.json').read_bytes(),before)

    @unittest.skipUnless(os.environ.get('NODE012'),'Exact Node 0.12.2 is optional on the host')
    def test_legacy_compiled_cleanup_and_admission_use_descriptor_io_on_node012(self):
        from scripts.root_node_build import compile_root_beta
        compiled=self.base/'legacy-tail.js'
        compiled.write_bytes(compile_root_beta({'cleanup_tail.js':SOURCE.read_bytes()})['cleanup_tail.js'])
        with patch.dict(os.environ,NODE8=os.environ['NODE012']),patch(__name__+'.SOURCE',compiled):
            result,reply=self.run_tail()
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(reply['stage'],'verified-clean')
            result,reply=self.run_tail(MODE='verify')
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(reply['state'],'verified-clean')

    def test_unavailable_or_malformed_catalog_never_retires_runtime(self):
        for flags,reason in (({'ALL_CATALOGS_DENIED':'1'},'cleanup-readback-unavailable'),
                             ({'CATALOG_MALFORMED':'1'},'cleanup-readback-malformed')):
            result,reply=self.run_tail(**flags)
            self.assertEqual(result.returncode,1)
            self.assertEqual(reply['cleanup_error'],reason)
            self.assertTrue((self.runtime/'bin/python3.13').exists())

    def test_actual_stdin_entry_reaches_selector_guard_with_readonly_global_crypto(self):
        # Node 20+ exposes getter-only global WebCrypto for stdin scripts. Model
        # that binding on Node 8 too; the VM harness has a separate global scope.
        source = ("'use strict';\nObject.defineProperty(global,'crypto',"
                  "{configurable:true,get:function(){return {};}});\n" + SOURCE.read_text())
        result = subprocess.run([os.environ.get('NODE8','node'), '-', 'inspect', '../foreign',
                                 '-', '0', '-1', '-1', '-', 'd'*32],
                                input=source, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stderr, 'CYTV_CLEAN_TAIL: invalid-cleanup-selector\n')
        self.assertEqual(json.loads(result.stdout), {
            'operation':'../foreign', 'removal':'d'*32, 'state':'recovery_required',
            'stage':'private-cleanup', 'current':False, 'reason':'private-cleanup-incomplete','cleanup_error':'invalid-cleanup-selector'})

    def first_handoff(self, managed_executor=False, executable_symlink=False, native=False, diagnostic=False):
        import fcntl
        import install_device
        import python_binding
        from updater.store import Store
        self.record.pop('runtime_cleanup')
        self.write('clean-removal-'+ID+'.json',self.record)
        files={str(p.relative_to(self.runtime)):hashlib.sha256(p.read_bytes()).hexdigest()
               for p in self.runtime.rglob('*') if p.is_file()}
        inventory={'schema':1,'archive_sha256':python_binding.ARCHIVE_SHA256,'files':files}
        (self.runtime/'.cytv-runtime.json').write_text(json.dumps(inventory))
        executable=self.runtime/'bin/python3.13';executable.chmod(0o700)
        (self.runtime/'lib/secret.py').write_text('changed owned library bytes')
        if executable_symlink:
            import sys
            executable.unlink();executable.symlink_to(sys.executable)
        payload=self.base/'payload';(payload/'root-updater').mkdir(parents=True)
        (payload/'root-updater/cleanup_tail.js').write_bytes(SOURCE.read_bytes())
        boot=self.boot_directory() if native else None
        if native:
            import shutil
            shutil.rmtree(self.runtime.parent)
        store=Store(self.state,uid=os.getuid())
        ownership=os.open(self.state/'ownership.lock',os.O_RDWR)
        self.addCleanup(os.close,ownership);fcntl.flock(ownership,fcntl.LOCK_EX|fcntl.LOCK_NB)
        device=install_device.LocalDevice.__new__(install_device.LocalDevice)
        device.ownership=SimpleNamespace(store=store,fd=ownership,status=lambda:store.read('operation'))
        device.payload=payload;device.clean_quiescent=lambda *args,**kwargs:None
        run=subprocess.run;calls=[]
        def node(args,**kwargs):
            calls.append(args)
            self.assertEqual(args[:3],['/usr/bin/node','-','finish'])
            if native:
                self.assertEqual(kwargs['pass_fds'],(ownership,store.lock_fd))
                self.assertEqual(args[6],'-1')
            source=kwargs['input'].decode()
            # Fixed TV paths and RPCs use the existing real-file Node harness.
            # Python's first inventory/lock/handoff production path is unchanged.
            source=source.replace('/var/',str(self.base/'var')+'/').replace('/media/',str(self.base/'media')+'/')
            source=source.replace("fs.readdirSync('/tmp')",'fs.readdirSync('+repr(str(self.base/'tmp'))+')')
            source=source.replace("fs.readdirSync('/proc')",'fs.readdirSync('+repr(str(self.base/'proc'))+')')
            source=source.replace('/proc/sys/kernel/random/boot_id',str(self.base/'proc/sys/kernel/random/boot_id'))
            source=source.replace("'/tmp/clean-your-tv-root-boot'",repr(str(self.base/'tmp/clean-your-tv-root-boot')))
            target=self.base/'first-tail.js';target.write_text(source)
            harness=self.base/'first-harness.js'
            harness.write_text(HARNESS.replace('/var/',str(self.base/'var')+'/'))
            env={**kwargs['env'],'OWNERSHIP_FD':args[5],'PROMOTION_FD':args[6],'WORKER_FD':args[7],
                 'MUTATION_LOG':str(self.base/'first-mutations.json')}
            if diagnostic:env['FOREIGN_ROUTE']='1'
            result=run([os.environ.get('NODE8','node'),str(harness),'/',str(target)],
                       stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,pass_fds=kwargs['pass_fds'],timeout=15)
            self.assertEqual(result.returncode,1 if diagnostic else 0,result.stderr.decode())
            return result
        directory=python_binding._directory
        with patch.object(python_binding,'MANAGED_ROOT',self.runtime.parent), \
             patch.object(python_binding,'EXPECTED_UID',os.getuid()), \
             patch.object(python_binding,'_directory',side_effect=lambda p:directory(p) if self.base in (p,*p.parents) else None), \
             patch('install_device.subprocess.run',side_effect=node),store.lock():
            if managed_executor:
                with patch('install_device.sys.executable',str(executable)):
                    with self.assertRaisesRegex(ValueError,'digest mismatch|Unsafe Python file'):
                        device.finish_clean_tail(self.record)
                self.assertNotIn('runtime_cleanup',self.record)
                self.assertEqual(calls,[])
                self.assertTrue((self.runtime/'lib/secret.py').exists())
            else:
                if diagnostic:
                    import io
                    from contextlib import redirect_stderr
                    output=io.StringIO()
                    with redirect_stderr(output):reply=device.finish_clean_tail(self.record)
                    self.assertEqual(reply['cleanup_error'],'route-changed')
                    self.assertEqual(output.getvalue(),'CYTV_CLEAN_TAIL: route-changed\n')
                    self.assertTrue(boot.exists())
                    return
                reply=device.finish_clean_tail(self.record)
                self.assertIsNotNone(reply,'Native Python still requires the final Node absence proof')
                self.assertEqual(reply['stage'],'verified-clean',reply)
                self.assertTrue(reply['result']['verified_clean'])
                self.assertEqual(len(calls),1)
                self.assertFalse(self.runtime.exists())
                if native:
                    self.assertFalse(self.runtime.parent.exists())
                    self.assertFalse(boot.exists())
                    self.assertEqual(calls[0][6],'-1')
                    self.assertEqual(self.record['runtime_cleanup']['files'],{})
                    self.assertIs(self.record['runtime_cleanup']['promotion_required'],False)
                    saved=json.loads((self.state/('clean-removal-'+ID+'.json')).read_text())
                    self.assertEqual(saved['stage'],'verified-clean')
                    # A stale Python caller cannot rewrite the completed proof;
                    # supported retries use current coordinator/Node readback.
                    before=(self.state/('clean-removal-'+ID+'.json')).read_bytes()
                    with self.assertRaisesRegex(ValueError,'completed_removal_readback_required'):
                        device.finish_clean_tail(self.record)
                    self.assertEqual((self.state/('clean-removal-'+ID+'.json')).read_bytes(),before)
                    self.assertEqual(len(calls),1)
                    store.write('operation',dict(schema=1,id='f'*32,owner='no-root',journal='no-root-'+'e'*32+'.json',stage='reserved',terminal=False))
                    with self.assertRaisesRegex(ValueError,'completed_removal_readback_required'):
                        device.finish_clean_tail(self.record)
                    self.assertEqual((self.state/('clean-removal-'+ID+'.json')).read_bytes(),before)
                    self.assertEqual(len(calls),1)
                    self.assertFalse(self.runtime.parent.exists());self.assertFalse(boot.exists())

    def test_python_handoff_relays_safe_tail_guard_to_existing_stderr(self):
        self.first_handoff(native=True,diagnostic=True)

    def test_native_python_first_handoff_retires_boot_directory_without_managed_runtime(self):
        self.first_handoff(native=True)

    def test_first_handoff_external_executor_retires_changed_unused_runtime(self):
        self.first_handoff()

    def test_first_handoff_damaged_managed_executor_is_refused_before_node(self):
        self.first_handoff(managed_executor=True)

    def test_first_handoff_managed_executor_symlink_is_not_an_external_executor(self):
        self.first_handoff(managed_executor=True,executable_symlink=True)

    def test_exact_runtime_retired_and_repeat_has_zero_deletions(self):
        result,reply=self.run_tail()
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(reply['stage'],'verified-clean');self.assertTrue(reply['result']['private_cleanup_verified'])
        self.assertFalse(self.runtime.exists())
        self.assertFalse(json.loads((self.state/'operation.json').read_text())['terminal'])
        result,reply=self.run_tail()
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads((self.base/'mutations.json').read_text()),[])

    def test_other_valid_host_removal_intent_cannot_retire_runtime(self):
        result,reply=self.run_tail(REMOVAL='e'*32)
        self.assertNotEqual(result.returncode,0)
        self.assertTrue(self.runtime.exists())
        self.assertEqual(json.loads((self.base/'mutations.json').read_text()),[])

    def test_package_progress_flags_never_replace_exact_removal_receipts(self):
        for invalid in ({}, {'state':'submitted'}, {'state':'absent-before-submission'},
                        {'state':'terminal','terminal':{'completed':True,'event':{'id':'foreign','details':{'state':'removed'}}}},
                        {'state':'terminal','terminal':{'completed':True,'event':{'details':{'state':'removed','errorCode':0}}}}):
            with self.subTest(invalid=invalid):
                self.record['packages']=packages();self.record['packages'][APPS[0]]=invalid
                self.write('clean-removal-'+ID+'.json',self.record)
                result,reply=self.run_tail();self.assertNotEqual(result.returncode,0)
                self.assertTrue(self.runtime.exists())
                self.assertEqual(json.loads((self.base/'mutations.json').read_text()),[])
        for inventory in (None, {}, {**packages(),'foreign':{'state':'submitted'}}):
            self.record['packages']=inventory;self.write('clean-removal-'+ID+'.json',self.record)
            result,reply=self.run_tail();self.assertNotEqual(result.returncode,0)
            self.assertEqual(json.loads((self.base/'mutations.json').read_text()),[])

    def test_same_boot_cannot_finish_even_with_current_absence(self):
        self.record['cleanup_boot_id']=self.record['cleanup_verified_boot_id']
        self.write('clean-removal-'+ID+'.json',self.record)
        result,reply=self.run_tail();self.assertNotEqual(result.returncode,0)
        self.assertEqual(json.loads((self.base/'mutations.json').read_text()),[])

    def boot_directory(self):
        directory=self.base/'tmp/clean-your-tv-root-boot';directory.mkdir(mode=0o700)
        for name in ('session.lock','session.json','normal.json'):
            p=directory/name;p.write_text('{}');p.chmod(0o600)
        return directory

    def test_durable_boot_fact_survives_retired_python_and_later_tmp_clear(self):
        directory=self.boot_directory()
        result,reply=self.run_tail(FAIL_FINAL_READBACK='1')
        self.assertNotEqual(result.returncode,0)
        self.assertFalse(self.runtime.exists());self.assertFalse(directory.exists())
        saved=json.loads((self.state/('clean-removal-'+ID+'.json')).read_text())
        self.assertEqual(saved['stage'],'private-cleanup')
        (self.base/'proc/sys/kernel/random/boot_id').write_text('33333333-3333-3333-3333-333333333333')
        result,reply=self.run_tail()
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(reply['stage'],'verified-clean');self.assertFalse(directory.exists())

    def test_exact_root_sticky_tmp_parent_allows_boot_directory_retirement(self):
        directory=self.boot_directory();(self.base/'tmp').chmod(0o1777)
        result,reply=self.run_tail(TMP_OWNER='0')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(reply['stage'],'verified-clean');self.assertFalse(directory.exists())

    def test_sticky_parent_exception_rejects_foreign_uid_and_other_writable_modes(self):
        directory=self.boot_directory()
        for owner,mode in (('123456',0o1777),('0',0o777),('0',0o1775)):
            with self.subTest(owner=owner,mode=oct(mode)):
                (self.base/'tmp').chmod(mode)
                result,reply=self.run_tail(TMP_OWNER=owner)
                self.assertNotEqual(result.returncode,0)
                self.assertTrue(directory.exists())

    def test_other_sticky_parent_does_not_gain_tmp_exception(self):
        self.runtime.parent.chmod(0o1777)
        result,reply=self.run_tail()
        self.assertNotEqual(result.returncode,0)
        self.assertTrue(self.runtime.exists())
        self.assertEqual(reply.get('cleanup_error'),'unsafe-cleanup-member')

    def test_sticky_private_boot_leaf_does_not_gain_parent_exception(self):
        directory=self.boot_directory();directory.chmod(0o1777)
        result,reply=self.run_tail(TMP_OWNER='0')
        self.assertNotEqual(result.returncode,0)
        self.assertTrue((directory/'session.json').exists())

    def test_unknown_boot_directory_member_is_preserved(self):
        directory=self.boot_directory();(directory/'foreign').write_text('preserve')
        result,reply=self.run_tail();self.assertNotEqual(result.returncode,0)
        self.assertEqual(sorted(p.name for p in directory.iterdir()),['foreign','normal.json','session.json','session.lock'])

    def test_unsafe_boot_directory_and_hardlink_are_preserved(self):
        directory=self.boot_directory();foreign=self.base/'foreign-boot';foreign.write_text('preserve')
        os.link(foreign,directory/'extra-link')
        result,reply=self.run_tail();self.assertNotEqual(result.returncode,0)
        self.assertEqual(foreign.read_text(),'preserve');self.assertTrue((directory/'session.json').exists())
        (directory/'extra-link').unlink();(directory/'session.json').unlink();os.link(foreign,directory/'session.json')
        result,reply=self.run_tail();self.assertNotEqual(result.returncode,0)
        self.assertEqual(foreign.read_text(),'preserve');self.assertTrue((directory/'session.lock').exists())

    def test_boot_directory_symlink_never_follows_foreign_target(self):
        foreign=self.base/'foreign-boot';foreign.mkdir(mode=0o700)
        (foreign/'session.json').write_text('preserve')
        (self.base/'tmp/clean-your-tv-root-boot').symlink_to(foreign,target_is_directory=True)
        result,reply=self.run_tail();self.assertNotEqual(result.returncode,0)
        self.assertEqual((foreign/'session.json').read_text(),'preserve')

    def test_missing_mixed_or_malformed_boot_fact_cannot_retire_runtime(self):
        baseline=self.record['cleanup_boot_id']
        for value in (None,baseline,'22222222-2222-2222-2222-222222222222',baseline+'extra',baseline+'\n'):
            self.record['cleanup_verified_boot_id']=value;self.write('clean-removal-'+ID+'.json',self.record)
            result,reply=self.run_tail();self.assertNotEqual(result.returncode,0)
            self.assertTrue(self.runtime.exists())
            self.assertEqual(json.loads((self.base/'mutations.json').read_text()),[])

    def test_legacy_distinct_raw_boot_fact_remains_valid(self):
        self.record['cleanup_boot_id']='11111111-1111-1111-1111-111111111111'
        self.record['cleanup_verified_boot_id']='22222222-2222-2222-2222-222222222222'
        self.write('clean-removal-'+ID+'.json',self.record)
        result,reply=self.run_tail();self.assertEqual(result.returncode,0,result.stderr)

    def test_changed_owned_runtime_bytes_are_removed_without_execution(self):
        (self.runtime/'lib/secret.py').write_text('changed old bytes; never execute')
        result,reply=self.run_tail()
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertFalse(self.runtime.exists())

    def test_shared_inventory_preserves_foreign_public_stage_at_final_tail(self):
        from cytv.no_root_cleanup import PRIVATE_CLEANUP_PROGRAM
        from cytv.package import ipk
        foreign=self.base/'media/developer/temp'/('cytv-'+'f'*32);foreign.mkdir(parents=True)
        package=foreign/'helper.ipk';package.write_bytes(ipk('org.foreign.app','1.0.0',{},architecture='arm'))
        shared=PRIVATE_CLEANUP_PROGRAM.replace('/media/developer',str(self.base/'media/developer')).replace('/var/luna-service2-dev',str(self.base/'var/luna-service2-dev'))
        shared=shared.replace('/var/lib',str(self.base/'var/lib')).replace('/var/webos-profile',str(self.base/'var/webos-profile')).replace('/proc/sys/kernel/random/boot_id',str(self.base/'proc/sys/kernel/random/boot_id'))
        source=self.base/'current-tail.js'
        injected,count=re.subn(r'\bvar\s+privateCleanupSource\s*=\s*null\s*;',lambda _: 'var privateCleanupSource='+json.dumps(shared)+';',SOURCE.read_text())
        self.assertEqual(count,1,'Expected one private cleanup source declaration')
        source.write_text(injected)
        harness=self.harness.read_text()
        # Only the shared current Node program executes normally; TV RPC stays simulated.
        marker='spawn:function(command,args,options){'
        self.assertIn(marker,harness)
        harness=harness.replace(marker,marker+'if(command==="/usr/bin/node")return require("child_process").spawn(process.execPath,args,options);',1)
        self.harness.write_text(harness)
        result=subprocess.run([os.environ.get('NODE8','node'),str(self.harness),str(self.base),str(source)],capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue(package.exists());self.assertFalse(self.runtime.exists())

    def test_interruption_preserves_pending_and_resume_deletes_remaining_only(self):
        result,reply=self.run_tail(FAIL_MEMBER='secret.py')
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(reply['reason'],'private-cleanup-incomplete')
        self.assertFalse((self.runtime/'bin/python3.13').exists())
        self.assertEqual(json.loads((self.state/('clean-removal-'+ID+'.json')).read_text())['stage'],'private-cleanup')
        result,reply=self.run_tail();self.assertEqual(result.returncode,0,result.stderr)
        calls=json.loads((self.base/'mutations.json').read_text())
        self.assertEqual([p for kind,p in calls if kind=='unlinkSync'],[str(self.runtime/'lib/secret.py')])

    def test_owned_runtime_symlink_is_unlinked_without_following_foreign_target(self):
        foreign=self.base/'foreign';foreign.write_text('keep foreign bytes')
        target=self.runtime/'lib/secret.py';target.unlink();target.symlink_to(foreign)
        result,reply=self.run_tail();self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(foreign.read_text(),'keep foreign bytes')
        self.assertFalse(self.runtime.exists())

    def test_foreign_similar_service_activities_do_not_block_tail(self):
        activities=[{'name':'com.cleanyourtv.recoveryprobe.boot','activityId':42,'callback':{'method':'luna://com.cleanyourtv.recoveryprobe.service/boot'}},
                    {'name':'foreign','activityId':43,'callback':{'method':'luna://com.cleanyourtv.root.preview.service.foreign/boot'}}]
        result,reply=self.run_tail(ACTIVITIES=json.dumps(activities))
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(reply['stage'],'verified-clean')

    def test_each_known_service_activity_and_reserved_recovery_name_block_tail(self):
        methods=['luna://'+app+('.renewal/' if app=='com.gathin.tvhome' else '.service/')+'unexpected' for app in APPS]
        activities=[{'name':'unexpected','activityId':7,'callback':{'method':method}} for method in methods]
        activities.append({'name':'com.cleanyourtv.root.preview.service.recovery','activityId':8,'callback':{'method':'luna://foreign.service/boot'}})
        for activity in activities:
            with self.subTest(activity=activity):
                result,reply=self.run_tail(ACTIVITIES=json.dumps([activity]))
                self.assertNotEqual(result.returncode,0)
                self.assertTrue(self.runtime.exists())
                self.assertEqual(json.loads((self.base/'mutations.json').read_text()),[])

    def test_failure_exposes_only_known_guard_code(self):
        result,reply=self.run_tail(FOREIGN_ROUTE='1')
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(reply.get('cleanup_error'),'route-changed')
        self.assertEqual(result.stderr,'CYTV_CLEAN_TAIL: route-changed\n')
        for private in ('sensitivecredential','ENOENT: private path /private/secret-key'):
            result,reply=self.run_tail(PRIVATE_ERROR=private)
            self.assertNotEqual(result.returncode,0)
            self.assertEqual(reply.get('cleanup_error'),'cleanup-readback-unavailable')
            self.assertNotIn(private,result.stdout+result.stderr)
            self.assertEqual(result.stderr,'CYTV_CLEAN_TAIL: cleanup-readback-unavailable\n')

    def test_changed_foreign_route_refuses_before_delete(self):
        result,reply=self.run_tail(FOREIGN_ROUTE='1')
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(json.loads((self.base/'mutations.json').read_text()),[])

    def test_inspect_needs_no_runtime_or_mutation(self):
        result,reply=self.run_tail(MODE='inspect')
        self.assertEqual(reply['state'],'tail-ready')
        self.assertEqual(json.loads((self.base/'mutations.json').read_text()),[])

    def test_corrupt_schema_or_lease_never_retires_runtime(self):
        lease=json.loads((self.state/'operation.json').read_text())
        for change in ({'schema':None},{'id':'different'},{'owner':'product'},{'terminal':True},{'stage':'complete'},{'unknown':'value'}):
            with self.subTest(change=change):
                self.write('operation.json',{**lease,**change})
                result,reply=self.run_tail();self.assertNotEqual(result.returncode,0)
                self.assertEqual(json.loads((self.base/'mutations.json').read_text()),[])
        self.write('operation.json',lease)
        original=dict(self.record)
        for removal in (None,ID+'x',123):
            self.write('clean-removal-'+ID+'.json',{**original,'removal':removal})
            result,reply=self.run_tail();self.assertNotEqual(result.returncode,0)
            self.assertEqual(json.loads((self.base/'mutations.json').read_text()),[])
        self.record.pop('schema');self.write('clean-removal-'+ID+'.json',self.record)
        result,reply=self.run_tail();self.assertNotEqual(result.returncode,0)
        self.assertEqual(json.loads((self.base/'mutations.json').read_text()),[])

    def test_stock_settings_tail_finishes_without_systemprofile(self):
        self.record['profileless_cleanup_eligible']=True
        self.record['routes']={'mode':'stock-settings','home':'com.webos.app.home'}
        self.write('clean-removal-'+ID+'.json',self.record)
        missing=json.dumps({'returnValue':False,'errorCode':-1,'errorText':'Service does not exist: com.webos.service.systemprofile.'})
        result,reply=self.run_tail(MISSING_PROFILES='1',PROFILE_ERROR=missing,SETTINGS_HOME='com.webos.app.home')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(reply['stage'],'verified-clean')
        self.assertFalse(self.runtime.exists())

    def compositor_record(self):
        self.record['profileless_cleanup_eligible']=True
        home=self.base/'usr/bin/com.webos.app.home';home.parent.mkdir(parents=True)
        home.write_bytes(b'\x7fELF\x01\x01\x01'+b'\0'*11+b'\x28\0'+b'\0'*32);home.chmod(0o700)
        appinfo=self.base/'usr/palm/applications/com.webos.app.home/appinfo.json'
        appinfo.parent.mkdir(parents=True);appinfo.write_text(json.dumps({'id':'com.webos.app.home','type':'native','main':'/usr/bin/com.webos.app.home'}))
        vendor=self.base/'usr/lib/qml/KeyFilters/systemUi.js';vendor.parent.mkdir(parents=True)
        vendor.write_text('function handleSystemKeys() { return Qt.Key_Super_L; }')
        (self.base/'proc/self').mkdir();(self.base/'proc/self/mountinfo').write_text('2 1 179:27 / /usr ro,relatime - squashfs /dev/mmcblk0p27 ro\n')
        self.record['routes']={'mode':'stock-compositor','target':{'dev':45851,'ino':home.stat().st_ino,'size':home.stat().st_size},'target_sha256':hashlib.sha256(home.read_bytes()).hexdigest()}
        self.write('routing-backup-'+ID+'.json',{})
        self.write('clean-removal-'+ID+'.json',self.record)
        return home,appinfo,vendor

    def compositor_tail(self,**env):
        return self.run_tail(NO_SYNC='1',SYSTEM_DEVICE='1',NO_HOME_APIS='1',MISSING_PROFILES='1',
            PROFILE_ERROR=json.dumps({'returnValue':False,'errorCode':-1,'errorText':'Service does not exist: com.webos.service.systemprofile.'}),**env)

    def test_current_stock_compositor_tail_finishes_without_home_settings(self):
        self.compositor_record()
        result,reply=self.compositor_tail()
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(reply['stage'],'verified-clean')
        self.assertFalse(self.runtime.exists())

    def test_stock_compositor_read_only_recheck_refuses_new_foreign_home_state(self):
        self.compositor_record()
        result,reply=self.compositor_tail(MODE='stock-proof')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(reply['routes'],self.record['routes'])
        self.assertTrue(self.runtime.exists())
        for name,raw in (('var/lib/luma-home',None),('home/root/.config/lginputhook/keybinds.json','{"773":{}}')):
            with self.subTest(path=name):
                path=self.base/name;path.parent.mkdir(parents=True,exist_ok=True)
                if raw is None:path.mkdir()
                else:path.write_text(raw)
                result,_=self.compositor_tail(MODE='stock-proof')
                self.assertNotEqual(result.returncode,0)
                self.assertEqual(json.loads((self.base/'mutations.json').read_text()),[])
                if path.is_dir():path.rmdir()
                else:path.unlink()

    def test_stock_compositor_tail_refuses_changed_identity_chain_mount_or_evidence(self):
        home,appinfo,vendor=self.compositor_record()
        mount=self.base/'proc/self/mountinfo';stock=mount.read_text()
        for change in ('binary','manifest','vendor','mount','stack','backup','live','chain'):
            with self.subTest(change=change):
                original=home.read_bytes(),appinfo.read_bytes(),vendor.read_bytes()
                if change=='binary':home.write_bytes(original[0]+b'changed')
                if change=='manifest':appinfo.write_text('{}')
                if change=='vendor':vendor.write_text('unknown vendor contract')
                if change=='mount':mount.write_text(stock.replace('squashfs','tmpfs'))
                if change=='stack':mount.write_text(stock+'3 2 179:27 /bin /usr/bin ro - squashfs /dev/mmcblk0p27 ro\n')
                if change=='backup':self.write('routing-backup-'+ID+'.json',{'profile-trial.json':'{}'})
                marker=self.base/'var/lib/clean-your-tv-root/persistent-intent.json'
                if change=='live':marker.parent.mkdir(exist_ok=True);marker.write_text('{}')
                result,_=self.compositor_tail(**({'FILTER_CHAIN':'[{"file":"/foreign/home.js","handler":"home"}]'} if change=='chain' else {}))
                self.assertNotEqual(result.returncode,0)
                self.assertTrue(self.runtime.exists())
                self.assertEqual(json.loads((self.base/'mutations.json').read_text()),[])
                home.write_bytes(original[0]);appinfo.write_bytes(original[1]);vendor.write_bytes(original[2]);mount.write_text(stock)
                self.write('routing-backup-'+ID+'.json',{})
                if marker.exists():marker.unlink();marker.parent.rmdir()

    def test_stock_settings_tail_requires_exact_missing_service_and_stock_readback(self):
        self.record['profileless_cleanup_eligible']=True
        self.record['routes']={'mode':'stock-settings','home':'com.webos.app.home'}
        self.write('clean-removal-'+ID+'.json',self.record)
        for reply in ({'returnValue':False,'errorCode':-1,'errorText':'Permission denied'},
                      {'returnValue':False,'errorCode':-1,'errorText':'Service does not exist: another.service.'},
                      {'returnValue':False,'errorCode':True,'errorText':'Service does not exist: com.webos.service.systemprofile.'},
                      {'returnValue':False}, {'errorCode':-1}, [],
                      {'returnValue':True}, {'returnValue':True,'profiles':None},
                      {'returnValue':True,'profiles':{}}):
            with self.subTest(reply=reply):
                result,_=self.run_tail(MISSING_PROFILES='1',PROFILE_ERROR=json.dumps(reply),SETTINGS_HOME='com.webos.app.home')
                self.assertNotEqual(result.returncode,0)
                self.assertEqual(json.loads((self.base/'mutations.json').read_text()),[])
                self.assertTrue(self.runtime.exists())
        missing=json.dumps({'returnValue':False,'errorCode':-1,'errorText':'Service does not exist: com.webos.service.systemprofile.'})
        result,_=self.run_tail(MISSING_PROFILES='1',PROFILE_ERROR=missing,SETTINGS_HOME='third.party.home')
        self.assertNotEqual(result.returncode,0)
        self.assertTrue(self.runtime.exists())
        # A service appearing later cannot silently change the selected contract.
        result,_=self.run_tail(SETTINGS_HOME='com.webos.app.home')
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(json.loads((self.base/'mutations.json').read_text()),[])
        self.record.pop('profileless_cleanup_eligible')
        self.write('clean-removal-'+ID+'.json',self.record)
        result,_=self.run_tail(MISSING_PROFILES='1',PROFILE_ERROR=missing,SETTINGS_HOME='com.webos.app.home')
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(json.loads((self.base/'mutations.json').read_text()),[])

    def untouched_record(self):
        self.record.update(routing_never_applied=True,profileless_cleanup_eligible=True,
            fenced_components={'deploy':{'stage':'install-observed'}},routes={'mode':'never-applied'})
        self.write('routing-backup-'+ID+'.json',{})
        self.write('clean-removal-'+ID+'.json',self.record)

    def test_untouched_home_tail_finishes_without_home_apis(self):
        self.untouched_record()
        result,reply=self.run_tail(NO_HOME_APIS='1',MISSING_PROFILES='1')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(reply['stage'],'verified-clean')
        self.assertFalse(self.runtime.exists())

    def test_untouched_home_tail_refuses_missing_or_contradictory_proof(self):
        for evidence in ('backup','missing-backup','phase','eligibility','live'):
            with self.subTest(evidence=evidence):
                self.untouched_record()
                marker=None
                if evidence=='backup':self.write('routing-backup-'+ID+'.json',{'profile-trial.json':'{}'})
                if evidence=='missing-backup':(self.state/('routing-backup-'+ID+'.json')).unlink()
                if evidence=='phase':self.record['fenced_components']['deploy']['stage']='installed-recovery-only'
                if evidence=='eligibility':self.record['profileless_cleanup_eligible']=False
                if evidence=='live':
                    marker=self.base/'var/lib/clean-your-tv-root/persistent-intent.json'
                    marker.parent.mkdir(exist_ok=True);marker.write_text('{}')
                self.write('clean-removal-'+ID+'.json',self.record)
                result,reply=self.run_tail(NO_HOME_APIS='1')
                self.assertNotEqual(result.returncode,0)
                self.assertTrue(self.runtime.exists())
                self.assertEqual(json.loads((self.base/'mutations.json').read_text()),[])
                if marker:marker.unlink();marker.parent.rmdir()

    def test_only_recorded_never_applied_routing_allows_missing_profile_interface(self):
        result,reply=self.run_tail(MISSING_PROFILES='1');self.assertNotEqual(result.returncode,0)
        self.assertEqual(json.loads((self.base/'mutations.json').read_text()),[])
        self.record['routing_never_applied']=True
        self.record['routes']={'mode':'never-applied','home':'third.party.home'}
        self.write('clean-removal-'+ID+'.json',self.record)
        result,reply=self.run_tail(MISSING_PROFILES='1');self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(reply['stage'],'verified-clean')

    def test_absent_package_with_live_helper_or_owned_private_file_is_not_clean(self):
        process=self.base/'proc/123';process.mkdir()
        (process/'cmdline').write_bytes(b'/media/developer/apps/usr/palm/applications/com.local.nativehome/relay\0')
        result,reply=self.run_tail();self.assertNotEqual(result.returncode,0)
        self.assertEqual(json.loads((self.base/'mutations.json').read_text()),[])

    def test_exact_service_directory_and_home_renewal_are_live_writers(self):
        process=self.base/'proc/456';process.mkdir()
        for service in ('com.local.nativehome.service','com.gathin.tvhome.renewal'):
            with self.subTest(service=service):
                (process/'cmdline').write_bytes(('/usr/bin/node\0/usr/palm/services/jsservicelauncher/bootstrap-node.js\0/media/developer/apps/usr/palm/services/'+service+'\0').encode())
                result,reply=self.run_tail();self.assertNotEqual(result.returncode,0)
                self.assertEqual(json.loads((self.base/'mutations.json').read_text()),[])
        (process/'cmdline').unlink();process.rmdir()
        state=self.base/'var/lib/clean-your-tv-root';state.mkdir()
        (state/'ssap.json').write_text('private')
        result,reply=self.run_tail();self.assertNotEqual(result.returncode,0)
        self.assertEqual(json.loads((self.base/'mutations.json').read_text()),[])

    @unittest.skipUnless(os.environ.get('CYTV_REAL_PROC_FD')=='1','requires real Linux /proc directory descriptors')
    def test_directory_replacement_cannot_redirect_pinned_deletions(self):
        result,reply=self.run_tail(SWAP_RUNTIME='1')
        self.assertNotEqual(result.returncode,0)
        self.assertEqual((self.runtime/'foreign').read_text(),'preserve replacement')
        self.assertEqual(json.loads((self.state/('clean-removal-'+ID+'.json')).read_text())['stage'],'private-cleanup')
