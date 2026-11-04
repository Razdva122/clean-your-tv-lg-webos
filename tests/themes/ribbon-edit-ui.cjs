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
  const peek=page.locator('#tiles .item[data-ribbon-slot="8"]');assert(await peek.isVisible(),'next card is visible as the right-edge continuation');
  const peekBox=await peek.boundingBox();assert(peekBox.x<1920&&peekBox.x+peekBox.width>1920,'viewport clips the next real card at the edge');assert.equal(await peek.evaluate(n=>getComputedStyle(n).pointerEvents),'none','clipped continuation cannot steal pointer focus');
  const topMetrics=()=>page.evaluate(()=>{const item=document.querySelector('#tiles .focused'),card=item.querySelector('.card').getBoundingClientRect(),caption=item.querySelector('.name').getBoundingClientRect(),m=getComputedStyle(item).transform.match(/matrix\(([^)]+)\)/),skew=m?Number(m[1].split(',')[2]):0;const label=item.querySelector('.name'),style=getComputedStyle(label);return {expected:card.x+card.width/2-card.height*skew/2,caption:caption.x+caption.width/2,card:{x:card.x,y:card.y,width:card.width,height:card.height},label:{x:caption.x,y:caption.y,width:caption.width,height:caption.height},transform:style.transform,origin:style.transformOrigin,bottom:style.bottom,offsetTop:label.offsetTop,offsetHeight:label.offsetHeight,itemTop:item.offsetTop,itemWidth:item.offsetWidth};});
  let anchorMetrics=await topMetrics();assert(Math.abs(anchorMetrics.expected-anchorMetrics.caption)<1,'caption is centered over the raised top edge: '+JSON.stringify(anchorMetrics));
  const originalTitle=await page.locator('#tiles .focused .name').textContent();await page.locator('#tiles .focused .name').evaluate(n=>n.textContent='A long television application name across several lines');anchorMetrics=await topMetrics();assert(Math.abs(anchorMetrics.expected-anchorMetrics.caption)<1,'multiline caption keeps the same top-edge center');await page.locator('#tiles .focused .name').evaluate((n,title)=>n.textContent=title,originalTitle);
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
  const crossStyle=await page.locator('#hideApp').evaluate(n=>({background:getComputedStyle(n).backgroundColor,radius:getComputedStyle(n).borderRadius}));assert.equal(crossStyle.background,'rgba(0, 0, 0, 0)');assert.equal(crossStyle.radius,'0px','plain cross has no circular container');
  for(const arrow of await page.locator('.ribbon-edit-arrow svg').all()){const b=await arrow.boundingBox();assert(Math.abs(b.y+b.height/2-card.y-16)<2,'chevrons sit just below the raised top corners');}
  assert.equal(await page.locator('.ribbon-edit-arrow svg').count(),2,'aligned vector chevrons replace font-dependent glyphs');
  const crossAnchor=await page.locator('#tiles .moving').evaluate(n=>{const b=n.querySelector('.card').getBoundingClientRect(),m=getComputedStyle(n).transform.match(/matrix\(([^)]+)\)/),c=m?Number(m[1].split(',')[2]):0;return b.x+b.width/2-b.height*c/2;});assert(Math.abs(cross.x+cross.width/2-crossAnchor)<1,'cross uses the same raised top-edge center');
  assert(card.y<still.y,'only selected card is raised');assert(Math.abs(1080-card.y-card.height-32)<1,'editing card detaches from the bottom edge with a visible gap');assert(cross.y+cross.height<=card.y,'cross is above selected card');assert(cross.x>=0&&cross.x+cross.width<=1920&&cross.y>=0);
  await page.screenshot({path:path.resolve('build/ribbon-edit-'+edition+'.png'),animations:'disabled'});
  await page.setViewportSize({width:1280,height:720});
  await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
  const hdCard=await page.locator('#tiles .moving .card').boundingBox(),hdCross=await page.locator('#hideApp').boundingBox();
  assert(hdCross.y+hdCross.height<=hdCard.y&&hdCross.y>=0&&hdCross.x>=0&&hdCross.x+hdCross.width<=1280,'cross remains anchored and onscreen after HD resize');
  await page.keyboard.press('ArrowDown');assert.notEqual(await page.evaluate(()=>document.activeElement.id),'hideApp','Down cannot select the cross above the card');
  await page.keyboard.press('ArrowUp');assert.equal(await page.evaluate(()=>document.activeElement.id),'hideApp');
  await page.keyboard.press('ArrowDown');assert.notEqual(await page.evaluate(()=>document.activeElement.id),'hideApp');
  await page.keyboard.press('ArrowRight');await page.keyboard.press('Escape');assert.deepEqual(await page.locator('#tiles .item').evaluateAll(ns=>ns.map(n=>n.dataset.appId||'add')),order,'Back cancels reordering');assert.equal(await page.locator('.ribbon-edit-arrow').count(),0);
  await page.keyboard.down('Enter');await page.waitForTimeout(700);await page.keyboard.up('Enter');await page.keyboard.press('ArrowUp');await page.keyboard.press('Enter');
  assert.equal(await page.evaluate(()=>HomePresentationController.state().mode),'overlay','hide and undo stay over content');
  assert.equal(await page.locator('#tiles .item').count(),order.length-1,'cross hides app without uninstalling');await page.locator('#appUndo button').click();assert.equal(await page.locator('#tiles .item').count(),order.length,'undo restores app');
  await page.evaluate(()=>ThemeManager.reset());await page.keyboard.down('Enter');await page.waitForTimeout(700);await page.keyboard.up('Enter');
  const footer=await page.locator('#hideApp').boundingBox();assert(footer.x>=0&&footer.x+footer.width<=1280&&footer.y>=0&&footer.y+footer.height<=720,'Classic footer position is restored after Ribbon editing');await page.keyboard.press('Escape');
  assert.deepEqual(errors,[]);await page.close();console.log('PASS Ribbon editing: one lifted card, inline arrows, cross focus, cancel, hide and undo: '+edition);
 }}finally{await browser.close();await new Promise(r=>server.close(r));}
})().catch(e=>{console.error(e);process.exitCode=1;});
