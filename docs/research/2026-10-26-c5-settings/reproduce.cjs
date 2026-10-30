'use strict';
// Characterize existing failures; this is not a TV compatibility test or a fix.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const vm = require('node:vm');
const source = path.resolve(process.argv[2] || path.join(__dirname, '../../../renewal-service'));
const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'cytv-c5-settings-'));
const helperPath = '/media/developer/apps/usr/palm/applications/com.local.nativehome/state';
const results = [];

function createService(name, options = {}) {
  const directory = path.join(temporary, name);
  const helper = path.join(directory, 'helper');
  fs.mkdirSync(helper, {recursive: true});
  if (options.corrupt) {
    fs.mkdirSync(path.join(directory, 'state'));
    fs.writeFileSync(path.join(directory, 'state/settings.json'), '{');
  }
  const failures = [], methods = {};
  const io = Object.create(fs);
  for (const method of ['readFileSync', 'writeFileSync', 'existsSync', 'mkdirSync', 'chmodSync', 'renameSync']) {
    io[method] = (...args) => {
      args = args.map(arg => typeof arg === 'string' && arg.startsWith(helperPath) ? helper + arg.slice(helperPath.length) : arg);
      try { return fs[method](...args); }
      catch (error) {
        failures.push({operation: method, target: path.basename(args[0]), code: error.code || error.name});
        throw error;
      }
    };
  }
  function Service() {
    this.register = (name, handler) => { methods[name] = handler; };
    this.call = (uri, payload, done) => { done({payload: {returnValue: true}}); };
  }
  const context = {
    __dirname: directory, setTimeout, clearTimeout, Promise,
    require(name) {
      if (name === 'fs') return io;
      if (name === 'webos-service') return Service;
      // No session token, network request, system activity or TV is accessed.
      if (name === './transport') return {createRequest: () => () => { throw Error('network must not be used'); }};
      if (name === './renewal') return {createRenewal: () => ({run: async () => ({status: 'healthy'})})};
      return require(path.join(source, name));
    }
  };
  vm.runInNewContext(fs.readFileSync(path.join(source, 'service.js'), 'utf8'), context);
  return {
    directory, helper, failures,
    call(name, caller = 'com.gathin.tvhome') {
      return new Promise(resolve => methods[name]({payload: {}, ls2Message: {applicationID: () => caller}, respond: resolve}));
    }
  };
}

(async () => {
  try {
    // Real local filesystem denial, equivalent to a runtime unable to write its
    // package directory. We do not claim the TV's actual mount/identity is known.
    const readOnly = createService('unwritable-parent');
    fs.chmodSync(readOnly.directory, 0o555);
    try {
      assert.equal((await readOnly.call('status')).state.error, undefined, 'missing state alone is not storage-error');
      const reply = await readOnly.call('enable');
      assert.equal(reply.state.error, 'storage-error');
      assert.equal(reply.state.enabled, false);
      assert(readOnly.failures.some(x => x.operation === 'mkdirSync' && x.code === 'EACCES'));
      results.push({case: 'unwritable service parent', reply, failures: readOnly.failures});
    } finally { fs.chmodSync(readOnly.directory, 0o755); }

    const corrupt = createService('corrupt-config', {corrupt: true});
    const corruptReply = await corrupt.call('status');
    assert.equal(corruptReply.state.error, 'storage-error');
    results.push({case: 'invalid settings JSON, without any write failure', reply: corruptReply});

    const inaccessible = createService('inaccessible-helper');
    fs.chmodSync(inaccessible.helper, 0);
    try {
      const reply = await inaccessible.call('homeStatus');
      assert.equal(reply.errorText, 'Home Helper data unavailable');
      assert(inaccessible.failures.some(x => x.code === 'EACCES'));
      results.push({case: 'Helper directory inaccessible to broker', reply, failures: inaccessible.failures});
    } finally { fs.chmodSync(inaccessible.helper, 0o755); }

    const createHome = require(path.join(source, 'home-control'));
    let now = 0, pending;
    const hiddenResponse = createHome(fs, temporary, {now: () => now, later: callback => { pending = callback; }, nonce: () => '1'.repeat(32)});
    const request = hiddenResponse('homeStatus', {});
    now = 5001; pending();
    const timeoutReply = await request;
    assert.equal(timeoutReply.errorText, 'Home Helper did not respond');
    results.push({case: 'request writable but no visible correlated response', reply: timeoutReply});

    const createManager = require(path.join(source, 'manager'));
    const manager = createManager({load: () => ({enabled: false}), save() {}, schedule: async () => { throw Error('non-storage failure'); }});
    const nonStorageReply = await manager.enable();
    assert.equal(nonStorageReply.error, 'storage-error');
    results.push({case: 'non-storage exception is also classified as storage-error', reply: nonStorageReply});

    const denied = createService('caller-denied');
    const deniedReply = await denied.call('homeStatus', 'another.app');
    assert.equal(deniedReply.errorText, 'caller-not-authorized');
    results.push({case: 'caller rejected before filesystem access', reply: deniedReply, filesystemFailures: denied.failures});

    const healthy = createService('healthy');
    const healthyReply = await healthy.call('enable');
    assert.equal(healthyReply.state.enabled, true);
    assert.equal(healthyReply.state.error, null);
    results.push({case: 'writable service storage control', reply: healthyReply});
    console.log(JSON.stringify({source, cases: results.length, results}, null, 2));
  } finally { fs.rmSync(temporary, {recursive: true, force: true}); }
})().catch(error => { console.error(error); process.exitCode = 1; });
