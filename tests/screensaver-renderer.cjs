'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const { chromium } = require('playwright');
const root = path.resolve(__dirname, '../screensaver');

(async () => {
  assert.ok(
    fs.existsSync(path.join(root, 'renderer.js')),
    'popup renderer exists'
  );
  const requests = [];
  let content = { mode: 'clock' };
  let close = false;
  let unavailable = false;
  const deniedTokens = new Set();
  const malformedTokens = new Set();
  const delayedTokens = new Set();
  const delayedReplies = new Map();
  const personalVideoPath = '/' + 'a'.repeat(32) + '/4k.mp4';
  const server = http.createServer((req, res) => {
    if (
      req.url === '/backgrounds/ribbon-video.mp4' ||
      req.url === personalVideoPath
    ) {
      res.setHeader('Content-Type', 'video/mp4');
      return fs
        .createReadStream(
          path.resolve(__dirname, '../themes/ribbon/assets/wallpaper-4k.mp4')
        )
        .pipe(res);
    }
    if (req.url === '/screensaver/media/photo.png?lease=opaque') {
      res.setHeader('Content-Type', 'image/png');
      return res.end(
        Buffer.from(
          'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=',
          'base64'
        )
      );
    }
    if (
      req.url === '/screensaver/media/test.mp4?lease=opaque' ||
      req.url === '/backgrounds/ribbon-video-1080p.mp4'
    ) {
      res.setHeader('Content-Type', 'video/mp4');
      return fs
        .createReadStream(
          path.resolve(__dirname, '../themes/ribbon/assets/wallpaper-1080p.mp4')
        )
        .pipe(res);
    }
    if (req.url === '/screensaver') {
      let body = '';
      req.on('data', (chunk) => {
        body += chunk;
      });
      req.on('end', () => {
        requests.push({
          body: JSON.parse(body),
          token: req.headers['x-cytv-session']
        });
        if (unavailable) return res.writeHead(503).end();
        if (deniedTokens.has(req.headers['x-cytv-session']))
          return res.writeHead(403).end();
        res.setHeader('Content-Type', 'application/json');
        if (delayedTokens.has(req.headers['x-cytv-session'])) {
          delayedReplies.set(req.headers['x-cytv-session'], () =>
            res.end(JSON.stringify({ close, content }))
          );
          return;
        }
        res.end(
          JSON.stringify(
            malformedTokens.has(req.headers['x-cytv-session'])
              ? { close: false }
              : { close, content }
          )
        );
      });
      return;
    }
    const file = path.join(
      root,
      req.url === '/' ? 'index.html' : req.url.slice(1)
    );
    if (!file.startsWith(root + path.sep) || !fs.existsSync(file))
      return res.writeHead(404).end();
    res.setHeader(
      'Content-Type',
      {
        '.html': 'text/html',
        '.js': 'application/javascript',
        '.css': 'text/css'
      }[path.extname(file)] || 'application/octet-stream'
    );
    res.end(fs.readFileSync(file));
  });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const origin = 'http://127.0.0.1:' + server.address().port;
  const endpoint = origin + '/screensaver';
  const sessionId = 'a'.repeat(48);
  let browser;
  const errors = [];
  async function pageFor(params = { sessionId, generation: 1, endpoint }) {
    const page = await browser.newPage();
    page.on('pageerror', (error) => errors.push(error.message));
    await page.addInitScript((launch) => {
      window.activationCount = 0;
      window.startupEvents = [];
      window.clockWithoutDate = false;
      new MutationObserver(() => {
        const ambient = document.getElementById('ambient');
        const clock = document.getElementById('clock');
        const date = document.getElementById('clockDate');
        if (
          ambient &&
          !ambient.hidden &&
          clock &&
          !clock.hidden &&
          date &&
          (date.hidden || !date.textContent)
        )
          window.clockWithoutDate = true;
      }).observe(document, {
        subtree: true,
        attributes: true,
        childList: true
      });
      const formatDate = Date.prototype.toLocaleDateString;
      Date.prototype.toLocaleDateString = function () {
        window.startupEvents.push('date');
        return formatDate.apply(this, arguments);
      };
      const send = XMLHttpRequest.prototype.send;
      XMLHttpRequest.prototype.send = function (data) {
        if (typeof data === 'string' && JSON.parse(data).mediaState === 'ready')
          window.startupEvents.push('ready');
        return send.call(this, data);
      };
      window.PalmSystem = {
        launchParams: JSON.stringify(launch),
        activate() {
          window.activationCount += 1;
        }
      };
      window.closeCount = 0;
      window.close = () => {
        window.closeCount += 1;
      };
    }, params);
    await page.goto(origin);
    return page;
  }
  try {
    browser = await chromium.launch({
      headless: true,
      channel: process.env.BROWSER_CHANNEL || 'chrome'
    });
    let page = await pageFor();
    await page.waitForFunction(
      () => document.querySelector('#clock').textContent.length > 0
    );
    await page.waitForTimeout(1100);
    assert.equal(await page.evaluate(() => activationCount), 1);
    assert.ok(
      requests.some(
        (r) => r.body.mediaState === 'ready' && r.body.visible && r.body.focused
      ),
      'clock becomes ready only with visible/focused heartbeat'
    );
    assert.ok(
      requests.every(
        (r) =>
          r.token === sessionId &&
          r.body.sessionId === sessionId &&
          r.body.generation === 1 &&
          r.body.schema === 1
      ),
      'every heartbeat authenticates the owned generation'
    );
    await page.keyboard.down('ArrowRight');
    await page.keyboard.down('ArrowRight');
    assert.equal(
      await page.evaluate(() => closeCount),
      0,
      'held navigation cannot leak its release to underlying app'
    );
    await page.keyboard.up('ArrowRight');
    await page.waitForFunction(() => closeCount === 1);
    await page.evaluate(() =>
      document.dispatchEvent(
        new KeyboardEvent('keyup', { keyCode: 39, bubbles: true })
      )
    );
    assert.equal(
      await page.evaluate(() => closeCount),
      1,
      'teardown is idempotent'
    );
    await page.close();

    const before = requests.length;
    page = await pageFor({
      sessionId,
      generation: 1,
      endpoint: 'http://127.0.0.1.evil.invalid/screensaver'
    });
    await page.waitForFunction(() => closeCount === 1);
    assert.equal(await page.evaluate(() => activationCount), 0);
    assert.equal(
      requests.length,
      before,
      'invalid endpoint never receives credentials'
    );
    await page.close();

    content = { mode: 'photo', url: 'https://example.invalid/photo.jpg' };
    page = await pageFor();
    await page.waitForTimeout(1100);
    assert.equal(
      await page.locator('img[src]').count(),
      0,
      'untrusted media is never fetched'
    );
    assert.ok(
      requests.some((r) => r.body.mediaState === 'error'),
      'unsupported content is reported'
    );
    const fallbackStart = requests.length;
    content = { mode: 'ambient', clockOverlay: true };
    await page.waitForTimeout(2100);
    assert.ok(
      requests
        .slice(fallbackStart)
        .some((r) => r.body.mediaState === 'ready' && r.body.visible),
      'controller-selected glow recovers from media error to a visible ready session'
    );
    assert.equal(await page.evaluate(() => closeCount), 0);
    assert.equal(await page.locator('#ambient').isVisible(), true);
    assert.match(
      await page
        .locator('#ambient .glow-visible')
        .evaluate((layer) => getComputedStyle(layer).backgroundImage),
      /radial-gradient/
    );
    assert.equal(await page.locator('#clockTime').isVisible(), true);
    assert.match(await page.locator('#clockTime').textContent(), /^\d\d:\d\d$/);
    assert.equal(await page.locator('#clockDate').isVisible(), true);
    assert.equal(
      await page.evaluate(() => clockWithoutDate),
      false,
      'ambient time and date become visible together'
    );
    assert.ok((await page.locator('#clockDate').textContent()).trim());
    assert.equal(
      await page.evaluate(() => startupEvents[0]),
      'ready',
      'locale date formatting must not block the first focused frame'
    );
    content = { ...content, clock: { locale: 'ru', hour12: true } };
    await page.waitForFunction(
      () => {
        const date = new Date();
        const localized = date.toLocaleDateString('ru', {
          weekday: 'long',
          month: 'long',
          day: 'numeric'
        });
        return (
          document.querySelector('#clockDate').textContent === localized &&
          !/^\d{2}:\d{2}$/.test(
            document.querySelector('#clockTime').textContent
          ) &&
          document.documentElement.lang === 'ru'
        );
      },
      null,
      { timeout: 2500 }
    );
    content = { ...content, clock: { locale: 'de', hour12: false } };
    await page.waitForFunction(
      () =>
        /^\d{2}:\d{2}$/.test(
          document.querySelector('#clockTime').textContent
        ) && document.documentElement.lang === 'de',
      null,
      { timeout: 2500 }
    );
    content = { ...content, clockOverlay: false };
    await page.locator('#clock').waitFor({ state: 'hidden', timeout: 2500 });
    assert.equal(await page.locator('#ambient').isVisible(), true);
    await page.close();

    content = {
      mode: 'photo',
      clockOverlay: true,
      url: origin + '/screensaver/media/photo.png?lease=opaque'
    };
    page = await pageFor();
    await page.locator('#photo').waitFor({ state: 'visible' });
    assert.equal(
      await page.locator('#photo').evaluate((image) => image.naturalWidth),
      1,
      'authorized photo decodes before presentation'
    );
    await page.locator('#clock').waitFor({ state: 'visible', timeout: 2500 });
    content = { ...content, clockOverlay: false };
    await page.locator('#clock').waitFor({ state: 'hidden', timeout: 2500 });
    assert.equal(await page.locator('#photo').isVisible(), true);
    content = { mode: 'clock' };
    await page.locator('#clock').waitFor({ state: 'visible' });
    assert.equal(
      await page.locator('#photo').getAttribute('src'),
      null,
      'content replacement releases the previous photo'
    );
    await page.close();

    content = {
      mode: 'video',
      clockOverlay: true,
      url: origin + '/screensaver/media/test.mp4?lease=opaque'
    };
    page = await pageFor();
    await page.waitForFunction(
      () => document.querySelector('video').currentTime > 0
    );
    assert.equal(
      await page.locator('video').evaluate((v) => v.muted && v.loop),
      true
    );
    await page.locator('#clock').waitFor({ state: 'visible', timeout: 2500 });
    content = { ...content, clockOverlay: false };
    await page.locator('#clock').waitFor({ state: 'hidden', timeout: 2500 });
    assert.equal(await page.locator('video').isVisible(), true);
    assert.equal(await page.locator('video').getAttribute('src'), content.url);
    close = true;
    await page.waitForFunction(() => closeCount === 1);
    assert.equal(
      await page.locator('video').getAttribute('src'),
      null,
      'close releases the video decoder source'
    );
    assert.equal(await page.locator('video').evaluate((v) => v.paused), true);
    await page.close();

    close = false;
    content = { mode: 'video', assetId: 'ribbon-video', clockOverlay: true };
    page = await pageFor();
    await page.waitForFunction(() => {
      var video = document.querySelector('video');
      return (
        video.videoWidth === 3840 &&
        video.videoHeight === 2160 &&
        video.currentTime > 0
      );
    });
    assert.equal(await page.locator('#clock').isVisible(), true);
    content = { ...content, quality: '1080p' };
    await page.waitForFunction(() => {
      var video = document.querySelector('video');
      return (
        video.videoWidth === 1920 &&
        video.videoHeight === 1080 &&
        video.currentTime > 0
      );
    });
    assert.equal(await page.locator('#clock').isVisible(), true);
    await page.close();

    content = {
      mode: 'video',
      cacheUrl: origin + personalVideoPath,
      clockOverlay: true
    };
    page = await pageFor();
    await page.waitForFunction(() => {
      var video = document.querySelector('video');
      var clock = document.querySelector('#clock');
      return (
        video.videoWidth === 3840 &&
        video.videoHeight === 2160 &&
        video.currentTime > 0 &&
        !clock.hidden
      );
    });
    await page.close();

    close = false;
    content = { mode: 'clock' };
    page = await pageFor({ sessionId, generation: 900, endpoint });
    await page.locator('#clock').waitFor({ state: 'visible' });
    async function relaunch(params) {
      await page.evaluate(
        (value) =>
          document.dispatchEvent(
            new CustomEvent('webOSRelaunch', { detail: { params: value } })
          ),
        params
      );
    }
    const sameOwnerToken = 'c'.repeat(48);
    await relaunch({ sessionId: sameOwnerToken, generation: 900, endpoint });
    await page.waitForTimeout(1200);
    assert.equal(await page.evaluate(() => activationCount), 2);
    assert.ok(
      requests.some(
        (r) => r.token === sameOwnerToken && r.body.mediaState === 'ready'
      ),
      'same owner may replace a session after authenticated proof'
    );
    const lowerOwnerToken = 'd'.repeat(48);
    await relaunch({ sessionId: lowerOwnerToken, generation: 2, endpoint });
    await page.waitForTimeout(1200);
    assert.ok(
      requests.some(
        (r) => r.token === lowerOwnerToken && r.body.mediaState === 'ready'
      ),
      'opaque lower generation may replace the current owner after authenticated proof'
    );
    const denied = 'e'.repeat(48);
    deniedTokens.add(denied);
    await relaunch({ sessionId: denied, generation: 999, endpoint });
    await page.waitForTimeout(1200);
    assert.equal(await page.evaluate(() => activationCount), 3);
    assert.equal(
      await page.evaluate(() => closeCount),
      0,
      'denied candidate cannot close the current surface'
    );
    assert.equal(
      requests.at(-1).token,
      lowerOwnerToken,
      'denied candidate cannot replace current heartbeat'
    );
    const malformed = 'f'.repeat(48);
    malformedTokens.add(malformed);
    await relaunch({ sessionId: malformed, generation: 1000, endpoint });
    await page.waitForTimeout(1200);
    assert.equal(
      requests.at(-1).token,
      lowerOwnerToken,
      'malformed proof cannot replace current owner'
    );
    const replayStart = requests.length;
    await relaunch({ sessionId: sameOwnerToken, generation: 900, endpoint });
    await page.waitForTimeout(1200);
    assert.ok(
      requests.slice(replayStart).every((r) => r.token === lowerOwnerToken),
      'retired session cannot be replayed'
    );
    const delayed = '1'.repeat(48);
    delayedTokens.add(delayed);
    await relaunch({ sessionId: delayed, generation: 3000, endpoint });
    await page.waitForTimeout(200);
    assert.ok(delayedReplies.has(delayed));
    const newest = '2'.repeat(48);
    await relaunch({ sessionId: newest, generation: 1, endpoint });
    await page.waitForTimeout(1200);
    assert.ok(
      requests.some((r) => r.token === newest && r.body.mediaState === 'ready')
    );
    delayedReplies.get(delayed)();
    const afterLate = requests.length;
    await page.waitForTimeout(1200);
    assert.ok(
      requests.slice(afterLate).every((r) => r.token === newest),
      'late proof from superseded candidate cannot replace accepted owner'
    );
    // Stopping the controller revokes the current token. A definitive denial
    // closes on the next heartbeat; a lost connection still gets a grace period.
    deniedTokens.add(newest);
    await page.waitForFunction(() => closeCount === 1, null, { timeout: 2500 });
    await page.close();

    page = await pageFor();
    await page.waitForTimeout(200);
    await page.keyboard.down('ArrowRight');
    await page.evaluate(
      (params) =>
        document.dispatchEvent(
          new CustomEvent('webOSRelaunch', { detail: { params } })
        ),
      { sessionId: 'b'.repeat(48), generation: 2, endpoint }
    );
    await page.waitForTimeout(200);
    await page.keyboard.up('ArrowRight');
    assert.equal(
      await page.evaluate(() => closeCount),
      0,
      'old wake release cannot close a relaunched generation'
    );
    await page.waitForTimeout(1100);
    assert.ok(
      requests.some(
        (r) => r.body.generation === 2 && r.token === 'b'.repeat(48)
      ),
      'relaunch adopts the new authenticated owner'
    );
    const newerStart = requests.findIndex((r) => r.token === 'b'.repeat(48));
    assert.ok(
      requests
        .slice(newerStart)
        .every(
          (r) => r.body.generation === 2 || r.body.mediaState === 'closed'
        ),
      'old timers cannot send current-state heartbeats for old owner'
    );
    unavailable = true;
    await page.evaluate(() => {
      Date.now = () => 0;
    });
    await page.waitForFunction(() => closeCount === 1, null, { timeout: 8000 });
    await page.close();
    assert.deepEqual(errors, []);
    console.log(
      'screensaver renderer: lifecycle, authentication, media cleanup and controller-loss checks passed'
    );
  } finally {
    if (browser) await browser.close();
    await new Promise((resolve) => server.close(resolve));
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
