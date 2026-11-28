'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');

if (!process.argv[2])
  throw Error('Pass the extracted IPK application directory');
const app = fs.realpathSync(process.argv[2]);
const manifest = JSON.parse(fs.readFileSync(path.join(app, 'appinfo.json')));
const origin = 'https://single-home.test';
const home = origin + '/' + manifest.main;
const service = 'luna://' + manifest.id + '.service/';
const launch = 'luna://com.webos.applicationManager/launch';
const fixtureDir = path.resolve(
  __dirname,
  '../../preview/reference-apps/icons'
);

const apps = [
  ['fixture.video', 'Video', 'youtube.png'],
  ['fixture.music', 'Music', 'apple-music.png']
].map(([id, title, filename]) => ({
  id,
  title,
  icon:
    'data:image/png;base64,' +
    fs.readFileSync(path.join(fixtureDir, filename)).toString('base64'),
  iconColor: '#27384a'
}));

(async () => {
  const browser = await chromium.launch({
    channel: process.env.BROWSER_CHANNEL || 'chrome'
  });
  try {
    const page = await browser.newPage({
      viewport: { width: 1920, height: 1080 },
      locale: 'en-US'
    });
    page.setDefaultTimeout(7000);
    const errors = [],
      missing = [];
    page.on('pageerror', (e) => errors.push(e.message));
    await page.route('**/*', async (route) => {
      const url = new URL(route.request().url());
      if (url.origin !== origin) return route.abort();
      const file = path.resolve(app, '.' + decodeURIComponent(url.pathname));
      if (
        !file.startsWith(app + path.sep) ||
        !fs.existsSync(file) ||
        !fs.statSync(file).isFile()
      ) {
        missing.push(url.pathname);
        return route.fulfill({ status: 404, body: '' });
      }
      // Playwright derives the response MIME type from this exact packaged path.
      return route.fulfill({ path: file });
    });
    await page.addInitScript(
      ({ apps, service, launch }) => {
        window.PalmServiceBridge = function () {
          this.cancel = () => {};
          this.call = (uri, raw) => {
            const args = JSON.parse(raw);
            const log = JSON.parse(
              sessionStorage.getItem('fixture.calls') || '[]'
            );
            log.push({ uri, args });
            sessionStorage.setItem('fixture.calls', JSON.stringify(log));
            const paired = sessionStorage.getItem('fixture.paired') === '1';
            let reply = { returnValue: false };
            if (uri === service + 'status') {
              reply = {
                returnValue: true,
                storageReady: true,
                credentialsReady: true,
                paired,
                pairing: false,
                startup: paired ? 'pending' : 'off',
                bootObserved: false
              };
            } else if (uri === service + 'pair' && args.confirm === true) {
              sessionStorage.setItem('fixture.paired', '1');
              reply = { returnValue: true, paired: true };
            } else if (uri === service + 'catalog' && paired) {
              reply = { returnValue: true, apps };
            } else if (uri === launch) reply = { returnValue: true };
            else if (
              uri === 'luna://com.webos.settingsservice/getSystemSettings'
            )
              reply = {
                returnValue: true,
                settings: { localeInfo: { locales: { UI: 'en-US' } } }
              };
            setTimeout(() => this.onservicecallback(JSON.stringify(reply)), 0);
          };
        };
      },
      { apps, service, launch }
    );
    const calls = () =>
      page.evaluate(() => JSON.parse(sessionStorage.getItem('fixture.calls')));
    const tiles = page.locator('#tiles .ctv-tile[data-app-id]');
    const ids = () =>
      tiles.evaluateAll((list) => list.map((node) => node.dataset.appId));
    const settings = page.locator('#btnSettings');
    const tab = (id) => page.locator('#settings-tab-' + id);
    const showAdd = page.locator('#homeShowAddApp');

    await page.goto(home);
    await page.waitForURL(origin + '/setup/index.html');
    await page.locator('#pair:focus').waitFor();
    assert.equal(
      (await calls()).some((c) => c.uri === service + 'pair'),
      false
    );
    await page.keyboard.press('Enter');
    await page.waitForURL(home);
    await page.waitForFunction(() => {
      const images = Array.from(
        document.querySelectorAll('#tiles [data-app-id] img.ctv-icon')
      );
      return (
        images.length === 2 &&
        images.every(
          (img) => img.complete && img.naturalWidth > 0 && img.offsetHeight > 0
        )
      );
    });
    assert.deepEqual(
      await ids(),
      apps.map((app) => app.id)
    );
    assert(
      await tiles.locator('img.ctv-icon').evaluateAll(
        (images, icons) =>
          images.every((image, index) => image.src === icons[index]),
        apps.map((app) => app.icon)
      ),
      'each tile must render its own catalog icon'
    );
    await tiles.first().click();
    await page.waitForFunction(
      (uri) =>
        JSON.parse(sessionStorage.getItem('fixture.calls')).some(
          (call) => call.uri === uri
        ),
      launch
    );
    assert.equal(
      (await calls()).find((c) => c.uri === launch).args.id,
      apps[0].id
    );

    await settings.click();
    await tab('appearance').click();
    assert.equal(await showAdd.getAttribute('aria-checked'), 'true');
    await showAdd.click();
    assert.equal(await showAdd.getAttribute('aria-checked'), 'false');
    await page.locator('#homeEditTiles').click();
    await page.mouse.move(0, 0);
    await page.keyboard.press('Enter');
    await page.locator('#tiles .moving[data-app-id="fixture.video"]').waitFor();
    await page.keyboard.press('ArrowRight');
    await page.keyboard.press('Enter');
    await page.keyboard.press('Escape');
    await page.reload();
    await tiles.nth(1).waitFor();
    assert.deepEqual(
      await ids(),
      [apps[1].id, apps[0].id],
      'tile order after relaunch'
    );
    assert.equal(await page.locator('#tiles .add-app').count(), 0);
    await settings.click();
    await tab('appearance').click();
    assert.equal(await showAdd.getAttribute('aria-checked'), 'false');

    await tab('themes').click();
    const ribbon = 'button[data-theme-id="builtin:ribbon"]';
    await page.locator(ribbon).click();
    try {
      await page.locator(ribbon + '[aria-pressed="true"]').waitFor();
    } catch (error) {
      const detail = await page.locator('#themeMessage').allTextContents();
      throw Error(
        'Could not apply the packaged Ribbon theme. ' +
          JSON.stringify({ detail, errors, missing }),
        { cause: error }
      );
    }
    await page.reload();
    await tiles.nth(1).waitFor();
    await settings.click();
    await tab('themes').click();
    await page.locator(ribbon + '[aria-pressed="true"]').waitFor();
    await tab('wallpapers').click();
    await page.locator('button[data-wallpaper-id]').first().waitFor();

    await tab('home').click();
    await page.locator('#pilotSetup').click();
    await page.waitForURL(origin + '/setup/index.html?settings=1');
    await page.locator('#pairAgain').waitFor();
    await page.keyboard.press('Escape');
    await page.waitForURL(home);
    await tiles.nth(1).waitFor();
    const log = await calls();
    assert.deepEqual(
      log.filter((c) => c.uri === service + 'pair').map((c) => c.args),
      [{ confirm: true }]
    );
    assert.deepEqual(
      [
        ...new Set(
          log
            .filter((c) => c.uri.startsWith(service))
            .map((c) => c.uri.slice(service.length))
        )
      ].sort(),
      ['catalog', 'pair', 'status']
    );
    assert.deepEqual(errors, []);
    assert.deepEqual(
      missing.filter((p) => p !== '/favicon.ico'),
      []
    );
    console.log(
      'PASS compiled product Home: first pairing, decoded catalog artwork, launch, tile edit and preference persistence, offline theme selection, wallpaper settings and owner setup'
    );
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
