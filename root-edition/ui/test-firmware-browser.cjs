// Run against scripts/preview.py; browser simulation is not TV acceptance.
const {chromium}=require('playwright'),assert=require('node:assert/strict');
const base=process.env.PREVIEW_URL||'http://127.0.0.1:8879';
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'chrome'});
 try{
  for(const locale of ['en','cs','de','es','pt-BR','fr','it','ko','hi','pl','ru','zh-Hans','zh-Hant'])for(const [width,height] of [[1920,1080],[1280,720]]){
   const page=await browser.newPage({viewport:{width,height},locale}),errors=[];
   page.on('pageerror',e=>errors.push(e.message));
   await page.goto(base+'/root-launcher/index.html');await page.locator('#tiles .add-app').waitFor();
   await page.evaluate(()=>document.fonts.ready);
   await page.locator('#btnSettings').click();
   const entry=page.getByRole('button',{name:await page.evaluate(()=>HomeI18n.t('LG firmware updates')),exact:true});
   await entry.click();
   const toggle=page.getByRole('switch',{name:await page.evaluate(()=>HomeI18n.t('Block LG firmware updates')),exact:true});
   await toggle.waitFor();await page.waitForFunction(()=>document.querySelector('.root-firmware [role=switch]').disabled===false);
   assert.equal(await toggle.getAttribute('aria-checked'),'false');
   await toggle.click();await page.waitForFunction(()=>document.querySelector('.root-firmware [role=switch]').getAttribute('aria-checked')==='true');
   await toggle.click();await page.waitForFunction(()=>document.querySelector('.root-firmware [role=switch]').getAttribute('aria-checked')==='false');
   for(let i=0;i<3;i++){
    await page.keyboard.press('ArrowDown');
    assert(await page.evaluate(()=>{const b=document.activeElement,r=b.getBoundingClientRect();return b.tagName==='BUTTON'&&r.top>=0&&r.bottom<=innerHeight&&r.left>=0&&r.right<=innerWidth;}),'remote focus stays visible: '+locale+' '+height);
   }
   if(['en','ru'].includes(locale))await page.screenshot({path:'/tmp/cytv-firmware-'+locale+'-'+height+'.png'});
   await page.keyboard.press('Escape');assert.equal(await entry.evaluate(e=>e===document.activeElement),true);
   await page.keyboard.press('Escape');assert.equal(await page.locator('.root-settings:visible').count(),0);
   assert.deepEqual(errors,[]);await page.close();
  }
  const page=await browser.newPage();await page.goto(base+'/launcher/index.html');await page.locator('#tiles .add-app').waitFor();await page.locator('#btnSettings').click();
  assert.equal(await page.locator('.settings-firmware').count(),0);await page.close();
  console.log('PASS firmware browser: 13 languages at 1080p/720p, on/off, visible remote focus, Back restoration and No-root isolation');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
