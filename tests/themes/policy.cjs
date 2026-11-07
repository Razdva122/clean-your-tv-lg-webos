const assert = require('node:assert/strict');
const fs = require('node:fs');
assert.ok(
  fs.existsSync('launcher/theme-policy.js'),
  'shared typed theme policy exists'
);
const p = require('../../launcher/theme-policy.js');
const valid = {
  schemaVersion: 1,
  rules: [
    {
      selector: [{ part: 'card', states: [] }],
      declarations: [
        {
          property: 'background-color',
          value: { type: 'color', rgba: [24, 35, 48, 1] }
        }
      ]
    }
  ]
};
assert.deepEqual(p.validateRules(valid), valid);
assert.match(p.compileRules(valid, {}), /background-color:rgba\(24,35,48,1\)/);
for (const bad of ['body', 'card > body', 'card:hover']) {
  const x = JSON.parse(JSON.stringify(valid));
  x.rules[0].selector[0].part = bad;
  assert.throws(() => p.validateRules(x), /css-selector/);
}
for (const value of [
  { type: 'raw', text: 'red;}body{display:none' },
  { type: 'color', rgba: [0, 0, 0, Infinity] },
  { type: 'color', rgba: [0, 0, 0, 1], raw: 'x' }
]) {
  const x = JSON.parse(JSON.stringify(valid));
  x.rules[0].declarations[0].value = value;
  assert.throws(() => p.validateRules(x), /css-value/);
}
assert.throws(
  () =>
    p.validateRules(
      JSON.parse('{"schemaVersion":1,"rules":[],"__proto__":{}}')
    ),
  /invalid|budget/
);
assert.throws(
  () =>
    p.validateRules({
      schemaVersion: 1,
      rules: new Array(513).fill(valid.rules[0])
    }),
  /css-budget/
);
assert.throws(
  () =>
    p.validateRules({
      schemaVersion: 1,
      rules: [
        {
          selector: [{ part: 'card', states: [] }],
          declarations: [
            { property: 'display', value: { type: 'keyword', value: 'none' } }
          ]
        }
      ]
    }),
  /css-property/
);
const fixture = require('./fixtures/valid-manifest.json');
assert.equal(p.validateManifest(fixture).layout.columns, 4);
for (const columns of [0, 9, NaN]) {
  const m = structuredClone(fixture);
  m.layout.columns = columns;
  assert.throws(() => p.validateManifest(m), /layout-invalid/);
}
assert.throws(
  () => p.validateManifest({ ...fixture, themeApiVersion: 2 }),
  /api-unsupported/
);
assert.throws(
  () =>
    p.validateManifest({
      ...fixture,
      assets: [...fixture.assets, ...fixture.assets]
    }),
  /asset-invalid/
);
const coll = {
  schemaVersion: 1,
  repository: 'https://github.com/owner/repo',
  themes: [
    {
      id: 'github:owner/repo:classic',
      title: 'Classic',
      themeVersion: '1.0.0',
      path: 'classic/cytv-theme.json',
      sha256: 'a'.repeat(64)
    }
  ]
};
assert.deepEqual(p.validateCollection(coll), coll);
for (const change of [
  { id: 'github:other/repo:classic' },
  { path: '../escape.json' },
  { sha256: 'bad' }
]) {
  const c = structuredClone(coll);
  Object.assign(c.themes[0], change);
  assert.throws(() => p.validateCollection(c));
}
assert.throws(() =>
  p.validateCollection({ ...coll, themes: [...coll.themes, ...coll.themes] })
);
const gradient = {
  schemaVersion: 1,
  rules: [
    {
      selector: [{ part: 'home', states: [] }],
      declarations: [
        {
          property: 'background-image',
          value: {
            type: 'gradient',
            angle: 180,
            stops: [
              { color: { type: 'raw', rgba: [0, 0, 0, 1] }, position: 0 },
              { color: { type: 'color', rgba: [0, 0, 0, 1] }, position: 100 }
            ]
          }
        }
      ]
    }
  ]
};
assert.throws(() => p.validateRules(gradient), /css-value/);

