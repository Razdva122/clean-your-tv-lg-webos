"""Explicit project removal with an ordinary reconnect/full-restart continuation.

Old installation receipts describe history. They are not permission to retain
the user's project keys or files after the user has requested their removal.
"""
import json
from contextlib import ExitStack
from time import monotonic, sleep

from .errors import (TVRejected, UserError, TVCommandError, TV_STORAGE_FULL, CLEANUP_BOOT_ACTIONS,
                     OBSERVER_EXCEPTION_NAMES, OBSERVER_EXCEPTION_CODES,
                     OBSERVER_FILESYSTEM_OPERATIONS, no_root_cleanup_details)

from .tv_sources import node_loader, trusted_source

APPS = ('com.local.nativehome', 'com.gathin.tvhome', 'com.cleanyourtv.updater')
STARTUP_SERVICES = ('com.local.nativehome.service', 'com.gathin.tvhome.renewal')
RESTART_MESSAGE = 'Restart the TV completely, then choose Try again to finish removal.'
ROOT_MESSAGE = 'Some project files require Root access. Reconnect using Root to finish removal.'

# Shared with Root's current trusted cleanup bundle. No retained TV source is
# executed, no arbitrary paths are accepted, and Root owner backups are untouched.
PRIVATE_CLEANUP_PROGRAM = r'''
var cleanupStep='runtime',cleanupDirectory;
(function(){
'use strict';
var fs=require('fs'),path=require('path'),c=require('constants'),zlib=require('zlib');
var bootProof=(function(){var module={exports:{}},exports=module.exports;
/* CYTV_BOOT_PROOF_CONTRACT */
return module.exports;}());
var input=JSON.parse(process.argv[process.argv.length-1]),uid=process.getuid();
if(['inventory','idle','sweep','stop','history','root-package','boot-create','boot-probe','boot-retire','boot-release'].indexOf(input.action)<0)throw Error('invalid-cleanup-action');
var base='/media/developer/apps/usr/palm',publicRoot='/media/developer/temp';
if(input.connection==='root-ssh'){
 if(uid!==0)throw Error('root-access-required');
 publicRoot='/var/lib/clean-your-tv-installer';
}
var apps=['com.local.nativehome','com.gathin.tvhome','com.cleanyourtv.updater'];
var services=['com.local.nativehome.service','com.gathin.tvhome.renewal','com.cleanyourtv.updater.service'];
var reply={schema:1,present:[],blocked:[],root_present:[],startup_services:[],external_update_hint:null,resident_installer:false,staging_ids:input.staging_ids||[]};
if(!Array.isArray(reply.staging_ids)||reply.staging_ids.length>128||reply.staging_ids.some(function(id){return typeof id!=='string'||!/^[a-f0-9]{32}$/.test(id);}))throw Error('invalid-staging-scope');
function exists(p){try{return fs.lstatSync(p);}catch(e){if(e.code==='ENOENT')return null;throw e;}}
// Inspect fixed names without listing or following a symlinked ancestor.
function exact(p,dir){
 var parent=path.dirname(p);
 if(parent!==p&&!exact(parent,true))return null;
 var s=exists(p);if(s&&(s.isSymbolicLink()||(dir?!s.isDirectory():!s.isFile())))fail();
 return s;
}
function same(a,b){return a.dev===b.dev&&a.ino===b.ino;}
function fail(){throw Error('unsafe-path');}
var sdkContainers=[path.dirname(base),base,base+'/applications',base+'/packages',base+'/services'];
var sharedRootDirectories=sdkContainers.concat([publicRoot,'/media/developer','/media/developer/apps'],
 apps.map(function(app){return base+'/applications/'+app;}),
 services.map(function(service){return base+'/services/'+service;}));
function sharedSdkDirectory(p,s){
 var mode=s.mode&4095;
 if(s.uid===0&&mode===511&&sharedRootDirectories.indexOf(p)>=0)return true;
 // Retail SDK trees can be owned by the platform account below apps/.
 // Keep the existing packages/services compatibility for older SDK views.
 if((p===base+'/packages'||p===base+'/services')&&[1001,501].indexOf(s.uid)>=0)return true;
 return sdkContainers.indexOf(p)>=0&&s.uid===1001&&s.gid===1001&&mode===511;
}
function ancestry(p){
 for(;;){
  var s=fs.lstatSync(p);
  if(!s.isDirectory()||s.isSymbolicLink())fail();
  if(!sharedSdkDirectory(p,s)&&([0,uid,5999].indexOf(s.uid)<0||
     ((s.mode&2)&&!(s.uid===0&&(s.mode&512)))))fail();
  if(path.dirname(p)===p)break;
  p=path.dirname(p);
 }
}
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
// Catalog paths are never passed to local deletion. Only an exact project
// slot with matching package metadata is eligible for a privileged sweep.
function verifyResidue(directory,stat,app,service,area){
 ancestry(path.dirname(directory));
 function trusted(s){return s.uid===0||(s.uid===5999&&s.gid===5000);}
 if(!trusted(stat))fail();
 var file={app:'appinfo.json',package:'packageinfo.json',service:'services.json'}[area];
 at(directory,stat,function(){
  var metadata=fs.lstatSync(file);
  if(!metadata.isFile()||metadata.nlink!==1||metadata.size>65536||
     !trusted(metadata)||(metadata.mode&18))fail();
  var fd=fs.openSync(file,c.O_RDONLY|c.O_NOFOLLOW|c.O_NONBLOCK);
  try{
   if(!same(metadata,fs.fstatSync(fd)))fail();
   var bytes=new Buffer(metadata.size),offset=0;
   while(offset<bytes.length){
    var count=fs.readSync(fd,bytes,offset,bytes.length-offset,offset);
    if(!count)fail();offset+=count;
   }
   if(!same(metadata,fs.lstatSync(file))||fs.fstatSync(fd).size!==metadata.size)fail();
   var info=JSON.parse(bytes.toString('utf8'));
   if(!info||info.id!==(area==='service'?service:app))fail();
   if(area==='package'&&(info.app!==app||!Array.isArray(info.services)||
      info.services.length!==1||info.services[0]!==service))fail();
  }finally{fs.closeSync(fd);}
 });
}
function rootResidue(directory,app,service,area){
 var scope=app+' '+area;
 try{
  var stat=exact(directory,true);if(!stat)return;
  if(input.action==='sweep'){
   verifyResidue(directory,stat,app,service,area);
   remove(directory,stat);
  }
  if(exact(directory,true))reply.present.push(scope);
 }catch(e){blocked(scope,e);}
}
function developerBlocked(scope,error){blocked(scope,error);reply.blocked[reply.blocked.length-1].developer_path=true;}
function developerVisit(p,scope,app){
 var s;
 try{
  s=exact(p,!!app);if(!s)return true;
  if(app&&input.action==='inventory'){
   ancestry(path.dirname(p)); // Keep the existing foreign-ancestor checks.
   if([0,uid,5999,501,1001].indexOf(s.uid)<0)fail();
   if(reply.footprints.indexOf(app)<0)reply.footprints.push(app);
   var parent=fs.lstatSync(path.dirname(p)),groups=process.getgroups();
   var permits=function(stat,bits){
    var shift=stat.uid===uid?6:groups.indexOf(stat.gid)>=0?3:0;
    return ((stat.mode>>shift)&bits)===bits;
   };
   if((!permits(s,7)||!permits(parent,3))&&reply.protected_targets.indexOf(app)<0)
    reply.protected_targets.push(app);
  }
  if(input.action==='sweep')remove(p,s);
  if(!exact(p,!!app))return true;
  reply.present.push(scope);
 }catch(e){
  if(!app&&!s&&(e.code==='EACCES'||e.code==='EPERM'))reply.legacy_registrations_unverified=true;
  else developerBlocked(scope,e);
 }
}
function rootHint(p,scope){try{if(exists(p))reply.root_present.push(scope);}catch(e){if(e.code==='EACCES')reply.root_present.push(scope);else blocked(scope,e);}}
// Every boot identity/proof rule lives in the shared host-bundled contract.
if(input.action.indexOf('boot-')===0){
 var bootReply=bootProof.run(input,function(step,directory){cleanupStep=step;if(directory)cleanupDirectory=directory;});
 Object.keys(bootReply).forEach(function(key){reply[key]=bootReply[key];});
 process.stdout.write(JSON.stringify(reply));return;
}
if(input.action==='root-package'){
 if(uid!==0||apps.concat(['com.cleanyourtv.root.preview','com.cleanyourtv.root.updater','com.cleanyourtv.system.updater']).indexOf(input.app)<0)throw Error('invalid-root-package');
 var service=input.app==='com.gathin.tvhome'?'com.gathin.tvhome.renewal':input.app+'.service';
 visit(base+'/applications/'+input.app,input.app+' app');visit(base+'/services/'+service,input.app+' service');visit(base+'/packages/'+input.app,input.app+' package');
 process.stdout.write(JSON.stringify(reply));return;
}
['clean-your-tv-root','clean-your-tv-installation','clean-your-tv-python','clean-your-tv-root-updater','clean-your-tv-system-updater'].forEach(function(name){rootHint('/var/lib/'+name,name);});
rootHint('/var/webos-profile/override/clean-your-tv-root.json','root-profile');
services.slice(0,2).forEach(function(service){
 if(input.guard_owner){
  try{if(exact(base+'/services/'+service+'/service.js',false))reply.startup_services.push(service);}
  catch(e){developerBlocked('startup-service '+service,e);}
  return;
 }
 try{var dir=base+'/services/'+service,s=exists(dir);if(s&&s.isDirectory()){ancestry(path.dirname(dir));at(dir,s,function(){var source=exists('service.js');if(source&&source.isFile())reply.startup_services.push(service);});}}catch(e){blocked('startup-service '+service,e);}});
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
var rootInstaller='/var/lib/clean-your-tv-installer', rootPrivate=rootInstaller+'/private';
if(uid===0)installerRoots.push('/tmp/.cytv-installer-root',rootInstaller);
else installerRoots.push('/.cytv-installer');
function privateInstaller(root){
 if(root===rootInstaller)root=rootPrivate;
 if(root!=='/.cytv-installer'&&root!==rootPrivate)return;
 var s=exists(root);if(!s)return;
 if(!s.isDirectory()||s.isSymbolicLink()||s.uid!==uid||(s.mode&4095)!==448)fail();
 for(var p=root;;p=path.dirname(p)){
  var parent=fs.lstatSync(p);
  if(!parent.isDirectory()||parent.isSymbolicLink()||(parent.uid!==0&&parent.uid!==uid)||
     ((parent.mode&18)&&!(parent.uid===0&&(parent.mode&512)))||
     (root===rootPrivate&&parent.uid!==0))fail();
  if(path.dirname(p)===p)break;
 }
}
if(input.guard_owner){
 try{
  var selected=input.cancellation, owned=null, hasOwner=false;
  // Check all other roots first. A cancellation can publish a marker only
  // inside the exact inherited reservation, and it grants no other scope.
  installerRoots.forEach(function(root){
   var a=(root===rootInstaller?rootPrivate:root)+'/active',stat=exists(a);
   if(stat){
    ancestry(a);
    if(!fs.readdirSync(a).length)return;
    if(root!==selected){reply.owner_conflict=true;fail();}
    hasOwner=true;
   }
  });
  if(selected){
   var cancellationInput={root:selected,public_root:input.public_root,plan:input.plan,goal:input.removal,
                          finalizing:input.finalizing,retire:input.action==='history'};
   try{owned=/* CYTV_OWNED_CANCELLATION */null;}
   catch(e){
    // An absent current owner is independent of old optional evidence.
    // Do not bypass an actual staged reservation or an observed writer.
    if(hasOwner||e.cancelReservation)throw e;
    blocked('installer-private',e);owned={};
   }
   reply.cancellation=owned;
   var active=selected+'/active', current=exists(active);
   if(current&&fs.readdirSync(active).length&&(!owned.reservation||!same(current,owned.reservation))){
    reply.owner_conflict=true;fail();
   }
  }
 }catch(e){if(!reply.owner_conflict)reply.owner_unverified=true;process.stdout.write(JSON.stringify(reply));return;}
}
installerRoots.forEach(function(root){try{privateInstaller(root);var operations=(root===rootInstaller?rootPrivate:root)+'/operations';if(exists(operations)){ancestry(operations);var ids=fs.readdirSync(operations);reply.resident_installer=reply.resident_installer||ids.length>0;ids.forEach(function(id){if(/^[a-f0-9]{32}$/.test(id)&&reply.staging_ids.indexOf(id)<0)reply.staging_ids.push(id);});if(reply.staging_ids.length>128)fail();}}catch(e){blocked('installer-private',e);}});
if(input.action==='history'){
 installerRoots.forEach(function(root){try{
  privateInstaller(root);
  // Releasing the owned reservation opens ordinary installation again.
  // Retire its exact operation only, without sweeping any successor's root.
  if(input.cancellation===root){var opdir=root+'/operations/'+input.plan.operation,stat=exists(opdir);if(stat)remove(opdir,stat);}
  else if(root===rootInstaller){
   // This disjoint Root public staging root was already guarded on entry.
   var stageRoot=exists(root);
   if(stageRoot)remove(root,stageRoot);
  }else{
   if(exists(root+'/active')&&fs.readdirSync(root+'/active').length)fail();
   var operations=root+'/operations';
   if(exists(operations))fs.readdirSync(operations).forEach(function(id){
    var entry=operations+'/'+id;
    if(input.staging_ids.indexOf(id)>=0){
     if(exists(entry+'/reservation')||exists(root+'/active')&&fs.readdirSync(root+'/active').length)fail();
     remove(entry,fs.lstatSync(entry));
    }
   });
  }
  var directory=root+'/operations';
  [directory,root+'/active',root].forEach(function(name){
   try{fs.rmdirSync(name);}catch(e){if(['ENOENT','ENOTEMPTY','EEXIST'].indexOf(e.code)<0)throw e;}
  });
 }catch(e){blocked('installer-private',e);}});
 process.stdout.write(JSON.stringify(reply));return;
}
if(input.action==='idle'){
 // File absence alone cannot prove that a deleted service or installer stopped.
 var prefixes=installerRoots.concat([publicRoot+'/cytv-', '/var/lib/clean-your-tv-', '/tmp/cytv-', '/tmp/clean-your-tv-']);
 apps.forEach(function(app,index){prefixes.push(base+'/applications/'+app,base+'/services/'+services[index]);});
 var afterStop=input.after_stop===true,waitForIdle=input.wait_for_idle===true,idleDeadline=Date.now()+8000;
 var hasNoUserspace=function(directory){
  var stat=fs.readFileSync(directory+'/stat','utf8'),close=stat.lastIndexOf(')');
  if(close<0)return false;
  var fields=stat.slice(close+1).trim().split(/\s+/);
  // State (field 3) and flags (field 9, PF_KTHREAD) from proc_pid_stat.
  return fields[0]==='Z'||fields[0]==='X'||(Number(fields[6])&0x00200000)!==0;
 };
 var readProcLink=function(file,args,argc){
  try{args.push(fs.readlinkSync(file).replace(/ \(deleted\)$/,''));}
  catch(e){
   if(e.code==='ENOENT')return;
   // After startup shutdown, the readable command
   // line identifies project invocations even if Linux restricts these links.
   if(afterStop&&(e.code==='EACCES'||e.code==='EPERM')&&
      (argc>0||hasNoUserspace(path.dirname(file))))return;
   throw e;
  }
 };
 var isProject=function(args){
  var shell=args.length&&/(^|\/)(sh|ash|bash|dash|zsh|ksh)$/.test(args[0]);
  return args.some(function(arg){return apps.concat(services).indexOf(arg)>=0||prefixes.some(function(prefix){return arg===prefix||arg.indexOf(prefix+'/')===0||(/[-]$/.test(prefix)&&arg.indexOf(prefix)===0)||(shell&&arg.indexOf(prefix)>=0);})||(shell&&apps.some(function(app){return arg.indexOf(app)>=0;}));});
 };
 var packageSender=function(args,prefix){
  return args.some(function(arg){return arg.indexOf(prefix)===0;})&&
   args.some(function(request){try{return apps.indexOf(JSON.parse(request).id)>=0;}catch(e){return false;}});
 };
 var isInstaller=function(args){
  return args.some(function(arg){return installerRoots.some(function(root){
   return arg===root||arg.indexOf(root+'/')===0;});})||
   args.some(function(arg){return arg.indexOf('no-root-original-stream-v1')>=0&&
    /"command":"(?:start|prepare|worker|upload-artifact|upload-configuration|config-claim|config-result|release)"/.test(arg);})||
   args.some(function(arg){return arg===services[2]||arg.indexOf(base+'/services/'+services[2])===0;})||
   packageSender(args,'luna://com.webos.appInstallService/dev/');
 };
 var checkIdle=function(){
  reply.idle=true;
  reply.project_running=false;
  reply.installer_running=false;
  // Keep observed Homebrew activity even if it exits during this poll.
  try{var proc='/proc/',pids=fs.readdirSync(proc).filter(function(pid){return /^[1-9][0-9]*$/.test(pid)&&Number(pid)!==process.pid;});
   if(pids.length>4096)reply.idle=false;
   pids.forEach(function(pid){try{
    var args=fs.readFileSync(proc+pid+'/cmdline','utf8').split('\0').filter(Boolean),argc=args.length;
    var homebrew=packageSender(args,'luna://org.webosbrew.hbchannel.service/install');
    var own=homebrew||isInstaller(args);if(own)reply.installer_running=true;
    if(homebrew)reply.homebrew_observed=true;
    if(isProject(args)||own){reply.project_running=true;reply.idle=false;return;}
    readProcLink(proc+pid+'/exe',args,argc);
    readProcLink(proc+pid+'/cwd',args,argc);
    var own=isInstaller(args);if(own)reply.installer_running=true;
    if(isProject(args)||own){reply.project_running=true;reply.idle=false;return;}
    // Known LS2 launcher with an explicit service ID. Project IDs and
    // project paths were already checked above.
    var serviceLauncher=afterStop&&argc===3&&/(^|\/)node$/.test(args[0])&&
     args[1]==='/usr/bin/run-js-service'&&/^[a-zA-Z0-9_-]+(?:[.][a-zA-Z0-9_-]+)+$/.test(args[2]);
    // Interpreter flags do not establish the script's identity.
    if(!serviceLauncher&&args.some(function(arg){return /(^|\/)(node|python[0-9.]*)$/.test(arg);})&&
       (argc<2||!/^\/.*[.](js|cjs|mjs|py|pyc)$/.test(args[1])))reply.idle=false;
   }catch(e){if(e.code!=='ENOENT'||exists(proc+pid))reply.idle=false;}});
  }catch(e){reply.idle=false;}
  // Calling disable can temporarily activate an LS2 service. Wait for its
  // process to exit without calling disable again while polling.
  if(waitForIdle&&reply.project_running&&Date.now()<idleDeadline){
   setTimeout(checkIdle,250);return;
  }
  process.stdout.write(JSON.stringify(reply));
 };
 checkIdle();return;
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
 try{s=input.guard_owner?exact(state,true):exists(state);}
 catch(e){if(input.guard_owner)developerBlocked('helper-control',e);else blocked('helper-control',e);}
 if(s)try{
  helperState(state);
  (function(){
   /* CYTV_HELPER_STORAGE_LOADER */
   try{load('./state-permissions').requestStop(state,{legacyCleanup:true,expectedDirectory:s});}
   catch(error){
    // Only the canonical refusal for this exact leaf can take the restart path.
    // Other Stop failures (including generation/latch failures) still block.
    var event=error.contractEvents&&error.contractEvents[0];
    if(!event||event.field!=='control'||event.expected!=='single-regular-file'||
       !at(state,s,function(){
        var control=exists('control.json');
        return control&&control.isDirectory();
       }))throw error;
    reply.invalid_stop_record=true;
   }
  }());
 }catch(e){blocked('helper-control',e);}
 var deadline=Date.now()+8000;
 var stopped=function(){var running=false;
  try{
   var pidFile=state+'/controller.pid',pidStat=input.guard_owner&&!exact(state,true)?null:exists(pidFile);
   if(pidStat){
    helperState(state);
    if(pidStat.isDirectory()||(pidStat.isFile()&&pidStat.nlink===1&&pidStat.size>32)){
     reply.invalid_stop_record=true;
    }else{
     if(!pidStat.isFile()||pidStat.nlink!==1)fail();
     var text=fs.readFileSync(pidFile,'utf8').trim();
     if(!/^[1-9][0-9]{0,8}$/.test(text))reply.invalid_stop_record=true;
     else try{
      var args=fs.readFileSync('/proc/'+text+'/cmdline','utf8').split('\0');
      if(args[0]===apps[0]||args.indexOf(base+'/applications/'+apps[0]+'/native.js')>=0){
       process.kill(Number(text),0);running=true;
      }
     }catch(e){if(e.code!=='ENOENT'&&e.code!=='ESRCH')throw e;}
    }
   }
  }
  catch(e){if(input.guard_owner)developerBlocked('helper-control',e);else blocked('helper-control',e);}
  if(running&&Date.now()<deadline){setTimeout(stopped,100);return;}
  reply.controller_running=running;process.stdout.write(JSON.stringify(reply));
 };stopped();return;
}
if(input.guard_owner){reply.footprints=[];reply.protected_targets=[];reply.legacy_registered=[];reply.legacy_registration_absent=[];}
apps.forEach(function(app,index){
 function project(p,area){
  if(input.guard_owner)developerVisit(base+p,app+' '+area,app);
  else if(input.connection==='root-ssh')rootResidue(base+p,app,services[index],area);
  else visit(base+p,app+' '+area);
 }
 project('/applications/'+app,'app');project('/packages/'+app,'package');project('/services/'+services[index],'service');
});
if(input.guard_owner){
 var legacy='/var/palm/ls2-dev',pub=legacy+'/services/pub';
 try{reply.legacy_layout=!!exact(pub,true);}
 catch(e){
  if(e.code==='EACCES'||e.code==='EPERM')reply.legacy_registrations_unverified=true;
  else developerBlocked('registrations legacy-public',e);
 }
 if(reply.legacy_layout){
  var registrations=function(folder,ids,suffix,peer){
   var dir=legacy+'/'+folder;
   try{
    if(!exact(dir,true)){if(peer)reply.legacy_registrations_unverified=true;return;}
   }catch(e){
    if(e.code==='EACCES'||e.code==='EPERM')reply.legacy_registrations_unverified=true;
    else developerBlocked('registrations '+folder,e);
    return;
   }
   ids.forEach(function(id){
    var name=id+suffix,n=reply.present.length;
    var absent=developerVisit(dir+'/'+name,'registration '+name);
    if(!peer){
     var app=apps[services.indexOf(id)];
     if(absent)reply.legacy_registration_absent.push(app);
     else if(reply.present.length>n)reply.legacy_registered.push(app);
    }
   });
  };
  registrations('services/pub',services,'.service',false);
  registrations('services/prv',services,'.service',true);
  registrations('roles/pub',apps.concat(services),'.json',true);
  registrations('roles/prv',apps.concat(services),'.json',true);
 }
}
if(!input.guard_owner)installerRoots.forEach(function(root){try{privateInstaller(root);visit(root,'installer-private');}catch(e){blocked('installer-private',e);}});
// Only fixed project registration names. Existing foreign roles/routes are not
// inferred to belong to this project merely because they reference an app.
['services.d','roles.d','client-permissions.d','api-permissions.d','manifests.d','groups.d'].forEach(function(folder){
 var dir='/var/luna-service2-dev/'+folder;
 try{if(!exists(dir))return;ancestry(dir);}catch(e){blocked('registrations '+folder,e);return;}
 // Developer Mode can search the registry without being allowed to list it.
 apps.concat(services).forEach(function(id){
  ['.json','.service','.app.json','.api.json','.group.json','.groups.json','.manifest.json','.package.json','.permissions.json'].forEach(function(suffix){
   var name=id+suffix;visit(dir+'/'+name,'registration '+name);
  });
 });
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
'''.replace('/* CYTV_BOOT_PROOF_CONTRACT */', trusted_source('boot-proof')).replace(
    '/* CYTV_HELPER_STORAGE_LOADER */', node_loader(('state-permissions', 'contract-events')))


