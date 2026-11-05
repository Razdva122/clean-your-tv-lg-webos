// Actual app event adapters, separate from the pure state-machine and demo tests.
const {assert,chromium,stage,fs,path}=require('./themes/browser.cjs'),http=require('node:http'),cp=require('node:child_process');
(async()=>{
 const site=stage('presentation');
 // Compile staged JS/CSS/HTML with the production compiler. Keep preview-only
 // font/inventory fixtures separate from the independently checked IPK builder.
 for(const edition of ['launcher','root-launcher']) {
  const input=path.join(site,edition),files={};
  function collect(dir) { for(const name of fs.readdirSync(dir)) {
   const file=path.join(dir,name);
   if(fs.statSync(file).isDirectory())collect(file);
   else if(/\.(js|css|html)$/.test(name))files[path.relative(input,file).split(path.sep).join('/')]=fs.readFileSync(file,'utf8');
  }}
  collect(input);
  const compiled=JSON.parse(cp.execFileSync(process.execPath,['scripts/compile-tv-web.cjs'],{input:JSON.stringify(files),maxBuffer:32*1024*1024}).toString());
  for(const [name,body] of Object.entries(compiled))fs.writeFileSync(path.join(input,name),body);
 }
 const server=http.createServer((req,res)=>{
  const file=path.resolve(site,'.'+new URL(req.url,'http://localhost').pathname);
  if(!file.startsWith(site+path.sep)||!fs.existsSync(file))return res.writeHead(404).end();
  res.setHeader('Content-Type',({'.js':'application/javascript','.json':'application/json','.css':'text/css','.png':'image/png','.jpg':'image/jpeg','.ttf':'font/ttf'})[path.extname(file)]||'text/html');res.end(fs.readFileSync(file));
 });
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const browser=await chromium.launch({headless:true,channel:process.env.BROWSER_CHANNEL||'chrome'});
 async function open(edition,native=false){
  const page=await browser.newPage({viewport:{width:1920,height:1080}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));await page.route(/^https:/,r=>r.abort());
  if(native)await page.route('**/preview/bridge.js',r=>r.fulfill({body:fs.readFileSync(path.join(site,'preview/bridge.js'),'utf8')+'\nwindow.CYTV_BROWSER_PREVIEW=false;'}));
  await page.goto('http://127.0.0.1:'+server.address().port+'/'+edition+'/index.html');
  await page.waitForFunction(()=>window.RootLauncherRendered===true);return {page,errors};
 }
 try {
  // Native handlesRelaunch windows receive no animation frames until activated.
  // Startup must prepare saved appearance, activate, then acknowledge painted UI.
  for(const edition of ['root-launcher','launcher']) {
  const cold=await browser.newPage({viewport:{width:1920,height:1080}});
  await cold.addInitScript(()=>{
   const frame=window.requestAnimationFrame.bind(window),queued=[];
   window.activationCalls=0;
   Object.defineProperty(document,'hidden',{configurable:true,get:()=>window.activationCalls===0});
   window.requestAnimationFrame=callback=>window.activationCalls?frame(callback):(queued.push(callback),queued.length);
   window.PalmSystem={activate(){window.activationCalls++;queued.splice(0).forEach(callback=>frame(callback));document.dispatchEvent(new Event('visibilitychange'));}};
  });
  await cold.route('**/app.js',route=>route.fulfill({body:
   'var personalStart=PersonalWallpaper.start;PersonalWallpaper.start=function(){window.personalRequested=true;return window.personalGate||(window.personalGate=new Promise(function(resolve){window.releasePersonal=function(){resolve(personalStart());};}));};\n'+
   fs.readFileSync(path.join(site,edition,'app.js'),'utf8')}));
  if(edition==='launcher')await cold.route('**/preview/bridge.js',r=>r.fulfill({body:fs.readFileSync(path.join(site,'preview/bridge.js'),'utf8')+'\nwindow.CYTV_BROWSER_PREVIEW=false;'}));
  await cold.goto('http://127.0.0.1:'+server.address().port+'/'+edition+'/index.html');
  await cold.waitForFunction(()=>window.personalRequested===true,{},{polling:50,timeout:3000});
  assert.equal(await cold.evaluate(()=>activationCalls),0,'saved personal appearance must settle before activation');
  assert.equal(await cold.evaluate(()=>RootLauncherRendered),false);
  await cold.evaluate(()=>releasePersonal());
  await cold.waitForFunction(()=>window.RootLauncherRendered===true,{},{polling:50,timeout:3000});
  assert.equal(await cold.evaluate(()=>activationCalls),1,'cold '+edition+' activates before waiting for foreground animation frames');
  assert.equal(await cold.locator('#homeSurface').evaluate(el=>getComputedStyle(el).visibility),'visible');
  await cold.close();
  }
  const {page,errors}=await open('root-launcher');
  await page.evaluate(async()=>{
   window.closeCalls=0;window.close=()=>window.closeCalls++;
   window.PREVIEW_HOME_CONTEXT='content';
   await ThemeManager.selectInstalled((await ThemeManager.list()).find(t=>t.id==='builtin:ribbon'));
   HomePresentationController.show({});
   window.testHidden=false;
   Object.defineProperty(document,'hidden',{configurable:true,get:()=>window.testHidden});
   window.setHidden=value=>{window.testHidden=value;document.dispatchEvent(new Event('visibilitychange'));};
  });
  const mode=value=>page.waitForFunction(v=>HomePresentationController.state().mode===v,value);
  await mode('overlay');
  assert.equal(await page.evaluate(()=>HomeWallpaper.state().paused),true,'overlay releases Home video wallpaper');
  assert.equal(await page.locator('#ctvWallpaper').evaluate(el=>getComputedStyle(el).display),'none','overlay hides wallpaper plane');
  // Dialog/relaunch must preserve modal focus and opacity.
  await page.locator('#btnSettings').click();
  await page.waitForFunction(()=>RenewalPanel.isOpen());await mode('full');
  const before=await page.evaluate(()=>document.activeElement.id);
  await page.evaluate(()=>document.dispatchEvent(new Event('webOSRelaunch')));
  assert.equal(await page.evaluate(()=>document.activeElement.id),before,'Home must not steal focus from an open dialog');
  assert.equal(await page.evaluate(()=>window.closeCalls),0);
  for(let i=0;i<3&&await page.evaluate(()=>RenewalPanel.isOpen());i++)await page.keyboard.press('Escape');
  await page.waitForFunction(()=>!RenewalPanel.isOpen());await mode('overlay');
  // Firmware relaunch while hidden, then activation/visible notification.
  await page.evaluate(()=>{setHidden(true);document.dispatchEvent(new Event('webOSRelaunch'));setHidden(false);});
  await mode('overlay');assert.equal(await page.evaluate(()=>window.closeCalls),0);
  // The context reply may settle between visible notification and activation relaunch.
  await page.evaluate(()=>{setHidden(true);setHidden(false);});await mode('overlay');
  await page.evaluate(()=>document.dispatchEvent(new Event('webOSRelaunch')));
  await mode('overlay');assert.equal(await page.evaluate(()=>window.closeCalls),0);
  await page.evaluate(()=>document.dispatchEvent(new Event('webOSRelaunch')));
  await mode('closed');assert.equal(await page.evaluate(()=>window.closeCalls),1);
  await page.evaluate(()=>document.dispatchEvent(new Event('webOSRelaunch')));await mode('overlay');
  // An actual tile launch: only an explicit, current success dismisses Home.
  await page.evaluate(()=>{
   const call=PalmServiceBridge.prototype.call;window.pendingLaunches=[];
   PalmServiceBridge.prototype.call=function(uri,raw){if(uri==='luna://com.webos.applicationManager/launch'){pendingLaunches.push(this);return;}call.call(this,uri,raw);};
  });
  await page.keyboard.press('Enter');
  await page.waitForFunction(()=>pendingLaunches.length===1);
  await page.evaluate(()=>pendingLaunches.shift().onservicecallback(JSON.stringify({returnValue:false})));
  assert.equal(await page.evaluate(()=>HomePresentationController.state().mode),'overlay');
  await page.keyboard.press('Enter');await page.waitForFunction(()=>pendingLaunches.length===1);
  await page.evaluate(()=>{setHidden(true);setHidden(false);});await mode('overlay');
  await page.evaluate(()=>pendingLaunches.shift().onservicecallback(JSON.stringify({returnValue:true})));
  assert.equal(await page.evaluate(()=>window.closeCalls),1,'late success cannot close reopened Home');
  await page.keyboard.press('Enter');await page.waitForFunction(()=>pendingLaunches.length===1);
  await page.evaluate(()=>pendingLaunches.shift().onservicecallback(JSON.stringify({returnValue:true})));
  await mode('closed');assert.equal(await page.evaluate(()=>window.closeCalls),2);
  assert.deepEqual(errors,[]);await page.close();
  // Actual No-root edition, with browser simulation disabled. Only the
  // measured native Helper seam supplies content, never Root preview context.
  const n=await open('launcher',true);
  await n.page.evaluate(async()=>{
   window.closeCalls=0;window.close=()=>window.closeCalls++;
   window.PREVIEW_HOME_CONTEXT='content';
   window.nativeRequests=0;
   window.nativeReply={returnValue:true,eligible:true,content:true,generation:7,observedAgeMs:10};
   const original=PalmServiceBridge.prototype.call;
   PalmServiceBridge.prototype.call=function(uri,raw){
    if(uri==='luna://com.gathin.tvhome.renewal/presentationContext'){
     nativeRequests++;const bridge=this,reply=JSON.stringify(nativeReply);
     const deliver=()=>bridge.onservicecallback(reply);
     if(window.deferNative)(window.nativePending||(window.nativePending=[])).push(deliver);else setTimeout(deliver,0);return;
    }
    original.call(this,uri,raw);
   };
   await ThemeManager.selectInstalled((await ThemeManager.list()).find(t=>t.id==='builtin:ribbon'));
   nativeRequests=0;HomePresentationController.show({});
  });
  assert.equal(await n.page.evaluate(()=>HomePresentationController.state().mode),'full','manual launch is opaque even with content preview');
  await n.page.waitForFunction(()=>nativeRequests===1,null,{timeout:3000});
  await n.page.waitForTimeout(30);
  assert.equal(await n.page.evaluate(()=>HomePresentationController.state().mode),'full','manual facts cannot authorize transparency');
  await n.page.evaluate(()=>HomePresentationController.show({cytvHome:{reason:'home',generation:7}}));
  await n.page.waitForFunction(()=>HomePresentationController.state().mode==='overlay',null,{timeout:3000});
  assert.equal(await n.page.evaluate(()=>nativeRequests),2);
  await n.page.locator('#btnSettings').click();
  await n.page.waitForFunction(()=>RenewalPanel.isOpen());
  assert.equal(await n.page.evaluate(()=>HomePresentationController.state().mode),'full');
  for(let i=0;i<3&&await n.page.evaluate(()=>RenewalPanel.isOpen());i++)await n.page.keyboard.press('Escape');
  await n.page.waitForFunction(()=>HomePresentationController.state().mode==='overlay',null,{timeout:3000});
  await n.page.keyboard.press('Escape');
  assert.equal(await n.page.evaluate(()=>window.closeCalls),1,'physical Back adapter closes No-root overlay');
  for(const reply of [null,{returnValue:false},{returnValue:true,eligible:true,content:true,generation:8,observedAgeMs:0},
   {returnValue:true,eligible:true,content:true,generation:7,observedAgeMs:2001}]) {
   await n.page.evaluate(reply=>{nativeReply=reply;HomePresentationController.show({cytvHome:{reason:'home',generation:7}});},reply);
   await n.page.waitForTimeout(30);
   assert.equal(await n.page.evaluate(()=>HomePresentationController.state().mode),'full','unknown/stale/cross-generation reply is opaque');
  }
  await n.page.evaluate(()=>{nativeReply={returnValue:true,eligible:true,content:true,generation:7,observedAgeMs:0};HomePresentationController.show({reason:'startup',cytvHome:{reason:'home',generation:7}});});
  assert.equal(await n.page.evaluate(()=>HomePresentationController.state().mode),'full','startup cannot become overlay from a launch hint');
  // Non-Home activations do not toggle an existing transparent Ribbon.
  await n.page.evaluate(()=>{window.activationCalls=0;window.PalmSystem={activate(){activationCalls++;}};});
  await n.page.evaluate(()=>{nativeReply={returnValue:true,eligible:true,content:true,generation:7,observedAgeMs:0};HomePresentationController.show({cytvHome:{reason:'home',generation:7}});});
  await n.page.waitForFunction(()=>HomePresentationController.state().mode==='overlay',null,{timeout:3000});
  await n.page.evaluate(()=>document.dispatchEvent(new CustomEvent('webOSRelaunch',{detail:{reason:'startup'}})));
  assert.equal(await n.page.evaluate(()=>HomePresentationController.state().mode),'full','startup relaunch must show opaque rather than dismiss');
  assert.equal(await n.page.evaluate(()=>activationCalls),1,'native No-root owns warm activation');
  assert.equal(await n.page.evaluate(()=>window.closeCalls),1);
  await n.page.evaluate(()=>document.dispatchEvent(new CustomEvent('webOSRelaunch',{detail:{cytvHome:{reason:'home',generation:7}}})));
  await n.page.waitForFunction(()=>HomePresentationController.state().mode==='overlay',null,{timeout:3000});
  await n.page.evaluate(()=>document.dispatchEvent(new CustomEvent('webOSRelaunch',{detail:{}})));
  assert.equal(await n.page.evaluate(()=>HomePresentationController.state().mode),'full','manual relaunch is opaque');
  assert.equal(await n.page.evaluate(()=>window.closeCalls),1);
  // An explicit manual reason cannot inherit authority from an attached Home hint.
  const beforeManual=await n.page.evaluate(()=>nativeRequests);
  await n.page.evaluate(()=>HomePresentationController.show({reason:'manual',cytvHome:{reason:'home',generation:7}}));
  await n.page.waitForTimeout(30);
  assert.equal(await n.page.evaluate(()=>HomePresentationController.state().mode),'full','explicit manual+hint show must remain opaque');
  assert.equal(await n.page.evaluate(()=>HomePresentationController.state().content),null,'explicit manual+hint cannot release decoder hold');
  assert.equal(await n.page.evaluate(()=>nativeRequests),beforeManual,'manual hint cannot fall through to decoder-only query');
  await n.page.evaluate(()=>HomePresentationController.show({cytvHome:{reason:'home',generation:7}}));
  await n.page.waitForFunction(()=>HomePresentationController.state().mode==='overlay',null,{timeout:3000});
  await n.page.evaluate(()=>document.dispatchEvent(new CustomEvent('webOSRelaunch',{detail:{reason:'manual',cytvHome:{reason:'home',generation:7}}})));
  await n.page.waitForTimeout(30);
  assert.equal(await n.page.evaluate(()=>HomePresentationController.state().mode),'full','explicit manual+hint relaunch must show opaque rather than dismiss');
  assert.equal(await n.page.evaluate(()=>HomePresentationController.state().content),null);
  assert.equal(await n.page.evaluate(()=>window.closeCalls),1,'explicit manual+hint relaunch must not close the existing overlay');
  // Mutation of the caller's object cannot retarget an in-flight RPC or refresh.
  await n.page.evaluate(()=>{
   window.deferNative=true;window.nativePending=[];
   window.mutableActivation={cytvHome:{reason:'home',generation:7}};
   nativeReply={returnValue:true,eligible:true,content:true,generation:8,observedAgeMs:0};
   HomePresentationController.show(mutableActivation);mutableActivation.cytvHome.generation=8;nativePending.shift()();
  });
  assert.equal(await n.page.evaluate(()=>HomePresentationController.state().content),null,'mutation7to8 cannot accept reply8 for original request7');
  assert.equal(await n.page.evaluate(()=>HomePresentationController.state().mode),'full');
  await n.page.evaluate(()=>{
   mutableActivation={cytvHome:{reason:'home',generation:7}};
   nativeReply={returnValue:true,eligible:true,content:true,generation:7,observedAgeMs:0};
   HomePresentationController.show(mutableActivation);mutableActivation.cytvHome.generation=8;mutableActivation.reason='manual';nativePending.shift()();
  });
  assert.equal(await n.page.evaluate(()=>HomePresentationController.state().mode),'overlay','original reply7 remains valid for the request7 snapshot');
  await n.page.evaluate(()=>{HomePresentationController.setTheme({presentation:'overlay'});nativePending.shift()();});
  assert.equal(await n.page.evaluate(()=>HomePresentationController.state().mode),'overlay','refresh cannot rebind snapshot to mutated reason/generation');
  await n.page.evaluate(()=>{
   nativeReply={returnValue:true,eligible:true,content:true,generation:8,observedAgeMs:0};
   HomePresentationController.show({cytvHome:{reason:'home',generation:8}});nativePending.shift()();deferNative=false;
  });
  assert.equal(await n.page.evaluate(()=>HomePresentationController.state().mode),'overlay','a new show may establish its own generation8 normally');
  // An opaque overlay can still sit above live video. Neither wallpaper nor
  // input preview may acquire the hardware pipeline from visibility alone.
  await n.page.evaluate(async()=>{
   window.previewCreations=0;window.PREVIEW_INPUT_MEDIA=()=>{previewCreations++;return document.createElement('div');};
   window.wallpaperCreations=0;const create=document.createElement.bind(document);document.createElement=function(tag){if(tag==='video')wallpaperCreations++;return create(tag);};
   InputSources.setPreviewEnabled(localStorage,true);
   TV_APPS.inputs=[{appId:'com.webos.app.hdmi1',label:'Synthetic HDMI'}];
   await ThemeManager.selectInstalled((await ThemeManager.list()).find(t=>t.id==='builtin:liquid-glass'));
   HomePresentationController.show({cytvHome:{reason:'home',generation:7}});
  });
  await n.page.waitForTimeout(50);
  await n.page.evaluate(()=>HomeWallpaper.configure({manifest:{id:'test:decoder',title:'Synthetic',defaults:{wallpaperAssetId:'poster',dim:0},assets:[{id:'poster',width:1920,height:1080}],wallpaperVideo:{variants:[{quality:'1080p',width:1920,height:1080}]}},assetHandles:{poster:'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw=='},videoHandles:{'1080p':'/synthetic-unavailable.mp4'}}));
  assert.equal(await n.page.evaluate(()=>wallpaperCreations),0,'known lower content blocks wallpaper decoder');
  await n.page.mouse.move(0,0);await n.page.locator('.ctv-input-tile').first().hover();
  await n.page.waitForTimeout(900);
  assert.equal(await n.page.evaluate(()=>previewCreations),0,'known lower content blocks input preview');
  await n.page.evaluate(()=>{nativeReply={returnValue:true,eligible:false,content:false,generation:7,observedAgeMs:0};HomePresentationController.show({cytvHome:{reason:'home',generation:7}});});
  await n.page.waitForFunction(()=>previewCreations===1,null,{timeout:3000});
  assert(await n.page.evaluate(()=>wallpaperCreations>0),'only a confirmed empty context can acquire wallpaper video');
  await n.page.evaluate(()=>{nativeReply=null;HomePresentationController.show({cytvHome:{reason:'home',generation:7}});});
  assert.equal(await n.page.locator('.ctv-input-preview').count(),0,'context reset releases active hardware preview immediately');
  await n.page.waitForTimeout(900);
  assert.equal(await n.page.evaluate(()=>previewCreations),1,'unknown context cannot restart preview');
  await n.page.evaluate(()=>{nativeReply={returnValue:true,eligible:false,content:false,generation:42,observedAgeMs:0};HomePresentationController.show({});});
  await n.page.waitForFunction(()=>previewCreations===2,null,{timeout:3000});
  assert.equal(await n.page.evaluate(()=>HomePresentationController.state().mode),'full','manual empty facts resume input preview while opaque');
  await n.page.evaluate(()=>{nativeReply=null;HomePresentationController.show({});});
  assert.equal(await n.page.locator('.ctv-input-preview').count(),0,'manual context reset immediately releases input preview');
  // Test wallpaper separately from the input preview's exclusive decoder hold.
  await n.page.evaluate(()=>HomeInputShelf.togglePreview());
  for(const content of [false,null]) {
   const before=await n.page.evaluate(()=>wallpaperCreations);
   await n.page.evaluate(content=>{nativeReply={returnValue:true,eligible:true,content,generation:42,observedAgeMs:0};HomePresentationController.show({});},content);
   await n.page.waitForTimeout(30);
   assert.equal(await n.page.evaluate(()=>HomePresentationController.state().content),null,'inconsistent wire reply must stay unknown even decoder-only');
   assert.equal(await n.page.evaluate(()=>HomePresentationController.state().mode),'full');
   assert.equal(await n.page.evaluate(()=>wallpaperCreations),before,'inconsistent wire reply cannot acquire decoder');
  }
  await n.page.evaluate(()=>{nativeReply={returnValue:true,eligible:true,content:true,generation:42,observedAgeMs:0};HomePresentationController.show({});});
  await n.page.waitForFunction(()=>HomePresentationController.state().content===true,null,{timeout:3000});
  assert.equal(await n.page.evaluate(()=>HomePresentationController.state().mode),'full','valid eligible=true wire reply cannot authorize manual transparency');
  assert.equal(await n.page.locator('#ctvWallpaperVideo').count(),0,'valid active content retains decoder hold');
  // Manual/startup/wake may use fresh decoder facts while remaining opaque.
  for(const activation of [{},{reason:'manual'},{reason:'startup'},{reason:'wake'}]) {
   const before=await n.page.evaluate(()=>wallpaperCreations);
   await n.page.evaluate(activation=>{nativeReply={returnValue:true,eligible:false,content:false,generation:42,observedAgeMs:0};HomePresentationController.show(activation);},activation);
   await n.page.waitForFunction(()=>HomePresentationController.state().content===false,null,{timeout:3000});
   assert.equal(await n.page.evaluate(()=>HomePresentationController.state().mode),'full');
   assert(await n.page.evaluate(before=>wallpaperCreations>before,before),'fresh manual/startup decoder facts permit own video attachment');
   await n.page.evaluate(()=>{nativeReply=null;HomePresentationController.show({});});await n.page.waitForTimeout(30);
   assert.equal(await n.page.locator('#ctvWallpaperVideo').count(),0,'unknown manual context keeps poster');
  }
  for(const reply of [null,{returnValue:true,eligible:false,content:true,generation:42,observedAgeMs:0},
   {returnValue:true,eligible:false,content:false,generation:42,observedAgeMs:2001},
   {returnValue:true,eligible:false,content:'false',generation:42,observedAgeMs:0}]) {
   await n.page.evaluate(reply=>{nativeReply=reply;HomePresentationController.show({reason:'startup'});},reply);await n.page.waitForTimeout(30);
   assert.equal(await n.page.locator('#ctvWallpaperVideo').count(),0,'active/unknown/stale/malformed startup facts retain decoder hold');
   assert.equal(await n.page.evaluate(()=>HomePresentationController.state().mode),'full');
  }
  await n.page.evaluate(()=>{
   window.deferNative=true;window.nativePending=[];
   nativeReply={returnValue:true,eligible:false,content:false,generation:42,observedAgeMs:0};HomePresentationController.show({});
   nativeReply=null;HomePresentationController.show({reason:'startup'});
   nativePending.shift()();
  });
  assert.equal(await n.page.evaluate(()=>HomePresentationController.state().content),null,'late manual decoder reply cannot release newer startup hold');
  assert.equal(await n.page.locator('#ctvWallpaperVideo').count(),0);
  await n.page.evaluate(()=>{nativePending.shift()();deferNative=false;});
  for(const hint of [undefined,null,'home',{reason:'home',generation:'7'},{reason:'home'},{reason:'other',generation:7}]) {
   await n.page.evaluate(hint=>{nativeReply={returnValue:true,eligible:false,content:false,generation:42,observedAgeMs:0};HomePresentationController.show({cytvHome:hint});},hint);
   await n.page.waitForTimeout(30);assert.equal(await n.page.evaluate(()=>HomePresentationController.state().content),null,'bad Home hint never falls through decoder-only');
  }
  await n.page.keyboard.press('Escape');
  assert.equal(await n.page.evaluate(()=>window.closeCalls),1,'shelf Back first returns focus to dock');
  assert.equal(await n.page.locator('#tiles .item.focused').count(),1);
  await n.page.keyboard.press('Escape');
  assert.equal(await n.page.evaluate(()=>window.closeCalls),2,'opaque native fallback has a Back exit even with Helper unavailable');
  assert.deepEqual(n.errors,[]);
  await n.page.close();
  console.log('PASS native app adapters: modal focus, visibility/relaunch ordering, launch failure/success/staleness, native No-root overlay and strict fallback');
 }finally{await browser.close();await new Promise(r=>server.close(r));}
})().catch(e=>{console.error(e);process.exitCode=1;});
