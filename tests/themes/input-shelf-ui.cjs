// Classic Inputs shelf: one-press remote path, live status, live preview, overflow, preferences and other layouts.
const {assert, chromium, stage, open: openBase} = require('./browser.cjs');
const shelfLayout={preset:'dock-grid',columns:5,spacingScale:1,textScale:1,focusScale:1.1,inputs:'shelf'};
async function open(...args) { const result=await openBase(...args); await result.page.evaluate(layout=>HomeLayoutState.setThemeLayout(layout),shelfLayout); return result; }

// Records the live-status bridge so the test can push subscription updates.
function recordStatusBridge() {
  let ctor;
  Object.defineProperty(window, 'PalmServiceBridge', {configurable: true, set: value => { ctor = value; }, get: () => {
    if (ctor && !ctor.recorded && ctor.prototype.call) {
      const call = ctor.prototype.call;
      ctor.prototype.call = function (uri) {
        if (uri === 'luna://com.webos.service.eim/getAllInputStatus') window.statusBridge = this;
        return call.apply(this, arguments);
      };
      ctor.recorded = true;
    }
    return ctor;
  }});
}

(async () => {
  const site = stage(), browser = await chromium.launch({headless: true, channel: process.env.BROWSER_CHANNEL || 'chrome'});
  try {
    for (const edition of ['launcher', 'root-launcher']) {
      const {page, errors} = await open(browser, site, edition);
      try {
        const focused = () => page.evaluate(() => {
          const pick = selector => document.querySelector(selector);
          if (pick('.ctv-input-tile.is-focused')) return 'shelf:' + pick('.ctv-input-tile.is-focused .input-name').textContent;
          if (pick('.ctv-shortcut.is-focused')) return 'top:' + pick('.ctv-shortcut.is-focused').id;
          if (pick('#inputsPanel:not(.hidden) .ctv-input-row.is-focused')) return 'dropdown';
          if (pick('.ctv-tile.is-focused')) return 'grid:' + pick('.ctv-tile.is-focused').dataset.appId;
          return 'none';
        });
        const press = async (...keys) => { for (const key of keys) await page.keyboard.press(key); };
        // Same settled state as open(): bootstraps, service replies and no transitions.
        const reload = async () => {
          await page.reload(); await page.locator('#tiles .focused').waitFor();
          await page.addStyleTag({content: '* { transition: none !important; animation: none !important; }'});
          await page.waitForTimeout(150);
          await page.evaluate(layout=>HomeLayoutState.setThemeLayout(layout),shelfLayout);
        };
        const dock = await focused();

        // The simulated TV reports four ports plus Live TV; only HDMI 1 is captured and connected.
        assert.equal(await page.locator('#inputShelf').isVisible(), true, edition + ': Classic shows the shelf');
        assert.deepEqual(await page.locator('.ctv-input-tile .input-name').allTextContents(), ['HDMI 1', 'HDMI 2', 'HDMI 3', 'HDMI 4', 'Live TV']);
        assert.deepEqual(await page.locator('.ctv-input-tile').evaluateAll(tiles => tiles.map(tile =>
          (tile.classList.contains('is-connected') ? 'on' : tile.classList.contains('is-disconnected') ? 'off' : '?') + ':' + tile.querySelector('.ctv-input-status').textContent)),
          ['on:PlayStation 5', 'off:Not connected', 'off:Not connected', 'off:Not connected', '?:']);
        assert.equal(await page.locator('.ctv-input-tile.is-disconnected').first().evaluate(el => Number(getComputedStyle(el).opacity)) < 0.5, true, 'disconnected sources are dimmed');
        assert.equal(await page.locator('.ctv-input-tile').first().getAttribute('aria-label'), 'HDMI 1, PlayStation 5');

        // The shelf sits in the empty band: below the header, above the dock app title.
        const geometry = await page.evaluate(() => ({
          header: document.querySelector('header').getBoundingClientRect().bottom,
          shelf: document.getElementById('inputShelf').getBoundingClientRect().toJSON(),
          tiles: document.getElementById('inputShelfWindow').getBoundingClientRect().bottom,
          hero: document.getElementById('hero').getBoundingClientRect().top
        }));
        assert(geometry.shelf.top > geometry.header, 'shelf clears the header');
        assert(geometry.tiles <= geometry.hero, 'shelf clears the focused app title');
        await page.screenshot({path: 'build/tests/input-shelf-' + edition + '.png'});

        // Grow and push: 16:9 tiles at rest; the focused tile grows and later tiles move right.
        const boxes = () => page.locator('.ctv-input-tile').evaluateAll(tiles => tiles.map(tile => {
          const r = tile.getBoundingClientRect();
          return {x: Math.round(r.left), w: Math.round(r.width), h: Math.round(r.height)};
        }));
        const rest = await boxes();
        assert(rest.every(box => box.w === 288 && box.h === 162), 'resting tiles are 288x162: ' + JSON.stringify(rest));
        await press('ArrowUp', 'ArrowRight');
        const grown = await boxes();
        assert.deepEqual([grown[1].w, grown[1].h], [404, 236], 'the focused tile grows to 404x236');
        assert.equal(grown[0].x, rest[0].x, 'tiles before the focused one stay put');
        assert.equal(grown[2].x, grown[1].x + 404 + 24, 'the next tile moves right to make room');
        assert.equal(await page.locator('.ctv-input-tile.is-focused').evaluate(el => getComputedStyle(el).transform), 'none', 'no scale transform softens the text');
        // A pointer at the next tile's left edge focuses it and stays on it after the re-layout.
        await page.mouse.move(grown[2].x + 6, 380);
        assert.equal(await focused(), 'shelf:HDMI 3');
        await page.waitForTimeout(100);
        assert.equal(await focused(), 'shelf:HDMI 3', 'focus stays under the pointer');
        assert.equal((await boxes())[2].w, 404);
        await page.mouse.move(0, 0);
        await press('ArrowDown');
        assert.deepEqual(await boxes(), rest, 'leaving the shelf restores every tile');

        // Remote path: dock -> shelf -> header -> shelf -> dock; Back and OK.
        for (let i = 0; i < 6; i++) await press('ArrowLeft');
        assert.equal(await focused(), dock);
        await press('ArrowUp');
        assert.equal(await focused(), 'shelf:HDMI 1', 'Up from the first dock tile reaches the nearest source');
        assert.equal(await page.locator('#hero').evaluate(el => getComputedStyle(el).opacity), '0', 'the app title hides while the shelf has focus');
        await press('ArrowLeft');
        assert.equal(await focused(), 'shelf:HDMI 1', 'Left does not wrap');
        await press('ArrowRight', 'ArrowRight');
        assert.equal(await focused(), 'shelf:HDMI 3');
        await press('ArrowUp');
        assert.match(await focused(), /^top:/, 'Up from the shelf reaches the header');
        await press('ArrowDown');
        assert.match(await focused(), /^shelf:/, 'Down from the header returns to the shelf');
        await press('ArrowDown');
        assert.match(await focused(), /^grid:/, 'Down from the shelf returns to the dock');
        await press('ArrowUp', 'Escape');
        assert.match(await focused(), /^grid:/, 'Back from the shelf returns to the dock');
        await press('ArrowUp', 'ArrowLeft', 'ArrowLeft', 'ArrowLeft', 'ArrowLeft');
        assert.equal(await focused(), 'shelf:HDMI 1');
        await page.keyboard.press('Enter');
        await page.waitForFunction(() => /preview\.hdmi1/.test(document.getElementById('toast').textContent));
        await page.locator('.ctv-input-tile').nth(4).click();
        await page.waitForFunction(() => /preview\.live/.test(document.getElementById('toast').textContent));

        // Lower grid rows fade the shelf instead of scrolling it under the header.
        await press('ArrowDown', 'ArrowDown');
        assert.equal(await page.locator('#inputShelf').evaluate(el => el.classList.contains('covered')), true);
        await press('ArrowUp', 'ArrowUp');
        assert.match(await focused(), /^shelf:/);
        assert.equal(await page.locator('#inputShelf').evaluate(el => el.classList.contains('covered')), false);

        // The dropdown shares live status and fades the shelf it would overlap.
        await press('ArrowUp');
        await page.locator('#btnInputs').click();
        assert.equal(await focused(), 'dropdown');
        assert.equal(await page.locator('.ctv-input-row').count(), 5);
        assert.equal(await page.locator('.ctv-input-row.is-connected').count(), 1);
        assert.equal(await page.locator('.ctv-input-row.is-disconnected').count(), 3);
        assert.equal(await page.locator('#inputShelf').evaluate(el => el.classList.contains('covered')), true);
        await press('Escape');
        assert.equal(await page.locator('#inputShelf').evaluate(el => el.classList.contains('covered')), false);

        // Placement belongs to the theme, not a saved user preference.
        await page.evaluate(layout=>HomeLayoutState.setThemeLayout({...layout,inputs:'menu'}),shelfLayout);
        assert.equal(await page.locator('#inputShelf').isVisible(),false);
        await press('Escape','ArrowUp');
        assert.match(await focused(), /^top:/, 'without the shelf Up reaches the header');

        // Live preview: resting on a connected source plays its picture inside the tile.
        await reload();
        const previews = () => page.evaluate(() => ({media: document.querySelectorAll('.ctv-input-preview').length,
          previewing: Array.from(document.querySelectorAll('.ctv-input-tile.is-previewing .input-name'), name => name.textContent)}));
        const playing = () => page.waitForFunction(() => document.querySelector('.ctv-input-tile.is-focused.is-previewing .ctv-input-preview'), null, {timeout: 1500});
        const idle = {media: 0, previewing: []};
        await press('ArrowUp');
        assert.deepEqual(await previews(), idle, 'nothing plays before the dwell');
        await playing();
        assert.deepEqual(await previews(), {media: 1, previewing: ['HDMI 1']}, 'one preview, in the focused tile');
        assert.deepEqual(await page.locator('.ctv-input-preview').evaluate(el => [el.getBoundingClientRect().width, el.getBoundingClientRect().height]), [384, 216], 'the picture is an exact 16:9 box');
        assert.equal(await page.locator('.ctv-input-tile.is-previewing .input-glyph').evaluate(el => getComputedStyle(el).visibility), 'hidden');
        await page.screenshot({path: 'build/tests/input-shelf-preview-' + edition + '.png'});
        await press('ArrowRight');
        assert.deepEqual(await previews(), idle, 'moving on stops the preview');
        await page.waitForTimeout(1200);
        assert.deepEqual(await previews(), idle, 'disconnected sources never preview');
        await press('ArrowLeft'); await playing();
        await press('ArrowUp');
        assert.deepEqual(await previews(), idle, 'the header stops the preview');
        await page.locator('.ctv-input-tile').first().hover(); await playing();
        await page.locator('#btnInputs').click();
        assert.deepEqual(await previews(), idle, 'the Inputs dropdown stops the preview');
        await press('Escape');
        await page.locator('.ctv-input-tile').first().hover(); await playing();
        const visibility = hidden => page.evaluate(hidden => {
          Object.defineProperty(document, 'hidden', {configurable: true, get: () => hidden});
          document.dispatchEvent(new Event('visibilitychange'));
        }, hidden);
        await visibility(true);
        assert.deepEqual(await previews(), idle, 'hiding Home stops the preview');
        await visibility(false);
        assert.match(await focused(), /^grid:/, 'returning to Home restores dock focus without a preview');
        await page.evaluate(() => {
          const proto = PalmServiceBridge.prototype, call = proto.call;
          proto.call = function (uri) {
            if (/applicationManager\/launch/.test(uri)) window.launchSawPreview = document.querySelectorAll('.ctv-input-preview').length;
            return call.apply(this, arguments);
          };
        });
        await press('ArrowUp'); await playing();
        await page.keyboard.press('Enter');
        assert.equal(await page.evaluate(() => window.launchSawPreview), 0, 'OK releases the preview before launching the input');
        // Returning to Home lands on the input you switched to, until focus moves elsewhere.
        await visibility(true); await visibility(false);
        assert.equal(await focused(), 'shelf:HDMI 1', 'Home returns to the input that was launched');
        await page.evaluate(() => document.dispatchEvent(new Event('webOSRelaunch')));
        assert.equal(await focused(), 'shelf:HDMI 1', 'a relaunch event right after keeps that input');
        await playing();
        await press('ArrowDown');
        await visibility(true); await visibility(false);
        assert.match(await focused(), /^grid:/, 'moving to the dock forgets the input');
        await press('ArrowUp', 'Enter', 'ArrowDown');
        await page.keyboard.down('Enter'); await page.keyboard.up('Enter');
        await visibility(true); await visibility(false);
        assert.match(await focused(), /^grid:/, 'launching an app forgets the input');
        await press('ArrowUp');
        // A source whose picture fails restores the static tile.
        await page.evaluate(() => {
          window.PREVIEW_INPUT_MEDIA = () => { const media = document.createElement('div'); setTimeout(() => media.dispatchEvent(new Event('error')), 100); return media; };
        });
        await press('ArrowRight', 'ArrowLeft');
        await page.waitForTimeout(1200);
        assert.deepEqual(await previews(), idle, 'a failed preview leaves the static tile');
        assert.equal(await page.locator('.ctv-input-tile.is-focused .input-glyph').evaluate(el => getComputedStyle(el).visibility), 'visible');
        // The Settings switch turns previews off and survives restart.
        await reload();
        await page.locator('#btnSettings').click();
        await page.locator('[data-category=appearance]').click();
        await page.locator('#homePreviewInputs').focus();
        assert.equal(await page.locator('#homePreviewInputs').getAttribute('aria-checked'), 'true');
        await page.keyboard.press('Enter');
        assert.equal(await page.locator('#homePreviewInputs').getAttribute('aria-checked'), 'false');
        await press('Escape', 'Escape');
        await page.mouse.move(0, 0);
        await reload();
        await press('ArrowUp');
        assert.equal(await focused(), 'shelf:HDMI 1');
        await page.waitForTimeout(1200);
        assert.deepEqual(await previews(), idle, 'the switch off prevents previews');
        assert.equal(await page.locator('#inputShelf').isVisible(), true, 'the preview switch keeps the shelf');
        await page.evaluate(() => InputSources.setPreviewEnabled(localStorage, true));

        // Live updates re-render in place: focus follows the source, then clamps when it leaves.
        await page.addInitScript(recordStatusBridge);
        await reload();
        await press('ArrowUp', 'ArrowRight');
        assert.equal(await focused(), 'shelf:HDMI 2');
        const push = devices => page.evaluate(devices => window.statusBridge.onservicecallback(JSON.stringify({returnValue: true, devices})), devices);
        await push([{appId: 'preview.hdmi2', label: 'HDMI 2', connected: true, deviceName: 'Apple TV'}, {appId: 'preview.hdmi3', label: 'HDMI 3', connected: false}]);
        assert.equal(await focused(), 'shelf:HDMI 2', 'focus follows the same source to its new position');
        assert.equal(await page.locator('.ctv-input-tile.is-focused').evaluate(el => el.classList.contains('is-connected')), true);
        await push([{appId: 'preview.hdmi3', label: 'HDMI 3', connected: true}]);
        assert.equal(await focused(), 'shelf:HDMI 3', 'a removed source clamps focus to its old position');
        await push([]);
        assert.deepEqual(await page.locator('.ctv-input-tile .input-name').allTextContents(), ['HDMI 1 · Console', 'Live TV'], 'an empty live list returns to the captured inventory');
        assert.equal(await page.locator('.ctv-input-tile.is-connected, .ctv-input-tile.is-disconnected').count(), 0, 'inventory fallback shows no status');

        // A status update while a preview plays keeps the same picture on the rebuilt tile.
        await reload();
        await press('ArrowUp');
        assert.equal(await focused(), 'shelf:HDMI 1');
        await playing();
        await page.evaluate(() => { document.querySelector('.ctv-input-preview').marked = true; });
        const live = name => [{id: 'HDMI_1', appId: 'preview.hdmi1', label: 'HDMI 1', connected: true, deviceName: name},
          {id: 'HDMI_2', appId: 'preview.hdmi2', label: 'HDMI 2', connected: true, deviceName: 'Apple TV'}];
        await push(live('Renamed console'));
        assert.deepEqual(await page.evaluate(() => {
          const media = document.querySelector('.ctv-input-tile.is-focused.is-previewing .ctv-input-preview');
          return {same: !!media && media.marked === true, count: document.querySelectorAll('.ctv-input-preview').length,
            detail: document.querySelector('.ctv-input-tile.is-focused .input-detail').textContent};
        }), {same: true, count: 1, detail: 'Renamed console'}, 'a rename keeps the running preview in the rebuilt tile');
        // ...and never starts one while Home is hidden or another window has focus.
        await visibility(true);
        await page.evaluate(() => window.dispatchEvent(new Event('focus')));
        await push(live('Hidden update'));
        await page.waitForTimeout(1200);
        assert.deepEqual(await previews(), idle, 'no preview starts while Home is hidden');
        await visibility(false);
        await press('ArrowUp');
        assert.equal(await focused(), 'shelf:HDMI 1');
        await playing();
        await page.evaluate(() => window.dispatchEvent(new Event('blur')));
        assert.deepEqual(await previews(), idle, 'losing window focus stops the preview');
        await push(live('Blurred update'));
        await page.waitForTimeout(1200);
        assert.deepEqual(await previews(), idle, 'no preview starts without window focus');
        await page.evaluate(() => window.dispatchEvent(new Event('focus')));
        await playing();

        // A denied status call keeps the captured inventory without dimming anything.
        await page.addInitScript(() => { window.PREVIEW_INPUT_STATUS = null; });
        await reload();
        assert.deepEqual(await page.locator('.ctv-input-tile .input-name').allTextContents(), ['HDMI 1 · Console', 'Live TV']);
        assert.equal(await page.locator('.ctv-input-tile.is-disconnected').count(), 0);

        // Overflow keeps the focused source in view and fades the clipped side.
        await page.addInitScript(() => {
          window.PREVIEW_INPUT_STATUS = Array.from({length: 9}, (_, i) => ({appId: 'preview.hdmi' + (i + 1), label: 'HDMI ' + (i + 1), connected: i % 2 === 0}));
        });
        await reload();
        assert.equal(await page.locator('.ctv-input-tile').count(), 10);
        assert.equal(await page.locator('#inputShelf').evaluate(el => el.classList.contains('overflow-right')), true);
        await press('ArrowUp');
        for (let i = 0; i < 9; i++) await press('ArrowRight');
        assert.equal(await focused(), 'shelf:Live TV');
        const inView = await page.evaluate(() => {
          const tile = document.querySelector('.ctv-input-tile.is-focused').getBoundingClientRect(), view = document.getElementById('inputShelfWindow').getBoundingClientRect();
          return tile.left >= view.left && tile.right <= view.right;
        });
        assert.equal(inView, true, 'the last source scrolls into view');
        assert.deepEqual(await page.locator('#inputShelf').evaluate(el => [el.classList.contains('overflow-left'), el.classList.contains('overflow-right')]), [true, false]);
        await page.screenshot({path: 'build/tests/input-shelf-overflow-' + edition + '.png'});

        // Other layouts keep today's header-only Inputs behavior.
        await press('Escape');
        for (const preset of ['icon-grid', 'side-grid', 'channel-list', 'scenic-grid']) {
          await page.evaluate(preset => HomeLayoutState.setThemeLayout({preset, columns: 5, allowColumnOverride: true, spacingScale: 1, textScale: 1, focusScale: 1.1}), preset);
          assert.equal(await page.locator('#inputShelf').isVisible(), false, preset + ' hides the shelf');
          await page.locator('#btnInputs').click();
          assert.equal(await focused(), 'dropdown', preset + ' keeps the Inputs dropdown');
          await press('Escape');
        }
        assert.equal(await page.locator('.ctv-input-preview').count(), 0, 'other layouts never preview');
        // The shelf switches only apply to Classic, so other layouts hide them.
        const switches = async () => {
          await page.locator('#btnSettings').click();
          await page.locator('[data-category=appearance]').click();
          const shown = await page.evaluate(() => ['homePreviewInputs'].map(id => document.getElementById(id).offsetHeight > 0));
          await press('Escape', 'Escape');
          await page.mouse.move(0, 0);
          return shown;
        };
        assert.deepEqual(await switches(), [false], 'other layouts hide the shelf switches');
        await page.evaluate(() => HomeLayoutState.setThemeLayout({preset: 'dock-grid', columns: 5, allowColumnOverride: true, spacingScale: 1, textScale: 1, focusScale: 1.1, inputs:'shelf'}));
        assert.equal(await page.locator('#inputShelf').isVisible(), true, 'returning to Classic restores the shelf');
        assert.deepEqual(await switches(), [true], 'Classic shows the shelf switches');
        assert.deepEqual(errors, [], 'renderer errors');
        console.log('PASS Inputs shelf: ' + edition);
      } finally { await page.close(); }
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
