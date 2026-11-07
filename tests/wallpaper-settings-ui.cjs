// Both real edition bootstraps keep the wallpaper playing beneath settings.
const { chromium, stage, fs, path } = require('./themes/browser.cjs');
const assert = require('node:assert/strict');
(async () => {
  const site = stage(),
    server = require('node:http').createServer((req, res) => {
      const file = path.resolve(
        site,
        '.' + new URL(req.url, 'http://localhost').pathname
      );
      if (!file.startsWith(site + path.sep) || !fs.existsSync(file))
        return res.writeHead(404).end();
      res.setHeader(
        'Content-Type',
        {
          '.js': 'application/javascript',
          '.json': 'application/json',
          '.css': 'text/css',
          '.png': 'image/png',
          '.jpg': 'image/jpeg',
          '.html': 'text/html'
        }[path.extname(file)] || 'application/octet-stream'
      );
      res.end(fs.readFileSync(file));
    });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const browser = await chromium.launch({
    headless: true,
    channel: process.env.BROWSER_CHANNEL || 'chrome'
  });
  try {
    for (const edition of ['launcher', 'root-launcher']) {
      const page = await browser.newPage({
          viewport: { width: 1280, height: 720 },
          locale: 'en-US'
        }),
        errors = [];
      page.on('pageerror', (e) => errors.push(e.message));
      await page.route(/^https:/, (route) => route.abort());
      await page.goto(
        'http://127.0.0.1:' +
          server.address().port +
          '/' +
          edition +
          '/index.html'
      );
      await page.locator('#tiles .focused').waitFor();
      await page.evaluate(async () => {
        const item = (await ThemeManager.list()).find(
          (i) => i.id === 'builtin:liquid-glass'
        );
        await ThemeManager.selectInstalled(item);
      });
      const poster = await page.evaluate(() => HomeWallpaper.state().posterURL);
      assert(poster, 'real theme has wallpaper');
      await page.locator('#btnSettings').click();
      await page.locator('[data-category=wallpapers]').click();
      assert.equal(
        await page.locator('#wallpaperPreview').getAttribute('src'),
        poster,
        'suspension retains actual borrowed wallpaper'
      );
      assert(
        await page
          .locator('#wallpaperPreview')
          .evaluate((img) => img.complete && img.naturalWidth > 0),
        'borrowed preview decodes'
      );
      assert(
        await page.locator('[data-wallpaper-quality="4k"]').isDisabled(),
        'image-only theme disables video'
      );
      await page.keyboard.press('ArrowRight');
      assert.equal(
        await page.evaluate(() => document.activeElement.id),
        'wallpaperSourceTheme'
      );
      await page.keyboard.press('ArrowDown');
      assert.equal(
        await page.evaluate(() => document.activeElement.id),
        'wallpaperBuiltin-black-hole'
      );
      await page.keyboard.press('ArrowDown');
      assert.equal(
        await page.evaluate(() =>
          document.activeElement.getAttribute('data-wallpaper-quality')
        ),
        'auto'
      );
      await page.keyboard.press('ArrowRight');
      assert.equal(
        await page.evaluate(() =>
          document.activeElement.getAttribute('data-wallpaper-quality')
        ),
        'image'
      );
      await page.keyboard.press('Enter');
      assert.equal(
        await page.evaluate(() => HomeWallpaper.state().preferenceQuality),
        'image'
      );
      await page.locator('#wallpaperDimPlus').click();
      assert.equal(
        await page.evaluate(() => document.activeElement.id),
        'wallpaperDimPlus'
      );
      await page.locator('#wallpaperReset').click();
      assert.equal(
        await page.evaluate(() => HomeWallpaper.state().preferenceQuality),
        'auto'
      );
      await page.screenshot({
        path: 'build/tests/wallpapers-active-' + edition + '.png'
      });
      await page.keyboard.press('Escape');
      assert.equal(
        await page.evaluate(() =>
          document.activeElement.getAttribute('data-category')
        ),
        'wallpapers'
      );
      await page.keyboard.press('Escape');
      assert(
        !(await page.locator('#homeWallpaperPanel').isVisible()),
        'Back closes settings'
      );
      await page.evaluate((bytes) => {
        const url = URL.createObjectURL(
          new Blob([Uint8Array.from(atob(bytes), (c) => c.charCodeAt(0))], {
            type: 'video/mp4'
          })
        );
        HomeWallpaper.configure({
          manifest: {
            id: 'test:settings-video',
            title: 'Settings video',
            defaults: { dim: 0.3, wallpaperAssetId: 'poster' },
            assets: [{ id: 'poster', width: 1920, height: 1080 }],
            wallpaperVideo: {
              variants: [{ quality: '1080p', width: 1920, height: 1080 }]
            }
          },
          assetHandles: { poster: HomeWallpaper.state().posterURL },
          videoHandles: { '1080p': url }
        });
      }, fs.readFileSync('tests/themes/fixtures/wallpaper-blue.mp4').toString('base64'));
      await page.waitForFunction(
        () => HomeWallpaper.state().actualQuality === '1080p'
      );
      await page.evaluate(() => {
        window.settingsVideo = document.getElementById('ctvWallpaperVideo');
        window.settingsVideoTime = settingsVideo.currentTime;
      });
      await page.locator('#btnSettings').click();
      assert(
        await page.evaluate(
          () =>
            document.getElementById('ctvWallpaperVideo') === settingsVideo &&
            !settingsVideo.paused
        ),
        edition + ': opening settings retains the playing wallpaper'
      );
      await page.locator('[data-category=wallpapers]').click();
      await page.waitForFunction(
        () => settingsVideo.currentTime > settingsVideoTime + 0.2
      );
      assert.equal(
        await page.evaluate(() => HomeWallpaper.state().paused),
        false,
        'wallpaper is playing beneath settings'
      );
      // The nested theme browser must not tear down the wallpaper either.
      await page.locator('[data-category=themes]').click();
      assert(
        await page.evaluate(
          () =>
            document.getElementById('ctvWallpaperVideo') === settingsVideo &&
            !settingsVideo.paused
        ),
        'theme settings retain the same decoder'
      );
      await page.locator('[data-category=wallpapers]').click();
      await page.keyboard.press('Escape');
      await page.keyboard.press('Escape');
      assert(
        await page.evaluate(
          () =>
            document.getElementById('ctvWallpaperVideo') === settingsVideo &&
            !settingsVideo.paused
        ),
        edition + ': closing settings does not restart the video'
      );
      await page.evaluate(() => {
        const url = settingsVideo.src;
        HomeWallpaper.reset();
        URL.revokeObjectURL(url);
      });
      await page.evaluate(async () => {
        InputSources.setPreviewEnabled(localStorage, true);
        await PersonalWallpaper.select('builtin:black-hole');
        HomeWallpaper.setQuality('4k');
        HomeLayoutState.setThemeLayout({
          preset: 'dock-grid',
          columns: 5,
          spacingScale: 1,
          textScale: 1,
          focusScale: 1.1,
          inputs: 'shelf'
        });
      });
      await page.waitForFunction(
        () => HomeWallpaper.state().actualQuality === '4k'
      );
      await page.locator('#btnSettings').click();
      await page.locator('[data-category=wallpapers]').click();
      assert(
        await page.locator('#wallpaperInputPreviewWarning').isVisible(),
        edition + ': 4K with HDMI previews shows the warning'
      );
      await page.locator('[data-wallpaper-quality="4k"]').focus();
      await page.screenshot({
        path: 'build/tests/wallpaper-preview-warning-' + edition + '.png'
      });
      await page.locator('#wallpaperDisableInputPreview').focus();
      await page.keyboard.press('Enter');
      assert.equal(
        await page.evaluate(() => HomeInputShelf.previewEnabled()),
        false,
        'the action saves the existing preview preference'
      );
      assert.equal(
        await page.locator('#homePreviewInputs').getAttribute('aria-checked'),
        'false',
        'the original settings switch stays in sync'
      );
      assert(await page.locator('#wallpaperInputPreviewWarning').isHidden());
      assert.equal(
        await page.evaluate(() =>
          document.activeElement.getAttribute('data-wallpaper-quality')
        ),
        '4k',
        'remote focus survives hiding the warning'
      );
      await page.evaluate(() => {
        HomeInputShelf.togglePreview();
        HomeWallpaperPanel.refresh();
      });
      assert(await page.locator('#wallpaperInputPreviewWarning').isVisible());
      await page.evaluate(() =>
        HomeLayoutState.setThemeLayout({
          preset: 'dock-grid',
          columns: 5,
          spacingScale: 1,
          textScale: 1,
          focusScale: 1.1,
          inputs: 'menu'
        })
      );
      assert(
        await page.locator('#wallpaperInputPreviewWarning').isHidden(),
        'a theme without previews hides the warning immediately'
      );
      await page.keyboard.press('Escape');
      await page.keyboard.press('Escape');
      await page.evaluate(() =>
        ThemeManager.begin({
          id: 'builtin:ribbon',
          title: 'Ribbon',
          builtin: true
        })
      );
      assert.equal(
        await page.evaluate(() => HomeWallpaper.state().source),
        'theme',
        'a theme trial shows its own wallpaper instead of the selected Black Hole'
      );
      assert.equal(
        await page.evaluate(() => HomeWallpaper.state().themeId),
        'builtin:ribbon'
      );
      assert.equal(
        await page.evaluate(() => PersonalWallpaper.state().builtinId),
        'builtin:black-hole',
        'a trial does not persist a different wallpaper source'
      );
      await page.evaluate(() => ThemeManager.cancel());
      assert.equal(
        await page.evaluate(() => HomeWallpaper.state().themeId),
        'builtin:black-hole',
        'cancel restores the selected wallpaper'
      );
      await page.evaluate(() =>
        ThemeManager.begin({
          id: 'builtin:classic',
          title: 'Classic',
          builtin: true
        })
      );
      assert.equal(
        await page.evaluate(() => HomeWallpaper.state().posterURL),
        '',
        'Classic trial is not covered by personal media'
      );
      await page.evaluate(() => ThemeManager.cancel());
      assert.equal(
        await page.evaluate(() => HomeWallpaper.state().themeId),
        'builtin:black-hole'
      );
      await page.evaluate(async () => {
        try {
          await ThemeManager.begin({ id: 'builtin:missing', title: 'Missing' });
        } catch (_) {}
      });
      assert.equal(
        await page.evaluate(() => HomeWallpaper.state().themeId),
        'builtin:black-hole',
        'failed trial restores the selected wallpaper'
      );
      await page.clock.install();
      await page.evaluate(() =>
        ThemeManager.begin({
          id: 'builtin:ribbon',
          title: 'Ribbon',
          builtin: true
        })
      );
      await page.clock.fastForward(21000);
      await page.waitForFunction(
        () =>
          !ThemeManager.current().trial &&
          HomeWallpaper.state().themeId === 'builtin:black-hole'
      );
      assert.equal(
        await page.evaluate(() => PersonalWallpaper.state().builtinId),
        'builtin:black-hole',
        'timeout leaves the saved wallpaper untouched'
      );
      await page.evaluate(() =>
        ThemeManager.begin({
          id: 'builtin:ribbon',
          title: 'Ribbon',
          builtin: true
        })
      );
      await page.reload();
      await page.locator('#tiles .focused').waitFor();
      await page.evaluate(() => HomeUIReady);
      assert.equal(
        await page.evaluate(() => ThemeManager.current().id),
        'builtin:classic',
        'interrupted trial follows existing Classic recovery'
      );
      assert.equal(
        await page.evaluate(() => HomeWallpaper.state().themeId),
        'builtin:black-hole',
        'interrupted trial cannot overwrite the saved wallpaper'
      );
      await page.evaluate(async () => {
        await ThemeManager.begin({
          id: 'builtin:ribbon',
          title: 'Ribbon',
          builtin: true
        });
        await ThemeManager.confirm();
      });
      assert.equal(
        await page.evaluate(() => PersonalWallpaper.state().source),
        'theme',
        'Keep commits the new theme wallpaper'
      );
      await page.evaluate(async () => {
        await PersonalWallpaper.select('builtin:black-hole');
        await ThemeManager.selectInstalled({ id: 'builtin:ribbon' });
      });
      assert.equal(
        await page.evaluate(() => HomeWallpaper.state().themeId),
        'builtin:black-hole',
        'reselecting the accepted theme retains its custom wallpaper'
      );
      await page.evaluate(() => PersonalWallpaper.select('theme'));
      await page.evaluate(() => ThemeManager.reset());
      await page.locator('#btnSettings').click();
      await page.locator('[data-category=wallpapers]').click();
      assert(
        await page.locator('#wallpaperPreview').isHidden(),
        'Classic empty state'
      );
      await page.screenshot({
        path: 'build/tests/wallpapers-' + edition + '.png'
      });
      assert.deepEqual(errors, [], edition + ' browser errors');
      await page.close();
    }
    console.log(
      'PASS both editions continuous settings video, nested themes, poster preview, controls, remote navigation, reset and Classic'
    );
  } finally {
    await browser.close();
    await new Promise((resolve) => server.close(resolve));
  }
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
