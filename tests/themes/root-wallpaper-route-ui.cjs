'use strict';
// The preview normally removes the cache adapter. Restore it to exercise the TV ordering.
const { assert, fs, path, chromium, stage } = require('./browser.cjs'),
  http = require('node:http');
(async () => {
  const site = stage('root-wallpaper-route'),
    errors = [];
  const server = http.createServer((req, res) => {
    const file = path.resolve(
      site,
      '.' + new URL(req.url, 'http://localhost').pathname
    );
    if (!file.startsWith(site + path.sep) || !fs.existsSync(file))
      return res.writeHead(404).end();
    let body = fs.readFileSync(file);
    if (file.endsWith('/index.html'))
      body = Buffer.from(
        body
          .toString()
          .replace(
            '<script>window.WallpaperMediaCache = undefined;</script>',
            '<script src="wallpaper-media-cache.js"></script>'
          )
      );
    if (file.endsWith('/bridge.js'))
      body = Buffer.concat([
        body,
        Buffer.from(`
   window.cacheCalls=[];const originalCall=PalmServiceBridge.prototype.call;
   PalmServiceBridge.prototype.call=function(uri,payload){
    if(/\\/wallpaperCache/.test(uri)){cacheCalls.push(uri.split('/').pop());queueMicrotask(()=>this.onservicecallback(JSON.stringify({returnValue:false,errorCode:-1})));return;}
    return originalCall.call(this,uri,payload);
   };`)
      ]);
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
    res.end(body);
  });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const browser = await chromium.launch({
    headless: true,
    channel: process.env.BROWSER_CHANNEL || 'chrome'
  });
  try {
    const page = await browser.newPage();
    page.on('pageerror', (e) => errors.push(e.message));
    await page.addInitScript(() => {
      window.PREVIEW_HOME_CONTEXT = 'empty';
      window.webOS = { deviceInfo: (callback) => callback({ uhd: true }) };
    });
    await page.route(/^https:/, (r) => r.abort());
    await page.goto(
      'http://127.0.0.1:' + server.address().port + '/root-launcher/index.html'
    );
    await page.locator('#tiles .focused').waitFor();
    await page.evaluate(() => HomeUIReady);
    await page.evaluate(async () => {
      if (!WallpaperMediaCache) throw Error('Missing real cache adapter');
      await PersonalWallpaper.select('builtin:black-hole');
      HomeWallpaper.setQuality('4k');
    });
    // Settle either route, so the old implementation fails on an explanatory assertion.
    await page.waitForFunction(
      () =>
        HomeWallpaper.state().actualQuality === '4k' ||
        HomeWallpaper.state().notice.includes('cache')
    );
    assert.equal(
      await page.evaluate(() => HomeWallpaper.state().actualQuality),
      '4k',
      'Root packaged MSE must be chosen before the rejecting native cache'
    );
    assert.equal(
      await page.evaluate(() => WallpaperStream.state().mode),
      'mse'
    );
    assert.deepEqual(await page.evaluate(() => cacheCalls), []);
    await page.waitForFunction(
      () => document.querySelector('video').currentTime > 1
    );
    assert.equal(await page.evaluate(() => CYTV_HOME_HOST), 'card');
    assert.equal(
      await page.evaluate(() => HomePresentationController),
      null,
      'ordinary CARD does not infer overlay context'
    );
    await page.evaluate(() => {
      window.oldVideo = document.querySelector('video');
      HomeWallpaper.suspend('decoder-context');
    });
    assert.equal(await page.locator('video').count(), 0);
    assert.equal(
      await page.evaluate(() => WallpaperStream.state().mode),
      'closed'
    );
    assert.equal(
      await page.evaluate(
        () => oldVideo.paused && !oldVideo.hasAttribute('src')
      ),
      true
    );
    await page.evaluate(() => HomeWallpaper.resume('decoder-context'));
    await page.waitForFunction(
      () => HomeWallpaper.state().actualQuality === '4k'
    );
    // Unsupported MSE retains the normal cache path; its explicit rejection stays image.
    await page.evaluate(() => {
      HomeWallpaper.setQuality('image');
      window.support = MediaSource.isTypeSupported;
      MediaSource.isTypeSupported = () => false;
      HomeWallpaper.setQuality('4k');
    });
    await page.waitForFunction(() =>
      HomeWallpaper.state().notice.includes('cache')
    );
    assert.equal(await page.locator('video').count(), 0);
    assert.equal(
      await page.evaluate(() => HomeWallpaper.state().actualQuality),
      'image'
    );
    assert.deepEqual(await page.evaluate(() => cacheCalls), [
      'wallpaperCacheStart'
    ]);
    await page.evaluate(() => {
      MediaSource.isTypeSupported = support;
      cacheCalls = [];
    });
    const corrupt = Buffer.from(
      fs.readFileSync('launcher/wallpapers/black-hole-stream.mp4')
    );
    corrupt[100] ^= 1;
    await page.route('**/wallpapers/black-hole-stream.mp4', (r) =>
      r.fulfill({ body: corrupt, contentType: 'video/mp4' })
    );
    await page.evaluate(() => HomeWallpaper.setQuality('4k'));
    await page.waitForFunction(() =>
      HomeWallpaper.state().notice.includes('playback failed')
    );
    assert.equal(await page.locator('video').count(), 0);
    assert.equal(
      await page.evaluate(() => HomeWallpaper.state().actualQuality),
      'image'
    );
    assert.deepEqual(await page.evaluate(() => cacheCalls), []);
    assert.deepEqual(errors, []);
    await page.close();
    const noRoot = await browser.newPage();
    noRoot.on('pageerror', (e) => errors.push(e.message));
    await noRoot.addInitScript(() => {
      window.webOS = { deviceInfo: (callback) => callback({ uhd: true }) };
    });
    await noRoot.route(/^https:/, (r) => r.abort());
    await noRoot.goto(
      'http://127.0.0.1:' + server.address().port + '/launcher/index.html'
    );
    await noRoot.locator('#tiles .focused').waitFor();
    await noRoot.evaluate(() => HomeUIReady);
    await noRoot.evaluate(async () => {
      if (!WallpaperMediaCache)
        throw Error('Missing real No-root cache adapter');
      await PersonalWallpaper.select('builtin:black-hole');
      HomeWallpaper.setQuality('4k');
    });
    await noRoot.waitForFunction(
      () => HomeWallpaper.state().actualQuality === '4k'
    );
    assert.equal(
      await noRoot.evaluate(() => WallpaperStream.state().mode),
      'mse'
    );
    assert.deepEqual(await noRoot.evaluate(() => cacheCalls), []);
    await noRoot.evaluate(() => HomeWallpaper.setQuality('image'));
    assert.equal(await noRoot.locator('video').count(), 0);
    assert.deepEqual(errors, []);
    console.log(
      'PASS Root and No-root CARD packaged MSE before rejecting real cache; decode, suspension, disposal, unsupported-MSE cache fallback and corrupt stream'
    );
  } finally {
    await browser.close();
    await new Promise((r) => server.close(r));
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
