// Manual launch must explain Helper without changing emergency state or starting input capture.
const assert = require('node:assert/strict'),
  fs = require('fs'),
  vm = require('vm');
function run(params) {
  const calls = [],
    spawns = [];
  let exit;
  const context = {
    require(name) {
      if (name === 'child_process')
        return {
          execFile: (file, args, options, cb) => {
            assert.equal(file, '/usr/bin/luna-send-pub');
            assert.equal(options.timeout, 5000);
            calls.push({ uri: args[2], p: JSON.parse(args[3]) });
            cb(null);
          },
          spawn: (...args) => {
            spawns.push(args);
            return { unref() {}, on() {} };
          }
        };
      if (name === '/usr/lib/node_modules/webos-service')
        throw Error(
          'manual entry must not register the running controller LS2 name'
        );
      throw Error(name);
    },
    process: {
      argv: ['node', 'entry', JSON.stringify(params)],
      exit: (c) => (exit = c)
    },
    setTimeout() {
      return 1;
    },
    clearTimeout() {}
  };
  vm.runInNewContext(
    fs.readFileSync('native/app/helper-entry.js', 'utf8'),
    context
  );
  return { calls, spawns, exit };
}
let r = run({});
assert.equal(r.spawns.length, 0);
assert.equal(r.calls[0].p.id, 'com.gathin.tvhome');
assert.equal(r.calls[0].p.params.showHelper, true);
r = run({ nativeHomeAuto: true });
assert.equal(r.calls.length, 0);
assert.equal(r.spawns.length, 1);
assert.equal(JSON.parse(r.spawns[0][1][0]).nativeHomeAuto, true);
r = run({ nativeHomeStart: true });
assert.equal(r.calls.length, 0);
assert.equal(JSON.parse(r.spawns[0][1][0]).nativeHomeAuto, false);
r = run({ nativeHomeAuto: 'true' });
assert.equal(r.spawns.length, 0, 'only a boolean allows unattended start');
console.log(
  'PASS Helper manual explanation, silent background launch and explicit restart'
);
