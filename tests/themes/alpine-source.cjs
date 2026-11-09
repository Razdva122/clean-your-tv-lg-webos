'use strict';
const assert = require('node:assert/strict'),
  fs = require('node:fs'),
  data = require('../../launcher/theme-data.js');
const { compileSource } = require('../../theme-api/compile.cjs');
(async () => {
  // The published 1.4.4 distribution stays immutable when the author source advances.
  const oldRoot = 'distributions/alpine/1.4.4/',
    descriptor = fs.readFileSync(oldRoot + 'cytv-theme.json'),
    old = JSON.parse(descriptor);
  const oldPack = { descriptor, digest: data.hash(descriptor), files: {} };
  for (const f of [old.rules, ...old.assets, ...old.documents])
    oldPack.files[f.path] = fs.readFileSync(oldRoot + f.path);
  data.verify(oldPack, '99.0.0');
  assert.equal(
    old.assets.find((a) => a.id === 'landscape').sha256,
    '0d38c92bbb35dc31d0cf05a7f2ac9e724e9a046922e52673f32d498dd09d81ff'
  );
  const root = 'themes/alpine/',
    manifest = JSON.parse(fs.readFileSync(root + 'theme.json'));
  const result = await compileSource({
    manifest,
    css: fs.readFileSync(root + 'theme.css', 'utf8'),
    assets: manifest.assets.map((a) => ({
      ...a,
      data: fs.readFileSync(root + a.path)
    })),
    videos: manifest.wallpaperVideo.variants.map((v) => ({
      ...v,
      data: fs.readFileSync(root + v.path)
    })),
    documents: ['LICENSE.txt', 'CREDITS.txt'].map((path) => ({
      path,
      data: fs.readFileSync(root + path)
    })),
    source: old.source,
    minimumHomeVersion: '1.6.0'
  });
  assert.equal(result.manifest.themeVersion, '1.6.0');
  assert(result.manifest.requires.capabilities.includes('weather-v1'));
  assert.deepEqual(result.manifest.layout.weather.formats, [
    'text',
    'current',
    'details',
    'forecast'
  ]);
  assert.equal(
    result.manifest.assets.find((a) => a.id === 'landscape').width,
    3840
  );
  assert.deepEqual(
    result.videos.map((v) => [v.quality, v.width, v.height]),
    [
      ['4k', 3840, 2160],
      ['1080p', 1920, 1080]
    ]
  );
  assert.equal(
    JSON.parse(fs.readFileSync(root + 'wallpaper-preparation.json'))
      .sourceSize[0],
    6000
  );
  console.log(
    'PASS native Alpine UHD/FHD media and immutable published Alpine 1.4.4'
  );
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
