const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const vm = require('node:vm');
const root = path.resolve(__dirname, '../..');
const ui = path.join(root, 'android/app/src/main/assets/ui');
const { words } = vm.runInNewContext(
  fs.readFileSync(path.join(ui, 'translations.js'), 'utf8') + ';({words})'
);
const events = JSON.parse(
  execFileSync(
    process.env.CYTV_PYTHON || 'python3',
    [
      '-c',
      `
import json
from cytv import i18n
from android.tests.test_bridge import BridgeTests
bridge=BridgeTests().module()
class Native:
 def __init__(self):self.events=[]
 def emit(self,raw):self.events.append(json.loads(raw))
result={}
for lang in i18n.LANGUAGES:
 if lang=='auto':continue
 i18n.set_language(lang);result[lang]={}
 for reason in ('restart-required','connection-interrupted','root-worker-busy','root-access-required'):
  native=Native();console=bridge.AndroidConsole(bridge.Callbacks(native))
  console.recovery_plan({'state':'waiting','disposition':'clean-removal','summary':'Removal is not finished yet.','next_step':'Try again',
   'removed':False,'verified_clean':False,'restart_required':reason=='restart-required','actions':['continue-removal'],
   'removal':{'stage':'restart-required' if reason=='restart-required' else 'package-removal','reason':reason}})
  result[lang][reason]=native.events[-1]
print(json.dumps(result))
`
    ],
    { cwd: root, encoding: 'utf8' }
  )
);
let browser;
(async () => {
  browser = await chromium.launch({
    headless: true,
    executablePath:
      process.env.CYTV_CHROME ||
      '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
  });
  const page = await browser.newPage({
    locale: 'en',
    viewport: { width: 320, height: 740 }
  });
  await page.addInitScript(() => {
    window.requests = [];
    window.CYTV = {
      snapshot: () => '[]',
      hasKey: () => false,
      answer: () => {},
      start: (raw) => requests.push(JSON.parse(raw))
    };
  });
  await page.goto('file://' + path.join(ui, 'index.html'));
  for (const [language, cases] of Object.entries(events)) {
    await page.evaluate(
      (language) => localStorage.setItem('cytv-language', language),
      language
    );
    await page.reload();
    for (const [reason, event] of Object.entries(cases))
      for (const edition of ['root', 'no-root']) {
        const target = {
          host: '192.0.2.10',
          edition,
          port: edition === 'root' ? 2222 : 9923,
          action: 'uninstall',
          language
        };
        await page.evaluate(
          ({ target, event, reason }) => {
            receiveNative({ kind: 'started', config: target });
            receiveNative(event);
            receiveNative({
              kind: 'finished',
              code: reason === 'connection-interrupted' ? 1 : 0
            });
          },
          { target, event, reason }
        );
        assert.equal(
          await page.locator('.review-symbol').count(),
          1,
          language + '/' + reason
        );
        assert.equal(await page.locator('[data-action=recover]').count(), 0);
        assert.equal(
          await page.locator('[data-action=retry-removal]').innerText(),
          words[language].tryAgain
        );
        assert(
          (await page.locator('.recovery-info').innerText()).includes(
            event.blockerText
          )
        );
        if (reason === 'restart-required')
          assert.equal(
            await page.locator('h1').innerText(),
            words[language].restartRemoval
          );
        if (reason === 'connection-interrupted') {
          assert.equal(
            await page.locator('[data-action=to-connection]').count(),
            1
          );
          await page.locator('[data-action=to-connection]').click();
          assert.equal(
            await page.locator('#host').getAttribute('readonly'),
            ''
          );
          assert.equal(
            await page.locator('#port').getAttribute('readonly'),
            ''
          );
          await page.evaluate(() => goBack());
          assert.equal(
            await page.locator('[data-action=retry-removal]').count(),
            1
          );
          await page.locator('[data-action=to-connection]').click();
          assert.equal(
            await page.locator('#host').getAttribute('readonly'),
            ''
          );
          await page.evaluate(() => {
            document.getElementById('host').value = '192.0.2.99';
            document.getElementById('port').value = '1234';
          });
          await page.locator('[data-action=start]').click();
          await page.evaluate(() => goBack());
          assert.equal(await page.locator('.progress-line').count(), 1);
        } else await page.locator('[data-action=retry-removal]').click();
        const request = await page.evaluate(() => requests.at(-1));
        for (const key of ['host', 'edition', 'port', 'action', 'language'])
          assert.equal(request[key], target[key], key);
        assert.equal(
          await page.locator('dialog[open]').count(),
          0,
          'Retry does not add a UI confirmation'
        );
        assert(
          await page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth
          ),
          language + ' overflow'
        );
      }
  }
  for (const removed of [undefined, false, true]) {
    await page.evaluate((removed) => {
      receiveNative({
        kind: 'started',
        config: { host: '192.0.2.10', edition: 'root', action: 'uninstall' }
      });
      receiveNative({
        kind: 'recovery-plan',
        state: 'complete',
        disposition: 'clean-removal',
        removed,
        verified_clean: true,
        summary: 'Verified final cleanup',
        nextStep: 'Other TV apps stay installed.'
      });
      receiveNative({ kind: 'finished', code: 0 });
    }, removed);
    assert.equal(
      await page.locator('.review-symbol').count(),
      removed === true ? 0 : 1,
      'both final booleans required'
    );
  }
  await page.evaluate(() => {
    receiveNative({
      kind: 'started',
      config: { host: '192.0.2.10', edition: 'root', action: 'uninstall' }
    });
    receiveNative({
      kind: 'recovery-plan',
      state: 'complete',
      disposition: 'clean-removal',
      removed: true,
      verified_clean: true,
      restart_required: true,
      summary: 'Stale completion flags',
      nextStep: 'Try again'
    });
    receiveNative({ kind: 'finished', code: 0 });
  });
  assert.equal(
    await page.locator('.review-symbol').count(),
    1,
    'restart-required overrides stale true flags'
  );
  await browser.close();
  console.log(
    'PASS simple Android removal: 13 locales, both editions, full restart/connection/busy/access instructions, direct same-goal retry and both final proof flags'
  );
})().catch(async (error) => {
  console.error(error);
  if (browser) await browser.close();
  process.exitCode = 1;
});
