const assert = require('node:assert/strict');
const { claim } = require('../service/boot-state');
assert.equal(claim({ enabled: false }, 'boot-a'), null);
assert.equal(claim({ enabled: true, boot: 'boot-a' }, 'boot-a'), null);
assert.equal(claim({ enabled: true }, ''), null);
const next = claim({ enabled: true, boot: 'boot-a' }, 'boot-b');
assert.deepEqual(next, { enabled: true, boot: 'boot-b' });
assert.equal(claim(next, 'boot-b'), null);
console.log(
  'PASS: disabled, duplicate boot, invalid boot, next boot, no restart after failure'
);
const { identity } = require('../service/boot-state');
assert.notEqual(
  identity('snapshot-id', 'cpu 1 2\nbtime 100\n'),
  identity('snapshot-id', 'cpu 1 2\nbtime 200\n')
);
assert.equal(identity('snapshot-id', 'no boot timestamp'), '');
console.log(
  'PASS: restored boot UUID with different kernel boot time is a new boot'
);
a = require('node:assert/strict');
a.equal(claim({ enabled: true, boot: 'old' }, 'new', true), null);
console.log(
  'PASS: blocked latch prevents startup even if wall clock changes boot identity'
);
