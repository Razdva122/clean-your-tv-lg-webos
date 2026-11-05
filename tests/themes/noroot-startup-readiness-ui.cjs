// Real producer TTL + launcher bootstrap; slow optional video must not gate Home.
'use strict';
const {assert, chromium, fs, path, stage} = require('./browser.cjs');
const http = require('node:http');
const producer = require('../../native/app/presentation-context.js');

(async () => {
  const site = stage('noroot-startup-readiness');
  const server = http.createServer((req, res) => {
    const file = path.resolve(site, '.' + new URL(req.url, 'http://localhost').pathname);
    if (!file.startsWith(site + path.sep) || !fs.existsSync(file)) return res.writeHead(404).end();
    res.setHeader('Content-Type', ({'.js':'application/javascript', '.json':'application/json', '.html':'text/html', '.css':'text/css', '.jpg':'image/jpeg', '.mp4':'video/mp4'})[path.extname(file)] || 'application/octet-stream');
    res.end(fs.readFileSync(file));
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const browser = await chromium.launch({headless:true, channel:process.env.BROWSER_CHANNEL || 'chrome'});
  async function check(savedBuiltin) {
  const page = await browser.newPage({viewport:{width:1920,height:1080}}), errors = [];
  const context = producer({seed:7, content:() => true});
  let queries = 0, mediaRequests = 0, releaseMedia;
  const mediaGate = new Promise(resolve => { releaseMedia = resolve; });
  page.on('pageerror', error => errors.push(error.message));
  await page.exposeFunction('producerContext', () => { queries++; return context.context(); });
  await page.addInitScript(savedBuiltin => {
    localStorage.setItem('tvhome.theme.choice.v1', JSON.stringify({id:'builtin:ribbon',title:'Ribbon'}));
    window.PalmSystem = {launchParams:{cytvHome:{reason:'home',generation:8}},activate(){}};
    window.seedWallpaper=savedBuiltin?new Promise((resolve,reject)=>{
      const request=indexedDB.open('ctv-personal-wallpaper-v1',1);
      request.onupgradeneeded=()=>request.result.createObjectStore('wallpaper');
      request.onerror=reject;request.onsuccess=()=>{const db=request.result,tx=db.transaction('wallpaper','readwrite');tx.objectStore('wallpaper').put({envelope:null,source:'builtin:black-hole'},'slot');tx.oncomplete=()=>{db.close();resolve();};tx.onerror=reject;};
    }):Promise.resolve();
  }, savedBuiltin);
  await page.route('**/personal-wallpaper.js', route => route.fulfill({body:
    fs.readFileSync(path.join(site, 'launcher/personal-wallpaper.js'), 'utf8') + `
      const restoreWallpaper=PersonalWallpaper.start;
      PersonalWallpaper.start=function(){return seedWallpaper.then(()=>restoreWallpaper());};` }));
  await page.route(/^https:/, route => route.abort());
  await page.route('**/theme-data.js', route => route.fulfill({body:
    fs.readFileSync(path.join(site, 'launcher/theme-data.js'), 'utf8') + `
      const prepareAppearance=ThemeData.prepare;
      ThemeData.prepare=function(){return prepareAppearance.apply(this,arguments).then(input=>{window.preparedAppearance=input;return input;});};` }));
  await page.route('**/preview/bridge.js', route => route.fulfill({body:
    fs.readFileSync(path.join(site, 'preview/bridge.js'), 'utf8') + `
      window.CYTV_BROWSER_PREVIEW=false;
      const original=window.PalmServiceBridge.prototype.call;
      window.PalmServiceBridge.prototype.call=function(uri,raw){
        if(uri==='luna://com.gathin.tvhome.renewal/presentationContext'){
          window.producerContext().then(reply=>this.onservicecallback(JSON.stringify(reply)));return;
        }
        original.call(this,uri,raw);
      };` }));
  await page.route('**/themes/ribbon/videos/**', async route => {
    mediaRequests++;
    await mediaGate;
    await route.continue();
  });
  try {
    const generation = context.begin('home');
    context.observe(generation, 'content.test');
    assert.equal(generation,8);
    await page.goto('http://127.0.0.1:' + server.address().port + '/launcher/index.html');
    // Hold optional media beyond the actual production producer's 2000 ms TTL.
    await page.waitForTimeout(2300);
    const before = await page.evaluate(() => ({ready:window.RootLauncherRendered === true, theme:ThemeManager.current().id, presentation:HomePresentationController.state()}));
    console.log(JSON.stringify({savedBuiltin,before,queries,mediaRequests,producer:context.context()}));
    assert.equal(before.ready,true,'verified poster/layout must become ready without optional video bytes');
    assert.equal(before.theme,'builtin:ribbon');
    if(savedBuiltin)assert.equal(await page.evaluate(()=>PersonalWallpaper.state().builtinId),'builtin:black-hole');
    assert.equal(before.presentation.mode,'overlay','real producer fact must reach launcher while fresh');
    assert.equal(before.presentation.content,true);
    assert.equal(mediaRequests,0,'content overlay must not fetch wallpaper video');
    // Exercise slow verified media preparation independently of the decoder guard:
    // no video element is created and the synthetic lease uses browser blob URLs.
    await page.evaluate(() => {
      window.WallpaperMediaCache=null;
      window.lazyMediaSettled=false;
      window.lazyMedia=preparedAppearance.videoLease.acquire().then(handles=>{window.lazyMediaSettled=true;return handles;});
    });
    await page.waitForFunction(() => !!window.lazyMedia);
    await page.waitForTimeout(2300);
    assert.equal(await page.evaluate(() => lazyMediaSettled),false,'media preparation remains pending beyond the producer TTL');
    const beforeMediaQueries=queries;
    releaseMedia();
    await page.evaluate(() => lazyMedia);
    assert.equal(queries,beforeMediaQueries,'media completion never reapplies presentation');
    assert.equal(await page.evaluate(() => HomePresentationController.state().mode),'overlay','late media work must not reapply the theme and erase fresh activation');
    assert.equal(await page.locator('video').count(),0,'lease preparation does not instantiate a decoder');
    assert.deepEqual(errors,[]);
    console.log('PASS No-root '+(savedBuiltin?'saved builtin wallpaper':'saved theme')+' poster-first readiness before media and production TTL expiry');
  } finally {
    releaseMedia();
    await page.close();
  }
  }
  try {
    for(const savedBuiltin of [false,true])await check(savedBuiltin);
  } finally {
    await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
})().catch(error => {console.error(error);process.exitCode=1;});
