'use strict';
const assert = require('node:assert/strict'),
  fs = require('node:fs');
assert.ok(
  fs.existsSync(__dirname + '/screensaver-register.js'),
  'Root service screensaver registration must exist'
);
const register = require('./screensaver-register');
const settings = require('../../screensaver/settings');
const personalPhoto = 'http://127.0.0.1:38123/' + 'a'.repeat(32) + '/photo.jpg';
const personalVideo = 'http://127.0.0.1:38123/' + 'a'.repeat(32) + '/1080p.mp4';
function fixture(whenReady = () => Promise.resolve(true)) {
  const methods = {},
    calls = [],
    monitors = [],
    canceled = [],
    operations = [],
    payloads = [];
  let time = 1000,
    snapshot = {
      state: settings.normalize(),
      owner: {
        active: true,
        healthy: true,
        legacyHelperActive: false,
        generation: 7
      },
      foregroundOwn: true,
      popupInstalled: true,
      validForMs: 1500
    };
  let adapterOptions,
    deliveryMs = 0,
    launchOK = true;
  const adapter = {
    enable(g) {
      calls.push(['enable', g]);
      return true;
    },
    whenReady,
    preview(g) {
      calls.push(['preview', g]);
      return true;
    },
    eligible(g) {
      calls.push(['eligible', g]);
      return true;
    },
    activity(g) {
      calls.push(['activity', g]);
      return true;
    },
    stop(g) {
      calls.push(['stop', g]);
      return true;
    },
    getSession() {
      return null;
    },
    reconcile() {
      calls.push(['reconcile']);
    },
    dispose() {
      calls.push(['dispose']);
    }
  };
  const service = {
    register(name, fn) {
      methods[name] = fn;
    },
    call(uri, payload, callback) {
      if (launchOK === 'throw') throw Error('Launch transport unavailable');
      calls.push(['luna', uri, payload]);
      callback({ payload: { returnValue: launchOK } });
    }
  };
  const api = register(service, {
    settings: {
      ...settings,
      personalMediaUrl: (mode, url) =>
        (mode === 'photo' && url === personalPhoto) ||
        (mode === 'video' && url === personalVideo)
    },
    createAdapter(options) {
      adapterOptions = options;
      return adapter;
    },
    controller: { monotonic: () => time },
    createLG() {},
    now: () => time,
    execute(command, payload) {
      operations.push(command);
      payloads.push(payload);
      if (command === 'configure') snapshot = { ...snapshot, state: payload };
      const observedAtMs = snapshot.observedAtMs ?? time + deliveryMs;
      time += deliveryMs;
      return Promise.resolve({ ...snapshot, observedAtMs });
    },
    setInterval(fn) {
      monitors.push(fn);
      return 1;
    },
    clearInterval(id) {
      canceled.push(id);
    }
  });
  async function request(
    name,
    payload = {},
    id = 'com.cleanyourtv.root.preview'
  ) {
    return new Promise((resolve) =>
      methods[name]({
        payload,
        ls2Message: { applicationID: () => id },
        respond: resolve
      })
    );
  }
  return {
    request,
    calls,
    operations,
    payloads,
    api,
    monitors,
    canceled,
    setTime(n) {
      time = n;
    },
    setDeliveryMs(n) {
      deliveryMs = n;
    },
    getSnapshot() {
      return snapshot;
    },
    setSnapshot(s) {
      snapshot = s;
    },
    options: () => adapterOptions,
    setLaunchOK(value) {
      launchOK = value;
    }
  };
}
(async () => {
  const startup = fixture();
  const saved = settings.normalize({
    enabled: true,
    scope: 'global',
    mode: 'ambient'
  });
  const awake = {
    ...startup.getSnapshot(),
    state: saved,
    foregroundOwn: false,
    foregroundForeign: true
  };
  startup.setSnapshot({ ...awake, owner: null, validForMs: 0 });
  await startup.api.resume();
  assert.equal(
    startup.monitors.length,
    1,
    'saved global mode waits for a healthy owner after service startup'
  );
  assert.equal(startup.options().context().globalEligible, false);
  startup.setSnapshot(awake);
  startup.monitors[0]();
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(
    startup.options().context().globalEligible,
    true,
    'an active foreign app re-arms LG without an RPC from Home'
  );
  startup.api.dispose();

  const disabled = fixture();
  await disabled.api.resume();
  assert.equal(
    disabled.monitors.length,
    0,
    'disabled mode needs no background monitor'
  );
  disabled.api.dispose();

  for (const stopBeforeReady of [false, true]) {
    let ready, entered;
    const waiting = new Promise((resolve) => {
      entered = resolve;
    });
    const cold = fixture(
      () =>
        new Promise((resolve) => {
          ready = resolve;
          entered();
        })
    );
    await cold.request('screensaverConfigure', {
      enabled: true,
      mode: 'photo',
      assetId: 'personal-photo'
    });
    const preview = cold.request('screensaverPreview', {
      mediaUrl: personalPhoto
    });
    await waiting;
    assert.equal(
      cold.calls.some(([operation]) => operation === 'preview'),
      false
    );
    if (stopBeforeReady) await cold.request('screensaverStop');
    ready(true);
    assert.equal((await preview).started, !stopBeforeReady);
    cold.api.dispose();
  }
  let f = fixture();
  assert.equal(
    f.operations.length,
    0,
    'service import registers without probing or starting'
  );
  let result = await f.request('screensaverPreview', {}, 'attacker');
  assert.equal(result.returnValue, false);
  assert.equal(f.operations.length, 0);
  result = await f.request('screensaverStatus');
  assert.equal(result.state.enabled, false);
  assert.equal(result.available, true);
  assert.equal(
    f.monitors.length,
    0,
    'status does not start recurring subprocesses'
  );
  f.setSnapshot({ ...f.getSnapshot(), popupInstalled: false });
  result = await f.request('screensaverStatus');
  assert.equal(
    result.available,
    false,
    'disabled setting without installed companion is unavailable'
  );
  f.setSnapshot({ ...f.getSnapshot(), popupInstalled: true });
  result = await f.request('screensaverConfigure', {
    enabled: true,
    scope: 'cytv',
    mode: 'clock',
    idleTimeoutMs: 30000
  });
  assert.equal(result.available, true);
  assert.equal(result.state.idleTimeoutMs, 30000);
  assert.equal(
    f.monitors.length,
    1,
    'enabled built-in arms background observation by default'
  );
  result = await f.request('screensaverPreview');
  assert.equal(result.started, true);
  assert.equal(
    f.monitors.length,
    1,
    'authorized local controller starts observation'
  );
  assert.ok(f.calls.some((x) => x[0] === 'preview' && x[1] === 7));
  assert.equal(f.options().context().globalTriggerVerified, true);
  result = await f.request('screensaverActivity');
  assert.equal(result.returnValue, true);
  result = await f.request('screensaverEligible');
  assert.equal(result.started, true);
  result = await f.request('screensaverStop');
  assert.equal(
    result.state.enabled,
    true,
    'stop does not clear saved user intent'
  );
  assert.ok(f.calls.some((x) => x[0] === 'stop'));
  assert.equal(
    f.canceled.length,
    1,
    'explicit stop cancels recurring observation'
  );
  for (const override of [
    { mode: 'photo', assetId: 'image_1' },
    { mode: 'video', assetId: 'clip_1' }
  ]) {
    result = await f.request('screensaverConfigure', {
      enabled: true,
      scope: 'cytv',
      mode: 'clock',
      ...override
    });
    assert.equal(result.available, true);
    result = await f.request('screensaverPreview');
    assert.equal(result.started, false);
  }
  await f.request('screensaverConfigure', {
    enabled: true,
    scope: 'cytv',
    mode: 'photo',
    assetId: 'alpine-photo'
  });
  assert.equal((await f.request('screensaverPreview')).started, true);
  assert.equal(f.options().context().assetId, 'alpine-photo');
  f = fixture();
  await f.request('screensaverConfigure', {
    enabled: true,
    scope: 'global',
    mode: 'ambient'
  });
  assert.equal(f.options().context().globalEligible, false);
  assert.equal(f.monitors.length, 1);
  f.setSnapshot({
    ...f.getSnapshot(),
    foregroundOwn: false,
    foregroundForeign: true
  });
  await f.request('screensaverStatus');
  assert.equal(f.options().context().globalEligible, true);
  assert.equal(f.options().context().inAppEligible, false);
  assert.equal((await f.request('screensaverPreview')).started, false);
  assert.equal(
    f.canceled.length,
    0,
    'rejected Home commands do not disarm the LG owner'
  );

  f = fixture();
  f.setSnapshot({
    ...f.getSnapshot(),
    foregroundOwn: false,
    foregroundForeign: true
  });
  f.setDeliveryMs(1000);
  await f.request('screensaverConfigure', {
    enabled: true,
    scope: 'global',
    mode: 'ambient'
  });
  f.setTime(2750);
  assert.equal(
    f.options().context().globalEligible,
    true,
    'slow Root checks must not age a foreground observation before it was made'
  );
  f.setTime(3500);
  assert.equal(
    f.options().getOwner(),
    null,
    'the observation still expires before authorizing a launch'
  );
  for (const observedAtMs of [3499, 3501]) {
    f.setDeliveryMs(0);
    f.setSnapshot({ ...f.getSnapshot(), observedAtMs });
    assert.equal((await f.request('screensaverStatus')).available, false);
  }

  f = fixture();
  await f.request('screensaverConfigure', {
    enabled: true,
    mode: 'photo',
    assetId: 'personal-photo'
  });
  await f.request('screensaverActivity');
  f.setSnapshot({ ...f.getSnapshot(), foregroundOwn: false });
  result = await f.request('screensaverPreview');
  assert.equal(result.started, false);
  assert.equal(f.options().getOwner(), null);
  assert.equal(
    f.canceled.length,
    1,
    'leaving known CYTV foreground ends observation'
  );
  f = fixture();
  await f.request('screensaverConfigure', {
    enabled: true,
    mode: 'photo',
    assetId: 'personal-photo'
  });
  await f.request('screensaverActivity');
  f.setTime(3000);
  assert.equal(
    f.options().getOwner(),
    null,
    'expired owner cache never grants lifecycle'
  );
  const count = f.operations.length;
  f.monitors[0]();
  await Promise.resolve();
  assert.equal(f.canceled.length, 1, 'expired observation ends polling');
  assert.equal(f.operations.length, count);
  f = fixture();
  await f.request('screensaverConfigure', { enabled: true });
  const denied = Object.assign({}, f.getSnapshot(), { owner: null });
  f.setSnapshot(denied);
  result = await f.request('screensaverPreview');
  assert.equal(result.started, false);
  await f.request('screensaverConfigure', { enabled: false });
  assert.equal(f.options().context().popupSupported, false);
  f = fixture();
  await f.request('screensaverConfigure', { enabled: true });
  await f.request('screensaverPreview');
  f.setSnapshot({ ...f.getSnapshot(), foregroundOwn: false, popupOwn: true });
  result = await f.request('screensaverStatus');
  assert.ok(
    f.options().getOwner(),
    'locally started popup keeps existing owner during startup'
  );
  result = await f.request('screensaverPreview');
  assert.equal(result.started, false, 'popup cannot authorize another start');
  f.setTime(12000);
  assert.equal(f.options().getOwner(), null);
  f = fixture();
  await f.request('screensaverConfigure', {
    enabled: true,
    mode: 'photo',
    assetId: 'personal-photo'
  });
  f.setSnapshot({ ...f.getSnapshot(), foregroundOwn: false, popupOwn: true });
  result = await f.request('screensaverPreview');
  assert.equal(result.started, false, 'unbound own popup grants no authority');
  f.setSnapshot({ ...f.getSnapshot(), foregroundOwn: true });
  result = await f.request('screensaverPreview');
  assert.equal(
    result.available,
    false,
    'underlying Home does not authorize an unbound popup'
  );
  assert.equal(result.started, false);
  f.api.dispose();
  assert.ok(f.calls.some((x) => x[0] === 'dispose'));
  for (const [mode, mediaUrl] of [
    ['photo', personalPhoto],
    ['video', personalVideo]
  ]) {
    f = fixture();
    await f.request('screensaverConfigure', {
      enabled: true,
      mode,
      assetId: 'personal-' + mode
    });
    await f.request('screensaverActivity');
    assert.equal(
      f.monitors.length,
      1,
      'personal selection arms idle without exposing a URL'
    );
    result = await f.request('screensaverPreview', { mediaUrl });
    assert.equal(
      result.started,
      true,
      'valid personal capability starts selected mode'
    );
    assert.equal(f.options().context().personalMediaUrl, mediaUrl);
    assert.equal(
      JSON.stringify(f.payloads).includes(mediaUrl),
      false,
      'URL never crosses runtime/persistence boundary'
    );
    assert.equal(
      JSON.stringify(result).includes(mediaUrl),
      false,
      'URL is not saved state'
    );
    await f.request('screensaverStop');
    assert.equal(f.options().context().personalMediaUrl, '');
    assert.equal(
      (await f.request('screensaverPreview')).started,
      false,
      'stopped URL cannot be reused'
    );
    await f.request('screensaverEligible', { mediaUrl });
    assert.equal(f.options().context().personalMediaUrl, mediaUrl);
    f.setSnapshot({
      ...f.getSnapshot(),
      owner: { ...f.getSnapshot().owner, generation: 8 }
    });
    await f.request('screensaverStatus');
    assert.equal(
      f.options().context().personalMediaUrl,
      '',
      'generation change clears capability'
    );
    assert.equal((await f.request('screensaverPreview')).started, false);
    for (const bad of [
      'file:///tmp/photo.jpg',
      'https://example.org/photo.jpg',
      personalVideo + '?x=1',
      42,
      '',
      undefined
    ]) {
      result = await f.request('screensaverPreview', { mediaUrl: bad });
      assert.equal(result.started, false);
      assert.equal(f.options().context().personalMediaUrl, '');
    }
    await f.request('screensaverPreview', { mediaUrl });
    await f.request('screensaverConfigure', { enabled: true, mode: 'clock' });
    assert.equal(
      f.options().context().personalMediaUrl,
      '',
      'reconfigure clears capability'
    );
    result = await f.request('screensaverPreview', { mediaUrl });
    assert.equal(result.started, false, 'clock cannot consume personal media');
    assert.equal(
      (await f.request('screensaverActivity', { mediaUrl })).returnValue,
      false
    );
    assert.equal(
      (await f.request('screensaverConfigure', { enabled: true, mediaUrl }))
        .returnValue,
      false
    );
    await f.request('screensaverConfigure', {
      enabled: true,
      mode,
      assetId: 'personal-' + mode
    });
    f.setSnapshot({ ...f.getSnapshot(), foregroundOwn: false });
    assert.equal(
      (await f.request('screensaverPreview', { mediaUrl })).started,
      false
    );
    assert.equal(
      f.options().context().personalMediaUrl,
      '',
      'foreign foreground never retains capability'
    );
    f.api.dispose();
    f = fixture();
    await f.request('screensaverConfigure', {
      enabled: true,
      mode,
      assetId: 'personal-' + mode
    });
    await f.request('screensaverPreview', { mediaUrl });
    f.setLaunchOK(false);
    f.options().launch('com.cleanyourtv.screensaver', {}, () => {});
    assert.equal(
      f.options().context().personalMediaUrl,
      '',
      'failed launch clears capability'
    );
    await f.request('screensaverPreview', { mediaUrl });
    f.setLaunchOK('throw');
    assert.doesNotThrow(() =>
      f.options().launch('com.cleanyourtv.screensaver', {}, () => {})
    );
    assert.equal(
      f.options().context().personalMediaUrl,
      '',
      'throwing launch clears capability'
    );
    await f.request('screensaverPreview', { mediaUrl });
    f.setSnapshot(null);
    await f.request('screensaverStatus');
    assert.equal(
      f.options().context().personalMediaUrl,
      '',
      'failed snapshot clears capability'
    );
    f.api.dispose();
  }
  console.log(
    'PASS Root screensaver registration: authenticated methods, verified owner, saved intent, local clock gates'
  );
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
