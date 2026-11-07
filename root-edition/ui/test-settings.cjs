const assert = require('node:assert/strict'),
  vm = require('vm'),
  fs = require('fs');
const buttons = [],
  listeners = {},
  calls = [];
let retry;
let selected,
  phase = 'active',
  restores = 0,
  failLaunch = false,
  delayStatus = false,
  delayLaunch = false,
  gateBackend = false;
const pending = [],
  launches = [],
  timers = new Map();
let nextTimer = 0;
class Element {
  constructor(tag) {
    this.tag = tag;
    this.hidden = false;
    this.disabled = false;
    this.attrs = {};
    if (tag === 'button') buttons.push(this);
  }
  appendChild() {}
  setAttribute(k, v) {
    this.attrs[k] = v;
  }
  focus() {
    selected = this;
    if (this.onfocus) this.onfocus();
  }
}
const document = {
  body: new Element('body'),
  activeElement: {
    focus() {
      selected = 'previous';
    }
  },
  createElement: (t) => new Element(t),
  addEventListener: (n, f) => (listeners[n] = f)
};
const context = {
  window: { close() {}, RootUpdates: { open() {} } },
  document,
  Promise,
  setTimeout(callback, delay) {
    const id = ++nextTimer;
    timers.set(id, { callback, delay });
    return id;
  },
  clearTimeout(id) {
    timers.delete(id);
  },
  createRootExit: (call, launch) => async () => {
    restores++;
    phase = 'disabled';
    await launch();
  },
  PalmServiceBridge: class {
    cancel() {}
    call(uri, raw) {
      calls.push({ uri, payload: JSON.parse(raw) });
      let r = { returnValue: true };
      if (JSON.parse(raw).startup) {
        r.result = {
          returnValue: true,
          result: {
            sources: { tv: true, youtube: false },
            active: phase === 'active'
          }
        };
        this.onservicecallback(JSON.stringify(r));
        return;
      }
      if (uri.endsWith('/status')) {
        if (delayStatus) {
          pending.push(this);
          return;
        }
        r.result = {
          returnValue: true,
          result: {
            intent: { phase },
            effective: gateBackend ? { backend: 'c1-native-gate' } : {}
          }
        };
      }
      if (uri.endsWith('/enable')) {
        phase = 'active';
        r.result = { returnValue: true, result: {} };
      }
      if (uri.endsWith('/launch') && delayLaunch) {
        launches.push(this);
        return;
      }
      if (uri.endsWith('/launch') && failLaunch) r.returnValue = false;
      this.onservicecallback(JSON.stringify(r));
    }
  }
};
vm.runInNewContext(
  fs.readFileSync(__dirname + '/root-settings.js', 'utf8'),
  context
);
const panel = context.window.RenewalPanel,
  tick = () => new Promise((r) => setImmediate(r));
