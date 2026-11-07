const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const root = path.resolve(__dirname, '../..');
const journeys = JSON.parse(
  execFileSync(
    process.env.CYTV_PYTHON || 'python3',
    ['-m', 'android.tests.recovery_events'],
    { cwd: root, encoding: 'utf8' }
  )
);
let browser;
(async () => {
  browser = await chromium.launch({
    headless: true,
    executablePath:
      process.env.CYTV_CHROME ||
      '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
  });
  for (const [name, journey] of Object.entries(journeys)) {
    const page = await browser.newPage({
      locale: 'en',
      viewport: { width: 320, height: 740 },
      reducedMotion: 'reduce'
    });
    await page.addInitScript(
      () =>
        (window.CYTV = {
          hasKey: () => false,
          snapshot: () => '[]',
          answer: () => {}
        })
    );
    await page.goto(
      'file://' + path.join(root, 'android/app/src/main/assets/ui/index.html')
    );
    await page.evaluate((journey) => {
      receiveNative({
        kind: 'started',
        config: {
          host: '192.0.2.10',
          edition: journey.edition,
          action: 'recover'
        }
      });
      if (journey.code === 130)
        receiveNative({
          kind: 'recovery-plan',
          state: 'waiting',
          disposition: 'clean-removal',
          summary: 'Removal has been requested.',
          nextStep: 'Connect to the TV to continue cleanup.'
        });
      for (const event of journey.events) receiveNative(event);
      receiveNative({ kind: 'finished', code: journey.code });
    }, journey);
    const plan = journey.events
      .filter((e) => e.kind === 'recovery-plan')
      .at(-1);
    const complete = journey.code === 0 && plan?.state === 'complete';
    assert.equal(
      await page.locator('.review-symbol').count(),
      (plan || journey.code === 130) && !complete ? 1 : 0,
      name
    );
    assert.equal(
      await page.locator('h1').innerText(),
      complete
        ? plan.summary
        : plan
          ? 'Review recovery options'
          : 'Operation cancelled',
      name
    );
    assert.equal(
      await page.locator('[data-action=restore],[data-action=status]').count(),
      0,
      name
    );
    assert.equal(await page.locator('.gesture').count(), 0, name);
    if (journey.pending)
      assert(!complete, name + ' pending operation presented as completed');
    for (const [width, height] of [
      [320, 740],
      [740, 375]
    ]) {
      await page.setViewportSize({ width, height });
      assert(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth
        ),
        name + ' overflow'
      );
    }
    await page.close();
  }
  await browser.close();
  console.log(
    'PASS Android recovery journey: real CLI/Store/assessment, original detached observer continuation, LG Home completion, retain, legacy unknown, running worker and cancelled authentication'
  );
})().catch(async (error) => {
  console.error(error);
  if (browser) await browser.close();
  process.exitCode = 1;
});
