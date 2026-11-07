// Preview recommendations are initial defaults; real user edits remain authoritative.
'use strict';
const { assert, chromium, fs, path, stage } = require('./browser.cjs');
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
      const type =
        {
          '.js': 'application/javascript',
          '.json': 'application/json',
          '.css': 'text/css',
          '.png': 'image/png',
          '.ttf': 'font/ttf'
        }[path.extname(file)] || 'text/html';
      res.setHeader('Content-Type', type);
      res.end(fs.readFileSync(file));
    });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const browser = await chromium.launch({
    headless: true,
    channel: process.env.BROWSER_CHANNEL || 'chrome'
  });
  const recommended = [
    'netflix',
    'youtube.leanback.v4',
    'com.apple.appletv',
    'com.apple.applemusic',
    'tv.twitch.tv.starshot.lg'
  ];
  try {
    for (const edition of ['launcher', 'root-launcher']) {
      const page = await browser.newPage({
          viewport: { width: 1920, height: 1080 },
          locale: 'en-US'
        }),
        errors = [];
      page.setDefaultTimeout(10000);
      page.on('pageerror', (error) => errors.push(error.message));
      await page.route(/^https:/, (route) => route.abort());
      await page.mouse.move(0, 0);
      const ready = async () => {
        await page.waitForFunction(() => window.RootLauncherRendered === true);
        await page.locator('#tiles .focused').waitFor();
      };
      const ids = () =>
        page
          .locator('#tiles .item[data-app-id]')
          .evaluateAll((items) => items.map((item) => item.dataset.appId));
      try {
        // Consume the actual exported config; overriding CONFIG would hide a broken default.
        await page.goto(
          'http://127.0.0.1:' +
            server.address().port +
            '/' +
            edition +
            '/index.html'
        );
        await ready();
        const original = await ids();
        assert.equal(original.length, 10);
        assert.deepEqual(
          original.slice(0, 5),
          recommended,
          'new Home starts with the requested international app order'
        );
        await page.keyboard.down('Enter');
        await page.waitForTimeout(700);
        await page.keyboard.up('Enter');
        assert.equal(
          await page.locator('#tiles .moving').getAttribute('data-app-id'),
          'netflix',
          'real hold enters Netflix editing'
        );
        await page.keyboard.press('ArrowRight');
        await page.keyboard.press('Enter');
        const reordered = [original[1], original[0], ...original.slice(2)];
        assert.deepEqual(
          await ids(),
          reordered,
          'manual placement swaps the first two real apps'
        );
        assert.deepEqual(
          await page.evaluate(
            () => JSON.parse(localStorage.getItem(AppLibrary.key)).ids
          ),
          reordered,
          'manual edit is durably saved'
        );
        await page.reload();
        await ready();
        assert.deepEqual(
          await ids(),
          reordered,
          'startup recommendations cannot replace saved user order'
        );
        await page.evaluate(async () => {
          const themed = (await ThemeManager.list()).find(
            (item) => item.id === 'builtin:liquid-glass'
          );
          await ThemeManager.selectInstalled(themed);
        });
        assert.equal(
          await page.evaluate(() => ThemeManager.current().id),
          'builtin:liquid-glass'
        );
        assert.deepEqual(
          await ids(),
          reordered,
          'real theme selection preserves manual app order'
        );
        await page.reload();
        await ready();
        assert.equal(
          await page.evaluate(() => ThemeManager.current().id),
          'builtin:liquid-glass'
        );
        assert.deepEqual(
          await ids(),
          reordered,
          'saved theme startup preserves manual app order'
        );
        assert.deepEqual(errors, []);
        console.log(
          'PASS recommended top five, manual reorder, persistence and theme change: ' +
            edition
        );
      } finally {
        await page.close();
      }
    }
  } finally {
    await browser.close();
    await new Promise((resolve) => server.close(resolve));
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
