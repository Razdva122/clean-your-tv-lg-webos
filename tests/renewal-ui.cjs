// Start scripts/preview.py first; PREVIEW_URL overrides its default port 8876.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const versions = require('../release-versions.json');
const base = process.env.PREVIEW_URL || 'http://127.0.0.1:8876';
(async () => {
  const browser = await chromium.launch({
    headless: true,
    channel: process.env.BROWSER_CHANNEL || 'chrome'
  });
  const page = await browser.newPage({
    viewport: { width: 1920, height: 1080 },
    locale: 'en'
  });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  try {
    await page.addInitScript((versions) => {
      window.calls = [];
      window.renewEnabled = false;
      window.PalmServiceBridge = function () {
        this.cancel = () => clearTimeout(this.timer);
        this.call = (uri, data) => {
          const p = JSON.parse(data);
          calls.push({ uri, p });
          this.timer = setTimeout(() => {
            let r = { returnValue: true };
            if (
              uri.startsWith('luna://com.cleanyourtv.system.updater.service/')
            ) {
              const method = uri.split('/').pop();
              r.result = null;
              if (method === 'check')
                r.result = {
                  edition: p.edition,
                  release: 'v' + versions.release,
                  components: ['home', 'helper', 'updater'].map((name) => ({
                    name,
                    installed: versions[name],
                    version: versions[name]
                  })),
                  canInstall: false,
                  reason: 'current',
                  notes: ''
                };
            } else if (uri === 'luna://com.gathin.tvhome.renewal/homeStatus')
              r.enabled = false;
            else if (uri.startsWith('luna://com.gathin.tvhome.renewal/')) {
              if (uri.endsWith('/enable')) renewEnabled = true;
              if (uri.endsWith('/disable')) renewEnabled = false;
              r.state = {
                enabled: renewEnabled,
                last: renewEnabled
                  ? {
                      status: 'healthy',
                      checkedAt: Date.now(),
                      remainingSeconds: 3240000
                    }
                  : null
              };
            } else if (uri.endsWith('registerServerStatus')) r.connected = true;
            this.onservicecallback(JSON.stringify(r));
          }, 10);
        };
      };
    }, versions);
    // The preview supplies HTML/assets; this test supplies its own bus replies.
    await page.route('**/preview/bridge.js', (r) => r.fulfill({ body: '' }));
    let connection;
    await page.route('**/apps.js', (r) =>
      r.fulfill({
        body:
          'window.TV_APPS={apps:[{id:"test.app",title:"Test App",icon:"brand-v2-icon.png"}],inputs:[]};' +
          (connection
            ? `window.CYTVNoRootConnection = ${JSON.stringify(connection)};`
            : '')
      })
    );
    await page.goto(base + '/launcher/index.html');
    await page.locator('#tiles .item').first().waitFor();
    assert.equal(
      await page.evaluate(
        () =>
          calls.filter(
            (c) => c.uri === 'luna://com.gathin.tvhome.renewal/status'
          ).length
      ),
      0
    );
    await page.locator('#btnSettings').click();
    await page.locator('[data-category=developer]').click();
    await page
      .locator('#renewalSummary')
      .filter({ hasText: 'Auto-renewal off' })
      .waitFor();
    await page.locator('#developerOpen').click();
    await page.keyboard.press('ArrowRight');
    assert.equal(
      await page.evaluate(() => document.activeElement.id),
      'renewalDiagnostics'
    );
    await page.keyboard.press('ArrowLeft');
    assert.equal(
      await page.evaluate(() => document.activeElement.id),
      'renewalToggle'
    );
    await page.keyboard.press('Enter');
    await page
      .locator('#renewalStatus')
      .filter({ hasText: 'Auto-renewal enabled (Beta)' })
      .waitFor();

    await page.locator('#renewalDiagnostics').click();
    assert.equal(
      await page.locator('#renewalDiagnostics').getAttribute('aria-expanded'),
      'true'
    );
    assert(
      !(await page.locator('#renewalDetails').innerText()).includes(
        'sessionToken'
      )
    );
    await page.locator('#renewalToggle').click();
    await page
      .locator('#renewalStatus')
      .filter({ hasText: 'Auto-renewal off' })
      .waitFor();
    await page.locator('#developerBack').click();
    await page.locator('[data-category=updates]').click();
    await page.locator('#renewalUpdates').click();
    await page.locator('#systemUpdates').waitFor({ state: 'visible' });
    await page.locator('#systemUpdateCheck').waitFor();
    await page.waitForFunction(
      () => !document.getElementById('systemUpdateCheck').disabled
    );
    await page
      .locator('#systemUpdateStatus')
      .filter({ hasText: 'All components are up to date.' })
      .waitFor();
    assert(await page.locator('#systemUpdateInstall').isDisabled());
    assert(!(await page.locator('#homeConfirmation').isVisible()));
    await page.keyboard.press('Escape');
    await page.locator('#renewalPanel').waitFor({ state: 'visible' });
    assert.equal(
      await page.evaluate(() => document.activeElement.id),
      'renewalUpdates'
    );
    await page.keyboard.press('ArrowLeft');
    await page.keyboard.press('ArrowDown');
    await page.keyboard.press('ArrowRight');
    assert.equal(
      await page.evaluate(() => document.activeElement.id),
      'renewalTV'
    );
    await page.keyboard.press('Escape');
    await page.keyboard.press('Escape');
    await page.locator('#renewalPanel').waitFor({ state: 'hidden' });
    await page.keyboard.press('ArrowDown');
    await page.keyboard.press('Enter');
    assert(await page.evaluate(() => calls.some((c) => c.p.id === 'test.app')));
    assert(
      !(await page.evaluate(() =>
        calls.some((c) => /\/(install|rollback)$/.test(c.uri))
      )),
      'viewing updates must not request an installation or rollback'
    );

    // A root SSH install hides the tab, including after a generic Home update.
    for (const mode of ['root-ssh', undefined]) {
      connection = mode;
      await page.reload();
      await page.locator('#btnSettings').click();
      await page.locator('[data-category=advanced]').focus();
      await page.keyboard.press('ArrowDown');
      assert.equal(await page.locator('[data-category=developer]').count(), 0);
      assert.equal(await page.locator('#developerOpen').isVisible(), false);
      assert.equal(
        await page.evaluate(() => document.activeElement.id),
        'renewalClose'
      );
      assert.equal(
        await page.evaluate(() =>
          calls.some((c) => c.uri === 'luna://com.gathin.tvhome.renewal/status')
        ),
        false
      );
    }

    connection = 'developer-mode';
    await page.reload();
    await page.locator('#btnSettings').click();
    await page.locator('[data-category=developer]').waitFor();
    assert.deepEqual(errors, []);
    console.log(
      'PASS Beta UI, updates, navigation and Developer Mode visibility by installation method'
    );
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
