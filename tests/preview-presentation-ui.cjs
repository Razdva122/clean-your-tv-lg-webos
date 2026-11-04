'use strict';
const {assert,chromium,fs,path,stage}=require('./themes/browser.cjs'),http=require('node:http');
(async()=>{
 const site=stage(),server=http.createServer((req,res)=>{const file=path.resolve(site,'.'+new URL(req.url,'http://localhost').pathname);if(!file.startsWith(site+path.sep)||!fs.existsSync(file))return res.writeHead(404).end();res.setHeader('Content-Type',({'.js':'application/javascript','.json':'application/json','.css':'text/css','.png':'image/png','.jpg':'image/jpeg','.ttf':'font/ttf'})[path.extname(file)]||'text/html');res.end(fs.readFileSync(file));});
 await new Promise(r=>server.listen(0,'127.0.0.1',r));const browser=await chromium.launch({headless:true,channel:process.env.BROWSER_CHANNEL||'chrome'});
 try{const page=await browser.newPage({viewport:{width:1440,height:1100},locale:'en-US'}),errors=[];page.on('pageerror',e=>errors.push(e.message));await page.route(/^https:/,r=>r.abort());
 await page.goto('http://127.0.0.1:'+server.address().port+'/index.html');
 for(const edition of ['No-root Edition','Root Edition']){
  await page.getByRole('button',{name:edition,exact:true}).click();await page.locator('#previewThemes[aria-busy="false"]').waitFor();
  await page.getByRole('button',{name:'Ribbon',exact:true}).click();await page.locator('#previewThemes[aria-busy="false"]').waitFor();
  await page.getByRole('button',{name:'Startup / wallpaper',exact:true}).click();
  const state=()=>page.evaluate(()=>document.getElementById('screen').contentWindow.HomePresentationController.state());
  await page.waitForFunction(()=>document.getElementById('screen').contentWindow.HomePresentationController.state().mode==='full');
  await page.getByRole('button',{name:'Over application',exact:true}).click();
  await page.waitForFunction(()=>document.getElementById('screen').contentWindow.HomePresentationController.state().mode==='overlay');
  const frame=page.frameLocator('#screen');assert.equal(await frame.locator('#previewContent').isVisible(),true);
  const transparency=await frame.locator('body').evaluate(()=>[document.documentElement,document.body,document.getElementById('homeSurface')].map(n=>getComputedStyle(n).backgroundColor));
  assert(transparency.every(color=>color==='rgba(0, 0, 0, 0)'), 'the renderer exposes the iframe content through every fullscreen layer');
  const focus=await frame.locator('.item.focused').boundingBox();assert(focus.x>=0&&focus.y>=0&&focus.x+focus.width<=1440&&focus.y+focus.height<=1100,'focused skew remains inside the preview screen');
  assert.equal(await frame.locator('.item.focused .name').isVisible(),true,'the selected app has a readable label');
  await page.screenshot({path:path.resolve('build/ribbon-demo-'+(edition==='Root Edition'?'root':'no-root')+'.png'),animations:'disabled'});
  const appearance=await frame.locator('.item.focused .card').evaluate(n=>{const c=getComputedStyle(n);return {background:c.backgroundColor,native:n.style.backgroundColor,border:c.borderTopColor,width:c.borderTopWidth};});
  assert.equal(appearance.border,'rgb(255, 255, 255)');assert.equal(appearance.width,'3px');assert.equal(appearance.background,appearance.native,'solid native card fill');
  await page.getByRole('button',{name:'Home',exact:true}).click();await page.waitForFunction(()=>!document.getElementById('screen').contentWindow.HomePresentationController.state().visible);
  await page.getByRole('button',{name:'Home',exact:true}).click();await page.waitForFunction(()=>document.getElementById('screen').contentWindow.HomePresentationController.state().mode==='overlay');
  await page.getByRole('button',{name:'Back',exact:true}).click();await page.waitForFunction(()=>!document.getElementById('screen').contentWindow.HomePresentationController.state().visible);
  await page.getByRole('button',{name:'Startup / wallpaper',exact:true}).click();
  await page.getByRole('button',{name:'Classic',exact:true}).click();await page.locator('#previewThemes[aria-busy="false"]').waitFor();assert.equal((await state()).mode,'full');
 }
 if(process.env.UPDATE_RIBBON_PREVIEWS==='1'){
  for(const edition of ['launcher','root-launcher']){
   const capture=await browser.newPage({viewport:{width:1920,height:1080},locale:'en-US'});await capture.clock.setFixedTime(new Date('2026-11-03T12:00:00Z'));
   await capture.goto('http://127.0.0.1:'+server.address().port+'/'+edition+'/index.html');await capture.waitForFunction(()=>window.RootLauncherRendered===true);
   await capture.evaluate(async()=>{const ribbon=(await ThemeManager.list()).find(t=>t.id==='builtin:ribbon');await ThemeManager.selectInstalled(ribbon);HomePresentationController.show({reason:'startup'});await document.fonts.ready;});
   await capture.locator('.item.focused .name').waitFor();await capture.addStyleTag({content:'*{animation:none!important;transition:none!important}'});
   await capture.screenshot({path:path.resolve('themes/ribbon/previews/'+(edition==='launcher'?'no-root':'root')+'-home.png'),animations:'disabled'});
   await capture.evaluate(()=>{window.PREVIEW_HOME_CONTEXT='content';HomePresentationController.show({});});await capture.waitForFunction(()=>HomePresentationController.state().mode==='overlay');
   await capture.screenshot({path:path.resolve('build/ribbon-overlay-'+edition+'.png'),animations:'disabled'});await capture.close();
  }
 }
 assert.deepEqual(errors,[]);console.log('PASS actual-renderer presentation demo: both editions, full/overlay, native filled cards, Home/Back and theme reset');
 }finally{await browser.close();await new Promise(r=>server.close(r));}
})().catch(e=>{console.error(e);process.exitCode=1;});
