"""Canonical storage contract against real host inodes (no TV operations)."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


@unittest.skipIf(os.name == 'nt', 'TV storage fixtures require POSIX ownership, modes and inode semantics')
class StorageContractTests(unittest.TestCase):
    def run_js(self, body):
        runtimes = ['node'] + [os.environ[k] for k in ('NODE010', 'NODE01025', 'NODE012') if os.environ.get(k)]
        for runtime in runtimes:
            with self.subTest(runtime=runtime), tempfile.TemporaryDirectory() as tmp:
                source = "var assert=require('assert'),fs=require('fs'),p=require(" + repr(str(ROOT/'native/app/state-permissions')) + "),d=" + repr(str(Path(tmp).resolve())) + ";\n"
                result = subprocess.run([runtime, '-e', source + body], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_runtime_consumes_installer_apps_without_repairing_them(self):
        # A runtime chmod of installer configuration must fail this test.
        self.run_js("""
fs.writeFileSync(d+'/apps.json','[]');fs.chmodSync(d+'/apps.json',509);
fs.writeFileSync(d+'/ssap-key.json','{"key":"pairing"}');fs.chmodSync(d+'/ssap-key.json',416);
fs.writeFileSync(d+'/blocked','emergency');fs.writeFileSync(d+'/watchdog','watchdog');
var before=fs.statSync(d+'/apps.json'),chmod=fs.fchmodSync,touched=0;
fs.fchmodSync=function(fd,mode){if(fs.fstatSync(fd).ino===before.ino){touched++;throw Error('apps mutation');}return chmod.apply(fs,arguments);};
assert.strictEqual(p(d,null,true),true);assert.strictEqual(touched,0);
assert.strictEqual(fs.statSync(d+'/apps.json').mode&4095,509);
assert.strictEqual(fs.readFileSync(d+'/blocked','utf8'),'emergency');
assert.strictEqual(fs.readFileSync(d+'/watchdog','utf8'),'watchdog');
p.inspectConfiguration(d,{});
""")

    def test_fixed_record_writer_preserves_latches_and_refuses_unsafe_destinations(self):
        self.run_js("""
fs.writeFileSync(d+'/blocked','emergency');
p.atomicRecord(d,'home-preference','{"enabled":false}');
assert.strictEqual(fs.readFileSync(d+'/home-control.json','utf8'),'{"enabled":false}');
assert.strictEqual(fs.statSync(d+'/home-control.json').mode&4095,432);
assert.throws(function(){p.atomicRecord(d,'blocked','replace');});
fs.symlinkSync(d+'/blocked',d+'/control.json');
assert.throws(function(){p.requestStop(d);});
assert.strictEqual(fs.readFileSync(d+'/blocked','utf8'),'emergency');
fs.unlinkSync(d+'/control.json');p.requestStop(d);
assert.strictEqual(fs.readFileSync(d+'/blocked','utf8'),'emergency');
assert.strictEqual(fs.readFileSync(d+'/control.json','utf8'),'{"cmd":"stop"}');
assert.strictEqual(fs.readdirSync(d).filter(function(n){return n.charAt(0)==='.';}).length,0);
""")

    def test_root_group_access_keeps_stop_safety_and_configuration_proof(self):
        # Membership-only admission breaks actual Root SSH before Root enable.
        # Host inode I/O stays real; metadata projects the packaged TV namespace.
        self.run_js("""
