const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
function fixture(uhd){
 const nodes={},events={},storage={},videos=[],timers=new Map();let sequence=0;
 function node(tag){const classes=new Set(),listeners={};return {tagName:tag,style:{},classList:{add:x=>classes.add(x),remove:x=>classes.delete(x),contains:x=>classes.has(x)},appendChild(n){n.parentNode=this;nodes[n.id]=n;},removeChild(n){delete nodes[n.id];n.parentNode=null;},setAttribute(){},removeAttribute(k){delete this[k];},addEventListener(k,f){listeners[k]=f;},removeEventListener(k){delete listeners[k];},fire(k){if(listeners[k])listeners[k]();},pause(){this.paused=true;},load(){},play(){this.paused=false;return {then:(ok,bad)=>{this.reject=bad;}};}};}
 const doc={body:node('body'),documentElement:node('html'),hidden:false,getElementById:id=>nodes[id],createElement(tag){const n=node(tag);if(tag==='video'){n.videoWidth=1920;n.videoHeight=1080;videos.push(n);}return n;},addEventListener(k,f){events[k]=f;},dispatchEvent(){}};nodes.homeSurface=node('main');
 const ctx={addEventListener:(k,f)=>{events["window:"+k]=f;},document:doc,localStorage:{getItem:k=>storage[k]||null,setItem:(k,v)=>storage[k]=v},CustomEvent:function(){},setTimeout:f=>{timers.set(++sequence,f);return sequence;},clearTimeout:id=>timers.delete(id),webOS:{deviceInfo:cb=>cb({uhd})}};
 vm.runInNewContext(fs.readFileSync('launcher/wallpaper.js','utf8'),ctx);
 const manifest={id:'test:theme',title:'Video',defaults:{wallpaperAssetId:'poster',dim:.3},assets:[{id:'poster',width:1920,height:1080}],wallpaperVideo:{variants:[{quality:'4k',width:3840,height:2160},{quality:'1080p',width:1920,height:1080}]}};
 return {api:ctx.HomeWallpaper,doc,nodes,videos,input:{manifest,assetHandles:{poster:'blob:poster'},videoHandles:{'4k':'blob:4k','1080p':'blob:fhd'}},events,timers,storage};
}
let f=fixture(undefined);assert(f.api,'wallpaper lifecycle API exists');
f.api.configure(f.input);assert.equal(f.videos.at(-1).src,'blob:fhd');assert.equal(f.api.state().capabilities.uhd,null);assert.equal(f.api.state().actualQuality,'image');
let old=f.videos.at(-1);old.fire('playing');assert.equal(f.api.state().actualQuality,'1080p');assert(f.nodes.homeSurface.classList.contains('ctv-wallpaper-playing'));
old.fire('error');assert.equal(f.api.state().actualQuality,'image');assert.equal(old.src,undefined);assert.match(f.api.state().notice,/image/i);
f=fixture(true);f.api.configure(f.input);old=f.videos.at(-1);assert.equal(old.src,'blob:4k');old.fire('error');let fallback=f.videos.at(-1);assert.equal(fallback.src,'blob:fhd');old.reject(Error('late'));assert.equal(f.videos.at(-1),fallback);fallback.fire('playing');f.api.suspend('settings');assert.equal(fallback.src,undefined);f.api.suspend('dialog');f.api.resume('settings');assert.equal(f.videos.at(-1),fallback);f.api.configure(f.input);assert.equal(f.videos.at(-1),fallback);f.api.resume('dialog');assert.notEqual(f.videos.at(-1),fallback);
f.api.setQuality('image');assert.equal(f.api.state().actualQuality,'image');f.api.setDim(.7);assert.equal(f.api.state().dim,.7);assert.throws(()=>f.api.setDim(1));assert.throws(()=>f.api.setQuality('bogus'));f.api.configure(f.input);assert.equal(f.api.state().preferenceQuality,'image');assert.equal(f.api.state().dim,.7);f.api.resetPreferences();assert.equal(f.api.state().dim,.3);assert.equal(f.api.state().preferenceQuality,'auto');
f.doc.hidden=true;f.events.visibilitychange();assert.equal(f.videos.at(-1).src,undefined);f.doc.hidden=false;f.events.visibilitychange();assert.equal(f.videos.at(-1).src,'blob:4k');f.api.reset();assert.equal(f.api.state().themeId,'builtin:classic');assert.equal(f.videos.at(-1).src,undefined);
f=fixture(false);f.api.configure(f.input);f.api.setQuality('4k');assert.equal(f.videos.at(-1).src,'blob:fhd');assert.match(f.api.state().notice,/4K/);
console.log('PASS wallpaper quality, static fallback, stale work, suspension, preferences and visibility');

