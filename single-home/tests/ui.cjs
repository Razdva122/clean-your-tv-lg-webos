'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const app = path.resolve(__dirname, '../app');
const service = 'luna://io.github.razdva122.cytvhomepilot.service/';
const origin = 'http://home.test';
const setup = origin + '/setup/index.html';
const home = origin + '/index.html';

(async () => {
  const browser = await chromium.launch({
    channel: process.env.BROWSER_CHANNEL || 'chrome'
  });
  try {
    const page = await browser.newPage({
      viewport: { width: 1920, height: 1080 },
      locale: 'ru-RU'
    });
    page.setDefaultTimeout(4500);
    const errors = [];
    page.on('pageerror', (e) => errors.push(e.message));
    await page.addInitScript(
      ({ service }) => {
        const read = (key, fallback) =>
          JSON.parse(sessionStorage.getItem(key) || JSON.stringify(fallback));
        const fixture = read('fixture', {
          storageReady: true,
          credentialsReady: true,
          paired: false,
          pairing: false,
          startup: 'off',
          bootObserved: false
        });
        window.patchState = (patch) => {
          Object.assign(fixture, patch);
          sessionStorage.setItem('fixture', JSON.stringify(fixture));
        };
        window.PalmServiceBridge = function () {
          this.cancel = () => {};
          this.call = (uri, raw) => {
            const method = uri.slice(service.length);
            if (!uri.startsWith(service)) throw Error('Unexpected URI ' + uri);
            const calls = read('calls', []);
            calls.push({ method, args: JSON.parse(raw) });
            sessionStorage.setItem('calls', JSON.stringify(calls));
            const reply = (value) =>
              this.onservicecallback(JSON.stringify(value));
            if (method === 'status' || method === 'probe')
              return reply({ returnValue: true, ...fixture });
            if (method === 'pair') {
              if (window.denyPair)
                return reply({
                  returnValue: false,
                  errorCode: 'pairing-declined',
                  errorText: 'private detail'
                });
              if (window.holdPair) {
                window.latePair = () =>
                  reply({ returnValue: true, paired: true });
                return;
              }
              if (!fixture.paired && fixture.startup === 'off')
                window.patchState({
                  startup: 'pending',
                  startupNeedsRetry: !!window.failStartup
                });
              window.patchState({ paired: true });
              return reply({
                returnValue: true,
                paired: true,
                startupNeedsRetry: fixture.startupNeedsRetry
              });
            }
            if (method === 'enable') {
              window.patchState({
                startup: 'pending',
                startupNeedsRetry: false
              });
              if (window.holdEnable) {
                window.lateEnable = () =>
                  reply({ returnValue: true, startup: 'pending' });
                return;
              }
            } else if (method === 'disable')
              window.patchState({ startup: 'stopped' });
            else if (method !== 'cancelPair')
              throw Error('Unexpected method ' + method);
            reply({ returnValue: true });
          };
        };
      },
      { service }
    );
    function serve(route) {
      const pathname = new URL(route.request().url()).pathname;
      if (pathname === '/index.html')
        return route.fulfill({
          contentType: 'text/html',
          body: '<title>Product Home fixture</title>'
        });
      const match =
        /^\/setup\/(index\.html|app\.js|style\.css|icon\.png)$/.exec(pathname);
      if (!match) return route.fulfill({ status: 404 });
      return route.fulfill({ path: path.join(app, match[1]) });
    }
    await page.route(origin + '/**', serve);
    const el = (id) => page.locator('#' + id);
    const calls = (method) =>
      page.evaluate(
        (m) =>
          JSON.parse(sessionStorage.getItem('calls')).filter(
            (c) => c.method === m
          ),
        method
      );
    await page.goto(setup);
    await el('pair').waitFor();
    assert.equal(
      await el('pair').evaluate((b) => b === document.activeElement),
      true
    );
    assert.match(await el('pair').textContent(), /телевизор|сопряж/i);
    assert.equal(await page.locator('#appGrid, #editLayout').count(), 0);
    assert.equal(await el('startupArea').isVisible(), false);
    assert.match(await el('pairStatus').textContent(), /при включении ТВ/);
    const preview = process.env.PILOT_PREVIEW_DIR;
    if (preview) {
      fs.mkdirSync(preview, { recursive: true });
      await page.screenshot({ path: path.join(preview, 'first-run.png') });
    }
    await page.evaluate(() =>
      localStorage.setItem('pilot.home.layout.v1', '[]')
    );
    await page.keyboard.press('ArrowRight');
    assert.equal(
      await el('later').evaluate((b) => b === document.activeElement),
      true
    );
    await page.keyboard.press('Enter');
    await page.waitForURL((url) => url.pathname === '/index.html');
    assert.equal(
      await page.evaluate(() => sessionStorage.getItem('cytv.home.skipSetup')),
      '1'
    );
    assert.equal((await calls('pair')).length, 0);

    await page.goto(setup);
    await page.evaluate(() => (window.denyPair = true));
    await page.keyboard.press('Enter');
    await el('retry').waitFor();
    assert.match(await el('notice').textContent(), /отклонил/);
    assert.doesNotMatch(await el('notice').textContent(), /private detail/);
    await page.evaluate(() => {
      window.denyPair = false;
      window.holdPair = true;
    });
    await page.keyboard.press('Enter');
    await el('cancelPair').waitFor();
    await page.keyboard.press('Escape');
    await page.evaluate(() => {
      window.holdPair = false;
      window.latePair();
    });
    assert.equal(page.url(), setup);
    await el('pair').click();
    await page.waitForURL(home);
    assert.equal((await calls('enable')).length, 0);
    assert.equal(
      await page.evaluate(() => localStorage.getItem('pilot.home.layout.v1')),
      '[]'
    );

    await page.goto(setup + '?settings=1&reason=saved-pairing-rejected');
    await el('pairAgain').waitFor();
    assert.match(await el('notice').textContent(), /сопряжение/);
    await page.keyboard.press('Escape');
    await page.waitForURL(home + '?skipSetup=1');
    assert.equal((await calls('pair')).length, 3);
    await page.goto(setup + '?settings=1&reason=saved-pairing-rejected');
    await el('pairAgain').click();
    await page.waitForURL(home);
    await page.goto(setup + '?settings=1');
    await el('pairAgain').waitFor();
    assert.deepEqual(
      (await calls('pair')).map((c) => c.args),
      Array(4).fill({ confirm: true })
    );
    assert.match(await el('startupStatus').textContent(), /подтверждения/);
    await el('stop').click();
    await el('pairAgain').click();
    await page.waitForURL(home);
    await page.goto(setup + '?settings=1');
    assert.match(await el('startupStatus').textContent(), /останов/i);
    await page.evaluate(() => (window.holdEnable = true));
    await el('enableStartup').click();
    assert(await el('stop').isVisible());
    await el('stop').click();
    await page.evaluate(() => window.lateEnable());
    assert.match(await el('startupStatus').textContent(), /останов/i);
    await page.reload();
    assert.match(await el('startupStatus').textContent(), /останов/i);
    assert.deepEqual(
      (await calls('enable')).map((c) => c.args),
      [{ confirm: true }]
    );
    assert.equal((await calls('disable')).length, 2);
    if (preview)
      await page.screenshot({ path: path.join(preview, 'settings.png') });
    await page.keyboard.press('Escape');
    await page.waitForURL(home);
    await page.goto(setup);
    await page.waitForURL(home);

    await page.evaluate(() => window.patchState({ credentialsReady: false }));
    await page.goto(setup);
    await el('probe').waitFor();
    assert.equal(
      page.url(),
      setup,
      'unusable saved pairing does not bounce between Home and setup'
    );
    await page.evaluate(() => window.patchState({ paired: false }));
    await page.goto(setup + '?settings=1');
    assert(await el('pair').isDisabled());
    await el('probe').click();
    assert.equal((await calls('pair')).length, 5);
    assert(await el('enableStartup').isEnabled());
    await el('enableStartup').click();
    await el('stop').click();
    assert.equal((await calls('disable')).length, 3);
    await el('back').click();
    await page.waitForURL((url) => url.pathname === '/index.html');
    assert.equal((await calls('catalog')).length, 0);
    await page.evaluate(() =>
      window.patchState({
        startup: 'off',
        paired: false,
        credentialsReady: true
      })
    );
    await page.goto(setup);
    await page.evaluate(() => {
      window.failStartup = true;
    });
    await el('pair').click();
    await el('enableStartup').waitFor();
    assert.match(await el('startupStatus').textContent(), /ещё раз/);
    await el('enableStartup').click();
    assert.match(await el('startupStatus').textContent(), /подтверждения/);
    assert.equal((await calls('pair')).length, 6);
    const offlinePage = await browser.newPage({ locale: 'en-US' });
    offlinePage.setDefaultTimeout(4500);
    offlinePage.on('pageerror', (e) => errors.push(e.message));
    await offlinePage.route(origin + '/**', serve);
    await offlinePage.goto(setup);
    assert.equal(
      await offlinePage.locator('#pair').textContent(),
      'Pair with this TV'
    );
    assert(await offlinePage.locator('#pair').isDisabled());
    assert.match(
      await offlinePage.locator('#notice').textContent(),
      /service did not respond/
    );
    assert.equal(
      await offlinePage
        .locator('#probe')
        .evaluate((b) => b === document.activeElement),
      true
    );
    await offlinePage.locator('#later').click();
    await offlinePage.waitForURL(home + '?skipSetup=1');
    assert.deepEqual(errors, []);
    console.log(
      'PASS single Home setup navigation, LG refusal and cancellation, explicit repair, first-pair startup and persistent Stop, private-storage gate and preserved layout'
    );
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