def _program(request):
    # Keep the SSH exec request tiny; old TV SSH servers reject long argv.
    source = PRIVATE_CLEANUP_PROGRAM
    if request.get('cancellation'):
        from .no_root_cancellation import SOURCE
        source = source.replace('/* CYTV_OWNED_CANCELLATION */null', SOURCE)
    if request.get('action') in CLEANUP_BOOT_ACTIONS:
        # Semantic failure envelope follows the observer protocol: SSH completion
        # is not cleanup success. The host refuses it before using any proof.
        source = "try {\n" + source + r"""
} catch(error) {
 function category(value,allowed){return typeof value==='string'&&allowed.indexOf(value)>=0?value:'unknown';}
 var detail={step:cleanupStep,failure:'runtime-error',
  exception_name:category(error&&error.name,NAMES),exception_code:category(error&&error.code,CODES),
  filesystem_operation:category(error&&error.syscall,OPERATIONS),
  reason:category(error&&error.message,['unsafe-path','invalid-boot-identity','invalid-cleanup-action','invalid-staging-scope','kernel-boot-unchanged'])};
 if(cleanupDirectory){
  detail.directory_mode=('0000'+(cleanupDirectory.mode&4095).toString(8)).slice(-4);
  detail.directory_owner=cleanupDirectory.uid===0?'root':cleanupDirectory.uid===process.getuid()?'current-user':'other';
  detail.directory_type=cleanupDirectory.isSymbolicLink()?'symlink':cleanupDirectory.isDirectory()?'directory':'other';
 }
 process.stdout.write(JSON.stringify({schema:1,cleanup_error:detail}));
}
""".replace('NAMES',json.dumps(OBSERVER_EXCEPTION_NAMES)).replace('CODES',json.dumps(OBSERVER_EXCEPTION_CODES)).replace('OPERATIONS',json.dumps(OBSERVER_FILESYSTEM_OPERATIONS))
    return ('process.argv.push(' + json.dumps(json.dumps(request)) + ');\n' + source).encode()


