'use strict';
// Classic motion is opt-in: layout.motion "classic" on dock-grid, paired with classic-motion-v1,
// and an opted-in theme cannot replace the engine's transitions on the parts it animates.
const assert = require('node:assert/strict');
const policy = require('../../launcher/theme-policy.js'),
  compiler = require('../../theme-api/compile.cjs'),
  contract = require('../../theme-api/contract.json');
const fixture = require('./fixtures/valid-manifest.json');
const layout = {
  preset: 'dock-grid',
  columns: 5,
  spacingScale: 1,
  textScale: 1,
  focusScale: 1.1
};
const manifest = (
  extra = { motion: 'classic' },
  capabilities = ['classic-motion-v1']
) => ({
  ...fixture,
  layout: { ...layout, ...extra },
  requires: { ...fixture.requires, capabilities }
});
const transition = (part) => ({
  schemaVersion: 1,
  rules: [
    {
      selector: [{ part, states: [] }],
      declarations: [
        {
          property: 'transition',
          value: {
            type: 'transition',
            property: 'box-shadow',
            duration: 200,
            easing: 'ease'
          }
        }
      ]
    }
  ]
});

assert.deepEqual(contract.layout.motion.values, ['classic']);
assert.equal(
  contract.optionalCapabilities['classic-motion-v1'].layout,
  'motion'
);
assert.deepEqual(
  contract.optionalCapabilities['classic-motion-v1'].engineMotionParts,
  ['card', 'focus', 'label', 'shortcut', 'input-tile']
);

assert.equal(policy.validateManifest(manifest()).layout.motion, 'classic');
assert.equal(
  policy.validateManifest(manifest({}, [])).layout.motion,
  undefined,
  'without the opt-in a theme keeps immediate remote focus'
);
for (const bad of [
  manifest({ motion: 'classic' }, []),
  manifest({}, ['classic-motion-v1'])
])
  assert.throws(
    () => policy.validateManifest(bad),
    (error) => error.code === 'api-unsupported',
    'the layout field and capability are paired'
  );
for (const bad of [
  manifest({ motion: 'fast' }),
  manifest({ motion: true }),
  manifest({ motion: 'classic', preset: 'side-grid' }),
  manifest({
    motion: 'classic',
    preset: 'scenic-grid',
    allowColumnOverride: false
  })
])
  assert.throws(
    () => policy.validateManifest(bad),
    (error) => error.code === 'layout-invalid',
    JSON.stringify(bad.layout)
  );

const opted = policy.validateManifest(manifest()),
  plain = policy.validateManifest(manifest({}, []));
for (const part of contract.optionalCapabilities['classic-motion-v1']
  .engineMotionParts) {
  assert.throws(
    () => policy.validateMotion(opted, transition(part)),
    (error) => error.code === 'css-value',
    part
  );
  policy.validateMotion(plain, transition(part));
}
for (const part of ['dock', 'inputs', 'input-row', 'library-row'])
  policy.validateMotion(opted, transition(part));

(async () => {
  const source = (css, extra) => ({
    manifest: manifest(extra, []),
    css,
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
  });
  const output = await compiler.compileSource(source('.ctv-card{color:red}'));
  assert.deepEqual(
    output.manifest.requires.capabilities,
    ['classic-motion-v1'],
    'the compiler emits the capability for layout.motion'
  );
  assert.equal(output.manifest.layout.motion, 'classic');
  await assert.rejects(
    compiler.compileSource(
      source('.ctv-focus{transition:box-shadow 200ms ease}')
    ),
    /transition on focus/
  );
  assert.deepEqual(
    (
      await compiler.compileSource(
        source('.ctv-focus{transition:box-shadow 200ms ease}', {})
      )
    ).manifest.requires.capabilities,
    [],
    'themes without the opt-in may still declare transitions'
  );
  console.log(
    'PASS opt-in Classic motion: paired capability, dock-grid only, engine-owned transitions, compiler'
  );
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
