// Presets change trusted geometry while the user's column preference remains authoritative.
const assert = require('node:assert/strict');
const { create, geometry } = require('../../launcher/home-layout.js');
const values = new Map();
const storage = {
  getItem: (k) => (values.has(k) ? values.get(k) : null),
  setItem: (k, v) => values.set(k, v),
  removeItem: (k) => values.delete(k)
};
const model = create(storage, { columns: 5 });
const layout = (preset, columns) => ({
  preset,
  columns,
  spacingScale: 1,
  textScale: 1,
  focusScale: 1.1
});
for (const preset of [
  'dock-grid',
  'icon-grid',
  'side-grid',
  'channel-list',
  'scenic-grid'
]) {
  model.setThemeLayout(layout(preset, 3));
  assert.equal(model.state().preset, preset);
  assert.equal(model.state().columns, 3);
  model.setColumns(8);
  model.setThemeLayout(layout(preset, 1));
  assert.equal(model.state().columns, 8);
  for (const count of [1, 2, 3, 4, 5, 6, 7, 8]) {
    const g = geometry(preset, count);
    assert(g.cardWidth > 0 && g.cardHeight >= 48);
    const first = g.left + (g.columnWidth - g.cardWidth) / 2;
    const margin = (g.cardWidth * 0.1 + 24) / 2;
    assert(
      first - margin >= 0 &&
        first + (count - 1) * g.columnWidth + g.cardWidth + margin <= 1920
    );
    assert(g.top + g.cardHeight + margin < 1080);
  }
  model.setColumns(null);
}
const before = model.state();
for (const bad of [
  layout('freeform', 3),
  layout('side-grid', 9),
  { ...layout('icon-grid', 3), spacingScale: 1.2 }
]) {
  assert.throws(() => model.setThemeLayout(bad), /layout-invalid/);
  assert.deepEqual(model.state(), before);
}
assert.equal(
  geometry('dock-grid', 5).top,
  708,
  'Classic geometry is preserved'
);
assert.notDeepEqual(geometry('icon-grid', 5), geometry('side-grid', 5));
console.log('PASS distinct trusted layouts, bounds and column precedence');

// Author-controlled layouts temporarily suspend the user's saved column choice.
model.setColumns(6);
model.setThemeLayout({
  ...layout('scenic-grid', 8),
  allowColumnOverride: false
});
assert.equal(model.state().columns, 8);
assert.equal(model.state().override, 6);
assert.equal(model.state().allowColumnOverride, false);
const storedBefore = storage.getItem(
  require('../../launcher/home-layout.js').key
);
assert.throws(() => model.setColumns(2), /columns-locked/);
assert.equal(
  storage.getItem(require('../../launcher/home-layout.js').key),
  storedBefore
);
model.setThemeLayout(layout('dock-grid', 5));
assert.equal(
  model.state().columns,
  6,
  'returning to an adjustable theme restores the user choice'
);
assert.equal(
  model.state().allowColumnOverride,
  true,
  'omitted flag remains backward compatible'
);
for (const invalid of [null, 0, 'false', {}]) {
  const previous = model.state();
  assert.throws(
    () =>
      model.setThemeLayout({
        ...layout('scenic-grid', 8),
        allowColumnOverride: invalid
      }),
    /layout-invalid/
  );
  assert.deepEqual(model.state(), previous);
}
