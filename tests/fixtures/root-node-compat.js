'use strict';
// ES5 test driver: execute generated files on the actual selected Node runtime.
var assert=require('assert'),fs=require('fs'),path=require('path'),crypto=require('crypto'),Module=require('module');
var base=process.argv[2],files=[];
function walk(dir){fs.readdirSync(dir).forEach(function(name){var file=path.join(dir,name);if(fs.statSync(file).isDirectory())walk(file);else if(/\.js$/.test(name)&&file.indexOf('/usr/palm/applications/')<0){try{new Function(fs.readFileSync(file,'utf8'));}catch(error){error.message=file+': '+error.message;throw error;}files.push(file);}});}
['root','root-updater','system','root-ipk','root-updater-ipk','system-ipk','infrastructure'].forEach(function(name){walk(base+'/'+name);});
var fetch=require(base+'/root-updater/updater/fetch'),policy=require(base+'/system/system_updater/policy');
var release='https://github.com/Razdva122/clean-your-tv-lg-webos/releases/download/v1.2.3/';
var manifest={schema:1,edition:'root',application:'com.cleanyourtv.root.preview',release:'v1.2.3',version:'1.2.3',runtime:1,updater:1,profile:1,url:release+'com.cleanyourtv.root.preview_1.2.3_all.ipk',sha256:new Array(65).join('a'),size:8,notes:'fixture'};
function signed(m){var bytes=Buffer.from(JSON.stringify(m)),signer=crypto.createSign('RSA-SHA256');signer.update(bytes);signer.end();return {payload:bytes.toString('base64'),signature:signer.sign(fs.readFileSync(base+'/key.pem')).toString('base64')};}
var pub=crypto.createPublicKey?crypto.createPublicKey(fs.readFileSync(base+'/key.pem')):fs.readFileSync(base+'/cert.pem');
assert.equal(fetch.verify(signed(manifest),pub).version,'1.2.3');
var tampered=signed(manifest);tampered.payload=Buffer.from('{}').toString('base64');assert.throws(function(){fetch.verify(tampered,pub);});
assert.throws(function(){fetch.verify({payload:'!',signature:'!'},pub);});
var systemManifest={schema:1,edition:'root',release:'v1.2.3',supervisor:1,notes:'fixture',components:[
 {name:'root',kind:'ipk',application:'com.cleanyourtv.root.preview',version:'1.2.3',url:release+'root.ipk',sha256:new Array(65).join('a'),size:8},
 {name:'root-updater',kind:'ipk',application:'com.cleanyourtv.root.updater',version:'1.2.3',url:release+'updater.ipk',sha256:new Array(65).join('a'),size:8},
 {name:'root-infrastructure',kind:'infrastructure',version:'1.2.3',url:release+'infra.tar.gz',sha256:new Array(65).join('a'),size:8}]};
assert.equal(policy.verify(signed(systemManifest),pub).edition,'root');
// Exercise the generated standalone CLI entry points with their packaged key
// first, then copy only the JS into a disposable synthetic-key test directory.
var cp=require('child_process'),cliDir=base+'/cli-'+process.version;
fs.mkdirSync(cliDir);
[[base+'/root-updater/updater/fetch.js',manifest],[base+'/system/system_updater/policy.js',systemManifest]].forEach(function(item,index){
 var proof=signed(item[1]);
 var denied=cp.spawnSync(process.execPath,[item[0],'verify'],{input:JSON.stringify({proof:proof}),encoding:'utf8'});
 assert.notEqual(denied.status,0,'packaged release key must reject the fixture signing key');
 var target=cliDir+'/policy'+index+'.js';fs.writeFileSync(target,fs.readFileSync(item[0]));
 fs.writeFileSync(cliDir+'/release-public.pem',fs.readFileSync(base+'/public.pem'));
 var accepted=cp.spawnSync(process.execPath,[target,'verify'],{input:JSON.stringify({proof:proof}),encoding:'utf8'});
 assert.equal(accepted.status,0,accepted.stderr);assert.equal(JSON.parse(accepted.stdout).edition,'root');
 proof.signature=Buffer.alloc(256).toString('base64');
 assert.notEqual(cp.spawnSync(process.execPath,[target,'verify'],{input:JSON.stringify({proof:proof})}).status,0);
});
var invalid=JSON.parse(JSON.stringify(systemManifest));invalid.components[0].application='org.other';assert.throws(function(){policy.verify(signed(invalid),pub);});
[fetch,policy].forEach(function(p){
 assert.equal(p.allowed(manifest.url),true);
 ['http://github.com/Razdva122/clean-your-tv-lg-webos/releases/x','https://user:pass@github.com/Razdva122/clean-your-tv-lg-webos/releases/x','https://github.com:444/Razdva122/clean-your-tv-lg-webos/releases/x','https://github.com.evil/Razdva122/clean-your-tv-lg-webos/releases/x','https://github.com/other/releases/x','https://github.com/Razdva122/clean-your-tv-lg-webos/releases/../../other','file:///etc/passwd','not a url'].forEach(function(url){assert.equal(p.allowed(url),false,url);});
 assert.equal(p.allowed('https://release-assets.githubusercontent.com/a?token=fixture'),true);
});
var ROOT='com.cleanyourtv.root.preview',registrations={},executed=[],load=Module._load,uid=process.getuid;
function Service(id){this.register=function(method,handler){registrations[id+'/'+method]=handler;};}
var child={execFile:function(command,args,options,callback){executed.push({command:command,args:args});var stdin={end:function(payload){assert.equal(typeof JSON.parse(payload),'object');callback(null,JSON.stringify({returnValue:true,result:{fixture:true}}));}};
 if(args[0]==='-n')callback(null,JSON.stringify({returnValue:true,apps:[{id:'org.fixture',title:'Fixture',visible:false}]}));
 else if(command==='/bin/sh'||args[0].indexOf('/runtime/cli.py')>=0)callback(null,JSON.stringify({returnValue:true,fixture:true}));
 return {stdin:stdin};}};
