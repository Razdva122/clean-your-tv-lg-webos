'use strict';
var assert = require('assert');
(async function () {
  var calls = [];
  var handlers = require('./handlers')(async function (command) {
    calls.push(command);
    return { ok: true };
  });
  assert.strictEqual((await handlers.boot({})).returnValue, false);
  assert.strictEqual(
    (
      await handlers.boot({
        reason: 'activity',
        $activity: { activityId: 1 },
        command: 'enable'
      })
    ).returnValue,
    false
  );
  assert.strictEqual(
    (await handlers.boot({ reason: 'activity', $activity: { activityId: 1 } }))
      .returnValue,
    true
  );
  assert.strictEqual(
    (await handlers.restore({ command: 'enable' })).returnValue,
    false
  );
  assert.strictEqual((await handlers.restore({})).returnValue, true);
  assert.strictEqual((await handlers.status({})).returnValue, true);
  assert.deepStrictEqual(calls, ['boot', 'restore', 'status']);
  const remoteCalls = [];
  const remote = require('./handlers')(async function (command, operation) {
    remoteCalls.push([command, operation]);
    if (operation === 'on') throw Error('Preference write failed');
    return {
      returnValue: true,
      result: { longBackOpensHome: operation !== 'off' }
    };
  });
  assert.deepStrictEqual((await remote.status({ longBack: 'status' })).result, {
    returnValue: true,
    result: { longBackOpensHome: true }
  });
  assert.deepStrictEqual(
    (await remote.enable({ longBack: 'configure', enabled: false })).result,
    { returnValue: true, result: { longBackOpensHome: false } }
  );
  assert.strictEqual(
    (await remote.enable({ longBack: 'configure', enabled: true })).returnValue,
    false
  );
  for (const payload of [
    { longBack: 'configure', enabled: 1 },
    { longBack: 'configure', enabled: false, extra: true },
    { longBack: 'status' }
  ])
    assert.strictEqual((await remote.enable(payload)).returnValue, false);
  assert.deepStrictEqual(remoteCalls, [
    ['long-back', 'status'],
    ['long-back', 'off'],
    ['long-back', 'on']
  ]);
  console.log('recovery handler tests passed');
})().catch(function (e) {
  console.error(e);
  process.exit(1);
});
