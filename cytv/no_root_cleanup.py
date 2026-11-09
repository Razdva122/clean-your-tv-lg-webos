"""Explicit project removal with an ordinary reconnect/full-restart continuation.

Old installation receipts describe history. They are not permission to retain
the user's project keys or files after the user has requested their removal.
"""
import json
import base64
import hashlib
from time import monotonic, sleep

from .errors import TVRejected, UserError

APPS = ('com.local.nativehome', 'com.gathin.tvhome', 'com.cleanyourtv.updater')
RESTART_MESSAGE = 'Restart the TV completely, then choose Try again to finish removal.'
ROOT_MESSAGE = 'Some project files require Root access. Reconnect using Root to finish removal.'

# Shared with Root's current trusted cleanup bundle. No retained TV source is
# executed, no arbitrary paths are accepted, and Root owner backups are untouched.
PRIVATE_CLEANUP_PROGRAM = r'''
(function(){
'use strict';
var fs=require('fs'),path=require('path'),c=require('constants'),zlib=require('zlib'),crypto=require('crypto');
var input=JSON.parse(process.argv[process.argv.length-1]),uid=process.getuid();
if(['inventory','idle','sweep','stop','root-package','stage-carrier','boot-create','boot-probe','boot-retire'].indexOf(input.action)<0)throw Error('invalid-cleanup-action');
var base='/media/developer/apps/usr/palm',publicRoot='/media/developer/temp';
if(input.connection==='root-ssh'){
 if(uid!==0)throw Error('root-access-required');
 publicRoot='/var/lib/clean-your-tv-installer';
}
var apps=['com.local.nativehome','com.gathin.tvhome','com.cleanyourtv.updater'];
var services=['com.local.nativehome.service','com.gathin.tvhome.renewal','com.cleanyourtv.updater.service'];
var reply={schema:1,boot_id:fs.readFileSync('/proc/sys/kernel/random/boot_id','utf8').trim(),present:[],blocked:[],root_present:[],startup_services:[],external_update_hint:null,resident_installer:false,staging_ids:input.staging_ids||[]};
if(!Array.isArray(reply.staging_ids)||reply.staging_ids.length>128||reply.staging_ids.some(function(id){return typeof id!=='string'||!/^[a-f0-9]{32}$/.test(id);}))throw Error('invalid-staging-scope');
if(!/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/.test(reply.boot_id))throw Error('invalid-boot-identity');
function exists(p){try{return fs.lstatSync(p);}catch(e){if(e.code==='ENOENT')return null;throw e;}}
function same(a,b){return a.dev===b.dev&&a.ino===b.ino;}
function fail(){throw Error('unsafe-path');}
function ancestry(p){for(;;){var s=fs.lstatSync(p),sdk=[publicRoot,'/media/developer','/media/developer/apps','/media/developer/apps/usr',base,base+'/applications',base+'/packages',base+'/services'].indexOf(p)>=0;
 // SDK creates these fixed containers and project app/service roots as0777.
 // This does not admit arbitrary writable ancestry or UUID staging directories.
 sdk=sdk||apps.some(function(app){return p===base+'/applications/'+app;})||services.some(function(service){return p===base+'/services/'+service;});
 var shared=(sdk&&s.uid===0&&(s.mode&4095)===511)||((p===base+'/packages'||p===base+'/services')&&[1001,501].indexOf(s.uid)>=0);
 if(!s.isDirectory()||s.isSymbolicLink()||(!shared&&[0,uid,5999].indexOf(s.uid)<0)||((s.mode&2)&&!shared&&!(s.uid===0&&(s.mode&512))))fail();if(path.dirname(p)===p)break;p=path.dirname(p);}}
function at(p,expected,fn){
 var before=fs.lstatSync(p),fd=fs.openSync(p,c.O_RDONLY|c.O_DIRECTORY|c.O_NOFOLLOW),prior=process.cwd(),priorStat=fs.statSync('.');
 try{if(!before.isDirectory()||!same(before,fs.fstatSync(fd))||!same(before,expected))fail();process.chdir(p);if(!same(before,fs.statSync('.')))fail();return fn(fd);}
 finally{fs.closeSync(fd);process.chdir(prior);if(!same(priorStat,fs.statSync('.')))fail();}
}
function remove(p,expected){
 ancestry(path.dirname(p));var s=fs.lstatSync(p);if(!same(s,expected))fail();
 if(!s.isDirectory()){if(!s.isFile()&&!s.isSymbolicLink())fail();at(path.dirname(p),fs.lstatSync(path.dirname(p)),function(fd){if(!same(s,fs.lstatSync(path.basename(p))))fail();fs.unlinkSync(path.basename(p));fs.fsyncSync(fd);});return;}
 var count=0;
 function walk(name,pin,depth){if(depth>32)fail();at(name,pin,function(fd){fs.readdirSync('.').forEach(function(child){
  if(++count>65536)fail();var item=fs.lstatSync(child);
  if(item.isDirectory()){walk(child,item,depth+1);if(!same(item,fs.lstatSync(child)))fail();fs.rmdirSync(child);}
  else{if(!item.isFile()&&!item.isSymbolicLink())fail();if(!same(item,fs.lstatSync(child)))fail();fs.unlinkSync(child);}
 });fs.fsyncSync(fd);});}
 walk(p,s,0);at(path.dirname(p),fs.lstatSync(path.dirname(p)),function(fd){if(!same(s,fs.lstatSync(path.basename(p))))fail();fs.rmdirSync(path.basename(p));fs.fsyncSync(fd);});
}
function blocked(scope,error){reply.blocked.push({scope:scope,reason:error.code==='EACCES'||error.code==='EPERM'?'permission-denied':'unsafe-path'});}
function visit(p,scope){try{var s=exists(p);if(!s)return;if(input.action==='sweep'||input.action==='root-package')remove(p,s);if(exists(p))reply.present.push(scope);}catch(e){blocked(scope,e);}}
function rootHint(p,scope){try{if(exists(p))reply.root_present.push(scope);}catch(e){if(e.code==='EACCES')reply.root_present.push(scope);else blocked(scope,e);}}
// A per-approved-goal volatile marker also distinguishes firmware that reuses
// kernel UUIDs after restoring a snapshot. Inventory never creates this marker.
if(input.action.indexOf('boot-')===0){
 var bootRoot='/tmp';
 ancestry(bootRoot);var parent=fs.lstatSync(bootRoot);
 if(parent.uid!==0||(parent.mode&4095)!==1023||typeof input.removal!=='string'||!/^[a-f0-9]{32}$/.test(input.removal))fail();
 var marker='cytv-removal-'+input.removal+'.boot',prefix='cytv-removal-v1:'+input.removal+':',proof=input.proof;
 var markerStat=function(s){if(!s.isFile()||s.isSymbolicLink()||s.uid!==uid||(s.mode&4095)!==384||s.nlink!==1||s.size!==prefix.length+37)fail();};
 var markerRead=function(expected){var s=exists(marker);if(!s)return null;markerStat(s);
  var fd=fs.openSync(marker,c.O_RDONLY|c.O_NOFOLLOW|c.O_NONBLOCK),b=new Buffer(s.size),offset=0;
  try{var opened=fs.fstatSync(fd);markerStat(opened);if(!same(s,opened))fail();
   while(offset<b.length){var n=fs.readSync(fd,b,offset,b.length-offset,offset);if(n<=0)fail();offset+=n;}
   var after=fs.lstatSync(marker);markerStat(after);if(!same(s,after))fail();
  }finally{fs.closeSync(fd);}
  var text=b.toString(),kernel=text.slice(prefix.length,-1);
  if(text!==prefix+kernel+'\n'||!/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/.test(kernel))fail();
  if(expected&&(!same(s,expected)||kernel!==expected.kernel))fail();return {stat:s,kernel:kernel};
 };
 at(bootRoot,parent,function(directory){
  if(input.action!=='boot-create'){
   if(!proof||Object.keys(proof).sort().join(',')!=='dev,goal,ino,kernel,schema'||proof.schema!==1||proof.goal!==input.removal||typeof proof.kernel!=='string'||!/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/.test(proof.kernel)||[proof.dev,proof.ino].some(function(n){return typeof n!=='number'||n<0||n>9007199254740991||Math.floor(n)!==n;}))fail();
  }
  var item=markerRead(input.action==='boot-create'?null:proof);
  if(input.action==='boot-create'){
   // A lost create response can reuse only this exact owned goal. If a genuine
   // kernel change preceded host capture, establish a fresh baseline first.
   if(item&&item.kernel!==reply.boot_id){remove(marker,item.stat);item=null;}
   if(!item){var out=fs.openSync(marker,c.O_WRONLY|c.O_CREAT|c.O_EXCL|c.O_NOFOLLOW,384),bytes=new Buffer(prefix+reply.boot_id+'\n');
    try{var offset=0;while(offset<bytes.length){var n=fs.writeSync(out,bytes,offset,bytes.length-offset,offset);if(n<=0)fail();offset+=n;}fs.fsyncSync(out);}finally{fs.closeSync(out);}fs.fsyncSync(directory);item=markerRead(null);}
   reply.boot_proof={schema:1,goal:input.removal,kernel:item.kernel,dev:item.stat.dev,ino:item.stat.ino};
  }else{
   reply.boot_restarted=!item||proof.kernel!==reply.boot_id;
   if(input.action==='boot-retire'){if(!reply.boot_restarted)fail();if(item)remove(marker,item.stat);}
  }
 });process.stdout.write(JSON.stringify(reply));return;
}
if(input.action==='stage-carrier'){
 var index=apps.indexOf(input.app);if(index<0||!/^[a-f0-9]{32}$/.test(input.removal)||!/^[a-f0-9]{64}$/.test(input.sha256)||!(input.size>0&&input.size<1048576))fail();
 ancestry(path.dirname(publicRoot));if(!exists(publicRoot))fs.mkdirSync(publicRoot,448);ancestry(publicRoot);
 var stage=publicRoot+'/cytv-'+input.removal,filename=['helper.ipk','launcher.ipk','updater.ipk'][index];
 if(!exists(stage))fs.mkdirSync(stage,448);ancestry(stage);var pin=fs.lstatSync(stage);if(pin.uid!==uid||(pin.mode&511)!==448)fail();
 if(typeof input.carrier!=='string'||input.carrier.length!==4*Math.ceil(input.size/3)||!/^[A-Za-z0-9+/]*={0,2}$/.test(input.carrier))fail();
 var raw=new Buffer(input.carrier,'base64');if(raw.length!==input.size||crypto.createHash('sha256').update(raw).digest('hex')!==input.sha256)fail();
  at(stage,pin,function(fd){var old=exists(filename);if(old){if(!old.isFile()||old.nlink!==1||old.size!==input.size)fail();var oldFd=fs.openSync(filename,c.O_RDONLY|c.O_NOFOLLOW);try{if(!same(old,fs.fstatSync(oldFd)))fail();var bytes=new Buffer(old.size),offset=0;while(offset<bytes.length){var n=fs.readSync(oldFd,bytes,offset,bytes.length-offset,offset);if(n<=0)fail();offset+=n;}if(!same(old,fs.lstatSync(filename))||crypto.createHash('sha256').update(bytes).digest('hex')!==input.sha256)fail();}finally{fs.closeSync(oldFd);}}
   else{var tmp='.carrier-'+crypto.randomBytes(12).toString('hex'),out=fs.openSync(tmp,c.O_WRONLY|c.O_CREAT|c.O_EXCL|c.O_NOFOLLOW,384);try{var offset=0;while(offset<raw.length){var n=fs.writeSync(out,raw,offset,raw.length-offset,offset);if(n<=0)fail();offset+=n;}fs.fsyncSync(out);}finally{fs.closeSync(out);}if(exists(filename))fail();fs.renameSync(tmp,filename);fs.fsyncSync(fd);}
  });process.stdout.write(JSON.stringify(reply));return;
}
if(input.action==='root-package'){
 if(uid!==0||apps.concat(['com.cleanyourtv.root.preview','com.cleanyourtv.root.updater','com.cleanyourtv.system.updater']).indexOf(input.app)<0)throw Error('invalid-root-package');
 var service=input.app==='com.gathin.tvhome'?'com.gathin.tvhome.renewal':input.app+'.service';
 visit(base+'/applications/'+input.app,input.app+' app');visit(base+'/services/'+service,input.app+' service');visit(base+'/packages/'+input.app,input.app+' package');
 process.stdout.write(JSON.stringify(reply));return;
}
['clean-your-tv-root','clean-your-tv-installation','clean-your-tv-python','clean-your-tv-root-updater','clean-your-tv-system-updater'].forEach(function(name){rootHint('/var/lib/'+name,name);});
rootHint('/var/webos-profile/override/clean-your-tv-root.json','root-profile');
services.slice(0,2).forEach(function(service){try{var dir=base+'/services/'+service,s=exists(dir);if(s&&s.isDirectory()){ancestry(path.dirname(dir));at(dir,s,function(){var source=exists('service.js');if(source&&source.isFile())reply.startup_services.push(service);});}}catch(e){blocked('startup-service '+service,e);}});
try{
 var journal=base+'/services/'+services[2]+'/state/transaction.json',transactionStat=exists(journal);
 if(transactionStat){ancestry(path.dirname(journal));if(!transactionStat.isFile()||transactionStat.nlink!==1||transactionStat.size>5242880)fail();
  var transactionFd=fs.openSync(journal,c.O_RDONLY|c.O_NOFOLLOW|c.O_NONBLOCK),bytes=new Buffer(transactionStat.size),offset=0;
  try{if(!same(transactionStat,fs.fstatSync(transactionFd)))fail();while(offset<bytes.length){var count=fs.readSync(transactionFd,bytes,offset,bytes.length-offset,offset);if(count<=0)fail();offset+=count;}if(!same(transactionStat,fs.lstatSync(journal)))fail();}
  finally{fs.closeSync(transactionFd);}
  // This is a historical hint, not proof that an external job is still active.
  // It moves the ordinary restart earlier, never blocks post-boot own cleanup.
  try{var transaction=JSON.parse(bytes.toString());if(transaction.schema===1&&['installing','rolling-back','recovery-required'].indexOf(transaction.status)>=0)reply.external_update_hint=transaction.status;}catch(ignored){}
 }
}catch(ignored){}
var installerRoots=['/media/developer/.cytv-installer','/tmp/.cytv-installer'];
if(uid===0)installerRoots.push('/tmp/.cytv-installer-root','/var/lib/clean-your-tv-installer');
else installerRoots.push('/.cytv-installer');
function privateInstaller(root){
 if(root!=='/.cytv-installer')return;
 var s=exists(root);if(!s)return;
 if(!s.isDirectory()||s.isSymbolicLink()||s.uid!==uid||(s.mode&4095)!==448)fail();
 for(var p=root;;p=path.dirname(p)){
  var parent=fs.lstatSync(p);
  if(!parent.isDirectory()||parent.isSymbolicLink()||(parent.uid!==0&&parent.uid!==uid)||
     ((parent.mode&18)&&!(parent.uid===0&&(parent.mode&512))))fail();
  if(path.dirname(p)===p)break;
 }
}
installerRoots.forEach(function(root){try{privateInstaller(root);var operations=root+'/operations';if(exists(operations)){ancestry(operations);var ids=fs.readdirSync(operations);reply.resident_installer=reply.resident_installer||ids.length>0;ids.forEach(function(id){if(/^[a-f0-9]{32}$/.test(id)&&reply.staging_ids.indexOf(id)<0)reply.staging_ids.push(id);});if(reply.staging_ids.length>128)fail();}}catch(e){blocked('installer-private',e);}});
if(input.action==='idle'){
 // File absence alone cannot prove that a deleted service or installer stopped.
 var prefixes=installerRoots.concat([publicRoot+'/cytv-', '/var/lib/clean-your-tv-', '/tmp/cytv-', '/tmp/clean-your-tv-']);
 apps.forEach(function(app,index){prefixes.push(base+'/applications/'+app,base+'/services/'+services[index]);});
 reply.idle=true;
 try{var proc='/proc/',pids=fs.readdirSync(proc).filter(function(pid){return /^[1-9][0-9]*$/.test(pid)&&Number(pid)!==process.pid;});
  if(pids.length>4096)reply.idle=false;
  pids.forEach(function(pid){try{
   var args=fs.readFileSync(proc+pid+'/cmdline','utf8').split('\0').filter(Boolean),argc=args.length;
   try{args.push(fs.readlinkSync(proc+pid+'/exe').replace(/ \(deleted\)$/,''));}catch(e){if(e.code!=='ENOENT')throw e;}
   try{args.push(fs.readlinkSync(proc+pid+'/cwd').replace(/ \(deleted\)$/,''));}catch(e){if(e.code!=='ENOENT')throw e;}
   if(args.some(function(arg){return apps.indexOf(arg)>=0||prefixes.some(function(prefix){return arg===prefix||arg.indexOf(prefix+'/')===0||(/[-]$/.test(prefix)&&arg.indexOf(prefix)===0);});}))reply.idle=false;
   // Require an unambiguous absolute script. Interpreter flags have too many
   // inline/combined spellings to infer that an old project body is absent.
   if(args.some(function(arg){return /(^|\/)(node|python[0-9.]*)$/.test(arg);})&&
      (argc<2||!/^\/.*[.](js|cjs|mjs|py|pyc)$/.test(args[1])))reply.idle=false;
  }catch(e){if(e.code!=='ENOENT'||exists(proc+pid))reply.idle=false;}});
 }catch(e){reply.idle=false;}
 process.stdout.write(JSON.stringify(reply));return;
}
function helperState(state){
 ancestry(path.dirname(state));var s=fs.lstatSync(state);
 // Published Helper accepts legacy shared state0777 when chmod is unavailable.
 // Only this exact directory is relaxed; at() pins it without following links.
 if(!s.isDirectory()||s.isSymbolicLink()||[0,uid,5999].indexOf(s.uid)<0||((s.mode&2)&&(s.mode&4095)!==511))fail();
 return s;
}
if(input.action==='stop'){
 var state=base+'/applications/'+apps[0]+'/state',s=null;
 try{s=exists(state);}catch(e){blocked('helper-control',e);}
 if(s)try{helperState(state);at(state,s,function(fd){
  ['blocked','control.json'].forEach(function(name){var old=exists(name);if(old&&(!old.isFile()||old.nlink!==1))fail();});
  if(!exists('blocked')){var marker=fs.openSync('blocked',c.O_WRONLY|c.O_CREAT|c.O_EXCL|c.O_NOFOLLOW,436);try{fs.writeSync(marker,new Buffer('stopped'),0,7,0);fs.fsyncSync(marker);}finally{fs.closeSync(marker);}}
  var name='.cytv-stop-'+crypto.randomBytes(12).toString('hex'),control=fs.openSync(name,c.O_WRONLY|c.O_CREAT|c.O_EXCL|c.O_NOFOLLOW,420);
  try{var b=new Buffer('{"cmd":"stop"}');fs.writeSync(control,b,0,b.length,0);fs.fsyncSync(control);}finally{fs.closeSync(control);}
  fs.renameSync(name,'control.json');fs.fsyncSync(fd);
 });}catch(e){blocked('helper-control',e);}
 var deadline=Date.now()+8000;
 var stopped=function(){var running=false;
  try{var pidFile=state+'/controller.pid',pidStat=exists(pidFile);if(pidStat){helperState(state);if(!pidStat.isFile()||pidStat.nlink!==1||pidStat.size>32)fail();var text=fs.readFileSync(pidFile,'utf8').trim();if(/^[1-9][0-9]{0,8}$/.test(text)){try{var args=fs.readFileSync('/proc/'+text+'/cmdline','utf8').split('\0');if(args[0]===apps[0]||args.indexOf(base+'/applications/'+apps[0]+'/native.js')>=0){process.kill(Number(text),0);running=true;}}catch(e){if(e.code!=='ENOENT'&&e.code!=='ESRCH')throw e;}}}}
  catch(e){blocked('helper-control',e);}
  if(running&&Date.now()<deadline){setTimeout(stopped,100);return;}
  reply.controller_running=running;process.stdout.write(JSON.stringify(reply));
 };stopped();return;
}
apps.forEach(function(app,index){visit(base+'/applications/'+app,app+' app');visit(base+'/packages/'+app,app+' package');visit(base+'/services/'+services[index],app+' service');});
installerRoots.forEach(function(root){try{privateInstaller(root);visit(root,'installer-private');}catch(e){blocked('installer-private',e);}});
// Only fixed project registration names. Existing foreign roles/routes are not
// inferred to belong to this project merely because they reference an app.
['services.d','roles.d','client-permissions.d','api-permissions.d','manifests.d','groups.d'].forEach(function(folder){
 var dir='/var/luna-service2-dev/'+folder;if(!exists(dir))return;
 try{ancestry(dir);fs.readdirSync(dir).forEach(function(name){if(apps.concat(services).some(function(id){return ['.json','.service','.app.json','.api.json','.group.json','.groups.json','.manifest.json','.package.json','.permissions.json'].some(function(suffix){return name===id+suffix;});}))visit(dir+'/'+name,'registration '+name);});}catch(e){blocked('registrations '+folder,e);}
});
// Inspect only the small IPK control member, never extract an archive or trust
// the cytv-* directory prefix alone. Foreign payloads remain in place.
function controlIdentity(file,done){var fd,stat,raw;
 try{ancestry(path.dirname(file));stat=fs.lstatSync(file);if(!stat.isFile()||stat.nlink!==1)fail();fd=fs.openSync(file,c.O_RDONLY|c.O_NOFOLLOW|c.O_NONBLOCK);if(!same(stat,fs.fstatSync(fd)))fail();
  var read=function(n,offset){var b=new Buffer(n);if(fs.readSync(fd,b,0,n,offset)!==n)fail();return b;};
  if(read(8,0).toString()!=='!<arch>\n')fail();var offset=8,count=0;
  while(offset+60<=stat.size&&++count<=4){var h=read(60,offset),name=h.slice(0,16).toString().trim().replace(/\/$/,''),sizeText=h.slice(48,58).toString().trim();if(h.slice(58).toString()!=='`\n'||!/^\d+$/.test(sizeText))fail();var size=Number(sizeText);offset+=60;if(offset+size>stat.size)fail();if(name==='control.tar.gz'){if(size>65536)fail();raw=read(size,offset);}offset+=size+(size%2);}
  if(!raw||!same(stat,fs.lstatSync(file)))fail();fs.closeSync(fd);fd=null;
 }catch(e){if(fd!==undefined&&fd!==null)fs.closeSync(fd);done(e);return;}
 var unzip=zlib.createGunzip(),parts=[],length=0,finished=false;
 function finish(error,value){if(finished)return;finished=true;done(error,value,stat);}
 unzip.on('data',function(b){length+=b.length;if(length>65536){unzip.destroy();finish(Error('unsafe-path'));}else parts.push(b);});
 unzip.on('error',finish);unzip.on('end',function(){try{var tar=Buffer.concat(parts,length),offset=0,app=null;
  while(offset+512<=tar.length){var h=tar.slice(offset,offset+512),name=h.slice(0,100).toString().replace(/\0.*$/,'').replace(/^\.\//,''),size=parseInt(h.slice(124,136).toString().replace(/\0.*$/,'').trim(),8);offset+=512;if(!name)break;if(!isFinite(size)||size<0||offset+size>tar.length)fail();
   if(name==='control'){var text=tar.slice(offset,offset+size).toString(),match=text.match(/^Package: ([a-zA-Z0-9_.-]+)\s*$/m);if(!match||app!==null)fail();app=match[1];}offset+=Math.ceil(size/512)*512;}
  if(!same(stat,fs.lstatSync(file)))fail();finish(null,app);
 }catch(e){finish(e);}});unzip.end(raw);
}
var stages=[];try{if(exists(publicRoot)){ancestry(publicRoot);stages=fs.readdirSync(publicRoot).filter(function(name){return /^cytv-[a-f0-9]{32}$/.test(name);});}}catch(e){blocked('installer-staging',e);}
function next(){if(!stages.length){process.stdout.write(JSON.stringify(reply));return;}var stage=stages.shift(),dir=publicRoot+'/'+stage,known=reply.staging_ids.indexOf(stage.slice(5))>=0,pin,files,owned=false;
 try{pin=fs.lstatSync(dir);if(!pin.isDirectory()||pin.isSymbolicLink()){if(known)visit(dir,'installer-staging');next();return;}files=fs.readdirSync(dir);}catch(e){if(known)blocked('installer-staging',e);next();return;}
 function retire(name,expected){if(!expected)return;owned=true;try{if(!same(pin,fs.lstatSync(dir)))fail();if(input.action==='sweep')remove(dir+'/'+name,expected);if(exists(dir+'/'+name))reply.present.push('installer-staging '+name);}catch(e){blocked('installer-staging',e);}}
 function file(){if(!files.length){try{if(input.action==='sweep'&&(known||owned)&&same(pin,fs.lstatSync(dir))&&!fs.readdirSync(dir).length)fs.rmdirSync(dir);}catch(e){blocked('installer-staging',e);}next();return;}
  var name=files.shift(),index=['helper.ipk','launcher.ipk','updater.ipk'].indexOf(name);if(index<0){if(known)retire(name,exists(dir+'/'+name));file();return;}
  controlIdentity(dir+'/'+name,function(error,app,expected){if(error){if(known)retire(name,exists(dir+'/'+name));file();return;}if(app===apps[index])retire(name,expected);file();});
 }file();
}next();
}());
'''