var role=0,owners={},gids={},open=fs.openSync,stat=fs.fstatSync;
process.getuid=function(){return role;};process.getgid=function(){return role;};process.getgroups=function(){return [role];};
['lstatSync','fstatSync','statSync'].forEach(function(name){var original=fs[name];fs[name]=function(){var s=original.apply(fs,arguments);s.uid=s.isDirectory()?5999:(owners[s.ino]===undefined?5999:owners[s.ino]);s.gid=gids[s.ino]===undefined?5000:gids[s.ino];return s;};});
fs.openSync=function(){var fd=open.apply(fs,arguments);if(arguments[1]&require('constants').O_CREAT){owners[stat(fd).ino]=role;gids[stat(fd).ino]=role;}return fd;};
fs.fchownSync=function(fd,uid,gid){owners[stat(fd).ino]=uid;gids[stat(fd).ino]=gid;};
fs.chmodSync(d,504);fs.writeFileSync(d+'/blocked','emergency');fs.chmodSync(d+'/blocked',436);
fs.writeFileSync(d+'/watchdog','retained');
role=21001;assert.throws(function(){p.requestStop(d,{role:'root',uid:0,groups:[5000]});});
assert.strictEqual(fs.readFileSync(d+'/blocked','utf8'),'emergency');assert.strictEqual(fs.existsSync(d+'/control.json'),false);
role=0;
var control=d+'/control.json',outside=d+'/outside';fs.writeFileSync(outside,'private');
fs.symlinkSync(outside,control);assert.throws(function(){p.requestStop(d);});fs.unlinkSync(control);
fs.linkSync(outside,control);assert.throws(function(){p.requestStop(d);});fs.unlinkSync(control);
fs.mkdirSync(control);assert.throws(function(){p.requestStop(d);});fs.rmdirSync(control);
assert.throws(function(){p.requestStop(d+'/../'+d.split('/').pop());});
assert.strictEqual(fs.readFileSync(outside,'utf8'),'private');assert.strictEqual(fs.readFileSync(d+'/blocked','utf8'),'emergency');
assert.strictEqual(p.requestStop(d),true);
assert.strictEqual(fs.readFileSync(control,'utf8'),'{"cmd":"stop"}');assert.strictEqual(fs.statSync(control).gid,5000);
var originalControl=fs.statSync(control),chown=fs.fchownSync;
fs.fchownSync=function(){var e=Error('denied');e.code='EPERM';throw e;};
assert.throws(function(){p.requestStop(d);});fs.fchownSync=chown;
assert.strictEqual(fs.statSync(control).ino,originalControl.ino);
assert.strictEqual(fs.readFileSync(control,'utf8'),'{"cmd":"stop"}');
assert.strictEqual(fs.readFileSync(d+'/blocked','utf8'),'emergency');assert.strictEqual(fs.readFileSync(d+'/watchdog','utf8'),'retained');
fs.writeFileSync(d+'/ssap-key.json','{"key":"retained"}');fs.chmodSync(d+'/ssap-key.json',416);
var key=d+'/ssap-key.json',before=fs.statSync(key);owners[before.ino]=21002;
assert.throws(function(){p.inspectConfiguration(d,{role:'root'});});
assert.throws(function(){p.prepareConfiguration(d,{role:'root',expectedHash:new Array(65).join('0')});});
assert.strictEqual(fs.statSync(key).ino,before.ino);assert.strictEqual(fs.readFileSync(key,'utf8'),'{"key":"retained"}');
var hash=require('crypto').createHash('sha256').update('{"key":"retained"}').digest('hex');
gids[before.ino]=98765;assert.throws(function(){p.prepareConfiguration(d,{expectedHash:hash});});gids[before.ino]=5000;
p.prepareConfiguration(d,{expectedHash:hash});assert.strictEqual(fs.statSync(key).uid,0);
assert.strictEqual(p.readConfiguration(d,'key'),'{"key":"retained"}');
p.atomicRecord(d,'pid','123');assert.strictEqual(fs.statSync(d+'/controller.pid').gid,5000);
assert.strictEqual(p(d),true);
assert.strictEqual(fs.readdirSync(d).filter(function(n){return n.charAt(0)==='.';}).length,0);
""")

    def test_configuration_inspection_is_readonly_and_validates_apps_before_key_repair(self):
        self.run_js("""
