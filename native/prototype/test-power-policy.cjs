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
