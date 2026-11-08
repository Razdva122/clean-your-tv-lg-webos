"""Admission and successor ownership never depend on retained TV Python."""
import hashlib
import json
import os
import shutil
from pathlib import Path
import tempfile
import subprocess
import sys
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from cytv.errors import UserError, TVCommandError


class HandoffSupport(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()
        bundle=self.root/'root-updater';bundle.mkdir()
        source=b'verified read-only cleanup support'
        (bundle/'cleanup_tail.js').write_bytes(source)
        (bundle/'bundle.json').write_text(json.dumps({'files':{'cleanup_tail.js':hashlib.sha256(source).hexdigest()}}))
        support=self.root/'installer-support';support.mkdir()
        (support/'lifecycle-gate').write_bytes(b'gate')
        self.installer=SimpleNamespace(payload=self.root,manifest={'files':{'installer-support/lifecycle-gate':hashlib.sha256(b'gate').hexdigest()}},
            remote=Mock(root=True),profile={'edition':'no-root','connection':'root-ssh'},tv_info={})

    def test_changed_support_refuses_before_any_device_effect(self):
        from cytv.root_no_root_handoff import support
        (self.root/'root-updater/cleanup_tail.js').write_bytes(b'changed')
        self.installer.tv_info['node_version']='20.12.2'
        with self.assertRaises(UserError):support(self.installer)
        self.installer.remote.upload.assert_not_called()

    def test_normal_support_is_loaded_without_tv_python(self):
        from cytv.root_no_root_handoff import support
        self.installer.tv_info['node_version']='20.12.2'
        source,gate=support(self.installer)
        self.assertEqual(source,'verified read-only cleanup support')
        self.assertEqual(gate,b'gate')
        self.installer.remote.run.assert_not_called()

    def test_handoff_stamp_is_strict_and_cannot_redirect_paths(self):
        from cytv.root_no_root_handoff import validate
        stamp={'operation':'a'*32,'removal':'b'*32,'lease':'c'*32}
        self.assertEqual(validate(stamp),stamp)
        for changed in ({},dict(stamp,path='/foreign'),dict(stamp,lease='../foreign'),dict(stamp,operation=None)):
            with self.subTest(changed=changed),self.assertRaises(UserError):validate(changed)

    def test_legacy_support_uses_stdin_and_observer_arguments_remain_bounded(self):
        from cytv.root_no_root_handoff import call
        from cytv import no_root_observer as observer
        remote=Mock();remote.run.return_value='{}'
        loaded=('x'*350000,b'gate')
        call(remote,loaded,'probe')
        native=next(item for item in remote.run.call_args_list if 'root-clean-lock' in item.args[0])
        self.assertEqual(native.kwargs['data'],loaded[0].encode())
        self.assertNotIn(loaded[0],native.args[0])
        remote.reset_mock();remote.run.return_value='{}'
        stamp=dict(operation='a'*32,removal='b'*32,lease='c'*32)
        plan=observer.make_plan('d'*32,'e'*32,'remove',{}, {},root_ssh=True,root_handoff=stamp)
        call(remote,loaded,'observer',plan=plan,source=observer.ROOT_PROGRAM,request={'plan':plan,'command':'status'})
        native=next(item for item in remote.run.call_args_list if 'root-clean-lock' in item.args[0])
        self.assertIsNone(native.kwargs['data'])
        self.assertLess(len(native.args[0].encode()),120000)
        self.assertIn('while :',native.args[0])

    def test_only_root_transport_can_bind_the_completed_removal(self):
        from cytv import no_root_observer as observer
        stamp=dict(operation='a'*32,removal='b'*32,lease='c'*32)
        with self.assertRaises(UserError):observer.make_plan('d'*32,'e'*32,'remove',{}, {},root_handoff=stamp)
        plan=observer.make_plan('d'*32,'e'*32,'remove',{}, {},root_ssh=True,root_handoff=stamp)
        self.assertEqual(plan['root_handoff'],stamp)
        self.assertEqual(plan['source_sha256'],hashlib.sha256(observer.ROOT_PROGRAM.encode()).hexdigest())


HARNESS=r'''
var real=require('fs'),vm=require('vm'),base=process.argv[2],input=JSON.parse(process.argv[3]),source=process.argv[4];
var paths={},native={},events=[];
function path(p){if(typeof p!=='string')return p;if(p==='/')return base;var m=/^\/proc\/self\/fd\/(\d+)(.*)$/.exec(p);if(m)return paths[m[1]]+m[2];if(p==='/var'||p==='/tmp'||p==='/media'||p.indexOf('/var/')===0||p.indexOf('/tmp/')===0||p.indexOf('/media/')===0)return base+p;return p;}
var fs=Object.create(real);
fs.openSync=function(p,flags,mode){var fd=real.openSync(path(p),flags,mode);paths[fd]=path(p);return fd;};
native[3]=real.openSync(base+'/var/lib/clean-your-tv-installation/ownership.lock','r');
native[5]=real.openSync(base+'/var/lib/clean-your-tv-installation/worker.lock','r');
if(input.promotion_fd4)native[4]=real.openSync(base+'/var/lib/clean-your-tv-python/.install.lock','r');
fs.fstatSync=function(fd){if(fd===4&&!native[4]){if(input.internal_fd4){var other=real.fstatSync(native[3]);other.uid=0;return other;}var e=Error('closed');e.code='EBADF';throw e;}var s=real.fstatSync(native[fd]||fd);s.uid=0;return s;};
fs.lstatSync=function(p){var s=real.lstatSync(path(p));s.uid=0;return s;};
['readdirSync','rmdirSync','unlinkSync'].forEach(function(name){fs[name]=function(p){return real[name](path(p));};});
fs.mkdirSync=function(p,mode){return real.mkdirSync(path(p),mode);};
fs.linkSync=function(a,b){return real.linkSync(path(a),path(b));};
fs.renameSync=function(a,b){if(input.fail_owner_write&&b.slice(-15)==='/operation.json')throw Error('interrupted owner publication');return real.renameSync(path(a),path(b));};
fs.readFileSync=function(p){return real.readFileSync(path(p));};
var cp={spawnSync:function(command,args,opts){events.push({kind:'verify',args:args,stdio:opts.stdio});return {status:input.fail_verify?1:0,stdout:new Buffer(JSON.stringify({state:'verified-clean',operation:'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',removal:'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',lease:'cccccccccccccccccccccccccccccccc'}))};},spawn:function(command,args,opts){events.push({kind:'spawn',command:command,args:args,stdio:opts.stdio,detached:opts.detached});return {unref:function(){}};}};
var fake=Object.create(process);fake.getuid=function(){return 0;};fake.argv=['node','-e',JSON.stringify(input)];
try{vm.runInNewContext(real.readFileSync(source,'utf8'),{require:function(name){return name==='fs'?fs:name==='child_process'?cp:require(name);},process:fake,Buffer:Buffer,console:console,setTimeout:setTimeout,clearTimeout:clearTimeout,setImmediate:setImmediate});}
catch(e){process.stderr.write(e.stack||e.message);process.exitCode=1;}
finally{real.writeFileSync(base+'/events.json',JSON.stringify(events));}
'''


@unittest.skipIf(os.name=='nt','POSIX lock descriptor fixture')
class SuccessorOwnership(unittest.TestCase):
    def setUp(self):
        from cytv.root_no_root_handoff import PROGRAM
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name).resolve();self.base.chmod(0o700)
        self.state=self.base/'var/lib/clean-your-tv-installation';self.state.mkdir(parents=True,mode=0o700)
        for parent in self.state.parents:
            if parent==self.base:break
            parent.chmod(0o700)
        for name in ('ownership.lock','worker.lock'):(self.state/name).touch(mode=0o600)
        self.stamp=dict(operation='a'*32,removal='b'*32,lease='c'*32)
        self.write('operation.json',dict(schema=1,id='c'*32,owner='clean-removal',journal='product-'+'a'*32+'.json',stage='verified-clean',terminal=False))
        self.write('clean-removal-'+'a'*32+'.json',dict(removal='b'*32,lease='9'*32,
            final_fence='c'*32,final_original_lease='9'*32,stage='verified-clean',current=True))
        self.program=self.base/'guard.js';self.program.write_text(PROGRAM)
        self.harness=self.base/'harness.js';self.harness.write_text(HARNESS)
        self.source="process.stdout.write(JSON.stringify({operation:JSON.parse(process.argv[process.argv.length-1]).plan.operation}));"
        self.plan=dict(connection='root-ssh',operation='d'*32,root_handoff=self.stamp,source_sha256=hashlib.sha256(self.source.encode()).hexdigest())

    def write(self,name,value):
        path=self.state/name;path.write_text(json.dumps(value));path.chmod(0o600)

    def run_guard(self,command,plan=None,**extra):
        from cytv.root_no_root_handoff import PROGRAM
        value=dict(command=command,cleanup='verified cleanup source',wrapper=PROGRAM)
        if plan is not None:value['plan']=plan
        value.update(extra)
        return subprocess.run([os.environ.get('HANDOFF_NODE','node'),str(self.harness),str(self.base),json.dumps(value),str(self.program)],capture_output=True,text=True,timeout=10)

    def test_probe_is_read_only_and_unverified_cleanup_never_claims(self):
        before=(self.state/'operation.json').read_bytes()
        result=self.run_guard('probe');self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),self.stamp)
        self.assertEqual((self.state/'operation.json').read_bytes(),before)
        result=self.run_guard('claim',self.plan,fail_verify=True)
        self.assertEqual(result.returncode,1)
        self.assertEqual((self.state/'operation.json').read_bytes(),before)
        self.assertFalse((self.state/('no-root-'+'d'*32+'.json')).exists())

    def test_unrelated_node_fd4_is_not_an_inherited_python_promotion_lock(self):
        result=self.run_guard('claim',self.plan,internal_fd4=True)
        self.assertEqual(result.returncode,0,result.stderr)
        event=json.loads((self.base/'events.json').read_text())[0]
        self.assertEqual(event['args'][5],'-1')
        self.assertEqual(event['stdio'][4],'ignore')

    def test_existing_python_promotion_lock_requires_the_exact_inherited_inode(self):
        parent=self.base/'var/lib/clean-your-tv-python';parent.mkdir(mode=0o755)
        (parent/'.install.lock').touch(mode=0o600)
        self.assertEqual(self.run_guard('claim',self.plan,internal_fd4=True).returncode,1)
        result=self.run_guard('claim',self.plan,promotion_fd4=True)
        self.assertEqual(result.returncode,0,result.stderr)
        event=json.loads((self.base/'events.json').read_text())[0]
        self.assertEqual(event['args'][5],'4')
        self.assertEqual(event['stdio'][4],4)

    def test_claim_is_bound_idempotent_and_changed_plan_cannot_take_active_owner(self):
        result=self.run_guard('claim',self.plan);self.assertEqual(result.returncode,0,result.stderr)
        lease=json.loads((self.state/'operation.json').read_text())
        self.assertEqual(lease['owner'],'no-root');self.assertFalse(lease['terminal'])
        self.assertNotEqual(lease['id'],self.stamp['lease'])
        self.assertEqual(self.run_guard('claim',self.plan).returncode,0)
        for changed in (dict(self.plan,source_sha256='e'*64),dict(self.plan,operation='e'*32)):
            result=self.run_guard('claim',changed)
            self.assertEqual(result.returncode,1,result.stdout)
            self.assertEqual(json.loads((self.state/'operation.json').read_text()),lease)

    def test_release_keeps_successor_fenced_if_current_absence_fails(self):
        self.assertEqual(self.run_guard('claim',self.plan).returncode,0)
        before=(self.state/'operation.json').read_bytes()
        self.assertEqual(self.run_guard('release',fail_verify=True).returncode,1)
        self.assertEqual((self.state/'operation.json').read_bytes(),before)
        result=self.run_guard('release');self.assertEqual(result.returncode,0,result.stderr)
        lease=json.loads((self.state/'operation.json').read_text())
        self.assertEqual(lease['owner'],'clean-removal');self.assertEqual(lease['stage'],'verified-clean')

    def test_detached_worker_inherits_original_locks_and_exact_wrapper(self):
        self.source="var input=JSON.parse(process.argv[process.argv.length-1]);require('child_process').spawn(process.execPath,['/tmp/.cytv-installer-root/operations/'+input.plan.operation+'/observer.js',JSON.stringify({command:'worker',plan:input.plan})],{cwd:'/tmp'}).unref();"
        self.plan['source_sha256']=hashlib.sha256(self.source.encode()).hexdigest()
        self.assertEqual(self.run_guard('claim',self.plan).returncode,0)
        result=self.run_guard('observer',self.plan,source=self.source,request={'plan':self.plan,'command':'start'})
        self.assertEqual(result.returncode,0,result.stderr)
        event=json.loads((self.base/'events.json').read_text())[-1]
        self.assertEqual(event['stdio'],['ignore','ignore','ignore',3,'ignore',5])
        self.assertTrue(event['detached'])
        self.assertEqual(event['args'][0],'-e')
        child=json.loads(event['args'][2]);self.assertEqual(child['plan'],self.plan)
        self.assertEqual(child['request']['command'],'worker')

    def test_pre_submission_continuation_is_read_only_and_never_replays_lost_evidence(self):
        before=(self.state/'operation.json').read_bytes()
        result=self.run_guard('continuation',self.plan)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['state'],'unclaimed')
        self.assertEqual(before,(self.state/'operation.json').read_bytes())
        self.assertEqual(self.run_guard('claim',self.plan).returncode,0)
        result=self.run_guard('continuation',self.plan)
        self.assertEqual(json.loads(result.stdout)['state'],'unprepared')
        name='no-root-'+self.plan['operation']+'.json'
        binding=json.loads((self.state/name).read_text());binding['effects_started']=True;self.write(name,binding)
        result=self.run_guard('continuation',self.plan)
        self.assertEqual(json.loads(result.stdout)['state'],'observing')

    def test_cleanup_revokes_old_capsule_even_when_original_clean_fence_returns(self):
        self.assertEqual(self.run_guard('claim',self.plan).returncode,0)
        self.assertEqual(self.run_guard('release').returncode,0)
        self.assertEqual(self.run_guard('claim',self.plan).returncode,1)

    def test_malformed_successor_receipt_refuses_before_another_effect(self):
        self.assertEqual(self.run_guard('claim',self.plan).returncode,0)
        name='no-root-'+self.plan['operation']+'.json'
        original=json.loads((self.state/name).read_text())
        for field,value in (('source_sha256',None),('effects_started','false'),('revoked','false')):
            with self.subTest(field=field):
                self.write(name,dict(original,**{field:value}))
                self.assertEqual(self.run_guard('claim',self.plan).returncode,1)
                self.assertEqual(json.loads((self.base/'events.json').read_text()),[])

    def original_prepare_request(self):
        from cytv import no_root_observer as observer
        # Real fixed-path observer bytes run through the filesystem adapter;
        # public TV ancestors are searchable, private operation leaves are not.
        for directory in (self.base,self.base/'var',self.base/'var/lib'):directory.chmod(0o755)
        (self.base/'tmp').mkdir(mode=0o755)
        self.source=observer.ROOT_PROGRAM
        self.plan=observer.make_plan('d'*32,'e'*32,'install',
            {'helper.ipk':b'helper','launcher.ipk':b'home'},
            {'com.local.nativehome':'0.8.0','com.gathin.tvhome':'1.13.1'},
            root_ssh=True,root_handoff=self.stamp)
        return dict(root=observer.ROOT_SSH_PRIVATE,public_root=observer.ROOT_SSH_PUBLIC,
                    sender='/usr/bin/luna-send',plan=self.plan,command='prepare',source=self.source)

    def closed_successor(self):
        self.assertEqual(self.run_guard('claim',self.plan).returncode,0)
        private=self.base/('tmp/.cytv-installer-root/operations/'+self.plan['operation'])
        private.mkdir(parents=True,mode=0o700)
        value=dict(protocol='no-root-original-stream-v1',operation=self.plan['operation'],
                   plan_sha256=hashlib.sha256(__import__('cytv.no_root_observer',fromlist=['canonical']).canonical(self.plan).encode()).hexdigest(),
                   source_sha256=self.plan['source_sha256'],result='verified')
        path=private/'closed.json';path.write_text(json.dumps(value));path.chmod(0o600)
        self.write('clean-removal-'+'a'*32+'.json',dict(removal='b'*32,lease='9'*32,
            final_fence='c'*32,final_original_lease='9'*32,stage='verified-clean',state='complete',current=True,
            result=dict(verified_clean=True,private_cleanup_verified=True)))

    def test_completed_no_root_owner_can_select_shared_cleanup_without_ignoring_real_root(self):
        self.closed_successor()
        before=(self.state/'operation.json').read_bytes()
        result=self.run_guard('cleanup-target')
        self.assertEqual(result.returncode,0,result.stderr)
        value=json.loads(result.stdout)
        self.assertEqual(value['operation'],self.plan['operation'])
        self.assertEqual(value['lease'],json.loads(before)['id'])
        self.assertEqual((self.state/'operation.json').read_bytes(),before)
        app=self.base/'media/developer/apps/usr/palm/applications/com.cleanyourtv.root.preview'
        app.mkdir(parents=True)
        self.assertEqual(self.run_guard('cleanup-target').returncode,1)
        self.assertEqual((self.state/'operation.json').read_bytes(),before)

    def test_cleanup_target_refuses_unclosed_observer_and_nonminimal_root_state(self):
        self.assertEqual(self.run_guard('claim',self.plan).returncode,0)
        self.assertEqual(self.run_guard('cleanup-target').returncode,1)
        self.closed_successor()
        root=self.base/'var/lib/clean-your-tv-root';root.mkdir(mode=0o700)
        (root/'config.json').write_text('still installed')
        self.assertEqual(self.run_guard('cleanup-target').returncode,1)

    def test_original_observer_prepares_after_clean_probe_removed_public_ancestor(self):
        request=self.original_prepare_request()
        public=self.base/'var/lib/clean-your-tv-installer'
        self.assertFalse(public.exists())
        self.assertEqual(self.run_guard('claim',self.plan).returncode,0)
        result=self.run_guard('observer',self.plan,source=self.source,request=request)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(public.stat().st_mode&0o777,0o755)
        self.assertTrue((public/('cytv-'+self.plan['operation'])).is_dir())
        prepared=self.base/('tmp/.cytv-installer-root/operations/'+self.plan['operation']+'/prepared.json')
        before=prepared.read_bytes();inode=public.stat().st_ino
        result=self.run_guard('observer',self.plan,source=self.source,request=request)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(prepared.read_bytes(),before)
        self.assertEqual(public.stat().st_ino,inode)
        result=self.run_guard('observer',self.plan,source=self.source,request=dict(request,command='status'))
        self.assertEqual(result.returncode,0,result.stderr)
        state=json.loads(result.stdout)
        self.assertEqual(state['reservation'],'active')
        self.assertEqual([s['submission'] for s in state['slots']],['prepared','prepared'])

    def test_unsafe_public_ancestor_refuses_before_original_observer_creates_evidence(self):
        request=self.original_prepare_request()
        public=self.base/'var/lib/clean-your-tv-installer';public.mkdir(mode=0o700)
        self.assertEqual(self.run_guard('claim',self.plan).returncode,0)
        result=self.run_guard('observer',self.plan,source=self.source,request=request)
        self.assertEqual(result.returncode,1)
        self.assertEqual(public.stat().st_mode&0o777,0o700)
        self.assertFalse((self.base/'tmp/.cytv-installer-root').exists())

    def test_changed_prepare_request_cannot_create_successor_staging(self):
        request=self.original_prepare_request()
        self.assertEqual(self.run_guard('claim',self.plan).returncode,0)
        changes=[dict(plan=dict(self.plan,operation='f'*32)),
                 dict(public_root='/var/lib/foreign'),dict(root='/tmp/foreign'),
                 dict(sender='/foreign'),dict(source=self.source+'\n')]
        for change in changes:
            with self.subTest(fields=list(change)):
                result=self.run_guard('observer',self.plan,source=self.source,request=dict(request,**change))
                self.assertEqual(result.returncode,1)
                self.assertFalse((self.base/'var/lib/clean-your-tv-installer').exists())
                self.assertFalse((self.base/'tmp/.cytv-installer-root').exists())

    def test_crash_between_binding_and_owner_resumes_identical_reservation(self):
        before=(self.state/'operation.json').read_bytes()
        self.assertEqual(self.run_guard('claim',self.plan,fail_owner_write=True).returncode,1)
        self.assertEqual(before,(self.state/'operation.json').read_bytes())
        binding=json.loads((self.state/('no-root-'+self.plan['operation']+'.json')).read_text())
        self.assertNotEqual(binding['lease'],self.stamp['lease'])
        result=self.run_guard('claim',self.plan);self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads((self.state/'operation.json').read_text())['id'],binding['lease'])

    def test_crash_during_release_keeps_old_capsule_revoked_until_retry(self):
        self.assertEqual(self.run_guard('claim',self.plan).returncode,0)
        self.assertEqual(self.run_guard('release',fail_owner_write=True).returncode,1)
        self.assertEqual(json.loads((self.state/'operation.json').read_text())['owner'],'no-root')
        self.assertEqual(self.run_guard('claim',self.plan).returncode,1)
        result=self.run_guard('release');self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads((self.state/'operation.json').read_text())['owner'],'clean-removal')


