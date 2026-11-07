const { chromium, fs, path } = require('./browser.cjs'),
  assert = require('node:assert/strict'),
  http = require('node:http');
(async () => {
  const site = path.resolve('build/tests/builtin-wallpaper-site');
  require('node:child_process').execFileSync(process.env.PYTHON || 'python3', [
    'scripts/preview.py',
    '--build',
    site
  ]);
  const server = http.createServer((req, res) => {
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
        '.html': 'text/html',
        '.css': 'text/css',
        '.json': 'application/json',
        '.mp4': 'video/mp4',
        '.jpg': 'image/jpeg'
      }[path.extname(file)] || 'application/octet-stream'
    );
    res.end(fs.readFileSync(file));
  });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const browser = await chromium.launch({
    headless: true,
    channel: process.env.BROWSER_CHANNEL || 'chrome'
  });
  try {
    for (const edition of ['launcher', 'root-launcher']) {
      const page = await browser.newPage({
          viewport: { width: 1280, height: 720 },
          locale: 'en-US'
        }),
        errors = [];
      page.on('pageerror', (e) => errors.push(e.message));
      await page.addInitScript(() =>
        Object.defineProperty(window, 'WallpaperMediaCache', {
          configurable: true,
          get: () => undefined,
          set: () => {}
        })
      );
      await page.route(/^https:/, (r) => r.abort());
      await page.goto(
        'http://127.0.0.1:' +
          server.address().port +
          '/' +
          edition +
          '/index.html'
      );
      await page.locator('#tiles .focused').waitFor();
      await page.evaluate(() => HomeUIReady);
      await page.locator('#btnSettings').click();
      await page.locator('[data-category=wallpapers]').click();
      assert.equal(
        await page.locator('#wallpaperBuiltin-black-hole').count(),
        1,
        'Black Hole must be available independently of themes'
      );
      await page.locator('#wallpaperBuiltin-black-hole').click();
      await page.waitForFunction(
        () => HomeWallpaper.state().source === 'builtin'
      );
      assert.match(
        await page.locator('#wallpaperSourceInfo').textContent(),
        /Xecutioner/
      );
      await page.evaluate(async () => {
        await ThemeManager.selectInstalled({ id: 'builtin:liquid-glass' });
        if (HomeWallpaper.state().source !== 'theme')
          throw Error('New theme did not restore its own wallpaper');
        await PersonalWallpaper.select('builtin:black-hole');
        ThemeManager.reset();
      });
      await page.reload();
      await page.locator('#tiles .focused').waitFor();
      await page.evaluate(() => HomeUIReady);
      await page.waitForFunction(
        () => HomeWallpaper.state().source === 'builtin'
      );
      assert.equal(
        await page.evaluate(() => HomeWallpaper.state().title),
        'Black Hole'
      );
      await page.evaluate(async () => {
        const canvas = document.createElement('canvas');
        canvas.width = 1280;
        canvas.height = 720;
        const data = canvas.toDataURL('image/jpeg').split(',')[1],
          bytes = Uint8Array.from(atob(data), (x) => x.charCodeAt(0));
        await PersonalWallpaper.receive({
          schemaVersion: 1,
          kind: 'wallpaper',
          source: 'phone',
          image: {
            mediaType: 'image/jpeg',
            width: 1280,
            height: 720,
            size: bytes.length,
            sha256: ThemeData.hash(bytes),
            data
          },
          variants: []
        });
        await PersonalWallpaper.apply();
        await PersonalWallpaper.select('builtin:black-hole');
        if (!PersonalWallpaper.state().installed)
          throw Error('Built-in replaced personal slot');
        await PersonalWallpaper.select('personal');
        if (HomeWallpaper.state().origin !== 'phone')
          throw Error('Personal wallpaper was lost');
        await PersonalWallpaper.select('builtin:black-hole');
        HomeWallpaper.setQuality('4k');
      });
      await page.waitForFunction(() => {
        const v = document.querySelector('video');
        return v && v.videoWidth === 3840 && v.currentTime > 1;
      });
      const result = await page.evaluate(() => ({
        source: HomeWallpaper.state().source,
        stream: WallpaperStream.state(),
        width: document.querySelector('video').videoWidth
      }));
      assert.equal(result.stream.mode, 'mse');
      await page.locator('#btnSettings').click();
      await page.locator('[data-category=wallpapers]').click();
      assert.equal(
        await page
          .locator('#wallpaperBuiltin-black-hole')
          .getAttribute('aria-pressed'),
        'true'
      );
      assert.ok(
        await page
          .locator('#homeWallpaperPanel')
          .evaluate((e) => e.scrollWidth <= e.clientWidth + 1)
      );
      await page.screenshot({
        path: 'build/tests/builtin-wallpaper-' + edition + '.png'
      });
      assert.deepEqual(errors, []);
      await page.close();
      console.log(
        'PASS ' +
          edition +
          ': built-in media, author credit, theme independence, restore, personal slot and UHD stream'
      );
    }
  } finally {
    await browser.close();
    await new Promise((r) => server.close(r));
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
