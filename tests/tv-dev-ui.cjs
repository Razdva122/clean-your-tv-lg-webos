// Compiled development UI smoke. Uses only a loopback HTTP server, never a TV.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const os = require('node:os');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = path.resolve(__dirname, '..');

(async () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'cytv-dev-browser-'));
  const output = path.join(temporary, 'ui');
  let server, browser;
  try {
    execFileSync(process.env.PYTHON || 'python3', ['scripts/tv-dev.py', 'ui', '--stage-only', '--output', output], {cwd: root, stdio: 'pipe'});
    server = http.createServer((request, response) => {
      if (request.url === '/seed') { response.end('<!doctype html><title>Seed</title>'); return; }
      const name = path.resolve(output, '.' + new URL(request.url, 'http://localhost').pathname);
      if (!name.startsWith(output + path.sep)) { response.writeHead(403).end(); return; }
      const types = {'.js':'text/javascript', '.css':'text/css', '.json':'application/json', '.html':'text/html', '.svg':'image/svg+xml', '.ttf':'font/ttf'};
      try { response.setHeader('Content-Type', types[path.extname(name)] || 'application/octet-stream'); response.end(fs.readFileSync(name)); }
      catch (_) { response.writeHead(404).end(); }
    });
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    const origin = 'http://127.0.0.1:' + server.address().port;
    browser = await chromium.launch({headless: true, channel: process.env.BROWSER_CHANNEL || 'chromium'});
    const page = await browser.newPage({viewport:{width:1920,height:1080}, locale:'en'});
    await page.goto(origin + '/seed');
    await page.evaluate(async () => {
      localStorage.setItem('tvhome.language', 'production-sentinel');
      await new Promise((resolve, reject) => {
        const request = indexedDB.open('ctv-themes-v1', 1);
        request.onupgradeneeded = () => request.result.createObjectStore('production-sentinel');
        request.onsuccess = () => { request.result.close(); resolve(); };
        request.onerror = () => reject(request.error);
      });
    });
    await page.addInitScript(() => {
      window.nativeCalls = 0;
      window.PalmServiceBridge = function () { window.nativeCalls++; this.call = () => window.nativeCalls++; };
      window.webOS = {service:{request:() => window.nativeCalls++}};
    });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', entry => { if (entry.text().includes('Content Security Policy')) errors.push(entry.text()); });
    await page.goto(origin + '/index.html');
    await page.waitForFunction(() => window.RootLauncherRendered === true);
    const result = await page.evaluate(async () => {
      const themes = await ThemeManager.list();
      await ThemeManager.selectInstalled({id:'builtin:alpine',title:'Alpine'});
      const cached = await ThemeStore.list();
      const background = getComputedStyle(document.getElementById('homeSurface')).backgroundImage;
      const match = /url\("?(blob:[^")]+)"?\)/.exec(background);
      if (!match) throw Error('Alpine wallpaper blob missing');
      await new Promise((resolve, reject) => { const image=new Image(); image.onload=resolve; image.onerror=()=>reject(Error('Alpine wallpaper did not decode')); image.src=match[1]; });
      const databases = await indexedDB.databases();
      return {themes:themes.map(item => item.id), current:ThemeManager.current(), cached:cached.length,
        databases:databases.map(item => item.name), nativeCalls:window.nativeCalls,
        production:localStorage.getItem('tvhome.language'), tiles:document.querySelectorAll('#tiles .item').length};
    });
    assert(result.themes.includes('builtin:alpine'));
    assert.equal(result.current.id, 'builtin:alpine');
    assert(result.databases.includes('cytv.dev.ui.ctv-themes-v1'));
    assert(result.databases.includes('ctv-themes-v1'));
    assert.equal(result.nativeCalls, 0);
    assert.equal(result.production, 'production-sentinel');
    assert(result.tiles > 0);
    assert.deepEqual(errors, []);
    await page.close();
    // Real browser fixture for readonly native APIs: the app must remain inert.
    const blocked = await browser.newPage();
    await blocked.addInitScript(() => Object.defineProperty(window, 'PalmServiceBridge', {
      value:function () { throw Error('Native service reached'); }, writable:false, configurable:false
    }));
    await blocked.goto(origin + '/index.html');
    assert.equal(await blocked.evaluate(() => typeof window.RootProfile), 'undefined');
    assert.equal(await blocked.locator('#tiles .item').count(), 0);
    await blocked.close();
    console.log('Compiled development UI: rendered tiles, applied Alpine, isolated localStorage/IndexedDB, blocked native APIs and readonly-native startup.');
  } finally {
    if (browser) await browser.close();
    if (server) await new Promise(resolve => server.close(resolve));
    fs.rmSync(temporary, {recursive:true, force:true});
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
