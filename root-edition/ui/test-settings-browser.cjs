// Actual launcher/Settings/Root exit with synthetic LS2; no TV acceptance.
const {chromium}=require('playwright'),assert=require('node:assert/strict');
const base=process.env.PREVIEW_URL||'http://127.0.0.1:8879';
(async()=>{
 const browser=await chromium.launch({headless:true,channel:process.env.BROWSER_CHANNEL||'chrome'});
 try {
  const page=await browser.newPage({locale:'en'}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base+'/root-launcher/index.html');await page.locator('#tiles .add-app').waitFor();
  await page.evaluate(()=>{
   const Original=window.PalmServiceBridge;
   window.settingsBackend={phase:'active',calls:[],pending:[],delay:false,fail:false};
   window.PalmServiceBridge=function(){
    const original=new Original();this.cancel=()=>original.cancel();
    this.call=(uri,raw)=>{
     const b=settingsBackend,method=uri.split('/').pop(),payload=JSON.parse(raw);
     if(!uri.startsWith('luna://com.cleanyourtv.root.preview.service/')||!['status','restore','enable'].includes(method)){
      original.onservicecallback=value=>this.onservicecallback(value);original.call(uri,raw);return;
     }
     if(payload.startup){
      const send=result=>this.onservicecallback(JSON.stringify({returnValue:true,result:{returnValue:true,result}}));
      if(payload.startup==='configure')b.sources=payload.sources;
      send({sources:b.sources||{tv:true,youtube:false,hdmi:false},active:b.phase==='active'});return;
     }
     b.calls.push(method);
     const send=result=>this.onservicecallback(JSON.stringify({returnValue:true,result:{returnValue:true,result}}));
     if(method==='status'){
      const answer=()=>b.fail?this.onservicecallback(JSON.stringify({returnValue:false})):send({intent:{phase:b.phase},effective:{sam_home:'com.webos.app.home',profiles:{defaultApps:{categories:{home:'com.webos.app.home'}},idleApp:{appId:'com.webos.app.home'}}}});
      if(b.delay)b.pending.push(answer);else answer();
     }else if(method==='enable'){b.phase='active';send({});}
     else{b.phase='disabled';send('restored');}
    };
   };
  });
  await page.locator('#btnSettings').click();
  const toggle=page.locator('.root-settings .home-routing-switch').first();
  await page.waitForFunction(()=>document.querySelector('.root-settings [role=switch]').getAttribute('aria-checked')==='true');
  assert.equal(await page.evaluate(()=>document.activeElement.id),'settings-tab-home','status must preserve category navigation focus');
  await page.evaluate(()=>{settingsBackend.fail=true;document.dispatchEvent(new Event('webOSRelaunch'));});
  const retry=page.getByRole('button',{name:'Check status',exact:true});await retry.waitFor();
  await retry.focus();await page.evaluate(()=>settingsBackend.fail=false);await page.keyboard.press('Enter');
  await page.waitForFunction(()=>!document.querySelector('.root-settings [role=switch]').disabled);
  assert.equal(await page.evaluate(()=>document.activeElement.textContent),'Open LG Home','retry keeps usable focus while its button disappears');
  await page.evaluate(()=>{
   settingsBackend.phase='disabled';settingsBackend.delay=true;
   Object.defineProperty(document,'hidden',{configurable:true,value:true});document.dispatchEvent(new Event('visibilitychange'));
   Object.defineProperty(document,'hidden',{configurable:true,value:false});document.dispatchEvent(new Event('visibilitychange'));
   document.dispatchEvent(new Event('webOSRelaunch'));
  });
  assert(await toggle.isDisabled());
  await page.evaluate(()=>document.querySelector('.root-settings [role=switch]').click());
  assert.deepEqual(await page.evaluate(()=>settingsBackend.calls.filter(m=>m!=='status')),[]);
  await page.evaluate(()=>{settingsBackend.pending.pop()();settingsBackend.delay=false;});
  await page.waitForFunction(()=>!document.querySelector('.root-settings [role=switch]').disabled);
  assert.equal(await toggle.getAttribute('aria-checked'),'false');
  const sources=page.locator('.startup-source-actions button');
  assert.equal(await sources.count(),3);assert(await sources.nth(0).isDisabled());
  assert.equal(await sources.nth(0).getAttribute('aria-checked'),'true');
  const sourceLayout=await page.evaluate(()=>({hint:document.querySelector('#rootStartupHint').getBoundingClientRect().bottom,content:document.querySelector('.settings-content').getBoundingClientRect().bottom}));
  assert(sourceLayout.hint<=sourceLayout.content,'all source controls and the Off explanation fit in the TV reading area');
  await toggle.focus();await page.keyboard.press('ArrowDown');assert.equal(await page.evaluate(()=>document.activeElement.textContent),'Open LG Home');
  await toggle.click();await page.waitForFunction(()=>document.querySelector('.root-settings [role=switch]').getAttribute('aria-checked')==='true');
  assert.deepEqual(await page.evaluate(()=>settingsBackend.calls.filter(m=>m!=='status')),['enable']);
  await sources.nth(1).click();await page.waitForFunction(()=>document.querySelectorAll('.startup-source-actions button')[1].getAttribute('aria-checked')==='true');
  assert.deepEqual(await page.evaluate(()=>settingsBackend.sources),{tv:true,youtube:true,hdmi:false});
  await page.waitForFunction(()=>!document.querySelector('.root-settings [role=switch]').disabled);
  await toggle.click();await page.waitForFunction(()=>document.querySelector('.root-settings [role=switch]').getAttribute('aria-checked')==='false');
  assert.deepEqual(await page.evaluate(()=>settingsBackend.calls.filter(m=>m!=='status')),['enable','restore']);
  // A late pre-emergency response cannot repaint the panel.
  await page.evaluate(()=>settingsBackend.pending.shift()());
  assert.equal(await toggle.getAttribute('aria-checked'),'false');
  assert.deepEqual(errors,[]);
  console.log('PASS actual Root launcher/Settings/exit: emergency resume, relaunch, delayed status, explicit enable and Off');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
