// Glasshouse is one looping row, with no duplicate app nodes or vertical paging.
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
        await page.evaluate(() =>
          HomeLayoutState.setThemeLayout({
            preset: 'scenic-grid',
            columns: 8,
            allowColumnOverride: false,
            spacingScale: 1,
            textScale: 1,
            focusScale: 1.1
          })
        );
        assert.equal(
          await page.locator('#hero').isVisible(),
          true,
          'selected name has a visible full-detail path'
        );
        assert.equal(
          await page.locator('#hero').textContent(),
          await page.locator('#tiles .focused').getAttribute('aria-label')
        );
        assert.equal(
          await page
            .locator('#tiles .focused')
            .evaluate((el) => getComputedStyle(el).outlineStyle),
          'none',
          'one focus frame, no nested outline'
        );
        assert.ok(
          (await page
            .locator('#tiles .name')
            .first()
            .evaluate((el) => parseFloat(getComputedStyle(el).fontSize))) >= 28,
          'TV captions keep a readable size'
        );
        await page.evaluate(() => {
          window.ribbonMoves = 0;
          window.ribbonObserver = new MutationObserver(
            (records) =>
              (window.ribbonMoves += records.filter(
                (r) => r.type === 'childList'
              ).length)
          );
          ribbonObserver.observe(document.getElementById('tiles'), {
            childList: true
          });
        });
        await page.keyboard.press('ArrowRight');
        assert.equal(
          await page.evaluate(() => {
            ribbonObserver.disconnect();
            return ribbonMoves;
          }),
          0,
          'selection does not detach and reinsert every app'
        );
        assert.doesNotMatch(
          await page.locator('#clock').textContent(),
          /AM|PM/i,
          'hour-cycle suffix does not compete with the clock'
        );
        assert.match(
          await page.locator('#ampm').textContent(),
          /AM|PM/i,
          '12-hour suffix remains visible separately'
        );
        const items = page.locator('#tiles .item'),
          ids = await items.evaluateAll((nodes) =>
            nodes.map((n) => n.dataset.appId || 'add')
          );
        assert.equal(
          await items.evaluateAll(
            (nodes) => new Set(nodes.map((n) => n.style.top)).size
          ),
          1,
          'all apps occupy one row'
        );
        const selected = () =>
          items.evaluateAll((nodes) =>
            nodes.findIndex((n) => n.classList.contains('focused'))
          );
        for (const columns of [1, 3, 8]) {
          await page.evaluate(
            (columns) =>
              HomeLayoutState.setThemeLayout({
                preset: 'scenic-grid',
                columns,
                allowColumnOverride: false,
                spacingScale: 1,
                textScale: 1,
                focusScale: 1.1
              }),
            columns
          );
          let current = await selected();
          for (const [key, step] of [
            ['ArrowRight', 1],
            ['ArrowLeft', -1]
          ]) {
            for (let i = 0; i < ids.length * 2 + 1; i++) {
              await page.keyboard.press(key);
              current = (current + step + ids.length) % ids.length;
              assert.equal(
                await selected(),
                current,
                'wrap follows exact app order in ' + key
              );
              const box = await page
                .locator('#tiles .focused .card')
                .boundingBox();
              assert(
                box.x >= 0 && box.x + box.width <= 1920,
                'selected app stays fully visible'
              );
              assert.equal(
                await items.evaluateAll(
                  (nodes) => new Set(nodes.map((n) => n.style.top)).size
                ),
                1
              );
            }
          }
        }
        const previous = await selected();
        await page.keyboard.press('ArrowDown');
        assert.equal(
          await selected(),
          previous,
          'Down never enters a second row'
        );
        await page.keyboard.press('ArrowUp');
        assert.equal(await page.locator('#topButtons .focused').count(), 1);
        await page.keyboard.press('ArrowDown');
        assert.equal(
          await selected(),
          previous,
          'menu returns to the same app'
        );
        while ((await selected()) !== 0)
          await page.keyboard.press('ArrowRight');
        await page.keyboard.down('Enter');
        await page.waitForTimeout(700);
        await page.keyboard.up('Enter');
        assert.equal(
          await page
            .locator('#tiles .moving')
            .evaluate((el) => getComputedStyle(el, '::after').content),
          'none',
          'scenic reorder has no decorative arrow cluster'
        );
        await page.keyboard.press('ArrowLeft');
        assert.equal(
          await selected(),
          ids.length - 2,
          'reorder also wraps, excluding Add app'
        );
        await page.keyboard.press('Escape');
        assert.deepEqual(
          await items.evaluateAll((nodes) =>
            nodes.map((n) => n.dataset.appId || 'add')
          ),
          ids,
          'cancel restores order and no clones are introduced'
        );
        // Real motion plus a parked pointer must preserve exact remote focus.
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
        await page.locator('#tiles .item[data-ribbon-slot="3"]').hover();
        let expected = await selected();
        for (let i = 0; i < ids.length + 2; i++) {
          await page.keyboard.press('ArrowRight');
          expected = (expected + 1) % ids.length;
          await page.waitForTimeout(190);
          assert.equal(
            await selected(),
            expected,
            'moving cards cannot steal remote focus'
          );
        }
        const sameHeight = await items.evaluateAll(
          (nodes) =>
            new Set(nodes.map((n) => Math.round(n.getBoundingClientRect().y)))
              .size
        );
        assert.equal(sameHeight, 1, 'real motion remains horizontal');
        // The clipped next-card hint must not drag the whole ribbon under a parked cursor.
        while ((await selected()) !== 0) await page.keyboard.press('ArrowLeft');
        await page.evaluate(() =>
          HomeLayoutState.setThemeLayout({
            preset: 'scenic-grid',
            columns: 8,
            allowColumnOverride: false,
            spacingScale: 1,
            textScale: 1,
            focusScale: 1.1
          })
        );
        await page.locator('#tiles .item').nth(7).hover();
        const clipped = await page.locator('#tiles .item').nth(8).boundingBox(),
          viewport = await page.locator('#viewport').boundingBox();
        const edge = {
          x: Math.min(
            clipped.x + clipped.width / 2,
            viewport.x + viewport.width - 5
          ),
          y: clipped.y + 40
        };
        assert.equal(
          await page
            .locator('#tiles .item')
            .nth(8)
            .evaluate((el) => getComputedStyle(el).pointerEvents),
          'none',
          'clipped preview cannot receive pointer focus'
        );
        await page.mouse.move(edge.x, edge.y);
        await page.waitForTimeout(400);
        assert.equal(
          await selected(),
          7,
          'a clipped neighbor is a continuation hint, not an auto-pan hover target'
        );
        await page.keyboard.press('ArrowRight');
        assert.equal(await selected(), 8);
        assert.equal(
          await page
            .locator('#tiles .focused')
            .evaluate((el) => getComputedStyle(el).pointerEvents),
          'auto',
          'a fully revealed card becomes interactive'
        );
        // Horizontal touchpad input moves the ribbon and is ignored inside Settings.
        const wheelTarget = await page
          .locator('#tiles .focused .card')
          .boundingBox();
        await page.mouse.move(
          wheelTarget.x + wheelTarget.width / 2,
          wheelTarget.y + wheelTarget.height / 2
        );
        let beforeWheel = await selected();
        await page.mouse.wheel(120, 0);
        await page.waitForTimeout(200);
        assert.equal(await selected(), (beforeWheel + 1) % ids.length);
        await page.mouse.wheel(-120, 0);
        await page.waitForTimeout(200);
        assert.equal(
          await selected(),
          beforeWheel,
          'wheel scrolls back in the opposite direction'
        );
        await page.locator('#btnSettings').click();
        beforeWheel = await selected();
        await page.mouse.wheel(120, 0);
        await page.waitForTimeout(200);
        assert.equal(
          await selected(),
          beforeWheel,
          'wheel cannot change Home behind Settings'
        );
        await page.keyboard.press('Escape');
        // A short or empty app library must not manufacture cloned tiles.
        for (const count of [1, 0]) {
          await page.evaluate((count) => {
            const apps = TV_APPS.apps.filter((a) => !a.hidden);
            localStorage.setItem(
              AppLibrary.key,
              JSON.stringify({
                version: 1,
                ids: apps.slice(0, count).map((a) => a.id),
                hidden: apps.slice(count).map((a) => a.id),
                catalog: apps
              })
            );
          }, count);
          await page.reload();
          await page.locator('#tiles .focused').waitFor();
          await page.evaluate(() =>
            HomeLayoutState.setThemeLayout({
              preset: 'scenic-grid',
              columns: 8,
              allowColumnOverride: false,
              spacingScale: 1,
              textScale: 1,
              focusScale: 1.1
            })
          );
          assert.equal(
            await items.count(),
            count + 1,
            'only real apps and one Add app tile'
          );
          for (let i = 0; i < 5; i++) {
            await page.keyboard.press('ArrowLeft');
            await page.keyboard.press('ArrowRight');
          }
          assert.equal(await items.count(), count + 1);
        }
        const longName =
          'A long television application name ' + 'W'.repeat(180);
        await page.route('**/apps.js', (route) =>
          route.fulfill({
            body:
              'window.TV_APPS=' +
              JSON.stringify({
                apps: [{ id: 'long.demo', title: longName, icon: '' }],
                inputs: []
              }) +
              ';'
          })
        );
        await page.evaluate(() => localStorage.removeItem(AppLibrary.key));
        await page.reload();
        await page.locator('#tiles .focused').waitFor();
        await page.evaluate(() =>
          HomeLayoutState.setThemeLayout({
            preset: 'scenic-grid',
            columns: 8,
            allowColumnOverride: false,
            spacingScale: 1,
            textScale: 1,
            focusScale: 1.1
          })
        );
        assert.equal(await page.locator('#hero').textContent(), longName);
        assert.ok(
          await page
            .locator('#hero')
            .evaluate((el) => el.scrollHeight <= el.clientHeight + 1),
          'long selected title is readable in full'
        );
        await page.emulateMedia({ reducedMotion: 'reduce' });
        await page.keyboard.press('ArrowLeft');
        assert.equal(
          await page
            .locator('#tiles .item')
            .first()
            .evaluate((el) => getComputedStyle(el).transitionDuration),
          '0s'
        );
        await page.evaluate(() => ThemeRuntime.reset());
        assert.equal(
          await page.locator('#ampm').textContent(),
          '',
          'Classic retains its original time formatting'
        );
        assert.match(await page.locator('#clock').textContent(), /AM|PM/i);
        assert.equal(
          await page
            .locator('#tiles .item')
            .first()
            .evaluate((el) => el.style.pointerEvents),
          '',
          'Classic receives normal pointer hit areas'
        );
        assert.deepEqual(errors, []);
        console.log(
          'PASS looping ribbon, both directions, one row, menu and reorder: ' +
            edition
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
