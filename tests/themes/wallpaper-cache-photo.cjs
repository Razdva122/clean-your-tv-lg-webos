'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const http = require('node:http');
const crypto = require('node:crypto');
const vm = require('node:vm');
const cache = require('../../theme-receiver/wallpaper-cache');
const png = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=',
  'base64'
);
const jpeg = fs.readFileSync(
  path.resolve(__dirname, '../../themes/ribbon/assets/preview.jpg')
);
function variant(bytes, mediaType) {
  return {
    quality: 'photo',
    mediaType,
    size: bytes.length,
    sha256: crypto.createHash('sha256').update(bytes).digest('hex')
  };
}
function get(url, method = 'GET', headers = {}) {
  return new Promise((resolve, reject) => {
    const req = http.request(url, { method, headers }, (res) => {
      const chunks = [];
      res.on('data', (b) => chunks.push(b));
      res.on('end', () =>
        resolve({
          status: res.statusCode,
          headers: res.headers,
          body: Buffer.concat(chunks)
        })
      );
    });
    req.on('error', reject);
    req.end();
  });
}
async function put(c, bytes, mediaType) {
  const session = await c.start({ variants: [variant(bytes, mediaType)] });
  for (let offset = 0; offset < bytes.length; offset += 49152)
    c.write({
      sessionId: session.sessionId,
      quality: 'photo',
      offset,
      data: bytes.subarray(offset, offset + 49152).toString('base64')
    });
  return session;
}
(async () => {
  const directory = fs.mkdtempSync(
    path.join(os.tmpdir(), 'screensaver-photo-cache-')
  );
  const c = cache.create({ directory });
  const active = [];
  try {
    for (const [bytes, mediaType, extension] of [
      [png, 'image/png', 'png'],
      [jpeg, 'image/jpeg', 'jpg']
    ]) {
      const session = await put(c, bytes, mediaType);
      active.push(session);
      const value = await c.commit(session);
      assert.match(
        value.handles.photo,
        new RegExp(
          '^http://127\\.0\\.0\\.1:\\d+/[a-f0-9]{32}/photo\\.' + extension + '$'
        )
      );
      let response = await get(value.handles.photo);
      assert.equal(response.status, 200);
      assert.equal(response.headers['content-type'], mediaType);
      assert.deepEqual(response.body, bytes);
      response = await get(value.handles.photo, 'GET', { Range: 'bytes=1-4' });
      assert.equal(response.status, 206);
      assert.deepEqual(response.body, bytes.subarray(1, 5));
      assert.equal((await get(value.handles.photo, 'HEAD')).body.length, 0);
      assert.equal(
        (
          await get(
            value.handles.photo.replace('/photo.' + extension, '/../photo.png')
          )
        ).status,
        404
      );
      c.stop(session);
      assert.equal(
        fs.readdirSync(directory).length,
        0,
        'photo lease cleanup removes its fixed extension'
      );
    }
    for (const change of [
      { mediaType: undefined },
      { mediaType: 'image/svg+xml' },
      { mediaType: 'image/jpeg;evil' },
      { size: 2097153 },
      { quality: '../photo' }
    ]) {
      await assert.rejects(
        c.start({ variants: [{ ...variant(png, 'image/png'), ...change }] }),
        /invalid variant/
      );
    }
    const maximum = await c.start({
      variants: [{ ...variant(png, 'image/png'), size: 2097152 }]
    });
    active.push(maximum);
    assert.ok(
      fs.existsSync(path.join(directory, maximum.sessionId, 'photo.png')),
      'exact 2 MiB bound remains admissible'
    );
    c.stop(maximum);
    for (const [bytes, mediaType] of [
      [Buffer.from('<svg>not an image</svg>'), 'image/png'],
      [png, 'image/jpeg'],
      [jpeg, 'image/png']
    ]) {
      const session = await put(c, bytes, mediaType);
      active.push(session);
      await assert.rejects(c.commit(session), /photo/);
      assert.equal(
        fs.readdirSync(directory).length,
        0,
        'failed photo admission releases all files'
      );
    }
    const corrupt = await c.start({ variants: [variant(png, 'image/png')] });
    active.push(corrupt);
    c.write({
      sessionId: corrupt.sessionId,
      quality: 'photo',
      offset: 0,
      data: Buffer.alloc(png.length).toString('base64')
    });
    await assert.rejects(c.commit(corrupt), /hash/);
  } finally {
    active.forEach((s) => c.stop(s));
    fs.rmSync(directory, { recursive: true, force: true });
  }

  // Controlled lease time proves successful authenticated requests extend TTL;
  // malformed ranges, wrong paths and forbidden origins must not extend it.
  let time = Date.now();
  const timers = new Map();
  let timerId = 0;
  class Clock extends Date {
    constructor(...args) {
      super(...(args.length ? args : [time]));
    }
    static now() {
      return time;
    }
  }
  const module = { exports: {} };
  vm.runInNewContext(
    fs.readFileSync(
      require.resolve('../../theme-receiver/wallpaper-cache'),
      'utf8'
    ),
    {
      module,
      exports: module.exports,
      require,
      process,
      Buffer,
      Promise,
      Date: Clock,
      setTimeout(fn, ms) {
        timers.set(++timerId, { fn, at: time + ms });
        return timerId;
      },
      clearTimeout(id) {
        timers.delete(id);
      }
    }
  );
  function advance(ms) {
    time += ms;
    for (const [id, timer] of [...timers])
      if (timer.at <= time) {
        timers.delete(id);
        timer.fn();
      }
  }
  const ttlDir = fs.mkdtempSync(
    path.join(os.tmpdir(), 'screensaver-photo-ttl-')
  );
  const leases = module.exports.create({ directory: ttlDir, ttlMs: 100 });
  let session;
  try {
    session = await put(leases, png, 'image/png');
    const url = (await leases.commit(session)).handles.photo;
    advance(60);
    assert.equal((await get(url, 'HEAD')).status, 200);
    advance(60);
    assert.equal((await get(url)).status, 200);
    advance(60);
    assert.equal((await get(url, 'HEAD')).status, 200);
    advance(60);
    assert.equal((await get(url, 'GET', { Range: 'bytes=999-' })).status, 416);
    assert.equal(
      (await get(url, 'GET', { Origin: 'https://evil.invalid' })).status,
      403
    );
    assert.equal(
      (await get(url.replace('/photo.png', '/unknown.png'))).status,
      404
    );
    advance(41);
    assert.throws(() => leases.keepAlive(session), /unavailable|expired/);
    assert.equal(fs.readdirSync(ttlDir).length, 0);
    assert.equal(timers.size, 0);
    const orphan = path.join(ttlDir, 'a'.repeat(48));
    fs.mkdirSync(orphan, 0o700);
    fs.writeFileSync(path.join(orphan, 'photo.jpg'), jpeg, { mode: 0o600 });
    fs.writeFileSync(path.join(orphan, 'photo.png'), png, { mode: 0o600 });
    fs.utimesSync(orphan, new Date(0), new Date(0));
    session = await leases.start({ variants: [variant(png, 'image/png')] });
    assert.equal(
      fs.existsSync(orphan),
      false,
      'stale recovery removes both safe photo extensions'
    );
    leases.stop(session);
  } finally {
    if (session) leases.stop(session);
    fs.rmSync(ttlDir, { recursive: true, force: true });
  }
  console.log(
    'PASS personal photo cache: JPEG/PNG bounds, signatures, digest, fixed routes, authenticated request TTL and cleanup'
  );
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
