'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
function fixture(options={}){
 const nodes={},events={},videos=[],timers=new Map();let sequence=0,acquires=0,releases=0,disposals=0,failStream;
 function node(){const listeners={},classes=new Set();return {style:{},classList:{add:x=>classes.add(x),remove:x=>classes.delete(x)},appendChild(n){n.parentNode=this;nodes[n.id]=n;},removeChild(n){delete nodes[n.id];n.parentNode=null;},setAttribute(){},removeAttribute(k){delete this[k];},addEventListener(k,f){listeners[k]=f;},removeEventListener(k){delete listeners[k];},fire(k){if(listeners[k])listeners[k]();},pause(){},load(){},play(){return Promise.resolve();}};}
 const doc={hidden:false,body:node(),documentElement:node(),getElementById:id=>nodes[id],createElement(tag){const n=node();if(tag==='video'){n.videoWidth=3840;n.videoHeight=2160;videos.push(n);}return n;},addEventListener(k,f){events[k]=f;},dispatchEvent(){}};
 nodes.homeSurface=node();
 const ctx={document:doc,ROOT_VERSION:options.noRoot?undefined:'0.9.2',CYTV_HOME_HOST:options.card?'card':undefined,MediaSource:{isTypeSupported:()=>!options.unsupportedMSE},localStorage:{getItem(){return null;},setItem(){}},CustomEvent:function(){},setTimeout:f=>{timers.set(++sequence,f);return sequence;},clearTimeout:id=>timers.delete(id),webOS:{deviceInfo:cb=>cb({uhd:options.unknownUHD?undefined:true})},WallpaperStream:{create(video,variant,failed){if(variant.quality!=='4k'||options.unsupportedMSE)return null;if(options.throwStream)throw Error('unsupported');if(options.noStream)return null;failStream=failed;return {url:'blob:verified-mse',dispose(){disposals++;}};}}};
 ctx.window=ctx;
 vm.runInNewContext(fs.readFileSync('launcher/wallpaper-library.js','utf8'),ctx);
 vm.runInNewContext(fs.readFileSync('launcher/wallpaper.js','utf8'),ctx);
 const input={origin:options.origin||'builtin',manifest:{id:options.id||'builtin:black-hole',title:'Black Hole',defaults:{wallpaperAssetId:'poster',dim:0},assets:[{id:'poster',width:1920,height:1080}],wallpaperVideo:{variants:[{quality:'4k',width:3840,height:2160,sha256:options.badHash?'0'.repeat(64):'37a30030526f89a939ad09c852736a9d0b01722630e2aca01869da2a70f256fb'},{quality:'1080p',width:1920,height:1080}]}},assetHandles:{poster:'blob:poster'},videoHandles:{},videoLease:{acquire(){acquires++;return Promise.reject(Error('cache denied'));},release(){releases++;return Promise.resolve();}}};
 if(options.cacheHandles)input.videoLease.acquire=function(){acquires++;return Promise.resolve({'1080p':'http://127.0.0.1/cached.mp4','4k':'http://127.0.0.1/cached4k.mp4'});};
 return {api:ctx.HomeWallpaper,input,doc,events,videos,timers,nodes,counts:()=>({acquires,releases,disposals}),failure:()=>failStream,fail:()=>failStream()};
}
(async()=>{
 let card=fixture({noRoot:true,card:true});card.api.configure(card.input);assert.equal(card.counts().acquires,0,'published CARD No-root uses the verified packaged route before cache');assert.equal(card.videos.at(-1).src,'blob:verified-mse');
 let native=fixture({unsupportedMSE:true,cacheHandles:true});native.api.configure(native.input);await Promise.resolve();await Promise.resolve();assert.equal(native.videos.at(-1).src,'http://127.0.0.1/cached4k.mp4','unsupported MSE retains the validated native-cache route');assert.equal(native.counts().acquires,1);
 let transition=fixture({unknownUHD:true,cacheHandles:true});transition.api.configure(transition.input);await Promise.resolve();await Promise.resolve();
 assert.equal(transition.videos.at(-1).src,'http://127.0.0.1/cached.mp4');
 const release=transition.input.videoLease.release;let releasedAttached=false;
 transition.input.videoLease.release=function(){releasedAttached=!!transition.nodes.ctvWallpaperVideo;return release();};
 transition.api.setQuality('4k');assert.equal(releasedAttached,false,'detach cached video before releasing its lease');assert.equal(transition.videos.at(-1).src,'blob:verified-mse');
 let f=fixture();f.api.configure(f.input);
 assert.equal(f.videos.at(-1).src,'blob:verified-mse');assert.equal(f.counts().acquires,0);
 f.api.suspend('decoder-context');assert.equal(f.nodes.ctvWallpaperVideo,undefined);assert.equal(f.counts().disposals,1);
 f.api.setQuality('4k');assert.equal(f.nodes.ctvWallpaperVideo,undefined,'held decoder context blocks all restarts');
 f.api.resume('decoder-context');const oldFailure=f.failure();f.fail();
 assert.equal(f.nodes.ctvWallpaperVideo,undefined);assert.equal(f.api.state().actualQuality,'image');assert.equal(f.counts().acquires,0,'MSE failure cannot descend into cache-backed FHD');
 f.api.setQuality('4k');const replacement=f.videos.at(-1);oldFailure();
 assert.equal(f.nodes.ctvWallpaperVideo,replacement);
 f.doc.hidden=true;f.events.visibilitychange();assert.equal(f.nodes.ctvWallpaperVideo,undefined);
 for(const options of [{noStream:true},{throwStream:true}]){f=fixture(options);f.api.configure(f.input);assert.equal(f.nodes.ctvWallpaperVideo,undefined);assert.equal(f.counts().acquires,0);assert.match(f.api.state().notice,/playback failed/);}
 f=fixture();f.api.configure(f.input);f.videos.at(-1).videoWidth=1920;f.videos.at(-1).fire('playing');assert.equal(f.nodes.ctvWallpaperVideo,undefined);assert.match(f.api.state().notice,/dimensions/);assert.equal(f.counts().acquires,0);
 f=fixture();f.api.configure(f.input);[...f.timers.values()][0]();assert.equal(f.nodes.ctvWallpaperVideo,undefined,'watchdog returns to image');assert.equal(f.counts().acquires,0);
 f=fixture({id:'builtin:ribbon',origin:'theme'});f.api.configure(f.input);assert.equal(f.videos.at(-1).src,'blob:verified-mse');
 for(const options of [{noRoot:true},{id:'personal:wallpaper',origin:'cytv'},{origin:'phone'},{id:'github:other/theme'},{badHash:true}]){
  f=fixture(options);f.api.configure(f.input);await Promise.resolve();await Promise.resolve();
  assert.equal(f.counts().acquires,1,'No-root and media outside the pinned built-in route retain the native cache');assert.equal(f.nodes.ctvWallpaperVideo,undefined);
 }
 console.log('PASS Root route identity, No-root/personal isolation, decoder/visibility ownership, null/throw/error/dimensions/watchdog image fallback and disposal');
})().catch(e=>{console.error(e);process.exitCode=1;});
