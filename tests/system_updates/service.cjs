'use strict';
const assert = require('assert'),
  fs = require('fs'),
  vm = require('vm');
let handlers = {},
  calls = [];
const sandbox = {
  module: { exports: {} },
  exports: {},
  require(name) {
    if (name === 'webos-service')
      return function () {
        this.register = (n, fn) => (handlers[n] = fn);
      };
    if (name === 'child_process')
      return {
        execFile() {
          throw Error('not called');
        }
      };
    return require(name);
  },
  __dirname: '/fixed',
  process: { getuid: () => 0 },
  Buffer,
  Promise
};
let source;
try {
  source = fs.readFileSync(
    require('path').resolve(__dirname, '../../system-updater/service.js'),
    'utf8'
  );
} catch (e) {
  assert.fail('independent authorized service is missing');
}
vm.runInNewContext(source, sandbox);
let dispatch = sandbox.module.exports.createDispatch(async (m, p) => {
  calls.push({ m, p });
  return 'ok';
});
function caller(id) {
  return {
    ls2Message: {
      applicationID() {
        return id;
      }
    }
  };
}
(async () => {
  assert.equal(
    await dispatch(caller('com.gathin.tvhome 123'), 'install', {
      edition: 'no-root',
      release: 'v1.2.3',
      profile: {}
    }),
    'ok'
  );
  await assert.rejects(
    () =>
      dispatch(caller('com.cleanyourtv.updater'), 'install', {
        edition: 'no-root',
        release: 'v1.2.3',
        profile: {}
      }),
    /authorized/
  );
  await assert.rejects(
    () =>
      dispatch(caller('com.gathin.tvhome'), 'healthy', {
        edition: 'root',
        transaction: 'a'.repeat(32),
        version: '1.2.3'
      }),
    /authorized/
  );
  await assert.rejects(
    () => dispatch(caller('foreign'), 'status', {}),
    /authorized/
  );
  await assert.rejects(
    () =>
      dispatch(caller('com.gathin.tvhome'), 'install', {
        edition: 'no-root',
        release: 'v1.2.3',
        profile: {},
        url: 'evil'
      }),
    /request/
  );
  assert.equal(
    await dispatch(caller('com.cleanyourtv.root.updater'), 'rollback', {}),
    'ok'
  );
  assert.equal(Object.keys(handlers).length, 7);
  console.log('System updater authorization tests passed');
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