def _device(installer, action, proof=None, *, after_stop=False, wait_for_idle=False, guard=False):
    pending = installer.store.pending(installer.profile) or {}
    request = {'action':action, 'staging_ids':pending.get('cleanup_staging_ids', []),
               'removal':pending.get('removal_operation'), 'proof':proof}
    if guard and installer.profile.get('connection') != 'root-ssh':
        from . import no_root_observer
        from .errors import connection_interrupted
        request['guard_owner'] = True
        previous = pending.get('previous')
        if (isinstance(previous, dict) and previous.get('recovery_protocol') == no_root_observer.PROTOCOL
                and previous.get('action') == 'install'):
            try:
                plan = no_root_observer.capsule(installer, previous)['plan']
            except UserError as error:
                if error.reason_code != 'pending-operation' or connection_interrupted(error):
                    raise
            else:
                request.update(cancellation=no_root_observer.private_root(plan), plan=plan,
                               public_root=no_root_observer.PUBLIC_ROOT,
                               finalizing=pending.get('stage') == 'verified-clean')
    if after_stop:
        request['after_stop'] = True
    if wait_for_idle:
        request['wait_for_idle'] = True
    if installer.profile.get('connection') == 'root-ssh':
        request['connection'] = 'root-ssh'
    try:
        raw = installer.remote.run('/usr/bin/node', data=_program(request), timeout=90)
    except (UserError, OSError) as error:
        if action in CLEANUP_BOOT_ACTIONS:
            error.no_root_cleanup = no_root_cleanup_details({'action':action,
                'failure':'command-failed' if isinstance(error,TVCommandError) else 'transport-error'})
        raise
    value = json.loads(raw)
    if isinstance(value,dict) and value.get('schema') == 1 and 'cleanup_error' in value:
        detail = value['cleanup_error'] if type(value['cleanup_error']) is dict else {}
        detail = no_root_cleanup_details(dict(detail,action=action))
        storage_full = detail.get('exception_code') in ('ENOSPC', 'EDQUOT')
        error = UserError(TV_STORAGE_FULL if storage_full else 'Removal could not be verified. Review recovery options before continuing.',
                          reason_code='tv-storage-full' if storage_full else 'pending-operation')
        error.no_root_cleanup = detail
        raise error
    if (not isinstance(value, dict) or value.get('schema') != 1 or
            not all(isinstance(value.get(k), list) for k in ('present', 'blocked', 'root_present'))):
        raise UserError('Removal could not be verified. Review recovery options before continuing.')
    if value.get('owner_conflict'):
        raise UserError('Another installer owns the TV reservation. Wait for it to finish and try again.',
                        reason_code='original-writer-active')
    if value.get('owner_unverified'):
        raise UserError('The current TV installer reservation could not be verified. Recovery data was kept.',
                        reason_code='ownership-conflict')
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


