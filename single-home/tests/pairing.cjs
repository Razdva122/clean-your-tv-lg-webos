const test = require('node:test'),
  assert = require('node:assert/strict'),
  E = require('node:events');
const inventory = require('../service/pairing');
const readIcons = require('../../native/service/app-inventory').icons;
const prompt = {
  id: 'register',
  type: 'response',
  payload: { returnValue: true, pairingType: 'PROMPT' }
};
const granted = {
  id: 'register',
  type: 'registered',
  payload: { 'client-key': 'fixture-key' }
};
const apps = {
  id: 'apps',
  type: 'response',
  payload: {
    returnValue: true,
    launchPoints: [
      { id: 'tv.app', title: 'TV' },
      { id: 'tv.hidden', title: 'Hidden', hidden: true }
    ]
  }
};
function run(key, replies, current = () => true, fixture = {}) {
  let sent = [];
  class Socket extends E {
    constructor(address, options) {
      super();
      assert.equal(address, 'wss://192.0.2.8:3001');
      assert.equal(options.localAddress, '192.0.2.8');
      setImmediate(() => this.emit('open'));
    }
    send(raw) {
      const q = JSON.parse(raw);
      sent.push(q);
      const messages =
        q.id === 'register'
          ? replies
          : q.id === 'apps'
            ? [fixture.apps || apps]
            : [
                {
                  id: 'tuner',
                  type: 'response',
                  payload: { returnValue: true, apps: fixture.installed || [] }
                }
              ];
      setImmediate(() =>
        messages.forEach((m) => this.emit('message', JSON.stringify(m)))
      );
    }
    terminate() {}
  }
  return {
    result: inventory(key, current, {
      WebSocket: Socket,
      readIcons,
      get: fixture.get,
      interfaces: () => ({
        eth: [{ family: 'IPv4', address: '192.0.2.8', internal: false }]
      })
    }),
    sent
  };
}
test('saved pairing returns raster icon data from the TV for visible apps and its installed tuner', async () => {
  const path = '/resources/0123456789abcdef/icon.png';
  const png =
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+ncV0AAAAASUVORK5CYII=';
  const calls = [];
  const result = await run('fixture-key', [granted], () => true, {
    apps: {
      ...apps,
      payload: {
        returnValue: true,
        launchPoints: [
          {
            id: 'tv.app',
            title: 'TV',
            icon: 'https://example.org/ad.png',
            bgColor: '#ABCDEF'
          },
          {
            id: 'tv.noicon',
            title: 'Other',
            icon: 'file:///tmp/private',
            iconColor: { invalid: true }
          },
          {
            id: 'tv.hidden',
            title: 'Hidden',
            hidden: true,
            icon: 'http://192.0.2.8:3000/hidden'
          }
        ]
      }
    },
    installed: [
      { id: 'tv.app', largeIcon: path },
      {
        id: 'com.webos.app.livetv',
        title: 'Live TV',
        hidden: true,
        icon: 'http://192.0.2.8:3000/tuner.png'
      }
    ],
    get(options, callback) {
      calls.push([options.hostname, options.path]);
      const request = new E();
      request.abort = () => {};
      setImmediate(() => {
        const response = new E();
        response.statusCode = 200;
        response.destroy = () => {};
        callback(response);
        response.emit('data', Buffer.from(png, 'base64'));
        response.emit('end');
      });
      return request;
    }
  }).result;
  const icon = 'data:image/png;base64,' + png;
  assert.deepEqual(result.apps, [
    { id: 'com.webos.app.livetv', title: 'Live TV', icon, iconColor: '' },
    { id: 'tv.app', title: 'TV', icon, iconColor: '#ABCDEF' },
    { id: 'tv.noicon', title: 'Other', icon: '', iconColor: '' }
  ]);
  assert.deepEqual(calls.sort(), [
    ['192.0.2.8', path],
    ['192.0.2.8', '/tuner.png']
  ]);
});
test('explicit first pairing requires a native prompt before registration; returns only launchable visible catalog', async () => {
  const op = run(null, [prompt, granted]);
  const r = await op.result;
  assert.equal(r.key, 'fixture-key');
  assert.deepEqual(
    r.apps.map((a) => a.id),
    ['tv.app']
  );
  assert.equal('client-key' in op.sent[0].payload, false);
  assert.deepEqual(op.sent[0].payload.manifest.permissions, [
    'READ_INSTALLED_APPS'
  ]);
  await assert.rejects(run(null, [granted]).result, /pairing-declined/);
  await assert.rejects(
    run(null, [{ id: 'register', type: 'error' }]).result,
    /pairing-declined/
  );
});
test('saved credential verification never accepts a replacement or a fresh prompt', async () => {
  for (const reply of [
    prompt,
    { ...granted, payload: { 'client-key': 'replacement' } },
    { id: 'register', type: 'error' }
  ])
    await assert.rejects(
      run('fixture-key', [reply]).result,
      /saved-pairing-rejected/
    );
  assert.equal(
    (await run('fixture-key', [granted]).result).apps[0].title,
    'TV'
  );
  await assert.rejects(
    run(null, [prompt, granted], () => false).result,
    /cancelled/
  );
});
