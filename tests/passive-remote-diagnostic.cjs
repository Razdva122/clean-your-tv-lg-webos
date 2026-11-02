'use strict';
const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const filename = 'scripts/passive-remote-diagnostic.js';
assert.ok(fs.existsSync(filename), 'passive diagnostic implementation must exist');
const source = fs.readFileSync(filename, 'utf8');
require('acorn').parse(source, {ecmaVersion: 5});
function event(code, value, type = 1) {
  const b = Buffer.alloc(16); b.writeUInt16LE(type, 8); b.writeUInt16LE(code, 10); b.writeInt32LE(value, 12); return b;
}
function run(devices, options = {}) {
  let now = 0, next = 10, calls = 0, result, timer, handlers = {};
  const opened = [], closed = [], handles = {};
  const error = code => Object.assign(new Error('PRIVATE_SECRET_PATH'), {code});
  const fakeFs = {
    openSync(path, flags) {
      assert.match(path, /^\/(sys\/class\/input\/event(?:[0-9]|[12][0-9]|3[01])\/device\/name|dev\/input\/event(?:[0-9]|[12][0-9]|3[01]))$/);
      const i = Number(path.match(/event(\d+)/)[1]); const dev = devices[i];
      if (!dev || dev.denied) throw error('EACCES');
      const kind = path.startsWith('/sys') ? 'name' : 'event';
      assert.equal(flags, kind === 'name' ? 0 : 0x20800);
      if (dev.symlink && kind === 'event') throw error('ELOOP');
      const fd = next++; handles[fd] = {i, kind, offset: 0}; opened.push(fd); return fd;
    },
    fstatSync(fd) { const d = devices[handles[fd].i]; return {isCharacterDevice: () => !d.regular, rdev: d.wrongDevice ? 999 : 0xd40 + handles[fd].i}; },
    readSync(fd, buffer, offset, length) {
      const h = handles[fd], d = devices[h.i];
      if (h.kind === 'event') { calls++; if (d.readError) throw error('EIO'); }
      const data = h.kind === 'name' ? Buffer.from(d.name) : (d.flood ? event(773, 2) : Buffer.concat(d.events || []));
      if (h.kind === 'event' && d.flood) {data.copy(buffer, offset); return data.length;}
      if (h.offset >= data.length) { if (h.kind === 'name') return 0; throw error('EAGAIN'); }
      const n = Math.min(length, data.length - h.offset, (h.kind === 'event' ? d.chunk : d.nameChunk) || length);
      data.copy(buffer, offset, h.offset, h.offset + n); h.offset += n; return n;
    },
    closeSync(fd) { assert.ok(handles[fd]); delete handles[fd]; closed.push(fd); }
  };
  const processFake = {platform: options.platform || 'linux', arch: options.arch || 'arm', hrtime: () => [Math.floor(now / 1000), (now % 1000) * 1e6], on: (s, f) => {handlers[s] = f;}, removeListener: s => {delete handlers[s];}};
  const context = {Buffer, module: {exports: {}}, process: processFake,
    require(name) {if (name === 'fs') return fakeFs; if (name === 'os') return {endianness: () => options.endian || 'LE'}; if (name === 'constants') return options.noFlags ? {} : {O_RDONLY: 0, O_NONBLOCK: 0x800, O_NOFOLLOW: 0x20000}; throw Error('forbidden module: ' + name);},
    setTimeout(fn) {timer = fn; return 1;}, clearTimeout() {timer = null;}};
  vm.runInNewContext(source, context);
  context.module.exports.run(r => {result = JSON.parse(JSON.stringify(r));});
  let ticks = 0;
  while (!result && ticks++ < 600) {now = options.reverseClock ? -1 : options.frozenClock ? 0 : now + 20; if (options.cancel && ticks === 1) handlers.SIGINT(); else {const fn = timer; timer = null; assert.ok(fn); fn();}}
  assert.ok(result, 'bounded completion'); assert.deepEqual(closed.sort(), opened.sort(), 'close every descriptor');
  assert.equal(Object.keys(handlers).length, 0, 'remove cancellation handlers');
  assert.ok(!JSON.stringify(result).match(/PRIVATE|\/dev|\/sys|LGE|serial|timestamp/));
  return {result, calls, ticks};
}
let r = run({0: {name: 'LGE RCU\n', events: [event(773, 1), event(773, 2), event(773, 0), event(4, 1), event(4, 0)]}});
assert.deepEqual(r.result.observations, [{role: 'ir', candidate_code: 773, completed_pair: true}]);
assert.equal(r.result.home_mapping_verified, false);
assert.equal(r.result.status, 'observed_candidate');
assert.equal(r.calls, 1, 'stop consuming a role after its first completed pair');
r = run({0: {name: 'LGE M-RCU - Builtin [0]\n', chunk: 3, events: [event(2048, 1), event(2048, 0), event(2047, 1), event(2047, 0)]}, 1: {name: 'LGE Simple Premium\n', events: [event(0, 1), event(0, 0)]}});
assert.deepEqual(r.result.observations.sort((a, b) => a.role.localeCompare(b.role)), [{role: 'magic_builtin', candidate_code: 2047, completed_pair: true}, {role: 'simple_premium', candidate_code: 0, completed_pair: true}]);
for (const name of ['LGE M-RCU - Builtin [1]\n', 'PRIVATE_SECRET_PATH\n', 'LGE RCU\nextra', 'LGE RCU\0', 'LGE RCU'.repeat(60)]) assert.equal(run({0: {name, events: [event(773, 1), event(773, 0)]}}).calls, 0);
for (const option of [{regular: true}, {wrongDevice: true}, {symlink: true}, {denied: true}]) assert.equal(run({0: Object.assign({name: 'LGE RCU\n'}, option)}).calls, 0);
for (const options of [{arch: 'x64'}, {platform: 'darwin'}, {endian: 'BE'}, {noFlags: true}]) assert.equal(run({0: {name: 'LGE RCU\n'}}, options).result.reason, 'unsupported_runtime');
r = run({0: {name: 'LGE RCU\n', flood: true}}); assert.ok(r.calls <= 128); assert.equal(r.result.reason, 'read_budget_exhausted');
assert.equal(run({0: {name: 'LGE RCU\n'}}, {reverseClock: true}).result.reason, 'clock_failure');
assert.ok(run({0: {name: 'LGE RCU\n'}}, {frozenClock: true}).ticks <= 500);
assert.equal(run({0: {name: 'LGE RCU\n'}}, {cancel: true}).result.reason, 'cancelled');
assert.equal(run({0: {name: 'LGE RCU\n', readError: true}}).result.reason, 'input_unavailable');
r = run({0: {name: 'LGE RCU\n', events: [event(773, 0), event(773, 2), event(773, -1), event(773, 1, 4)]}}); assert.deepEqual(r.result.observations, []);

