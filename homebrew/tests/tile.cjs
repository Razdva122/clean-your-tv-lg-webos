'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const source = fs.readFileSync(path.join(__dirname, '../app/tile.js'), 'utf8');

function fixture(
  edition,
  saved = {},
  response = { returnValue: true },
  params = {},
  initiallyHidden = false
) {
  const calls = [],
    pages = [],
    events = {},
    timers = new Map();
  let nextTimer = 0;
  const storage = new Map(Object.entries(saved));
  const window = {
    CYTVTileEdition: edition,
    location: { hash: '', replace: (page) => pages.push(page) },
    PalmSystem: { launchParams: JSON.stringify(params) },
    localStorage: {
      getItem: (key) => storage.get(key),
      setItem: (key, value) => storage.set(key, value)
    },
    document: {
      hidden: initiallyHidden,
      addEventListener: (name, callback) => {
        events[name] = callback;
      }
    },
    PalmServiceBridge: function () {
      this.cancel = () => {};
      this.call = (uri, raw) => {
        calls.push({ uri, payload: JSON.parse(raw) });
        if (response) this.onservicecallback(JSON.stringify(response));
      };
    }
  };
  const setTimeout = (cb) => {
    timers.set(++nextTimer, cb);
    return nextTimer;
  };
  const clearTimeout = (id) => timers.delete(id);
  vm.runInNewContext(source, { window, setTimeout, clearTimeout });
  return {
    calls,
    pages,
    window,
    events,
    runTimers() {
      for (const [id, cb] of [...timers]) {
        timers.delete(id);
        cb();
      }
    }
  };
}
for (const [edition, target] of [
  ['root', 'com.cleanyourtv.root.preview'],
  ['no-root', 'com.gathin.tvhome']
]) {
  const f = fixture(edition, {
    'cytv.tile.home': edition === 'root' ? 'no-root' : 'root'
  });
  assert.deepStrictEqual(f.calls, [
    {
      uri: 'luna://com.webos.applicationManager/launch',
      payload: { id: target }
    }
  ]);
  assert.deepStrictEqual(f.pages, []);
  f.window.document.hidden = true;
  f.events.visibilitychange();
  f.runTimers();
  assert.deepStrictEqual(f.pages, []);
  f.window.document.hidden = false;
  f.events.visibilitychange();
  f.events.webOSRelaunch({});
  assert.strictEqual(
    f.calls.length,
    2,
    'a deliberate relaunch opens Home again'
  );
  f.runTimers();
  assert.deepStrictEqual(
    f.pages,
    ['recovery.html'],
    'ack without backgrounding opens recovery'
  );
}
for (const [edition, target] of [
  [null, null],
  ['root', 'com.cleanyourtv.root.preview']
]) {
  const hiddenLaunch = fixture(edition, {}, { returnValue: true }, {}, true);
  assert.equal(hiddenLaunch.calls.length, 0);
  assert.deepEqual(hiddenLaunch.pages, []);
  hiddenLaunch.window.document.hidden = false;
  hiddenLaunch.events.visibilitychange();
  hiddenLaunch.runTimers();
  if (target) {
    assert.deepEqual(hiddenLaunch.calls[0].payload, { id: target });
    assert.deepEqual(hiddenLaunch.pages, []);
  } else {
    assert.deepEqual(hiddenLaunch.pages, ['setup.html#open']);
    assert.equal(hiddenLaunch.calls.length, 0);
  }
}
assert.deepStrictEqual(fixture(null).pages, ['setup.html#open']);
assert.deepStrictEqual(
  fixture(null, {
    'cytv.installer.operation': 'a'.repeat(32),
    'cytv.tile.home': 'root'
  }).pages,
  ['setup.html#open']
);
assert.deepStrictEqual(
  fixture(null, { 'cytv.tile.home': 'no-root' }).calls[0].payload,
  { id: 'com.gathin.tvhome' }
);
assert.deepStrictEqual(fixture('root', {}, { returnValue: false }).pages, [
  'recovery.html'
]);
const explicit = fixture('root', {}, null, { cytvRecovery: true });
assert.deepStrictEqual(explicit.pages, ['recovery.html#status']);
assert.strictEqual(explicit.calls.length, 0);
const nested = fixture('root', {}, null, { params: { cytvRecovery: true } });
assert.deepStrictEqual(nested.pages, ['recovery.html#status']);
assert.strictEqual(nested.calls.length, 0);
const unknown = fixture('neither', { 'cytv.tile.home': 'root' });
assert.deepStrictEqual(unknown.pages, ['recovery.html']);
assert.strictEqual(unknown.calls.length, 0);
const timeout = fixture('root', {}, null);
timeout.runTimers();
assert.deepStrictEqual(timeout.pages, ['recovery.html']);
{
  const elements = {};
  function node() {
    return { focus() {}, scrollIntoView() {}, appendChild() {} };
  }
  const document = {
    getElementById(id) {
      if (!elements[id]) elements[id] = node();
      return elements[id];
    },
    createElement: node,
    addEventListener() {}
  };
  let external, saved, shown;
  const window = {
    InstallerDiagnostics: {
      explain() {},
      load() {
        return saved;
      },
      save(value) {
        saved = value;
        return true;
      },
      render(parent, value, translate, persisted) {
        shown = { value, persisted };
      },
      record(source, detail, code) {
        return { source, code };
      }
    },
    InstallerDiagnosticI18n: (key) => key,
    location: { hash: '' },
    CYTVTileEdition: 'no-root',
    HomeI18n: {
      ready(callback) {
        callback();
      },
      t(key) {
        return key;
      }
    },
    SystemUpdates: {
      open(options) {
        options.fallback();
      },
      openExternal(options) {
        external = options;
      }
    }
  };
  vm.runInNewContext(fs.readFileSync('homebrew/app/tile-recovery.js', 'utf8'), {
    window,
    document
  });
  elements.recover.onclick();
  assert.equal(external.edition, 'no-root');
  assert.equal(elements.tileActions.hidden, true);
  external.onClose();
  assert.equal(elements.tileActions.hidden, false);
  assert.equal(elements['save-report'].hidden, false);
  elements['save-report'].onclick();
  assert.equal(elements['tile-main'].hidden, true);
  assert.equal(elements['tile-report-body'].hidden, false);
  assert.equal(shown.persisted, true);
  assert.equal(shown.value.source, 'recovery');
  assert.equal(shown.value.code, 'update_service_unavailable');
}
console.log(
  'PASS edition-bound tile, daily launch, no Home activation, crash/timeout and explicit recovery'
);
