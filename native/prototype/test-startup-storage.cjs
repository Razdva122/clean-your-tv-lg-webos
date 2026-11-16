// Real storage/inodes; only LG service calls, proc and debug output are modeled.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const vm = require('node:vm');
const storage = require('../app/state-permissions');
const root = fs.realpathSync(
  fs.mkdtempSync(path.join(os.tmpdir(), 'cytv-startup-data-'))
);
const state = path.join(root, 'state');
fs.mkdirSync(state);
let latch = '',
  launches = 0;
const methods = {};
const io = Object.assign({}, fs, {
  readFileSync(name, ...args) {
    if (name === '/proc/sys/kernel/random/boot_id') return 'current-boot';
    if (name === '/proc/stat') return 'btime 1';
    return fs.readFileSync(name, ...args);
  },
  statSync(name) {
    if (latch && name.endsWith('/' + latch)) return {};
    return fs.statSync(name);
  },
  writeFileSync(name, ...args) {
    // Callback debug is irrelevant to saved startup data; keep it in this fixture.
    if (name.startsWith('/tmp/nativehome-boot-'))
      name = path.join(root, path.basename(name));
    return fs.writeFileSync(name, ...args);
  }
});
// Do not prepare the real TV namespace on the host. All record reads and writes
// use the production storage implementation against the real temporary directory.
const secure = Object.assign(() => true, storage);
try {
  vm.runInNewContext(
    fs.readFileSync(path.join(__dirname, '../service/service.js'), 'utf8'),
    {
      console,
      __dirname: root,
      require(name) {
        if (name === 'fs') return io;
        if (name === './state-permissions') return secure;
        if (name === './boot-state') return require('../service/boot-state');
        if (name === 'webos-service')
          return class {
            register(name, callback) {
              methods[name] = callback;
            }
            call(uri, args, callback) {
              assert.equal(uri, 'luna://com.webos.applicationManager/launch');
              assert.equal(args.id, 'com.local.nativehome');
              assert.equal(args.params.nativeHomeAuto, true);
              launches++;
              callback({ payload: { returnValue: true } });
            }
          };
        throw Error(name);
      }
    }
  );
  function invoke(name) {
    let result;
    methods[name]({
      payload: {},
      respond(value) {
        result = value;
      }
    });
    return result;
  }
  storage.atomicRecord(
    state,
    'startup-state',
    JSON.stringify({ enabled: true, schema: 3, boot: 'previous' })
  );
  fs.chmodSync(state, 0o777);
  fs.chmodSync(path.join(state, 'startup-state.json'), 0o777);
  assert.equal(invoke('status').state.enabled, true);
  assert.equal(invoke('tick').result.returnValue, true);
  assert.equal(launches, 1, 'expanded startup data still launches once');
  fs.chmodSync(path.join(state, 'startup-state.json'), 0o777);
  assert.equal(invoke('tick').result.skipped, true);
  assert.equal(launches, 1, 'mode expansion never resets the boot claim');
  for (latch of ['blocked', 'watchdog']) {
    storage.atomicRecord(
      state,
      'startup-state',
      JSON.stringify({ enabled: true, boot: 'previous' })
    );
    fs.chmodSync(path.join(state, 'startup-state.json'), 0o777);
    assert.equal(invoke('tick').result.blocked, true);
    assert.equal(
      launches,
      1,
      'latch prevents boot even with expanded preferences'
    );
  }
  latch = '';
  for (const bytes of ['{"enabled":false}', '{broken', '{"enabled":"true"}']) {
    fs.writeFileSync(path.join(state, 'startup-state.json'), bytes);
    fs.chmodSync(path.join(state, 'startup-state.json'), 0o777);
    assert.equal(invoke('tick').result.skipped, true);
    assert.equal(
      launches,
      1,
      'off/invalid data cannot enable automatic startup'
    );
  }
  console.log(
    'PASS real 0777 startup storage, one launch per boot, Stop/watchdog and invalid/off settings'
  );
} finally {
  fs.rmSync(root, { recursive: true, force: true });
}
