const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const vm = require('node:vm');
const ui = path.resolve(__dirname, '../app/src/main/assets/ui');
const {words} = vm.runInNewContext(fs.readFileSync(path.join(ui, 'translations.js'), 'utf8') + ';({words})');
let browser;
(async () => {
  browser = await chromium.launch({headless:true, executablePath:process.env.CYTV_CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
  for (const [locale, dictionary] of Object.entries(words)) {
    for (const action of ['status', 'restore', 'home-diagnostics', 'recover', 'uninstall']) {
      const page = await browser.newPage({locale, viewport:{width:320, height:740}, reducedMotion:'reduce'});
      await page.addInitScript(() => {
        window.requests = [];
        window.CYTV = {
          hasKey:()=>false, snapshot:()=> '[]', answer:()=>{}, saveReport:()=>requests.push({saveReport:true}),
          inspect:config=>receiveNative({kind:'inspection', host:JSON.parse(config).host, root_ssh:true, developer_ssh:false}),
          start:config=>requests.push(JSON.parse(config)),
        };
      });
      await page.goto('file://' + path.join(ui, 'index.html'));
      await page.locator('[data-action=tools]').click();
      assert.equal(await page.locator('.steps').count(), 0);
      await page.locator(`[data-action=choose-${action==='home-diagnostics'?'diagnostics':action}]`).click();
      assert.equal(await page.locator('h1').innerText(), dictionary[action==='uninstall'?'uninstall':action==='recover'?'recoveryReview':action==='home-diagnostics'?'homeDiagnostics':action==='status'?'statusTool':'restore']);
      await page.locator('#host').fill('192.168.1.50');
      await page.locator('[data-action=inspect]').click();
      assert.equal(await page.locator('.steps').count(), 0);
      assert.equal(await page.locator('h1').innerText(), dictionary.connectionMethod);
      await page.locator('[data-action=back]').click();
      assert.equal(await page.locator('h1').innerText(), dictionary[action==='uninstall'?'uninstall':action==='recover'?'recoveryReview':action==='home-diagnostics'?'homeDiagnostics':action==='status'?'statusTool':'restore']);
      assert.equal(await page.locator('#host').inputValue(), '192.168.1.50');
      await page.locator('[data-action=inspect]').click();
      await page.locator('[data-action=connect]').click();
      assert.equal(await page.locator('h1').innerText(), dictionary[action==='uninstall'?'uninstall':action==='recover'?'recoveryReview':action==='home-diagnostics'?'homeDiagnostics':action==='status'?'statusTool':'restore']);
      assert(!(await page.locator('body').innerText()).includes(dictionary.reviewFoot));
      await page.locator('[data-action=start]').click();
      assert.equal(await page.evaluate(()=>requests.at(-1).action), action);
      assert.equal(await page.locator('.task-list').count(), 0);
      assert.equal(await page.locator('.progress-copy p').innerText(), dictionary[action==='home-diagnostics'?'diagnosticProgress':'maintenanceProgress']);
      assert.equal(await page.locator('#live-caption').innerText(), dictionary.awaiting);
      const expectedTitle = dictionary[action==='uninstall'?'uninstall':action==='recover'?'recoveryReview':action==='home-diagnostics'?'homeDiagnostics':action==='status'?'statusTitle':'restoreTitle'].replace('<br>', '\n');
      assert.equal(await page.locator('[role=progressbar]').getAttribute('aria-label'), expectedTitle.replace('\n', ' '));
      await page.evaluate(()=>receiveNative({kind:'stage', stage:3}));
      assert.equal(await page.locator('.task-list').count(), 0);
      // Activity recreation replays the action, rather than installation defaults.
      await page.evaluate(a=>receiveNative({kind:'started', config:{host:'192.168.1.50', edition:'root', action:a}}), action);
      assert.equal(await page.locator('.task-list').count(), 0);
      const typography = await page.locator('.progress-copy p').evaluate(el=>({size:parseFloat(getComputedStyle(el).fontSize), family:getComputedStyle(el).fontFamily}));
      assert(typography.size >= 16);
      assert(typography.family.startsWith('system-ui'));
      for (const [width,height] of [[320,740],[375,667],[740,375]]) {
        await page.setViewportSize({width,height});
        assert(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth), `${locale}/${action}/${width} overflow`);
      }
      if(action==='home-diagnostics'){
        await page.evaluate(()=>{receiveNative({kind:'report-ready',name:'diagnostic-123456abcdef.json'});receiveNative({kind:'finished',code:0});});
        await page.locator('[data-action=save-report]').click();
        assert.equal(await page.evaluate(()=>requests.at(-1).saveReport),true);
        assert.equal(await page.locator('h1').innerText(),dictionary.reportDone);
      }
      await page.close();
    }
  }
  for (const [edition, port] of [['no-root', 9922], ['root', 2222]]) {
    for (const action of ['status', 'restore', 'home-diagnostics', 'recover', 'uninstall']) {
      const page = await browser.newPage({locale:'en'});
      await page.addInitScript(edition => {
        window.requests = [];
        window.CYTV = {
          hasKey:()=>false, snapshot:()=> '[]', answer:()=>{},
          inspect:config=>receiveNative({kind:'inspection', host:JSON.parse(config).host,
            root_ssh:edition==='root', developer_ssh:edition==='no-root', root_port:22}),
          start:config=>requests.push(JSON.parse(config)),
        };
      }, edition);
      await page.goto('file://' + path.join(ui, 'index.html'));
      await page.locator('#host').fill('192.0.2.10');
      await page.locator('[data-action=inspect]').click();
      await page.locator('[data-action=connect]').click();
      if (edition==='root') await page.locator('#port').fill(String(port));
      await page.locator('[data-action=start]').click();
      await page.evaluate(()=>receiveNative({kind:'finished', code:0}));
      await page.locator('[data-action=home]').click();
      await page.locator('[data-action=tools]').click();
      await page.locator(`[data-action=choose-${action==='home-diagnostics'?'diagnostics':action}]`).click();
      assert.equal(await page.locator('#port').inputValue(), String(port), 'Tools must preserve the chosen SSH port after Done');
      await page.locator('[data-action=start]').click();
      const request = await page.evaluate(()=>requests.at(-1));
      assert.equal(request.host, '192.0.2.10');
      assert.equal(request.edition, edition);
      assert.equal(request.port, port);
      assert.equal(request.action, action);
      await page.close();
    }
  }
  // Recovery-only install results must never claim installed Helper behavior.
  for (const state of ['review', 'ready', 'blocked', 'waiting', 'complete']) {
    const page = await browser.newPage({locale:'ru', viewport:{width:320,height:740}});
    await page.addInitScript(() => {
      window.CYTV={hasKey:()=>false,snapshot:()=> '[]',answer:()=>{}};
    });
    await page.goto('file://' + path.join(ui,'index.html'));
    await page.evaluate(state=>{
      receiveNative({kind:'started',config:{host:'192.0.2.10',edition:'no-root',port:9923,action:'install'}});
      receiveNative({kind:'recovery-plan',state,summary:'Проверка восстановления',nextStep:'Сохраните отчёт'});
      receiveNative({kind:'report-ready',name:'diagnostic-123456abcdef.json'});
      receiveNative({kind:'finished',code:state==='blocked'?2:0});
    },state);
    assert.equal(await page.locator('.gesture').count(),0);
    assert.equal(await page.locator('[data-action=restore]').count(),0);
    assert.equal(await page.locator('[data-action=status]').count(),0);
    assert.equal(await page.locator('[data-action=recover]').count(),state==='review'?1:0);
    assert.equal(await page.locator('[data-action=save-report]').count(),1);
    assert.equal(await page.locator(state==='complete'?'.progress-copy p':'.recovery-info').innerText(),'Сохраните отчёт');
    assert.equal(await page.locator('.review-symbol').count(),state==='complete'?0:1);
    if(state!=='complete')assert.equal(await page.locator('.result-symbol svg use[href="#check"]').count(),0);
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.evaluate(()=>receiveNative({kind:'question',text:'Проверить? [y/N]',defaultNo:true,context:'Отдельное подтверждение'}));
    await page.waitForFunction(()=>document.activeElement?.dataset.action==='cancel-prompt');
    assert.equal(await page.locator('[data-action=confirm]').count(),1);
    await page.close();
  }
  // A removal exit code cannot substitute for the backend's final cleanup proof.
  for (const verifiedClean of [undefined,false,true]) {
    const page=await browser.newPage({locale:'en'});
    await page.addInitScript(()=>window.CYTV={hasKey:()=>false,snapshot:()=> '[]',answer:()=>{}});
    await page.goto('file://'+path.join(ui,'index.html'));
    await page.evaluate(verifiedClean=>{
      receiveNative({kind:'started',config:{host:'192.0.2.10',edition:'root',action:'uninstall'}});
      receiveNative({kind:'recovery-plan',state:'complete',disposition:'clean-removal',verified_clean:verifiedClean,
        summary:'Clean Your TV removal is verified.',nextStep:'Other TV apps stay installed.'});
      receiveNative({kind:'finished',code:0});
    },verifiedClean);
    assert.equal(await page.locator('.review-symbol').count(),verifiedClean===true?0:1);
    assert.equal(await page.locator('h1').innerText(),verifiedClean===true?'Clean Your TV removal is verified.':'Review recovery options');
    await page.close();
  }
  // An intentionally completed LG Home goal outranks physical Clean Home checks.
  {
    const page=await browser.newPage({locale:'en',viewport:{width:320,height:740}});
    await page.addInitScript(()=>window.CYTV={hasKey:()=>false,snapshot:()=> '[]',answer:()=>{}});
    await page.goto('file://'+path.join(ui,'index.html'));
    await page.evaluate(()=>{
      receiveNative({kind:'started',config:{host:'192.0.2.10',edition:'root',action:'install'}});
      receiveNative({kind:'check',checkId:'packages',status:'pass',label:'Packages',detail:'',statusText:'pass'});
      receiveNative({kind:'check',checkId:'home-button',status:'unknown',label:'Home button',detail:'Not tested',statusText:'unknown'});
      receiveNative({kind:'recovery-plan',state:'complete',disposition:'home-off',summary:'Root setup finished with LG Home and Home control off.',nextStep:'Keep LG Home active.'});
      receiveNative({kind:'finished',code:0});
    });
    assert.equal(await page.locator('h1').innerText(),'Root setup finished with LG Home and Home control off.');
    assert.equal(await page.locator('.review-symbol').count(),0);
    assert((await page.locator('.tv-checks').innerText()).includes('Not tested'));
    await page.close();
  }
  for (const [locale,dictionary] of Object.entries(words)) {
    const page=await browser.newPage({locale,viewport:{width:320,height:667}});
    await page.addInitScript(()=>{
      window.answers=[];
      window.CYTV={hasKey:()=>false,snapshot:()=> '[]',answer:raw=>answers.push(JSON.parse(raw))};
    });
    await page.goto('file://'+path.join(ui,'index.html'));
    for(const homeStatus of ['unknown','fail','pass']){
      await page.evaluate(homeStatus=>{
        receiveNative({kind:'started',config:{host:'192.0.2.10',edition:'no-root',action:'install'}});
        receiveNative({kind:'check',checkId:'ssh',status:'pass',label:'ssh',detail:'',statusText:'pass',title:'TV checks'});
        for(const [checkId,status] of [['packages','pass'],['startup','pass'],['home-button',homeStatus]])
          receiveNative({kind:'check',checkId,status,label:checkId,detail:'',statusText:status,title:'TV checks'});
        receiveNative({kind:'report-ready',name:'diagnostic-123456abcdef.json'});
        receiveNative({kind:'finished',code:0});
      },homeStatus);
      assert.equal(await page.locator('h1').innerText(),dictionary[homeStatus==='pass'?'homeObserved':'tvChecksReview']);
      assert.equal(await page.locator('.review-symbol').count(),homeStatus==='pass'?0:1);
      assert((await page.locator('.tv-checks li').first().innerText()).includes('packages'));
      assert.equal(await page.locator('[data-action=save-report]').count(),1);
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),locale+' result overflow');
    }
    await page.evaluate(()=>receiveNative({kind:'question',id:'home-test',context:'Physical Home check',
      options:[{value:'1',label:'Home opened'},{value:'2',label:'Home did not work'},{value:'3',label:'Not tested'}],defaultChoice:'3'}));
    await page.waitForFunction(()=>document.activeElement?.dataset.value==='3');
    assert.equal(await page.locator('[data-action=confirm]').count(),0);
    await page.keyboard.press('Enter');
    assert.equal(await page.evaluate(()=>answers.at(-1).value),'3');
    await page.evaluate(()=>{
      receiveNative({kind:'started',config:{host:'192.0.2.11',edition:'root',action:'status'}});
      receiveNative({kind:'finished',code:0});
    });
    assert.equal(await page.locator('h1').innerText(),dictionary.statusDone);
    assert.equal(await page.locator('.tv-checks').count(),0);
    await page.close();
  }
  const {execFileSync}=require('node:child_process');
  const guides=JSON.parse(execFileSync(process.env.CYTV_PYTHON||'python3',['-c',`
import json
from cytv import i18n
from cytv.failure_help import GUIDES
result={}
for language in i18n.LANGUAGES:
 if language=='auto':continue
 i18n.set_language(language);result[language]={}
 for code,(title,detail,next_step,edit) in GUIDES.items():
  result[language][code]={'kind':'failure-help','code':code,'title':i18n.translate(title),'detail':i18n.translate(detail),'nextStep':i18n.translate(next_step),'canEditConnection':edit,'pending':code=='pending-operation'}
print(json.dumps(result))
`],{cwd:path.resolve(__dirname,'../..'),encoding:'utf8'}));
  for(const [locale,dictionary] of Object.entries(words)){
    const page=await browser.newPage({locale,viewport:{width:320,height:740}});
    await page.addInitScript(()=>{
      window.requests=[];
      window.CYTV={hasKey:()=>false,snapshot:()=> '[]',answer:()=>{},saveReport:()=>requests.push('save'),start:c=>requests.push(JSON.parse(c))};
    });
    await page.goto('file://'+path.join(ui,'index.html'));
    for(const code of ['ssh-unreachable','ssh-identity','developer-key-unlock','root-home-interfaces','pending-operation','recovery-status-rejected','removal-not-submitted']){
      const guide=guides[locale][code];const edition=code.startsWith('developer-')?'no-root':'root';
      await page.evaluate(({guide,edition})=>{
        receiveNative({kind:'started',config:{host:'192.0.2.10',port:2222,edition,action:'install'}});
        receiveNative({kind:'check',checkId:'ssh',status:'pass',label:'SSH',detail:'',statusText:'pass',title:'TV checks'});
        if(guide.code==='root-home-interfaces')receiveNative({kind:'check',checkId:'home-profiles',status:'fail',label:'Home profiles',detail:'',statusText:'fail',title:'TV checks'});
        receiveNative(guide);
        receiveNative({kind:'report-ready',name:'diagnostic-123456abcdef.json'});
        receiveNative({kind:'finished',code:2});
      },{guide,edition});
      assert.equal(await page.locator('h1').innerText(),guide.title);
      assert.equal(await page.locator('[role=note]').innerText(),guide.nextStep);
      assert.equal(await page.locator('[data-action=status]').count(),0);
      assert.equal(await page.locator('[data-action=restore]').count(),0);
      assert.equal(await page.locator('[data-action=to-connection]').count(),guide.canEditConnection?1:0);
      assert.equal(await page.evaluate(()=>requests.length),0,'Advice must not invoke operations');
      if(code==='root-home-interfaces')assert((await page.locator('.tv-checks li').first().innerText()).includes('Home profiles'));
      for(const [width,height] of [[320,740],[740,375]]){
        await page.setViewportSize({width,height});
        assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),locale+'/'+code+' overflow');
      }
      await page.setViewportSize({width:320,height:740});
      if(guide.canEditConnection){
        await page.locator('[data-action=to-connection]').click();
        assert.equal(await page.locator('#port').inputValue(),'2222');
      }
    }
    await page.evaluate(()=>{
      receiveNative({kind:'started',config:{host:'192.0.2.11',edition:'root',action:'status'}});
      receiveNative({kind:'finished',code:0});
    });
    assert.equal(await page.locator('h1').innerText(),dictionary.statusDone);
    assert.equal(await page.locator('[role=note]').count(),0);
    await page.close();
  }
  await browser.close();
  console.log('PASS Android maintenance: thirteen locales, correct commands, connection flow, progress, replay, readable text and responsive widths');
})().catch(async error=>{console.error(error);if(browser)await browser.close();process.exitCode=1});
