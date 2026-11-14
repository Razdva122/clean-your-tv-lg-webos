const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
(async () => {
  const browser = await chromium.launch({
    headless: true,
    channel: process.env.BROWSER_CHANNEL || 'chrome'
  });
  try {
    const page = await browser.newPage({
      viewport: { width: 1280, height: 720 }
    });
    await page.setContent('<div id="host"></div>');
    await page.evaluate(() => {
      window.HomeI18n = {
        language: () => 'en',
        t: (s) => s,
        clockFormat: () => 'auto',
        formatTime: () => '13:40'
      };
      window.testState = {
        themeId: 'test',
        title: 'Test theme',
        posterURL:
          'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="16" height="9"/>',
        available: ['4k', '1080p', 'image'],
        actualQuality: '1080p',
        preferenceQuality: 'auto',
        dim: 0.3,
        capabilities: { uhd: null }
      };
      window.HomeWallpaper = {
        state: () => window.testState,
        setQuality: (q) => {
          testState.preferenceQuality = q;
          return Promise.resolve();
        },
        setDim: (d) => {
          testState.dim = d;
          return Promise.resolve();
        },
        resetPreferences: () => {
          testState.dim = 0.2;
          testState.preferenceQuality = 'auto';
        }
      };
    });
    await page.addScriptTag({
      path: path.resolve('launcher/wallpaper-panel.js')
    });
    await page.addStyleTag({
      path: path.resolve('launcher/wallpaper-panel.css')
    });
    await page.evaluate(() =>
      HomeWallpaperPanel.mount(document.getElementById('host'))
    );
    assert.equal(
      await page.locator('#wallpaperPreview').getAttribute('src'),
      await page.evaluate(() => testState.posterURL)
    );
    assert.match(
      await page.locator('#wallpaperCapability').innerText(),
      /unknown/i
    );
    assert.match(await page.locator('#wallpaperActual').innerText(), /1080p/);
    await page.evaluate(() => {
      testState.paused = true;
      testState.actualQuality = 'image';
      HomeWallpaperPanel.refresh();
    });
    assert.match(
      await page.locator('#wallpaperActual').innerText(),
      /Paused while settings are open/,
      'suspension is distinct from image fallback'
    );
    await page.evaluate(() => {
      testState.paused = false;
      HomeWallpaperPanel.refresh();
    });
    assert.match(
      await page.locator('#wallpaperActual').innerText(),
      /Image/,
      'actual image mode remains visible when not paused'
    );
    await page.locator('[data-wallpaper-quality="4k"]').click();
    assert.equal(await page.evaluate(() => testState.preferenceQuality), '4k');
    await page.evaluate(() => {
      window.previewTheme = true;
      window.previewOn = true;
      window.HomeInputShelf = {
        enabled: () => previewTheme,
        previewEnabled: () => previewOn,
        togglePreview: () => {
          previewOn = !previewOn;
        }
      };
      HomeWallpaperPanel.refresh();
    });
    assert(
      await page.locator('#wallpaperInputPreviewWarning').isVisible(),
      '4K with active input previews explains the temporary 1080p poster'
    );
    assert.match(
      await page.locator('#wallpaperInputPreviewWarning').innerText(),
      /static 1080p/
    );
    await page.evaluate(() => {
      previewTheme = false;
      HomeWallpaperPanel.refresh();
    });
    assert(
      await page.locator('#wallpaperInputPreviewWarning').isHidden(),
      'themes without input previews have no warning'
    );
    await page.evaluate(() => {
      previewTheme = true;
      testState.preferenceQuality = '1080p';
      HomeWallpaperPanel.refresh();
    });
    assert(
      await page.locator('#wallpaperInputPreviewWarning').isHidden(),
      '1080p selection has no 4K warning'
    );
    await page.evaluate(() => {
      testState.preferenceQuality = 'auto';
      testState.actualQuality = '4k';
      HomeWallpaperPanel.refresh();
    });
    assert(
      await page.locator('#wallpaperInputPreviewWarning').isVisible(),
      'actual Auto UHD playback also explains the fallback'
    );
    await page.evaluate(() => {
      window.savedToggle = HomeInputShelf.togglePreview;
      HomeInputShelf.togglePreview = () => {};
    });
    await page.locator('#wallpaperDisableInputPreview').click();
    assert(
      await page.locator('#wallpaperInputPreviewWarning').isVisible(),
      'a failed preference save keeps the warning visible'
    );
    assert.equal(
      await page.locator('#wallpaperNotice').innerText(),
      'Could not change wallpaper settings.'
    );
    await page.evaluate(() => {
      HomeInputShelf.togglePreview = savedToggle;
    });
    await page.locator('#wallpaperDisableInputPreview').click();
    assert.equal(
      await page.evaluate(() => previewOn),
      false,
      'the existing preview preference is disabled'
    );
    assert(
      await page.locator('#wallpaperInputPreviewWarning').isHidden(),
      'warning disappears after disabling previews'
    );
    assert.equal(
      await page.evaluate(() =>
        document.activeElement.getAttribute('data-wallpaper-quality')
      ),
      '4k',
      'focus stays on a visible quality control'
    );
    await page.evaluate(() => {
      previewOn = true;
      testState.preferenceQuality = '4k';
      testState.actualQuality = '1080p';
      HomeWallpaperPanel.refresh();
    });
    await page.evaluate(() => {
      testState.capabilities.uhd = false;
      HomeWallpaperPanel.refresh();
    });
    assert(
      await page.locator('[data-wallpaper-quality="4k"]').isDisabled(),
      'known unsupported UHD disabled'
    );
    await page.locator('#wallpaperDimPlus').click();
    assert.equal(await page.evaluate(() => testState.dim), 0.35);
    await page.locator('#wallpaperDimPlus').focus();
    await page.evaluate(() =>
      document.dispatchEvent(new Event('home-wallpaper-change'))
    );
    assert.equal(
      await page.evaluate(() => document.activeElement.id),
      'wallpaperDimPlus',
      'state updates preserve focus'
    );
    await page.evaluate(() => {
      testState.available = ['image'];
      testState.actualQuality = 'image';
      HomeWallpaperPanel.refresh();
    });
    assert(await page.locator('[data-wallpaper-quality="4k"]').isDisabled());
    assert.equal(
      await page.locator('#wallpaperNotice').innerText(),
      'This wallpaper has no video version.'
    );
    await page.evaluate(() => {
      testState.dim = 0.8;
      HomeWallpaperPanel.refresh();
    });
    await page.locator('#wallpaperDimPlus').click();
    assert.equal(await page.evaluate(() => testState.dim), 0.85);
    assert(
      await page.locator('#wallpaperDimPlus').isDisabled(),
      'upper dim bound is visible'
    );
    assert.equal(
      await page.evaluate(() => document.activeElement.id),
      'wallpaperDimMinus',
      'boundary keeps focus on an operable control'
    );
    await page.locator('#wallpaperReset').click();
    assert.equal(await page.evaluate(() => testState.dim), 0.2);
    await page.evaluate(() => {
      testState = {
        themeId: 'classic',
        available: [],
        capabilities: { uhd: false }
      };
      HomeWallpaperPanel.refresh();
    });
    assert(await page.locator('#wallpaperPreview').isHidden());
    assert.match(
      await page.locator('#wallpaperNotice').innerText(),
      /wallpaper/i
    );
    assert(await page.locator('#wallpaperDimPlus').isDisabled());
    await page.addScriptTag({
      path: path.resolve('launcher/wallpaper-locales.js')
    });
    await page.addScriptTag({
      path: path.resolve('launcher/settings-categories.js')
    });
    await page.evaluate(() => {
      testState = {
        themeId: 'test',
        title: 'Test theme',
        posterURL:
          'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="16" height="9"/>',
        available: ['4k', '1080p', 'image'],
        actualQuality: '1080p',
        preferenceQuality: 'auto',
        dim: 0.3,
        capabilities: { uhd: null }
      };
      const overlay = document.createElement('div'),
        card = document.createElement('div');
      card.innerHTML =
        '<div class="settings-heading">Settings</div><div class="settings-footer"><button>Close</button></div>';
      overlay.appendChild(card);
      document.body.appendChild(overlay);
      window.categories = SettingsCategories.attach(overlay, card, [
        { id: 'home', label: 'Home', elements: [] },
        {
          id: 'wallpapers',
          label: 'Wallpapers',
          elements: [document.getElementById('host')]
        }
      ]);
      categories.open();
    });
    await page.locator('[data-category=wallpapers]').click();
    await page.keyboard.press('ArrowRight');
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
      '4k'
    );
    await page.keyboard.press('Enter');
    assert.equal(await page.evaluate(() => testState.preferenceQuality), '4k');
    await page.keyboard.press('Escape');
    assert.equal(
      await page.evaluate(() =>
        document.activeElement.getAttribute('data-category')
      ),
      'wallpapers'
    );
    for (const locale of [
      'cs',
      'de',
      'es',
      'pt-BR',
      'fr',
      'it',
      'ko',
      'hi',
      'pl',
      'ru',
      'zh-Hans',
      'zh-Hant'
    ]) {
      await page.evaluate((locale) => {
        HomeI18n.language = () => locale;
        HomeWallpaperPanel.refresh();
      }, locale);
      assert.notEqual(
        await page.locator('#wallpaperReset').innerText(),
        'Reset to theme defaults',
        locale + ' localized reset'
      );
      assert(
        !(
          await page.locator('#wallpaperInputPreviewWarning').innerText()
        ).includes('During HDMI previews'),
        locale + ' localized HDMI warning'
      );
      assert.notEqual(
        await page.locator('#wallpaperDisableInputPreview').innerText(),
        'Disable HDMI previews',
        locale + ' localized disable action'
      );
      await page.evaluate(() => {
        testState.paused = true;
        testState.actualQuality = 'image';
        testState.notice =
          'Video dimensions do not match the theme. Video playback failed. Using the image.';
        HomeWallpaperPanel.refresh();
      });
      assert(
        !(await page.locator('#wallpaperActual').innerText()).includes(
          'Paused while settings are open'
        ),
        locale + ' localized paused state'
      );
      assert(
        !(await page.locator('#wallpaperNotice').innerText()).includes(
          'Video dimensions do not match'
        ),
        locale + ' localized dimension notice'
      );
      assert(
        !(await page.locator('#wallpaperNotice').innerText()).includes(
          'Video playback failed'
        ),
        locale + ' localized fallback suffix'
      );
      assert(
        await page
          .locator('#homeWallpaperPanel')
          .evaluate((el) => el.scrollWidth <= el.clientWidth + 1),
        locale + ' fits'
      );
    }
    console.log(
      'PASS wallpaper actual preview, quality availability, bounded dim, reset and focus retention'
    );
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
