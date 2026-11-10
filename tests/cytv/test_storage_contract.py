"""Canonical storage contract against real host inodes (no TV operations)."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


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
