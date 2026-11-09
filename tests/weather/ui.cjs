'use strict';
const { chromium } = require('playwright'),
  fs = require('node:fs'),
  path = require('node:path'),
  assert = require('node:assert/strict'),
  { pathToFileURL } = require('node:url');
const site = path.resolve(process.env.WEATHER_SITE || 'build/tests/weather-ui');
if (!process.env.WEATHER_SITE) {
  const cp = require('node:child_process'),
    localPython = path.resolve(
      '.venv-cytv',
      process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python'
    );
  cp.execFileSync(
    process.env.PYTHON ||
      (fs.existsSync(localPython) ? localPython : 'python3'),
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
  admin1: 'Berlin',
  timezone: 'Asia/Tokyo'
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
    let geoLocation = {
      city: 'Berlin',
      country_code: 'DE',
      latitude: '52.52',
      longitude: '13.41'
    };
    await page.clock.install({ time: new Date('2026-11-09T18:30:00Z') });
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
          json: geoLocation
        });
      return r.abort();
    });
    await page.addInitScript(() => {
      window.installWeatherBridge = () => {
        window.weatherBridgeCalls = [];
        window.weatherBridgeFail = false;
        window.weatherBridgeHold = false;
        window.PalmServiceBridge = function () {
          this.cancel = () => {
            this.cancelled = true;
          };
          this.call = (uri, body) => {
            if (!/weatherForecast/.test(uri)) {
              setTimeout(
                () => this.onservicecallback?.('{"returnValue":false}'),
                0
              );
              return;
            }
            window.weatherBridgeCalls.push({ uri, body: JSON.parse(body) });
            if (/Cancel$/.test(uri) || window.weatherBridgeHold) return;
            const forecast = {
              properties: {
                meta: {
                  updated_at: new Date(
                    Math.floor(Date.now() / 1000) * 1000 - 4.5 * 3600000
                  ).toISOString(),
                  units: {
                    air_temperature: 'celsius',
                    wind_speed: 'm/s',
                    relative_humidity: '%'
                  }
                },
                timeseries: Array.from({ length: 4 }, (_, i) => ({
                  time: new Date(
                    Math.floor(Date.now() / 1000) * 1000 + i * 86400000
                  ).toISOString(),
                  data: {
                    instant: {
                      details: {
                        air_temperature: 8 + i,
                        wind_speed: 4,
                        relative_humidity: 70
                      }
                    },
                    next_1_hours: { summary: { symbol_code: 'cloudy' } }
                  }
                }))
              }
            };
            setTimeout(
              () =>
                this.onservicecallback?.(
                  JSON.stringify(
                    window.weatherBridgeFail
                      ? { returnValue: false }
                      : { returnValue: true, forecast }
                  )
                ),
              0
            );
          };
        };
      };
    });
    await page.goto(pathToFileURL(path.join(site, edition, 'index.html')).href);
    await page.waitForFunction(
      () => window.RootLauncherRendered && window.HomeWeather
    );
    await page.evaluate(() => document.fonts.ready);
    await page.evaluate(() => installWeatherBridge());
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
    const sources = page.locator('.weather-sources-button');
    assert.equal(
      await sources.isVisible(),
      true,
      'sources stay accessible while weather is off'
    );
    assert.equal(
      await page.locator('[data-weather-provider]:visible').count(),
      3
    );
    await page.locator('[data-weather-provider="met-no"]').click();
    assert.equal(
      await page.evaluate(() => weatherBridgeCalls.length),
      0,
      'source can be chosen while Off'
    );
    await page.waitForFunction(
      () =>
        document
          .querySelector('[data-weather-provider="met-no"]')
          .getAttribute('aria-pressed') === 'true'
    );
    await page.locator('.weather-enabled').focus();
    await page.keyboard.press('ArrowRight');
    assert.equal(
      await page
        .locator('[data-weather-provider="met-no"]')
        .evaluate((e) => e === document.activeElement),
      true,
      'Right enters source controls from weather switch'
    );
    await page.locator('[data-weather-provider="auto"]').focus();
    await page.keyboard.press('ArrowLeft');
    assert.equal(
      await page
        .locator('.weather-enabled')
        .evaluate((e) => e === document.activeElement),
      true,
      'Left returns to switch from source controls'
    );
    await sources.click();
    const dialog = page.locator('.weather-sources-dialog');
    assert.equal(await dialog.getAttribute('role'), 'dialog');
    assert.equal(await dialog.locator('a').count(), 8);
    assert.equal(
      await dialog.locator('a').first().getAttribute('href'),
      'https://www.met.no/'
    );
    await page.keyboard.press('Escape');
    assert.equal(
      await sources.evaluate((e) => document.activeElement === e),
      true
    );
    await page.locator('.weather-enabled').click();
    await page.waitForTimeout(70);
    assert.equal(await page.locator('.weather-live-preview').isVisible(), true);
    assert.equal(await page.locator('#homeWeather').isVisible(), false);
    await page.locator('[data-weather-choice="text"]').click();
    await page.waitForTimeout(70);
    const compactPreview = await page.evaluate(() => {
      const preview = document.getElementById('weatherPreview'),
        area = document.querySelector('.weather-preview-window'),
        p = preview.getBoundingClientRect(),
        a = area.getBoundingClientRect();
      return {
        inlineIcons: preview.querySelectorAll('svg').length,
        width: p.width,
        inside:
          p.left >= a.left - 2 &&
          p.top >= a.top - 2 &&
          p.right <= a.right + 2 &&
          p.bottom <= a.bottom + 2
      };
    });
    assert(compactPreview.inlineIcons > 0, 'Compact uses the real inline SVG');
    assert(
      compactPreview.width > 0 && compactPreview.inside,
      'Compact SVG preview fits its window ' + JSON.stringify(compactPreview)
    );
    await page.locator('.weather-city-summary').click();
    await page.locator('.weather-city-search input').fill('Berlin');
    await page.locator('.weather-city-search input').press('Enter');
    await page.locator('.weather-city-results button').click();
    await page.waitForFunction(() => HomeWeather.store.state().data);
    assert.equal(
      await page.locator('[aria-labelledby="weather-city-title"]').isVisible(),
      false
    );
    assert.equal(
      await page.evaluate(() => HomeWeather.store.state().source),
      'met-no'
    );
    await page.waitForFunction(() =>
      document
        .querySelector('.weather-actual-source')
        .textContent.includes('MET Norway')
    );
    assert.match(
      await page.locator('.weather-actual-source').innerText(),
      /MET Norway/
    );
    assert.equal(
      await page.evaluate(() => weatherBridgeCalls[0].uri),
      'luna://' +
        (edition === 'root-launcher'
          ? 'com.cleanyourtv.root.preview.service'
          : 'com.gathin.tvhome.renewal') +
        '/weatherForecast'
    );
    await page.locator('[data-weather-choice="forecast"]').click();
    await page.waitForTimeout(70);
    assert.equal(
      await page.locator('#homeWeather .ctv-weather-day').first().innerText(),
      'Today',
      'MET local calendar day around UTC midnight'
    );
    await page.locator('[data-weather-provider="met-no"]').focus();
    await page.keyboard.press('ArrowRight');
    assert.equal(
      await page
        .locator('[data-weather-provider="open-meteo"]')
        .evaluate((e) => e === document.activeElement),
      true
    );
    await page.keyboard.press('Enter');
    await page.waitForFunction(
      () => HomeWeather.store.state().source === 'open-meteo'
    );
    await page.locator('[data-weather-provider="auto"]').click();
    await page.waitForFunction(
      () => HomeWeather.store.state().provider === 'auto'
    );
    await page.locator('[data-weather-choice="forecast"]').click();
    await page.waitForTimeout(70);
    assert.equal(await page.locator('#weatherPreview .weather-row').count(), 4);
    assert.equal(await page.locator('#homeWeather .weather-row').count(), 4);
    assert.equal(
      await page.locator('.weather-credit').count(),
      0,
      'providers are not repeated in widgets'
    );
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
    await page.locator('[data-weather-provider="auto"]').focus();
    await page.keyboard.press('Escape');
    assert.equal(
      await page
        .locator('[data-category="weather"]')
        .evaluate((e) => e === document.activeElement),
      true,
      'Back returns from source controls to category'
    );
    await page.keyboard.press('Escape');
    assert.equal(
      await page.locator('.weather-settings').isVisible(),
      false,
      'second Back exits settings'
    );
    await page.evaluate(() => {
      RenewalPanel.open();
      document.querySelector('[data-category="weather"]').click();
    });
    await page.locator('.weather-city-summary').click();
    await page.keyboard.press('Escape');
    assert.equal(
      await page
        .locator('.weather-city-summary')
        .evaluate((e) => document.activeElement === e),
      true
    );
    await page.evaluate(() => {
      document.querySelector('.settings-footer button').click();
      HomeWeather.store.setPreferences({ preferred: 'forecast' });
      HomeLayoutState.setThemeLayout({
        preset: 'channel-list',
        columns: 1,
        spacingScale: 1,
        textScale: 1,
        focusScale: 1.1,
        allowColumnOverride: false
      });
    });
    await page.waitForTimeout(100);
    const checkChannel = async () => {
      const rects = await page.evaluate(() => ({
        hero: HomeViewport.rect(document.getElementById('hero')),
        weather: HomeViewport.rect(document.getElementById('homeWeather'))
      }));
      assert(
        rects.hero.top >= rects.weather.bottom + 30,
        'channel title stays below weather ' + JSON.stringify(rects)
      );
    };
    await checkChannel();
    await page.keyboard.press('ArrowDown');
    await page.keyboard.press('ArrowUp');
    await checkChannel();
    await page.evaluate(() => {
      ThemeRuntime.reset();
      RenewalPanel.open();
      document.querySelector('[data-category="weather"]').click();
    });
    await page.locator('.weather-enabled').click();
    await page.locator('.weather-options').waitFor({ state: 'hidden' });
    assert.equal(await page.locator('.weather-options').isVisible(), false);
    assert.equal(
      await page.locator('.weather-live-preview').isVisible(),
      false
    );
    assert.equal(
      await page.locator('#hero').evaluate((e) => e.style.whiteSpace),
      '',
      'weather typography cleanup after Off'
    );
    await page.evaluate(() => {
      HomeWeather.store.clear();
      weatherBridgeFail = true;
      HomeWeather.store.setPreferences({ provider: 'met-no', enabled: true });
      HomeWeather.store.setMode('auto');
    });
    const omBefore = calls.filter((u) => /api.open-meteo/.test(u)).length;
    await page.waitForFunction(
      () => HomeWeather.store.state().status === 'error'
    );
    assert.equal(
      calls.filter((u) => /api.open-meteo/.test(u)).length,
      omBefore,
      'manual MET failure never silently falls back'
    );
    assert.equal(
      await page.evaluate(() => HomeWeather.store.state().source),
      null
    );
    await page.locator('[data-weather-provider="auto"]').click();
    await page.waitForFunction(
      () => HomeWeather.store.state().source === 'open-meteo'
    );
    await page.waitForFunction(() =>
      document
        .querySelector('.weather-actual-source')
        .textContent.includes('Open-Meteo')
    );
    assert.match(
      await page.locator('.weather-actual-source').innerText(),
      /Open-Meteo/
    );
    // Each cancellation case uses a genuinely different request location.
    // Same-location resume must honor MET admission even though clear() was used.
    for (const [index, lifecycle] of ['hidden', 'pagehide', 'Off'].entries()) {
      geoLocation = { ...geoLocation, latitude: String(53 + index) };
      const nativeBefore = await page.evaluate(() => weatherBridgeCalls.length),
        omBefore = calls.filter((u) => /api.open-meteo/.test(u)).length;
      await page.evaluate(() => {
        HomeWeather.store.clear();
        weatherBridgeFail = false;
        weatherBridgeHold = true;
        HomeWeather.store.setPreferences({ provider: 'auto', enabled: true });
        HomeWeather.store.setMode('auto');
      });
      await page.waitForFunction(
        ({ count, latitude }) => {
          const last = weatherBridgeCalls[weatherBridgeCalls.length - 1];
          return (
            weatherBridgeCalls.length > count &&
            !/Cancel$/.test(last.uri) &&
            last.body.latitude === latitude
          );
        },
        { count: nativeBefore, latitude: Number(geoLocation.latitude) }
      );
      await page.waitForFunction(
        () =>
          document
            .querySelector('.weather-enabled')
            .getAttribute('aria-checked') === 'true'
      );
      const pending = await page.evaluate(
        () => weatherBridgeCalls[weatherBridgeCalls.length - 1]
      );
      if (lifecycle === 'hidden')
        await page.evaluate(() => {
          Object.defineProperty(document, 'visibilityState', {
            configurable: true,
            value: 'hidden'
          });
          document.dispatchEvent(new Event('visibilitychange'));
        });
      else if (lifecycle === 'pagehide')
        await page.evaluate(() => window.dispatchEvent(new Event('pagehide')));
      else await page.locator('.weather-enabled').click();
      await page.waitForFunction((id) => {
        const last = weatherBridgeCalls[weatherBridgeCalls.length - 1];
        return /Cancel$/.test(last.uri) && last.body.id === id;
      }, pending.body.id);
      await page.waitForTimeout(50);
      assert.equal(
        await page.evaluate(() => weatherBridgeCalls.length),
        nativeBefore + 2,
        lifecycle + ' cancels only the original native request'
      );
      assert.equal(
        calls.filter((u) => /api.open-meteo/.test(u)).length,
        omBefore,
        lifecycle + ' cancellation cannot start fallback while disallowed'
      );
      if (lifecycle === 'hidden')
        await page.evaluate(() => {
          Object.defineProperty(document, 'visibilityState', {
            configurable: true,
            value: 'visible'
          });
          document.dispatchEvent(new Event('visibilitychange'));
        });
      else if (lifecycle === 'pagehide')
        await page.evaluate(() => window.dispatchEvent(new Event('pageshow')));
      else await page.locator('.weather-enabled').click();
      // Resuming allows a new Auto refresh. MET stays in cooldown; OM is eligible.
      await page.waitForFunction(
        () => HomeWeather.store.state().source === 'open-meteo'
      );
      await page.waitForTimeout(50);
      assert.equal(
        await page.evaluate(() => weatherBridgeCalls.length),
        nativeBefore + 2,
        lifecycle + ' same-location resume cannot restart MET within cooldown'
      );
      assert.equal(
        calls.filter((u) => /api.open-meteo/.test(u)).length,
        omBefore + 1,
        lifecycle + ' allowed Auto resume makes exactly one Open-Meteo request'
      );
    }
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
