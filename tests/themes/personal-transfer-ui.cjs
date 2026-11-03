'use strict';
// Actual HTTP receipt -> chunked TV read -> native browser decode -> Apply/reload.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const crypto = require('node:crypto');
const os = require('node:os');
const {execFileSync} = require('node:child_process');
const {chromium} = require('playwright');
const receiverCore = require('../../theme-receiver/core');
const register = require('../../theme-receiver/register');

function listen(server) {
  return new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
}
function send(session, body) {
  return new Promise((resolve, reject) => {
    const request = http.request({host: '127.0.0.1', port: session.port,
      path: '/v1/wallpaper', method: 'POST', headers: {
        Host: '127.0.0.1:' + session.port, 'X-CYTV-PIN': session.pin,
        'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body)
      }}, response => {
        response.resume(); response.on('end', () => resolve(response.statusCode));
      });
    request.on('error', reject); request.end(body);
  });
}

(async () => {
  const site = path.resolve('build/tests/personal-transfer-site');
  execFileSync('python3', ['scripts/preview.py', '--build', site], {stdio: 'pipe'});
  const server = http.createServer((request, response) => {
    const file = path.resolve(site, '.' + new URL(request.url, 'http://localhost').pathname);
    if (!file.startsWith(site + path.sep) || !fs.existsSync(file)) return response.writeHead(404).end();
    response.setHeader('Content-Type', ({'.js': 'application/javascript', '.css': 'text/css',
      '.html': 'text/html', '.json': 'application/json'})[path.extname(file)] || 'application/octet-stream');
    response.end(fs.readFileSync(file));
  });
  await listen(server);
  const browser = await chromium.launch({headless: true, channel: process.env.BROWSER_CHANNEL || 'chrome'});
  const clip = fs.readFileSync('tests/themes/fixtures/wallpaper-blue.mp4');
  const variant = {quality: '1080p', mediaType: 'video/mp4', width: 1920, height: 1080,
    size: clip.length, sha256: crypto.createHash('sha256').update(clip).digest('hex'), data: clip.toString('base64')};
  try {
    for (const edition of ['launcher', 'root-launcher']) {
      const context = await browser.newContext({viewport: {width: 1920, height: 1080}, locale: 'en-US'});
      const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'personal-transfer-'));
      const methods = {}, sessions = new Set();
      register({register(name, handler) { methods[name] = handler; }}, {appId: 'personal.test', directory});
      function rpc(method, payload) {
        return new Promise(resolve => methods[method]({payload, ls2Message: {applicationID: () => 'personal.test'}, respond(reply) {
          if (method === 'wallpaperCacheStart' && reply.sessionId) sessions.add(reply.sessionId);
          if (method === 'wallpaperCacheStop') sessions.delete(payload.sessionId);
          resolve(reply);
        }}));
      }
      await context.exposeFunction('__personalCacheRPC', rpc);
      // Keep other preview services mocked; only the media lease uses the real service closure.
      await context.route('**/preview/bridge.js', route => route.fulfill({contentType: 'application/javascript',
        body: fs.readFileSync(path.join(site, 'preview/bridge.js'), 'utf8') + `
          (function(){var original=PalmServiceBridge.prototype.call;
            PalmServiceBridge.prototype.call=function(uri,raw){var bridge=this;
              if(uri.indexOf('/wallpaperCache')>=0){window.__personalCacheRPC(uri.split('/').pop(),JSON.parse(raw)).then(function(reply){if(bridge.onservicecallback)bridge.onservicecallback(JSON.stringify(reply));});return;}
              return original.call(this,uri,raw);
            };
          }());`
      }));
      await context.route(/^https:/, route => route.abort());
      const page = await context.newPage(), errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.goto('http://127.0.0.1:' + server.address().port + '/' + edition + '/index.html');
      await page.locator('#tiles .focused').waitFor();
      await page.evaluate(() => HomeUIReady);
      const envelope = await page.evaluate(variant => {
        const canvas = document.createElement('canvas'); canvas.width = 1920; canvas.height = 1080;
        canvas.getContext('2d').fillRect(0, 0, canvas.width, canvas.height);
        const data = canvas.toDataURL('image/jpeg').split(',')[1], raw = atob(data);
        const bytes = Uint8Array.from(raw, character => character.charCodeAt(0));
        return {schemaVersion: 1, kind: 'wallpaper', source: 'cytv',
          image: {mediaType: 'image/jpeg', width: canvas.width, height: canvas.height,
            size: bytes.length, sha256: ThemeData.hash(bytes), data}, variants: [variant]};
      }, variant);
      const receiver = receiverCore.create({port: 0});
      const session = await receiver.start({kind: 'wallpaper'});
      let received;
      try {
        assert.equal(await send(session, JSON.stringify(envelope)), 202);
        assert.equal(receiver.status(session.sessionId).state, 'received');
        const chunks = [];
        for (let offset = 0;;) {
          const part = receiver.read(session.sessionId, offset);
          chunks.push(Buffer.from(part.data, 'base64')); offset = part.nextOffset;
          if (part.done) break;
        }
        received = JSON.parse(Buffer.concat(chunks).toString('utf8'));
      } finally { await receiver.stop(session.sessionId); }
      const before = await page.evaluate(async () => ({theme: ThemeManager.current().id, count: (await ThemeManager.list()).length}));
      await page.locator('#btnSettings').click();
      await page.locator('[data-category=wallpapers]').click();
      await page.evaluate(data => PersonalWallpaper.receive(data), received);
      assert.equal(await page.evaluate(() => PersonalWallpaper.state().installed), false);
      await page.locator('#wallpaperApply').click();
      await page.waitForFunction(() => PersonalWallpaper.state().installed);
      await page.getByRole('button', {name: 'Back to Home', exact: true}).click();
      await page.waitForFunction(() => {
        const video = document.getElementById('ctvWallpaperVideo');
        return HomeWallpaper.state().source === 'personal' && HomeWallpaper.state().actualQuality === '1080p' && video && video.currentTime > 0;
      }).catch(async error => {
        const observed = await page.evaluate(() => {
          const video = document.getElementById('ctvWallpaperVideo');
          const state = HomeWallpaper.state(); delete state.posterURL;
          return {state, video: video && {width: video.videoWidth, height: video.videoHeight,
            error: video.error && video.error.code, time: video.currentTime}, errors: []};
        });
        throw Error(error.message + ': ' + JSON.stringify(observed));
      });
      assert.deepEqual(await page.evaluate(() => {
        const video = document.getElementById('ctvWallpaperVideo'); return [video.videoWidth, video.videoHeight, video.muted];
      }), [1920, 1080, true]);
      assert.deepEqual(await page.evaluate(async () => ({theme: ThemeManager.current().id, count: (await ThemeManager.list()).length})), before,
        'personal upload never installs/selects a theme');
      await page.reload(); await page.locator('#tiles .focused').waitFor(); await page.evaluate(() => HomeUIReady);
      await page.waitForFunction(() => HomeWallpaper.state().actualQuality === '1080p');
      assert.equal(await page.evaluate(() => PersonalWallpaper.state().origin), 'cytv');
      await page.evaluate(async () => {
        const item = (await ThemeManager.list()).find(theme => theme.id === 'builtin:ribbon');
        await ThemeManager.selectInstalled(item);
      });
      await page.waitForFunction(() => HomeWallpaper.state().source === 'personal' && HomeWallpaper.state().actualQuality === '1080p');
      await page.evaluate(() => PersonalWallpaper.remove());
      assert.equal(await page.evaluate(() => HomeWallpaper.state().source), 'theme');
      assert.equal(await page.locator('#ctvWallpaperVideo').count(), 0);
      assert.deepEqual(errors, []);
      await context.close();
      for (const sessionId of sessions) await rpc('wallpaperCacheStop', {sessionId});
      fs.rmSync(directory, {recursive: true, force: true});
      console.log('PASS personal video HTTP receipt, explicit Apply, real decode, reload and theme independence: ' + edition);
    }
  } finally { await browser.close(); await new Promise(resolve => server.close(resolve)); }
})().catch(error => { console.error(error); process.exitCode = 1; });
