'use strict';
var diagnostics=require('./diagnostics');
// The service writes inside its own jail-visible package. The native controller
// reads this provisioned prisoner:jailer 2770 channel; request files stay 0660.
module.exports=function(fs,dir,options){
 options=options||{};
 var busy=false,now=options.now||Date.now,later=options.later||setTimeout;
 var inputs=options.inputs===true,prefix=inputs?'input':'home';
 var nonce=options.nonce||function(){return require('crypto').randomBytes(16).toString('hex');};
 return function(method,payload){
  if((inputs?['inputStatus']:['homeStatus','setHomeControl','openLGHome']).indexOf(method)<0||
     (method==='inputStatus'&&(!payload||typeof payload!=='object'||Array.isArray(payload)||Object.keys(payload).length!==0))||
     (method==='setHomeControl'&&(!payload||typeof payload.enabled!=='boolean')))
   return Promise.resolve({returnValue:false,errorText:'Invalid Home request'});
  if(busy)return Promise.resolve({returnValue:false,errorText:'Home control busy',diagnostic:diagnostics.describe('home','wait',{code:'BUSY'})});
  busy=true;
  return new Promise(function(resolve){
   var id=nonce(),deadline=now()+5000,operation='write',lastFailure=null;
   function finish(r){busy=false;resolve(r);}
   try{
    var request={id:id,method:method,expires:deadline};
    if(method==='setHomeControl')request.enabled=payload.enabled;
    fs.writeFileSync(dir+'/'+prefix+'-request.tmp',JSON.stringify(request),{mode:432});
    operation='chmod';
    fs.chmodSync(dir+'/'+prefix+'-request.tmp',432);
    operation='rename';
    fs.renameSync(dir+'/'+prefix+'-request.tmp',dir+'/'+prefix+'-request.json');
   }catch(e){finish({returnValue:false,errorText:'Home Helper data unavailable',diagnostic:diagnostics.describe('home',operation,e)});return;}
   function poll(){
    operation='read';
    try{
     var raw=fs.readFileSync(dir+'/'+prefix+'-response.json','utf8');operation='parse';
     var r=JSON.parse(raw);lastFailure=null;
     if(r.id===id){finish(r);return;}
    }catch(e){lastFailure=diagnostics.describe('home',operation,e);}
    if(now()>=deadline){finish({returnValue:false,errorText:'Home Helper did not respond',diagnostic:lastFailure||diagnostics.describe('home','wait',{code:'TIMEOUT'})});return;}
    later(poll,100);
   }
   poll();
  });
 };
};
