const assert = require('node:assert/strict'),
  layout = require('../../launcher/home-layout.js');
for (const preset of [
  'dock-grid',
  'scenic-grid',
  'icon-grid',
  'side-grid',
  'channel-list'
]) {
  const original = layout.geometry(preset, 5),
    reserved = layout.geometry(preset, 5, null, {
      bottom: 600,
      format: 'forecast',
      shelfTop: 236
    });
  assert.equal(
    reserved.top - reserved.dockTop,
    original.top - original.dockTop
  );
  assert(reserved.dockTop >= 632, preset);
  assert.deepEqual(layout.geometry(preset, 5), original);
}
const base = layout.geometry('dock-grid', 5),
  shelf = layout.geometry('dock-grid', 5, null, {
    bottom: 320,
    format: 'text',
    shelfTop: 358
  });
assert.equal(shelf.dockTop, base.dockTop + 122);
assert.equal(
  layout.geometry('channel-list', 1, null, { bottom: 700, format: 'forecast' })
    .dockTop,
  240
);
console.log('PASS preset-owned weather and Inputs reservations');
