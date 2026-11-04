'use strict';
// Exercise current source CSS without regenerating committed bundled provenance.
const {assert,fs,path,chromium,stage,open}=require('./browser.cjs');
const {compileThemeCss}=require('../../theme-api/compile.cjs');
(async()=>{
 const rules=(await compileThemeCss(fs.readFileSync('themes/ribbon/theme.css','utf8'))).bundle;
 const manifest=JSON.parse(fs.readFileSync('launcher/themes/ribbon/cytv-theme.json'));
 manifest.layout=JSON.parse(fs.readFileSync('themes/ribbon/theme.json')).layout;
 manifest.defaults.wallpaperAssetId=null;delete manifest.wallpaperVideo;manifest.requires.capabilities=manifest.requires.capabilities.filter(c=>c!=="video-wallpaper-v1");
 manifest.assets=JSON.parse(fs.readFileSync("tests/themes/fixtures/valid-manifest.json")).assets;
 const site=stage(),browser=await chromium.launch({headless:true,channel:process.env.BROWSER_CHANNEL||'chrome'});
 try{for(const edition of ['launcher','root-launcher']){
  const {page,errors}=await open(browser,site,edition);
  try{
   await page.evaluate(({manifest,rules})=>ThemeRuntime.apply({manifest,rules,assetHandles:{}}),{manifest,rules});
   const group=await page.locator('#topButtons').evaluate(n=>{const s=getComputedStyle(n),b=n.getBoundingClientRect();return {x:b.x,y:b.y,width:b.width,height:b.height,background:s.backgroundColor,before:getComputedStyle(n,'::before').backgroundColor};});
   assert.deepEqual({x:group.x,y:group.y,width:group.width,height:group.height},{x:80,y:930,width:244,height:132},'shortcuts occupy one bottom-aligned group');
   assert.equal(group.before,'rgb(17, 19, 24)','outlined charcoal block remains distinct from the backdrop');
   const fills=await page.locator('#tiles .item[data-app-id] .card').evaluateAll(ns=>ns.map(n=>({actual:getComputedStyle(n).backgroundColor,native:n.style.background})));
   assert(fills.every(f=>f.actual===f.native),'every app keeps its native solid fill across the card');
   assert(new Set(fills.map(f=>f.actual)).size>3,'native app fills remain distinct');
   await page.locator('#btnSettings').hover();
   const focus=await page.locator('#btnSettings').evaluate(n=>{const s=getComputedStyle(n);return {border:s.borderTopColor,width:s.borderTopWidth,background:s.backgroundColor,icon:getComputedStyle(n.querySelector('svg')).width};});
   assert.equal(focus.border,'rgb(255, 255, 255)');assert.equal(focus.width,'3px');assert.equal(focus.icon,'30px');
   await page.screenshot({path:path.resolve('build/ribbon-reference-'+edition+'.png'),animations:'disabled'});
   const external=structuredClone(manifest);delete external.layout.presentation;external.requires.capabilities=external.requires.capabilities.filter(c=>c!=='overlay-presentation-v1');
   await page.evaluate(manifest=>ThemeRuntime.apply({manifest,rules:{schemaVersion:1,rules:[]},assetHandles:{}}),external);
   assert.equal(await page.locator('#topButtons').evaluate(n=>getComputedStyle(n,'::before').content),'none','external Ribbon themes keep their original shortcut geometry');
   assert.deepEqual(errors,[]);console.log('PASS reference Ribbon black shortcut group and native solid fills: '+edition);
  }finally{await page.close();}
 }}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
