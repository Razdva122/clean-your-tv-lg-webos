'use strict';
const assert = require('assert/strict'),
  vm = require('vm'),
  fs = require('fs'),
  crypto = require('crypto');
async function run() {
  const bytes = new Uint8Array(100000),
    digest = crypto.createHash('sha256').update(bytes).digest('hex'),
    manifest = {
      wallpaperVideo: {
        variants: [
          {
            quality: '1080p',
            path: 'video.mp4',
            size: bytes.length,
            sha256: digest
          }
        ]
      }
    },
    pack = { files: { 'video.mp4': bytes } };
  let starts = 0,
    stops = [],
    writes = [],
    fail = false,
    delayStart = false,
    pending = [],
    liveTimers = 0;
  class Bridge {
    cancel() {}
    call(uri, body) {
      const method = uri.split('/').pop(),
        p = JSON.parse(body);
      let response = { returnValue: true };
      if (method === 'wallpaperCacheStart') {
        starts++;
        response.sessionId = starts.toString(16).padStart(48, '0');
      } else if (method === 'wallpaperCacheStop') stops.push(p.sessionId);
      else if (method === 'wallpaperCacheWrite') {
        writes.push(p);
        response.nextOffset = p.offset + Buffer.from(p.data, 'base64').length;
        if (fail) {
          fail = false;
          response.returnValue = false;
        }
      } else if (method === 'wallpaperCacheCommit')
        response.handles = {
          '1080p': 'http://127.0.0.1:1234/' + 'a'.repeat(32) + '/1080p.mp4'
        };
      const callback = () => this.onservicecallback(JSON.stringify(response));
      if (method === 'wallpaperCacheStart' && delayStart)
        pending.push(callback);
      else Promise.resolve().then(callback);
    }
  }
  const context = {
    Promise,
    Uint8Array,
    JSON,
    PalmServiceBridge: Bridge,
    setTimeout,
    clearTimeout,
    setInterval() {
      liveTimers++;
      return {};
    },
    clearInterval(timer) {
      if (timer) liveTimers--;
    },
    document: { querySelector: () => null },
    btoa: (raw) => Buffer.from(raw, 'binary').toString('base64')
  };
  vm.runInNewContext(
    fs.readFileSync('launcher/wallpaper-media-cache.js', 'utf8'),
    context
  );
  let externallyCancelled = false;
  await assert.rejects(
    context.WallpaperMediaCache.prepare(manifest, pack, () => true),
    /Cancelled/
  );
  const lease = await context.WallpaperMediaCache.prepare(
    manifest,
    pack,
    () => externallyCancelled
  );
  assert.equal(starts, 0, 'prepare is lazy');
  const first = lease.acquire();
  assert.equal(first, lease.acquire(), 'concurrent acquire reuses upload');
  const handles = await first;
  assert.match(handles['1080p'], /^http:\/\/127/);
  assert.deepEqual(
    writes.map((p) => p.offset),
    [0, 49152, 98304]
  );
  assert.equal(await lease.acquire(), handles);
  assert.equal(starts, 1);
  assert.equal(liveTimers, 1);
  await lease.release();
  assert.equal(stops.length, 1);
  assert.equal(liveTimers, 0);
  externallyCancelled = true;
  await lease.acquire();
  await lease.release();
  assert.equal(
    starts,
    2,
    'accepted lease survives routine manager cancellation on resume'
  );
  fail = true;
  await assert.rejects(lease.acquire(), /unavailable/);
  assert.equal(stops.length, 3);
  await lease.acquire();
  assert.equal(starts, 4, 'retry opens a fresh lease');
  await lease.release();
  delayStart = true;
  const stale = lease.acquire();
  await lease.release();
  pending.shift()();
  await assert.rejects(stale, /Cancelled/);
  assert.equal(stops.length, 5, 'late start session is stopped');
  delayStart = false;
  await lease.acquire();
  await lease.dispose();
  assert.equal(liveTimers, 0);
  await assert.rejects(lease.acquire(), /Cancelled/);
  console.log(
    'PASS native adapter lazy upload, bounded chunks, coalescing, retry, release and stale start cleanup'
  );
}
run().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
