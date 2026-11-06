const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const root = path.resolve(__dirname,'../..');
const details = JSON.parse(execFileSync(process.env.CYTV_PYTHON || 'python3',['-c',`
import json
from cytv import i18n
from android.tests.test_bridge import BridgeTests
module=BridgeTests().module()
class Native:
 def __init__(self):self.events=[]
 def emit(self,raw):self.events.append(json.loads(raw))
result={}
for language in i18n.LANGUAGES:
 if language=='auto':continue
 i18n.set_language(language);native=Native();console=module.AndroidConsole(module.Callbacks(native))
 console.recovery_plan({'state':'blocked','disposition':'clean-removal','summary':'Removal is still in progress.','next_step':'Continue the remaining cleanup for this TV.',
  'actions':['continue-removal','retain-evidence'],'removal':{'stage':'private-cleanup','reason':'private-cleanup-incomplete'}})
 result[language]=native.events[-1]
print(json.dumps(result))
`],{cwd:root,encoding:'utf8'}));
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
          const plan={kind:'recovery-plan',state:'complete',removed:true,summary:'Completion received',nextStep:'Keep the existing report.'};
          if(disposition!==null)plan.disposition=disposition;
          if(proof!==null)plan.verified_clean=proof;
          receiveNative(plan);
          receiveNative({kind:'finished',code:0});
        },{disposition,proof,edition});
        const complete=disposition==='clean-removal'&&proof===true;
        assert.equal(await page.locator('.review-symbol').count(),complete?0:1,`${edition}/${disposition}/${proof}`);
        assert.equal(await page.locator('h1').innerText(),complete?'Completion received':'Removal is not finished yet.');
      }
    }
  }
  for (const [language,event] of Object.entries(details)) {
    await page.evaluate(language=>localStorage.setItem('cytv-language',language),language);
    await page.reload();
    await page.evaluate(event=>{
      receiveNative({kind:'started',config:{host:'192.0.2.10',port:2222,edition:'root',action:'uninstall'}});
      receiveNative(event);
    },event);
    assert((await page.locator('#recovery-details').innerText()).includes(event.stageText),language+' live stage');
    await page.evaluate(()=>receiveNative({kind:'finished',code:2}));
    assert.equal(await page.locator('.review-symbol').count(),1);
    assert((await page.locator('.recovery-info').innerText()).includes(event.blockerText));
    assert.equal(await page.locator('[data-action=retry-removal]').count(),1);
    await page.evaluate(event=>{receiveNative({...event,actions:['retain-evidence']});receiveNative({kind:'finished',code:2});},event);
    assert.equal(await page.locator('[data-action=retry-removal]').count(),1,language+' retry rechecks same goal');
    await page.evaluate(event=>{receiveNative(event);receiveNative({kind:'finished',code:2});},event);
    assert.equal(await page.locator('[data-action=recover]').count(),0);
    assert(!(await page.locator('body').innerText()).includes('PRIVATE'));
  }
  await page.close();
  await browser.close();
  console.log('PASS Android removal: 18 proof combinations; 13 localized bridge phase/blocker events, live rendering and assessment-backed same-TV actions');
})().catch(async error=>{console.error(error);if(browser)await browser.close();process.exitCode=1});
