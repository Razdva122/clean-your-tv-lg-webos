'use strict';
var assert=require('assert'),fs=require('fs'),vm=require('vm'),path=require('path');
var ID='a'.repeat(32),SHA='b'.repeat(64),calls=[];
function loadBridge(reply) {
 var context={Promise:Promise,setTimeout:setTimeout,clearTimeout:clearTimeout,module:{exports:{}},PalmServiceBridge:function(){this.cancel=function(){};this.call=function(uri,body){calls.push({uri:uri,body:JSON.parse(body)});this.onservicecallback(JSON.stringify(reply));};}};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../app/bridge.js'),'utf8'),context);return context.module.exports;
}
async function rejects(fn){var failed=false;try{await fn();}catch(e){failed=true;}assert(failed,'must reject');}
(async function(){
 assert(fs.existsSync(path.join(__dirname,'../app/bridge.js')),'fixed Homebrew bridge is required');
 var bridge=loadBridge({returnValue:true,stdoutString:JSON.stringify({state:'fresh',installation:{can_install:true}})});
 for(var bad of [{operation:ID,candidate:SHA,path:'/tmp/x'},{operation:'$(id)',candidate:SHA},{operation:ID,candidate:'A'.repeat(64)},{operation:ID,candidate:SHA,prepareSupervisor:'true'},{operation:ID,candidate:SHA,url:'https://example.com'}])await rejects(function(){return bridge.start(bad);});
 assert.equal(calls.length,0,'invalid options never reach HBC');
 await bridge.start({operation:ID,candidate:SHA,prepareSupervisor:true,migrate:false});
 assert.equal(calls[0].uri,'luna://org.webosbrew.hbchannel.service/exec');
 assert.equal(calls[0].body.command,'/usr/bin/node /media/developer/apps/usr/palm/applications/com.cleanyourtv.installer/bootstrap.js install --operation '+ID+' --candidate '+SHA+' --prepare-supervisor');
 await bridge.status(ID);assert(calls[1].body.command.endsWith('status --operation '+ID+' --verify-current'));
 await bridge.resume(ID,'remove');assert(calls[2].body.command.endsWith('remove --operation '+ID+' --resume'));
 var candidateReads=0,operationReads=0,supervisorReads=0,migrateReads=0;
 var accessor={};
 Object.defineProperties(accessor,{
  operation:{enumerable:true,get:function(){operationReads++;return operationReads===1?ID:'; printf OPERATION_INJECTION';}},
  candidate:{enumerable:true,get:function(){candidateReads++;return candidateReads<=2?SHA:'; printf BRIDGE_INJECTION';}}
 });
 var beforeAccessor=calls.length;await bridge.start(accessor);
 assert.equal(candidateReads,1,'candidate getter is read once before validation and construction');
 assert.equal(operationReads,1);
 assert.equal(calls.length,beforeAccessor+1);
 assert.equal(calls[calls.length-1].body.command,'/usr/bin/node /media/developer/apps/usr/palm/applications/com.cleanyourtv.installer/bootstrap.js install --operation '+ID+' --candidate '+SHA);
 await bridge.start({operation:ID,candidate:SHA,get prepareSupervisor(){supervisorReads++;return supervisorReads===1?false:'; printf FLAG_INJECTION';},get migrate(){migrateReads++;return migrateReads===1?false:true;}});assert.equal(supervisorReads,1);assert.equal(migrateReads,1);assert(calls[calls.length-1].body.command.endsWith('--candidate '+SHA));
 var inspectReads=0;await bridge.inspect({get prepareSupervisor(){inspectReads++;return inspectReads===1?false:true;}});assert.equal(inspectReads,1);assert(calls[calls.length-1].body.command.endsWith(' inspect'));
 var beforeCoercion=calls.length,coercions=0,coercible={toString:function(){coercions++;return SHA+'; printf COERCION_INJECTION';}};
 for(var objectOptions of [{operation:ID,candidate:coercible},{operation:coercible,candidate:SHA},{operation:ID,candidate:SHA,prepareSupervisor:coercible},{operation:ID,candidate:SHA,migrate:coercible}])await rejects(function(){return bridge.start(objectOptions);});
 assert.equal(calls.length,beforeCoercion,'coercible objects never reach HBC');assert.equal(coercions,0,'tokens must remain validated primitives');
 // LS2 denial is distinct from missing service/root/backend failure; never expose raw text.
 for(var denialText of ['Denied method call "exec" for category "/"','Denied method call "exec" for category "/".']){
  bridge=loadBridge({returnValue:false,errorCode:-1,errorText:denialText});
  await assert.rejects(bridge.inspect(),{message:'homebrew_exec_denied'});
  await assert.rejects(bridge.start({operation:ID,candidate:SHA}),{message:'homebrew_exec_denied'});
 }
 for(var errorReply of [{returnValue:false,errorText:'Unknown method'},{returnValue:false,errorText:'private diagnostics Denied method call "exec" for category "/"'},{returnValue:true,errorText:'Denied method call "exec" for category "/"',stdoutString:'not json'},{returnValue:false,errorText:'Denied method call "inspect" for category "/"'}]){
  bridge=loadBridge(errorReply);await assert.rejects(bridge.inspect(),{message:'installer_unavailable'});
 }
 bridge=loadBridge({returnValue:true,stdout:'{}'});await rejects(function(){return bridge.inspect();});
 bridge=loadBridge({returnValue:false,errorText:'Unknown method'});await rejects(function(){return bridge.inspect();});
 bridge=loadBridge({returnValue:true,stdoutString:'private diagnostics'});await rejects(function(){return bridge.inspect();});
 var bootstrap=require('../bootstrap.js'),executed=[],prepares=0,inspects=0,cleanups=0;
 var deps={process:{geteuid:function(){return 0;},versions:{node:'8.12.0'}},runtime:{stage:function(state,full){return Promise.resolve({root:'/private/stage',driver:'/private/stage/root-updater/install_driver.py',cleanup:function(){cleanups++;return Promise.resolve();}});},inspect:function(p){inspects++;assert.equal(p,bootstrap.PAYLOAD);return Promise.resolve({python:'/usr/bin/python3',privateRuntimeRequired:false});},prepare:function(){prepares++;return Promise.resolve('/usr/bin/python3');}},execute:function(exe,args){executed.push({exe:exe,args:args});return Promise.resolve(JSON.stringify({state:'fresh'}));}};
 for(var badArgs of [['install','--operation',ID,'--candidate',SHA,'--url','x'],['status','--operation','A'.repeat(32)],['install','--operation',ID,'--candidate',SHA,'--prepare-supervisor','true'],['inspect','--resume'],['remove','--operation',ID],['activate','--payload','/tmp']])await rejects(function(){return bootstrap.run(badArgs,deps);});
 assert.equal(inspects,0,'backend validates before runtime or effects');
 await bootstrap.run(['inspect'],deps);assert.equal(prepares,0);assert.equal(executed[0].args[3],'/private/stage/root-updater/install_driver.py');
 assert.equal(executed[0].args[executed[0].args.indexOf('--payload')+1],'/private/stage');
 await bootstrap.run(['status','--operation',ID,'--verify-current'],deps);assert(executed[1].args.indexOf('--verify-current')>=0);
 await bootstrap.run(['remove','--operation',ID,'--resume'],deps);assert(executed[2].args.indexOf('--resume')>=0);assert(executed[2].args.indexOf('--payload')<0,'resume uses original snapshot');
 var recoverySelections=[];deps.runtime.inspect=function(root,recovery){recoverySelections.push(recovery);return Promise.resolve({python:'/usr/bin/python3'});};
 await bootstrap.run(['status','--operation',ID],deps);await bootstrap.run(['restore'],deps);await bootstrap.run(['remove','--operation',ID,'--candidate',SHA],deps);await bootstrap.run(['inspect'],deps);assert.deepEqual(recoverySelections,[true,true,true,false]);
 deps.runtime.inspect=function(){return Promise.resolve({python:null,privateRuntimeRequired:true,requiredSpace:335544320});};
 assert.equal((await bootstrap.run(['inspect'],deps)).state,'prerequisites');assert.equal(prepares,0);
 await rejects(function(){return bootstrap.run(['install','--operation',ID,'--candidate',SHA],deps);});assert.equal(prepares,0);
 await bootstrap.run(['prepare-runtime'],deps);assert.equal(prepares,1);
 deps.runtime.inspect=function(){return Promise.resolve({python:'/usr/bin/python3'});};
 var priorCleanups=cleanups;deps.execute=function(){return Promise.resolve('invalid json');};await rejects(function(){return bootstrap.run(['inspect'],deps);});assert.equal(cleanups,priorCleanups+1,'invalid child output still cleans this private stage after exit');
 deps.execute=function(){return Promise.reject(new Error('child exited'));};await rejects(function(){return bootstrap.run(['restore'],deps);});assert.equal(cleanups,priorCleanups+2,'failed child still cleans this private stage after exit');
 deps.process.geteuid=function(){return 1000;};await rejects(function(){return bootstrap.run(['inspect'],deps);});
 deps.process.geteuid=function(){return 0;};deps.process.versions.node='0.12.2';await rejects(function(){return bootstrap.run(['inspect'],deps);});
 console.log('PASS fixed HBC exec reply, exact LS2 denial classification, input boundaries, root/Node gates, read-only prerequisites/status, explicit runtime and original resume');
})().catch(function(e){console.error(e);process.exitCode=1;});