def _blocked_area(row):
    prefix, _, suffix = row.get('scope', '').partition(' ')
    if prefix in APPS:
        return suffix
    return {'startup-service': 'service', 'registration': 'ls2-registration',
            'registrations': 'ls2-registry', 'helper-control': 'helper-state',
            'installer-private': 'installer-private'}.get(prefix)


def _check_access(value, defer_packages=False, *, action='inventory', guard=False):
    optional = ('installer-staging', 'installer-private') if guard else ('installer-staging',)
    blocked = [row for row in value['blocked'] if row.get('scope') not in optional
               and not (defer_packages and (_protected_package(row) or
                        row.get('developer_path') and row.get('reason') == 'permission-denied'))]
    access_denied = [row for row in blocked if row.get('reason') == 'permission-denied']
    root_required = value['root_present'] or any(not row.get('developer_path') for row in access_denied)
    if root_required or access_denied:
        error = (UserError(ROOT_MESSAGE, reason_code='root-access-required') if root_required else
                 UserError('Developer Mode could not verify removal of some project files. Save a diagnostic report from Recovery options.',
                           reason_code='cleanup-check-failed'))
        if action == 'sweep' or not root_required:
            areas = ['root-location'] if value['root_present'] else []
            areas.extend(_blocked_area(row) for row in access_denied)
            error.no_root_cleanup = no_root_cleanup_details({'action': action, 'blocked_areas': areas})
        raise error
    if blocked:
        error = UserError('Some project paths changed. Close other installers, then review recovery options.')
        error.no_root_cleanup = no_root_cleanup_details({
            'action': action, 'reason': 'unsafe-path',
            'blocked_areas': [_blocked_area(row) for row in blocked],
        })
        raise error


