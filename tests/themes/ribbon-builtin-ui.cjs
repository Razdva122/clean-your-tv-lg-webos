'use strict';
// Packaged themes are available and persistent with every remote request blocked.
const {assert,fs,path,chromium,stage,open}=require('./browser.cjs');
(async()=>{const site=stage(),browser=await chromium.launch({headless:true,channel:process.env.BROWSER_CHANNEL||'chrome'});try{for(const edition of ['launcher','root-launcher']){
 const {page,errors}=await open(browser,site,edition);page.setDefaultTimeout(10000);let remote=0;await page.route(/^https?:/,route=>{remote++;return route.abort();});
 try{
  const settings=async()=>{await page.locator('#btnSettings').click();await page.locator('[data-category=appearance]').click();await page.locator('[data-theme-id="builtin:ribbon"]').waitFor();};
  await page.evaluate(()=>HomeLayoutState.setColumns(4));await settings();
  const ribbon=page.locator('.theme-option').filter({has:page.locator('[data-theme-id="builtin:ribbon"]')});
  assert.equal(await ribbon.locator('.theme-remove').count(),0,'packaged Ribbon has no remove action');
  assert.equal(await ribbon.locator('small').first().textContent(),'Built-in');
  await ribbon.locator('.theme-choice').focus();const choice=await ribbon.locator('.theme-choice').boundingBox();assert(choice.x>=0&&choice.x+choice.width<=1920,'remote focus reveals the packaged Ribbon choice in the installed lane');
  await ribbon.locator('img').waitFor();await ribbon.locator('img').evaluate(img=>img.complete?Promise.resolve():new Promise(resolve=>{img.onload=resolve;img.onerror=resolve;}));assert(await ribbon.locator('img').evaluate(img=>img.naturalWidth>0),'built-in preview loads from packaged registry catalog path');
  await ribbon.locator('.theme-choice').click();await page.waitForFunction(()=>ThemeManager.current().id==='builtin:ribbon'&&!ThemeManager.current().trial);
  assert.equal(await page.locator('#themeKeep').count(),0,'installed built-in applies immediately without a trial');
  await page.keyboard.press('Escape');await page.locator('#homeThemePanel').waitFor({state:'hidden'});
  assert.equal(await page.locator('#timeRow').isVisible(),false);assert.equal(await page.locator('#hero').isVisible(),false);assert.equal(await page.evaluate(()=>HomeLayoutState.state().columns),8);
  const controls=await page.locator('#topButtons .pill').evaluateAll(ns=>ns.map(n=>n.getBoundingClientRect().toJSON()));assert(controls.every(b=>b.left>=0&&b.top>=0&&b.right<=1920&&b.bottom<=1080),'compact controls stay onscreen');
  await page.locator('#btnInputs').click();const input=await page.locator('#inputsPanel').boundingBox();assert(input.y>=0&&input.y+input.height<=1080,'packaged Ribbon inputs remain accessible');await page.keyboard.press('Escape');
  await page.reload();await page.locator('#tiles .focused').waitFor();await page.evaluate(()=>ThemeManager.start());assert.equal(await page.evaluate(()=>ThemeManager.current().id),'builtin:ribbon','Ribbon survives an offline reload');assert.equal(remote,0,'packaged application and reload require no internet');
  await page.screenshot({path:path.resolve('build/ribbon-builtin-'+edition+'.png'),animations:'disabled'});
  await settings();assert.equal(await page.locator('#ctv-theme-style').evaluate(n=>n.disabled),true,'trusted settings suspend packaged appearance');
  await page.setViewportSize({width:1280,height:720});
  for(const control of await page.locator('#homeThemePanel button:visible:not(:disabled)').all()){await control.focus();const box=await control.boundingBox();assert(box.x>=0&&box.y>=0&&box.x+box.width<=1280.1&&box.y+box.height<=720.1,'settings controls remain reachable with three installed themes at 720p');}
  await page.setViewportSize({width:1920,height:1080});await page.locator('#themeCatalog').click();await page.locator('#themeCatalogRefresh').waitFor();assert.equal(await page.locator('.theme-catalog-card[data-theme-id^="builtin:"]').count(),0,'installed built-ins do not leak into Showcase');await page.keyboard.press('Escape');await page.locator('[data-theme-id="builtin:classic"]').click();await page.waitForFunction(()=>ThemeManager.current().id==='builtin:classic');await page.keyboard.press('Escape');await page.locator('#homeThemePanel').waitFor({state:'hidden'});
  assert.equal(await page.evaluate(()=>HomeLayoutState.state().columns),4,'Classic restores the saved column preference');assert.equal(await page.evaluate(()=>HomeLayoutState.state().override),4);assert.equal(await page.locator('#homeSurface').getAttribute('data-ribbon'),null);assert.equal(await page.locator('#timeRow').isVisible(),true);
  assert.deepEqual(errors,[]);console.log('PASS packaged Ribbon offline picker, persistence, controls, reset: '+edition);
 }finally{await page.close();}
}}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
