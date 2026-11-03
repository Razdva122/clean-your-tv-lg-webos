// Uses both real edition bootstraps and a prepared built-in wallpaper, including settings suspension.
const {chromium,stage,fs,path}=require('./themes/browser.cjs');
const assert=require('node:assert/strict');
(async()=>{
 const site=stage(),server=require('node:http').createServer((req,res)=>{const file=path.resolve(site,'.'+new URL(req.url,'http://localhost').pathname);if(!file.startsWith(site+path.sep)||!fs.existsSync(file))return res.writeHead(404).end();res.setHeader('Content-Type',({'.js':'application/javascript','.json':'application/json','.css':'text/css','.png':'image/png','.jpg':'image/jpeg','.html':'text/html'})[path.extname(file)]||'application/octet-stream');res.end(fs.readFileSync(file));});
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const browser=await chromium.launch({headless:true,channel:process.env.BROWSER_CHANNEL||'chrome'});
 try {
  for(const edition of ['launcher','root-launcher']){
   const page=await browser.newPage({viewport:{width:1280,height:720},locale:'en-US'}),errors=[];page.on('pageerror',e=>errors.push(e.message));await page.route(/^https:/,route=>route.abort());
   await page.goto('http://127.0.0.1:'+server.address().port+'/'+edition+'/index.html');await page.locator('#tiles .focused').waitFor();
   await page.evaluate(async()=>{const item=(await ThemeManager.list()).find(i=>i.id==='builtin:alpine');await ThemeManager.selectInstalled(item);});
   const poster=await page.evaluate(()=>HomeWallpaper.state().posterURL);assert(poster,'real theme has wallpaper');
   await page.locator('#btnSettings').click();await page.locator('[data-category=wallpapers]').click();
   assert.equal(await page.locator('#wallpaperPreview').getAttribute('src'),poster,'suspension retains actual borrowed wallpaper');
   assert(await page.locator('#wallpaperPreview').evaluate(img=>img.complete&&img.naturalWidth>0),'borrowed preview decodes');
   assert(await page.locator('[data-wallpaper-quality="4k"]').isDisabled(),'image-only theme disables video');
   await page.keyboard.press('ArrowRight');assert.equal(await page.evaluate(()=>document.activeElement.getAttribute('data-wallpaper-quality')),'auto');
   await page.keyboard.press('ArrowRight');assert.equal(await page.evaluate(()=>document.activeElement.getAttribute('data-wallpaper-quality')),'image');
   await page.keyboard.press('Enter');assert.equal(await page.evaluate(()=>HomeWallpaper.state().preferenceQuality),'image');
   await page.locator('#wallpaperDimPlus').click();
   assert.equal(await page.evaluate(()=>document.activeElement.id),'wallpaperDimPlus');
   await page.locator('#wallpaperReset').click();assert.equal(await page.evaluate(()=>HomeWallpaper.state().preferenceQuality),'auto');
   await page.screenshot({path:'build/tests/wallpapers-active-'+edition+'.png'});
   await page.keyboard.press('Escape');assert.equal(await page.evaluate(()=>document.activeElement.getAttribute('data-category')),'wallpapers');
   await page.keyboard.press('Escape');assert(!(await page.locator('#homeWallpaperPanel').isVisible()),'Back closes settings');
   await page.evaluate(()=>ThemeManager.reset());
   await page.locator('#btnSettings').click();await page.locator('[data-category=wallpapers]').click();
   assert(await page.locator('#wallpaperPreview').isHidden(),'Classic empty state');
   await page.screenshot({path:'build/tests/wallpapers-'+edition+'.png'});
   assert.deepEqual(errors,[],edition+' browser errors');await page.close();
  }
  console.log('PASS both editions wallpaper preview during suspension, controls, remote navigation, reset and Classic');
 } finally {await browser.close();await new Promise(resolve=>server.close(resolve));}
})().catch(error=>{console.error(error);process.exit(1);});
