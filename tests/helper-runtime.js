// ES5: executed unchanged by Node 0.10.25, 0.12.2 and current Node.
'use strict';
var assert=require('assert'),path=require('path'),root=process.argv[2];
require(path.join(root,'state-permissions'));
assert.equal(typeof Object.assign,'function');
assert.equal(typeof Promise,'function');
assert.equal(typeof Symbol,'function');
assert.equal(Buffer.from('hello').toString(),'hello');
var WebSocket=require(path.join(root,'websocket'));
var rejected=0;
function receiver(limit){return Number(process.versions.node.split('.')[0])<10?
 new WebSocket.Receiver('nodebuffer',{},limit,1024,1024):new WebSocket.Receiver({maxPayload:limit});}
var invalid=receiver(65536);invalid.on('error',function(e){assert(/UTF-8/.test(e.message));rejected++;});
invalid.write(Buffer.from([0x81,2,0xc0,0xaf]));
var oversized=receiver(2);oversized.on('error',function(e){assert(/payload/i.test(e.message));rejected++;});
oversized.write(Buffer.from([0x81,3,0x61,0x62,0x63]));
// Only TV hardware and Luna are substituted; execute the compiled controller
// and its real policies under the selected Node runtime.
var vm=require('vm'),fs=require('fs'),Emitter=require('events').EventEmitter;
// Exercise the key replacement against real files, including the descriptor
// read on Node 0.10. Never substitute a pathname read after opening the key.
if(process.getuid){
 var state=path.join(root,'runtime-state-'+process.version),secure=require(path.join(root,'state-permissions'));
 fs.mkdirSync(state,504);fs.chmodSync(state,504);
 fs.writeFileSync(path.join(state,'ssap-key.json'),JSON.stringify({key:'runtime-test'}));
 fs.chmodSync(path.join(state,'ssap-key.json'),384);
 var chmod=fs.fchmodSync,denied=false;
 fs.fchmodSync=function(fd,mode){
  if(mode===416&&!denied){denied=true;var e=Error('foreign key');e.code='EPERM';throw e;}
  return chmod.apply(fs,arguments);
 };
 try{assert.equal(secure(state),true);
  assert(denied,'exercise foreign-key replacement');
  assert.equal(JSON.parse(fs.readFileSync(path.join(state,'ssap-key.json'),'utf8')).key,'runtime-test');
  assert.equal(fs.statSync(path.join(state,'ssap-key.json')).mode&511,416);
  assert.equal(secure(state,null,true),true);
  assert.equal(fs.readFileSync(path.join(state,'control.json'),'utf8'),'{}');
 }finally{fs.fchmodSync=chmod;}
}
var logs=[],handlers={},commands=[],start,fatalExit,exitCode,failLog=false;
var worker=new Emitter();worker.stdin=new Emitter();worker.stdout=new Emitter();worker.stderr=new Emitter();
worker.stdin.write=function(command){commands.push(command);};worker.stdin.end=function(){throw Error('broken pipe');};
var fakefs={existsSync:function(){return false;},writeFileSync:function(){},chmodSync:function(){},unlinkSync:function(){},
 readFileSync:function(){var error=Error('absent');error.code='ENOENT';throw error;},appendFileSync:function(file,raw){if(failLog)throw Error('disk full');logs.push(JSON.parse(raw));}};
function Service(){this.activityManager={create:function(){}};this.call=function(uri,payload,done){done({payload:{returnValue:true,state:{enabled:true,schema:3}}});};}
var context={Object:Object,Buffer:Buffer,console:{error:function(){}},require:function(name){
 if(name==='fs')return fakefs;
 if(name==='child_process')return{spawn:function(){return worker;}};
 if(name==='/usr/lib/node_modules/webos-service')return Service;
 if(name==='./state-permissions')return function(){return true;};
 if(name==='./screen-watch')return function(){return{close:function(){}};};
 return require(path.join(root,name));
},process:{argv:['node','native.js','{"nativeHomeAuto":true}'],pid:1,getuid:function(){return 6252;},hrtime:function(){return[0,0];},
 on:function(name,handler){handlers[name]=handler;},exit:function(code){exitCode=code;}},
 setTimeout:function(fn,ms){if(ms===0)start=fn;if(ms===2500)fatalExit=fn;return 1;},clearTimeout:function(){},
 setInterval:function(){return 1;},clearInterval:function(){}};
