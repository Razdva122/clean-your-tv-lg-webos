const fs = require('fs'),
  vm = require('vm'),
  a = require('node:assert/strict'),
  { EventEmitter } = require('events'),
  legacyPing = require('../app/vendor/ws-legacy').prototype.ping;
const source = fs.readFileSync(require.resolve('../app/screen-watch'), 'utf8');
function setup(withPower, secure = true) {
  let seq = 0,
    timers = new Map(),
    logs = [],
    events = [],
    power = [],
    resets = 0,
    reads = 0;
  class WS extends EventEmitter {
    constructor(url, opts) {
      super();
      this.url = url;
      this.sent = [];
      this.readyState = 1;
      // Substitute the transport, retaining the real legacy ws ping contract.
      this._sender = {
        ping: (data, mask, cb) => {
          this.pings = (this.pings || 0) + 1;
          if (cb) cb();
        }
      };
      WS.last = this;
    }
    send(v) {
      this.sent.push(JSON.parse(v));
    }
    terminate() {
      if (!this.ended) {
        this.ended = true;
        this.emit('close', 1006);
      }
    }
    ping(cb) {
      return legacyPing.call(this, cb);
    }
  }
  const sandbox = {
    module: { exports: {} },
    require(n) {
      return n === './state-permissions'
        ? () => (typeof secure === 'function' ? secure() : secure)
        : n === 'fs'
          ? {
              readFileSync: () => {
                reads++;
                return '{"key":"private-test-key"}';
              }
            }
          : n === 'os'
            ? {
                networkInterfaces: () => ({
                  lo: [
                    { internal: true, family: 'IPv4', address: '127.0.0.1' }
                  ],
                  wlan: [
                    { internal: false, family: 'IPv4', address: '192.0.2.50' }
                  ]
                })
              }
            : WS;
    },
    setTimeout(f, ms) {
      timers.set(++seq, { f, ms });
      return seq;
    },
    clearTimeout(i) {
      timers.delete(i);
    },
    setInterval(f, ms) {
      timers.set(++seq, { f, ms, interval: true });
      return seq;
    },
    clearInterval(i) {
      timers.delete(i);
    }
  };
  vm.runInNewContext(source, sandbox);
  let watcher = sandbox.module.exports(
    '/state',
    (x) => logs.push(x),
    (x) => events.push(x),
    () => resets++,
    withPower ? (x) => power.push(x) : undefined
  );
  return {
    watcher,
    WS,
    logs,
    events,
    power,
    timers,
    resets: () => resets,
    reads: () => reads
  };
}
let t = setup(),
  s = t.WS.last;
a.equal(s.url, 'wss://192.0.2.50:3001');
s.emit('open');
a.equal(s.sent[0].payload['client-key'], 'private-test-key');
a.deepEqual(
  Array.from(s.sent[0].payload.manifest.permissions),
  [
    'READ_APP_STATUS',
    'READ_RUNNING_APPS',
    'READ_POWER_STATE',
    'CONTROL_POWER',
    'READ_INSTALLED_APPS',
    'READ_INPUT_DEVICE_LIST'
  ],
  'screen watcher and inventory retain the same full SSAP permission set'
);

s.emit('message', JSON.stringify({ type: 'registered' }));
a.equal(s.sent[1].type, 'subscribe');
s.emit(
  'message',
  JSON.stringify({
    id: 'foreground',
    type: 'response',
    payload: { appId: 'app' }
  })
);
a.deepEqual(t.events, ['app']);
a.equal([...t.timers.values()].filter((x) => x.interval).length, 1);
t.watcher.close();
s.emit(
  'message',
  JSON.stringify({ id: 'foreground', payload: { appId: 'com.webos.app.home' } })
);
a.deepEqual(t.events, ['app']);
a.equal(t.timers.size, 0);
a.equal(JSON.stringify(t.logs).includes('private-test-key'), false);
t = setup();
s = t.WS.last;
s.emit(
  'message',
  JSON.stringify({ type: 'error', error: '401 insufficient permissions' })
);
a.equal(t.timers.size, 0);
t = setup();
s = t.WS.last;
s.terminate();
a.equal([...t.timers.values()][0].ms, 10000);
console.log(
  'PASS: local endpoint, registration, subscription, stop, key redaction, permanent error, reconnect'
);

