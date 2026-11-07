const assert = require('node:assert/strict');
const create = require('../renewal-service/manager');
function setup() {
  let state = { enabled: false },
    schedules = 0,
    cancels = 0,
    runs = 0,
    fail = false;
  const io = {
    load: () => state,
    save: (s) => {
      state = { ...s };
    },
    schedule: async () => {
      schedules++;
      return { returnValue: !fail };
    },
    cancel: async () => {
      cancels++;
      return { returnValue: true };
    },
    run: async () => {
      runs++;
      return { status: 'healthy', remainingSeconds: 1000 };
    },
    now: () => 1000
  };
  return {
    m: create(io),
    io,
    counts: () => ({ schedules, cancels, runs }),
    fail: () => {
      fail = true;
    },
    state: () => state
  };
}
(async () => {
  let t = setup();
  await t.m.check();
  assert.equal(t.counts().runs, 0);
  assert.equal(t.m.status().enabled, false);
  await t.m.enable();
  assert.equal(t.state().enabled, true);
  assert.equal(t.counts().runs, 1);
  assert.equal(t.counts().schedules, 1);
  await t.m.disable();
  assert.equal(t.state().enabled, false);
  assert.equal(t.counts().cancels, 1);
  await t.m.check();
  assert.equal(t.counts().runs, 1);
  t = setup();
  t.fail();
  await t.m.enable();
  assert.equal(t.state().enabled, false);
  assert.equal(t.counts().runs, 0);
  t = setup();
  let release;
  t.io.run = () =>
    new Promise((r) => {
      release = r;
    });
  let p = t.m.enable();
  await new Promise((r) => setImmediate(r));
  let d = t.m.disable();
  assert.equal(t.m.allowed(), false);
  release({ status: 'healthy' });
  await Promise.all([p, d]);
  assert.equal(t.state().enabled, false);
  assert.equal(t.counts().cancels, 1);
  t = setup();
  let finishSchedule;
  t.io.schedule = () =>
    new Promise((r) => {
      finishSchedule = r;
    });
  p = t.m.enable();
  await new Promise((r) => setImmediate(r));
  d = t.m.disable();
  finishSchedule({ returnValue: true });
  await Promise.all([p, d]);
  assert.equal(t.counts().runs, 0);
  assert.equal(t.state().enabled, false);
  t = setup();
  t.io.save = () => {
    throw Error('disk');
  };
  assert.equal((await t.m.enable()).enabled, false);
  assert.equal(t.counts().runs, 0);
  t = setup();
  await t.m.enable();
  t.io.save = () => {
    throw Error('disk full');
  };
  let off = await t.m.disable();
  assert.equal(t.counts().cancels, 1);
  assert.equal(off.error, 'disable-not-saved');
  console.log('renewal manager tests passed');
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
