// webos-service changes process.title; live detection must survive that rename
// while rejecting stale PIDs pointing at a different process.
const fs = require('fs'),
  vm = require('vm'),
  assert = require('node:assert/strict');
let cmdline = 'com.local.nativehome\0\0',
  pid = '4321';
const methods = {};
const fakefs = {
  readFileSync(p) {
    if (p.endsWith('/controller.pid')) return pid;
    if (p === '/proc/4321/cmdline') return cmdline;
    throw Object.assign(Error('missing'), { code: 'ENOENT' });
  },
  statSync() {
    throw Object.assign(Error('missing'), { code: 'ENOENT' });
  }
};
vm.runInNewContext(fs.readFileSync('native/service/service.js', 'utf8'), {
  console,
  __dirname: '/service',
  require(n) {
    if (n === 'fs') return fakefs;
    if (n === 'webos-service')
      return class {
        constructor() {
          this.register = (n, f) => (methods[n] = f);
        }
      };
    if (n === './boot-state') return { identity: () => ({}), claim() {} };
    if (n === './state-permissions') return () => true;
    throw Error(n);
  }
});
// Status also reads boot files; keep those fixtures separate from process identity.
const read = fakefs.readFileSync;
fakefs.readFileSync = (p) =>
  p === '/proc/sys/kernel/random/boot_id'
    ? 'test-boot'
    : p === '/proc/stat'
      ? 'btime 1'
      : read(p);
function status() {
  let reply;
  methods.status({ respond: (r) => (reply = r) });
  assert.equal(reply.returnValue, true);
  return reply;
}
assert.equal(status().running, true, 'renamed live controller is running');
cmdline = 'unrelated-process\0';
assert.equal(status().running, false, 'stale PID is not running Helper');
cmdline =
  'node\0/media/developer/apps/usr/palm/applications/com.local.nativehome/native.js\0';
assert.equal(
  status().running,
  true,
  'recognize startup before process title changes'
);
pid = '../bad';
assert.equal(status().running, false, 'reject invalid PID before reading proc');
console.log(
  'PASS Helper status after process rename, startup, stale PID and invalid PID'
);

// A watchdog orphan must suppress automatic boot just like an emergency stop.
for (const name of ['blocked', 'watchdog']) {
  fakefs.statSync = (p) => {
    if (p.endsWith('/' + name)) return {};
    throw Object.assign(Error('missing'), { code: 'ENOENT' });
  };
  assert.equal(
    status().blocked,
    true,
    name + ' latch visible to boot/status service'
  );
}
