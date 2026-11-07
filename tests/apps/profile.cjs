const assert = require('node:assert/strict');
const data = require('../../launcher/user-data');
const map = new Map(),
  storage = {
    getItem: (k) => map.get(k) || null,
    setItem: (k, v) => map.set(k, v)
  };
const layout = JSON.stringify({
  version: 1,
  ids: ['b'],
  hidden: ['a'],
  catalog: [{ id: 'b', title: 'B', icon: '' }]
});
const profile = {
  schema: 1,
  inventory: { apps: [], inputs: [] },
  config: { columns: 5, dockApps: [], hiddenApps: [] },
  settings: { 'tvhome.layout': layout }
};
data.save(storage, profile);
data.apply(storage, data.load(storage));
assert.equal(map.get('tvhome.layout'), layout);
const library = require('../../launcher/app-library').create(
  storage,
  [{ id: 'a', title: 'A' }],
  profile.config
);
assert.deepEqual(
  library.visible().map((a) => a.id),
  ['b']
);
assert.deepEqual(
  library.available().map((a) => a.id),
  ['a']
);
console.log('PASS layout preserved through profile backup and restore');
