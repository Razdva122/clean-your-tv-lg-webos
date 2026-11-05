'use strict';
const assert=require('assert/strict'),vm=require('vm'),fs=require('fs'),http=require('http');
const core=require('../../theme-receiver/core');
async function cacheCheck(existing,bytes,expected){
 let written=false;
 const database={transaction(){let aborted=false;const tx={abort(){aborted=true;Promise.resolve().then(()=>tx.onabort());},objectStore(){return {openCursor(){const cursor={};let i=0;function step(){cursor.result=i<existing.length?{key:'stored-'+i,value:existing[i++],continue(){Promise.resolve().then(step);}}:null;cursor.onsuccess();}Promise.resolve().then(step);return cursor;},put(){written=true;Promise.resolve().then(()=>{if(!aborted)tx.oncomplete();});}};}};return tx;}};
 const context={Promise,setTimeout,clearTimeout,indexedDB:{open(){const request={result:database};Promise.resolve().then(()=>request.onsuccess());return request;}}};vm.runInNewContext(fs.readFileSync('launcher/theme-store.js','utf8'),context);
 const operation=context.ThemeStore.put({digest:'incoming',descriptor:new ArrayBuffer(bytes),files:{}},bytes);
 if(expected)await operation;else await assert.rejects(operation,/storage/);assert.equal(written,expected);
}
async function run(){
 const stored={descriptor:new ArrayBuffer(22*1024*1024),files:{}};
 await cacheCheck([stored],22*1024*1024,true);await cacheCheck([stored,stored],22*1024*1024,false);
 await cacheCheck(Array(7).fill({descriptor:new ArrayBuffer(1),files:{}}),1,true);await cacheCheck(Array(8).fill({descriptor:new ArrayBuffer(1),files:{}}),1,false);
 const receiver=core.create({port:0});const s=await receiver.start();
 function post(body,headers){return new Promise((resolve,reject)=>{const req=http.request({host:'127.0.0.1',port:s.port,path:'/v1/theme',method:'POST',headers:Object.assign({Host:'127.0.0.1:'+s.port,'Content-Type':'application/json','X-CYTV-PIN':s.pin},headers)},res=>{res.resume();res.on('end',()=>resolve(res.statusCode));});req.on('error',reject);req.end(body);});}
 try{
  assert.equal(await post('{}',{'Content-Length':require('../../launcher/theme-policy.js').limits.envelopeBytes+1}),413);
  const body=JSON.stringify({schemaVersion:1,descriptor:'e30=',files:{'wallpaper.mp4':Buffer.alloc(8*1024*1024).toString('base64')}});assert(body.length>10*1024*1024);assert.equal(await post(body),202);assert.equal(receiver.status(s.sessionId).size,Buffer.byteLength(body));
 }finally{await receiver.stop(s.sessionId);}
 console.log('PASS 64MiB/eight-version cache and video-sized receiver envelope bounds');
}
run().catch(e=>{console.error(e);process.exitCode=1;});
