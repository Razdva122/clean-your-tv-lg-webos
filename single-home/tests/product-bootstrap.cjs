'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const library = require('../../launcher/app-library.js');
const entry = path.resolve(__dirname, '../launcher/profile-bootstrap.js');
const service = 'luna://io.github.razdva122.cytvhomepilot.service/';
const apps = [
  {
    id: 'example.video',
    title: 'Video',
    icon: 'data:image/png;base64,YQ==',
    iconColor: '#aabbcc'
  },
  { id: 'example.music', title: 'Music', icon: '', iconColor: '' }
];
function storage(entries = {}) {
  return {
    getItem: (k) => (Object.hasOwn(entries, k) ? entries[k] : null),
    setItem: (k, v) => {
      entries[k] = String(v);
    },
    removeItem: (k) => {
      delete entries[k];
    }
  };
}
function start({
  saved = storage(),
  status = {},
  catalog = { apps },
  search = '',
  skip = false
} = {}) {
  const requests = [],
    scripts = [],
    routes = [];
  const env = {
    AppLibrary: { ...library },
    CONFIG: { columns: 5, dockApps: [] },
    localStorage: saved,
    sessionStorage: storage(skip ? { 'cytv.home.skipSetup': '1' } : {}),
    location: { search, replace: (s) => routes.push(s) },
    setTimeout,
    clearTimeout,
    document: {
      createElement: () => ({}),
      body: { appendChild: (s) => scripts.push(s.src) }
    },
    PalmServiceBridge: function () {
      this.cancel = () => {};
      this.call = (uri) => {
        requests.push(uri);
        const reply =
          uri === service + 'status'
            ? {
                returnValue: true,
                paired: true,
                pairing: false,
                credentialsReady: true,
                storageReady: true,
                startup: 'off',
                ...status
              }
            : uri === service + 'catalog'
              ? { returnValue: true, ...catalog }
              : {};
        this.onservicecallback(JSON.stringify(reply));
      };
    }
  };
  env.window = env;
  assert.ok(
    fs.existsSync(entry),
    'single-package Home must provide a product bootstrap'
  );
  vm.runInNewContext(fs.readFileSync(entry, 'utf8'), env);
  return { requests, scripts, routes, env, saved };
}
function tiles(result) {
  return Array.from(result.env.PilotHome.library.visible(), (a) => a.id);
}
const first = start();
assert.deepEqual(first.requests, [service + 'status', service + 'catalog']);
assert.deepEqual(first.scripts, ['app.js']);
assert.deepEqual(tiles(first), ['example.video', 'example.music']);
assert.deepEqual(first.env.PilotHome.library.visible()[0], apps[0]);
const migrated = start({
  saved: storage({ 'pilot.home.layout.v1': '["example.music"]' })
});
assert.deepEqual(tiles(migrated), ['example.music']);
assert.deepEqual(Array.from(migrated.env.PilotHome.library.hidden()), [
  'example.video'
]);
migrated.env.PilotHome.library.save(
  [],
  ['example.music', 'example.video'],
  false
);
const reloaded = start({ saved: migrated.saved });
assert.deepEqual(tiles(reloaded), []);
assert.equal(reloaded.env.PilotHome.library.showAddApp(), false);
assert.deepEqual(
  Array.from(reloaded.env.PilotHome.library.available(), (a) => a.id),
  ['example.music', 'example.video']
);
const oldEmpty = start({
  saved: storage({ 'pilot.home.layout.v1': '[]', 'tvhome.layout': '{invalid' })
});
assert.deepEqual(tiles(oldEmpty), []);
assert.equal(oldEmpty.env.PilotHome.library.available().length, 2);
const full = storage({ 'pilot.home.layout.v1': '[]' });
full.setItem = () => {
  throw Error('QuotaExceededError');
};
assert.deepEqual(
  tiles(start({ saved: full })),
  [],
  'storage failure must retain a migrated empty Home'
);
const ordered = start();
ordered.env.PilotHome.library.save(['example.music', 'example.video'], []);
const temporaryEmpty = start({ saved: ordered.saved, catalog: { apps: [] } });
assert.deepEqual(tiles(temporaryEmpty), []);
assert.deepEqual(
  tiles(start({ saved: ordered.saved })),
  ['example.music', 'example.video'],
  'a temporarily missing launch point must keep its saved Home position'
);
const unpaired = start({ status: { paired: false } });
assert.deepEqual(unpaired.routes, ['setup/index.html']);
assert.deepEqual(unpaired.scripts, []);
assert.deepEqual(unpaired.requests, [service + 'status']);
const later = start({ status: { paired: false }, search: '?skipSetup=1' });
assert.deepEqual(tiles(later), []);
assert.equal(later.saved.getItem(library.key), null);
const cached = start({
  saved: migrated.saved,
  catalog: { returnValue: false, errorCode: 'network-unavailable' }
});
assert.deepEqual(tiles(cached), []);
assert.equal(cached.env.PilotHome.library.available().length, 2);
const rejected = start({
  catalog: { returnValue: false, errorCode: 'saved-pairing-rejected' }
});
assert.deepEqual(rejected.routes, [
  'setup/index.html?settings=1&reason=saved-pairing-rejected'
]);
let refreshed;
first.env.PilotHome.installed((items, ids) => {
  refreshed = [items, ids];
});
assert.deepEqual(Array.from(refreshed[1]), ['example.video', 'example.music']);
assert.equal(first.requests.at(-1), service + 'catalog');
console.log(
  'Product Home bootstrap, migration, pairing, cache and catalog refresh passed.'
);
