// Real No-root launcher: denied direct EIM, same-package snapshots and independent Home settings.
const {assert,chromium,stage,open}=require('./browser.cjs');
(async()=>{
 const site=stage(),browser=await chromium.launch({headless:true,channel:process.env.BROWSER_CHANNEL||'chrome'});
 try{
  const context=await browser.newContext({locale:'en-US'});
  await context.addInitScript(()=>{
   let ctor;window.inputReads=[];window.pendingInputs=[];window.holdInputs=false;
   window.inputSnapshot={returnValue:true,devices:[{appId:'preview.hdmi1',label:'HDMI 1',connected:true},{appId:'preview.hdmi2',label:'HDMI 2',connected:false}]};
   Object.defineProperty(window,'PalmServiceBridge',{configurable:true,set(value){ctor=value},get(){
    if(ctor&&!ctor.inputRecorded&&ctor.prototype.call){const call=ctor.prototype.call;ctor.prototype.call=function(uri,raw){
     if(uri==='luna://com.webos.service.eim/getAllInputStatus'){inputReads.push({uri,payload:JSON.parse(raw)});this.onservicecallback(JSON.stringify({returnValue:false,errorCode:-1}));return;}
     if(uri==='luna://com.gathin.tvhome.renewal/inputStatus'){inputReads.push({uri,payload:JSON.parse(raw)});const answer=()=>this.onservicecallback(JSON.stringify(inputSnapshot));if(holdInputs)pendingInputs.push(answer);else setTimeout(answer,30);return;}
     return call.apply(this,arguments);
    };ctor.inputRecorded=true;}return ctor;
   }});
  });
  const {page,errors}=await open(context,site,'launcher');
  assert.deepEqual(await page.evaluate(()=>inputReads.map(r=>r.uri)),['luna://com.webos.service.eim/getAllInputStatus','luna://com.gathin.tvhome.renewal/inputStatus']);
  await page.evaluate(()=>HomeLayoutState.setThemeLayout({preset:'dock-grid',columns:5,spacingScale:1,textScale:1,focusScale:1.1,inputs:'shelf'}));
  assert.deepEqual(await page.locator('.ctv-input-status').allTextContents(),['Connected','Not connected','']);
  await page.evaluate(()=>holdInputs=true);
  await page.locator('#btnSettings').click();
  assert.equal(await page.evaluate(()=>pendingInputs.length),1,'settings refresh coalesces metadata');
  await page.waitForFunction(()=>{const button=document.getElementById('homeRoutingToggle');return button&&!button.hidden&&!button.disabled;});
  await page.evaluate(()=>{HomeInputShelf.refresh();window.dispatchEvent(new Event('focus'));});
  assert.equal(await page.evaluate(()=>pendingInputs.length),1,'parallel interactions do not fan out');
  const readsBeforeFailure=await page.evaluate(()=>inputReads.length);
  await page.evaluate(()=>{inputSnapshot={returnValue:false};pendingInputs.shift()();});
  await page.waitForTimeout(50);
  assert.equal(await page.locator('.ctv-input-tile.is-connected,.ctv-input-tile.is-disconnected').count(),0,'failed broker clears stale status');
  assert.equal(await page.evaluate(()=>inputReads.length),readsBeforeFailure,'failed read does not retry');
  assert.deepEqual(errors,[]);await page.close();await context.close();
 }finally{await browser.close();}
 console.log('PASS No-root denied-EIM fallback, labels, settings independence, coalescing and failure fallback');
})().catch(error=>{console.error(error);process.exitCode=1;});
