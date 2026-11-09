'use strict';
const { chromium } = require('playwright'),
  fs = require('node:fs'),
  path = require('node:path'),
  assert = require('node:assert/strict'),
  { pathToFileURL } = require('node:url');
const site = path.resolve(process.env.WEATHER_SITE || 'build/tests/weather-ui');
if (!process.env.WEATHER_SITE) {
  const cp = require('node:child_process');
  cp.execFileSync(
    process.env.PYTHON || path.resolve('.venv-cytv/bin/python'),
    ['scripts/preview.py', '--build', site],
    { stdio: 'pipe' }
  );
  for (const edition of ['launcher', 'root-launcher']) {
    const folder = path.join(site, edition),
      sources = {};
    function walk(dir) {
      for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
        const file = path.join(dir, e.name);
        if (e.isDirectory()) walk(file);
        else if (/\.(js|css|html)$/.test(file))
          sources[path.relative(folder, file)] = fs.readFileSync(file, 'utf8');
      }
    }
    walk(folder);
    const compiled = JSON.parse(
      cp.execFileSync(process.execPath, ['scripts/compile-tv-web.cjs'], {
        input: JSON.stringify(sources),
        maxBuffer: 64 * 1024 * 1024
      })
    );
    for (const [name, content] of Object.entries(compiled))
      fs.writeFileSync(path.join(folder, name), content);
  }
}
const city = {
  id: 2950159,
  name: 'Berlin',
  latitude: 52.52,
  longitude: 13.41,
  country: 'Germany',
  admin1: 'Berlin'
};
const weather = {
  timezone: 'Europe/Berlin',
  utc_offset_seconds: 3600,
  current: {
    temperature_2m: 8,
    apparent_temperature: 5,
    weather_code: 3,
    is_day: 1,
    wind_speed_10m: 4,
    relative_humidity_2m: 70
  },
  daily: {
    time: ['2026-11-09', '2026-11-10', '2026-11-11', '2026-11-12'],
    temperature_2m_min: [3, 4, 2, 1],
    temperature_2m_max: [8, 9, 7, 6],
    weather_code: [3, 61, 0, 45],
    precipitation_probability_max: [20, 50, 0, 5]
  }
};
(async () => {
  const browser = await chromium.launch({ headless: true });
  const results = [];
  for (const edition of ['launcher', 'root-launcher']) {
    const page = await browser.newPage({
        viewport: { width: 1920, height: 1080 },
        locale: 'en-US'
      }),
      errors = [],
      calls = [];
    page.on('pageerror', (e) => errors.push(e.message));
    await page.route(/^https?:/, (r) => {
      const url = r.request().url();
      calls.push(url.split('?')[0]);
      if (url.includes('geocoding-api'))
        return r.fulfill({
          json: url.includes('/search') ? { results: [city] } : city
        });
      if (url.includes('api.open-meteo')) return r.fulfill({ json: weather });
      if (url.includes('get.geojs.io'))
        return r.fulfill({
          json: {
            city: 'Berlin',
            country_code: 'DE',
            latitude: '52.52',
            longitude: '13.41'
          }
        });
      return r.abort();
    });
    await page.goto(pathToFileURL(path.join(site, edition, 'index.html')).href);
    await page.waitForFunction(
      () => window.RootLauncherRendered && window.HomeWeather
    );
    await page.evaluate(() => document.fonts.ready);
    assert.equal(calls.filter((u) => /open-meteo|geojs/.test(u)).length, 0);
    await page.evaluate(() => {
      RenewalPanel.open();
      document.querySelector('[data-category="weather"]').click();
    });
    await page.waitForTimeout(70);
    const order = await page
      .locator('[role=tab]')
      .evaluateAll((a) => a.map((n) => n.dataset.category));
    assert.equal(order.indexOf('weather'), order.indexOf('wallpapers') + 1);
    assert.equal(await page.locator('.weather-options').isVisible(), false);
    await page.locator('.weather-enabled').click();
    await page.waitForTimeout(70);
    assert.equal(await page.locator('.weather-live-preview').isVisible(), true);
    assert.equal(await page.locator('#homeWeather').isVisible(), false);
    await page.locator('.weather-city-summary').click();
    await page.locator('.weather-city-search input').fill('Berlin');
    await page.locator('.weather-city-search input').press('Enter');
    await page.locator('.weather-city-results button').click();
    await page.waitForFunction(() => HomeWeather.store.state().data);
    assert.equal(await page.locator('.weather-city-dialog').isVisible(), false);
    await page.locator('[data-weather-choice="forecast"]').click();
    await page.waitForTimeout(70);
    assert.equal(await page.locator('#weatherPreview .weather-row').count(), 4);
    assert.equal(await page.locator('#homeWeather .weather-row').count(), 4);
    await page.locator('.settings-footer button:visible').click();
    await page.waitForTimeout(100);
    const layout = await page.evaluate(() => {
      const w = HomeViewport.rect(document.getElementById('homeWeather'));
      return {
        weather: w,
        overlaps: [
          'clock',
          'topButtons',
          'dockBand',
          'inputShelf',
          'hero'
        ].filter((id) => {
          const e = document.getElementById(id);
          if (
            !e ||
            !e.offsetHeight ||
            getComputedStyle(e).display === 'none' ||
            getComputedStyle(e).opacity === '0'
          )
            return false;
          const r = HomeViewport.rect(e);
          return (
            w.left < r.right - 2 &&
            w.right > r.left + 2 &&
            w.top < r.bottom - 2 &&
            w.bottom > r.top + 2
          );
        })
      };
    });
    assert.deepEqual(layout.overlaps, [], JSON.stringify(layout));
    await page.screenshot({
      path: path.join(site, 'weather-' + edition + '.png')
    });
    await page.keyboard.press('ArrowDown');
    await page.waitForTimeout(400);
    assert.equal(
      await page
        .locator('body')
        .evaluate((e) => e.classList.contains('weather-scrolled')),
      true
    );
    assert.equal(
      await page
        .locator('body')
        .evaluate((e) => e.classList.contains('scrolled')),
      false
    );
    await page.keyboard.press('ArrowUp');
    await page.waitForTimeout(400);
    assert.equal(
      await page
        .locator('body')
        .evaluate((e) => e.classList.contains('weather-scrolled')),
      false
    );
    await page.evaluate(() => {
      RenewalPanel.open();
      document.querySelector('[data-category="weather"]').click();
    });
    await page.locator('[data-weather-unit="metric"]').focus();
    await page.keyboard.press('ArrowRight');
    await page.keyboard.press('Enter');
    await page.waitForFunction(
      () => HomeWeather.store.state().units === 'imperial'
    );
    await page.locator('.weather-city-summary').click();
    await page.keyboard.press('Escape');
    assert.equal(
      await page
        .locator('.weather-city-summary')
        .evaluate((e) => document.activeElement === e),
      true
    );
    await page.locator('.weather-enabled').click();
    await page.locator('.weather-options').waitFor({ state: 'hidden' });
    assert.equal(await page.locator('.weather-options').isVisible(), false);
    assert.equal(
      await page.locator('.weather-live-preview').isVisible(),
      false
    );
    assert.deepEqual(errors, []);
    results.push({
      edition,
      calls: calls.filter((u) => /open-meteo|geojs/.test(u)).length,
      layout
    });
    await page.close();
  }
  await browser.close();
  console.log(JSON.stringify({ results }, null, 2));
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
