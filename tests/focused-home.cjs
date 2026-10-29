const assert = require('node:assert/strict');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {chromium} = require('playwright');

(async () => {
  const browser = await chromium.launch({headless: true, channel: process.env.BROWSER_CHANNEL || 'chrome'});
  try {
    for (const homeApps of [['input.xbox', 'input.apple', 'input.xbox', 'missing'], []]) {
      const page = await browser.newPage({viewport: {width: 1920, height: 1080}});
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.addInitScript(() => {
        window.launches = [];
        localStorage.setItem('tvhome.layout', JSON.stringify({version: 1,
          ids: ['other', 'input.apple'], hidden: ['input.xbox'], catalog: []}));
        window.PalmServiceBridge = function () {
          this.cancel = function () {};
          this.call = function (uri, raw) {
            if (uri === 'luna://com.webos.applicationManager/launch') window.launches.push(JSON.parse(raw).id);
            setTimeout(() => this.onservicecallback(JSON.stringify({returnValue: false,
              errorText: 'Service does not exist: com.cleanyourtv.system.updater.service'})), 0);
          };
        };
      });
      await page.route('**/config.js', route => route.fulfill({body: 'window.CONFIG=' +
        JSON.stringify({columns: 7, homeApps, dockApps: [], hiddenApps: []}) + ';'}));
      await page.route('**/apps.js', route => route.fulfill({body: 'window.TV_APPS=' + JSON.stringify({
        apps: [{id: 'input.apple', title: 'Apple TV'}, {id: 'input.xbox', title: 'Xbox'},
          {id: 'other', title: 'Other'}].map(app => ({...app, icon: 'brand-v2-icon.png'})), inputs: []
      }) + ';'}));
      await page.goto(pathToFileURL(path.resolve('launcher/index.html')).href);
      await page.waitForFunction(() => document.body.classList.contains('minimal-home'));
      await page.waitForTimeout(700);
      assert.equal(await page.locator('.add-app').count(), 0);
      assert.equal(await page.locator('#hero').isVisible(), false);
      const ids = await page.locator('#tiles .item').evaluateAll(items => items.map(el => el.dataset.appId));
      assert.deepEqual(ids, homeApps.length ? ['input.xbox', 'input.apple'] : []);
      if (homeApps.length) {
        const band = await page.locator('#dockBand').boundingBox();
        assert(Math.abs(band.x + band.width / 2 - 960) < 1, 'two-card dock is centered');
        await page.keyboard.press('Enter');
        await page.keyboard.press('ArrowRight');
        await page.keyboard.press('Enter');
        assert.deepEqual(await page.evaluate(() => launches), ['input.xbox', 'input.apple']);
        await page.keyboard.down('Enter');
        await page.waitForTimeout(700);
        await page.keyboard.up('Enter');
        assert.equal(await page.locator('body.editing').count(), 0);
        await page.keyboard.press('ArrowUp');
        assert.equal(await page.locator('#topButtons .focused').count(), 1);
      } else {
        assert.equal(await page.locator('#btnInputs.focused').count(), 1);
        await page.evaluate(() => document.dispatchEvent(new Event('webOSRelaunch')));
        assert.equal(await page.locator('#btnInputs.focused').count(), 1);
      }
      const saved = await page.evaluate(() => JSON.parse(localStorage.getItem('tvhome.layout')));
      assert.deepEqual(saved.ids, ['other', 'input.apple']);
      assert.deepEqual(saved.hidden, ['input.xbox']);
      assert.deepEqual(errors, []);
      await page.close();
    }
    console.log('PASS focused Home: exact selection, preserved layout, centered dock, launch, navigation and empty recovery');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
