'use strict';
const assert = require('node:assert/strict');
const diagnostics = require('../app/diagnostics.js')({});

const hostile = {
  state: 'recovery_required',
  code: 'operation_requires_recovery',
  stage: 'blocked',
  operation: 'a'.repeat(32),
  reason: 'restart-required',
  failure: {
    inspect_check: 'live_original_worker',
    errorText: 'test-secret /var/private 192.168.2.3',
    exception_type: 'OSError'
  }
};
const record = diagnostics.record('setup', hostile);
assert.deepEqual(record, {
  schema: 1,
  source: 'setup',
  code: 'operation_requires_recovery',
  state: 'recovery_required',
  stage: 'blocked',
  detail: 'live_original_worker'
});
assert.deepEqual(diagnostics.advice(record), [
  'restartNeeded',
  'restartAndRetry'
]);

const unknown = diagnostics.record('setup', {
  state: 'x'.repeat(30),
  code: 'private-serial-12345',
  stage: '/tmp/user',
  reason: 'do not export this',
  failure: { inspect_check: '192.168.2.3' }
});
assert.deepEqual(unknown, { schema: 1, source: 'setup', code: 'unconfirmed' });
assert.deepEqual(diagnostics.advice(unknown), [
  'reasonUnknown',
  'checkOrComputer'
]);
assert.deepEqual(
  diagnostics.advice(diagnostics.record('setup', {}, 'homebrew_exec_denied')),
  ['homebrewDeniedTitle', 'homebrewDeniedBody']
);
assert.deepEqual(
  diagnostics.advice(
    diagnostics.record('recovery', {}, 'update_service_unavailable')
  ),
  ['updateServiceUnavailable', 'computerRecovery']
);
assert.deepEqual(
  diagnostics.advice(
    diagnostics.record('setup', {
      state: 'recovery_required',
      failure: { package_rejected: true }
    })
  ),
  ['packageRejected', 'checkOrComputer']
);
assert.deepEqual(
  diagnostics.advice(
    diagnostics.record('setup', {
      state: 'complete',
      activation: { state: 'unverified' }
    })
  ),
  ['activationUnverified', 'checkOrComputer']
);

const memory = new Map();
const storage = {
  getItem: (key) => memory.get(key),
  setItem: (key, value) => memory.set(key, value)
};
const saved = require('../app/diagnostics.js')({ localStorage: storage });
assert.equal(saved.save(record), true);
assert.deepEqual(saved.load(), record);
const key = [...memory.keys()][0];
memory.set(key, JSON.stringify({ ...record, password: 'test-secret' }));
assert.equal(saved.load(), null, 'unexpected saved fields cannot be displayed');
memory.set(key, JSON.stringify({ ...record, detail: 'test-secret' }));
assert.equal(saved.load(), null, 'stored values are validated again');
const blocked = require('../app/diagnostics.js')({
  get localStorage() {
    throw Error('storage denied');
  }
});
assert.equal(blocked.save(record), false);
assert.equal(blocked.load(), null);
assert.equal(
  saved.save({ ...record, serial: 'test-secret' }),
  false,
  'unvalidated input cannot be written'
);
console.log(
  'PASS bounded diagnostic classification and safe persistent report'
);
