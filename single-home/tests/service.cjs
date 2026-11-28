'use strict';
const assert = require('node:assert/strict'),
  test = require('node:test');
const register = require('../service/controller'),
  boot = require('../service/boot');
const app = 'io.github.razdva122.cytvhomepilot',
  serviceId = app + '.service',
  uuid = '12345678-1234-1234-1234-123456789012:1000000000';
function fixture() {
  let state = {
      key: null,
      startup: 'off',
      generation: '',
      activityId: null,
      ownerVisit: null,
      receipt: null
    },
    now = 4000,
    ident = uuid,
    ready = false,
    pairing = async () => ({
      key: 'private',
      apps: [{ id: 'tv.app', title: 'App' }]
    }),
    calls = [],
    methods = {};
  const svc = {
    register(n, fn) {
      methods[n] = fn;
    },
    call(uri, args, cb) {
      calls.push([uri, args]);
      cb({ payload: { returnValue: true, activityId: 31 } });
    },
    activityManager: {
      complete(a, params, cb) {
        calls.push(['complete', params]);
        cb(a);
      }
    }
  };
  const store = {
    probe: async () => true,
    credentialsReady: async () => ready,
    read: async () => structuredClone(state),
    write: async (s) => {
      state = structuredClone(s);
    }
  };
  store.readBoot = async () => ({
    ...structuredClone(state),
    key: undefined,
    paired: !!state.key
  });
  store.writeBoot = async (s) => {
    const key = state.key;
    state = { ...structuredClone(s), key };
  };
  register(
    svc,
    store,
    (...args) => pairing(...args),
    () => ({ boot: ident, at: now })
  );
  function invoke(n, p = {}, id = app) {
    return new Promise((resolve) =>
      methods[n]({
        payload: p,
        ls2Message: { applicationID: () => id },
        respond: resolve
      })
    );
  }
  function tick(gen, id = 31, actor = 'com.palm.activitymanager') {
    const a = {
      name: serviceId + '.wake',
      creator: { serviceId },
      type: { continuous: false },
      activityId: id
    };
    return new Promise((resolve) =>
      methods.tick({
        payload: { $activity: a, generation: gen, version: 1 },
        activity: a,
        uniqueToken: 't' + now,
        ls2Message: { senderServiceName: () => actor },
        respond: resolve
      })
    );
  }
  return {
    state: () => state,
    invoke,
    tick,
    calls,
    ready: () => (ready = true),
    writeCredential: (writer) => {
      store.write = writer;
    },
    pair: (f) => (pairing = f),
    time: (t) => (now = t),
    boot: (v) => (ident = v)
  };
}
test('only the packaged UI can act; probe and status expose no secrets', async () => {
  const f = fixture();
  assert.equal(
    (await f.invoke('pair', { confirm: true }, 'malicious')).errorCode,
    'denied'
  );
  assert.equal(
    (await f.invoke('pair', { confirm: true })).errorCode,
    'storage-unverified'
  );
  assert.equal(
    (await f.invoke('pair', { confirm: false })).errorCode,
    'invalid-request'
  );
  f.ready();
  assert.equal((await f.invoke('pair', { confirm: true })).paired, true);
  assert.equal(f.state().startup, 'off');
  assert(!JSON.stringify(await f.invoke('status')).includes('private'));
});
test('decline and cancel preserve older verified pairing; catalog limited to same package', async () => {
  const f = fixture();
  f.ready();
  await f.invoke('pair', { confirm: true });
  f.pair(async () => {
    throw Error('pairing-declined');
  });
  assert.equal(
    (await f.invoke('pair', { confirm: true })).errorCode,
    'pairing-declined'
  );
  assert.equal(f.state().key, 'private');
  let release, started;
  const waiting = new Promise((r) => (started = r));
  f.pair(
    () =>
      new Promise((r) => {
        release = r;
        started();
      })
  );
  const task = f.invoke('pair', { confirm: true });
  await waiting;
  assert.equal((await f.invoke('cancelPair')).returnValue, true);
  release({ key: 'replacement', apps: [] });
  assert.equal((await task).errorCode, 'cancelled');
  assert.equal(f.state().key, 'private');
  assert.equal((await f.invoke('catalog', {}, 'bad')).errorCode, 'denied');
});
test('owner opt-in, two actual callbacks, pre-UI proof, idempotence and persistent Stop', async () => {
  const f = fixture();
  assert.equal((await f.invoke('enable', {})).errorCode, 'invalid-request');
  let result = await f.invoke('enable', { confirm: true });
  assert.equal(result.startup, 'pending');
  const gen = f.state().generation;
  assert.equal((await f.tick(gen, 32)).returnValue, false);
  assert.equal((await f.tick(gen, 31, 'pretend')).returnValue, false);
  await f.tick(gen);
  assert.equal(f.state().startup, 'pending');
  f.time(16000);
  await f.tick(gen);
  assert.equal(f.state().startup, 'enabled');
  const creates = () => f.calls.filter((c) => c[0].endsWith('/create')).length;
  assert.equal(creates(), 1);
  await f.invoke('enable', { confirm: true });
  assert.equal(creates(), 1);
  f.boot(uuid.replace(':1000000000', ':1000002222'));
  f.time(2000);
  await f.tick(gen);
  f.time(8000);
  const proof = await f.invoke('status');
  assert.equal(proof.bootObserved, true);
  assert.equal(proof.bootReceiptUptimeMs, 2000);
  assert.equal(proof.firstOwnerUptimeMs, 8000);
  await f.invoke('disable');
  assert.equal((await f.tick(gen)).returnValue, false);
  assert.equal(f.state().startup, 'stopped');
  assert.equal(f.state().activityId, null);
  assert(f.calls.every((c) => !c[0].includes('applicationManager')));
});
test('Stop received before DB returns cancels already received pair and enable requests', async () => {
  const f = fixture();
  f.ready();
  let count = 0;
  f.pair(async () => {
    count++;
    return { key: 'should-not-save' };
  });
  const pair = f.invoke('pair', { confirm: true }),
    enable = f.invoke('enable', { confirm: true }),
    stop = f.invoke('disable');
  assert.equal((await pair).errorCode, 'cancelled');
  assert.equal((await enable).errorCode, 'cancelled');
  await stop;
  assert.equal(f.state().key, null);
  assert.equal(count, 0);
  assert.equal(f.calls.filter((c) => c[0].endsWith('/create')).length, 0);
});
test('create replaces only an owner-scoped fixed-name conflict; Stop prevents replacement', async () => {
  const calls = [];
  let active = true;
  function svc(interrupt) {
    return {
      call(uri, p, cb) {
        calls.push(p);
        if (!p.replace) {
          if (interrupt) active = false;
          cb({ payload: { returnValue: false, errorCode: 17 } });
        } else cb({ payload: { returnValue: true, activityId: 42 } });
      }
    };
  }
  assert.equal(await boot.create(svc(false), 'a'.repeat(32), () => active), 42);
  assert.deepEqual(
    calls.map((p) => p.replace),
    [false, true]
  );
  assert.equal(calls[0].activity.name, serviceId + '.wake');
  calls.length = 0;
  await assert.rejects(
    boot.create(svc(true), 'a'.repeat(32), () => active),
    /cancelled/
  );
  assert.equal(calls.length, 1);
});

test('an indeterminate pairing write retains its safe diagnostic during cancellation', async () => {
  const f = fixture();
  f.ready();
  let started, fail;
  const writing = new Promise((resolve) => {
    started = resolve;
  });
  f.writeCredential(
    () =>
      new Promise((resolve, reject) => {
        started();
        fail = () =>
          reject(
            Object.assign(new Error('untrusted private payload'), {
              code: 'storage-credential-write-indeterminate'
            })
          );
      })
  );
  const pairing = f.invoke('pair', { confirm: true });
  await writing;
  const cancel = f.invoke('cancelPair');
  fail();
  assert.deepEqual(await pairing, {
    returnValue: false,
    errorCode: 'storage-unavailable',
    storageIssue: 'storage-credential-write-indeterminate'
  });
  assert.equal((await cancel).cancelled, true);
});
