'use strict';
const assert=require('assert/strict'),fs=require('fs'),os=require('os'),path=require('path'),crypto=require('crypto'),http=require('http');
const cache=require('../../theme-receiver/wallpaper-cache');
async function run(){
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'wallpaper-cache-test-')),bytes=Buffer.from('verified-media-bytes'),variant={quality:'1080p',size:bytes.length,sha256:crypto.createHash('sha256').update(bytes).digest('hex')};let holds=0;
 const c=cache.create({directory,ttlMs:100,hold(){holds++;return()=>holds--;}});
 const start=()=>c.start({variants:[variant]});
 const s=await start();assert.equal(holds,1);assert.throws(()=>c.write({sessionId:s.sessionId,quality:'1080p',offset:1,data:bytes.toString('base64')}));
 c.write({sessionId:s.sessionId,quality:'1080p',offset:0,data:bytes.toString('base64')});
 const active=await c.commit({sessionId:s.sessionId});
 function get(url,headers={},method='GET'){return new Promise((resolve,reject)=>{http.get(url,{headers,method},res=>{const chunks=[];res.on('data',b=>chunks.push(b));res.on('end',()=>resolve({status:res.statusCode,headers:res.headers,body:Buffer.concat(chunks)}));}).on('error',reject);});}
 assert.match(active.handles['1080p'],/^http:\/\/127\.0\.0\.1:\d+\/[a-f0-9]{32}\/1080p\.mp4$/);
 let r=await get(active.handles['1080p']);assert.equal(r.status,200);assert.equal(r.body.toString(),bytes.toString());r=await get(active.handles['1080p'],{Range:'bytes=2-5'});assert.equal(r.status,206);assert.equal(r.body.toString(),bytes.subarray(2,6).toString());assert.equal(r.headers['content-range'],'bytes 2-5/'+bytes.length);
 assert.equal((await get(active.handles['1080p'],{Range:'bytes=0-1,3-4'})).status,416);assert.equal((await get(active.handles['1080p'],{Range:'bytes=999-'})).status,416);assert.equal((await get(active.handles['1080p'],{Range:'bytes=-3'})).body.toString(),bytes.subarray(-3).toString());assert.equal((await get(active.handles['1080p'],{Origin:'https://evil.invalid'})).status,403);assert.equal((await get(active.handles['1080p'],{},'HEAD')).body.length,0);assert.equal((await get(active.handles['1080p'].replace('/1080p.mp4','/../bad'))).status,404);
 c.stop({sessionId:s.sessionId});assert.equal(holds,0);assert.equal(fs.readdirSync(directory).length,0);
 const corrupt=await start();c.write({sessionId:corrupt.sessionId,quality:'1080p',offset:0,data:Buffer.alloc(bytes.length).toString('base64')});await assert.rejects(c.commit({sessionId:corrupt.sessionId}),/hash/);assert.equal(holds,0);
 const a=await start(),b=await start();await assert.rejects(start(),/busy/);c.stop({sessionId:a.sessionId});c.stop({sessionId:b.sessionId});
 const expired=await start();await new Promise(r=>setTimeout(r,130));assert.throws(()=>c.keepAlive({sessionId:expired.sessionId}));assert.equal(holds,0);fs.rmdirSync(directory);
 const methods={};require('../../theme-receiver/register')({register:(name,fn)=>methods[name]=fn},{appId:'com.test'});
 for(const name of ['wallpaperCacheStart','wallpaperCacheWrite','wallpaperCacheCommit','wallpaperCacheKeepAlive','wallpaperCacheStop']){assert(methods[name]);let reply;methods[name]({payload:{},ls2Message:{applicationID:()=>'evil'},respond:r=>reply=r});assert.equal(reply.returnValue,false);}
 const activityDirectory=fs.mkdtempSync(path.join(os.tmpdir(),'wallpaper-activity-test-')),activityMethods={},activeActivities=new Map(),completed=[];let activityId=0;
 const manager={create(name,callback){assert(!activeActivities.has(name),'activity names must be distinct');const activity={name,activityId:++activityId};activeActivities.set(name,activity);callback(activity);},complete(activity,callback){assert.equal(activeActivities.get(activity.name),activity);activeActivities.delete(activity.name);completed.push(activity.name);callback();}};
 require('../../theme-receiver/register')({register:(name,fn)=>activityMethods[name]=fn,activityManager:manager},{appId:'com.test',directory:activityDirectory,port:0,ttlMs:1000});
 const call=(method,payload={})=>new Promise(resolve=>activityMethods[method]({payload,ls2Message:{applicationID:()=>'com.test'},respond:resolve}));
 const receiver=await call('themeReceiverStart'),one=await call('wallpaperCacheStart',{variants:[variant]}),two=await call('wallpaperCacheStart',{variants:[variant]});
 assert(receiver.returnValue&&one.returnValue&&two.returnValue);assert.equal(activeActivities.size,3,'receiver and both media leases each own an activity');assert(activeActivities.has('themeReceiver'));const mediaNames=[...activeActivities.keys()].filter(name=>name!=='themeReceiver');assert(mediaNames.every(name=>/^wallpaperMedia-\d+$/.test(name)));
 await call('wallpaperCacheStop',{sessionId:one.sessionId});assert.equal(activeActivities.size,2);assert(activeActivities.has('themeReceiver'));assert(activeActivities.has(mediaNames[1]));
 await call('themeReceiverStop',{sessionId:receiver.sessionId});assert.equal(activeActivities.size,1);assert(activeActivities.has(mediaNames[1]));await call('wallpaperCacheKeepAlive',{sessionId:two.sessionId});await call('wallpaperCacheStop',{sessionId:two.sessionId});assert.equal(activeActivities.size,0);assert.equal(completed.length,3);
 let customHolds=0;const customMethods={};require('../../theme-receiver/register')({register:(name,fn)=>customMethods[name]=fn,activityManager:{create(){throw Error('custom hold must be honored');},complete(){}}},{appId:'com.test',directory:activityDirectory,port:0,hold(){customHolds++;return()=>customHolds--;}});
 const custom=(method,payload={})=>new Promise(resolve=>customMethods[method]({payload,ls2Message:{applicationID:()=>'com.test'},respond:resolve}));const customReceiver=await custom('themeReceiverStart'),customCache=await custom('wallpaperCacheStart',{variants:[variant]});assert.equal(customHolds,2);await custom('themeReceiverStop',{sessionId:customReceiver.sessionId});assert.equal(customHolds,1);await custom('wallpaperCacheStop',{sessionId:customCache.sessionId});assert.equal(customHolds,0);fs.rmdirSync(activityDirectory);
 // A private-looking directory must also belong to the service account.
 if(typeof process.getuid==='function'){
  const vm=require('vm'),foreignDirectory=fs.mkdtempSync(path.join(os.tmpdir(),'wallpaper-foreign-test-')),fakeFs=Object.create(fs);fakeFs.lstatSync=name=>{const stat=fs.lstatSync(name);if(name===foreignDirectory)stat.uid=process.getuid()+1;return stat;};
  const module={exports:{}};vm.runInNewContext(fs.readFileSync(require.resolve('../../theme-receiver/wallpaper-cache'),'utf8'),{module,exports:module.exports,require:name=>name==='fs'?fakeFs:require(name),process,Buffer,Promise,setTimeout,clearTimeout});
  await assert.rejects(module.exports.create({directory:foreignDirectory}).start({variants:[variant]}),/unsafe directory/);assert.equal(fs.readdirSync(foreignDirectory).length,0);fs.rmdirSync(foreignDirectory);
 }
 // Capacity reservations survive asynchronous df without exceeding lease limits.
 const budgetDir=fs.mkdtempSync(path.join(os.tmpdir(),'wallpaper-budget-test-')),budgetCache=cache.create({directory:budgetDir}),originalSpace=cache.space;
 let required=[];cache.space=async size=>{required.push(size);await new Promise(resolve=>setTimeout(resolve,5));return {required:size,available:100000000,shortfall:0};};
 try{
  const results=await Promise.allSettled([budgetCache.start({variants:[variant]}),budgetCache.start({variants:[variant]}),budgetCache.start({variants:[variant]})]);
  assert.equal(results.filter(result=>result.status==='fulfilled').length,2,'only two concurrent leases admitted');
  for(const result of results)if(result.status==='fulfilled')budgetCache.stop({sessionId:result.value.sessionId});
  const first=await budgetCache.start({variants:[variant]});budgetCache.write({sessionId:first.sessionId,quality:'1080p',offset:0,data:bytes.toString('base64')});
  const second=await budgetCache.start({variants:[variant]});assert.equal(required.at(-1),bytes.length+1048576,'df already excludes bytes written to current cache');budgetCache.stop({sessionId:first.sessionId});budgetCache.stop({sessionId:second.sessionId});
  cache.space=async size=>({required:size,available:0,shortfall:size});
  await assert.rejects(budgetCache.start({variants:[variant]}),error=>error.code==='wallpaper-cache-storage-full'&&error.storage.shortfall===bytes.length+1048576);
  assert.equal(fs.readdirSync(budgetDir).length,0,'full disk does not create a partial session');
 }finally{cache.space=originalSpace;fs.rmdirSync(budgetDir);}
 console.log('PASS receiver/media independent activity ownership, hold overrides and cache directory ownership');
 console.log('PASS native cache auth, offsets, hash, HTTP ranges, disposal, lease bounds and expiry');
}
run().catch(e=>{console.error(e);process.exitCode=1;});
