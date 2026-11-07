'use strict';
const assert = require('assert');
(async () => {
  const calls = [];
  const h = require('./handlers')(async (c, tx) => {
    calls.push([c, tx]);
    return 'ok';
  });
  assert.strictEqual((await h.enable({})).returnValue, true);
  assert.strictEqual((await h.confirm({})).returnValue, false);
  assert.strictEqual(
    (await h.confirm({ transaction: 'not-a-uuid' })).returnValue,
    false
  );
  const tx = '12345678-1234-1234-1234-123456789abc';
  assert.strictEqual((await h.confirm({ transaction: tx })).returnValue, true);
  assert.deepStrictEqual(calls, [
    ['enable', undefined],
    ['confirm', tx]
  ]);
  console.log('persistent control handlers passed');
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