fs.writeFileSync(d+'/ssap-key.json','retained');fs.chmodSync(d+'/ssap-key.json',509);
fs.writeFileSync(d+'/apps.json','[]');fs.chmodSync(d+'/apps.json',511);
var before=fs.statSync(d+'/ssap-key.json');
assert.throws(function(){p.prepareConfiguration(d,{});});
assert.strictEqual(fs.statSync(d+'/ssap-key.json').mode&4095,509);
fs.chmodSync(d+'/apps.json',420);
assert.throws(function(){p.inspectConfiguration(d,{});});
assert.strictEqual(fs.statSync(d+'/ssap-key.json').mode&4095,509);
p.prepareConfiguration(d,{});
assert.strictEqual(fs.statSync(d+'/ssap-key.json').ino,before.ino);
assert.strictEqual(fs.statSync(d+'/ssap-key.json').mode&4095,416);
assert.strictEqual(fs.readFileSync(d+'/ssap-key.json','utf8'),'retained');
""")

    def test_installer_runtime_installer_role_cycle_uses_original_hash_only(self):
        self.run_js("""
var role=21001,owners={},open=fs.openSync,stat=fs.fstatSync,realUid=process.getuid();
process.getuid=function(){return role;};process.getgid=function(){return 5000;};process.getgroups=function(){return [5000];};
['lstatSync','fstatSync','statSync'].forEach(function(name){var original=fs[name];fs[name]=function(){var s=original.apply(fs,arguments);s.gid=5000;s.uid=s.isDirectory()?5999:(owners[s.ino]||21001);return s;};});
fs.openSync=function(){var fd=open.apply(fs,arguments);if(arguments[1]&require('constants').O_CREAT)owners[stat(fd).ino]=role;return fd;};
fs.fchownSync=function(){};
fs.chmodSync(d,509);
fs.writeFileSync(d+'/ssap-key.json','{"key":"retained"}');fs.chmodSync(d+'/ssap-key.json',509);
fs.writeFileSync(d+'/apps.json','[]');fs.chmodSync(d+'/apps.json',509);
fs.writeFileSync(d+'/blocked','emergency');fs.writeFileSync(d+'/watchdog','watchdog');
var hash=require('crypto').createHash('sha256').update('{"key":"retained"}').digest('hex');
p.prepareConfiguration(d,{});var installer=fs.statSync(d+'/ssap-key.json').ino;
// Model legacy runtime expansion of the key before controller B repairs privacy.
fs.chmodSync(d+'/ssap-key.json',509);role=21002;
assert.strictEqual(p(d,null,true),true);
assert.notStrictEqual(fs.statSync(d+'/ssap-key.json').ino,installer);
assert.strictEqual(p.readConfiguration(d,'apps'),'[]');
assert.strictEqual(fs.statSync(d+'/apps.json').mode&4095,509);
role=21001;assert.throws(function(){p.inspectConfiguration(d,{});});
assert.throws(function(){p.prepareConfiguration(d,{expectedHash:new Array(65).join('0')});});
p.prepareConfiguration(d,{expectedHash:hash});
assert.strictEqual(fs.statSync(d+'/ssap-key.json').uid,21001);
assert.strictEqual(fs.readFileSync(d+'/ssap-key.json','utf8'),'{"key":"retained"}');
assert.strictEqual(fs.readFileSync(d+'/blocked','utf8'),'emergency');
assert.strictEqual(fs.readFileSync(d+'/watchdog','utf8'),'watchdog');
""")

    def test_packaged_key_privacy_repair_requires_hash_and_caller_owned_staging(self):
        # Trusting a packaged reader does not authorize chmod of its inode.
        for caller in (0, 21001):
            with self.subTest(caller=caller):
                self.run_js("""
