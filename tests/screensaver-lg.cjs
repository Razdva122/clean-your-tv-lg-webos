'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const EventEmitter = require('node:events');
const modulePath = path.resolve(__dirname, '../native/app/screensaver-lg.js');
assert.ok(fs.existsSync(modulePath), 'LG coordinator must be implemented');
const createLG = require(modulePath);
const registerURI =
  'luna://com.webos.service.tvpower/power/registerScreenSaverRequest';
const responseURI =
  'luna://com.webos.service.tvpower/power/responseScreenSaverRequest';
function fixture(overrides = {}) {
  let time = 10000;
  let session = {
    sessionId: 'owned-1',
    generation: 1,
    state: 'visible',
    visible: true,
    focused: true,
    lastHeartbeatMs: 9900
  };
  const calls = [],
    subscriptions = [],
    timers = new Map(),
    logs = [];
  let timerId = 0;
  const service = {
    subscribe(uri, payload) {
      const subscription = new EventEmitter();
      subscription.cancel = function () {
        this.cancelled = true;
        this.emit('cancel');
      };
      subscriptions.push({ uri, payload, subscription });
      return subscription;
    },
    call(uri, payload, callback) {
      calls.push({ uri, payload, callback });
    }
  };
  const coordinator = createLG({
    service,
    clientName: 'com.local.nativehome.screensaver',
    getSession: () => session,
    now: () => time,
    log: (e) => logs.push(e),
    setTimeout: (callback, delay) => {
      logs.push({ event: 'test-timer', delay });
      timers.set(++timerId, callback);
      return timerId;
    },
    clearTimeout: (id) => timers.delete(id),
    ...overrides
  });
  const start = () => {
    coordinator.start();
    subscriptions.at(-1).subscription.emit('response', {
      payload: { returnValue: true, subscribed: true }
    });
  };
  const request = (timestamp, extra = {}) =>
    subscriptions.at(-1).subscription.emit('response', {
      payload: { returnValue: true, timestamp, state: 'Active', ...extra }
    });
  const accept = () =>
    calls.at(-1).callback({ payload: { returnValue: true } });
  return {
    coordinator,
    calls,
    subscriptions,
    timers,
    logs,
    start,
    request,
    accept,
    setTime: (n) => {
      time = n;
    },
    setSession: (s) => {
      session = s;
    },
    session: () => session
  };
}

// A subscription must never be created as an import/construction side effect.
let f = fixture();
assert.equal(f.subscriptions.length, 0);
f.start();
f.coordinator.start();
assert.equal(f.subscriptions.length, 1);
assert.equal(f.subscriptions[0].uri, registerURI);
assert.deepEqual(f.subscriptions[0].payload, {
  subscribe: true,
  clientName: 'com.local.nativehome.screensaver'
});
assert.equal(
  f.calls.length,
  0,
  'registration acknowledgement is not a saver request'
);
f.request('9007199254740993123');
assert.equal(f.calls[0].uri, responseURI);
assert.deepEqual(f.calls[0].payload, {
  clientName: 'com.local.nativehome.screensaver',
  ack: false,
  timestamp: '9007199254740993123'
});
f.accept();
f.request('9007199254740993123');
f.request('9007199254740993122');
assert.equal(
  f.calls.length,
  1,
  'duplicate/stale timestamps cannot produce another veto'
);
f.request('9007199254740993124');
assert.equal(
  f.calls.length,
  2,
  'adjacent large decimal timestamps remain distinct'
);
f.accept();
f.coordinator.stop();

// C3 tvpowerd sends the low 32 bits of wall-clock microseconds as text.
for (const [first, second] of [
  ['4264538688', '150064392'],
  ['4119666392', '4844096']
]) {
  f = fixture();
  f.start();
  f.request(first);
  f.accept();
  f.setTime(190200);
  f.setSession({ ...f.session(), lastHeartbeatMs: 190100 });
  f.request(second);
  assert.equal(
    f.calls.length,
    2,
    'a new request after rollover must get a reply'
  );
  assert.deepEqual(f.calls[1].payload, {
    clientName: 'com.local.nativehome.screensaver',
    ack: false,
    timestamp: second
  });
  f.accept();
  f.request(first);
  f.request(second);
  assert.equal(
    f.calls.length,
    2,
    'ignore a delayed pre-wrap request and a duplicate'
  );
  f.coordinator.stop();
}

f = fixture();
f.start();
f.request('1250000000');
f.accept();
f.setTime(2510000);
f.setSession({ ...f.session(), lastHeartbeatMs: 2509900 });
f.request('3750000000');
assert.equal(
  f.calls.length,
  2,
  'long silence must allow a new ordering window'
);
f.accept();
f.coordinator.stop();

// Regressions here could suppress LG for startup, stale renderer, focus loss or unknown state.
for (const update of [
  null,
  { state: 'starting' },
  { state: 'closing' },
  { visible: false },
  { focused: false },
  { lastHeartbeatMs: 7000 },
  { lastHeartbeatMs: 10001 },
  { lastHeartbeatMs: NaN },
  { sessionId: '' },
  { generation: -1 }
]) {
  f = fixture();
  f.start();
  f.setSession(update === null ? null : { ...f.session(), ...update });
  f.request('100');
  assert.equal(f.calls[0].payload.ack, true, JSON.stringify(update));
  f.accept();
  f.coordinator.stop();
}
f = fixture({
  getSession() {
    throw new Error('renderer unavailable');
  }
});
f.start();
f.request(101);
assert.equal(f.calls[0].payload.ack, true);
assert.equal(
  f.calls[0].payload.timestamp,
  101,
  'safe numeric timestamp keeps its type'
);
f.accept();
f.coordinator.stop();
f = fixture();
f.start();
f.request('100', { state: 'Screen Saver' });
assert.equal(
  f.calls[0].payload.ack,
  true,
  'unknown/non-active power states never authorize a veto'
);
f.accept();
f.coordinator.stop();

