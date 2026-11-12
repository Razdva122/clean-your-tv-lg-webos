// Record the bundled browser renderer with its public demo inventory, never a TV.
// Run after prepare.mjs, with the website dev server running. Pillow assembles WebP.
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { mkdirSync, mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { resolve, join } from 'node:path';
import { execFileSync } from 'node:child_process';
const require = createRequire(new URL('../../package.json', import.meta.url));
const { chromium } = require('playwright');
const destination = resolve('website/assets/previews');
const frames = mkdtempSync(join(tmpdir(), 'cytv-preview-'));
mkdirSync(destination, { recursive: true });
const browser = await chromium.launch({ headless: true, channel: 'chrome' });
try {
  for (const theme of ['classic', 'liquid-glass', 'ribbon']) {
    const page = await browser.newPage({
      locale: 'en-US',
      viewport: { width: 1920, height: 1080 },
      deviceScaleFactor: 1
    });
    await page.goto(
      (process.env.PREVIEW_ORIGIN || 'http://127.0.0.1:4322') +
        '/clean-your-tv-lg-webos/demo/root-launcher/index.html'
    );
    await page.waitForFunction(
      () => window.RootLauncherRendered && window.ThemeManager
    );
    await page.evaluate(async (id) => {
      await window.ThemeManager.selectInstalled(
        (await window.ThemeManager.list()).find((t) => t.id === 'builtin:' + id)
      );
      document.dispatchEvent(new Event('webOSRelaunch'));
    }, theme);
    await page.waitForTimeout(900);
    assert.equal(
      await page.locator('html').getAttribute('lang'),
      'en',
      `Expected English launcher UI for ${theme}`
    );
    await page.evaluate(() => document.fonts.ready);
    const dir = join(frames, theme);
    mkdirSync(dir);
    await page.screenshot({ path: join(dir, '00.png') });
    for (let i = 1; i <= 15; i++) {
      if (i === 1 || i === 6 || i === 11) {
        await page.evaluate(() => {
          for (const type of ['keydown', 'keyup'])
            document.dispatchEvent(
              new KeyboardEvent(type, {
                key: 'ArrowRight',
                keyCode: 39,
                which: 39,
                bubbles: true
              })
            );
        });
      }
      await page.waitForTimeout(90);
      await page.screenshot({
        path: join(dir, String(i).padStart(2, '0') + '.png')
      });
    }
    execFileSync(
      process.env.PYTHON || '.venv-cytv/bin/python',
      [
        '-c',
        `
from PIL import Image
from pathlib import Path
import sys
source, target, theme = map(Path, sys.argv[1:])
frames = [Image.open(p).convert('RGB').resize((960, 540), Image.Resampling.LANCZOS) for p in sorted(source.glob('*.png'))]
frames[0].save(target / (str(theme) + '-still.webp'), quality=85)
frames[0].save(target / (str(theme) + '.webp'), save_all=True, append_images=frames[1:], duration=[1000] + [100] * 4 + [750] + [100] * 4 + [750] + [100] * 4 + [1000], loop=0, quality=72, method=6)
small = [frame.resize((480, 270), Image.Resampling.LANCZOS) for frame in frames]
small[0].save(target / (str(theme) + '-still-small.webp'), quality=85)
small[0].save(target / (str(theme) + '-small.webp'), save_all=True, append_images=small[1:], duration=[1000] + [100] * 4 + [750] + [100] * 4 + [750] + [100] * 4 + [1000], loop=0, quality=72, method=6)
`,
        dir,
        destination,
        theme
      ],
      { cwd: resolve('.') }
    );
    console.log('Recorded', theme);
    await page.close();
  }
} finally {
  await browser.close();
  rmSync(frames, { recursive: true, force: true });
}
