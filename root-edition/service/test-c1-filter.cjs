'use strict';
var assert = require('assert'),
  fs = require('fs'),
  vm = require('vm');
var source = fs.existsSync(__dirname + '/../runtime/c1-home-filter.js')
  ? fs.readFileSync(__dirname + '/../runtime/c1-home-filter.js', 'utf8')
  : '';
function setup(change) {
  var callbacks = [],
    timers = [],
    launches = [],
    sends = [],
    homeCallbacks = [];
  var ctx = {
    Qt: { Key_Super_L: 42 },
    KeyPolicy: { NextPolicy: 0, Accepted: 1 },
    genericTimer: {
      set: function (ms, fn) {
        assert(ms <= 3000);
        timers.push(fn);
      }
    },
    applicationManager: {
      launch: function (id, params) {
        launches.push([id, params]);
      }
    },
    lunaCall: {
      send: function (service, method, payload, cb) {
        assert.strictEqual(service, 'com.webos.cleanyourtv.root.lease');
        assert.strictEqual(method, '/c1Home');
        sends.push(JSON.parse(payload));
        homeCallbacks.push(cb);
      },
      subscribe: function (service, method, payload, cb) {
        assert.strictEqual(service, 'com.webos.cleanyourtv.root.lease');
        assert.strictEqual(method, '/c1Lease');
        assert.strictEqual(JSON.parse(payload).subscribe, true);
        callbacks.push(cb);
      }
    }
  };
  if (change) change(ctx);
  vm.createContext(ctx);
  vm.runInContext(source, ctx);
  assert.strictEqual(typeof ctx.init, 'function', 'filter must export init');
  ctx.init();
  assert.strictEqual(
    callbacks.length,
    change ? 0 : 1,
    'filter must subscribe to private alias'
  );
  return {
    ctx: ctx,
    callbacks: callbacks,
    timers: timers,
    launches: launches,
    sends: sends,
    homeCallbacks: homeCallbacks,
    key: function (d, r, k) {
      return ctx.cytvC1HomeKey(k === undefined ? 42 : k, d, !!r);
    },
    reply: function (v) {
      callbacks[callbacks.length - 1](JSON.stringify(v));
    }
  };
}
function lease(sequence, token) {
  return {
    returnValue: true,
    subscribed: true,
    backend: 'c1-native-gate',
    routing: 'compositor-keyfilter-v1',
    healthy: true,
    token: token || 'a'.repeat(32),
    sequence: sequence
  };
}
var s = setup();
assert.strictEqual(s.key(true), 0);
s.reply(lease(1));
assert.strictEqual(s.key(false), 0, 'unmatched LG release stays LG');
assert.strictEqual(s.key(true), 1);
assert.strictEqual(
  s.launches.length,
  0,
  'compositor never directly launches Root'
);
assert.strictEqual(s.sends.length, 1);
assert.strictEqual(s.sends[0].token, 'a'.repeat(32));
assert.strictEqual(s.key(true, true), 1);
assert.strictEqual(s.sends.length, 1);
s.timers[0]();
assert.strictEqual(s.key(false), 1, 'consume own release after expiry');
assert.strictEqual(s.key(true), 0);
s = setup();
s.key(true);
s.reply(lease(1));
assert.strictEqual(
  s.key(true, true),
  0,
  'LG press cannot be stolen by renewal'
);
assert.strictEqual(s.key(false), 0);
assert.strictEqual(s.key(true), 1);
assert.strictEqual(s.key(true, false, 99), 0);
assert.strictEqual(s.key(false, false, 99), 0);
s.key(false);
s = setup();
s.reply(lease(1));
s.reply(lease(2));
s.timers[0]();
assert.strictEqual(
  s.key(true),
  1,
  'cancelled older timer cannot expire fresh lease'
);
s.key(false);
s.reply(lease(2));
assert.strictEqual(s.key(true), 0, 'duplicate disarms');
s.key(false);
s.reply(lease(3));
assert.strictEqual(
  s.key(true),
  0,
  'bad stream stays disarmed until new subscription'
);
s = setup();
s.reply(lease(1));
s.reply(lease(2, 'b'.repeat(32)));
assert.strictEqual(
  s.key(true),
  0,
  'changed attempt cannot rearm existing filter'
);
[
  null,
  {},
  { returnValue: false },
  Object.assign(lease(1), { subscribed: false }),
  Object.assign(lease(1), { sequence: 1.5 }),
  Object.assign(lease(1), { healthy: 'true' })
].forEach(function (bad) {
  var a = setup();
  a.reply(bad);
  a.reply(lease(2));
  assert.strictEqual(a.key(true), 0);
});
s = setup();
var old = s.callbacks[0];
s.ctx.init();
old(JSON.stringify(lease(9)));
assert.strictEqual(s.key(true), 0, 'retired subscription callback cannot arm');
s.key(false);
s.reply(lease(1));
assert.strictEqual(s.key(true), 1);
s.key(false);
s.callbacks[1]('bad JSON');
assert.strictEqual(s.key(true), 0);
s = setup();
s.reply(Object.assign(lease(1), { healthy: false }));
assert.strictEqual(s.key(true), 0);
s.key(false);
s.reply(lease(2));
assert.strictEqual(
  s.key(true),
  1,
  'initial pending lease permits later readiness'
);
s.key(false);
s.reply(Object.assign(lease(3), { healthy: false }));
s.reply(lease(4));
assert.strictEqual(s.key(true), 0, 'readiness loss cannot automatically rearm');
s = setup();
s.reply(Object.assign(lease(1), { unexpected: true }));
assert.strictEqual(
  s.key(true),
  0,
  'unexpected healthy reply fields fail closed'
);
s = setup();
s.callbacks[0](lease(1));
assert.strictEqual(s.key(true), 1, 'Qt may deliver an already parsed reply');
s = setup();
s.reply(lease(1));
s.key(true);
s.homeCallbacks[0](JSON.stringify({ returnValue: false }));
assert.strictEqual(s.launches.length, 1);
assert.strictEqual(
  s.launches[0][0],
  'com.webos.app.home',
  'stopped native dispatch falls back to LG'
);
assert.strictEqual(s.key(false), 1);
assert.strictEqual(s.key(true), 0);
s = setup();
s.reply(lease(1));
s.key(true);
s.timers[1]();
assert.strictEqual(
  s.launches[0][0],
  'com.webos.app.home',
  'dispatch timeout falls back LG'
);
s.homeCallbacks[0](
  JSON.stringify({
    returnValue: true,
    backend: 'c1-native-gate',
    routing: 'compositor-keyfilter-v1',
    token: 'a'.repeat(32)
  })
);
assert.strictEqual(s.launches.length, 1, 'late callback has no second effect');
s = setup();
s.reply(lease(1));
s.key(true);
var pendingHome = s.homeCallbacks[0];
var pendingTimeout = s.timers[1];
s.ctx.init();
pendingHome(JSON.stringify({ returnValue: false }));
pendingTimeout();
assert.strictEqual(
  s.launches.length,
  0,
  'retired generation callbacks cannot launch LG'
);
s = setup();
s.reply(lease(1));
delete s.ctx.lunaCall.send;
assert.strictEqual(
  s.key(true),
  0,
  'missing send fails open before key capture'
);
s = setup();
s.reply(lease(1));
s.key(true);
s.homeCallbacks[0]({
  returnValue: true,
  backend: 'c1-native-gate',
  routing: 'compositor-keyfilter-v1',
  token: 'a'.repeat(32)
});
assert.strictEqual(s.launches.length, 0, 'native owns successful Root effect');
s.key(false);
s.key(true);
assert.strictEqual(
  s.sends.length,
  2,
  'next physical press dispatches once after completion'
);
[
  function (ctx) {
    delete ctx.genericTimer;
  },
  function (ctx) {
    delete ctx.genericTimer.set;
  },
  function (ctx) {
    delete ctx.lunaCall.subscribe;
  },
  function (ctx) {
    delete ctx.lunaCall.send;
  },
  function (ctx) {
    delete ctx.applicationManager.launch;
  },
  function (ctx) {
    ctx.Qt.Key_Super_L = NaN;
  },
  function (ctx) {
    delete ctx.KeyPolicy.Accepted;
  }
].forEach(function (change) {
  var unavailable = setup(change);
  assert.strictEqual(
    unavailable.callbacks.length,
    0,
    'missing Qt capability must not establish a broker lease'
  );
  assert.strictEqual(
    unavailable.key(true),
    0,
    'unverified Qt contract must leave Home with LG'
  );
  assert.strictEqual(unavailable.sends.length, 0);
});
console.log('C1 compositor filter tests passed');
