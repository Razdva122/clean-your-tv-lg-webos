// Real UI and original reference app bytes with simulated services; no device/network access.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { execFileSync } = require('node:child_process');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = path.resolve(__dirname, '../..');

function stage(name = process.env.THEME_STAGE || 'site') {
  const site = path.join(root, 'build/tests/themes', name);
  execFileSync(
    process.env.PYTHON || 'python3',
    ['scripts/preview.py', '--build', site],
    {
      cwd: root
    }
  );
  return site;
}

async function open(browser, site, edition, columns = 5) {
  const page = await browser.newPage({
    viewport: { width: 1920, height: 1080 },
    locale: 'en-US'
  });
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.mouse.move(0, 0);
  await page.clock.setFixedTime(new Date('2026-10-28T12:00:00Z'));
  await page.route('**/config.js', (route) =>
    route.fulfill({
      body:
        'window.CONFIG=' +
        JSON.stringify({
          columns,
          dockApps: [],
          hiddenApps: ['com.webos.app.browser'],
          liveTvApp: 'preview.live'
        }) +
        ';'
    })
  );
  // Keep one real app off Home so the library state has an available choice.
  // Inputs are explicit browser simulations, separate from captured app metadata.
  const inventory = JSON.parse(
    fs.readFileSync(path.join(root, 'preview/reference-apps/inventory.json'))
  );
  inventory.referenceApps = true;
  inventory.inputs = [{ label: 'HDMI 1 · Console', appId: 'preview.hdmi1' }];
  await page.route('**/apps.js', (route) =>
    route.fulfill({ body: 'window.TV_APPS=' + JSON.stringify(inventory) + ';' })
  );
  await page.route(/^https?:/, (route) => route.abort());
  await page.goto(pathToFileURL(path.join(site, edition, 'index.html')).href);
  await page.locator('#tiles .focused').waitFor();
  await page.evaluate(() => document.fonts.ready);
  await page.addStyleTag({
    content: '* { transition: none !important; animation: none !important; }'
  });
  // Both edition bootstraps and preview service replies have completed.
  await page.waitForTimeout(150);
  return { page, errors };
}

async function states(page, visit) {
  await visit('dock');
  await page.keyboard.press('ArrowDown');
  await visit('grid');
  await page.keyboard.press('ArrowUp');
  await page.keyboard.press('ArrowRight');
  await visit('focused');
  await page.keyboard.down('Enter');
  await page.waitForTimeout(700);
  await page.keyboard.up('Enter');
  assert.equal(await page.locator('#tiles .moving').count(), 1);
  await visit('reorder');
  await page.keyboard.press('Escape');
  await page.locator('.add-app').hover();
  assert.equal(
    await page.locator('.add-app.focused').count(),
    1,
    'real pointer focuses Add app'
  );
  await visit('add-app');
  await page.locator('.add-app').click();
  await page.locator('#appPicker .app-choice').waitFor();
  // Remote navigation must not race hover when tiles move beneath the pointer
  // left at Add app by the preceding click (same guard as launcher-geometry).
  await page.mouse.move(0, 0);
  await visit('library');
  await page.keyboard.press('Escape');
  for (let row = 0; row < 12; row++) await page.keyboard.press('ArrowUp');
  await page.locator('#btnInputs').click();
  await visit('inputs');
  await page.keyboard.press('Escape');
  await page.locator('#btnSettings').click();
  await visit('settings');
  await page.evaluate(() =>
    HomeI18n.confirm(
      {
        title: 'Test confirmation',
        message: 'Synthetic browser fixture.',
        action: 'Continue'
      },
      function () {}
    )
  );
  await visit('confirmation');
  await page.keyboard.press('Escape');
  await page.keyboard.press('Escape');
}

module.exports = { assert, fs, path, chromium, root, stage, open, states };
