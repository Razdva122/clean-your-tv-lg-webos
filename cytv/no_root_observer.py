"""Bounded original-stream observation for new Developer Mode operations.

The imported PROGRAM is bundled with Python on desktop and Android. A trusted
invocation verifies retained bytes; status never executes the retained worker.
An unresolved claim is permanent uncertainty, never permission to resubmit.
"""
import hashlib
import base64
import json
import shlex
import time
import uuid

from .errors import UserError

PROTOCOL = 'no-root-original-stream-v1'
ROOT = '/media/developer/.cytv-installer'
PUBLIC_ROOT = '/media/developer/temp'
APPS = ('com.local.nativehome', 'com.gathin.tvhome')

PROGRAM = r'''
(function () {
'use strict';
var fs=require('fs'), path=require('path'), c=require('constants'), crypto=require('crypto');
var cp=require('child_process'), Decoder=require('string_decoder').StringDecoder;
var input=JSON.parse(process.argv[process.argv.length-1]), plan=input.plan;
var uid=process.getuid(), root=input.root, publicRoot=input.public_root;
process.umask(63); // Private by default, including the sender's inherited environment.
var protocol='no-root-original-stream-v1', apps=['com.local.nativehome','com.gathin.tvhome'];
function fail(code){throw Error(code);}
function hash(raw){return crypto.createHash('sha256').update(raw).digest('hex');}
function buffer(raw){return new Buffer(raw,'utf8');}
function canonical(value){
 if(value===null||typeof value!=='object')return JSON.stringify(value);
 if(Array.isArray(value))return '['+value.map(canonical).join(',')+']';
 return '{'+Object.keys(value).sort().map(function(k){return JSON.stringify(k)+':'+canonical(value[k]);}).join(',')+'}';
}
function same(a,b){return a.dev===b.dev&&a.ino===b.ino;}
function exists(name){try{fs.lstatSync(name);return true;}catch(e){if(e.code==='ENOENT')return false;throw e;}}
function directory(name,privateLeaf){
 var s=fs.lstatSync(name);
 if(!s.isDirectory()||s.isSymbolicLink()||(s.uid!==0&&s.uid!==uid))fail('unsafe-directory');
 // A root-owned sticky temporary ancestor is safe for an owned private child.
 if((s.mode&18)&&!(s.uid===0&&(s.mode&512)))fail('writable-directory');
 if(privateLeaf&&(s.uid!==uid||(s.mode&511)!==448))fail('nonprivate-directory');
 return s;
}
function ancestry(name,publicAccess){
 var current=path.resolve(name);
 for(;;){var s=directory(current,false);if(publicAccess&&!(s.mode&1))fail('private-public-parent');var parent=path.dirname(current);if(parent===current)break;current=parent;}
}
function sync(name){var fd=fs.openSync(name,c.O_RDONLY|c.O_NOFOLLOW);try{fs.fsyncSync(fd);}finally{fs.closeSync(fd);}}
function mkdir(name,mode){
 fs.mkdirSync(name,448);var before=fs.lstatSync(name),fd=fs.openSync(name,c.O_RDONLY|c.O_NOFOLLOW);
 try{if(!same(before,fs.fstatSync(fd)))fail('changed-directory');fs.fchmodSync(fd,mode);fs.fsyncSync(fd);}
 finally{fs.closeSync(fd);}sync(path.dirname(name));
}
function read(name,limit,publicFile){
 ancestry(path.dirname(name));
 var before=fs.lstatSync(name), fd, raw;
 if(!before.isFile()||before.isSymbolicLink()||before.nlink!==1||before.uid!==uid||
    (before.mode&511)!==(publicFile?420:384)||before.size>limit)fail('unsafe-file');
 fd=fs.openSync(name,c.O_RDONLY|c.O_NOFOLLOW|c.O_NONBLOCK);
 try{
  if(!same(before,fs.fstatSync(fd)))fail('changed-file');
  raw=new Buffer(before.size);var offset=0;
  while(offset<raw.length){var n=fs.readSync(fd,raw,offset,raw.length-offset,offset);if(n<=0)fail('short-read');offset+=n;}
  var after=fs.fstatSync(fd);
  if(!same(before,after)||after.size!==before.size||!same(before,fs.lstatSync(name)))fail('changed-file');
 }finally{fs.closeSync(fd);}
 return raw;
}
function json(name){return JSON.parse(read(name,262144,false).toString('utf8'));}
function exclusive(name,raw,mode){
 var fd=fs.openSync(name,c.O_WRONLY|c.O_CREAT|c.O_EXCL|c.O_NOFOLLOW,mode||384);
 try{var b=buffer(raw),offset=0;while(offset<b.length){var n=fs.writeSync(fd,b,offset,b.length-offset);if(n<=0)fail('short-write');offset+=n;}fs.fsyncSync(fd);}
 finally{fs.closeSync(fd);}
 sync(path.dirname(name));
}
function atomicNew(name,value){
 var tmp=path.dirname(name)+'/.pending-'+crypto.randomBytes(16).toString('hex');
 exclusive(tmp,canonical(value));
 // Exclusive link publishes complete bytes without replacing first evidence.
 try{fs.linkSync(tmp,name);}finally{fs.unlinkSync(tmp);}
 sync(path.dirname(name));
}
if(typeof c.O_NOFOLLOW!=='number'||typeof c.O_EXCL!=='number')fail('unsupported-storage');
if(!plan||plan.protocol!==protocol||plan.edition!=='no-root'||!/^\w{32}$/.test(plan.operation)||
   !/^[a-f0-9]{32}$/.test(plan.operation)||!/^[a-f0-9]{32}$/.test(plan.diagnostic_id)||
   (plan.action!=='install'&&plan.action!=='remove')||!Array.isArray(plan.slots)||plan.slots.length!==2||
   root!==path.resolve(root)||publicRoot!==path.resolve(publicRoot)||!/^[a-f0-9]{64}$/.test(plan.source_sha256)||
   !/^[a-f0-9]{64}$/.test(plan.configuration_sha256))fail('invalid-plan');
var op=plan.operation, opdir=root+'/operations/'+op, stage=publicRoot+'/cytv-'+op;
var planText=canonical(plan), planSha=hash(planText), active=root+'/active', marker='owner-'+op+'.json';
plan.slots.forEach(function(slot,i){
 var request={id:apps[i],subscribe:true};
 if(plan.action==='install')request.ipkUrl=stage+'/'+(i===0?'helper.ipk':'launcher.ipk');
 if(slot.app!==apps[i]||slot.index!==i||slot.method!=='com.webos.appInstallService/dev/'+plan.action||
    slot.request!==canonical(request)||slot.request_sha256!==hash(slot.request)||
    (plan.action==='install'?(!/^[a-f0-9]{64}$/.test(slot.artifact_sha256)||typeof slot.version!=='string'):
       (slot.artifact_sha256!==null||slot.version!==null)))fail('invalid-slot');
});
function binding(){return {protocol:protocol,operation:op,plan_sha256:planSha,source_sha256:plan.source_sha256};}
function bound(value){var expected=binding();Object.keys(expected).forEach(function(k){if(!value||value[k]!==expected[k])fail('foreign-evidence');});return value;}
function checked(){
 ancestry(root);directory(root,true);directory(root+'/operations',true);directory(opdir,true);
 if(read(opdir+'/plan.json',262144,false).toString('utf8')!==planText||hash(read(opdir+'/observer.js',262144,false))!==plan.source_sha256)fail('changed-plan-source');
 bound(json(opdir+'/storage.json'));
 return bound(json(opdir+'/prepared.json'));
}
function publicStage(){
 ancestry(publicRoot,true);var s=directory(stage,false),identity=bound(json(opdir+'/public-stage.json'));
 if(s.uid!==uid||(s.mode&511)!==493||s.dev!==identity.dev||s.ino!==identity.ino)fail('changed-public-stage');
}
function attached(){
 var identity=checked(), s=directory(active,true), owner=bound(json(active+'/'+marker));
 if(s.dev!==identity.dev||s.ino!==identity.ino||owner.nonce!==identity.nonce||fs.readdirSync(active).join(',')!==marker)fail('foreign-reservation');
 return identity;
}
function claimName(i){return opdir+'/claim-'+i+'.json';}
function evidence(i,kind){
 var name=opdir+'/'+kind+'-'+i+'.json';if(!exists(name))return null;
 var value=bound(json(name));if(value.slot!==i)fail('foreign-slot');return value;
}
function slotStatus(i){
 var claim=evidence(i,'claim'), terminal=evidence(i,'terminal'), readback=evidence(i,'readback');
 if(terminal&&(!claim||claim.disposition!=='request'||['success','failure'].indexOf(terminal.terminal)<0))fail('invalid-terminal');
 if(terminal){
  var reply=terminal.reply,detail=reply&&reply.details,state=detail&&detail.state;
  if(!reply||typeof reply!=='object'||Array.isArray(reply))fail('invalid-terminal-reply');
  var negative=reply.returnValue===false||Object.prototype.hasOwnProperty.call(reply,'errorCode')||
      detail&&Object.prototype.hasOwnProperty.call(detail,'errorCode')||/fail|error/.test(state||'');
  if(terminal.terminal==='success'&&(negative||[plan.action==='install'?'installed':'removed','success'].indexOf(state)<0)||
     terminal.terminal==='failure'&&!negative&&Object.keys(reply).length)fail('conflicting-terminal');
 }
 if(readback&&(!claim||!(terminal&&terminal.terminal==='success'||claim.disposition==='no-request')||readback.result!=='matches'))fail('invalid-readback');
 if(claim&&['request','no-request'].indexOf(claim.disposition)<0)fail('invalid-claim');
 return {submission:claim?(claim.disposition==='no-request'?'sealed':'claimed-possibly-submitted'):'prepared',
         terminal:terminal?terminal.terminal:'none',readback:readback?'matches':'not-checked',
         reason:(evidence(i,'lost')||{}).reason||null,reply:terminal?terminal.reply||{}:{}};
}
function accepted(i){var s=slotStatus(i);return !s.reason&&s.readback==='matches'&&(s.terminal==='success'||s.submission==='sealed');}
function stabilize(i){
 slotStatus(i);['claim','terminal','readback'].forEach(function(kind){var name=opdir+'/'+kind+'-'+i+'.json';if(exists(name))sync(name);});sync(opdir);
}
function predecessor(i){for(var k=0;k<i;k++){if(!accepted(k))fail('predecessor-unverified');stabilize(k);}}
var configSteps=plan.action==='install'?['files','eim','launch']:['restore'];
function configState(step){
 var claim=evidence(step,'config-claim'),result=evidence(step,'config-result');
 if(claim&&!/^[a-f0-9]{64}$/.test(claim.nonce))fail('invalid-configuration-claim');
 if(result&&(!claim||result.nonce!==claim.nonce||['verified','unavailable'].indexOf(result.result)<0||result.result==='unavailable'&&step!=='eim'))fail('invalid-configuration-result');
 return result?'complete':claim?'unknown':'prepared';
}
function syncConfig(step){
 if(configState(step)!=='complete')fail('configuration-unverified');
 sync(opdir+'/config-claim-'+step+'.json');sync(opdir+'/config-result-'+step+'.json');sync(opdir);
}
function configSummary(){var value={};configSteps.forEach(function(step){value[step]=configState(step);});return value;}
function closed(){
 if(!exists(opdir+'/closed.json'))return null;
 var value=bound(json(opdir+'/closed.json'));if(value.result!=='verified')fail('invalid-closure');return value;
}
function reservation(){
 if(exists(opdir+'/closed.json'))return 'closed';
 try{attached();return 'active';}catch(e){
  if(exists(active)&&fs.readdirSync(active).length)return 'busy';
  if(exists(opdir+'/reservation')){
   var identity=checked(),s=directory(opdir+'/reservation',true),owner=bound(json(opdir+'/reservation/'+marker));
   if(s.dev===identity.dev&&s.ino===identity.ino&&owner.nonce===identity.nonce&&fs.readdirSync(opdir+'/reservation').join(',')===marker)return 'prepared';
  }
  return 'unknown';
 }
}
function status(){checked();return {protocol:protocol,operation:op,plan_sha256:planSha,reservation:reservation(),configuration:configSummary(),
 slots:plan.slots.map(function(s,i){return slotStatus(i);}),closed:closed()};}
function prepare(){
 ancestry(path.dirname(root));
 if(!exists(root))mkdir(root,448);directory(root,true);
 if(!exists(root+'/operations'))mkdir(root+'/operations',448);directory(root+'/operations',true);
 if(!exists(opdir)){
  mkdir(opdir,448); // Incomplete exclusive initialization is never repaired.
  if(typeof input.source!=='string'||hash(input.source)!==plan.source_sha256)fail('changed-source');
  exclusive(opdir+'/plan.json',planText);exclusive(opdir+'/observer.js',input.source);
  atomicNew(opdir+'/storage.json',binding()); // Prove atomic publication support before requests.
  mkdir(opdir+'/reservation',448);
  var owner=binding();owner.nonce=crypto.randomBytes(32).toString('hex');
  exclusive(opdir+'/reservation/'+marker,canonical(owner));sync(opdir+'/reservation');
  var s=directory(opdir+'/reservation',true);owner.dev=s.dev;owner.ino=s.ino;
  exclusive(opdir+'/prepared.json',canonical(owner));
 }
 var identity=checked();if(exists(opdir+'/closed.json'))fail('operation-closed');
 if(exists(opdir+'/reservation')){
  var source=directory(opdir+'/reservation',true), prepared=bound(json(opdir+'/reservation/'+marker));
  if(source.dev!==identity.dev||source.ino!==identity.ino||prepared.nonce!==identity.nonce||fs.readdirSync(opdir+'/reservation').join(',')!==marker)fail('changed-reservation');
  try{fs.renameSync(opdir+'/reservation',active);}catch(e){if(e.code!=='ENOENT')throw e;}
 }
 attached();sync(active);sync(opdir);sync(root);
 if(plan.action==='install'){
  ancestry(publicRoot,true);
  if(!exists(stage)){
   if(exists(opdir+'/public-stage.json'))fail('missing-public-stage');
   mkdir(stage,493);
   var created=directory(stage,false),stageIdentity=binding();stageIdentity.dev=created.dev;stageIdentity.ino=created.ino;
   exclusive(opdir+'/public-stage.json',canonical(stageIdentity));
  }
  publicStage();
 }
 return {operation:op,plan_sha256:planSha};
}
function slotIndex(){if(typeof input.slot!=='number'||input.slot%1||input.slot<0||input.slot>=plan.slots.length)fail('invalid-slot');return input.slot;}
function worker(i){
 attached();predecessor(i);
 if(plan.action==='remove')syncConfig('restore');
 if(exists(claimName(i))){slotStatus(i);return;}
 var slot=plan.slots[i];
 if(plan.action==='install'){publicStage();if(hash(read(JSON.parse(slot.request).ipkUrl,128*1024*1024,true))!==slot.artifact_sha256)fail('changed-artifact');}
 var claim=binding();claim.slot=i;claim.disposition='request';
 try{exclusive(claimName(i),canonical(claim));}catch(e){if(e.code==='EEXIST')return;throw e;}
 // No request before the permanent exclusive claim AND its directory sync.
 var child, timer, killer, done=false, total=0,count=0,text='',decoder=new Decoder('utf8'),stderr=0;
 function end(terminal,reason,reply){
  if(done)return;done=true;clearTimeout(timer);
  var result=binding();result.slot=i;
  try{if(terminal){result.terminal=terminal;result.reply=reply||{};atomicNew(opdir+'/terminal-'+i+'.json',result);}
      else{result.reason=reason;atomicNew(opdir+'/lost-'+i+'.json',result);}}
  catch(e){
   // Preserve an observed terminal separately from a journal durability failure.
   // If storage rejects even this marker, every later mutator must stabilize
   // the exact original evidence before it can advance to another slot.
   try{var lost=binding();lost.slot=i;lost.reason='terminal-persistence-unverified';atomicNew(opdir+'/lost-'+i+'.json',lost);}catch(ignored){}
  }
  // Keep stdin OPEN until the terminal file and containing directory are synced.
  if(child){
   child.stdin.end();child.kill();
   killer=setTimeout(function(){try{child.kill('SIGKILL');}catch(ignored){}},1000);
  }
 }
 function reply(value){
  if(!value||Array.isArray(value)||typeof value!=='object')return end(null,'malformed-reply');
  var details=value.details===undefined?{}:value.details;
  if(!details||Array.isArray(details)||typeof details!=='object')return end('failure');
  var state=String(details.state||'').toLowerCase();
  var projected={details:{state:['installing','installed','removing','removed','success','failed','error','install failed','remove failed'].indexOf(state)>=0?state:'unknown'}};
  function number(v){if(typeof v==='string'&&/^-?[0-9]{1,10}$/.test(v))v=Number(v);return typeof v==='number'&&v%1===0&&v>=-2147483648&&v<=2147483647?v:null;}
  ['errorCode','statusValue'].forEach(function(k){if(Object.prototype.hasOwnProperty.call(value,k))projected[k]=number(value[k]);});
  if(Object.prototype.hasOwnProperty.call(details,'errorCode'))projected.details.errorCode=number(details.errorCode);
  if(typeof value.returnValue==='boolean')projected.returnValue=value.returnValue;
  if(['FAILED_INTERNAL_ERROR','FAILED_CREATE_TMP','FAILED_NOT_ENOUGH_TEMP_SPACE','FAILED_NOT_ENOUGH_INSTALL_SPACE','FAILED_PACKAGEFILE_NOT_FOUND','FAILED_PACKAGEFILE_CORRUPT','FAILED_VERIFY','FAILED_IPKG_INSTALL','FAILED_INSTALL'].indexOf(details.reason)>=0)projected.details.reason=details.reason;
  if(value.returnValue===false||Object.prototype.hasOwnProperty.call(value,'errorCode')||
     Object.prototype.hasOwnProperty.call(details,'errorCode')||/fail|error/.test(state))return end('failure',null,projected);
  if(state===(plan.action==='install'?'installed':'removed')||state==='success')return end('success',null,projected);
 }
 function parse(chunk){
  if(done)return;total+=chunk.length;if(total>1048576)return end(null,'oversized-stream');
  text+=decoder.write(chunk);if(text.indexOf('\ufffd')>=0)return end(null,'malformed-utf8');
  while(!done){
   text=text.replace(/^\s+/,'');if(!text)return;if(text.charAt(0)!=='{')return end(null,'malformed-reply');
   var depth=0,quoted=false,escaped=false,stop=-1;
   for(var j=0;j<text.length;j++){
    var ch=text.charAt(j);
    if(quoted){if(escaped)escaped=false;else if(ch==='\\')escaped=true;else if(ch==='"')quoted=false;}
    else if(ch==='"')quoted=true;else if(ch==='{'||ch==='[')depth++;else if(ch==='}'||ch===']'){depth--;if(depth===0){stop=j+1;break;}}
   }
   if((stop<0?text.length:stop)>65536)return end(null,'oversized-reply');if(stop<0)return;
   var value;try{value=JSON.parse(text.slice(0,stop));}catch(e){return end(null,'malformed-reply');}
   text=text.slice(stop);count++;if(count>1024)return end(null,'too-many-replies');reply(value);
  }
 }
 timer=setTimeout(function(){end(null,'observation-timeout');},Math.min(input.timeout||150000,150000));
 try{
  child=cp.spawn(input.sender||'/usr/bin/luna-send-pub',['-i','luna://'+slot.method,slot.request],{stdio:['pipe','pipe','pipe']});
  child.stdin.on('error',function(){end(null,'sender-stdin-lost');});
  child.stdout.on('data',parse);
  child.stderr.on('data',function(chunk){stderr+=chunk.length;if(stderr>1048576)end(null,'oversized-stderr');});
  child.on('error',function(){end(null,'sender-unavailable');});
  child.on('close',function(){end(null,'stream-ended');clearTimeout(killer);});
 }catch(e){end(null,'sender-unavailable');}
}
function release(){
 checked();plan.slots.forEach(function(s,i){if(!accepted(i))fail('unresolved-slot');stabilize(i);});
 configSteps.forEach(syncConfig);
 var configuration=bound(json(opdir+'/configuration.json'));if(configuration.result!=='verified')fail('configuration-unverified');
 if(!exists(opdir+'/closed.json')){var close=binding();close.result='verified';atomicNew(opdir+'/closed.json',close);}
 else closed();
 sync(opdir+'/configuration.json');sync(opdir+'/closed.json');sync(opdir);
 // Only this exact old owner's child may be unlinked. A new nonempty active
 // directory cannot be removed by a delayed old rmdir (including duplicate releases).
 if(exists(active+'/'+marker)){
  var owner=bound(json(active+'/'+marker)),identity=checked();if(owner.nonce!==identity.nonce)fail('foreign-reservation');
  try{fs.unlinkSync(active+'/'+marker);sync(active);}catch(e){if(e.code!=='ENOENT')throw e;}
 }
 try{fs.rmdirSync(active);}catch(e){
  if(e.code!=='ENOENT'){
   if(['ENOTEMPTY','EEXIST'].indexOf(e.code)<0)throw e;
   try{
    var names=fs.readdirSync(active),current=directory(active,true);
    if(names.length!==1||!/^owner-[a-f0-9]{32}\.json$/.test(names[0])||names[0]===marker)fail('unexpected-reservation');
    var foreign=json(active+'/'+names[0]),foreignID=names[0].slice(6,-5),prepared=json(root+'/operations/'+foreignID+'/prepared.json');
    if(foreign.operation!==foreignID||foreign.protocol!==protocol||foreign.nonce!==prepared.nonce||
       foreign.plan_sha256!==prepared.plan_sha256||foreign.source_sha256!==prepared.source_sha256||
       current.dev!==prepared.dev||current.ino!==prepared.ino)fail('unexpected-reservation');
   }catch(changed){if(changed.code!=='ENOENT')throw changed;}
  }
 }
 sync(root);return status();
}
var result;
switch(input.command){
case 'prepare':result=prepare();break;
case 'status':result=status();break;
case 'attach':attached();sync(active);sync(root);result={operation:op};break;
case 'artifacts':
 attached();publicStage();var missing=[];
 plan.slots.forEach(function(s,i){if(!exists(claimName(i))){var name=JSON.parse(s.request).ipkUrl;if(!exists(name))missing.push(i);else if(hash(read(name,128*1024*1024,true))!==s.artifact_sha256)fail('changed-artifact');}});
 result={operation:op,missing:missing};break;
case 'config-claim':
 attached();var step=input.slot,position=configSteps.indexOf(step);
 if(position<0)fail('invalid-configuration-step');
 if(plan.action==='install')plan.slots.forEach(function(s,i){if(!accepted(i))fail('unresolved-slot');stabilize(i);});
 configSteps.slice(0,position).forEach(syncConfig);
 var stateBefore=configState(step),won=false,token=null;
 if(stateBefore==='prepared'){
  var configClaim=binding();configClaim.slot=step;configClaim.nonce=crypto.randomBytes(32).toString('hex');
  try{exclusive(opdir+'/config-claim-'+step+'.json',canonical(configClaim));won=true;token=configClaim.nonce;}
  catch(e){if(e.code!=='EEXIST')throw e;}
 }
 if(configState(step)==='complete')syncConfig(step);
 result={operation:op,won:won,nonce:token,state:configState(step)};break;
case 'config-result':
 attached();var configStep=input.slot;
 if(configSteps.indexOf(configStep)<0)fail('invalid-configuration-step');
 var ownedClaim=evidence(configStep,'config-claim');
 if(!ownedClaim||!input.proof||input.proof.nonce!==ownedClaim.nonce||
    ['verified','unavailable'].indexOf(input.proof.result)<0||input.proof.result==='unavailable'&&configStep!=='eim')fail('foreign-configuration-result');
 if(configState(configStep)!=='complete'){
  var configResult=binding();configResult.slot=configStep;configResult.nonce=ownedClaim.nonce;configResult.result=input.proof.result;
  atomicNew(opdir+'/config-result-'+configStep+'.json',configResult);
 }
 syncConfig(configStep);result={operation:op};break;
case 'start':
 attached();var index=slotIndex();predecessor(index);
 if(!exists(claimName(index))){
  var workerInput={command:'worker',root:root,public_root:publicRoot,plan:plan,slot:index,sender:input.sender,timeout:input.timeout};
  var detached=cp.spawn(process.execPath,[opdir+'/observer.js',JSON.stringify(workerInput)],{detached:true,stdio:['ignore','ignore','ignore'],cwd:opdir});
  detached.unref();
 }
 result={operation:op};break;
case 'worker':worker(slotIndex());return;
case 'seal':
 attached();var sealIndex=slotIndex();predecessor(sealIndex);if(plan.action!=='remove')fail('invalid-seal');
 syncConfig('restore');
 var seal=binding();seal.slot=sealIndex;seal.disposition='no-request';exclusive(claimName(sealIndex),canonical(seal));result=status();break;
case 'readback':
 attached();var readIndex=slotIndex(), state=slotStatus(readIndex);
 if(state.reason||state.terminal!=='success'&&state.submission!=='sealed')fail('terminal-unverified');
 stabilize(readIndex);
 if(state.readback!=='matches'){var proof=binding();proof.slot=readIndex;proof.result='matches';atomicNew(opdir+'/readback-'+readIndex+'.json',proof);}
 result=status();break;
case 'configured':
 attached();plan.slots.forEach(function(s,i){if(!accepted(i))fail('unresolved-slot');stabilize(i);});
 configSteps.forEach(syncConfig);
 if(!exists(opdir+'/configuration.json')){var config=binding();config.result='verified';atomicNew(opdir+'/configuration.json',config);}
 else bound(json(opdir+'/configuration.json'));result=status();break;
case 'release':result=release();break;
case 'retire':
 checked();if(!closed())fail('operation-not-closed');
 if(plan.action==='install'&&exists(stage)){
  publicStage();
  plan.slots.forEach(function(s){var name=JSON.parse(s.request).ipkUrl;if(exists(name)){if(hash(read(name,128*1024*1024,true))!==s.artifact_sha256)fail('changed-artifact');fs.unlinkSync(name);sync(stage);}});
  fs.rmdirSync(stage);sync(publicRoot);
 }
 result=status();break;
default:fail('unsupported-command');
}
process.stdout.write(JSON.stringify(result));
}());
'''


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def make_plan(operation, diagnostic_id, action, artifacts, versions, public_root=PUBLIC_ROOT, configuration_sha256=None):
    slots = []
    for index, app in enumerate(APPS):
        name = ('helper.ipk', 'launcher.ipk')[index]
        request = {'id': app, 'subscribe': True}
        if action == 'install':
            request['ipkUrl'] = public_root + '/cytv-' + operation + '/' + name
        request = canonical(request)
        slots.append(dict(index=index, app=app, method='com.webos.appInstallService/dev/' + action,
                          request=request, request_sha256=hashlib.sha256(request.encode()).hexdigest(),
                          artifact_sha256=hashlib.sha256(artifacts[name]).hexdigest() if action == 'install' else None,
                          version=versions[app] if action == 'install' else None))
    return dict(protocol=PROTOCOL, edition='no-root', operation=operation, diagnostic_id=diagnostic_id,
                action=action, source_sha256=hashlib.sha256(PROGRAM.encode()).hexdigest(), slots=slots,
                configuration_sha256=configuration_sha256 or hashlib.sha256(b'{}').hexdigest())


