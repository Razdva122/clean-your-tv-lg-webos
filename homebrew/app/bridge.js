/* HBC exec uses returnValue + stdoutString (service src/service.ts, 2026-10-25).
 * spawn currently emits event while README says type; no streaming assumption. */
(function(root){
 'use strict';
 var FIXED='/usr/bin/node /media/developer/apps/usr/palm/applications/com.cleanyourtv.installer/bootstrap.js';
 function fail(){throw new Error('installer_unavailable');}
 function id(value){if(typeof value!=='string'||!/^[a-f0-9]{32}$/.test(value))fail();return value;}
 function options(value,allowed){if(!value||typeof value!=='object'||Array.isArray(value))fail();Object.keys(value).forEach(function(k){if(allowed.indexOf(k)<0)fail();});var snapshot={};allowed.forEach(function(k){snapshot[k]=value[k];});return snapshot;}
 var grammar={
  inspect:/^(--prepare-supervisor)?$/,
  'prepare-runtime':/^$/,restore:/^$/,activate:/^$/,
  status:/^--operation [a-f0-9]{32} --verify-current$/,
  install:/^--operation [a-f0-9]{32} (--resume|--candidate [a-f0-9]{64}( --prepare-supervisor)?( --migrate-packaged-home)?)$/,
  remove:/^--operation [a-f0-9]{32} (--resume|--candidate [a-f0-9]{64})$/
 };
 function call(action,tokens){
  return Promise.resolve().then(function(){
   if(typeof action!=='string'||!Object.prototype.hasOwnProperty.call(grammar,action)||!Array.isArray(tokens)||tokens.some(function(token){return typeof token!=='string';}))fail();
   var argumentsText=tokens.join(' ');if(!grammar[action].test(argumentsText))fail();
   var command=FIXED+' '+action+(argumentsText?' '+argumentsText:'');
   if(typeof root.PalmServiceBridge!=='function')fail();
   return new Promise(function(resolve,reject){
    var bridge=new root.PalmServiceBridge(),done=false,timer;
    function finish(error,value){if(done)return;done=true;clearTimeout(timer);try{bridge.cancel();}catch(_){}if(error)reject(new Error(error==='homebrew_exec_denied'?error:'installer_unavailable'));else resolve(value);}
    timer=setTimeout(function(){finish(true);},125000);
    bridge.onservicecallback=function(raw){try{var reply=JSON.parse(raw);if(reply.returnValue===false&&typeof reply.errorText==='string'&&/^Denied method call "exec" for category "\/"\.?$/.test(reply.errorText)){finish('homebrew_exec_denied');return;}if(reply.returnValue!==true||typeof reply.stdoutString!=='string'||reply.stdoutString.length>65536)fail();var value=JSON.parse(reply.stdoutString);if(!value||typeof value.state!=='string')fail();finish(false,value);}catch(_){finish(true);}};
    try{bridge.call('luna://org.webosbrew.hbchannel.service/exec',JSON.stringify({command:command}));}catch(_){finish(true);}
   });
  });
 }
 function submission(action,value){
  return Promise.resolve().then(function(){
   value=options(value,action==='install'?['operation','candidate','prepareSupervisor','migrate']:['operation','candidate']);
   var args=['--operation',id(value.operation)];
   if(typeof value.candidate!=='string'||!/^[a-f0-9]{64}$/.test(value.candidate))fail();args.push('--candidate',value.candidate);
   ['prepareSupervisor','migrate'].forEach(function(k){if(value[k]!==undefined&&typeof value[k]!=='boolean')fail();});
   if(value.prepareSupervisor)args.push('--prepare-supervisor');if(value.migrate)args.push('--migrate-packaged-home');return call(action,args);
  });
 }
 var api={
  inspect:function(value){return Promise.resolve().then(function(){value=options(value||{},['prepareSupervisor']);if(value.prepareSupervisor!==undefined&&typeof value.prepareSupervisor!=='boolean')fail();return call('inspect',value.prepareSupervisor?['--prepare-supervisor']:[]);});},
  start:function(value){return submission('install',value);},
  status:function(operation){return Promise.resolve().then(function(){return call('status',['--operation',id(operation),'--verify-current']);});},
  restore:function(operation){return Promise.resolve().then(function(){if(operation!==undefined)id(operation);return call('restore',[]);});},
  remove:function(value){return submission('remove',value);},
  prepareRuntime:function(){return call('prepare-runtime',[]);},
  activate:function(){return call('activate',[]);},
  resume:function(operation,action){return Promise.resolve().then(function(){if(action!=='install'&&action!=='remove')fail();return call(action,['--operation',id(operation),'--resume']);});}
 };
 root.InstallerBridge=api;if(typeof module!=='undefined')module.exports=api;
}(typeof window!=='undefined'?window:this));
