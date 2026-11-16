'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { test } = require('node:test');
assert.ok(
  fs.existsSync('native/app/screensaver-owner.js'),
  'native owner must implement authenticated controls'
);
const create = require('../native/app/screensaver-owner');
const settings = require('../screensaver/settings');
function fixture(overrides = {}) {
  let time = 0,
    healthy = true,
    session = null;
  const calls = [];
  let context;
  const owner = create({
    generation: 5,
    now: () => time,
    healthy: () => healthy,
    powerActive: () => true,
    settings,
    ...overrides,
    createAdapter(options) {
      context = options.context;
      return {
        enable() {
          calls.push('enable');
          return true;
        },
        whenReady: overrides.whenReady || (() => Promise.resolve(true)),
        preview() {
          calls.push('preview');
          return true;
        },
        eligible() {
          calls.push('eligible');
          return true;
        },
        activity() {
          calls.push('activity');
        },
        stop() {
          calls.push('stop');
          session = null;
        },
        dispose() {
          calls.push('dispose');
          session = null;
        },
        getSession() {
          return session;
        }
      };
    }
  });
  return {
    owner,
    calls,
    context: () => context(),
    setTime: (n) => {
      time = n;
    },
    setHealthy: (v) => {
      healthy = v;
    },
    setSession: (v) => {
      session = v;
    }
  };
}
const config = {
  enabled: true,
  scope: 'cytv',
  mode: 'clock',
  assetId: '',
  idleTimeoutMs: 60000
};
test('No-root owner controls activation and persisted settings', async () => {
  let f = fixture();
  assert.equal(f.owner.handle('screensaverStatus').state.enabled, false);
  assert.equal(f.owner.handle('screensaverStatus').available, false);
  assert.deepEqual(f.calls, []);
  f.owner.installed(['com.cleanyourtv.screensaver']);
  f.owner.foreground('com.gathin.tvhome');
  assert.equal(f.owner.handle('screensaverStatus').available, true);
  assert.equal((await f.owner.handle('screensaverPreview')).started, false);
  f.owner.handle('screensaverConfigure', config);
  assert.equal((await f.owner.handle('screensaverPreview')).started, true);
  assert.equal(f.context().previewEligible, true);
  f.owner.foreground('com.cleanyourtv.screensaver');
  assert.notEqual(
    f.calls.at(-1),
    'stop',
    'accepted launch may transfer focus to its own popup'
  );
  assert.equal(f.context().inAppEligible, false);
  f.setTime(10001);
  f.owner.foreground('com.cleanyourtv.screensaver');
  assert.equal(
    f.calls.at(-1),
    'stop',
    'unknown/unready popup cannot retain ownership forever'
  );
  f.owner.foreground('com.gathin.tvhome');
  await f.owner.handle('screensaverPreview');
  f.setSession({ sessionId: 'owned', generation: 5, state: 'visible' });
  f.setTime(30000);
  f.owner.foreground('com.cleanyourtv.screensaver');
  assert.notEqual(
    f.calls.at(-1),
    'stop',
    'verified visible session retains ownership above Home'
  );
  f.owner.foreground('youtube.leanback.v4');
  assert.notEqual(f.calls.at(-1), 'stop', 'built-in stays armed outside Home');
  assert.equal(f.context().globalEligible, true);
  assert.equal((await f.owner.handle('screensaverPreview')).started, false);
  assert.equal((await f.owner.handle('screensaverEligible')).started, false);
  f.owner.foreground(null);
  assert.equal(f.owner.handle('screensaverActivity').returnValue, false);
  f.owner.foreground('com.gathin.tvhome');
  assert.equal(f.owner.handle('screensaverActivity').returnValue, true);
  assert.equal(f.calls.at(-1), 'activity');
  assert.equal((await f.owner.handle('screensaverEligible')).started, true);
  f.owner.handle('screensaverStop');
  assert.equal(f.calls.at(-1), 'stop');
  assert.equal(
    f.owner.handle('screensaverStatus').state.enabled,
    true,
    'stop releases lifecycle without erasing preference'
  );
  f.owner.handle('screensaverConfigure', { ...config, enabled: false });
  assert.equal(f.calls.at(-1), 'stop');
  assert.equal((await f.owner.handle('screensaverPreview')).started, false);

  // Unregistered assets cannot activate. Personal assets require a Home lease.
  f = fixture();
  f.owner.installed(['com.cleanyourtv.screensaver']);
  f.owner.foreground('com.gathin.tvhome');
  assert.equal(
    f.owner.handle('screensaverConfigure', {
      ...config,
      mode: 'video',
      assetId: 'ribbon-video'
    }).available,
    true
  );
  assert.equal((await f.owner.handle('screensaverPreview')).started, true);
  for (const change of [
    { mode: 'photo', assetId: 'approved-id' },
    { mode: 'video', assetId: 'approved-id' }
  ]) {
    f = fixture();
    f.owner.installed(['com.cleanyourtv.screensaver']);
    f.owner.foreground('com.gathin.tvhome');
    const result = f.owner.handle('screensaverConfigure', {
      ...config,
      ...change
    });
    assert.equal(result.available, false);
    assert.notEqual((await f.owner.handle('screensaverPreview')).started, true);
    assert.equal(f.calls.includes('enable'), false);
  }
  f = fixture();
  f.owner.installed(['com.cleanyourtv.screensaver']);
  f.owner.foreground('com.gathin.tvhome');
  for (const invalid of [
    null,
    {},
    { ...config, path: '/private/file' },
    { ...config, enabled: 'true' }
  ]) {
    assert.equal(
      f.owner.handle('screensaverConfigure', invalid).returnValue,
      false
    );
    assert.equal(f.owner.handle('screensaverStatus').state.enabled, false);
  }
  f.owner.handle('screensaverConfigure', config);
  f.setHealthy(false);
  assert.equal((await f.owner.handle('screensaverPreview')).started, false);
  assert.equal(f.calls.at(-1), 'stop');
  f.setHealthy(true);
  f.owner.installed([]);
  assert.equal(f.owner.handle('screensaverStatus').available, false);
  assert.equal((await f.owner.handle('screensaverPreview')).started, false);
  f.owner.stop();
  assert.equal(f.calls.at(-1), 'stop');
  let saved;
  f = fixture({
    loadSettings: () => ({ ...config, scope: 'global' }),
    saveSettings: (value) => {
      saved = value;
    }
  });
  assert.equal(
    f.owner.handle('screensaverStatus').state.scope,
    'global',
    'saved unavailable intent survives restart'
  );
  f.owner.handle('screensaverConfigure', config);
  assert.deepEqual(saved, settings.normalize(config));
  f.owner.handle('screensaverConfigure', { ...config, clockOverlay: false });
  assert.equal(saved.clockOverlay, false);
  f = fixture({
    loadSettings: () => config,
    saveSettings() {
      throw new Error('storage failure');
    }
  });
  assert.equal(
    f.owner.handle('screensaverConfigure', { ...config, enabled: false })
      .returnValue,
    false
  );
  assert.equal(
    f.owner.handle('screensaverStatus').state.enabled,
    true,
    'failed persistence cannot silently change preference'
  );
  assert.throws(
    () => fixture({ loadSettings: () => ({ enabled: true }) }),
    /settings/
  );
  console.log(
    'PASS No-root screensaver owner: package capability, exact settings, local foreground and cleanup'
  );
});

