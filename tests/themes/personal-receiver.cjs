'use strict';
const assert = require('assert/strict'),
  http = require('http'),
  fs = require('fs'),
  crypto = require('crypto'),
  net = require('net'),
  vm = require('vm'),
  acorn = require('acorn');
const core = require('../../theme-receiver/core'),
  register = require('../../theme-receiver/register');
const image = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLttAAAAABJRU5ErkJggg==',
  'base64'
);
function envelope() {
  return {
    schemaVersion: 1,
    kind: 'wallpaper',
    source: 'phone',
    image: {
      mediaType: 'image/png',
      width: 1,
      height: 1,
      size: image.length,
      sha256: crypto.createHash('sha256').update(image).digest('hex'),
      data: image.toString('base64')
    },
    variants: []
  };
}
function request(s, path, method = 'GET', body, headers = {}) {
  return new Promise((resolve, reject) => {
    let r = http.request(
      {
        host: '127.0.0.1',
        port: s.port,
        path,
        method,
        headers: Object.assign(
          {
            Host: '127.0.0.1:' + s.port,
            'X-CYTV-PIN': s.pin,
            'Content-Type': 'application/json'
          },
          headers
        )
      },
      (res) => {
        let chunks = [];
        res.on('data', (x) => chunks.push(x));
        res.on('end', () =>
          resolve({
            code: res.statusCode,
            body: Buffer.concat(chunks).toString(),
            headers: res.headers
          })
        );
      }
    );
    r.on('error', reject);
    r.end(
      body === undefined
        ? undefined
        : typeof body === 'string'
          ? body
          : JSON.stringify(body)
    );
  });
}
const delay = (ms) => new Promise((r) => setTimeout(r, ms));
async function run() {
  for (const file of ['core', 'register', 'wallpaper-phone', 'wallpaper-heic'])
    acorn.parse(fs.readFileSync('theme-receiver/' + file + '.js', 'utf8'), {
      ecmaVersion: 5
    });
  const calls = [];
  let protocol = true;
  const context = {
    ThemePolicy: { limits: { envelopeBytes: 33 * 1024 * 1024 } },
    document: { querySelector: () => false },
    setTimeout,
    clearTimeout,
    Promise,
    Date,
    Number,
    Uint8Array,
    atob
  };
  context.PalmServiceBridge = function () {
    this.cancel = () => {};
    this.call = (url, raw) => {
      calls.push({ url, p: JSON.parse(raw) });
      this.onservicecallback(
        JSON.stringify(
          url.endsWith('Start')
            ? Object.assign(
                {
                  returnValue: true,
                  sessionId: 'abc',
                  pin: '123456',
                  addresses: ['192.168.1.2'],
                  port: 8879,
                  expiresAt: Date.now() + 500000
                },
                protocol ? { kind: 'wallpaper', wallpaperProtocol: 1 } : {}
              )
            : { returnValue: true }
        )
      );
    };
  };
  vm.runInNewContext(
    fs.readFileSync('launcher/theme-receiver.js', 'utf8'),
    context
  );
  assert.equal(
    (await context.ThemeReceiver.start({}, 'wallpaper')).wallpaperProtocol,
    1
  );
  assert.equal(calls[0].p.kind, 'wallpaper');
  protocol = false;
  await assert.rejects(
    context.ThemeReceiver.start({}, 'wallpaper'),
    /Wallpaper receiver unavailable/
  );
  assert(calls.some((c) => c.url.endsWith('Stop')));

  let released = 0;
  const r = core.create({ port: 0, hold: () => () => released++ });
  let s = await r.start({ kind: 'wallpaper' });
  try {
    assert.equal(s.kind, 'wallpaper');
    assert.equal(s.wallpaperProtocol, 1);
    assert.equal((await request(s, '/wallpaper')).code, 200);
    const worker = await request(s, '/wallpaper-heic-worker.js');
    assert.equal(worker.code, 200);
    assert.equal(worker.body, require('../../theme-receiver/wallpaper-heic')());
    assert.match(
      (await request(s, '/wallpaper-heic-license.txt')).body,
      /GNU LESSER GENERAL PUBLIC LICENSE/
    );
    for (const asset of [
      '/wallpaper-heic-worker.js',
      '/wallpaper-heic-license.txt'
    ]) {
      assert.equal(
        (
          await request(s, asset, 'GET', undefined, {
            Origin: 'http://evil.example'
          })
        ).code,
        403
      );
      assert.equal(
        (
          await request(s, asset, 'GET', undefined, {
            Origin: 'http://127.0.0.1:' + s.port
          })
        ).code,
        200
      );
    }
    assert.match((await request(s, '/wallpaper')).body, /image\/jpeg/);
    const capabilities = JSON.parse(
      (await request(s, '/v1/wallpaper-capabilities')).body
    );
    assert.equal(capabilities.wallpaperProtocol, 1);
    assert.equal(capabilities.videoCacheStorage.required, 0);
    assert(
      capabilities.videoCacheStorage.available === null ||
        capabilities.videoCacheStorage.available >= 0
    );
    assert.equal(
      (
        await request(s, '/v1/wallpaper-capabilities', 'GET', undefined, {
          'X-CYTV-PIN': 'bad'
        })
      ).code,
      403
    );
    assert.equal((await request(s, '/v1/theme', 'POST', {})).code, 404);
    const origin = { Origin: 'http://127.0.0.1:' + s.port };
    assert.equal(
      (
        await request(s, '/v1/wallpaper', 'POST', envelope(), {
          Origin: 'http://foreign.invalid'
        })
      ).code,
      403
    );
    assert.equal(
      (
        await request(s, '/v1/wallpaper', 'POST', envelope(), {
          Host: 'localhost:' + s.port
        })
      ).code,
      403
    );
    for (const mutate of [
      (v) => (v.source = 'evil'),
      (v) => (v.image.width = 1921),
      (v) => (v.variants = [{}]),
      (v) => v.image.size++,
      (v) => (v.image.sha256 = '0'.repeat(64)),
      (v) => (v.image.data = 'AB=='),
      (v) => (v.image.mediaType = 'video/mp4'),
      (v) =>
        (v.image.data = Buffer.alloc(2 * 1024 * 1024 + 1).toString('base64')),
      (v) => {
        v.source = 'cytv';
      }
    ]) {
      let v = envelope();
      mutate(v);
      assert.equal(
        (await request(s, '/v1/wallpaper', 'POST', v, origin)).code,
        400
      );
    }
    assert.equal(
      (await request(s, '/v1/wallpaper', 'POST', envelope(), origin)).code,
      202
    );
    assert.equal(r.status(s.sessionId).state, 'received');
    assert.deepEqual(
      JSON.parse(Buffer.from(r.read(s.sessionId, 0).data, 'base64').toString()),
      envelope()
    );
    assert.equal(released, 0);
  } finally {
    await r.stop(s.sessionId);
  }
  assert.equal(released, 1);
  s = await r.start({ kind: 'wallpaper' });
  try {
    const v = envelope();
    v.source = 'cytv';
    const video = fs.readFileSync('tests/themes/fixtures/wallpaper-blue.mp4');
    v.variants = [
      {
        quality: '1080p',
        mediaType: 'video/mp4',
        width: 1920,
        height: 1080,
        size: video.length,
        sha256: crypto.createHash('sha256').update(video).digest('hex'),
        data: video.toString('base64')
      }
    ];
    assert.equal((await request(s, '/v1/wallpaper', 'POST', v)).code, 202);
    assert.equal(r.status(s.sessionId).state, 'received');
  } finally {
    await r.stop(s.sessionId);
  }
  s = await r.start();
  try {
    assert.equal((await request(s, '/wallpaper')).code, 404);
    assert.equal((await request(s, '/wallpaper-heic-worker.js')).code, 404);
    assert.equal((await request(s, '/wallpaper-heic-license.txt')).code, 404);
    assert.equal((await request(s, '/v1/wallpaper-capabilities')).code, 404);
    assert.equal(
      (
        await request(
          s,
          '/v1/theme',
          'POST',
          {},
          { Origin: 'http://127.0.0.1:' + s.port }
        )
      ).code,
      403
    );
  } finally {
    await r.stop(s.sessionId);
  }
  await assert.rejects(r.start({ kind: 'invalid' }), /invalid-request/);
  const exp = core.create({ port: 0, ttlMs: 40, hold: () => () => released++ });
  s = await exp.start({ kind: 'wallpaper' });
  let socket = net.connect(s.port, '127.0.0.1');
  await new Promise((resolve) => socket.once('connect', resolve));
  const closed = new Promise((resolve) => socket.once('close', resolve));
  await delay(70);
  await closed;
  assert.throws(() => exp.status(s.sessionId));
  assert.equal(released, 4);
  const wrong = core.create({ port: 0, maxWrongPins: 1 });
  s = await wrong.start({ kind: 'wallpaper' });
  await request(s, '/v1/wallpaper-capabilities', 'GET', undefined, {
    'X-CYTV-PIN': 'bad'
  });
  await delay(10);
  assert.throws(() => wrong.status(s.sessionId));
  const methods = {};
  register(
    { register: (name, fn) => (methods[name] = fn) },
    { appId: 'com.test', port: 0 }
  );
  const call = (name, payload) =>
    new Promise((resolve) =>
      methods[name]({
        payload,
        ls2Message: { applicationID: () => 'com.test' },
        respond: resolve
      })
    );
  s = await call('themeReceiverStart', { kind: 'wallpaper' });
  assert.equal(s.wallpaperProtocol, 1);
  await call('themeReceiverStop', { sessionId: s.sessionId });
  console.log(
    'PASS personal receiver mode, real HTTP, origin/PIN/size/hash boundaries, read, expiry and holds'
  );
}
module.exports = { envelope, request };
if (require.main === module)
  run().catch((e) => {
    console.error(e);
    process.exit(1);
  });
