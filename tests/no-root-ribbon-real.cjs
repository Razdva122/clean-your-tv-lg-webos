// Actual shared Home/Ribbon UI in a developer app, with native services blocked.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const {chromium} = require('playwright');

(async () => {
  const root = path.resolve('build/no-root-ribbon-prototype/real');
  assert.ok(fs.existsSync(path.join(root, 'index.html')), 'Build --real-ribbon before testing');
  const server = http.createServer((req, res) => {
    const file = path.resolve(root, '.' + new URL(req.url, 'http://localhost').pathname);
    if (!file.startsWith(root + path.sep)) return res.writeHead(403).end();
    const types = {'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json','.png':'image/png','.jpg':'image/jpeg','.svg':'image/svg+xml','.ttf':'font/ttf'};
    try { res.setHeader('Content-Type', types[path.extname(file)] || 'application/octet-stream'); res.end(fs.readFileSync(file)); }
    catch (_) { res.writeHead(404).end(); }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  let browser;
  try {
    browser = await chromium.launch({headless:true, channel:process.env.BROWSER_CHANNEL || 'chrome'});
    const page = await browser.newPage({viewport:{width:1920,height:1080},locale:'en-US'});
    await page.clock.install();
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.addInitScript(() => {
      window.nativeCalls = 0; window.labClosed = 0; window.labActivated = 0;
      window.PalmServiceBridge = function () { window.nativeCalls++; this.call = () => window.nativeCalls++; };
      window.PalmSystem = {launchParams:'{"mode":"overlay"}',activate:() => window.labActivated++};
      window.close = () => window.labClosed++;
    });
    const origin = 'http://127.0.0.1:' + server.address().port;
    await page.goto(origin + '/index.html');
    await page.waitForFunction(() => window.RootLauncherRendered === true && ThemeManager.current().id === 'builtin:ribbon' && HomePresentationController.state().mode === 'overlay' && window.labActivated === 1);
    assert.ok(await page.locator('#tiles .item').count() >= 8, 'Uses actual app cards, not the three-button probe');
    assert.equal(await page.locator('#homeSurface').getAttribute('data-ribbon'), 'true');
    assert.equal(await page.evaluate(() => nativeCalls), 0, 'Product actions never reach native services');
    assert.equal(await page.evaluate(() => labActivated), 1, 'Only the isolated host activates its window');
    assert.equal(await page.locator('#previewContent').count(), 0, 'No synthetic content covers actual underlying video');
    assert.equal(await page.locator('video').count(), 0, 'No wallpaper decoder is acquired');
    await page.screenshot({path:'build/no-root-ribbon-prototype/real-browser.png'});
    const selected = await page.locator('#tiles .focused').getAttribute('data-app-id');
    await page.keyboard.press('ArrowRight');
    assert.notEqual(await page.locator('#tiles .focused').getAttribute('data-app-id'), selected);
    await page.locator('#btnSettings').click();
    await page.waitForFunction(() => HomePresentationController.state().mode === 'full');
    assert.equal(await page.evaluate(() => labClosed), 0);
    await page.keyboard.press('Escape');
    await page.waitForFunction(() => HomePresentationController.state().mode === 'overlay');
    await page.keyboard.press('Escape');
    assert.equal(await page.evaluate(() => labClosed), 1);
    await page.reload();
    await page.waitForFunction(() => window.RootLauncherRendered === true && HomePresentationController.state().mode === 'overlay');
    await page.evaluate(() => document.dispatchEvent(new Event('webOSRelaunch')));
    assert.equal(await page.evaluate(() => labClosed), 1);
    await page.reload();
    await page.waitForFunction(() => window.RootLauncherRendered === true && HomePresentationController.state().mode === 'overlay');
    await page.clock.fastForward(60000);
    assert.equal(await page.evaluate(() => labClosed), 1, 'The real host also has an absolute lifetime');
    assert.deepEqual(errors, []);
    await page.close();
    console.log('PASS real Ribbon: renderer, navigation, opaque settings, Back/relaunch, service isolation, no wallpaper video');
  } finally { if (browser) await browser.close(); await new Promise(resolve => server.close(resolve)); }
})().catch(e => { console.error(e); process.exitCode = 1; });
