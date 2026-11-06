const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
let browser;
(async () => {
  browser = await chromium.launch({headless:true, executablePath:process.env.CYTV_CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
  const page = await browser.newPage({locale:'en',viewport:{width:320,height:740}});
  await page.addInitScript(()=>window.CYTV={hasKey:()=>false,snapshot:()=> '[]',answer:()=>{}});
  await page.goto('file://' + path.resolve(__dirname,'../app/src/main/assets/ui/index.html'));
  for (const disposition of [null,'home-off','clean-removal']) {
    for (const proof of [null,false,true]) {
      for (const edition of ['root','no-root']) {
        await page.evaluate(({disposition,proof,edition})=>{
          receiveNative({kind:'started',config:{host:'192.0.2.10',edition,action:'uninstall'}});
          const plan={kind:'recovery-plan',state:'complete',summary:'Completion received',nextStep:'Keep the existing report.'};
          if(disposition!==null)plan.disposition=disposition;
          if(proof!==null)plan.verified_clean=proof;
          receiveNative(plan);
          receiveNative({kind:'finished',code:0});
        },{disposition,proof,edition});
        const complete=disposition==='clean-removal'&&proof===true;
        assert.equal(await page.locator('.review-symbol').count(),complete?0:1,`${edition}/${disposition}/${proof}`);
        assert.equal(await page.locator('h1').innerText(),complete?'Completion received':'Review recovery options');
      }
    }
  }
  await page.close();
  await browser.close();
  console.log('PASS explicit Android uninstall: 18 edition/disposition/proof combinations require both clean-removal and verified_clean true');
})().catch(async error=>{console.error(error);if(browser)await browser.close();process.exitCode=1});
