// Exercise the settings entry, actual grid reflow, persistence and remote focus.
const {assert, chromium, stage, open} = require('./browser.cjs');
(async () => {
  const site = stage(), browser = await chromium.launch({headless: true, channel: process.env.BROWSER_CHANNEL || 'chrome'});
  try {
    for (const edition of ['launcher', 'root-launcher']) {
      const {page, errors} = await open(browser, site, edition);
      try {
        const ids = await page.locator('#tiles [data-app-id]').evaluateAll(items => items.map(el => el.dataset.appId));
        // Real settings callbacks may finish after a child dialog opens.
        await page.evaluate(() => {
          const Bridge = window.PalmServiceBridge;
          window.pendingColumnStatus = [];
          window.PalmServiceBridge = function () {
            const bridge = new Bridge();
            this.cancel = () => bridge.cancel();
            this.call = (uri, payload) => {
              bridge.onservicecallback = raw => {
                const reply = () => this.onservicecallback(raw);
                if (uri === 'luna://com.cleanyourtv.root.preview.service/status' ||
                    uri === 'luna://com.gathin.tvhome.renewal/homeStatus') window.pendingColumnStatus.push(reply);
                else reply();
              };
              bridge.call(uri, payload);
            };
          };
        });
        await page.locator('#btnSettings').click();await page.locator('[data-category=appearance]').click();
        assert.equal(await page.locator('#homeColumns').innerText(), 'Columns: 5', 'entry shows the effective count before opening');
        await page.locator('#homeColumns').click();
        await page.keyboard.press('ArrowRight');
        await page.keyboard.press('Tab');
        await page.keyboard.press('Shift+Tab');
        await page.waitForFunction(() => window.pendingColumnStatus.length > 0);
        await page.evaluate(() => window.pendingColumnStatus.splice(0).forEach(reply => reply()));
        assert.equal(await page.locator('[data-columns="1"]').evaluate(el => el === document.activeElement), true,
          'late settings status must preserve focus inside Columns');
        await page.keyboard.press('Enter');
        assert.equal(await page.locator('#tiles .dock').count(), 1, 'remote selection still works after late settings status');
        await page.evaluate(() => HomeI18n.confirm({title: 'Test confirmation', message: 'Synthetic nested dialog.', action: 'Continue'}, function () {}));
        assert.equal(await page.locator('#homeConfirmation').evaluate(el => el.contains(document.activeElement)), true,
          'Columns must defer focus to a higher-priority confirmation');
        await page.keyboard.press('Escape');
        assert.equal(await page.locator('[data-columns="1"]').evaluate(el => el === document.activeElement), true,
          'closing a nested confirmation restores the Columns choice');
        for (const count of [8, 1, 4, 5]) {
          await page.locator('[data-columns="' + count + '"]').click();
          assert.equal(await page.locator('#tiles .dock').count(), count);
          assert.equal(await page.locator('#homeColumns').innerText(), 'Columns: '+count);
          assert.deepEqual(await page.locator('#tiles [data-app-id]').evaluateAll(items => items.map(el => el.dataset.appId)), ids);
        }
        await page.locator('[data-columns="8"]').click();
        await page.evaluate(() => HomeLayoutState.setThemeColumns(3));
        assert.equal(await page.locator('#tiles .dock').count(), 8, 'user overrides theme');
        await page.locator('[data-columns="auto"]').click();
        assert.equal(await page.locator('#tiles .dock').count(), 3, 'By theme uses author default');
        await page.keyboard.press('ArrowRight');
        await page.keyboard.press('Enter');
        assert.equal(await page.locator('#tiles .dock').count(), 1, 'remote picks next option');
        await page.keyboard.press('Escape');
        assert.equal(await page.locator('#homeColumns').evaluate(el => el === document.activeElement), true);
        await page.keyboard.press('Escape');
        await page.keyboard.press('Escape');
        // A theme can lock columns while a choice dialog is open.
        await page.locator('#btnSettings').click();await page.locator('[data-category=appearance]').click();
        await page.locator('#homeColumns').click();
        await page.evaluate(()=>HomeLayoutState.setThemeLayout({preset:'scenic-grid',columns:8,allowColumnOverride:false,spacingScale:1,textScale:1,focusScale:1.1}));
        assert.equal(await page.locator('#homeLayoutPanel').isVisible(),false,'locking closes the open Columns dialog');
        assert.equal(await page.locator('#homeColumns').isVisible(),false,'fixed theme hides Columns');
        await page.evaluate(()=>HomeLayoutPanel.open());
        assert.equal(await page.locator('#homeLayoutPanel').isVisible(),false,'direct open cannot bypass lock');
        assert.equal(await page.evaluate(()=>HomeLayoutState.state().columns),8);
        await page.evaluate(()=>ThemeRuntime.reset());
        assert.equal(await page.locator('#homeColumns').isVisible(),true,'Classic restores the option');
        assert.equal(await page.evaluate(()=>HomeLayoutState.state().columns),1,'previous choice survives locked theme');
        await page.keyboard.press('Escape');
        await page.reload();
        await page.locator('#tiles .focused').waitFor();
        assert.equal(await page.locator('#tiles .dock').count(), 1, 'choice persists after reload');
        assert.deepEqual(errors, []);
        console.log('PASS on-TV columns settings, live reflow and reload: ' + edition);
      } finally {await page.close();}
    }
  } finally {await browser.close();}
})().catch(error => {console.error(error); process.exitCode = 1;});
