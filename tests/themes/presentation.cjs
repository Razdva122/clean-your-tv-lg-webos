const assert = require('node:assert/strict'),
  fs = require('node:fs');
const policy = require('../../launcher/theme-policy');
const fixture = JSON.parse(
  fs.readFileSync('launcher/themes/ribbon/cytv-theme.json')
);
const manifest = JSON.parse(JSON.stringify(fixture));
manifest.layout.presentation = 'overlay';
manifest.requires.capabilities = manifest.requires.capabilities
  .filter((c) => c !== 'overlay-presentation-v1')
  .concat('overlay-presentation-v1');
assert.equal(policy.validateManifest(manifest).layout.presentation, 'overlay');
for (const bad of [
  { ...manifest, layout: { ...manifest.layout, presentation: 'floating' } },
  {
    ...manifest,
    requires: {
      ...manifest.requires,
      capabilities: manifest.requires.capabilities.filter(
        (c) => c !== 'overlay-presentation-v1'
      )
    }
  },
  { ...manifest, layout: { ...manifest.layout, preset: 'dock-grid' } },
  { ...manifest, layout: { ...manifest.layout, ribbon: undefined } }
])
  assert.throws(() => policy.validateManifest(bad));
const without = JSON.parse(JSON.stringify(manifest));
delete without.layout.presentation;
assert.throws(
  () => policy.validateManifest(without),
  'capability must be paired with opt-in'
);
console.log('PASS bounded overlay presentation opt-in and capability pairing');
