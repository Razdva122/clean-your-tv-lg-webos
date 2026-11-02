'use strict';
var Service=require('webos-service'),fs=require('fs');
var service=new Service('com.cleanyourtv.updater.service');
var store=require('./storage')(__dirname+'/state'),policy=require('./policy'),data=require('./user-data');
var key=fs.readFileSync(__dirname+'/release-public.pem','utf8');
var channel='https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/';
function rpc(uri,args,install){return new Promise(function(resolve,reject){
 var request,done=false,timer=setTimeout(function(){finish(Error('timeout'));},install?180000:10000);
 function finish(e,r){if(done)return;done=true;clearTimeout(timer);if(request&&request.cancel)request.cancel();if(e)reject(e);else resolve(r);}
 function response(m){var p=m.payload||{};
  if(p.returnValue===false){var error=Error('service-rejected');/* Homebrew errors do not distinguish bus failures from terminal installer failures. */error.definite=false;finish(error);}
  else if(!install||p.finished===true)finish(null,p);
 }
 try{if(install){request=service.subscribe(uri,args);request.on('response',response);}else service.call(uri,args,response);}catch(_){finish(Error('service-unavailable'));}
});}
async function root(){try{var r=await rpc('luna://org.webosbrew.hbchannel.service/checkRoot',{});return r.returnValue===true;}catch(_){return false;}}
async function app(id){var r=await rpc('luna://org.webosbrew.hbchannel.service/getAppInfo',{id:id});if(!r.appInfo||r.appInfo.id!==id)throw Error('version-unavailable');return r.appInfo;}
async function versions(){return {home:(await app('com.gathin.tvhome')).version,helper:(await app('com.local.nativehome')).version};}
var manager=require('./manager')({load:function(){return store.read('transaction');},save:function(s){store.write('transaction',s);},root:root,versions:versions,
 pauseRenewal:async function(id){var r=await rpc('luna://com.gathin.tvhome.renewal/pauseForUpdate',{id:id});
  if(!r.state||r.state.enabled!==false||r.state.error)throw Error('pause-unconfirmed');return r.state.updatePause;},
 resumeRenewal:async function(receipt){if(!receipt)throw Error('missing-pause-receipt');
  var imported=await rpc('luna://com.gathin.tvhome.renewal/importUpdatePause',{receipt:receipt});
  if(!imported.state||imported.state.error)throw Error('pause-import-unconfirmed');
  var r=await rpc('luna://com.gathin.tvhome.renewal/resumeAfterUpdate',{id:receipt.id});
  return {restored:!!(r.state&&!r.state.error&&!r.state.updatePause&&r.state.completedUpdate===receipt.id)};},
 backup:async function(s){var tx=store.read('transaction'),existing=tx&&tx.profile!==undefined?tx.profile:store.read('profile');if(existing!==null)data.validate(existing);data.validate(s);},
 install:function(m){var checked=policy.verify(m.proof,key);if(checked.home!==m.home||checked.url!==m.url||checked.sha256!==m.sha256||checked.helper!==m.helper)throw Error('invalid-saved-manifest');return rpc('luna://org.webosbrew.hbchannel.service/install',{ipkUrl:m.url,ipkHash:m.sha256,id:'com.gathin.tvhome',subscribe:true},true);}
});
function authorized(m){
 // Identity comes from the bus, never from a caller-supplied payload.
 try{var raw=m.ls2Message;var id=raw&&raw.applicationID&&raw.applicationID();
  return typeof id==='string'&&['com.gathin.tvhome','com.cleanyourtv.updater'].indexOf(id.split(' ')[0])>=0;
 }catch(_){return false;}
}
function register(name,fn){service.register(name,function(m){if(!authorized(m)){m.respond({returnValue:false,errorText:'caller-not-authorized'});return;}
 Promise.resolve().then(function(){return fn(m.payload||{});}).then(function(value){m.respond({returnValue:true,result:value});},function(){m.respond({returnValue:false,errorText:'update-operation-failed'});});
});}
async function readOffer(){
 var info=await rpc('luna://com.webos.service.tv.systemproperty/getSystemInfo',{keys:['UHD']}),value=info.UHD,resolution;
 if(info.returnValue===true&&(value===true||value==='true'))resolution='1920x1080';
 else if(info.returnValue===true&&(value===false||value==='false'))resolution='1280x720';
 else throw Error('graphics-capability-unavailable');
 var raw=JSON.parse(await require('./transport').get(channel+(resolution==='1280x720'?'update-720p.json':'update.json')));
 var candidate=policy.graphics(policy.verify(raw,key),resolution),prior=raw.previous?policy.verify(raw.previous,key):null;
 candidate.proof={payload:raw.payload,signature:raw.signature};if(prior)prior.proof={payload:raw.previous.payload,signature:raw.previous.signature};
 return {candidate:candidate,prior:prior};
}
register('check',async function(){
 var v=await versions(),r=await root(),selected=await readOffer(),candidate=selected.candidate,prior=selected.prior;
 return {home:v.home,helper:v.helper,root:r,state:policy.offer(candidate,v.home,v.helper),candidate:candidate,
  canInstall:r&&policy.offer(candidate,v.home,v.helper)==='available'&&!!prior&&prior.home===v.home&&prior.helper===v.helper&&policy.compare(prior.home,'1.2.0')>=0};
});
register('status',async function(){return {transaction:manager.status(),root:await root()};});
register('restore',function(p){
 var tx=store.read('transaction'),profile=tx&&tx.profile!==undefined?data.validate(tx.profile):store.read('profile');
 if(!p.withTransaction)return profile;
 return {profile:profile,transaction:tx?{id:tx.id,status:tx.status,prior:tx.prior,candidate:tx.candidate}:null};
});
register('install',async function(p){var selected=await readOffer();if(!selected||!selected.prior||policy.compare(selected.prior.home,'1.2.0')<0||p.version!==selected.candidate.home)throw Error('check-first');
 // Services may stop between UI actions. Fetch and verify again; never trust caller URLs/hashes.
 var renewal=await rpc('luna://com.gathin.tvhome.renewal/status',{});
 if(!renewal.state||typeof renewal.state.enabled!=='boolean')throw Error('renewal-state-unavailable');
 return manager.install(selected.candidate,selected.prior,data.validate(p.profile));
});
register('reconcile',manager.reconcile);
register('healthy',function(p){return manager.healthy(p.version);});

register('rollback',manager.rollback);