def invoke(remote, plan, command, slot=None, source=None, proof=None):
    request = dict(root=ROOT, public_root=PUBLIC_ROOT, plan=plan, command=command, slot=slot)
    if command == 'prepare':
        request['source'] = PROGRAM if source is None else source
    if proof is not None:request['proof']=proof
    try:
        reply = json.loads(remote.run('env -u NODE_OPTIONS -u NODE_PATH /usr/bin/node -e ' +
                                     shlex.quote(PROGRAM) + ' ' + shlex.quote(canonical(request)), timeout=30))
        if not isinstance(reply, dict) or reply.get('operation') != plan['operation']:
            raise ValueError('foreign-observer')
        return reply
    except (OSError, RuntimeError, ValueError, KeyError, TypeError):
        raise UserError('The original No-root observation could not be verified. Recovery data was kept.',
                        reason_code='pending-operation') from None


def refuse():
    raise UserError('The original No-root operation cannot safely continue. Recovery data was kept.',
                    reason_code='pending-operation')


def begin(installer, action, artifacts, versions, expected, configuration):
    operation = uuid.uuid4().hex
    installer.store.begin(installer.profile, 'install' if action == 'install' else 'uninstall',
                          recovery_protocol=PROTOCOL, observer_operation=operation,
                          expected=expected, versions=versions)
    pending = installer.store.pending(installer.profile)
    config_hash=hashlib.sha256(canonical({name:hashlib.sha256(raw).hexdigest() for name,raw in configuration.items()}).encode()).hexdigest()
    plan = make_plan(operation, pending['diagnostic_id'], action, artifacts, versions, PUBLIC_ROOT,config_hash)
    capsule = dict(schema=1, profile=installer.profile, plan=plan, source=PROGRAM, expected=expected,
                   artifacts={name: base64.b64encode(raw).decode() for name, raw in artifacts.items()},
                   configuration={name: raw.decode('utf8') for name, raw in configuration.items()})
    digest = installer.store.save_capsule(installer.profile, operation, capsule)
    installer.store.checkpoint(installer.profile, capsule_sha256=digest)
    invoke(installer.remote, plan, 'prepare')
    for slot in plan['slots']:
        if action == 'install':
            name = ('helper.ipk', 'launcher.ipk')[slot['index']]
            installer.remote.upload(json.loads(slot['request'])['ipkUrl'], artifacts[name], mode=0o644)
    return installer.store.pending(installer.profile)


