const assert = require('assert');
const create = require('../../updater-service/manager');
const candidate = {
  home: '1.2.0',
  helper: '0.6.13',
  url: 'new',
  sha256: 'new'
};
const prior = { home: '1.1.0', helper: '0.6.13', url: 'old', sha256: 'old' };
function rig(extra = {}) {
  let state = null,
    calls = [],
    installed = '1.1.0';
  let io = {
    load: () => state && structuredClone(state),
    save: (s) => {
      state = JSON.parse(JSON.stringify(s));
    },
    root: async () => true,
    versions: async () => ({ home: installed, helper: '0.6.13' }),
    backup: async () => {},
    pauseRenewal: async (id) => ({ id, wasEnabled: false, confirmed: true }),
    resumeRenewal: async () => ({ restored: true }),
    install: async (m) => {
      calls.push(m.home);
      installed = m.home;
    },
    ...extra
  };
  return {
    manager: create(io),
    restart: () => create(io),
    calls,
    state: () => state
  };
}
(async () => {
  let r = rig();
  await r.manager.install(candidate, prior, { schema: 1 });
  assert.deepEqual(r.calls, ['1.2.0']);
  assert.equal(r.state().status, 'awaiting-launch');
  await r.manager.healthy('1.2.0');
  assert.equal(r.state().status, 'complete');
  await r.manager.rollback();
  assert.equal(r.state().status, 'rolled-back');
  assert.deepEqual(r.calls, ['1.2.0', '1.1.0']);
  r = rig({ root: async () => false });
  await assert.rejects(r.manager.install(candidate, prior, {}));
  assert.equal(r.calls.length, 0);
  r = rig({
    backup: async () => {
      throw Error('disk');
    }
  });
  await assert.rejects(r.manager.install(candidate, prior, {}));
  assert.equal(r.calls.length, 0);
  let calls = [];
  r = rig({
    install: async (m) => {
      calls.push(m.home);
      if (m.home === '1.2.0')
        throw Object.assign(Error('failed'), { definite: true });
    }
  });
  await r.manager.install(candidate, prior, {});
  assert.deepEqual(calls, ['1.2.0', '1.1.0']);
  assert.equal(r.state().status, 'rolled-back');
  r = rig({
    install: async () => {
      throw Error('timeout');
    }
  });
  await r.manager.install(candidate, prior, {});
  assert.equal(r.state().status, 'recovery-required');
  await assert.rejects(r.manager.install(candidate, prior, {}));
  await r.manager.reconcile();
  assert.equal(r.state().status, 'recovery-required');
  await assert.rejects(r.manager.install(candidate, prior, {}));
  r = rig();
  await r.manager.install(candidate, prior, {});
  await r.manager.healthy('1.2.0');
  const results = await Promise.allSettled([
    r.manager.rollback(),
    r.manager.rollback()
  ]);
  assert.equal(results.filter((x) => x.status === 'fulfilled').length, 1);
  assert.equal(r.calls.length, 2);
  r = rig();
  await assert.rejects(
    r.manager.install(candidate, { ...prior, helper: '0.6.12' }, {})
  );
  assert.equal(r.calls.length, 0);
  r = rig();
  await r.manager.install(candidate, prior, {});
  await r.manager.healthy(candidate.home);
  // The saved transaction, rather than a live manager or a recent health signal, owns recovery.
  r.state().startedAt = 1;
  let restarted = r.restart();
  assert.equal((await restarted.reconcile()).status, 'complete');
  assert.equal((await restarted.rollback()).status, 'rolled-back');
  await assert.rejects(restarted.rollback());
  assert.deepEqual(r.calls, ['1.2.0', '1.1.0']);
  r = rig();
  await r.manager.install(candidate, prior, {});
  await r.manager.healthy(candidate.home);
  const next = { ...candidate, home: '1.3.0' };
  await r.restart().install(next, candidate, { schema: 1 });
  await r.restart().healthy(next.home);
  assert.equal((await r.restart().rollback()).status, 'rolled-back');
  assert.deepEqual(r.calls, ['1.2.0', '1.3.0', '1.2.0']);
  console.log('PASS update transactions and recovery');
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
