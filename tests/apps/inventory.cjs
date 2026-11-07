const assert = require('node:assert/strict'),
  fs = require('fs'),
  { EventEmitter } = require('events');
assert.ok(
  fs.existsSync(__dirname + '/../../native/service/app-inventory.js'),
  'TV inventory transport must exist'
);
const query = require('../../native/service/app-inventory');
(async () => {
  let socket,
    sent = [];
  class WS extends EventEmitter {
    constructor(url) {
      super();
      this.url = url;
      socket = this;
      queueMicrotask(() => this.emit('open'));
    }
    send(raw) {
      const msg = JSON.parse(raw);
      sent.push(msg);
      queueMicrotask(() =>
        this.emit(
          'message',
          JSON.stringify(
            msg.type === 'register'
              ? { type: 'registered' }
              : {
                  id: 'apps',
                  type: 'response',
                  payload: {
                    returnValue: true,
                    launchPoints: [{ id: 'a', title: 'Alpha' }]
                  }
                }
          )
        )
      );
    }
    terminate() {
      this.closed = true;
    }
  }
  const options = {
    WebSocket: WS,
    readKey: () => ({ key: 'paired' }),
    interfaces: () => ({
      eth0: [{ internal: false, family: 'IPv4', address: '192.168.1.5' }]
    }),
    timeout: 100
  };
  assert.deepEqual(await query(options), [{ id: 'a', title: 'Alpha' }]);
  assert(socket.closed);
  assert.equal(socket.url, 'wss://192.168.1.5:3001');
  assert.equal(
    sent[1].uri,
    'ssap://com.webos.applicationManager/listLaunchPoints'
  );
  await assert.rejects(query({ ...options, readKey: () => ({}) }), /pairing/);
  await assert.rejects(
    query({ ...options, interfaces: () => ({}) }),
    /network/
  );
  class Multi extends WS {
    send(raw) {
      if (this.url.includes('192.168.1.6')) super.send(raw);
      else queueMicrotask(() => this.emit('error', Error('offline')));
    }
  }
  assert.deepEqual(
    await query({
      ...options,
      WebSocket: Multi,
      interfaces: () => ({
        eth0: [
          { internal: false, family: 'IPv4', address: '192.168.1.5' },
          { internal: false, family: 'IPv4', address: '192.168.1.6' }
        ]
      })
    }),
    [{ id: 'a', title: 'Alpha' }]
  );
  class Revoked extends WS {
    send() {
      queueMicrotask(() =>
        this.emit(
          'message',
          JSON.stringify({ payload: { pairingType: 'PROMPT' } })
        )
      );
    }
  }
  await assert.rejects(query({ ...options, WebSocket: Revoked }), /pairing/);
  assert(socket.closed);
  class Silent extends WS {
    send() {}
  }
  await assert.rejects(query({ ...options, WebSocket: Silent }), /timeout/);
  assert(socket.closed);
  let inputRequest, inputRegistration, inputSocket;
  class Inputs extends WS {
    constructor(url, opts) {
      super(url);
      inputSocket = this;
      assert.equal(opts.maxPayload, 256 * 1024);
    }
    send(raw) {
      const msg = JSON.parse(raw);
      if (msg.type === 'register') inputRegistration = msg;
      else inputRequest = msg;
      queueMicrotask(() =>
        this.emit(
          'message',
          JSON.stringify(
            msg.type === 'register'
              ? { type: 'registered' }
              : {
                  id: 'inputs',
                  type: 'response',
                  payload: {
                    returnValue: true,
                    devices: [
                      {
                        appId: 'com.webos.app.hdmi3',
                        id: 'HDMI_3',
                        label: 'HDMI 3',
                        connected: true,
                        spdProductDescription: 'Console',
                        serial: 'PRIVATE'
                      },
                      { appId: 'com.webos.app.hdmi1', connected: false },
                      {
                        appId: 'unknown',
                        label: 'x'.repeat(300),
                        connected: 'yes'
                      }
                    ]
                  }
                }
          )
        )
      );
    }
  }
  const devices = await query({ ...options, inputs: true, WebSocket: Inputs });
  assert.equal(
    inputRequest.uri,
    'ssap://tv/getExternalInputList',
    'input read must use its fixed paired endpoint'
  );
  // webOS 3.x keeps only the last registered permission set per key: every Helper
  // SSAP client must request the same full manifest as screen-watch.js.
  assert.deepEqual(inputRegistration.payload.manifest.permissions, [
    'READ_APP_STATUS',
    'READ_RUNNING_APPS',
    'READ_POWER_STATE',
    'CONTROL_POWER',
    'READ_INSTALLED_APPS',
    'READ_INPUT_DEVICE_LIST'
  ]);
  assert.deepEqual(devices, [
    {
      appId: 'com.webos.app.hdmi3',
      id: 'HDMI_3',
      label: 'HDMI 3',
      spdProductDescription: 'Console',
      connected: true
    },
    { appId: 'com.webos.app.hdmi1', connected: false },
    { appId: 'unknown', label: 'x'.repeat(256), connected: null }
  ]);
  assert(inputSocket.closed);
  assert(!JSON.stringify(devices).includes('PRIVATE'));
  for (const payload of [
    { returnValue: false },
    { returnValue: true, devices: [null] },
    { returnValue: true, devices: {} },
    { returnValue: true, devices: [{ connected: true }] }
  ]) {
    class InvalidInput extends WS {
      send(raw) {
        const msg = JSON.parse(raw);
        queueMicrotask(() =>
          this.emit(
            'message',
            JSON.stringify(
              msg.type === 'register'
                ? { type: 'registered' }
                : { id: 'inputs', type: 'response', payload }
            )
          )
        );
      }
    }
    await assert.rejects(
      query({ ...options, inputs: true, WebSocket: InvalidInput })
    );
  }
  class NullReply extends WS {
    send() {
      queueMicrotask(() => this.emit('message', 'null'));
    }
  }
  await assert.rejects(
    query({ ...options, inputs: true, WebSocket: NullReply }),
    /invalid/
  );
  class SendFailure extends WS {
    send() {
      throw Error('PRIVATE transport error');
    }
  }
  await assert.rejects(
    query({ ...options, inputs: true, WebSocket: SendFailure })
  );
  const root = require('../../root-edition/service/app-inventory');
  const calls = [];
  const apps = await root(
    (file, args, opts, cb) => {
      calls.push({ file, args });
      cb(
        null,
        JSON.stringify({
          returnValue: true,
          apps: [
            {
              id: 'a',
              title: 'Alpha',
              icon: 'a.png',
              folderPath: '/tmp/untrusted'
            },
            {
              id: 'store',
              title: 'Store app',
              folderPath: '/media/cryptofs/apps/usr/palm/applications/store'
            },
            { id: 'system', title: 'Hidden system app', visible: false }
          ]
        })
      );
    },
    () => 0
  );
  assert.equal(apps[0].id, 'a');
  assert.equal(apps[0].icon, '');
  assert.equal(
    calls[0].args[2],
    'luna://com.webos.applicationManager/listApps'
  );
  const library = require('../../launcher/app-library').create(
    { getItem: () => null },
    apps,
    {}
  );
  assert.deepEqual(
    library.visible().map((a) => a.id),
    ['a', 'store'],
    'Root catalog retains sideloaded and store apps while filtering hidden system apps'
  );
  await assert.rejects(
    root(
      () => {
        throw Error('should not run');
      },
      () => 1000
    ),
    /Root/
  );
  console.log(
    'PASS TV inventory, local endpoint, missing/revoked pairing, timeout, root listing'
  );
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
