'use strict';
const { assert, fs, path, chromium, stage } = require('./browser.cjs'),
  http = require('http');
const entry = require('../../scripts/check-theme-submissions.cjs')
  .loadRegistry()
  .find((e) => e.record.title === 'Channel');
const envelope = {
  descriptor: fs
    .readFileSync(path.resolve('showcase', entry.base, 'cytv-theme.json'))
    .toString('base64'),
  files: {}
};
for (const name of entry.files.filter((n) => n !== 'cytv-theme.json'))
  envelope.files[name] = fs
    .readFileSync(path.resolve('showcase', entry.base, name))
    .toString('base64');
async function exerciseRollback(page, rollBack) {
  const downloads = await page.evaluate(async (input) => {
    ThemeManager.reset();
    await ThemeStore.clear();
    const decode = (s) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));
    const manifest = JSON.parse(ThemeData.decode(decode(input.descriptor)));
    const downloads = [];
    for (let i = 0; i < 8; i++) {
      manifest.themeVersion = '2.0.' + i;
      manifest.requires.minimumHomeVersion = '1.5.1';
      const descriptor = btoa(
        String.fromCharCode(...ThemeData.encode(JSON.stringify(manifest)))
      );
      const item = await ThemeManager.installEnvelope({
        schemaVersion: 1,
        descriptor,
        files: input.files
      });
      downloads.push(item.digest);
    }
    manifest.title = 'Compatible replacement';
    manifest.requires.minimumHomeVersion = '1.4.0';
    const descriptor = btoa(
      String.fromCharCode(...ThemeData.encode(JSON.stringify(manifest)))
    );
    return {
      keys: downloads.sort(),
      compatible: { schemaVersion: 1, descriptor, files: input.files }
    };
  }, envelope);
  rollBack();
  await page.reload();
  await page.locator('#tiles .focused').waitFor();
  await assert.rejects(
    page.evaluate(
      (pack) => ThemeManager.installEnvelope(pack),
      downloads.compatible
    ),
    /8 themes maximum/
  );
  await page.locator('#btnSettings').click();
  await page.locator('[data-category=themes]').click();
  const rows = page
    .locator('.theme-option')
    .filter({ hasText: 'Unavailable downloaded theme' });
  await rows.last().waitFor();
  assert.equal(await rows.count(), 8);
  const titles = await rows.locator('strong').allTextContents();
  assert.deepEqual(
    titles.slice(0, 2),
    downloads.keys
      .slice(0, 2)
      .map((key) => 'Unavailable downloaded theme · ' + key.slice(0, 12))
  );
  const first = rows.first();
  assert.deepEqual(await first.getByRole('button').allTextContents(), [
    'Remove'
  ]);
  assert.equal(await first.locator('img').count(), 0);
  const remove = first.getByRole('button', { name: 'Remove', exact: true });
  await remove.click();
  await page.getByText(titles[0], { exact: true }).waitFor();
  await page.locator('#themeRemoveCancel').click();
  await remove.waitFor();
  assert.equal(await rows.count(), 8);
  await remove.click();
  await page.locator('#themeRemoveConfirm').click();
  await page.waitForFunction(
    () => document.querySelectorAll('.theme-unavailable').length === 7
  );
  const added = await page.evaluate(
    (pack) => ThemeManager.installEnvelope(pack),
    downloads.compatible
  );
  const remaining = await page.evaluate(async (keys) => {
    const packs = await Promise.all(keys.map((key) => ThemeStore.get(key)));
    return keys.filter((_, index) => packs[index]);
  }, downloads.keys);
  assert.deepEqual(remaining, downloads.keys.slice(1));
  assert.equal(
    await page.evaluate(async () => (await ThemeStore.list()).length),
    8
  );

  await page.locator('[data-category=language]').click();
  await page.locator('[data-category=themes]').click();
  await page
    .locator('.theme-option')
    .filter({ hasText: 'Compatible replacement' })
    .getByRole('button', { name: 'Apply theme', exact: true })
    .click();
  await page.waitForFunction(
    (digest) =>
      ThemeManager.current().digest === digest && !ThemeManager.current().trial,
    added.digest
  );

  // An incomplete package must have a Remove action even without previewable files.
  await page.evaluate(async (key) => {
    const pack = await ThemeStore.get(key);
    delete pack.files[Object.keys(pack.files)[0]];
    await ThemeStore.put(pack, pack.size);
  }, added.digest);
  await page.locator('[data-category=language]').click();
  await page.locator('[data-category=themes]').click();
  await rows.nth(7).waitFor();
  const incomplete = rows.nth(
    remaining.filter((key) => key < added.digest).length
  );
  await assert.rejects(
    page.evaluate(
      (key) => ThemeManager.remove({ unavailable: true, storageKey: key }),
      added.digest
    ),
    /Switch to another theme/
  );
  await incomplete.getByRole('button', { name: 'Remove', exact: true }).click();
  await page.getByText('Classic will be restored.', { exact: true }).waitFor();
  await page.locator('#themeRemoveConfirm').click();
  await page.waitForFunction(
    () => document.querySelectorAll('.theme-unavailable').length === 7
  );
  assert.equal(
    await page.evaluate(() => ThemeManager.current().id),
    'builtin:classic'
  );
  assert.equal(
    await page.evaluate((key) => ThemeStore.get(key), added.digest),
    undefined
  );
}

