"""Explicit project removal with an ordinary reconnect/full-restart continuation.

Old installation receipts describe history. They are not permission to retain
the user's project keys or files after the user has requested their removal.
"""
import json
import shlex

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
if(['inventory','sweep','stop'].indexOf(input.action)<0)throw Error('invalid-cleanup-action');
var base='/media/developer/apps/usr/palm',publicRoot='/media/developer/temp';
var apps=['com.local.nativehome','com.gathin.tvhome','com.cleanyourtv.updater'];
var services=['com.local.nativehome.service','com.gathin.tvhome.renewal','com.cleanyourtv.updater.service'];
var reply={schema:1,boot_id:fs.readFileSync('/proc/sys/kernel/random/boot_id','utf8').trim(),present:[],blocked:[],root_present:[],external_update_hint:null,resident_installer:false};
if(!/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/.test(reply.boot_id))throw Error('invalid-boot-identity');
function exists(p){try{return fs.lstatSync(p);}catch(e){if(e.code==='ENOENT')return null;throw e;}}
function same(a,b){return a.dev===b.dev&&a.ino===b.ino;}
function fail(){throw Error('unsafe-path');}
function ancestry(p){for(;;){var s=fs.lstatSync(p);if(!s.isDirectory()||s.isSymbolicLink()||[0,uid,5999].indexOf(s.uid)<0||((s.mode&2)&&!(s.uid===0&&(s.mode&512))))fail();if(path.dirname(p)===p)break;p=path.dirname(p);}}
function at(p,expected,fn){
 var before=fs.lstatSync(p),fd=fs.openSync(p,c.O_RDONLY|c.O_DIRECTORY|c.O_NOFOLLOW),prior=process.cwd(),priorStat=fs.statSync('.');
 try{if(!before.isDirectory()||!same(before,fs.fstatSync(fd))||!same(before,expected))fail();process.chdir(p);if(!same(before,fs.statSync('.')))fail();return fn(fd);}
 finally{fs.closeSync(fd);process.chdir(prior);if(!same(priorStat,fs.statSync('.')))fail();}
}
function remove(p,expected){
 ancestry(path.dirname(p));var s=fs.lstatSync(p);if(!same(s,expected))fail();
 if(!s.isDirectory()){if(!s.isFile()&&!s.isSymbolicLink())fail();fs.unlinkSync(p);return;}
 var count=0;
 function walk(name,pin,depth){if(depth>32)fail();at(name,pin,function(fd){fs.readdirSync('.').forEach(function(child){
  if(++count>65536)fail();var item=fs.lstatSync(child);
  if(item.isDirectory()){walk(child,item,depth+1);if(!same(item,fs.lstatSync(child)))fail();fs.rmdirSync(child);}
  else{if(!item.isFile()&&!item.isSymbolicLink())fail();if(!same(item,fs.lstatSync(child)))fail();fs.unlinkSync(child);}
 });fs.fsyncSync(fd);});}
 walk(p,s,0);at(path.dirname(p),fs.lstatSync(path.dirname(p)),function(fd){if(!same(s,fs.lstatSync(path.basename(p))))fail();fs.rmdirSync(path.basename(p));fs.fsyncSync(fd);});
}
function blocked(scope,error){reply.blocked.push({scope:scope,reason:error.code==='EACCES'||error.code==='EPERM'?'permission-denied':'unsafe-path'});}
function visit(p,scope){try{var s=exists(p);if(!s)return;if(input.action==='sweep')remove(p,s);if(exists(p))reply.present.push(scope);}catch(e){blocked(scope,e);}}
function rootHint(p,scope){try{if(exists(p))reply.root_present.push(scope);}catch(e){if(e.code==='EACCES')reply.root_present.push(scope);else blocked(scope,e);}}
['clean-your-tv-root','clean-your-tv-installation','clean-your-tv-python','clean-your-tv-root-updater','clean-your-tv-system-updater'].forEach(function(name){rootHint('/var/lib/'+name,name);});
rootHint('/var/webos-profile/override/clean-your-tv-root.json','root-profile');
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
try{var operations='/media/developer/.cytv-installer/operations';if(exists(operations)){ancestry(operations);reply.resident_installer=fs.readdirSync(operations).length>0;}}catch(e){blocked('installer-private',e);}
if(input.action==='stop'){
 var state=base+'/applications/'+apps[0]+'/state',s=exists(state);
 if(s)try{ancestry(state);at(state,s,function(fd){
  ['blocked','control.json'].forEach(function(name){var old=exists(name);if(old&&(!old.isFile()||old.nlink!==1))fail();});
  if(!exists('blocked')){var marker=fs.openSync('blocked',c.O_WRONLY|c.O_CREAT|c.O_EXCL|c.O_NOFOLLOW,436);try{fs.writeSync(marker,new Buffer('stopped'),0,7,0);fs.fsyncSync(marker);}finally{fs.closeSync(marker);}}
  var name='.cytv-stop-'+crypto.randomBytes(12).toString('hex'),control=fs.openSync(name,c.O_WRONLY|c.O_CREAT|c.O_EXCL|c.O_NOFOLLOW,420);
  try{var b=new Buffer('{"cmd":"stop"}');fs.writeSync(control,b,0,b.length,0);fs.fsyncSync(control);}finally{fs.closeSync(control);}
  fs.renameSync(name,'control.json');fs.fsyncSync(fd);
 });}catch(e){blocked('helper-control',e);}
 process.stdout.write(JSON.stringify(reply));return;
}
apps.forEach(function(app,index){visit(base+'/applications/'+app,app+' app');visit(base+'/packages/'+app,app+' package');visit(base+'/services/'+services[index],app+' service');});
visit('/media/developer/.cytv-installer','installer-private');
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
function next(){if(!stages.length){process.stdout.write(JSON.stringify(reply));return;}var dir=publicRoot+'/'+stages.shift(),pin,files;
 try{pin=fs.lstatSync(dir);if(!pin.isDirectory()||pin.isSymbolicLink())fail();files=fs.readdirSync(dir);}catch(e){blocked('installer-staging',e);next();return;}
 function file(){if(!files.length){try{if(input.action==='sweep'&&same(pin,fs.lstatSync(dir))&&!fs.readdirSync(dir).length)fs.rmdirSync(dir);}catch(e){blocked('installer-staging',e);}next();return;}
  var name=files.shift(),index=['helper.ipk','launcher.ipk','updater.ipk'].indexOf(name);if(index<0){file();return;}
  controlIdentity(dir+'/'+name,function(error,app,expected){if(error){blocked('installer-staging',error);file();return;}if(app===apps[index]){
   try{if(!same(pin,fs.lstatSync(dir)))fail();if(input.action==='sweep')remove(dir+'/'+name,expected);if(exists(dir+'/'+name))reply.present.push('installer-staging '+name);}catch(e){blocked('installer-staging',e);}
  }file();});
 }file();
}next();
}());
'''


def _device(installer, action):
    raw = installer.remote.run('/usr/bin/node -e ' + shlex.quote(PRIVATE_CLEANUP_PROGRAM) + ' ' +
                               shlex.quote(json.dumps({'action': action})), timeout=90)
    value = json.loads(raw)
    if (not isinstance(value, dict) or value.get('schema') != 1 or
            not all(isinstance(value.get(k), list) for k in ('present', 'blocked', 'root_present'))):
        raise UserError('Removal could not be checked. Reconnect and try again.')
    return value


def _check_access(value):
    if value['root_present'] or any(row.get('reason') == 'permission-denied' for row in value['blocked']):
        raise UserError(ROOT_MESSAGE, reason_code='root-access-required')
    if value['blocked']:
        raise UserError('Some project paths changed. Close other installers and try again.')


def continue_removal(installer, expected_pending):
    pending = installer.store.pending(installer.profile)
    if pending != expected_pending or not pending or pending.get('recovery_protocol') != 'clean-removal-v1':
        raise UserError('Removal evidence changed. Recovery data was kept.', reason_code='pending-operation')
    current = _device(installer, 'inventory')
    _check_access(current)
    apps = {app['id'] for app in installer.installed_apps()}
    if any(app in apps for app in ('com.cleanyourtv.root.preview', 'com.cleanyourtv.root.updater', 'com.cleanyourtv.system.updater')):
        raise UserError(ROOT_MESSAGE, reason_code='root-access-required')
    if pending.get('stage') == 'verified-clean' and not current['present'] and not apps.intersection(APPS):
        installer.store.finish_clean_removal(installer.profile)
        return {'removed': True, 'verified_clean': True}
    baseline = pending.get('cleanup_boot_id')
    if baseline is None or pending.get('stage') == 'verified-clean':
        baseline = current['boot_id']
        installer.store.checkpoint(installer.profile, cleanup_boot_id=baseline, stage='requested')
    restarted = current['boot_id'] != baseline
    installer.progress('Restoring TV controls…')
    _check_access(_device(installer, 'stop'))
    if APPS[0] in apps:
        reply = installer.remote.luna('com.local.nativehome.service/disable', {})
        cancel = reply.get('cancel', {})
        if cancel.get('returnValue') is not True and cancel.get('errorCode') != 2:
            raise UserError('TV startup could not be disabled. Try again.')
    if APPS[1] in apps:
        reply = installer.remote.luna('com.gathin.tvhome.renewal/disable', {})
        state = reply.get('state', {})
        if state.get('enabled') is not False or state.get('error'):
            raise UserError('TV startup could not be disabled. Try again.')
    devices = installer.remote.luna('com.webos.service.eim/getAllInputStatus', {}).get('devices')
    if not isinstance(devices, list):
        raise UserError('TV input shortcuts could not be checked. Try again.')
    if any(device.get('appId') == APPS[1] or device.get('id') == APPS[1] for device in devices):
        installer.remote.luna('com.webos.service.eim/deleteDevice', {'appId': APPS[1]})
    installer.remote.luna('com.webos.applicationManager/launch', {'id': 'com.webos.app.home'})
    installer.store.checkpoint(installer.profile, stage='controls-restored')
    previous = pending.get('previous')
    resident = current.get('resident_installer') is True or current.get('external_update_hint') is not None
    if current.get('external_update_hint') is not None:
        installer.store.checkpoint(installer.profile, previous_update_status=current['external_update_hint'])
    while isinstance(previous, dict):
        resident |= previous.get('recovery_protocol') == 'no-root-original-stream-v1'
        previous = previous.get('previous')
    if resident and not restarted:
        installer.store.checkpoint(installer.profile, stage='restart-required', removal_reason='restart-required', cleanup_restart_first=True)
        installer.progress(RESTART_MESSAGE)
        return {'removed': False, 'verified_clean': False, 'restart_required': True}
    for app, message in zip(APPS, ('Removing Helper…', 'Removing Home…', 'Removing the updater…')):
        if app not in apps:
            continue
        installer.progress(message)
        installer.store.checkpoint(installer.profile, stage='package-removal')
        try:
            installer.remote.luna('com.webos.appInstallService/dev/remove', {'id': app, 'subscribe': True}, terminal='removed', timeout=150)
        except TVRejected as error:
            error.args = ('The TV rejected removal. Check the error details and try again.',)
            raise
    installer.progress('Removing private recovery data…')
    installer.store.checkpoint(installer.profile, stage='private-cleanup')
    _check_access(_device(installer, 'sweep'))
    if not restarted:
        installer.store.checkpoint(installer.profile, stage='restart-required', removal_reason='restart-required')
        installer.progress(RESTART_MESSAGE)
        return {'removed': False, 'verified_clean': False, 'restart_required': True}
    installer.progress('Verifying removal…')
    final = _device(installer, 'inventory')
    _check_access(final)
    if final['present'] or {app['id'] for app in installer.installed_apps()}.intersection(APPS):
        raise UserError('Some project files remain. Try again to finish removal.')
    installer.store.checkpoint(installer.profile, stage='verified-clean', removal_reason='removal-verified',
                               result={'removed': True, 'verified_clean': True})
    installer.store.finish_clean_removal(installer.profile)
    return {'removed': True, 'verified_clean': True}