var role=CALLER,owners={},gids={},open=fs.openSync,stat=fs.fstatSync;
process.getuid=function(){return role;};process.getgid=function(){return role===0?0:5000;};process.getgroups=function(){return [role===0?0:5000];};
['lstatSync','fstatSync','statSync'].forEach(function(name){var original=fs[name];fs[name]=function(){var s=original.apply(fs,arguments);s.uid=s.isDirectory()?5999:(owners[s.ino]===undefined?5999:owners[s.ino]);s.gid=gids[s.ino]===undefined?5000:gids[s.ino];return s;};});
fs.openSync=function(){var fd=open.apply(fs,arguments);if(arguments[1]&require('constants').O_CREAT){owners[stat(fd).ino]=role;gids[stat(fd).ino]=role===0?0:5000;}return fd;};
fs.fchownSync=function(fd,uid,gid){owners[stat(fd).ino]=uid;gids[stat(fd).ino]=gid;};
fs.chmodSync(d,504);
var key=d+'/ssap-key.json',apps=d+'/apps.json',bytes='{"key":"retained"}';
fs.writeFileSync(key,bytes);fs.chmodSync(key,416);fs.writeFileSync(apps,'[]');fs.chmodSync(apps,420);
fs.writeFileSync(d+'/blocked','emergency');fs.writeFileSync(d+'/watchdog','retained');
var before=fs.statSync(key),hash=require('crypto').createHash('sha256').update(bytes).digest('hex');
p.inspectConfiguration(d,{});p.prepareConfiguration(d,{expectedHash:hash});
assert.strictEqual(fs.statSync(key).ino,before.ino);assert.strictEqual(fs.statSync(key).uid,5999);assert.strictEqual(fs.statSync(key).mode&4095,416);
[384,432].forEach(function(mode){fs.chmodSync(key,mode);p.inspectConfiguration(d,{});p.prepareConfiguration(d,{expectedHash:hash});assert.strictEqual(fs.statSync(key).ino,before.ino);assert.strictEqual(fs.statSync(key).uid,5999);assert.strictEqual(fs.statSync(key).mode&4095,mode);});
fs.chmodSync(key,509);
function retained(){var s=fs.statSync(key);assert.strictEqual(s.ino,before.ino);assert.strictEqual(s.uid,5999);assert.strictEqual(s.mode&4095,509);assert.strictEqual(fs.readFileSync(key,'utf8'),bytes);assert.strictEqual(fs.readdirSync(d).filter(function(n){return n.charAt(0)==='.';}).length,0);}
assert.throws(function(){p.inspectConfiguration(d,{expectedHash:hash});});retained();
assert.throws(function(){p.prepareConfiguration(d,{});});retained();
assert.throws(function(){p.prepareConfiguration(d,{expectedHash:new Array(65).join('0')});});retained();
gids[before.ino]=98765;assert.throws(function(){p.prepareConfiguration(d,{expectedHash:hash});});gids[before.ino]=5000;retained();
var appInode=fs.statSync(apps).ino;owners[appInode]=21002;
assert.throws(function(){p.prepareConfiguration(d,{expectedHash:hash});});retained();owners[appInode]=5999;
p.prepareConfiguration(d,{expectedHash:hash});
var after=fs.statSync(key);assert.notStrictEqual(after.ino,before.ino);assert.strictEqual(after.uid,role);assert.strictEqual(after.gid,5000);assert.strictEqual(after.mode&4095,416);
assert.strictEqual(fs.readFileSync(key,'utf8'),bytes);assert.strictEqual(fs.readFileSync(apps,'utf8'),'[]');assert.strictEqual(fs.statSync(apps).ino,appInode);
fs.chmodSync(key,509);p.prepareConfiguration(d,{});assert.strictEqual(fs.statSync(key).ino,after.ino);assert.strictEqual(fs.statSync(key).uid,role);assert.strictEqual(fs.statSync(key).mode&4095,416);
assert.strictEqual(fs.readFileSync(d+'/blocked','utf8'),'emergency');assert.strictEqual(fs.readFileSync(d+'/watchdog','utf8'),'retained');
assert.strictEqual(fs.readdirSync(d).filter(function(n){return n.charAt(0)==='.';}).length,0);
""".replace('CALLER', str(caller)))

    def test_staging_refuses_directory_substitution_before_any_bytes_are_written(self):
        self.run_js("""
