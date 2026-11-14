const assert = require('node:assert/strict'),
  fs = require('fs'),
  os = require('os'),
  path = require('path');
const storage = require('../native/app/state-permissions');
const create = require('./storage-fixture.cjs').load(
  path.resolve('renewal-service/home-control.js'),
  storage
);
const dir = fs.realpathSync(
  fs.mkdtempSync(path.join(os.tmpdir(), 'cytv-control-'))
);
fs.chmodSync(dir, 0o2770);
if ((fs.statSync(dir).mode & 0o7777) !== 0o2770) {
  const inode = fs.statSync(dir).ino;
  for (const method of ['lstatSync', 'fstatSync', 'statSync']) {
    const original = fs[method];
    fs[method] = function (...args) {
      const stat = original.apply(fs, args);
      if (stat.ino === inode) stat.mode |= 0o2000;
      return stat;
    };
  }
}
(async () => {
  try {
    let now = 0,
      queue = [],
      seq = 0;
    const send = create(fs, dir, {
      now: () => now,
      later: (f) => queue.push(f),
      nonce: () => String(++seq).padStart(32, '0')
    });
    fs.writeFileSync(
      path.join(dir, 'home-response.json'),
      JSON.stringify({ id: 'old', returnValue: true, enabled: false })
    );
    let pending = send('setHomeControl', { enabled: false });
    let req = JSON.parse(
      fs.readFileSync(path.join(dir, 'home-request.json'), 'utf8')
    );
    assert.equal(req.enabled, false);
    assert.equal(req.method, 'setHomeControl');
    assert.equal(
      (await send('openLGHome', {})).returnValue,
      false,
      'serialize commands'
    );
    fs.writeFileSync(
      path.join(dir, 'home-response.json'),
      JSON.stringify({ id: req.id, returnValue: true, enabled: false })
    );
    queue.shift()();
    assert.equal((await pending).enabled, false);
    pending = send('openLGHome', {});
    now = 5001;
    queue.shift()();
    assert.equal(
      (await pending).returnValue,
      false,
      'stale responses cannot confirm a new command'
    );
    assert.equal(
      (await send('setHomeControl', { enabled: 'false' })).returnValue,
      false
    );
    assert.equal((await send('shell', { command: 'noop' })).returnValue, false);
    const input = create(fs, dir, {
      inputs: true,
      now: () => now,
      later: (f) => queue.push(f),
      nonce: () => String(++seq).padStart(32, '0')
    });
    pending = input('inputStatus', {});
    req = JSON.parse(
      fs.readFileSync(path.join(dir, 'input-request.json'), 'utf8')
    );
    const catalog = create(fs, dir, {
      catalog: true,
      now: () => now,
      later: (f) => queue.push(f),
      nonce: () => String(++seq).padStart(32, '0')
    });
    const catalogPending = catalog('listApps', {}),
      catalogReq = JSON.parse(
        fs.readFileSync(path.join(dir, 'catalog-request.json'), 'utf8')
      );
    assert.equal(catalogReq.method, 'listApps');
    storage.atomicRecord(
      dir,
      'catalog-response',
      JSON.stringify({
        id: catalogReq.id,
        returnValue: true,
        apps: [{ id: 'org.example', title: 'Example' }]
      })
    );
    queue.pop()();
    assert.equal((await catalogPending).apps[0].id, 'org.example');
    for (const name of ['catalog-request.json', 'catalog-response.json']) {
      const stat = fs.statSync(path.join(dir, name));
      assert.equal(stat.mode & 0o7777, 0o660);
      assert.equal(stat.gid, fs.statSync(dir).gid);
    }
    for (const method of ['homeStatus', 'setHomeControl', 'inputStatus'])
      assert.equal(
        (await catalog(method, {})).returnValue,
        false,
        'catalog channel is read-only'
      );
    assert.equal(
      (await catalog('listApps', { uri: 'PRIVATE' })).returnValue,
      false,
      'catalog query accepts no caller-selected arguments'
    );
    const homePending = send('homeStatus', {}),
      homeReq = JSON.parse(
        fs.readFileSync(path.join(dir, 'home-request.json'), 'utf8')
      );
    fs.writeFileSync(
      path.join(dir, 'home-response.json'),
      JSON.stringify({ id: homeReq.id, returnValue: true, enabled: true })
    );
    queue.pop()();
    assert.equal(
      (await homePending).enabled,
      true,
      'metadata cannot occupy Home settings channel'
    );
    assert.equal(
      req.method,
      'inputStatus',
      'paired input reads must use the existing same-package channel'
    );
    assert(!('uri' in req));
    fs.writeFileSync(
      path.join(dir, 'input-response.json'),
      JSON.stringify({
        id: req.id,
        returnValue: true,
        devices: [{ appId: 'com.webos.app.hdmi3', connected: true }]
      })
    );
    queue.shift()();
    assert.equal((await pending).devices[0].connected, true);
    assert.equal(
      (await input('inputStatus', { uri: 'PRIVATE' })).returnValue,
      false,
      'input reads cannot choose a target or add payload fields'
    );
    assert.equal(
      (await input('setHomeControl', { enabled: false })).returnValue,
      false,
      'metadata channel cannot mutate Home'
    );
    pending = send('presentationContext', {});
    req = JSON.parse(
      fs.readFileSync(path.join(dir, 'home-request.json'), 'utf8')
    );
    assert.equal(
      req.method,
      'presentationContext',
      'presentation context uses the existing HOME channel'
    );
    assert.equal(req.expires, now + 5000);
    assert.deepEqual(Object.keys(req).sort(), ['expires', 'id', 'method']);
    const contextId = req.id;
    fs.writeFileSync(
      path.join(dir, 'home-response.json'),
      JSON.stringify({
        id: req.id,
        returnValue: true,
        eligible: false,
        content: false,
        generation: 7,
        observedAgeMs: 0
      })
    );
    queue.shift()();
    assert.equal((await pending).content, false);
    pending = send('presentationDismissed', { generation: 7 });
    req = JSON.parse(
      fs.readFileSync(path.join(dir, 'home-request.json'), 'utf8')
    );
    assert.equal(req.method, 'presentationDismissed');
    assert.equal(req.generation, 7);
    assert.deepEqual(Object.keys(req).sort(), [
      'expires',
      'generation',
      'id',
      'method'
    ]);
    let completed = false;
    pending.then(() => {
      completed = true;
    });
    fs.writeFileSync(
      path.join(dir, 'home-response.json'),
      JSON.stringify({ id: contextId, returnValue: true, dismissed: true })
    );
    queue.shift()();
    await Promise.resolve();
    assert.equal(
      completed,
      false,
      'old context response cannot confirm dismissal'
    );
    fs.writeFileSync(
      path.join(dir, 'home-response.json'),
      JSON.stringify({ id: req.id, returnValue: true, dismissed: true })
    );
    queue.shift()();
    assert.equal((await pending).dismissed, true);
    const before = fs.readFileSync(path.join(dir, 'home-request.json'), 'utf8');
    for (const payload of [undefined, null, [], 1, '', { extra: true }])
      assert.equal(
        (await send('presentationContext', payload)).returnValue,
        false,
        'context requires exactly an empty object'
      );
    for (const generation of [
      undefined,
      null,
      true,
      -1,
      1.5,
      NaN,
      Infinity,
      Number.MAX_SAFE_INTEGER + 1,
      '7',
      {},
      []
    ])
      assert.equal(
        (await send('presentationDismissed', { generation })).returnValue,
        false,
        'dismissal generation must be a safe nonnegative integer'
      );
    for (const payload of [{}, { generation: 0, extra: true }, null, []])
      assert.equal(
        (await send('presentationDismissed', payload)).returnValue,
        false,
        'dismissal has exactly one key'
      );
    for (const method of ['presentationContext', 'presentationDismissed'])
      assert.equal(
        (
          await input(
            method,
            method === 'presentationContext' ? {} : { generation: 0 }
          )
        ).returnValue,
        false,
        'input metadata cannot issue presentation commands'
      );
    assert.equal(
      fs.readFileSync(path.join(dir, 'home-request.json'), 'utf8'),
      before,
      'invalid or input-channel commands perform no HOME writes'
    );
    const mutable = { generation: 0 },
      snapshot = create(fs, dir, {
        now: () => now,
        later: (f) => queue.push(f),
        nonce: () => {
          mutable.generation = 99;
          return String(++seq).padStart(32, '0');
        }
      });
    pending = snapshot('presentationDismissed', mutable);
    req = JSON.parse(
      fs.readFileSync(path.join(dir, 'home-request.json'), 'utf8')
    );
    assert.equal(
      req.generation,
      0,
      'capture validated generation before nonce or later mutation'
    );
    fs.writeFileSync(
      path.join(dir, 'home-response.json'),
      JSON.stringify({ id: req.id, returnValue: true, dismissed: true })
    );
    queue.shift()();
    assert.equal((await pending).dismissed, true);
    pending = send('presentationDismissed', {
      generation: Number.MAX_SAFE_INTEGER
    });
    req = JSON.parse(
      fs.readFileSync(path.join(dir, 'home-request.json'), 'utf8')
    );
    assert.equal(req.generation, Number.MAX_SAFE_INTEGER);
    assert.equal(req.expires, now + 5000);
    fs.writeFileSync(
      path.join(dir, 'home-response.json'),
      JSON.stringify({ id: req.id, returnValue: true, dismissed: true })
    );
    queue.shift()();
    assert.equal((await pending).dismissed, true);
    const missing = await create(fs, path.join(dir, 'missing'))(
      'homeStatus',
      {}
    );
    assert.equal(missing.diagnostic.code, 'ENOENT');
    assert.equal(missing.channelMode, undefined);
    // Exercise both requests on a shared directory whose original mode
    // cannot be restored by either unprivileged runtime.
    const drifted = fs.mkdtempSync(
      path.join(path.dirname(dir), 'cytv-drifted-')
    );
    const privateDir = path.join(drifted, '.private');
    const originalChmod = fs.fchmodSync;
    const stats = ['lstatSync', 'fstatSync', 'statSync'].map((method) => [
      method,
      fs[method]
    ]);
    let privateInode;
    let retainSetgid = false;
    try {
      fs.chmodSync(drifted, 0o775);
      for (const [method, original] of stats) {
        fs[method] = function (...args) {
          const stat = original.apply(fs, args);
          if (stat.ino === privateInode && retainSetgid) stat.mode |= 0o2000;
          return stat;
        };
      }
      fs.fchmodSync = function (fd, mode) {
        assert.equal(
          fs.fstatSync(fd).ino,
          fs.statSync(privateDir).ino,
          'only chmod the private child'
        );
        assert.equal(mode, 0o2770);
        // Model a filesystem that does not retain setgid on chmod.
        originalChmod(fd, mode & ~0o2000);
      };
      assert.throws(
        () => storage.atomicRecord(drifted, 'input-request', '{}'),
        /unsafe-storage/
      );
      assert.deepEqual(fs.readdirSync(privateDir), []);
      fs.chmodSync(privateDir, 0o700);
      fs.fchmodSync = function (fd, mode) {
        const stat = fs.fstatSync(fd);
        if (!stat.isDirectory()) return originalChmod(fd, mode);
        assert.equal(
          stat.ino,
          fs.statSync(privateDir).ino,
          'only chmod the private child'
        );
        assert.equal(mode, 0o2770);
        originalChmod(fd, mode);
        privateInode = stat.ino;
        retainSetgid = true;
      };
      fs.writeFileSync(
        path.join(drifted, 'home-request.json'),
        '{"stale":true}'
      );
      assert.throws(
        () => storage.readChannelRecord(drifted, 'home-request'),
        /unsafe-storage/
      );
      for (const method of ['homeStatus', 'listApps']) {
        const catalog = method === 'listApps';
        const prefix = catalog ? 'catalog' : 'home';
        const call = create(fs, drifted, {
          catalog,
          now: () => 1,
          later: (fn) => queue.push(fn)
        });
        const reply = call(method, {});
        assert.equal(fs.statSync(drifted).mode & 0o7777, 0o775);
        assert.equal(fs.statSync(privateDir).mode & 0o7777, 0o2770);
        const request = JSON.parse(
          storage.readChannelRecord(drifted, prefix + '-request')
        );
        assert.equal(request.method, method);
        storage.atomicRecord(
          drifted,
          prefix + '-response',
          JSON.stringify({
            id: request.id,
            returnValue: true,
            enabled: true,
            apps: [{ id: 'new' }]
          })
        );
        queue.pop()();
        assert.equal((await reply).returnValue, true);
      }
      assert.deepEqual(
        JSON.parse(fs.readFileSync(path.join(drifted, 'home-request.json'))),
        { stale: true }
      );
      assert.equal(
        fs.existsSync(path.join(drifted, 'catalog-request.json')),
        false
      );
      fs.rmSync(privateDir, { recursive: true });
      fs.symlinkSync(dir, privateDir);
      assert.throws(
        () => storage.atomicRecord(drifted, 'catalog-request', '{}'),
        /unsafe-storage/
      );
      assert.throws(
        () => storage.readChannelRecord(drifted, 'catalog-request'),
        /unsafe-storage/
      );
    } finally {
      fs.fchmodSync = originalChmod;
      for (const [method, original] of stats) fs[method] = original;
      fs.rmSync(drifted, { recursive: true });
    }
    const rejected = fs.mkdtempSync(
      path.join(path.dirname(dir), 'cytv-rejected-')
    );
    try {
      for (const mode of [0o770, 0o777]) {
        fs.chmodSync(rejected, mode);
        for (const method of ['homeStatus', 'listApps']) {
          const call = create(fs, rejected, { catalog: method === 'listApps' });
          const reply = await call(method, {});
          assert.equal(reply.returnValue, false);
          assert.equal(reply.diagnostic.code, 'INVALID_STATE');
          assert.equal(reply.diagnostic.operation, 'write');
          assert.equal(reply.channelMode, mode);
          assert.deepEqual(fs.readdirSync(rejected), []);
        }
      }
      let forwarded = 0;
      const fallback = create(fs, rejected, {
        fallback(method, payload, expires, done) {
          forwarded++;
          assert.equal(method, 'homeStatus');
          assert.deepEqual(payload, {});
          done({ returnValue: true, enabled: true });
        }
      });
      assert.equal((await fallback('homeStatus', {})).enabled, true);
      assert.equal(forwarded, 1);
      assert.deepEqual(fs.readdirSync(rejected), []);
    } finally {
      fs.rmSync(rejected, { recursive: true });
    }
    console.log(
      'PASS same-package Home broker: fixed commands, serialization, correlated response, timeout and validation'
    );
  } finally {
    fs.rmSync(dir, { recursive: true });
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
