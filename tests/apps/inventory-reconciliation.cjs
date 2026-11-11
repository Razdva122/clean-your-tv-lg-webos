const { test } = require('node:test');
const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');
const { create } = require('../../launcher/app-library');
const query = require('../../native/service/app-inventory');
function model(fail = false) {
  const values = new Map();
  const storage = {
    getItem: (k) => values.get(k) || null,
    setItem(k, v) {
      if (fail) throw Error('quota');
      values.set(k, v);
    }
  };
  return {
    storage,
    library: create(
      storage,
      [
        { id: 'gone', title: 'Gone' },
        { id: 'hidden', title: 'Hidden' },
        { id: 'kept', title: 'Kept', icon: 'data:image/png;base64,b2xk' }
      ],
      { dockApps: ['gone', 'kept'], hiddenApps: ['hidden'] }
    )
  };
}
test('confirmed installed IDs prune removed apps and persist without adding discoveries', () => {
  const { library, storage } = model();
  library.refresh([{ id: 'new', title: 'New' }], ['kept', 'hidden', 'new']);
  assert.deepEqual(
    library.visible().map((a) => a.id),
    ['kept']
  );
  assert.deepEqual(
    library.available().map((a) => a.id),
    ['hidden', 'new']
  );
  assert.deepEqual(library.hidden(), ['hidden']);
  const restarted = create(
    storage,
    [{ id: 'gone', title: 'Packaged stale' }],
    {}
  );

  assert.deepEqual(
    restarted.visible().map((a) => a.id),
    ['kept']
  );
  assert(!restarted.available().some((a) => a.id === 'gone'));
});
test('legacy, partial, malformed and contradictory authority never erase saved apps', () => {
  for (const ids of [
    undefined,
    null,
    ['kept', 'kept'],
    [null],
    Array(301).fill('kept'),
    []
  ]) {
    const { library } = model();
    library.refresh([{ id: 'kept', title: 'Kept' }], ids);
    assert(library.visible().some((a) => a.id === 'gone'));
  }
  const { library } = model();
  library.refresh([], []);
  assert.deepEqual(library.visible(), []);
  assert.deepEqual(library.available(), []);
  assert.deepEqual(library.hidden(), []);
});
test('failed reconciliation storage commit preserves the complete previous model', () => {
  const { library } = model(true);
  assert.throws(
    () => library.refresh([{ id: 'kept', title: 'Changed' }], ['kept']),
    /quota/
  );
  assert(library.visible().some((a) => a.id === 'gone'));
  assert.equal(library.visible().find((a) => a.id === 'kept').title, 'Kept');
});
function read(installed, extra = {}) {
  class WS extends EventEmitter {
    constructor() {
      super();
      queueMicrotask(() => this.emit('open'));
    }
    terminate() {}
    send(raw) {
      const m = JSON.parse(raw);
      if (m.id === 'tuner' && installed === 'silent') return;
      queueMicrotask(() =>
        this.emit(
          'message',
          JSON.stringify(
            m.type === 'register'
              ? { type: 'registered' }
              : {
                  id: m.id,
                  payload:
                    m.id === 'apps'
                      ? {
                          returnValue: true,
                          launchPoints: [
                            { id: 'kept', title: 'Kept', ...extra.app },
                            { id: 'com.webos.app.livetv', title: 'TV' }
                          ]
                        }
                      : installed
                }
          )
        )
      );
    }
  }
  return query({
    details: true,
    WebSocket: WS,
    readKey: () => ({ key: 'fixture' }),
    interfaces: () => ({
      eth: [{ internal: false, family: 'IPv4', address: '192.0.2.1' }]
    }),
    timeout: 100,
    ...extra
  });
}
test('No-root confirms installed IDs even when launch points already contain tuner', async () => {
  const result = await read({
    returnValue: true,
    apps: [
      { id: 'kept', title: 'Kept' },
      { id: 'com.webos.app.livetv', title: 'TV' },
      { id: 'hidden', title: 'Hidden', visible: false }
    ]
  });
  assert.deepEqual(result.installedIds, [
    'kept',
    'com.webos.app.livetv',
    'hidden'
  ]);
  assert.deepEqual(
    result.apps.map((a) => a.id),
    ['com.webos.app.livetv', 'kept']
  );
});
test('denied, truncated, malformed or contradictory confirmation remains non-destructive', async () => {
  for (const reply of [
    { returnValue: false },
    { returnValue: true, apps: [] },
    { returnValue: true, apps: [null] },
    { returnValue: true, apps: Array(301).fill({ id: 'x', title: 'X' }) }
  ]) {
    const result = await read(reply);
    assert.equal(result.installedIds, undefined);
    assert(result.apps.some((a) => a.id === 'kept'));
  }
});
function get(responses, calls) {
  return (options, callback) => {
    const req = new EventEmitter();
    req.abort = () => {
      req.aborted = true;
    };
    calls.push(options);
    queueMicrotask(() => {
      const r = new EventEmitter();
      r.statusCode = responses[options.path]?.status || 200;
      r.resume = () => {};
      r.destroy = () => {};
      callback(r);
      for (const chunk of responses[options.path]?.chunks || [
        Buffer.from('bad')
      ])
        r.emit('data', chunk);
      r.emit('end');
    });
    return req;
  };
}
const png = Buffer.from('\x89PNG\r\n\x1a\nfixture', 'binary');
test('No-root embeds largeIcon and falls back from invalid images without remote URLs', async () => {
  const calls = [];
  const apps = await query.icons(
    [
      {
        id: 'new',
        title: 'New',
        extraLargeIcon: 'https://192.0.2.1:3001/bad',
        largeIcon: 'https://192.0.2.1:3001/good'
      }
    ],
    '192.0.2.1',
    { get: get({ '/good': { chunks: [png] } }, calls) },
    Date.now() + 500
  );
  assert.equal(apps[0].icon, 'data:image/png;base64,' + png.toString('base64'));
  assert.equal(calls.length, 2);
  assert.equal(calls[0].rejectUnauthorized, false);
});
test('icon fetching rejects foreign hosts, credentials, ports, redirects and oversized content', async () => {
  const calls = [];
  const apps = await query.icons(
    [
      { id: 'foreign', title: 'Foreign', icon: 'https://example.com/x' },
      { id: 'auth', title: 'Auth', icon: 'https://user@192.0.2.1/x' },
      { id: 'port', title: 'Port', icon: 'https://192.0.2.1:9000/x' },
      { id: 'local', title: 'Local', icon: 'file:///etc/passwd' },
      { id: 'redirect', title: 'Redirect', icon: 'https://192.0.2.1/redirect' },
      { id: 'large', title: 'Large', icon: 'https://192.0.2.1/large' }
    ],
    '192.0.2.1',
    {
      get: get(
        {
          '/redirect': { status: 302 },
          '/large': { chunks: [Buffer.alloc(256 * 1024 + 1)] }
        },
        calls
      )
    },
    Date.now() + 500
  );
  assert.equal(calls.length, 2);
  assert(apps.every((a) => a.icon === ''));
});

