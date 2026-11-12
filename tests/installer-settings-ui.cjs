// Real Home startup/relaunch and theme selection with simulated TV launch events.
const { assert, fs, path, chromium, stage } = require('./themes/browser.cjs');
const http = require('node:http');
(async () => {
  const site = stage('installer-settings');
  const server = http.createServer((req, res) => {
    const file = path.resolve(
      site,
      '.' + new URL(req.url, 'http://localhost').pathname
    );
    if (
      !file.startsWith(site + path.sep) ||
      !fs.existsSync(file) ||
      !fs.statSync(file).isFile()
    )
      return res.writeHead(404).end();
    res.setHeader(
      'Content-Type',
      {
        '.js': 'application/javascript',
        '.json': 'application/json',
        '.css': 'text/css',
        '.svg': 'image/svg+xml',
        '.png': 'image/png'
      }[path.extname(file)] || 'text/html'
    );
    res.end(fs.readFileSync(file));
  });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  let browser;
  try {
    browser = await chromium.launch({
      headless: true,
      channel: process.env.BROWSER_CHANNEL || 'chrome'
    });
    for (const edition of ['launcher', 'root-launcher']) {
      const page = await browser.newPage();
      const errors = [];
      page.on('pageerror', (error) => errors.push(error.message));
      await page.route(/^https?:\/\/(?!127\.0\.0\.1:)/, (route) =>
        route.abort()
      );
      await page.goto(
        'http://127.0.0.1:' +
          server.address().port +
          '/' +
          edition +
          '/index.html'
      );
      await page.waitForFunction(() => window.RootLauncherRendered === true);
      await Promise.all([
        page.waitForEvent('load'),
        page.evaluate((edition) => {
          document.dispatchEvent(
            new CustomEvent('webOSRelaunch', {
              detail: {
                params: {
                  cytvSetup: {
                    id: 'a'.repeat(32),
                    theme: 'liquid-glass',
                    weather: true,
                    ...(edition === 'root-launcher'
                      ? { tv_name: 'Setup TV' }
                      : {})
                  }
                }
              }
            })
          );
        }, edition)
      ]);
      await page.waitForFunction(
        () =>
          window.RootLauncherRendered === true &&
          ThemeManager.current().id === 'builtin:liquid-glass'
      );
      assert.equal(
        await page.evaluate(
          () => JSON.parse(localStorage.getItem('tvhome.weather.v1')).enabled
        ),
        true
      );
      assert.equal(
        await page.evaluate(
          () => JSON.parse(localStorage.getItem('tvhome.weather.v1')).mode
        ),
        'auto'
      );
      assert.equal(
        await page.evaluate(() => localStorage.getItem('tvhome.name')),
        edition === 'root-launcher' ? 'Setup TV' : null
      );
      if (edition === 'root-launcher')
        assert.equal(await page.title(), 'Setup TV');
      await page.locator('#btnSettings').click();
      assert.equal(await page.locator('#homeTvName').count(), 0);
      await page.keyboard.press('Escape');
      // Initial launch params on a later startup also run after profile readiness.
      await page.addInitScript(() => {
        window.PalmSystem = {
          launchParams: JSON.stringify({
            cytvSetup: { id: 'b'.repeat(32), theme: 'ribbon', weather: false }
          })
        };
      });
      await page.reload();
      await page.waitForFunction(
        () =>
          window.RootLauncherRendered === true &&
          ThemeManager.current().id === 'builtin:ribbon'
      );
      assert.equal(
        await page.evaluate(
          () => JSON.parse(localStorage.getItem('tvhome.weather.v1')).enabled
        ),
        false
      );
      assert.deepEqual(errors, []);
      await page.close();
    }
    console.log(
      'PASS both editions: post-install relaunch, initial parameters, reload idempotence, theme rendering and weather preferences'
    );
  } finally {
    if (browser) await browser.close();
    await new Promise((resolve) => server.close(resolve));
    fs.rmSync(site, { recursive: true, force: true });
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
