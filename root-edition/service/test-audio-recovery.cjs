const assert = require('node:assert/strict');
const create = require('./handlers').audio;
let uid = 0,
  calls = [],
  resolve;
const api = create(
  () => uid,
  async (command) => {
    calls.push(command);
    return { returnValue: true, command };
  }
);
(async () => {
  for (const [method, payload] of [
    ['audioRecoveryStatus', { extra: 1 }],
    ['setAudioRecoveryEnabled', { enabled: 'true' }],
    ['setAudioRecoveryEnabled', { enabled: true, uri: 'other' }],
    ['recoverAudio', { operation: 'shell' }],
    ['recoverAudio', null]
  ]) {
    assert.equal((await api[method](payload)).returnValue, false);
    assert.equal(calls.length, 0);
  }
  uid = 1000;
  assert.equal(
    (await api.recoverAudio({ operation: 'restart-earc' })).returnValue,
    false
  );
  assert.equal(calls.length, 0);
  uid = 0;
  assert.equal((await api.audioRecoveryStatus({})).command, 'status');
  assert.equal(
    (await api.setAudioRecoveryEnabled({ enabled: false })).command,
    'disable'
  );
  assert.equal(
    (await api.recoverAudio({ operation: 'restore-setting' })).command,
    'restore-setting'
  );
  const busy = create(
    () => 0,
    () =>
      new Promise((r) => {
        resolve = r;
      })
  );
  const first = busy.recoverAudio({ operation: 'restart-earc' });
  assert.equal(
    (await busy.recoverAudio({ operation: 'restart-earc' })).errorCode,
    'busy'
  );
  resolve({ returnValue: true });
  await first;
  const rootCalls = [];
  const handlers = require('./handlers')(async (command) => {
    rootCalls.push(command);
    return command;
  }, api);
  assert.equal((await handlers.status({ audio: 'status' })).command, 'status');
  assert.equal(
    (await handlers.enable({ audio: 'configure', enabled: false })).command,
    'disable'
  );
  assert.equal(
    (await handlers.enable({ audio: 'recover', operation: 'restore-setting' }))
      .command,
    'restore-setting'
  );
  assert.equal(rootCalls.length, 0);
  const before = calls.length;
  for (const [method, payload] of [
    ['status', { audio: 'recover', operation: 'restart-earc' }],
    ['enable', { audio: 'configure', enabled: 'true' }],
    ['enable', { audio: 'recover', operation: 'shell' }],
    ['enable', { audio: 'recover', operation: 'restart-earc', extra: 1 }]
  ])
    assert.equal((await handlers[method](payload)).returnValue, false);
  assert.equal(calls.length, before);
  assert.equal((await handlers.status({})).result, 'status');
  assert.deepEqual(rootCalls, ['status']);
  console.log(
    'PASS eARC RPC: root-only fixed operations, strict payloads and duplicate suppression'
  );
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
