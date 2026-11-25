'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const files = new Map();
const actions = [];
let foreground = 'com.gathin.tvhome',
  installed = ['com.cleanyourtv.screensaver'],
  watch,
  now = 1000,
  inventoryCalls = 0;
const fakefs = {
  existsSync: () => false,
  writeFileSync: (p, v) => files.set(p, v),
  appendFileSync() {},
  chmodSync() {},
  unlinkSync() {},
  readFileSync(p) {
    if (p.endsWith('apps.json')) return '[]';
    if (files.has(p)) return files.get(p);
    const error = new Error('missing');
    error.code = 'ENOENT';
    throw error;
  }
};
const context = {
  Buffer,
  console,
  require(name) {
    if (name === 'fs') return fakefs;
    if (name === 'child_process') return {};
    if (name === './state-permissions')
      return require('./storage-fixture.cjs').create(fakefs);
    if (name === './home-control')
      return require('./storage-fixture.cjs').homeControl(fakefs);
    if (name === './app-inventory')
      return () => {
        inventoryCalls++;
        return Promise.resolve({ apps: [], installedIds: installed });
      };
    if (name === './screensaver-owner')
      return (options) =>
        require('../native/app/screensaver-owner')({
          ...options,
          generation: 5,
          settings: require('../screensaver/settings'),
          createAdapter: () => ({
            enable() {
              actions.push('enable');
              return true;
            },
            whenReady: () => Promise.resolve(true),
            unavailable: () => false,
            closePending: () => false,
            preview() {
              actions.push('preview');
              return true;
            },
            eligible() {
              actions.push('eligible');
              return true;
            },
            activity() {
              actions.push('activity');
            },
            stop() {
              actions.push('stop');
            },
            getSession() {
              return null;
            }
          })
        });
    if (name === '/usr/lib/node_modules/webos-service')
      return function () {
        this.activityManager = { create() {} };
        this.call = (uri, p, done) =>
          done({
            payload: { returnValue: true, state: { enabled: true, schema: 3 } }
          });
      };
    if (name === './screen-watch')
      return (data, log, fg, reset, power) => {
        watch = { fg, reset, power };
        return { foreground: (done) => done(foreground), close() {} };
      };
    return require('../native/app/' + name.slice(2));
  },
  process: {
    argv: ['node', 'native', '{"nativeHomeAuto":true}'],
    pid: 1,
    getuid: () => 5431,
    hrtime: () => [Math.floor(now / 1000), (now % 1000) * 1000000],
    on() {},
    exit() {}
  },
  setTimeout() {
    return 1;
  },
  clearTimeout() {},
  setInterval() {
    return 1;
  },
  clearInterval() {}
};
vm.runInNewContext(fs.readFileSync('native/app/native.js', 'utf8'), context);
context.ready = true;
const directory =
  '/media/developer/apps/usr/palm/services/com.gathin.tvhome.renewal/state/home-control';
let sequence = 0;
async function request(method, settings, channel = {}) {
  const dir = channel.directory || directory;
  files.set(
    dir + '/home-request.json',
    JSON.stringify({
      id: (++sequence).toString(16).padStart(32, '0'),
      method,
      settings,
      expires: Date.now() + 5000
    })
  );
  context.readHomeRequest({ directory: dir, last: '', ...channel });
  for (let i = 0; i < 10; i++) await Promise.resolve();
  const reply = files.get(dir + '/home-response.json');
  return reply && JSON.parse(reply);
}
(async () => {
  assert.equal(
    actions.length,
    0,
    'startup must not create listener or LG subscription'
  );
  const status = await request('screensaverStatus');
  assert.equal(
    status.returnValue,
    true,
    'authenticated screensaver status must reach native owner'
  );
  assert.equal(status.available, true);
  assert.equal(status.state.enabled, true);
  const settings = {
    enabled: true,
    scope: 'cytv',
    mode: 'clock',
    assetId: '',
    idleTimeoutMs: 60000
  };
  assert.equal(
    (await request('screensaverConfigure', settings)).state.enabled,
    true
  );
  assert.equal((await request('screensaverPreview')).started, true);
  assert.equal(
    inventoryCalls,
    1,
    'activity controls must reuse recent installed capability instead of requesting full inventory repeatedly'
  );
  foreground = 'youtube.leanback.v4';
  assert.equal((await request('screensaverPreview')).started, false);
  assert.notEqual(
    actions.at(-1),
    'stop',
    'normal foreground change keeps the LG owner armed'
  );
  foreground = 'com.gathin.tvhome';
  assert.equal((await request('screensaverActivity')).returnValue, true);
  assert.equal(actions.at(-1), 'activity');
  watch.reset();
  assert.equal(
    actions.at(-1),
    'stop',
    'monitor reset closes owned screensaver'
  );
  await request('screensaverActivity');
  watch.power({
    state: 'Suspend',
    processing: 'Request Suspend',
    onOff: 'off'
  });
  assert.equal(
    actions.at(-1),
    'stop',
    'power transition closes owned screensaver'
  );
  const legacy =
    '/media/developer/apps/usr/palm/applications/com.local.nativehome/state';
  assert.equal(
    (await request('screensaverPreview', undefined, { directory: legacy }))
      .returnValue,
    false,
    'legacy channel cannot control screensaver'
  );
  installed = [];
  now += 31000;
  assert.equal(
    (await request('screensaverStatus')).available,
    false,
    'actual installed inventory gates feature'
  );
  const timers = [];
  const exits = [];
  context.screensaverOwner.closePending = () => true;
  context.setTimeout = (callback, delay) => timers.push({ callback, delay });
  context.process.exit = (code) => exits.push(code);
  context.finish({ code: 0, exitCode: 0, terminalUI: false });
  assert.deepEqual(exits, [], 'keep Helper alive for outstanding popup close');
  const drain = timers.at(-1);
  assert.equal(drain.delay, 50);
  now += 3200;
  drain.callback();
  assert.deepEqual(
    exits,
    [0],
    'unanswered popup close cannot block terminal exit'
  );
  console.log(
    'PASS native production screensaver wiring: authenticated channel, inventory, foreground, reset, power and bounded shutdown'
  );
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
