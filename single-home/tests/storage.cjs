'use strict';
const assert = require('node:assert/strict');
const test = require('node:test');
const crypto = require('node:crypto');
const createStore = require('../service/storage');

const owner = 'io.github.razdva122.cytvhomepilot.service';
const kind = owner + '.store:1';
function platform() {
  const calls = [],
    handles = new Map();
  let row = null,
    master = null,
    denied = '';
  function answer(uri, payload) {
    const name = uri.split('/').pop();
    if (name === denied)
      return {
        returnValue: false,
        errorCode: -3963,
        errorText: 'private-fixture'
      };
    switch (name) {
      case 'putKind':
        assert.deepEqual(payload, { id: kind, owner, private: true });
        return {};
      case 'find':
        assert.equal(payload.query.from, kind);
        return { results: row ? [structuredClone(row)] : [] };
      case 'put': {
        const obj = payload.objects[0];
        assert.equal(obj._kind, kind);
        if (row) assert.equal(obj._rev, row._rev);
        row = {
          ...structuredClone(obj),
          _id: 'generatedId',
          _rev: (row ? row._rev : 0) + 1
        };
        return { results: [{ id: row._id, rev: row._rev }] };
      }
      case 'generateKey':
        assert.deepEqual(payload.params.mode, ['GCM']);
        assert.equal(payload.params.size, 256);
        assert.equal(payload.params.mac_length, undefined);
        if (master) return { returnValue: false, errorCode: -10002 };
        master = crypto.randomBytes(32);
        return {};
      case 'begin': {
        assert.equal(payload.params.type, 'AES');
        assert.equal(payload.params.mode[0], 'GCM');
        assert.equal(payload.params.mac_length, '128');
        const encrypt = payload.params.purpose[0] === 'encrypt';
        const iv = encrypt
          ? crypto.randomBytes(12)
          : Buffer.from(payload.params.iv, 'base64');
        const handle = String(calls.length);
        handles.set(handle, { encrypt, iv });
        return { handle, iv: iv.toString('base64') };
      }
      case 'finish': {
        const task = handles.get(payload.handle);
        const data = Buffer.from(payload.data, 'base64'),
          aad = Buffer.from(payload.aad, 'base64');
        assert.ok(aad.length);
        assert.ok(task);
        try {
          const cipher = task.encrypt
            ? crypto.createCipheriv('aes-256-gcm', master, task.iv)
            : crypto.createDecipheriv('aes-256-gcm', master, task.iv);
          cipher.setAAD(aad);
          if (!task.encrypt) cipher.setAuthTag(data.subarray(-16));
          const output = Buffer.concat([
            cipher.update(task.encrypt ? data : data.subarray(0, -16)),
            cipher.final(),
            task.encrypt ? cipher.getAuthTag() : Buffer.alloc(0)
          ]);
          handles.delete(payload.handle);
          return { output: output.toString('base64') };
        } catch {
          return { returnValue: false, errorCode: -20030 };
        }
      }
      case 'abort':
        handles.delete(payload.handle);
        return {};
      default:
        assert.fail(name);
    }
  }
  return {
    service: {
      call(uri, payload, cb) {
        calls.push({ uri, payload: structuredClone(payload) });
        const reply = answer(uri, payload);
        cb({ payload: { returnValue: true, ...reply } });
      }
    },
    calls,
    handles,
    row: () => row,
    deny: (n) => {
      denied = n;
    }
  };
}
test('service-owned state survives reopening with a canary and grants no caller access', async () => {
  const tv = platform(),
    store = createStore(tv.service);
  assert.equal(await store.probe(), true);
  const id = (await store.evidence()).canarySha256;
  assert.match(id, /^[0-9a-f]{64}$/);
  let s = await store.read();
  assert.equal(s.key, null);
  assert.equal(s.startup, 'off');
  s.startup = 'pending';
  s.generation = 'a'.repeat(32);
  s.activityId = 12;
  await store.write(s);
  const next = createStore(tv.service);
  assert.equal((await next.evidence()).canarySha256, id);
  assert.deepEqual(await next.read(), s);
  assert.ok(
    !tv.calls.some(
      (c) => c.uri.includes('keymanager') || c.uri.includes('Permissions')
    )
  );
});
test('TEE-encrypted pairing state survives service exit and rejects corrupt ciphertext', async () => {
  const tv = platform(),
    store = createStore(tv.service),
    synthetic = 'unit-test-only-credential';
  assert.equal(await store.credentialsReady(), true);
  const s = await store.read();
  s.key = synthetic;
  await store.write(s);
  assert.ok(
    !JSON.stringify(
      tv.calls.filter((c) => c.uri.includes('com.palm.db'))
    ).includes(synthetic)
  );
  assert.ok(
    !JSON.stringify(tv.row()).includes(
      Buffer.from(synthetic).toString('base64')
    )
  );
  const next = createStore(tv.service);
  assert.equal((await next.read()).key, synthetic);
  const data = Buffer.from(tv.row().secret.data, 'base64');
  data[0] ^= 1;
  tv.row().secret.data = data.toString('base64');
  await assert.rejects(next.read());
  assert.equal(tv.handles.size, 0);
});
test('platform refusal fails closed before a credential is written; startup remains usable', async () => {
  const tv = platform(),
    store = createStore(tv.service),
    s = await store.read();
  tv.deny('generateKey');
  await assert.rejects(
    store.credentialsReady(),
    (err) =>
      err.code.includes('generateKey') &&
      err.code.includes('-3963') &&
      !err.message.includes('private-fixture')
  );
  await assert.rejects(store.write({ ...s, key: 'test-only' }));
  assert.equal(tv.row().secret, null);
  s.startup = 'stopped';
  await store.write(s);
  assert.equal((await store.read()).startup, 'stopped');
  const foreign = platform();
  foreign.deny('putKind');
  await assert.rejects(createStore(foreign.service).probe());
  assert.equal(foreign.row(), null);
});

