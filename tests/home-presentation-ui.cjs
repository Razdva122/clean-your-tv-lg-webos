// Actual app event adapters, separate from the pure state-machine and demo tests.
const {assert,chromium,stage,fs,path}=require('./themes/browser.cjs'),http=require('node:http');
(async()=>{
 const site=stage('presentation'),server=http.createServer((req,res)=>{
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
     setTimeout(()=>bridge.onservicecallback(reply),0);return;
    }
    original.call(this,uri,raw);
   };
   await ThemeManager.selectInstalled((await ThemeManager.list()).find(t=>t.id==='builtin:ribbon'));
   HomePresentationController.show({});
  });
  assert.equal(await n.page.evaluate(()=>HomePresentationController.state().mode),'full','manual launch is opaque even with content preview');
  assert.equal(await n.page.evaluate(()=>nativeRequests),0,'manual launch cannot query itself into overlay');
  await n.page.evaluate(()=>HomePresentationController.show({cytvHome:{reason:'home',generation:7}}));
  await n.page.waitForFunction(()=>HomePresentationController.state().mode==='overlay',null,{timeout:3000});
  assert.equal(await n.page.evaluate(()=>nativeRequests),1);
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
  await n.page.evaluate(()=>{nativeReply={returnValue:true,eligible:true,content:true,generation:7,observedAgeMs:0};HomePresentationController.show({cytvHome:{reason:'home',generation:7}});});
  await n.page.waitForFunction(()=>HomePresentationController.state().mode==='overlay',null,{timeout:3000});
  await n.page.evaluate(()=>document.dispatchEvent(new CustomEvent('webOSRelaunch',{detail:{reason:'startup'}})));
  assert.equal(await n.page.evaluate(()=>HomePresentationController.state().mode),'full','startup relaunch must show opaque rather than dismiss');
  assert.equal(await n.page.evaluate(()=>window.closeCalls),1);
  await n.page.evaluate(()=>document.dispatchEvent(new CustomEvent('webOSRelaunch',{detail:{cytvHome:{reason:'home',generation:7}}})));
  await n.page.waitForFunction(()=>HomePresentationController.state().mode==='overlay',null,{timeout:3000});
  await n.page.evaluate(()=>document.dispatchEvent(new CustomEvent('webOSRelaunch',{detail:{}})));
  assert.equal(await n.page.evaluate(()=>HomePresentationController.state().mode),'full','manual relaunch is opaque');
  assert.equal(await n.page.evaluate(()=>window.closeCalls),1);
  // An opaque overlay can still sit above live video. Neither wallpaper nor
  // input preview may acquire the hardware pipeline from visibility alone.
  await n.page.evaluate(async()=>{
   window.previewCreations=0;window.PREVIEW_INPUT_MEDIA=()=>{previewCreations++;return document.createElement('div');};
   InputSources.setPreviewEnabled(localStorage,true);
   TV_APPS.inputs=[{appId:'com.webos.app.hdmi1',label:'Synthetic HDMI'}];
   await ThemeManager.selectInstalled((await ThemeManager.list()).find(t=>t.id==='builtin:liquid-glass'));
   HomePresentationController.show({cytvHome:{reason:'home',generation:7}});
  });
  await n.page.waitForTimeout(50);
  await n.page.mouse.move(0,0);await n.page.locator('.ctv-input-tile').first().hover();
  await n.page.waitForTimeout(900);
  assert.equal(await n.page.evaluate(()=>previewCreations),0,'known lower content blocks input preview');
  await n.page.evaluate(()=>{nativeReply={returnValue:true,eligible:false,content:false,generation:7,observedAgeMs:0};HomePresentationController.show({cytvHome:{reason:'home',generation:7}});});
  await n.page.waitForFunction(()=>previewCreations===1,null,{timeout:3000});
  await n.page.evaluate(()=>{nativeReply=null;HomePresentationController.show({cytvHome:{reason:'home',generation:7}});});
  assert.equal(await n.page.locator('.ctv-input-preview').count(),0,'context reset releases active hardware preview immediately');
  await n.page.waitForTimeout(900);
  assert.equal(await n.page.evaluate(()=>previewCreations),1,'unknown context cannot restart preview');
  assert.deepEqual(n.errors,[]);
  await n.page.close();
  console.log('PASS native app adapters: modal focus, visibility/relaunch ordering, launch failure/success/staleness, native No-root overlay and strict fallback');
 }finally{await browser.close();await new Promise(r=>server.close(r));}
})().catch(e=>{console.error(e);process.exitCode=1;});
