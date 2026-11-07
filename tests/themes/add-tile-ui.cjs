// Catches inaccessible app management, stale focus and last-tile edit bounds without +.
const { assert, chromium, stage, open } = require('./browser.cjs');
(async () => {
  const site = stage(),
    browser = await chromium.launch({
      headless: true,
      channel: process.env.BROWSER_CHANNEL || 'chrome'
    });
  try {
    for (const edition of ['launcher', 'root-launcher']) {
      const { page, errors } = await open(browser, site, edition);
      try {
        const ids = () =>
          page
            .locator('#tiles [data-app-id]')
            .evaluateAll((items) => items.map((el) => el.dataset.appId));
        const original = await ids();
        assert.equal(await page.locator('.add-app').count(), 1);
        await page.locator('#btnSettings').click();
        await page.locator('[data-category=appearance]').click();
        assert.equal(
          await page.locator('#homeShowAddApp').count(),
          1,
          'visibility switch is available'
        );
        await page.locator('#homeShowAddApp').focus();
        await page.keyboard.press('Enter');
        assert.equal(
          await page.locator('#homeShowAddApp').getAttribute('aria-checked'),
          'false'
        );
        assert.equal(
          await page
            .locator('#homeShowAddApp')
            .evaluate((el) => getComputedStyle(el).position),
          'relative',
          'switch thumb is positioned inside its own row'
        );
        assert.equal(await page.locator('.add-app').count(), 0);
        assert.deepEqual(await ids(), original);
        await page.screenshot({
          path: 'build/tests/add-tile-' + edition + '.png'
        });
        await page.waitForFunction(
          () =>
            !Array.from(document.querySelectorAll('#homeThemePanel p')).some(
              (el) => el.textContent === 'Loading themes…'
            )
        );
        assert.equal(
          await page.evaluate(() => document.activeElement.id),
          'homeShowAddApp',
          'late theme load failures must preserve focus on the visibility switch'
        );
        // A failed persistent save must neither flip the switch nor change the grid.
        await page.evaluate(() => {
          window.originalSet = Storage.prototype.setItem;
          Storage.prototype.setItem = function (k, v) {
            if (k === 'tvhome.layout') throw Error('quota');
            return window.originalSet.call(this, k, v);
          };
        });
        await page.keyboard.press('Enter');
        assert.equal(
          await page.locator('#homeShowAddApp').getAttribute('aria-checked'),
          'false'
        );
        assert(await page.locator('#homeAppsError').textContent());
        await page.evaluate(
          () => (Storage.prototype.setItem = window.originalSet)
        );
        await page.keyboard.press('Escape');
        await page.keyboard.press('Escape');
        await page.reload();
        await page.locator('#tiles .focused').waitFor();
        assert.equal(
          await page.locator('.add-app').count(),
          0,
          'choice survives startup'
        );
        // Keep only two apps to exercise the former implicit + sentinel at the end.
        await page.evaluate(() => {
          const s = JSON.parse(localStorage.getItem('tvhome.layout'));
          s.hidden = s.ids.slice(2);
          s.ids = s.ids.slice(0, 2);
          localStorage.setItem('tvhome.layout', JSON.stringify(s));
        });
        await page.reload();
        await page.locator('#tiles .focused').waitFor();
        const pair = await ids();
        assert.equal(pair.length, 2);
        for (const preset of [
          'dock-grid',
          'icon-grid',
          'side-grid',
          'channel-list',
          'scenic-grid'
        ]) {
          await page.evaluate(
            (preset) =>
              HomeLayoutState.setThemeLayout({
                preset,
                columns: 5,
                allowColumnOverride: true,
                spacingScale: 1,
                textScale: 1,
                focusScale: 1.1
              }),
            preset
          );
          // This is an intentional pointer action, not layout-generated mouseover.
          await page.mouse.move(0, 0);
          await page.locator('#tiles [data-app-id]').first().hover();
          assert(
            await page
              .locator('#tiles [data-app-id]')
              .first()
              .evaluate((el) => el.classList.contains('focused')),
            preset + ': pointer selects the first move source'
          );
          const before = await ids();
          await page.keyboard.down('Enter');
          await page.waitForTimeout(700);
          await page.keyboard.up('Enter');
          await page.keyboard.press('ArrowRight');
          await page.keyboard.press('Enter');
          assert.deepEqual(
            await ids(),
            [before[1], before[0]],
            preset + ': last app remains a valid move destination'
          );
        }
        await page.evaluate(() => ThemeRuntime.reset());
        // Hide the last apps and dismiss Undo; upper controls must remain operable.
        for (let i = 0; i < 2; i++) {
          await page.keyboard.down('Enter');
          await page.waitForTimeout(700);
          await page.keyboard.up('Enter');
          await page.keyboard.press('ArrowDown');
          await page.keyboard.press('Enter');
          await page.keyboard.press('Escape');
        }
        assert.equal((await ids()).length, 0);
        assert.equal(
          await page
            .locator('#glass')
            .evaluate((el) => Number(el.style.opacity)),
          0,
          'empty Home clears the old tile focus frame'
        );
        await page.reload();
        await page.waitForFunction(() => window.RootLauncherRendered === true);
        await page.keyboard.press('ArrowRight');
        assert.equal(
          await page.locator('#btnWifi.focused').count(),
          1,
          'empty startup retains remote navigation'
        );
        await page.evaluate(() =>
          document.dispatchEvent(new Event('webOSRelaunch'))
        );
        await page.keyboard.press('ArrowRight');
        assert.equal(await page.locator('#btnWifi.focused').count(), 1);
        // App management remains reachable through Settings even with an empty Home.
        await page.locator('#btnSettings').click();
        await page.locator('[data-category=appearance]').click();
        await page.locator('#homeAddApp').click();
        await page.locator('#appPicker .app-choice').first().waitFor();
        await page.locator('#appPicker .app-choice').first().click();
        assert.equal((await ids()).length, 1);
        assert.equal(await page.locator('.add-app').count(), 0);
        await page.locator('#btnSettings').click();
        await page.locator('[data-category=appearance]').click();
        await page.locator('#homeShowAddApp').click();
        assert.equal(await page.locator('.add-app').count(), 1);
        assert.deepEqual(errors, []);
        console.log(
          'PASS Add app settings, editing, empty recovery and picker: ' +
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
