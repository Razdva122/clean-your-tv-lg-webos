const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const policyPath = path.join(__dirname, '../screensaver/policy.js');
assert.ok(fs.existsSync(policyPath), 'shared screensaver policy must exist');
const { createInitialState, transition } = require(policyPath);
const context = {
  ownerGeneration: 7,
  popupSupported: true,
  ownerHealthy: true,
  previewEligible: true,
  inAppEligible: true,
  idleTimeoutMs: 1000,
  launchTimeoutMs: 100,
  heartbeatTimeoutMs: 50,
  closeTimeoutMs: 20
};
let checks = 0;
function test(name, fn) {
  fn();
  checks += 1;
  console.log('PASS ' + name);
}
function step(state, type, at, fields = {}, overrides = {}) {
  return transition(
    state,
    Object.assign({ type }, fields),
    Object.assign({}, context, overrides),
    at
  );
}
function enabled() {
  return step(createInitialState(7), 'ENABLE', 0).state;
}
function starting(id = 'opaque-session-a') {
  return step(enabled(), 'PREVIEW', 1, { sessionId: id, generation: 7 }).state;
}
function envelope(state, extra = {}) {
  return Object.assign(
    {
      schema: 1,
      sessionId: state.sessionId,
      generation: state.generation,
      visible: true,
      focused: true,
      mediaState: 'ready'
    },
    extra
  );
}
function visible() {
  const s = starting();
  return step(s, 'READY', 2, envelope(s)).state;
}

