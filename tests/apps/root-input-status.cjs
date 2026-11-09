'use strict';
const assert = require('node:assert/strict'),
  fs = require('node:fs'),
  vm = require('node:vm');
const inventory = require('../../root-edition/service/app-inventory');
(async () => {
  assert.equal(
    typeof inventory.inputs,
    'function',
    'Root input status must use the existing packaged inventory module'
  );
  assert.equal(
    typeof inventory.inputHandler,
    'function',
    'Inputs must share the already granted listApps endpoint'
  );
  let calls = [];
  const raw = {
    returnValue: true,
    devices: [
      {
        appId: 'com.webos.app.hdmi3',
        id: 'HDMI_3',
        label: 'HDMI 3',
        deviceName: 'Console',
        spdProductDescription: 'Product',
        connected: true,
        cecDeviceInfo: { private: 'UNNEEDED' }
      },
      { appId: 'com.webos.app.hdmi1', connected: false },
      { appId: 'other', label: 'x'.repeat(300), connected: 'yes' }
    ],
    private: 'UNNEEDED'
  };
  const exec = (file, args, options, callback) => {
    calls.push({ file, args, options });
    callback(null, JSON.stringify(raw));
  };
  const result = await inventory.inputs(exec, () => 0);
  assert.deepEqual(result, {
    returnValue: true,
    devices: [
      {
        appId: 'com.webos.app.hdmi3',
        id: 'HDMI_3',
        label: 'HDMI 3',
        deviceName: 'Console',
        spdProductDescription: 'Product',
        connected: true
      },
      { appId: 'com.webos.app.hdmi1', connected: false },
      { appId: 'other', label: 'x'.repeat(256), connected: null }
    ]
  });
  assert.deepEqual(calls, [
    {
      file: '/usr/bin/luna-send',
      args: ['-n', '1', 'luna://com.webos.service.eim/getAllInputStatus', '{}'],
      options: { timeout: 8000, maxBuffer: 256 * 1024 }
    }
  ]);
  await assert.rejects(
    inventory.inputs(
      () => assert.fail('non-root must not query EIM'),
      () => 1000
    )
  );
  for (const reply of [
    'not json',
    null,
    [],
    { returnValue: false, errorText: 'PRIVATE' },
    { returnValue: true },
    { returnValue: true, devices: {} },
    { returnValue: true, devices: [null] },
    { returnValue: true, devices: [[]] }
  ]) {
    await assert.rejects(
      inventory.inputs(
        (f, a, o, cb) =>
          cb(null, typeof reply === 'string' ? reply : JSON.stringify(reply)),
        () => 0
      )
    );
  }
  const limited = await inventory.inputs(
    (f, a, o, cb) =>
      cb(
        null,
        JSON.stringify({
          returnValue: true,
          devices: Array.from({ length: 101 }, () => ({
            id: 'HDMI_1',
            appId: 'a'.repeat(300),
            label: 'b'.repeat(300),
            deviceName: 42,
            spdProductDescription: 'c'.repeat(300)
          }))
        })
      ),
    () => 0
  );
  assert.equal(limited.devices.length, 100);
  assert.equal(limited.devices[0].appId.length, 256);
  assert.equal(limited.devices[0].label.length, 256);
  assert.equal(limited.devices[0].spdProductDescription.length, 256);
  assert(!('deviceName' in limited.devices[0]));
  assert.equal(limited.devices[0].connected, null);
  let pending = [],
    executions = 0,
    uid = 0;
  const handler = inventory.inputHandler(
    (f, a, o, callback) => {
      executions++;
      pending.push(callback);
    },
    () => uid
  );
  function request(
    payload = { inputs: true },
    caller = 'com.cleanyourtv.root.preview 123',
    ls2 = true
  ) {
    let responses = [];
    handler({
      payload,
      ls2Message: ls2
        ? {
            applicationID() {
              if (caller instanceof Error) throw caller;
              return caller;
            }
          }
        : undefined,
      respond(value) {
        responses.push(value);
      }
    });
    return responses;
  }
  for (const caller of [
    'com.other',
    'com.cleanyourtv.root.preview.evil',
    'com.cleanyourtv.root.preview.service',
    'com.webos.lunasend-1',
    '',
    null,
    Error('PRIVATE')
  ])
    assert.equal(request({}, caller)[0].returnValue, false);
  assert.equal(request({}, '', false)[0].returnValue, false);
  for (const payload of [
    null,
    undefined,
    [],
    {},
    { inputs: false },
    { inputs: 1 },
    { inputs: true, subscribe: true },
    { inputs: true, uri: 'PRIVATE' },
    { inputs: true, command: 'PRIVATE' }
  ]) {
    let responses = [];
    handler({
      payload,
      ls2Message: { applicationID: () => 'com.cleanyourtv.root.preview' },
      respond: (value) => responses.push(value)
    });
    assert.equal(responses[0].returnValue, false);
  }
  assert.equal(
    executions,
    0,
    'invalid callers/payloads cannot start or join a privileged read'
  );
  const first = request(),
    second = request({ inputs: true }, 'com.cleanyourtv.root.preview');
  assert.equal(executions, 1, 'concurrent authorized reads coalesce');
  assert.deepEqual(first, []);
  assert.deepEqual(second, []);
  assert.equal(
    request({ inputs: true }, 'com.other')[0].returnValue,
    false,
    'unauthorized caller cannot join an active read'
  );
  uid = 1000;
  assert.equal(
    request()[0].returnValue,
    false,
    'non-root cannot join an active read'
  );
  uid = 0;
  assert.equal(executions, 1);
  pending.shift()(null, JSON.stringify(raw));
  await new Promise((resolve) => setImmediate(resolve));
  assert.deepEqual(first, [result]);
  assert.deepEqual(second, [result]);
  const failed = request();
  assert.equal(executions, 2, 'completed reads are not cached');
  pending.shift()(Error('PRIVATE STDERR'), '', 'PRIVATE STDERR');
  await new Promise((resolve) => setImmediate(resolve));
  assert.deepEqual(failed, [
    { returnValue: false, errorText: 'Input status unavailable' }
  ]);
  assert(!JSON.stringify(failed).includes('PRIVATE'));
  uid = 1000;
  const nonRoot = request();
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(executions, 2);
  assert.deepEqual(nonRoot, [
    { returnValue: false, errorText: 'Input status unavailable' }
  ]);
  uid = 0;
  const recovered = request();
  assert.equal(
    executions,
    3,
    'failure releases the read slot without retrying'
  );
  pending.shift()(null, JSON.stringify({ returnValue: true, devices: [] }));
  await new Promise((resolve) => setImmediate(resolve));
  assert.deepEqual(recovered, [{ returnValue: true, devices: [] }]);
  // Load actual service.js without Python, the HTTP receiver or the independent
  // C1 lease broker (covered by root-edition/service/test-c1-lease.cjs).
  const methods = {},
    registered = [],
    legacyApps = [{ id: 'legacy', title: 'Unchanged app response' }];
  const serviceInventory = Object.assign(() => Promise.resolve(legacyApps), {
    inputHandler: () => inventory.inputHandler(exec, () => 0)
  });
  vm.runInNewContext(
    fs.readFileSync(
      require.resolve('../../root-edition/service/service.js'),
      'utf8'
    ),
    {
      __dirname: __dirname,
      process: { getuid: () => 0 },
      Promise,
      require(name) {
        if (name === 'webos-service')
          return class {
            register(name, callback) {
              assert.equal(arguments.length, 2);
              registered.push(name);
              methods[name] = callback;
            }
          };
        if (name === 'child_process') return { execFile: exec };
        if (name === './handlers')
          return require('../../root-edition/service/handlers');
        if (name === './app-inventory') return serviceInventory;
        if (name === './weather')
          return require('../../renewal-service/weather');
        if (name === './theme-receiver')
          return require('../../theme-receiver/register');
        if (name === './c1-lease') return () => {};
        if (name === './presentation-context')
          return require('../../root-edition/service/presentation-context');
        throw Error('Unexpected import ' + name);
      }
    }
  );
  assert.equal(registered.filter((name) => name === 'listApps').length, 1);
  assert(!registered.includes('listInputs'), 'no new method or ACL migration');
  const broker = [],
    legacy = [];
  methods.listApps({
    payload: { inputs: true },
    ls2Message: { applicationID: () => 'com.cleanyourtv.root.preview 123' },
    respond: (value) => broker.push(value)
  });
  methods.listApps({ payload: {}, respond: (value) => legacy.push(value) });
  await new Promise((resolve) => setImmediate(resolve));
  assert.deepEqual(broker, [result]);
  assert.deepEqual(JSON.parse(JSON.stringify(legacy)), [
    { returnValue: true, apps: legacyApps }
  ]);
  const malformed = [];
  const before = calls.length;
  methods.listApps({
    payload: { inputs: false },
    ls2Message: { applicationID: () => 'com.cleanyourtv.root.preview' },
    respond: (value) => malformed.push(value)
  });
  assert.deepEqual(malformed, [
    { returnValue: false, errorText: 'Input status unavailable' }
  ]);
  assert.equal(
    calls.length,
    before,
    'own invalid selector cannot fall through to app inventory'
  );
  const contextReply = [];
  const contextBefore = calls.length;
  methods.status({
    payload: { presentation: 'context' },
    respond: (value) => contextReply.push(value)
  });
  await new Promise((resolve) => setImmediate(resolve));
  assert.deepEqual(JSON.parse(JSON.stringify(contextReply)), [
    { returnValue: true, result: { content: null }, root: true }
  ]);
  assert.equal(calls.length, contextBefore + 1);
  assert.deepEqual(
    calls[calls.length - 1].args,
    ['-n', '1', 'luna://com.webos.surfacemanager/getForegroundAppInfo', '{}'],
    'presentation uses its own fixed query alongside EIM'
  );
  console.log(
    'PASS Root input status: fixed root query, caller/payload guards, sanitized bounds, coalescing, failure isolation and legacy endpoint routing'
  );
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
