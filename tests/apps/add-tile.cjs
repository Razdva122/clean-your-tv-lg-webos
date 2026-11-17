// Catches lost visibility preferences, unintended layout edits and partial saves.
const assert = require('node:assert/strict');
const { create, key } = require('../../launcher/app-library.js');
const rootProfile = require('../../root-edition/ui/root-profile-data.js');
const data = require('../../launcher/user-data.js');
const values = new Map();
const storage = {
  getItem: (k) => values.get(k) ?? null,
  setItem: (k, v) => values.set(k, v)
};
const inventory = ['a', 'b', 'c', 'd'].map((id) => ({
  id,
  title: id,
  icon: 'data:image/png;base64,YQ=='
}));
const config = { columns: 5, dockApps: [], hiddenApps: [] };
let library = create(storage, inventory, config);
assert.equal(
  typeof library.showAddApp,
  'function',
  'app library must expose the saved visibility preference'
);
assert.equal(
  library.showAddApp(),
  true,
  'existing installations show + by default'
);
library.save(['b', 'a'], ['a']);
library.setShowAddApp(false);
assert.deepEqual(
  library.visible().map((a) => a.id),
  ['b']
);
assert.deepEqual(library.hidden(), ['a']);
library = create(storage, inventory, config);
assert.equal(library.showAddApp(), false, 'choice survives reload');
library.add('a');
assert.equal(
  create(storage, inventory, config).showAddApp(),
  false,
  'adding keeps + hidden'
);
assert.deepEqual(
  library.visible().map((a) => a.id),
  ['b', 'a']
);
for (const adapter of [data, rootProfile]) {
  const profile = adapter.validate({
    schema: 1,
    inventory: { apps: inventory, inputs: [] },
    config,
    settings: { 'tvhome.layout': storage.getItem(key) }
  });
  const restored = create(
    { getItem: (k) => profile.settings[k] ?? null },
    inventory,
    config
  );
  assert.equal(
    restored.showAddApp(),
    false,
    'portable profile retains visibility'
  );
}
const malformed = {
  schema: 1,
  inventory: { apps: inventory, inputs: [] },
  config,
  settings: {
    'tvhome.layout': JSON.stringify({
      version: 1,
      ids: [],
      hidden: [],
      catalog: [],
      showAddApp: 'false'
    })
  }
};
assert.throws(
  () => rootProfile.validate(malformed),
  /Invalid Add app visibility/
);
const before = storage.getItem(key);
assert.throws(() => library.setShowAddApp('false'), /invalid/);
assert.equal(storage.getItem(key), before);
const setItem = storage.setItem;
storage.setItem = () => {
  throw Error('quota');
};
assert.throws(() => library.setShowAddApp(true), /quota/);
assert.equal(
  library.showAddApp(),
  false,
  'failed save leaves live choice intact'
);
storage.setItem = setItem;
library.setShowAddApp(true);
assert.equal(create(storage, inventory, config).showAddApp(), true);
library.save(['b', 'a', 'c', 'd'], []);
const ids = (apps) => apps.map((a) => a.id);
assert.deepEqual(ids(library.ordered(1)), ['b', 'a', 'c', 'd']);
library.recordLaunch('d'); // Disabled installations do not collect launches.
library.setUsageSort(true);
assert.deepEqual(ids(library.ordered(1)), ['b', 'a', 'c', 'd']);
library.recordLaunch('d');
library.recordLaunch('c');
library.recordLaunch('d');
library = create(storage, inventory, config);
assert.deepEqual(ids(library.ordered(1)), ['b', 'd', 'c', 'a']);
assert.deepEqual(ids(library.visible()), ['b', 'a', 'c', 'd']);
library.save(['b', 'a', 'c'], ['d']);
assert.deepEqual(ids(library.ordered(1)), ['b', 'c', 'a']);
library.save(['b', 'a', 'c', 'd'], []);
assert.deepEqual(ids(library.ordered(1)), ['b', 'd', 'c', 'a']);
library.setUsageSort(false);
assert.deepEqual(ids(library.ordered(1)), ['b', 'a', 'c', 'd']);
console.log(
  'PASS app visibility and usage sorting defaults, reload, editing and storage failure'
);
