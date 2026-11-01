const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');

let browser;
(async () => {
  browser = await chromium.launch({headless: true, executablePath: process.env.CYTV_CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
  const page = await browser.newPage({locale:'ru-RU',viewport:{width:412,height:892},deviceScaleFactor:2});
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(() => {
    window.requests = [];
    window.CYTV = {snapshot:()=> '[]', hasKey:()=>false, inspect:config=>receiveNative({kind:'inspection',host:JSON.parse(config).host,root_ssh:false,developer_ssh:true,root_port:22}),
      start:config=>window.requests.push(JSON.parse(config)),
      answer:value=>window.requests.push(JSON.parse(value)), importKey:()=>{}};
  });
  await page.goto('file://' + path.resolve(__dirname,'../app/src/main/assets/ui/index.html'));
  assert.equal(await page.getByRole('img',{name:'Clean Your TV'}).count(),1);
  assert.equal(await page.getByText('Рекомендуем',{exact:true}).count(),0);
  assert.equal(await page.getByRole('radio').count(),0);
  await page.getByRole('button',{name:'Проверить подключение',exact:true}).click();
  assert.equal(await page.locator('#host').getAttribute('aria-invalid'),'true');
  await page.locator('#host').fill('192.168.1.999');
  await page.getByRole('button',{name:'Проверить подключение',exact:true}).click();
  assert.equal((await page.evaluate(()=>window.requests)).length,0);
  await page.locator('#host').fill('192.168.1.50');
  await page.getByRole('button',{name:'Проверить подключение',exact:true}).click();
  await page.getByRole('button',{name:'Продолжить',exact:true}).click();
  await page.getByRole('button',{name:'Проверить и установить',exact:true}).click();
  assert.equal((await page.evaluate(()=>window.requests))[0].edition,'no-root');
  await page.evaluate(()=>receiveNative({kind:'started',config:{host:'192.168.1.50',edition:'no-root',action:'install'}}));
  await page.evaluate(()=>receiveNative({kind:'trust',id:'test-trust',fingerprint:'SHA256:example',root:false}));
  await page.getByRole('button',{name:'Доверять и продолжить',exact:true}).click();
  assert.equal((await page.evaluate(()=>window.requests)).at(-1).value,'yes');
  await page.evaluate(()=>receiveNative({kind:'secret',id:'test-secret',text:'Developer Mode passphrase:'}));
  await page.locator('#prompt-value').fill('SECRET-TEST');
  await page.getByRole('button',{name:'Продолжить',exact:true}).click();
  assert.equal(await page.locator('body').innerText().then(t=>t.includes('SECRET-TEST')),false);
  await page.evaluate(()=>{
    receiveNative({kind:'error',text:'Correctable input error',fatal:false});
    receiveNative({kind:'finished',code:0});
  });
  assert.equal(await page.locator('.error-result').count(),0,'corrected input does not turn success into failure');
  await page.evaluate(()=>receiveNative({kind:'started',config:{host:'192.168.1.50',edition:'no-root',action:'install'}}));
  await page.evaluate(()=>receiveNative({kind:'error',text:'Helper <failure>'}));
  assert.equal(await page.locator('#log-text .error-text').textContent(),'Ошибка: Helper <failure>');
  assert.equal(await page.locator('#log-text .error-text').evaluate(el=>getComputedStyle(el).color),'rgb(255, 107, 107)');
  assert.equal(await page.locator('#live-caption').evaluate(el=>getComputedStyle(el).color),'rgb(255, 107, 107)');
  const requestsBeforeFailure = (await page.evaluate(()=>window.requests)).length;
  await page.evaluate(()=>receiveNative({kind:'finished',code:2}));
  assert.equal(await page.locator('.error-summary').isVisible(),true,'failure details are visible without opening the log');
  assert.equal(await page.locator('.error-result h1').evaluate(el=>getComputedStyle(el).color),'rgb(255, 107, 107)');
  assert.equal(await page.locator('[data-action="status"], [data-action="restore"]').count(),0,'unknown failure must not offer blind Status/Restore');
  assert.equal(await page.locator('.bottom [data-action="home"]').count(),1,'failure can be left without starting another operation');
  assert.equal((await page.evaluate(()=>window.requests)).length,requestsBeforeFailure,'displaying failure does not retry or run maintenance');
  await page.getByRole('button',{name:'Вернуться к подключению',exact:true}).click();
  assert.equal(await page.locator('#host').inputValue(),'192.168.1.50');
  assert.equal(await page.locator('#port').inputValue(),'9922');
  await page.getByRole('button',{name:'Назад',exact:true}).click();
  await page.getByRole('radio',{name:/Root Уже есть root/}).click();
  await page.getByRole('button',{name:'Продолжить',exact:true}).click();
  assert.equal(await page.locator('#port').inputValue(),'22');
  await page.getByRole('button',{name:'SSH-ключ',exact:true}).click();
  await page.getByRole('button',{name:'Проверить и установить',exact:true}).click();
  assert.equal(await page.locator('#key-error').isVisible(),true);
  await page.locator('#host').fill('192.168.1.88');
  await page.locator('#port').fill('2222');
  await page.getByRole('button',{name:'Выбрать файл ключа',exact:true}).click();
  await page.evaluate(()=>receiveNative({kind:'key-imported'}));
  assert.equal(await page.locator('#host').inputValue(),'192.168.1.88');
  assert.equal(await page.locator('#port').inputValue(),'2222');
  for (const width of [320,375,412,768,1024]) {
    await page.setViewportSize({width,height:892});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth),true,`overflow at ${width}`);
  }
  assert.deepEqual(errors,[]);
  console.log('Android UI: validation, both editions, explicit trust, secret separation, recovery and responsive widths passed.');
  await browser.close();
})().catch(async e=>{console.error(e);if(browser)await browser.close();process.exitCode=1});
