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
  await page.goto('http://127.0.0.1:'+server.address().port+'/'+edition+'/index.html');await page.locator('#tiles .focused').waitFor();await page.evaluate(()=>ThemeManager.start());await page.locator('#btnSettings').click();await page.locator('[data-category=appearance]').click();await page.locator('#themeMore').waitFor();
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
  async function back(){await page.keyboard.press('Escape');await page.locator('#themeMore').waitFor();}
  await focusAudit('installed');await capture('installed');
  await page.locator('#themeMore').click();await focusAudit('more');await capture('more');
  await page.locator('#themeAddUrl').click();await page.locator('#themeUrl').fill('https://example.com/not-a-theme');await page.locator('#themeLoad').click();await page.locator('#themeMessage').waitFor();await focusAudit('URL error');await capture('url-error');await back();
  await page.locator('#themeReceive').click();assert.equal(await page.locator('#themeReceiverRetry').count(),0,'preview must explain the TV requirement');assert.equal(await page.locator('#homeColumns').isVisible(),false,'unrelated Columns do not appear in theme subviews');await focusAudit('browser receiver');await capture('preview-receiver');
  assert.equal(await page.locator('#themeReceiveLegacy').count(),0);assert.equal(await page.locator('#themeComputer').count(),0);await back();
  // Device service failure is tested separately from the browser-only explanation.
  await page.evaluate(()=>{window.CYTV_BROWSER_PREVIEW=false;});await page.locator('#themeReceive').click();await page.locator('#themeReceiverRetry').waitFor();await focusAudit('device receiver error');await capture('device-error');
  assert.equal(await page.locator('#themeReceiveLegacy').count(),0);await back();
  await page.locator('#themeCatalog').click();await page.locator('#themeCatalogRefresh').waitFor();await focusAudit('showcase');await capture('showcase');await page.locator('.theme-catalog-card').first().click();await page.locator('#themeDownload').waitFor();await focusAudit('theme detail');await capture('detail');
  await page.keyboard.press('Escape');await page.locator('#themeCatalogRefresh').waitFor();await back();
  await page.evaluate(env=>ThemeManager.installEnvelope(env),envelope);await page.locator('[data-category=language]').click();await page.locator('[data-category=appearance]').click();const channel=page.locator('.theme-option').filter({hasText:'Channel'});await channel.locator('.theme-choice').click();await page.waitForFunction(()=>ThemeManager.current().title==='Channel');await channel.locator('.theme-remove').click();await page.locator('#themeRemoveCancel').click();assert.equal(await page.evaluate(()=>ThemeManager.current().title),'Channel','cancel keeps the current theme');await channel.locator('.theme-remove').click();await focusAudit('remove active confirmation');await capture('remove-active');await page.locator('#themeRemoveConfirm').click();await page.waitForFunction(count=>ThemeManager.current().id==='builtin:classic'&&document.querySelectorAll('.theme-option').length===count,builtinCount);assert.equal(await page.evaluate(async()=>(await ThemeStore.list()).length),0,'confirmed removal resets Classic and deletes the package');
  await page.locator('#themeMore').click();await page.locator('#homeThemePanel').getByRole('button',{name:language==='en'?'Clear downloaded themes':'Очистить загруженные темы',exact:true}).click();await focusAudit('clear confirmation');await capture('clear');await back();
  await page.locator('.settings-footer button:visible').click();assert.equal(await page.locator('#homeThemePanel').evaluate(el=>el.hidden),true);assert.deepEqual(errors,[]);
  console.log('PASS Appearance secondary views, field values and visible focus: '+edition+' '+language+' '+height);await page.close();
 }}finally{await browser.close();await new Promise(r=>server.close(r));}
})().catch(e=>{console.error(e);process.exitCode=1;});
