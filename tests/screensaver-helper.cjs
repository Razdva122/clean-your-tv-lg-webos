'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const EventEmitter = require('node:events');
const adapterPath = path.join(
  __dirname,
  '../native/app/screensaver-controller.js'
);
assert.ok(fs.existsSync(adapterPath), 'No-root screensaver adapter must exist');
const create = require(adapterPath);
const shared = require('../screensaver/controller');
const createLG = require('../native/app/screensaver-lg');

function fixture(overrides = {}) {
  let time = 100;
  let context = {
    popupSupported: true,
    ownerHealthy: true,
    previewEligible: true,
    inAppEligible: true,
    idleTimeoutMs: 10
  };
  let update;
  let created = 0;
  let closed = 0;
  const calls = [],
    subscriptions = [],
    intervals = new Map();
  const service = {
    call(uri, payload, done) {
      calls.push({ uri, payload });
      if (overrides.onCall) return overrides.onCall(uri, done);
      done({ payload: { returnValue: true } });
    },
    subscribe(uri, payload) {
      const s = new EventEmitter();
      s.cancel = () => {
        s.cancelled = true;
        s.emit('cancel');
      };
      subscriptions.push({ uri, payload, s });
      return s;
    }
  };
  const adapter = create({
    generation: 9,
    service,
    context: () => context,
    controller: {
      monotonic: shared.monotonic,
      create(options) {
        created += 1;
        return shared.create(options);
      }
    },
    createLG,
    now: () => time,
    listen(current, receive, ready) {
      update = receive;
      ready(null, {
        endpoint: 'http://127.0.0.1:1234/screensaver',
        close() {
          closed += 1;
        }
      });
    },
    setInterval(fn) {
      intervals.set(fn, fn);
      return fn;
    },
    clearInterval(id) {
      intervals.delete(id);
    },
    ...overrides
  });
  function ready() {
    const launch = calls.findLast((c) => c.uri.endsWith('/launch'));
    const p = launch.payload.params;
    update({
      schema: 1,
      sessionId: p.sessionId,
      generation: p.generation,
      visible: true,
      focused: true,
      mediaState: 'ready'
    });
    return p;
  }
  function request(timestamp) {
    subscriptions.at(-1).s.emit('response', {
      payload: { returnValue: true, state: 'Active', timestamp }
    });
  }
  function enable() {
    const result = adapter.enable();
    if (subscriptions.length)
      subscriptions.at(-1).s.emit('response', {
        payload: { returnValue: true, subscribed: true }
      });
    return result;
  }
  return {
    adapter,
    calls,
    subscriptions,
    intervals,
    enable,
    ready,
    request,
    setTime: (n) => {
      time = n;
    },
    setContext: (c) => {
      context = c;
    },
    created: () => created,
    closed: () => closed,
    update: (p) => update(p)
  };
}

const closeUri = 'luna://com.webos.applicationManager/closeByAppId';
const launchUri = 'luna://com.webos.applicationManager/launch';
const appId = 'com.cleanyourtv.screensaver';

function deferredCalls() {
  const replies = [];
  const f = fixture({
    onCall(uri, done) {
      if (uri === closeUri || uri === launchUri) replies.push(done);
      else done({ payload: { returnValue: true } });
    }
  });
  f.enable();
  return Object.assign(f, {
    reply(payload) {
      assert.ok(replies.length, 'a SAM call is waiting for a reply');
      replies.shift()({ payload });
    },
    tick(time) {
      f.setTime(time);
      for (const callback of f.intervals.keys()) callback();
    }
  });
}

{
  const f = deferredCalls();
  assert.equal(f.adapter.preview(), false, 'wait for SAM close capability');
  assert.deepEqual(f.calls, [{ uri: closeUri, payload: { id: appId } }]);
  f.reply({
    returnValue: false,
    errorCode: -1,
    errorText: 'Permission denied'
  });
  assert.equal(f.adapter.unavailable(), true);
  assert.equal(f.adapter.preview(), false);
  assert.equal(
    f.calls.some((call) => call.uri === launchUri),
    false
  );
  f.adapter.dispose();
}

