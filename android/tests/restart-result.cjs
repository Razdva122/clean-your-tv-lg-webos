const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
let browser;
(async()=>{
 browser=await chromium.launch({headless:true,executablePath:process.env.CYTV_CHROME||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 const page=await browser.newPage({locale:'en',viewport:{width:320,height:740}});
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.addInitScript(()=>window.CYTV={snapshot:()=> '[]',hasKey:()=>false,start:()=>{},answer:()=>{}});
 await page.goto('file://'+path.resolve(__dirname,'../app/src/main/assets/ui/index.html'));
 const variants=[{restart_required:true},{removal:{stage:'restart-required'}},
  {restart_required:false,removal:{stage:'restart-required'}},
  {restart_required:false,removal:{stage:'package-removal',reason:'restart-required'}},
  {restart_required:false,reason:'restart-required'}];
 for(const variant of variants){
  await page.evaluate(variant=>{
   receiveNative({kind:'started',config:{host:'192.0.2.10',edition:'root',action:'uninstall'}});
   receiveNative({kind:'recovery-plan',state:'complete',disposition:'clean-removal',removed:true,verified_clean:true,
    summary:'Stale complete flags',nextStep:'Try again',...variant});
   receiveNative({kind:'finished',code:0});
  },variant);
  assert.equal(await page.locator('.review-symbol').count(),1,JSON.stringify(variant));
  assert.equal(await page.locator('h1').innerText(),'Restart the TV to finish removal');
  assert((await page.locator('.recovery-info').innerText()).includes('disconnect it from power'));
 }
 for(const malformed of ['PRIVATE',['PRIVATE'],true,1,{stage:['PRIVATE'],reason:{PRIVATE:1}}]){
  await page.evaluate(removal=>{
   receiveNative({kind:'started',config:{host:'192.0.2.10',edition:'root',action:'uninstall'}});
   receiveNative({kind:'recovery-plan',state:'waiting',disposition:'clean-removal',removed:false,verified_clean:false,
    removal,summary:'Removal is not finished yet.',nextStep:'Try again'});
   receiveNative({kind:'finished',code:0});
  },malformed);
  assert.equal(await page.locator('.review-symbol').count(),1);
  assert.equal(await page.locator('h1').innerText(),'Removal is not finished yet.');
 }
 await page.evaluate(()=>{
  receiveNative({kind:'started',config:{host:'192.0.2.10',edition:'root',action:'uninstall'}});
  receiveNative({kind:'recovery-plan',state:'complete',disposition:'clean-removal',removed:true,verified_clean:true,
   stageText:'Restart the TV to finish removal',summary:'Verified current cleanup',nextStep:'Done'});
  receiveNative({kind:'finished',code:0});
 });
 assert.equal(await page.locator('.review-symbol').count(),0,'translated prose is not restart authority');
 assert.equal(await page.locator('h1').innerText(),'Verified current cleanup');
 await page.evaluate(()=>{
  receiveNative({kind:'started',config:{host:'192.0.2.10',edition:'root',action:'install'}});
  receiveNative({kind:'recovery-plan',state:'complete',disposition:'home-off',
   summary:'Root setup finished with LG Home and Home control off.',nextStep:'Keep LG Home active.'});
  receiveNative({kind:'finished',code:0});
 });
 assert.equal(await page.locator('.review-symbol').count(),0);
 assert.equal(await page.locator('h1').innerText(),'Root setup finished with LG Home and Home control off.');
 assert.deepEqual(errors,[]);
 await browser.close();
 console.log('PASS removal restart semantics: five contradictory completion variants, five malformed shapes, semantic-only cleanup proof and unchanged Home-off completion');
})().catch(async error=>{console.error(error);if(browser)await browser.close();process.exitCode=1});
