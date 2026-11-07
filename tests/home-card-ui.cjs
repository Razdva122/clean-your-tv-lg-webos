// Canonical Home is a persistent CARD, including Ribbon and native editions.
'use strict';
const { assert, chromium, fs, path, stage } = require('./themes/browser.cjs'),
  http = require('node:http');
const { compile } = require('../scripts/compile-tv-web.cjs');
(async () => {
  const site = stage('home-card'),
    compiled = await compile({
      'app.js': fs.readFileSync('launcher/app.js', 'utf8')
    });
  const server = http.createServer((req, res) => {
    const file = path.resolve(
      site,
      '.' + new URL(req.url, 'http://localhost').pathname
    );
    if (!file.startsWith(site + path.sep) || !fs.existsSync(file))
      return res.writeHead(404).end();
    res.setHeader(
      'Content-Type',
      file.endsWith('.js')
        ? 'application/javascript'
        : file.endsWith('.json')
          ? 'application/json'
          : file.endsWith('.css')
            ? 'text/css'
            : file.endsWith('.html')
              ? 'text/html'
              : 'application/octet-stream'
    );
    res.end(
      path.basename(file) === 'app.js'
        ? compiled['app.js']
        : fs.readFileSync(file)
    );
  });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const browser = await chromium.launch({
    headless: true,
    channel: process.env.BROWSER_CHANNEL || 'chrome'
  });
  try {
    for (const edition of ['launcher', 'root-launcher']) {
      const page = await browser.newPage({
          viewport: { width: 1920, height: 1080 }
        }),
        errors = [];
      page.on('pageerror', (error) => errors.push(error.message));
      try {
        const info = JSON.parse(
          fs.readFileSync(path.join(site, edition, 'appinfo.json'))
        );
        assert.equal(info.defaultWindowType, 'card');
        assert.equal(info.transparent, false);
        assert.notEqual(
          info.handlesRelaunch,
          true,
          'platform owns CARD foreground activation'
        );
        await page.addInitScript(() => {
          localStorage.setItem(
            'tvhome.theme.choice.v1',
            JSON.stringify({ id: 'builtin:ribbon', title: 'Ribbon' })
          );
          window.closeCalls = 0;
          window.contextCalls = 0;
          window.activationCalls = 0;
          window.PalmSystem = {
            activate() {
              activationCalls++;
            }
          };
        });
        await page.route(/^https:/, (route) => route.abort());
        await page.route('**/preview/bridge.js', (route) =>
          route.fulfill({
            body:
              fs.readFileSync(path.join(site, 'preview/bridge.js'), 'utf8') +
              ';window.CYTV_BROWSER_PREVIEW=false;window.close=function(){closeCalls++;};var realCall=PalmServiceBridge.prototype.call;PalmServiceBridge.prototype.call=function(uri,raw){if(/presentationContext|presentationDismissed/.test(uri)||uri.indexOf("root.preview.service/status")>=0&&JSON.parse(raw).presentation){contextCalls++;}realCall.call(this,uri,raw);};'
          })
        );
        await page.goto(
          'http://127.0.0.1:' +
            server.address().port +
            '/' +
            edition +
            '/index.html'
        );
        await page.waitForFunction(() => window.RootLauncherRendered === true);
        assert.equal(await page.evaluate(() => CYTV_HOME_HOST), 'card');
        assert.equal(
          await page.evaluate(() => !!window.HomePresentationController),
          false
        );
        assert.equal(
          await page.evaluate(() => contextCalls),
          0,
          'CARD does not borrow an underlay context'
        );
        assert.notEqual(
          await page
            .locator('#homeSurface')
            .evaluate((el) => getComputedStyle(el).backgroundImage),
          'none',
          'Ribbon retains its own poster'
        );
        await page.keyboard.press('Enter');
        await page.waitForTimeout(100);
        assert.equal(
          await page.evaluate(() => closeCalls),
          0,
          'app launch does not close canonical Home'
        );
        await page.evaluate(() =>
          document.dispatchEvent(new Event('webOSRelaunch'))
        );
        await page.keyboard.press('Escape');
        assert.equal(
          await page.evaluate(() => closeCalls),
          0,
          'Home/relaunch/Back have no transient dismiss'
        );
        const activations = await page.evaluate(() => activationCalls);
        await page.evaluate(() => {
          Object.defineProperty(document, 'hidden', {
            configurable: true,
            value: true
          });
          document.dispatchEvent(new Event('visibilitychange'));
          document.dispatchEvent(new Event('webOSRelaunch'));
        });
        assert.equal(
          await page.evaluate(() => activationCalls),
          activations,
          'CARD relaunch does not override platform foreground activation'
        );
        await page.evaluate(() => {
          Object.defineProperty(document, 'hidden', {
            configurable: true,
            value: false
          });
          document.dispatchEvent(new Event('visibilitychange'));
        });
        await page.clock.install();
        await page.clock.fastForward(121000);
        assert.equal(
          await page.evaluate(() => closeCalls),
          0,
          'no transient 120-second lifetime'
        );
        await page.evaluate(() => {
          Object.defineProperty(document, 'hidden', {
            configurable: true,
            value: true
          });
          document.dispatchEvent(new Event('visibilitychange'));
        });
        assert.equal(
          await page.evaluate(() => HomeWallpaper.state().actualQuality),
          'image',
          'hidden CARD releases media'
        );
        assert.deepEqual(errors, []);
        console.log(
          'PASS ' +
            edition +
            ' persistent CARD, Ribbon poster, native launch/relaunch/Back, no timeout and hidden media release'
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
