/* Trusted loopback media lease. Bytes remain in the verified application cache. */
(function(root){
 'use strict';
 if(!root.PalmServiceBridge)return;
 function service(){return 'luna://'+(document.querySelector('script[src="root-settings.js"]')?'com.cleanyourtv.root.preview.service':'com.gathin.tvhome.renewal')+'/';}
 function rpc(method,payload){return new Promise(function(resolve,reject){var bridge,done=false,timer=setTimeout(function(){finish(Error('Wallpaper cache timed out'));},10000);
  function finish(error,value){if(done)return;done=true;clearTimeout(timer);if(bridge&&!(error&&method==='wallpaperCacheStart'))try{bridge.cancel();}catch(_){}if(error)reject(error);else resolve(value);}
  try{bridge=new root.PalmServiceBridge();bridge.onservicecallback=function(raw){var value;try{value=JSON.parse(raw);}catch(_){finish(Error('Invalid wallpaper cache response'));return;}if(done){if(method==='wallpaperCacheStart'&&value&&typeof value.sessionId==='string')rpc('wallpaperCacheStop',{sessionId:value.sessionId}).catch(function(){});return;}if(!value||value.returnValue!==true){finish(Error('Wallpaper cache unavailable'));return;}finish(null,value);};bridge.call(service()+method,JSON.stringify(payload));}catch(_){finish(Error('Wallpaper cache unavailable'));}
 });}
 function prepare(manifest,pack,cancelled){
  if(cancelled&&cancelled())return Promise.reject(Error('Cancelled'));
  cancelled=null;
  // Runtime owns the accepted lease through dispose/release and its own generation.
  var disposed=false,generation=0,session=null,acquiring=null,timer=null,handles={},variants=manifest.wallpaperVideo.variants;
  function stopped(id){return id?rpc('wallpaperCacheStop',{sessionId:id}).catch(function(){}):Promise.resolve();}
  function release(){generation++;clearInterval(timer);timer=null;handles={};var id=session;session=null;acquiring=null;return stopped(id);}
  function acquire(){
   if(disposed)return Promise.reject(Error('Cancelled'));
   if(session&&Object.keys(handles).length)return Promise.resolve(handles);if(acquiring)return acquiring;
   var identity=++generation,owned=null;
   function check(){if(disposed||identity!==generation)throw Error('Cancelled');}
   var operation=rpc('wallpaperCacheStart',{variants:variants.map(function(v){return {quality:v.quality,size:v.size,sha256:v.sha256};})}).then(function(value){
    if(typeof value.sessionId!=='string'||! /^[a-f0-9]{48}$/.test(value.sessionId))throw Error('Invalid wallpaper cache session');owned=value.sessionId;check();session=owned;
    var chain=Promise.resolve();variants.forEach(function(v){chain=chain.then(function upload(){check();var bytes=new Uint8Array(pack.files[v.path]),offset=0;function chunk(){check();if(offset===bytes.length)return;var end=Math.min(offset+49152,bytes.length),raw='';for(var i=offset;i<end;i++)raw+=String.fromCharCode(bytes[i]);return rpc('wallpaperCacheWrite',{sessionId:owned,quality:v.quality,offset:offset,data:btoa(raw)}).then(function(r){check();if(r.nextOffset!==end)throw Error('Invalid wallpaper cache offset');offset=end;return chunk();});}return chunk();});});return chain;
   }).then(function(){check();return rpc('wallpaperCacheCommit',{sessionId:owned});}).then(function(result){check();var map=result.handles;if(!map||typeof map!=='object'||Object.keys(map).length!==variants.length)throw Error('Invalid wallpaper cache handles');variants.forEach(function(v){if(typeof map[v.quality]!=='string'||! /^http:\/\/127\.0\.0\.1:[0-9]{1,5}\/[a-f0-9]{32}\/(?:4k|1080p)\.mp4$/.test(map[v.quality])||map[v.quality].slice(-v.quality.length-4)!==v.quality+'.mp4')throw Error('Invalid wallpaper cache handle');});handles=map;timer=setInterval(function(){if(identity!==generation||disposed)return;rpc('wallpaperCacheKeepAlive',{sessionId:owned}).catch(function(){if(identity===generation)release();});},20000);return handles;
   }).catch(function(e){if(identity===generation){session=null;handles={};clearInterval(timer);timer=null;}return stopped(owned).then(function(){throw e;});});
   acquiring=operation;operation.then(function(){if(acquiring===operation)acquiring=null;},function(){if(acquiring===operation)acquiring=null;});return operation;
  }
  return Promise.resolve({handles:handles,acquire:acquire,release:release,dispose:function(){disposed=true;return release();}});
 }
 root.WallpaperMediaCache={prepare:prepare};
}(this));
