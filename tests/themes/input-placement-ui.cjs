'use strict';
const {assert,chromium,stage,open}=require('./browser.cjs');
const fixture=require('./fixtures/valid-manifest.json');
const {compileThemeCss}=require('../../theme-api/compile.cjs');
(async()=>{
 const rules=(await compileThemeCss('.ctv-input-tile.is-focused{background-color:#123456}.ctv-input-status{color:#fedcba}.ctv-input-preview{border-color:red}')).bundle;
 const site=stage(),browser=await chromium.launch({headless:true});
 try {for(const edition of ['launcher','root-launcher']){
  const {page,errors}=await open(browser,site,edition);
  await page.evaluate(()=>InputSources.setPreviewEnabled(localStorage,true));
  const apply=async inputs=>page.evaluate(({fixture,inputs,rules})=>{
   const manifest={...fixture,layout:{...fixture.layout,inputs},requires:{...fixture.requires,capabilities:['input-placement-v1']}};
   ThemeRuntime.apply({manifest,rules});
  },{fixture,inputs,rules});
  assert.equal(await page.locator('#inputShelf').isVisible(),false,'default keeps header menu');
  for(const width of [1280,1920]){
   await page.setViewportSize({width,height:width*9/16});
   await apply('shelf');assert.equal(await page.locator('#inputShelf').isVisible(),true);
   assert.equal(await page.locator('#btnInputs').isVisible(),false,'shelf replaces header Inputs');
   await page.keyboard.press('ArrowUp');await page.waitForFunction(()=>document.querySelector('.ctv-input-tile.is-focused'));
   assert.equal(await page.locator('.ctv-input-tile.is-focused').evaluate(e=>getComputedStyle(e).backgroundColor),'rgb(18, 52, 86)');
   await page.waitForFunction(()=>document.querySelector('.ctv-input-preview'));
   await apply('menu');assert.equal(await page.locator('#inputShelf').isVisible(),false);
   assert.equal(await page.locator('.ctv-input-preview').count(),0,'changing theme releases active video');
   await page.keyboard.press('ArrowUp');assert.equal(await page.locator('.ctv-shortcut.is-focused').count(),1);
   await page.locator('#btnInputs').click();assert.equal(await page.locator('#inputsPanel').isVisible(),true);
   await page.keyboard.press('Escape');await page.keyboard.press('ArrowDown');
  }
  await page.evaluate(()=>ThemeRuntime.reset());assert.equal(await page.locator('#inputShelf').isVisible(),false);
  assert.equal(await page.locator('#homeShowInputs').count(),0,'placement has no global settings override');
  assert.deepEqual(errors,[]);await page.close();
 }}finally{await browser.close();}
 console.log('PASS theme input menu/shelf and CSS, active preview cleanup, defaults and reset, both editions at HD/FHD');
})().catch(e=>{console.error(e);process.exitCode=1});
