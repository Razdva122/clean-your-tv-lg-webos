const assert = require('node:assert/strict');
const create = require('../launcher/install-settings.js');
const values = new Map();
const storage = {
  getItem: (key) => (values.has(key) ? values.get(key) : null),
  setItem: (key, value) => values.set(key, value),
  removeItem: (key) => values.delete(key)
};
const setup = create({ localStorage: storage });
assert.equal(
  setup.apply({
    cytvSetup: { id: 'a'.repeat(32), theme: 'liquid-glass', weather: true }
  }),
  true
);
assert.equal(
  JSON.parse(values.get('tvhome.theme.choice.v1')).id,
  'builtin:liquid-glass'
);
assert.deepEqual(JSON.parse(values.get('tvhome.weather.v1')), {
  enabled: true,
  mode: 'auto'
});
values.set(
  'tvhome.theme.choice.v1',
  JSON.stringify({ id: 'builtin:classic', title: 'Classic' })
);
assert.equal(
  setup.apply({
    cytvSetup: { id: 'a'.repeat(32), theme: 'liquid-glass', weather: true }
  }),
  false
);
assert.equal(
  JSON.parse(values.get('tvhome.theme.choice.v1')).id,
  'builtin:classic'
);
assert.equal(
  setup.apply({
    cytvSetup: { id: 'b'.repeat(32), theme: 'ribbon', weather: true }
  }),
  false
);
assert.equal(
  setup.apply({
    cytvSetup: { id: 'b'.repeat(32), theme: 'external', weather: false }
  }),
  false
);
assert.equal(
  setup.apply({
    cytvSetup: {
      id: 'b'.repeat(32),
      theme: 'classic',
      weather: true,
      renewal: true
    }
  }),
  false
);
assert.equal(
  setup.apply({
    cytvSetup: { id: 'b'.repeat(32), theme: 'ribbon', weather: false }
  }),
  true
);
assert.equal(JSON.parse(values.get('tvhome.weather.v1')).enabled, false);
assert.throws(() =>
  create({
    localStorage: {
      getItem: () => null,
      setItem: () => {},
      removeItem: () => {}
    }
  }).apply({ cytvSetup: { id: 'c'.repeat(32), theme: 'classic' } })
);
console.log(
  'PASS post-install appearance parameters, mode bounds, one-time application and storage errors'
);
