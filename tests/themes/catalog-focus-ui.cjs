'use strict';
const {assert,chromium,stage,fs,path}=require('./browser.cjs'),http=require('http');
(async()=>{
 const site=stage(),server=http.createServer((req,res)=>{const file=path.resolve(site,'.'+new URL(req.url,'http://localhost').pathname);if(!file.startsWith(site+path.sep)||!fs.existsSync(file))return res.writeHead(404).end();res.setHeader('Content-Type',file.endsWith('.js')?'application/javascript':file.endsWith('.css')?'text/css':file.endsWith('.json')?'application/json':file.endsWith('.png')?'image/png':file.endsWith('.jpg')?'image/jpeg':'text/html');res.end(fs.readFileSync(file));});await new Promise(r=>server.listen(0,'127.0.0.1',r));const browser=await chromium.launch({headless:true,channel:process.env.BROWSER_CHANNEL||'chrome'});
 try{for(const edition of ['launcher','root-launcher']){
  const page=await browser.newPage({viewport:{width:1920,height:1080},locale:'en-US'}),errors=[];page.setDefaultTimeout(10000);page.on('pageerror',e=>errors.push(e.message));await page.route('https://**',r=>r.abort());await page.goto('http://127.0.0.1:'+server.address().port+'/'+edition+'/index.html');await page.locator('#tiles .focused').waitFor();await page.evaluate(()=>ThemeManager.start());await page.evaluate(()=>document.fonts.ready);
  await page.evaluate(()=>{const original=ThemeManager.catalog;window.__catalogCalls=0;ThemeManager.catalog=function(signal,partial){window.__catalogCalls++;window.__finishCatalog=null;return original(signal,partial).then(entries=>new Promise(resolve=>{window.__finishCatalog=()=>resolve(entries);}));};});
  await page.locator('#btnSettings').click();await page.locator('[data-category=themes]').click();await page.locator('#themeCatalog').waitFor();await page.locator('#themeCatalog').click();await page.locator('#themeCatalogRefresh').waitFor();await page.waitForFunction(()=>typeof window.__finishCatalog==='function');
  const back=page.locator('#homeThemePanel').getByRole('button',{name:'Back',exact:true});await back.focus();
  await page.evaluate(()=>window.__finishCatalog());await page.evaluate(()=>new Promise(requestAnimationFrame));
  assert.equal(await page.evaluate(()=>document.activeElement.textContent),'Back','late catalogue completion must preserve Back focus');
  assert.equal(await back.evaluate(el=>{const r=el.getBoundingClientRect(),p=el.closest('.settings-content'),b=p.getBoundingClientRect();return r.top>=b.top-1&&r.bottom<=b.top+p.clientHeight+1;}),true,'focused Back stays inside scroll viewport');
  await page.locator('#themeCatalogRefresh').click();await page.waitForFunction(()=>window.__catalogCalls===2&&typeof window.__finishCatalog==='function');
  const footer=page.locator('.settings-footer button:visible');await footer.focus();await page.evaluate(()=>window.__finishCatalog());await page.evaluate(()=>new Promise(requestAnimationFrame));
  assert.equal(await footer.evaluate(el=>document.activeElement===el),true,'late catalogue completion must not steal Settings footer focus');assert.deepEqual(errors,[]);
  console.log('PASS deferred catalogue keeps Back visible and preserves Settings footer: '+edition);await page.close();
 }}finally{await browser.close();await new Promise(r=>server.close(r));}
})().catch(e=>{console.error(e);process.exitCode=1;});
