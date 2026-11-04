'use strict';
const {assert,chromium,stage,open}=require('./browser.cjs');
(async()=>{
 const site=stage(),browser=await chromium.launch({headless:true});
 try {
  const context=await browser.newContext();
  await context.addInitScript(()=>{
   window.PREVIEW_INPUT_STATUS=[
    {id:'HDMI_2',appId:'preview.hdmi2',label:'HDMI 2',connected:true,deviceName:'PlayStation 5'},
    {id:'HDMI_3',appId:'preview.hdmi3',label:'HDMI 3',connected:true},
    {id:'HDMI_4',appId:'preview.hdmi4',label:'HDMI 4',connected:false}
   ];
  });
  for(const edition of ['launcher','root-launcher']) {
   const {page,errors}=await open(context,site,edition);
   const layout={preset:'dock-grid',columns:5,spacingScale:1,textScale:1,focusScale:1.1};
   await page.evaluate(layout=>HomeLayoutState.setThemeLayout({...layout,inputs:'shelf'}),layout);
   const tile=name=>page.locator('.ctv-input-tile').filter({has:page.locator('.input-name',{hasText:name})});
   assert.equal(await tile('HDMI 3').locator('.input-detail').textContent(),'Connected','unnamed connected source has an honest fallback');
   assert.equal(await tile('HDMI 2').locator('.input-detail').textContent(),'PlayStation 5','reported name is rendered');
   assert.equal(await tile('HDMI 4').locator('.input-detail').textContent(),'Not connected');
   assert.equal(await page.evaluate(()=>localStorage.getItem(InputSources.previewKey)),null,'fresh profile has no saved preview choice');
   await tile('HDMI 2').hover();
   await page.waitForFunction(()=>document.querySelector('.ctv-input-tile.is-previewing .ctv-input-preview'));
   assert.equal(await page.locator('.ctv-input-tile.is-previewing .input-name').textContent(),'HDMI 2','connected source previews by default');
   await page.locator('#btnSettings').click();await page.locator('[data-category=appearance]').click();
   assert.equal(await page.locator('#homePreviewInputs').isVisible(),true);
   assert.equal(await page.locator('#homePreviewInputs').getAttribute('aria-checked'),'true');
   assert.equal(await page.locator('#homeInputPreviewHint').count(),0,'one switch without extra explanation');
   await page.evaluate(layout=>HomeLayoutState.setThemeLayout({...layout,inputs:'menu'}),layout);
   assert.equal(await page.locator('#homePreviewInputs').isVisible(),false,'menu themes hide preview switch');
   assert.deepEqual(errors,[]);await page.close();
  }
  await context.close();
 }finally{await browser.close();}
 console.log('PASS reported device names, Connected fallback and shelf-only preview switch default on in both editions');
})().catch(e=>{console.error(e);process.exitCode=1});
