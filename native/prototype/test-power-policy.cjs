const a = require('node:assert/strict'),
  make = require('../app/power-policy');
let p = make();
a.equal(p.next({ state: 'Active' }), false);
a.equal(
  p.next({ state: 'Active', processing: 'Request Power Off', onOff: 'off' }),
  false
);
a.equal(p.next({ state: 'Active Standby' }), false);
a.equal(
  p.next({ state: 'Active Standby', processing: 'Screen On', onOff: 'on' }),
  false
);
a.equal(p.next({ state: 'Active' }), true);
a.equal(p.next({ state: 'Active' }), false);
p.next({ state: 'Active Standby' });
a.equal(
  p.next({ state: 'Active', processing: 'Prepare Power On', onOff: 'on' }),
  false
);
a.equal(p.next({ state: 'Active' }), true);
a.equal(p.next({ state: 'Screen Off' }), false);
a.equal(p.next({ state: 'Active' }), false);
console.log(
  'PASS: standby resume once; initial active, intermediate states and screen-off ignored'
);
// Truthy firmware processing must delay wake, including unknown types.
for (const [processing, settled, count] of [
  ['Request Power Off', false, 0],
  ['Screen On', false, 0],
  ['Prepare Power On', false, 0],
  [true, false, 0],
  [false, true, 0],
  [undefined, true, 0],
  ['private-marker', false, 1],
  [{ secret: 'private-marker' }, false, 1],
  [0, true, 1]
]) {
  const policy = make();
  policy.observe({ state: 'Suspend' }, 1000);
  const facts = policy.observe(
    { state: 'Active', processing, onOff: 'on' },
    1200
  );
  a.equal(facts.settledActive, settled);
  a.equal(facts.resumed, settled);
  a.equal(facts.command, 'R');
  a.equal(facts.deadline, 0);
  a.equal(facts.cancelWakeWait, !settled);
  a.equal(facts.diagnostics.length, count);
  a(!JSON.stringify(facts.diagnostics).includes('private-marker'));
}
const facts = make().observe({ state: 'Prepare Power Off' }, 1000);
a.deepEqual(
  [
    facts.command,
    facts.deadline,
    facts.settledActive,
    facts.cancelWakeWait,
    facts.cancelPresentation
  ],
  ['T', 16000, false, true, false]
);
a.equal(make().observe({ state: 'Suspend' }, 1000).cancelPresentation, true);
a.equal(
  make().observe({ state: 'unknown-private-value' }, 1000).diagnostics.length,
  1
);
console.log(
  'PASS: normalized firmware power facts preserve truthiness without private diagnostics'
);
for (const payload of [null, undefined, false, 'private-value', []]) {
  const d = make().observe(payload, 1000);
  a.deepEqual([d.command, d.settledActive, d.resumed], [null, false, false]);
  a.equal(d.diagnostics[0].field, 'payload');
  a(!JSON.stringify(d.diagnostics).includes('private-value'));
}