{
  const f = deferredCalls();
  f.reply({
    returnValue: false,
    errorCode: 40,
    errorText: appId + ' is not running'
  });
  assert.equal(f.adapter.preview(), true);
  assert.equal(f.calls.at(-1).uri, launchUri);
  f.reply({ returnValue: true });
  f.tick(10100);
  assert.deepEqual(f.calls.at(-1), { uri: closeUri, payload: { id: appId } });
  f.tick(12100);
  assert.equal(
    f.adapter.preview(),
    false,
    'unconfirmed close blocks another launch'
  );
  f.reply({ returnValue: true });
  assert.equal(f.adapter.preview(), true);
  f.reply({ returnValue: true });
  f.adapter.dispose();
  f.reply({ returnValue: true });
}

{
  const f = deferredCalls();
  f.reply({ returnValue: true });
  f.adapter.preview();
  f.tick(10100);
  assert.equal(
    f.calls.at(-1).uri,
    closeUri,
    'close even if launch reply is missing'
  );
  f.reply({ returnValue: true }); // Accept the late launch.
  f.reply({ returnValue: true }); // Settle the first close.
  assert.deepEqual(
    f.calls.map(({ uri }) => uri),
    [closeUri, launchUri, closeUri, closeUri]
  );
  f.adapter.stop();
  assert.equal(f.adapter.closePending(), true);
  f.reply({ returnValue: true });
  assert.equal(f.adapter.closePending(), false);
}

{
  const f = deferredCalls();
  f.reply({
    returnValue: false,
    errorCode: 1,
    errorText: 'app is not running'
  });
  f.adapter.preview();
  f.reply({ returnValue: true });
  const params = f.ready();
  f.update({
    schema: 1,
    ...params,
    visible: false,
    focused: false,
    mediaState: 'closed'
  });
  assert.deepEqual(f.calls.at(-1), { uri: closeUri, payload: { id: appId } });
  assert.equal(
    f.adapter.preview(),
    false,
    'renderer cannot confirm SAM closed'
  );
  f.reply({
    returnValue: false,
    errorCode: -1,
    errorText: 'Permission denied'
  });
  assert.equal(
    f.calls.filter(({ uri }) => uri === closeUri).length,
    3,
    'one close retry'
  );
  f.reply({
    returnValue: false,
    errorCode: -1,
    errorText: 'Permission denied'
  });
  assert.equal(f.adapter.unavailable(), true);
  assert.equal(f.adapter.preview(), false);
  f.adapter.dispose();
}

// Removing explicit enable/capability gates would create transport and LG ownership.
let f = fixture();
assert.equal(f.created(), 0);
assert.equal(f.adapter.preview(), false);
assert.equal(f.subscriptions.length, 0);
f.setContext({ ownerHealthy: true, popupSupported: false });
assert.equal(f.enable(), false);
assert.equal(f.created(), 0);
f.adapter.dispose();

// Use the real shared policy/controller and LG protocol through fake external I/O.
f = fixture();
assert.equal(f.enable(), true);
assert.equal(f.enable(), true);
assert.equal(f.created(), 1);
assert.equal(f.subscriptions.length, 1);
assert.equal(f.adapter.preview(), true);
assert.deepEqual(f.calls[0], { uri: closeUri, payload: { id: appId } });
assert.equal(f.calls[1].uri, launchUri);
assert.equal(f.calls[1].payload.id, appId);
assert.equal(f.calls[1].payload.params.generation, 9);
assert.match(f.calls[1].payload.params.sessionId, /^[a-f0-9]{48}$/);
f.request('1000');
assert.equal(f.calls.at(-1).payload.ack, true, 'startup must allow LG');
const first = f.ready();
f.request('1001');
assert.equal(
  f.calls.at(-1).payload.ack,
  false,
  'visible healthy surface can coordinate LG'
);
f.adapter.activity();
f.request('1002');
assert.equal(
  f.calls.at(-1).payload.ack,
  true,
  'wake activity immediately stops the veto'
);
assert.deepEqual(
  f.update({
    schema: 1,
    ...first,
    visible: false,
    focused: false,
    mediaState: 'closed'
  }),
  { close: true }
);
f.adapter.stop();
assert.equal(f.subscriptions[0].s.cancelled, true);
assert.equal(f.intervals.size, 0);
assert.equal(f.closed(), 1);
assert.equal(f.adapter.preview(), false);
assert.equal(f.adapter.getSession(), null);
assert.ok(
  f.calls.every(
    (c) =>
      c.uri === launchUri ||
      c.uri === closeUri ||
      c.uri.endsWith('/responseScreenSaverRequest')
  )
);
assert.ok(
  f.calls
    .filter((c) => c.uri === launchUri || c.uri === closeUri)
    .every((c) => c.payload.id === 'com.cleanyourtv.screensaver')
);

