'use strict';
// Packaged Liquid Glass: offline picker, Classic layout with the Inputs shelf, glass styling,
// Classic motion and the baked glow kept under the theme.
const {assert, fs, path, chromium, stage} = require('./browser.cjs'), http = require('node:http');
const types = {'.js': 'application/javascript', '.json': 'application/json', '.css': 'text/css', '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml'};

(async () => {
  const site = stage(), server = http.createServer((req, res) => {
    const file = path.resolve(site, '.' + new URL(req.url, 'http://localhost').pathname);
    if (!file.startsWith(site + path.sep) || !fs.existsSync(file)) return res.writeHead(404).end();
    res.setHeader('Content-Type', types[path.extname(file)] || 'text/html');
    res.end(fs.readFileSync(file));
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const browser = await chromium.launch({headless: true, channel: process.env.BROWSER_CHANNEL || 'chrome'});
  try {
    for (const edition of ['launcher', 'root-launcher']) {
      const page = await browser.newPage({viewport: {width: 1920, height: 1080}, locale: 'en-US'}), errors = [];
      page.setDefaultTimeout(10000);
      page.on('pageerror', error => errors.push(error.message));
      let remote = 0;
      await page.route(/^https?:\/\/(?!127\.0\.0\.1:)/, route => { remote++; return route.abort(); });
      await page.mouse.move(0, 0);
      await page.clock.setFixedTime(new Date('2026-10-28T12:00:00Z'));
      await page.route('**/config.js', route => route.fulfill({body: 'window.CONFIG=' + JSON.stringify({columns: 5, dockApps: [], hiddenApps: ['com.webos.app.browser'], liveTvApp: 'preview.live'}) + ';'}));
      const inventory = JSON.parse(fs.readFileSync(path.resolve('preview/reference-apps/inventory.json')));
      inventory.referenceApps = true;
      inventory.inputs = [1, 2, 3, 4].map(n => ({label: 'HDMI ' + n, appId: 'preview.hdmi' + n}));
      await page.route('**/apps.js', route => route.fulfill({body: 'window.TV_APPS=' + JSON.stringify(inventory) + ';'}));
      await page.goto('http://127.0.0.1:' + server.address().port + '/' + edition + '/index.html');
      await page.locator('#tiles .focused').waitFor();
      await page.evaluate(() => document.fonts.ready);
      const still = await page.addStyleTag({content: '*{transition:none!important;animation:none!important;}'});
      try {
        const settings = async () => {
          await page.locator('#btnSettings').click();
          await page.locator('[data-category=themes]').click();
          await page.locator('[data-theme-id="builtin:liquid-glass"]').waitFor();
        };
        await page.evaluate(() => HomeLayoutState.setColumns(4));
        await settings();
        const glass = page.locator('.theme-option').filter({has: page.locator('[data-theme-id="builtin:liquid-glass"]')});
        assert.equal(await glass.locator('.theme-remove').count(), 0, 'packaged Liquid Glass has no remove action');
        assert.equal(await glass.locator('small').first().textContent(), 'Built-in');
        await glass.locator('.theme-choice').focus();
        const choice = await glass.locator('.theme-choice').boundingBox();
        assert(choice.x >= 0 && choice.x + choice.width <= 1920, 'remote focus reveals the packaged choice in the installed lane');
        await glass.locator('img').waitFor();
        await glass.locator('img').evaluate(img => img.complete ? Promise.resolve() : new Promise(resolve => { img.onload = resolve; img.onerror = resolve; }));
        assert(await glass.locator('img').evaluate(img => img.naturalWidth > 0), 'the preview loads from the packaged registry');
        await glass.locator('.theme-choice').click();
        await page.waitForFunction(() => ThemeManager.current().id === 'builtin:liquid-glass' && !ThemeManager.current().trial);
        assert.equal(await page.locator('#themeKeep').count(), 0, 'installed built-in applies immediately without a trial');
        await page.getByRole('button', {name: 'Back to Home', exact: true}).click();
        await page.locator('#homeThemePanel').waitFor({state: 'hidden'});

        // Classic layout with the shelf, the clock and the column override.
        assert.equal(await page.locator('#homeSurface').getAttribute('data-layout'), 'dock-grid');
        assert.equal(await page.locator('#homeSurface').evaluate(el => el.classList.contains('ctv-classic-motion')), true, 'the theme opts into Classic motion');
        assert.equal(await page.locator('#timeRow').isVisible(), true, 'the Classic header stays');
        assert.equal(await page.evaluate(() => HomeLayoutState.state().columns), 4, 'the theme allows the saved column override');
        assert.equal(await page.locator('.ctv-input-tile').count(), 5, 'the Inputs shelf shows four inputs and Live TV');

        // Glass styling: the focus frame, a focused input tile and a focused shortcut.
        const style = (selector, ...names) => page.locator(selector).first().evaluate((el, names) => names.map(name => getComputedStyle(el)[name]), names);
        const [radius, frame] = await style('.ctv-focus', 'borderTopLeftRadius', 'backgroundImage');
        assert.equal(radius, '32px');
        assert.match(frame, /^linear-gradient/, 'the focus frame is a glass gradient');
        // The card rim is a ring, so Add app keeps its dashed outline and resting cards have no border.
        assert.equal((await style('.add-app .card', 'borderTopStyle'))[0], 'dashed', 'Add app keeps its dashed outline');
        assert.equal((await style('#tiles .item:not(.focused):not(.add-app) .card', 'borderTopWidth'))[0], '0px', 'resting app cards have no border');
        // Measured on a 4K webOS TV: a translucent border on the repainting input tiles and a wide
        // blur on the dock band each cost about 2 missed frames per shelf press.
        assert.equal((await style('.ctv-input-tile', 'borderTopWidth'))[0], '0px', 'input tiles draw their rim as a ring, not a border');
        assert.equal((await style('.ctv-dock', 'boxShadow'))[0], 'none', 'the dock band has no blurred shadow');
        await page.keyboard.press('ArrowUp');
        assert.equal(await page.locator('.ctv-input-tile.is-focused').count(), 1, 'Up from the dock reaches the shelf');
        const [tileFill, tileColor] = await style('.ctv-input-tile.is-focused', 'backgroundColor', 'color');
        assert.equal(tileFill, 'rgba(255, 255, 255, 0.86)', 'the focused tile is near-opaque white glass');
        assert.equal(tileColor, 'rgb(11, 13, 24)', 'with dark text');
        await page.keyboard.press('ArrowRight');
        assert.equal(await page.locator('.ctv-input-tile.is-focused .input-name').textContent(), 'HDMI 2', 'the shelf is navigable');
        // Labels over a live picture turn white, as in Classic.
        const previewLabels = await page.locator('.ctv-input-tile.is-focused').evaluate(tile => {
          tile.classList.add('previewing', 'is-previewing');
          const colors = [tile.querySelector('.input-name'), tile.querySelector('.ctv-input-status')].map(el => getComputedStyle(el).color);
          tile.classList.remove('previewing', 'is-previewing');
          return colors;
        });
        assert.deepEqual(previewLabels, ['rgb(255, 255, 255)', 'rgba(255, 255, 255, 0.78)'], 'preview labels are white over the picture');
        await page.screenshot({path: path.resolve('build/liquid-glass-shelf-' + edition + '.png')});
        await page.keyboard.press('ArrowUp');
        assert.equal(await page.locator('.ctv-shortcut.is-focused').count(), 1, 'Up from the shelf reaches the shortcuts');
        const [pillFill, pillColor] = await style('.ctv-shortcut.is-focused', 'backgroundColor', 'color');
        assert.equal(pillFill, 'rgba(255, 255, 255, 0.86)');
        assert.equal(pillColor, 'rgb(11, 13, 24)');
        await page.keyboard.press('ArrowDown');
        await page.keyboard.press('ArrowDown');
        assert.equal(await page.locator('#tiles .focused').count(), 1, 'back on the grid');

        // Classic motion under the theme: the engine's transitions survive, the focused input
        // grows and its fill fades, a tap that scrolls glides, and card zoom keeps its transition.
        await still.evaluate(node => node.remove());
        await page.waitForTimeout(400);
        assert.deepEqual([await style('.ctv-input-tile', 'transitionProperty'), await style('.pill', 'transitionProperty')],
          [['transform, background, color, opacity'], ['background, color, transform']], 'the theme keeps the engine transitions');
        assert.equal(await page.locator('#viewport').evaluate(el => getComputedStyle(el, '::after').opacity), '1', 'the next row fades at the bottom edge');
        const press = code => page.evaluate(code => document.dispatchEvent(new KeyboardEvent('keydown', {keyCode: code, which: code, bubbles: true, cancelable: true})), code);
        await press(38);
        await page.waitForTimeout(400);
        // Freeze the focused tile's transitions 60 ms in, so a busy runner cannot skip past them.
        const grow = await page.evaluate(() => new Promise(resolve => {
          document.dispatchEvent(new KeyboardEvent('keydown', {keyCode: 39, which: 39, bubbles: true, cancelable: true}));
          requestAnimationFrame(() => requestAnimationFrame(() => {
            const tile = document.querySelector('.ctv-input-tile.is-focused'), running = tile.getAnimations();
            running.forEach(animation => { animation.pause(); animation.currentTime = 60; });
            const style = getComputedStyle(tile), result = {properties: running.map(animation => animation.transitionProperty).sort(), transform: style.transform, fill: style.backgroundColor};
            running.forEach(animation => animation.finish());
            resolve(result);
          }));
        }));
        assert(grow.properties.indexOf('transform') >= 0 && grow.properties.indexOf('background-color') >= 0, 'the focused input grows and fades: ' + grow.properties);
        assert.notEqual(grow.transform, 'none', 'the focused input grows from its old box');
        const alpha = Number((/rgba\(255, 255, 255, ([\d.]+)\)/.exec(grow.fill) || [])[1]);
        assert(alpha > 0.12 && alpha < 0.86, 'the focused fill fades in: ' + grow.fill);
        await page.waitForTimeout(400);
        await press(40);
        await page.waitForTimeout(400);
        assert.equal(await page.locator('#tiles .focused').count(), 1, 'back on the grid');
        const motion = await page.evaluate(() => new Promise(resolve => {
          const surface = document.getElementById('homeSurface'), press = () => document.dispatchEvent(new KeyboardEvent('keydown', {keyCode: 40, which: 40, bubbles: true, cancelable: true}));
          let glided = false, step = 0;
          (function next() {
            press();
            glided = glided || surface.classList.contains('ctv-scroll-glide');
            if (!glided && step++ < 4) return setTimeout(next, 400);
            surface.classList.add('ctv-remote-navigation');
            const card = getComputedStyle(document.querySelector('#tiles .card')), frame = getComputedStyle(document.getElementById('glass'));
            const transform = style => style.transitionDuration.split(', ')[style.transitionProperty.split(', ').indexOf('transform')];
            surface.classList.remove('ctv-remote-navigation');
            resolve({glided, card: transform(card), frame: transform(frame)});
          }());
        }));
        assert.equal(motion.glided, true, 'a tap that scrolls rows glides under the theme');
        assert.deepEqual([motion.card, motion.frame], ['0.24s', '0.24s'], 'card zoom and the frame keep one shared transform transition under remote navigation');
        await page.waitForTimeout(400);
        assert.equal(await page.locator('#viewport').evaluate(el => getComputedStyle(el, '::before').opacity), '1', 'rows above fade under the top edge');

        // The glow bakes into the base element, which carries the theme's clear ambient rule.
        await page.waitForTimeout(1800);
        const glow = await page.evaluate(() => ({
          base: getComputedStyle(document.getElementById('ambientBase')).backgroundImage,
          layers: Array.from(document.querySelectorAll('.ambient')).map(el => getComputedStyle(el).opacity),
        }));
        assert.match(glow.base, /^linear-gradient\(0deg, rgba\(0, 0, 0, 0\)/, "the baked base carries the theme's clear ambient gradient, not Classic's glow");
        assert.deepEqual(glow.layers, ['0', '0'], 'no glow layer is drawn at rest');
        for (let row = 0; row < 8; row++) await page.keyboard.press('ArrowUp');
        await page.keyboard.press('ArrowDown');
        await page.addStyleTag({content: '*{transition:none!important;animation:none!important;}'});
        await page.waitForTimeout(300);

        // The focused library row's label is dark on the white fill.
        await page.locator('.add-app').click();
        await page.locator('#appPicker .app-choice').first().focus();
        assert.deepEqual(await page.locator('#appPicker .app-choice.is-focused .ctv-label').evaluate(el => [getComputedStyle(el).color, getComputedStyle(el).textShadow]),
          ['rgb(11, 13, 24)', 'rgba(0, 0, 0, 0) 0px 0px 0px'], 'the focused library row stays readable');
        await page.keyboard.press('Escape');
        await page.locator('#appPicker').waitFor({state: 'hidden'});
        await page.mouse.move(0, 0);

        await page.reload();
        await page.locator('#tiles .focused').waitFor();
        await page.evaluate(() => ThemeManager.start());
        assert.equal(await page.evaluate(() => ThemeManager.current().id), 'builtin:liquid-glass', 'Liquid Glass survives an offline reload');
        assert.equal(remote, 0, 'packaged application and reload require no internet');
        await page.evaluate(() => document.fonts.ready);
        await page.addStyleTag({content: '*{transition:none!important;animation:none!important;}'});
        await page.waitForTimeout(1800);
        await page.screenshot({path: path.resolve('build/liquid-glass-' + edition + '.png')});
        await page.setViewportSize({width: 1280, height: 720});
        await page.waitForTimeout(200);
        await page.screenshot({path: path.resolve('build/liquid-glass-720-' + edition + '.png')});
        await settings();
        for (const control of await page.locator('#homeThemePanel button:visible:not(:disabled)').all()) {
          await control.focus();
          const box = await control.boundingBox();
          assert(box.x >= 0 && box.y >= 0 && box.x + box.width <= 1280.1 && box.y + box.height <= 720.1, 'settings controls remain reachable with four installed themes at 720p');
        }
        await page.setViewportSize({width: 1920, height: 1080});
        await page.locator('[data-theme-id="builtin:classic"]').click();
        await page.waitForFunction(() => ThemeManager.current().id === 'builtin:classic');
        await page.getByRole('button', {name: 'Back to Home', exact: true}).click();
        await page.locator('#homeThemePanel').waitFor({state: 'hidden'});
        assert.equal(await page.evaluate(() => HomeLayoutState.state().columns), 4, 'Classic restores the saved column preference');
        assert.deepEqual(errors, []);
        console.log('PASS packaged Liquid Glass picker, shelf, glass styling, motion, baked glow, reset: ' + edition);
      } finally { await page.close(); }
    }
  } finally { await browser.close(); await new Promise(resolve => server.close(resolve)); }
})().catch(error => { console.error(error); process.exitCode = 1; });
