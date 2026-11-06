"""Real-file Node tail tests with TV RPC and Linux fd-path translation adapters.

The macOS adapter resolves /proc/self/fd paths to stationary fixture paths. It
tests inventories, retries and receipts, NOT Linux rename-race confinement; that
requires the unchanged source on a Linux runner. Production has no test hooks.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SOURCE=Path(__file__).resolve().parents[1]/'cleanup_tail.js'
RUNTIME='/var/lib/clean-your-tv-python/4a71641c8d5536175e404a961624e8656eba30e97b5026f6bd7dc31e4bbeaaea'
STATE='/var/lib/clean-your-tv-installation'
ID='a'*32
APPS=('com.cleanyourtv.root.preview','com.cleanyourtv.root.updater','com.cleanyourtv.system.updater','com.cleanyourtv.updater','com.local.nativehome','com.gathin.tvhome')
def packages():
    return {app:{'state':'absent','readback':{'app':app,'absent':True}} for app in APPS}
HARNESS=r'''
var real=require('fs'),vm=require('vm'),base=process.argv[2],source=process.argv[3],paths={},calls=[];
function path(p){
 if(typeof p!=='string')return p;
 if(p==='/')return base;
 var match=/^\/proc\/self\/fd\/(\d+)(.*)$/.exec(p);
 if(match)return process.env.CYTV_REAL_PROC_FD==='1'?p:paths[match[1]]+match[2];
 return /^\/(var|media|tmp|proc)(\/|$)/.test(p)?base+p:p;
}
var fs=Object.create(real);
fs.openSync=function(p,flags,mode){var fd=real.openSync(path(p),flags,mode);paths[fd]=path(p);return fd;};
['lstatSync','readFileSync','readlinkSync','readdirSync','rmdirSync','unlinkSync'].forEach(function(name){fs[name]=function(p){
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
 return real[name](path(p));
};});
fs.renameSync=function(a,b){return real.renameSync(path(a),path(b));};
var lock=process.env.OWNERSHIP_FD?Number(process.env.OWNERSHIP_FD):fs.openSync('/var/lib/clean-your-tv-installation/ownership.lock','r+');
var promotion=process.env.PROMOTION_FD?Number(process.env.PROMOTION_FD):fs.openSync('/var/lib/clean-your-tv-python/.install.lock','r+');
var worker=process.env.WORKER_FD?Number(process.env.WORKER_FD):fs.openSync('/var/lib/clean-your-tv-installation/worker.lock','r+');
var fake={getuid:process.getuid,pid:999999,ppid:999998,argv:['node','-',process.env.MODE||'finish','aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',process.env.TAIL_STAGE||'-',String(lock),String(promotion),String(worker),process.env.GATE_SHA||'-',process.env.REMOVAL||'dddddddddddddddddddddddddddddddd'],stdout:process.stdout};
var cp={spawnSync:function(command,args,options){
 if(command==='/proc/self/fd/3')return require('child_process').spawnSync(command,args,options);
 var method=args[2],value={returnValue:true};
 if(method.indexOf('listApps')!==-1)value.apps=[];
 else if(method.indexOf('getSystemSettings')!==-1)value.settings={defaultApps:{home:process.env.FOREIGN_ROUTE?'changed':'third.party.home'}};
 else if(method.indexOf('getProfiles')!==-1){if(process.env.MISSING_PROFILES)value.returnValue=false;else value.profiles={defaultApps:{categories:{home:'third.party.home'}},idleApp:{appId:'third.party.home'}};}
 else if(method.indexOf('activitymanager')!==-1)value.activities=[];
 else if(method.indexOf('getAllInputStatus')!==-1)value.devices=[];
 else throw Error('Unexpected RPC '+method);
 return {status:0,stdout:Buffer.from(JSON.stringify(value))};
}};
try{vm.runInNewContext(real.readFileSync(source,'utf8').replace('}catch(error){','}catch(error){console.error(error.stack);'),{require:function(name){return name==='fs'?fs:name==='child_process'?cp:require(name);},process:fake,Buffer:Buffer,console:console});}
finally{real.closeSync(lock);real.writeFileSync(process.env.MUTATION_LOG||base+'/mutations.json',JSON.stringify(calls));}
process.exitCode=fake.exitCode||0;
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
            state='recovery_required',cleanup_boot_id='11111111-1111-1111-1111-111111111111',routes=['third.party.home']*3,support_stages=[],packages=packages(),
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
        self.record['cleanup_boot_id']='22222222-2222-2222-2222-222222222222'
        self.write('clean-removal-'+ID+'.json',self.record)
        result,reply=self.run_tail();self.assertNotEqual(result.returncode,0)
        self.assertEqual(json.loads((self.base/'mutations.json').read_text()),[])

    def test_interruption_preserves_pending_and_resume_deletes_remaining_only(self):
        result,reply=self.run_tail(FAIL_MEMBER='secret.py')
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(reply['reason'],'private-cleanup-incomplete')
        self.assertFalse((self.runtime/'bin/python3.13').exists())
        self.assertEqual(json.loads((self.state/('clean-removal-'+ID+'.json')).read_text())['stage'],'private-cleanup')
        result,reply=self.run_tail();self.assertEqual(result.returncode,0,result.stderr)
        calls=json.loads((self.base/'mutations.json').read_text())
        self.assertEqual([p for kind,p in calls if kind=='unlinkSync'],[str(self.runtime/'lib/secret.py')])

    def test_changed_owned_runtime_source_and_symlink_refuse_before_delete(self):
        for change in ('bytes','symlink'):
            with self.subTest(change=change):
                target=self.runtime/'lib/secret.py'
                if change=='bytes':target.write_text('different executable')
                else:target.unlink();target.symlink_to(self.runtime/'bin/python3.13')
                result,reply=self.run_tail();self.assertNotEqual(result.returncode,0)
                self.assertEqual(json.loads((self.base/'mutations.json').read_text()),[])

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