// Stop must reject both old callbacks and future reuse of an old subscription generation.
f = fixture();
f.start();
const old = f.subscriptions[0].subscription;
f.coordinator.stop();
f.coordinator.stop();
assert.equal(old.cancelled, true);
old.emit('response', {
  payload: { returnValue: true, timestamp: '200', state: 'Active' }
});
assert.equal(f.calls.length, 0);
f.start();
old.emit('response', {
  payload: { returnValue: true, timestamp: '201', state: 'Active' }
});
assert.equal(f.calls.length, 0);
f.request('202');
f.accept();
f.coordinator.stop();

// Stop during the decision must win even when the injected owner callback is reentrant.
let owner;
f = fixture({
  getSession() {
    owner.stop();
    return {
      sessionId: 'old',
      generation: 1,
      state: 'visible',
      visible: true,
      focused: true,
      lastHeartbeatMs: 9900
    };
  }
});
owner = f.coordinator;
f.start();
f.request('300');
assert.equal(
  f.calls.length,
  0,
  'cancelled registration cannot send a stale veto'
);

// Errors and unanswered acknowledgements release the subscription, preventing further vetoes.
f = fixture();
f.start();
f.request('400');
f.calls[0].callback({ payload: { returnValue: false, errorCode: -1 } });
assert.equal(f.subscriptions[0].subscription.cancelled, true);
f.request('401');
assert.equal(f.calls.length, 1);
f = fixture();
f.start();
f.request('500');
assert.equal(f.timers.size, 1);
[...f.timers.values()][0]();
assert.equal(f.subscriptions[0].subscription.cancelled, true);
f.calls[0].callback({ payload: { returnValue: true } });
assert.equal(
  f.coordinator.status().running,
  false,
  'late ack cannot revive a cancelled registration'
);
f = fixture();
f.start();
f.request('600');
f.request('601');
assert.equal(
  f.calls[1].payload.ack,
  true,
  'pending acknowledgement cannot authorize another veto'
);
f.coordinator.stop();
assert.equal(f.timers.size, 0);

// Malformed requests cannot be echoed as an invented timestamp or keep a broken subscriber registered.
for (const timestamp of [
  undefined,
  null,
  {},
  '',
  'NaN',
  Infinity,
  1.5,
  9007199254740992
]) {
  f = fixture();
  f.start();
  f.request(timestamp);
  assert.equal(f.calls.length, 0);
  if (timestamp !== undefined)
    assert.equal(f.subscriptions[0].subscription.cancelled, true);
  f.coordinator.stop();
}
f = fixture();
f.start();
f.subscriptions[0].subscription.emit('response', {
  payload: { returnValue: false }
});
assert.equal(f.coordinator.status().running, false);
f = fixture();
f.start();
f.subscriptions[0].subscription.emit('error', new Error('disconnected'));
assert.equal(f.coordinator.status().running, false);
f = fixture({
  service: {
    subscribe() {
      throw new Error('denied');
    },
    call() {}
  }
});
assert.doesNotThrow(() => f.coordinator.start());
assert.equal(f.coordinator.status().running, false);
f = fixture();
f.start();
f.coordinator.stop();
assert.equal(
  f.logs.some((e) => e.event === 'screensaver-lg-stop'),
  true
);
console.log(
  'PASS screensaver LG coordination: exact timestamps, healthy veto, stale/stop/error fail-open'
);

// An authenticated LG request may start a new saver only within its deadline.
let completeGlobal,
  cancelGlobal = 0;
f = fixture({
  startGlobal(done) {
    completeGlobal = done;
    return () => {
      cancelGlobal++;
    };
  }
});
f.setSession(null);
f.start();
f.request(300);
assert.equal(
  f.logs.at(-1).delay,
  1500,
  'leave half of the measured LG response window'
);
assert.equal(
  f.calls.length,
  0,
  'wait for a visible renderer before answering LG'
);
f.setTime(11150);
f.setSession({
  sessionId: 'global-1',
  generation: 1,
  state: 'visible',
  visible: true,
  focused: true,
  lastHeartbeatMs: 11150
});
completeGlobal(true);
assert.equal(f.calls.at(-1).payload.ack, false);
f.accept();
f.setSession(null);
f.request(301);
assert.equal(
  f.calls.at(-1).payload.ack,
  true,
  'allow LG after custom dismissal'
);
f.accept();
f.request(302);
const late = completeGlobal;
Array.from(f.timers.values())[0]();
assert.equal(cancelGlobal, 1);
assert.equal(f.calls.at(-1).payload.ack, true, 'timeout leaves LG in charge');
const beforeLate = f.calls.length;
late(true);
assert.equal(
  f.calls.length,
  beforeLate,
  'late readiness cannot change the answer'
);
f.accept();
f.request(303);
const beforeExpired = f.calls.length;
f.setTime(12650);
f.setSession({
  sessionId: 'global-2',
  generation: 1,
  state: 'visible',
  visible: true,
  focused: true,
  lastHeartbeatMs: 12650
});
completeGlobal(true);
assert.equal(f.calls.length, beforeExpired + 1);
assert.equal(
  f.calls.at(-1).payload.ack,
  true,
  'exact deadline allows LG even if the timer is delayed'
);
f.coordinator.stop();
