const assert = require('node:assert/strict');
const create = require('../../updater-service/manager');
const candidate = { home: '1.2.1', helper: '0.6.13' },
  prior = { home: '1.2.0', helper: '0.6.13' };
function rig() {
  let disk = null,
    version = prior.home;
  const events = [];
  const io = {
    load: () => disk && structuredClone(disk),
    save: (s) => {
      disk = structuredClone(s);
      events.push(s.status);
    },
    root: async () => true,
    versions: async () => ({ home: version, helper: prior.helper }),
    backup: async () => {},
    pauseRenewal: async (id) => {
      events.push('pause');
      assert.equal(disk.status, 'pausing-renewal');
      assert.equal(disk.id, id);
      return { id, wasEnabled: true, confirmed: true };
    },
    resumeRenewal: async (receipt) => {
      events.push('resume');
      assert.equal(receipt.wasEnabled, true);
      return { restored: true };
    },
    install: async (m) => {
      events.push('install');
      version = m.home;
    }
  };
  return {
    io,
    events,
    m: create(io),
    state: () => disk,
    restart: () => create(io)
  };
}
async function expectExclusiveRestoration(
  r,
  operation,
  expected,
  fail = false
) {
  let started, resolve;
  const restoring = new Promise((signal) => (started = signal));
  const response = new Promise((signal) => (resolve = signal));
  const resume = r.io.resumeRenewal;
  r.io.resumeRenewal = async (receipt) => {
    const result = await resume(receipt);
    if (!started) return result;
    started();
    started = null;
    return response;
  };
  const completion = operation();
  await restoring;
  const installs = r.events.filter((event) => event === 'install').length;
  try {
    await assert.rejects(r.m.reconcile(), { message: 'busy' });
    assert.equal(r.state().status, 'restoring-renewal');
  } finally {
    resolve({ restored: !fail });
    await completion;
  }
  assert.equal(r.events.filter((event) => event === 'resume').length, 1);
  assert.equal(r.state().status, fail ? 'renewal-recovery' : expected);
  if (fail) {
    r.io.resumeRenewal = resume;
    await r.m.reconcile();
    assert.equal(r.state().status, expected);
  }
  assert.equal(
    r.events.filter((event) => event === 'install').length,
    installs
  );
}

(async () => {
  let r = rig();
  await r.m.install(candidate, prior, {});
  await expectExclusiveRestoration(
    r,
    () => r.m.healthy(candidate.home),
    'complete',
    true
  );
  r = rig();
  await r.m.install(candidate, prior, {});
  await expectExclusiveRestoration(r, () => r.m.rollback(), 'rolled-back');
  r = rig();
  const install = r.io.install;
  r.io.install = async (m) => {
    if (m === candidate)
      throw Object.assign(Error('rejected'), { definite: true });
    return install(m);
  };
  await expectExclusiveRestoration(
    r,
    () => r.m.install(candidate, prior, {}),
    'rolled-back'
  );
  r = rig();
  const pause = r.io.pauseRenewal;
  r.io.pauseRenewal = async () => {
    throw Error('timeout');
  };
  await r.m.install(candidate, prior, {});
  r.io.pauseRenewal = pause;
  await expectExclusiveRestoration(r, () => r.m.reconcile(), 'aborted');
  r = rig();
  await r.m.install(candidate, prior, {});
  assert(
    r.events.indexOf('pause') >= 0,
    'must pause renewal before installing'
  );
  assert(r.events.indexOf('pause') < r.events.indexOf('install'));
  assert(!r.events.includes('resume'));
  await r.m.healthy(candidate.home);
  assert.equal(r.state().status, 'complete');
  assert(r.events.includes('resume'));
  r = rig();
  r.io.pauseRenewal = async () => {
    throw Error('timeout');
  };
  await r.m.install(candidate, prior, {});
  assert.equal(r.state().status, 'renewal-recovery');
  assert(!r.events.includes('install'));
  await assert.rejects(r.m.install(candidate, prior, {}));
  r = rig();
  r.io.install = async () => {
    throw Error('timeout');
  };
  await r.m.install(candidate, prior, {});
  assert.equal(r.state().status, 'recovery-required');
  assert(!r.events.includes('resume'));
  r = rig();
  await r.m.install(candidate, prior, {});
  r.io.resumeRenewal = async () => {
    throw Error('service unavailable');
  };
  await r.m.healthy(candidate.home);
  assert.equal(r.state().status, 'renewal-recovery');
  assert.equal(r.state().terminalStatus, 'complete');
  r.io.resumeRenewal = async () => ({ restored: true });
  await r.restart().reconcile();
  assert.equal(r.state().status, 'complete');
  assert.equal(r.events.filter((x) => x === 'install').length, 1);
  r = rig();
  await r.m.install(candidate, prior, {});
  await r.m.healthy(candidate.home);
  const pauses = r.events.filter((x) => x === 'pause').length;
  await r.m.rollback();
  assert.equal(r.events.filter((x) => x === 'pause').length, pauses + 1);
  assert.equal(r.state().status, 'rolled-back');
  r = rig();
  const original = r.io.install;
  r.io.install = async (m) => {
    if (m === candidate)
      throw Object.assign(Error('rejected'), { definite: true });
    return original(m);
  };
  await r.m.install(candidate, prior, {});
  assert.equal(r.state().status, 'rolled-back');
  assert(r.events.includes('resume'));
  r = rig();
  const persist = r.io.save;
  let fail = true;
  r.io.save = (s) => {
    if (fail && s.status === 'installing') throw Error('disk');
    persist(s);
  };
  await assert.rejects(r.m.install(candidate, prior, {}));
  assert(!r.events.includes('install'));
  fail = false;
  await r.restart().reconcile();
  assert.equal(r.state().status, 'aborted');
  assert(!r.events.includes('install'));
  r = rig();
  r.io.pauseRenewal = async (id) => ({
    id: 'wrong',
    wasEnabled: true,
    confirmed: true
  });
  await r.m.install(candidate, prior, {});
  assert.equal(r.state().status, 'renewal-recovery');
  assert(!r.events.includes('install'));
  r = rig();
  await r.m.install(candidate, prior, {});
  r.io.resumeRenewal = async () => ({ restored: false });
  await r.m.healthy(candidate.home);
  assert.equal(r.state().status, 'renewal-recovery');
  await assert.rejects(r.m.rollback());
  console.log(
    'PASS update pause journal, ambiguous failure, restore retry and rollback pause'
  );
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
