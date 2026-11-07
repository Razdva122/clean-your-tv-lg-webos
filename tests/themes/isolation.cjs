// A missing suspension hook, premature nested-dialog resume or theme selector
// escaping the Home surface must change the actual standard dialog rendering.
const { assert, chromium, stage, open } = require('./browser.cjs');
async function appearance(page, selector) {
  return page
    .locator(selector)
    .first()
    .evaluate((element) => {
      const s = getComputedStyle(element),
        r = element.getBoundingClientRect();
      return {
        color: s.color,
        background: s.background,
        border: s.border,
        font: s.font,
        shadow: s.boxShadow,
        bounds: [r.x, r.y, r.width, r.height]
      };
    });
}
(async () => {
  const site = stage();
  const browser = await chromium.launch({
    headless: true,
    channel: process.env.BROWSER_CHANNEL || 'chrome'
  });
  try {
    for (const edition of ['launcher', 'root-launcher']) {
      const { page, errors } = await open(browser, site, edition);
      try {
        assert(
          await page.evaluate(() => !!window.ThemeRuntime),
          'shared theme lifecycle is missing'
        );
        await page.locator('#btnSettings').click();
        const settings =
          edition === 'launcher'
            ? '#renewalPanel .settings-main'
            : '.root-settings .settings-main';
        const standard = await appearance(page, settings);
        await page.evaluate(() =>
          HomeI18n.confirm(
            { title: 'Test', message: 'Test', action: 'Continue' },
            function () {}
          )
        );
        const confirmation = await appearance(page, '.confirmation-card');
        await page.keyboard.press('Escape');
        await page.keyboard.press('Escape');
        const classic = await appearance(page, '#clock');
        const themeStyle = await page.addStyleTag({
          content:
            '.ctv-home { background: rgb(20, 40, 60); color: rgb(0, 255, 0); }' +
            '.ctv-home .ctv-clock { color: rgb(255, 0, 128); } .ctv-home .ctv-shortcut { background: rgb(60, 0, 80); }'
        });
        await themeStyle.evaluate((style) => {
          style.id = 'ctv-theme-style';
        });
        assert.equal(
          (await appearance(page, '#clock')).color,
          'rgb(255, 0, 128)'
        );
        await page.locator('#btnSettings').click();
        assert.deepEqual(
          await appearance(page, settings),
          standard,
          'Settings stays standard'
        );
        assert.equal(
          (await appearance(page, '#clock')).color,
          classic.color,
          'Settings suspends theme'
        );
        await page.evaluate(() =>
          HomeI18n.confirm(
            { title: 'Test', message: 'Test', action: 'Continue' },
            function () {}
          )
        );
        assert.deepEqual(
          await appearance(page, '.confirmation-card'),
          confirmation
        );
        await page.keyboard.press('Escape');
        assert.equal(
          (await appearance(page, '#clock')).color,
          classic.color,
          'closing nested confirmation keeps Settings unthemed'
        );
        await page.keyboard.press('Escape');
        assert.equal(
          (await appearance(page, '#clock')).color,
          'rgb(255, 0, 128)',
          'Home resumes theme'
        );
        await page.evaluate(() => HomeI18n.openLanguagePicker());
        assert.equal((await appearance(page, '#clock')).color, classic.color);
        await page.keyboard.press('Escape');
        assert.equal(
          (await appearance(page, '#clock')).color,
          'rgb(255, 0, 128)'
        );
        await page.evaluate(() =>
          SystemUpdates.open({
            edition: window.ROOT_VERSION ? 'root' : 'no-root',
            recovery: true,
            error: 'Synthetic recovery'
          })
        );
        assert.equal(
          (await appearance(page, '#clock')).color,
          classic.color,
          'recovery suspends theme'
        );
        await page.keyboard.press('Escape');
        assert.equal(
          (await appearance(page, '#clock')).color,
          'rgb(255, 0, 128)'
        );
        await page.evaluate(() => {
          ThemeRuntime.suspend('one');
          ThemeRuntime.suspend('one');
          ThemeRuntime.suspend('two');
          ThemeRuntime.resume('one');
        });
        assert.equal(
          (await appearance(page, '#clock')).color,
          classic.color,
          'another owner still holds suspension'
        );
        await page.evaluate(() => ThemeRuntime.resume('two'));
        assert.equal(
          (await appearance(page, '#clock')).color,
          'rgb(255, 0, 128)'
        );
        await page.evaluate(() => {
          Object.defineProperty(document, 'hidden', {
            configurable: true,
            value: true
          });
          document.dispatchEvent(new Event('visibilitychange'));
        });
        assert.equal(
          (await appearance(page, '#clock')).color,
          'rgb(255, 0, 128)',
          'hidden Home retains validated appearance before compositor exposure'
        );
        await page.evaluate(() => {
          Object.defineProperty(document, 'hidden', {
            configurable: true,
            value: false
          });
          document.dispatchEvent(new Event('visibilitychange'));
        });
        assert.equal(
          (await appearance(page, '#clock')).color,
          'rgb(255, 0, 128)',
          'visible Home resumes accepted appearance'
        );
        await page.evaluate(() => {
          document.getElementById('ctv-theme-style').disabled = true;
          ThemeRuntime.suspend();
          ThemeRuntime.resume();
        });
        assert.equal(
          (await appearance(page, '#clock')).color,
          classic.color,
          'never activate an already disabled sheet'
        );
        assert.deepEqual(errors, []);
        console.log(
          'PASS theme isolation, nested dialogs and recovery: ' + edition
        );
      } finally {
        await page.close();
      }
    }
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
