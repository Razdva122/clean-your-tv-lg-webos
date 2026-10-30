'use strict';
const {assert,chromium,fs,path,stage}=require('./themes/browser.cjs');
const http=require('node:http');
(async()=>{
 const site=stage(),server=http.createServer((req,res)=>{const file=path.resolve(site,'.'+new URL(req.url,'http://localhost').pathname);if(!file.startsWith(site+path.sep)||!fs.existsSync(file))return res.writeHead(404).end();res.setHeader('Content-Type',({'.js':'application/javascript','.json':'application/json','.css':'text/css','.png':'image/png','.jpg':'image/jpeg','.ttf':'font/ttf'})[path.extname(file)]||'text/html');res.end(fs.readFileSync(file));});
 await new Promise(r=>server.listen(0,'127.0.0.1',r));const browser=await chromium.launch({headless:true,channel:process.env.BROWSER_CHANNEL||'chrome'});
 let page;try{page=await browser.newPage({viewport:{width:1440,height:1000},locale:'en-US'});await page.route(/^https:/,r=>r.abort());page.setDefaultTimeout(10000);const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto('http://127.0.0.1:'+server.address().port+'/index.html');
  assert.equal(await page.getByRole('link',{name:'Theme showcase',exact:true}).count(),0);assert.equal((await page.request.get('http://127.0.0.1:'+server.address().port+'/themes/index.html')).status(),404,'standalone catalogue is not exported');
  const frame=page.frameLocator('#screen');await page.getByRole('region',{name:'Themes',exact:true}).waitFor();
  await frame.locator('#tiles .focused').waitFor();const order=await frame.locator('#tiles .item[data-app-id]').evaluateAll(items=>items.map(i=>i.dataset.appId));
  for(const edition of ['No-root Edition','Root Edition']){
   await page.getByRole('button',{name:edition,exact:true}).click();await page.waitForFunction(root=>document.getElementById('screen').getAttribute('src')===(root?'root-launcher/index.html':'launcher/index.html'),edition==='Root Edition');await page.locator('#previewThemes[aria-busy="false"]').waitFor();await frame.locator('#tiles .focused').waitFor();
   if(edition==='Root Edition')assert.equal(await frame.locator('body').evaluate(()=>ThemeManager.current().title),'Itachi · Sharingan','selected theme survives edition switch');
   for(const title of ['Channel','Alpine','Classic','Itachi · Sharingan']){
    await page.getByRole('button',{name:title,exact:true}).click();await page.waitForFunction(title=>{const w=document.getElementById('screen').contentWindow;return w.ThemeManager&&w.ThemeManager.current().title===title;},title);
    assert.equal(await page.getByRole('button',{name:title,exact:true}).getAttribute('aria-pressed'),'true');assert.deepEqual(await frame.locator('#tiles .item[data-app-id]').evaluateAll(items=>items.map(i=>i.dataset.appId)),order);
   }
  }
  assert.deepEqual(errors,[]);await browser.close();console.log('PASS inline published Themes in Root/No-root, offline validated packages and original app order');
 }catch(e){console.error(await page.locator('#themeStatus').innerText());throw e;}finally{await browser.close();await new Promise(r=>server.close(r));}
})().catch(e=>{console.error(e);process.exitCode=1;});
