// Actual compiled Root renderer and cache/HTTP path. LS2/activity and input media
// are host fixtures; Chrome playback proves no retail decoder/lifecycle acceptance.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os'),cp=require('node:child_process');
const {pathToFileURL}=require('node:url'),{chromium}=require('playwright'),root=path.resolve(__dirname,'..');
(async()=>{
 const site=path.join(root,'build/tests/root-decoder');
 fs.rmSync(site,{recursive:true,force:true});
 cp.execFileSync('python3',['scripts/preview.py','--build',site],{cwd:root});
 cp.execFileSync('python3',['scripts/tv_web_build.py','--input',path.join(site,'root-launcher'),'--output',path.join(site,'compiled')],{cwd:root});
 fs.renameSync(path.join(site,'root-launcher'),path.join(site,'raw'));fs.renameSync(path.join(site,'compiled'),path.join(site,'root-launcher'));
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'cytv-root-decoder-')),methods={},calls=[],sessions=new Set(),holds=new Set();let id=0;
 require('../theme-receiver/register')({register:(name,fn)=>methods[name]=fn,activityManager:{create(name,cb){const a={activityId:++id};holds.add(a);cb(a);},complete(a,cb){holds.delete(a);cb();}}},{appId:'com.cleanyourtv.root.preview',directory,port:0});
 function call(method,payload){calls.push(method);return new Promise(resolve=>methods[method]({payload,ls2Message:{applicationID:()=> 'com.cleanyourtv.root.preview'},respond:v=>{if(method==='wallpaperCacheStart'&&v.sessionId)sessions.add(v.sessionId);resolve(v);}}));}
 const browser=await chromium.launch({headless:true,channel:process.env.BROWSER_CHANNEL||'chrome',args:['--allow-file-access-from-files']});
 try{
  const p=await browser.newPage({viewport:{width:1920,height:1080}}),errors=[];p.on('pageerror',e=>errors.push(e.message));
  await p.exposeBinding('__cacheRPC',(_,uri,raw)=>call(uri.split('/').pop(),JSON.parse(raw)));
  await p.addInitScript(()=>{
   const create=Document.prototype.createElement;window.videoCreates=0;window.inputCreates=0;
   Document.prototype.createElement=function(name){if(name.toLowerCase()==='video')videoCreates++;return create.apply(this,arguments);};
   window.close=()=>{};
  });
  await p.route(/^https:/,r=>r.abort());
  await p.route('**/root-launcher/index.html',r=>r.fulfill({body:fs.readFileSync(path.join(site,'root-launcher/index.html'),'utf8').replace('<script>window.WallpaperMediaCache = undefined;</script>','<script src="wallpaper-media-cache.js"></script>'),contentType:'text/html'}));
  await p.route('**/preview/bridge.js',r=>r.fulfill({body:fs.readFileSync(path.join(site,'preview/bridge.js'),'utf8')+`
   window.CYTV_BROWSER_PREVIEW=false;window.pendingContext=[];
   (function(){var original=PalmServiceBridge.prototype.call;
    PalmServiceBridge.prototype.call=function(uri,raw){var bridge=this;
     if(/\\/wallpaperCache/.test(uri)){__cacheRPC(uri,raw).then(function(v){bridge.onservicecallback(JSON.stringify(v));});return;}
     if(uri==='luna://com.cleanyourtv.root.preview.service/status'&&JSON.parse(raw).presentation==='context'){pendingContext.push(bridge);return;}
     return original.call(this,uri,raw);
    };
    var input=PREVIEW_INPUT_MEDIA;PREVIEW_INPUT_MEDIA=function(uri){inputCreates++;return input(uri);};
   }());`,contentType:'application/javascript'}));
  const url=pathToFileURL(path.join(site,'root-launcher/index.html')).href;
  await p.goto(url);await p.waitForFunction(()=>window.RootLauncherRendered===true);
  // Persist real source/quality, then exercise the cold restoration before show().
  await p.evaluate(async()=>{await ThemeManager.selectInstalled({id:'builtin:liquid-glass'});await PersonalWallpaper.select('builtin:black-hole');HomeWallpaper.setQuality('4k');});
  const beforeCold=calls.length;await p.reload();await p.waitForFunction(()=>window.RootLauncherRendered===true);await p.waitForTimeout(100);
  assert.equal(calls.slice(beforeCold).filter(m=>m==='wallpaperCacheStart').length,0,'cold unknown context must not acquire a media lease');
  assert.equal(await p.evaluate(()=>PersonalWallpaper.state().builtinId),'builtin:black-hole');
  assert.equal(await p.evaluate(()=>videoCreates),0,'cold restoration must not attach media before a positive context');
  assert.equal(await p.locator('#ctvWallpaperVideo').count(),0);
  assert(await p.locator('#ctvWallpaperImage').textContent(),'unknown opaque Home retains the static poster');
  const reply=value=>p.evaluate(value=>{const latest=pendingContext.pop();pendingContext=[];if(!latest)throw Error('missing Root context query');latest.onservicecallback(JSON.stringify({returnValue:true,result:{content:value}}));},value);
  const count=()=>calls.filter(m=>m==='wallpaperCacheCommit').length;
  const commits=count();await reply(true);await p.waitForTimeout(100);
  assert.equal(count(),commits,'active content cannot acquire a cache lease');
  assert(await p.locator('#ctvWallpaperImage').textContent(),'opaque fallback retains the static poster');
  await p.evaluate(()=>HomePresentationController.show({reason:'startup'}));await reply(null);
  assert.equal(await p.evaluate(()=>videoCreates),0,'unknown startup context cannot attach video');
  await p.evaluate(()=>HomePresentationController.show({reason:'startup'}));await reply(false);
  await p.waitForFunction(()=>HomeWallpaper.state().actualQuality==='4k');
  assert.equal(await p.locator('#ctvWallpaperVideo').evaluate(v=>v.videoWidth),3840);
  assert.equal(await p.evaluate(()=>WallpaperStream.state().mode),'mse');assert(count()>commits);
  assert.equal(await p.evaluate(()=>HomePresentationController.state().mode),'full');
  // Force the existing native fallback branch, exercising actual cache HTTP bytes.
  await p.evaluate(()=>{HomeWallpaper.setQuality('image');window.originalSupport=MediaSource.isTypeSupported;MediaSource.isTypeSupported=()=>false;HomeWallpaper.setQuality('4k');});
  await p.waitForFunction(()=>HomeWallpaper.state().actualQuality==='4k'&&document.querySelector('#ctvWallpaperVideo').currentTime>1);
  assert.equal(await p.evaluate(()=>WallpaperStream.state().mode),'native');
  await p.evaluate(()=>HomePresentationController.show({}));
  assert.equal(await p.locator('#ctvWallpaperVideo').count(),0,'refresh synchronously releases active media');
  await p.evaluate(()=>{window.obsoleteContext=pendingContext.pop();HomePresentationController.show({});});await reply(true);
  const deniedCreates=await p.evaluate(()=>videoCreates),deniedCommits=count();
  await p.evaluate(()=>obsoleteContext.onservicecallback(JSON.stringify({returnValue:true,result:{content:false}})));
  await p.waitForTimeout(100);assert.equal(await p.evaluate(()=>videoCreates),deniedCreates);assert.equal(count(),deniedCommits,'stale false cannot reacquire');
  // The real shelf dwell must obey the same snapshot, including re-arm/release.
  await p.evaluate(()=>{HomeWallpaper.setQuality('image');InputSources.setPreviewEnabled(localStorage,true);HomeLayoutState.setThemeLayout({preset:'dock-grid',columns:5,spacingScale:1,textScale:1,focusScale:1.1,inputs:'shelf'});HomePresentationController.show({});});
  await reply(true);await p.keyboard.press('ArrowUp');await p.waitForTimeout(1100);
  assert.equal(await p.evaluate(()=>inputCreates),0,'active content blocks external input acquisition');
  await p.evaluate(()=>HomePresentationController.show({}));await reply(null);await p.waitForTimeout(900);assert.equal(await p.evaluate(()=>inputCreates),0);
  await p.evaluate(()=>HomePresentationController.show({}));await reply(false);await p.waitForFunction(()=>inputCreates===1);
  assert.equal(await p.locator('.ctv-input-preview').count(),1);
  await p.evaluate(()=>HomePresentationController.show({}));assert.equal(await p.locator('.ctv-input-preview').count(),0,'unknown refresh releases input immediately');
  await reply(true);await p.waitForTimeout(1100);assert.equal(await p.evaluate(()=>inputCreates),1);
  await p.evaluate(()=>{HomePresentationController.show({});window.hiddenReply=pendingContext.pop();HomePresentationController.hide();hiddenReply.onservicecallback(JSON.stringify({returnValue:true,result:{content:false}}));});
  assert.equal(await p.locator('#ctvWallpaperVideo,.ctv-input-preview').count(),0);
  assert.deepEqual(errors,[]);
  console.log('PASS compiled Root decoder snapshot gate: cold attachment, true/unknown/startup, real cache MSE/native, stale release, input shelf; no TV claim');
 }finally{await browser.close();for(const sessionId of sessions)await call('wallpaperCacheStop',{sessionId});fs.rmSync(directory,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exitCode=1;});