def _program(request):
    # Keep the SSH exec request tiny; old TV SSH servers reject long argv.
    return ('process.argv.push(' + json.dumps(json.dumps(request)) + ');\n' + PRIVATE_CLEANUP_PROGRAM).encode()


def _device(installer, action, proof=None):
    pending = installer.store.pending(installer.profile) or {}
    request = {'action':action, 'staging_ids':pending.get('cleanup_staging_ids', []),
               'removal':pending.get('removal_operation'), 'proof':proof}
    if installer.profile.get('connection') == 'root-ssh':
        request['connection'] = 'root-ssh'
    raw = installer.remote.run('/usr/bin/node', data=_program(request), timeout=90)
    value = json.loads(raw)
    if (not isinstance(value, dict) or value.get('schema') != 1 or
            not all(isinstance(value.get(k), list) for k in ('present', 'blocked', 'root_present'))):
        raise UserError('Removal could not be checked. Reconnect and try again.')
    return value


def _protected_package(row):
    """Only permission failures in fixed No-root OS-owned namespaces qualify."""
    if row.get('reason') != 'permission-denied':
        return None
    scope = row.get('scope', '')
    for app, service in zip(APPS, ('com.local.nativehome.service', 'com.gathin.tvhome.renewal', 'com.cleanyourtv.updater.service')):
        if scope in (app + ' app', app + ' package', app + ' service', 'startup-service ' + service):
            return app
        if scope == 'helper-control':
            return APPS[0]
        if scope.startswith('registration ') and scope[13:].startswith((app + '.', service + '.')):
            return app
    return None


