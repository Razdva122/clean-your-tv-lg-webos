// Real browser IndexedDB with only native image load delivery deferred, exposing user/restore ordering.
const { chromium, fs, path } = require('./browser.cjs'),
  assert = require('assert/strict'),
  http = require('http');
(async () => {
  const site = path.resolve('build/tests/personal-restore-site');
  require('child_process').execFileSync(process.env.PYTHON || 'python3', [
    'scripts/preview.py',
    '--build',
    site
  ]);
  const server = http.createServer((req, res) => {
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
        '.html': 'text/html',
        '.css': 'text/css',
        '.json': 'application/json'
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
      const page = await browser.newPage({ locale: 'en-US' });
      await page.route(/^https:/, (route) => route.abort());
      await page.goto(
        'http://127.0.0.1:' +
          server.address().port +
          '/' +
          edition +
          '/index.html'
      );
      await page.waitForFunction(() => !!window.HomeUIReady);
      await page.evaluate(() => HomeUIReady);
      const wire = await page.evaluate(async () => {
        const canvas = document.createElement('canvas');
        canvas.width = 320;
        canvas.height = 180;
        canvas.getContext('2d').fillRect(0, 0, 320, 180);
        const data = canvas.toDataURL('image/jpeg').split(',')[1],
          bytes = Uint8Array.from(atob(data), (x) => x.charCodeAt(0)),
          envelope = {
            schemaVersion: 1,
            kind: 'wallpaper',
            source: 'phone',
            image: {
              mediaType: 'image/jpeg',
              width: 320,
              height: 180,
              size: bytes.length,
              sha256: ThemeData.hash(bytes),
              data
            },
            variants: []
          };
        await PersonalWallpaper.receive(envelope);
        await PersonalWallpaper.apply();
        return envelope;
      });
      await page.addInitScript(() => {
        const NativeImage = window.Image;
        window.Image = function () {
          if (window.skipRestoreGate) return new NativeImage();
          const image = new NativeImage();
          let handler;
          Object.defineProperty(image, 'onload', {
            get: () => handler,
            set: (value) => {
              handler = value;
            }
          });
          image.addEventListener('load', () => {
            if (!window.releaseRestore) {
              window.releaseRestore = () => {
                if (handler) handler.call(image);
              };
            } else if (handler) handler.call(image);
          });
          return image;
        };
      });
      await page.reload();
      await page.waitForFunction(() => typeof releaseRestore === 'function');
      await page.evaluate(() => {
        window.choiceSettled = false;
        window.choice = PersonalWallpaper.select('theme').then(() => {
          window.choiceSettled = true;
        });
      });
      // A real transaction barrier settles any prior source write without releasing image decode.
      await page.evaluate(async () => {
        const db = await new Promise((resolve, reject) => {
          const r = indexedDB.open('ctv-personal-wallpaper-v1', 1);
          r.onsuccess = () => resolve(r.result);
          r.onerror = reject;
        });
        await new Promise((resolve, reject) => {
          const tx = db.transaction('wallpaper', 'readwrite');
          tx.oncomplete = resolve;
          tx.onabort = reject;
          tx.objectStore('wallpaper').get('slot');
        });
        db.close();
      });
      assert.equal(
        await page.evaluate(() => choiceSettled),
        false,
        'source selection waits for saved wallpaper restoration'
      );
      await page.evaluate(async () => {
        releaseRestore();
        await choice;
        await HomeUIReady;
      });
      assert.equal(
        await page.evaluate(() => PersonalWallpaper.state().source),
        'theme'
      );
      assert.equal(
        await page.evaluate(() => PersonalWallpaper.state().installed),
        true
      );
      await page.reload();
      await page.waitForFunction(() => typeof releaseRestore === 'function');
      await page.evaluate(async () => {
        releaseRestore();
        await HomeUIReady;
      });
      assert.equal(
        await page.evaluate(() => PersonalWallpaper.state().source),
        'theme',
        'source choice persists'
      );
      await page.reload();
      await page.waitForFunction(() => typeof releaseRestore === 'function');
      await page.evaluate(async () => {
        try {
          await PersonalWallpaper.receive({});
        } catch (_) {}
        releaseRestore();
        await HomeUIReady;
      });
      assert.equal(
        await page.evaluate(() => PersonalWallpaper.state().installed),
        true,
        'rejected replacement during restore preserves installed wallpaper'
      );
      await page.reload();
      await page.waitForFunction(() => typeof releaseRestore === 'function');
      await page.evaluate(async () => {
        const removed = PersonalWallpaper.remove();
        releaseRestore();
        await Promise.all([removed, HomeUIReady]);
      });
      assert.equal(
        await page.evaluate(() => PersonalWallpaper.state().installed),
        false,
        'remove during restore cannot resurrect'
      );
      assert.equal(
        await page.evaluate(() => PersonalWallpaper.state().error),
        ''
      );
      await page.evaluate(async (envelope) => {
        await PersonalWallpaper.receive(envelope);
        await PersonalWallpaper.apply();
      }, wire);
      await page.reload();
      await page.waitForFunction(() => typeof releaseRestore === 'function');
      await page.evaluate(async (envelope) => {
        const receiving = PersonalWallpaper.receive(envelope);
        releaseRestore();
        await receiving;
        await PersonalWallpaper.apply();
        await HomeUIReady;
      }, wire);
      assert.equal(
        await page.evaluate(() => PersonalWallpaper.state().source),
        'personal',
        'replacement during restore wins'
      );
      assert.equal(
        await page.evaluate(() => PersonalWallpaper.state().error),
        ''
      );
      async function corruptSlot() {
        await page.evaluate(async () => {
          const db = await new Promise((resolve, reject) => {
            const r = indexedDB.open('ctv-personal-wallpaper-v1', 1);
            r.onsuccess = () => resolve(r.result);
            r.onerror = reject;
          });
          await new Promise((resolve, reject) => {
            const tx = db.transaction('wallpaper', 'readwrite');
            tx.oncomplete = resolve;
            tx.onabort = reject;
            tx.objectStore('wallpaper').put(
              { source: 'personal', envelope: {} },
              'slot'
            );
          });
          db.close();
        });
        await page.reload();
        await page.waitForFunction(() => !!window.HomeUIReady);
        await page.evaluate(() => HomeUIReady);
        assert(
          await page.evaluate(() => !!PersonalWallpaper.state().error),
          'corrupt slot reports restore error'
        );
        await page.locator('#btnSettings').click();
        await page.locator('[data-category=wallpapers]').click();
      }
      await corruptSlot();
      await page.evaluate(async (envelope) => {
        window.skipRestoreGate = true;
        await PersonalWallpaper.receive(envelope);
        await PersonalWallpaper.apply();
      }, wire);
      assert.equal(
        await page.evaluate(() => PersonalWallpaper.state().error),
        '',
        'successful replacement clears restore error'
      );
      assert.equal(
        await page.locator('#wallpaperStatus').textContent(),
        '',
        'recovery removes visible error'
      );
      await corruptSlot();
      await page.evaluate(() => PersonalWallpaper.remove());
      assert.equal(
        await page.evaluate(() => PersonalWallpaper.state().error),
        '',
        'successful removal clears restore error'
      );
      assert.equal(
        await page.locator('#wallpaperStatus').textContent(),
        '',
        'removal removes visible error'
      );
      await page.close();
    }
    console.log(
      'PASS deferred native-image restore ordered with source/remove/replacement in both editions'
    );
  } finally {
    await browser.close();
    await new Promise((resolve) => server.close(resolve));
  }
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
