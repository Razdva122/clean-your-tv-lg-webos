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
if(['inventory','idle','sweep','stop','root-package','boot-create','boot-probe','boot-retire','boot-release'].indexOf(input.action)<0)throw Error('invalid-cleanup-action');
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
installerRoots.forEach(function(root){try{privateInstaller(root);var operations=(root===rootInstaller?rootPrivate:root)+'/operations';if(exists(operations)){ancestry(operations);var ids=fs.readdirSync(operations);reply.resident_installer=reply.resident_installer||ids.length>0;ids.forEach(function(id){if(/^[a-f0-9]{32}$/.test(id)&&reply.staging_ids.indexOf(id)<0)reply.staging_ids.push(id);});if(reply.staging_ids.length>128)fail();}}catch(e){blocked('installer-private',e);}});
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
   // After a new boot and confirmed startup shutdown, the readable command
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
 var checkIdle=function(){
  reply.idle=true;
  reply.project_running=false;
  try{var proc='/proc/',pids=fs.readdirSync(proc).filter(function(pid){return /^[1-9][0-9]*$/.test(pid)&&Number(pid)!==process.pid;});
   if(pids.length>4096)reply.idle=false;
   pids.forEach(function(pid){try{
    var args=fs.readFileSync(proc+pid+'/cmdline','utf8').split('\0').filter(Boolean),argc=args.length;
    if(isProject(args)){reply.project_running=true;reply.idle=false;return;}
    readProcLink(proc+pid+'/exe',args,argc);
    readProcLink(proc+pid+'/cwd',args,argc);
    if(isProject(args)){reply.project_running=true;reply.idle=false;return;}
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
  if(((afterStop&&!reply.idle)||(waitForIdle&&reply.project_running))&&Date.now()<idleDeadline){
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
 try{s=exists(state);}catch(e){blocked('helper-control',e);}
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
   var pidFile=state+'/controller.pid',pidStat=exists(pidFile);
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
'''.replace('/* CYTV_BOOT_PROOF_CONTRACT */', trusted_source('boot-proof')).replace(
    '/* CYTV_HELPER_STORAGE_LOADER */', node_loader(('state-permissions', 'contract-events')))


def _program(request):
    # Keep the SSH exec request tiny; old TV SSH servers reject long argv.
    source = PRIVATE_CLEANUP_PROGRAM
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


def _device(installer, action, proof=None, *, after_stop=False, wait_for_idle=False):
    pending = installer.store.pending(installer.profile) or {}
    request = {'action':action, 'staging_ids':pending.get('cleanup_staging_ids', []),
               'removal':pending.get('removal_operation'), 'proof':proof}
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
        error = UserError(TV_STORAGE_FULL if storage_full else 'Removal could not be checked. Reconnect and try again.',
                          reason_code='tv-storage-full' if storage_full else 'pending-operation')
        error.no_root_cleanup = detail
        raise error
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
    blocked = [row for row in value['blocked']
               if not (defer_packages and _protected_package(row))
               and row.get('scope') != 'installer-staging']
    if value['root_present'] or any(row.get('reason') == 'permission-denied' for row in blocked):
        raise UserError(ROOT_MESSAGE, reason_code='root-access-required')
    if blocked:
        raise UserError('Some project paths changed. Close other installers and try again.')


def _remove_package(installer, app):
    try:
        installer.remote.luna('com.webos.appInstallService/dev/remove', {'id': app, 'subscribe': True}, terminal='removed', timeout=150)
    except TVRejected as error:
        error.args = ('The TV rejected removal. Check the error details and try again.',)
        error.reason_code = 'removal-failed'
        raise


def _original_install_finished(installer, previous):
    from . import no_root_observer
    from .errors import connection_interrupted

    try:
        original = no_root_observer.capsule(installer, previous)
        result = no_root_observer.snapshot(installer, original)
    except UserError as error:
        if connection_interrupted(error):
            raise
        return False
    return (result['reservation'] in ('active', 'closed')
            and all(slot['terminal'] == 'success' and slot['readback'] == 'matches' and not slot.get('reason')
                    for slot in result['slots']))


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
        raise UserError('Removal could not be checked. Reconnect and try again.', reason_code='controls-unverified')
    stock={'com.webos.app.home','com.webos.app.livetv',
           'com.webos.app.hdmi1','com.webos.app.hdmi2','com.webos.app.hdmi3','com.webos.app.hdmi4'}
    message = 'Removal could not be checked. Reconnect and try again.'
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
    current = _device(installer, 'inventory')
    _check_access(current, defer_packages=True)
    installer.store.checkpoint(installer.profile, cleanup_staging_ids=current['staging_ids'])
    app_info = installer.installed_apps()
    apps = {app['id'] for app in app_info}
    # A previous cytv version may have left an inert cleanup package registered.
    carriers = {app['id'] for app in app_info if app.get('title') == 'Clean Your TV cleanup' and app.get('visible') is False}
    root_apps = apps.intersection(('com.cleanyourtv.root.preview', 'com.cleanyourtv.root.updater',
                                   'com.cleanyourtv.system.updater'))
    if root_apps:
        raise UserError(ROOT_MESSAGE, reason_code='root-access-required')
    proof = pending.get('cleanup_boot_proof')
    reused_restart = proof is not None and pending.get('cleanup_boot_verified') is True
    restarted = reused_restart
    new_kernel = reused_restart
    if proof is not None and not reused_restart and not pending.get('cleanup_boot_release_started'):
        boot = _device(installer, 'boot-probe', proof=proof)
        new_kernel = boot.get('boot_id') not in (None, proof.get('kernel'))
        restarted = boot['boot_restarted'] is True and (not legacy_install or new_kernel)

    def require_restart(triggers, *, rearm=False):
        nonlocal proof
        stage = 'restart-required'
        if rearm and proof is not None:
            _device(installer, 'boot-retire', proof=proof)
        if proof is None or rearm or pending.get('cleanup_boot_release_started'):
            installer.store.checkpoint(installer.profile, stage=stage, cleanup_boot_proof=None,
                                       cleanup_boot_verified=False, cleanup_boot_release_started=False,
                                       removal_reason=stage, cleanup_restart_triggers=triggers)
            proof = _device(installer, 'boot-create')['boot_proof']
            installer.store.checkpoint(installer.profile, cleanup_boot_proof=proof)
        else:
            installer.store.checkpoint(installer.profile, stage=stage, removal_reason=stage,
                                       cleanup_restart_triggers=triggers)
        installer.progress(RESTART_MESSAGE)
        return {'removed': False, 'verified_clean': False, 'restart_required': True}

    original_install = (isinstance(previous, dict) and previous.get('action') == 'install'
                        and previous.get('recovery_protocol') == 'no-root-original-stream-v1'
                        and 'previous' not in previous)
    resident = current.get('resident_installer') is True
    uncertain_install = previous is not None or resident
    if pending.get('stage') == 'restart-required':
        installer.store.checkpoint(installer.profile, stage='requested', removal_reason='removal-recheck-required')
    package_idle = not uncertain_install
    if uncertain_install:
        from .operations import require_removal_idle
        deadline = monotonic() + 20
        waiting = False
        while True:
            try:
                require_removal_idle(installer.remote, installer.profile, pending, report_busy=True)
            except TVRejected as error:
                if not error.package_status_denied:
                    raise
                package_idle = restarted or original_install and _original_install_finished(installer, previous)
            except UserError as error:
                if error.reason_code == 'original-writer-active':
                    if not waiting:
                        installer.progress('Waiting for the original TV operation…')
                        waiting = True
                    remaining = deadline - monotonic()
                    if remaining <= 0:
                        raise
                    sleep(min(1, remaining))
                    continue
                if error.reason_code != 'pending-operation' or restarted:
                    raise
            else:
                package_idle = True
            break
        if not package_idle:
            trigger = 'resident-installer-evidence' if resident or original_install else 'prior-operation-unresolved'
            return require_restart([trigger])
    installer.progress('Restoring TV controls…')
    stopped = _device(installer, 'stop')
    _check_access(stopped, defer_packages=True)
    invalid_stop_record = stopped.get('invalid_stop_record') is True
    if invalid_stop_record:
        # A missing volatile marker alone cannot replace a failed Stop.
        if not new_kernel:
            return require_restart(['invalid-helper-stop-record'])
    unavailable = set(pending.get('cleanup_startup_unavailable', []))
    inaccessible_packages = {_protected_package(row) for row in current['blocked'] + stopped['blocked']}
    inaccessible_packages.discard(None)
    startup_access_blocked = not restarted and bool(inaccessible_packages - apps)
    startup_disable_unverified = False
    inaccessible_startup = ({row['scope'] for row in current['blocked'] + stopped['blocked']
                             if _protected_package(row)} if invalid_stop_record else set())
    for app, service in zip(APPS, ('com.local.nativehome.service', 'com.gathin.tvhome.renewal')):
        if ((service not in current['startup_services'] and 'startup-service ' + service not in inaccessible_startup)
                or app in carriers
                or (restarted and service in unavailable and not invalid_stop_record)):
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
            startup_disable_unverified |= invalid_stop_record or app not in apps
    if unavailable:
        installer.store.checkpoint(installer.profile, cleanup_startup_unavailable=sorted(unavailable))
    inputs_removed = _remove_input_shortcut(installer)
    installer.store.checkpoint(installer.profile, cleanup_inputs_pending=not inputs_removed)
    restore_stock_home(installer)
    installer.store.checkpoint(installer.profile, stage='controls-restored')
    external_update = current.get('external_update_hint')
    if external_update is not None:
        installer.store.checkpoint(installer.profile, previous_update_status=external_update)
    restart_triggers = []
    if stopped.get('controller_running'):
        restart_triggers.append('controller-still-running')
    if startup_access_blocked:
        restart_triggers.append('protected-package-access')
    if startup_disable_unverified:
        restart_triggers.append('startup-disable-unverified')
    if external_update is not None and not restarted:
        restart_triggers.append('resident-installer-evidence')
    if invalid_stop_record:
        if restart_triggers or _device(installer, 'idle', after_stop=True).get('idle') is not True:
            raise UserError('Removal could not be checked. Reconnect and try again.', reason_code='cleanup-check-failed')
    elif restart_triggers:
        return require_restart(restart_triggers, rearm=restarted)
    else:
        idle = _device(installer, 'idle', wait_for_idle=True)
        _check_access(idle, defer_packages=True)
        needs_full_idle = not restarted and (uncertain_install or inaccessible_packages or unavailable)
        if idle.get('project_running') is not False or (needs_full_idle and idle.get('idle') is not True):
            return require_restart(['process-idle-unverified'], rearm=restarted)
    for app, message in zip(APPS, ('Removing Helper…', 'Removing Home…', 'Removing the updater…')):
        if app not in apps:
            continue
        installer.progress(message)
        installer.store.checkpoint(installer.profile, stage='package-removal')
        _remove_package(installer, app)
    installer.progress('Removing private recovery data…')
    installer.store.checkpoint(installer.profile, stage='private-cleanup')
    _check_access(_device(installer, 'sweep'))
    installer.progress('Verifying removal…')
    final = _device(installer, 'inventory')
    _check_access(final)
    remaining = [scope for scope in final['present']
                 if scope != 'installer-staging' and not scope.startswith('installer-staging ')]
    if remaining or {app['id'] for app in installer.installed_apps()}.intersection(APPS):
        raise UserError('Some project files remain. Try again to finish removal.')
    idle = _device(installer, 'idle', after_stop=invalid_stop_record, wait_for_idle=True)
    if idle.get('project_running') is not False or ((not restarted or reused_restart or invalid_stop_record)
                                                  and idle.get('idle') is not True):
        return require_restart(['process-idle-unverified'], rearm=restarted)
    if not inputs_removed:
        installer.store.checkpoint(installer.profile, removal_reason='controls-unverified')
        raise UserError('TV input shortcuts could not be checked. Try again.', reason_code='controls-unverified')
    if proof is not None and not pending.get('cleanup_boot_release_started'):
        if restarted:
            installer.store.checkpoint(installer.profile, cleanup_boot_verified=True)
        else:
            installer.store.checkpoint(installer.profile, cleanup_boot_release_started=True)
        _device(installer, 'boot-retire' if restarted else 'boot-release', proof=proof)
    result = {'removed': True, 'verified_clean': True}
    if final['present'] or final['blocked']:
        result['temporary_files_retained'] = True
        installer.progress('Some temporary files were kept; they do not prevent reinstallation.')
    installer.store.checkpoint(installer.profile, stage='verified-clean', removal_reason='removal-verified',
                               result=result)
    from .root_no_root_handoff import release
    release(installer)
    installer.store.finish_clean_removal(installer.profile)
    return result