def _check_access(value, defer_packages=False):
    blocked = [row for row in value['blocked'] if not (defer_packages and _protected_package(row))]
    if value['root_present'] or any(row.get('reason') == 'permission-denied' for row in blocked):
        raise UserError(ROOT_MESSAGE, reason_code='root-access-required')
    if blocked:
        raise UserError('Some project paths changed. Close other installers and try again.')


def _remove_package(installer, app):
    try:
        installer.remote.luna('com.webos.appInstallService/dev/remove', {'id': app, 'subscribe': True}, terminal='removed', timeout=150)
    except TVRejected as error:
        error.args = ('The TV rejected removal. Check the error details and try again.',)
        raise


def _remove_input_shortcut(installer):
    """A fixed owned delete can succeed even when the optional list API fails."""
    def request(method, payload):
        try:
            return installer.remote.luna('com.webos.service.eim/' + method, payload)
        except (TVRejected, ValueError):
            return {}
        except UserError as error:
            if error.reason_code != 'operation-timeout' and str(error) not in (
                    'TV operation timed out. Run cytv status before retrying.',
                    'TV command ended without a confirmed result. Run cytv status.'):
                raise
            # An optional bus failure is not proof of a working SSH connection.
            _device(installer, 'inventory')
            return {}
    devices = request('getAllInputStatus', {}).get('devices')
    if (isinstance(devices, list) and all(isinstance(row, dict) and
            (isinstance(row.get('id'), str) or isinstance(row.get('appId'), str)) for row in devices)
            and not any(row.get('appId') == APPS[1] or row.get('id') == APPS[1] for row in devices)):
        return True
    return request('deleteDevice', {'appId': APPS[1]}).get('returnValue') is True


