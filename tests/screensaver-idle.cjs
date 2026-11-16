'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const file = path.resolve(__dirname, '../launcher/screensaver-idle.js');
assert.ok(fs.existsSync(file), 'application-owned idle observer must exist');
const createIdle = require(file);
function target() {
  const listeners = new Map();
  return {
    addEventListener(type, fn) {
      const set = listeners.get(type) || new Set();
      set.add(fn);
      listeners.set(type, set);
    },
    removeEventListener(type, fn) {
      listeners.get(type)?.delete(fn);
    },
    emit(type) {
      for (const fn of [...(listeners.get(type) || [])])
        fn({
          type,
          preventDefault() {
            throw new Error('must not suppress keys');
          },
          stopPropagation() {
            throw new Error('must not suppress keys');
          }
        });
    },
    count() {
      return [...listeners.values()].reduce((sum, set) => sum + set.size, 0);
    }
  };
}
function fixture(options = {}) {
  let time = 0,
    focused = true,
    eligible = true,
    timerCount = 0;
  const window = target(),
    document = Object.assign(target(), {
      hidden: false,
      hasFocus: () => focused
    });
  const requests = [],
    timers = new Map(),
    history = [];
  const idle = createIdle({
    window,
    document,
    idleMs: 1000,
    maxTimerDriftMs: 100,
    now: () => time,
    isEligible: () => eligible,
    onIdle: (event) => requests.push(event),
    setTimeout(fn, delay) {
      const entry = { fn, due: time + delay, id: ++timerCount };
      timers.set(entry.id, entry);
      history.push(entry);
      return entry.id;
    },
    clearTimeout(id) {
      timers.delete(id);
    },
    ...options
  });
  function advance(ms) {
    const end = time + ms;
    while (true) {
      const next = [...timers.values()]
        .filter((t) => t.due <= end)
        .sort((a, b) => a.due - b.due)[0];
      if (!next) break;
      time = next.due;
      timers.delete(next.id);
      next.fn();
    }
    time = end;
  }
  return {
    idle,
    window,
    document,
    requests,
    timers,
    history,
    advance,
    setTime(n) {
      time = n;
    },
    setEligible(value) {
      eligible = value;
    },
    setFocus(value) {
      focused = value;
    },
    timerCount: () => timerCount
  };
}
let checks = 0;
function test(name, fn) {
  fn();
  checks++;
  console.log('PASS ' + name);
}
test('input hook can cancel pending preparation before eligibility is rechecked', () => {
  const observed = [];
  const f = fixture({
    onInput: (event) => {
      observed.push(event.type);
      f.setEligible(true);
    }
  });
  f.setEligible(false);
  f.idle.enable();
  assert.deepEqual(observed, []);
  f.document.emit('keydown');
  assert.deepEqual(observed, ['keydown']);
  f.advance(1000);
  assert.equal(f.requests.length, 1);
});
test('construction and disabled mode do not observe input or request presentation', () => {
  const f = fixture();
  assert.equal(f.window.count() + f.document.count(), 0);
  assert.equal(f.timers.size, 0);
  f.advance(10000);
  assert.equal(f.requests.length, 0);
  f.idle.enable();
  f.idle.enable();
  assert.equal(f.timers.size, 1);
  f.idle.disable();
  assert.equal(f.window.count() + f.document.count(), 0);
  assert.equal(f.timers.size, 0);
  f.history[0].fn();
  assert.equal(f.requests.length, 0);
});
test('one idle request per epoch; fresh activity is required for another', () => {
  const f = fixture();
  f.idle.enable();
  f.advance(999);
  assert.equal(f.requests.length, 0);
  f.advance(1);
  assert.equal(f.requests.length, 1);
  assert.equal(f.requests[0].idleMs, 1000);
  f.advance(10000);
  assert.equal(f.requests.length, 1);
  f.document.emit('keydown');
  f.advance(1000);
  assert.equal(f.requests.length, 2);
  assert.notEqual(f.requests[0].epoch, f.requests[1].epoch);
});
test('eligible activity is reported to the owner without reporting hidden input', () => {
  const activity = [];
  const f = fixture({ onActivity: (event) => activity.push(event) });
  f.idle.enable();
  assert.equal(activity.length, 1);
  f.document.emit('keydown');
  assert.equal(activity.length, 2);
  assert.ok(activity[1].epoch > activity[0].epoch);
  f.document.hidden = true;
  f.document.emit('keyup');
  assert.equal(activity.length, 2);
});
test('key down/up, pointer, wheel and touch reset idle without consuming input', () => {
  for (const type of [
    'keydown',
    'keyup',
    'pointerdown',
    'pointerup',
    'pointermove',
    'mousedown',
    'mouseup',
    'mousemove',
    'wheel',
    'touchstart',
    'touchmove',
    'touchend'
  ]) {
    const f = fixture();
    f.idle.enable();
    f.advance(900);
    f.document.emit(type);
    f.advance(999);
    assert.equal(f.requests.length, 0, type);
    f.advance(1);
    assert.equal(f.requests.length, 1, type);
  }
});
test('pointer movement floods do not create a timer for every event', () => {
  const f = fixture();
  f.idle.enable();
  for (let i = 0; i < 5000; i++) {
    f.setTime(i / 10);
    f.document.emit('pointermove');
  }
  assert.equal(f.timerCount(), 1);
  assert.equal(f.timers.size, 1);
  f.advance(1000);
  assert.equal(f.requests.length, 1);
});
test('hidden and unfocused CYTV cannot request and regain starts a fresh interval', () => {
  for (const kind of ['visibility', 'focus']) {
    const f = fixture();
    f.idle.enable();
    f.advance(900);
    if (kind === 'visibility') {
      f.document.hidden = true;
      f.document.emit('visibilitychange');
    } else {
      f.setFocus(false);
      f.window.emit('blur');
    }
    assert.equal(f.timers.size, 0);
    f.advance(10000);
    assert.equal(f.requests.length, 0);
    if (kind === 'visibility') {
      f.document.hidden = false;
      f.document.emit('visibilitychange');
    } else {
      f.setFocus(true);
      f.window.emit('focus');
    }
    f.advance(999);
    assert.equal(f.requests.length, 0);
    f.advance(1);
    assert.equal(f.requests.length, 1);
  }
});
test('eligibility changes, errors and non-boolean results never imply paused playback', () => {
  for (const value of [false, null, undefined, 'paused', 1]) {
    const f = fixture();
    f.setEligible(value);
    f.idle.enable();
    f.advance(5000);
    assert.equal(f.requests.length, 0);
    f.setEligible(true);
    f.idle.refresh();
    f.advance(999);
    assert.equal(f.requests.length, 0);
    f.advance(1);
    assert.equal(f.requests.length, 1);
  }
  const f = fixture({
    isEligible() {
      throw new Error('unknown playback');
    }
  });
  f.idle.enable();
  f.advance(10000);
  assert.equal(f.requests.length, 0);
});
test('expiry rechecks visibility and owner eligibility even if change notifications were missed', () => {
  for (const change of [
    (f) => f.setEligible(false),
    (f) => f.setFocus(false),
    (f) => {
      f.document.hidden = true;
    }
  ]) {
    const f = fixture();
    f.idle.enable();
    f.advance(900);
    change(f);
    f.advance(100);
    assert.equal(f.requests.length, 0);
    assert.equal(f.timers.size, 0);
  }
});
test('stale, delayed and backward-clock timers cannot launch from an old deadline', () => {
  const f = fixture();
  f.idle.enable();
  const old = f.history[0];
  f.idle.disable();
  f.idle.enable();
  old.fn();
  assert.equal(f.requests.length, 0);
  f.advance(1000);
  assert.equal(f.requests.length, 1);
  for (const time of [10000, -1]) {
    const g = fixture();
    g.idle.enable();
    const timer = g.history[0];
    g.timers.delete(timer.id);
    g.setTime(time);
    timer.fn();
    assert.equal(g.requests.length, 0);
  }
});
test('refresh discards already elapsed playback time and invalid clock fails closed', () => {
  const f = fixture();
  f.idle.enable();
  f.advance(900);
  f.idle.refresh();
  f.advance(999);
  assert.equal(f.requests.length, 0);
  f.advance(1);
  assert.equal(f.requests.length, 1);
  const g = fixture({ now: () => NaN });
  g.idle.enable();
  assert.equal(g.timers.size, 0);
  assert.equal(g.requests.length, 0);
});
test('destruction and reentrant disable prevent new callbacks and detach listeners', () => {
  const f = fixture();
  f.idle.enable();
  f.idle.destroy();
  f.idle.enable();
  f.idle.refresh();
  f.advance(5000);
  assert.equal(f.requests.length, 0);
  assert.equal(f.window.count() + f.document.count(), 0);
  let owner;
  const g = fixture({
    isEligible() {
      owner.disable();
      return true;
    }
  });
  owner = g.idle;
  owner.enable();
  assert.equal(g.timers.size, 0);
  g.advance(5000);
  assert.equal(g.requests.length, 0);
});
test('browser factory export is opt-in and throwing consumer is not repeatedly retried', () => {
  const window = target(),
    document = target();
  const context = { window, document };
  vm.runInNewContext(fs.readFileSync(file, 'utf8'), context);
  assert.equal(typeof window.CYTVScreensaverIdle, 'function');
  assert.equal(window.count() + document.count(), 0);
  const f = fixture({
    onIdle() {
      throw new Error('caller refused');
    }
  });
  f.idle.enable();
  assert.doesNotThrow(() => f.advance(1000));
  assert.equal(f.timers.size, 0);
  assert.equal(f.idle.status().requested, true);
});
console.log('PASS screensaver idle: ' + checks + ' cases');