var parent=d+'/state',foreign=d+'/foreign';fs.mkdirSync(parent,504);fs.mkdirSync(foreign,504);
var open=fs.openSync,write=fs.writeSync,swapped=false,writes=0;
fs.openSync=function(name){if(!swapped&&String(name).indexOf('.cytv-record-')===0){swapped=true;fs.renameSync(parent,parent+'-old');fs.symlinkSync(foreign,parent);}return open.apply(fs,arguments);};
fs.writeSync=function(){writes++;return write.apply(fs,arguments);};
assert.throws(function(){p.atomicRecord(parent,'home-preference','private-staging-marker');});
assert.strictEqual(writes,0);assert.strictEqual(fs.readdirSync(foreign).length,0);
assert.strictEqual(fs.readdirSync(parent+'-old').length,0);
""")

    def test_configuration_rejects_type_link_size_group_and_symlink_ancestors(self):
        self.run_js("""
var key=d+'/ssap-key.json',apps=d+'/apps.json';fs.writeFileSync(apps,'[]');
fs.writeFileSync(key,'retained');fs.chmodSync(key,509);
fs.linkSync(apps,d+'/other');assert.throws(function(){p.prepareConfiguration(d);});fs.unlinkSync(d+'/other');
assert.strictEqual(fs.statSync(key).mode&4095,509);
fs.unlinkSync(apps);fs.mkdirSync(apps);assert.throws(function(){p.prepareConfiguration(d);});fs.rmdirSync(apps);fs.writeFileSync(apps,'[]');
fs.truncateSync(key,65537);assert.throws(function(){p.prepareConfiguration(d);});fs.truncateSync(key,8);
var original=fs.lstatSync,ino=fs.statSync(apps).ino;
fs.lstatSync=function(){var s=original.apply(fs,arguments);if(s.ino===ino)s.uid=process.getuid()+1;return s;};
assert.throws(function(){p.prepareConfiguration(d);});assert.strictEqual(fs.statSync(key).mode&4095,509);fs.lstatSync=original;
var nested=d+'/nested';fs.mkdirSync(nested);fs.symlinkSync(nested,d+'/alias');
assert.throws(function(){p.inspectConfiguration(d+'/alias');});
var groups=process.getgroups,gid=process.getgid;process.getgroups=function(){return [98765];};process.getgid=function(){return 98765;};
assert.strictEqual(p(d),false);assert.throws(function(){p.atomicRecord(d,'pid','123');});
process.getgroups=groups;process.getgid=gid;
""")

    def test_record_failures_retain_fixed_storage_phase_and_existing_destination(self):
        self.run_js("""
fs.writeFileSync(d+'/controller.pid','original');
[['writeSync','write'],['fchmodSync','chmod'],['renameSync','rename']].forEach(function(item){
 var original=fs[item[0]],caught;
 fs[item[0]]=function(){var e=Error('private-path-marker');e.code='EACCES';throw e;};
 try{p.atomicRecord(d,'pid','replacement');}catch(e){caught=e;}finally{fs[item[0]]=original;}
 assert(caught);assert.strictEqual(caught.storagePhase,item[1]);
 assert.strictEqual(fs.readFileSync(d+'/controller.pid','utf8'),'original');
 assert.strictEqual(fs.readdirSync(d).length,1);
});
""")

    def test_accepted_legacy_runtime_directory_supports_followup_writers_and_readers(self):
        self.run_js("""
