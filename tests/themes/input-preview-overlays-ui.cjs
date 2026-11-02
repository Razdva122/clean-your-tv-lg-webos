// Input media must yield to every owned dialog, including relaunch-driven Helper.
const {assert, chromium, stage, open: openBase} = require('./browser.cjs');
async function open(...args) { const result = await openBase(...args); await result.page.evaluate(() => HomeLayoutState.setThemeLayout({preset:'dock-grid', columns:5, spacingScale:1, textScale:1, focusScale:1.1, inputs:'shelf'})); return result; }
(async () => {
  const site = stage(), browser = await chromium.launch({headless: true, channel: process.env.BROWSER_CHANNEL || 'chrome'});
  try {
    for (const edition of ['launcher', 'root-launcher']) {
      for (const pending of [false, true]) {
        const {page, errors} = await open(browser, site, edition);
        try {
          await page.keyboard.press('ArrowUp');
          const playing = () => page.waitForFunction(() => document.querySelector('.ctv-input-tile.is-previewing .ctv-input-preview'));
          if (!pending) await playing();
          await page.evaluate(() => RenewalPanel.open());
          await page.waitForTimeout(1100);
          assert.equal(await page.locator('.ctv-input-preview').count(), 0, edition + ': Settings releases ' + (pending ? 'pending' : 'active') + ' input media');
          // Dialogs keep ownership on focus/visibility/relaunch notifications too.
          await page.evaluate(() => {
            window.dispatchEvent(new Event('focus'));
            document.dispatchEvent(new Event('visibilitychange'));
            document.dispatchEvent(new CustomEvent('webOSRelaunch'));
          });
          await page.waitForTimeout(1100);
          assert.equal(await page.locator('.ctv-input-preview').count(), 0, 'no restart beneath Settings');
          assert.deepEqual(errors, []);
        } finally { await page.close(); }
      }
      const {page, errors} = await open(browser, site, edition);
      try {
        // Launch records the source to restore; the next foreground Home must retain it.
        await page.keyboard.press('ArrowUp');
        await page.keyboard.press('Enter');
        await page.evaluate(() => document.dispatchEvent(new CustomEvent('webOSRelaunch')));
        await page.waitForFunction(() => document.querySelector('.ctv-input-tile.is-previewing .ctv-input-preview'));
        await page.evaluate(() => document.dispatchEvent(new CustomEvent('webOSRelaunch', {detail: {params: {showHelper: true}}})));
        if (edition === 'launcher') {
          await page.locator('.helper-panel:not([hidden])').waitFor();
          await page.waitForTimeout(1100);
          assert.equal(await page.locator('.ctv-input-preview').count(), 0, 'manual Helper relaunch cannot start a preview');
          await page.keyboard.press('Escape');
        } else {
          assert.equal(await page.evaluate(() => typeof window.HomeHelper), 'undefined', 'Root has no manual No-root Helper panel');
        }
        await page.waitForFunction(() => document.querySelector('.ctv-input-tile.is-focused.is-previewing .ctv-input-preview'));
        assert.equal(await page.locator('.ctv-input-tile.is-focused .input-name').textContent(), 'HDMI 1', 'closing Helper keeps the launched source selected');
        // Other owners use the same visible dialog contract, even when ThemeRuntime is resumed for a trial.
        for (const owner of ['settings', 'language', 'confirmation', 'columns', 'updates', 'themes']) {
          await page.evaluate(owner => {
            if (owner === 'settings') RenewalPanel.open();
            if (owner === 'language') HomeI18n.openLanguagePicker();
            if (owner === 'confirmation') HomeI18n.confirm({title: 'Check', message: 'Preview ownership', action: 'OK'}, function () {});
            if (owner === 'columns') HomeLayoutPanel.open();
            if (owner === 'updates') (window.RootUpdates || window.HomeUpdates).open();
            if (owner === 'themes') { RenewalPanel.open(); HomeThemePanel.open(); }
          }, owner);
          await page.waitForTimeout(1100);
          assert.equal(await page.locator('.ctv-input-preview').count(), 0, owner + ' releases the running preview');
          await page.evaluate(() => { window.dispatchEvent(new Event('focus')); document.dispatchEvent(new CustomEvent('webOSRelaunch')); });
          await page.waitForTimeout(1100);
          assert.equal(await page.locator('.ctv-input-preview').count(), 0, owner + ' blocks relaunch/focus restart');
          await page.keyboard.press('Escape');
          await page.waitForFunction(() => document.querySelector('.ctv-input-tile.is-focused.is-previewing .ctv-input-preview'));
        }
        assert.deepEqual(errors, []);
        console.log('PASS input preview yields to owned overlays and preserves return source: ' + edition);
      } finally { await page.close(); }
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
