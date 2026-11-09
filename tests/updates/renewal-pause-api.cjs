const assert = require('node:assert/strict'),
  vm = require('node:vm'),
  fs = require('node:fs');
const methods = {};
let calls = [];
function Service() {
  this.register = (name, fn) => (methods[name] = fn);
}
const manager = {
  importUpdatePause: async (receipt) => {
    calls.push(['import', receipt]);
    return { enabled: false };
  },
  pauseForUpdate: async (id) => {
    calls.push(['pause', id]);
    return { enabled: false };
  },
  resumeAfterUpdate: async (id) => {
    calls.push(['resume', id]);
    return { enabled: false };
  }
};
vm.runInNewContext(fs.readFileSync('renewal-service/service.js', 'utf8'), {
  require: (n) =>
    n === './weather'
      ? require('../../renewal-service/weather')
      : n === './theme-receiver'
        ? require('../../theme-receiver/register')
        : n === 'fs'
          ? {}
          : n === 'webos-service'
            ? Service
            : n === './diagnostics'
              ? require('../../renewal-service/diagnostics')
              : n === './package.json'
                ? require('../../renewal-service/package.json')
                : n === './home-control'
                  ? require('../../renewal-service/home-control')
                  : n === './manager'
                    ? () => manager
                    : n === './local-io'
                      ? { createLocalIO: () => ({}) }
                      : n === './transport'
                        ? { createRequest: () => {} }
                        : n === './renewal'
                          ? { createRenewal: () => ({}) }
                          : null,
  __dirname: '/unused',
  setTimeout,
  clearTimeout,
  Date,
  Promise
});
function request(method, sender, appId = '') {
  return new Promise((resolve) =>
    methods[method]({
      payload: { id: 'job-1' },
      ls2Message: {
        applicationID: () => appId,
        senderServiceName: () => sender
      },
      respond: resolve
    })
  );
}
(async () => {
  assert.equal(typeof methods.pauseForUpdate, 'function');
  for (const method of ['homeStatus', 'setHomeControl', 'openLGHome'])
    assert.equal(
      (await request(method, 'other.service', 'other.app')).returnValue,
      false
    );
  assert.equal(
    (await request('pauseForUpdate', 'other.service')).returnValue,
    false
  );
  assert.equal(
    (
      await request(
        'pauseForUpdate',
        'com.cleanyourtv.updater.service',
        'other.app'
      )
    ).returnValue,
    false
  );
  assert.equal(
    (await request('importUpdatePause', 'other.service')).returnValue,
    false
  );
  assert.equal(calls.length, 0);
  assert.equal(
    (await request('pauseForUpdate', 'com.cleanyourtv.updater.service'))
      .returnValue,
    true
  );
  assert.equal(
    (await request('resumeAfterUpdate', 'com.cleanyourtv.updater.service'))
      .returnValue,
    true
  );
  assert.deepEqual(calls, [
    ['pause', 'job-1'],
    ['resume', 'job-1']
  ]);
  assert.equal(
    (await request('importUpdatePause', 'com.cleanyourtv.updater.service'))
      .returnValue,
    true
  );
  assert.equal(calls[2][0], 'import');
  console.log('PASS renewal pause endpoints only accept updater bus identity');
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
