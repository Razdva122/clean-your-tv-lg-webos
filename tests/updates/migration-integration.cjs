const assert = require('node:assert/strict');
const renewalFactory = require('../../renewal-service/manager'),
  updateFactory = require('../../updater-service/manager');
async function scenario(enabled, manualOff) {
  let renewalDisk = { enabled },
    journal = null,
    version = '1.2.0',
    schedules = 0;
  const renewIO = {
    load: () => renewalDisk && structuredClone(renewalDisk),
    save: (s) => {
      renewalDisk = structuredClone(s);
    },
    cancel: async () => ({ returnValue: true }),
    schedule: async () => {
      schedules++;
      return { returnValue: true };
    },
    run: async () => ({ status: 'healthy' }),
    now: () => 1
  };
  let renewal = renewalFactory(renewIO);
  const io = {
    load: () => journal && structuredClone(journal),
    save: (s) => {
      journal = structuredClone(s);
    },
    root: async () => true,
    versions: async () => ({ home: version, helper: '0.6.13' }),
    backup: async () => {},
    pauseRenewal: async (id) => (await renewal.pauseForUpdate(id)).updatePause,
    install: async (pkg) => {
      version = pkg.home;
      renewalDisk = null;
      renewal = renewalFactory(renewIO);
    },
    resumeRenewal: async (receipt) => {
      let s = await renewal.importUpdatePause(receipt);
      if (s.error) return { restored: false };
      s = await renewal.resumeAfterUpdate(receipt.id);
      return {
        restored: !s.error && s.completedUpdate === receipt.id && !s.updatePause
      };
    }
  };
  let updater = updateFactory(io);
  await updater.install(
    { home: '1.2.1', helper: '0.6.13' },
    { home: '1.2.0', helper: '0.6.13' },
    {}
  );
  assert.equal(renewal.allowed(), false);
  assert.equal(schedules, 0);
  if (manualOff) await renewal.disable();
  updater = updateFactory(io);
  await updater.healthy('1.2.1');
  assert.equal(journal.status, 'complete');
  assert.equal(renewal.allowed(), enabled && !manualOff);
  assert.equal(schedules, enabled && !manualOff ? 1 : 0);
  await updater.rollback();
  assert.equal(journal.status, 'rolled-back');
  assert.equal(version, '1.2.0');
  assert.equal(renewal.allowed(), enabled && !manualOff);
}
(async () => {
  await scenario(true, false);
  await scenario(false, false);
  await scenario(true, true);
  console.log(
    'PASS real managers across erased package state, updater restart and rollback'
  );
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