def _exact_developer_app(installer, app):
    uri = 'com.webos.applicationManager/getAppInfo'
    try:
        result = installer.remote.luna(uri, {'id': app}, timeout=5)
    except (TVRejected, ValueError):
        return False
    except UserError as error:
        if error.reason_code == 'operation-timeout' or str(error) == 'TV command ended without a confirmed result. Run cytv status.':
            return False
        raise
    info = result.get('appInfo') if isinstance(result, dict) and result.get('returnValue') is True else None
    if not isinstance(info, dict) or not isinstance(info.get('id'), str) or not isinstance(info.get('folderPath'), str):
        return False
    if (result.get('appId', app) != app or info.get('id') != app or
            info.get('folderPath') not in (f'/media/developer/apps/usr/palm/applications/{app}',
                                           f'/media/developer/apps/usr/palm/applications/{app}/')):
        raise UserError('The TV returned a different application location. Recovery data was kept.',
                        reason_code='cleanup-check-failed')
    return True


def _has_developer_target(observation, app):
    return (app in observation.get('protected_targets', ()) or
            app in observation.get('footprints', ()) and app in observation.get('legacy_registered', ()))


def _remove_package(installer, app):
    from .transport import terminal_reply
    uri = 'com.webos.appInstallService/dev/remove'
    try:
        reply = installer.remote.luna(uri, {'id': app, 'subscribe': True}, terminal='removed', timeout=150)
        if (not isinstance(reply, dict) or not terminal_reply(reply, 'removed', uri)
                or reply.get('id', app) != app or reply.get('details', {}).get('id', app) != app):
            raise UserError('The TV package result could not be verified.', reason_code='removal-failed')
    except TVRejected as error:
        error.args = ('The TV package result could not be verified. Review recovery options before continuing.',)
        error.reason_code = 'removal-failed'
        raise


def _input_request(installer, method, payload):
    try:
        return installer.remote.luna('com.webos.service.eim/' + method, payload)
    except (TVRejected, ValueError):
        return {}
    except UserError as error:
        if error.reason_code != 'operation-timeout' and str(error) not in (
                'TV operation timed out. Run cytv status before retrying.',
                'TV command ended without a confirmed result. Run cytv status.'):
            raise
        _device(installer, 'inventory')
        return {}


def _input_absent(installer, *, fallback=True):
    devices = _input_request(installer, 'getAllInputStatus', {}).get('devices')
    if not isinstance(devices, list) or not all(isinstance(row, dict) and
            (isinstance(row.get('id'), str) or isinstance(row.get('appId'), str)) for row in devices):
        return fallback
    return not any(row.get('appId') == APPS[1] or row.get('id') == APPS[1] for row in devices)


def _remove_input_shortcut(installer):
    """A fixed owned delete can succeed even when the optional list API fails."""
    return (_input_absent(installer, fallback=False)
            or _input_request(installer, 'deleteDevice', {'appId': APPS[1]}).get('returnValue') is True)