// Stop and inactive power always unregister; explicit enable is needed afterwards.
for (const end of ['stop', 'powerInactive', 'dispose']) {
  f = fixture();
  f.enable();
  f.adapter.preview();
  f.ready();
  const old = f.subscriptions[0].s;
  f.adapter[end]();
  assert.equal(old.cancelled, true, end);
  assert.equal(f.intervals.size, 0, end);
  assert.equal(f.adapter.preview(), false, end);
  const count = f.calls.length;
  old.emit('response', {
    payload: { returnValue: true, state: 'Active', timestamp: '2000' }
  });
  assert.equal(
    f.calls.length,
    count,
    'old registration cannot send a veto after ' + end
  );
  if (end === 'dispose') assert.equal(f.enable(), false);
  else {
    assert.equal(f.enable(), true);
    assert.equal(f.created(), 2);
  }
  f.adapter.dispose();
}

// Eligibility is supplied only by the trusted owning app, never inferred from LG.
f = fixture();
f.enable();
assert.equal(f.adapter.eligible(), false);
f.adapter.activity();
f.setTime(111);
assert.equal(f.adapter.eligible(), true);
f.adapter.dispose();
f = fixture();
f.enable();
f.setContext({
  ownerHealthy: true,
  popupSupported: true,
  inAppEligible: false,
  globalEligible: true
});
f.adapter.activity();
f.setTime(70000);
assert.equal(f.adapter.eligible(), false);
f.request('3000');
assert.equal(f.calls.filter((c) => c.uri.endsWith('/launch')).length, 1);
assert.equal(
  f.calls.filter((c) => c.uri.includes('responseScreenSaverRequest')).length,
  0
);
f.ready();
assert.equal(
  f.calls.findLast((c) => c.uri.includes('responseScreenSaverRequest')).payload
    .ack,
  false
);
f.adapter.dispose();

// Transport must not survive failed initialization or a throwing owner callback.
f = fixture({
  context() {
    throw new Error('owner unavailable');
  }
});
assert.equal(f.enable(), false);
assert.equal(f.created(), 0);
f.adapter.dispose();
let cancelled = 0;
let disposed = 0;
const broken = create({
  generation: 9,
  service: {},
  context: () => ({ ownerHealthy: true, popupSupported: true }),
  controller: {
    monotonic: () => 0,
    create: () => ({
      enable() {},
      dispose() {
        disposed += 1;
      },
      getSession: () => null
    })
  },
  createLG: () => ({
    start() {
      throw new Error('cannot register');
    },
    stop() {
      cancelled += 1;
    }
  })
});
assert.equal(broken.enable(), false);
assert.equal(cancelled, 1);
assert.equal(disposed, 1);
broken.dispose();

// Only an enabled healthy owner may acquire the pre-authorized media lease.
let acquired = 0;
let mediaReleased = 0;
f = fixture({
  acquireMedia() {
    acquired += 1;
    return {
      mode: 'photo',
      lease: {
        contentType: 'image/png',
        size: 8,
        serve() {},
        release() {
          mediaReleased += 1;
        }
      }
    };
  }
});
assert.equal(acquired, 0);
f.enable();
assert.equal(acquired, 0);
f.adapter.preview();
assert.equal(acquired, 1, 'accepted activation acquires trusted media');
const photo = f.ready();
assert.equal(
  f.update({
    schema: 1,
    ...photo,
    visible: true,
    focused: true,
    mediaState: 'ready'
  }).content.mode,
  'photo'
);
f.adapter.stop();
assert.equal(mediaReleased, 1);
assert.equal(f.adapter.preview(), false);
assert.equal(acquired, 1);

// Revoked health during acquisition releases the result before exposing it.
mediaReleased = 0;
f = fixture({
  acquireMedia() {
    f.setContext({ ownerHealthy: false, popupSupported: true });
    return {
      mode: 'photo',
      lease: {
        contentType: 'image/png',
        size: 8,
        serve() {},
        release() {
          mediaReleased += 1;
        }
      }
    };
  }
});
f.enable();
f.adapter.preview();
assert.equal(mediaReleased, 1);
assert.equal(
  f.calls.filter((call) => call.uri.endsWith('/launch')).length,
  0,
  'revoked owner cannot launch after acquiring media'
);
f.adapter.dispose();
console.log(
  'PASS No-root screensaver adapter: explicit ownership, own popup, LG cleanup and capability gates'
);
