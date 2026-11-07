'use strict';
const assert = require('node:assert/strict');
const policy = require('../../launcher/theme-policy.js'),
  HomeLayout = require('../../launcher/home-layout.js'),
  compiler = require('../../theme-api/compile.cjs');
const fixture = require('./fixtures/valid-manifest.json');
const manifest = (inputs = 'shelf') => ({
  ...fixture,
  layout: { ...fixture.layout, inputs },
  requires: { ...fixture.requires, capabilities: ['input-placement-v1'] }
});
assert.equal(policy.validateManifest(manifest()).layout.inputs, 'shelf');
assert.equal(policy.validateManifest(manifest('menu')).layout.inputs, 'menu');
assert.equal(policy.validateManifest(fixture).layout.inputs, undefined);
for (const mutate of [
  (m) => (m.layout.inputs = 'bottom'),
  (m) => (m.layout.inputs = {}),
  (m) => (m.requires.capabilities = []),
  (m) => delete m.layout.inputs,
  (m) => (m.layout.preset = 'side-grid')
]) {
  const m = manifest();
  mutate(m);
  assert.throws(() => policy.validateManifest(m));
}
const storage = {
  getItem: () => null,
  setItem: () => {
    throw Error('theme placement must not write a user preference');
  }
};
const model = HomeLayout.create(storage, { columns: 5 });
assert.equal(model.state().inputs, 'menu');
model.setThemeLayout(manifest().layout);
assert.equal(model.state().inputs, 'shelf');
const before = model.state();
assert.throws(() =>
  model.setThemeLayout({ ...manifest().layout, inputs: 'bottom' })
);
assert.deepEqual(model.state(), before);
model.setThemeLayout(fixture.layout);
assert.equal(model.state().inputs, 'menu');
(async () => {
  const source = {
    manifest: manifest(),
    css: '.ctv-input-tile.is-focused{background-color:#123456}.ctv-input-status{color:white}.ctv-input-preview{border-color:red}',
    assets: [
      {
        id: 'preview',
        path: 'preview.png',
        mediaType: 'image/png',
        data: Buffer.from(
          'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aE1sAAAAASUVORK5CYII=',
          'base64'
        )
      }
    ],
    documents: [
      { path: 'LICENSE.txt', data: 'MIT' },
      { path: 'CREDITS.txt', data: 'Original' }
    ]
  };
  const out = await compiler.compileSource(source);
  assert.deepEqual(out.manifest.requires.capabilities, ['input-placement-v1']);
  assert.match(policy.compileRules(out.rules, {}), /ctv-input-preview/);
  const combined = manifest();
  combined.layout.motion = 'classic';
  combined.layout.datePlacement = 'below-clock';
  combined.requires.capabilities = [
    'modern-icon-css-v1',
    'classic-motion-v1',
    'date-placement-v1',
    'input-placement-v1'
  ];
  assert.equal(policy.validateManifest(combined).layout.inputs, 'shelf');
  policy.validateMotion(combined, { schemaVersion: 1, rules: [] });
  console.log(
    'PASS theme-owned input placement, strict capability pairing, defaults, no preference writes, CSS and combined capabilities'
  );
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
