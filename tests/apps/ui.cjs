// Start scripts/preview.py first; PREVIEW_URL overrides its default port 8876.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const base = process.env.PREVIEW_URL || 'http://127.0.0.1:8876';
(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'chrome' });
  try {
    const page = await browser.newPage({
        viewport: { width: 1920, height: 1080 },
        locale: 'en'
      }),
      errors = [];
    const ready = () =>
      page.waitForFunction(() => window.RootLauncherRendered === true);
    page.on('pageerror', (e) => errors.push(e.message));
    await page.addInitScript(() => {
      window.calls = [];
      window.offline = false;
      window.PalmServiceBridge = function () {
        this.cancel = () => {};
        this.call = (uri, raw) => {
          calls.push({ uri, p: JSON.parse(raw) });
          setTimeout(() => {
            let r = { returnValue: false };
            if (
              uri.endsWith('/restoreProfile') ||
              uri === 'luna://com.cleanyourtv.system.updater.service/status'
            )
              r = { returnValue: true, result: null };
            if (uri.endsWith('/listApps') && !window.offline)
              r = {
                returnValue: true,
                apps: [
                  { id: 'a', title: 'Alpha' },
                  { id: 'b', title: 'Beta' },
                  { id: 'c', title: 'Gamma' },
                  { id: 'com.sdk.ares.hostedapp', title: 'Ares Hosted App' },
                  { id: 'com.cleanyourtv.root.updater', title: 'Root Updater' }
                ]
              };
            if (uri.endsWith('/listApps') && window.inventoryOverride)
              r = { returnValue: true, apps: window.inventoryOverride };
            if (
              uri.endsWith('/listApps') &&
              location.pathname.startsWith('/root-launcher/')
            ) {
              const priority = JSON.parse(raw).priorityIds || [];
              r = {
                returnValue: true,
                apps: ['a', 'b', 'c'].map((id) => ({
                  id,
                  title: id.toUpperCase(),
                  icon: priority.includes(id)
                    ? 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII='
                    : ''
                }))
              };
            }
            if (
              uri === 'luna://com.local.nativehome.service/listApps' &&
              window.inventoryDenied
            )
              r = { returnValue: false, errorCode: -1 };
            if (uri.endsWith('/launch')) r = { returnValue: true };
            this.onservicecallback(JSON.stringify(r));
          }, 10);
        };
      };
    });
    // Keep this app-library fixture in control of RPCs instead of the demo bridge.
    await page.route('**/preview/bridge.js', (r) =>
      r.fulfill({ body: '', contentType: 'application/javascript' })
    );
    await page.route('**/apps.js', (r) =>
      r.fulfill({
        body: 'window.TV_APPS={apps:[{id:"a",title:"Alpha",icon:"brand-v2-icon.png"},{id:"b",title:"Beta",icon:"brand-v2-icon.png"}],inputs:[]};'
      })
    );
    // Home Helper polling has its own tests; isolate app editing from its startup RPCs.
    await page.goto(base + '/launcher/index.html');
    await page.locator('#tiles .item').first().waitFor();
    await ready();
    assert.equal(
      await page.locator('#tiles .add-app').count(),
      1,
      'last tile adds apps'
    );
    const ids = () =>
      page
        .locator('#tiles .item')
        .evaluateAll((els) => els.map((e) => e.dataset.appId || '+'));
    assert.deepEqual(await ids(), ['a', 'b', '+']);
    await page.keyboard.down('Enter');
    await page.waitForTimeout(680);
    await page.keyboard.up('Enter');
    assert.equal(await page.locator('.moving').count(), 1);
    assert.equal(
      await page.evaluate(
        () =>
          calls.filter(
            (c) => c.uri.endsWith('/launch') && ['a', 'b', 'c'].includes(c.p.id)
          ).length
      ),
      0,
      'hold must not launch'
    );
    await page.keyboard.press('ArrowRight');
    await page.keyboard.press('Enter');
    assert.deepEqual(await ids(), ['b', 'a', '+']);
    await page.reload();
    await ready();
    await page.locator('#tiles .add-app').waitFor();
    assert.deepEqual(await ids(), ['b', 'a', '+']);
    await page.keyboard.down('Enter');
    await page.waitForTimeout(680);
    await page.keyboard.up('Enter');
    await page.keyboard.press('ArrowRight');
    await page.keyboard.press('Escape');
    assert.deepEqual(await ids(), ['b', 'a', '+']);
    await page.keyboard.down('Enter');
    await page.waitForTimeout(680);
    await page.keyboard.up('Enter');
    await page.keyboard.press('ArrowDown');
    await page.screenshot({ path: '/tmp/home-app-editing.png' });
    await page.keyboard.press('Enter');
    assert.deepEqual(await ids(), ['a', '+']);
    await page.keyboard.press('Enter'); // Undo receives focus after hiding.
    assert.deepEqual(await ids(), ['b', 'a', '+']);
    await page.locator('.add-app').click();
    await page.locator('#appPicker [data-app-id="c"]').waitFor();
    assert.equal(await page.locator('#appPicker [data-app-id="a"]').count(), 0);
    assert.equal(
      await page
        .locator(
          '#appPicker [data-app-id="com.sdk.ares.hostedapp"], #appPicker [data-app-id="com.cleanyourtv.root.updater"]'
        )
        .count(),
      0,
      'development and updater utilities stay out of Add app'
    );
    await page.screenshot({ path: '/tmp/home-app-picker.png' });
    await page.locator('#appPicker [data-app-id="c"]').click();
    assert.deepEqual(await ids(), ['b', 'a', 'c', '+']);
    await page.reload();
    await ready();
    await page.locator('.add-app').waitFor();
    assert.deepEqual(await ids(), ['b', 'a', 'c', '+']);
    // Releasing a pointer hold over another tile must not swallow the next placement click.
    await page.locator('[data-app-id="b"]').hover();
    await page.mouse.down();
    await page.waitForTimeout(680);
    // One pointer move reorders immediately; locator.hover would chase the displaced tile.
    const target = await page.locator('[data-app-id="c"]').boundingBox();
    await page.mouse.move(
      target.x + target.width / 2,
      target.y + target.height / 2
    );
    await page.mouse.up();
    await page.waitForTimeout(50);
    await page.locator('.moving').click();
    assert.equal(await page.locator('.moving').count(), 0);
    // Restore the test order with a fresh persisted layout before the remaining scenarios.
    await page.evaluate(() => {
      let state = JSON.parse(localStorage.getItem('tvhome.layout'));
      state.ids = ['b', 'a', 'c'];
      localStorage.setItem('tvhome.layout', JSON.stringify(state));
    });
    await page.reload();
    await ready();
    await page.locator('.add-app').waitFor();
    // Pointer hold and hide; then restore through +.
    await page.locator('[data-app-id="b"]').hover();
    await page.mouse.down();
    await page.waitForTimeout(680);
    await page.mouse.up();
    assert.equal(
      await page.locator('.moving').count(),
      1,
      'pointer hold stays in edit mode'
    );
    await page.locator('#hideApp').click();
    assert.deepEqual(await ids(), ['a', 'c', '+']);
    await page.keyboard.press('Escape');
    await page.locator('.add-app').click();
    await page.locator('#appPicker [data-app-id="b"]').click();
    assert.deepEqual(await ids(), ['a', 'c', 'b', '+']);
    await page.locator('.add-app').click();
    await page
      .locator('#appPickerStatus')
      .filter({ hasText: 'All installed' })
      .waitFor();
    await page.keyboard.press('Escape');
    await page.evaluate(() => (window.offline = true));
    await page.locator('.add-app').click();
    await page
      .locator('#appPickerStatus')
      .filter({ hasText: 'saved list' })
      .waitFor();
    await page.keyboard.press('Escape');
    // Hide every tile; + remains reachable and survives reload.
    for (let count = 0; count < 3; count++) {
      await page.locator('#tiles .item:not(.add-app)').first().hover();
      await page.keyboard.down('Enter');
      await page.waitForTimeout(650);
      await page.keyboard.up('Enter');
      await page.keyboard.press('ArrowDown');
      await page.keyboard.press('Enter');
      await page.keyboard.press('Escape');
    }
    assert.deepEqual(await ids(), ['+']);
    await page.reload();
    await ready();
    await page.locator('.add-app').waitFor();
    assert.deepEqual(await ids(), ['+']);
    await page.keyboard.press('Enter');
    await page.locator('#appPicker [data-app-id="a"]').waitFor();
    await page.keyboard.press('Enter');
    assert.deepEqual(await ids(), ['a', '+']);
    // Releasing OK after the page loses focus must not launch or start editing.
    await page.keyboard.down('Enter');
    await page.evaluate(() => window.dispatchEvent(new Event('blur')));
    await page.waitForTimeout(650);
    await page.keyboard.up('Enter');
    assert.equal(await page.locator('.moving').count(), 0);
    // A successful but partial TV response must preserve hidden apps and Undo's other tiles.
    await page.evaluate(() => {
      let state = JSON.parse(localStorage.getItem('tvhome.layout'));
      state.ids = ['a', 'b', 'c'];
      state.hidden = [];
      localStorage.setItem('tvhome.layout', JSON.stringify(state));
    });
    await page.reload();
    await ready();
    await page.locator('.add-app').waitFor();
    await page.evaluate(() => {
      window.inventoryOverride = [{ id: 'a', title: 'Alpha' }];
    });
    await page.locator('.add-app').click();
    await page
      .locator('#appPickerStatus')
      .filter({ hasText: 'All installed' })
      .waitFor();
    await page.keyboard.press('Escape');
    const hideFirst = async () => {
      await page.locator('#tiles [data-app-id="a"]').hover();
      await page.keyboard.down('Enter');
      await page.waitForTimeout(680);
      await page.keyboard.up('Enter');
      await page.keyboard.press('ArrowDown');
      await page.keyboard.press('Enter');
    };
    await hideFirst();
    await page.keyboard.press('Enter');
    assert.deepEqual(
      await ids(),
      ['a', 'b', 'c', '+'],
      'Undo retains apps missing from TV response'
    );
    await hideFirst();
    await page.evaluate(() => {
      window.inventoryOverride = [{ id: 'b', title: 'Beta' }];
    });
    await page.locator('.add-app').click();
    await page.locator('#appPicker [data-app-id="a"]').click();
    assert.deepEqual(
      await ids(),
      ['b', 'c', 'a', '+'],
      'plus restores hidden app without dropping other tiles'
    );
    await page.reload();
    await ready();
    await page.locator('.add-app').waitFor();
    assert.deepEqual(
      await ids(),
      ['b', 'c', 'a', '+'],
      'restored layout persists'
    );
    // A cross-package refusal still discovers apps through Home's own service.
    const layoutBeforeFallback = await page.evaluate(() =>
      localStorage.getItem('tvhome.layout')
    );
    await page.evaluate(() => {
      window.inventoryDenied = true;
      window.inventoryOverride = [
        { id: 'org.example.homebrew', title: 'Example homebrew' }
      ];
      window.calls = [];
    });
    await page.locator('.add-app').click();
    await page
      .locator('#appPicker [data-app-id="org.example.homebrew"]')
      .waitFor();
    assert.deepEqual(
      await page.evaluate(() =>
        calls.filter((c) => c.uri.endsWith('/listApps')).map((c) => c.uri)
      ),
      [
        'luna://com.local.nativehome.service/listApps',
        'luna://com.gathin.tvhome.renewal/listApps'
      ]
    );
    await page
      .locator('#appPicker [data-app-id="org.example.homebrew"]')
      .click();
    assert(
      (await ids()).includes('org.example.homebrew'),
      'fallback inventory remains selectable'
    );
    await page.evaluate(
      (state) => localStorage.setItem('tvhome.layout', state),
      layoutBeforeFallback
    );
    await page.reload();
    await ready();
    await page.unroute('**/apps.js');
    await page.route('**/apps.js', (r) =>
      r.fulfill({
        body:
          'window.TV_APPS=' +
          JSON.stringify({
            apps: Array.from({ length: 7 }, (_, i) => ({
              id: 'row' + i,
              title: 'App ' + i,
              icon: 'brand-v2-icon.png'
            })),
            inputs: []
          }) +
          ';'
      })
    );
    await page.evaluate(() => localStorage.clear());
    await page.reload();
    await ready();
    await page.locator('.add-app').waitFor();
    await page.keyboard.down('Enter');
    await page.waitForTimeout(650);
    await page.keyboard.up('Enter');
    await page.keyboard.press('ArrowDown');
    assert.equal(
      await page
        .locator('#hideApp')
        .evaluate((e) => e.classList.contains('focused')),
      false,
      'first down moves into second row'
    );
    await page.keyboard.press('ArrowRight');
    await page.keyboard.press('ArrowRight');
    assert.equal(
      (await ids()).at(-1),
      '+',
      'plus stays last even at movement boundary'
    );
    await page.keyboard.press('ArrowDown');
    assert.equal(
      await page
        .locator('#hideApp')
        .evaluate((e) => e.classList.contains('focused')),
      true
    );
    await page.keyboard.press('ArrowUp');
    await page.keyboard.press('Escape');
    assert.deepEqual(await ids(), [
      'row0',
      'row1',
      'row2',
      'row3',
      'row4',
      'row5',
      'row6',
      '+'
    ]);
    // Simulate an exhausted Root catalog: only requested priorities have icons.
    await page.unroute('**/apps.js');
    await page.route('**/apps.js', (r) =>
      r.fulfill({
        body: 'window.TV_APPS={apps:[{id:"b",title:"B",icon:""}],inputs:[]};'
      })
    );
    await page.evaluate(() => {
      localStorage.clear();
      localStorage.setItem(
        'tvhome.layout',
        JSON.stringify({
          version: 1,
          ids: ['b'],
          hidden: [],
          catalog: [{ id: 'b', title: 'B', icon: '' }]
        })
      );
    });
    await page.goto(base + '/root-launcher/index.html');
    await ready();
    await page.waitForFunction(
      () =>
        document.querySelector('#tiles [data-app-id="b"] img')?.naturalWidth > 0
    );
    assert.deepEqual(
      await page.evaluate(
        () =>
          calls.find((c) => c.uri.endsWith('/listApps') && !c.p.inputs).p
            .priorityIds
      ),
      ['b']
    );
    await page.locator('.add-app').click();
    await page.locator('#appPicker [data-app-id="c"]').click();
    await page.waitForFunction(
      () =>
        document.querySelector('#tiles [data-app-id="c"] img')?.naturalWidth > 0
    );
    assert.deepEqual(await ids(), ['b', 'c', '+']);
    assert.deepEqual(
      await page.evaluate(
        () =>
          calls.filter((c) => c.uri.endsWith('/listApps') && !c.p.inputs).at(-1)
            .p.priorityIds
      ),
      ['c', 'b']
    );
    assert.deepEqual(errors, []);
    await page.screenshot({ path: '/tmp/home-app-management.png' });
    console.log(
      'PASS hold, pointer, reorder, cancel, hide, undo, add, persistence, empty picker, offline'
    );
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