var logs=[],uid=process.getuid();
process.getgid=function(){return 5000;};process.getgroups=function(){return [5000];};
['lstatSync','fstatSync','statSync'].forEach(function(name){var original=fs[name];fs[name]=function(){var s=original.apply(fs,arguments);s.gid=5000;if(s.isDirectory())s.uid=5999;return s;};});
fs.chmodSync(d,511);
fs.writeFileSync(d+'/ssap-key.json','{"key":"retained"}');fs.chmodSync(d+'/ssap-key.json',416);
fs.writeFileSync(d+'/apps.json','[]');fs.chmodSync(d+'/apps.json',420);
fs.writeFileSync(d+'/blocked','emergency');fs.writeFileSync(d+'/watchdog','watchdog');
assert.strictEqual(p(d,function(event){logs.push(event);},true),true);
assert(logs.some(function(event){return event.event==='state-permissions-warning';}));
p.atomicRecord(d,'pid','123');p.atomicRecord(d,'logger','');
p.atomicRecord(d,'home-preference','{"enabled":false}');
p.atomicRecord(d,'home-response','{"returnValue":true}',{role:'app'});
p.atomicRecord(d,'startup-state','{"enabled":true}');
assert.strictEqual(fs.readFileSync(d+'/controller.pid','utf8'),'123');
assert.strictEqual(fs.readFileSync(d+'/controller.log','utf8'),'');
assert.strictEqual(fs.readFileSync(d+'/home-control.json','utf8'),'{"enabled":false}');
assert.strictEqual(p.readConfiguration(d,'key'),'{"key":"retained"}');assert.strictEqual(p.readConfiguration(d,'apps'),'[]');
assert.strictEqual(fs.readFileSync(d+'/blocked','utf8'),'emergency');assert.strictEqual(fs.readFileSync(d+'/watchdog','utf8'),'watchdog');
assert.throws(function(){p.inspectConfiguration(d);});assert.throws(function(){p.prepareConfiguration(d);});
assert.throws(function(){p.requestStop(d);});assert.throws(function(){p.atomicRecord(d,'home-request','{}');});
""")

    def test_directory_chmod_denial_requires_checked_unchanged_safe_metadata(self):
        self.run_js("""
fs.writeFileSync(d+'/ssap-key.json','{"key":"retained"}');fs.chmodSync(d+'/ssap-key.json',416);
fs.writeFileSync(d+'/apps.json','[]');fs.chmodSync(d+'/apps.json',420);
var chmod=fs.fchmodSync,ino=fs.statSync(d).ino;
['EPERM','EACCES'].forEach(function(code){
 fs.chmodSync(d,509);var logs=[];
 fs.fchmodSync=function(fd,mode){if(fs.fstatSync(fd).ino===ino){var e=Error('private-marker');e.code=code;throw e;}return chmod.apply(fs,arguments);};
 assert.strictEqual(p(d,function(event){logs.push(event);},true),true);
 assert(logs.some(function(event){return event.event==='state-permissions-warning';}));
 assert.strictEqual(fs.statSync(d).mode&4095,509);
 p.atomicRecord(d,'pid','123');p.atomicRecord(d,'logger','');p.atomicRecord(d,'home-preference','{"enabled":false}');
 assert.strictEqual(p.readConfiguration(d,'key'),'{"key":"retained"}');
 assert.strictEqual(p.readConfiguration(d,'apps'),'[]');
 fs.fchmodSync=function(fd,mode){if(fs.fstatSync(fd).ino===ino){fs.chmodSync(d,1023);var e=Error('denied');e.code=code;throw e;}return chmod.apply(fs,arguments);};
 assert.strictEqual(p(d,null,true),false,'denied normalization cannot accept changed unsafe mode');
 fs.chmodSync(d,509);
 var lstat=fs.lstatSync;fs.lstatSync=function(){var s=lstat.apply(fs,arguments);if(s.ino===ino)s.gid=98765;return s;};
 assert.strictEqual(p(d,null,true),false,'denial cannot waive group/identity checks');fs.lstatSync=lstat;
 fs.fchmodSync=chmod;
});
fs.chmodSync(d,509);fs.fchmodSync=function(fd,mode){if(fs.fstatSync(fd).ino===ino){var e=Error('io');e.code='EIO';throw e;}return chmod.apply(fs,arguments);};
assert.strictEqual(p(d,null,true),false,'unexpected chmod failures must not be swallowed');fs.fchmodSync=chmod;
""")