const htmlDocument = structuredClone(fixture);
htmlDocument.documents[0].path = 'payload.html';
htmlDocument.license.textPath = 'payload.html';
assert.throws(() => p.validateManifest(htmlDocument), /asset-invalid/);
const wrongImage = structuredClone(fixture);
wrongImage.assets[0].path = 'payload.html';
assert.throws(() => p.validateManifest(wrongImage), /asset-invalid/);
const imageRule = {
  selector: [{ part: 'home', states: [] }],
  declarations: [
    { property: 'background-image', value: { type: 'asset', id: 'preview' } }
  ]
};
const repeatedImages = {
  schemaVersion: 1,
  rules: Array.from({ length: 512 }, () => structuredClone(imageRule))
};
const imageHandle =
  'data:image/png;base64,' + Buffer.alloc(32768).toString('base64');
assert.throws(
  () => p.compileRules(repeatedImages, { preview: imageHandle }),
  /css-budget/,
  'repeated handle bytes count toward emitted CSS budget'
);
const smallImageCss = p.compileRules(
  { schemaVersion: 1, rules: [imageRule] },
  { preview: 'data:image/png;base64,AA==' }
);
assert.match(
  smallImageCss,
  /data:image\/png;base64,AA==/,
  'small trusted data images remain supported'
);
assert(
  p.compileRules(repeatedImages, { preview: 'blob:verified-image' }).length <=
    p.limits.emittedCssBytes
);
// Layout choices remain a finite trusted set; themes still cannot set geometry CSS.
for (const preset of [
  'dock-grid',
  'icon-grid',
  'side-grid',
  'channel-list',
  'scenic-grid'
]) {
  const m = structuredClone(fixture);
  m.layout.preset = preset;
  assert.equal(p.validateManifest(m).layout.preset, preset);
}
for (const preset of ['custom', '../side-grid', '', null]) {
  const m = structuredClone(fixture);
  m.layout.preset = preset;
  assert.throws(() => p.validateManifest(m), /layout-invalid/);
}
const focusRule = structuredClone(valid);
focusRule.rules[0].selector[0].part = 'focus';
assert.match(p.compileRules(focusRule, {}), /\.ctv-focus/);
for (const property of [
  'position',
  'left',
  'top',
  'width',
  'height',
  'transform',
  'opacity',
  'visibility'
]) {
  const x = structuredClone(focusRule);
  x.rules[0].declarations[0].property = property;
  assert.throws(() => p.validateRules(x), /css-property/);
}
// The library panel and close control expose appearance, never modal geometry.
for (const part of ['library-panel', 'library-close']) {
  const rule = structuredClone(valid);
  rule.rules[0].selector[0].part = part;
  if (part === 'library-close') rule.rules[0].selector[0].states = ['focused'];
  assert.match(p.compileRules(rule, {}), new RegExp('\\.ctv-' + part));
  for (const property of [
    'display',
    'position',
    'width',
    'height',
    'opacity',
    'visibility'
  ]) {
    const invalid = structuredClone(rule);
    invalid.rules[0].declarations[0].property = property;
    assert.throws(() => p.validateRules(invalid), /css-property/);
  }
}
console.log('Theme policy checks passed');

for (const value of [true, false]) {
  const m = structuredClone(fixture);
  m.layout.allowColumnOverride = value;
  assert.equal(p.validateManifest(m).layout.allowColumnOverride, value);
}
for (const value of [null, 0, 'false', {}]) {
  const m = structuredClone(fixture);
  m.layout.allowColumnOverride = value;
  assert.throws(() => p.validateManifest(m), /layout-invalid/);
}

// UHD is reserved for the wallpaper; previews and button artwork stay bounded.
const uhd = structuredClone(fixture),
  wallpaper = structuredClone(uhd.assets[0]);
wallpaper.id = 'wallpaper';
wallpaper.path = 'wallpaper.png';
wallpaper.width = 3840;
wallpaper.height = 2160;
uhd.assets.push(wallpaper);
uhd.defaults.wallpaperAssetId = 'wallpaper';
assert.equal(p.validateManifest(uhd).assets[1].width, 3840);
assert.throws(
  () =>
    p.validateManifest({
      ...uhd,
      defaults: { ...uhd.defaults, wallpaperAssetId: null }
    }),
  /asset-invalid/
);
for (const dimensions of [
  [3841, 2160],
  [3840, 2161]
]) {
  const invalid = structuredClone(uhd);
  [invalid.assets[1].width, invalid.assets[1].height] = dimensions;
  assert.throws(() => p.validateManifest(invalid), /asset-invalid/);
}
