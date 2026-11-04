// First-presented appearance and real intermediate motion, both editions.
'use strict';
const {assert,fs,path,chromium,stage}=require('./browser.cjs'),http=require('node:http');
const {loadRegistry}=require('../../scripts/check-theme-submissions.cjs');
const selectedCase=process.env.CYTV_THEME_CASE||'all';
(async()=>{
 const site=stage(),out=path.resolve('build/rc150-startup-motion',selectedCase);fs.mkdirSync(out,{recursive:true});
 const server=http.createServer((req,res)=>{const file=path.resolve(site,'.'+new URL(req.url,'http://localhost').pathname);if(!file.startsWith(site+path.sep)||!fs.existsSync(file))return res.writeHead(404).end();res.setHeader('Content-Type',file.endsWith('.js')?'application/javascript':file.endsWith('.css')?'text/css':file.endsWith('.json')?'application/json':file.endsWith('.png')?'image/png':file.endsWith('.jpg')?'image/jpeg':file.endsWith('.svg')?'image/svg+xml':'application/octet-stream');if(file.endsWith('.html'))res.setHeader('Content-Type','text/html');res.end(fs.readFileSync(file));});
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const browser=await chromium.launch({headless:true,channel:process.env.BROWSER_CHANNEL||'chrome'}),results=[];
 try{for(const edition of ['launcher','root-launcher']){
  const page=await browser.newPage({viewport:{width:1920,height:1080},locale:'en-US'}),errors=[];page.on('pageerror',e=>errors.push(e.message));await page.route(/^https:/,route=>route.abort());
  const url='http://127.0.0.1:'+server.address().port+'/'+edition+'/index.html';
  const wait=async()=>{await page.waitForFunction(()=>window.RootLauncherRendered===true);await page.locator('#tiles .focused').waitFor();};
  await page.goto(url);await wait();
  const native=await page.locator('#tiles img').evaluateAll(nodes=>nodes.map(node=>node.getAttribute('src')));
   const packs={};for(const title of ['Itachi','Channel']){const entry=loadRegistry().find(entry=>entry.record.title.indexOf(title)===0);assert(entry,'registry '+title);const base=path.resolve('showcase',entry.base),m=entry.manifest;packs[title]={descriptor:fs.readFileSync(path.join(base,'cytv-theme.json')).toString('base64'),files:{}};for(const file of [m.rules,...m.assets,...m.documents])packs[title].files[file.path]=fs.readFileSync(path.join(base,file.path)).toString('base64');}
   await page.evaluate(async packs=>{for(const title in packs){const e=packs[title],decode=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0)),descriptor=decode(e.descriptor),pack={descriptor,digest:ThemeData.hash(descriptor),files:{}};for(const file in e.files)pack.files[file]=decode(e.files[file]);const verified=ThemeData.verify(pack,'1.6.0');await ThemeStore.put(pack,verified.size);}},packs);
  if(selectedCase!=='motion'){
   await page.addInitScript(()=>{window.auditFrames=[];function frame(){var home=document.getElementById('homeSurface');if(home){var css=getComputedStyle(home);auditFrames.push({visible:css.visibility==='visible'&&css.display!=='none',background:css.backgroundImage==='none'?'none':'image',video:!!(window.HomeWallpaper&&HomeWallpaper.state().actualQuality!=='image'),theme:window.ThemeManager?ThemeManager.current().id:null,ready:window.RootLauncherRendered===true,marker:!!localStorage.getItem('tvhome.theme.trial.v1')});}if(auditFrames.length<1200)requestAnimationFrame(frame);}requestAnimationFrame(frame);});
   const savedChoices=(await page.evaluate(()=>ThemeManager.list())).filter(item=>item.id!=='builtin:classic');
   for(const choice of savedChoices){
   await page.evaluate(choice=>localStorage.setItem('tvhome.theme.choice.v1',JSON.stringify(choice)),choice);
   await page.route('**/theme-data.js',route=>route.fulfill({contentType:'application/javascript',body:fs.readFileSync('launcher/theme-data.js','utf8')+`;window.auditPrepare=ThemeData.prepare;ThemeData.prepare=function(){var args=arguments;window.auditPreparing=true;return new Promise(function(resolve){window.auditRelease=function(){resolve(auditPrepare.apply(ThemeData,args));};});};`}));

   await page.reload();await page.waitForFunction(()=>window.auditPreparing);await page.waitForTimeout(120);
   assert.equal(await page.locator('#homeSurface').evaluate(el=>getComputedStyle(el).visibility),'hidden','Home must not expose Classic while saved theme prepares');assert.equal(await page.evaluate(()=>RootLauncherRendered),false,'render readiness cannot precede saved appearance');
   await page.evaluate(()=>{for(const key of [38,39,39,13])document.dispatchEvent(new KeyboardEvent('keydown',{keyCode:key,which:key,bubbles:true,cancelable:true}));document.dispatchEvent(new KeyboardEvent('keyup',{keyCode:13,which:13,bubbles:true}));});
   assert.equal(await page.evaluate(()=>!!(window.RenewalPanel&&RenewalPanel.isOpen())),false,'hidden pending Home must not open Settings from remote input');
   await page.evaluate(()=>auditRelease());await wait();await page.waitForTimeout(60);
   const frames=await page.evaluate(()=>auditFrames),shown=frames.filter(frame=>frame.visible);
   assert(shown.length);assert(shown.every(frame=>frame.theme===choice.id&&(frame.background===(choice.title==='Channel'?'none':'image')||frame.video&&choice.id==='builtin:ribbon')),'every exposed startup frame uses saved wallpaper/appearance');
   assert(frames.filter(frame=>frame.ready).every(frame=>frame.visible&&!frame.marker),'ready only follows exposed presentation and completed boot marker');
   const before=await page.locator('#homeSurface').evaluate(el=>getComputedStyle(el).backgroundImage);
   const videoActive=await page.evaluate(()=>HomeWallpaper.state().actualQuality!=='image');
   await page.evaluate(()=>{window.auditLoads=0;ThemeData.load=function(){auditLoads++;throw Error('warm return must not load');};Object.defineProperty(document,'hidden',{configurable:true,value:true});document.dispatchEvent(new Event('visibilitychange'));});
   const hiddenBackground=await page.locator('#homeSurface').evaluate(el=>getComputedStyle(el).backgroundImage);
   if(videoActive)assert.notEqual(hiddenBackground,'none','suspending video restores the accepted poster');else assert.equal(hiddenBackground,before,'image stays accepted even while hidden');
   await page.evaluate(()=>document.dispatchEvent(new Event('webOSRelaunch')));
   assert.equal(await page.locator('#ctv-theme-style').evaluate(el=>el.disabled),false,'relaunch-before-visible cannot expose a disabled sheet');
   await page.evaluate(()=>{Object.defineProperty(document,'hidden',{configurable:true,value:false});document.dispatchEvent(new Event('visibilitychange'));});
   assert.equal(await page.evaluate(()=>auditLoads),0);
   await page.locator('#btnSettings').click();assert.equal(await page.locator('#ctv-theme-style').evaluate(el=>el.disabled),true,'settings remains standard');
   await page.evaluate(()=>{Object.defineProperty(document,'hidden',{configurable:true,value:true});document.dispatchEvent(new Event('visibilitychange'));Object.defineProperty(document,'hidden',{configurable:true,value:false});document.dispatchEvent(new Event('visibilitychange'));});
   assert.equal(await page.locator('#ctv-theme-style').evaluate(el=>el.disabled),true,'visibility cannot release settings owner');await page.keyboard.press('Escape');assert.equal(await page.locator('#ctv-theme-style').evaluate(el=>el.disabled),false);
   await page.screenshot({path:path.join(out,edition+'-first-'+choice.title.replace(/[^a-z]/gi,'').toLowerCase()+'.png')});
   results.push({edition,case:'startup',theme:choice.id,frames:frames.map(frame=>({...frame})),warmFetches:0});
   await page.unroute('**/theme-data.js');
   await page.reload();await wait();
   }
   await page.unroute('**/theme-data.js');
   await page.reload();await wait();
   await page.evaluate(()=>localStorage.setItem('tvhome.theme.trial.v1',JSON.stringify({kind:'trial',id:'builtin:alpine'})));
   await page.reload();await wait();assert.equal(await page.evaluate(()=>ThemeManager.current().id),'builtin:classic','interrupted preview presents trusted Classic');assert.equal(await page.evaluate(()=>localStorage.getItem(ThemeManager.trialKey)),null);
   await page.evaluate(()=>localStorage.setItem('tvhome.theme.choice.v1',JSON.stringify({id:'builtin:ribbon',title:'Ribbon'})));
   await page.route('**/theme-data.js',route=>route.fulfill({contentType:'application/javascript',body:fs.readFileSync('launcher/theme-data.js','utf8')+`;window.auditPrepare=ThemeData.prepare;ThemeData.prepare=function(){var args=arguments;window.auditPreparing=true;return new Promise(function(resolve){window.auditRelease=function(){resolve(auditPrepare.apply(ThemeData,args));};});};`}));
   await page.reload();await page.waitForFunction(()=>window.auditPreparing);await wait();
   assert.equal(await page.evaluate(()=>ThemeManager.current().id),'builtin:classic','watchdog makes Home usable when preparation never completes');assert.match(await page.evaluate(()=>ThemeManager.current().notice),/timed out/i);
   const fallback=await page.evaluate(()=>auditFrames);assert(fallback.some(frame=>frame.visible),'bounded fallback must actually become visible');assert(fallback.filter(frame=>frame.visible).every(frame=>frame.theme==='builtin:classic'&&frame.background==='none'),'timeout never exposes a stale/partially restored appearance');
   await page.evaluate(()=>auditRelease());await page.waitForTimeout(200);assert.equal(await page.evaluate(()=>ThemeManager.current().id),'builtin:classic','late decode cannot replace fallback');
   results.push({edition,case:'fallback',frames:fallback});await page.unroute('**/theme-data.js');await page.reload();await wait();
  }
  if(selectedCase!=='startup'){
   for(const theme of ['Classic','Liquid Glass','Itachi','Channel']){
    await page.evaluate(async title=>{const item=(await ThemeManager.list()).find(item=>item.title.indexOf(title)===0);await ThemeManager.selectInstalled(item);},theme);
    const originalIds=await page.locator('#tiles .item').evaluateAll(nodes=>nodes.map(n=>n.dataset.appId||'add'));
    // Park a real pointer before remote navigation; moving geometry must not steal focus.
    await page.locator('#tiles .focused .card').hover();
    for(const interval of [50,80,120,200]){
     const trace=await page.evaluate(async interval=>{
      var frames=[],failures=[],count=document.querySelectorAll('#tiles .item').length,state=HomeLayoutState.state(),scenic=state.preset==='scenic-grid';
      function selected(){return Array.prototype.indexOf.call(document.querySelectorAll('#tiles .item'),document.querySelector('#tiles .item.focused'));}
      var expected=selected(),running=true;
      // A fresh tap may glide the rows or bump an edge; only those frames skip the exact
      // stage/item position check. Held repeats, focus, glass and bounds stay strict.
      function settling(){var c=document.getElementById('homeSurface').classList;return c.contains('ctv-scroll-glide')||c.contains('ctv-edge-bump');}
      function sample(){var item=document.querySelector('#tiles .item.focused');if(item){var r=item.getBoundingClientRect(),card=item.querySelector('.card').getBoundingClientRect(),glass=document.getElementById('glass'),g=glass.getBoundingClientRect(),x=Math.abs(r.left-parseFloat(item.style.left)),stage=document.getElementById('stage'),transform=new WebKitCSSMatrix(getComputedStyle(stage).transform),target=new WebKitCSSMatrix(stage.style.transform),y=Math.abs(transform.m42-target.m42),glassLag=getComputedStyle(glass).display==='none'?0:Math.abs(g.left+g.width/2-card.left-card.width/2);var frame={index:selected(),expected,x,y,glassLag,left:card.left,right:card.right,top:card.top,bottom:card.bottom};frames.push(frame);if(frame.index!==expected||!settling()&&(x>1||y>1)||glassLag>1||card.left<0||card.right>1921)failures.push(frame);}if(running)requestAnimationFrame(sample);}
      requestAnimationFrame(sample);
      var directions=scenic?[39,37]:[40,38,39,37];
      for(var d=0;d<directions.length;d++){var key=directions[d];for(var step=0;step<(scenic?count*2+1:Math.max(state.columns+1,Math.ceil(count/state.columns)+1));step++){
       if(scenic)expected=(expected+(key===39?1:-1)+count)%count;
       else if(key===39&&expected%state.columns<state.columns-1&&expected<count-1)expected++;
       else if(key===37&&expected%state.columns>0)expected--;
       else if(key===40&&Math.floor(expected/state.columns)<Math.floor((count-1)/state.columns))expected=Math.min(expected+state.columns,count-1);
       else if(key===38&&Math.floor(expected/state.columns)>0)expected-=state.columns;
       // Stay inside the grid at its upper boundary; header navigation is covered separately.
       if(key===38&&Math.floor(selected()/state.columns)===0)continue;
       document.dispatchEvent(new KeyboardEvent('keydown',{keyCode:key,which:key,bubbles:true,cancelable:true,repeat:step>0}));
       await new Promise(resolve=>setTimeout(resolve,interval));
      }document.dispatchEvent(new KeyboardEvent('keyup',{keyCode:key,which:key,bubbles:true}));}
      await new Promise(resolve=>setTimeout(resolve,80));running=false;return {frames,failures};
     },interval);
     results.push({edition,case:'motion',theme,interval,...trace});assert.equal(trace.failures.length,0,theme+' '+edition+' '+interval+'ms: exact focus and bounded intermediate geometry; first failure '+JSON.stringify(trace.failures[0]));
    }
    assert.deepEqual(await page.locator('#tiles img').evaluateAll(nodes=>nodes.map(node=>node.getAttribute('src'))),native,'original native icon sources remain unchanged');
    // Reorder/cancel uses the same immediate remote geometry, without a queue.
    await page.keyboard.down('Enter');await page.waitForTimeout(650);await page.keyboard.up('Enter');assert.equal(await page.locator('#tiles .moving').count(),1);await page.keyboard.press('ArrowLeft');await page.keyboard.press('Escape');assert.deepEqual(await page.locator('#tiles .item').evaluateAll(nodes=>nodes.map(n=>n.dataset.appId||'add')),originalIds);
    await page.emulateMedia({reducedMotion:'reduce'});await page.keyboard.press('ArrowRight');assert.equal(await page.locator('#tiles .focused').evaluate(el=>getComputedStyle(el).transitionDuration),'0s');await page.emulateMedia({reducedMotion:'no-preference'});
    await page.screenshot({path:path.join(out,edition+'-'+theme.toLowerCase()+'.png')});
   }
  }
  assert.deepEqual(errors,[]);await page.close();console.log('PASS first-frame/warm lifecycle and/or held-arrow intermediate geometry: '+edition);
 }}finally{fs.writeFileSync(path.join(out,'results.json'),JSON.stringify(results,null,2));await browser.close();await new Promise(resolve=>server.close(resolve));}
})().catch(error=>{console.error(error);process.exitCode=1;});
