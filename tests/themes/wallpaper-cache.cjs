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
 console.log('PASS native cache auth, offsets, hash, HTTP ranges, disposal, lease bounds and expiry');
}
run().catch(e=>{console.error(e);process.exitCode=1;});
