const assert = require('node:assert/strict');
const create = require('../../renewal-service/manager');
function rig(enabled) {
  let disk = { enabled },
    runs = 0,
    schedules = 0,
    cancels = 0;
  const io = {
    load: () => structuredClone(disk),
    save: (s) => {
      disk = structuredClone(s);
    },
    now: () => 10,
    run: async () => {
      runs++;
      return { status: 'healthy' };
    },
    schedule: async () => {
      schedules++;
      return { returnValue: true };
    },
    cancel: async () => {
      cancels++;
      return { returnValue: true };
    }
  };
  return {
    io,
    m: create(io),
    restart: () => create(io),
    counts: () => ({ runs, schedules, cancels }),
    disk: () => disk
  };
}
(async () => {
  let r = rig(true);
  assert.equal(
    typeof r.m.pauseForUpdate,
    'function',
    'renewal needs a durable update pause'
  );
  let s = await r.m.pauseForUpdate('job-1');
  assert.equal(s.updatePause.confirmed, true);
  assert.equal(s.enabled, false);
  await r.m.check();
  assert.equal(r.counts().runs, 0);
  let m = r.restart();
  assert.equal(m.allowed(), false);
  await m.resumeAfterUpdate('wrong');
  assert.equal(m.allowed(), false);
  await m.resumeAfterUpdate('job-1');
  assert.equal(m.allowed(), true);
  assert.equal(r.counts().schedules, 1);
  r = rig(false);
  await r.m.pauseForUpdate('job-2');
  await r.m.resumeAfterUpdate('job-2');
  assert.equal(r.m.allowed(), false);
  assert.equal(r.counts().schedules, 0);
  r = rig(true);
  let finish;
  r.io.run = () =>
    new Promise((resolve) => {
      finish = resolve;
    });
  const running = r.m.check();
  await new Promise((resolve) => setImmediate(resolve));
  let settled = false;
  const paused = r.m.pauseForUpdate('job-3').then(() => {
    settled = true;
  });
  assert.equal(r.m.allowed(), false);
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(settled, false);
  finish({ status: 'healthy' });
  await running;
  await paused;
  assert.equal(r.disk().updatePause.confirmed, true);
  r = rig(true);
  r.io.cancel = async () => ({ returnValue: false });
  s = await r.m.pauseForUpdate('job-4');
  assert.equal(s.updatePause.confirmed, false);
  assert.equal(s.error, 'cancel-unconfirmed');
  assert.equal((await r.m.resumeAfterUpdate('job-4')).enabled, false);
  r = rig(true);
  await r.m.pauseForUpdate('job-5');
  await r.m.disable();
  await r.m.resumeAfterUpdate('job-5');
  assert.equal(r.m.allowed(), false);
  assert.equal(r.counts().schedules, 0);
  r = rig(true);
  await r.m.pauseForUpdate('job-6');
  s = await r.m.enable();
  assert.equal(s.enabled, false);
  assert.equal(s.error, 'update-in-progress');
  await r.m.pauseForUpdate('other');
  assert.equal(r.m.status().updatePause.id, 'job-6');
  r = rig(true);
  await r.m.pauseForUpdate('job-7');
  r.io.schedule = async () => ({ returnValue: false });
  s = await r.m.resumeAfterUpdate('job-7');
  assert.equal(s.enabled, false);
  assert.equal(s.updatePause.id, 'job-7');
  r = rig(true);
  r.io.save = () => {
    throw Error('disk full');
  };
  s = await r.m.pauseForUpdate('job-8');
  assert.notEqual(s.updatePause.confirmed, true);
  assert.equal(r.m.allowed(), false);
  r = rig(true);
  await r.m.pauseForUpdate('job-9');
  let releaseSchedule;
  r.io.schedule = () =>
    new Promise((resolve) => {
      releaseSchedule = resolve;
    });
  const resuming = r.m.resumeAfterUpdate('job-9');
  await new Promise((resolve) => setImmediate(resolve));
  const disabling = r.m.disable();
  releaseSchedule({ returnValue: true });
  await Promise.all([resuming, disabling]);
  assert.equal(r.m.allowed(), false);
  assert.equal(r.disk().enabled, false);
  r = rig(true);
  await r.m.pauseForUpdate('job-10');
  const save = r.io.save;
  r.io.save = () => {
    throw Error('disk full');
  };
  await r.m.resumeAfterUpdate('job-10');
  assert.equal(r.m.allowed(), false);
  r.io.save = save;
  await r.m.resumeAfterUpdate('job-10');
  assert.equal(
    r.m.allowed(),
    true,
    'failed persistence must retain a retryable pause'
  );
  r = rig(true);
  await r.m.pauseForUpdate('job-11');
  r.io.cancel = async () => ({ returnValue: false });
  s = await r.m.pauseForUpdate('job-11');
  assert.equal(
    s.updatePause.confirmed,
    false,
    'retry must not reuse an earlier cancellation confirmation'
  );
  r = rig(true);
  await r.m.pauseForUpdate('job-12');
  await r.m.resumeAfterUpdate('job-12');
  await r.m.disable();
  s = await r.restart().resumeAfterUpdate('job-12');
  assert.equal(s.completedUpdate, 'job-12');
  assert.equal(s.enabled, false);
  assert(!s.error);
  console.log(
    'PASS durable renewal pause, in-flight drain, restart, failure and user disable'
  );
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
