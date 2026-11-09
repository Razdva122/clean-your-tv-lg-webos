'use strict';
const assert = require('node:assert/strict'),
  policy = require('../../launcher/theme-policy.js'),
  fixture = require('../themes/fixtures/valid-manifest.json'),
  compiler = require('../../theme-api/compile.cjs');
const valid = () => ({
  ...structuredClone(fixture),
  layout: {
    ...fixture.layout,
    weather: {
      formats: ['text', 'current', 'details', 'forecast'],
      scale: 1,
      padding: 24,
      icons: 'fill'
    }
  },
  requires: { ...fixture.requires, capabilities: ['weather-v1'] }
});
(async () => {
  assert.deepEqual(policy.normalizeWeather({ formats: ['text'] }), {
    formats: ['text'],
    scale: 1,
    padding: 24,
    icons: 'fill'
  });
  assert.deepEqual(policy.validateManifest(valid()).layout.weather.formats, [
    'text',
    'current',
    'details',
    'forecast'
  ]);
  assert.doesNotThrow(() => policy.validateManifest(structuredClone(fixture)));
  for (const weather of [
    { formats: ['unknown'] },
    { formats: ['text', 'text'] },
    { scale: 0.2 },
    { scale: 1.26 },
    { padding: 100 },
    { icons: 'https://x' },
    { left: 100 },
    { formats: 'text' }
  ])
    assert.throws(
      () => policy.normalizeWeather(weather),
      undefined,
      JSON.stringify(weather)
    );
  const missing = valid();
  missing.requires.capabilities = [];
  assert.throws(() => policy.validateManifest(missing));
  const unpaired = valid();
  delete unpaired.layout.weather;
  assert.throws(() => policy.validateManifest(unpaired));
  for (const part of [
    'weather',
    'weather-temp',
    'weather-secondary',
    'weather-condition',
    'weather-bar',
    'weather-track',
    'weather-day',
    'weather-icon'
  ]) {
    const c = await compiler.compileThemeCss(
      '.ctv-' +
        part +
        '{color:#ddd;background-color:transparent;border-radius:4px}'
    );
    assert.match(c.css, new RegExp('ctv-' + part));
  }
  await assert.rejects(() =>
    compiler.compileThemeCss('.ctv-weather{position:absolute;left:50px}')
  );
  console.log(
    'PASS typed weather theme capability, safe parts and legacy manifests'
  );
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