def stage_remaining(installer, value):
    """Only missing unclaimed paths; never replace changed or claimed payloads."""
    plan=value['plan']
    if plan['action']!='install':return
    missing=invoke(installer.remote,plan,'artifacts').get('missing')
    if not isinstance(missing,list) or any(type(index) is not int or index not in (0,1) for index in missing):refuse()
    for index in missing:
        name=('helper.ipk','launcher.ipk')[index]
        raw=base64.b64decode(value['artifacts'][name],validate=True)
        installer.remote.upload(json.loads(plan['slots'][index]['request'])['ipkUrl'],raw,mode=0o644)
    if invoke(installer.remote,plan,'artifacts').get('missing')!=[]:refuse()


def capsule(installer, pending):
    if (not pending or pending.get('recovery_protocol') != PROTOCOL or 'previous' in pending or
            pending.get('action') not in ('install', 'uninstall') or installer.profile['edition'] != 'no-root'):
        refuse()
    value = installer.store.read_capsule(installer.profile, pending.get('observer_operation'), pending.get('capsule_sha256'))
    try:
        plan = value['plan']
        if (value['schema'] != 1 or value['profile'] != installer.profile or plan['operation'] != pending['observer_operation'] or
                plan['diagnostic_id'] != pending['diagnostic_id'] or plan['protocol'] != PROTOCOL or
                plan['action'] != ('install' if pending['action'] == 'install' else 'remove') or
                hashlib.sha256(value['source'].encode()).hexdigest() != plan['source_sha256'] or
                value['expected'] != pending['expected']):
            refuse()
        artifacts = {name: base64.b64decode(raw, validate=True) for name, raw in value['artifacts'].items()}
        config_hash=hashlib.sha256(canonical({name:hashlib.sha256(raw.encode()).hexdigest() for name,raw in value['configuration'].items()}).encode()).hexdigest()
        rebuilt = make_plan(plan['operation'], plan['diagnostic_id'], plan['action'], artifacts, pending['versions'], PUBLIC_ROOT,config_hash)
        rebuilt['source_sha256'] = plan['source_sha256']
        if rebuilt != plan:
            refuse()
        if plan['action'] == 'install':
            from .operations import HELPER_STATE
            if set(value['configuration']) != {'ssap-key.json', 'apps.json'}:
                refuse()
            for name, raw in value['configuration'].items():
                if hashlib.sha256(raw.encode()).hexdigest() != value['expected'][HELPER_STATE+'/'+name]:
                    refuse()
        return value
    except (KeyError, ValueError, TypeError):
        refuse()


