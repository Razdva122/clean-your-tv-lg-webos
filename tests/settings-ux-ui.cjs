// Remote directions follow visible geometry; failures retain a recovery path.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
(async () => {
  const browser = await chromium.launch({
    headless: true,
    channel: process.env.BROWSER_CHANNEL || 'chrome'
  });
  const failures = [];
  fs.mkdirSync('build/tests/settings-ux', { recursive: true });
  try {
    for (const edition of ['launcher', 'root-launcher']) {
      const page = await browser.newPage({
        viewport: { width: 1280, height: 720 }
      });
      const errors = [];
      page.on('pageerror', (error) => errors.push(error.message));
      await page.route(/^https:\/\//, (route) => route.abort());
      await page.addInitScript(() =>
        localStorage.setItem('tvhome.language', 'ru')
      );
      await page.goto(
        (process.env.PREVIEW_URL || 'http://127.0.0.1:8876') +
          '/' +
          edition +
          '/index.html'
      );
      await page.locator('#tiles .item').first().waitFor();
      await page.locator('#btnSettings').click();
      async function category(id) {
        await page.locator('[data-category=' + id + ']').click();
      }
      async function check(name, run) {
        try {
          await run();
        } catch (error) {
          failures.push(edition + '/' + name + ': ' + error.message);
        }
      }
      await category('appearance');
      await check('focus memory', async () => {
        await page.locator('#homeAddApp').focus();
        await page.keyboard.press('ArrowLeft');
        await page.keyboard.press('ArrowRight');
        assert.equal(
          await page.evaluate(() => document.activeElement.id),
          'homeAddApp'
        );
      });
      await page.locator('#homeColumns').click();
      await check('column directions', async () => {
        await page.locator('[data-columns="1"]').focus();
        await page.keyboard.press('ArrowDown');
        assert.equal(
          await page.evaluate(() => document.activeElement.dataset.columns),
          '4'
        );
        await page.keyboard.press('ArrowRight');
        assert.equal(
          await page.evaluate(() => document.activeElement.dataset.columns),
          '5'
        );
        await page.keyboard.press('ArrowUp');
        assert.equal(
          await page.evaluate(() => document.activeElement.dataset.columns),
          '2'
        );
        await page.keyboard.press('ArrowUp');
        assert.equal(
          await page.evaluate(() => document.activeElement.dataset.columns),
          '2',
          'Up stays in the top row'
        );
      });
      await page.keyboard.press('Escape');
      await category('language');
      await check('selected language entry', async () => {
        await page.keyboard.press('ArrowRight');
        assert.equal(
          await page.evaluate(() => document.activeElement.dataset.language),
          'ru'
        );
      });
      await category('weather');
      await check('weather primary entry', async () => {
        await page.keyboard.press('ArrowRight');
        assert(
          await page.evaluate(() =>
            document.activeElement.classList.contains('weather-enabled')
          )
        );
      });
      await page.locator('.weather-enabled').click();
      await page.waitForFunction(
        () => document.querySelector('#weatherPreview').offsetWidth > 0
      );
      await check('compact weather fits', async () => {
        const fits = await page.locator('#weatherPreview').evaluate((el) => {
          const r = el.getBoundingClientRect(),
            a = el.closest('.weather-preview-window').getBoundingClientRect();
          return r.left >= a.left - 1 && r.right <= a.right + 1;
        });
        assert(fits);
      });
      await category('themes');
      await page.locator('.theme-option').first().waitFor();
      await check(
        'installed themes fit without horizontal scrolling',
        async () => {
          assert(
            await page
              .locator('.theme-installed-grid')
              .evaluate((el) => el.scrollWidth <= el.clientWidth + 1)
          );
        }
      );
      await category('home');
      if (edition === 'root-launcher') {
        await page.waitForFunction(
          () =>
            !document.querySelector('.root-settings .home-routing-switch')
              .disabled
        );
        await check('compact Home row direction', async () => {
          await page
            .locator('.root-settings .home-routing-switch')
            .first()
            .focus();
          await page.keyboard.press('ArrowRight');
          assert(
            await page.evaluate(() =>
              document.activeElement.classList.contains('home-visit-button')
            )
          );
        });
        await category('advanced');
        await page.evaluate(() => {
          const Original = PalmServiceBridge;
          window.PalmServiceBridge = function () {
            const original = new Original();
            this.cancel = () => original.cancel();
            this.call = (uri, raw) => {
              if (JSON.parse(raw).audio === 'status') {
                window.answerAudio = () =>
                  this.onservicecallback(
                    JSON.stringify({
                      returnValue: true,
                      enabled: false,
                      canRestart: true,
                      autoSupported: true
                    })
                  );
              } else {
                original.onservicecallback = (reply) =>
                  this.onservicecallback(reply);
                original.call(uri, raw);
              }
            };
          };
        });
        await page.locator('#settings-pane-advanced button').nth(1).click();
        await page.waitForFunction(() => window.answerAudio);
        await check('audio loading is not failure', async () => {
          assert(
            !/недоступно/i.test(
              await page.locator('.root-audio .settings-status').innerText()
            )
          );
          assert.equal(
            await page.locator('.root-audio').getAttribute('aria-busy'),
            'true'
          );
        });
        await page.evaluate(() => answerAudio());
        await page.keyboard.press('Escape');
      } else {
        await page.evaluate(() => {
          const Original = PalmServiceBridge;
          window.homeStatusFails = true;
          window.PalmServiceBridge = function () {
            const original = new Original();
            this.cancel = () => original.cancel();
            this.call = (uri, raw) => {
              if (uri.endsWith('/homeStatus') && window.homeStatusFails)
                this.onservicecallback(JSON.stringify({ returnValue: false }));
              else {
                original.onservicecallback = (reply) =>
                  this.onservicecallback(reply);
                original.call(uri, raw);
              }
            };
          };
          RenewalPanel.open();
        });
        await page.locator('#renewalClose').click();
        await page.locator('#btnSettings').click();
        await check('Home failure can retry', async () => {
          assert(await page.locator('#homeRoutingToggle').isVisible());
          assert(await page.locator('#homeRoutingToggle').isDisabled());
          assert.equal(
            await page
              .locator('#homeRoutingToggle')
              .getAttribute('aria-checked'),
            null
          );
          assert(await page.locator('#homeRoutingRetry').isVisible());
          await page.evaluate(() => (window.homeStatusFails = false));
          await page.locator('#homeRoutingRetry').click();
          await page.waitForFunction(
            () => !document.getElementById('homeRoutingToggle').disabled
          );
          assert(!(await page.locator('#homeRoutingRetry').isVisible()));
          assert(
            await page.evaluate(() => document.activeElement.offsetHeight > 0)
          );
        });
      }
      await page.screenshot({
        path: 'build/tests/settings-ux/' + edition + '.png'
      });
      assert.deepEqual(errors, [], edition + ' browser errors');
      await page.close();
    }
    assert.deepEqual(failures, []);
    console.log(
      'PASS settings UX: spatial navigation, entry focus, weather, recovery and loading'
    );
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
