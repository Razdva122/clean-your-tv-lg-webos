const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict'),EventEmitter=require('events');
let now=1000,worker,watch,start,tick,closeMode='success',allowWorkerEnd=false,workerEnds=0;const closeCalls=[],closeReplies=[];const methods={},calls=[],launches=[],commands=[],files=new Map();
function Service(){this.register=(n,f)=>methods[n]=f;this.activityManager={create(){}};this.call=(uri,p,cb)=>{if(uri.endsWith('/closeByAppId')){closeCalls.push(p.id);if(closeMode==='hold'){closeReplies.push(()=>cb({payload:{returnValue:true}}));return;}if(closeMode==='deny'){cb({payload:{returnValue:false}});return;}if(closeMode==='unknown'){cb({payload:{}});return;}}if(uri.endsWith('/launch')){calls.push(p.id);launches.push(p);}cb({payload:{returnValue:true,state:{enabled:true,schema:3}}});};}
const fakefs={existsSync:()=>false,writeFileSync:(p,s)=>files.set(p,s),renameSync:(a,b)=>{files.set(b,files.get(a));files.delete(a);},chmodSync(){},unlinkSync(){},appendFileSync(){},readFileSync(p){if(p.endsWith('apps.json'))return '["test.app"]';if(files.has(p))return files.get(p);const e=new Error('missing');e.code='ENOENT';throw e;}};
const context={Buffer,require(n){if(n==='./state-permissions')return()=>true;if(n==='fs')return fakefs;if(n==='child_process')return{spawn(){worker=new EventEmitter();worker.stdout=new EventEmitter();worker.stderr=new EventEmitter();worker.stdin=new EventEmitter();worker.stdin.write=c=>commands.push(c);worker.stdin.end=()=>{if(allowWorkerEnd){workerEnds++;return;}throw Error('worker must stay active')};return worker;}};if(n==='/usr/lib/node_modules/webos-service')return Service;if(n==='./screen-watch')return(d,l,fg,reset,power)=>{watch={fg,power};return{foreground(done){done('test.app');},close(){}}};return require('../native/app/'+n.slice(2));},process:{argv:['node','app','{"nativeHomeAuto":true}'],pid:1,getuid:()=>5431,hrtime:()=>[Math.floor(now/1000),(now%1000)*1e6],on(){},exit(){throw Error('must not stop')}},setTimeout(fn,ms){if(ms===0)start=fn;return 1;},clearTimeout(){},setInterval(fn){tick=fn;},clearInterval(){}};
vm.runInNewContext(fs.readFileSync('native/app/native.js','utf8'),context);start();worker.stdout.emit('data',Buffer.from('READY\n'));
let seq=0;function rpc(n,p={},dir='/media/developer/apps/usr/palm/applications/com.local.nativehome/state'){files.set(dir+'/home-request.json',JSON.stringify({id:(++seq).toString(16).padStart(32,'0'),method:n,enabled:p.enabled,generation:p.generation,expires:Date.now()+5000}));tick();return JSON.parse(files.get(dir+'/home-response.json'));}
assert.equal(rpc('homeStatus').enabled,true);
// Installing the separate Home app closes its UI. That foreground transition
// must leave the detached helper/relay alive without trying to reopen the app
// while SAM may still be replacing it.
watch.fg('com.gathin.tvhome');const beforeUpdateClose=calls.length;
watch.fg('');watch.fg('com.webos.app.home');
assert.equal(calls.length,beforeUpdateClose,'Home closure must not trigger a helper launch attempt');
assert.equal(rpc('homeStatus').enabled,true,'Home closure must preserve routing');
assert.equal(files.get('/media/developer/apps/usr/palm/applications/com.local.nativehome/state/controller.pid'),'1');
assert(!commands.includes('Q'),'Home closure must not stop the relay');
watch.fg('test.app');worker.stdout.emit('data',Buffer.from('LGHOME\n'));assert.equal(calls.at(-1),'com.webos.app.home');
const count=calls.length;watch.fg('com.webos.app.home');assert.equal(calls.length,count,'explicit visit must not bounce back');assert.equal(rpc('homeStatus').enabled,true);
worker.stdout.emit('data',Buffer.from('HOME\n'));assert.equal(calls.at(-1),'com.gathin.tvhome');
assert.equal(rpc('setHomeControl',{enabled:false}).enabled,false);assert.equal(commands.filter(c=>c!=='P').at(-1),'D');
let before=calls.length;watch.fg('test.app');watch.fg('com.webos.app.home');worker.stdout.emit('data',Buffer.from('HOME\n'));assert.equal(calls.length,before);
rpc('openLGHome');assert.equal(rpc('homeStatus').enabled,false);assert.equal(calls.at(-1),'com.webos.app.home');
rpc('setHomeControl',{enabled:true});assert.equal(commands.filter(c=>c!=='P').at(-1),'E');now+=8000;worker.stdout.emit('data',Buffer.from('P\n'));before=calls.length;watch.fg('test.app');watch.fg('com.webos.app.home');assert.equal(calls.length,before+1);
assert(![...files.keys()].some(p=>p.endsWith('/blocked')));assert.equal(rpc('setHomeControl',{enabled:'false'}).returnValue,false);
console.log('PASS real controller: one-time LG visit, next Home, disabled Home/Back routing, persisted preference, no emergency latch');

