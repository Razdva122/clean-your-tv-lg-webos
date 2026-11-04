'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path'),vm=require('node:vm');
const root=fs.mkdtempSync(path.join(os.tmpdir(),'home-service-jail-'));
const own='/media/developer/apps/usr/palm/services/com.gathin.tvhome.renewal';
const methods={},writes=[];
// Model the service mount namespace: its own package exists; the Helper app
// remains absent even though a native controller can access it outside this jail.
function local(p){if(!p.startsWith(own+'/')){const e=new Error('outside service jail');e.code='ENOENT';throw e;}return root+p.slice(own.length);}
const jailed={readFileSync:p=>fs.readFileSync(local(p),'utf8'),existsSync:p=>fs.existsSync(local(p)),mkdirSync:p=>fs.mkdirSync(local(p)),
 writeFileSync(p,b,o){writes.push(p);fs.writeFileSync(local(p),b,o);},chmodSync:(p,m)=>fs.chmodSync(local(p),m),
 renameSync(a,b){fs.renameSync(local(a),local(b));if(/\/(home|input)-request[.]json$/.test(b)){
  const request=JSON.parse(fs.readFileSync(local(b),'utf8'));
  fs.writeFileSync(local(b.replace('-request','-response')),JSON.stringify(request.method==='inputStatus'?{id:request.id,returnValue:true,devices:[{appId:'com.webos.app.hdmi3',connected:true}]}:{id:request.id,returnValue:true,enabled:true}));
 }}};
function Service(){this.register=(n,f)=>{methods[n]=f;};this.call=()=>{throw Error('no network or launch expected');};}
fs.mkdirSync(root+'/state/home-control',{recursive:true});
vm.runInNewContext(fs.readFileSync('renewal-service/service.js','utf8'),{__dirname:own,setTimeout,clearTimeout,require(n){
 if(n==='fs')return jailed;if(n==='webos-service')return Service;
 if(n==='./manager')return()=>({});if(n==='./local-io')return{createLocalIO:()=>({})};
 if(n==='./transport')return{createRequest:()=>{}};if(n==='./renewal')return{createRenewal:()=>({})};
 return require('../renewal-service/'+n.slice(2));
}});
function call(app,method='homeStatus',payload={}){return new Promise(resolve=>methods[method]({payload,ls2Message:{applicationID:()=>app},respond:resolve}));}
(async()=>{try{
 assert.equal((await call('other.app')).returnValue,false);assert.equal(writes.length,0,'authorization precedes all I/O');
 assert.equal(typeof methods.inputStatus,'function','same-package service must expose a fixed authorized input read');
 assert.equal((await call('other.app','inputStatus')).returnValue,false);assert.equal(writes.length,0);
 assert.equal((await call('com.gathin.tvhome','inputStatus',{uri:'PRIVATE'})).returnValue,false);assert.equal(writes.length,0);
 const reply=await call('com.gathin.tvhome');
 assert.equal(reply.returnValue,true,JSON.stringify(reply));assert.equal(reply.enabled,true);
 assert.deepEqual(writes,[own+'/state/home-control/home-request.tmp'],'service never needs the other app mount');
 const inputs=await call('com.gathin.tvhome','inputStatus');assert.equal(inputs.devices[0].connected,true);
 console.log('PASS actual service Home RPC in a service-only filesystem namespace');
}finally{fs.rmSync(root,{recursive:true,force:true});}})().catch(e=>{console.error(e);process.exitCode=1;});