t = setup(true);
s = t.WS.last;
s.emit('message', JSON.stringify({ type: 'registered' }));
a.equal(s.sent[1].id, 'power');
s.emit(
  'message',
  JSON.stringify({
    id: 'power',
    type: 'response',
    payload: { returnValue: true, state: 'Active Standby' }
  })
);
a.equal(t.power[0].state, 'Active Standby');
s.emit(
  'message',
  JSON.stringify({ id: 'power', type: 'error', error: '403 access denied' })
);
a.equal(s.ended, undefined);
t.watcher.close();
s.emit(
  'message',
  JSON.stringify({ id: 'power', payload: { state: 'Active' } })
);
a.equal(t.power.length, 1);
console.log(
  'PASS: power subscription, isolated permission failure, stopped power callback'
);

t = setup(false, false);
a.equal(t.WS.last, undefined);
a.equal(t.logs[0].reason, 'state-permissions');
a.equal(t.reads(), 0);
a.equal(t.timers.size, 1, 'unsafe boot permissions must schedule recovery');
t.watcher.close();
a.equal(t.timers.size, 0, 'stop cancels pending permission recovery');
let safe = false;
t = setup(true, () => safe);
function retryPermissionCheck() {
  const [id, timer] = [...t.timers.entries()][0];
  t.timers.delete(id);
  timer.f();
}
retryPermissionCheck();
a.equal(t.WS.last, undefined);
a.equal(t.reads(), 0, 'never read the key while state is unsafe');
a.equal(t.timers.size, 1);
a.equal([...t.timers.values()][0].ms, 20000);
safe = true;
retryPermissionCheck();
s = t.WS.last;
a.ok(s, 'monitor connects after boot permissions become safe');
a.equal(t.reads(), 1);
s.emit('open');
s.emit('message', JSON.stringify({ type: 'registered' }));
s.emit(
  'message',
  JSON.stringify({ id: 'foreground', payload: { appId: 'app' } })
);
s.emit(
  'message',
  JSON.stringify({ id: 'power', payload: { state: 'Active' } })
);
a.deepEqual(t.events, ['app']);
a.equal(t.power[0].state, 'Active');
a.equal(JSON.stringify(t.logs).includes('private-test-key'), false);
t.watcher.close();
a.equal(t.timers.size, 0);
console.log(
  'PASS: unsafe boot retries without key access, recovery enables foreground/power monitoring, stop cancels retries'
);