// The JS-service jail exposes its own directory, not the Helper application.
const serviceChannel='/media/developer/apps/usr/palm/services/com.gathin.tvhome.renewal/state/home-control';
assert.equal(rpc('homeStatus',{},serviceChannel).enabled,true);
assert.equal(rpc('setHomeControl',{enabled:false},serviceChannel).enabled,false);
assert.equal(rpc('homeStatus').enabled,false,'legacy Home still reads the same controller state');
assert.equal(rpc('setHomeControl',{enabled:true},serviceChannel).enabled,true);
assert.equal(rpc('openLGHome',{},serviceChannel).returnValue,true);
assert.equal(rpc('homeStatus',{},serviceChannel).enabled,true,'visiting LG Home preserves Home routing');
console.log('PASS service-owned channel and legacy Home use the same live controller');

// Product Home routing must carry a live generation, not rely on a UI hint alone.
worker.stdout.emit('data',Buffer.from('HOME\n'));
const opened=launches.at(-1),hint=opened.params&&opened.params.cytvHome;
assert(hint&&hint.reason==='home','physical Home needs a generated activation hint');
const info=rpc('presentationContext',{},serviceChannel);
assert.equal(info.generation,hint.generation);assert.equal(info.eligible,true);
watch.fg('com.gathin.tvhome');worker.stdout.emit('data',Buffer.from('HOME\n'));
assert.equal(launches.at(-1).params.cytvHome.generation,hint.generation,'repeated Home keeps one owned generation');
assert.equal(rpc('presentationDismissed',{generation:hint.generation},serviceChannel).dismissed,true);
const dismissedCount=calls.length;watch.fg('com.webos.app.home');
assert.equal(calls.length,dismissedCount,'dismissal must cancel return bookkeeping before the window closes');
worker.stdout.emit('data',Buffer.from('HOME\n'));
const replacement=launches.at(-1).params.cytvHome.generation;
assert.notEqual(replacement,hint.generation);
assert.equal(rpc('presentationDismissed',{generation:hint.generation},serviceChannel).returnValue,false);
assert.equal(rpc('presentationContext',{},serviceChannel).generation,replacement);
console.log('PASS actual controller: physical activation, context bridge, repeated Home and no-bounce dismissal');

// A rejected close must not suppress a later required off/Stop close.
closeMode='deny';rpc('setHomeControl',{enabled:false});const failedCloseCount=closeCalls.length;
rpc('setHomeControl',{enabled:true});rpc('setHomeControl',{enabled:false});
assert.equal(closeCalls.length,failedCloseCount+1,'known failure permits a later independent close');
rpc('setHomeControl',{enabled:true});
closeMode='hold';rpc('setHomeControl',{enabled:false});
assert.equal(closeReplies.length,1);
rpc('setHomeControl',{enabled:true});const beforePendingClose=calls.length;
worker.stdout.emit('data',Buffer.from('HOME\n'));
assert.equal(calls.length,beforePendingClose,'a previous unresolved close must settle before a new SAM launch');
closeReplies.shift()();closeMode='success';
assert.equal(calls.length,beforePendingClose+1);
assert.equal(calls.at(-1),'com.gathin.tvhome');
console.log('PASS actual controller: known close failure and unresolved-close/new-activation ordering');

// Unknown close outcome must not be replayed or race a new window.
closeMode='unknown';rpc('setHomeControl',{enabled:false});const unknownCloseCount=closeCalls.length;
rpc('setHomeControl',{enabled:true});const unknownLaunchCount=calls.length;allowWorkerEnd=true;
worker.stdout.emit('data',Buffer.from('HOME\n'));
assert.equal(calls.length,unknownLaunchCount,'unresolved close outcome refuses a new window');
assert.equal(workerEnds,1,'unavailable UI routing releases the relay instead of trapping Home');
closeMode='success';rpc('setHomeControl',{enabled:false});
assert.equal(closeCalls.length,unknownCloseCount,'unknown close is not automatically replayed');
assert.equal(commands.filter(c=>c!=='P').at(-1),'D','off still releases routing independently of UI closure');
console.log('PASS actual controller: unknown close fenced without replay and input release independent');
