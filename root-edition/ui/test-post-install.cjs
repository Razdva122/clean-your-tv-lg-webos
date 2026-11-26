const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({
    ...(process.env.BROWSER_CHANNEL
      ? { channel: process.env.BROWSER_CHANNEL }
      : {})
  });
  try {
    for (const size of [
      { width: 1280, height: 720 },
      { width: 1920, height: 1080 }
    ]) {
      const page = await browser.newPage({ viewport: size });
      await page.route('http://cytv.test/', (route) =>
        route.fulfill({
          body: '<!doctype html><button id="outside">Home</button>',
          contentType: 'text/html'
        })
      );
      await page.goto('http://cytv.test/');
      await page.evaluate(() => {
        window.HomeI18n = { ready: (fn) => fn(), t: (key) => key };
        window.PalmSystem = {
          launchParams: { cytvPostInstall: 'a'.repeat(32) }
        };
        window.theme = 'builtin:classic';
        window.ThemeManager = {
          current: () => ({ id: window.theme }),
          list: async () => [
            { id: 'builtin:classic', title: 'Classic', builtin: true },
            { id: 'builtin:ribbon', title: 'Ribbon', builtin: true },
            { id: 'external', title: 'External', builtin: false }
          ],
          selectInstalled: async (item) => {
            window.theme = item.id;
          }
        };
        window.commands = [];
        window.PalmServiceBridge = function () {
          this.cancel = function () {};
          this.call = (uri, raw) => {
            window.commands.push({ uri, raw: JSON.parse(raw) });
            const result = / debloat-status$/.test(JSON.parse(raw).command)
              ? {
                  settings: {
                    homePromotion: { value: 'on', saved: false },
                    livePlus: { value: null, saved: false }
                  }
                }
              : {
                  results: { homePromotion: 'verified' },
                  settings: { homePromotion: { value: 'off', saved: true } }
                };
            this.onservicecallback(
              JSON.stringify({
                returnValue: true,
                stdoutString: JSON.stringify({ ...result, state: 'debloat' })
              })
            );
          };
        };
      });
      await page.addScriptTag({
        path: path.join(__dirname, 'root-post-install.js')
      });
      const panel = page.getByRole('dialog', { name: 'Set up your TV' });
      await panel.waitFor();
      assert.equal(await page.evaluate(() => commands.length), 0);
      await page.getByRole('button', { name: 'Themes', exact: true }).click();
      await page.getByRole('button', { name: 'Ribbon', exact: true }).click();
      await page.waitForFunction(() => window.theme === 'builtin:ribbon');
      assert.equal(
        await page.getByRole('button', { name: 'External' }).count(),
        0
      );
      await page.keyboard.press('Escape');
      await page.getByRole('button', { name: 'Adjust LG settings' }).click();
      const apply = page.getByRole('button', {
        name: 'Apply selected settings'
      });
      assert.equal(await apply.isEnabled(), false);
      await page
        .getByRole('checkbox', { name: 'Turn off sponsored tiles' })
        .click();
      await apply.click();
      await page
        .getByText('Successfully applied and verified', { exact: true })
        .waitFor();
      const last = await page.evaluate(
        () => window.commands[window.commands.length - 1]
      );
      assert.equal(last.uri, 'luna://org.webosbrew.hbchannel.service/exec');
      assert.match(last.raw.command, / debloat --settings homePromotion$/);
      await page.keyboard.press('Escape');
      await page
        .getByRole('button', { name: 'Open Home', exact: true })
        .click();
      assert.equal(await panel.isVisible(), false);
      await page.evaluate(() =>
        document.dispatchEvent(
          new CustomEvent('webOSRelaunch', {
            detail: { cytvPostInstall: 'a'.repeat(32) }
          })
        )
      );
      assert.equal(await panel.isVisible(), false);
      assert.equal(
        await page.evaluate(() => RootPostInstall.available()),
        true
      );
      await page.close();
    }
  } finally {
    await browser.close();
  }
  console.log(
    'PASS TV post-install panel, themes, consent, Debloat readback and one-time launch'
  );
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
