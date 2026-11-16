'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const { chromium } = require('playwright');
const root = path.resolve(__dirname, '..');
(async () => {
  assert.ok(fs.existsSync(path.join(root, 'launcher/screensaver-personal.js')));
  const server = http.createServer((req, res) =>
    res.end('<!doctype html><body></body>')
  );
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const browser = await chromium.launch({
    headless: true,
    channel: process.env.BROWSER_CHANNEL || 'chrome'
  });
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', (e) => errors.push(e.message));
    async function load() {
      await page.goto('http://127.0.0.1:' + server.address().port);
      for (const file of [
        'theme-policy.js',
        'theme-data.js',
        'personal-wallpaper.js',
        'screensaver-personal.js'
      ])
        await page.addScriptTag({ path: path.join(root, 'launcher', file) });
      await page.evaluate(() => {
        window.StorageBudget = {
          check: () => Promise.resolve({}),
          quotaFailure: (error) => Promise.reject(error)
        };
        window.HomeWallpaper = {
          setPersonal: (value) => {
            window.homePersonal = value;
          }
        };
        window.cacheEvents = [];
        window.badHandle = false;
        function lease(kind) {
          return Promise.resolve({
            acquire: () => {
              cacheEvents.push('acquire:' + kind);
              return Promise.resolve(
                kind === 'photo'
                  ? {
                      photo:
                        'http://127.0.0.1:1234/' + 'a'.repeat(32) + '/photo.jpg'
                    }
                  : {
                      '4k': badHandle
                        ? 'https://example.com/movie.mp4'
                        : 'http://127.0.0.1:1234/' + 'a'.repeat(32) + '/4k.mp4',
                      '1080p':
                        'http://127.0.0.1:1234/' + 'a'.repeat(32) + '/1080p.mp4'
                    }
              );
            },
            dispose: () => {
              cacheEvents.push('dispose:' + kind);
              return Promise.resolve();
            }
          });
        }
        window.WallpaperMediaCache = {
          prepare: () => lease('video'),
          prepareImage: () => lease('photo')
        };
      });
    }
    await load();
    const videos = ['4k', '1080p'].map((quality) => ({
      quality,
      data: fs
        .readFileSync(
          path.join(root, 'themes/ribbon/assets/wallpaper-' + quality + '.mp4')
        )
        .toString('base64')
    }));
    await page.evaluate((videos) => {
      const canvas = document.createElement('canvas');
      canvas.width = 1280;
      canvas.height = 720;
      const data = canvas.toDataURL('image/jpeg').split(',')[1];
      function descriptor(data, mediaType, width, height) {
        const bytes = Uint8Array.from(atob(data), (x) => x.charCodeAt(0));
        return {
          data,
          mediaType,
          width,
          height,
          size: bytes.length,
          sha256: ThemeData.hash(bytes)
        };
      }
      window.photoEnvelope = {
        schemaVersion: 1,
        kind: 'wallpaper',
        source: 'cytv',
        image: descriptor(data, 'image/jpeg', 1280, 720),
        variants: []
      };
      window.videoEnvelope = {
        ...photoEnvelope,
        variants: videos.map((v) => ({
          quality: v.quality,
          ...descriptor(
            v.data,
            'video/mp4',
            v.quality === '4k' ? 3840 : 1920,
            v.quality === '4k' ? 2160 : 1080
          )
        }))
      };
    }, videos);
    assert.deepEqual(await page.evaluate(() => ScreensaverPersonal.start()), {
      photo: false,
      video: false
    });
    await page.evaluate(async () => {
      await ScreensaverPersonal.receive('photo', photoEnvelope);
      await ScreensaverPersonal.receive('video', videoEnvelope);
      if (PersonalWallpaper.state().installed)
        throw Error('Modified wallpaper slot');
    });
    assert.deepEqual(await page.evaluate(() => ScreensaverPersonal.state()), {
      photo: true,
      video: true
    });
    const result = await page.evaluate(async () => {
      const photo = await ScreensaverPersonal.prepare('photo');
      const video = await ScreensaverPersonal.prepare('video');
      const urls = [photo.mediaUrl, video.mediaUrl];
      await photo.dispose();
      await photo.dispose();
      await video.dispose();
      return { urls, events: cacheEvents };
    });
    assert.match(result.urls[0], /\/photo.jpg$/);
    assert.match(result.urls[1], /\/4k.mp4$/);
    assert.deepEqual(result.events, [
      'acquire:photo',
      'acquire:video',
      'dispose:photo',
      'dispose:video'
    ]);
    const renditions = await page.evaluate(async () => {
      const hd = await ScreensaverPersonal.prepare(
        'video',
        null,
        '1080p',
        true
      );
      const poster = await ScreensaverPersonal.prepare(
        'video',
        null,
        'image',
        true
      );
      const preview = await ScreensaverPersonal.preview('video');
      URL.revokeObjectURL(preview.url);
      await hd.dispose();
      await poster.dispose();
      return [
        hd.mediaUrl.split('/').pop(),
        poster.mediaUrl.split('/').pop(),
        preview.qualities
      ];
    });
    assert.deepEqual(renditions, ['1080p.mp4', 'photo.jpg', ['4k', '1080p']]);
    await page.evaluate(async () => {
      for (const [mode, envelope] of [
        ['video', photoEnvelope],
        [
          'photo',
          {
            ...photoEnvelope,
            image: { ...photoEnvelope.image, sha256: '0'.repeat(64) }
          }
        ]
      ]) {
        let failed = false;
        try {
          await ScreensaverPersonal.receive(mode, envelope);
        } catch (_) {
          failed = true;
        }
        if (!failed) throw Error('Invalid import accepted');
      }
      StorageBudget.check = () => Promise.reject(Error('Quota exceeded'));
      try {
        await ScreensaverPersonal.receive('photo', photoEnvelope);
        throw Error('Quota failure ignored');
      } catch (e) {
        if (e.message === 'Quota failure ignored') throw e;
      }
      badHandle = true;
      try {
        await ScreensaverPersonal.prepare('video');
        throw Error('External URL accepted');
      } catch (e) {
        if (e.message === 'External URL accepted') throw e;
      }
    });
    assert.deepEqual(
      await page.evaluate(() => ScreensaverPersonal.state()),
      { photo: true, video: true },
      'failed replacement preserves independent slots'
    );
    await page.evaluate(async () => {
      StorageBudget.check = () => Promise.resolve({});
      badHandle = false;
      await PersonalWallpaper.selectMedia('photo');
      if (!PersonalWallpaper.state().installed)
        throw Error('Home cannot select shared photo');
      const dbs = await indexedDB.databases();
      if (dbs.length !== 1 || dbs[0].name !== 'ctv-personal-wallpaper-v1')
        throw Error('Screensaver created a duplicate media store');
      await ScreensaverPersonal.receive('photo', videoEnvelope);
      const still = await ScreensaverPersonal.prepare('photo');
      if (!still.mediaUrl.endsWith('/4k.mp4') || still.mode !== 'video')
        throw Error('Lost prepared native-resolution still rendition');
      await still.dispose();
    });
    await load();
    assert.deepEqual(
      await page.evaluate(() => ScreensaverPersonal.start()),
      { photo: true, video: true },
      'both slots persist across reload'
    );
    await page.evaluate(async () => {
      await PersonalWallpaper.start();
      if (!homePersonal || homePersonal.videoLease)
        throw Error('Replacing library photo changed pinned Home photo');
      const saver = await ScreensaverPersonal.prepare('photo');
      if (!saver.mediaUrl.endsWith('/4k.mp4') || saver.mode !== 'video')
        throw Error('Reload lost new library UHD photo');
      await saver.dispose();
    });
    await page.evaluate(() => {
      window.cancelled = false;
      WallpaperMediaCache.prepare = () =>
        Promise.resolve({
          acquire: () =>
            new Promise((resolve) => {
              window.finishAcquire = resolve;
            }),
          dispose: () => {
            cacheEvents.push('dispose:pending');
            return Promise.resolve();
          }
        });
      window.cancelledPreparation = ScreensaverPersonal.prepare(
        'video',
        () => cancelled
      ).then(
        () => 'accepted',
        () => 'cancelled'
      );
    });
    await page.waitForFunction(() => typeof finishAcquire === 'function');
    await page.evaluate(() => {
      cancelled = true;
    });
    await page.waitForFunction(() => cacheEvents.includes('dispose:pending'));
    assert.equal(
      await page.evaluate(async () => {
        finishAcquire({});
        return cancelledPreparation;
      }),
      'cancelled',
      'cancelled prepare releases in-flight acquisition'
    );
    assert.deepEqual(errors, []);
    console.log(
      'PASS personal screensaver: validation, independent persistence, best quality and lease teardown'
    );
  } finally {
    await browser.close();
    await new Promise((resolve) => server.close(resolve));
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
