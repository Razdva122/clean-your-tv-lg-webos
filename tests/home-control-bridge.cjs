const assert = require('node:assert/strict'),
  fs = require('fs'),
  os = require('os'),
  path = require('path');
const create = require('../renewal-service/home-control');
const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'cytv-control-'));
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
