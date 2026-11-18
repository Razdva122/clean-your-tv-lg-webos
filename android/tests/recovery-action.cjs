const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
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
  const page = await browser.newPage({ viewport: { width: 360, height: 740 } });
  await page.addInitScript(() => {
    localStorage.setItem('cytv-language', 'en');
    window.requests = [];
    window.answers = [];
    window.CYTV = {
      snapshot: () => '[]',
      hasKey: () => true,
      answer: (raw) => answers.push(JSON.parse(raw)),
      start: (raw) => requests.push(JSON.parse(raw))
    };
  });
  await page.goto(
    'file://' + path.resolve(__dirname, '../app/src/main/assets/ui/index.html')
  );
  const profile = {
    host: '192.0.2.10',
    edition: 'no-root',
    port: 2222,
    connection: 'root-ssh'
  };
  await page.evaluate((profile) => {
    receiveNative({
      kind: 'started',
      config: { ...profile, action: 'install' }
    });
    receiveNative({
      kind: 'question',
      id: 'storage',
      reason: 'storage-preflight-failed',
      actions: ['retry-storage-check'],
      confirmLabel: 'Retry storage check',
      text: 'Repeat the read-only check on the same TV.',
      defaultNo: true
    });
  }, profile);
  const retry = page.getByRole('button', { name: 'Retry storage check' });
  assert.equal(await retry.count(), 1);
  await retry.click();
  assert.deepEqual(await page.evaluate(() => answers), [
    { id: 'storage', value: 'y' }
  ]);
  assert.deepEqual(await page.evaluate(() => requests), []);

  for (const [plan, useImportedKey] of [
    [
      {
        disposition: 'no-root-package-check',
        reason: 'original-terminal-unknown',
        actions: ['check', 'retain-evidence']
      },
      true
    ],
    [{ state: 'review' }, false]
  ]) {
    await page.evaluate(
      ({ profile, plan, useImportedKey }) => {
        requests.length = 0;
        receiveNative({
          kind: 'started',
          config: { ...profile, action: 'recover', useImportedKey }
        });
        receiveNative({
          kind: 'recovery-plan',
          state: 'blocked',
          summary: 'The TV package result could not be verified.',
          nextStep: 'Keep recovery data.',
          ...plan
        });
        receiveNative({ kind: 'finished', code: 2 });
      },
      { profile, plan, useImportedKey }
    );
    assert.equal(await page.locator('[data-action=recover]').count(), 0);
    await page.getByRole('button', { name: 'Installation status' }).click();
    assert.deepEqual(await page.evaluate(() => requests), [
      {
        ...profile,
        action: 'status',
        language: 'en',
        useImportedKey
      }
    ]);
  }
  for (const edition of ['root', 'no-root']) {
    for (const reason of [
      'cleanup-check-failed',
      'private-cleanup-incomplete',
      'ownership-conflict',
      'unknown',
      'missing-advice',
      'stale-restart',
      'stale-connection',
      'connection-unverified'
    ]) {
      await page.evaluate(
        ({ edition, reason }) => {
          requests.length = 0;
          receiveNative({
            kind: 'started',
            config: {
              host: '192.0.2.10',
              edition,
              action: 'uninstall',
              port: edition === 'root' ? 22 : 9922,
              language: 'en'
            }
          });
          receiveNative({
            kind: 'recovery-plan',
            state: 'blocked',
            disposition: 'clean-removal',
            reason:
              reason === 'stale-connection' ? 'connection-interrupted' : reason,
            connection_failure: reason === 'connection-unverified',
            blockerText:
              'Removal could not be verified. Review recovery options before continuing.',
            summary: 'Removal is not finished yet.',
            nextStep: 'Review recovery options',
            actions: ['continue-removal'],
            removal:
              reason === 'stale-restart'
                ? { stage: 'restart-required' }
                : undefined,
            removal_action:
              reason === 'missing-advice'
                ? undefined
                : {
                    action: 'check',
                    condition: 'unverified',
                    requires_change: true
                  }
          });
          receiveNative({ kind: 'finished', code: 1 });
        },
        { edition, reason }
      );
      assert.equal(
        await page.locator('[data-action=retry-removal]').count(),
        0,
        edition + '/' + reason
      );
      if (reason === 'stale-connection') {
        assert(!(await page.locator('h1').innerText()).includes('connection'));
        assert(
          (await page.locator('.recovery-info').innerText()).includes(
            'Review recovery options'
          )
        );
      }
      if (reason === 'stale-restart') {
        assert(
          !(await page.locator('.recovery-info').innerText()).includes(
            'disconnect it from power'
          )
        );
      }
      if (reason === 'connection-unverified') {
        await page.locator('[data-action=to-connection]').click();
        assert.equal(await page.locator('#host').getAttribute('readonly'), '');
        await page.locator('[data-action=start]').click();
      } else if (reason === 'missing-advice') {
        await page.getByRole('button', { name: 'Installation status' }).click();
      } else await page.locator('[data-action=recover]').click();
      const calls = await page.evaluate(() => requests);
      assert.equal(calls.length, 1);
      assert.equal(
        calls[0].action,
        reason === 'missing-advice' ? 'status' : 'recover'
      );
      assert.equal(calls[0].edition, edition);
      assert.equal(calls[0].host, '192.0.2.10');
      assert.notEqual(calls[0].yes, true);
    }
  }
  await browser.close();
  console.log('Android recovery policy dispatch passed for both editions.');
})().catch(async (error) => {
  if (browser) await browser.close();
  console.error(error);
  process.exit(1);
});
