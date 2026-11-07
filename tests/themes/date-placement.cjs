'use strict';
const assert = require('node:assert/strict'),
  fs = require('node:fs'),
  vm = require('node:vm');
const policy = require('../../launcher/theme-policy.js'),
  fixture = require('./fixtures/valid-manifest.json');
const manifest = () => ({
  ...structuredClone(fixture),
  layout: { ...fixture.layout, datePlacement: 'below-clock' },
  requires: { ...fixture.requires, capabilities: ['date-placement-v1'] }
});
assert.equal(
  policy.validateManifest(manifest()).layout.datePlacement,
  'below-clock'
);
for (const change of [
  (m) => (m.requires.capabilities = []),
  (m) => (m.layout.datePlacement = 'absolute'),
  (m) => (m.layout.preset = 'side-grid')
]) {
  const m = manifest();
  change(m);
  assert.throws(() => policy.validateManifest(m));
}
const nodes = {},
  document = {
    getElementById: (id) => nodes[id] || null,
    createElement: () => ({}),
    head: {
      appendChild(n) {
        nodes[n.id] = n;
        n.parentNode = this;
      },
      removeChild(n) {
        delete nodes[n.id];
      }
    }
  };
const context = {
  document,
  ThemePolicy: {
    ...policy,
    compileRules: (b, h) => policy.compileRules(structuredClone(b), h)
  }
};
vm.runInNewContext(
  fs.readFileSync('launcher/theme-runtime.js', 'utf8'),
  context
);
const rules = { schemaVersion: 1, rules: [] };
context.ThemeRuntime.apply({ manifest: manifest(), rules });
assert.match(nodes['ctv-theme-style'].textContent, /#timeRow/);
context.ThemeRuntime.suspend('settings');
assert.equal(nodes['ctv-theme-style'].disabled, true);
context.ThemeRuntime.resume('settings');
assert.equal(nodes['ctv-theme-style'].disabled, false);
context.ThemeRuntime.apply({ manifest: fixture, rules });
assert.doesNotMatch(nodes['ctv-theme-style'].textContent, /#timeRow/);
const invalid = manifest();
invalid.layout.datePlacement = 'absolute';
const before = nodes['ctv-theme-style'].textContent;
assert.throws(() => context.ThemeRuntime.apply({ manifest: invalid, rules }));
assert.equal(nodes['ctv-theme-style'].textContent, before);
context.ThemeRuntime.reset();
assert.equal(nodes['ctv-theme-style'], undefined);
console.log('PASS optional date placement validation and lifecycle');
assert.throws(() =>
  policy.validateManifest({
    ...manifest(),
    layout: { ...manifest().layout, datePlacement: 'below-clock;color:red' }
  })
);
assert.throws(() =>
  policy.validateManifest({
    ...fixture,
    requires: { ...fixture.requires, capabilities: ['date-placement-v1'] }
  })
);
const inline = manifest();
inline.layout.datePlacement = 'inline';
context.ThemeRuntime.apply({ manifest: inline, rules });
assert.doesNotMatch(nodes['ctv-theme-style'].textContent, /#timeRow/);
(async () => {
  const compiler = require('../../theme-api/compile.cjs');
  const source = {
    manifest: manifest(),
    css: '.ctv-card{color:red}',
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
  const compiled = await compiler.compileSource(source);
  assert.deepEqual(compiled.manifest.requires.capabilities, [
    'date-placement-v1'
  ]);
  assert.equal(compiled.manifest.layout.datePlacement, 'below-clock');
  const unchanged = await compiler.compileSource({
    ...source,
    manifest: fixture
  });
  assert.deepEqual(unchanged.manifest.requires.capabilities, []);
  assert.equal(
    Object.hasOwn(unchanged.manifest.layout, 'datePlacement'),
    false
  );
  console.log('PASS compiler infers only optional date capability');
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
