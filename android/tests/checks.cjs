const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath:
      process.env.CYTV_CHROME ||
      '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
  });
  try {
    const page = await browser.newPage({
      viewport: { width: 320, height: 740 },
      locale: 'ru-RU'
    });
    const errors = [];
    page.on('pageerror', (e) => errors.push(e.message));
    await page.addInitScript(() => {
      window.CYTV = { snapshot: () => '[]', hasKey: () => false };
    });
    await page.goto(
      'file://' +
        path.resolve(__dirname, '../app/src/main/assets/ui/index.html')
    );
    await page.evaluate(() => {
      receiveNative({
        kind: 'started',
        config: { host: '192.0.2.10', edition: 'root', action: 'doctor' }
      });
      for (const [id, status, label] of [
        ['ssh', 'pass', 'SSH'],
        ['python3', 'fail', 'Python 3.9+'],
        ['node-version', 'fail', 'Node.js 8+'],
        ['pairing', 'pending', 'Сопряжение']
      ])
        receiveNative({
          kind: 'check',
          checkId: id,
          status,
          label,
          statusText: status,
          detail: '<details>'
        });
      receiveNative({
        kind: 'check',
        checkId: 'ssh',
        status: 'pass',
        label: 'SSH',
        statusText: 'Пройдено',
        detail: ''
      });
    });
    assert.equal(
      await page.locator('.tv-checks li').count(),
      4,
      'show checks without duplicate rows'
    );
    await page.evaluate(() => {
      receiveNative({ kind: 'error', text: 'Root requirements failed' });
      receiveNative({ kind: 'finished', code: 2 });
    });
    assert.equal(
      await page.locator('.tv-checks li[data-status=fail]').count(),
      2
    );
    assert.equal(
      await page.locator('.tv-checks li[data-status=pending]').count(),
      1
    );
    assert.equal(await page.locator('.tv-checks').isVisible(), true);
    assert.equal(
      await page.locator('.tv-checks details').count(),
      0,
      'escape detail text'
    );
    assert.equal(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth
      ),
      true
    );
    await page.evaluate(() =>
      receiveNative({
        kind: 'started',
        config: { host: '192.0.2.10', edition: 'no-root', action: 'install' }
      })
    );
    assert.equal(
      await page.locator('.tv-checks li').count(),
      0,
      'new run clears old checks'
    );
    await page.evaluate(() => {
      CYTV.answer = (raw) => {
        window.lastAnswer = JSON.parse(raw);
      };
      CYTV.start = (raw) => {
        window.lastStart = JSON.parse(raw);
      };
      receiveNative({
        kind: 'started',
        config: {
          host: '192.0.2.10',
          edition: 'root',
          port: 22,
          action: 'install'
        }
      });
      receiveNative({
        kind: 'selected-profile',
        profile: {
          host: '192.0.2.10',
          edition: 'no-root',
          port: 22,
          connection: 'root-ssh'
        }
      });
      receiveNative({
        kind: 'question',
        id: 'legacy',
        text: 'Alternative edition [0]: ',
        defaultChoice: '0',
        options: [
          { value: '1', label: 'No-root via root SSH' },
          { value: '2', label: 'Root Beta for Node.js 0.12.2' },
          { value: '0', label: 'Cancel' }
        ]
      });
    });
    await page.waitForFunction(
      () => document.activeElement?.dataset.value === '0'
    );
    assert.match(await page.locator('.target').textContent(), /No-root/);
    await page.locator('[data-action=choice-prompt][data-value="0"]').click();
    assert.equal(await page.evaluate(() => lastAnswer.value), '0');
    await page.evaluate(() => {
      receiveNative({ kind: 'finished', code: 0 });
      action = 'status';
      start(true);
    });
    assert.equal(await page.evaluate(() => lastStart.connection), 'root-ssh');
    assert.equal(await page.evaluate(() => lastStart.edition), 'no-root');
    await page.evaluate(() => {
      receiveNative({
        kind: 'started',
        config: {
          host: '192.0.2.10',
          edition: 'root',
          port: 22,
          action: 'install'
        }
      });
      receiveNative({
        kind: 'selected-profile',
        profile: {
          host: '192.0.2.10',
          edition: 'root',
          port: 22,
          root_variant: 'node012-beta'
        }
      });
    });
    assert.match(await page.locator('.target').textContent(), /Root Beta/);
    assert.deepEqual(errors, []);
    console.log(
      'Android checks: updates, retained failures, pending steps, escaping and reset passed.'
    );
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