FILE_CHECK = r'''
(function(){
 var fs=require('fs'),c=require('constants'),crypto=require('crypto'),path=require('path');
 var expected=JSON.parse(process.argv[process.argv.length-1]);
 Object.keys(expected).forEach(function(name){
  for(var parent=path.dirname(name);;parent=path.dirname(parent)){
   var directory=fs.lstatSync(parent);if(!directory.isDirectory()||directory.isSymbolicLink())throw Error('unsafe-parent');
   if(parent===path.dirname(parent))break;
  }
  var before=fs.lstatSync(name);
  if(!before.isFile()||before.nlink!==1||before.size>128*1024*1024)throw Error('unsafe-file');
  var fd=fs.openSync(name,c.O_RDONLY|c.O_NOFOLLOW|c.O_NONBLOCK),hash=crypto.createHash('sha256'),b=new Buffer(65536),n;
  try{
   var opened=fs.fstatSync(fd);if(opened.ino!==before.ino||opened.dev!==before.dev)throw Error('changed-file');
   while((n=fs.readSync(fd,b,0,b.length,null))>0)hash.update(b.slice(0,n));
   var after=fs.lstatSync(name);if(after.ino!==before.ino||after.dev!==before.dev||after.size!==before.size)throw Error('changed-file');
  }finally{fs.closeSync(fd);}
  if(hash.digest('hex')!==expected[name])throw Error('changed-content');
 });process.stdout.write('CYTV_ORIGINAL_FILES_VERIFIED');
}());
'''

