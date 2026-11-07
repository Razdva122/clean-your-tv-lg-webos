'use strict';
const assert = require('node:assert/strict'),
  fs = require('node:fs'),
  os = require('node:os'),
  path = require('node:path'),
  vm = require('node:vm');
const root = fs.mkdtempSync(path.join(os.tmpdir(), 'home-service-jail-'));
const own = '/media/developer/apps/usr/palm/services/com.gathin.tvhome.renewal';
const methods = {},
  writes = [];
// Model the service mount namespace: its own package exists; the Helper app
// remains absent even though a native controller can access it outside this jail.
function local(p) {
  if (!p.startsWith(own + '/')) {
    const e = new Error('outside service jail');
    e.code = 'ENOENT';
    throw e;
  }
  return root + p.slice(own.length);
}
const jailed = {
  readFileSync: (p) => fs.readFileSync(local(p), 'utf8'),
  existsSync: (p) => fs.existsSync(local(p)),
  mkdirSync: (p) => fs.mkdirSync(local(p)),
  writeFileSync(p, b, o) {
    writes.push(p);
    fs.writeFileSync(local(p), b, o);
  },
  chmodSync: (p, m) => fs.chmodSync(local(p), m),
  renameSync(a, b) {
    fs.renameSync(local(a), local(b));
    if (/\/(home|input|catalog)-request[.]json$/.test(b)) {
      const request = JSON.parse(fs.readFileSync(local(b), 'utf8'));
      const response =
        request.method === 'listApps'
          ? {
              id: request.id,
              returnValue: true,
              apps: [{ id: 'org.example', title: 'Example' }]
            }
          : request.method === 'inputStatus'
            ? {
                id: request.id,
                returnValue: true,
                devices: [{ appId: 'com.webos.app.hdmi3', connected: true }]
              }
            : request.method === 'presentationContext'
              ? {
                  id: request.id,
                  returnValue: true,
                  eligible: false,
                  content: false,
                  generation: 7,
                  observedAgeMs: 0
                }
              : request.method === 'presentationDismissed'
                ? {
                    id: request.id,
                    returnValue: true,
                    dismissed: true,
                    generation: request.generation
                  }
                : { id: request.id, returnValue: true, enabled: true };
      fs.writeFileSync(
        local(b.replace('-request', '-response')),
        JSON.stringify(response)
      );
    }
  }
};
function Service() {
  this.register = (n, f) => {
    methods[n] = f;
  };
  this.call = () => {
    throw Error('no network or launch expected');
  };
}
fs.mkdirSync(root + '/state/home-control', { recursive: true });
vm.runInNewContext(fs.readFileSync('renewal-service/service.js', 'utf8'), {
  __dirname: own,
  setTimeout,
  clearTimeout,
  require(n) {
    if (n === 'fs') return jailed;
    if (n === 'webos-service') return Service;
    if (n === './manager') return () => ({});
    if (n === './local-io') return { createLocalIO: () => ({}) };
    if (n === './transport') return { createRequest: () => {} };
    if (n === './renewal') return { createRenewal: () => ({}) };
    return require('../renewal-service/' + n.slice(2));
  }
});
function call(app, method = 'homeStatus', payload = {}) {
  return new Promise((resolve) =>
    methods[method]({
      payload,
      ls2Message: { applicationID: () => app },
      respond: resolve
    })
  );
}
(async () => {
  try {
    assert.equal((await call('other.app')).returnValue, false);
    assert.equal(writes.length, 0, 'authorization precedes all I/O');
    assert.equal(
      typeof methods.inputStatus,
      'function',
      'same-package service must expose a fixed authorized input read'
    );
    assert.equal((await call('other.app', 'inputStatus')).returnValue, false);
    assert.equal(writes.length, 0);
    assert.equal(
      (await call('com.gathin.tvhome', 'inputStatus', { uri: 'PRIVATE' }))
        .returnValue,
      false
    );
    assert.equal(writes.length, 0);
    for (const method of ['presentationContext', 'presentationDismissed']) {
      assert.equal(
        typeof methods[method],
        'function',
        'presentation methods must be registered through the Home caller gate'
      );
      for (const app of [
        'other.app',
        'com.gathin.tvhome.other',
        '',
        null,
        undefined
      ])
        assert.equal(
          (
            await call(
              app,
              method,
              method === 'presentationContext' ? {} : { generation: 7 }
            )
          ).returnValue,
          false
        );
    }
    assert.equal(
      writes.length,
      0,
      'unauthorized presentation requests cannot touch either channel'
    );
    assert.equal(
      (await call('com.gathin.tvhome', 'presentationContext', { extra: true }))
        .returnValue,
      false
    );
    assert.equal(
      (
        await call('com.gathin.tvhome', 'presentationDismissed', {
          generation: 1,
          extra: true
        })
      ).returnValue,
      false
    );
    assert.equal(
      writes.length,
      0,
      'malformed authorized presentation requests are denied before I/O'
    );
    const reply = await call('com.gathin.tvhome');
    assert.equal(reply.returnValue, true, JSON.stringify(reply));
    assert.equal(reply.enabled, true);
    assert.deepEqual(
      writes,
      [own + '/state/home-control/home-request.tmp'],
      'service never needs the other app mount'
    );
    assert.equal(typeof methods.listApps, 'function');
    const beforeCatalog = writes.length;
    for (const app of [
      'other.app',
      'com.gathin.tvhome.other',
      '',
      null,
      undefined
    ])
      assert.equal((await call(app, 'listApps')).returnValue, false);
    assert.equal(
      (await call('com.gathin.tvhome', 'listApps', { path: 'PRIVATE' }))
        .returnValue,
      false
    );
    assert.equal(writes.length, beforeCatalog);
    assert.equal(
      (await call('com.gathin.tvhome', 'listApps')).apps[0].id,
      'org.example'
    );
    assert.equal(
      writes.at(-1),
      own + '/state/home-control/catalog-request.tmp'
    );
    const inputs = await call('com.gathin.tvhome', 'inputStatus');
    assert.equal(inputs.devices[0].connected, true);
    const context = await call('com.gathin.tvhome', 'presentationContext', {});
    assert.equal(context.returnValue, true);
    assert.equal(context.content, false);
    assert.equal(context.generation, 7);
    const dismissed = await call('com.gathin.tvhome', 'presentationDismissed', {
      generation: 7
    });
    assert.equal(dismissed.returnValue, true);
    assert.equal(dismissed.dismissed, true);
    assert.equal(dismissed.generation, 7);
    const request = JSON.parse(
      fs.readFileSync(root + '/state/home-control/home-request.json', 'utf8')
    );
    assert.equal(request.method, 'presentationDismissed');
    assert.equal(request.generation, 7);
    assert(
      writes
        .slice(-2)
        .every((p) => p === own + '/state/home-control/home-request.tmp'),
      'presentation uses only the existing HOME jail path'
    );
    console.log(
      'PASS actual service Home RPC in a service-only filesystem namespace'
    );
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
