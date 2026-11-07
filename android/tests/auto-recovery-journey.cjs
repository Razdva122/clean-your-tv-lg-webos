const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const root = path.resolve(__dirname, '../..');
const journeys = JSON.parse(
  execFileSync(
    process.env.CYTV_PYTHON || 'python3',
    ['-m', 'android.tests.auto_recovery_events'],
    { cwd: root, encoding: 'utf8' }
  )
);
let browser;
(async () => {
  browser = await chromium.launch({
    headless: true,
    channel: process.env.BROWSER_CHANNEL,
    executablePath:
      process.env.CYTV_CHROME ||
      (process.platform === 'darwin'
        ? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
        : undefined)
  });
  for (const [name, journey] of Object.entries(journeys)) {
    const page = await browser.newPage({
      locale: 'en',
      viewport: { width: 320, height: 740 }
    });
    await page.addInitScript(() => {
      window.starts = [];
      window.CYTV = {
        hasKey: () => false,
        snapshot: () => '[]',
        answer: () => {},
        start: (raw) => window.starts.push(JSON.parse(raw))
      };
      localStorage.setItem('cytv-language', 'en');
    });
    await page.goto(
      'file://' + path.join(root, 'android/app/src/main/assets/ui/index.html')
    );
    await page.evaluate((journey) => {
      receiveNative({
        kind: 'started',
        config: {
          host: '192.0.2.10',
          port: 22,
          edition: journey.edition,
          action: journey.action
        }
      });
      for (const event of journey.events) receiveNative(event);
      receiveNative({ kind: 'finished', code: journey.code });
    }, journey);
    assert.equal(
      await page
        .locator('.result-symbol:not(.review-symbol):not(.error-symbol)')
        .count(),
      0,
      name
    );
    assert.equal(
      await page.locator('[data-action=save-report]').count(),
      1,
      name
    );
    if (name === 'root-access') {
      await page.locator('[data-action=connect-root]').click();
      assert.equal(await page.locator('#host').inputValue(), '192.0.2.10');
      assert.equal(await page.locator('#port').inputValue(), '22');
      await page.locator('[data-action=start]').click();
      assert.deepEqual(await page.evaluate(() => starts.at(-1)), {
        host: '192.0.2.10',
        edition: 'root',
        port: 22,
        action: 'uninstall',
        language: 'en',
        useImportedKey: false
      });
    } else {
      assert.equal(
        await page.locator('[data-action=recover]').count(),
        1,
        name
      );
      if (journey.code === 130)
        assert.equal(
          await page.locator('h1').innerText(),
          'Operation cancelled'
        );
      await page.locator('[data-action=recover]').click();
      assert.equal(
        (await page.evaluate(() => starts.at(-1))).action,
        'recover'
      );
    }
    await page.close();
  }
  await browser.close();
  console.log(
    'PASS Android failed setup, cancellation report, recovery button and Root-removal handoff'
  );
})().catch(async (error) => {
  console.error(error);
  if (browser) await browser.close();
  process.exitCode = 1;
});