test('Root confirmation includes installed apps beyond the visible 200 entry limit', async () => {
  const root = require('../../root-edition/service/app-inventory');
  const result = await root(
    (file, args, options, cb) =>
      cb(
        null,
        JSON.stringify({
          returnValue: true,
          apps: Array.from({ length: 201 }, (_, i) => ({
            id: 'app' + i,
            title: 'App',
            visible: false
          }))
        })
      ),
    () => 0,
    [],
    true
  );
  assert.equal(result.apps.length, 200);
  assert.equal(result.installedIds.length, 201);
  assert(result.installedIds.includes('app200'));
});
test('icon refresh enforces a total byte budget and returns promptly on stalled requests', async () => {
  const big = Buffer.alloc(120 * 1024);
  png.copy(big);
  const calls = [];
  const apps = Array.from({ length: 12 }, (_, i) => ({
    id: 'app' + i,
    title: 'App',
    icon: 'https://192.0.2.1/big'
  }));
  const result = await query.icons(
    apps,
    '192.0.2.1',
    { get: get({ '/big': { chunks: [big] } }, calls) },
    Date.now() + 500
  );
  const embedded = result.filter((a) => a.icon);
  assert.equal(embedded.length, 4);
  assert(
    embedded.reduce(
      (n, a) => n + Buffer.from(a.icon.split(',')[1], 'base64').length,
      0
    ) <=
      512 * 1024
  );
  const stalled = [];
  const start = Date.now();
  const timed = await query.icons(
    apps,
    '192.0.2.1',
    {
      get() {
        const r = new EventEmitter();
        r.abort = () => {
          r.aborted = true;
        };
        stalled.push(r);
        return r;
      }
    },
    start + 30
  );
  assert(stalled.length <= 4);
  assert(stalled.every((r) => r.aborted));
  assert(timed.every((a) => a.icon === ''));
  assert(Date.now() - start < 500);
});

test('a silent optional confirmation leaves time to fetch a new icon', async () => {
  const calls = [];
  const result = await read('silent', {
    app: { largeIcon: 'https://192.0.2.1/good' },
    get: get({ '/good': { chunks: [png] } }, calls)
  });
  assert.equal(result.installedIds, undefined);
  assert.equal(calls.length, 1);
  assert.equal(
    result.apps.find((a) => a.id === 'kept').icon,
    'data:image/png;base64,' + png.toString('base64')
  );
});