function registered() {
  const t = setup(true),
    s = t.WS.last;
  s.emit('open');
  s.emit('message', JSON.stringify({ type: 'registered' }));
  return { t, s };
}
function foregroundRequest(t, s, results) {
  t.watcher.foreground((v) => results.push(v));
  return s.sent.at(-1);
}
function fireTimer(t, ms) {
  const entry = [...t.timers.entries()].find(
    ([, v]) => v.ms === ms && !v.interval
  );
  a.ok(entry, 'expected ' + ms + 'ms timer');
  t.timers.delete(entry[0]);
  entry[1].f();
}
{
  const t = setup(),
    out = [];
  a.equal(typeof t.watcher.foreground, 'function');
  t.watcher.foreground((v) => out.push(v));
  a.deepEqual(out, [null]);
  a.equal(t.WS.last.sent.length, 0);
  t.watcher.close();
}
{
  const { t, s } = registered(),
    out = [];
  const request = foregroundRequest(t, s, out);
  a.equal(request.type, 'request');
  a.equal(
    request.uri,
    'ssap://com.webos.applicationManager/getForegroundAppInfo'
  );
  a.deepEqual(request.payload, {});
  a.notEqual(request.id, 'foreground');
  a.equal([...t.timers.values()].filter((v) => v.ms === 800).length, 1);
  s.emit(
    'message',
    JSON.stringify({
      type: 'response',
      id: 'wrong-id',
      payload: { appId: 'wrong' }
    })
  );
  a.deepEqual(out, []);
  const second = [];
  t.watcher.foreground((v) => second.push(v));
  a.deepEqual(second, [null]);
  a.equal(s.sent.at(-1).id, request.id);
  s.emit(
    'message',
    JSON.stringify({
      type: 'response',
      id: request.id,
      payload: { appId: 'test.app' }
    })
  );
  a.deepEqual(out, ['test.app']);
  a.deepEqual(t.events, [], 'fresh reply is not a subscription event');
  s.emit(
    'message',
    JSON.stringify({
      type: 'response',
      id: request.id,
      payload: { appId: 'late' }
    })
  );
  a.deepEqual(out, ['test.app']);
  a.equal([...t.timers.values()].filter((v) => v.ms === 800).length, 0);
  t.watcher.close();
}
for (const bad of [
  { type: 'error', error: '403 denied' },
  { type: 'response', payload: { returnValue: false, appId: 'bad' } },
  { type: 'response', payload: { returnValue: 'true', appId: 'bad' } },
  { type: 'response', payload: { appId: 7 } },
  { type: 'response', payload: { appId: '' } },
  { type: 'response', payload: null },
  { type: 'event', payload: { appId: 'bad' } }
]) {
  const { t, s } = registered(),
    out = [],
    q = foregroundRequest(t, s, out);
  s.emit('message', JSON.stringify({ ...bad, id: q.id }));
  a.deepEqual(out, [null]);
  a.equal(s.ended, undefined, 'one-shot refusal must not stop subscriptions');
  t.watcher.close();
}
for (const invalid of ['not-json', 'null', '[]']) {
  const { t, s } = registered(),
    out = [];
  foregroundRequest(t, s, out);
  s.emit('message', invalid);
  a.deepEqual(out, [null]);
  t.watcher.close();
}
{
  const { t, s } = registered(),
    out = [],
    q = foregroundRequest(t, s, out);
  fireTimer(t, 800);
  a.deepEqual(out, [null]);
  const newer = [],
    next = foregroundRequest(t, s, newer);
  a.notEqual(next.id, q.id);
  s.emit(
    'message',
    JSON.stringify({ type: 'response', id: q.id, payload: { appId: 'stale' } })
  );
  a.deepEqual(newer, []);
  s.emit(
    'message',
    JSON.stringify({
      type: 'response',
      id: next.id,
      payload: { returnValue: true, appId: 'current' }
    })
  );
  a.deepEqual(newer, ['current']);
  t.watcher.close();
}
for (const reason of ['close', 'error', 'stop', 'global-error', 'pairing']) {
  const { t, s } = registered(),
    out = [],
    q = foregroundRequest(t, s, out);
  if (reason === 'close') s.terminate();
  if (reason === 'error')
    s.emit('error', Object.assign(Error('network'), { code: 'EIO' }));
  if (reason === 'stop') t.watcher.close();
  if (reason === 'global-error')
    s.emit(
      'message',
      JSON.stringify({ type: 'error', error: '500 disconnected' })
    );
  if (reason === 'pairing')
    s.emit('message', JSON.stringify({ payload: { pairingType: 'PROMPT' } }));
  a.deepEqual(out, [null], reason);
  s.emit(
    'message',
    JSON.stringify({ type: 'response', id: q.id, payload: { appId: 'late' } })
  );
  a.deepEqual(out, [null], reason);
  t.watcher.close();
  a.equal(t.timers.size, 0);
}
{
  const { t, s } = registered(),
    out = [],
    q = foregroundRequest(t, s, out);
  s.terminate();
  a.deepEqual(out, [null]);
  fireTimer(t, 10000);
  const newerSocket = t.WS.last;
  a.notEqual(newerSocket, s);
  const unready = [];
  t.watcher.foreground((v) => unready.push(v));
  a.deepEqual(unready, [null]);
  newerSocket.emit('open');
  newerSocket.emit('message', JSON.stringify({ type: 'registered' }));
  const newer = [],
    next = foregroundRequest(t, newerSocket, newer);
  s.emit(
    'message',
    JSON.stringify({
      type: 'response',
      id: next.id,
      payload: { appId: 'old-socket' }
    })
  );
  s.emit('close', 1006);
  s.emit('error', Error('old'));
  a.deepEqual(newer, []);
  newerSocket.emit(
    'message',
    JSON.stringify({
      type: 'response',
      id: next.id,
      payload: { appId: 'new-socket' }
    })
  );
  a.deepEqual(newer, ['new-socket']);
  t.watcher.close();
}
{
  const { t, s } = registered(),
    out = [];
  s.send = () => {
    throw Error('send failure');
  };
  t.watcher.foreground((v) => out.push(v));
  a.deepEqual(out, [null]);
  t.watcher.close();
}
{
  const { t, s } = registered(),
    out = [],
    q = foregroundRequest(t, s, out),
    oldTimer = [...t.timers.values()].find((v) => v.ms === 800).f;
  s.emit(
    'message',
    JSON.stringify({ type: 'response', id: q.id, payload: { appId: 'first' } })
  );
  const newer = [],
    next = foregroundRequest(t, s, newer);
  oldTimer();
  a.deepEqual(newer, [], 'queued old timer cannot settle a newer request');
  s.emit(
    'message',
    JSON.stringify({ id: 'power', type: 'error', error: '403 isolated' })
  );
  a.deepEqual(newer, []);
  s.emit(
    'message',
    JSON.stringify({
      id: 'foreground',
      type: 'response',
      payload: { appId: 'subscription' }
    })
  );
  a.deepEqual(t.events, ['subscription']);
  a.deepEqual(newer, []);
  s.emit(
    'message',
    JSON.stringify({
      id: next.id,
      type: 'response',
      payload: { appId: 'fresh' }
    })
  );
  a.deepEqual(newer, ['fresh']);
  a.deepEqual(t.events, ['subscription']);
  t.watcher.close();
}
for (const state of [2, 3]) {
  // Power-off: the socket can stop being OPEN before close clears the timer.
  const t = setup(),
    s = t.WS.last;
  s.emit('open');
  s.emit('message', JSON.stringify({ type: 'registered' }));
  s.emit(
    'message',
    JSON.stringify({
      id: 'foreground',
      type: 'response',
      payload: { appId: 'app' }
    })
  );
  const beat = [...t.timers.values()].find((x) => x.interval).f,
    resets = t.resets();
  s.readyState = state;
  a.doesNotThrow(
    beat,
    'heartbeat on socket state ' + state + ' must not throw'
  );
  a.equal(s.ended, undefined);
  beat();
  a.equal(s.ended, true, 'a missed pong still terminates the socket');
  a.equal(t.resets(), resets + 1, 'termination resets the foreground state');
  a.equal([...t.timers.values()].filter((x) => x.interval).length, 0);
  fireTimer(t, 10000);
  a.notEqual(t.WS.last, s, 'a failed heartbeat still allows reconnection');
  t.watcher.close();
  a.equal(t.timers.size, 0);
}
{
  const { t, s } = registered();
  s.emit(
    'message',
    JSON.stringify({ id: 'foreground', payload: { appId: 'app' } })
  );
  const beat = [...t.timers.values()].find((x) => x.interval).f;
  beat();
  a.equal(s.pings, 1, 'the heartbeat invokes the legacy ws ping sender');
  s.emit('pong');
  beat();
  a.equal(s.pings, 2, 'a pong permits the next heartbeat');
  a.equal(s.ended, undefined, 'a responsive socket stays connected');
  beat();
  a.equal(s.ended, true, 'a missing pong still terminates an OPEN socket');
  t.watcher.close();
  a.equal(t.timers.size, 0);
}
console.log(
  'PASS: legacy ws CLOSING/CLOSED heartbeat, reconnect, pong and timeout'
);
console.log(
  'PASS: fresh registered foreground request, correlation, timeout, reset/close/errors, stale socket and single settlement'
);
