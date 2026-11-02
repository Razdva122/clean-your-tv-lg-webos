'use strict';
// Real generated trust validator, with an in-memory root-owned TV filesystem.
var assert=require('assert'),fs=require('fs'),path=require('path'),crypto=require('crypto'),Module=require('module'),cp=require('child_process');
var base=process.argv[2],state='/var/lib/clean-your-tv-root',pin='4a71641c8d5536175e404a961624e8656eba30e97b5026f6bd7dc31e4bbeaaea';
var executable='/var/lib/clean-your-tv-python/'+pin+'/bin/python3.13',slot=path.dirname(path.dirname(executable)),files,metadata,spawns,load=Module._load;
function digest(raw){return crypto.createHash('sha256').update(raw).digest('hex');}
var fakeFs={lstatSync:function(name){
 if(!Object.prototype.hasOwnProperty.call(files,name)&&(name===state+'/python-launcher'||name===state+'/python-runtime.json')){var e=Error();e.code='ENOENT';throw e;}
 var file=Object.prototype.hasOwnProperty.call(files,name),meta=metadata[name]||{};
 return {uid:meta.uid===undefined?0:meta.uid,mode:meta.mode===undefined?(file?33216:16877):meta.mode,nlink:meta.nlink===undefined?1:meta.nlink,size:file?Buffer.byteLength(files[name]):0,isSymbolicLink:function(){return !!meta.link;},isFile:function(){return file;},isDirectory:function(){return !file;}};
},readFileSync:function(name,encoding){return encoding?files[name]:Buffer.from(files[name]);}};
var child={spawnSync:function(){spawns++;return {status:17};}};
var copies=['root/python_boot.js','root-updater/python_boot.js','system/python_boot.js','infrastructure/support/python_boot.js','infrastructure/updater/python_boot.js'];
copies.forEach(function(copy){
 var file=base+'/'+copy;
 Module._load=function(name,parent,isMain){if(parent&&parent.filename===file&&name==='fs')return fakeFs;if(parent&&parent.filename===file&&name==='child_process')return child;return load.call(this,name,parent,isMain);};
 var helper=require(file);files={};metadata={};spawns=0;assert.equal(helper.command(state),'/usr/bin/python3');
 function restore(){metadata={};files={};files[executable]='verified-python';files[slot+'/.cytv-runtime.json']=JSON.stringify({schema:1,archive_sha256:pin,files:{'bin/python3.13':digest(files[executable])}});files[state+'/python-runtime.json']=JSON.stringify({schema:1,executable:executable,archive_sha256:pin,inventory_sha256:digest(files[slot+'/.cytv-runtime.json'])});files[state+'/python-launcher']='#!/bin/sh\nunset PYTHONHOME PYTHONPATH\nexport PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1\nexec '+executable+' "$@"\n';}
 restore();assert.equal(helper.command(state),state+'/python-launcher');assert.equal(helper.run(state,state+'/runtime/cli.py',['boot']),17);assert.equal(spawns,1);spawns=0;
 [function(){files[state+'/python-launcher']='#!/bin/sh\nreboot\n';},function(){delete files[state+'/python-runtime.json'];},function(){metadata[state+'/python-launcher']={link:true};},function(){metadata[state+'/python-runtime.json']={nlink:2};},function(){metadata[state]={mode:16895};},function(){metadata[state+'/python-runtime.json']={uid:1};},function(){files[executable]='tampered';},function(){files[slot+'/.cytv-runtime.json']='{}';}].forEach(function(fault){restore();fault();assert.throws(function(){helper.run(state,state+'/runtime/cli.py',['boot']);});assert.equal(spawns,0);});
 restore();assert.throws(function(){helper.run(state,state+'/../foreign.py',[]);});assert.throws(function(){helper.run(state,'/outside.py',[]);});assert.equal(spawns,0);
 Module._load=load;
});
// Exercise Node's actual synchronous child path through the generated binding.
var real=require(base+'/root/python_boot.js'),stateDir=base+'/system-python-'+process.version;
fs.mkdirSync(stateDir);fs.writeFileSync(stateDir+'/child.py','import sys\nsys.exit(7)\n');
assert.equal(real.run(stateDir,stateDir+'/child.py',[]),7);
console.log('PASS Root generated Python binding '+process.version+': five copies reject tampering/unsafe paths before spawn; real child status preserved');
