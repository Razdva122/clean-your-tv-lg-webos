'use strict';
const {assert,chromium,fs,path,stage}=require('./themes/browser.cjs'),http=require('node:http');
(async()=>{
 const site=stage('card-preview'),server=http.createServer((req,res)=>{
  const file=path.resolve(site,'.'+new URL(req.url,'http://localhost').pathname);
  if(!file.startsWith(site+path.sep)||!fs.existsSync(file))return res.writeHead(404).end();
  res.setHeader('Content-Type',({'.js':'application/javascript','.json':'application/json','.css':'text/css','.png':'image/png','.jpg':'image/jpeg','.ttf':'font/ttf','.mp4':'video/mp4'})[path.extname(file)]||'text/html');res.end(fs.readFileSync(file));
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const browser=await chromium.launch({headless:true,channel:process.env.BROWSER_CHANNEL||'chrome'});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1100},locale:'en-US'}),errors=[];
  page.on('pageerror',error=>errors.push(error.message));await page.route(/^https:/,route=>route.abort());
  await page.goto('http://127.0.0.1:'+server.address().port+'/index.html');
  assert.equal(await page.locator('[data-context]').count(),0,'the preview must not offer an under-application Ribbon mode');
  for(const edition of ['No-root Edition','Root Edition']){
   await page.getByRole('button',{name:edition,exact:true}).click();await page.locator('#previewThemes[aria-busy="false"]').waitFor();
   await page.getByRole('button',{name:'Ribbon',exact:true}).click();await page.locator('#previewThemes[aria-busy="false"]').waitFor();
   const frame=page.frameLocator('#screen');
   const state=await page.evaluate(()=>{const w=document.getElementById('screen').contentWindow;w.previewCloseCalls=0;w.close=()=>w.previewCloseCalls++;return {host:w.CYTV_HOME_HOST,ready:w.RootLauncherRendered,presentation:w.document.documentElement.getAttribute('data-home-presentation'),theme:w.ThemeManager.current().id,underlay:w.document.querySelector('#previewContent')!==null,background:w.getComputedStyle(w.document.getElementById('homeSurface')).backgroundImage};});
   assert.equal(state.host,'card');assert.equal(state.ready,true);assert.equal(state.theme,'builtin:ribbon');
   assert.notEqual(state.presentation,'overlay');assert.equal(state.underlay,false);await page.waitForFunction(()=>{const w=document.getElementById('screen').contentWindow,v=w.document.getElementById('ctvWallpaperVideo');return w.getComputedStyle(w.document.getElementById('homeSurface')).backgroundImage!=='none'||w.HomeWallpaper.state().actualQuality!=='image'&&v&&!v.paused&&v.readyState>=2;});
   assert.equal(await frame.locator('.item.focused .name').isVisible(),true);
   const focus=await frame.locator('.item.focused').boundingBox();assert(focus.x>=0&&focus.y>=0&&focus.x+focus.width<=1440&&focus.y+focus.height<=1100,'focused Ribbon card stays inside the preview');
   await page.getByRole('button',{name:'Home',exact:true}).click();await page.getByRole('button',{name:'Home',exact:true}).click();
   await page.getByRole('button',{name:'Back',exact:true}).click();
   assert.equal(await page.evaluate(()=>document.getElementById('screen').contentWindow.previewCloseCalls),0,'ordinary Home/Back navigation must not close the CARD host');
   await page.getByRole('button',{name:'Classic',exact:true}).click();await page.locator('#previewThemes[aria-busy="false"]').waitFor();
   assert.equal(await page.evaluate(()=>document.getElementById('screen').contentWindow.ThemeManager.current().id),'builtin:classic');
  }
  assert.deepEqual(errors,[]);console.log('PASS single-Home preview: both CARD editions, Ribbon own background, no synthetic underlay, Home/Back navigation and theme reset');
 }finally{await browser.close();await new Promise(resolve=>server.close(resolve));}
})().catch(error=>{console.error(error);process.exitCode=1;});
