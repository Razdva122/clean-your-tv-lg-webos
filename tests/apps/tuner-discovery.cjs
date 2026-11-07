const assert = require('node:assert/strict'),
  { EventEmitter } = require('events');
const query = require('../../native/service/app-inventory'),
  root = require('../../root-edition/service/app-inventory'),
  { create } = require('../../launcher/app-library');
const tv = {
    id: 'com.webos.app.livetv',
    title: 'Телетрансляция',
    visible: false,
    hidden: true
  },
  ordinary = { id: 'video', title: 'Video' };
async function read(extra, points = [ordinary], mode = 'reply') {
  const requests = [];
  let socket;
  class WS extends EventEmitter {
    constructor() {
      super();
      socket = this;
      queueMicrotask(() => this.emit('open'));
    }
    terminate() {
      this.closed = true;
    }
    send(raw) {
      const m = JSON.parse(raw);
      requests.push(m);
      if (m.id === 'tuner' && mode === 'silent') return;
      if (m.id === 'tuner' && mode === 'close') {
        queueMicrotask(() => this.emit('close'));
        return;
      }
      queueMicrotask(() =>
        this.emit(
          'message',
          JSON.stringify(
            m.type === 'register'
              ? { type: 'registered' }
              : m.id === 'apps'
                ? {
                    id: m.id,
                    payload: { returnValue: true, launchPoints: points }
                  }
                : extra === 'denied'
                  ? { type: 'error', id: m.id }
                  : { id: m.id, payload: extra }
          )
        )
      );
    }
  }
  const apps = await query({
    WebSocket: WS,
    readKey: () => ({ key: 'fixture' }),
    interfaces: () => ({
      eth: [{ internal: false, family: 'IPv4', address: '192.0.2.1' }]
    }),
    timeout: 40
  });
  assert(socket.closed);
  assert(
    requests
      .filter((m) => m.type === 'request')
      .every((m) => /\/list(?:LaunchPoints|Apps)$/.test(m.uri)),
    'discovery must never launch or pair'
  );
  return { apps, requests };
}
(async () => {
  const { apps, requests } = await read({
    returnValue: true,
    apps: [
      { id: 'private-system', title: 'System', visible: false },
      tv,
      { id: 'com.webos.app.livetvopapp', title: 'OpApp' }
    ]
  });
  assert.equal(
    apps.find((a) => a.id === tv.id)?.hidden,
    false,
    'installed tuner must survive LG hidden/visible metadata'
  );
  assert.deepEqual(
    apps.map((a) => a.id),
    [tv.id, ordinary.id],
    'only the confirmed tuner supplements launch points'
  );
  assert.equal(requests[2].uri, 'ssap://com.webos.applicationManager/listApps');
  const library = create(
    {
      getItem: () =>
        JSON.stringify({ version: 1, ids: [], hidden: [], catalog: [] }),
      setItem: () => {}
    },
    apps,
    {}
  );
  assert.equal(library.available().find((a) => a.id === tv.id).title, tv.title);
  library.add(tv.id);
  assert.equal(library.visible()[0].id, tv.id);
  for (const extra of [
    'denied',
    null,
    { returnValue: false, apps: [tv] },
    { returnValue: true, apps: {} },
    { returnValue: true, apps: [null, {}, { ...tv, title: undefined }] }
  ])
    assert.deepEqual((await read(extra)).apps, [ordinary]);
  assert.deepEqual((await read({}, [ordinary], 'silent')).apps, [ordinary]);
  assert.deepEqual((await read({}, [ordinary], 'close')).apps, [ordinary]);
  assert.deepEqual(
    (await read({ returnValue: true, apps: [] })).apps,
    [ordinary],
    'no tuner on models without discovery evidence'
  );
  const present = await read({ returnValue: true, apps: [tv] }, [
    ordinary,
    { ...tv, hidden: false }
  ]);
  assert.equal(present.apps.filter((a) => a.id === tv.id).length, 1);
  const many = await read(
    { returnValue: true, apps: [tv] },
    Array.from({ length: 200 }, (_, i) => ({ id: 'app' + i, title: 'App' }))
  );
  assert(
    create({ getItem: () => null, setItem: () => {} }, many.apps, {})
      .visible()
      .some((a) => a.id === tv.id),
    'catalog bound must not discard confirmed tuner'
  );
  const rooted = await root(
    (file, args, opts, cb) =>
      cb(
        null,
        JSON.stringify({
          returnValue: true,
          apps: [
            ordinary,
            tv,
            { id: 'private-system', title: 'System', visible: false }
          ]
        })
      ),
    () => 0
  );
  assert.equal(
    rooted.find((a) => a.id === tv.id).hidden,
    false,
    'Root must retain the installed tuner'
  );
  assert.equal(
    rooted.find((a) => a.id === 'private-system').hidden,
    true,
    'other hidden system apps stay filtered'
  );
  const mixed = [
    ordinary,
    tv,
    { ...ordinary, title: 'Duplicate' },
    { id: 'invisible', title: 'Invisible system app', visible: false },
    { id: 'hidden', title: 'Hidden system app', hidden: true },
    { id: 'com.sdk.ares.hostedapp', title: 'Ares Hosted App' },
    { id: 'com.cleanyourtv.root.updater', title: 'Root Updater' }
  ];
  const normalized = await root(
    (file, args, opts, cb) =>
      cb(null, JSON.stringify({ returnValue: true, apps: mixed })),
    () => 0
  );
  for (const catalog of [mixed, normalized]) {
    const shared = create(
      {
        getItem: () =>
          JSON.stringify({ version: 1, ids: [], hidden: [], catalog: [] }),
        setItem() {}
      },
      catalog,
      {}
    );
    assert.deepEqual(
      shared
        .available()
        .map((a) => a.id)
        .sort(),
      [tv.id, ordinary.id].sort(),
      'raw and Root catalogs share visibility, tuner, deduplication and utility picker rules'
    );
    shared.add(tv.id);
    shared.refresh([ordinary]);
    assert.equal(
      shared.visible()[0].id,
      tv.id,
      'partial refresh preserves the discovered tuner tile'
    );
  }
  console.log(
    'PASS discovered tuner, localized title, hidden flags, optional-query failures, absent models, deduplication and Root filtering'
  );
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