STATE_CHECK = r'''
(function(){
 var fs=require('fs'),path=require('path'),directory=process.argv[process.argv.length-1],uid=process.getuid();
 function owner(s){return s.uid===uid||s.uid===5999&&s.gid===5000;}
 for(var current=directory;;current=path.dirname(current)){
  var s=fs.lstatSync(current);if(!s.isDirectory()||s.isSymbolicLink())throw Error('unsafe-state-parent');
  if(current===directory&&(!owner(s)||(s.mode&2)))throw Error('unsafe-state-owner');
  if(current===path.dirname(current))break;
 }
 ['ssap-key.json','apps.json'].forEach(function(name){
  var s;try{s=fs.lstatSync(directory+'/'+name);}catch(e){if(e.code==='ENOENT')return;throw e;}
  if(!s.isFile()||s.nlink!==1||!owner(s)||(s.mode&2)||(name==='ssap-key.json'&&(s.mode&7)))throw Error('unsafe-config-file');
 });process.stdout.write('CYTV_CONFIGURATION_PRIVATE');
}());
'''

EMPTY_PACKAGE = r'''
(function(){
 var fs=require('fs'),path=require('path'),c=require('constants'),args=JSON.parse(process.argv[process.argv.length-1]);
 if(['com.local.nativehome','com.gathin.tvhome'].indexOf(args.app)<0)throw Error('unexpected-app');
 function exists(name){try{fs.lstatSync(name);return true;}catch(e){if(e.code==='ENOENT')return false;throw e;}}
 var service=args.app+(args.app==='com.gathin.tvhome'?'.renewal':'.service'),directory=args.base+'/packages/'+args.app;
 if(exists(args.base+'/applications/'+args.app)||exists(args.base+'/services/'+service))throw Error('application-remains');
 for(var current=directory;;current=path.dirname(current)){
  var s=fs.lstatSync(current);if(!s.isDirectory()||s.isSymbolicLink())throw Error('unsafe-parent');
  if(current===path.dirname(current))break;
 }
 var before=fs.lstatSync(directory);
 if((before.uid!==process.getuid()&&before.uid!==0&&!(before.uid===5999&&before.gid===5000))||(before.mode&2)||fs.readdirSync(directory).length)throw Error('foreign-metadata');
 if(args.cleanup===true){
  var fd=fs.openSync(directory,c.O_RDONLY|c.O_NOFOLLOW);
  try{var opened=fs.fstatSync(fd);if(opened.dev!==before.dev||opened.ino!==before.ino)throw Error('changed-metadata');fs.rmdirSync(directory);}
  finally{fs.closeSync(fd);}
 }
 process.stdout.write('CYTV_EMPTY_PACKAGE');
}());
'''