async function nextStatus() {
  await tick();
  return pending.shift();
}
function pollTimer() {
  return [...timers].find(([, timer]) => timer.delay === 1000);
}
async function poll() {
  const entry = pollTimer();
  assert(entry, 'transitional status schedules another read');
  timers.delete(entry[0]);
  entry[1].callback();
  await tick();
}
function key(keyCode) {
  listeners.keydown({
    keyCode,
    preventDefault() {},
    stopImmediatePropagation() {}
  });
}
(async () => {
  panel.open();
  await tick();
  const sources = buttons.filter((b) =>
    ['LG Channels / Live TV', 'YouTube', 'HDMI'].includes(b.textContent)
  );
  assert.equal(sources.length, 2, 'only two startup switches');
  assert(
    !buttons.some((b) => b.textContent === 'HDMI'),
    'no HDMI startup switch'
  );
  assert.equal(sources[0].attrs['aria-checked'], 'true');
  assert.equal(sources[1].attrs['aria-checked'], 'false');
  sources.forEach((b) => buttons.splice(buttons.indexOf(b), 1));
  retry = buttons.splice(
    buttons.findIndex((b) => b.textContent === 'Check status'),
    1
  )[0];
  assert.equal(selected, buttons[0]);
  assert.equal(buttons[0].attrs['aria-checked'], 'true');
  key(39);
  assert.equal(selected, buttons[1]);
  key(13);
  key(13);
  await tick();
  assert.equal(calls.filter((c) => c.uri.endsWith('/launch')).length, 1);
  assert.equal(restores, 0);
  assert.equal(phase, 'active');
  assert(!panel.isOpen());
  panel.open();
  await tick();
  buttons[0].onclick();
  await tick();
  assert.equal(restores, 1);
  assert.equal(buttons[0].attrs['aria-checked'], 'false');
  assert(panel.isOpen());
  assert(
    sources.every((b) => b.disabled),
    'Home Off disables sources'
  );
  const writes = calls.filter((c) => c.payload.startup === 'configure').length;
  sources[0].onclick();
  assert.equal(
    calls.filter((c) => c.payload.startup === 'configure').length,
    writes
  );
  buttons[0].onclick();
  await tick();
  assert.equal(phase, 'active');
  assert.equal(buttons[0].attrs['aria-checked'], 'true');
  assert(!buttons[0].disabled);
  failLaunch = true;
  buttons[1].onclick();
  await tick();
  assert(panel.isOpen());
  assert.equal(phase, 'active');
  assert(!buttons[1].disabled);
  key(461);
  assert(!panel.isOpen());
  // External emergency stop while the real Settings module remains open.
  failLaunch = false;
  panel.open();
  await tick();
  phase = 'disabled';
  delayStatus = true;
  document.hidden = true;
  if (listeners.visibilitychange) listeners.visibilitychange();
  document.hidden = false;
  if (listeners.visibilitychange) listeners.visibilitychange();
  const before = restores;
  buttons[0].onclick();
  await tick();
  assert.equal(
    restores,
    before,
    'resume must invalidate active cache before the first click'
  );
  assert(buttons[0].disabled, 'status unresolved: toggle unavailable');
  assert.equal(pending.length, 1, 'visible resumes status');
  (await nextStatus()).onservicecallback(
    JSON.stringify({
      returnValue: true,
      result: { returnValue: true, result: { intent: { phase: 'disabled' } } }
    })
  );
  await tick();
  assert.equal(buttons[0].attrs['aria-checked'], 'false');
  assert(!buttons[0].disabled);
  delayStatus = false;
  buttons[0].onclick();
  await tick();
  assert.equal(phase, 'active');
  assert.equal(restores, before);
  // Each lifecycle refresh owns a generation, including failures and close/reopen.
  delayStatus = true;
  listeners.webOSRelaunch();
  const old = await nextStatus();
  listeners.webOSRelaunch();
  await tick();
  assert.equal(pending.length, 0, 'a later refresh waits for the active read');
  const reply = (bridge, value) =>
    bridge.onservicecallback(JSON.stringify(value));
  const status = (phase) => ({
    returnValue: true,
    result: { returnValue: true, result: { intent: { phase } } }
  });
  reply(old, status('active'));
  await tick();
  assert(buttons[0].disabled, 'stale completion cannot enable controls');
  reply(await nextStatus(), status('disabled'));
  await tick();
  assert.equal(buttons[0].attrs['aria-checked'], 'false');
  assert.equal(phase, 'active', 'status refresh never mutates backend intent');
  listeners.webOSRelaunch();
  const staleFailure = await nextStatus();
  listeners.webOSRelaunch();
  await tick();
  assert.equal(pending.length, 0);
  reply(staleFailure, { returnValue: false });
  await tick();
  assert(buttons[0].disabled);
  reply(await nextStatus(), status('disabled'));
  await tick();
  assert(!buttons[0].disabled);
  assert(retry.hidden);
  listeners.webOSRelaunch();
  reply(await nextStatus(), { returnValue: false });
  await tick();
  assert(buttons[0].disabled);
  assert(!retry.hidden);
  assert(!retry.disabled);
  retry.onclick();
  reply(await nextStatus(), {
    returnValue: true,
    result: { returnValue: true, result: {} }
  });
  await tick();
  assert(buttons[0].disabled);
  assert(!retry.hidden, 'malformed successful status offers read-only retry');
  const enables = calls.filter((c) => c.uri.endsWith('/enable')).length;
  buttons[0].onclick();
  assert.equal(calls.filter((c) => c.uri.endsWith('/enable')).length, enables);
  retry.onclick();
  assert(retry.hidden);
  reply(await nextStatus(), status('disabled'));
  await tick();
  assert(!buttons[0].disabled);
  assert.equal(restores, before);
  listeners.webOSRelaunch();
  const closed = await nextStatus();
  key(461);
  assert(!panel.isOpen());
  panel.open();
  await tick();
  assert.equal(pending.length, 0);
  reply(closed, status('active'));
  await tick();
  assert(buttons[0].disabled);
  reply(await nextStatus(), status('disabled'));
  await tick();
  assert.equal(buttons[0].attrs['aria-checked'], 'false');
  // Hiding invalidates an in-flight reply even before the visible event arrives.
  listeners.webOSRelaunch();
  const hidden = await nextStatus();
  document.hidden = true;
  listeners.visibilitychange();
  reply(hidden, status('active'));
  await tick();
  assert(buttons[0].disabled);
  document.hidden = false;
  listeners.visibilitychange();
  reply(await nextStatus(), status('disabled'));
  await tick();
  delayStatus = false;
  phase = 'disabled';
  buttons[0].onclick();
  await tick();
  assert.equal(phase, 'active');
  assert.equal(restores, before);
  buttons[0].onclick();
  await tick();
  assert.equal(phase, 'disabled');
  assert.equal(restores, before + 1);
  listeners.webOSRelaunch();
  await tick();
  assert.equal(phase, 'disabled', 'explicit Off survives relaunch');
  assert.equal(
    calls.filter((c) => c.uri.endsWith('/enable')).length,
    enables + 1,
    'only explicit later click enables'
  );
  // Audio/Firmware hide only the parent panel; resume still invalidates it.
  phase = 'active';
  listeners.webOSRelaunch();
  await tick();
  let childClose;
  context.window.RootAudio = {
    open(_request, onClose) {
      childClose = onClose;
    }
  };
  buttons.find((b) => b.textContent === 'HDMI sound').onclick();
  assert(!panel.isOpen());
  phase = 'disabled';
  listeners.webOSRelaunch();
  delayStatus = true;
  childClose();
  assert(buttons[0].disabled, 'child return waits for fresh Home status');
  reply(await nextStatus(), status('disabled'));
  await tick();
  assert(!buttons[0].disabled);
  // A delayed failed one-time visit after resume cannot leave an inert enabled toggle.
  delayLaunch = true;
  buttons[1].onclick();
  listeners.webOSRelaunch();
  reply(launches.shift(), { returnValue: false });
  await tick();
  assert(
    buttons[0].disabled,
    'failed visit after resume must refresh before re-enabling'
  );
  assert.equal(pending.length, 1);
  reply(await nextStatus(), status('disabled'));
  await tick();
  assert(!buttons[0].disabled);
  delayStatus = false;
  delayLaunch = false;
  // A transitional reply must converge without another user action or write.
  const pollingEnables = calls.filter((c) => c.uri.endsWith('/enable')).length;
  phase = 'enabling';
  listeners.webOSRelaunch();
  await tick();
  assert(buttons[0].disabled);
  phase = 'active';
  await poll();
  assert(!buttons[0].disabled, 'follow-up status unlocks Change Home');
  assert.equal(buttons[0].attrs['aria-checked'], 'true');
  assert.equal(pollTimer(), undefined, 'stable active stops polling');
  assert(retry.hidden);
  // A bounded wait eventually offers the existing read-only manual retry.
  phase = 'disabling';
  listeners.webOSRelaunch();
  await tick();
  let polls = 0;
  while (pollTimer() && polls < 20) {
    await poll();
    polls++;
  }
  assert(polls > 0 && polls < 20, 'transitional polling has a finite budget');
  assert.equal(pollTimer(), undefined);
  assert(buttons[0].disabled);
  assert(
    !retry.hidden && !retry.disabled,
    'exhausted wait offers Check status'
  );
  phase = 'disabled';
  retry.onclick();
  await tick();
  assert(!buttons[0].disabled);
  assert.equal(pollTimer(), undefined, 'stable disabled does not poll');
  // Close, background, relaunch and child-panel hide cancel scheduled reads.
  for (const [cancel, resume] of [
    [() => key(461), () => panel.open()],
    [
      () => {
        document.hidden = true;
        listeners.visibilitychange();
      },
      () => {
        document.hidden = false;
      }
    ],
    [() => listeners.webOSRelaunch(), () => {}],
    [
      () => buttons.find((b) => b.textContent === 'HDMI sound').onclick(),
      () => childClose()
    ]
  ]) {
    phase = 'enabling';
    listeners.webOSRelaunch();
    await tick();
    const timer = pollTimer();
    assert(timer);
    const reads = calls.length;
    cancel();
    assert(!timers.has(timer[0]), 'lifecycle invalidation clears poll timer');
    timer[1].callback();
    assert.equal(calls.length, reads, 'even a queued stale timer does no work');
    phase = 'disabled';
    resume();
    listeners.visibilitychange();
    await tick();
    assert(!buttons[0].disabled);
    assert.equal(pollTimer(), undefined);
  }
  // A user action cancels the wait and finishes without awaiting the polling budget.
  phase = 'enabling';
  listeners.webOSRelaunch();
  await tick();
  delayLaunch = true;
  buttons[1].onclick();
  assert.equal(pollTimer(), undefined, 'busy visit cancels scheduled polling');
  reply(launches.shift(), { returnValue: false });
  await tick();
  assert(!buttons[1].disabled, 'completed action releases its busy state');
  assert(
    pollTimer(),
    'completed action independently refreshes transitional status'
  );
  delayLaunch = false;
  // An in-flight poll cannot paint an old generation or schedule more reads.
  phase = 'enabling';
  listeners.webOSRelaunch();
  await tick();
  delayStatus = true;
  await poll();
  const stalePoll = await nextStatus();
  listeners.webOSRelaunch();
  reply(stalePoll, status('active'));
  await tick();
  assert(buttons[0].disabled);
  assert.equal(pollTimer(), undefined);
  reply(await nextStatus(), status('disabled'));
  await tick();
  assert(!buttons[0].disabled);
  // Request timeouts retain explicit retry, with no automatic writes.
  listeners.webOSRelaunch();
  const timedOut = await nextStatus();
  const timeout = [...timers].find(([, timer]) => timer.delay === 30000);
  assert(timeout, 'status request still owns its timeout');
  timers.delete(timeout[0]);
  timeout[1].callback();
  await tick();
  assert(!retry.hidden && !retry.disabled);
  assert.equal(pollTimer(), undefined);
  reply(timedOut, status('active'));
  await tick();
  assert(buttons[0].disabled, 'late timed-out response cannot enable controls');
  delayStatus = false;
  retry.onclick();
  await tick();
  assert.equal(
    calls.filter((c) => c.uri.endsWith('/enable')).length,
    pollingEnables,
    'polling, exhaustion and lifecycle recovery never enable Home'
  );
  gateBackend = true;
  phase = 'active';
  listeners.webOSRelaunch();
  await tick();
  const gateRestores = restores;
  buttons[1].onclick();
  await tick();
  assert.equal(
    restores,
    gateRestores + 1,
    'experimental LG Home releases routing before launch'
  );
  assert.equal(phase, 'disabled', 'experimental visit does not silently rearm');
  console.log(
    'PASS Root switch, one-time visit, failure recovery, duplicate suppression and remote focus'
  );
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