(async () => {
  const site = stage(),
    server = http.createServer((req, res) => {
      const file = path.resolve(
        site,
        '.' + new URL(req.url, 'http://localhost').pathname
      );
      if (!file.startsWith(site + path.sep) || !fs.existsSync(file))
        return res.writeHead(404).end();
      res.setHeader(
        'Content-Type',
        file.endsWith('.js')
          ? 'application/javascript'
          : file.endsWith('.json')
            ? 'application/json'
            : file.endsWith('.css')
              ? 'text/css'
              : file.endsWith('.png')
                ? 'image/png'
                : 'text/html'
      );
      res.end(fs.readFileSync(file));
    });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const browser = await chromium.launch({
    headless: true,
    channel: process.env.BROWSER_CHANNEL || 'chrome'
  });
  try {
    for (const width of [1280, 1920])
      for (const edition of ['launcher', 'root-launcher']) {
        const context = await browser.newContext({
            viewport: { width, height: width === 1280 ? 720 : 1080 },
            locale: 'en-US'
          }),
          page = await context.newPage();
        page.setDefaultTimeout(10000);
        await context.route(/^https:\/\//, (r) => r.abort());
        let engineVersion = '1.5.1';
        await context.route('**/appinfo.json', (r) =>
          r.fulfill({ json: { version: engineVersion } })
        );
        await page.goto(
          'http://127.0.0.1:' +
            server.address().port +
            '/' +
            edition +
            '/index.html'
        );
        await page.locator('#tiles .focused').waitFor();
        const custom = await page.evaluate(async (input) => {
          const decode = (s) =>
              Uint8Array.from(atob(s), (c) => c.charCodeAt(0)),
            manifest = JSON.parse(ThemeData.decode(decode(input.descriptor)));
          manifest.id = manifest.id.replace(/:[^:]+$/, ':custom-offline');
          manifest.title = 'Private offline theme';
          const descriptor = ThemeData.encode(JSON.stringify(manifest)),
            pack = {
              descriptor,
              digest: ThemeData.hash(descriptor),
              files: {}
            };
          for (const name in input.files)
            pack.files[name] = decode(input.files[name]);
          await ThemeStore.put(pack, ThemeData.verify(pack, '1.5.1').size);
          window.previewRevoked = [];
          const revoke = URL.revokeObjectURL;
          URL.revokeObjectURL = function (url) {
            previewRevoked.push(url);
            revoke.call(URL, url);
          };
          return { id: manifest.id, digest: pack.digest };
        }, envelope);
        await page.evaluate(() => {
          window.listOriginal = ThemeManager.list;
          ThemeManager.list = function () {
            return window.listOriginal().then(
              (items) =>
                new Promise((resolve) => {
                  window.finishInitialThemeList = () => resolve(items);
                })
            );
          };
        });
        await page.locator('#btnSettings').click();
        await page.locator('[data-category=themes]').click();
        await page.waitForFunction(() => !!window.finishInitialThemeList);
        assert.equal(
          await page.evaluate(() =>
            document.activeElement.getAttribute('data-category')
          ),
          'themes',
          'initial load keeps category focus'
        );
        await page.keyboard.press('ArrowRight');
        assert.equal(
          await page
            .locator('#homeThemePanel')
            .evaluate((el) => el.contains(document.activeElement)),
          true,
          'user can enter loading controls'
        );
        await page.evaluate(() => {
          ThemeManager.list = window.listOriginal;
          window.finishInitialThemeList();
        });
        await page.locator('.theme-option').first().waitFor();
        assert.equal(
          await page
            .locator('.theme-option [aria-pressed="true"]')
            .evaluate((el) => el === document.activeElement),
          true,
          'loading control focus restores to selected card'
        );
        await page.locator('[data-category=language]').click();
        await page.evaluate(() => {
          window.finishInitialThemeList = null;
          ThemeManager.list = function () {
            return window.listOriginal().then(
              (items) =>
                new Promise((resolve) => {
                  window.finishInitialThemeList = () => resolve(items);
                })
            );
          };
        });
        await page.locator('[data-category=themes]').click();
        await page.waitForFunction(() => !!window.finishInitialThemeList);
        await page.evaluate(() => {
          ThemeManager.list = window.listOriginal;
          window.finishInitialThemeList();
        });
        await page.locator('.theme-option').first().waitFor();
        assert.equal(
          await page.evaluate(() =>
            document.activeElement.getAttribute('data-category')
          ),
          'themes',
          'resolved list does not steal untouched category focus'
        );
        assert.equal(
          await page.locator('#homeThemes').count(),
          0,
          'Appearance renders themes without a launch button'
        );
        await page
          .locator('#homeThemePanel.theme-inline .theme-option')
          .first()
          .waitFor();
        assert.equal(
          await page
            .locator('#homeThemePanel')
            .evaluate((el) =>
              document.getElementById('settings-pane-themes').contains(el)
            ),
          true,
          'theme cards are inside Themes'
        );
        const row = page
            .locator('.theme-option')
            .filter({ hasText: 'Private offline theme' }),
          image = row.locator('img');
        await image.waitFor();
        await page.waitForFunction((id) => {
          const image = document.querySelector(
            'button[data-theme-id="' + id + '"] img'
          );
          return image && image.complete && image.naturalWidth > 0;
        }, custom.id);
        assert(
          (await row.innerText()).includes(entry.manifest.themeVersion),
          'installed versions must be distinguishable in their cards'
        );
        const firstUrl = await image.getAttribute('src');
        assert.match(firstUrl, /^blob:/);
        const lane = await page
          .locator('.theme-installed-grid')
          .evaluate((el) => {
            const bounds = el.getBoundingClientRect();
            const rects = Array.from(el.children).map((x) =>
              x.getBoundingClientRect()
            );
            return {
              contained: rects.every(
                (r) => r.left >= bounds.left - 1 && r.right <= bounds.right + 1
              ),
              overflow: el.scrollWidth > el.clientWidth
            };
          });
        assert.equal(
          lane.contained,
          true,
          'installed cards fit the Themes pane'
        );
        assert.equal(
          lane.overflow,
          false,
          'installed themes need no horizontal scroll'
        );
        await row.locator('.theme-choice').focus();
        const visible = await row.locator('.theme-choice').evaluate((el) => {
          const box = el.getBoundingClientRect(),
            lane = el.closest('.theme-installed-grid').getBoundingClientRect();
          return {
            visible: box.left >= lane.left - 1 && box.right <= lane.right + 1,
            left: box.left,
            right: box.right,
            laneLeft: lane.left,
            laneRight: lane.right,
            active: el === document.activeElement,
            scrollLeft: el.closest('.theme-installed-grid').scrollLeft,
            scrollWidth: el.closest('.theme-installed-grid').scrollWidth
          };
        });
        assert.equal(
          visible.visible,
          true,
          'focused theme remains horizontally visible: ' +
            JSON.stringify(visible)
        );
        assert.equal(
          await row
            .getByRole('button', { name: 'Apply theme', exact: true })
            .count(),
          1
        );
        assert.equal(
          await row
            .getByRole('button', { name: 'Remove', exact: true })
            .count(),
          1
        );
        assert.equal(
          await page
            .locator('.theme-option')
            .filter({ hasText: 'Classic' })
            .getByRole('button', { name: 'Remove', exact: true })
            .count(),
          0
        );
        await row
          .getByRole('button', { name: 'Apply theme', exact: true })
          .click();
        await page.waitForFunction(
          (id) =>
            ThemeManager.current().id === id && !ThemeManager.current().trial,
          custom.id
        );
        assert.equal(
          await image.getAttribute('src'),
          firstUrl,
          'Apply retains the same cached preview URL'
        );
        assert.equal(
          await page.evaluate((url) => previewRevoked.includes(url), firstUrl),
          false,
          'Apply does not revoke the displayed preview'
        );
        const secondUrl = firstUrl;
        await page.locator('#themeCatalog').click();
        await page.waitForFunction(
          (url) => previewRevoked.includes(url),
          secondUrl
        );
        await page.locator('.theme-catalog-card').first().waitFor();
        assert.equal(
          await page
            .locator('.theme-catalog-card')
            .filter({ hasText: 'Private offline theme' })
            .count(),
          0
        );
        assert.equal(await page.locator('#themeCatalogRefresh').count(), 1);
        await page.evaluate(() => {
          const original = ThemeManager.preview;
          window.previewOriginal = original;
          ThemeManager.preview = function (item) {
            return original(item).then(
              (lease) =>
                new Promise((resolve) => {
                  window.pendingPreview = () => {
                    window.stalePreviewUrl = lease.url;
                    resolve(lease);
                  };
                })
            );
          };
        });
        await page
          .locator('#homeThemePanel')
          .getByRole('button', { name: 'Back', exact: true })
          .click();
        await page.waitForFunction(() => !!window.pendingPreview);
        const beforeLatePreview = await row.boundingBox();
        await row
          .getByRole('button', { name: 'Apply theme', exact: true })
          .click();
        await page.waitForFunction(
          () =>
            document
              .querySelector('.theme-settings-card')
              .getAttribute('aria-busy') === 'false'
        );
        await page.evaluate(() => pendingPreview());
        await image.waitFor();
        const afterLatePreview = await row.boundingBox();
        assert(
          Math.abs(afterLatePreview.height - beforeLatePreview.height) < 1,
          'late preview cannot resize the retained card'
        );
        assert.equal(
          await page.evaluate(() => previewRevoked.includes(stalePreviewUrl)),
          false,
          'late preview survives Apply when its original card is retained'
        );
        // Cancelling an in-flight installed Apply retains a live preview lease.
        await page.evaluate(() => {
          window.prepareOriginal = ThemeData.prepare;
          ThemeData.prepare = function () {
            const args = arguments;
            if (window.finishCancelledApply)
              return prepareOriginal.apply(ThemeData, args);
            return new Promise(
              (resolve) =>
                (window.finishCancelledApply = () =>
                  resolve(prepareOriginal.apply(ThemeData, args)))
            );
          };
        });
        await row
          .getByRole('button', { name: 'Apply theme', exact: true })
          .click();
        await page.waitForFunction(() => !!window.finishCancelledApply);
        await page.keyboard.press('Escape');
        await page.evaluate(() => {
          finishCancelledApply();
          ThemeData.prepare = prepareOriginal;
        });
        await page.waitForTimeout(100);
        assert.equal(
          await page.evaluate(() => previewRevoked.includes(stalePreviewUrl)),
          false,
          'Back from installed Apply retains the visible preview lease'
        );
        await page.locator('#themeCatalog').click();
        await page.evaluate(() => (window.pendingPreview = null));
        await page
          .locator('#homeThemePanel')
          .getByRole('button', { name: 'Back', exact: true })
          .click();
        await page.waitForFunction(() => !!window.pendingPreview);
        await page.locator('#themeCatalog').click();
        await page.evaluate(() => pendingPreview());
        await page.waitForFunction(() =>
          previewRevoked.includes(stalePreviewUrl)
        );
        await page.evaluate(
          () => (ThemeManager.preview = window.previewOriginal)
        );
        await page
          .locator('#homeThemePanel')
          .getByRole('button', { name: 'Back', exact: true })
          .click();
        await image.waitFor();
        const leavingUrl = await image.getAttribute('src');
        await page.locator('[data-category=language]').click();
        await page.waitForFunction(
          (url) => previewRevoked.includes(url),
          leavingUrl
        );
        assert.equal(
          await page.locator('#homeThemePanel').evaluate((el) => el.hidden),
          true,
          'leaving Appearance releases inline content'
        );
        await page.locator('[data-category=themes]').click();
        await image.waitFor();
        const closingUrl = await image.getAttribute('src');
        await page
          .getByRole('button', { name: 'Back to Home', exact: true })
          .click();
        await page.waitForFunction(
          (url) => previewRevoked.includes(url),
          closingUrl
        );
        assert.equal(
          await page.evaluate(() => ThemeManager.current().id),
          custom.id,
          'closing settings preserves installed selection'
        );
        if (width === 1280)
          await exerciseRollback(page, () => (engineVersion = '1.4.0'));
        await context.close();
        console.log(
          'PASS arbitrary cached theme preview offline, Apply/Remove and separate showcase: ' +
            edition
        );
      }
  } finally {
    await browser.close();
    await new Promise((r) => server.close(r));
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