test('boot receipts update without decrypting or clearing an existing credential', async () => {
  const tv = platform(),
    store = createStore(tv.service);
  await store.write({ ...(await store.read()), key: 'synthetic' });
  const envelope = structuredClone(tv.row().secret);
  const boot = '12345678-1234-1234-1234-123456789012:1795850000',
    generation = 'b'.repeat(32);
  tv.deny('begin');
  const start = tv.calls.length,
    state = await store.readBoot();
  assert.equal(state.paired, true);
  assert.equal('key' in state, false);
  state.startup = 'enabled';
  state.generation = generation;
  state.activityId = 19;
  state.receipt = { boot, generation, at: 3000, early: true };
  state.ownerVisit = { boot, at: 12000 };
  await store.writeBoot(state);
  assert.deepEqual(await createStore(tv.service).readBoot(), state);
  assert.deepEqual(tv.row().secret, envelope);
  assert.ok(!tv.calls.slice(start).some((c) => c.uri.includes('keymanager')));
});
test('a damaged stored canary prevents encryption of the first live key', async () => {
  const tv = platform(),
    store = createStore(tv.service);
  const state = await store.read();
  await store.credentialsReady();
  tv.row().canary = 'f'.repeat(64);
  await assert.rejects(store.write({ ...state, key: 'synthetic' }), {
    code: 'storage-canary-mismatch'
  });
  assert.equal(tv.row().secret, null);
});

test('cancel racing first pairing can restore the prior empty credential', async () => {
  const tv = platform(),
    store = createStore(tv.service),
    previous = await store.read();
  await store.write({ ...previous, key: 'interrupted-pair' });
  await store.write(previous);
  assert.equal((await store.readBoot()).paired, false);
  assert.deepEqual(await store.read(), previous);
});

test('a failed candidate decrypt leaves the previously working credential and boot state intact', async () => {
  const tv = platform(),
    store = createStore(tv.service);
  const previous = { ...(await store.read()), key: 'first-valid' };
  await store.write(previous);
  const before = structuredClone(tv.row());
  const call = tv.service.call.bind(tv.service);
  tv.service.call = (uri, params, cb) =>
    call(uri, params, (message) => {
      if (
        uri.endsWith('/finish') &&
        params.data === Buffer.from('new-pair').toString('base64')
      ) {
        const corrupted = Buffer.from(message.payload.output, 'base64');
        corrupted[0] ^= 1;
        message.payload.output = corrupted.toString('base64');
      }
      cb(message);
    });
  await assert.rejects(
    store.write({ ...previous, key: 'new-pair', startup: 'enabled' })
  );
  assert.deepEqual(tv.row(), before);
  assert.deepEqual(await createStore(tv.service).read(), previous);
});

test('a lost DB8 commit receipt is resolved against the exact previously verified envelope', async () => {
  const tv = platform(),
    store = createStore(tv.service);
  const previous = { ...(await store.read()), key: 'first-valid' };
  await store.write(previous);
  const call = tv.service.call.bind(tv.service);
  tv.service.call = (uri, params, cb) =>
    call(uri, params, (message) => {
      cb(
        uri.endsWith('/put')
          ? { payload: { returnValue: true, results: [] } }
          : message
      );
    });
  const next = { ...previous, key: 'replacement', startup: 'enabled' };
  await store.write(next);
  assert.deepEqual(await createStore(tv.service).read(), next);
});

test('an unreadable commit outcome is distinguished from a known denied replacement', async () => {
  const tv = platform(),
    store = createStore(tv.service);
  const previous = { ...(await store.read()), key: 'first-valid' };
  await store.write(previous);
  tv.deny('put');
  await assert.rejects(store.write({ ...previous, key: 'denied' }), {
    code: 'storage-db-put:-3963'
  });
  assert.deepEqual(await store.read(), previous);
  tv.deny('');
  const call = tv.service.call.bind(tv.service);
  tv.service.call = (uri, params, cb) =>
    call(uri, params, (message) => {
      if (uri.endsWith('/put')) tv.deny('find');
      cb(message);
    });
  await assert.rejects(store.write({ ...previous, key: 'uncertain' }), {
    code: 'storage-credential-write-indeterminate'
  });
  tv.deny('');
  assert.equal((await createStore(tv.service).read()).key, 'uncertain');
});