test('No-root first photo preview waits for the listener and checks the request again', async () => {
  for (const expired of [false, true]) {
    let ready;
    let current = true;
    const f = fixture({
      whenReady: () =>
        new Promise((resolve) => {
          ready = resolve;
        })
    });
    f.owner.installed(['com.cleanyourtv.screensaver']);
    f.owner.foreground('com.gathin.tvhome');
    f.owner.handle('screensaverConfigure', {
      ...config,
      mode: 'photo',
      assetId: 'personal-photo'
    });
    const preview = f.owner.handle(
      'screensaverPreview',
      {
        mediaUrl: 'http://127.0.0.1:1234/' + 'a'.repeat(32) + '/4k.mp4'
      },
      () => current
    );
    assert.equal(f.calls.includes('preview'), false);
    current = !expired;
    ready(true);
    assert.equal((await preview).started, !expired);
    assert.equal(f.calls.includes('preview'), !expired);
  }
});

test('No-root global mode keeps the owner armed outside Home without accepting Home RPC launches', async () => {
  let active = true;
  const f = fixture({ powerActive: () => active });
  f.owner.installed(['com.cleanyourtv.screensaver']);
  f.owner.foreground('com.gathin.tvhome');
  assert.equal(
    f.owner.handle('screensaverConfigure', { ...config, scope: 'global' })
      .available,
    true
  );
  assert.equal(f.context().globalEligible, false);
  f.owner.foreground('youtube.leanback.v4');
  assert.equal(f.context().globalEligible, true);
  assert.equal((await f.owner.handle('screensaverEligible')).started, false);
  assert.equal((await f.owner.handle('screensaverPreview')).started, false);
  active = false;
  assert.equal(f.context().globalEligible, false);
  active = true;
  f.owner.foreground(null);
  assert.equal(f.context().globalEligible, false);
});
