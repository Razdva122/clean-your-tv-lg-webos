// Startup may validate appearance separately; media must remain unusable until verified.
'use strict';
const assert = require('node:assert/strict'),
  fs = require('node:fs'),
  vm = require('node:vm');
const policy = require('../../launcher/theme-policy.js'),
  data = require('../../launcher/theme-data.js');
const descriptor = new Uint8Array(
  fs.readFileSync('launcher/themes/ribbon/cytv-theme.json')
);
const manifest = JSON.parse(data.decode(descriptor));
function pack(includeVideo = false) {
  const files = {};
  for (const f of [
    manifest.rules,
    ...manifest.assets,
    ...manifest.documents,
    ...(includeVideo ? manifest.wallpaperVideo.variants : [])
  ])
    files[f.path] = new Uint8Array(
      fs.readFileSync('launcher/themes/ribbon/' + f.path)
    );
  return { descriptor, digest: data.hash(descriptor), files };
}
function fixture() {
  let serial = 0;
  const urls = new Map(),
    revoked = [];
  class Blob {
    constructor(parts, options) {
      this.bytes = parts[0];
      this.type = options.type;
    }
  }
  class Image {
    set src(url) {
      const b = urls.get(url),
        info = data.imageInfo(b.bytes, b.type, true);
      this.naturalWidth = info.width;
      this.naturalHeight = info.height;
      Promise.resolve().then(() => this.onload && this.onload());
    }
  }
  const ctx = {
    JSON,
    ThemePolicy: policy,
    Uint8Array,
    ArrayBuffer,
    DataView,
    Int32Array,
    Promise,
    Image,
    Blob,
    setTimeout,
    clearTimeout,
    URL: {
      createObjectURL(blob) {
        const url = 'blob:test-' + ++serial;
        urls.set(url, blob);
        return url;
      },
      revokeObjectURL(url) {
        revoked.push(url);
      }
    }
  };
  vm.runInNewContext(fs.readFileSync('launcher/theme-data.js', 'utf8'), ctx);
  return {
    data: ctx.ThemeData,
    ctx,
    urls,
    revoked,
    videoURLs: () =>
      [...urls.values()].filter((blob) => blob.type === 'video/mp4').length
  };
}
(async () => {
  const partial = pack();
  assert.throws(
    () => data.verify(partial, '99.0.0'),
    /Unexpected|missing/,
    'strict default cannot accept partial media'
  );
  let f = fixture(),
    input = await f.data.prepare(partial, '99.0.0', () => false, true);
  assert.equal(f.videoURLs(), 0);
  assert.deepEqual(Object.keys(input.videoHandles), []);
  await assert.rejects(input.videoLease.acquire(), /Unexpected|missing/);
  assert.equal(f.videoURLs(), 0);
  f.data.dispose(input.assetHandles, input.videoHandles, input.videoLease);
  assert.equal(f.revoked.length, f.urls.size);
  for (const corruption of ['hash', 'size', 'format', 'dimensions']) {
    f = fixture();
    const p = pack(true),
      m = JSON.parse(data.decode(p.descriptor)),
      v = m.wallpaperVideo.variants[0];
    if (corruption === 'hash') p.files[v.path][0] ^= 1;
    if (corruption === 'size') p.files[v.path] = p.files[v.path].slice(0, -1);
    if (corruption === 'format') {
      p.files[v.path][4] = 0;
      v.sha256 = data.hash(p.files[v.path]);
      p.descriptor = data.encode(JSON.stringify(m));
      p.digest = data.hash(p.descriptor);
    }
    if (corruption === 'dimensions') {
      const bytes = Buffer.from(p.files[v.path]),
        tk = bytes.indexOf(Buffer.from('tkhd')) + 4;
      bytes.writeUInt32BE(1920 * 65536, tk + 76);
      p.files[v.path] = new Uint8Array(bytes);
      v.sha256 = data.hash(bytes);
      p.descriptor = data.encode(JSON.stringify(m));
      p.digest = data.hash(p.descriptor);
    }
    input = await f.data.prepare(p, '99.0.0', () => false, true);
    await assert.rejects(input.videoLease.acquire(), /hash|MP4/);
    assert.equal(
      f.videoURLs(),
      0,
      'no ' + corruption + ' bytes become a media URL'
    );
    assert.equal(
      input.manifest.id,
      'builtin:ribbon',
      'media rejection preserves verified appearance'
    );
    f.data.dispose(input.assetHandles, input.videoHandles, input.videoLease);
  }
  f = fixture();
  const full = pack(true);
  input = await f.data.prepare(full, '99.0.0', () => false, true);
  const handles = await input.videoLease.acquire();
  assert.equal(f.videoURLs(), 2);
  assert.equal(Object.keys(handles).length, 2);
  await input.videoLease.release();
  assert.equal(f.revoked.length, 2, 'release owns both media URLs');
  await input.videoLease.acquire();
  assert.equal(f.videoURLs(), 4, 'released lease can safely reacquire');
  f.data.dispose(input.assetHandles, input.videoHandles, input.videoLease);
  assert.equal(f.revoked.length, f.urls.size);
  await assert.rejects(input.videoLease.acquire(), /Cancelled/);
  for (const action of ['release', 'dispose', 'cancel']) {
    f = fixture();
    const p = pack(true);
    let finish,
      signal,
      cancelled = false;
    p.loadVideos = (s) => {
      signal = s;
      return new Promise((resolve) => {
        finish = resolve;
      });
    };
    input = await f.data.prepare(p, '99.0.0', () => cancelled, true);
    const pending = input.videoLease.acquire();
    await Promise.resolve();
    assert(finish);
    if (action === 'cancel') cancelled = true;
    else await input.videoLease[action]();
    finish();
    await assert.rejects(pending, /Cancelled/);
    assert.equal(f.videoURLs(), 0, 'late ' + action + ' cannot expose bytes');
    if (action !== 'cancel') assert.equal(signal.cancelled, true);
    f.data.dispose(input.assetHandles, input.videoHandles, input.videoLease);
  }
  // A theme switch disposes the old lease while native cache acquisition is pending.
  f = fixture();
  let deliver,
    disposed = 0,
    cacheCalls = 0;
  f.ctx.WallpaperMediaCache = {
    prepare: async () => {
      cacheCalls++;
      return {
        acquire: () =>
          new Promise((resolve) => {
            deliver = resolve;
          }),
        dispose() {
          disposed++;
        }
      };
    }
  };
  input = await f.data.prepare(pack(true), '99.0.0', () => false, true);
  const acquiring = input.videoLease.acquire();
  while (!deliver) await Promise.resolve();
  f.data.dispose(input.assetHandles, input.videoHandles, input.videoLease);
  deliver({ '1080p': 'http://127.0.0.1/synthetic' });
  await assert.rejects(acquiring, /Cancelled/);
  assert.equal(cacheCalls, 1);
  assert.equal(disposed, 1, 'late native lease is retired after theme switch');
  assert.equal(f.videoURLs(), 0);
  console.log(
    'PASS partial appearance vs strict package, deferred media hash/size/format/dimensions, ownership, reacquire and cancellation fences'
  );
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
