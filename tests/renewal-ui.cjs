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
      window.helperStopped = false;
      window.helperStarting = false;
      window.helperStatusAvailable = true;
      window.helperStopLatched = true;
      window.homeChoice = null;
      window.homeBusyReplies = 0;
      // Older Helpers omit keepSource; set a boolean to emulate support.
      window.keepSourceChoice = undefined;
      window.homeBrokerFailure = null;
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
            } else if (uri === 'luna://com.local.nativehome.service/status') {
              if (!helperStatusAvailable)
                r = { returnValue: false, errorCode: -1 };
              else {
                r.blocked = helperStopped && helperStopLatched;
                r.running = !helperStopped;
              }
            } else if (
              uri === 'luna://com.webos.applicationManager/launch' &&
              p.id === 'com.local.nativehome' &&
              p.params?.nativeHomeStart &&
              p.params.nativeHomePanel
            ) {
              helperStarting = true;
              setTimeout(() => {
                helperStopped = false;
                helperStarting = false;
              }, 1750);
            } else if (uri === 'luna://com.gathin.tvhome.renewal/homeStatus') {
              if (homeBusyReplies > 0) {
                homeBusyReplies--;
                r.returnValue = false;
                r.diagnostic = {
                  component: 'home',
                  operation: 'wait',
                  code: 'BUSY'
                };
              } else if (helperStopped) {
                r.returnValue = false;
                if (homeBrokerFailure) r.diagnostic = homeBrokerFailure;
              } else {
                r.enabled =
                  homeChoice ??
                  calls.some((call) => call.p.id === 'com.local.nativehome');
                if (keepSourceChoice !== undefined)
                  r.keepSource = keepSourceChoice;
              }
            } else if (
              uri === 'luna://com.gathin.tvhome.renewal/setHomeControl'
            ) {
              homeChoice = p.enabled;
              r.enabled = homeChoice;
            } else if (
              uri === 'luna://com.gathin.tvhome.renewal/setKeepSource'
            ) {
              keepSourceChoice = p.enabled;
              r.enabled = homeChoice;
              r.keepSource = keepSourceChoice;
            } else if (
              uri === 'luna://com.gathin.tvhome.renewal/screensaverStatus'
            ) {
              if (helperStopped) r.returnValue = false;
              else
                Object.assign(r, {
                  available: true,
                  state: { enabled: false }
                });
            } else if (uri.startsWith('luna://com.gathin.tvhome.renewal/')) {
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
    for (const category of ['home', 'screensaver']) {
      await page.evaluate(() => {
        helperStopped = true;
      });
      await page.locator('#btnSettings').click();
      await page.locator('[data-category=' + category + ']').click();
      const pane = page.locator('#settings-pane-' + category);
      await pane
        .getByText('Home Helper is stopped.', { exact: false })
        .waitFor({
          timeout: 5000
        });
      assert.equal(
        await page.evaluate(() => helperStopped && !helperStarting),
        true
      );
      await pane.getByRole('button', { name: 'Start Helper' }).click();
      await page
        .locator('#homeConfirmation')
        .getByRole('button', { name: 'Start Helper' })
        .click();
      await page.waitForFunction(() => !helperStopped);
      await page.waitForFunction(() => {
        const toggle = document.querySelector('#homeRoutingToggle');
        return (
          toggle.getAttribute('data-home-state') === 'known' &&
          toggle.getAttribute('aria-checked') === 'true'
        );
      });
      if (category === 'home')
        await page.locator('[data-category=screensaver]').click();
      await page.waitForFunction(
        () => !document.getElementById('screensaverEnabled').disabled
      );
      await page.reload();
      await page.locator('#tiles .item').first().waitFor();
    }
    for (const category of ['home', 'screensaver']) {
      // C3 after Restore: the broker rejects both requests and the native
      // Helper status endpoint replies with an error instead of a stop flag.
      await page.evaluate(() => {
        helperStopped = true;
        helperStatusAvailable = false;
      });
      await page.locator('#btnSettings').click();
      await page.locator('[data-category=' + category + ']').click();
      const pane = page.locator('#settings-pane-' + category);
      await pane
        .getByText(
          category === 'home'
            ? 'Could not check which screen the Home button opens.'
            : 'Could not check screensaver availability.'
        )
        .waitFor({ timeout: 6000 });
      const start = pane.getByRole('button', { name: 'Start Helper' });
      await start.waitFor({ timeout: 3000 });
      assert(await pane.getByRole('button', { name: 'Try again' }).isVisible());
      if (category === 'screensaver')
        assert(await pane.locator('#screensaverEnabled').isHidden());

      assert(!(await pane.getByText('Home Helper is stopped.').isVisible()));
      assert(await page.evaluate(() => !helperStarting && helperStopped));
      await start.click();
      const dialog = page.locator('#homeConfirmation');
      await dialog.getByRole('button', { name: 'Cancel' }).click();
      assert(await page.evaluate(() => !helperStarting && helperStopped));
      await start.click();
      await dialog.getByRole('button', { name: 'Start Helper' }).click();
      await page.waitForFunction(() => !helperStopped);
      await page.waitForFunction(() => {
        const toggle = document.querySelector('#homeRoutingToggle');
        return (
          toggle.getAttribute('data-home-state') === 'known' &&
          toggle.getAttribute('aria-checked') === 'true'
        );
      });
      if (category === 'home')
        await page.locator('[data-category=screensaver]').click();
      await page.waitForFunction(
        () => !document.getElementById('screensaverEnabled').disabled
      );
      assert(await start.isHidden());
      await page.reload();
      await page.locator('#tiles .item').first().waitFor();
    }
    // A concurrent screensaver query can briefly own the Home broker.
    await page.evaluate(() => {
      homeChoice = true;
      homeBusyReplies = 1;
    });
    await page.locator('#btnSettings').click();
    await page.locator('[data-category=home]').click();
    await page
      .locator('#homeRoutingToggle[role=switch][aria-checked=true]')
      .waitFor({ timeout: 3500 });
    assert(await page.locator('#homeRoutingStart').isHidden());
    assert(await page.evaluate(() => !helperStarting && !helperStopped));
    await page.locator('#renewalClose').click();
    // A broker without its Helper must permit explicit recovery of the saved Off state.
    await page.evaluate(() => {
      homeChoice = false;
      helperStopped = true;
      helperStopLatched = false;
      homeBrokerFailure = {
        component: 'home',
        operation: 'wait',
        code: 'BUSY'
      };
    });
    await page.locator('#btnSettings').click();
    await page.locator('[data-category=home]').click();
    const homePane = page.locator('#settings-pane-home');
    const retryHome = homePane.getByRole('button', { name: 'Try again' });
    const startHelper = homePane.getByRole('button', { name: 'Start Helper' });
    const homeSwitch = homePane.locator('#homeRoutingToggle');
    await retryHome.waitFor();
    assert(await startHelper.isHidden());
    await page.evaluate(() => {
      homeBrokerFailure.code = 'TIMEOUT';
    });
    await retryHome.click();
    await startHelper.waitFor({ timeout: 3000 });
    assert(await homeSwitch.isDisabled());
    assert(await page.evaluate(() => !helperStarting && helperStopped));
    await startHelper.click();
    await page
      .locator('#homeConfirmation')
      .getByRole('button', { name: 'Start Helper' })
      .click();
    await homePane
      .locator('#homeRoutingToggle[role=switch][aria-checked=false]')
      .waitFor();
    await homeSwitch.click();
    await homePane
      .locator('#homeRoutingToggle[role=switch][aria-checked=true]')
      .waitFor();
    // Stay on HDMI or Live TV when the TV wakes stays hidden for a Helper that omits it.
    assert(await homePane.locator('#homeKeepSource').isHidden());
    assert(await homePane.locator('#homeKeepSourceHint').isHidden());
    // Reopening settings refreshes Home status from a Helper that reports it.
    await page.evaluate(() => {
      keepSourceChoice = false;
    });
    await page.locator('#renewalClose').click();
    await page.locator('#renewalPanel').waitFor({ state: 'hidden' });
    await page.locator('#btnSettings').click();
    await page.locator('[data-category=home]').click();
    const keepSwitch = homePane.getByRole('switch', {
      name: 'Stay on HDMI or Live TV when the TV wakes'
    });
    await homePane
      .locator('#homeKeepSource[role=switch][aria-checked=false]')
      .waitFor();
    assert(await homePane.locator('#homeKeepSourceHint').isVisible());
    assert.equal(
      await homePane.locator('#homeKeepSourceHint').textContent(),
      'If your TV wakes from standby already showing a game console, Live TV, or another input, that screen stays open. The Home button works as usual.'
    );
    await keepSwitch.focus();
    await page.keyboard.press('Enter');
    await homePane
      .locator('#homeKeepSource[role=switch][aria-checked=true]')
      .waitFor();
    assert.equal(
      await page.evaluate(() => document.activeElement.id),
      'homeKeepSource'
    );
    assert.deepEqual(
      await page.evaluate(() =>
        calls
          .filter(
            (c) => c.uri === 'luna://com.gathin.tvhome.renewal/setKeepSource'
          )
          .map((c) => c.p)
      ),
      [{ enabled: true }]
    );
    assert.equal(await page.evaluate(() => keepSourceChoice), true);
    assert.equal(
      await homeSwitch.getAttribute('aria-checked'),
      'true',
      'Stay on HDMI or Live TV when the TV wakes does not change Home routing'
    );
    await homeSwitch.click();
    await homePane.locator('#homeRoutingToggle[aria-checked=false]').waitFor();
    assert(
      await keepSwitch.isEnabled(),
      'Change Home leaves the input switch usable'
    );
    assert.equal(await keepSwitch.getAttribute('aria-checked'), 'true');
    await keepSwitch.click();
    await homePane.locator('#homeKeepSource[aria-checked=false]').waitFor();
    assert.equal(await page.evaluate(() => keepSourceChoice), false);
    await page.evaluate(() => {
      keepSourceChoice = undefined;
    });
    await page.locator('#renewalClose').click();
    await page.locator('#btnSettings').click();
    await page.locator('[data-category=home]').click();
    await homePane.locator('#homeRoutingToggle[role=switch]').waitFor();
    assert(await homePane.locator('#homeKeepSource').isHidden());
    assert(await homePane.locator('#homeKeepSourceHint').isHidden());
    await page.reload();
    await page.locator('#tiles .item').first().waitFor();
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
      .filter({ hasText: 'Auto-renewal enabled' })
      .waitFor();
    assert.doesNotMatch(
      await page.locator('#developerSettings').innerText(),
      /\bBeta\b/i
    );

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
      'PASS renewal UI, updates, navigation and Developer Mode visibility by installation method'
    );
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
