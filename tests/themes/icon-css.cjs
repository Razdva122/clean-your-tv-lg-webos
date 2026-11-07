'use strict';
const assert = require('node:assert/strict'),
  p = require('../../launcher/theme-policy.js'),
  c = require('../../theme-api/compile.cjs');
(async () => {
  await c.compileThemeCss(
    '.ctv-card{isolation:isolate;overflow:visible}.ctv-card .ctv-icon{transform:scale(1.6)}.ctv-card .ctv-icon.is-wide{transform:scale(2)}'
  );
  const result = await c.compileThemeCss(
    '.ctv-icon{filter:grayscale(1) invert(1) brightness(1.3);mix-blend-mode:screen}'
  );
  await c.compileThemeCss(
    '.ctv-icon.is-bright{filter:grayscale(1) invert(1) brightness(.8) contrast(10);mix-blend-mode:screen}'
  );
  assert.match(
    p.compileRules(result.bundle, {}),
    /grayscale\(1\) invert\(1\) brightness\(1.3\)/
  );
  for (const css of [
    '.ctv-home{filter:brightness(0)}',
    '.ctv-icon{filter:url(https://evil/x)}',
    '.ctv-icon{filter:blur(10px)}',
    '.ctv-icon{filter:brightness(999)}',
    '.ctv-icon{mix-blend-mode:overlay}',
    '.ctv-card .ctv-icon{transform:scale(9)}',
    '.ctv-card .ctv-icon{transform:translateX(10px)}',
    '.ctv-home{overflow:visible}',
    '.ctv-icon{transform:scale(2)}'
  ])
    await assert.rejects(() => c.compileThemeCss(css));
  const fixture = require('./fixtures/valid-manifest.json'),
    image = Buffer.from(
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aE1sAAAAASUVORK5CYII=',
      'base64'
    );
  const output = await c.compileSource({
    manifest: fixture,
    source: fixture.source,
    css: '.ctv-icon{filter:invert(1);mix-blend-mode:screen}',
    assets: [
      {
        id: 'preview',
        path: 'preview.png',
        mediaType: 'image/png',
        data: image
      }
    ],
    documents: [
      { path: 'LICENSE.txt', data: 'MIT' },
      { path: 'CREDITS.txt', data: 'Original' }
    ]
  });
  assert.deepEqual(output.manifest.requires.capabilities, [
    'modern-icon-css-v1'
  ]);
  assert.throws(() =>
    p.validateManifest({
      ...output.manifest,
      requires: { ...output.manifest.requires, capabilities: ['arbitrary'] }
    })
  );
  console.log(
    'PASS typed CSS-only icon effects and explicit modern-browser capability'
  );
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
