const assert = require('assert'),
  create = require('../../renewal-service/manager');
let saved = { enabled: false },
  scheduled = 0,
  runs = 0;
const m = create({
  load: () => saved,
  save: (s) => {
    saved = JSON.parse(JSON.stringify(s));
  },
  schedule: async () => {
    scheduled++;
  },
  run: async () => {
    runs++;
  },
  now: Date.now
});
(async () => {
  await m.restoreHistory({ enabled: true, last: { status: 'renewed' } });
  assert.equal(saved.last, undefined);
  await m.restoreHistory({
    enabled: false,
    last: { status: 'healthy', checkedAt: 100, token: 'never copy' },
    lastRenewedAt: 90
  });
  assert.equal(saved.last.checkedAt, 100);
  assert.equal(saved.last.token, undefined);
  assert.equal(saved.enabled, false);
  assert.equal(scheduled, 0);
  assert.equal(runs, 0);
  await m.restoreHistory({ enabled: false, last: { status: 'old' } });
  assert.equal(saved.last.status, 'healthy');
  console.log('PASS renewal history restores without enabling or scheduling');
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
