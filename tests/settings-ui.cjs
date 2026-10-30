// Catches hidden-category focus, broken column navigation and lost subdialog return.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:process.env.BROWSER_CHANNEL||'chrome'});
 try {
  for(const edition of ['launcher','root-launcher']){
   const page=await browser.newPage({viewport:{width:1920,height:1080}}),errors=[];
   page.on('pageerror',error=>errors.push(error.message));
   await page.route('https://**',route=>route.abort());
   await page.goto((process.env.PREVIEW_URL||'http://127.0.0.1:8876')+'/'+edition+'/index.html');
   await page.locator('#tiles .item').first().waitFor();await page.locator('#btnSettings').click();
   const nav=page.locator('.settings-categories');
   assert.equal(await nav.count(),1,'settings must expose category navigation');
   await nav.locator('button').first().focus();
   await page.keyboard.press('ArrowDown');
   assert.equal(await nav.locator('[aria-selected=true]').getAttribute('data-category'),'appearance');
   assert.equal(await page.locator('#homeThemePanel').isVisible(),false,'Appearance only shows layout and app controls');
   assert(!(await page.locator('.home-routing-switch').first().isVisible()));
   await page.keyboard.press('ArrowRight');
   assert.equal(await page.evaluate(()=>document.activeElement.id),'homeColumns','category enters the primary layout controls');
   await page.keyboard.press('ArrowLeft');assert.equal(await page.evaluate(()=>document.activeElement.getAttribute('data-category')),'appearance');
   await nav.locator('[data-category=themes]').click();await page.locator('.theme-option').first().waitFor();
   await page.locator('#themeCatalog').click();await page.locator('.theme-catalog-card').first().waitFor();await page.keyboard.press('Escape');await page.locator('.theme-option').first().waitFor();assert.equal(await page.locator('#homeThemePanel').getAttribute('aria-modal'),null,'ordinary theme views are inline regions');
   await page.locator('#themeReceive').click();assert.equal(await page.locator('#themeReceiveLegacy').count(),0);await page.keyboard.press('Escape');await page.locator('.theme-option').first().waitFor();
   await page.locator('#themeAddUrl').click();await page.locator('#themeUrl').fill('https://github.com/example/themes');for(const keyCode of [37,13])assert.equal(await page.locator('#themeUrl').evaluate((el,keyCode)=>el.dispatchEvent(new KeyboardEvent('keydown',{keyCode,bubbles:true,cancelable:true})),keyCode),true,'URL entry preserves native IME keys');await page.keyboard.press('Escape');await page.locator('.theme-option').first().waitFor();
   await page.evaluate(()=>HomeLayoutState.setThemeLayout({preset:'scenic-grid',columns:8,allowColumnOverride:false,spacingScale:1,textScale:1,focusScale:1.1}));
   await nav.locator('[data-category=appearance]').click();assert(!(await page.locator('#homeColumns').isVisible()),'fixed themes hide Columns');
   await page.evaluate(()=>ThemeRuntime.reset());
   await nav.locator('[data-category=updates]').click();
   await page.locator('.settings-pane:not([hidden]) button').first().click();
   await page.locator('#systemUpdates').waitFor({state:'visible'});
   await page.keyboard.press('Escape');
   assert.equal(await nav.locator('[aria-selected=true]').getAttribute('data-category'),'updates');
   assert(await page.evaluate(()=>document.activeElement.offsetHeight>0),'update return restores visible focus');
   if(edition==='launcher'){
    await nav.locator('[data-category=developer]').click();
    await page.locator('#developerOpen').click();
    await page.locator('#renewalDiagnostics').click();
    assert.equal(await page.evaluate(()=>document.activeElement.id),'renewalDetails');
    await page.keyboard.press('Escape');
    assert.equal(await page.evaluate(()=>document.activeElement.id),'developerOpen');
    assert.equal(await nav.locator('[aria-selected=true]').getAttribute('data-category'),'developer');
   }
   for(const locale of ['en','de','es','pt-BR','fr','it','ko','hi','pl','ru','zh-Hans','zh-Hant']){
    await page.evaluate(code=>localStorage.setItem('tvhome.language',code),locale);
    await page.reload();await page.locator('#tiles .item').first().waitFor();await page.locator('#btnSettings').click();
    for(const size of [{width:1920,height:1080},{width:1280,height:720}]){
     await page.setViewportSize(size);
     for(const tab of await page.locator('.settings-categories [role=tab]').all()){
      await tab.click();
      assert(await page.locator('.settings-workspace').evaluate(el=>el.scrollWidth<=el.clientWidth+1),'workspace fits horizontally');
      const pane=page.locator('.settings-pane:not([hidden])');
      assert.equal(await pane.count(),1);
      await page.keyboard.press('ArrowRight');
      assert(await page.evaluate(()=>{const el=document.activeElement,r=el.getBoundingClientRect();return el.offsetHeight>0&&r.top>=0&&r.bottom<=innerHeight;}),'focus stays visible');
      if(await tab.getAttribute('data-category')==='appearance'){
       await page.locator('#homeShowAddApp').focus();

       const geometry=await page.locator('#homeShowAddApp').evaluate(el=>{const r=el.getBoundingClientRect();return {top:r.top,bottom:r.bottom,left:r.left,right:r.right,scrollWidth:el.scrollWidth,clientWidth:el.clientWidth,viewportWidth:innerWidth,viewportHeight:innerHeight};});
       assert(geometry.top>=0&&geometry.bottom<=geometry.viewportHeight&&geometry.left>=0&&geometry.right<=geometry.viewportWidth&&geometry.scrollWidth<=geometry.clientWidth+1,'localized visibility switch stays visible: '+JSON.stringify({edition,locale,size,geometry}));
      }
     }
    }
   }
   await page.evaluate(()=>localStorage.setItem('tvhome.language','ru'));
   await page.reload();await page.locator('#tiles .item').first().waitFor();await page.locator('#btnSettings').click();
   await page.setViewportSize({width:1920,height:1080});
   await page.screenshot({path:'build/tests/categories-'+edition+'.png'});
   assert.deepEqual(errors,[],edition+' browser errors');
   await page.close();
  }
  console.log('PASS category switching, remote column navigation, theme return and 48 localized layouts');
 } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exit(1);});
