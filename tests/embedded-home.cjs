'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');
const runtime = path.join(__dirname, '../root-edition/runtime');

function setup(change, stockEnums) {
  const timers = [],
    messages = [],
    stock = [],
    sends = [];
  let context;
  const ctx = {
    Qt: {
      Key_Super_L: 42,
      include(name) {
        if (name === 'qrc:///keypolicies.js') {
          vm.runInContext(
            stockEnums || 'var NotAccepted=0, Accepted=1, NextPolicy=2;',
            context
          );
          return { status: 0 };
        }
        vm.runInContext(
          fs.readFileSync(path.join(runtime, name), 'utf8'),
          context
        );
        return { status: 0 };
      }
    },
    isFinite
  };
  context = vm.createContext(ctx);
  vm.runInContext(
    fs.readFileSync(path.join(runtime, 'embedded-home.js'), 'utf8'),
    context
  );
  function handleSystemKeys(key, pressed, repeat) {
    stock.push([key, pressed, repeat]);
    if (key === 42 && !pressed)
      ysm.state = ysm.state === 'hidden' ? 'visible' : 'hidden';
    return 1;
  }
  const earlier = function earlier() {
    return 2;
  };
  const alert = { modalAlertsVisible: false, children: [] };
  const ysm = {
    state: 'hidden',
    smartTvReady: true,
    access: { ribbon: true, keyFilter: { home: true } },
    children: [alert],
    keyFilter: {
      keyPolicies: [earlier, handleSystemKeys],
      pressFunction: 'handleKeyPressed',
      releaseFunction: 'handleKeyReleased',
      handleKeyEvents() {},
      handleKeyPressed() {},
      handleKeyReleased() {}
    },
    goHome() {
      this.state = this.state === 'hidden' ? 'visible' : 'hidden';
    }
  };
  const api = {
    later(ms, fn) {
      timers.push({ ms, fn });
    },
    subscribe(service, method, payload, callback) {
      messages.push({
        service,
        method,
        payload: JSON.parse(payload),
        callback
      });
    },
    send(service, method, payload, callback) {
      sends.push({ service, method, payload: JSON.parse(payload), callback });
    }
  };
  if (change) change(ysm, api);
  const attachment = ctx.attach(ysm, api);
  function key(pressed, repeat = false, value = 42) {
    return ysm.keyFilter.keyPolicies[1](value, pressed, repeat);
  }
  function lease(sequence = 1) {
    messages[0].callback({
      returnValue: true,
      subscribed: true,
      backend: 'c1-native-gate',
      routing: 'compositor-keyfilter-v1',
      healthy: true,
      token: 'a'.repeat(32),
      sequence
    });
  }
  return {
    ctx,
    ysm,
    api,
    timers,
    messages,
    sends,
    stock,
    alert,
    attachment,
    key,
    lease,
    earlier
  };
}

test('unchanged earlier policies and stock pass-through without a lease', () => {
  const s = setup();
  assert(s.attachment);
  assert.equal(s.ysm.keyFilter.keyPolicies[0], s.earlier);
  s.key(true);
  s.key(false);
  assert.equal(s.ysm.state, 'visible');
  assert.equal(s.sends.length, 0);
  assert.deepEqual(s.stock, [
    [42, true, false],
    [42, false, false]
  ]);
});

test('a healthy C1 lease captures the pair then expiry gives the next pair to LG', () => {
  const s = setup();
  s.lease();
  s.key(true);
  assert.equal(s.sends.length, 1);
  assert.equal(s.sends[0].method, '/c1Home');
  s.timers.find((row) => row.ms === 1500).fn();
  s.key(false);
  assert.deepEqual(s.stock, []);
  s.key(true);
  s.key(false);
  assert.equal(s.ysm.state, 'visible');
  assert.equal(s.stock.length, 2);
});

test('a failed or timed-out Home claim recovers LG once and stays disarmed', () => {
  const s = setup();
  s.lease();
  s.key(true);
  s.key(false);
  s.timers.find((row) => row.ms === 3000).fn();
  assert.equal(s.ysm.state, 'visible');
  s.sends[0].callback({ returnValue: false });
  assert.equal(s.ysm.state, 'visible');
  s.lease(2);
  s.key(true);
  s.key(false);
  assert.equal(s.sends.length, 1);
});

