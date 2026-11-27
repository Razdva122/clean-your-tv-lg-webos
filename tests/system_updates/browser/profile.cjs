// Exercise webOS Home's two real IndexedDB stores after destroying its browser origin.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { execFileSync } = require('node:child_process');
const { chromium } = require('playwright');
const root = path.resolve(__dirname, '../../..');
const sample = require('../../../scripts/check-theme-submissions.cjs')
  .loadRegistry()
  .find((e) => e.record.title === 'Channel');
function file(name) {
  return fs.readFileSync(path.join(root, 'showcase', sample.base, name));
}
const theme = {
  digest: sample.record.descriptorSha256,
  descriptor: file('cytv-theme.json').toString('base64'),
  files: {}
};
for (const f of sample.files.filter((f) => f !== 'cytv-theme.json'))
  theme.files[f] = file(f).toString('base64');
const image = fs.readFileSync(
  path.join(root, 'assets/icons/installer-256.png')
);
const poster = {
  mediaType: 'image/png',
  width: image.readUInt32BE(16),
  height: image.readUInt32BE(20),
  size: image.length,
  sha256: crypto.createHash('sha256').update(image).digest('hex'),
  data: image.toString('base64')
};
const ref = 'media:' + poster.sha256 + ':';
const browserState = {
  schema: 1,
  local: {
    'tvhome.name': 'Living room',
    'tvhome.columns.v1': '{"version":1,"columns":6}',
    'tvhome.usage.v1': '{"enabled":true}',
    'tvhome.theme.choice.v1': JSON.stringify({
      id: sample.manifest.id,
      title: 'Channel',
      digest: theme.digest
    }),
    'tvhome.language': 'de'
  },
  themes: [theme],
  wallpapers: [
    { key: 'library:photo', value: ref },
    {
      key: ref,
      value: {
        schemaVersion: 1,
        kind: 'wallpaper',
        source: 'phone',
        mediaKind: 'photo',
        image: poster,
        variants: []
      }
    },
    { key: 'slot', value: { source: 'personal', mediaRef: ref } }
  ]
};
const profile = {
  schema: 1,
  inventory: {
    apps: [{ id: 'one', title: 'One', icon: 'data:image/png;base64,YQ==' }],
    inputs: []
  },
  config: { columns: 5, dockApps: [], hiddenApps: [] },
  settings: { 'tvhome.language': 'de' }
};
const scripts = [
  'theme-policy',
  'theme-data',
  'theme-store',
  'wallpaper-library',
  'personal-wallpaper',
  'browser-profile',
  'app-library',
  'user-data',
  'root-profile-data'
];
const origin = 'https://profile.test';
(async () => {
  const browser = await chromium.launch({
    headless: true,
    channel: process.env.BROWSER_CHANNEL || 'chrome'
  });
  try {
    for (const edition of ['root', 'no-root']) {
      const context = await browser.newContext();
      let boot = false,
        receipt = null,
        transitions = [],
        snapshot;
      await context.exposeBinding('readSystem', (_, method, payload) => {
        transitions.push(method);
        if (method === 'healthy') {
          receipt = payload;
          return null;
        }
        assert.equal(method, 'restoreProfile');
        return {
          transaction: 'a'.repeat(32),
          version: '1.5.1',
          phase: 'verifying',
          profile: { ...profile, browserState: snapshot }
        };
      });
      await context.route(origin + '/**', (r) => {
        const name = new URL(r.request().url()).pathname.slice(1);
        if (name === 'appinfo.json')
          return r.fulfill({
            json: {
              id:
                edition === 'root'
                  ? 'com.cleanyourtv.root.preview'
                  : 'com.gathin.tvhome',
              version: '1.5.1'
            }
          });
        if (name === 'app.js')
          return r.fulfill({
            contentType: 'text/javascript',
            body: 'window.RootLauncherRendered=true;'
          });
        if (name === 'index.html')
          return r.fulfill({
            contentType: 'text/html',
            body:
              '<div id="tiles"><div class="item" data-app-id="one"></div></div>' +
              scripts
                .map((s) => '<script src="' + s + '.js"></script>')
                .join('') +
              (boot
                ? '<script src="' +
                  (edition === 'root' ? 'root-profile' : 'profile-bootstrap') +
                  '.js"></script>'
                : '')
          });
        const dir = name.startsWith('root-profile')
          ? 'root-edition/ui'
          : 'launcher';
        return r.fulfill({
          path: path.join(root, dir, name),
          contentType: 'text/javascript'
        });
      });
      await context.addInitScript(() => {
        window.CYTVProductGeneration = 2;
        window.ROOT_VERSION = '1.5.1';
        window.TV_APPS = { apps: [], inputs: [] };
        window.CONFIG = { columns: 5, dockApps: [], hiddenApps: [] };
        window.SystemUpdates = {
          rpc: (m, p) => window.readSystem(m, p),
          open: (o) => {
            window.failure = o.error;
          }
        };
        window.RootUpdates = {
          open: (o) => {
            window.failure = o.error;
          }
        };
      });
      let page = await context.newPage();
      await page.goto(origin + '/index.html');
      await page.evaluate(async (state) => {
        localStorage.setItem('foreign.key', 'private');
        await HomeBrowserProfile.restore(state);
      }, browserState);
      snapshot = await page.evaluate(() => HomeBrowserProfile.capture());
      assert.deepEqual(snapshot, browserState);
      // The worker authenticates and stores the actual JSON received over the app bridge.
      const temp = fs.mkdtempSync(
        path.join(require('node:os').tmpdir(), 'cytv-browser-profile-')
      );
      try {
        const fixture = path.join(temp, 'profile.json');
        fs.writeFileSync(
          fixture,
          JSON.stringify({ ...profile, browserState: snapshot }),
          { mode: 0o600 }
        );
        execFileSync(
          process.env.PYTHON || 'python3',
          [
            '-c',
            [
              'import json, runpy, sys',
              'from pathlib import Path',
              "runpy.run_path('tests/system_updates/test_core.py')",
              'from system_updater.core import validate_profile',
              'path=Path(sys.argv[2]); src=json.loads(path.read_text())',
              'path.write_text(json.dumps(validate_profile(src,sys.argv[1],captured=True)))'
            ].join('\n'),
            edition,
            fixture
          ],
          { cwd: root, timeout: 10000 }
        );
        snapshot = JSON.parse(fs.readFileSync(fixture, 'utf8')).browserState;
      } finally {
        fs.rmSync(temp, { recursive: true, force: true });
      }

      const mediaError = await page.evaluate(async (state) => {
        await PersonalWallpaper.replaceProfileRecords([
          {
            key: 'slot',
            value: {
              source: 'personal',
              envelope: { image: { data: 'a'.repeat(3 * 1024 * 1024) } }
            }
          }
        ]);
        try {
          await HomeBrowserProfile.capture();
        } catch (error) {
          return error.message;
        } finally {
          await PersonalWallpaper.replaceProfileRecords(state.wallpapers);
        }
      }, snapshot);
      assert.match(mediaError, /backup is too large/);
      const trial = await page.evaluate(async () => {
        localStorage.setItem('tvhome.theme.trial.v1', 'active');
        try {
          await HomeBrowserProfile.capture();
        } catch (e) {
          return e.message;
        } finally {
          localStorage.removeItem('tvhome.theme.trial.v1');
        }
      });
      assert.equal(
        trial,
        'Finish or cancel your theme preview before updating.'
      );
      await page.evaluate(() =>
        localStorage.setItem('tvhome.name', 'x'.repeat(65537))
      );
      assert.equal(
        await page.evaluate(() =>
          Promise.resolve()
            .then(() => HomeBrowserProfile.capture())
            .then(
              () => false,
              () => true
            )
        ),
        true
      );
      await page.close();
      page = await context.newPage();
      const cdp = await context.newCDPSession(page);
      await cdp.send('Storage.clearDataForOrigin', {
        origin,
        storageTypes: 'all'
      });
      await page.goto(origin + '/index.html');
      assert.deepEqual(
        await page.evaluate(() => HomeBrowserProfile.capture()),
        { schema: 1, local: {}, themes: [], wallpapers: [] }
      );
      boot = true;
      await page.reload();
      await page.waitForFunction(
        () => window.RootLauncherRendered || window.failure
      );
      assert.equal(await page.evaluate(() => window.failure), undefined);
      await page.waitForFunction(
        () =>
          typeof window.RootLauncherRendered === 'boolean' &&
          window.RootLauncherRendered
      );
      assert.equal(receipt?.edition, edition);
      assert.equal(receipt.version, '1.5.1');
      assert.equal(transitions.at(-1), 'healthy');
      assert.equal(transitions.filter((m) => m === 'restoreProfile').length, 2);
      assert.deepEqual(
        await page.evaluate(() => HomeBrowserProfile.capture()),
        snapshot
      );
      assert.equal(
        await page.evaluate(() => localStorage.getItem('foreign.key')),
        null
      );
      // An authenticated profile which no longer matches the durable readback cannot report health.
      receipt = null;
      await page.evaluate(() => localStorage.setItem('tvhome.name', 'partial'));
      await page.reload();
      await page.waitForFunction(() => window.failure);
      assert.equal(receipt, null);
      assert.equal(
        await page.evaluate(() => window.RootLauncherRendered === true),
        false
      );
      await context.close();
    }
    console.log(
      'PASS cleared Home origin: both editions restore local preferences, installed theme and personal wallpaper before exact health'
    );
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
