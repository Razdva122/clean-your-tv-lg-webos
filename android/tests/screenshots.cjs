const { chromium } = require('playwright');
const path = require('node:path');
const fs = require('node:fs');
(async () => {
  const out = path.resolve(__dirname, '../screenshots');
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({
    headless: true,
    executablePath:
      process.env.CYTV_CHROME ||
      '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
  });
  const page = await browser.newPage({
    locale: 'ru-RU',
    viewport: { width: 412, height: 892 },
    deviceScaleFactor: 2
  });
  for (const [name, mode] of [
    ['01-welcome', 'welcome'],
    ['02-edition', 'editions'],
    ['02-no-root', 'connect'],
    ['03-root', 'root'],
    ['04-installation', 'progress'],
    ['05-complete', 'success']
  ]) {
    await page.goto(
      'file://' +
        path.resolve(__dirname, '../app/src/main/assets/ui/index.html') +
        '?preview=' +
        mode
    );
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({
      path: path.join(out, name + '.png'),
      fullPage: true
    });
  }
  await browser.close();
  console.log('Saved 5 UI preview screenshots in ' + out);
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
