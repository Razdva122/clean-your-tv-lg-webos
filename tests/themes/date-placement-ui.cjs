'use strict';
const {assert,chromium,stage,open}=require('./browser.cjs');
const fixture=require('./fixtures/valid-manifest.json');
(async()=>{
 const site=stage(),browser=await chromium.launch({headless:true});
 try {for(const edition of ['launcher','root-launcher']){
  const {page,errors}=await open(browser,site,edition);
  const baseline=await page.locator('#date').evaluate(e=>getComputedStyle(e).cssText+'|'+getComputedStyle(e).marginTop+'|'+getComputedStyle(e).whiteSpace);
  const manifest={...fixture,layout:{...fixture.layout,datePlacement:'below-clock'},requires:{...fixture.requires,capabilities:['date-placement-v1']}};
  for(const width of [1280,1920]){
   await page.setViewportSize({width,height:width*9/16});
   await page.evaluate(m=>ThemeRuntime.apply({manifest:m,rules:{schemaVersion:1,rules:[]}}),manifest);
   const rect=await page.evaluate(()=>{const c=document.querySelector('#clock').getBoundingClientRect(),d=document.querySelector('#date').getBoundingClientRect();return {clockBottom:c.bottom,dateTop:d.top,dateRight:d.right};});
   assert(rect.dateTop>=rect.clockBottom,'date is below clock');assert(rect.dateRight<=width,'date remains on screen');
   await page.keyboard.press('ArrowRight');assert.equal(await page.locator('#tiles .focused').count(),1);
   await page.evaluate(()=>ThemeRuntime.suspend('test'));assert.equal(await page.locator('#date').evaluate(e=>getComputedStyle(e).cssText+'|'+getComputedStyle(e).marginTop+'|'+getComputedStyle(e).whiteSpace),baseline);
   await page.evaluate(()=>ThemeRuntime.resume('test'));
  }
  await page.evaluate(()=>ThemeRuntime.reset());assert.equal(await page.locator('#date').evaluate(e=>getComputedStyle(e).cssText+'|'+getComputedStyle(e).marginTop+'|'+getComputedStyle(e).whiteSpace),baseline);assert.deepEqual(errors,[]);await page.close();
 }}finally{await browser.close();}
 console.log('PASS Date placement both editions at 720p/1080p, focus and lifecycle');
})().catch(e=>{console.error(e);process.exitCode=1;});
