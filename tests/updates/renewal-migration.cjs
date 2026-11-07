const assert = require('node:assert/strict'),
  create = require('../../renewal-service/manager');
function rig(initial) {
  let disk = initial,
    schedules = 0;
  const io = {
    load: () => disk && structuredClone(disk),
    save: (s) => {
      disk = structuredClone(s);
    },
    cancel: async () => ({ returnValue: true }),
    schedule: async () => {
      schedules++;
      return { returnValue: true };
    },
    run: async () => ({ status: 'healthy' }),
    now: () => 1
  };
  return {
    io,
    m: create(io),
    restart: () => create(io),
    count: () => schedules
  };
}
const receipt = { id: 'migration-1', wasEnabled: true, confirmed: true };
(async () => {
  let r = rig();
  assert.equal(typeof r.m.importUpdatePause, 'function');
  let s = await r.m.importUpdatePause(receipt);
  assert.equal(s.updatePause.id, receipt.id);
  assert.equal(r.m.allowed(), false);
  assert.equal(r.count(), 0);
  await r.restart().resumeAfterUpdate(receipt.id);
  assert.equal(r.count(), 1);
  r = rig();
  await r.m.disable();
  await r.m.importUpdatePause(receipt);
  await r.m.resumeAfterUpdate(receipt.id);
  assert.equal(r.m.allowed(), false);
  assert.equal(r.count(), 0);
  r = rig();
  await r.m.importUpdatePause({ ...receipt, wasEnabled: false });
  await r.m.resumeAfterUpdate(receipt.id);
  assert.equal(r.m.allowed(), false);
  r = rig();
  await r.m.importUpdatePause(receipt);
  await r.m.disable();
  await r.m.importUpdatePause(receipt);
  await r.m.resumeAfterUpdate(receipt.id);
  assert.equal(r.m.allowed(), false);
  r = rig();
  await r.m.importUpdatePause(receipt);
  await r.m.resumeAfterUpdate(receipt.id);
  await r.m.disable();
  await r.restart().importUpdatePause(receipt);
  assert.equal(r.m.allowed(), false);
  assert.equal(r.count(), 1);
  r = rig();
  s = await r.m.importUpdatePause({ ...receipt, confirmed: false });
  assert.equal(s.error, 'invalid-pause-receipt');
  assert(!s.updatePause);
  r = rig({ enabled: false, error: 'storage-error' });
  s = await r.m.importUpdatePause(receipt);
  assert.equal(s.error, 'pause-import-conflict');
  assert(!s.updatePause);
  r = rig({ enabled: false, completedUpdate: 'other' });
  s = await r.m.importUpdatePause(receipt);
  assert.equal(s.error, 'pause-import-conflict');
  r = rig();
  r.io.cancel = async () => ({ returnValue: false });
  s = await r.m.importUpdatePause(receipt);
  assert.equal(s.updatePause.confirmed, false);
  assert.equal(s.error, 'cancel-unconfirmed');
  assert.equal(r.count(), 0);
  r.io.cancel = async () => ({ returnValue: true });
  s = await r.m.importUpdatePause(receipt);
  assert.equal(s.updatePause.confirmed, true);
  assert(!s.error);
  console.log(
    'PASS renewal receipt migration, restart, manual preference and conflict rejection'
  );
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
