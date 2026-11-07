'use strict';
const assert = require('node:assert/strict');
const { createRenewal, parseRemaining } = require('../renewal-service/renewal');
const tests = [];
function test(name, fn) {
  tests.push([name, fn]);
}
function fixture(responses, options) {
  let time = 100000000,
    token = 'secretToken123',
    state = {};
  const calls = [],
    saved = [];
  const io = {
    now: () => time,
    readToken: async () => token,
    load: async () => state,
    save: async (value) => {
      state = JSON.parse(JSON.stringify(value));
      saved.push(state);
    },
    request: async (operation, value) => {
      calls.push([operation, value]);
      const response = responses.shift();
      if (response instanceof Error) throw response;
      return response;
    }
  };
  return {
    io,
    calls,
    saved,
    engine: createRenewal(io, options),
    advance: (ms) => {
      time += ms;
    },
    token: (v) => {
      token = v;
    }
  };
}
const success = (hours) => ({ result: 'success', errorMsg: hours + ':00:00' });
test('strict countdown parsing', () => {
  assert.equal(parseRemaining(success(999)), 999 * 3600);
  for (const value of [
    'GNL',
    '1:60:00',
    '-1:00:00',
    '1:00:60',
    '999999999999:00:00'
  ])
    assert.equal(parseRemaining({ result: 'success', errorMsg: value }), null);
});
test('disabled by default: no token read or network', async () => {
  const f = fixture([]);
  f.io.readToken = () => {
    throw Error('must not read');
  };
  assert.equal((await f.engine.run()).status, 'disabled');
  assert.equal(f.calls.length, 0);
});
test('missing or malformed token never reaches network', async () => {
  for (const value of ['', 'a&other=1', 'x'.repeat(4097)]) {
    const f = fixture([], { enabled: true });
    f.token(value);
    assert.equal((await f.engine.run()).status, 'unavailable');
    assert.equal(f.calls.length, 0);
  }
});
test('healthy session checks once and persists cooldown across restart', async () => {
  const f = fixture([success(900)], { enabled: true });
  assert.equal((await f.engine.run()).status, 'healthy');
  assert.equal(
    (await createRenewal(f.io, { enabled: true }).run()).status,
    'cooldown'
  );
  assert.equal(f.calls.length, 1);
});
test('check-reset-check verifies a real increase', async () => {
  const f = fixture(
    [success(100), { result: 'success', errorMsg: 'GNL' }, success(999)],
    { enabled: true }
  );
  assert.equal((await f.engine.run()).status, 'renewed');
  assert.deepEqual(
    f.calls.map((x) => x[0]),
    ['check', 'reset', 'check']
  );
  assert.ok(!JSON.stringify(f.saved).includes('secretToken123'));
});
test('success without increase is not called renewed', async () => {
  const f = fixture([success(100), { result: 'success' }, success(100)], {
    enabled: true
  });
  assert.equal((await f.engine.run()).status, 'unverified');
});
test('offline failures are sanitized and rate limited', async () => {
  const f = fixture([Error('URL contains secretToken123')], { enabled: true });
  assert.equal((await f.engine.run()).status, 'retry');
  assert.equal((await f.engine.run()).status, 'cooldown');
  assert.ok(!JSON.stringify(f.saved).includes('secretToken123'));
});
test('concurrent triggers execute only once', async () => {
  const f = fixture([success(900)], { enabled: true });
  await Promise.all([f.engine.run(), f.engine.run(), f.engine.run()]);
  assert.equal(f.calls.length, 1);
});
test('rotation before reset prevents renewing stale token', async () => {
  const f = fixture([success(100)], { enabled: true });
  let n = 0;
  f.io.readToken = async () => (++n === 1 ? 'first' : 'second');
  assert.equal((await f.engine.run()).status, 'session-changed');
  assert.equal(f.calls.length, 1);
});
test('failed persistence stops before any network request', async () => {
  const f = fixture([], { enabled: true });
  f.io.save = async () => {
    throw Error('disk');
  };
  assert.equal((await f.engine.run()).status, 'storage-error');
  assert.equal(f.calls.length, 0);
});
test('clock rollback does not bypass cooldown', async () => {
  const f = fixture([success(900)], { enabled: true });
  await f.engine.run();
  f.advance(-50000000);
  assert.equal((await f.engine.run()).status, 'cooldown');
});
test('exhausted retries back off for a day', async () => {
  const f = fixture([Error(), Error(), Error(), Error()], { enabled: true });
  for (const ms of [0, 15 * 60000, 60 * 60000, 6 * 3600000]) {
    f.advance(ms);
    await f.engine.run();
  }
  f.advance(6 * 3600000);
  assert.equal((await f.engine.run()).status, 'cooldown');
  assert.equal(f.calls.length, 4);
});
(async () => {
  for (const [name, fn] of tests) {
    await fn();
    console.log('PASS ' + name);
  }
  console.log(tests.length + ' tests passed');
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
