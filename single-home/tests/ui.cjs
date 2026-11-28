'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright');
const app = path.resolve(__dirname, '../app');
const service = 'luna://io.github.razdva122.cytvhomepilot.service/';
const entry = path.join(app, 'index.html');
assert.ok(fs.existsSync(entry), 'the Home tile opens its own first-run screen');
(async () => {
  const browser = await chromium.launch({
    channel: process.env.BROWSER_CHANNEL || 'chrome'
  });
  try {
    const page = await browser.newPage({
      viewport: { width: 1920, height: 1080 },
      locale: 'ru-RU'
    });
    const errors = [];
    page.on('pageerror', (e) => errors.push(e.message));
    await page.addInitScript(
      ({ service }) => {
        window.requests = [];
        window.fixture = JSON.parse(
          sessionStorage.getItem('fixture') ||
            '{"storageReady":true,"credentialsReady":true,"paired":false,"pairing":false,"startup":"off","bootObserved":false}'
        );
        window.persist = () =>
          sessionStorage.setItem('fixture', JSON.stringify(fixture));
        window.PalmServiceBridge = function () {
          this.cancel = () => {};
          this.call = (uri, raw) => {
            const args = JSON.parse(raw);
            requests.push({ uri, args });
            if (uri === 'luna://com.webos.applicationManager/launch') {
              this.onservicecallback('{"returnValue":true}');
              return;
            }
            if (!uri.startsWith(service)) throw Error('Unexpected RPC');
            const method = uri.slice(service.length);
            let reply = { returnValue: true };
            if (method === 'status' || method === 'probe')
              Object.assign(reply, fixture);
            else if (method === 'pair') {
              if (window.holdPair) {
                window.completePair = () =>
                  this.onservicecallback('{"returnValue":true,"paired":true}');
                return;
              }
              if (window.denyPair)
                reply = {
                  returnValue: false,
                  errorCode: 'pairing-declined',
                  errorText: 'sensitive test detail'
                };
              else {
                fixture.paired = true;
                reply.paired = true;
              }
            } else if (method === 'catalog') {
              if (window.failCatalog)
                reply = { returnValue: false, errorCode: window.failCatalog };
              else
                reply.apps = [
                  { id: 'sample.video', title: 'Кино' },
                  { id: 'sample.music', title: 'Музыка' }
                ];
            } else if (method === 'enable') {
              fixture.startup = 'pending';
              reply.startup = 'pending';
              if (window.holdEnable) {
                window.completeEnable = () =>
                  this.onservicecallback(JSON.stringify(reply));
                return;
              }
            } else if (method === 'disable') {
              fixture.startup = 'stopped';
              reply.startup = 'stopped';
            } else if (method !== 'cancelPair')
              throw Error('Unexpected method');
            persist();
            this.onservicecallback(JSON.stringify(reply));
          };
        };
      },
      { service }
    );
    await page.goto(pathToFileURL(entry).href);
    const el = (id) => page.locator('#' + id);
    const rpcCount = (method) =>
      page.evaluate(
        ([u, m]) => requests.filter((c) => c.uri === u + m).length,
        [service, method]
      );
    await el('pair').waitFor();
    assert.equal(await rpcCount('pair'), 0);
    assert.match(await el('pair').textContent(), /телевизор|сопряж/i);
    const preview = process.env.PILOT_PREVIEW_DIR;
    if (preview) {
      fs.mkdirSync(preview, { recursive: true });
      await page.screenshot({ path: path.join(preview, 'first-run.png') });
    }
    await el('later').click();
    assert.equal(await rpcCount('pair'), 0);
    await el('settings').click();
    await el('pair').waitFor();
    await page.evaluate(() => (window.denyPair = true));
    await el('pair').focus();
    await page.keyboard.press('Enter');
    await el('retry').waitFor();
    assert.equal(await rpcCount('enable'), 0);
    assert(
      !(await page
        .locator('body')
        .textContent()
        .then((x) => x.includes('sensitive test detail')))
    );
    await page.evaluate(() => {
      window.denyPair = false;
      window.holdPair = true;
    });
    await page.keyboard.press('Enter');
    await el('cancelPair').click();
    await page.evaluate(() => {
      window.holdPair = false;
      window.completePair();
    });
    assert.equal(await rpcCount('enable'), 0);
    await el('pair').click();
    const tiles = page.locator('#appGrid button[data-app-id]');
    await tiles.first().waitFor();
    assert.equal(await tiles.count(), 2);
    if (preview)
      await page.screenshot({ path: path.join(preview, 'grid.png') });
    await tiles.first().focus();
    await page.keyboard.press('ArrowRight');
    await page.keyboard.press('Enter');
    assert.equal(
      await page.evaluate(
        () =>
          requests.filter(
            (c) => c.uri === 'luna://com.webos.applicationManager/launch'
          ).length
      ),
      1
    );
    await el('editLayout').click();
    await tiles.first().click();
    await tiles.first().click();
    assert.equal(await tiles.count(), 0);
    await page.reload();
    await el('settings').waitFor();
    assert.equal(
      await tiles.count(),
      0,
      'preserve deliberately empty layout on relaunch'
    );
    await el('settings').click();
    await el('restoreApps').click();
    await tiles.first().waitFor();
    assert.equal(await tiles.count(), 2);
    await el('settings').click();
    await page.evaluate(() => (window.holdEnable = true));
    await el('enableStartup').click();
    assert.equal(await rpcCount('enable'), 1);
    assert(
      await el('stop').isVisible(),
      'Stop is available before enable acknowledges'
    );
    await el('stop').click();
    await page.evaluate(() => window.completeEnable());
    assert.match(await el('startupStatus').textContent(), /останов/i);
    assert.equal(await rpcCount('disable'), 1);
    await page.reload();
    await el('settings').click();
    assert.match(await el('startupStatus').textContent(), /останов/i);
    assert.equal(
      await rpcCount('enable'),
      0,
      'opening the tile cannot clear Stop'
    );
    await page.evaluate(() => {
      fixture.credentialsReady = false;
      fixture.paired = false;
      persist();
    });
    await page.reload();
    await el('settings').click();
    assert(await el('pair').isDisabled());
    await el('probe').click();
    assert.equal(await rpcCount('pair'), 0);
    assert(
      await el('enableStartup').isEnabled(),
      'background service may be explicitly tested before TV pairing'
    );
    assert.equal(await rpcCount('enable'), 0);
    await el('enableStartup').click();
    assert.equal(await rpcCount('enable'), 1);
    assert.equal(await rpcCount('pair'), 0);
    await el('stop').click();
    assert.equal(await rpcCount('disable'), 1);
    assert.deepEqual(errors, []);
    console.log(
      'PASS first run, native refusal, cancellation, private-storage gate, daily grid, D-pad, saved empty layout, explicit restore, separate startup consent and Stop'
    );
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
