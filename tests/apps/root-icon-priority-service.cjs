'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const { test } = require('node:test');

test('Root service keeps different icon priorities independent and releases failed reads', async () => {
  const methods = {},
    calls = [];
  const inventory = Object.assign(
    (exec, uid, ids) =>
      new Promise((resolve, reject) => {
        calls.push({
          ids: ids === undefined ? [] : JSON.parse(JSON.stringify(ids)),
          resolve,
          reject
        });
      }),
    { inputHandler: () => () => assert.fail('unexpected input query') }
  );
  vm.runInNewContext(
    fs.readFileSync('root-edition/service/service.js', 'utf8'),
    {
      __dirname: '/fixture/service',
      process: { getuid: () => 0 },
      Promise,
      require(name) {
        if (name === 'webos-service')
          return function () {
            this.register = (name, fn) => {
              methods[name] = fn;
            };
          };
        if (name === 'child_process')
          return { execFile() {}, execFileSync() {} };
        if (name === '/var/lib/clean-your-tv-root/python_boot.js')
          return { command: () => '/usr/bin/python' };
        if (name === './handlers')
          return require('../../root-edition/service/handlers');
        if (name === './app-inventory') return inventory;
        if (name === './presentation-context') return () => ({});
        if (name === './weather')
          return require('../../renewal-service/weather');
        if (name === './theme-receiver')
          return require('../../theme-receiver/register');
        if (name === './c1-lease') return () => {};
        throw Error('Unexpected module ' + name);
      }
    }
  );
  function request(payload) {
    const replies = [];
    methods.listApps({
      payload,
      respond: (reply) => replies.push(JSON.parse(JSON.stringify(reply)))
    });
    return replies;
  }
  for (const ids of [
    null,
    {},
    'late',
    [false],
    [''],
    ['x'.repeat(257)],
    Array(201).fill('late')
  ]) {
    assert.equal(request({ priorityIds: ids })[0].returnValue, false);
  }
  assert.equal(
    calls.length,
    0,
    'invalid priority metadata cannot start a catalog query'
  );
  const legacy = request(null);
  const pinned = request({ priorityIds: ['late'] });
  const same = request({ priorityIds: ['late'] });
  assert.equal(
    calls.length,
    2,
    'do not reuse an unprioritized in-flight response'
  );
  assert.deepEqual(
    calls.map((c) => c.ids),
    [[], ['late']]
  );
  calls[0].resolve([{ id: 'late', icon: '' }]);
  await new Promise((resolve) => setImmediate(resolve));
  request({ priorityIds: ['late'] });
  assert.equal(
    calls.length,
    2,
    'an older completion cannot clear the newer pending slot'
  );
  calls[1].resolve([{ id: 'late', icon: 'data:image/png;base64,aWNvbg==' }]);
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(legacy[0].apps[0].icon, '');
  assert(pinned[0].apps[0].icon);
  assert.deepEqual(pinned, same);
  const failed = request({ priorityIds: ['other'] });
  calls[2].reject(Error('unavailable'));
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(failed[0].returnValue, false);
  request({ priorityIds: ['other'] });
  assert.equal(calls.length, 4, 'retry after failure starts a fresh read');
  calls[3].resolve([]);
});