assert.equal(run({0: {name: 'LGE RCU\nPRIVATE_SECRET_PATH', nameChunk: 8, events: [event(773, 1), event(773, 0)]}}).calls, 0, 'reject a partial name with hidden suffix');

// Interleaved keys: report the first completed pair, never later history.
r = run({0: {name: 'LGE RCU\n', events: [event(3, 1), event(773, 1), event(773, 0), event(3, 0)]}});
assert.equal(r.result.observations[0].candidate_code, 773);
// An overrun invalidates state until SYN_REPORT; no inferred missing release.
r = run({0: {name: 'LGE RCU\n', events: [event(3, 1), event(3, 0, 0), event(773, 1), event(773, 0), event(0, 0, 0), event(3, 0)]}});
assert.deepEqual(r.result.observations, []);
// Empty polling does not spend the successful-read budget before ten seconds.
r = run({0: {name: 'LGE RCU\n'}}); assert.equal(r.result.reason, 'window_complete'); assert.equal(r.ticks, 500);

console.log('passive remote diagnostic: privacy, read-only, bounds, parser and cleanup passed');

// Keep this function ES5: it executes the real script on exact legacy Node.
function legacyRuntimeFixture() {
  var assert = require('assert'), fs = require('fs'), vm = require('vm');
  var source = fs.readFileSync('scripts/passive-remote-diagnostic.js', 'utf8');
  var next = 10, handles = {}, closed = 0, opened = 0, report;
  var pair = new Buffer(32); pair.fill(0);
  pair.writeUInt16LE(1, 8); pair.writeUInt16LE(773, 10); pair.writeInt32LE(1, 12);
  pair.writeUInt16LE(1, 24); pair.writeUInt16LE(773, 26); pair.writeInt32LE(0, 28);
  var io = {
    openSync: function (path, flags) {
      if (path !== '/sys/class/input/event0/device/name' && path !== '/dev/input/event0') { throw new Error('absent'); }
      var name = path.indexOf('/sys/') === 0;
      assert.equal(flags, name ? 0 : 0x20800);
      var fd = next++; handles[fd] = {name: name, read: false}; opened++; return fd;
    },
    fstatSync: function () { return {isCharacterDevice: function () {return true;}, rdev: 0xd40}; },
    readSync: function (fd, b) { var h = handles[fd]; if (h.read) {return 0;} h.read = true; var data = h.name ? new Buffer('LGE RCU\n') : pair; data.copy(b); return data.length; },
    closeSync: function (fd) {delete handles[fd]; closed++;}
  };
  var context = {Buffer: Buffer, module: {exports: {}},
    require: function (name) {
      if (name === 'fs') {return io;}
      if (name === 'os') {return {endianness: function () {return 'LE';}};}
      if (name === 'constants') {return {O_RDONLY: 0, O_NONBLOCK: 0x800, O_NOFOLLOW: 0x20000};}
      throw new Error('forbidden');
    },
    process: {platform: 'linux', arch: 'arm', hrtime: function () {return [0, 0];}, on: function () {}, removeListener: function () {}},
    setTimeout: function () {throw new Error('pair must complete immediately');}, clearTimeout: function () {}
  };
  vm.runInNewContext(source, context);
  context.module.exports.run(function (value) {report = value;});
  assert.equal(report.status, 'observed_candidate');
  assert.equal(report.home_mapping_verified, false);
  assert.equal(report.observations.length, 1);
  assert.equal(report.observations[0].candidate_code, 773);
  assert.equal(opened, closed);
  process.stdout.write('exact runtime ARM32 fixture passed\n');
}
if (process.env.NODE012) {
  const cp = require('child_process');
  const old = cp.spawnSync(process.env.NODE012, ['-e', '(' + legacyRuntimeFixture.toString() + ')()'], {encoding: 'utf8'});
  assert.equal(old.status, 0, old.stderr || old.stdout); process.stdout.write(old.stdout);
  const cli = cp.spawnSync(process.env.NODE012, [filename], {encoding: 'utf8'});
  assert.equal(cli.status, 0, cli.stderr); assert.equal(cli.stderr, '');
  assert.equal(JSON.parse(cli.stdout).reason, 'unsupported_runtime');
}
