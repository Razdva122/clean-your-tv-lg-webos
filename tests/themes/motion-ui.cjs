// Focus motion: one shared glide without overshoot, glass that never trails the card,
// press feedback, the app title crossfade and the 12-hour clock.
const { assert, chromium, stage, open } = require('./browser.cjs');
const fixture = require('./fixtures/valid-manifest.json');
const CURVE = 'cubic-bezier(0.2, 0.8, 0.2, 1)';

(async () => {
  const site = stage(),
    browser = await chromium.launch({
      headless: true,
      channel: process.env.BROWSER_CHANNEL || 'chrome'
    });
  try {
    for (const edition of ['launcher', 'root-launcher']) {
      const { page, errors } = await open(browser, site, edition);
      try {
        await page.evaluate(() =>
          HomeLayoutState.setThemeLayout({
            preset: 'dock-grid',
            columns: 5,
            spacingScale: 1,
            textScale: 1,
            focusScale: 1.1,
            inputs: 'shelf'
          })
        );
        // open() disables transitions for geometry tests; this test needs the real ones.
        await page.evaluate(() =>
          Array.from(document.querySelectorAll('style'))
            .filter((style) =>
              /transition: none !important/.test(style.textContent)
            )
            .forEach((style) => style.remove())
        );
        // Real compiled themes on the Classic layout, with and without the Classic motion opt-in.
        // The plain one declares a card transition, which the opt-in would reject.
        await page.evaluate((fixture) => {
          window.applyTheme = (motion) => {
            const manifest = JSON.parse(JSON.stringify(fixture));
            manifest.layout = {
              preset: 'dock-grid',
              columns: 5,
              spacingScale: 1,
              textScale: 1,
              focusScale: 1.1,
              inputs: 'shelf'
            };
            manifest.requires.capabilities = ['input-placement-v1'];
            if (motion) {
              manifest.layout.motion = 'classic';
              manifest.requires.capabilities.push('classic-motion-v1');
            }
            const rules = motion
              ? []
              : [
                  {
                    selector: [{ part: 'card', states: [] }],
                    declarations: [
                      {
                        property: 'transition',
                        value: {
                          type: 'transition',
                          property: 'box-shadow',
                          duration: 200,
                          easing: 'ease'
                        }
                      }
                    ]
                  }
                ];
            ThemeRuntime.apply({
              manifest,
              rules: { schemaVersion: 1, rules },
              assetHandles: {}
            });
          };
        }, fixture);
        await page.evaluate(() => {
          window.launches = [];
          const call = PalmServiceBridge.prototype.call;
          PalmServiceBridge.prototype.call = function (uri, params) {
            if (/applicationManager\/launch/.test(uri))
              window.launches.push(JSON.parse(params).id);
            return call.apply(this, arguments);
          };
        });
        const timing = (selector) =>
          page
            .locator(selector)
            .first()
            .evaluate((el) => {
              const style = getComputedStyle(el),
                names = style.transitionProperty.split(', ');
              const at = names.indexOf('transform');
              return {
                duration: style.transitionDuration.split(', ')[at],
                curve:
                  style.transitionTimingFunction.split(/,\s*(?![^(]*\))/)[at],
                all: style.transitionTimingFunction
              };
            });
        // Growing, shrinking and the glass share one 240 ms ease-out.
        for (const selector of [
          '#tiles .item.focused .card',
          '#tiles .item:not(.focused) .card',
          '#glass'
        ]) {
          const t = await timing(selector);
          assert.deepEqual(
            [t.duration, t.curve],
            ['0.24s', CURVE],
            edition + ' ' + selector + ' ' + JSON.stringify(t)
          );
        }
        // Nothing Home moves overshoots: every curve keeps its control points within 0..1.
        for (const selector of [
          '#tiles .card',
          '#glass',
          '#stage',
          '#hero',
          '.ctv-input-tile',
          '#inputShelfTrack',
          '.pill'
        ]) {
          const curves = await page
            .locator(selector)
            .first()
            .evaluate((el) => getComputedStyle(el).transitionTimingFunction);
          for (const match of curves.matchAll(/cubic-bezier\(([^)]*)\)/g)) {
            const [, y1, , y2] = match[1].split(',').map(Number);
            assert(
              y1 <= 1 && y2 <= 1 && y1 >= 0 && y2 >= 0,
              selector + ' overshoots: ' + match[0]
            );
          }
        }
        await page.waitForTimeout(400);
        assert.match(
          await page
            .locator('#tiles .item.focused .card')
            .evaluate((el) => getComputedStyle(el).transform),
          /^matrix\(1\.1, 0, 0, 1\.1,/,
          'same 1.1x enlargement as before'
        );

        // Remote focus: the glass lands on the new card and grows with it, never trailing.
        const before = await page.locator('#hero').textContent();
        const trace = await page.evaluate(
          () =>
            new Promise((resolve) => {
              const frames = [];
              document.dispatchEvent(
                new KeyboardEvent('keydown', {
                  keyCode: 39,
                  which: 39,
                  bubbles: true,
                  cancelable: true
                })
              );
              document.dispatchEvent(
                new KeyboardEvent('keyup', {
                  keyCode: 39,
                  which: 39,
                  bubbles: true
                })
              );
              const start = performance.now();
              (function sample() {
                const card = document
                    .querySelector('#tiles .item.focused .card')
                    .getBoundingClientRect(),
                  glass = document
                    .getElementById('glass')
                    .getBoundingClientRect();
                frames.push({
                  lag: Math.abs(
                    glass.left + glass.width / 2 - card.left - card.width / 2
                  ),
                  width: glass.width,
                  card: card.width
                });
                if (performance.now() - start < 400)
                  requestAnimationFrame(sample);
                else resolve(frames);
              })();
            })
        );
        assert(
          trace.every((frame) => frame.lag <= 1),
          'glass stays centred on the focused card: ' +
            JSON.stringify(trace.find((frame) => frame.lag > 1))
        );
        assert(
          trace[0].width < trace[trace.length - 1].width - 10,
          'glass grows with the card instead of snapping: ' +
            JSON.stringify([trace[0], trace[trace.length - 1]])
        );
        assert(
          trace[0].card < trace[trace.length - 1].card,
          'the card grows in place'
        );

        // The app title crossfades to the new name within about 450 ms.
        await page.waitForTimeout(100);
        const hero = await page.locator('#hero').evaluate((el) => ({
          text: el.textContent,
          opacity: getComputedStyle(el).opacity
        }));
        assert.notEqual(hero.text, before, 'the title follows focus');
        assert.equal(hero.opacity, '1', 'the new title is fully shown');

        // OK dips the card, keyup launches; holding OK still enters edit mode.
        await page.keyboard.down('Enter');
        assert.equal(
          await page.locator('#tiles .item.focused.pressed').count(),
          1,
          'OK shows press feedback'
        );
        await page.waitForTimeout(200);
        assert.match(
          await page
            .locator('#tiles .item.focused .card')
            .evaluate((el) => getComputedStyle(el).transform),
          /^matrix\(1\.05[56]/,
          'pressed card dips below 1.1x'
        );
        await page.keyboard.up('Enter');
        assert.equal(
          await page.locator('.pressed').count(),
          0,
          'release clears the press'
        );
        assert.equal(
          await page.evaluate(() => window.launches.length),
          1,
          'release launches the app'
        );
        await page.keyboard.down('Enter');
        await page.waitForTimeout(700);
        assert.equal(
          await page.locator('#tiles .moving').count(),
          1,
          'holding OK still enters edit mode'
        );
        assert.equal(
          await page.locator('.pressed').count(),
          0,
          'edit mode clears the press'
        );
        await page.keyboard.up('Enter');
        await page.keyboard.press('Escape');

        // Rows: a tap glides, a held arrow jumps straight to the target.
        await page.evaluate(() => {
          window.key = (code, repeat) => {
            document.dispatchEvent(
              new KeyboardEvent('keydown', {
                keyCode: code,
                which: code,
                repeat: !!repeat,
                bubbles: true,
                cancelable: true
              })
            );
            document.dispatchEvent(
              new KeyboardEvent('keyup', {
                keyCode: code,
                which: code,
                bubbles: true
              })
            );
          };
          window.stageY = () => ({
            now: new WebKitCSSMatrix(
              getComputedStyle(document.getElementById('stage')).transform
            ).m42,
            target: new WebKitCSSMatrix(
              document.getElementById('stage').style.transform
            ).m42
          });
          window.track = (ms, run) =>
            new Promise((resolve) => {
              const frames = [],
                start = performance.now();
              run();
              (function sample() {
                const card = document
                    .querySelector('#tiles .item.focused .card')
                    .getBoundingClientRect(),
                  glass = document
                    .getElementById('glass')
                    .getBoundingClientRect();
                frames.push(
                  Object.assign(
                    {
                      t: performance.now() - start,
                      lagX: Math.abs(
                        glass.left +
                          glass.width / 2 -
                          card.left -
                          card.width / 2
                      ),
                      lagY: Math.abs(
                        glass.top +
                          glass.height / 2 -
                          card.top -
                          card.height / 2
                      ),
                      bumpY: new WebKitCSSMatrix(
                        getComputedStyle(document.getElementById('viewport'))
                          .transform
                      ).m42,
                      bump: document.getElementById('homeSurface').className
                    },
                    stageY()
                  )
                );
                if (performance.now() - start < ms)
                  requestAnimationFrame(sample);
                else resolve(frames);
              })();
            });
        });
        // Three columns give the reference inventory enough rows to scroll.
        await page.evaluate(() => HomeLayoutState.setColumns(3));
        const rows = await page.evaluate(() =>
          Math.ceil(
            document.querySelectorAll('#tiles .item').length /
              HomeLayoutState.state().columns
          )
        );
        assert(
          rows >= 3,
          'the reference inventory needs at least three rows: ' + rows
        );
        await page.waitForTimeout(400);
        const glide = await page.evaluate(() =>
          track(420, () => key(40, false))
        );
        const target = glide[glide.length - 1].target;
        assert(target < -1, 'Down from the dock scrolls the rows: ' + target);
        assert(
          glide.some(
            (frame) => frame.t < 250 && frame.now < -1 && frame.now > target + 1
          ),
          'a tap glides through intermediate positions'
        );
        assert(
          Math.abs(glide[glide.length - 1].now - target) <= 1,
          'the glide arrives within 400 ms'
        );
        assert(
          glide.every((frame) => frame.lagX <= 1 && frame.lagY <= 1),
          'the glass rides with the card: ' +
            JSON.stringify(
              glide.find((frame) => frame.lagX > 1 || frame.lagY > 1)
            )
        );
        assert.deepEqual(
          await page
            .locator('#viewport')
            .evaluate((el) => [
              el.classList.contains('row-above'),
              el.classList.contains('row-peek')
            ]),
          [true, rows > 2],
          'top fade while scrolled, bottom fade while rows remain below'
        );
        // Held Down: every repeat lands exactly on the next frame, even mid-glide.
        for (let i = 0; i < rows; i++) {
          const held = await page.evaluate(
            () =>
              new Promise((resolve) => {
                key(40, true);
                requestAnimationFrame(() => resolve(stageY()));
              })
          );
          assert(
            Math.abs(held.now - held.target) <= 1,
            'held arrows never chase the scroll: ' + JSON.stringify(held)
          );
          await page.waitForTimeout(60);
        }
        assert.equal(
          await page
            .locator('#homeSurface')
            .evaluate((el) => el.classList.contains('ctv-edge-bump')),
          false,
          'held arrows at the last row never bump'
        );
        assert.equal(
          await page
            .locator('#viewport')
            .evaluate((el) => el.classList.contains('row-peek')),
          false,
          'no bottom fade on the last row'
        );
        // A fresh Down on the last row bumps and springs back. Presses of the same arrow
        // under 150 ms apart count as held, so let the held run end first.
        await page.waitForTimeout(200);
        const bump = await page.evaluate(() =>
          track(260, () => key(40, false))
        );
        assert(
          /bump-down/.test(bump[0].bump),
          'a fresh press at the end bumps'
        );
        assert(
          bump.some((frame) => frame.bumpY > 1),
          'the grid nudges down during the bump (a compositor transform)'
        );
        assert(Math.abs(bump[bump.length - 1].bumpY) < 0.5, 'and springs back');
        assert(
          bump.every((frame) => frame.lagX <= 1 && frame.lagY <= 1),
          'the glass moves with the bump'
        );
        // Up back to the dock glides home to offset 0.
        for (let i = 0; i < rows - 2; i++)
          await page.evaluate(() => key(38, true));
        await page.waitForTimeout(200);
        const home = await page.evaluate(() =>
          track(420, () => key(38, false))
        );
        assert.equal(home[home.length - 1].target, 0);
        assert(
          home.some((frame) => frame.now < -1) &&
            Math.abs(home[home.length - 1].now) <= 1,
          'returning to the dock glides'
        );
        assert.equal(
          await page
            .locator('#viewport')
            .evaluate((el) => el.classList.contains('row-above')),
          false
        );
        // The shelf bumps at its ends.
        await page.evaluate(() => key(38, false));
        assert.equal(
          await page.locator('.ctv-input-tile.is-focused').count(),
          1
        );
        for (let i = 0; i < 6; i++) await page.evaluate(() => key(37, true));
        await page.waitForTimeout(200);
        const shelfBump = await page.evaluate(
          () =>
            new Promise((resolve) => {
              key(37, false);
              setTimeout(
                () =>
                  resolve({
                    cls: document.getElementById('homeSurface').className,
                    x: new WebKitCSSMatrix(
                      getComputedStyle(
                        document.getElementById('inputShelfWindow')
                      ).transform
                    ).m41
                  }),
                60
              );
            })
        );
        assert(
          /bump-shelf-left/.test(shelfBump.cls) && shelfBump.x < -1,
          'Left on the first input bumps the shelf: ' +
            JSON.stringify(shelfBump)
        );
        // The focused input grows by FLIP: its layout box is final at once and a transform
        // animates from the old box, then clears so the text is sharp at rest.
        await page.waitForTimeout(300);
        const flip = await page.evaluate(
          () =>
            new Promise((resolve) => {
              key(39, false);
              setTimeout(() => {
                const tile = document.querySelector(
                  '.ctv-input-tile.is-focused'
                );
                resolve({
                  size: [tile.offsetWidth, tile.offsetHeight],
                  transform: getComputedStyle(tile).transform
                });
              }, 60);
            })
        );
        assert.deepEqual(
          flip.size,
          [404, 236],
          'the focused input takes its final layout at once'
        );
        assert(
          flip.transform !== 'none' &&
            !/^matrix\(1, 0, 0, 1, 0, 0\)$/.test(flip.transform),
          'a transform animates the growth: ' + flip.transform
        );
        await page.waitForTimeout(300);
        assert.deepEqual(
          await page
            .locator('.ctv-input-tile')
            .evaluateAll((tiles) =>
              tiles
                .map((tile) => getComputedStyle(tile).transform)
                .filter((value) => value !== 'none')
            ),
          [],
          'no input keeps a transform at rest'
        );
        // Only themes that opt into Classic motion keep the edge fades.
        await page.evaluate(() => key(40, false));
        await page.waitForTimeout(400);
        await page.evaluate(() => key(40, false));
        await page.waitForTimeout(400);
        const topFade = () =>
          page
            .locator('#viewport')
            .evaluate((el) => getComputedStyle(el, '::before').opacity);
        assert.equal(await topFade(), '1');
        await page.evaluate(() => applyTheme(false));
        await page.waitForTimeout(300);
        assert.equal(
          await topFade(),
          '0',
          'a theme without the opt-in keeps its own edges'
        );
        await page.evaluate(() => applyTheme(true));
        await page.waitForTimeout(300);
        assert.equal(
          await topFade(),
          '1',
          'a theme that opts into Classic motion keeps the top fade'
        );
        await page.evaluate(() => ThemeRuntime.reset());
        // Remote paths that send a held key as separate presses (no `repeat`) stay
        // immediate, and a held arrow cuts a running glide short even without scrolling.
        for (let i = 0; i < rows; i++) await page.evaluate(() => key(38, true));
        await page.waitForTimeout(400);
        const pairs = await page.evaluate(
          () =>
            new Promise((resolve) => {
              key(40, false);
              setTimeout(() => {
                key(40, false);
                requestAnimationFrame(() => resolve(stageY()));
              }, 60);
            })
        );
        assert(
          Math.abs(pairs.now - pairs.target) <= 1,
          'a second press within 150 ms counts as held: ' +
            JSON.stringify(pairs)
        );
        await page.waitForTimeout(400);
        const cut = await page.evaluate(
          () =>
            new Promise((resolve) => {
              key(40, false);
              const gliding = document
                .getElementById('homeSurface')
                .classList.contains('ctv-scroll-glide');
              setTimeout(() => {
                key(39, true);
                resolve({
                  gliding,
                  after: document
                    .getElementById('homeSurface')
                    .classList.contains('ctv-scroll-glide')
                });
              }, 30);
            })
        );
        assert.deepEqual(
          cut,
          { gliding: true, after: false },
          'a held sideways arrow ends the glide at once'
        );
        // Other layouts and themes without the opt-in keep fully immediate remote focus (card
        // and frame both snap, even with an author card transition); an opted-in theme keeps
        // the card and frame on the same 240 ms transform, and so does a held key's glide.
        const remote = await page.evaluate(() => {
          const surface = document.getElementById('homeSurface');
          const read = () => {
            const card = getComputedStyle(
                document.querySelector('#tiles .card')
              ),
              glass = getComputedStyle(document.getElementById('glass'));
            const at = (style, name) =>
              style.transitionDuration.split(', ')[
                style.transitionProperty.split(', ').indexOf(name)
              ] || style.transitionDuration;
            return [at(card, 'transform'), at(glass, 'transform')];
          };
          surface.classList.add('ctv-remote-navigation');
          const classic = read();
          surface.setAttribute('data-layout', 'side-grid');
          const side = read();
          surface.setAttribute('data-layout', 'dock-grid');
          applyTheme(false);
          const plain = read();
          applyTheme(true);
          const opted = read();
          ThemeRuntime.reset();
          return { classic, side, plain, opted };
        });
        assert.deepEqual(
          remote,
          {
            classic: ['0.24s', '0.24s'],
            side: ['0s', '0s'],
            plain: ['0s', '0s'],
            opted: ['0.24s', '0.24s']
          },
          JSON.stringify(remote)
        );
        await page.evaluate(() => applyTheme(false));
        for (let i = 0; i < rows; i++) await page.evaluate(() => key(38, true));
        await page.waitForTimeout(400);
        assert.equal(
          await page.evaluate(() => {
            key(40, false);
            return document
              .getElementById('homeSurface')
              .classList.contains('ctv-scroll-glide');
          }),
          false,
          'a theme without the opt-in never glides'
        );
        await page.evaluate(() => ThemeRuntime.reset());
        await page.waitForTimeout(400);
        // Reduced motion: no glide, no bump, and an opted-in theme cannot bring motion back.
        await page.emulateMedia({ reducedMotion: 'reduce' });
        await page.evaluate(() => applyTheme(true));
        assert.deepEqual(
          await page.evaluate(() => [
            getComputedStyle(document.querySelector('#tiles .card'))
              .transitionDuration,
            getComputedStyle(document.getElementById('glass'))
              .transitionDuration
          ]),
          ['0s', '0s'],
          'reduced motion also covers an opted-in theme'
        );
        await page.evaluate(() => ThemeRuntime.reset());
        for (let i = 0; i < rows; i++) await page.evaluate(() => key(38, true));
        const calm = await page.evaluate(
          () =>
            new Promise((resolve) => {
              key(40, false);
              requestAnimationFrame(() => resolve(stageY()));
            })
        );
        assert(
          Math.abs(calm.now - calm.target) <= 1,
          'reduced motion jumps straight to the row'
        );
        assert.equal(
          await page
            .locator('#viewport')
            .evaluate((el) => getComputedStyle(el).animationName),
          'none'
        );
        await page.emulateMedia({ reducedMotion: 'no-preference' });
        await page.evaluate(() => HomeLayoutState.setColumns(null));

        // 12-hour languages drop the leading zero; 24-hour languages keep it.
        assert.equal(
          await page.evaluate(() =>
            HomeI18n.formatTime(new Date(2026, 10, 1, 18, 5))
          ),
          '6:05 PM'
        );
        assert.equal(
          await page.evaluate(() =>
            HomeI18n.formatTime(new Date(2026, 10, 1, 9, 5))
          ),
          '9:05 AM'
        );
        await page.evaluate(() =>
          localStorage.setItem('tvhome.language', 'de')
        );
        await page.reload();
        await page.locator('#tiles .focused').waitFor();
        assert.deepEqual(
          await page.evaluate(() => [
            HomeI18n.formatTime(new Date(2026, 10, 1, 18, 5)),
            HomeI18n.formatTime(new Date(2026, 10, 1, 6, 5))
          ]),
          ['18:05', '06:05']
        );
        await page.evaluate(() => localStorage.removeItem('tvhome.language'));
        assert.deepEqual(errors, [], 'renderer errors');
        console.log(
          'PASS focus motion, press feedback, title crossfade and clock: ' +
            edition
        );
      } finally {
        await page.close();
      }
    }
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