def empty_package(installer, app, cleanup=False):
    from .operations import BASE
    args={'base':BASE,'app':app,'cleanup':cleanup}
    if installer.remote.run('/usr/bin/node -e '+shlex.quote(EMPTY_PACKAGE)+' '+shlex.quote(canonical(args))).strip()!='CYTV_EMPTY_PACKAGE':refuse()


def files_match(installer, expected):
    if not expected:
        refuse()
    if installer.remote.run('/usr/bin/node -e '+shlex.quote(FILE_CHECK)+' '+shlex.quote(canonical(expected))).strip() != 'CYTV_ORIGINAL_FILES_VERIFIED':
        refuse()


def readback(installer, value, index, allow_empty=False):
    plan = value['plan']; slot = plan['slots'][index]; app = slot['app']
    if plan['action'] == 'remove':
        if any(item['id'] == app for item in installer.installed_apps()):
            refuse()
        try:installer.verify_absent(app)
        except UserError:
            if not allow_empty:raise
            empty_package(installer,app)
        return
    deadline = time.monotonic()+10
    while time.monotonic()<deadline:
        observed=installer.installed_apps(timeout=deadline-time.monotonic())
        from .diagnostic_context import status_summary
        installer.tv_info['components']=status_summary({'device':{'apps':observed}}).get('components',{})
        apps = {item['id']: item.get('version') for item in observed}
        if time.monotonic()>=deadline:
            break
        if apps.get(app) == slot['version']:
            break
        time.sleep(min(1,max(0,deadline-time.monotonic())))
    if time.monotonic()>=deadline:
        raise UserError('Installed version did not match the package. Run cytv status; do not retry blindly.',reason_code='version-mismatch')
    paths = {name: digest for name, digest in value['expected'].items()
             if ('/'+app+'/' in name or '/'+app+'.service/' in name or '/'+app+'.renewal/' in name)
             and '/state/' not in name}
    files_match(installer, paths)


