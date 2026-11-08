// Standard IR remote Home (#207): the relay reports IRHOME without grabbing the remote, so the
// real controller opens custom Home only after IR_HOME_DELAY, once for repeated presses, and
// never when Home control is Off or after the relay reported its emergency exit.
const fs = require('fs'),
  vm = require('vm'),
  assert = require('node:assert/strict'),
  EventEmitter = require('events');
let now = 1000,
  worker,
  tick,
  timerId = 0;
const launches = [],
  files = new Map(),
  timers = new Map();
function Service() {
  this.register = () => {};
  this.activityManager = { create() {} };
  this.call = (uri, p, cb) => {
    if (uri.endsWith('/launch')) launches.push(p.id);
    cb({ payload: { returnValue: true, state: { enabled: true, schema: 3 } } });
  };
}
const fakefs = {
  existsSync: () => false,
  writeFileSync: (p, s) => files.set(p, s),
  renameSync: (a, b) => {
    files.set(b, files.get(a));
    files.delete(a);
  },
  chmodSync() {},
  unlinkSync() {},
  appendFileSync() {},
  readFileSync(p) {
    if (p.endsWith('apps.json')) return '["test.app"]';
    if (files.has(p)) return files.get(p);
    const e = new Error('missing');
    e.code = 'ENOENT';
    throw e;
  }
};
const context = {
  Buffer,
  require(n) {
    if (n === './state-permissions') return () => true;
    if (n === 'fs') return fakefs;
    if (n === 'child_process')
      return {
        spawn() {
          worker = new EventEmitter();
          worker.stdout = new EventEmitter();
          worker.stderr = new EventEmitter();
          worker.stdin = new EventEmitter();
          worker.stdin.write = () => {};
          worker.stdin.end = () => {};
          return worker;
        }
      };
    if (n === '/usr/lib/node_modules/webos-service') return Service;
    if (n === './screen-watch')
      return () => ({
        foreground(done) {
          done('test.app');
        },
        close() {}
      });
    return require('../native/app/' + n.slice(2));
  },
  process: {
    argv: ['node', 'app', '{"nativeHomeAuto":true}'],
    pid: 1,
    getuid: () => 5431,
    hrtime: () => [Math.floor(now / 1000), (now % 1000) * 1e6],
    on() {},
    exit() {}
  },
  setTimeout(fn, ms) {
    timers.set(++timerId, { fn, ms });
    return timerId;
  },
  clearTimeout(id) {
    timers.delete(id);
  },
  setInterval(fn) {
    tick = fn;
  },
  clearInterval() {}
};
// Run (and drop) every pending timer with this delay.
function fire(ms) {
  for (const [id, t] of [...timers]) {
    if (t.ms !== ms) continue;
    timers.delete(id);
    t.fn();
  }
}
const pending = (ms) => [...timers.values()].filter((t) => t.ms === ms).length;
const relay = (line) => worker.stdout.emit('data', Buffer.from(line + '\n'));
let seq = 0;
function rpc(n, p = {}) {
  const dir =
    '/media/developer/apps/usr/palm/applications/com.local.nativehome/state';
  files.set(
    dir + '/home-request.json',
    JSON.stringify({
      id: (++seq).toString(16).padStart(32, '0'),
      method: n,
      enabled: p.enabled,
      expires: Date.now() + 5000
    })
  );
  tick();
  return JSON.parse(files.get(dir + '/home-response.json'));
}

vm.runInNewContext(fs.readFileSync('native/app/native.js', 'utf8'), context);
fire(0);
relay('READY');
const homes = () => launches.filter((id) => id === 'com.gathin.tvhome').length;
const base = homes();

relay('IRHOME');
assert.equal(homes(), base, 'IR Home waits for LG Home to open first');
assert.equal(pending(700), 1);
fire(700);
assert.equal(homes(), base + 1, 'IR Home opens custom Home after the delay');

relay('IRHOME');
relay('IRHOME');
assert.equal(pending(700), 1, 'repeated IR Home restarts the delay');
fire(700);
assert.equal(homes(), base + 2, 'repeated IR Home opens custom Home once');

assert.equal(rpc('setHomeControl', { enabled: false }).enabled, false);
relay('IRHOME');
fire(700);
assert.equal(homes(), base + 2, 'Home control Off leaves IR Home to webOS');
rpc('setHomeControl', { enabled: true });

relay('IRHOME');
relay('EXIT 27');
fire(700);
assert.equal(homes(), base + 2, 'no custom Home after the triple-Home exit');
console.log(
  'PASS real controller: IR Home after delay, coalesced repeats, none while Off or after emergency exit'
);