test('stale readiness cannot claim a newer surface', () => {
  const s = starting();
  const result = step(s, 'READY', 2, envelope(s, { generation: 6 }));
  assert.equal(result.state.phase, 'starting');
  assert.deepEqual(result.effects, []);
});
test('feature remains disabled until enabled', () => {
  const result = step(createInitialState(7), 'PREVIEW', 0, {
    sessionId: 'a',
    generation: 7
  });
  assert.equal(result.state.phase, 'disabled');
  assert.deepEqual(result.effects, []);
});
test('preview launches only the supplied session once', () => {
  const result = step(enabled(), 'PREVIEW', 1, {
    sessionId: 'opaque-session-a',
    generation: 7
  });
  assert.equal(result.state.phase, 'starting');
  assert.deepEqual(result.effects, [
    { type: 'LAUNCH', sessionId: 'opaque-session-a', generation: 7 }
  ]);
  assert.deepEqual(
    step(result.state, 'PREVIEW', 2, { sessionId: 'b', generation: 7 }).effects,
    []
  );
});
test('missing preview eligibility or owner health prevents launch', () => {
  for (const overrides of [
    { previewEligible: false },
    { popupSupported: false },
    { ownerHealthy: false },
    { ownerHealthy: undefined }
  ]) {
    assert.deepEqual(
      step(
        enabled(),
        'PREVIEW',
        1,
        { sessionId: 'a', generation: 7 },
        overrides
      ).effects,
      []
    );
  }
});
test('missing or foreign activation identity never launches', () => {
  for (const fields of [
    {},
    { sessionId: '', generation: 7 },
    { sessionId: 'a', generation: 8 }
  ]) {
    assert.deepEqual(step(enabled(), 'PREVIEW', 1, fields).effects, []);
  }
});
test('in-app launch requires fresh activity and a complete idle period', () => {
  let s = enabled();
  const fields = { sessionId: 'a', generation: 7 };
  assert.deepEqual(step(s, 'ELIGIBLE', 2000, fields).effects, []);
  s = step(s, 'ACTIVITY', 2001).state;
  assert.deepEqual(step(s, 'ELIGIBLE', 3000, fields).effects, []);
  assert.equal(step(s, 'ELIGIBLE', 3001, fields).effects[0].type, 'LAUNCH');
});
test('unverified global start never launches even with apparent idle flags', () => {
  const s = step(enabled(), 'ACTIVITY', 0).state;
  assert.deepEqual(
    step(
      s,
      'ELIGIBLE',
      2000,
      { sessionId: 'a', generation: 7 },
      { inAppEligible: false, globalEligible: true, lgTriggerVerified: true }
    ).effects,
    []
  );
});
test('LG request never starts a popup and preserves opaque request values', () => {
  const request = { timestamp: '00012345678901234567890', clientName: 'cytv' };
  const result = step(enabled(), 'LG_REQUEST', 1, { request });
  assert.deepEqual(result.effects, [
    { type: 'RESPOND_LG', request, allow: true }
  ]);
  assert.equal(result.state.phase, 'armed');
});
test('starting surface cannot veto LG', () => {
  assert.equal(
    step(starting(), 'LG_REQUEST', 2, { request: {} }).effects[0].allow,
    true
  );
});
test('fresh healthy visible focused surface may veto LG', () => {
  const result = step(visible(), 'LG_REQUEST', 51, {
    request: { timestamp: 'x' }
  });
  assert.equal(result.effects[0].allow, false);
});
test('heartbeat expiry closes custom surface and allows LG at the exact deadline', () => {
  const result = step(visible(), 'LG_REQUEST', 52, { request: {} });
  assert.equal(result.state.phase, 'closing');
  assert.equal(result.effects.find((e) => e.type === 'RESPOND_LG').allow, true);
  assert.equal(
    result.effects.find((e) => e.type === 'CLOSE').reason,
    'heartbeat-timeout'
  );
});
test('matching heartbeat renews ownership while stale heartbeat cannot', () => {
  let s = visible();
  s = step(s, 'HEARTBEAT', 40, envelope(s)).state;
  assert.equal(
    step(s, 'LG_REQUEST', 80, { request: {} }).effects[0].allow,
    false
  );
  s = step(s, 'HEARTBEAT', 85, envelope(s, { sessionId: 'old' })).state;
  assert.equal(
    step(s, 'LG_REQUEST', 90, { request: {} }).effects.find(
      (e) => e.type === 'RESPOND_LG'
    ).allow,
    true
  );
});
test('heartbeat before readiness cannot skip startup', () => {
  const s = starting();
  assert.equal(step(s, 'HEARTBEAT', 2, envelope(s)).state.phase, 'starting');
});
test('invalid renderer schemas cannot establish readiness', () => {
  for (const schema of [undefined, 0, 2]) {
    const s = starting();
    assert.equal(
      step(s, 'READY', 2, envelope(s, { schema })).state.phase,
      'starting'
    );
  }
});
test('late readiness cannot defeat startup deadline', () => {
  const s = starting();
  const result = step(s, 'READY', 101, envelope(s));
  assert.equal(result.state.phase, 'closing');
  assert.equal(result.effects[0].reason, 'launch-timeout');
});
test('loss of visibility focus or usable media closes only owned surface', () => {
  for (const fields of [
    { focused: false },
    { visible: false },
    { mediaState: 'error' },
    { mediaState: 'loading' },
    { mediaState: 'closed' }
  ]) {
    const s = visible();
    const result = step(s, 'HEARTBEAT', 3, envelope(s, fields));
    assert.equal(result.state.phase, 'closing');
    assert.equal(result.effects[0].type, 'CLOSE');
    assert.equal(result.effects[0].sessionId, 'opaque-session-a');
  }
});
test('activity during startup cancels without waiting for readiness', () => {
  const result = step(starting(), 'ACTIVITY', 2);
  assert.equal(result.state.phase, 'closing');
  assert.equal(result.effects[0].type, 'CLOSE');
});
test('old-session activity cannot dismiss a new activation', () => {
  const result = step(visible(), 'ACTIVITY', 3, {
    sessionId: 'old',
    generation: 7
  });
  assert.equal(result.state.phase, 'visible');
  assert.deepEqual(result.effects, []);
});
test('close is idempotent and stale close acknowledgement cannot release owner', () => {
  const s = visible();
  const closing = step(s, 'CLOSE', 3, envelope(s)).state;
  assert.deepEqual(step(closing, 'CLOSE', 4, envelope(closing)).effects, []);
  assert.equal(
    step(closing, 'CLOSED', 4, envelope(closing, { generation: 6 })).state
      .phase,
    'closing'
  );
  const result = step(closing, 'CLOSED', 4, envelope(closing));
  assert.equal(result.effects[0].type, 'RELEASE');
  assert.equal(result.state.phase, 'armed');
});
test('dismissed idle session cannot relaunch from its old deadline', () => {
  let s = visible();
  s = step(s, 'ACTIVITY', 3).state;
  s = step(s, 'CLOSED', 4, envelope(s)).state;
  assert.deepEqual(
    step(s, 'ELIGIBLE', 2000, { sessionId: 'b', generation: 7 }).effects,
    []
  );
  s = step(s, 'ACTIVITY', 2001).state;
  assert.equal(
    step(s, 'ELIGIBLE', 3001, { sessionId: 'b', generation: 7 }).state.phase,
    'starting'
  );
});
test('close timeout releases session if renderer never acknowledges', () => {
  const s = step(visible(), 'CLOSE', 3, envelope(visible())).state;
  const result = step(s, 'DEADLINE', 23, envelope(s));
  assert.equal(result.state.phase, 'armed');
  assert.equal(result.effects[0].type, 'RELEASE');
});
test('disable never rearms after close', () => {
  let s = step(visible(), 'DISABLE', 3).state;
  const result = step(s, 'CLOSED', 4, envelope(s));
  assert.equal(result.state.phase, 'disabled');
});
test('owner stop releases immediately and does not auto-enable', () => {
  const result = step(visible(), 'OWNER_STOP', 3);
  assert.equal(result.state.phase, 'disabled');
  assert.deepEqual(
    result.effects.map((e) => e.type),
    ['CLOSE', 'RELEASE']
  );
});
test('owner generation change releases old session and disables new owner', () => {
  const result = step(visible(), 'DEADLINE', 3, {}, { ownerGeneration: 8 });
  assert.equal(result.state.generation, 8);
  assert.equal(result.state.phase, 'disabled');
  assert.ok(result.effects.every((e) => e.generation === 7));
});
test('standby and unhealthy owner stop vetoing LG', () => {
  const result = step(visible(), 'POWER_INACTIVE', 3);
  assert.equal(result.state.phase, 'closing');
  assert.equal(
    step(result.state, 'LG_REQUEST', 4, { request: {} }).effects[0].allow,
    true
  );
  const unhealthy = step(
    visible(),
    'LG_REQUEST',
    3,
    { request: {} },
    { ownerHealthy: false }
  );
  assert.equal(
    unhealthy.effects.find((e) => e.type === 'RESPOND_LG').allow,
    true
  );
});
test('backward monotonic time ends ownership safely', () => {
  const result = step(visible(), 'LG_REQUEST', 1, { request: {} });
  assert.equal(result.state.phase, 'closing');
  assert.equal(result.effects.find((e) => e.type === 'RESPOND_LG').allow, true);
});
test('transitions never mutate caller state event or context', () => {
  const state = Object.freeze(visible());
  const event = Object.freeze(
    Object.assign({ type: 'HEARTBEAT' }, envelope(state))
  );
  const frozenContext = Object.freeze(Object.assign({}, context));
  const result = transition(state, event, frozenContext, 3);
  assert.equal(state.heartbeatAtMs, 2);
  assert.equal(result.state.heartbeatAtMs, 3);
});
console.log('screensaver policy: ' + checks + ' checks passed');
