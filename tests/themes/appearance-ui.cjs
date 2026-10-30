'use strict';
// Exercise secondary views and clipping, not just the initial theme cards.
const {assert,fs,path,chromium,stage}=require('./browser.cjs'),http=require('http');
const builtinCount=1+JSON.parse(fs.readFileSync(path.resolve('launcher/builtin-themes.json'))).themes.length;
const entry=require('../../scripts/check-theme-submissions.cjs').loadRegistry().find(e=>e.record.title==='Channel'),envelope={schemaVersion:1,descriptor:fs.readFileSync(path.resolve('showcase',entry.base,'cytv-theme.json')).toString('base64'),files:{}};
for(const file of entry.files.filter(f=>f!=='cytv-theme.json'))envelope.files[file]=fs.readFileSync(path.resolve('showcase',entry.base,file)).toString('base64');
(async()=>{
 const site=stage(),server=http.createServer((req,res)=>{const file=path.resolve(site,'.'+new URL(req.url,'http://localhost').pathname);if(!file.startsWith(site+path.sep)||!fs.existsSync(file))return res.writeHead(404).end();res.setHeader('Content-Type',file.endsWith('.js')?'application/javascript':file.endsWith('.css')?'text/css':file.endsWith('.json')?'application/json':file.endsWith('.png')?'image/png':file.endsWith('.jpg')?'image/jpeg':'text/html');res.end(fs.readFileSync(file));});
 await new Promise(r=>server.listen(0,'127.0.0.1',r));const browser=await chromium.launch({headless:true,channel:process.env.BROWSER_CHANNEL||'chrome'});
 try{for(const edition of ['launcher','root-launcher'])for(const language of ['en','ru'])for(const height of [1080,720]){
  const page=await browser.newPage({viewport:{width:height===1080?1920:1280,height},locale:'en-US'}),errors=[];
  page.setDefaultTimeout(10000);page.on('pageerror',e=>errors.push(e.message));await page.route('https://**',r=>r.abort());
  await page.addInitScript(lang=>localStorage.setItem('tvhome.language',lang),language);
  await page.goto('http://127.0.0.1:'+server.address().port+'/'+edition+'/index.html');await page.locator('#tiles .focused').waitFor();await page.evaluate(()=>ThemeManager.start());await page.locator('#btnSettings').click();await page.locator('[data-category=appearance]').click();
  for(const id of ['homeColumns','homeShowAddApp','homeAddApp']){
   assert(await page.locator('#'+id).isVisible(),id+' is available in Appearance');
   assert(await page.locator('#'+id).evaluate(el=>{const r=el.getBoundingClientRect(),pane=document.querySelector('.settings-content').getBoundingClientRect();return r.top>=pane.top&&r.bottom<=pane.bottom;}),id+' is visible without scrolling');
  }
  assert.equal(await page.locator('#homeThemePanel').isVisible(),false,'theme cards are separate from Appearance');await capture('appearance');
  await page.locator('[data-category=themes]').click();await page.locator('#themeAddUrl').waitFor();
  const initialControls=await page.locator('#themeCatalog,#themeReceive,#themeAddUrl').evaluateAll(els=>els.map(el=>{const r=el.getBoundingClientRect(),pane=document.querySelector('.settings-content').getBoundingClientRect();return {id:el.id,visible:r.top>=pane.top&&r.bottom<=pane.bottom};}));
  assert(initialControls.every(el=>el.visible),'all Themes actions are visible before scrolling: '+JSON.stringify(initialControls));
  async function focusAudit(scene){
   const controls=page.locator('#homeThemePanel button:visible:not(:disabled),#homeThemePanel input:visible');
   for(const el of await controls.all()){
    await el.focus();
    const state=await el.evaluate(el=>{const r=el.getBoundingClientRect();let clipped=null;for(let p=el.parentElement;p&&p!==document.body;p=p.parentElement){const s=getComputedStyle(p);if(/auto|scroll|hidden/.test(s.overflowY)){const b=p.getBoundingClientRect(),top=b.top+p.clientTop,bottom=top+p.clientHeight;if(r.top<top-1||r.bottom>bottom+1){clipped=p.className||p.id;break;}}}return {label:el.id||el.textContent,clipped,outside:r.left<0||r.right>innerWidth||r.top<0||r.bottom>innerHeight};});
    assert.equal(state.clipped,null,scene+' clipped focus: '+state.label+' by '+state.clipped);assert.equal(state.outside,false,scene+' outside viewport: '+state.label);
   }
   assert.equal(await page.locator('#homeThemePanel').evaluate(el=>el.scrollWidth<=el.clientWidth+1),true,scene+' horizontal overflow');
  }
  async function capture(scene){if(!process.env.THEME_AUDIT_SCREENSHOTS)return;const out=process.env.THEME_AUDIT_SCREENSHOTS;fs.mkdirSync(out,{recursive:true});await page.screenshot({path:path.join(out,edition+'-'+language+'-'+height+'-'+scene+'.png')});}
  async function back(){await page.keyboard.press('Escape');await page.locator('#themeAddUrl').waitFor();}
  await capture('installed');await focusAudit('installed');
  assert.equal(await page.locator('#themeMore,#themeAdvanced,#themeReset').count(),0,'obsolete advanced controls are removed');
  assert.deepEqual(await page.locator('.theme-picker-actions>button').evaluateAll(els=>els.map(el=>el.id)),['themeCatalog','themeReceive','themeAddUrl']);
  assert.match(await page.locator('#themeAddUrl').innerText(),language==='ru'?/Добавить по ID/:/Add by ID/);
  const entries=await page.locator('.theme-picker-actions>button').evaluateAll(els=>els.map(el=>{const r=el.getBoundingClientRect();return {top:r.top,left:r.left,right:r.right};}));
  assert.equal(entries[2].top,entries[1].top,'ID entry stays beside the computer entry');assert(entries[2].left>=entries[1].right,'ID entry is on the right');
  async function layoutVisible(expected){for(const id of ['homeColumns','homeShowAddApp','homeAddApp'])assert.equal(await page.locator('#'+id).isVisible(),expected,id+' belongs only to the main Appearance view');}
  await layoutVisible(false);
  await page.locator('#themeAddUrl').click();await layoutVisible(false);await page.keyboard.press('Escape');await page.locator('#themeAddUrl').waitFor();await layoutVisible(false);
  await page.locator('#themeAddUrl').click();await page.locator('#themeUrl').fill('https://example.com/not-a-theme');await page.locator('#themeLoad').click();await page.locator('#themeMessage').waitFor();await focusAudit('URL error');await capture('url-error');await back();
  await page.locator('#themeReceive').click();await layoutVisible(false);assert.equal(await page.locator('#themeReceiverRetry').count(),0,'preview must explain the TV requirement');assert.equal(await page.locator('#homeColumns').isVisible(),false,'unrelated Columns do not appear in theme subviews');await focusAudit('browser receiver');await capture('preview-receiver');
  assert.equal(await page.locator('#themeReceiveLegacy').count(),0);assert.equal(await page.locator('#themeComputer').count(),0);await back();
  // Device service failure is tested separately from the browser-only explanation.
  await page.evaluate(()=>{window.CYTV_BROWSER_PREVIEW=false;});await page.locator('#themeReceive').click();await page.locator('#themeReceiverRetry').waitFor();await focusAudit('device receiver error');await capture('device-error');
  assert.equal(await page.locator('#themeReceiveLegacy').count(),0);await back();
  await page.locator('#themeCatalog').click();await page.locator('#themeCatalogRefresh').waitFor();await layoutVisible(false);await focusAudit('showcase');await capture('showcase');await page.locator('.theme-catalog-card').first().click();await page.locator('#themeDownload').waitFor();await focusAudit('theme detail');await capture('detail');
  await page.keyboard.press('Escape');await page.locator('#themeCatalogRefresh').waitFor();await back();
  await page.evaluate(env=>ThemeManager.installEnvelope(env),envelope);await page.locator('[data-category=language]').click();await page.locator('[data-category=themes]').click();const channel=page.locator('.theme-option').filter({hasText:'Channel'});await channel.locator('.theme-choice').click();await page.waitForFunction(()=>ThemeManager.current().title==='Channel');await channel.locator('.theme-remove').click();await page.locator('#themeRemoveCancel').click();assert.equal(await page.evaluate(()=>ThemeManager.current().title),'Channel','cancel keeps the current theme');await channel.locator('.theme-remove').click();await focusAudit('remove active confirmation');await capture('remove-active');await page.locator('#themeRemoveConfirm').click();await page.waitForFunction(count=>ThemeManager.current().id==='builtin:classic'&&document.querySelectorAll('.theme-option').length===count,builtinCount);assert.equal(await page.evaluate(async()=>(await ThemeStore.list()).length),0,'confirmed removal resets Classic and deletes the package');
  await layoutVisible(false);
  await page.locator('.settings-footer button:visible').click();assert.equal(await page.locator('#homeThemePanel').evaluate(el=>el.hidden),true);assert.deepEqual(errors,[]);
  console.log('PASS Appearance secondary views, field values and visible focus: '+edition+' '+language+' '+height);await page.close();
 }}finally{await browser.close();await new Promise(r=>server.close(r));}
})().catch(e=>{console.error(e);process.exitCode=1;});
