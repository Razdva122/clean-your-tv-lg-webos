const assert = require('node:assert/strict');
const { test } = require('node:test');
const { create } = require('../../launcher/app-library');
const inventory = [
  { id: 'a', title: 'Alpha' },
  { id: 'b', title: 'Beta' },
  { id: 'c', title: 'Gamma' }
];
function setup() {
  const values = new Map();
  const storage = {
    getItem: (k) => values.get(k) || null,
    setItem: (k, v) => values.set(k, v)
  };
  return {
    storage,
    model: create(storage, inventory, { dockApps: ['a', 'b', 'c'] })
  };
}
test('hidden app remains available after an incomplete TV inventory response', () => {
  const { model, storage } = setup();
  model.save(['b', 'c'], ['a']);
  model.refresh([
    { id: 'b', title: 'Beta updated' },
    { id: 'd', title: 'Delta' }
  ]);
  assert.deepEqual(
    model.available().map((a) => a.id),
    ['a', 'd']
  );
  model.add('a');
  assert.deepEqual(
    model.visible().map((a) => a.id),
    ['b', 'c', 'a']
  );
  assert.equal(model.visible()[0].title, 'Beta updated');
  assert.deepEqual(
    create(storage, [], {})
      .visible()
      .map((a) => a.id),
    ['b', 'c', 'a']
  );
});
test('Undo restores the whole layout after a partial or empty refresh', () => {
  for (const response of [[{ id: 'a', title: 'Alpha' }], []]) {
    const { model } = setup();
    model.refresh(response);
    model.save(['b', 'c'], ['a']);
    model.save(['a', 'b', 'c'], []);
    assert.deepEqual(
      model.visible().map((a) => a.id),
      ['a', 'b', 'c']
    );
  }
});
