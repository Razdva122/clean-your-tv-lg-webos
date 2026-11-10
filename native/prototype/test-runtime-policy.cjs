const a = require('node:assert/strict'),
  p = require('../app/runtime-policy');
a.equal(p.expired(0, 2500), false);
a.equal(p.expired(0, 2501), true);
for (const code of [0, 20, 22, 23, 24, 26, 27, 28, 30, 31])
  a.equal(p.shouldBlock(code, null), true);
a.equal(p.shouldBlock(null, 'SIGKILL'), true);
a.equal(p.shouldBlock(25, null), false);
console.log('PASS: watchdog boundary and persistent stop policy');
// Literal decisions catch OS/reported conflation, missing stop proof and budget bypass.
const vectors = [
  [{ code: 25 }, ['terminal', false, false, false]],
  [{ code: 25, ready: true }, ['terminal', false, true, false]],
  [{ code: 25, reportedReason: 27 }, ['terminal', true, false, true]],
  [
    { code: null, signal: 'SIGKILL', reportedReason: 27 },
    ['terminal', true, true, true]
  ],
  [{ code: 22 }, ['terminal', true, false, true]],
  [{ code: 20, tracked: true }, ['retry-watchdog', false, true, false]],
  [
    { code: 20, tracked: true, watchdog: true, watchdogOwned: true },
    ['retry-watchdog', false, true, false]
  ],
  [
    { code: 20, tracked: true, watchdog: true },
    ['terminal', true, false, false]
  ],
  [{ code: 20, tracked: true, stop: true }, ['terminal', true, false, true]],
  [
    { code: 20, tracked: true, blocked: true },
    ['terminal', true, false, false]
  ],
  [
    { code: 20, tracked: true, retryCount: 5 },
    ['terminal', true, false, false]
  ],
  [{ code: 20, tracked: false }, ['terminal', true, false, false]],
  [
    { code: null, signal: 'SIGKILL', tracked: true, watchdogKill: true },
    ['retry-watchdog', false, true, false]
  ],
  [
    { code: null, signal: 'SIGTERM', tracked: true, watchdogKill: true },
    ['terminal', true, true, false]
  ],
  [
    { code: 20, tracked: true, reportedReason: 31 },
    ['terminal', true, false, false]
  ],
  [
    { code: 32, tracked: true, reportedReason: 32, powerOffUntil: 1000 },
    ['wait-power', false, false, false]
  ],
  [
    { code: 32, tracked: true, reportedReason: 32, powerOffUntil: 999 },
    ['terminal', true, false, false]
  ],
  [
    { code: 32, tracked: true, powerOffUntil: 1000 },
    ['terminal', true, false, false]
  ],
  [
    {
      code: 32,
      tracked: true,
      reportedReason: 32,
      powerOffUntil: 1000,
      watchdog: true,
      watchdogOwned: true
    },
    ['terminal', true, false, false]
  ],
  [
    {
      code: 32,
      tracked: true,
      reportedReason: 32,
      powerOffUntil: 1000,
      stop: true
    },
    ['terminal', true, false, true]
  ],
  [
    {
      code: 32,
      tracked: true,
      reportedReason: 32,
      powerOffUntil: 1000,
      signal: 'SIGTERM'
    },
    ['terminal', true, true, false]
  ],
  [{ code: 99, reportedReason: 20 }, ['terminal', true, false, false]]
];
for (const [input, want] of vectors) {
  const d = p.classifyExit({ now: 1000, retryCount: 0, ...input });
  a.deepEqual(
    [d.action, d.block, d.cleanup, d.terminalUI],
    want,
    JSON.stringify(input)
  );
  a.equal(d.code, input.code);
  a.equal(d.signal, input.signal);
  a.equal(d.reportedReason, input.reportedReason);
}
const mismatch = p.classifyExit({ code: 99, reportedReason: 20 });
a.equal(mismatch.diagnostics[0].actual.os_code, 99);
a.equal(mismatch.diagnostics[0].actual.reported_code, 20);
a.equal(
  require('../app/contract-events').normalize(mismatch.diagnostics[0]).decision,
  'retain'
);
console.log(
  'PASS: literal lifecycle decisions and safe original exit diagnostics'
);
const exhausted = p.classifyExit({
  code: null,
  signal: 'SIGKILL',
  tracked: true,
  watchdogKill: true,
  retryCount: 5
});
a.equal(exhausted.exitCode, 20);
a.equal(exhausted.code, null);
a.equal(exhausted.signal, 'SIGKILL');
const signaled = p.classifyExit({
  code: null,
  signal: 'SIGKILL',
  reportedReason: 27
});
a.equal(signaled.diagnostics[1].field, 'signal');
a.equal(signaled.diagnostics[1].actual.code, 9);
const unknownSignal = p.classifyExit({ code: null, signal: 'private-signal' });
a.equal(unknownSignal.diagnostics[0].field, 'signal');
a.equal(unknownSignal.diagnostics[0].actual.length, 14);
a(!JSON.stringify(unknownSignal.diagnostics).includes('private-signal'));