f=fixture(true);f.api.configure(f.input);let timeout=Array.from(f.timers.values())[0];timeout();assert.equal(f.videos.at(-1).src,'blob:fhd');timeout=Array.from(f.timers.values())[0];timeout();assert.equal(f.api.state().actualQuality,'image');assert.equal(f.videos.at(-1).src,undefined);
console.log('PASS bounded no-play/stall cascade releases media');
(async()=>{
 const f=fixture(true);let finish,acquisitions=0,releases=0;
 f.input.videoHandles={};f.input.videoLease={acquire(){acquisitions++;return new Promise(resolve=>{finish=resolve;});},release(){assert.equal(f.videos.at(-1)&&f.videos.at(-1).src,undefined,'decoder detaches before native cache release');releases++;}};
 f.api.configure(f.input);assert.equal(acquisitions,1,'native cache acquired only as wallpaper becomes active');assert.equal(f.api.state().actualQuality,'image');assert.equal(f.videos.length,0);
 f.api.suspend('settings');finish({'4k':'http://127.0.0.1/native-first'});await Promise.resolve();assert.equal(f.videos.length,0,'late acquisition cannot start media behind settings');assert.equal(releases,1);
 f.api.resume('settings');assert.equal(acquisitions,2);finish({'4k':'http://127.0.0.1/native-second'});await Promise.resolve();assert.equal(f.videos.at(-1).src,'http://127.0.0.1/native-second');f.videos.at(-1).videoWidth=3840;f.videos.at(-1).videoHeight=2160;f.videos.at(-1).fire('playing');f.api.setQuality('image');assert.equal(releases,2);assert.equal(f.videos.at(-1).src,undefined);
 console.log('PASS lazy native lease acquire, stale result and hidden/image release');
})().catch(e=>{console.error(e);process.exitCode=1;});
f=fixture(true);f.api.configure(f.input);let firstTimer=Array.from(f.timers.keys())[0];f.videos.at(-1).fire('waiting');assert(f.timers.has(firstTimer),'waiting without frame progress cannot postpone fallback indefinitely');
f.api.setDim(.8);delete f.storage['tvhome.wallpaper.preferences.v1'];f.api.configure(f.input);assert.equal(f.api.state().dim,.3,'removed profile preferences do not survive in memory');

f=fixture(true);f.api.configure(f.input);f.videos.at(-1).fire('playing');assert.equal(f.api.state().actualQuality,'image','mismatched decoded UHD dimensions never expose video');assert.equal(f.videos.at(-1).src,'blob:fhd','decoded mismatch descends to compatible FHD');assert.match(f.api.state().notice,/dimensions/);
f=fixture(true);f.api.configure(f.input);f.api.suspend('settings');assert.equal(f.api.state().paused,true);f.api.setQuality('image');assert.equal(f.api.state().paused,false);f.api.configure({...f.input,manifest:{...f.input.manifest,wallpaperVideo:undefined},videoHandles:{}});assert.equal(f.api.state().paused,false);

f=fixture(true);f.api.configure(f.input);old=f.videos.at(-1);
assert.equal(typeof f.events['window:blur'],'function','window overlays release the wallpaper decoder');
f.events['window:blur']();assert.equal(old.src,undefined);
f.api.suspend('settings');f.events['window:focus']();assert.equal(f.videos.at(-1),old,'focus cannot bypass settings');
f.api.resume('settings');assert.notEqual(f.videos.at(-1),old);
f.api.reset();console.log('PASS focus ownership composes with settings suspension');

f=fixture(true);f.api.configure(f.input);f.api.suspend('input-preview');
assert.match(f.nodes.ctvWallpaperImage.textContent,/blob:poster/,'input decoder suspension retains personal static wallpaper');
f.api.suspend('settings');assert.equal(f.nodes.ctvWallpaperImage.textContent,'','settings keep their standard background');
f.api.resume('settings');assert.match(f.nodes.ctvWallpaperImage.textContent,/blob:poster/);
f.api.resume('input-preview');f.api.reset();
f=fixture(true);f.api.suspend('decoder-context');f.api.configure(f.input);
assert.equal(f.videos.length,0,'unknown Root decoder snapshot prevents initial attachment');
assert.match(f.nodes.ctvWallpaperImage.textContent,/blob:poster/,'decoder-only suspension retains the static poster');
f.api.suspend('presentation');assert.equal(f.nodes.ctvWallpaperImage.textContent,'','transparent Home still hides the poster');
f.api.resume('presentation');assert.match(f.nodes.ctvWallpaperImage.textContent,/blob:poster/);
f.api.resume('decoder-context');assert.equal(f.videos.length,1,'positive context can release the decoder-only hold');f.api.reset();

f=fixture(false);f.api.configure(f.input);
const personal={...f.input,origin:'phone',manifest:{...f.input.manifest,id:'personal:wallpaper'}};
f.api.setPersonal(personal,true);assert.equal(f.api.state().source,'personal');
f.api.setThemePreview(true);assert.equal(f.api.state().source,'theme');assert.equal(f.api.state().themeId,'test:theme');
f.api.configure({...f.input,manifest:{...f.input.manifest,id:'test:candidate'}});
f.api.setPersonal({...personal,manifest:{...personal.manifest,title:'Replacement'}},true);
assert.equal(f.api.state().themeId,'test:candidate','personal media updates cannot cover an active theme trial');
f.api.setThemePreview(false);assert.equal(f.api.state().source,'personal');assert.equal(f.api.state().title,'Replacement');
const resumed=f.videos.at(-1);f.api.setThemePreview(false);assert.equal(f.videos.at(-1),resumed,'releasing an inactive trial does not restart the wallpaper');
f.api.reset();console.log('PASS temporary theme trial source, candidate replacement and personal restoration');