test('modal, access and unrelated input remain stock decisions', () => {
  const s = setup();
  s.lease();
  s.alert.modalAlertsVisible = true;
  s.key(true);
  s.key(false);
  s.alert.modalAlertsVisible = false;
  s.ysm.access.keyFilter.home = false;
  s.key(true);
  s.key(false);
  s.key(true, false, 72);
  s.key(false, false, 72);
  assert.equal(s.sends.length, 0);
  assert.equal(s.stock.length, 6);
});

test('gate changes preserve the recipient of an in-progress pair', () => {
  const s = setup();
  s.lease();
  s.key(true);
  s.alert.modalAlertsVisible = true;
  s.key(false);
  assert.deepEqual(s.stock, []);
  s.key(true);
  s.alert.modalAlertsVisible = false;
  s.key(false);
  assert.equal(s.stock.length, 2);
});

test('missing, duplicate or unobservable capabilities leave original policies intact', () => {
  for (const change of [
    (ysm) => {
      ysm.children = [];
    },
    (ysm) => {
      ysm.keyFilter.keyPolicies = [];
    },
    (ysm) => {
      ysm.keyFilter.keyPolicies.push(ysm.keyFilter.keyPolicies[1]);
    },
    (_ysm, api) => {
      delete api.later;
    }
  ]) {
    const s = setup(change);
    assert.equal(s.attachment, null);
    assert.equal(s.messages.length, 0);
  }
});

test('retirement restores only the owned policy slot and preserves concurrent edits', () => {
  const s = setup();
  const foreign = function foreign() {
    return 2;
  };
  s.ysm.keyFilter.keyPolicies.unshift(foreign);
  s.attachment.retire();
  assert.equal(s.ysm.keyFilter.keyPolicies[0], foreign);
  assert.equal(s.ysm.keyFilter.keyPolicies[1], s.earlier);
  assert.equal(s.ysm.keyFilter.keyPolicies[2].name, 'handleSystemKeys');
});

test('an initially stock-owned gesture does not prevent a later healthy capture', () => {
  const s = setup();
  s.key(true);
  s.key(false);
  s.lease();
  s.key(true);
  s.key(false);
  assert.equal(s.sends.length, 1);
  assert.equal(s.stock.length, 2);
});

test('a new physical down recovers from a lost captured release', () => {
  const s = setup();
  s.lease();
  s.key(true);
  s.timers.find((row) => row.ms === 1500).fn();
  s.key(true);
  s.key(false);
  assert.equal(s.ysm.state, 'visible');
  assert.equal(s.stock.length, 2);
});

test('only an installed adapter subscribes with the embedded readiness tag', () => {
  const s = setup();
  assert.deepEqual(s.messages[0].payload, {
    subscribe: true,
    adapter: 'embedded-qml-v1'
  });
  s.lease();
  s.key(true);
  s.key(false);
  assert.deepEqual(s.sends[0].payload, { token: 'a'.repeat(32) });
  s.attachment.retire();
  assert.throws(() =>
    s.ctx.lunaCall.subscribe(
      'com.webos.cleanyourtv.root.lease',
      '/c1Lease',
      '{"subscribe":true}',
      () => {}
    )
  );
  assert.equal(s.messages.length, 1);
});

test('enum and key-dispatch capabilities come from the stock module', () => {
  for (const enums of [
    'var NotAccepted=0, Accepted=1, NextPolicy=1;',
    'var NotAccepted=0, Accepted="1", NextPolicy=2;',
    'var NotAccepted=0, Accepted=1;',
    'var NotAccepted=0, Accepted=1, NextPolicy=NaN;'
  ]) {
    const s = setup(null, enums);
    assert.equal(s.attachment, null);
    assert.equal(s.messages.length, 0);
  }
  for (const change of [
    (ysm) => {
      ysm.keyFilter.pressFunction = 'anotherPress';
    },
    (ysm) => {
      ysm.keyFilter.releaseFunction = 'anotherRelease';
    },
    (ysm) => {
      delete ysm.keyFilter.handleKeyEvents;
    },
    (ysm) => {
      delete ysm.keyFilter.handleKeyReleased;
    }
  ]) {
    const s = setup(change);
    assert.equal(s.attachment, null);
    assert.equal(s.messages.length, 0);
  }
});
