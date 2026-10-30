const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
const base=process.env.PREVIEW_URL||'http://127.0.0.1:8876';
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'chrome'});
 try{
  const samples={en:'Settings',de:'Einstellungen',es:'Ajustes','pt-BR':'Configurações',fr:'Paramètres',it:'Impostazioni',ko:'설정',hi:'सेटिंग्स',pl:'Ustawienia',ru:'Настройки','zh-Hans':'设置','zh-Hant':'設定'};
  for(const edition of ['launcher','root-launcher'])for(const [locale,label] of Object.entries(samples)){
   const context=await browser.newContext({viewport:{width:1920,height:1080},locale});
   const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=400&&r.url().includes('/fonts/'))errors.push('Font resource failed: '+r.url());});
   await page.goto(base+'/'+edition+'/index.html');await page.locator('#tiles .add-app').waitFor();
   await page.evaluate(()=>document.fonts.ready);
   assert.equal(await page.locator('html').getAttribute('lang'),locale);
   assert(await page.locator('#topButtons').evaluate(el=>el.getBoundingClientRect().right<=1809),'localized date must keep shortcuts inside header');
   assert.equal(await page.locator('#btnSettings span').textContent(),label);
   if(locale.indexOf('zh-')===0){
    const client=await context.newCDPSession(page);await client.send('DOM.enable');await client.send('CSS.enable');
    const document=await client.send('DOM.getDocument'),node=await client.send('DOM.querySelector',{nodeId:document.root.nodeId,selector:'#btnSettings span'});
    const {fonts}=await client.send('CSS.getPlatformFontsForNode',{nodeId:node.nodeId});
    assert(fonts.some(font=>font.isCustomFont&&font.familyName==='Noto Sans '+(locale==='zh-Hans'?'SC':'TC')&&font.glyphCount>0),'Chinese settings must render with the packaged script font: '+JSON.stringify(fonts));
    await client.detach();
   }
   assert((await page.locator('#tiles .item .name').allTextContents()).includes('YouTube'),'third-party app names must not be translated');
   if(locale==='en')await page.evaluate(()=>{const Bridge=window.PalmServiceBridge;window.languagePendingStatus=[];window.PalmServiceBridge=function(){const bridge=new Bridge();this.cancel=()=>bridge.cancel();this.call=(uri,payload)=>{bridge.onservicecallback=raw=>{const reply=()=>this.onservicecallback(raw);if(/\/(?:status|homeStatus)$/.test(uri))languagePendingStatus.push(reply);else reply();};bridge.call(uri,payload);};};});
   await page.locator('#btnSettings').click();await page.locator('[data-category=language]').click();
   assert.equal(await page.locator('#settingsLanguageChoices button').count(),13,'languages are directly available in the category');
   assert.equal(await page.locator('#languagePicker').isVisible(),false,'no extra modal is needed');
   assert(await page.locator(edition==='launcher'?'#renewalPanel':'.root-settings').evaluate(el=>getComputedStyle(el).fontFamily.includes('CYTV')),'settings retain packaged language fonts');
   for(const [code,font] of [['zh-Hans','CYTV NotoSansSC'],['zh-Hant','CYTV NotoSansTC']])assert((await page.locator('#settingsLanguageChoices [data-language="'+code+'"]').evaluate(el=>getComputedStyle(el).fontFamily)).includes(font),'Chinese option retains its script font in '+locale);
   await page.keyboard.press('ArrowRight');assert.equal(await page.evaluate(()=>document.activeElement.dataset.language),'auto');
   if(locale==='en'){await page.waitForFunction(()=>languagePendingStatus.length>0);await page.evaluate(()=>languagePendingStatus.splice(0).forEach(reply=>reply()));assert.equal(await page.evaluate(()=>document.activeElement.dataset.language),'auto','late settings status preserves inline language focus');}
   await page.keyboard.press('ArrowDown');assert.equal(await page.evaluate(()=>document.activeElement.dataset.language),'en');
   await page.keyboard.press('ArrowRight');assert.equal(await page.evaluate(()=>document.activeElement.dataset.language),'de');
   await page.keyboard.press('ArrowLeft');assert.equal(await page.evaluate(()=>document.activeElement.dataset.language),'en');
   await page.keyboard.press('Escape');assert.equal(await page.evaluate(()=>document.activeElement.getAttribute('data-category')),'language');
   const target=locale==='ru'?'de':'ru';await page.locator('[data-language="'+target+'"]').click();
   await page.waitForFunction(code=>document.documentElement.lang===code,target);
   await page.locator('#tiles .add-app').waitFor();
   assert.equal(await page.evaluate(()=>localStorage.getItem('tvhome.language')),target);
   await page.reload();await page.locator('#tiles .add-app').waitFor();assert.equal(await page.locator('html').getAttribute('lang'),target);
   await page.locator('#btnSettings').click();await page.locator('[data-category=language]').click();await page.locator('[data-language="auto"]').click();
   await page.waitForFunction(code=>document.documentElement.lang===code,locale);await page.locator('#tiles .add-app').waitFor();
   await page.locator('#btnSettings').click();await page.locator('[data-category=language]').click();await page.locator('#settingsLanguageChoices').waitFor({state:'visible'});
   await page.screenshot({path:'/tmp/cytv-settings-'+edition+'-'+locale+'.png'});
   assert.deepEqual(errors,[],locale+' browser errors');await context.close();
  }
  console.log('PASS twelve UI languages, app name preservation, inline remote navigation, persisted override and automatic reset');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