def snapshot(installer, value):
    plan=value['plan']; result=invoke(installer.remote,plan,'status')
    if (result.get('protocol')!=PROTOCOL or result.get('plan_sha256')!=hashlib.sha256(canonical(plan).encode()).hexdigest()
            or not isinstance(result.get('slots'),list) or len(result['slots'])!=2
            or result.get('reservation') not in ('active','prepared','closed','busy','unknown')
            or not isinstance(result.get('configuration'),dict)
            or set(result['configuration'])!=set(('files','eim','launch') if plan['action']=='install' else ('restore',))
            or any(state not in ('prepared','unknown','complete') for state in result['configuration'].values())):
        refuse()
    for slot in result['slots']:
        if (not isinstance(slot,dict) or slot.get('submission') not in ('prepared','claimed-possibly-submitted','sealed') or
                slot.get('terminal') not in ('none','success','failure') or slot.get('readback') not in ('matches','not-checked')):
            refuse()
    return result


def observe(installer, pending):
    value=capsule(installer,pending); result=snapshot(installer,value)
    ready=True
    reason='original-work-remaining'
    if result.get('reservation') not in ('active','prepared','closed'):
        ready=False;reason='original-reservation-unverified'
    if 'unknown' in result.get('configuration',{}).values():
        ready=False;reason='original-configuration-unknown'
    for index,slot in enumerate(result['slots']):
        if slot.get('reason'):
            ready=False;reason='original-terminal-unknown';break
        if slot['terminal']=='failure':
            ready=False;reason='original-vendor-failure';break
        if slot['submission']=='claimed-possibly-submitted' and slot['terminal']=='none':
            ready=False;reason='original-terminal-unknown';break
        if slot['terminal']=='success' or slot['submission']=='sealed':
            try:readback(installer,value,index,allow_empty=slot['terminal']=='success')
            except (RuntimeError,ValueError,KeyError):ready=False;reason='original-readback-unverified';break
    return dict(device={'observer':result},pending=pending,reconciled=None,can_resume_root_setup=False,
                no_root_ready=ready,no_root_reason=reason)


def guard_helper(installer):
    from .operations import HELPER_STATE
    command='if [ -e '+shlex.quote(HELPER_STATE+'/blocked')+' ] || [ -L '+shlex.quote(HELPER_STATE+'/blocked')+' ] || [ -e '+shlex.quote(HELPER_STATE+'/watchdog')+' ] || [ -L '+shlex.quote(HELPER_STATE+'/watchdog')+' ]; then printf CYTV_STOP_RETAINED; else printf CYTV_START_ALLOWED; fi'
    if installer.remote.run(command).strip()!='CYTV_START_ALLOWED':
        raise UserError('Home Helper remains stopped by its safety control. Recovery data was kept; use the TV controls to review it.',reason_code='pending-operation')


def claim_step(installer,plan,step):
    claim=invoke(installer.remote,plan,'config-claim',step)
    if claim.get('state')=='complete':return None
    token=claim.get('nonce')
    if claim.get('won') is not True or not isinstance(token,str) or len(token)!=64:refuse()
    return token


def finish_step(installer,plan,step,token,result='verified'):
    invoke(installer.remote,plan,'config-result',step,proof={'nonce':token,'result':result})


