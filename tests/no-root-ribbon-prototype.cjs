// The compiled standalone app must dismiss once, preserve navigation and fail opaque.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {chromium} = require('playwright');

(async () => {
  const entry = path.resolve('build/no-root-ribbon-prototype/app/index.html');
  assert.ok(fs.existsSync(entry), 'Build the standalone prototype before testing it');
  const browser = await chromium.launch({headless: true, channel: process.env.BROWSER_CHANNEL || 'chrome'});
  let count = 0;
  try {
    async function open(params, system = 'PalmSystem') {
      const page = await browser.newPage({viewport: {width: 1920, height: 1080}});
      await page.clock.install();
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.addInitScript(({params, system}) => {
        window.probeCloses = 0;
        window.probeActivations = 0;
        window.close = function () { window.probeCloses++; };
        window[system] = {launchParams: params, activate: function () { window.probeActivations++; }};
      }, {params, system});
      await page.goto(pathToFileURL(entry).href);
      await page.locator('#ribbon button').first().waitFor();
      return {page, errors};
    }
    async function check(params, run, system) {
      const {page, errors} = await open(params, system);
      try { await run(page); assert.deepEqual(errors, []); count++; }
      finally { await page.close(); }
    }
    await check('{}', async page => {
      assert.equal(await page.locator('body').getAttribute('data-mode'), 'full');
      await page.keyboard.press('ArrowRight');
      assert.equal(await page.locator(':focus').textContent(), 'Fullscreen');
      await page.keyboard.press('ArrowRight');
      await page.keyboard.press('ArrowRight');
      assert.equal(await page.locator(':focus').textContent(), 'Overlay');
      await page.keyboard.press('Enter');
      assert.equal(await page.locator('body').getAttribute('data-mode'), 'overlay');
      assert.equal(await page.locator('body').evaluate(el => getComputedStyle(el).backgroundColor), 'rgba(0, 0, 0, 0)');
      const box = await page.locator('#ribbon').boundingBox();
      assert.ok(box.y > 700 && box.y + box.height <= 1080, 'Ribbon stays within the bottom safe area');
    });
    for (const params of ['not-json', 'null', '[]', '{"mode":"unexpected"}']) {
      await check(params, async page => {
        assert.equal(await page.locator('body').getAttribute('data-mode'), 'full');
      });
    }
    await check('{"mode":"overlay"}', async page => {
      await page.evaluate(() => {
        document.dispatchEvent(new KeyboardEvent('keydown', {keyCode: 461, bubbles: true}));
        document.dispatchEvent(new Event('webOSRelaunch'));
      });
      assert.equal(await page.evaluate(() => probeCloses), 1);
      await page.clock.fastForward(60000);
      assert.equal(await page.evaluate(() => probeCloses), 1);
      assert.equal(await page.locator('#ribbon').isVisible(), false);
    });
    await check({mode: 'overlay'}, async page => {
      await page.evaluate(() => document.dispatchEvent(new Event('webOSRelaunch')));
      assert.equal(await page.evaluate(() => probeCloses), 1, 'An explicit repeated launch dismisses');
    }, 'webOSSystem');
    await check('{}', async page => {
      await page.clock.fastForward(59999);
      assert.equal(await page.evaluate(() => probeCloses), 0);
      await page.clock.fastForward(1);
      assert.equal(await page.evaluate(() => probeCloses), 1, 'The absolute lifetime is bounded');
    });
    await check('{}', async page => {
      await page.keyboard.press('Escape');
      assert.equal(await page.evaluate(() => probeCloses), 1);
    });
    await check('{}', async page => {
      await page.getByRole('button', {name: 'Close panel'}).click();
      assert.equal(await page.evaluate(() => probeCloses), 1);
    });
    await check('{"mode":"overlay"}', async page => {
      await page.getByRole('button', {name: 'Fullscreen', exact: true}).click();
      assert.equal(await page.locator('body').getAttribute('data-mode'), 'full');
      assert.equal(await page.evaluate(() => probeActivations), 1);
    });
    console.log('PASS standalone compiled Ribbon:', count, 'browser scenarios (platform calls simulated; no TV evidence)');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