vm.runInNewContext(fs.readFileSync(path.join(root,'native.js'),'utf8'),context);
assert.equal(logs[0].event,'start');start();worker.stdout.emit('data',Buffer.from('READY\n'));
assert(commands.indexOf('E')!==-1,'controller starts relay and enables Home');
handlers.uncaughtException(Error('original failure'));
assert(logs.some(function(record){return record.error==='Error: original failure'&&record.stack.indexOf('original failure')!==-1;}));
failLog=true;handlers.uncaughtException(Error('disk full path'));handlers.exit(2);fatalExit();assert.equal(exitCode,2);
function checkService(port,done){
 var serviceRoot=path.join(root,'service'),methods={};
 var serviceFs={readFileSync:function(file){
  if(file==='/proc/sys/kernel/random/boot_id')return 'boot-id';
  if(file==='/proc/stat')return 'btime 123\n';
  if(/controller.pid$/.test(file))return '123';
  if(file==='/proc/123/cmdline')return 'node\0/media/developer/apps/usr/palm/applications/com.local.nativehome/native.js\0';
  var e=Error('absent');e.code='ENOENT';throw e;
 },statSync:function(){var e=Error('absent');e.code='ENOENT';throw e;}};
 function StatusService(){this.register=function(name,fn){methods[name]=fn;};}
 var serviceContext={__dirname:serviceRoot,console:{error:function(){}},require:function(name){
  if(name==='fs')return serviceFs;
  if(name==='webos-service')return StatusService;
  if(name==='./state-permissions')return function(){return true;};
  if(name==='./app-inventory')return function(){return require(path.join(serviceRoot,'app-inventory'))({
   readKey:function(){return{key:'test'};},interfaces:function(){return{lan:[{internal:false,family:'IPv4',address:'127.0.0.1'}]};},
   WebSocket:function(url,options){assert.equal(url,'wss://127.0.0.1:3001');return new WebSocket('wss://127.0.0.1:'+port,options);}
  });};
  return require(path.join(serviceRoot,name));
 }};
 vm.runInNewContext(fs.readFileSync(path.join(serviceRoot,'service.js'),'utf8'),serviceContext);
 methods.status({respond:function(reply){assert.equal(reply.returnValue,true);assert.equal(reply.running,true);assert.equal(reply.blocked,false);}});
 methods.listApps({respond:function(reply){assert.equal(reply.returnValue,true);assert.equal(reply.apps[0].id,'com.example.video');done();}});
}
var httpsServer=require('https').createServer({key:fs.readFileSync(path.join(root,'test-key.pem')),cert:fs.readFileSync(path.join(root,'test-cert.pem'))});
var server=new WebSocket.Server({server:httpsServer,perMessageDeflate:false});
var deadline=setTimeout(function(){throw Error('WebSocket exchange timed out');},10000);
server.on('listening',function(){
 var client=new WebSocket('wss://127.0.0.1:'+httpsServer.address().port,{rejectUnauthorized:false,perMessageDeflate:false,maxPayload:65536});
 client.on('error',function(e){throw e;});
 client.on('open',function(){client.send(JSON.stringify({type:'register',payload:{'client-key':'test'}}));});
 client.on('message',function(raw){
  var message=JSON.parse(String(raw));
  if(message.type==='registered')client.send(JSON.stringify({type:'subscribe',id:'foreground'}));
  else {assert.equal(message.payload.appId,'com.gathin.tvhome');client.ping('alive');}
 });
 client.on('pong',function(raw){assert.equal(String(raw),'alive');client.close();});
 client.on('close',function(){checkService(httpsServer.address().port,function(){server.close(function(){httpsServer.close(function(){assert.equal(rejected,2,'invalid UTF-8 and oversized frames must be rejected');clearTimeout(deadline);console.log('PASS Helper runtime '+process.version+': controller startup/error handling, service status/listApps, polyfills, WSS register/subscribe, fragmented UTF-8, ping/pong, close, invalid frame limits');});});});});
});
httpsServer.listen(0,'127.0.0.1');
server.on('connection',function(socket){
 socket.on('message',function(raw){
  var message=JSON.parse(String(raw));
  if(message.type==='register')socket.send('{"type":"registered"}');
  else if(message.id==='apps')socket.send('{"id":"apps","payload":{"launchPoints":[{"id":"com.example.video"}]}}');
  else {socket.send('{"payload":{"appId":"com.',{fin:false});socket.send('gathin.tvhome","label":"Привет"}}',{fin:true});}
 });
});
