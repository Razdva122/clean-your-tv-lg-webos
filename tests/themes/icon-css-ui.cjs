'use strict';
// Real renderer + real theme bytes. No TV mutation or replacement assets.
const { assert, fs, path, chromium, stage } = require('./browser.cjs'),
  http = require('node:http');
const sourceRoot = path.resolve('themes/itachi'),
  source = JSON.parse(fs.readFileSync(path.join(sourceRoot, 'theme.json'))),
  version = JSON.parse(fs.readFileSync('launcher/appinfo.json')).version;
(async () => {
  const compiled = await require('../../theme-api/compile.cjs').compileSource({
    manifest: source,
    css: fs.readFileSync(path.join(sourceRoot, 'theme.css'), 'utf8'),
    source: {
      repository: 'https://github.com/razdva122/clean-your-tv-lg-webos',
      commit: '0'.repeat(40)
    },
    minimumHomeVersion: version,
    assets: source.assets.map((a) => ({
      ...a,
      data: fs.readFileSync(path.join(sourceRoot, a.path))
    })),
    documents: [source.license.textPath, source.license.creditsPath].map(
      (p) => ({ path: p, data: fs.readFileSync(path.join(sourceRoot, p)) })
    )
  });
  assert.equal(
    compiled.assets.length,
    2,
    'only wallpaper and preview, no icon assets'
  );
  const envelope = {
    descriptor: Buffer.from(JSON.stringify(compiled.manifest) + '\n').toString(
      'base64'
    ),
    files: {}
  };
  envelope.files[compiled.manifest.rules.path] = Buffer.from(
    JSON.stringify(compiled.rules) + '\n'
  ).toString('base64');
  for (const a of [...compiled.assets, ...compiled.documents])
    envelope.files[a.path] = a.data.toString('base64');
  const site = stage(),
    server = http.createServer((req, res) => {
      const name = path.resolve(
        site,
        '.' + new URL(req.url, 'http://localhost').pathname
      );
      if (!name.startsWith(site + path.sep) || !fs.existsSync(name))
        return res.writeHead(404).end();
      res.setHeader(
        'Content-Type',
        name.endsWith('.js')
          ? 'application/javascript'
          : name.endsWith('.json')
            ? 'application/json'
            : name.endsWith('.css')
              ? 'text/css'
              : name.endsWith('.png')
                ? 'image/png'
                : name.endsWith('.svg')
                  ? 'image/svg+xml'
                  : name.endsWith('.ttf')
                    ? 'font/ttf'
                    : 'text/html'
      );
      res.end(fs.readFileSync(name));
    });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const browser = await chromium.launch({
    headless: true,
    channel: process.env.BROWSER_CHANNEL || 'chrome'
  });
  try {
    for (const edition of ['launcher', 'root-launcher']) {
      const context = await browser.newContext({
          viewport: { width: 1920, height: 1080 },
          locale: 'ru-RU',
          timezoneId: 'Asia/Yekaterinburg'
        }),
        page = await context.newPage(),
        errors = [];
      await page.clock.setFixedTime(new Date('2026-10-29T16:42:00Z'));
      page.on('pageerror', (e) => errors.push(e.message));
      await context.route(/^https:\/\//, (r) =>
        r.abort()
      ); /* Read the real staged appinfo, including the independent Root package version. */
      await context.route('**/config.js', (r) =>
        r.fulfill({
          body:
            'window.CONFIG=' +
            JSON.stringify({
              columns: 5,
              dockApps: [
                'youtube.leanback.v4',
                'netflix',
                'com.apple.appletv',
                'com.apple.applemusic',
                'com.webos.app.browser'
              ],
              hiddenApps: [],
              liveTvApp: 'preview.live'
            }) +
            ';'
        })
      );
      await page.goto(
        'http://127.0.0.1:' +
          server.address().port +
          '/' +
          edition +
          '/index.html'
      );
      await page.locator('#tiles .focused').waitFor();
      await page.waitForFunction(() =>
        ['youtube.leanback.v4', 'netflix'].every((id) => {
          const i = document.querySelector('[data-app-id="' + id + '"] img');
          return i && i.complete && i.naturalWidth > 0;
        })
      );
      const original = await page.locator('#tiles img').evaluateAll((images) =>
        images.map((i) => ({
          src: i.getAttribute('src'),
          width: i.naturalWidth,
          height: i.naturalHeight
        }))
      );
      const installed = await page.evaluate(
        async ({ envelope, version }) => {
          const decode = (s) =>
              Uint8Array.from(atob(s), (c) => c.charCodeAt(0)),
            descriptor = decode(envelope.descriptor),
            pack = {
              descriptor,
              digest: ThemeData.hash(descriptor),
              files: {}
            };
          for (const name in envelope.files)
            pack.files[name] = decode(envelope.files[name]);
          const before = JSON.stringify(TV_APPS),
            verified = ThemeData.verify(pack, version);
          await ThemeStore.put(pack, verified.size);
          const item = (await ThemeManager.list()).find(
            (i) => i.id === verified.manifest.id && i.digest === pack.digest
          );
          await ThemeManager.selectInstalled(item);
          return { id: item.id, inventory: before };
        },
        { envelope, version }
      );
      assert.deepEqual(
        await page.locator('#tiles img').evaluateAll((images) =>
          images.map((i) => ({
            src: i.getAttribute('src'),
            width: i.naturalWidth,
            height: i.naturalHeight
          }))
        ),
        original,
        'CSS never changes an original icon source or resolution'
      );
      assert.equal(
        await page
          .locator('#tiles .item')
          .evaluateAll((items) =>
            items
              .filter((e) => Number(e.getAttribute('data-ribbon-slot')) >= 5)
              .every((e) => getComputedStyle(e).visibility === 'hidden')
          ),
        true,
        'scaled off-screen logos cannot leak into the gutter'
      );
      const netflix = page.locator('[data-app-id="netflix"] img');
      assert.equal(
        await netflix.evaluate((i) => getComputedStyle(i).mixBlendMode),
        'screen'
      );
      assert.match(
        await netflix.evaluate((i) => getComputedStyle(i).filter),
        /brightness\(1.3\)/
      );
      assert.equal(
        await page
          .locator('#tiles .focused .card')
          .evaluate((e) => getComputedStyle(e).borderTopWidth),
        '0px'
      );
      await page.keyboard.press('ArrowRight');
      for (
        let n = 0;
        n < 15 &&
        (await page.locator('#tiles .focused').getAttribute('data-app-id')) !==
          'netflix';
        n++
      )
        await page.keyboard.press('ArrowRight');
      assert(
        (await netflix.boundingBox()).width >= 200,
        'original Netflix is visibly enlarged through CSS'
      );
      fs.writeFileSync(
        path.resolve('build/itachi-css-styles-' + edition + '.json'),
        JSON.stringify(
          await page.locator('#tiles img').evaluateAll((images) =>
            images.map((i) => ({
              id: i.closest('.item').dataset.appId,
              classes: i.className,
              filter: getComputedStyle(i).filter,
              blend: getComputedStyle(i).mixBlendMode,
              rect: i.getBoundingClientRect().toJSON()
            }))
          ),
          null,
          2
        )
      );
      await page.evaluate(() => document.fonts.ready);
      await page.screenshot({
        path: path.resolve('build/itachi-css-' + edition + '.png'),
        animations: 'disabled'
      });
      if (edition === 'launcher') {
        const before = await page.screenshot({ animations: 'disabled' }),
          preview =
            await require('../../scripts/build-itachi-theme.cjs').capturePreview(
              page
            );
        assert.deepEqual(
          page.viewportSize(),
          { width: 1920, height: 1080 },
          'thumbnail capture must not change the renderer viewport'
        );
        const difference = await page.evaluate(
          async ({ before, preview }) => {
            async function pixels(src) {
              const image = new Image();
              image.src =
                'data:image/' +
                (src === before ? 'png' : 'jpeg') +
                ';base64,' +
                src;
              await image.decode();
              const c = document.createElement('canvas');
              c.width = 960;
              c.height = 540;
              c.getContext('2d').drawImage(image, 0, 0, 960, 540);
              return {
                data: c.getContext('2d').getImageData(0, 0, 960, 540).data,
                width: image.naturalWidth,
                height: image.naturalHeight
              };
            }
            const a = await pixels(before),
              b = await pixels(preview);
            let difference = 0;
            for (let i = 0; i < a.data.length; i += 4)
              difference +=
                Math.abs(a.data[i] - b.data[i]) +
                Math.abs(a.data[i + 1] - b.data[i + 1]) +
                Math.abs(a.data[i + 2] - b.data[i + 2]);
            return {
              difference: difference / (960 * 540 * 3),
              width: b.width,
              height: b.height
            };
          },
          {
            before: before.toString('base64'),
            preview: preview.toString('base64')
          }
        );
        assert.equal(difference.width, 960);
        assert.equal(difference.height, 540);
        assert(
          difference.difference < 8,
          'thumbnail represents the whole full-size frame, including bottom ribbon'
        );
        fs.writeFileSync(path.resolve('build/itachi-css-preview.jpg'), preview);
      }
      await page.locator('#btnSettings').click();
      assert.equal(
        await netflix.evaluate((i) => getComputedStyle(i).filter),
        'none'
      );
      await page.keyboard.press('Escape');
      await page.reload();
      await page.locator('#tiles .focused').waitFor();
      await page.evaluate(() => ThemeManager.start());
      assert.equal(
        await page.evaluate(() => ThemeManager.current().id),
        installed.id
      );
      assert.equal(
        await page.evaluate(() => JSON.stringify(TV_APPS)),
        installed.inventory
      );
      await page.evaluate(() => ThemeManager.reset());
      assert.equal(
        await netflix.evaluate((i) => getComputedStyle(i).filter),
        'none'
      );
      assert.deepEqual(errors, []);
      await context.close();
      console.log(
        'PASS CSS-only Itachi, unchanged icon bytes/sources, optional browser gate, cache/offline reload, Settings and reset: ' +
          edition
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
