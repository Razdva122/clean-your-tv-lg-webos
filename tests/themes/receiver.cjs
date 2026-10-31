'use strict';
const assert=require('assert/strict'),http=require('http'),net=require('net'),fs=require('fs'),acorn=require('acorn');
const core=require('../../theme-receiver/core'),register=require('../../theme-receiver/register');
const body=JSON.stringify({schemaVersion:1,descriptor:'e30=',files:{'rules.json':'e30='}});
function post(s,content=body,headers={}){return new Promise((resolve,reject)=>{const req=http.request({host:'127.0.0.1',port:s.port,path:'/v1/theme',method:'POST',headers:Object.assign({'Host':'127.0.0.1:'+s.port,'Content-Type':'application/json','X-CYTV-PIN':s.pin},headers)},res=>{res.resume();res.on('end',()=>resolve(res.statusCode));});req.on('error',reject);req.end(content);});}
const delay=ms=>new Promise(r=>setTimeout(r,ms));
async function test(){
 for(const f of ['core','register'])acorn.parse(fs.readFileSync(require.resolve('../../theme-receiver/'+f),'utf8'),{ecmaVersion:5});
 const r=core.create({port:0});let s=await r.start();
 await assert.rejects(r.start(),/receiver-busy/);
 assert.match(s.pin,/^\d{6}$/);assert.match(s.sessionId,/^[a-f0-9]{32,}$/);assert(!s.addresses.some(a=>a.indexOf('127.')===0),'advertise only private LAN addresses');
 assert.deepEqual(r.status(s.sessionId),{state:'waiting',size:0});
 assert.equal(await post(s,body,{'X-CYTV-PIN':'000000'===s.pin?'111111':'000000'}),403);
 assert.equal(await post(s,body,{'Host':'localhost:'+s.port}),403);
 assert.equal(await post(s,body,{'Origin':'null'}),403);
 for(const invalid of ['{}','null','[]',JSON.stringify({schemaVersion:1,descriptor:'!!!!',files:{}}),JSON.stringify({schemaVersion:1,descriptor:'e30=',files:[]}),JSON.stringify({schemaVersion:1,descriptor:'e30=',files:{a:12}})])assert.equal(await post(s,invalid),400);
 assert.equal(await post(s,body,{'Host':'127.0.0.2:'+s.port}),403);
 assert.equal(await post(s,body,{'Content-Type':'text/plain'}),415);
 assert.equal(await post(s,'{}'),400);assert.equal(r.status(s.sessionId).state,'waiting');
 assert.equal(await post(s),202);assert.deepEqual(r.status(s.sessionId),{state:'received',size:Buffer.byteLength(body)});
 assert.throws(()=>r.read(s.sessionId,-1));assert.throws(()=>r.read(s.sessionId,1));
 let chunk=r.read(s.sessionId,0);assert.equal(Buffer.from(chunk.data,'base64').toString(),body);assert(chunk.done);assert.equal(chunk.nextOffset,Buffer.byteLength(body));
 await delay(10);await assert.rejects(post(s));
 assert.throws(()=>r.read('bad',0));await r.stop(s.sessionId);assert.throws(()=>r.status(s.sessionId));
 s=await r.start();await r.stop(s.sessionId);await assert.rejects(post(s));
 const exp=core.create({port:0,ttlMs:35});s=await exp.start();await delay(60);assert.throws(()=>exp.status(s.sessionId));
 const wrong=core.create({port:0,maxWrongPins:2});s=await wrong.start();await post(s,body,{'X-CYTV-PIN':'bad'});await post(s,body,{'X-CYTV-PIN':'bad'});await delay(10);assert.throws(()=>wrong.status(s.sessionId));
 const small=core.create({port:0,maxBytes:50});s=await small.start();assert.equal(await post(s),413);assert.equal(await post(s,body,{'Transfer-Encoding':'chunked'}),413);await small.stop(s.sessionId);
 const aborted=core.create({port:0});s=await aborted.start();let req=http.request({host:'127.0.0.1',port:s.port,path:'/v1/theme',method:'POST',headers:{Host:'127.0.0.1:'+s.port,'Content-Type':'application/json','X-CYTV-PIN':s.pin,'Content-Length':500}});req.on('error',()=>{});req.write('{');await delay(20);assert.equal(aborted.status(s.sessionId).state,'receiving');req.destroy();await delay(20);assert.equal(aborted.status(s.sessionId).state,'waiting');await aborted.stop(s.sessionId);
 const timeout=core.create({port:0,requestTimeoutMs:35});s=await timeout.start();
 let sock=net.connect(s.port,'127.0.0.1');await new Promise(resolve=>sock.once('connect',resolve));sock.write('POST /v1/theme HTTP/1.1\r\nHost: 127.0.0.1:'+s.port+'\r\nContent-Type: application/json\r\nX-CYTV-PIN: '+s.pin+'\r\nContent-Length: 100\r\n\r\n{');await delay(10);assert.equal(timeout.status(s.sessionId).state,'receiving');assert.equal(await post(s),409);sock.resume();await delay(70);assert.equal(timeout.status(s.sessionId).state,'waiting');sock.destroy();await timeout.stop(s.sessionId);
 const large=core.create({port:0});s=await large.start();const data=JSON.stringify({schemaVersion:1,descriptor:'e30=',files:{'big':Buffer.alloc(2*1024*1024,97).toString('base64')}});assert.equal(await post(s,data),202);chunk=large.read(s.sessionId,0);assert.equal(Buffer.from(chunk.data,'base64').length,49152);assert(!chunk.done);assert.throws(()=>large.read(s.sessionId,3));let rebuilt=Buffer.from(chunk.data,'base64');while(!chunk.done){chunk=large.read(s.sessionId,chunk.nextOffset);rebuilt=Buffer.concat([rebuilt,Buffer.from(chunk.data,'base64')]);}assert.equal(rebuilt.toString(),data);await large.stop(s.sessionId);
 const methods={};register({register:(name,fn)=>methods[name]=fn},{appId:'com.test',port:0});
 const call=(name,payload,id,raw=true)=>new Promise(resolve=>methods[name]({payload,ls2Message:raw?{applicationID:()=>id}:undefined,applicationID:()=>id,respond:resolve}));
 for(const name of Object.keys(methods)){assert.equal((await call(name,{appId:'com.test'},'evil')).returnValue,false);assert.equal((await call(name,{},'com.test',false)).returnValue,false);}
 let reply=await call('themeReceiverStart',{},'com.test 123');assert(reply.returnValue);s=reply;
 assert.equal((await call('themeReceiverStatus',{sessionId:s.sessionId},'com.test')).state,'waiting');
 assert.equal((await call('themeReceiverRead',{sessionId:s.sessionId,offset:0},'com.test')).returnValue,false);
 assert.equal((await call('themeReceiverStop',{sessionId:s.sessionId},'com.test')).returnValue,true);
 // A session keeps its hold until it ends, whichever way it ends.
 let holds=0,releases=0;const hold=()=>{holds++;let done=false;return()=>{assert(!done,'release once');done=true;releases++;};};
 const held=core.create({port:0,hold});s=await held.start();assert.deepEqual([holds,releases],[1,0]);assert.equal(await post(s),202);assert.equal(releases,0,'received theme is still read through the session');await held.stop(s.sessionId);assert.deepEqual([holds,releases],[1,1]);
 const heldExp=core.create({port:0,ttlMs:35,hold});s=await heldExp.start();await delay(60);assert.deepEqual([holds,releases],[2,2]);
 const heldWrong=core.create({port:0,maxWrongPins:1,hold});s=await heldWrong.start();await post(s,body,{'X-CYTV-PIN':'bad'});await delay(10);assert.deepEqual([holds,releases],[3,3]);
 const blocker=net.createServer();await new Promise(resolve=>blocker.listen(0,'0.0.0.0',resolve));
 await assert.rejects(core.create({port:blocker.address().port,hold}).start(),/receiver-unavailable/);blocker.close();assert.deepEqual([holds,releases],[4,4]);
 // register() holds a webos-service activity, so the idle timer cannot exit the service mid-session.
 const am={created:[],completed:[],create(name,cb){const a={activityId:this.created.length+1,name};this.created.push(a);cb(a);},complete(a,cb){this.completed.push(a.activityId);cb(a);}};
 const amMethods={};register({register:(name,fn)=>amMethods[name]=fn,activityManager:am},{appId:'com.test',port:0});
 const amCall=(name,payload)=>new Promise(resolve=>amMethods[name]({payload,ls2Message:{applicationID:()=>'com.test'},respond:resolve}));
 reply=await amCall('themeReceiverStart',{});assert(reply.returnValue);assert.equal(am.created.length,1);assert.deepEqual(am.completed,[]);
 assert.equal((await amCall('themeReceiverStop',{sessionId:reply.sessionId})).returnValue,true);assert.deepEqual(am.completed,[1]);
 // An activity granted after the session already ended is completed at once.
 let late;const lateAm={completed:[],create(name,cb){late=cb;},complete(a,cb){this.completed.push(a.activityId);cb(a);}};
 const lateMethods={};register({register:(name,fn)=>lateMethods[name]=fn,activityManager:lateAm},{appId:'com.test',port:0});
 reply=await new Promise(resolve=>lateMethods.themeReceiverStart({payload:{},ls2Message:{applicationID:()=>'com.test'},respond:resolve}));
 await new Promise(resolve=>lateMethods.themeReceiverStop({payload:{sessionId:reply.sessionId},ls2Message:{applicationID:()=>'com.test'},respond:resolve}));
 late({activityId:7});assert.deepEqual(lateAm.completed,[7]);
 if(process.env.NODE012){const result=require('child_process').spawnSync(process.env.NODE012,['-e','('+legacy.toString()+')()'],{cwd:process.cwd(),encoding:'utf8',timeout:60000});assert.equal(result.status,0,result.stderr||result.error);assert.match(result.stdout,/PASS Node 0.12.2/);console.log(result.stdout.trim());}
 console.log('PASS receiver real HTTP, bounds, expiry, one-shot, session activity hold, ES5 and LS2 authorization');
}
function legacy(){
 require(process.cwd()+'/node_modules/core-js-bundle/minified.js');
 var assert=require('assert'),http=require('http'),core=require(process.cwd()+'/theme-receiver/core');
 var bytes=new Buffer(2*1024*1024);bytes.fill(97);
 var body=JSON.stringify({schemaVersion:1,descriptor:'e30=',files:{image:bytes.toString('base64')}}),receiver=core.create({port:0,ttlMs:30000});
 receiver.start().then(function(s){var req=http.request({host:'127.0.0.1',port:s.port,path:'/v1/theme',method:'POST',headers:{Host:'127.0.0.1:'+s.port,'Content-Type':'application/json','X-CYTV-PIN':s.pin}},function(res){
  assert.equal(res.statusCode,202);res.resume();res.on('end',function(){var chunks=[],chunk,offset=0;do{chunk=receiver.read(s.sessionId,offset);chunks.push(new Buffer(chunk.data,'base64'));offset=chunk.nextOffset;}while(!chunk.done);assert.equal(Buffer.concat(chunks).toString(),body);receiver.stop(s.sessionId).then(function(){console.log('PASS Node 0.12.2 actual 2MiB HTTP upload/read/stop');});});
 });req.on('error',function(e){throw e;});req.end(body);}).catch(function(e){console.error(e);process.exit(1);});
}
test().catch(e=>{console.error(e);process.exit(1);});
