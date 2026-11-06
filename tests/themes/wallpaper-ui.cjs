/* Real browser decoding of an original procedural H264 fixture, no TV acceptance claim. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {chromium}=require('playwright');
(async()=>{
 const fixture=process.env.WALLPAPER_TEST_MP4 || path.resolve('tests/themes/fixtures/wallpaper-blue.mp4');
 assert(fs.existsSync(fixture),'Set WALLPAPER_TEST_MP4 to an original silent H264 MP4 fixture');
 const browser=await chromium.launch({headless:true,args:['--autoplay-policy=no-user-gesture-required']});
 try {
  const page=await browser.newPage({viewport:{width:1920,height:1080}});
  await page.setContent('<html><body><main id="homeSurface" class="ctv-home" style="position:absolute;width:1920px;height:1080px;transform:scale(.5);background:red"><div id="ambient" class="ctv-ambient"></div></main></body></html>');
  await page.addStyleTag({path:'launcher/wallpaper.css'});
  await page.addScriptTag({path:'launcher/wallpaper.js'});
  assert.equal(await page.locator('#ambient').evaluate(el=>getComputedStyle(el).visibility),'visible','Classic without wallpaper retains its app-colour glow');
  await page.evaluate(bytes=>{
   const url=URL.createObjectURL(new Blob([Uint8Array.from(atob(bytes),c=>c.charCodeAt(0))],{type:'video/mp4'}));
   window.testInput={manifest:{id:'test:movie',title:'Test video',defaults:{dim:.3,wallpaperAssetId:'poster'},assets:[{id:'poster',width:1920,height:1080}],wallpaperVideo:{variants:[{quality:'1080p',width:1920,height:1080}]}},assetHandles:{poster:'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'},videoHandles:{'1080p':url}};
   HomeWallpaper.configure(testInput);
  },fs.readFileSync(fixture).toString('base64'));
  assert.equal(await page.locator('#ambient').evaluate(el=>getComputedStyle(el).visibility),'hidden','the poster is not tinted while the first video frame prepares');
  await page.waitForFunction(()=>HomeWallpaper.state().actualQuality==='1080p');
  assert.equal(await page.locator('#ambient').evaluate(el=>getComputedStyle(el).visibility),'hidden','playing video is not tinted');
  const geometry=await page.evaluate(()=>{const v=document.querySelector('video'),r=v.getBoundingClientRect();return {parent:v.parentNode.parentNode.tagName,width:r.width,height:r.height,muted:v.muted,loop:v.loop,frames:v.getVideoPlaybackQuality().totalVideoFrames};});
  assert.equal(geometry.parent,'BODY');assert.equal(geometry.width,1920);assert.equal(geometry.height,1080);assert(geometry.muted&&geometry.loop);assert(geometry.frames>0);
  await page.evaluate(()=>{window.oldVideo=document.querySelector('video');HomeWallpaper.suspend('settings');HomeWallpaper.suspend('dialog');HomeWallpaper.resume('settings');});
  assert.equal(await page.locator('video').count(),0);assert(await page.evaluate(()=>oldVideo.paused&&!oldVideo.hasAttribute('src')));
  assert.equal(await page.locator('#ambient').evaluate(el=>getComputedStyle(el).visibility),'hidden','decoder suspension cannot restore the coloured glow over a selected wallpaper');
  await page.evaluate(()=>HomeWallpaper.resume('dialog'));await page.waitForFunction(()=>HomeWallpaper.state().actualQuality==='1080p');
  await page.evaluate(()=>HomeWallpaper.setQuality('image'));assert.equal(await page.locator('video').count(),0);assert.equal(await page.evaluate(()=>document.body.classList.contains('ctv-wallpaper-playing')),false);
  assert.equal(await page.locator('#ambient').evaluate(el=>getComputedStyle(el).visibility),'hidden','image-only wallpaper is not tinted');
  await page.evaluate(()=>{HomeWallpaper.configure(testInput);HomeWallpaper.reset();});await page.waitForTimeout(100);assert.equal(await page.locator('video').count(),0);assert.equal(await page.evaluate(()=>HomeWallpaper.state().themeId),'builtin:classic');
  assert.equal(await page.locator('#ambient').evaluate(el=>getComputedStyle(el).visibility),'visible','removing wallpaper restores the Classic glow');
  await page.evaluate(()=>{
   testInput.manifest.wallpaperVideo.variants.unshift({quality:'4k',width:3840,height:2160});testInput.videoHandles['4k']=testInput.videoHandles['1080p'];
   window.modes=[];document.addEventListener('home-wallpaper-change',()=>modes.push(HomeWallpaper.state().actualQuality));
   HomeWallpaper.configure(testInput);HomeWallpaper.setQuality('4k');
  });
  await page.waitForFunction(()=>HomeWallpaper.state().actualQuality==='1080p');
  assert.equal(await page.evaluate(()=>modes.includes('4k')),false,'decoded FHD cannot be promoted as UHD from manifest metadata');
  assert.match(await page.evaluate(()=>HomeWallpaper.state().notice),/dimensions/);
  await page.evaluate(()=>HomeWallpaper.reset());
  console.log('PASS real H264 decode, unscaled viewport, silent looping, decoder release and stale replacement');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
