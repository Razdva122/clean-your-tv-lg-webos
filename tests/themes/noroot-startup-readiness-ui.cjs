// Real producer TTL + launcher bootstrap; slow optional video must not gate Home.
'use strict';
const {assert, chromium, fs, path, stage} = require('./browser.cjs');
const http = require('node:http');
const producer = require('../../native/app/presentation-context.js');
const {execFileSync}=require('node:child_process');
const {compile}=require('../../scripts/compile-tv-web.cjs');

(async () => {
  const site = stage('noroot-startup-readiness');
  const historical=process.env.CYTV_READINESS_SOURCE,shared=['app.js','theme-manager.js','theme-data.js','personal-wallpaper.js','wallpaper-library.js'];
  const source=(edition,name)=>historical&&shared.includes(name)?execFileSync('git',['show',historical+':launcher/'+name],{encoding:'utf8'}):fs.readFileSync(path.join(site,edition,name),'utf8');
  const server = http.createServer((req, res) => {
    const file = path.resolve(site, '.' + new URL(req.url, 'http://localhost').pathname);
    if (!file.startsWith(site + path.sep) || !fs.existsSync(file)) return res.writeHead(404).end();
    res.setHeader('Content-Type', ({'.js':'application/javascript', '.json':'application/json', '.html':'text/html', '.css':'text/css', '.jpg':'image/jpeg', '.mp4':'video/mp4'})[path.extname(file)] || 'application/octet-stream');
    const name=path.basename(file),edition=path.basename(path.dirname(file));
    res.end(historical&&shared.includes(name)?source(edition,name):fs.readFileSync(file));
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const browser = await chromium.launch({headless:true, channel:process.env.BROWSER_CHANNEL || 'chrome'});
  async function check(savedBuiltin,edition) {
  const page = await browser.newPage({viewport:{width:1920,height:1080}}), errors = [];
  const context = producer({seed:7, content:() => true});
  let queries = 0, mediaRequests = 0, releaseMedia;
  const mediaGate = new Promise(resolve => { releaseMedia = resolve; });
  page.on('pageerror', error => errors.push(error.message));
  await page.exposeFunction('producerContext', () => { queries++; return context.context(); });
  await page.addInitScript(({savedBuiltin,rootEdition}) => {
    localStorage.setItem('tvhome.theme.choice.v1', JSON.stringify({id:'builtin:ribbon',title:'Ribbon'}));
    window.PalmSystem = {launchParams:{cytvHome:{reason:'home',generation:8}},activate(){}};
    window.rootAudit=[];
    if(rootEdition){
      const frame=requestAnimationFrame.bind(window),queued=[];let active=false;
      Object.defineProperty(document,'hidden',{configurable:true,get:()=>!active});
      window.requestAnimationFrame=callback=>active?frame(time=>{rootAudit.push('frame');callback(time);}):(queued.push(callback),queued.length);
      PalmSystem.activate=()=>{rootAudit.push('activate');active=true;queued.splice(0).forEach(callback=>requestAnimationFrame(callback));document.dispatchEvent(new Event('visibilitychange'));};
    }
    window.seedWallpaper=savedBuiltin?new Promise((resolve,reject)=>{
      const request=indexedDB.open('ctv-personal-wallpaper-v1',1);
      request.onupgradeneeded=()=>request.result.createObjectStore('wallpaper');
      request.onerror=reject;request.onsuccess=()=>{const db=request.result,tx=db.transaction('wallpaper','readwrite');tx.objectStore('wallpaper').put({envelope:null,source:'builtin:black-hole'},'slot');tx.oncomplete=()=>{db.close();resolve();};tx.onerror=reject;};
    }):Promise.resolve();
  }, {savedBuiltin,rootEdition:edition==='root-launcher'});
  await page.route('**/personal-wallpaper.js', route => route.fulfill({body:
    source(edition,'personal-wallpaper.js') + `
      const restoreWallpaper=PersonalWallpaper.start;
      PersonalWallpaper.start=function(){return seedWallpaper.then(()=>restoreWallpaper());};` }));
  await page.route(/^https:/, route => route.abort());
  await page.route('**/theme-data.js', route => route.fulfill({body:
    source(edition,'theme-data.js') + `
      const prepareAppearance=ThemeData.prepare;
      ThemeData.prepare=function(){return prepareAppearance.apply(this,arguments).then(input=>{window.preparedAppearance=input;return input;});};` }));
  await page.route('**/preview/bridge.js', route => route.fulfill({body:
    fs.readFileSync(path.join(site, 'preview/bridge.js'), 'utf8') + `
      window.CYTV_BROWSER_PREVIEW=false;
      const original=window.PalmServiceBridge.prototype.call;
      window.PalmServiceBridge.prototype.call=function(uri,raw){
        if(window.ROOT_VERSION&&uri==='luna://com.cleanyourtv.system.updater.service/restoreProfile'){
          rootAudit.push('restore');
          const icon='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aE1sAAAAASUVORK5CYII=';
          const profile={schema:1,inventory:{apps:[{id:'readiness.app',title:'Readiness fixture',icon}],inputs:[]},config:{columns:5,dockApps:['readiness.app'],hiddenApps:[]},settings:{}};
          this.onservicecallback(JSON.stringify({returnValue:true,result:{profile,transaction:'readiness-root',version:ROOT_VERSION,phase:'verifying'}}));return;
        }
        if(window.ROOT_VERSION&&uri==='luna://com.cleanyourtv.system.updater.service/healthy'){
          rootAudit.push('healthy');window.rootHealth={payload:JSON.parse(raw),rendered:RootLauncherRendered,marker:localStorage.getItem('tvhome.theme.trial.v1'),theme:ThemeManager.current().id};
          this.onservicecallback(JSON.stringify({returnValue:true,result:{}}));return;
        }
        if(window.ROOT_VERSION&&uri==='luna://com.cleanyourtv.root.preview.service/status'&&JSON.parse(raw).presentation==='context'){
          window.producerContext().then(()=>this.onservicecallback(JSON.stringify({returnValue:true,result:{content:true}})));return;
        }
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
    await page.goto('http://127.0.0.1:' + server.address().port + '/'+edition+'/index.html');
    // Hold optional media beyond the actual production producer's 2000 ms TTL.
    await page.waitForTimeout(2300);
    const before = await page.evaluate(() => ({ready:window.RootLauncherRendered === true, theme:ThemeManager.current().id, presentation:HomePresentationController.state()}));
    console.log(JSON.stringify({edition,savedBuiltin,before,queries,mediaRequests,producer:context.context()}));
    assert.equal(before.ready,true,'verified poster/layout must become ready without optional video bytes');
    assert.equal(before.theme,'builtin:ribbon');
    if(savedBuiltin)assert.equal(await page.evaluate(()=>PersonalWallpaper.state().builtinId),'builtin:black-hole');
    assert.equal(before.presentation.mode,'overlay','real producer fact must reach launcher while fresh');
    assert.equal(before.presentation.content,true);
    assert.equal(mediaRequests,0,'content overlay must not fetch wallpaper video');
    if(edition==='root-launcher'){
      const root=await page.evaluate(()=>({version:ROOT_VERSION,health:rootHealth,audit:rootAudit,profile:localStorage.getItem(RootProfileData.key)}));
      assert(root.version&&root.profile,'actual Root version branch and profile restore adapter ran');
      assert.equal(root.health.rendered,true);assert.equal(root.health.theme,'builtin:ribbon');assert.equal(root.health.marker,null);
      assert.equal(root.health.payload.edition,'root');
      assert(root.audit.indexOf('restore')<root.audit.indexOf('activate'));
      assert(root.audit.indexOf('activate')<root.audit.indexOf('frame'),'Root activates before any presentation frame');
      assert(root.audit.slice(0,root.audit.indexOf('healthy')).filter(event=>event==='frame').length>=2,'profile health follows painted readiness frames');
      assert.equal(await page.evaluate(()=>HomeWallpaper.state().paused),true,'Root content context retains the decoder guard');
    }
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
    console.log('PASS '+edition+' '+(savedBuiltin?'saved builtin wallpaper':'saved theme')+' poster-first readiness before slow media; presentation/profile/frame ordering preserved');
  } finally {
    releaseMedia();
    await page.close();
  }
  }
  async function checkOverlap(edition,scenario) {
    const page=await browser.newPage(),errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    const names=['app.js','theme-data.js','personal-wallpaper.js'],sources={};
    for(const name of names)sources[name]=source(edition,name);
    const compiled=await compile(sources);
    try {
      await page.addInitScript(()=>{
        localStorage.setItem('tvhome.theme.choice.v1',JSON.stringify({id:'builtin:ribbon',title:'Ribbon'}));
        window.activationCalls=0;window.PalmSystem={activate(){window.activationCalls++;}};
        window.seedWallpaper=new Promise((resolve,reject)=>{
          const request=indexedDB.open('ctv-personal-wallpaper-v1',1);
          request.onupgradeneeded=()=>request.result.createObjectStore('wallpaper');
          request.onerror=reject;request.onsuccess=()=>{const db=request.result,tx=db.transaction('wallpaper','readwrite');tx.objectStore('wallpaper').put({envelope:null,source:'builtin:black-hole'},'slot');tx.oncomplete=()=>{db.close();resolve();};tx.onerror=reject;};
        });
      });
      await page.route(/^https:/,route=>route.abort());
      await page.route('**/app.js',route=>route.fulfill({body:compiled['app.js']}));
      await page.route('**/preview/bridge.js',route=>route.fulfill({body:fs.readFileSync(path.join(site,'preview/bridge.js'),'utf8')+';window.CYTV_BROWSER_PREVIEW=false;window.PREVIEW_HOME_CONTEXT="content";'}));
      await page.route('**/theme-data.js',route=>route.fulfill({body:compiled['theme-data.js']+';var realThemePrepare=ThemeData.prepare;ThemeData.prepare=function(){var args=arguments;if(window.themeRequested)return realThemePrepare.apply(ThemeData,args);window.themeRequested=true;return new Promise(function(resolve,reject){window.releaseTheme=function(fail){if(fail)reject(Error("Theme fixture failure"));else resolve(realThemePrepare.apply(ThemeData,args));};});};'}));
      await page.route('**/personal-wallpaper.js',route=>route.fulfill({body:compiled['personal-wallpaper.js']+';var realPersonalStart=PersonalWallpaper.start;PersonalWallpaper.start=function(){window.personalRequested=true;return window.personalRestore||(window.personalRestore=new Promise(function(resolve,reject){window.releasePersonal=function(fail){if(fail)reject(Error("Personal fixture failure"));else resolve(seedWallpaper.then(function(){return realPersonalStart();}));};}).then(function(value){window.personalSettled=true;return value;}));};'}));
      await page.goto('http://127.0.0.1:'+server.address().port+'/'+edition+'/index.html');
      await page.waitForFunction(()=>window.themeRequested===true);
      assert.equal(await page.evaluate(()=>window.personalRequested===true),true,'personal restoration starts before theme preparation completes');
      const pending=()=>page.evaluate(()=>({ready:RootLauncherRendered,hidden:document.getElementById('homeSurface').classList.contains('ctv-starting'),activations:activationCalls}));
      assert.deepEqual(await pending(),{ready:false,hidden:true,activations:0});
      const personalFirst=scenario==='personal-first'||scenario==='personal-failure'||scenario==='cancel';
      await page.evaluate(({personalFirst,scenario})=>personalFirst?releasePersonal(scenario==='personal-failure'):releaseTheme(scenario==='theme-failure'),{personalFirst,scenario});
      await page.waitForTimeout(80);
      if(personalFirst&&scenario!=='personal-failure')await page.waitForFunction(()=>window.personalSettled===true);
      assert.deepEqual(await pending(),{ready:false,hidden:true,activations:0},'either pending appearance prevents reveal and activation');
      if(scenario==='cancel')await page.evaluate(()=>ThemeManager.reset());
      await page.evaluate(personalFirst=>personalFirst?releaseTheme():releasePersonal(),personalFirst);
      await page.waitForFunction(()=>RootLauncherRendered===true);
      const expected=scenario==='theme-failure'||scenario==='cancel'?'builtin:classic':'builtin:ribbon';
      assert.equal(await page.evaluate(()=>ThemeManager.current().id),expected);
      assert.equal(await page.evaluate(()=>PersonalWallpaper.state().builtinId),scenario==='personal-failure'?null:'builtin:black-hole','late theme application/recovery preserves the independently restored wallpaper');
      assert.equal(await page.evaluate(()=>activationCalls),1);
      assert.equal(await page.locator('video').count(),0,'overlap cannot bypass native decoder ownership');
      assert.deepEqual(errors,[]);
      console.log('PASS compiled '+edition+' concurrent startup '+scenario+'; both appearance barriers and activation ordering retained');
    } finally {await page.close();}
  }
  try {
    const editions=process.env.CYTV_READINESS_EDITION?[process.env.CYTV_READINESS_EDITION]:['launcher','root-launcher'],overlapOnly=process.env.CYTV_READINESS_OVERLAP_ONLY==='1';
    if(!overlapOnly)for(const edition of editions)for(const savedBuiltin of [false,true])await check(savedBuiltin,edition);
    if(!historical||overlapOnly)for(const edition of editions)for(const scenario of ['personal-first','theme-first','theme-failure','personal-failure','cancel'])await checkOverlap(edition,scenario);
  } finally {
    await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
})().catch(error => {console.error(error);process.exitCode=1;});
