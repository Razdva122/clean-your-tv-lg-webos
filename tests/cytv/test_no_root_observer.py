"""Real Node/filesystem/pipe tests; no TV or vendor requests."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import signal
import unittest
from cytv import no_root_observer as observer
PROCESS_TMP='/private/tmp' if Path('/private/tmp').exists() else tempfile.gettempdir()


class Harness:
    def __init__(self, root, runtime=None, source=None, operation='a'*32, action='install'):
        self.root=Path(root).resolve();self.runtime=runtime or shutil.which('node')
        self.root.chmod(0o755)
        self.source=source or observer.PROGRAM
        self.sender=self.root/'sender'
        self.sender.write_text('''#!/usr/bin/env python3
import json,sys,select,os,time
from pathlib import Path
root=Path(ROOT)
with (root/'requests').open('a') as f:f.write(json.loads(sys.argv[-1])['id']+'\\n')
(root/'sender-pid').write_text(str(os.getpid()))
(root/'observer-pid').write_text(str(os.getppid()))
if select.select([sys.stdin],[],[],.08)[0]:sys.exit(12)
while (root/'hold').exists():time.sleep(.02)
raw=(root/'reply').read_bytes() if (root/'reply').exists() else json.dumps({'returnValue':True,'details':{'state':'removed' if sys.argv[-2].endswith('/remove') else 'installed'}}).encode()
for b in raw:
 sys.stdout.buffer.write(bytes([b]));sys.stdout.buffer.flush()
sys.stdin.read()
'''.replace('ROOT',repr(str(self.root))))
        self.sender.chmod(0o700)
        (self.root/'public').mkdir(exist_ok=True)
        self.config=dict(root=str(self.root/'private'),public_root=str(self.root/'public'),sender=str(self.sender),timeout=1500)
        self.plan=observer.make_plan(operation,'b'*32,action,{'helper.ipk':b'helper','launcher.ipk':b'home'},
                                     dict(zip(observer.APPS,['1','2'])),public_root=self.config['public_root'])
        self.plan['source_sha256']=hashlib.sha256(self.source.encode()).hexdigest()

    def command(self, command, slot=None):
        return dict(self.config,command=command,slot=slot,plan=self.plan,source=self.source)

    def process(self, command, slot=None, prefix='', **extra):
        return subprocess.Popen([self.runtime,'-e',prefix+self.source,json.dumps(dict(self.command(command,slot),**extra))],stdout=subprocess.PIPE,stderr=subprocess.PIPE)

    def call(self,command,slot=None,ok=True,prefix='',**extra):
        child=self.process(command,slot,prefix,**extra)
        stdout,stderr=child.communicate(timeout=8)
        if ok and child.returncode:raise AssertionError(stderr.decode())
        if not ok:
            if not child.returncode:raise AssertionError('unsafe command succeeded: '+command)
            return stderr.decode()
        return json.loads(stdout)

    def prepare(self):
        self.call('prepare')
        if self.plan['action']=='install':
            stage=self.root/'public'/('cytv-'+self.plan['operation'])
            for name,data in [('helper.ipk',b'helper'),('launcher.ipk',b'home')]:
                target=stage/name;target.write_bytes(data);target.chmod(0o644)

    @property
    def directory(self):return self.root/'private/operations'/self.plan['operation']

    def wait(self,index=0,reason=None):
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            result=self.call('status')
            slot=result['slots'][index]
            if (slot['terminal']!='none' or slot['reason']) and (reason is None or slot['reason']==reason):return slot
            time.sleep(.03)
        raise AssertionError('observer did not end')

    def finish(self):
        if self.plan['action']=='remove':self.complete_config('restore')
        for index in range(2):
            self.call('start',index)
            assert self.wait(index)['terminal']=='success'
            self.call('readback',index)
        if self.plan['action']=='install':
            for step in ('files','eim','launch'):self.complete_config(step)
        self.call('configured')

    def complete_config(self,step):
        result=self.call('config-claim',step)
        self.call('config-result',step,proof={'nonce':result['nonce'],'result':'verified'})


@unittest.skipIf(os.name=='nt','The TV observer uses POSIX process and filesystem primitives')
class ObserverProcesses(unittest.TestCase):
    def test_sdk_staging_permissions_with_private_sticky_storage(self):
        with tempfile.TemporaryDirectory(dir=PROCESS_TMP) as root:
            h=Harness(root)
            developer=h.root/'developer';developer.mkdir(mode=0o775);developer.chmod(0o775)
            public=developer/'temp';public.mkdir(mode=0o777);public.chmod(0o777)
            # Model the fixed root-owned SDK containers; real Node still runs
            # as this unprivileged host user and performs every storage operation.
            prefix="var fs=require('fs'),original=fs.lstatSync;fs.lstatSync=function(p){var s=original(p);if(p===DEV||p===PUB)s.uid=0;return s;};".replace('DEV',json.dumps(str(developer))).replace('PUB',json.dumps(str(public)))
            h.source=prefix+observer.PROGRAM.replace("'/media/developer'",json.dumps(str(developer)))
            h.config['public_root']=str(public)
            h.plan=observer.make_plan('a'*32,'b'*32,'install',{'helper.ipk':b'helper','launcher.ipk':b'home'},dict(zip(observer.APPS,['1','2'])),public_root=str(public))
            h.plan['source_sha256']=hashlib.sha256(h.source.encode()).hexdigest()
            runtimes=[shutil.which('node')]+[os.environ[name] for name in ('NODE010','NODE01025','NODE012') if os.environ.get(name)]
            for runtime in runtimes:
                with self.subTest(runtime=runtime):
                    h.runtime=runtime
                    for mode in (0o775,0o777):
                        developer.chmod(mode)
                        h.call('storage-check')
            self.assertEqual(list(public.iterdir()),[])
            self.assertFalse((h.root/'requests').exists())
            h.call('prepare')
            self.assertEqual(h.call('status')['reservation'],'active')
            self.assertEqual((h.root/'private').stat().st_mode&0o777,0o700)
            public.chmod(0o775)  # Only the exact known SDK layout is admitted.
            h.call('storage-check',ok=False)

    def test_pinned_stream_uploads_on_every_configured_runtime(self):
        runtimes=[shutil.which('node')]+[os.environ[name] for name in ('NODE010','NODE01025','NODE012') if os.environ.get(name)]
        for runtime in runtimes:
            for substitute in (False,True,'pre-pin','pre-pin-safe','unsafe-pinned'):
                with self.subTest(runtime=runtime,substitute=substitute),tempfile.TemporaryDirectory(dir=PROCESS_TMP) as root:
                    h=Harness(root,runtime=runtime)
                    hashes={'ssap-key.json':hashlib.sha256(b'private-original').hexdigest(),'apps.json':hashlib.sha256(b'[]').hexdigest()}
                    h.plan['configuration_sha256']=hashlib.sha256(observer.canonical(hashes).encode()).hexdigest()
                    h.call('prepare')
                    for index,raw in enumerate((b'helper',b'home')):
                        request=h.command('upload-artifact',index)
                        result=subprocess.run([runtime,'-e',h.source,json.dumps(request)],input=raw,capture_output=True,timeout=5)
                        self.assertEqual(result.returncode,0,result.stderr.decode())
                        h.call('start',index)
                        terminal=h.directory/('terminal-'+str(index)+'.json');deadline=time.monotonic()+5
                        while (not terminal.exists() or terminal.stat().st_nlink!=1) and time.monotonic()<deadline:time.sleep(.01)
                        self.assertEqual(h.wait(index)['terminal'],'success');h.call('readback',index)
                    claim=h.call('config-claim','files')
                    state=h.root/'state';state.mkdir(mode=0o700);foreign=h.root/'foreign';foreign.mkdir()
                    request=dict(h.command('upload-configuration'),proof={'nonce':claim['nonce'],'directory':str(state),'name':'ssap-key.json','hashes':hashes})
                    prefix=''
                    if substitute is True:
                        # Runs AFTER chdir/identity validation, at the actual
                        # exclusive temp-file open immediately before bytes.
                        prefix="var fs=require('fs'),original=fs.openSync,swapped=false;fs.openSync=function(name){if(!swapped&&String(name).indexOf('.cytv-')===0){swapped=true;fs.renameSync(STATE,STATE+'-old');fs.symlinkSync(FOREIGN,STATE);}return original.apply(fs,arguments);};".replace('STATE',json.dumps(str(state))).replace('FOREIGN',json.dumps(str(foreign)))
                    elif substitute in ('pre-pin','pre-pin-safe','unsafe-pinned'):
                        prefix=r'''
var fs=require('fs'),lstat=fs.lstatSync,chdir=process.chdir,write=fs.writeSync,swapped=false,leafReads=0;
function replace(){if(swapped)return;swapped=true;fs.renameSync(STATE,STATE+'-old');fs.mkdirSync(STATE);fs.chmodSync(STATE,CASE==='pre-pin-safe'?448:511);}
fs.lstatSync=function(name){if(name===STATE&&++leafReads===2&&CASE.indexOf('pre-pin')===0)replace();return lstat.apply(fs,arguments);};
process.chdir=function(name){
 if(name===STATE&&CASE.indexOf('pre-pin')===0)replace();
 var result=chdir.apply(process,arguments);
 if(name===STATE&&CASE==='unsafe-pinned')fs.chmodSync('.',511);
 return result;
};
fs.writeSync=function(fd,b){if(Buffer.isBuffer(b)&&b.toString().indexOf('private-original')>=0)process.stderr.write('PRIVATE_WRITE_REACHED\n');return write.apply(fs,arguments);};
'''.replace('STATE',json.dumps(str(state))).replace('CASE',json.dumps(substitute))
                    result=subprocess.run([runtime,'-e',prefix+h.source,json.dumps(request)],input=b'private-original',capture_output=True,timeout=5)
                    self.assertEqual(list(foreign.iterdir()),[])
                    if substitute:
                        self.assertNotEqual(result.returncode,0)
                        if substitute in ('pre-pin','pre-pin-safe','unsafe-pinned'):
                            self.assertNotIn(b'PRIVATE_WRITE_REACHED',result.stderr,'Private bytes reached an unvalidated destination before cleanup')
                            self.assertEqual(list(state.iterdir()),[])
                        if substitute!='unsafe-pinned':self.assertEqual(list(state.with_name('state-old').iterdir()),[])
                        self.assertEqual(h.call('status')['configuration']['files'],'unknown')
                    else:
                        self.assertEqual(result.returncode,0,result.stderr.decode())
                        self.assertEqual((state/'ssap-key.json').read_bytes(),b'private-original')
                        self.assertEqual((state/'ssap-key.json').stat().st_mode&0o777,0o640)

    def test_key_mode_repair_only_restricts_a_checked_owned_single_link_inode(self):
        runtimes=[shutil.which('node')]+[os.environ[name] for name in ('NODE010','NODE01025','NODE012') if os.environ.get(name)]
        for runtime in runtimes:
            with self.subTest(runtime=runtime),tempfile.TemporaryDirectory(dir=PROCESS_TMP) as root:
                state=Path(root).resolve()/'state';state.mkdir(mode=0o775)
                key=state/'ssap-key.json';key.write_bytes(b'retained-key');key.chmod(0o775)
                apps=state/'apps.json';apps.write_bytes(b'[]');apps.chmod(0o775)
                latch=state/'blocked';latch.write_bytes(b'keep-stop');latch.chmod(0o775)
                before=key.stat()
                def run(repair=False):
                    args=['repair-key-mode'] if repair else []
                    return subprocess.run([runtime,'-e',observer.STATE_CHECK]+args+[str(state)],capture_output=True,timeout=5)
                self.assertNotEqual(run().returncode,0,'Read-only status must not silently repair permissions')
                result=run(True)
                self.assertEqual(result.returncode,0,result.stderr.decode())
                after=key.stat()
                self.assertEqual(after.st_mode&0o777,0o640)
                self.assertEqual((after.st_ino,after.st_uid,after.st_gid),(before.st_ino,before.st_uid,before.st_gid))
                self.assertEqual(key.read_bytes(),b'retained-key')
                self.assertEqual(latch.read_bytes(),b'keep-stop')
                self.assertEqual(latch.stat().st_mode&0o777,0o775)
                for kind in ('world-write','hardlink','symlink','unsafe-apps'):
                    with self.subTest(kind=kind):
                        key.unlink();key.write_bytes(b'retained-key');key.chmod(0o775)
                        other=state/'other';other.unlink(missing_ok=True)
                        if kind=='world-write':key.chmod(0o777)
                        if kind=='hardlink':os.link(key,other)
                        if kind=='symlink':key.rename(other);key.symlink_to(other)
                        if kind=='unsafe-apps':apps.chmod(0o777)
                        self.assertNotEqual(run(True).returncode,0)
                        self.assertEqual(key.stat().st_mode&0o777,0o777 if kind=='world-write' else 0o775)
                        self.assertEqual(key.read_bytes(),b'retained-key')

    def test_target_readback_scripts_run_on_every_configured_runtime(self):
        runtimes=[shutil.which('node')]+[os.environ[name] for name in ('NODE010','NODE01025','NODE012') if os.environ.get(name)]
        for runtime in runtimes:
            with self.subTest(runtime=runtime),tempfile.TemporaryDirectory(dir=PROCESS_TMP) as root:
                root=Path(root).resolve();state=root/'state';state.mkdir(mode=0o700)
                key=state/'ssap-key.json';key.write_text('original');key.chmod(0o600)
                package=root/'packages'/observer.APPS[0];package.mkdir(parents=True)
                for script,argument,expected in (
                    (observer.FILE_CHECK,json.dumps({str(key):hashlib.sha256(b'original').hexdigest()}),b'CYTV_ORIGINAL_FILES_VERIFIED'),
                    (observer.STATE_CHECK,str(state),b'CYTV_CONFIGURATION_PRIVATE'),
                    (observer.EMPTY_PACKAGE,json.dumps({'base':str(root),'app':observer.APPS[0],'cleanup':False}),b'CYTV_EMPTY_PACKAGE')):
                    result=subprocess.run([runtime,'-e',script,argument],capture_output=True,timeout=5)
                    self.assertEqual(result.returncode,0,result.stderr.decode());self.assertEqual(result.stdout,expected)
                self.assertTrue(package.exists())

    def test_conflicting_terminal_and_wrong_package_bindings_are_refused(self):
        with tempfile.TemporaryDirectory(dir=PROCESS_TMP) as root:
            h=Harness(root);h.prepare();h.call('start',0);self.assertEqual(h.wait()['terminal'],'success')
            terminal=h.directory/'terminal-0.json';value=json.loads(terminal.read_text());value['reply']['errorCode']=24
            terminal.write_text(json.dumps(value));terminal.chmod(0o600)
            h.call('status',ok=False)
            h.plan['slots'][0]['app']=observer.APPS[1]
            h.call('start',0,ok=False)
            self.assertEqual((h.root/'requests').read_text().splitlines(),[observer.APPS[0]])

    def test_unsupported_hardlink_storage_refuses_before_requests(self):
        with tempfile.TemporaryDirectory(dir=PROCESS_TMP) as root:
            source="require('fs').linkSync=function(){throw Error('unsupported link');};"+observer.PROGRAM
            h=Harness(root,source=source)
            h.call('prepare',ok=False)
            self.assertFalse((h.root/'requests').exists())

    def test_unexpected_active_children_are_retained_and_reported(self):
        with tempfile.TemporaryDirectory(dir=PROCESS_TMP) as root:
            h=Harness(root);h.prepare();h.finish()
            foreign=h.root/'private/active/foreign';foreign.write_text('keep');foreign.chmod(0o600)
            h.call('release',ok=False)
            self.assertEqual(foreign.read_text(),'keep')

    def test_delayed_original_worker_loses_permanent_claim_to_retry(self):
        with tempfile.TemporaryDirectory(dir=PROCESS_TMP) as root:
            pause=Path(root)/'paused';go=Path(root)/'continue'
            prefix="var fs=require('fs'),open=fs.openSync;fs.openSync=function(p,flags){if(String(p).indexOf('/claim-0.json')>=0&&(flags&require('constants').O_CREAT)&&!fs.existsSync(PAUSE)){fs.writeFileSync(PAUSE,String(process.pid));while(!fs.existsSync(GO)){};}return open.apply(fs,arguments);};".replace('PAUSE',json.dumps(str(pause))).replace('GO',json.dumps(str(go)))
            h=Harness(root,source=prefix+observer.PROGRAM);h.config['timeout']=2000;h.prepare();h.call('start',0)
            try:
                deadline=time.monotonic()+5
                while not pause.exists() and time.monotonic()<deadline:time.sleep(.02)
                self.assertTrue(pause.exists());h.call('start',0)
                self.assertEqual(h.wait()['terminal'],'success')
                claim=(h.directory/'claim-0.json').read_bytes();go.touch();time.sleep(.1)
                self.assertEqual((h.directory/'claim-0.json').read_bytes(),claim)
                self.assertEqual((h.root/'requests').read_text().splitlines(),[observer.APPS[0]])
            finally:
                go.touch()

    def test_publication_without_ack_attaches_same_inode_and_partial_writes_complete(self):
        with tempfile.TemporaryDirectory(dir=PROCESS_TMP) as root:
            partial="var fs=require('fs'),write=fs.writeSync;fs.writeSync=function(){arguments[3]=Math.min(arguments[3],7);return write.apply(fs,arguments);};"
            h=Harness(root,source=partial+observer.PROGRAM)
            prefix="var fs=require('fs'),rename=fs.renameSync;fs.renameSync=function(a,b){var result=rename.apply(fs,arguments);if(b.slice(-7)==='/active')process.kill(process.pid,'SIGKILL');return result;};"
            child=h.process('prepare',prefix=prefix);child.communicate(timeout=5)
            self.assertNotEqual(child.returncode,0)
            inode=(h.root/'private/active').stat().st_ino
            h.prepare()
            self.assertEqual((h.root/'private/active').stat().st_ino,inode)
            h.call('start',0);self.assertEqual(h.wait()['terminal'],'success')
            self.assertEqual(json.loads((h.directory/'claim-0.json').read_text())['slot'],0)
            self.assertFalse((h.directory/'reservation').exists())

    def test_sender_ignoring_eof_and_term_is_bounded_after_terminal_persistence(self):
        with tempfile.TemporaryDirectory(dir=PROCESS_TMP) as root:
            h=Harness(root);h.config['timeout']=3000;h.prepare()
            h.sender.write_text('#!/usr/bin/env python3\nimport os,signal,time\nfrom pathlib import Path\n'
                'signal.signal(signal.SIGTERM,lambda *_:None)\nPath('+repr(str(h.root/'sender-pid'))+').write_text(str(os.getpid()))\n'
                'print(\'{"details":{"state":"installed"}}\',flush=True)\nwhile True:time.sleep(.05)\n')
            h.call('start',0)
            # The sender starts only after the permanent claim is fully written
            # and synced. Do not poll strict evidence reads during its creation.
            sender_pid=h.root/'sender-pid';deadline=time.monotonic()+5
            while not sender_pid.exists() and time.monotonic()<deadline:time.sleep(.01)
            self.assertTrue(sender_pid.exists(),'sender did not start after claim persistence')
            self.assertEqual(h.wait()['terminal'],'success')
            pid=int((h.root/'sender-pid').read_text());alive=True;deadline=time.monotonic()+2.5
            try:
                while time.monotonic()<deadline:
                    try:os.kill(pid,0)
                    except ProcessLookupError:alive=False;break
                    time.sleep(.05)
                self.assertFalse(alive,'bounded observer left its own sender alive')
            finally:
                if alive:os.kill(pid,signal.SIGKILL)

    def test_paused_initializer_cannot_replace_new_nonempty_reservation(self):
        with tempfile.TemporaryDirectory(dir=PROCESS_TMP) as root:
            old=Harness(root);new=Harness(root,operation='c'*32)
            pause=old.root/'paused';go=old.root/'continue'
            prefix="var fs=require('fs'),rename=fs.renameSync;fs.renameSync=function(a,b){if(a.slice(-12)==='/reservation'){fs.writeFileSync(PAUSE,'ready');while(!fs.existsSync(GO)){};}return rename.apply(fs,arguments);};".replace('PAUSE',json.dumps(str(pause))).replace('GO',json.dumps(str(go)))
            process=old.process('prepare',prefix=prefix)
            try:
                deadline=time.monotonic()+5
                while not pause.exists() and time.monotonic()<deadline:time.sleep(.02)
                self.assertTrue(pause.exists());new.prepare();go.touch()
                stdout,stderr=process.communicate(timeout=5)
                self.assertNotEqual(process.returncode,0)
                self.assertEqual(new.call('status')['reservation'],'active')
                old.call('start',0,ok=False)
                self.assertFalse((old.root/'requests').exists())
            finally:
                if process.poll() is None:process.kill();process.communicate()

    def test_killed_bootstrap_and_worker_loss_never_duplicate_original_request(self):
        with tempfile.TemporaryDirectory(dir=PROCESS_TMP) as root:
            h=Harness(root);h.prepare()
            prefix="var cp=require('child_process'),spawn=cp.spawn;cp.spawn=function(){var child=spawn.apply(cp,arguments);process.kill(process.pid,'SIGKILL');return child;};"
            boot=h.process('start',0,prefix=prefix);boot.communicate(timeout=5)
            self.assertNotEqual(boot.returncode,0)
            self.assertEqual(h.wait()['terminal'],'success')
            h.call('start',0)
            self.assertEqual((h.root/'requests').read_text().splitlines(),[observer.APPS[0]])
        with tempfile.TemporaryDirectory(dir=PROCESS_TMP) as root:
            h=Harness(root);h.prepare();(h.root/'hold').touch();h.call('start',0)
            deadline=time.monotonic()+4
            while not (h.root/'observer-pid').exists() and time.monotonic()<deadline:time.sleep(.02)
            os.kill(int((h.root/'observer-pid').read_text()),signal.SIGKILL)
            (h.root/'hold').unlink();h.call('start',0)
            self.assertEqual(h.call('status')['slots'][0]['terminal'],'none')
            h.call('start',1,ok=False);h.call('release',ok=False)
            self.assertEqual((h.root/'requests').read_text().splitlines(),[observer.APPS[0]])

    def test_terminal_directory_sync_failure_and_readback_sync_failure_block_next_slot(self):
        for after_publication in (False,True):
            with self.subTest(after_publication=after_publication),tempfile.TemporaryDirectory(dir=PROCESS_TMP) as root:
                prefix="var fs=require('fs'),link=fs.linkSync,sync=fs.fsyncSync,seen=false;fs.linkSync=function(a,b){var result=link.apply(fs,arguments);if(b.indexOf('/terminal-0.json')>=0)seen=true;return result;};fs.fsyncSync=function(){if(seen){seen=false;throw Error('directory sync failed');}return sync.apply(fs,arguments);};" if after_publication else ''
                h=Harness(root,source=prefix+observer.PROGRAM);h.prepare();h.call('start',0)
                # The terminal link is published before the failed directory sync
                # is recorded; wait for that evidence rather than racing its writer.
                slot=h.wait(reason='terminal-persistence-unverified' if after_publication else None)
                self.assertEqual(slot['terminal'],'success')
                if after_publication:
                    self.assertEqual(slot['reason'],'terminal-persistence-unverified')
                    h.call('readback',0,ok=False)
                else:
                    h.call('readback',0,ok=False,prefix="require('fs').fsyncSync=function(){throw Error('disk full');};")
                h.call('start',1,ok=False);h.call('release',ok=False)
                self.assertEqual((h.root/'requests').read_text().splitlines(),[observer.APPS[0]])

    def test_status_is_read_only_and_exact_runtimes_preserve_permanent_removal_seals(self):
        runtimes=[shutil.which('node')]+[os.environ[name] for name in ('NODE010','NODE01025','NODE012') if os.environ.get(name)]
        for runtime in runtimes:
            with self.subTest(runtime=runtime),tempfile.TemporaryDirectory(dir=PROCESS_TMP) as root:
                h=Harness(root,runtime=runtime,action='remove');h.prepare();h.complete_config('restore')
                for index in (0,1):h.call('seal',index);h.call('readback',index)
                h.call('configured')
                readonly="var fs=require('fs');['fsyncSync','writeSync','writeFileSync','mkdirSync','renameSync','unlinkSync','linkSync','rmdirSync','chmodSync'].forEach(function(k){fs[k]=function(){throw Error('status mutation');};});"
                self.assertEqual(h.call('status',prefix=readonly)['slots'][0]['submission'],'sealed')
                h.call('release');h.call('start',0,ok=False)
                new=Harness(root,runtime=runtime,operation='c'*32,action='remove');new.call('prepare')
                h.call('release')
                self.assertEqual(new.call('status')['reservation'],'active')
                self.assertFalse((h.root/'requests').exists())

    def test_private_public_parent_is_refused_without_chmod(self):
        with tempfile.TemporaryDirectory(dir=PROCESS_TMP) as root:
            h=Harness(root);(h.root/'public').chmod(0o700)
            h.call('prepare',ok=False)
            self.assertEqual((h.root/'public').stat().st_mode & 0o777,0o700)
            self.assertFalse((h.root/'requests').exists())

    def test_replaced_public_stage_is_not_adopted_or_retired(self):
        with tempfile.TemporaryDirectory(dir=PROCESS_TMP) as root:
            h=Harness(root);h.prepare()
            stage=h.root/'public'/('cytv-'+h.plan['operation'])
            stage.rename(stage.with_suffix('.old'));stage.mkdir(mode=0o755)
            (stage/'helper.ipk').write_bytes(b'helper');(stage/'launcher.ipk').write_bytes(b'home')
            stage.chmod(0o755)
            for archive in stage.iterdir():archive.chmod(0o644)
            h.call('worker',0,ok=False)
            self.assertFalse((h.root/'requests').exists())
            h.call('retire',ok=False)

    def test_failure_unknown_parser_bounds_and_no_terminal_replay(self):
        cases=[(b'{"returnValue":false,"errorCode":24}{"details":{"state":"installed"}}','failure',None),
               (b'[]','none','malformed-reply'),(b'{broken}','none','malformed-reply'),
               (b'{"details":{"state":"removed"}}','none','observation-timeout'),
               (b'{"padding":"'+b'x'*66000+b'"}','none','oversized-reply'),
               (b'{"returnValue":true,"details":{"state":"installing"}}','none','observation-timeout'),
               (b'{\n"note":"split \xe2\x82\xac", "details":{"state":"installed"}\n}','success',None)]
        for raw,terminal,reason in cases:
            with self.subTest(terminal=terminal,reason=reason),tempfile.TemporaryDirectory(dir=PROCESS_TMP) as root:
                h=Harness(root);h.prepare();(h.root/'reply').write_bytes(raw)
                h.call('start',0); result=h.wait()
                self.assertEqual(result['terminal'],terminal);self.assertEqual(result['reason'],reason)
                h.call('start',0)
                self.assertEqual((h.root/'requests').read_text().splitlines(),[observer.APPS[0]])
                h.call('start',1,ok=False)
                h.call('release',ok=False)

    def test_claim_and_terminal_durability_failures_never_replay(self):
        for boundary in ('claim','terminal'):
            with self.subTest(boundary=boundary),tempfile.TemporaryDirectory(dir=PROCESS_TMP) as root:
                prelude=("var fs=require('fs'),original=fs.fsyncSync,opened={},open=fs.openSync;"
                         "fs.openSync=function(p){var fd=open.apply(fs,arguments);opened[fd]=p;return fd;};"
                         "fs.fsyncSync=function(fd){if(String(opened[fd]).indexOf('/claim-')>=0)throw Error('disk full');return original.apply(fs,arguments);};") if boundary=='claim' else (
                         "var fs=require('fs'),link=fs.linkSync;fs.linkSync=function(a,b){if(b.indexOf('/terminal-')>=0)throw Error('disk full');return link.apply(fs,arguments);};")
                h=Harness(root,source=prelude+observer.PROGRAM);h.prepare();h.call('start',0)
                deadline=time.monotonic()+3
                while not (h.directory/'claim-0.json').exists() and time.monotonic()<deadline:time.sleep(.02)
                if boundary=='terminal':h.wait()
                before=(h.root/'requests').read_text() if (h.root/'requests').exists() else ''
                h.call('start',0);time.sleep(.15)
                after=(h.root/'requests').read_text() if (h.root/'requests').exists() else ''
                self.assertEqual(after,before)
                self.assertEqual(bool(after),boundary=='terminal')
                self.assertEqual(h.call('status')['slots'][0]['terminal'],'none')
                h.call('release',ok=False)

    def test_unsafe_sources_artifacts_and_partial_claims_fail_closed(self):
        for kind in ('source','symlink','hardlink','mode','partial-claim'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory(dir=PROCESS_TMP) as root:
                h=Harness(root);h.prepare()
                artifact=h.root/'public'/('cytv-'+h.plan['operation'])/'helper.ipk'
                if kind=='source':(h.directory/'observer.js').write_text('changed')
                if kind=='symlink':artifact.unlink();artifact.symlink_to(h.root/'sender')
                if kind=='hardlink':os.link(artifact,artifact.with_suffix('.link'))
                if kind=='mode':artifact.chmod(0o666)
                if kind=='partial-claim':(h.directory/'claim-0.json').write_text('{')
                if kind=='source':h.call('start',0,ok=False)
                else:h.call('start',0)
                time.sleep(.2)
                self.assertFalse((h.root/'requests').exists())
                h.call('release',ok=False)

    def test_distinct_operations_exclude_and_stale_releaser_cannot_delete_new_owner(self):
        with tempfile.TemporaryDirectory(dir=PROCESS_TMP) as root:
            old=Harness(root);old.prepare();old.finish()
            new=Harness(root,operation='c'*32)
            new.call('prepare',ok=False)
            pause=old.root/'paused';go=old.root/'continue'
            prefix="var fs=require('fs'),unlink=fs.unlinkSync;fs.unlinkSync=function(p){if(p.indexOf('/active/owner-')>=0){fs.writeFileSync(PAUSE,'ready');while(!fs.existsSync(GO)){};}return unlink.apply(fs,arguments);};".replace('PAUSE',json.dumps(str(pause))).replace('GO',json.dumps(str(go)))
            stale=old.process('release',prefix=prefix)
            deadline=time.monotonic()+5
            while not pause.exists() and time.monotonic()<deadline:time.sleep(.02)
            self.assertTrue(pause.exists())
            old.call('release')
            new.call('prepare')
            go.write_text('continue')
            stdout,stderr=stale.communicate(timeout=5)
            # ENOENT during exact-old unlink is safe but must be a successful retry.
            self.assertEqual(stale.returncode,0,stderr.decode())
            self.assertEqual(list((old.root/'private/active').iterdir()),[old.root/'private/active'/('owner-'+'c'*32+'.json')])
            old.call('start',0,ok=False)
            old.call('release')
            new.call('status')

    def test_detached_original_stream_is_claimed_once_on_every_runtime(self):
        from cytv import no_root_observer as observer
        runtimes = [shutil.which('node')]
        runtimes += [os.environ[name] for name in ('NODE010', 'NODE01025', 'NODE012') if os.environ.get(name)]
        for runtime in runtimes:
            with self.subTest(runtime=runtime), tempfile.TemporaryDirectory(dir=PROCESS_TMP) as temporary:
                root = Path(temporary).resolve()
                root.chmod(0o755)
                sender = root / 'sender'
                sender.write_text('#!/usr/bin/env python3\nimport os,sys,time,select\n'
                                  'with open('+repr(str(root / 'requests'))+',"a") as f: f.write("request\\n")\n'
                                  'if select.select([sys.stdin],[],[],0.2)[0]: sys.exit(12)\n'
                                  'print(\'{"returnValue":true,"details":{"state":"installed"}}\',flush=True)\n'
                                  'sys.stdin.read()\n')
                sender.chmod(0o700)
                config = dict(root=str(root / 'private'), public_root=str(root / 'public'),
                              sender=str(sender), timeout=2000)
                (root / 'public').mkdir(mode=0o755)
                plan = observer.make_plan('a'*32, 'b'*32, 'install', {'helper.ipk': b'helper', 'launcher.ipk': b'home'},
                                          {'com.local.nativehome': '1', 'com.gathin.tvhome': '2'},
                                          public_root=config['public_root'])
                def call(action, slot=None):
                    request = dict(config, command=action, plan=plan, source=observer.PROGRAM, slot=slot)
                    result = subprocess.run([runtime, '-e', observer.PROGRAM, json.dumps(request)],
                                            capture_output=True, timeout=8)
                    self.assertEqual(result.returncode, 0, result.stderr.decode())
                    return json.loads(result.stdout)
                prepared = call('prepare')
                self.assertEqual(prepared['operation'], 'a'*32)
                stage = root / 'public' / ('cytv-'+'a'*32)
                (stage / 'helper.ipk').write_bytes(b'helper')
                (stage / 'launcher.ipk').write_bytes(b'home')
                for path in stage.iterdir(): path.chmod(0o644)
                call('start', 0)
                call('start', 0)
                deadline = time.monotonic()+5
                while time.monotonic() < deadline:
                    status = call('status')
                    if status['slots'][0].get('terminal') == 'success': break
                    time.sleep(.03)
                self.assertEqual(status['slots'][0]['terminal'], 'success')
                self.assertEqual((root / 'requests').read_text(), 'request\n')
                self.assertEqual(status['slots'][1]['submission'], 'prepared')
                call('start', 0)
                self.assertEqual((root / 'requests').read_text(), 'request\n')


if __name__ == '__main__':
    unittest.main()
