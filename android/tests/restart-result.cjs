const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
let browser;
(async () => {
  browser = await chromium.launch({
    headless: true,
    executablePath:
      process.env.CYTV_CHROME ||
      '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
  });
  const page = await browser.newPage({
    locale: 'en',
    viewport: { width: 320, height: 740 }
  });
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.addInitScript(() => {
    window.requests = [];
    window.CYTV = {
      snapshot: () => sessionStorage.getItem('operation-events') || '[]',
      hasKey: () => true,
      start: (raw) => requests.push(JSON.parse(raw)),
      answer: () => {}
    };
  });
  await page.goto(
    'file://' + path.resolve(__dirname, '../app/src/main/assets/ui/index.html')
  );
  for (const [edition, port] of [
    ['root', 2222],
    ['no-root', 9922]
  ]) {
    const config = {
      host: '192.0.2.10',
      edition,
      port,
      action: 'uninstall',
      language: 'en',
      useImportedKey: edition === 'root'
    };
    const started = { kind: 'started', config };
    const terminal = [
      {
        kind: 'recovery-plan',
        state: 'waiting',
        disposition: 'clean-removal',
        removed: false,
        verified_clean: false,
        restart_required: true,
        removal_action: {
          action: 'retry-removal',
          condition: 'restart',
          requires_change: true
        },
        actions: ['continue-removal'],
        titleText: 'Restart the TV to finish removal',
        blockerText: 'Disconnect it from power and choose Try again.'
      },
      { kind: 'finished', code: 0 }
    ];
    await page.evaluate((event) => {
      // Operation.snapshot() returns a JSON array of serialized events.
      sessionStorage.setItem(
        'operation-events',
        JSON.stringify([JSON.stringify(event)])
      );
    }, started);
    await page.setViewportSize({ width: 740, height: 320 });
    await page.reload();
    assert.equal(await page.locator('[role=progressbar]').count(), 1);
    assert.equal(
      await page.locator('h1').innerText(),
      'Uninstall Clean Your TV'
    );
    assert.deepEqual(await page.evaluate(() => requests), []);

    // The existing Activity gets callbacks even while its WebView is hidden.
    await page.evaluate((events) => {
      Object.defineProperty(document, 'hidden', {
        configurable: true,
        value: true
      });
      document.dispatchEvent(new Event('visibilitychange'));
      for (const event of events) receiveNative(event);
      delete document.hidden;
      document.dispatchEvent(new Event('visibilitychange'));
    }, terminal);
    assert.equal(await page.locator('[data-action=retry-removal]').count(), 0);
    assert.equal(await page.locator('[data-action=recover]').count(), 1);
    assert.equal(
      await page.locator('h1').innerText(),
      'Review recovery options'
    );
    assert.deepEqual(await page.evaluate(() => requests), []);

    await page.evaluate(
      (events) => {
        sessionStorage.setItem(
          'operation-events',
          JSON.stringify(events.map((event) => JSON.stringify(event)))
        );
      },
      [started, ...terminal]
    );
    await page.setViewportSize({ width: 320, height: 740 });
    await page.reload();
    assert.equal(
      await page.locator('h1').innerText(),
      'Review recovery options'
    );
    assert.equal(await page.locator('[data-action=retry-removal]').count(), 0);
    assert.match(
      await page.locator('.recovery-info').innerText(),
      /check the TV state/i
    );
    assert.deepEqual(await page.evaluate(() => requests), []);
    await page.getByRole('button', { name: 'Review recovery options' }).click();
    const recovery = { ...config, action: 'recover' };
    assert.deepEqual(await page.evaluate(() => requests), [recovery]);

    // A failed connection can replace an earlier restart result, including
    // during a removal whose retained reason was projected as recheck-required.
    const failedAction = edition === 'root' ? 'recover' : 'uninstall';
    await page.evaluate(
      (config) => {
        receiveNative({ kind: 'started', config });
        receiveNative({
          kind: 'recovery-plan',
          state: 'blocked',
          disposition: 'clean-removal',
          restart_required: false,
          reason:
            config.action === 'recover'
              ? 'connection-interrupted'
              : 'removal-recheck-required',
          connection_failure: true,
          removal_action: {
            action: 'retry-removal',
            condition: 'transient',
            requires_change: false
          }
        });
        receiveNative({ kind: 'finished', code: 2 });
      },
      { ...config, action: failedAction }
    );
    if (edition === 'root') {
      await page.getByRole('button', { name: 'Try again' }).click();
    } else {
      await page.locator('[data-action=to-connection]').click();
      await page.locator('[data-action=start]').click();
    }
    assert.deepEqual(await page.evaluate(() => requests), [recovery, recovery]);
  }
  const variants = [
    { restart_required: true },
    { removal: { stage: 'restart-required' } },
    { restart_required: false, removal: { stage: 'restart-required' } },
    {
      restart_required: false,
      removal: { stage: 'package-removal', reason: 'restart-required' }
    },
    { restart_required: false, reason: 'restart-required' }
  ];
  for (const variant of variants) {
    await page.evaluate((variant) => {
      receiveNative({
        kind: 'started',
        config: { host: '192.0.2.10', edition: 'root', action: 'uninstall' }
      });
      receiveNative({
        kind: 'recovery-plan',
        state: 'complete',
        disposition: 'clean-removal',
        removed: true,
        verified_clean: true,
        summary: 'Stale complete flags',
        nextStep: 'Try again',
        ...variant
      });
      receiveNative({ kind: 'finished', code: 0 });
    }, variant);
    assert.equal(
      await page.locator('.review-symbol').count(),
      1,
      JSON.stringify(variant)
    );
    assert.equal(
      await page.locator('h1').innerText(),
      'Restart the TV to finish removal'
    );
    assert(
      (await page.locator('.recovery-info').innerText()).includes(
        'disconnect it from power'
      )
    );
  }
  for (const [code, nextStep] of [
    [
      'ssh-unreachable',
      'Connection to the TV was interrupted. Check the connection and try again.'
    ],
    ['ssh-access-denied', 'Check network permissions.'],
    ['ssh-refused', 'Check the SSH port.'],
    ['ssh-timeout', 'Check the TV network.'],
    ['ssh-auth-root', 'Check your Root SSH key.'],
    ['developer-key-server', 'Enable Key Server on the TV.']
  ]) {
    await page.evaluate(
      ({ code, nextStep }) => {
        receiveNative({
          kind: 'started',
          config: { host: '192.0.2.10', edition: 'root', action: 'uninstall' }
        });
        receiveNative({
          kind: 'recovery-plan',
          state: 'complete',
          disposition: 'clean-removal',
          removed: true,
          verified_clean: true,
          restart_required: true,
          removal: { stage: 'restart-required' },
          summary: 'Old restart state',
          nextStep: 'Old restart guidance'
        });
        receiveNative({ kind: 'failure-help', code, nextStep });
        receiveNative({ kind: 'finished', code: 0 });
        receiveNative({ kind: 'report-ready' });
      },
      { code, nextStep }
    );
    assert.equal(
      await page.locator('.review-symbol').count(),
      1,
      'connection advice does not override the restart completion gate'
    );
    assert.equal(
      await page.locator('h1').innerText(),
      'Check the TV connection to continue removal'
    );
    assert(
      (await page.locator('.recovery-info').innerText()).includes(nextStep)
    );
    assert(
      !(await page.locator('.recovery-info').innerText()).includes(
        'disconnect it from power'
      )
    );
    assert.equal(
      await page.locator('[data-action=check-status].primary').count(),
      1
    );
    assert.equal(
      await page.locator('[data-action=save-report].secondary').count(),
      1
    );
    assert.equal(await page.locator('footer button.primary').count(), 1);
  }
  await page.evaluate(() => {
    receiveNative({
      kind: 'started',
      config: { host: '192.0.2.10', edition: 'root', action: 'uninstall' }
    });
    receiveNative({ kind: 'finished', code: 1 });
    receiveNative({ kind: 'report-ready' });
  });
  assert.equal(await page.locator('[data-action=retry-removal]').count(), 0);
  assert.equal(
    await page.locator('[data-action=save-report].primary').count(),
    1,
    'report remains primary when no removal Retry is available'
  );
  for (const malformed of [
    'PRIVATE',
    ['PRIVATE'],
    true,
    1,
    { stage: ['PRIVATE'], reason: { PRIVATE: 1 } }
  ]) {
    await page.evaluate((removal) => {
      receiveNative({
        kind: 'started',
        config: { host: '192.0.2.10', edition: 'root', action: 'uninstall' }
      });
      receiveNative({
        kind: 'recovery-plan',
        state: 'waiting',
        disposition: 'clean-removal',
        removed: false,
        verified_clean: false,
        removal,
        summary: 'Removal is not finished yet.',
        nextStep: 'Try again'
      });
      receiveNative({ kind: 'finished', code: 0 });
    }, malformed);
    assert.equal(await page.locator('.review-symbol').count(), 1);
    assert.equal(
      await page.locator('h1').innerText(),
      'Removal is not finished yet.'
    );
  }
  await page.evaluate(() => {
    receiveNative({
      kind: 'started',
      config: { host: '192.0.2.10', edition: 'root', action: 'uninstall' }
    });
    receiveNative({
      kind: 'recovery-plan',
      state: 'complete',
      disposition: 'clean-removal',
      removed: true,
      verified_clean: true,
      stageText: 'Restart the TV to finish removal',
      summary: 'Verified current cleanup',
      nextStep: 'Done'
    });
    receiveNative({ kind: 'finished', code: 0 });
  });
  assert.equal(
    await page.locator('.review-symbol').count(),
    0,
    'translated prose is not restart authority'
  );
  assert.equal(
    await page.locator('h1').innerText(),
    'Verified current cleanup'
  );
  await page.evaluate(() => {
    receiveNative({
      kind: 'started',
      config: { host: '192.0.2.10', edition: 'root', action: 'install' }
    });
    receiveNative({
      kind: 'recovery-plan',
      state: 'complete',
      disposition: 'home-off',
      summary: 'Root setup finished with LG Home and Home control off.',
      nextStep: 'Keep LG Home active.'
    });
    receiveNative({ kind: 'finished', code: 0 });
  });
  assert.equal(await page.locator('.review-symbol').count(), 0);
  assert.equal(
    await page.locator('h1').innerText(),
    'Root setup finished with LG Home and Home control off.'
  );
  assert.deepEqual(errors, []);
  await browser.close();
  console.log(
    'PASS removal restart semantics: native snapshot, rotation, background return, guarded reconnect, five contradictory completion variants, five malformed shapes, current connection/auth priority, safe status fallback/report behavior, semantic-only cleanup proof and unchanged Home-off completion'
  );
})().catch(async (error) => {
  console.error(error);
  if (browser) await browser.close();
  process.exitCode = 1;
});
