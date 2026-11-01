// Real Home geometry and native hit-testing, not a mocked layout implementation.
const {chromium}=require('playwright'),assert=require('node:assert/strict');
const base=process.env.PREVIEW_URL||'http://127.0.0.1:8876';
(async()=>{
 const browser=await chromium.launch({headless:true,channel:process.env.BROWSER_CHANNEL||'chrome'});
 try{
  for(const edition of ['launcher','root-launcher'])for(const [width,height] of [[1280,720],[1920,1080]]){
   const page=await browser.newPage({viewport:{width,height},locale:'en'}),errors=[];page.on('pageerror',e=>errors.push(e.message));
   await page.route('https://**',route=>route.abort());
   await page.goto(base+'/'+edition+'/index.html');await page.locator('#tiles .focused').waitFor();
   await page.addStyleTag({content:'*{transition:none!important;animation:none!important}'});
   const scene=await page.locator('#homeSurface').boundingBox();
   assert(Math.abs(scene.width-width)<1&&Math.abs(scene.height-height)<1,'logical scene must fit '+edition+' '+width+': '+JSON.stringify(scene));
   for(const preset of ['dock-grid','icon-grid','side-grid','channel-list','scenic-grid'])for(let columns=1;columns<=8;columns++){
    await page.evaluate(({preset,columns})=>{HomeLayoutState.setThemeLayout({preset,columns,allowColumnOverride:true,spacingScale:1,textScale:1,focusScale:1.1});HomeLayoutState.setColumns(columns);},{preset,columns});
    await page.waitForTimeout(25);
    await page.locator('#tiles .item').first().dispatchEvent('mouseover');
    // A physical pointer must hit the transformed card, including 720p coordinates.
    const card=page.locator('#tiles .item').first().locator('.card');const box=await card.boundingBox();
    assert(box&&box.x>=-1&&box.y>=-1&&box.x+box.width<=width+1&&box.y+box.height<=height+1,preset+' '+columns+' visible first card '+JSON.stringify(box));
    assert(await card.evaluate(el=>{const r=el.getBoundingClientRect();return el.contains(document.elementFromPoint(r.left+r.width/2,r.top+r.height/2));}),'pointer hit target '+preset+' '+columns);
   }
   await page.evaluate(()=>{HomeLayoutState.setThemeLayout({preset:'dock-grid',columns:5,allowColumnOverride:true,spacingScale:1,textScale:1,focusScale:1.1});HomeLayoutState.setColumns(5);});
   await page.evaluate(()=>HomeLayoutState.setColumns(8));
   const target=page.locator('#tiles .item').nth(2).locator('.card');await target.hover();
   const nearestTo=(el,selector)=>el.evaluate((el,selector)=>{const r=el.getBoundingClientRect(),x=r.left+r.width/2;return Array.from(document.querySelectorAll(selector)).map((b,i)=>{const p=b.getBoundingClientRect();return {id:b.id||String(i),d:Math.abs(p.left+p.width/2-x)};}).sort((a,b)=>a.d-b.d)[0].id;},selector);
   const nearestSource=await nearestTo(target,'.ctv-input-tile');
   const selected=await target.boundingBox(),glass=await page.locator('#glass').boundingBox();
   assert(glass&&Math.abs(selected.x+selected.width/2-glass.x-glass.width/2)<1&&Math.abs(selected.y+selected.height/2-glass.y-glass.height/2)<1,'scaled focus frame follows the selected card');
   // Classic's Inputs shelf sits between the dock and the header shortcuts.
   await page.keyboard.press('ArrowUp');assert.equal(await page.locator('.ctv-input-tile').evaluateAll(tiles=>String(tiles.findIndex(t=>t.classList.contains('is-focused')))),nearestSource,'upward navigation selects the visually nearest input');
   const nearest=await nearestTo(page.locator('.ctv-input-tile.is-focused'),'#topButtons .pill');
   await page.keyboard.press('ArrowUp');assert.equal(await page.locator('#topButtons .focused').getAttribute('id'),nearest,'upward navigation selects the visually nearest shortcut');
   await page.locator('#btnInputs').click();const inputs=await page.locator('#inputsPanel').boundingBox(),button=await page.locator('#btnInputs').boundingBox();
   // Opening Inputs removes the shortcut's focus growth; allow that small visual inset.
   assert(inputs&&inputs.y>=button.y+button.height-1&&Math.abs(inputs.x-button.x)<=button.width*.05,'Inputs position must use logical scene coordinates '+JSON.stringify({inputs,button,scale:await page.evaluate(()=>HomeViewport.update())}));
   assert(inputs.x+inputs.width<=width+1&&inputs.y+inputs.height<=height+1,'Inputs fits viewport');
   await page.keyboard.press('Escape');
   await page.locator('#btnSettings').click();
   const dialog=page.locator(edition==='launcher'?'#renewalPanel':'.root-settings').first(),r=await dialog.boundingBox();
   assert(r&&Math.abs(r.width-width)<1&&Math.abs(r.height-height)<1,'trusted Settings uses physical viewport');
   await page.locator('[data-category=language]').click();await page.locator('[data-language=cs]').focus();
   assert(await page.evaluate(()=>{const r=document.activeElement.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&r.top>=0&&r.bottom<=innerHeight;}),'focused trusted language remains visible');
   assert.deepEqual(errors,[]);await page.close();
   console.log('PASS '+edition+' '+width+'x'+height+' five presets × columns1–8, Inputs, pointer and trusted Settings');
  }
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