def _restore_home(installer):
    """Old webOS has an LG Home bar rather than a launchable Home app.

    Only the exact missing-app rejection admits a fresh stock-surface readback.
    Never infer restored controls from an arbitrary app or a launch receipt.
    """
    uri='com.webos.applicationManager/'
    try:
        result=installer.remote.luna(uri+'launch', {'id':'com.webos.app.home'})
    except TVRejected as error:
        if (error.luna.get('operation')!='application-launch' or error.luna.get('error_code')!=-101
                or error.luna.get('return_value') is not False):
            raise
    else:
        if isinstance(result,dict) and result.get('returnValue') is True:
            return
        raise UserError('Removal could not be checked. Reconnect and try again.', reason_code='controls-unverified')
    stock={'com.webos.app.home','com.webos.app.livetv',
           'com.webos.app.hdmi1','com.webos.app.hdmi2','com.webos.app.hdmi3','com.webos.app.hdmi4'}
    def foreground():
        reply=installer.remote.luna(uri+'getForegroundAppInfo', {}, timeout=5)
        app=reply.get('appId') if isinstance(reply,dict) and reply.get('returnValue') is True else None
        if not isinstance(app,str) or not app:
            raise UserError('Removal could not be checked. Reconnect and try again.', reason_code='controls-unverified')
        return app
    if foreground() in stock:
        return
    # Fixed built-in source only; never relaunch an arbitrary observed app.
    launched=installer.remote.luna(uri+'launch', {'id':'com.webos.app.livetv'})
    if not isinstance(launched,dict) or launched.get('returnValue') is not True:
        raise UserError('Removal could not be checked. Reconnect and try again.', reason_code='controls-unverified')
    deadline=monotonic()+5
    while foreground() not in stock:
        if monotonic()>=deadline:
            raise UserError('Removal could not be checked. Reconnect and try again.', reason_code='controls-unverified')
        sleep(.1)


