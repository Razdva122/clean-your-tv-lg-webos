'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const root = path.resolve(__dirname, '..');
const uiFile = path.join(root, 'launcher/screensaver-settings.js');
(async () => {
  assert.ok(fs.existsSync(uiFile), 'shared screensaver settings UI exists');
  const browser = await chromium.launch({
    headless: true,
    channel: process.env.BROWSER_CHANNEL || 'chrome'
  });
  try {
    for (const edition of ['noroot', 'root']) {
      const page = await browser.newPage({
        viewport: { width: 1920, height: 1080 }
      });
      const errors = [];
      page.on('pageerror', (e) => errors.push(e.message));
      await page.clock.install();
      await page.setContent(
        '<body><div id="homeSurface"></div><section id="renewalPanel" role="dialog"><div class="renewal-card"><div class="settings-heading"><h2>Settings</h2></div><div class="settings-footer"><button>Done</button></div></div></section></body>'
      );
      await page.addStyleTag({
        path: path.join(root, 'launcher/settings-panel.css')
      });
      await page.addStyleTag({
        path: path.join(root, 'launcher/renewal-panel.css')
      });
      await page.addStyleTag({
        path: path.join(root, 'launcher/screensaver-settings.css')
      });
      await page.evaluate((isRoot) => {
        if (isRoot) window.ROOT_VERSION = 'test';
        window.calls = [];
        window.pendingStatus = [];
        window.delayStatus = false;
        window.pendingPreview = null;
        window.delayPreview = false;
        window.busyStatus = 0;
        window.busyConfigure = 0;
        window.backend = {
          enabled: false,
          scope: 'cytv',
          mode: 'ambient',
          assetId: '',
          idleTimeoutMs: 30000
        };
        window.available = true;
        window.started = false;
        window.popupUnavailable = false;
        window.personal = { photo: false, video: false };
        window.mediaCalls = [];
        window.ScreensaverPersonal = {
          start: () => Promise.resolve({ ...personal }),
          state: () => ({ ...personal }),
          receive: (mode) => {
            personal[mode] = true;
            mediaCalls.push('import:' + mode);
            return Promise.resolve();
          },
          prepare: (mode) => {
            mediaCalls.push('prepare:' + mode);
            return Promise.resolve({
              mediaUrl:
                'http://127.0.0.1:1234/' +
                'a'.repeat(32) +
                (mode === 'video' ? '/4k.mp4' : '/photo.jpg'),
              dispose: () => {
                mediaCalls.push('dispose:' + mode);
                return Promise.resolve();
              }
            });
          }
        };
        window.receiverCalls = [];
        window.ThemeReceiver = {
          start: (signal, kind) => {
            receiverCalls.push('start:' + kind);
            return Promise.resolve({
              sessionId: 'receiver1',
              pin: '123456',
              addresses: ['192.168.1.2'],
              expiresAt: Date.now() + 600000
            });
          },
          status: () => Promise.resolve({ state: 'waiting' }),
          read: () => Promise.resolve({}),
          stop: () => {
            receiverCalls.push('stop');
            return Promise.resolve();
          }
        };
        window.clockAppearance = { locale: 'ru', hour12: false };
        window.HomeI18n = {
          t: (text) => text,
          add: () => {},
          ready: (callback) => (window.finishLanguageLoad = callback),
          language: () => clockAppearance.locale,
          formatTime: () => (clockAppearance.hour12 ? '12:00 PM' : '12:00'),
          formatDate: () =>
            clockAppearance.locale === 'ru' ? 'понедельник' : 'Monday',
          clockFormat: () => 'auto',
          clockPresentation: () => ({ ...clockAppearance }),
          setClockFormat: () => true
        };
        window.PalmServiceBridge = function () {
          this.cancel = () => {};
          this.call = (uri, raw) => {
            const method = uri.split('/').pop();
            const payload = JSON.parse(raw);
            calls.push({ uri, method, payload });
            const statusBusy = method === 'screensaverStatus' && busyStatus > 0;
            const savingBusy =
              method === 'screensaverConfigure' && busyConfigure > 0;
            if (statusBusy) busyStatus--;
            if (savingBusy) busyConfigure--;
            else if (method === 'screensaverConfigure') backend = payload;
            const channelBusy = statusBusy || savingBusy;
            const denied = popupUnavailable;
            const response = JSON.stringify(
              channelBusy
                ? {
                    returnValue: false,
                    errorText: 'Home control busy'
                  }
                : {
                    returnValue: true,
                    available: available && !denied,
                    state: backend,
                    started: started && !denied,
                    reason: denied ? 'popup-unavailable' : undefined
                  }
            );
            const send = () => this.onservicecallback(response);
            if (delayStatus && method === 'screensaverStatus')
              pendingStatus.push(send);
            else if (delayPreview && method === 'screensaverPreview')
              pendingPreview = send;
            else send();
          };
        };
      }, edition === 'root');
      await page.addScriptTag({
        path: path.join(root, 'screensaver/settings.js')
      });
      await page.addScriptTag({
        path: path.join(root, 'launcher/screensaver-idle.js')
      });
      await page.addScriptTag({
        path: path.join(root, 'launcher/wallpaper-panel.js')
      });
      await page.addScriptTag({ path: uiFile });
      await page.addScriptTag({
        path: path.join(root, 'launcher/settings-categories.js')
      });
      await page.evaluate(() => {
        window.view = SettingsCategories.attach(
          document.getElementById('renewalPanel'),
          document.querySelector('.renewal-card'),
          [
            { id: 'home', label: 'Home', elements: [] },
            { id: 'wallpapers', label: 'Wallpapers', elements: [] },
            { id: 'advanced', label: 'Advanced', elements: [] }
          ]
        );
        if (!window.ROOT_VERSION) {
          backend.enabled = true;
          busyStatus = 1;
        }
        HomeScreensaver.start();
        view.open();
      });
      assert.equal(
        await page
          .locator(
            '[data-category="wallpapers"] + [data-category="screensaver"]'
          )
          .count(),
        1
      );
      const toggle = page.locator('#screensaverEnabled');
      if (edition === 'noroot') {
        await page.waitForFunction(
          () =>
            document
              .querySelector('#screensaverEnabled')
              .getAttribute('aria-checked') === 'true'
        );
        assert.equal(
          await page.evaluate(
            () =>
              calls.filter(({ method }) => method === 'screensaverStatus')
                .length
          ),
          2,
          'No-root retries a busy first status before showing the enabled default'
        );
      }
      await page.locator('[data-category="screensaver"]').focus();
      await page.keyboard.press('ArrowRight');
      assert.equal(
        await page.evaluate(() => document.activeElement.id),
        'screensaverEnabled'
      );
      if (edition === 'noroot') {
        await toggle.click();
        await page.waitForFunction(
          () =>
            document
              .querySelector('#screensaverEnabled')
              .getAttribute('aria-checked') === 'false'
        );
        assert.equal(await page.evaluate(() => backend.enabled), false);
      }
      assert.equal(
        await page.locator('#screensaverEnabled').getAttribute('aria-checked'),
        'false'
      );
      assert.equal(
        await page
          .locator('#screensaverAmbientCard')
          .getAttribute('aria-pressed'),
        'true'
      );
      await page.evaluate(() => {
        busyStatus = 1;
        available = false;
        HomeScreensaver.activate(true);
        HomeScreensaver.activate(true);
      });
      await page.waitForFunction(
        () => document.querySelector('#screensaverEnabled').disabled
      );
      await page.evaluate(() => {
        busyStatus = 1;
        available = true;
        HomeScreensaver.activate(true);
      });
      await page.waitForFunction(
        () => !document.querySelector('#screensaverEnabled').disabled
      );
      await page.evaluate(() => {
        busyConfigure = 1;
        document.querySelector('#screensaverEnabled').click();
      });
      await page.waitForFunction(
        () =>
          document
            .querySelector('#screensaverEnabled')
            .getAttribute('aria-checked') === 'true'
      );
      await toggle.click();
      await page.waitForFunction(
        () =>
          document
            .querySelector('#screensaverEnabled')
            .getAttribute('aria-checked') === 'false'
      );
      const status = page.locator('.screensaver-status');
      const assertLocked = async (canEnable) => {
        const count = await page.evaluate(
          () =>
            calls.filter(({ method }) => method === 'screensaverConfigure')
              .length
        );
        assert.equal(await toggle.isEnabled(), canEnable);
        assert.equal(
          await page.locator('.screensaver-settings button:enabled').count(),
          canEnable ? 1 : 0
        );
        await page.evaluate(() => {
          for (const button of document.querySelectorAll(
            '.screensaver-settings button:not(#screensaverEnabled)'
          )) {
            button.focus();
            if (document.activeElement === button)
              throw Error('A dependent control received focus while locked');
            button.click();
          }
        });
        assert.equal(
          await page.evaluate(
            () =>
              calls.filter(({ method }) => method === 'screensaverConfigure')
                .length
          ),
          count
        );
        assert.deepEqual(await page.evaluate(() => receiverCalls), []);
      };
      await assertLocked(true);
      assert.match(await status.textContent(), /Turn on the screensaver/);
      assert.equal(
        await page.evaluate(() => backend.clock),
        undefined,
        'do not persist a provisional language before Home is ready'
      );
      await page.evaluate(() => finishLanguageLoad());
      assert.deepEqual(await page.evaluate(() => backend.clock), {
        locale: 'ru',
        hour12: false
      });
      assert.equal(await page.evaluate(() => backend.enabled), false);
      await page.evaluate(() => {
        available = false;
        HomeScreensaver.activate(true);
      });
      await assertLocked(false);
      assert.match(await status.textContent(), /Screensaver is unavailable/);
      await page.evaluate(() => {
        available = true;
        HomeScreensaver.activate(true);
      });
      await toggle.click();
      assert.equal(await page.locator('#screensaverScope').count(), 0);
      assert.equal(await page.evaluate(() => backend.scope), 'global');
      const date = page.locator('.screensaver-preview-date');
      const previewTime = page
        .locator('.screensaver-clock-preview > span')
        .first();
      assert.equal(await date.isVisible(), true);
      assert.equal(await date.textContent(), 'понедельник');
      assert.equal(await previewTime.textContent(), '12:00');
      await page.evaluate(() => {
        clockAppearance = { locale: 'en', hour12: true };
        document.dispatchEvent(new CustomEvent('home-clock-format-change'));
      });
      assert.deepEqual(await page.evaluate(() => backend.clock), {
        locale: 'en',
        hour12: true
      });
      assert.equal(await date.textContent(), 'Monday');
      assert.equal(await previewTime.textContent(), '12:00 PM');
      if (edition === 'noroot') {
        await page.evaluate(() => (popupUnavailable = true));
        await page.locator('#screensaverPreview').click();
        await page.waitForFunction(() =>
          document
            .querySelector('.screensaver-status')
            .textContent.includes('only in Clean Your TV')
        );
        assert.equal(await toggle.isDisabled(), false);
        assert.equal(
          await page.locator('#screensaverPreview').isDisabled(),
          false
        );
        await toggle.click();
        assert.equal(await toggle.getAttribute('aria-checked'), 'false');
        await toggle.click();
        assert.equal(await toggle.getAttribute('aria-checked'), 'true');
        await page.evaluate(() => {
          popupUnavailable = false;
          HomeScreensaver.activate(true);
        });
        await page.waitForFunction(
          () => !document.querySelector('#screensaverEnabled').disabled
        );
      }
      if (edition === 'root') {
        for (const launches of [true, false]) {
          await page.evaluate((launches) => {
            calls = [];
            delete backend.clock;
            started = launches;
            delayStatus = delayPreview = true;
            HomeScreensaver.activate(true);
          }, launches);
          await page.locator('#screensaverPreview').click();
          await page.waitForFunction(() => pendingPreview !== null);
          await page.evaluate(() => {
            delayStatus = false;
            pendingStatus.splice(0).forEach((send) => send());
          });
          const relevantCalls = () =>
            page.evaluate(() =>
              calls
                .map(({ method }) => method)
                .filter((method) => method !== 'screensaverStatus')
            );
          assert.deepEqual(
            await relevantCalls(),
            ['screensaverPreview'],
            'a late status cannot configure the clock during Preview'
          );
          await page.evaluate(() => {
            delayPreview = false;
            pendingPreview();
            pendingPreview = null;
          });
          if (launches) {
            await page.clock.runFor(1000);
            assert.deepEqual(
              await relevantCalls(),
              ['screensaverPreview'],
              'successful Preview retains the handoff until focus returns'
            );
            await page.evaluate(() => {
              delayStatus = true;
              window.dispatchEvent(new Event('focus'));
            });
            await page.clock.runFor(1000);
            assert.deepEqual(
              await relevantCalls(),
              ['screensaverPreview'],
              'background configure waits for fresh status after focus returns'
            );
            await page.evaluate(() => {
              delayStatus = false;
              pendingStatus.splice(0).forEach((send) => send());
            });
          }
          await page.clock.runFor(1000);
          assert.deepEqual(await relevantCalls(), [
            'screensaverPreview',
            'screensaverConfigure'
          ]);
          assert.deepEqual(await page.evaluate(() => backend.clock), {
            locale: 'en',
            hour12: true
          });
        }
      }
      const overlay = page.locator('#screensaverClockOverlay');
      await overlay.focus();
      await page.evaluate(() => {
        available = false;
        HomeScreensaver.activate(true);
      });
      await assertLocked(false);
      assert.equal(
        await page.evaluate(() => document.activeElement.id),
        'screensaverStatus'
      );
      await page.evaluate(() => {
        available = true;
        HomeScreensaver.activate(true);
      });
      assert.equal(await overlay.getAttribute('aria-checked'), 'true');
      await overlay.focus();
      await page.keyboard.press('Enter');
      assert.equal(await overlay.getAttribute('aria-checked'), 'false');
      assert.equal(await page.evaluate(() => backend.clockOverlay), false);
      assert.equal(await date.isVisible(), false);
      assert.equal(
        await page.locator('.screensaver-clock-preview').isVisible(),
        true
      );
      await page.keyboard.press('Enter');
      assert.equal(await overlay.getAttribute('aria-checked'), 'true');
      const fiveMinutes = page.locator('#screensaverDelay-300000');
      await fiveMinutes.focus();
      await page.keyboard.press('Enter');
      assert.equal(await fiveMinutes.getAttribute('aria-pressed'), 'true');
      assert.equal(await page.evaluate(() => backend.idleTimeoutMs), 300000);
      await page.locator('#screensaverDelay-30000').click();
      await page.locator('#screensaverScene-ribbon').click();
      assert.deepEqual(
        await page
          .locator('.wallpaper-summary .wallpaper-media-badges span')
          .allTextContents(),
        ['Video', '4K', '1080p']
      );
      const hd = page.locator('#screensaverQuality-1080p');
      await hd.click();
      assert.equal(await hd.getAttribute('aria-pressed'), 'true');
      assert.equal(await page.evaluate(() => backend.quality), '1080p');
      assert.match(
        await page.locator('img.wallpaper-preview-image').getAttribute('src'),
        /ribbon-preview\.jpg$/
      );
      await page.locator('#screensaverBackground-photo').click();
      await page.locator('#screensaverScene-ribbon').click();
      assert.equal(await page.evaluate(() => backend.assetId), 'ribbon-photo');
      await page
        .locator('.screensaver-settings [data-background-upload]')
        .click();
      await page.locator('#screensaverImport-photo').click();
      await page.waitForFunction(() =>
        document
          .getElementById('screensaverReceiverPin')
          .textContent.includes('123456')
      );
      assert.match(
        await page.locator('#screensaverReceiverAddress').textContent(),
        /192\.168\.1\.2/
      );
      await page.locator('#screensaverReceiverCancel').click();
      assert.deepEqual(await page.evaluate(() => receiverCalls), [
        'start:wallpaper',
        'stop'
      ]);
      await page.evaluate(() => {
        ThemeReceiver.status = () =>
          Promise.resolve({ state: 'received', size: 1 });
      });
      await page.locator('#screensaverImport-photo').click();
      await page.waitForFunction(() => backend.assetId === 'personal-photo');
      assert.match(
        await page.locator('#screensaverImport-photo').textContent(),
        /Replace/
      );
      if (edition === 'root') {
        await page.evaluate(() => {
          const prepare = ScreensaverPersonal.prepare;
          ScreensaverPersonal.prepare = (mode) =>
            new Promise((resolve) => {
              window.finishClockOnlyPrepare = () => {
                ScreensaverPersonal.prepare = prepare;
                resolve(prepare(mode));
              };
            });
          delete backend.clock;
          delayStatus = true;
          HomeScreensaver.activate(true);
        });
      }
      await page.locator('#screensaverPreview').click();
      if (edition === 'root') {
        await page.waitForFunction(() => window.finishClockOnlyPrepare);
        await page.evaluate(() => {
          delayStatus = false;
          pendingStatus.splice(0).forEach((send) => send());
          finishClockOnlyPrepare();
        });
      }
      await page.waitForFunction(() => mediaCalls.includes('dispose:photo'));
      assert.equal(
        (await page.evaluate(() => calls))
          .filter((r) => r.method === 'screensaverPreview')
          .at(-1).payload.mediaUrl,
        'http://127.0.0.1:1234/' + 'a'.repeat(32) + '/photo.jpg',
        'clock-only status during preparation preserves personal Preview'
      );
      const previewBefore = (await page.evaluate(() => calls)).filter(
        (r) => r.method === 'screensaverPreview'
      ).length;
      await page.evaluate(() => {
        window.prepareOriginal = ScreensaverPersonal.prepare;
        ScreensaverPersonal.prepare = () =>
          new Promise((resolve) => {
            window.finishPrepare = resolve;
          });
      });
      await page.locator('#screensaverPreview').click();
      await page
        .locator('.screensaver-settings [data-background-tab=built-in]')
        .click();
      await page.locator('#screensaverScene-ribbon').click();
      await page.evaluate(() => {
        finishPrepare({
          mediaUrl: 'http://127.0.0.1:1234/' + 'a'.repeat(32) + '/photo.jpg',
          dispose: () => {
            mediaCalls.push('dispose:stale');
            return Promise.resolve();
          }
        });
        ScreensaverPersonal.prepare = prepareOriginal;
      });
      await page.waitForFunction(() => mediaCalls.includes('dispose:stale'));
      assert.equal(
        (await page.evaluate(() => calls)).filter(
          (r) => r.method === 'screensaverPreview'
        ).length,
        previewBefore,
        'replaced preparation releases lease without late activation'
      );
      await page.locator('#screensaverScene-ribbon').click();
      await page.evaluate(() => {
        ThemeReceiver.status = () => Promise.resolve({ state: 'waiting' });
      });
      await page.locator('#screensaverImport-video').click();
      await page.waitForFunction(() =>
        document
          .getElementById('screensaverReceiverPin')
          .textContent.includes('123456')
      );
      await page.locator('[data-category="home"]').click();
      assert.equal(
        await page.locator('#screensaverReceiverPin').textContent(),
        '',
        'leaving settings category clears PIN and closes receiver'
      );
      await page.locator('[data-category="screensaver"]').click();
      await page.locator('#screensaverBackground-video').click();
      assert.equal(await page.evaluate(() => backend.assetId), 'ribbon-video');
      assert.equal(
        await page
          .locator('#screensaverScene-ribbon')
          .getAttribute('aria-pressed'),
        'true'
      );
      if (edition === 'noroot')
        await page.screenshot({
          path: '/private/tmp/cytv-screensaver-media-settings.png'
        });
      await page.locator('#screensaverAmbientCard').click();
      assert.equal(await page.evaluate(() => backend.mode), 'ambient');
      assert.equal(await page.locator('#screensaverScenes').isVisible(), true);
      await toggle.click();
      assert.equal(
        await page.locator('#screensaverPreview').isDisabled(),
        true
      );
      await page.evaluate(() => {
        delayStatus = true;
        HomeScreensaver.activate(true);
      });
      await page.locator('#screensaverEnabled').click();
      assert.equal(
        await page.locator('#screensaverEnabled').getAttribute('aria-checked'),
        'true'
      );
      await page.evaluate(() => {
        pendingStatus.forEach((send) => send());
        pendingStatus = [];
        delayStatus = false;
      });
      assert.equal(
        await page.locator('#screensaverEnabled').getAttribute('aria-checked'),
        'true',
        'late status cannot undo accepted configure'
      );
      await page.screenshot({
        path: '/private/tmp/cytv-screensaver-settings-' + edition + '.png'
      });
      await page.locator('#screensaverPreview').click();
      assert.ok(
        (await page.evaluate(() => calls)).some(
          (r) => r.method === 'screensaverPreview'
        )
      );
      const service =
        edition === 'root'
          ? 'com.cleanyourtv.root.preview.service'
          : 'com.gathin.tvhome.renewal';
      assert.ok(
        (await page.evaluate(() => calls)).every((r) =>
          r.uri.startsWith('luna://' + service + '/')
        ),
        'edition-authenticated service only'
      );

      await page.evaluate(() => {
        calls = [];
      });
      await page.clock.runFor(31000);
      assert.equal(
        (await page.evaluate(() => calls)).filter(
          (r) => r.method === 'screensaverEligible'
        ).length,
        0,
        'settings dialog blocks automatic activation'
      );
      await page.evaluate(() =>
        document.getElementById('renewalPanel').classList.add('hidden')
      );
      await page.keyboard.press('ArrowRight');
      await page.clock.runFor(31000);
      assert.ok(
        (await page.evaluate(() => calls)).some(
          (r) => r.method === 'screensaverActivity'
        )
      );
      assert.ok(
        (await page.evaluate(() => calls)).some(
          (r) => r.method === 'screensaverEligible'
        ),
        'fresh real input followed by local idle offers eligibility'
      );
      const refusedAttempts = (await page.evaluate(() => calls)).filter(
        (r) => r.method === 'screensaverEligible'
      ).length;
      await page.clock.runFor(31000);
      assert.equal(
        (await page.evaluate(() => calls)).filter(
          (r) => r.method === 'screensaverEligible'
        ).length,
        refusedAttempts,
        'refused activation requires new input instead of retrying old idle'
      );
      await page.evaluate(() => {
        calls = [];
        document.body.classList.add('editing');
      });
      await page.clock.runFor(31000);
      assert.equal(
        (await page.evaluate(() => calls)).filter(
          (r) => r.method === 'screensaverEligible'
        ).length,
        0,
        'tile editing blocks automatic activation'
      );
      await page.route('http://media.test/home.mp4', (route) =>
        route.fulfill({
          path: path.join(root, 'themes/ribbon/assets/wallpaper-1080p.mp4'),
          contentType: 'video/mp4'
        })
      );
      await page.evaluate(async () => {
        document.body.classList.remove('editing');
        const video = document.createElement('video');
        video.id = 'homeVideo';
        video.muted = true;
        video.loop = true;
        video.src = 'http://media.test/home.mp4';
        document.body.appendChild(video);
        await video.play();
        calls = [];
      });
      await page.keyboard.press('ArrowRight');
      await page.clock.runFor(31000);
      assert.equal(
        (await page.evaluate(() => calls)).filter(
          (r) => r.method === 'screensaverEligible'
        ).length,
        0,
        'actual Home video playback blocks automatic activation'
      );
      await page.evaluate(() => {
        const video = document.getElementById('homeVideo');
        video.id = 'ctvWallpaperVideo';
        window.wallpaperEvents = [];
        window.HomeWallpaper = {
          suspend: (owner) => {
            wallpaperEvents.push('suspend:' + owner);
            video.pause();
            video.removeAttribute('src');
            video.load();
            if (!window.wallpaperReleased)
              return new Promise((resolve) => {
                window.releaseWallpaper = () => {
                  wallpaperReleased = true;
                  resolve();
                };
              });
          },
          resume: (owner) => wallpaperEvents.push('resume:' + owner)
        };
        calls = [];
      });
      await page.keyboard.press('ArrowRight');
      await page.clock.runFor(32500);
      assert.deepEqual(
        await page.evaluate(() => wallpaperEvents),
        ['suspend:screensaver'],
        'owned wallpaper pauses before saver starts'
      );
      assert.equal(
        await page.evaluate(
          () => document.getElementById('ctvWallpaperVideo').paused
        ),
        true
      );
      assert.equal(
        (await page.evaluate(() => calls)).filter(
          (r) => r.method === 'screensaverEligible'
        ).length,
        0,
        'wait for wallpaper lease release before new launch'
      );
      await page.evaluate(() => releaseWallpaper());
      await page.waitForFunction(() =>
        wallpaperEvents.includes('resume:screensaver')
      );
      await page.evaluate(() => {
        const video = document.getElementById('ctvWallpaperVideo');
        video.pause();
        video.remove();
        started = true;
        calls = [];
      });
      await page.keyboard.press('ArrowRight');
      await page.clock.runFor(31000);
      assert.equal(
        (await page.evaluate(() => calls)).filter(
          (r) => r.method === 'screensaverEligible'
        ).length,
        1
      );
      await page.clock.runFor(10000);
      assert.equal(
        (await page.evaluate(() => calls)).filter(
          (r) => r.method === 'screensaverStop'
        ).length,
        1,
        'accepted launch that never takes focus releases at startup deadline'
      );
      await page.clock.runFor(31000);
      assert.equal(
        (await page.evaluate(() => calls)).filter(
          (r) => r.method === 'screensaverEligible'
        ).length,
        1,
        'failed handoff cannot restart without fresh input'
      );
      await page.evaluate(() => {
        calls = [];
        wallpaperEvents = [];
      });
      await page.keyboard.press('ArrowRight');
      await page.clock.runFor(31000);
      await page.evaluate(() => window.dispatchEvent(new Event('blur')));
      await page.clock.runFor(2000);
      assert.equal(
        (await page.evaluate(() => calls)).filter(
          (r) => r.method === 'screensaverStop'
        ).length,
        0,
        'popup handoff blur must not stop its own session'
      );
      assert.deepEqual(
        await page.evaluate(() => wallpaperEvents),
        ['suspend:screensaver'],
        'owned popup keeps Home wallpaper suspended'
      );
      await page.evaluate(() => {
        // A freshly loaded owner profile is authoritative, including disabled
        // intent. The launcher must not restore an obsolete browser preference.
        backend = {
          enabled: false,
          scope: 'cytv',
          mode: 'clock',
          assetId: '',
          idleTimeoutMs: 900000
        };
        window.dispatchEvent(new Event('focus'));
      });
      await page.waitForFunction(() =>
        wallpaperEvents.includes('resume:screensaver')
      );
      assert.equal(
        await page.locator('#screensaverEnabled').getAttribute('aria-checked'),
        'false',
        'saved owner profile controls UI after owner restart'
      );
      assert.equal(
        await page
          .locator('#screensaverDelay-900000')
          .getAttribute('aria-pressed'),
        'true'
      );
      await page.evaluate(() => {
        backend = {
          enabled: true,
          scope: 'cytv',
          mode: 'photo',
          assetId: 'personal-photo',
          idleTimeoutMs: 30000
        };
        ScreensaverPersonal.prepare = () =>
          new Promise((resolve) => {
            window.finishIdlePrepare = resolve;
          });
        calls = [];
        window.dispatchEvent(new Event('focus'));
      });
      await page.clock.runFor(31000);
      assert.equal(
        await page.evaluate(() => typeof finishIdlePrepare),
        'function'
      );
      const beforeCancelResume = await page.evaluate(
        () =>
          wallpaperEvents.filter((event) => event === 'resume:screensaver')
            .length
      );
      await page.keyboard.press('ArrowRight');
      assert.equal(
        await page.evaluate(
          () =>
            wallpaperEvents.filter((event) => event === 'resume:screensaver')
              .length
        ),
        beforeCancelResume,
        'do not resume wallpaper until pending saver lease teardown completes'
      );
      await page.evaluate(() =>
        finishIdlePrepare({
          mediaUrl: 'http://127.0.0.1:1234/' + 'a'.repeat(32) + '/photo.jpg',
          dispose: () => {
            mediaCalls.push('dispose:interrupted-idle');
            return Promise.resolve();
          }
        })
      );
      assert.equal(
        (await page.evaluate(() => calls)).filter(
          (r) => r.method === 'screensaverEligible'
        ).length,
        0,
        'fresh input cancels automatic preparation before it can launch'
      );
      assert.ok(
        await page.evaluate(() =>
          mediaCalls.includes('dispose:interrupted-idle')
        )
      );
      if (edition === 'root') {
        await page.evaluate(() => {
          document.getElementById('renewalPanel').classList.remove('hidden');
          document.querySelector('[data-category=screensaver]').click();
          available = false;
          HomeScreensaver.activate(true);
        });
        await toggle
          .isDisabled()
          .then((disabled) => assert.equal(disabled, true));
        await page.evaluate(() => {
          available = true;
        });
        await page.clock.runFor(1200);
        await page.waitForFunction(
          () => !document.querySelector('#screensaverEnabled').disabled
        );
        const writes = await page.evaluate(
          () =>
            calls.filter((entry) => entry.method === 'screensaverConfigure')
              .length
        );
        await page.evaluate(() => {
          available = false;
          document.querySelector('#screensaverEnabled').click();
        });
        assert.equal(await toggle.getAttribute('aria-checked'), 'false');
        assert.equal(await toggle.isDisabled(), true);
        await page.evaluate(() => {
          available = true;
        });
        await page.clock.runFor(1200);
        assert.equal(await toggle.isDisabled(), false);
        assert.equal(
          await page.evaluate(
            () =>
              calls.filter((entry) => entry.method === 'screensaverConfigure')
                .length
          ),
          writes + 1,
          'Root availability readback does not replay a setting write'
        );
      }
      if (edition === 'noroot') {
        await page.evaluate(() => {
          backend = {
            enabled: true,
            scope: 'global',
            mode: 'ambient',
            assetId: '',
            idleTimeoutMs: 30000
          };
          popupUnavailable = true;
          document.getElementById('renewalPanel').classList.remove('hidden');
          document.querySelector('[data-category=screensaver]').click();
          window.dispatchEvent(new Event('focus'));
          HomeScreensaver.activate(true);
        });
        await page
          .locator('.screensaver-status')
          .filter({ hasText: 'only in Clean Your TV' })
          .waitFor();
        const inlineOrigin = 'http://cytv-screensaver.invalid/';
        await page.route(
          inlineOrigin + 'screensaver-companion/files/**',
          (route) => {
            const name = new URL(route.request().url()).pathname
              .split('/')
              .pop();
            return route.fulfill({
              path: path.join(root, 'screensaver', name)
            });
          }
        );
        await page.evaluate((origin) => {
          const base = document.createElement('base');
          base.href = origin;
          document.head.appendChild(base);
          calls = [];
        }, inlineOrigin);
        await page.locator('#screensaverPreview').click();
        const inline = page.locator('.screensaver-inline.visible');
        await inline.waitFor();
        await inline.contentFrame().locator('#clock:not([hidden])').waitFor();
        assert.deepEqual(
          await page.evaluate(() =>
            calls.filter(({ method }) => method === 'screensaverPreview')
          ),
          [],
          'the iframe uses the existing renderer without a popup request'
        );
        await page.keyboard.press('ArrowLeft');
        await inline.waitFor({ state: 'detached' });
        assert.equal(
          await page.locator('#screensaverPreview').isEnabled(),
          true
        );
        const bundledPhoto = 'wallpapers/ribbon-preview.jpg';
        await page.route(
          inlineOrigin + 'screensaver-companion/manifest.json',
          (route) =>
            route.fulfill({
              headers: { 'Access-Control-Allow-Origin': '*' },
              json: {
                files: {
                  'backgrounds/ribbon-photo.jpg':
                    'usr/palm/applications/com.gathin.tvhome/' + bundledPhoto
                }
              }
            })
        );
        await page.route(inlineOrigin + bundledPhoto, (route) =>
          route.fulfill({ path: path.join(root, 'launcher', bundledPhoto) })
        );
        await page.evaluate(() => {
          backend.mode = 'video';
          backend.assetId = 'ribbon-video';
          backend.quality = 'image';
          HomeScreensaver.activate(true);
        });
        await page.locator('#screensaverPreview').click();
        await inline.contentFrame().locator('#photo:not([hidden])').waitFor();
        await page.mouse.move(5, 5);
        await inline.waitFor({ state: 'detached' });
        await page.evaluate(() => {
          backend.mode = 'ambient';
          backend.assetId = '';
          backend.quality = 'auto';
          HomeScreensaver.activate(true);
        });
        await page.evaluate(() => {
          HomeScreensaver.activate(false);
          document.getElementById('renewalPanel').classList.add('hidden');
        });
        await page.keyboard.press('ArrowRight');
        await page.clock.runFor(32000);
        await inline.waitFor();
        assert.equal(
          await page.evaluate(() =>
            calls.some(({ method }) => method === 'screensaverEligible')
          ),
          false
        );
        await page.evaluate(() => window.dispatchEvent(new Event('blur')));
        await inline.waitFor({ state: 'detached' });
      }
      assert.deepEqual(errors, []);
      await page.close();
    }
    console.log(
      'screensaver settings UI: both edition routes, controls, stale replies and local idle ownership passed'
    );
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
