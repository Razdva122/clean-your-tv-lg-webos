// Actual launcher/Settings/Root exit with synthetic LS2; no TV acceptance.
const { chromium } = require('playwright'),
  assert = require('node:assert/strict');
const base = process.env.PREVIEW_URL || 'http://127.0.0.1:8879';
(async () => {
  const browser = await chromium.launch({
    headless: true,
    channel: process.env.BROWSER_CHANNEL || 'chrome'
  });
  try {
    const page = await browser.newPage({ locale: 'en' }),
      errors = [];
    page.on('pageerror', (e) => errors.push(e.message));
    await page.goto(base + '/root-launcher/index.html');
    await page.locator('#tiles .add-app').waitFor();
    await page.evaluate(() => {
      window.exitCloseCalls = 0;
      window.close = function () {
        window.exitCloseCalls++;
      };
      const Original = window.PalmServiceBridge;
      window.settingsBackend = {
        phase: 'active',
        calls: [],
        pending: [],
        contextCalls: 0,
        delay: false,
        fail: false
      };
      window.PalmServiceBridge = function () {
        const original = new Original();
        this.cancel = () => original.cancel();
        this.call = (uri, raw) => {
          const b = settingsBackend,
            method = uri.split('/').pop(),
            payload = JSON.parse(raw);
          if (
            uri === 'luna://com.webos.applicationManager/launch' &&
            payload.id === 'com.webos.app.home' &&
            b.delayLG
          ) {
            b.launchPending = b.launchPending || [];
            b.launchPending.push(() =>
              this.onservicecallback(JSON.stringify({ returnValue: true }))
            );
            return;
          }
          if (
            !uri.startsWith('luna://com.cleanyourtv.root.preview.service/') ||
            !['status', 'restore', 'enable'].includes(method)
          ) {
            original.onservicecallback = (value) =>
              this.onservicecallback(value);
            original.call(uri, raw);
            return;
          }
          // Presentation is a separate read-only status operation, not a routing
          // refresh. Keep the routing single-flight/stale-response queue independent.
          if (
            method === 'status' &&
            Object.keys(payload).length === 1 &&
            payload.presentation === 'context'
          ) {
            b.contextCalls++;
            this.onservicecallback(
              JSON.stringify({ returnValue: true, result: { content: false } })
            );
            return;
          }
          if (payload.startup) {
            const send = (result) =>
              this.onservicecallback(
                JSON.stringify({
                  returnValue: true,
                  result: { returnValue: true, result }
                })
              );
            if (payload.startup === 'configure') b.sources = payload.sources;
            send({
              sources: b.sources || { tv: true, youtube: false },
              active: b.phase === 'active'
            });
            return;
          }
          b.calls.push(method);
          const send = (result) =>
            this.onservicecallback(
              JSON.stringify({
                returnValue: true,
                result: { returnValue: true, result }
              })
            );
          if (method === 'status') {
            const answer = () =>
              b.fail
                ? this.onservicecallback(JSON.stringify({ returnValue: false }))
                : send({
                    intent: { phase: b.phase },
                    effective: {
                      sam_home: 'com.webos.app.home',
                      profiles: {
                        defaultApps: {
                          categories: { home: 'com.webos.app.home' }
                        },
                        idleApp: { appId: 'com.webos.app.home' }
                      }
                    }
                  });
            if (b.delay) b.pending.push(answer);
            else answer();
          } else if (method === 'enable') {
            b.phase = 'active';
            send({});
          } else {
            b.phase = 'disabled';
            send('restored');
          }
        };
      };
    });
    await page.locator('#btnSettings').click();
    const toggle = page.locator('.root-settings .home-routing-switch').first();
    await page.waitForFunction(
      () =>
        document
          .querySelector('.root-settings [role=switch]')
          .getAttribute('aria-checked') === 'true'
    );
    assert.equal(
      await page.evaluate(() => document.activeElement.id),
      'settings-tab-home',
      'status must preserve category navigation focus'
    );
    // A backend transition completes while Settings stays open, without writes.
    await page.evaluate(() => {
      settingsBackend.phase = 'enabling';
      document.dispatchEvent(new Event('webOSRelaunch'));
    });
    await page.waitForFunction(
      () =>
        document.querySelector('.settings-status').textContent ===
        'Changing Home control…'
    );
    assert(await toggle.isDisabled());
    await page.evaluate(() => (settingsBackend.phase = 'active'));
    await page.waitForFunction(
      () => !document.querySelector('.root-settings [role=switch]').disabled
    );
    assert.equal(await toggle.getAttribute('aria-checked'), 'true');
    assert.deepEqual(
      await page.evaluate(() =>
        settingsBackend.calls.filter((m) => m !== 'status')
      ),
      [],
      'status convergence never enables or restores Home'
    );
    await page.evaluate(() => {
      settingsBackend.fail = true;
      document.dispatchEvent(new Event('webOSRelaunch'));
    });
    const retry = page.getByRole('button', {
      name: 'Check status',
      exact: true
    });
    await retry.waitFor();
    await retry.focus();
    await page.evaluate(() => (settingsBackend.fail = false));
    await page.keyboard.press('Enter');
    await page.waitForFunction(
      () => !document.querySelector('.root-settings [role=switch]').disabled
    );
    assert.equal(
      await page.evaluate(() => document.activeElement.textContent),
      'Open LG Home',
      'retry keeps usable focus while its button disappears'
    );
    await page.evaluate(() => {
      settingsBackend.phase = 'disabled';
      settingsBackend.delay = true;
      Object.defineProperty(document, 'hidden', {
        configurable: true,
        value: true
      });
      document.dispatchEvent(new Event('visibilitychange'));
      Object.defineProperty(document, 'hidden', {
        configurable: true,
        value: false
      });
      document.dispatchEvent(new Event('visibilitychange'));
    });
    await page.waitForFunction(() => settingsBackend.pending.length === 1);
    assert.equal(
      await page.evaluate(() => settingsBackend.contextCalls),
      0,
      'persistent CARD Home does not query transient overlay context'
    );
    await page.evaluate(() =>
      document.dispatchEvent(new Event('webOSRelaunch'))
    );
    assert.equal(
      await page.evaluate(() => settingsBackend.pending.length),
      1,
      'relaunch waits for the active status request'
    );
    assert(await toggle.isDisabled());
    await page.evaluate(() =>
      document.querySelector('.root-settings [role=switch]').click()
    );
    assert.deepEqual(
      await page.evaluate(() =>
        settingsBackend.calls.filter((m) => m !== 'status')
      ),
      []
    );
    await page.evaluate(() => settingsBackend.pending.shift()());
    await page.waitForFunction(() => settingsBackend.pending.length === 1);
    assert(
      await toggle.isDisabled(),
      'stale completion cannot unlock Home before the queued refresh'
    );
    await page.evaluate(() => {
      settingsBackend.pending.shift()();
      settingsBackend.delay = false;
    });
    await page.waitForFunction(
      () => !document.querySelector('.root-settings [role=switch]').disabled
    );
    assert.equal(await toggle.getAttribute('aria-checked'), 'false');
    const sources = page.locator('.startup-source-actions button');
    assert.equal(await sources.count(), 2);
    assert.deepEqual(await sources.allTextContents(), [
      'LG Channels / Live TV',
      'YouTube'
    ]);
    assert(await sources.nth(0).isDisabled());
    assert.equal(await sources.nth(0).getAttribute('aria-checked'), 'true');
    const sourceLayout = await page.evaluate(() => ({
      hint: document.querySelector('#rootStartupHint').getBoundingClientRect()
        .bottom,
      content: document
        .querySelector('.settings-content')
        .getBoundingClientRect().bottom
    }));
    assert(
      sourceLayout.hint <= sourceLayout.content,
      'all source controls and the Off explanation fit in the TV reading area'
    );
    await toggle.focus();
    await page.keyboard.press('ArrowDown');
    assert.equal(
      await page.evaluate(() => document.activeElement.textContent),
      'Open LG Home'
    );
    await toggle.click();
    await page.waitForFunction(
      () =>
        document
          .querySelector('.root-settings [role=switch]')
          .getAttribute('aria-checked') === 'true'
    );
    assert.deepEqual(
      await page.evaluate(() =>
        settingsBackend.calls.filter((m) => m !== 'status')
      ),
      ['enable']
    );
    await sources.nth(1).click();
    await page.waitForFunction(
      () =>
        document
          .querySelectorAll('.startup-source-actions button')[1]
          .getAttribute('aria-checked') === 'true'
    );
    assert.deepEqual(await page.evaluate(() => settingsBackend.sources), {
      tv: true,
      youtube: true
    });
    await page.waitForFunction(
      () => !document.querySelector('.root-settings [role=switch]').disabled
    );
    await toggle.click();
    await page.waitForFunction(
      () =>
        document
          .querySelector('.root-settings [role=switch]')
          .getAttribute('aria-checked') === 'false'
    );
    assert.deepEqual(
      await page.evaluate(() =>
        settingsBackend.calls.filter((m) => m !== 'status')
      ),
      ['enable', 'restore']
    );
    assert.equal(
      await page.evaluate(() => settingsBackend.pending.length),
      0,
      'every serialized request completed'
    );
    assert.equal(await toggle.getAttribute('aria-checked'), 'false');
    assert.equal(
      await page.evaluate(() => exitCloseCalls),
      1,
      'explicit Off closes only its Root overlay after verified restore and accepted LG Home launch'
    );
    await toggle.click();
    await page.waitForFunction(
      () =>
        document
          .querySelector('.root-settings [role=switch]')
          .getAttribute('aria-checked') === 'true'
    );
    await page.evaluate(() => (settingsBackend.delayLG = true));
    await page
      .getByRole('button', { name: 'Open LG Home', exact: true })
      .click();
    await page.waitForFunction(
      () =>
        settingsBackend.launchPending &&
        settingsBackend.launchPending.length === 1
    );
    await page.evaluate(() => {
      Object.defineProperty(document, 'hidden', {
        configurable: true,
        value: true
      });
      document.dispatchEvent(new Event('visibilitychange'));
      settingsBackend.launchPending.shift()();
    });
    await page.waitForFunction(() => exitCloseCalls === 2);
    assert.equal(
      await page.evaluate(() => settingsBackend.phase),
      'active',
      'temporary LG Home keeps routing preference'
    );
    await page.evaluate(() => {
      Object.defineProperty(document, 'hidden', {
        configurable: true,
        value: false
      });
      document.dispatchEvent(new Event('visibilitychange'));
      document.dispatchEvent(new Event('webOSRelaunch'));
    });
    await page.locator('#btnSettings').click();
    await page.waitForFunction(
      () => !document.querySelector('.root-settings [role=switch]').disabled
    );
    await page
      .getByRole('button', { name: 'Open LG Home', exact: true })
      .click();
    await page.waitForFunction(
      () => settingsBackend.launchPending.length === 1
    );
    await page.evaluate(() => {
      Object.defineProperty(document, 'hidden', {
        configurable: true,
        value: true
      });
      document.dispatchEvent(new Event('visibilitychange'));
      Object.defineProperty(document, 'hidden', {
        configurable: true,
        value: false
      });
      document.dispatchEvent(new Event('visibilitychange'));
      document.dispatchEvent(new Event('webOSRelaunch'));
      settingsBackend.launchPending.shift()();
    });
    await page.waitForFunction(
      () => document.querySelector('.root-settings').hidden
    );
    assert.equal(
      await page.evaluate(() => exitCloseCalls),
      2,
      'late LG reply cannot close a newly shown/relaunched Root window'
    );
    assert.deepEqual(errors, []);
    console.log(
      'PASS actual Root launcher/Settings/exit: emergency resume, relaunch, delayed status, explicit enable and Off'
    );
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
