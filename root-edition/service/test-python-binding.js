'use strict';
const assert=require('assert'),vm=require('vm'),fs=require('fs'),crypto=require('crypto'),path=require('path'),os=require('os');
const state='/var/lib/clean-your-tv-root',pin='4a71641c8d5536175e404a961624e8656eba30e97b5026f6bd7dc31e4bbeaaea';
const executable='/var/lib/clean-your-tv-python/'+pin+'/bin/python3.13',slot=path.dirname(path.dirname(executable));
const digest=raw=>crypto.createHash('sha256').update(raw).digest('hex');
let files={},metadata={},spawns=0,invoke,allowSpawn=false,lastOptions;
const fakeFs={lstatSync(name){
 if((name===state+'/python-launcher'||name===state+'/python-runtime.json')&&!files[name]){let e=Error();e.code='ENOENT';throw e;}
 const file=Object.prototype.hasOwnProperty.call(files,name),meta=metadata[name]||{};
 return {uid:meta.uid===undefined?0:meta.uid,mode:meta.mode===undefined?(file?0o100700:0o40755):meta.mode,nlink:1,size:file?Buffer.byteLength(files[name]):0,isSymbolicLink:()=>!!meta.link,isFile:()=>file,isDirectory:()=>!file};
},readFileSync(name,encoding){return encoding?files[name]:Buffer.from(files[name]);},existsSync(name){return Object.prototype.hasOwnProperty.call(files,name);}};
const marker=path.join(fs.mkdtempSync(path.join(os.tmpdir(),'root-binding-')),'executed');
const child={execFile(command,args,options,callback){spawns++;if(!allowSpawn)throw Error('unexpected service spawn');lastOptions=options;callback(null,'{"returnValue":true}');return {};},spawnSync(command){
 spawns++;
 if(files[command]&&files[command].indexOf('touch ')!==-1)require('child_process').execFileSync('/bin/sh',['-c',files[command]]);
 return {status:0};
}};
const helperModule={exports:{}};
vm.runInNewContext(fs.readFileSync(__dirname+'/../python_boot.js','utf8'),{module:helperModule,require(name){
 if(name==='fs')return fakeFs;if(name==='child_process')return child;return require(name);
}});
const helper=helperModule.exports;
vm.runInNewContext(fs.readFileSync(__dirname+'/service.js','utf8'),{require(name){
 if(name==='webos-service')return function(){this.register=function(){};};
 if(name==='./handlers'){const handlers=fn=>{invoke=fn;return {};};handlers.audio=require('./handlers').audio;return handlers;}
 if(name==='child_process')return child;
 if(name==='fs')return fakeFs;
 if(name===state+'/python_boot.js')return helper;
 return require(name);
},__dirname,process:{getuid:()=>0}});
(async()=>{
 assert.equal(helper.command(state),'/usr/bin/python3');
 files[executable]='verified-python';
 files[slot+'/.cytv-runtime.json']=JSON.stringify({schema:1,archive_sha256:pin,files:{'bin/python3.13':digest(files[executable])}});
 const receipt=JSON.stringify({schema:1,executable,archive_sha256:pin,inventory_sha256:digest(files[slot+'/.cytv-runtime.json'])});
 const launcher='#!/bin/sh\nunset PYTHONHOME PYTHONPATH\nexport PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1\nexec '+executable+' "$@"\n';
 function restore(){metadata={};files[state+'/python-runtime.json']=receipt;files[state+'/python-launcher']=launcher;files[executable]='verified-python';}
 restore();assert.equal(helper.command(state),state+'/python-launcher');
 assert.equal(helper.run(state,state+'/runtime/cli.py',['boot']),0);assert.equal(spawns,1);spawns=0;
 const faults=[
  ()=>{files[state+'/python-launcher']='#!/bin/sh\ntouch '+marker+'\n';},
  ()=>{delete files[state+'/python-runtime.json'];},
  ()=>{files[state+'/python-runtime.json']=receipt.replace(pin,'a'.repeat(64));},
  ()=>{metadata[state+'/python-launcher']={link:true};},
  ()=>{metadata[state+'/python-launcher']={mode:0o100777};},
  ()=>{metadata[state]={mode:0o40777};},
  ()=>{metadata[state+'/python-runtime.json']={uid:1};},
  ()=>{files[executable]='changed-python';}
 ];
 for(const fault of faults){
  restore();fault();
  assert.throws(()=>helper.run(state,state+'/runtime/cli.py',['boot']));
  await assert.rejects(()=>invoke('boot'));
  assert.equal(spawns,0,'boot spawned before binding verification');
  assert.equal(fs.existsSync(marker),false,'altered launcher executed');
 }
 restore();allowSpawn=true;
 await invoke('enable');assert.equal(lastOptions.timeout,30000,'normal backend deadline remains unchanged');
 files[state+'/home-backend.json']='experimental';
 await invoke('enable');assert.equal(lastOptions.timeout,90000,'gate permits delayed stock close and idle handoff');
 await invoke('status');assert.equal(lastOptions.timeout,30000,'descriptor does not extend other operations');
 console.log('Root service and boot reject invalid Python bindings before execution');
})().catch(error=>{console.error(error);process.exitCode=1;});
