'use strict';
const { assert, fs, path, chromium, stage } = require('./browser.cjs'),
  http = require('node:http');
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
        {
          '.js': 'application/javascript',
          '.json': 'application/json',
          '.html': 'text/html',
          '.css': 'text/css',
          '.mp4': 'video/mp4',
          '.jpg': 'image/jpeg'
        }[path.extname(file)] || 'application/octet-stream'
      );
      res.end(fs.readFileSync(file));
    });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const browser = await chromium.launch({
    headless: true,
    channel: process.env.BROWSER_CHANNEL || 'chrome'
  });
  try {
    const p = await browser.newPage({
        viewport: { width: 1920, height: 1080 }
      }),
      errors = [];
    p.on('pageerror', (e) => errors.push(e.message));
    await p.addInitScript(() => {
      Object.defineProperty(window, 'WallpaperMediaCache', {
        configurable: true,
        get: () => undefined,
        set: () => {}
      });
      window.heldWallpaperFrames = [];
      window.holdWallpaperFrames = true;
      const native = HTMLVideoElement.prototype.requestVideoFrameCallback;
      HTMLVideoElement.prototype.requestVideoFrameCallback = function (
        callback
      ) {
        const video = this;
        return native.call(video, (now, metadata) => {
          const deliver = () => callback(now, metadata);
          if (holdWallpaperFrames) heldWallpaperFrames.push({ video, deliver });
          else deliver();
        });
      };
    });
    await p.route(/^https:/, (r) => r.abort());
    await p.goto(
      'http://127.0.0.1:' + server.address().port + '/launcher/index.html'
    );
    await p.locator('#tiles .focused').waitFor();
    await p.evaluate(() => HomeUIReady);
    await p.evaluate(async () => {
      await PersonalWallpaper.select('builtin:black-hole');
      HomeWallpaper.setQuality('4k');
    });
    await p.waitForFunction(
      () => {
        const v = document.querySelector('video');
        return (
          v &&
          v.videoWidth === 3840 &&
          heldWallpaperFrames.some((frame) => frame.video === v)
        );
      },
      null,
      { timeout: 8000 }
    );
    const handoff = await p.evaluate(() => ({
      quality: HomeWallpaper.state().actualQuality,
      poster: document.querySelector('video').poster,
      background: getComputedStyle(document.getElementById('homeSurface'))
        .backgroundImage,
      revealed: document
        .getElementById('homeSurface')
        .classList.contains('ctv-wallpaper-playing')
    }));
    assert.equal(handoff.quality, 'image');
    assert.equal(handoff.revealed, false);
    assert.match(
      handoff.background,
      /blob:/,
      'poster must remain painted above the video'
    );
    assert.match(handoff.poster, /blob:/);
    await p.evaluate(() => {
      holdWallpaperFrames = false;
      heldWallpaperFrames.forEach((frame) => frame.deliver());
      heldWallpaperFrames = [];
    });
    await p.waitForFunction(() => {
      const v = document.querySelector('video');
      return v && v.videoWidth === 3840 && v.currentTime > 1;
    });
    await p.evaluate(() => {
      window.streamEvents = [];
      const v = document.querySelector('video');
      ['seeking', 'waiting', 'ended', 'error'].forEach((name) =>
        v.addEventListener(name, () =>
          streamEvents.push({ name, time: v.currentTime })
        )
      );
    });
    await p.waitForFunction(
      () => document.querySelector('video').currentTime > 38,
      null,
      { timeout: 42000 }
    );
    const state = await p.evaluate(() => {
      const v = document.querySelector('video');
      return {
        stream: WallpaperStream.state(),
        events: streamEvents,
        width: v.videoWidth,
        height: v.videoHeight,
        time: v.currentTime,
        buffered: Array.from({ length: v.buffered.length }, (_, i) => [
          v.buffered.start(i),
          v.buffered.end(i)
        ])
      };
    });
    assert.deepEqual(
      state.events,
      [],
      'three loop boundaries must not seek or wait'
    );
    assert.equal(state.stream.mode, 'mse');
    assert.equal(state.width, 3840);
    assert.equal(state.height, 2160);
    assert.equal(state.buffered.length, 1);
    assert.ok(
      state.stream.bufferSpanSeconds < 50,
      'old compressed data must be removed'
    );
    assert.ok(state.stream.appends >= 4);
    await p.evaluate(() => HomeWallpaper.setQuality('image'));
    assert.equal(await p.locator('video').count(), 0);
    assert.equal(
      await p.evaluate(() => WallpaperStream.state().mode),
      'closed'
    );
    await p.evaluate(() => {
      window.originalMediaSupport = MediaSource.isTypeSupported;
      MediaSource.isTypeSupported = () => false;
      HomeWallpaper.setQuality('4k');
    });
    await p.waitForFunction(() => HomeWallpaper.state().actualQuality === '4k');
    assert.equal(
      await p.evaluate(() => WallpaperStream.state().mode),
      'native'
    );
    await p.evaluate(() => {
      HomeWallpaper.setQuality('image');
      MediaSource.isTypeSupported = originalMediaSupport;
    });
    const corrupt = Buffer.from(
      fs.readFileSync('launcher/wallpapers/black-hole-stream.mp4')
    );
    corrupt[100] ^= 1;
    await p.route('**/wallpapers/black-hole-stream.mp4', (r) =>
      r.fulfill({ body: corrupt, contentType: 'video/mp4' })
    ); // The pinned CARD route refuses corrupt media; it must not launch a second decoder.
    await p.evaluate((size) => {
      window.integrityAudit = {
        hashChecks: 0,
        hash: null,
        appends: 0,
        created: [],
        revoked: [],
        videos: 0
      };
      const hash = ThemeData.hash,
        append = SourceBuffer.prototype.appendBuffer,
        create = URL.createObjectURL,
        revoke = URL.revokeObjectURL,
        element = document.createElement;
      ThemeData.hash = function (bytes) {
        const result = hash(bytes);
        if (bytes.byteLength === size) {
          integrityAudit.hashChecks++;
          integrityAudit.hash = result;
        }
        return result;
      };
      SourceBuffer.prototype.appendBuffer = function (bytes) {
        integrityAudit.appends++;
        return append.call(this, bytes);
      };
      URL.createObjectURL = function (value) {
        const url = create.call(this, value);
        if (value instanceof MediaSource) integrityAudit.created.push(url);
        return url;
      };
      URL.revokeObjectURL = function (url) {
        if (integrityAudit.created.includes(url))
          integrityAudit.revoked.push(url);
        return revoke.call(this, url);
      };
      document.createElement = function (name) {
        if (name.toLowerCase() === 'video') integrityAudit.videos++;
        return element.apply(this, arguments);
      };
    }, corrupt.length);
    await p.evaluate(() => HomeWallpaper.setQuality('4k'));
    await p.waitForFunction(
      () =>
        HomeWallpaper.state().actualQuality === 'image' &&
        /4K playback failed/.test(HomeWallpaper.state().notice) &&
        WallpaperStream.state().mode === 'failed'
    );
    const refusal = await p.evaluate(() => ({
      audit: integrityAudit,
      state: HomeWallpaper.state(),
      background: getComputedStyle(document.getElementById('homeSurface'))
        .backgroundImage,
      playing: document
        .getElementById('homeSurface')
        .classList.contains('ctv-wallpaper-playing')
    }));
    assert.equal(
      refusal.audit.hashChecks,
      1,
      'the streamed bytes reach the real hash check'
    );
    assert.equal(
      refusal.audit.hash,
      require('node:crypto').createHash('sha256').update(corrupt).digest('hex')
    );
    assert.equal(
      refusal.audit.appends,
      0,
      'corrupt bytes never reach SourceBuffer'
    );
    assert.equal(
      refusal.audit.videos,
      1,
      'integrity refusal never creates an FHD fallback decoder'
    );
    assert.equal(refusal.audit.created.length, 1);
    assert.deepEqual(
      refusal.audit.revoked,
      refusal.audit.created,
      'the failed MSE URL is disposed'
    );
    assert.equal(await p.locator('video').count(), 0);
    assert.equal(refusal.playing, false);
    assert.match(
      refusal.background,
      /blob:/,
      'the accepted poster remains visible'
    );
    assert.equal(refusal.state.preferenceQuality, '4k');
    assert.match(
      refusal.state.notice,
      /4K playback failed\. Using the image\./
    );
    await p.evaluate(() => HomeWallpaper.setQuality('image'));
    assert.deepEqual(errors, []);
    console.log(
      'PASS first-frame poster handoff, continuous native UHD across 3 loops, bounded buffer, teardown, unsupported-MSE validated native fallback and corrupt-stream poster fallback without decoder/URL leaks'
    );
  } finally {
    await browser.close();
    await new Promise((r) => server.close(r));
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
