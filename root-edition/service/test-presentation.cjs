'use strict';
const assert = require('assert');
const createHandlers = require('./handlers');
(async () => {
  let finish;
  const handlers = createHandlers(
    () => new Promise((r) => (finish = r)),
    null,
    null,
    async () => ({ content: true })
  );
  const busy = handlers.restore({});
  assert.deepStrictEqual(await handlers.status({ presentation: 'context' }), {
    returnValue: true,
    result: { content: true }
  });
  for (const payload of [
    { presentation: 'context', extra: true },
    { presentation: 'other' }
  ])
    assert.strictEqual((await handlers.status(payload)).returnValue, false);
  finish({});
  await busy;
  const context = require('./presentation-context');
  const card = (appId) => ({ appId, windowType: '_WEBOS_WINDOW_TYPE_CARD' });
  const overlay = {
    appId: 'com.cleanyourtv.root.preview',
    windowType: '_WEBOS_WINDOW_TYPE_OVERLAY'
  };
  let response = {
      returnValue: true,
      foregroundAppInfo: [overlay, card('youtube.leanback.v4')]
    },
    calls = 0;
  const service = (file, args, options, callback) => {
    calls++;
    assert.strictEqual(file, '/usr/bin/luna-send');
    assert.deepStrictEqual(args, [
      '-n',
      '1',
      'luna://com.webos.surfacemanager/getForegroundAppInfo',
      '{}'
    ]);
    assert.deepStrictEqual(options, { timeout: 1500, maxBuffer: 65536 });
    callback(null, JSON.stringify(response));
  };
  const query = context(service, () => 0);
  for (const [surfaces, want] of [
    [[overlay, card('youtube.leanback.v4')], true],
    [[card('com.webos.app.hdmi1')], true],
    [[card('com.webos.app.livetv')], true],
    [[], false],
    [[overlay], false],
    [[card('com.webos.app.home')], false],
    [[card('com.gathin.tvhome')], false],
    [[card('com.webos.app.cpcover')], false],
    [[card('com.webos.app.fullhome')], false],
    [[{ appId: 'org.player', windowType: '_WEBOS_WINDOW_TYPE_OVERLAY' }], null],
    [
      [
        card('youtube.leanback.v4'),
        {
          appId: 'com.palm.app.settings',
          windowType: '_WEBOS_WINDOW_TYPE_OVERLAY'
        }
      ],
      null
    ],
    [[{ ...card('youtube.leanback.v4'), pip: true }], null],
    [[{ appId: 'org.player' }], null],
    [null, null],
    [[{ ...card('org.player'), displayId: 1 }], false]
  ]) {
    response = { returnValue: true, foregroundAppInfo: surfaces };
    assert.deepStrictEqual(await query(), { content: want });
  }
  response = { returnValue: false, errorText: 'private' };
  assert.deepStrictEqual(await query(), { content: null });
  let before = calls;
  assert.deepStrictEqual(await context(service, () => 1)(), { content: null });
  assert.strictEqual(calls, before);
  for (const run of [
    (file, args, options, cb) => cb(Error('timeout'), ''),
    (file, args, options, cb) => cb(null, 'invalid json'),
    (file, args, options, cb) => cb(null, ' '.repeat(65537)),
    () => {
      throw Error('spawn failed');
    }
  ])
    assert.deepStrictEqual(await context(run, () => 0)(), { content: null });
  console.log('presentation context tests passed');
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
