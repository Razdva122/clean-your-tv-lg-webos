'use strict';
const {assert,fs,path,chromium,stage}=require('./browser.cjs'),http=require('node:http');
(async()=>{
 const site=stage('ribbon-edit'),server=http.createServer((req,res)=>{
  const file=path.resolve(site,'.'+new URL(req.url,'http://localhost').pathname);
  if(!file.startsWith(site+path.sep)||!fs.existsSync(file))return res.writeHead(404).end();
  res.setHeader('Content-Type',({'.html':'text/html','.js':'application/javascript','.json':'application/json','.css':'text/css','.jpg':'image/jpeg','.png':'image/png','.mp4':'video/mp4'})[path.extname(file)]||'application/octet-stream');res.end(fs.readFileSync(file));
 });
 await new Promise(r=>server.listen(0,'127.0.0.1',r));const browser=await chromium.launch({headless:true,channel:process.env.BROWSER_CHANNEL||'chrome'});
 try{for(const edition of ['launcher','root-launcher']){
  const page=await browser.newPage({viewport:{width:1920,height:1080}}),errors=[];page.on('pageerror',e=>errors.push(e.message));await page.route(/^https:/,r=>r.abort());
  await page.goto('http://127.0.0.1:'+server.address().port+'/'+edition+'/index.html');await page.waitForFunction(()=>window.RootLauncherRendered===true);
  await page.evaluate(async()=>ThemeManager.selectInstalled({id:'builtin:ribbon'}));await page.locator('#tiles .focused').waitFor();
  await page.evaluate(()=>{PREVIEW_HOME_CONTEXT='content';HomePresentationController.show({});});await page.waitForFunction(()=>HomePresentationController.state().mode==='overlay');
  const order=await page.locator('#tiles .item').evaluateAll(ns=>ns.map(n=>n.dataset.appId||'add'));
  const base=await page.locator('#tiles .item:not(.focused) .card').first().boundingBox();
  await page.keyboard.down('Enter');await page.waitForTimeout(700);await page.keyboard.up('Enter');
  assert.equal(await page.locator('#tiles .moving').count(),1);
  await page.waitForTimeout(100);assert.equal(await page.evaluate(()=>HomePresentationController.state().mode),'overlay','editing preserves the underlying app instead of showing Home wallpaper');
  assert.equal(await page.locator('#editHint').isVisible(),false,'editing has no explanation text');
  assert.equal(await page.locator('#tiles .ribbon-edit-arrow').count(),2);
  const still=await page.locator('#tiles .item:not(.moving) .card').first().boundingBox();assert(Math.abs(still.y-base.y)<1,'editing keeps the rest of the ribbon at its baseline');
  assert.equal(await page.locator('#tiles .moving .name').isVisible(),false,'cross cannot overlap the app title');
  const card=await page.locator('#tiles .moving .card').boundingBox(),cross=await page.locator('#hideApp').boundingBox();
  assert(card.y<still.y,'only selected card is raised');assert(cross.y+cross.height<=card.y,'cross is above selected card');assert(cross.x>=0&&cross.x+cross.width<=1920&&cross.y>=0);
  await page.screenshot({path:path.resolve('build/ribbon-edit-'+edition+'.png'),animations:'disabled'});
  await page.keyboard.press('ArrowUp');assert.equal(await page.evaluate(()=>document.activeElement.id),'hideApp');
  await page.keyboard.press('ArrowDown');assert.notEqual(await page.evaluate(()=>document.activeElement.id),'hideApp');
  await page.keyboard.press('ArrowRight');await page.keyboard.press('Escape');assert.deepEqual(await page.locator('#tiles .item').evaluateAll(ns=>ns.map(n=>n.dataset.appId||'add')),order,'Back cancels reordering');assert.equal(await page.locator('.ribbon-edit-arrow').count(),0);
  await page.keyboard.down('Enter');await page.waitForTimeout(700);await page.keyboard.up('Enter');await page.keyboard.press('ArrowUp');await page.keyboard.press('Enter');
  assert.equal(await page.evaluate(()=>HomePresentationController.state().mode),'overlay','hide and undo stay over content');
  assert.equal(await page.locator('#tiles .item').count(),order.length-1,'cross hides app without uninstalling');await page.locator('#appUndo button').click();assert.equal(await page.locator('#tiles .item').count(),order.length,'undo restores app');
  assert.deepEqual(errors,[]);await page.close();console.log('PASS Ribbon editing: one lifted card, inline arrows, cross focus, cancel, hide and undo: '+edition);
 }}finally{await browser.close();await new Promise(r=>server.close(r));}
})().catch(e=>{console.error(e);process.exitCode=1;});
