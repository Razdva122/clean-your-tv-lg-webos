'use strict';
const assert = require('node:assert/strict');
const { observe } = require('../app/setup-progress.js');

const initial = observe(null, null, null, true);
assert.equal(initial['homebrew-access'], 'running');
assert.equal(initial['python-runtime'], 'pending');
const inspected = {
  checks: {
    'homebrew-access': 'pass',
    'python-runtime': 'pass',
    'product-state': 'pass'
  }
};
for (const stage of ['submitted', 'resume-submitted']) {
  assert.equal(
    observe(inspected, { action: 'install', state: 'pending', stage })[
      'install-request'
    ],
    'running'
  );
}
assert.equal(
  observe(inspected, {
    action: 'install',
    state: 'recovery_required',
    stage: 'blocked'
  })['install-request'],
  'fail'
);
assert.equal(
  observe(inspected, null, null, true, 'running')['python-runtime'],
  'running'
);
const pending = observe(inspected, {
  action: 'install',
  state: 'pending',
  stage: 'supervisor'
});
assert.equal(pending['install-root'], 'pass');
assert.equal(pending['install-updates'], 'running');
assert.equal(pending['install-readback'], 'pending');
assert.equal(pending['activate-home'], 'pending');
const failed = observe(inspected, {
  action: 'install',
  state: 'recovery_required',
  stage: 'supervisor'
});
assert.equal(failed['install-updates'], 'fail');
assert.equal(failed['install-readback'], 'pending');
assert.equal(
  observe(
    inspected,
    { action: 'install', state: 'pending', stage: 'supervisor' },
    'status_unavailable'
  )['install-updates'],
  'unknown'
);
assert.equal(
  observe(null, null, 'homebrew_exec_denied')['homebrew-access'],
  'fail'
);
assert.equal(
  observe(
    inspected,
    { action: 'install', stage: 'supervisor' },
    'homebrew_exec_denied'
  )['homebrew-access'],
  'fail'
);
assert.equal(
  observe(null, null, 'homebrew_timeout')['homebrew-access'],
  'unknown'
);
assert.equal(
  observe(inspected, {
    action: 'install',
    state: 'complete',
    stage: 'complete',
    activation: { state: 'cancelled' }
  })['activate-home'],
  'pending'
);
assert.equal(
  observe(inspected, {
    action: 'install',
    state: 'complete',
    stage: 'complete',
    activation: { state: 'active', completed: true }
  })['activate-home'],
  'pass'
);
assert.equal(
  observe(inspected, {
    action: 'remove',
    state: 'recovery_required',
    stage: 'root-remove-submitting'
  })['install-root'],
  'pending'
);
console.log(
  'PASS Homebrew check projections preserve unknown, failed and untouched stages'
);
