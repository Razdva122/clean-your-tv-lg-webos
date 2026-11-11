const assert = require('assert');
const fs = require('fs');
const path = require('path');
const os = require('os');
const vm = require('vm');
const secure = require('../app/state-permissions');
const directory = fs.realpathSync(
  fs.mkdtempSync(path.join(os.tmpdir(), 'cytv-setup-generation-'))
);
const state = path.join(directory, 'state');
const source = fs.readFileSync(require.resolve('../app/native'), 'utf8');
// Exercise actual initialization and Home preference transition with real files.
const startup =
  source
    .slice(0, source.indexOf('// Keep the legacy channel'))
    .replace(
      "var root = '/media/developer/apps/usr/palm/applications/com.local.nativehome';",
      'var root = ' + JSON.stringify(directory) + ';'
    ) +
  '\nvar screenPolicy; function cancelIrHome() {} function cancelResume() {}';
function run(phase) {
  fs.mkdirSync(state, { mode: 0o770 });
  const token = secure.stopGeneration(state, true);
  fs.writeFileSync(path.join(state, 'blocked'), 'old-stop');
  fs.writeFileSync(path.join(state, 'watchdog'), 'old-watchdog');
  fs.writeFileSync(path.join(state, 'home-control.json'), '{"enabled":false}');
  let fired = false,
    latest = token,
    exit;
  function interrupt(at) {
    if (!fired && phase === at) {
      fired = true;
      latest = secure.publishStopGeneration(state);
    }
  }
  const io = Object.assign({}, fs, {
    unlinkSync(file) {
      interrupt('clear');
      return fs.unlinkSync(file);
    }
  });
  function storage(dir, log, init) {
    const result = secure(dir, log, init);
    interrupt('initialize');
    return result;
  }
  Object.assign(storage, secure);
  const home = require('../app/home-control');
  const context = {
    Buffer,
    console,
    setTimeout() {},
    clearTimeout() {},
    require(name) {
      if (name === 'fs') return io;
      if (name === './state-permissions') return storage;
      if (name === './home-control')
        return (f, d, apply, visit) => {
          const control = home(f, d, apply, visit),
            set = control.set;
          control.set = (value) => {
            const result = set(value);
            interrupt('home-on');
            return result;
          };
          return control;
        };
      if (name === '/usr/lib/node_modules/webos-service')
        return function () {
          this.activityManager = { create() {} };
        };
      if (name.charAt(0) === '.') return require('../app/' + name.slice(2));
      return require(name);
    },
    process: {
      argv: ['node', 'native', JSON.stringify({ nativeHomeSetup: token })],
      pid: process.pid,
      hrtime: process.hrtime,
      getuid: process.getuid,
      on() {},
      exit(code) {
        exit = code;
        throw Error('exit');
      }
    }
  };
  interrupt('before');
  try {
    vm.runInNewContext(startup, context);
  } catch (e) {
    if (e.message !== 'exit') throw e;
  }
  if (phase) {
    assert.strictEqual(exit, 0, phase + ' must cancel');
    assert.strictEqual(
      secure.stopGeneration(state),
      latest,
      'activation must retain cancellation token'
    );
    assert.strictEqual(
      fs.existsSync(path.join(state, 'blocked')),
      true,
      'cancellation must continue blocking automatic boot'
    );
    if (phase === 'before' || phase === 'initialize')
      assert.strictEqual(
        fs.readFileSync(path.join(state, 'blocked'), 'utf8'),
        'old-stop'
      );
  } else {
    assert.strictEqual(exit, undefined);
    assert.strictEqual(fs.existsSync(path.join(state, 'blocked')), false);
    assert.strictEqual(fs.existsSync(path.join(state, 'watchdog')), false);
    assert.strictEqual(
      JSON.parse(fs.readFileSync(path.join(state, 'home-control.json')))
        .enabled,
      true
    );
    assert.strictEqual(secure.stopGeneration(state), token);
  }
  fs.rmSync(state, { recursive: true, force: true });
}
try {
  for (const phase of [null, 'before', 'initialize', 'clear', 'home-on'])
    run(phase);
  console.log(
    'PASS: actual setup initialization/Home On and Stops across initialization, latch clear and preference write'
  );
} finally {
  fs.rmSync(directory, { recursive: true, force: true });
}