def _repair_registration(installer, value):
    """One same-ID repair; an uncertain install is never submitted again."""
    from . import no_root_carrier, package
    candidates = {app for row in value['blocked'] if (app := _protected_package(row))}
    if not candidates or not hasattr(installer, 'payload'):
        return value
    registered = {app['id'] for app in installer.installed_apps()}
    for app in sorted(candidates - registered):
        pending = installer.store.pending(installer.profile)
        carriers = dict(pending.get('cleanup_carriers', {}))
        if carriers.get(app) not in (None, 'failed'):
            raise UserError(ROOT_MESSAGE, reason_code='root-access-required')
        def authenticated(name):
            raw = (installer.payload / package.safe_name(name)).read_bytes()
            if hashlib.sha256(raw).hexdigest() != installer.manifest['files'].get(name):
                raise ValueError('Cleanup payload changed')
            return raw
        try:
            source = authenticated(installer.manifest.get({'com.local.nativehome':'helper', 'com.gathin.tvhome':'launcher', 'com.cleanyourtv.updater':'updater'}[app],
                                                        ('helper.ipk', 'launcher.ipk', 'updater.ipk')[APPS.index(app)]))
            carrier = no_root_carrier.build(app, [source], noop=authenticated('installer-support/cleanup-noop'),
                                           architecture='arm' if app == APPS[0] else 'all')
        except (OSError, ValueError, KeyError):
            raise UserError(ROOT_MESSAGE, reason_code='root-access-required') from None
        pending = installer.store.pending(installer.profile)
        identifier = pending['removal_operation']
        stages = list(pending.get('cleanup_staging_ids', []))
        if identifier not in stages:
            stages.append(identifier)
            installer.store.checkpoint(installer.profile, cleanup_staging_ids=stages)
        request = {'action':'stage-carrier', 'app':app, 'removal':identifier, 'size':len(carrier),
                   'sha256':hashlib.sha256(carrier).hexdigest(), 'carrier':base64.b64encode(carrier).decode('ascii')}
        installer.remote.run('/usr/bin/node', data=_program(request), timeout=90)
        filename = ('helper.ipk', 'launcher.ipk', 'updater.ipk')[APPS.index(app)]
        carriers[app] = 'submitted'
        installer.store.checkpoint(installer.profile, cleanup_carriers=carriers)
        try:
            installer.remote.luna('com.webos.appInstallService/dev/install',
                                  {'id':app, 'ipkUrl':'/media/developer/temp/cytv-' + identifier + '/' + filename, 'subscribe':True}, terminal='installed', timeout=150)
        except TVRejected:
            carriers[app] = 'failed'
            installer.store.checkpoint(installer.profile, cleanup_carriers=carriers)
            raise
        carriers[app] = 'installed'
        installer.store.checkpoint(installer.profile, cleanup_carriers=carriers)
        if app not in {row['id'] for row in installer.installed_apps()}:
            raise UserError('Removal could not be checked. Reconnect and try again.')
        _remove_package(installer, app)
        carriers[app] = 'removed'
        installer.store.checkpoint(installer.profile, cleanup_carriers=carriers)
    return _device(installer, 'sweep')


