'use strict';
const fs = require('node:fs'),
  path = require('node:path'),
  assert = require('node:assert/strict'),
  { pathToFileURL } = require('node:url'),
  { chromium } = require('playwright');
const { loadRegistry } = require('../../scripts/check-theme-submissions.cjs');
const site = path.resolve(process.env.WEATHER_SITE || 'build/tests/weather-ui');
const packages = [
  {
    title: 'Classic',
    input: null,
    formats: ['text', 'current', 'details', 'forecast']
  }
];
for (const e of require('../../launcher/builtin-themes.json').themes) {
  const base = path.dirname(path.resolve('launcher', e.url));
  add(base);
}
for (const e of loadRegistry(path.resolve('showcase')).filter(
  (e) => !e.record.availability
))
  add(path.resolve('showcase', e.base));
function add(base) {
  const m = JSON.parse(fs.readFileSync(path.join(base, 'cytv-theme.json')));
  packages.push({
    title: m.title,
    formats: m.layout.ribbon ? [] : m.layout.weather.formats,
    input: {
      manifest: m,
      rules: JSON.parse(fs.readFileSync(path.join(base, m.rules.path))),
      assetHandles: Object.fromEntries(
        m.assets.map((a) => [
          a.id,
          'data:' +
            a.mediaType +
            ';base64,' +
            fs.readFileSync(path.join(base, a.path)).toString('base64')
        ])
      )
    }
  });
}
const languages = [
  'en',
  'ru',
  'cs',
  'de',
  'es',
  'pt-BR',
  'fr',
  'it',
  'ko',
  'hi',
  'pl',
  'zh-Hans',
  'zh-Hant'
];
(async () => {
  const browser = await chromium.launch({ headless: true });
  let count = 0;
  try {
    for (const edition of ['launcher', 'root-launcher'])
      for (const language of process.env.WEATHER_LANGS
        ? process.env.WEATHER_LANGS.split(',')
        : languages) {
        const page = await browser.newPage({
            viewport: { width: 1920, height: 1080 }
          }),
          errors = [];
        page.on('pageerror', (e) => errors.push(e.message));
        await page.route(/^https?:/, (r) => r.abort());
        await page.addInitScript(
          ({ language }) => {
            localStorage.setItem('tvhome.language', language);
            const data = {
              city: 'Berlin',
              temp: -3,
              feels: -7,
              wind: 4,
              humidity: 78,
              precip: 20,
              code: 3,
              isDay: true,
              offset: 0,
              timezone: 'UTC',
              days: [
                [-7, -1, 3],
                [-8, -2, 73],
                [-5, 0, 2],
                [-4, 1, 0]
              ].map((v, i) => ({
                date: new Date(Date.now() + i * 86400000)
                  .toISOString()
                  .slice(0, 10),
                low: v[0],
                high: v[1],
                code: v[2]
              }))
            };
            localStorage.setItem(
              'tvhome.weather.v1',
              JSON.stringify({
                enabled: true,
                preferred: 'forecast',
                mode: 'manual',
                location: { name: 'Berlin', latitude: 52.52, longitude: 13.41 },
                locationLanguage: language,
                cache: { key: '52.520,13.410', updated: Date.now(), data }
              })
            );
          },
          { language }
        );
        await page.goto(
          pathToFileURL(path.join(site, edition, 'index.html')).href
        );
        await page.waitForFunction(
          () => window.RootLauncherRendered && window.HomeWeather
        );
        await page.evaluate(() => document.fonts.ready);
        for (const pack of packages) {
          await page.evaluate((input) => {
            if (input) {
              Object.keys(input.assetHandles).forEach((id) => {
                const url = input.assetHandles[id],
                  split = url.indexOf(','),
                  raw = atob(url.slice(split + 1)),
                  bytes = new Uint8Array(raw.length);
                for (let i = 0; i < raw.length; i++)
                  bytes[i] = raw.charCodeAt(i);
                input.assetHandles[id] = URL.createObjectURL(
                  new Blob([bytes], { type: url.slice(5, url.indexOf(';')) })
                );
              });
              ThemeRuntime.apply(input);
            } else ThemeRuntime.reset();
          }, pack.input);
          await page.waitForTimeout(40);
          for (const format of ['text', 'current', 'details', 'forecast']) {
            await page.evaluate(
              (format) =>
                HomeWeather.store.setPreferences({ preferred: format }),
              format
            );
            await page.waitForTimeout(35);
            const label = [edition, language, pack.title, format].join('/');
            const info = await page.evaluate(() => {
              const w = document.getElementById('homeWeather'),
                r = w.getBoundingClientRect(),
                shown = !w.hidden;
              const visible = (e) => {
                const s = getComputedStyle(e);
                return (
                  e.offsetHeight &&
                  s.display !== 'none' &&
                  s.visibility !== 'hidden' &&
                  s.opacity !== '0'
                );
              };
              const overlaps = shown
                ? [
                    ...document.querySelectorAll(
                      '#clock,#topButtons,#hero,#inputShelf,#ribbonPosition,.ctv-card'
                    )
                  ]
                    .filter((e) => {
                      if (!e || !visible(e)) return false;
                      const t = e.getBoundingClientRect();
                      return (
                        r.left < t.right - 2 &&
                        r.right > t.left + 2 &&
                        r.top < t.bottom - 2 &&
                        r.bottom > t.top + 2
                      );
                    })
                    .map((e) => e.id || e.className)
                : [];
              return {
                shown,
                format: w.dataset.format,
                bottom: r.bottom,
                right: r.right,
                overlaps,
                overflow: [
                  ...w.querySelectorAll(
                    '.weather-line,.weather-row,.weather-header,.weather-metrics'
                  )
                ]
                  .filter((e) => e.scrollWidth > e.clientWidth + 3)
                  .map((e) => e.className)
              };
            });
            assert.equal(info.shown, !!pack.formats.length, label);
            if (info.shown) {
              assert.equal(
                info.format,
                pack.formats.includes(format) ? format : pack.formats[0],
                label
              );
              assert(
                info.bottom <= 1050 && info.right <= 1920,
                label + JSON.stringify(info)
              );
              assert.deepEqual(info.overlaps, [], label);
              assert.deepEqual(info.overflow, [], label);
            }
            count++;
          }
          if (language === 'ru' && edition === 'launcher') {
            fs.mkdirSync(path.join(site, 'matrix'), { recursive: true });
            await page.screenshot({
              path: path.join(
                site,
                'matrix',
                pack.title.replace(/[^a-z0-9]/gi, '-') + '-home.png'
              )
            });
          }
          await page.evaluate(() => {
            RenewalPanel.open();
            document.querySelector('[data-category="weather"]').click();
          });
          await page.waitForTimeout(45);
          const available = await page
            .locator('[data-weather-choice]:visible')
            .count();
          assert.equal(
            available,
            pack.formats.length,
            [language, pack.title, 'settings formats'].join('/')
          );
          if (language === 'ru' && edition === 'launcher') {
            fs.mkdirSync(path.join(site, 'matrix'), { recursive: true });
            await page.screenshot({
              path: path.join(
                site,
                'matrix',
                pack.title.replace(/[^a-z0-9]/gi, '-') + '-settings.png'
              )
            });
          }
          await page.evaluate(() =>
            document.querySelector('.settings-footer button').click()
          );
        }
        assert.deepEqual(errors, [], edition + '/' + language);
        await page.close();
      }
    console.log(
      'PASS weather matrix: ' +
        count +
        ' format/theme/locale cases, ' +
        packages.length +
        ' themes, ' +
        (process.env.WEATHER_LANGS
          ? process.env.WEATHER_LANGS.split(',').length
          : languages.length) +
        ' languages, both editions'
    );
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
