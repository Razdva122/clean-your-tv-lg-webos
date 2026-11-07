'use strict';
const { assert, fs, path, chromium, stage, open } = require('./browser.cjs');
const entry = require('../../launcher/builtin-themes.json').themes.find(
  (e) => e.id === 'builtin:liquid-glass'
);
const base = path.dirname(path.resolve('launcher', entry.url)),
  manifest = JSON.parse(fs.readFileSync(path.join(base, 'cytv-theme.json'))),
  rules = JSON.parse(fs.readFileSync(path.join(base, manifest.rules.path)));
const handles = Object.fromEntries(
  manifest.assets.map((a) => [
    a.id,
    'data:' +
      a.mediaType +
      ';base64,' +
      fs.readFileSync(path.join(base, a.path)).toString('base64')
  ])
);
(async () => {
  const site = stage(),
    browser = await chromium.launch({ headless: true });
  try {
    for (const edition of ['launcher', 'root-launcher']) {
      const { page, errors } = await open(browser, site, edition);
      await page.evaluate(() =>
        Array.from(document.querySelectorAll('style'))
          .filter((s) => /transition: none !important/.test(s.textContent))
          .forEach((s) => s.remove())
      );
      await page.evaluate(() =>
        InputSources.setPreviewEnabled(localStorage, true)
      );
      await page.evaluate((input) => ThemeRuntime.apply(input), {
        manifest,
        rules,
        assetHandles: handles
      });
      assert.equal(await page.locator('#btnInputs').isVisible(), false);
      await page.clock.install();
      await page.clock.pauseAt(await page.evaluate(() => Date.now() + 1000));
      await page.keyboard.press('ArrowUp');
      await page.clock.runFor(800);
      assert.equal(
        await page.locator('.preview-input-media').evaluate((e) => e.hidden),
        true,
        'no simulated picture before its first frame'
      );
      assert.equal(
        await page.locator('.ctv-input-tile.is-previewing').count(),
        0
      );
      await page.clock.runFor(300);
      const frame = await page
        .locator('.ctv-input-tile.is-previewing')
        .evaluate((tile) => {
          const media = tile.querySelector('.ctv-input-preview'),
            screen = media.querySelector('.preview-input-media'),
            rect = media.getBoundingClientRect();
          return {
            hidden: screen.hidden,
            glyph: getComputedStyle(tile.querySelector('.input-glyph'))
              .visibility,
            color: getComputedStyle(tile).color,
            detail: getComputedStyle(tile.querySelector('.input-detail')).color,
            timings: [
              tile,
              tile.querySelector('.input-name'),
              tile.querySelector('.input-detail')
            ].map((e) => ({
              property: getComputedStyle(e).transitionProperty,
              duration: getComputedStyle(e).transitionDuration
            })),
            radius: getComputedStyle(media).borderTopLeftRadius,
            cornerClipped: !media.contains(
              document.elementFromPoint(rect.left + 1, rect.top + 1)
            ),
            centerVisible: media.contains(
              document.elementFromPoint(
                rect.left + rect.width / 2,
                rect.top + rect.height / 2
              )
            )
          };
        });
      assert.equal(frame.hidden, false);
      assert.equal(frame.glyph, 'hidden');
      assert.equal(frame.color, 'rgb(255, 255, 255)');
      assert.equal(frame.detail, 'rgba(255, 255, 255, 0.78)');
      assert(
        frame.timings.every(
          (t) =>
            !t.property
              .split(', ')
              .some(
                (p, i) =>
                  (p === 'color' || p === 'all') &&
                  t.duration.split(', ')[i % t.duration.split(', ').length] !==
                    '0s'
              )
        ),
        'color never trails video: ' + JSON.stringify(frame)
      );
      assert.equal(
        frame.timings[0].duration.split(', ')[
          frame.timings[0].property.split(', ').indexOf('transform')
        ],
        '0.24s',
        'preview preserves focus transform animation'
      );
      await page
        .locator('.ctv-input-tile.is-previewing')
        .evaluate((e) =>
          e.dispatchEvent(
            new MouseEvent('mousedown', { button: 0, bubbles: true })
          )
        );
      assert.equal(
        await page
          .locator('.ctv-input-tile.is-previewing')
          .evaluate((e) => getComputedStyle(e).transitionDuration),
        '0.12s',
        'preview preserves the press dip'
      );
      await page
        .locator('.ctv-input-tile.is-previewing')
        .evaluate((e) =>
          e.dispatchEvent(
            new MouseEvent('mouseup', { button: 0, bubbles: true })
          )
        );
      assert(
        parseFloat(frame.radius) > 0 &&
          frame.cornerClipped &&
          frame.centerVisible,
        'rounded browser preview clips only corners: ' + JSON.stringify(frame)
      );
      await page.screenshot({
        path: 'build/tests/input-preview-presentation-' + edition + '.png'
      });
      assert.deepEqual(errors, []);
      await page.close();
    }
  } finally {
    await browser.close();
  }
  console.log(
    'PASS first-frame presentation sync, no duplicate Inputs and rounded browser preview in both editions'
  );
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
