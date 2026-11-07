// Catches category badges diverging from the existing update action in either edition.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
(async () => {
  const browser = await chromium.launch({
    headless: true,
    channel: process.env.BROWSER_CHANNEL || 'chrome'
  });
  try {
    for (const edition of ['launcher', 'root-launcher']) {
      const page = await browser.newPage({
        viewport: { width: 1920, height: 1080 },
        locale: 'en'
      });
      await page.goto(
        (process.env.PREVIEW_URL || 'http://127.0.0.1:8876') +
          '/' +
          edition +
          '/index.html'
      );
      await page.locator('#tiles .item').first().waitFor();
      // Device responses are synthetic; use the real edition's settings/check callback.
      await page.evaluate(() => {
        window.badgeOffer = true;
        SystemUpdates.check = function () {
          return window.badgeOffer === null
            ? Promise.reject(new Error('offline'))
            : Promise.resolve({ canInstall: window.badgeOffer });
        };
      });
      await page.locator('#btnSettings').click();
      const category = page.locator('[data-category=updates]'),
        dot = category.locator('.settings-update-dot');
      assert.equal(
        await dot.count(),
        1,
        'Updates category must include an availability marker'
      );
      await page.waitForFunction(
        () =>
          document
            .querySelector('[data-category=updates]')
            .getAttribute('data-update-available') === 'true'
      );
      assert(
        await dot.isVisible(),
        'category badge stays visible while another category is selected'
      );
      assert.equal(
        await category.getAttribute('aria-label'),
        'Software updates. Update available.'
      );
      const focus = await page.evaluate(() => document.activeElement.id);
      assert.equal(
        focus,
        'settings-tab-home',
        'update availability must not steal focus'
      );
      await category.click();
      const action = page.locator(
          '.settings-pane:not([hidden]) button[data-update-available]'
        ),
        actionDot = action.locator('.settings-update-dot');
      assert(
        await actionDot.isVisible(),
        'nested update button also shows the badge'
      );
      for (const marker of [dot, actionDot])
        assert.equal(
          await marker.evaluate((el) => getComputedStyle(el).backgroundColor),
          'rgb(255, 179, 71)'
        );
      await page.screenshot({
        path: 'build/tests/update-badges-' + edition + '.png'
      });
      for (const offer of [null, false, true]) {
        await page
          .locator('.settings-workspace .settings-footer button')
          .click();
        await page.evaluate((value) => (window.badgeOffer = value), offer);
        await page.locator('#btnSettings').click();
        // The check completes on a promise microtask before the next browser evaluation.
        assert.equal(
          await category.getAttribute('data-update-available'),
          String(offer !== false),
          'failed checks retain the last confirmed state'
        );
        assert.equal(
          await category.getAttribute('aria-label'),
          offer === false
            ? 'Software updates'
            : 'Software updates. Update available.'
        );
        assert.equal(await dot.isVisible(), offer !== false);
        await category.click();
        assert.equal(
          await actionDot.isVisible(),
          offer !== false,
          'both indicators must appear and disappear together'
        );
      }
      await page.close();
    }
    console.log(
      'PASS update availability badges on category and nested action in both editions, including clear and offline retention'
    );
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
