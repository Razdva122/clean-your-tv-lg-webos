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
    for (const action of ['status', 'restore', 'home-diagnostics', 'recover']) {
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
      assert.equal(await page.locator('h1').innerText(), dictionary[action==='recover'?'recoveryReview':action==='home-diagnostics'?'homeDiagnostics':action==='status'?'statusTool':'restore']);
      await page.locator('#host').fill('192.168.1.50');
      await page.locator('[data-action=inspect]').click();
      assert.equal(await page.locator('.steps').count(), 0);
      assert.equal(await page.locator('h1').innerText(), dictionary.connectionMethod);
      await page.locator('[data-action=back]').click();
      assert.equal(await page.locator('h1').innerText(), dictionary[action==='recover'?'recoveryReview':action==='home-diagnostics'?'homeDiagnostics':action==='status'?'statusTool':'restore']);
      assert.equal(await page.locator('#host').inputValue(), '192.168.1.50');
      await page.locator('[data-action=inspect]').click();
      await page.locator('[data-action=connect]').click();
      assert.equal(await page.locator('h1').innerText(), dictionary[action==='recover'?'recoveryReview':action==='home-diagnostics'?'homeDiagnostics':action==='status'?'statusTool':'restore']);
      assert(!(await page.locator('body').innerText()).includes(dictionary.reviewFoot));
      await page.locator('[data-action=start]').click();
      assert.equal(await page.evaluate(()=>requests.at(-1).action), action);
      assert.equal(await page.locator('.task-list').count(), 0);
      assert.equal(await page.locator('.progress-copy p').innerText(), dictionary[action==='home-diagnostics'?'diagnosticProgress':'maintenanceProgress']);
      assert.equal(await page.locator('#live-caption').innerText(), dictionary.awaiting);
      const expectedTitle = dictionary[action==='recover'?'recoveryReview':action==='home-diagnostics'?'homeDiagnostics':action==='status'?'statusTitle':'restoreTitle'].replace('<br>', '\n');
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
    for (const action of ['status', 'restore', 'home-diagnostics', 'recover']) {
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
  for (const state of ['review', 'ready', 'blocked', 'complete']) {
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
    assert.equal(await page.locator('.recovery-info').innerText(),'Сохраните отчёт');
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.evaluate(()=>receiveNative({kind:'question',text:'Проверить? [y/N]',defaultNo:true,context:'Отдельное подтверждение'}));
    await page.waitForFunction(()=>document.activeElement?.dataset.action==='cancel-prompt');
    assert.equal(await page.locator('[data-action=confirm]').count(),1);
    await page.close();
  }
  await browser.close();
  console.log('PASS Android maintenance: twelve locales, correct commands, connection flow, progress, replay, readable text and responsive widths');
})().catch(async error=>{console.error(error);if(browser)await browser.close();process.exitCode=1});