@unittest.skipIf(os.name=='nt' or not shutil.which('cc') or not shutil.which('node'),'POSIX native gate and Node required')
class DelayedWorker(unittest.TestCase):
    @unittest.skipUnless(sys.platform.startswith('linux'),'Requires real Linux /proc/self/fd traversal')
    def test_real_guard_claim_and_detached_worker_keep_original_locks_without_python(self):
        from cytv.root_no_root_handoff import PROGRAM
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp).resolve();state=base/'installation';state.mkdir(mode=0o700)
            for name in ('ownership.lock','worker.lock'):(state/name).touch(mode=0o600)
            gate=base/'gate';source=Path(__file__).resolve().parents[2]/'native/installer/lifecycle-gate.c'
            result=subprocess.run(['cc','-O2','-DCYTV_ROOT_LOCK_DIRECTORY='+json.dumps(str(state)),
                '-DCYTV_RUNTIME_LOCK_DIRECTORY='+json.dumps(str(base/'absent-runtime')),str(source),'-o',str(gate)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            node=shutil.which('node');uid=os.getuid()
            # Only fixed namespace/host UID adaptations; execute the actual
            # guard, native locks, VM observer and detached child processes.
            program=PROGRAM.replace('/var/lib/clean-your-tv-installation',str(state))
            program=program.replace('/var/lib/clean-your-tv-python',str(base/'absent-runtime'))
            program=program.replace('process.getuid() !== 0','process.getuid() !== '+str(uid))
            program=program.replace('s.uid !== 0','[0,'+str(uid)+'].indexOf(s.uid) < 0')
            program=program.replace("'/usr/bin/node'",json.dumps(node))
            marker=base/'worker'
            observer=("var input=JSON.parse(process.argv[process.argv.length-1]);"
                "if(input.command==='worker'){require('fs').appendFileSync("+json.dumps(str(marker))+",'submitted\\n');setTimeout(function(){},1500);}"
                "else{require('child_process').spawn(process.execPath,['/tmp/.cytv-installer-root/operations/'+input.plan.operation+'/observer.js',JSON.stringify({command:'worker',plan:input.plan})],{cwd:"+json.dumps(str(base))+"}).unref();}")
            predecessor=dict(operation='a'*32,removal='b'*32,lease='c'*32)
            plan=dict(connection='root-ssh',operation='d'*32,root_handoff=predecessor,source_sha256=hashlib.sha256(observer.encode()).hexdigest())
            def write(name,value):
                file=state/name;file.write_text(json.dumps(value));file.chmod(0o600)
            write('operation.json',dict(schema=1,id='c'*32,owner='clean-removal',journal='product-'+'a'*32+'.json',stage='verified-clean',terminal=False))
            write('clean-removal-'+'a'*32+'.json',dict(removal='b'*32,final_fence='c'*32,stage='verified-clean',current=True))
            # Cleanup RPC/absence is a fixed proof fixture here; the real
            # cleanup verifier has its independent filesystem/RPC tests.
            proof="process.stdout.write("+json.dumps(json.dumps(dict(state='verified-clean',**predecessor)))+");"
            def run(command,**extra):
                request=dict(command=command,plan=plan,wrapper=program,cleanup=proof)
                request.update(extra)
                return subprocess.run([str(gate),'root-clean-lock',node,'-e',program,json.dumps(request)],capture_output=True,text=True,timeout=10)
            result=run('claim');self.assertEqual(result.returncode,0,result.stderr)
            result=run('observer',source=observer,request={'command':'start','plan':plan})
            self.assertEqual(result.returncode,0,result.stderr)
            deadline=time.monotonic()+3
            while not marker.exists() and time.monotonic()<deadline:time.sleep(.01)
            self.assertTrue(marker.exists(),'The real detached worker never entered its observer')
            busy=subprocess.run([str(gate),'root-clean-lock','/bin/true'],capture_output=True)
            self.assertEqual(busy.returncode,75)
            while time.monotonic()<deadline:
                result=subprocess.run([str(gate),'root-clean-lock','/bin/true'],capture_output=True)
                if result.returncode==0:break
                time.sleep(.05)
            self.assertEqual(result.returncode,0)
            self.assertEqual(marker.read_text(),'submitted\n')

    def test_native_busy_observation_waits_without_repeating_package_worker(self):
        from cytv.root_no_root_handoff import call
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp).resolve();state=base/'installation';state.mkdir(mode=0o700)
            for name in ('ownership.lock','worker.lock'):(state/name).touch(mode=0o600)
            gate=base/'gate';source=Path(__file__).resolve().parents[2]/'native/installer/lifecycle-gate.c'
            built=subprocess.run(['cc','-O2','-DCYTV_ROOT_LOCK_DIRECTORY='+json.dumps(str(state)),
                '-DCYTV_RUNTIME_LOCK_DIRECTORY='+json.dumps(str(base/'absent-runtime')),str(source),'-o',str(gate)],capture_output=True,text=True)
            self.assertEqual(built.returncode,0,built.stderr)
            node=shutil.which('node');marker=base/'worker';observed=base/'observed'
            worker="require('fs').appendFileSync("+json.dumps(str(marker))+",'submitted\\n');setTimeout(function(){},700);"
            parent="require('child_process').spawn(process.execPath,['-e',"+json.dumps(worker)+"],{detached:true,stdio:['ignore','ignore','ignore',3,'ignore',5]}).unref();"
            started=subprocess.run([str(gate),'root-clean-lock',node,'-e',parent],capture_output=True,text=True)
            self.assertEqual(started.returncode,0,started.stderr)
            class Remote:
                busy=0
                def upload(self,*args,**kwargs):pass
                def run(self,command,**kwargs):
                    if 'root-clean-lock' not in command:return ''
                    code="require('fs').appendFileSync("+json.dumps(str(observed))+",'observed\\n');process.stdout.write('{}');"
                    result=subprocess.run([str(gate),'root-clean-lock',node,'-e',code],capture_output=True,text=True)
                    if result.returncode:
                        self.busy+=1;raise TVCommandError(result.returncode)
                    return result.stdout
            remote=Remote();reply=call(remote,('cleanup',gate.read_bytes()),'observer',plan={})
            self.assertEqual(reply,'{}');self.assertGreaterEqual(remote.busy,1)
            self.assertEqual(marker.read_text(),'submitted\n')
            self.assertEqual(observed.read_text(),'observed\n')
