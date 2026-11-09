'use strict';
const assert = require('node:assert/strict'),
  fs = require('node:fs'),
  path = require('node:path');
const { compileSource } = require('../../theme-api/compile.cjs'),
  data = require('../../launcher/theme-data.js');
(async () => {
  const directory = path.resolve('themes/craciun'),
    manifest = JSON.parse(fs.readFileSync(path.join(directory, 'theme.json')));
  const read = (name) => fs.readFileSync(path.join(directory, name));
  const compiled = await compileSource({
    manifest,
    css: read('theme.css').toString(),
    assets: manifest.assets.map((a) => ({ ...a, data: read(a.path) })),
    videos: manifest.wallpaperVideo.variants.map((v) => ({
      ...v,
      data: read(v.path)
    })),
    documents: [manifest.license.textPath, manifest.license.creditsPath].map(
      (name) => ({ path: name, data: read(name) })
    ),
    source: {
      repository: 'https://github.com/razdva122/clean-your-tv-lg-webos',
      commit: 'a'.repeat(40)
    },
    minimumHomeVersion: '1.8.0'
  });
  const m = compiled.manifest,
    descriptor = data.encode(JSON.stringify(m)),
    files = {};
  files[m.rules.path] = data.encode(JSON.stringify(compiled.rules) + '\n');
  for (const f of [
    ...compiled.assets,
    ...compiled.documents,
    ...compiled.videos
  ])
    files[f.path] = f.data;
  data.verify({ descriptor, digest: data.hash(descriptor), files }, '1.10.0');
  assert.equal(m.themeVersion, '1.3.0');
  assert.ok(m.requires.capabilities.includes('video-wallpaper-v1'));
  assert.deepEqual(
    m.wallpaperVideo.variants.map((v) => [v.quality, v.width, v.height]),
    [
      ['4k', 3840, 2160],
      ['1080p', 1920, 1080]
    ]
  );
  assert.equal(
    data.hash(read('assets/wallpaper.jpg')),
    '2eef0d73d1c600c12f368a7ded24589a45e5e6dd3f56f68d8894ba9c8b4bce4d',
    'original image fallback is preserved'
  );
  assert.equal(data.metadata(m, descriptor.length).has4k, true);
  assert.equal(data.metadata(m, descriptor.length).hasVideo, false);
  assert.match(read('CREDITS.txt').toString(), /No animation/);
  assert.match(read('CREDITS.txt').toString(), /1672×941/);
  console.log(
    'PASS Craciun 1.3.0: compiled UHD/FHD still video, original fallback, capability, package hashes and attribution'
  );
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