def restore_stock_home(installer):
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
        raise UserError('Removal could not be verified. Review recovery options before continuing.', reason_code='controls-unverified')
    stock={'com.webos.app.home','com.webos.app.livetv',
           'com.webos.app.hdmi1','com.webos.app.hdmi2','com.webos.app.hdmi3','com.webos.app.hdmi4'}
    message = 'Removal could not be verified. Review recovery options before continuing.'
    method = uri + 'getForegroundAppInfo'
    with ExitStack() as connection:
        paired = None

        def foreground(timeout=5):
            nonlocal paired
            if paired is None:
                try:
                    reply = installer.remote.luna(method, {}, timeout=timeout)
                except TVRejected as error:
                    if (installer.profile.get('connection') == 'root-ssh'
                            or error.luna.get('error_code') != -1
                            or error.luna.get('return_value') is not False):
                        raise
                    from websockets.exceptions import WebSocketException
                    from .tv import SSAP
                    profile = installer.profile
                    try:
                        paired = connection.enter_context(SSAP(profile['host'], installer.store.device_dir(profile),
                                                               installer.progress, reuse_only=True))
                    except (OSError, ValueError, UserError, WebSocketException) as exc:
                        raise UserError(message, reason_code='controls-unverified') from exc
            if paired is not None:
                try:
                    reply = paired.call('ssap://' + method, timeout=timeout)
                except (OSError, ValueError, UserError) as exc:
                    raise UserError(message, reason_code='controls-unverified') from exc
            app = None
            if isinstance(reply, dict):
                accepted = reply.get('returnValue', paired is not None) is True
                if accepted and not reply.get('pairingType'):
                    app = reply.get('appId')
            if not isinstance(app, str) or not app:
                raise UserError(message, reason_code='controls-unverified')
            return app

        if foreground() in stock:
            return
        # Fixed built-in source only; require foreground confirmation after launch.
        launched = installer.remote.luna(uri+'launch', {'id':'com.webos.app.livetv'})
        if not isinstance(launched, dict) or launched.get('returnValue') is not True:
            raise UserError(message, reason_code='controls-unverified')
        deadline = monotonic() + 5
        while (remaining := deadline - monotonic()) > 0:
            if foreground(remaining) in stock:
                return
            sleep(min(.1, remaining))
        raise UserError(message, reason_code='controls-unverified')


