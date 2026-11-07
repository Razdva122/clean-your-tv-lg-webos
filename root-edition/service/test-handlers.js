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
  console.log('recovery handler tests passed');
})().catch(function (e) {
  console.error(e);
  process.exit(1);
});
