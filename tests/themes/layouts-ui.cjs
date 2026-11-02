// Real renderer: preset geometry must match remote navigation, bounds and theme reset.
const {assert,chromium,stage,open}=require('./browser.cjs');
(async()=>{
 const site=stage(),browser=await chromium.launch({headless:true,channel:process.env.BROWSER_CHANNEL||'chrome'});
 try {
  for(const edition of ['launcher','root-launcher']) {
   const {page,errors}=await open(browser,site,edition);
   try {
    for(const preset of ['dock-grid','icon-grid','side-grid','channel-list','scenic-grid']) {
     for(const columns of [1,3,6,8]) {
      await page.evaluate(({preset,columns})=>{HomeLayoutState.setColumns(null);HomeLayoutState.setThemeLayout({preset,columns,spacingScale:1,textScale:1,focusScale:1.1});},{preset,columns});
      for(let i=0;i<15;i++)await page.keyboard.press('ArrowUp');
      await page.keyboard.press(preset==='side-grid'?'ArrowRight':'ArrowDown');
      // Classic's Inputs shelf sits between the header and the dock.
      if(preset==='dock-grid')await page.keyboard.press('ArrowDown');
      const check=async()=>{
       await page.waitForFunction(()=>{const r=document.querySelector('#tiles .focused .card').getBoundingClientRect();return r.top>=-1 && r.bottom<=1081;});
       const g=await page.evaluate(()=>{const card=document.querySelector('#tiles .focused .card').getBoundingClientRect(),glass=document.getElementById('glass').getBoundingClientRect();return{card:{x:card.x,y:card.y,w:card.width,h:card.height},glass:{x:glass.x,y:glass.y,w:glass.width,h:glass.height},selected:document.querySelector('#tiles .focused').dataset.appId};});
       if(preset==='scenic-grid') {
        assert(g.card.y>=760 && g.card.y+g.card.h<=1080,'scenic row stays in bottom viewport');
        assert.equal(await page.locator('#clock').evaluate(el=>getComputedStyle(el).fontSize),'176px');
        assert.equal(await page.locator('#hero').evaluate(el=>getComputedStyle(el).display),'block');
        return g;
       }
       assert(g.glass.x>=0&&g.glass.x+g.glass.w<=1920,'frame fits horizontally '+preset+columns);
       if(preset==='channel-list') {
        assert(await page.locator('#tiles .focused .name').evaluate(el=>el.clientWidth>30),'channel label keeps a positive readable area');
        assert.equal(await page.locator('#tiles .focused .card').evaluate(el=>getComputedStyle(el).transform),'none','channel icon does not shift onto its number');
       }
       assert(Math.abs(g.card.x+g.card.w/2-g.glass.x-g.glass.w/2)<1,'card and frame centre x');
       assert(Math.abs(g.card.y+g.card.h/2-g.glass.y-g.glass.h/2)<1,'card and frame centre y');
       if(preset==='side-grid')assert(g.glass.x>=500,'grid remains outside fixed sidebar');
       return g;
      };
      await check();
      for(let i=0;i<4;i++){await page.keyboard.press('ArrowDown');await check();}
      if(preset==='scenic-grid') {
       for(let i=0;i<15;i++)await page.keyboard.press('ArrowUp');
       await page.keyboard.press('ArrowDown');
       for(let i=0;i<20 && await page.locator('#tiles .item').evaluateAll(nodes=>nodes.findIndex(n=>n.classList.contains('focused')))!==0;i++)await page.keyboard.press('ArrowLeft');
       await page.keyboard.down('Enter');await page.waitForTimeout(700);await page.keyboard.up('Enter');
       const box=await page.locator('#tiles .moving .card').boundingBox();
       assert(box.y>=600 && box.y+box.height<=850,'reorder row clears trusted controls');
       await page.keyboard.press('Escape');
      }
      await page.evaluate(()=>HomeLayoutState.setColumns(2));
      assert.equal(await page.evaluate(()=>HomeLayoutState.state().columns),2);
      if(preset==='side-grid') {
       // Select first column then leave it toward the visible vertical menu.
       await page.keyboard.press('ArrowLeft');await page.keyboard.press('ArrowLeft');
       await page.keyboard.press('ArrowDown');
       assert.equal(await page.locator('#topButtons .focused').count(),1);
       await page.keyboard.press('ArrowRight');
       assert.equal(await page.locator('#tiles .focused').count(),1);
      }
     }
    }
    await page.evaluate(()=>{HomeLayoutState.setColumns(null);ThemeRuntime.reset();});
    assert.equal(await page.locator('#homeSurface').getAttribute('data-layout'),'dock-grid');
    assert.equal(await page.evaluate(()=>HomeLayoutState.state().columns),5);
    assert.deepEqual(errors,[]);
    console.log('PASS all layout presets + column override + navigation + reset: '+edition);
   }finally{await page.close();}
  }
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