def configure(installer,value):
    from .operations import HELPER_STATE, HOME, HELPER
    from .errors import TVRejected
    plan=value['plan']
    expected={HELPER_STATE+'/'+name:value['expected'][HELPER_STATE+'/'+name] for name in value['configuration']}
    if installer.remote.run('/usr/bin/node -e '+shlex.quote(STATE_CHECK)+' '+shlex.quote(HELPER_STATE)).strip()!='CYTV_CONFIGURATION_PRIVATE':refuse()
    token=claim_step(installer,plan,'files')
    if token:
        if installer.helper_state() not in ('stopped','stale'):refuse()
        for name,raw in value['configuration'].items():
            installer.remote.upload(HELPER_STATE+'/'+name,raw.encode(),mode=0o640 if name=='ssap-key.json' else 0o644)
        files_match(installer,expected)
        finish_step(installer,plan,'files',token)
    else:files_match(installer,expected)
    installer.store.checkpoint(installer.profile,configuration_stage='eim-ready')
    token=claim_step(installer,plan,'eim')
    if token:
        installer.store.checkpoint(installer.profile,configuration_stage='eim-submitted')
        disposition='verified'
        try:
            installer.remote.luna('com.webos.service.eim/addDevice',{'appId':HOME,'pigImage':'','mvpdIcon':''})
            installer.save_eim(True)
        except TVRejected:
            installer.save_eim(installer.read_eim())
            disposition='unavailable'
            installer.progress('Warning: early input restoration is unavailable; startup will use the guarded fallback.')
        finish_step(installer,plan,'eim',token,disposition)
    installer.store.checkpoint(installer.profile,configuration_stage='launch-ready')
    # Read-only guard occurs before claiming; an emergency marker may be reviewed
    # on the TV without consuming the still-unsubmitted automatic launch.
    state=snapshot(installer,value)
    if state.get('configuration',{}).get('launch')=='prepared':guard_helper(installer)
    token=claim_step(installer,plan,'launch')
    if token:
        installer.store.checkpoint(installer.profile,configuration_stage='launch-submitted')
        installer.outcome.launch_submitted()
        # Automatic native entry preserves a stop arriving after the host guard.
        installer.remote.luna('com.webos.applicationManager/launch',{'id':HELPER,'params':{'nativeHomeAuto':True}})
        installer.outcome.launch_accepted()
        finish_step(installer,plan,'launch',token)
    installer.store.checkpoint(installer.profile,configuration_stage='complete')


def continue_operation(installer, expected_pending):
    pending=installer.store.pending(installer.profile)
    if pending!=expected_pending:
        refuse()
    value=capsule(installer,pending);plan=value['plan'];result=snapshot(installer,value)
    if installer.store.pending(installer.profile)!=pending:
        refuse()
    if not result.get('closed'):
        if result.get('reservation') in ('prepared','active'):
            invoke(installer.remote,plan,'prepare',source=value['source'])
        invoke(installer.remote,plan,'attach')
        stage_remaining(installer,value)
        if plan['action']=='remove':
            token=claim_step(installer,plan,'restore')
            if token:
                installer.restore()
                finish_step(installer,plan,'restore',token)
            installer.store.checkpoint(installer.profile,restored_before_removal=True)
        for index in range(2):
            result=snapshot(installer,value);slot=result['slots'][index]
            if slot['terminal']=='failure':
                from .errors import TVRejected
                raise TVRejected('TV package operation failed. Run cytv status before retrying.',slot.get('reply'),plan['slots'][index]['method'])
            if slot['submission']=='prepared':
                if plan['action']=='remove' and not any(item['id']==plan['slots'][index]['app'] for item in installer.installed_apps()):
                    installer.verify_absent(plan['slots'][index]['app'])
                    invoke(installer.remote,plan,'seal',index)
                else:
                    invoke(installer.remote,plan,'start',index)
                    deadline=time.monotonic()+155
                    while True:
                        result=snapshot(installer,value);slot=result['slots'][index]
                        if slot['terminal']!='none' or slot.get('reason'):
                            break
                        if time.monotonic()>=deadline:
                            refuse()
                        time.sleep(.2)
            result=snapshot(installer,value);slot=result['slots'][index]
            if slot['terminal']=='failure':
                from .errors import TVRejected
                raise TVRejected('TV package operation failed. Run cytv status before retrying.',slot.get('reply'),plan['slots'][index]['method'])
            if slot.get('reason') or slot['terminal']!='success' and slot['submission']!='sealed':
                refuse()
            if plan['action']=='remove' and slot['terminal']=='success':
                try:installer.verify_absent(plan['slots'][index]['app'])
                except UserError:empty_package(installer,plan['slots'][index]['app'],cleanup=True)
            readback(installer,value,index)
            invoke(installer.remote,plan,'readback',index)
        # Re-read BOTH packages; earlier success is historical, not current state.
        for index in range(2):readback(installer,value,index)
        if plan['action']=='install':
            installer.outcome.packages_verified()
            configure(installer,value)
        invoke(installer.remote,plan,'configured')
    else:
        for index in range(2):readback(installer,value,index)
    result=invoke(installer.remote,plan,'release')
    try:
        invoke(installer.remote,plan,'retire')
    except RuntimeError:
        raise UserError('Packages are verified, but temporary package cleanup is incomplete. Recovery data was kept.',reason_code='pending-operation') from None
    from .state import private_write
    archive=installer.store.recovery(installer.profile,'finish-no-root-operation')
    private_write(archive,json.dumps({'action':'finish-no-root-operation','stage':'verified','previous':installer.store.pending(installer.profile),'observer':result}).encode())
    installer.store.finish(installer.profile)
    try:
        installer.store.retire_capsule(installer.profile,pending['observer_operation'],pending['capsule_sha256'])
    except (RuntimeError,OSError):
        installer.progress('Setup is verified, but the private recovery capsule could not be removed. Keep the local record for cleanup.')
    if plan['action']=='install':
        try:
            current=installer.helper_state(timeout=5)
            installer.outcome.startup_observed('process-observed' if current=='running' else 'not-observed' if current in ('stopped','stale') else 'unverified')
        except Exception:installer.outcome.startup_observed('unverified')
    return {'installed':'no-root','launch_requested':True,'hardware_verified':False} if plan['action']=='install' else {'removed':True}
