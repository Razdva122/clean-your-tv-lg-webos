// Real animations and a parked pointer: scrolling must not steal remote focus.
const { assert, chromium, stage, open } = require('./browser.cjs');
const { compileThemeCss } = require('../../theme-api/compile.cjs');
(async () => {
  const rules = (
    await compileThemeCss(
      '.ctv-home {background-color:#121c85;color:#ffffff;} .ctv-card.is-focused {background-color:#ffffff;color:#121c85;} .ctv-label.is-focused {color:#121c85;} .ctv-focus {background-color:#ffffff;}'
    )
  ).bundle;
  const manifest = require('./fixtures/valid-manifest.json');
  manifest.layout.preset = 'channel-list';
  manifest.layout.columns = 1;
  const site = stage(),
    browser = await chromium.launch({
      headless: true,
      channel: process.env.BROWSER_CHANNEL || 'chrome'
    });
  try {
    for (const edition of ['launcher', 'root-launcher']) {
      const { page, errors } = await open(browser, site, edition);
      try {
        await page.evaluate(
          ({ manifest, rules }) =>
            ThemeRuntime.apply({ manifest, rules, assetHandles: {} }),
          { manifest, rules }
        );
        const selected = () =>
          page
            .locator('#tiles .item')
            .evaluateAll((items) =>
              items.findIndex((el) => el.classList.contains('focused'))
            );
        await page.keyboard.press('ArrowDown');
        assert.equal(
          await page.locator('#hero').textContent(),
          await page.locator('#tiles .focused').getAttribute('aria-label'),
          'Channel title updates immediately with focus'
        );
        await page.locator('#tiles .item').nth(4).hover();
        assert.equal(
          await selected(),
          4,
          'the first real pointer movement after keyboard startup restores hover'
        );
        await page.locator('.add-app').click();
        await page.locator('#appPicker .app-choice').first().click();
        await page.mouse.move(0, 0);
        await page
          .locator('style')
          .evaluateAll((styles) =>
            styles
              .filter((s) =>
                s.textContent.includes(
                  '* { transition: none !important; animation: none !important; }'
                )
              )
              .forEach((s) => s.remove())
          );
        // Scroll to the last item, then park the cursor over row eight as in the report.
        await page.keyboard.press('ArrowDown');
        await page.waitForTimeout(500);
        await page.locator('#tiles .item').nth(7).hover();
        await page.waitForTimeout(500);
        assert.equal(await selected(), 7);
        for (let expected = 6; expected >= 0; expected--) {
          await page.keyboard.press('ArrowUp');
          await page.waitForTimeout(500);
          assert.equal(
            await selected(),
            expected,
            'Up must select exactly the previous row with a stationary pointer'
          );
        }
        assert.equal(
          await page
            .locator('#hero')
            .evaluate((el) => getComputedStyle(el).transitionDuration),
          '0s',
          'Channel title has no fade or slide'
        );
        assert.equal(
          await page
            .locator('#glass')
            .evaluate((el) => getComputedStyle(el).visibility),
          'hidden',
          'Channel uses one row highlight, not an animated enlarged glass'
        );
        await page.locator('#tiles .item').nth(4).hover();
        await page.waitForTimeout(200);
        assert.equal(
          await selected(),
          4,
          'real pointer movement re-enables hover'
        );
        assert.deepEqual(errors, []);
        console.log(
          'PASS Channel parked pointer, arrow scroll and single highlight: ' +
            edition
        );
      } finally {
        await page.close();
      }
    }
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
