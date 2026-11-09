'use strict';
const { assert, chromium, fs, path, stage } = require('./themes/browser.cjs');
const http = require('node:http');
(async () => {
  const site = stage(),
    server = http.createServer((req, res) => {
      const file = path.resolve(
        site,
        '.' + new URL(req.url, 'http://localhost').pathname
      );
      if (!file.startsWith(site + path.sep) || !fs.existsSync(file))
        return res.writeHead(404).end();
      res.setHeader(
        'Content-Type',
        {
          '.js': 'application/javascript',
          '.json': 'application/json',
          '.css': 'text/css',
          '.png': 'image/png',
          '.jpg': 'image/jpeg',
          '.ttf': 'font/ttf'
        }[path.extname(file)] || 'text/html'
      );
      res.end(fs.readFileSync(file));
    });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const browser = await chromium.launch({
    headless: true,
    channel: process.env.BROWSER_CHANNEL || 'chrome'
  });
  let page;
  try {
    page = await browser.newPage({
      viewport: { width: 1440, height: 1000 },
      locale: 'en-US'
    });
    await page.route(/^https:/, (r) => r.abort());
    page.setDefaultTimeout(10000);
    const packages = [];
    page.on('request', (r) => {
      if (r.url().includes('/preview/packages/')) packages.push(r.url());
    });
    const errors = [];
    page.on('pageerror', (e) => errors.push(e.message));
    await page.goto(
      'http://127.0.0.1:' + server.address().port + '/index.html'
    );
    assert.equal(
      await page
        .getByRole('link', { name: 'Theme showcase', exact: true })
        .count(),
      0
    );
    assert.equal(
      (
        await page.request.get(
          'http://127.0.0.1:' + server.address().port + '/themes/index.html'
        )
      ).status(),
      404,
      'standalone catalogue is not exported'
    );
    const frame = page.frameLocator('#screen');
    await page.getByRole('region', { name: 'Themes', exact: true }).waitFor();
    await frame.locator('#tiles .focused').waitFor();
    const order = await frame
      .locator('#tiles .item[data-app-id]')
      .evaluateAll((items) => items.map((i) => i.dataset.appId));
    await page.locator('#previewThemes[aria-busy="false"]').waitFor();
    for (const id of [
      'github:razdva122/clean-your-tv-lg-theme:terminal',
      'github:razdva122/clean-your-tv-lg-theme:itachi'
    ])
      assert.equal(
        await page
          .locator('#previewThemes button[data-theme="' + id + '"]')
          .count(),
        0,
        'retired early themes are not offered in the catalogue'
      );
    assert.equal(
      packages.length,
      0,
      'no theme packages requested before a preview click'
    );
    assert.ok(
      fs.statSync(path.join(site, 'preview/themes.json')).size < 32768,
      'initial catalogue excludes package bytes'
    );
    assert.ok(
      await page
        .locator('.theme-media-badges')
        .first()
        .evaluate((el) => parseFloat(getComputedStyle(el).fontSize) >= 18),
      'metadata badges remain readable'
    );
    const catalog = JSON.parse(
      fs.readFileSync(path.resolve('launcher/theme-catalog.json'))
    ).themes;
    for (const entry of catalog) {
      const card = page.locator(
        '#previewThemes button[data-theme="' + entry.id + '"]'
      );
      assert.equal(
        await card.locator('.theme-video-badge').count(),
        entry.hasVideo ? 1 : 0
      );
      assert.equal(
        await card
          .locator('.theme-media-badge')
          .filter({ hasText: '4K' })
          .count(),
        entry.has4k ? 1 : 0
      );
      if (entry.packageSize !== undefined)
        assert.ok(
          (await card.locator('small').innerText()).includes(
            Math.max(0.1, entry.packageSize / 1000000).toFixed(1) + ' MB'
          )
        );
      assert.equal(
        await card.locator('button,[tabindex]').count(),
        0,
        'metadata adds no focus targets'
      );
    }
    const exportedThemes = JSON.parse(
      fs.readFileSync(path.join(site, 'preview/themes.json'))
    ).themes;
    const videoFilter = page.getByRole('button', {
      name: 'Video',
      exact: true
    });
    const fourKFilter = page.getByRole('button', { name: '4K', exact: true });
    const visibleThemes = () =>
      page
        .locator('#previewThemes button:visible')
        .evaluateAll((buttons) =>
          buttons.map((button) => button.dataset.theme)
        );
    const initialTheme = await frame
      .locator('body')
      .evaluate(() => ThemeManager.current().id);
    await videoFilter.focus();
    await page.keyboard.press('Space');
    assert.equal(await videoFilter.getAttribute('aria-pressed'), 'true');
    assert.deepEqual(
      await visibleThemes(),
      exportedThemes.filter((t) => t.hasVideo).map((t) => t.id)
    );
    await fourKFilter.click();
    assert.deepEqual(
      await visibleThemes(),
      exportedThemes.filter((t) => t.hasVideo && t.has4k).map((t) => t.id)
    );
    assert.equal(
      await frame.locator('body').evaluate(() => ThemeManager.current().id),
      initialTheme,
      'filtering must not change the selected theme'
    );
    assert.equal(
      packages.length,
      0,
      'filtering must not download theme packages'
    );
    await videoFilter.click();
    assert.deepEqual(
      await visibleThemes(),
      exportedThemes.filter((t) => t.has4k).map((t) => t.id)
    );
    for (const edition of ['Root Edition', 'No-root Edition']) {
      await page.getByRole('button', { name: edition, exact: true }).click();
      await page.locator('#previewThemes[aria-busy="false"]').waitFor();
      assert.equal(await fourKFilter.getAttribute('aria-pressed'), 'true');
      assert.deepEqual(
        await visibleThemes(),
        exportedThemes.filter((t) => t.has4k).map((t) => t.id)
      );
    }
    await fourKFilter.click();
    assert.deepEqual(
      await visibleThemes(),
      exportedThemes.map((t) => t.id)
    );
    await page.route('**/preview/packages/*.json', async (route) => {
      await page.unroute('**/preview/packages/*.json');
      await route.fulfill({ json: { schemaVersion: 1 } });
    });
    await page.getByRole('button', { name: 'Retro', exact: true }).click();
    await page.locator('#previewThemes[aria-busy="false"]').waitFor();
    assert.match(
      await page.locator('#themeStatus').innerText(),
      /Could not apply theme/
    );
    assert.notEqual(
      await frame.locator('body').evaluate(() => ThemeManager.current().title),
      'Retro'
    );
    for (const edition of ['No-root Edition', 'Root Edition']) {
      await page.getByRole('button', { name: edition, exact: true }).click();
      await page.waitForFunction(
        (root) =>
          document.getElementById('screen').getAttribute('src') ===
          (root ? 'root-launcher/index.html' : 'launcher/index.html'),
        edition === 'Root Edition'
      );
      await page.locator('#previewThemes[aria-busy="false"]').waitFor();
      await frame.locator('#tiles .focused').waitFor();
      if (edition === 'Root Edition')
        assert.equal(
          await frame
            .locator('body')
            .evaluate(() => ThemeManager.current().title),
          'Crăciun la Brașov',
          'selected theme survives edition switch'
        );
      for (const title of [
        'Retro',
        'Alpine',
        'Classic',
        'Minimal',
        'Atmosphere',
        'Crăciun la Brașov'
      ]) {
        await page.getByRole('button', { name: title, exact: true }).click();
        await page.waitForFunction((title) => {
          const w = document.getElementById('screen').contentWindow;
          return w.ThemeManager && w.ThemeManager.current().title === title;
        }, title);
        await page.locator('#previewThemes[aria-busy="false"]').waitFor();
        const wallpaper = await frame
          .locator('body')
          .evaluate(() => HomeWallpaper.state());
        if (wallpaper.available.length > 1) {
          assert.equal(
            wallpaper.paused,
            false,
            'theme selector must not leave video wallpaper paused after ' +
              title
          );
          await page.waitForFunction(() => {
            const w = document.getElementById('screen').contentWindow,
              v = w.document.getElementById('ctvWallpaperVideo');
            return (
              w.HomeWallpaper.state().actualQuality !== 'image' &&
              v &&
              !v.paused &&
              v.currentTime > 0
            );
          });
        }
        if (title === 'Crăciun la Brașov') {
          await frame
            .locator('body')
            .evaluate(() => HomeWallpaper.setQuality('4k'));
          await page.waitForFunction(() => {
            const w = document.getElementById('screen').contentWindow,
              v = w.document.getElementById('ctvWallpaperVideo');
            return (
              w.HomeWallpaper.state().actualQuality === '4k' &&
              v &&
              v.videoWidth === 3840 &&
              v.videoHeight === 2160 &&
              v.currentTime > 0
            );
          });
          assert.equal(
            await page
              .getByRole('button', { name: title, exact: true })
              .locator('.theme-video-badge')
              .count(),
            0,
            'a still-video wallpaper has no motion badge'
          );
          for (const image of await page.locator('#previewThemes img').all())
            assert.equal(
              await image.evaluate(
                (image) => image.complete && image.naturalWidth > 0
              ),
              true,
              'all preview images load'
            );
          if (process.env.THEME_SCREENSHOTS) {
            fs.mkdirSync(process.env.THEME_SCREENSHOTS, { recursive: true });
            await page.screenshot({
              path: path.join(
                process.env.THEME_SCREENSHOTS,
                edition === 'Root Edition' ? 'root-demo.png' : 'noroot-demo.png'
              )
            });
          }
        }
        assert.equal(
          await page
            .getByRole('button', { name: title, exact: true })
            .getAttribute('aria-pressed'),
          'true'
        );
        assert.deepEqual(
          await frame
            .locator('#tiles .item[data-app-id]')
            .evaluateAll((items) => items.map((i) => i.dataset.appId)),
          order
        );
      }
    }
    assert.equal(
      packages.length,
      catalog.filter((entry) => !entry.builtin).length + 1,
      'failed package is retried; successful packages are reused across edition switches'
    );
    assert.equal(
      new Set(packages).size,
      catalog.filter((entry) => !entry.builtin).length
    );
    // A catalogue without matching media must explain the empty result and reset.
    const noVideo = JSON.parse(
      fs.readFileSync(path.join(site, 'preview/themes.json'))
    );
    for (const theme of noVideo.themes) theme.hasVideo = false;
    await page.route('**/preview/themes.json', (route) =>
      route.fulfill({ json: noVideo })
    );
    await page.setViewportSize({ width: 320, height: 900 });
    await page.reload();
    await page.locator('#previewThemes[aria-busy="false"]').waitFor();
    await videoFilter.click();
    assert.deepEqual(await visibleThemes(), []);
    assert.equal(await page.locator('#filterStatus').isVisible(), true);
    assert.equal(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth
      ),
      true,
      'filters must fit a narrow phone screen'
    );
    await videoFilter.focus();
    await page.keyboard.press('Enter');
    assert.deepEqual(
      await visibleThemes(),
      exportedThemes.map((t) => t.id)
    );
    assert.equal(await page.locator('#filterStatus').isVisible(), false);
    assert.deepEqual(errors, []);
    await browser.close();
    console.log(
      'PASS inline Themes; Video/4K filters, intersection, keyboard, edition persistence, empty results and 320px layout; offline packages and original app order'
    );
  } catch (e) {
    console.error(await page.locator('#themeStatus').innerText());
    throw e;
  } finally {
    await browser.close();
    await new Promise((r) => server.close(r));
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
