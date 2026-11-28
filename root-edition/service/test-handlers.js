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
  var actions = [];
  var privacy = require('./handlers')(async function (command, action) {
    actions.push([command, action]);
    return { returnValue: true, result: 'off' };
  });
  assert.strictEqual(
    (await privacy.enable({ domainBlocking: 'status' })).returnValue,
    false
  );
  assert.strictEqual(
    (await privacy.status({ domainBlocking: 'on' })).returnValue,
    false
  );
  assert.strictEqual(
    (await privacy.enable({ domainBlocking: 'on', hosts: [] })).returnValue,
    false
  );
  for (const action of ['status', 'on', 'off'])
    assert.strictEqual(
      (
        await privacy[action === 'status' ? 'status' : 'enable']({
          domainBlocking: action
        })
      ).returnValue,
      true
    );
  assert.deepStrictEqual(
    actions,
    ['status', 'on', 'off'].map((action) => ['domain-blocking', action])
  );
  console.log('recovery handler tests passed');
})().catch(function (e) {
  console.error(e);
  process.exit(1);
});
