// Render the actual launcher: stale CSS dimensions or focus/scroll arithmetic
// must fail even when the app-library order is still correct.
const assert = require('node:assert/strict');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const appRoot = path.resolve(
  process.env.TV_WEB_DIR || path.join(__dirname, '../launcher')
);

(async () => {
  const browser = await chromium.launch({
    headless: true,
    channel: process.env.BROWSER_CHANNEL || 'chrome'
  });
  try {
    for (const columns of [5, 8, 6, 7, 4, 3, 2, 1]) {
      const page = await browser.newPage({
        viewport: { width: 1920, height: 1080 },
        locale: 'en'
      });
      const errors = [];
      page.on('pageerror', (error) => errors.push(error.message));
      // Keep pointer hover from taking focus when the grid moves beneath it.
      await page.mouse.move(0, 0);
      await page.addInitScript(() => {
        window.PalmServiceBridge = function () {
          this.cancel = function () {};
          this.call = function (uri) {
            setTimeout(
              () =>
                this.onservicecallback(
                  JSON.stringify({
                    returnValue: false,
                    errorText:
                      'Service does not exist: com.cleanyourtv.system.updater.service'
                  })
                ),
              0
            );
          };
        };
      });
      await page.route('**/config.js', (route) =>
        route.fulfill({
          body:
            'window.CONFIG=' +
            JSON.stringify({ columns, dockApps: [], hiddenApps: [] }) +
            ';'
        })
      );
      await page.route('**/apps.js', (route) =>
        route.fulfill({
          body:
            'window.TV_APPS=' +
            JSON.stringify({
              apps: Array.from({ length: columns * 4 + 1 }, (_, i) => ({
                id: 'test.' + i,
                title: 'App ' + String(i).padStart(2, '0'),
                icon: 'brand-v2-icon.png'
              })),
              inputs: []
            }) +
            ';'
        })
      );
      await page.goto(pathToFileURL(path.join(appRoot, 'index.html')).href);
      await page.locator('#tiles .focused').waitFor();
      const focusedId = () =>
        page.locator('#tiles .focused').getAttribute('data-app-id');
      const settle = () => page.waitForTimeout(650);
      const geometry = () =>
        page.evaluate(() => {
          const rect = (element) => {
            const r = element.getBoundingClientRect();
            return {
              left: r.left,
              right: r.right,
              top: r.top,
              bottom: r.bottom,
              width: r.width,
              height: r.height
            };
          };
          const selected = document.querySelector('#tiles .focused');
          return {
            card: rect(selected.querySelector('.card')),
            glass: rect(document.getElementById('glass')),
            next:
              selected.nextElementSibling &&
              rect(selected.nextElementSibling.querySelector('.card')),
            stageTop: document.getElementById('stage').getBoundingClientRect()
              .top
          };
        });
      await settle();
      let g = await geometry();
      if (columns > 1)
        assert(
          g.next.left - g.glass.right >= 23,
          columns +
            ' columns: focus frame must leave space before the next card'
        );
      if (columns <= 4)
        assert.equal(
          await page
            .locator('.card')
            .first()
            .evaluate((el) => el.offsetWidth),
          360,
          'sparse layouts retain their original card size'
        );
      const checkFocus = async () => {
        const { card, glass } = await geometry();
        assert(
          Math.abs(
            (card.left + card.right) / 2 - (glass.left + glass.right) / 2
          ) < 1,
          'frame centres horizontally'
        );
        assert(
          Math.abs(
            (card.top + card.bottom) / 2 - (glass.top + glass.bottom) / 2
          ) < 1,
          'frame centres vertically'
        );
        assert(
          glass.left < card.left && glass.right > card.right,
          'frame surrounds card horizontally'
        );
        assert(
          glass.top < card.top && glass.bottom > card.bottom,
          'frame surrounds card vertically'
        );
        assert(
          glass.left >= 0 &&
            glass.right <= 1920 &&
            glass.top >= 0 &&
            glass.bottom <= 1080,
          'frame stays on screen'
        );
      };
      await checkFocus();
      if (columns > 1) {
        await page.keyboard.press('ArrowRight');
        assert.equal(await focusedId(), 'test.1');
        await page.keyboard.press('ArrowLeft');
        assert.equal(await focusedId(), 'test.0');
      }
      await page.keyboard.press('ArrowUp');
      assert.equal(
        await page.locator('#topButtons .focused').getAttribute('id'),
        'btnInputs'
      );
      await page.keyboard.press('ArrowDown');
      assert.equal(
        await focusedId(),
        'test.0',
        'Down restores the dock selection'
      );
      for (let row = 1; row <= 4; row++) {
        await page.keyboard.press('ArrowDown');
        assert.equal(
          await focusedId(),
          'test.' + columns * row,
          'Down follows the same column'
        );
        await settle();
        await checkFocus();
      }
      assert((await geometry()).stageTop < 0, 'lower rows scroll into view');
      for (let row = 0; row < 4; row++) await page.keyboard.press('ArrowUp');
      await settle();
      assert.equal(
        (await geometry()).stageTop,
        0,
        'returning to dock resets scrolling'
      );
      // The separately constructed Add tile shares dimensions and focus geometry.
      await page.locator('.add-app').dispatchEvent('mouseover');
      await settle();
      await checkFocus();
      assert.equal(
        await page.locator('.add-app .card').evaluate((el) => el.offsetWidth),
        await page
          .locator('.card')
          .first()
          .evaluate((el) => el.offsetWidth)
      );
      assert.deepEqual(errors, []);
      console.log('PASS launcher geometry/navigation, columns=' + columns);
      await page.close();
    }
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
