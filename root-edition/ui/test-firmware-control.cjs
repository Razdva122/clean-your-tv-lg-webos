const assert = require('node:assert/strict');
const create = require('./root-firmware-control');
function fixture(options) {
  options = options || {};
  let enabled = !!options.enabled;
  const calls = [];
  const api = create((uri, payload, timeout) => {
    const method = uri.split('/').pop();
    calls.push({ uri, method, payload, timeout });
    if (options.hang && method === 'setConfiguration')
      return new Promise((resolve) => {
        options.release = resolve;
      });
    if (options.failRead && method === 'getConfiguration')
      return Promise.reject(Error('secret remote text'));
    if (method === 'setConfiguration') {
      if (!options.ignoreWrite) enabled = payload.blockUpdates;
      if (options.failWrite)
        return Promise.reject(Error('secret mutation error'));
    }
    return Promise.resolve({
      returnValue: true,
      root: options.root !== false,
      blockUpdates: enabled
    });
  });
  return { api, calls };
}
(async () => {
  let f = fixture({ enabled: true });
  assert.equal((await f.api.get()).enabled, true);
  f = fixture();
  let reply = await f.api.set(true, false);
  assert.equal(reply.returnValue, true);
  assert.equal(reply.enabled, true);
  assert.deepEqual(
    f.calls
      .filter((c) => c.method === 'setConfiguration')
      .map((c) => c.payload),
    [{ blockUpdates: true }]
  );
  assert(
    f.calls.every(
      (c) =>
        c.uri.startsWith('luna://org.webosbrew.hbchannel.service/') &&
        c.timeout === 10000
    )
  );
  f = fixture({ enabled: true });
  assert.equal((await f.api.set(false, true)).enabled, false);
  for (const args of [
    [undefined, false],
    ['true', false],
    [true, undefined],
    [{}, false]
  ]) {
    f = fixture();
    assert.equal((await f.api.set(...args)).returnValue, false);
    assert.equal(f.calls.length, 0);
  }
  for (const options of [{ root: false }, { failRead: true }]) {
    f = fixture(options);
    reply = await f.api.set(true, false);
    assert.equal(reply.returnValue, false);
    assert(!f.calls.some((c) => c.method === 'setConfiguration'));
    assert(!JSON.stringify(reply).includes('secret'));
  }
  f = fixture({ enabled: true });
  reply = await f.api.set(false, false);
  assert.equal(reply.errorCode, 'changed');
  assert(!f.calls.some((c) => c.method === 'setConfiguration'));
  f = fixture({ ignoreWrite: true });
  assert.equal((await f.api.set(true, false)).returnValue, false);
  f = fixture({ failWrite: true });
  reply = await f.api.set(true, false);
  assert.equal(reply.errorCode, 'unconfirmed');
  assert.equal(reply.status.enabled, true);
  assert(!JSON.stringify(reply).includes('secret'));
  const options = { hang: true };
  f = fixture(options);
  const pending = f.api.set(true, false);
  await new Promise((r) => setImmediate(r));
  assert.equal((await f.api.set(false, false)).errorCode, 'busy');
  options.release({ returnValue: false });
  await pending;
  f = fixture({ enabled: true });
  await f.api.set(true, true);
  assert(!f.calls.some((c) => c.method === 'setConfiguration'));
  for (const [bad, code] of [
    [null, 'unavailable'],
    [{}, 'unavailable'],
    [{ returnValue: true, root: true }, 'unsupported'],
    [{ returnValue: false, root: true, blockUpdates: false }, 'unavailable']
  ]) {
    const api = create(() => Promise.resolve(bad));
    assert.equal((await api.get()).errorCode, code);
  }
  const failures = [
    [
      {
        returnValue: false,
        errorText:
          'Denied methods call \"getConfiguration\" for category \"/\" private-data'
      },
      'permission-denied'
    ],
    [
      { returnValue: false, errorText: 'Service does not exist private-data' },
      'service-unavailable'
    ],
    [{ returnValue: true, root: false, blockUpdates: false }, 'not-root'],
    [{ returnValue: true, root: true, blockUpdates: 'false' }, 'unsupported']
  ];
  for (const [value, code] of failures) {
    const calls = [],
      api = create((uri) => {
        calls.push(uri);
        return Promise.resolve(value);
      });
    assert.deepEqual(await api.get(), { returnValue: false, errorCode: code });
    assert.equal((await api.set(true, false)).errorCode, code);
    assert(
      !calls.some((uri) => uri.endsWith('/setConfiguration')),
      'failed capability read must not mutate Homebrew'
    );
    assert(!JSON.stringify(await api.get()).includes('private-data'));
  }
  for (const [message, code] of [
    ['Response timed out. Check status before retrying.', 'timeout'],
    ['Invalid service response', 'unsupported'],
    ['Denied method call private-data', 'permission-denied']
  ]) {
    const api = create(() => Promise.reject(Error(message)));
    assert.deepEqual(await api.get(), { returnValue: false, errorCode: code });
  }
  const injected = create(() =>
    Promise.resolve({ returnValue: false, firmwareCode: 'private-data' })
  );
  assert.deepEqual(await injected.get(), {
    returnValue: false,
    errorCode: 'unavailable'
  });
  console.log(
    'PASS firmware control: Homebrew-only partial writes, strict values, readback, uncertainty, concurrency and stale state'
  );
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
