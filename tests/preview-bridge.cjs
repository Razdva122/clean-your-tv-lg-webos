const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
let now = 0,
  timerId = 0;
const timers = new Map();
function advance(ms) {
  now += ms;
  for (const [id, timer] of timers) {
    if (timer.at <= now) {
      timers.delete(id);
      timer.fn();
    }
  }
}
const context = {
  window: { TV_APPS: { apps: [] } },
  document: { getElementById: () => null, addEventListener: () => {} },
  setTimeout: (fn, delay) => {
    const id = ++timerId;
    timers.set(id, { fn, at: now + delay });
    return id;
  },
  clearTimeout: (id) => timers.delete(id)
};
vm.createContext(context);
vm.runInContext(fs.readFileSync('preview/bridge.js', 'utf8'), context);
function call(
  method,
  payload = {},
  service = 'com.cleanyourtv.root.preview.service'
) {
  return new Promise((resolve) => {
    const bridge = new context.window.PalmServiceBridge();
    bridge.onservicecallback = (raw) => resolve(JSON.parse(raw));
    bridge.call('luna://' + service + '/' + method, JSON.stringify(payload));
    advance(30);
  });
}
(async () => {
  assert.equal(
    (await call('status', { presentation: 'context' })).result.content,
    false
  );
  context.window.PREVIEW_HOME_CONTEXT = 'content';
  assert.equal(
    (await call('status', { presentation: 'context' })).result.content,
    true
  );
  context.window.PREVIEW_HOME_CONTEXT = 'unknown';
  assert.equal(
    (await call('status', { presentation: 'context' })).result.content,
    null
  );
  const supervisor = 'com.cleanyourtv.system.updater.service';
  assert.equal(
    (await call('restoreProfile', { edition: 'root' }, supervisor)).result,
    null
  );
  assert.equal((await call('status', {}, supervisor)).result, null);
  const previewOffer = await call('check', { edition: 'root' }, supervisor);
  assert.equal(previewOffer.returnValue, true);
  assert.equal(previewOffer.result.canInstall, false);
  assert(
    previewOffer.result.components.some(
      (component) => component.name === 'root-infrastructure'
    )
  );
  assert.equal(
    (await call('install', { edition: 'root' }, supervisor)).returnValue,
    false
  );
  const homebrew = 'org.webosbrew.hbchannel.service';
  assert.equal(
    (await call('getConfiguration', {}, homebrew)).blockUpdates,
    false
  );
  assert.equal(
    (await call('setConfiguration', { blockUpdates: true }, homebrew))
      .blockUpdates,
    true
  );
  assert.equal(
    (await call('getConfiguration', {}, homebrew)).blockUpdates,
    true
  );
  assert.equal(
    (await call('setConfiguration', { blockUpdates: 'false' }, homebrew))
      .returnValue,
    false
  );
  assert.equal(
    (
      await call(
        'setConfiguration',
        { blockUpdates: false, failsafe: false },
        homebrew
      )
    ).returnValue,
    false
  );
  let reply = await call('status');
  assert.equal(reply.result.result.intent.phase, 'disabled');
  await call('enable');
  reply = await call('status');
  assert.equal(reply.result.result.intent.phase, 'active');
  advance(120000);
  assert.equal((await call('status')).result.result.intent.phase, 'active');
  assert.equal(
    (await call('confirm', { transaction: 'preview-root-activation' }))
      .returnValue,
    false,
    'Persistent activation has no Keep confirmation'
  );
  assert.equal((await call('restore')).result.result, 'restored');
  reply = await call('status');
  assert.equal(reply.result.result.intent.phase, 'disabled');
  assert.equal(reply.result.result.effective.sam_home, 'com.webos.app.home');
  assert.equal(
    reply.result.result.effective.profiles.defaultApps.categories.home,
    'com.webos.app.home'
  );
  assert.equal(
    reply.result.result.effective.profiles.idleApp.appId,
    'com.webos.app.home'
  );
  context.window.TV_APPS.apps = [{ id: 'preview.youtube', title: 'YouTube' }];
  for (const service of [
    'com.local.nativehome.service',
    'com.cleanyourtv.root.preview.service'
  ]) {
    reply = await call('listApps', {}, service);
    assert.equal(reply.returnValue, true);
    assert.equal(reply.apps[0].id, 'preview.youtube');
    assert.equal(reply.apps[1].id, 'preview.gallery');
  }
  context.window.TV_APPS = JSON.parse(
    fs.readFileSync('preview/reference-apps/inventory.json', 'utf8')
  );
  context.window.TV_APPS.referenceApps = true;
  for (const service of [
    'com.local.nativehome.service',
    'com.cleanyourtv.root.preview.service'
  ]) {
    reply = await call('listApps', {}, service);
    assert.equal(reply.returnValue, true);
    assert.equal(
      reply.apps.length,
      10,
      'reference inventory must not gain synthetic apps'
    );
    assert.deepEqual(reply.apps, context.window.TV_APPS.apps);
  }
  function updater(method) {
    return call(method, {}, 'com.cleanyourtv.root.updater.service');
  }
  context.window.ROOT_VERSION = '0.1.1';
  reply = await updater('restoreProfile');
  assert.equal(reply.returnValue, true);
  assert.equal(
    reply.result,
    null,
    'Demo profile bootstrap must proceed without a real updater'
  );
  reply = await updater('check');
  assert.equal(reply.result.installed.version, '0.1.1');
  assert.equal(reply.result.canInstall, false);
  assert.equal(reply.result.reason, 'current');
  assert.equal((await updater('status')).result, null);
  assert.equal(
    (await updater('install')).returnValue,
    false,
    'Browser preview cannot install packages'
  );
  console.log(
    'PASS browser app management, persistent Root activation/restore and Software updates preview'
  );
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
