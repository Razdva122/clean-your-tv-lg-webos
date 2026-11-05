'use strict';
// Unwired fixed native pipe adapter. No provider/path/UID/FD injection seam.
var cp=require('child_process');
var executable='/media/developer/apps/usr/palm/applications/com.local.nativehome/stop-io';
var HEADER=16,MAX_REPLY=1048576+4096,MAX_REQUEST=16384+64,MAX_STDERR=4096,TIMEOUT=10000;
var READY=0,BEGIN=1,READ=2,END=5,CLOSE=6;
function error(code){var e=Error(code);e.code=code;return e;}
function nativeError(status){var e=error('STOP_IO_NATIVE');e.status=status;return e;}
function equal(a,b){if(a.length!==b.length)return false;for(var i=0;i<a.length;i++)if(a[i]!==b[i])return false;return true;}
function text(raw){var value=raw.toString('utf8');if(value.indexOf('\u0000')>=0||!equal(Buffer.from(value,'utf8'),raw))throw error('STOP_IO_UTF8');return value;}
function decode(op,status,raw){
 if(status!==0){if(raw.length)throw error('STOP_IO_FRAME');return {failure:nativeError(status)};}
 if(op!==READ){if(raw.length)throw error('STOP_IO_FRAME');return {value:null};}
 if(raw.length<4)throw error('STOP_IO_FRAME');
 var count=raw.readUInt32BE(0),offset=4,records=[];
 if(!count||count>64)throw error('STOP_IO_FRAME');
 for(var i=0;i<count;i++){
  if(offset+8>raw.length)throw error('STOP_IO_FRAME');
  var seq=raw.readUInt32BE(offset),len=raw.readUInt32BE(offset+4);offset+=8;
  if(seq!==i||!len||len>16384||len>raw.length-offset)throw error('STOP_IO_FRAME');
  var value=text(raw.slice(offset,offset+len));offset+=len;
  records.push({name:'entry.'+('0000'+seq).slice(-4)+'.json',raw:value});
 }
 if(offset!==raw.length)throw error('STOP_IO_FRAME');
 return {value:{status:'snapshot',records:records}};
}
function transport(onFatal){
 var child=cp.spawn(executable,['controller'],{stdio:['pipe','pipe','pipe']});
 var pending=null,nextID=1,header=Buffer.alloc(HEADER),headerUsed=0,body=null,bodyUsed=0,stderrBytes=0;
 var terminal=false,closed=false,resolveClosed;
 var c={fatal:null};
 c.closed=new Promise(function(resolve){resolveClosed=resolve;});
 function fail(e){
  if(c.fatal)return;
  c.fatal=e;onFatal(e);
  if(pending){clearTimeout(pending.timer);pending.reject(e);pending=null;}
  body=null;headerUsed=bodyUsed=0;
  // Keep stdout draining. EOF is queued behind the one already-submitted write.
  try{child.stdin.end();}catch(ignored){}
 }
 c.fail=fail;
 function complete(){
  if(!pending||!pending.answer||!pending.written||c.fatal)return;
  var p=pending;pending=null;clearTimeout(p.timer);
  if(p.op===CLOSE)terminal=true;
  if(p.answer.failure)p.reject(p.answer.failure);else p.resolve(p.answer.value);
 }
 function expectation(op,id,written,resolve,reject){
  pending={op:op,id:id,written:written,resolve:resolve,reject:reject,answer:null,timer:null};
  pending.timer=setTimeout(function(){fail(error('STOP_IO_TIMEOUT'));},TIMEOUT);
 }
 c.ready=new Promise(function(resolve,reject){expectation(READY,0,true,resolve,reject);});
 c.command=function(op,payload){
  return new Promise(function(resolve,reject){
   if(c.fatal||closed||terminal){reject(c.fatal||error('STOP_IO_CLOSED'));return;}
   if(pending){reject(error('STOP_IO_BUSY'));return;}
   if(nextID>4294967295){fail(error('STOP_IO_ID_EXHAUSTED'));reject(c.fatal);return;}
   payload=payload||Buffer.alloc(0);
   if(payload.length>MAX_REQUEST){reject(error('STOP_IO_REQUEST_LIMIT'));return;}
   var id=nextID++,frame=Buffer.alloc(HEADER+payload.length);
   frame.write('CYI1',0,'ascii');frame[4]=op;frame.writeUInt32BE(id,8);frame.writeUInt32BE(payload.length,12);payload.copy(frame,HEADER);
   expectation(op,id,false,resolve,reject);
   try{
    if(child.stdin.write(frame)){pending.written=true;complete();}
    else child.stdin.once('drain',function(){if(pending&&pending.id===id){pending.written=true;complete();}});
   }catch(e){fail(error('STOP_IO_WRITE'));}
  });
 };
 child.stdout.on('data',function(chunk){
  if(c.fatal)return;
  if(!Buffer.isBuffer(chunk)||chunk.length>MAX_REPLY+HEADER){fail(error('STOP_IO_FRAME'));return;}
  try{
   if(!pending||pending.answer)throw error('STOP_IO_UNEXPECTED');
   var offset=0;
   while(offset<chunk.length){
    if(headerUsed<HEADER){var h=Math.min(HEADER-headerUsed,chunk.length-offset);chunk.copy(header,headerUsed,offset,offset+h);headerUsed+=h;offset+=h;if(headerUsed<HEADER)break;}
    if(body===null){
     if(header[0]!==67||header[1]!==89||header[2]!==73||header[3]!==49||header[4]!==pending.op||header[5]>4||header[6]||header[7]||header.readUInt32BE(8)!==pending.id)throw error('STOP_IO_FRAME');
     var len=header.readUInt32BE(12);if(len>MAX_REPLY)throw error('STOP_IO_FRAME');body=Buffer.alloc(len);bodyUsed=0;
    }
    var n=Math.min(body.length-bodyUsed,chunk.length-offset);chunk.copy(body,bodyUsed,offset,offset+n);bodyUsed+=n;offset+=n;
    if(bodyUsed===body.length){
     if(offset!==chunk.length)throw error('STOP_IO_TRAILING');
     pending.answer=decode(pending.op,header[5],body);body=null;headerUsed=bodyUsed=0;complete();break;
    }
   }
  }catch(e){fail(e);}
 });
 child.stderr.on('data',function(chunk){stderrBytes+=chunk.length;if(stderrBytes>MAX_STDERR)fail(error('STOP_IO_STDERR_LIMIT'));});
 child.stdin.on('error',function(){fail(error('STOP_IO_PIPE'));});
 child.stdout.on('error',function(){fail(error('STOP_IO_PIPE'));});
 child.stderr.on('error',function(){fail(error('STOP_IO_PIPE'));});
 child.on('error',function(){fail(error('STOP_IO_SPAWN'));});
 child.stdout.on('end',function(){if(!terminal&&!c.fatal)fail(error('STOP_IO_EOF'));});
 child.on('close',function(code,signal){
  closed=true;if((!terminal||code!==0||signal)&&!c.fatal)fail(error('STOP_IO_CHILD_CLOSE'));
  resolveClosed({code:code,signal:signal});
 });
 return c;
}
function create(){
 if(arguments.length)throw error('STOP_IO_NO_OPTIONS');
 var connection=null,busy=false,ended=false,scope=null,closePromise=null;
 function get(){if(!connection)connection=transport(function(){ended=true;if(scope)scope.open=false;});return connection;}
 function cancel(){ended=true;if(scope)scope.open=false;if(!connection)return Promise.resolve();connection.fail(error('STOP_IO_CANCELLED'));return connection.closed.then(function(){});}
 function close(){
  if(closePromise)return closePromise;
  ended=true;
  if(!connection)return Promise.resolve();
  if(busy||connection.fatal)return cancel();
  var c=connection;
  closePromise=c.ready.then(function(){return c.command(CLOSE);}).then(function(){return c.closed;}).then(function(){if(c.fatal)throw c.fatal;},function(e){c.fail(e);return c.closed.then(function(){});});
  return closePromise;
 }
 function transaction(callback){
  if(typeof callback!=='function'||ended)return Promise.reject(error('STOP_IO_CLOSED'));
  if(busy)return Promise.reject(error('STOP_IO_BUSY'));
  busy=true;var c=get(),s={open:true,inflight:null},finished=false,finishing=false;
  scope=s;
  return new Promise(function(resolve,reject){
   function done(value,err){if(finished)return;finished=true;s.open=false;scope=null;busy=false;if(err)reject(err);else resolve(value);}
   function abort(err){c.fail(err);c.closed.then(function(){done(null,err);});}
   function finish(value,err){
    if(finished||finishing)return;finishing=true;s.open=false;
    var drain=s.inflight||Promise.resolve();
    drain.then(function(){if(c.fatal)throw c.fatal;return c.command(END);}).then(function(){done(value,err);},abort);
   }
   function readJournal(){
    if(!s.open||c.fatal)return Promise.reject(error('STOP_IO_SCOPE_CLOSED'));
    if(s.inflight)return Promise.reject(error('STOP_IO_BUSY'));
    var operation=c.command(READ).then(function(value){s.inflight=null;return value;},function(e){s.inflight=null;throw e;});
    s.inflight=operation.then(function(){},function(){});
    return operation;
   }
   c.closed.then(function(){if(c.fatal)done(null,c.fatal);});
   c.ready.then(function(){if(!s.open||c.fatal)throw c.fatal||error('STOP_IO_SCOPE_CLOSED');return c.command(BEGIN);}).then(function(){
    if(!s.open||c.fatal)throw c.fatal||error('STOP_IO_SCOPE_CLOSED');
    return Promise.resolve().then(function(){return callback({readJournal:readJournal});}).then(function(value){finish(value,s.inflight?error('STOP_IO_EARLY_RETURN'):null);},function(e){finish(null,e);});
   }).then(null,abort);
  });
 }
 return {withControllerTransaction:transaction,close:close,cancel:cancel};
}
module.exports=create();
module.exports.create=create;
