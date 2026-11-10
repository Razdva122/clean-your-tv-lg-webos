'use strict';
const {
  assert,
  fs,
  path,
  chromium,
  stage,
  open
} = require('./themes/browser.cjs');
(async () => {
  const site = stage('tv-name'),
    browser = await chromium.launch({ headless: true });
  try {
    for (const edition of ['launcher', 'root-launcher']) {
      const { page, errors } = await open(browser, site, edition);
      await page.locator('#btnSettings').click();
      const input = page.locator('#homeTvName');
      await input.waitFor({ state: 'visible' });
      assert.equal(await input.inputValue(), 'Home');
      await page.evaluate(
        (app) => {
          window.nameCalls = [];
          window.nameTitle = 'Home';
          window.denyName = false;
          window.PalmServiceBridge = function () {
            this.cancel = function () {};
            this.call = (uri, raw) => {
              const params = JSON.parse(raw);
              window.nameCalls.push({ uri, params });
              let reply;
              if (uri.endsWith('/listLaunchPoints'))
                reply = {
                  returnValue: true,
                  launchPoints: [
                    {
                      id: app,
                      launchPointId: app + '_default',
                      title: window.nameTitle
                    }
                  ]
                };
              else if (uri.endsWith('/updateLaunchPoint')) {
                if (!window.denyName) window.nameTitle = params.title;
                reply = { returnValue: !window.denyName };
              } else reply = { returnValue: false };
              this.onservicecallback(JSON.stringify(reply));
            };
          };
        },
        edition === 'launcher'
          ? 'com.gathin.tvhome'
          : 'com.cleanyourtv.root.preview'
      );
      await input.fill('Aashiyan TV');
      await page
        .getByRole('button', { name: 'Save name', exact: true })
        .click();
      assert.equal(await page.title(), 'Aashiyan TV');
      assert.equal(
        await page.evaluate(() => localStorage.getItem('tvhome.name')),
        'Aashiyan TV'
      );
      await page.getByText('TV name saved.', { exact: true }).waitFor();
      assert.equal(await page.evaluate(() => window.nameCalls.length), 3);
      assert.equal(await page.evaluate(() => window.nameTitle), 'Aashiyan TV');
      await page.reload();
      await page.locator('#tiles .focused').waitFor();
      assert.equal(
        await page.locator('#tvNameLoading').count(),
        0,
        'no duplicate app-managed loading screen'
      );
      assert.equal(await page.title(), 'Aashiyan TV');
      await page.locator('#btnSettings').click();
      assert.equal(await input.inputValue(), 'Aashiyan TV');
      await page
        .getByRole('button', { name: 'Reset to Home', exact: true })
        .click();
      assert.equal(await page.title(), 'Home');
      await page
        .getByText(
          'Name saved in Home. LG startup title could not be verified.',
          { exact: true }
        )
        .waitFor();
      await page.evaluate(() => {
        window._setItem = Storage.prototype.setItem;
        Storage.prototype.setItem = function (k, v) {
          if (k === 'tvhome.name') throw Error('quota');
          return window._setItem.call(this, k, v);
        };
      });
      await input.fill('Unsaved');
      await page
        .getByRole('button', { name: 'Save name', exact: true })
        .click();
      assert.equal(await page.title(), 'Home');
      await page
        .getByText(
          'Could not save TV name. Check available storage and try again.',
          { exact: true }
        )
        .waitFor();
      assert.deepEqual(errors, []);
      fs.mkdirSync(path.resolve('build/tests/tv-name'), { recursive: true });
      await page.screenshot({
        path: path.resolve('build/tests/tv-name', edition + '.png')
      });
      await page.close();
    }
  } finally {
    await browser.close();
  }
  console.log(
    'TV-name Settings UI: legacy defaults, rename, restart, reset and failed save passed in both editions.'
  );
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