def continue_removal(installer, expected_pending):
    pending = installer.store.pending(installer.profile)
    if pending != expected_pending or not pending or pending.get('recovery_protocol') != 'clean-removal-v1':
        raise UserError('Removal evidence changed. Recovery data was kept.', reason_code='pending-operation')
    previous = pending.get('previous')
    legacy_install = (isinstance(previous, dict) and previous.get('action') == 'install'
                      and previous.get('stage') == 'pending' and 'recovery_protocol' not in previous)
    profile = installer.profile
    store = installer.store
    guard = profile.get('connection') != 'root-ssh'

    terminals_this_pass = set()
    surviving_registrations = set()

    def device(action, **options):
        value = _device(installer, action, guard=guard, **options)
        if guard and action in ('inventory', 'sweep'):
            # Track only public registration leaves observed after this pass's
            # vendor terminal. A hidden directory cannot refute that evidence.
            surviving_registrations.update(terminals_this_pass.intersection(value.get('legacy_registered', ())))
            surviving_registrations.difference_update(value.get('legacy_registration_absent', ()))
        return value

    def check(value, **options):
        _check_access(value, guard=guard, **options)

    def wait_for_stopped_processes(require_idle, *, verify_after_remove=False):
        idle = device('idle', after_stop=True, wait_for_idle=True)
        check(defer_catalogued_paths(idle) if not verify_after_remove else idle,
              defer_packages=True, action='idle')
        if idle.get('project_running') is True:
            raise UserError('A Clean Your TV process did not stop in time. Removal data was kept.',
                            reason_code='cleanup-check-failed')
        return idle.get('project_running') is False and (not require_idle or idle.get('idle') is True)

    # The fixed IDs from this goal's package requests still need readback
    # if a vendor request changes the SDK's public legacy view.
    sam_readback = {app for app in APPS if app in pending.get('removals', {})}

    def check_surviving_registrations():
        if surviving_registrations:
            error = UserError('Removal could not verify that a remaining service registration was cleared.',
                              reason_code='cleanup-check-failed')
            error.no_root_cleanup = no_root_cleanup_details({'action': 'sweep', 'blocked_areas': ['ls2-registration']})
            raise error

    def verify_functional(require_idle):
        final = device('inventory')
        check(final)
        check_surviving_registrations()
        remaining = [scope for scope in final['present']
                     if scope != 'installer-staging' and not scope.startswith('installer-staging ')]
        catalog_remains = {app['id'] for app in installer.installed_apps()}.intersection(APPS)
        sam_apps = APPS if final.get('legacy_layout') else sam_readback
        if remaining or catalog_remains or (guard and any(
                _exact_developer_app(installer, app) for app in APPS if app in sam_apps)):
            raise UserError('Final cleanup could not be verified. Review recovery options before continuing.',
                            reason_code='cleanup-check-failed')
        return final, wait_for_stopped_processes(require_idle, verify_after_remove=True)

    def finish(result):
        from .root_no_root_handoff import release
        if guard:
            history = device('history')
            if history['blocked']:
                result = dict(result, temporary_files_retained=True)
                store.checkpoint(profile, result=result)
                installer.progress('Some temporary recovery files were kept.')
        if result.get('legacy_registrations_unverified'):
            installer.progress('Developer Mode could not inspect all legacy service registration directories.')
        release(installer)
        store.finish_clean_removal(profile)
        return result

    if pending.get('stage') == 'verified-clean':
        _, stopped = verify_functional(not guard or pending.get('removal_reason') in (
            'original-writer-active', 'ownership-conflict', 'cleanup-check-failed'))
        if not stopped or (guard and not _input_absent(installer)):
            raise UserError('TV controls could not be verified. Recovery data was kept.', reason_code='controls-unverified')
        return finish(pending['result'])

    def catalog():
        app_info = installer.installed_apps()
        apps = {app['id'] for app in app_info}
        if apps.intersection(('com.cleanyourtv.root.preview', 'com.cleanyourtv.root.updater',
                              'com.cleanyourtv.system.updater')):
            raise UserError(ROOT_MESSAGE, reason_code='root-access-required')
        # An older cytv may have left an inert cleanup package registered.
        carriers = {app['id'] for app in app_info
                    if app.get('title') == 'Clean Your TV cleanup' and app.get('visible') is False}
        return apps, carriers

    if not guard:
        apps, carriers = catalog()

    def defer_catalogued_paths(value):
        if guard:
            return value
        # A rejected local probe does not invalidate an LG catalog entry.
        # Keep the original observation for service shutdown and recheck
        # remaining paths after the vendor removal has finished.
        covered = {'startup-service ' + service for app, service in zip(APPS, STARTUP_SERVICES)
                   if app in apps}
        covered.update(app + ' ' + area for app in apps.intersection(APPS)
                       for area in ('app', 'package', 'service'))
        return dict(value, blocked=[row for row in value['blocked'] if row.get('scope') not in covered])

    current = device('inventory')
    check(defer_catalogued_paths(current), defer_packages=True)
    store.checkpoint(profile, cleanup_staging_ids=current['staging_ids'])

    proof = pending.get('cleanup_boot_proof')
    boot_triggers = pending.get('cleanup_restart_triggers', [])
    reused_restart = proof is not None and pending.get('cleanup_boot_verified') is True
    restarted = reused_restart
    new_kernel = reused_restart
    if proof is not None and not reused_restart and not pending.get('cleanup_boot_release_started'):
        boot = _device(installer, 'boot-probe', proof=proof)
        new_kernel = boot.get('boot_id') not in (None, proof.get('kernel'))
        critical = set(boot_triggers) & {
            'package-removal-unverified', 'original-configuration-unverified',
            'original-package-unverified', 'homebrew-request-unverified', 'catalog-helper-stop-unverified'}
        restarted = boot['boot_restarted'] is True and (not (legacy_install or critical) or new_kernel)

    def require_restart(triggers, *, rearm=False, observed_writer=False):
        nonlocal proof
        stage = 'restart-required'
        reason = triggers[0]
        # A vendor idle observation cannot settle an independent Homebrew
        # request. A newer shared baseline still covers both outstanding scopes.
        if guard and not new_kernel and 'homebrew-request-unverified' in boot_triggers:
            triggers = ['homebrew-request-unverified', *(trigger for trigger in triggers
                                                        if trigger != 'homebrew-request-unverified')]
        if rearm and proof is not None and not pending.get('cleanup_boot_release_started'):
            _device(installer, 'boot-release', proof=proof)
        if proof is None or rearm or pending.get('cleanup_boot_release_started'):
            installer.store.checkpoint(installer.profile, stage=stage, cleanup_boot_proof=None,
                                       cleanup_boot_verified=False, cleanup_boot_release_started=False,
                                       removal_reason=stage, cleanup_restart_triggers=triggers)
            proof = _device(installer, 'boot-create')['boot_proof']
            installer.store.checkpoint(installer.profile, cleanup_boot_proof=proof)
        else:
            installer.store.checkpoint(installer.profile, stage=stage, removal_reason=stage,
                                       cleanup_restart_triggers=triggers)
        if observed_writer:
            raise UserError('A Homebrew package request was observed. Wait for it to settle before continuing.',
                            reason_code='original-writer-active')
        if (guard and pending.get('removal_reason') in ('restart-required', 'removal-terminal-unknown')
                and proof is not None and not rearm and set(triggers).issubset(boot_triggers)
                and reason in ('package-removal-unverified', 'original-configuration-unverified',
                                    'original-package-unverified', 'homebrew-request-unverified')):
            # Preserve this boot baseline. The retry UI can report the current
            # unresolved request without sending the same power-cycle steps.
            store.checkpoint(profile, stage='package-removal', removal_reason='removal-terminal-unknown')
            raise UserError('The TV still has an unconfirmed earlier request. Try again after it settles or the TV fully restarts.',
                            reason_code='removal-terminal-unknown')
        installer.progress(RESTART_MESSAGE)
        return {'removed': False, 'verified_clean': False, 'restart_required': True}

    if pending.get('stage') == 'restart-required':
        store.checkpoint(profile, stage='requested', removal_reason='removal-recheck-required')
    resident = current.get('resident_installer') is True
    cancellation = current.get('cancellation', {})
    if guard:
        writers = device('idle', after_stop=True, wait_for_idle=True)
        if writers.get('homebrew_observed') is True:
            return require_restart(['homebrew-request-unverified'], observed_writer=True,
                                   rearm=proof is not None and (new_kernel or
                                       'homebrew-request-unverified' not in pending.get('cleanup_restart_triggers', [])))
        if writers.get('installer_running') is True:
            raise UserError('An original TV operation is still running. Wait and try again.',
                            reason_code='original-writer-active')

    # The optional monitor can settle older requests. The first supported
    # fixed-ID remove has its own terminal, even without monitoring privilege.
    removals = dict(pending.get('removals', {}))
    submitted = {app for app in APPS if removals.get(app) == 'submitted'}
    uncertain_install = previous is not None or resident
    package_idle = False
    if uncertain_install or submitted:
        from .operations import require_removal_idle
        deadline = monotonic() + 20
        waiting = False
        while True:
            try:
                observed_idle = require_removal_idle(
                    installer.remote, profile, pending, report_busy=True,
                    optional_monitor=guard)
            except TVRejected as error:
                if not error.package_status_denied:
                    raise
            except UserError as error:
                if error.reason_code != 'original-writer-active':
                    raise
                if not waiting:
                    installer.progress('Waiting for the original TV operation…')
                    waiting = True
                remaining = deadline - monotonic()
                if remaining <= 0:
                    raise
                sleep(min(1, remaining))
                continue
            else:
                package_idle = observed_idle is not False
            break

    if guard:
        # The drain and package-manager wait can finish an old registration.
        # Read current paths and exact package IDs before changing controls.
        if uncertain_install or submitted or 'cancellation' in writers:
            current = device('inventory')
            check(current, defer_packages=True)
            store.checkpoint(profile, cleanup_staging_ids=current['staging_ids'])
            cancellation = current.get('cancellation', {})
    if guard or uncertain_install or submitted:
        apps, carriers = catalog()

    def nominated(observation, app):
        footprint = _has_developer_target(observation, app)
        # SAM is optional, but a positive conflicting mapping raises before
        # the vendor request, even when an exact footprint is visible.
        if footprint or observation.get('legacy_layout') or app in sam_readback:
            return _exact_developer_app(installer, app) or footprint
        return False

    targets = apps.copy()
    if guard:
        for app in APPS:
            if app not in apps and nominated(current, app):
                targets.add(app)
                sam_readback.add(app)

    configuration_pending = cancellation.get('eim_pending') or cancellation.get('launch_pending')
    configuration_settled = False
    if configuration_pending:
        # The original configuration is bound to the immutable capsule under
        # this removal goal. Save its verified settlement before another
        # request can replace the shared boot proof.
        original = previous['observer_operation']
        configuration_settled = pending.get('cleanup_original_configuration_settled') == original
        if not configuration_settled and new_kernel and 'original-configuration-unverified' in boot_triggers:
            store.checkpoint(profile, cleanup_original_configuration_settled=original)
            configuration_settled = True

    # A proof predating our new vendor request cannot settle that request.
    if submitted and not package_idle and not (new_kernel and 'package-removal-unverified' in boot_triggers):
        return require_restart(['package-removal-unverified'], rearm=proof is not None
                               and 'package-removal-unverified' not in boot_triggers)
    if configuration_pending and not configuration_settled:
        return require_restart(['original-configuration-unverified'], rearm=proof is not None
                               and 'original-configuration-unverified' not in boot_triggers)
    bound_package_pending = cancellation.get('package_pending') is True
    older_request = legacy_install or (isinstance(previous, dict)
        and (previous.get('stage') in ('submitted', 'removing') or
             isinstance(previous.get('removals'), dict) and 'submitted' in previous['removals'].values()))
    older_request = older_request or not guard and uncertain_install
    older_pending = older_request and not (package_idle or new_kernel)
    if older_pending and (not guard or not targets.intersection(APPS)):
        return require_restart(['prior-operation-unresolved'])
    original_package_settled = package_idle or new_kernel and 'original-package-unverified' in boot_triggers
    if bound_package_pending and not original_package_settled and not targets.intersection(APPS):
        return require_restart(['original-package-unverified'], rearm=proof is not None
                               and 'original-package-unverified' not in boot_triggers)
    installer.progress('Restoring TV controls…')
    stopped = device('stop')
    helper_stop_blocked = any(row.get('scope') == 'helper-control' for row in stopped['blocked'])
    helper_stop_restarted = not guard and new_kernel and 'catalog-helper-stop-unverified' in boot_triggers
    unverified_helper_stop = not guard and APPS[0] in apps and helper_stop_blocked and not helper_stop_restarted
    if unverified_helper_stop:
        return require_restart(['catalog-helper-stop-unverified'], rearm=restarted)
    stop_check = defer_catalogued_paths(stopped)
    if helper_stop_restarted:
        stop_check = dict(stop_check, blocked=[row for row in stop_check['blocked']
                                              if row.get('scope') != 'helper-control'])
    check(stop_check, defer_packages=True, action='stop')
    invalid_stop_record = stopped.get('invalid_stop_record') is True
    if invalid_stop_record:
        # A missing volatile marker alone cannot replace a failed Stop.
        if not new_kernel:
            return require_restart(['invalid-helper-stop-record'])
    unavailable = set(pending.get('cleanup_startup_unavailable', []))
    inaccessible_packages = {_protected_package(row) for row in current['blocked'] + stopped['blocked']
                             if not row.get('developer_path')}
    inaccessible_packages.discard(None)
    startup_access_blocked = not restarted and bool(inaccessible_packages - targets)
    startup_disable_unverified = False
    inaccessible_startup = ({row['scope'] for row in current['blocked'] + stopped['blocked']
                             if _protected_package(row)} if invalid_stop_record else set())
    for app, service in zip(APPS, STARTUP_SERVICES):
        catalogued = not guard and app in apps
        if ((not catalogued and service not in current['startup_services']
             and 'startup-service ' + service not in inaccessible_startup)
                or app in carriers
                or (restarted and service in unavailable and not invalid_stop_record)):
            continue
        try:
            if guard:
                device('inventory')
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
            device('inventory')
            unavailable.add(service)
            startup_disable_unverified |= invalid_stop_record or app not in targets
    if unavailable:
        installer.store.checkpoint(installer.profile, cleanup_startup_unavailable=sorted(unavailable))
    if guard:
        device('inventory')
    inputs_removed = _remove_input_shortcut(installer)
    installer.store.checkpoint(installer.profile, cleanup_inputs_pending=not inputs_removed)
    if guard:
        device('inventory')
    restore_stock_home(installer)
    installer.store.checkpoint(installer.profile, stage='controls-restored')
    external_update = current.get('external_update_hint')
    if external_update is not None:
        installer.store.checkpoint(installer.profile, previous_update_status=external_update)
    restart_triggers = []
    if startup_access_blocked:
        restart_triggers.append('protected-package-access')
    if startup_disable_unverified:
        restart_triggers.append('startup-disable-unverified')
    if not guard and external_update is not None and not restarted:
        restart_triggers.append('resident-installer-evidence')
    if invalid_stop_record and restart_triggers:
        raise UserError('Removal could not be verified. Review recovery options before continuing.', reason_code='cleanup-check-failed')
    if restart_triggers:
        return require_restart(restart_triggers, rearm=restarted)

    if not wait_for_stopped_processes(invalid_stop_record or
                                     not restarted and (uncertain_install or inaccessible_packages or unavailable)):
        if invalid_stop_record:
            raise UserError('Removal could not be verified. Review recovery options before continuing.', reason_code='cleanup-check-failed')
        return require_restart(['process-idle-unverified'], rearm=restarted)
    rejected = None
    for app, message in zip(APPS, ('Removing Helper…', 'Removing Home…', 'Removing the updater…')):
        if app not in targets:
            continue
        if removals.get(app) == 'terminal':
            if app in apps:
                raise UserError('A removed package is present again. Recovery data was kept.', reason_code='removal-failed')
            # A surviving exact footprint still needs readback or safe sweep.
            continue
        if guard:
            fresh = device('inventory')
            check(fresh, defer_packages=True)
            if app not in apps and not nominated(fresh, app):
                continue
        installer.progress(message)
        removals[app] = 'submitted'
        checkpoint = {'stage': 'package-removal', 'removals': removals}
        if guard and 'package-removal-unverified' in boot_triggers:
            # The earlier reboot can settle other work, but it predates this
            # request. Retire its vendor coverage before sending the request.
            checkpoint['cleanup_restart_triggers'] = [
                trigger for trigger in boot_triggers if trigger != 'package-removal-unverified']
        store.checkpoint(profile, **checkpoint)
        try:
            _remove_package(installer, app)
        except TVRejected as error:
            # A malformed stream can also raise TVRejected. Only a scoped,
            # definite rejection releases our submitted checkpoint.
            if not guard or error.definite_package_removal_rejection(app):
                removals.pop(app)
                store.checkpoint(profile, removals=removals)
                if app not in apps:
                    # We know this request finished. Try independent targets,
                    # but leave the failed target and its dependent sweep pending.
                    if rejected is None:
                        from .diagnostic_context import record_first_failure
                        record_first_failure(store, profile, pending, {
                            'action': 'uninstall', 'phase': 'uninstall',
                            'error_type': type(error).__name__, 'reason_code': error.reason_code,
                            'luna': error.luna,
                        })
                        rejected = error
                    continue
            raise
        removals[app] = 'terminal'
        terminals_this_pass.add(app)
        store.checkpoint(profile, removals=removals)
    if rejected:
        raise rejected
    if older_pending:
        return require_restart(['prior-operation-unresolved'])
    if 'homebrew-request-unverified' in boot_triggers and not new_kernel:
        return require_restart(['homebrew-request-unverified'])
    if bound_package_pending and not original_package_settled:
        return require_restart(['original-package-unverified'], rearm=proof is not None
                               and 'original-package-unverified' not in boot_triggers)
    if not guard and any(entry['id'] in APPS for entry in installer.installed_apps()):
        raise UserError('The TV package result could not be verified.', reason_code='removal-failed')
    installer.progress('Removing project files…')
    store.checkpoint(profile, stage='private-cleanup')
    swept = device('sweep')
    check(swept, action='sweep')
    installer.progress('Verifying removal…')
    final, process_stopped = verify_functional(not restarted or reused_restart or invalid_stop_record)
    if not process_stopped:
        return require_restart(['process-idle-unverified'], rearm=restarted)
    if guard:
        device('inventory')
        check_surviving_registrations()
        inputs_removed = _remove_input_shortcut(installer) if not inputs_removed else _input_absent(installer)
    if not inputs_removed:
        store.checkpoint(profile, removal_reason='controls-unverified')
        raise UserError('TV controls could not be verified. Review recovery options before continuing.', reason_code='controls-unverified')
    if proof is not None and not pending.get('cleanup_boot_release_started'):
        if restarted:
            store.checkpoint(profile, cleanup_boot_verified=True)
        else:
            store.checkpoint(profile, cleanup_boot_release_started=True)
        _device(installer, 'boot-retire' if restarted else 'boot-release', proof=proof)
    result = {'removed': True, 'verified_clean': True}
    if (final.get('legacy_registrations_unverified')
            or guard and current.get('legacy_layout') and not final.get('legacy_layout')):
        result['legacy_registrations_unverified'] = True
    if final['present'] or final['blocked'] or swept['blocked']:
        result['temporary_files_retained'] = True
        installer.progress('Some temporary recovery files were kept.')
    store.checkpoint(profile, stage='verified-clean', removal_reason='removal-verified', result=result)
    return finish(result)
