const a = require('node:assert/strict'),
  p = require('../app/runtime-policy');
a.equal(p.expired(0, 2500), false);
a.equal(p.expired(0, 2501), true);
for (const code of [0, 20, 22, 23, 24, 26, 27, 28, 30, 31])
  a.equal(p.shouldBlock(code, null), true);
a.equal(p.shouldBlock(null, 'SIGKILL'), true);
a.equal(p.shouldBlock(25, null), false);
console.log('PASS: watchdog boundary and persistent stop policy');