process.getuid=function(){return 0;};
Module._load=function(name,parent,isMain){if(name==='webos-service')return Service;if(name==='child_process')return child;
 if(name==='/var/lib/clean-your-tv-root/python_boot.js')return load.call(this,base+'/root/python_boot.js',parent,isMain);
 // Installed service entry wrappers must select their real staged private closure.
 if(name==='/var/lib/clean-your-tv-root-updater/code/service.js')name=base+'/root-updater/service.js';
 if(name==='/var/lib/clean-your-tv-system-updater/code/service.js')name=base+'/system/service.js';
 return load.call(this,name,parent,isMain);};
var recoveryId=ROOT+'.service',updaterId='com.cleanyourtv.root.updater.service',systemId='com.cleanyourtv.system.updater.service';
require(base+'/root-ipk/usr/palm/services/'+recoveryId+'/service.js');
require(base+'/root-updater-ipk/usr/palm/services/'+updaterId+'/service.js');
require(base+'/system-ipk/usr/palm/services/'+systemId+'/service.js');
function rpc(id,method,payload,caller){return new Promise(function(resolve,reject){try{registrations[id+'/'+method]({payload:payload,ls2Message:{applicationID:function(){return caller||ROOT+' 123';}},respond:resolve});}catch(e){reject(e);}});}
function rejectCall(promise){return promise.then(function(){throw Error('unexpected dispatch success');},function(){});}
Promise.resolve().then(function(){return rpc(recoveryId,'status',{});}).then(function(result){assert.equal(result.returnValue,true);assert.equal(result.root,true);return rpc(recoveryId,'boot',{reason:'activity',$activity:{activityId:1}});}).then(function(result){assert.equal(result.returnValue,true);assert.equal(executed[1].command,'/bin/sh');return rpc(recoveryId,'listApps',{});}).then(function(result){assert.equal(result.apps[0].hidden,true);return rpc(recoveryId,'themeReceiverStart',{},'org.foreign');}).then(function(result){assert.equal(result.errorCode,'caller-not-authorized');return rpc(updaterId,'status',{});}).then(function(result){assert.equal(result.result.fixture,true);return rpc(updaterId,'install',{version:'1.2.3',profile:{}},'org.foreign');}).then(function(result){assert.equal(result.returnValue,false);return rpc(systemId,'status',{});}).then(function(result){assert.equal(result.result.fixture,true);return rpc(systemId,'install',{edition:'root',release:'v1.2.3',profile:{}},'com.cleanyourtv.root.updater');}).then(function(result){assert.equal(result.returnValue,false);
 var handlers=require(base+'/root-ipk/usr/palm/services/'+recoveryId+'/handlers'),releaseAudio;
 var audio=handlers.audio(function(){return 0;},function(){return new Promise(function(resolve){releaseAudio=resolve;});});
 var pending=audio.recoverAudio({operation:'restart-earc'});
 return audio.recoverAudio({operation:'restart-earc'}).then(function(r){assert.equal(r.errorCode,'busy');releaseAudio({returnValue:true});return pending;});
}).then(function(){Module._load=load;process.getuid=uid;console.log('PASS Root generated closure '+process.version+' ('+files.length+' scripts): signatures, URL policy, recovery, inventory, receiver authorization, updater dispatch and audio lock');},function(error){Module._load=load;process.getuid=uid;console.error(error.stack);process.exitCode=1;});