def continue_removal(installer, expected_pending):
    pending = installer.store.pending(installer.profile)
    if pending != expected_pending or not pending or pending.get('recovery_protocol') != 'clean-removal-v1':
        raise UserError('Removal evidence changed. Recovery data was kept.', reason_code='pending-operation')
    current = _device(installer, 'inventory')
    _check_access(current, defer_packages=True)
    installer.store.checkpoint(installer.profile, cleanup_staging_ids=current['staging_ids'])
    app_info = installer.installed_apps()
    apps = {app['id'] for app in app_info}
    carriers = {app['id'] for app in app_info if app.get('title') == 'Clean Your TV cleanup' and app.get('visible') is False}
    if any(app in apps for app in ('com.cleanyourtv.root.preview', 'com.cleanyourtv.root.updater', 'com.cleanyourtv.system.updater')):
        raise UserError(ROOT_MESSAGE, reason_code='root-access-required')
    if pending.get('stage') == 'verified-clean' and not current['blocked'] and not current['present'] and not apps.intersection(APPS):
        from .root_no_root_handoff import release
        release(installer)
        installer.store.finish_clean_removal(installer.profile)
        return {'removed': True, 'verified_clean': True}
    empty = (pending.get('stage') == 'requested' and not pending.get('previous') and not pending.get('cleanup_boot_proof')
             and not current['blocked'] and not current['present'] and not apps.intersection(APPS)
             and not current['startup_services'] and not current['resident_installer'] and not current['external_update_hint'])
    if empty and _device(installer, 'idle').get('idle') is True and _remove_input_shortcut(installer):
        _restore_home(installer)
        final = _device(installer, 'inventory')
        _check_access(final)
        if (not final['present'] and not {row['id'] for row in installer.installed_apps()}.intersection(APPS)
                and _device(installer, 'idle').get('idle') is True):
            installer.store.checkpoint(installer.profile, stage='verified-clean', removal_reason='removal-verified',
                                       result={'removed': True, 'verified_clean': True})
            from .root_no_root_handoff import release
            release(installer)
            installer.store.finish_clean_removal(installer.profile)
            return {'removed': True, 'verified_clean': True}
    def capture_boot():
        # A lost re-arm create response must retry seeding, not compare the new
        # marker against a retired inode from the previous captured baseline.
        installer.store.checkpoint(installer.profile, cleanup_boot_proof=None, stage='requested')
        proof = _device(installer, 'boot-create')['boot_proof']
        installer.store.checkpoint(installer.profile, cleanup_boot_proof=proof,
                                   cleanup_boot_id=proof['kernel'], stage='requested')
        return proof
    proof = pending.get('cleanup_boot_proof')
    if proof is None or pending.get('stage') == 'verified-clean':
        if proof is not None:
            _device(installer, 'boot-retire', proof=proof)
        proof = capture_boot()
        restarted = False
    else:
        restarted = _device(installer, 'boot-probe', proof=proof)['boot_restarted'] is True
    installer.progress('Restoring TV controls…')
    stopped = _device(installer, 'stop')
    _check_access(stopped, defer_packages=True)
    unavailable = set(pending.get('cleanup_startup_unavailable', []))
    startup_failed = not restarted and any(_protected_package(row) for row in current['blocked'] + stopped['blocked'])
    for app, service in zip(APPS, ('com.local.nativehome.service', 'com.gathin.tvhome.renewal')):
        if service not in current['startup_services'] or app in carriers or (restarted and service in unavailable):
            continue
        try:
            reply = installer.remote.luna(service + '/disable', {}, timeout=10)
            if service == 'com.local.nativehome.service':
                cancel = reply.get('cancel', {})
                disabled = cancel.get('returnValue') is True or cancel.get('errorCode') == 2
            else:
                state = reply.get('state', {})
                disabled = state.get('enabled') is False and not state.get('error')
            if not disabled:
                raise UserError('TV startup could not be disabled. Try again.')
        except UserError as error:
            if not isinstance(error, TVRejected) and str(error) not in (
                    'TV startup could not be disabled. Try again.',
                    'TV operation timed out. Run cytv status before retrying.',
                    'TV command ended without a confirmed result. Run cytv status.'):
                raise
            # A failed optional service cannot make its own broken files
            # undeletable. Check the SSH connection, then move restart earlier.
            _device(installer, 'inventory')
            unavailable.add(service)
            startup_failed = True
    if unavailable:
        installer.store.checkpoint(installer.profile, cleanup_startup_unavailable=sorted(unavailable))
    inputs_removed = _remove_input_shortcut(installer)
    installer.store.checkpoint(installer.profile, cleanup_inputs_pending=not inputs_removed)
    _restore_home(installer)
    installer.store.checkpoint(installer.profile, stage='controls-restored')
    previous = pending.get('previous')
    resident = current.get('resident_installer') is True or current.get('external_update_hint') is not None
    if current.get('external_update_hint') is not None:
        installer.store.checkpoint(installer.profile, previous_update_status=current['external_update_hint'])
    while isinstance(previous, dict):
        resident |= previous.get('recovery_protocol') == 'no-root-original-stream-v1'
        previous = previous.get('previous')
    if stopped.get('controller_running') or startup_failed or (resident and not restarted):
        if (stopped.get('controller_running') or startup_failed) and restarted:
            _device(installer, 'boot-retire', proof=proof)
            proof = capture_boot()
        installer.store.checkpoint(installer.profile, stage='restart-required', removal_reason='restart-required', cleanup_restart_first=True)
        installer.progress(RESTART_MESSAGE)
        return {'removed': False, 'verified_clean': False, 'restart_required': True}
    for app, message in zip(APPS, ('Removing Helper…', 'Removing Home…', 'Removing the updater…')):
        if app not in apps:
            continue
        installer.progress(message)
        installer.store.checkpoint(installer.profile, stage='package-removal')
        _remove_package(installer, app)
    installer.progress('Removing private recovery data…')
    installer.store.checkpoint(installer.profile, stage='private-cleanup')
    _check_access(_repair_registration(installer, _device(installer, 'sweep')))
    if not restarted:
        installer.store.checkpoint(installer.profile, stage='restart-required', removal_reason='restart-required')
        installer.progress(RESTART_MESSAGE)
        return {'removed': False, 'verified_clean': False, 'restart_required': True}
    installer.progress('Verifying removal…')
    final = _device(installer, 'inventory')
    _check_access(final)
    if final['present'] or {app['id'] for app in installer.installed_apps()}.intersection(APPS):
        raise UserError('Some project files remain. Try again to finish removal.')
    if not inputs_removed:
        installer.store.checkpoint(installer.profile, removal_reason='controls-unverified')
        raise UserError('TV input shortcuts could not be checked. Try again.', reason_code='controls-unverified')
    _device(installer, 'boot-retire', proof=proof)
    installer.store.checkpoint(installer.profile, stage='verified-clean', removal_reason='removal-verified',
                               result={'removed': True, 'verified_clean': True})
    from .root_no_root_handoff import release
    release(installer)
    installer.store.finish_clean_removal(installer.profile)
    return {'removed': True, 'verified_clean': True}
