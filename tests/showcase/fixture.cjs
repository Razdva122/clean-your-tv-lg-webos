'use strict';
const fs = require('node:fs'),
  path = require('node:path');
const {
  hash,
  assetBase,
  keyFor
} = require('../../scripts/check-theme-submissions.cjs');
module.exports = function fixture(root, slug = 'night', title = 'Classic') {
  fs.mkdirSync(path.join(root, 'registry'), { recursive: true });
  const manifest = structuredClone(
    require('../themes/fixtures/valid-manifest.json')
  );
  const image = Buffer.from(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=',
    'base64'
  );
  const bytes = {
    'rules.json': Buffer.from(JSON.stringify({ schemaVersion: 1, rules: [] })),
    'preview.png': image,
    'LICENSE.txt': Buffer.from('MIT\n'),
    'CREDITS.txt': Buffer.from('Original test image\n')
  };
  manifest.title = title;
  manifest.id = 'github:owner/collection:' + slug;
  manifest.source.repository = 'https://github.com/owner/collection';
  manifest.author = { name: 'Owner', url: 'https://github.com/owner' };
  manifest.assets[0].width = 1;
  manifest.assets[0].height = 1;
  for (const f of [manifest.rules, ...manifest.assets, ...manifest.documents]) {
    f.size = bytes[f.path].length;
    f.sha256 = hash(bytes[f.path]);
  }
  const descriptor = Buffer.from(JSON.stringify(manifest));
  const record = {
    schemaVersion: 1,
    id: manifest.id,
    title: manifest.title,
    description: manifest.description,
    author: { name: 'Owner', sourceProfile: 'https://github.com/owner' },
    sourceRepository: manifest.source.repository,
    sourceCommit: manifest.source.commit,
    descriptorUrl:
      'https://raw.githubusercontent.com/owner/collection/' +
      manifest.source.commit +
      '/' +
      slug +
      '/cytv-theme.json',
    descriptorSha256: hash(descriptor),
    themeVersion: manifest.themeVersion,
    themeApiVersion: 1,
    license: 'MIT',
    creditsFile: '',
    previewFiles: [],
    tags: ['dark'],
    addedAt: '2026-10-28',
    reviewedAt: '2026-10-28',
    evidence: [
      {
        kind: 'browser',
        summary: 'Synthetic fixture only; no device acceptance.'
      }
    ]
  };
  const base = assetBase(record);
  record.creditsFile = base + 'CREDITS.txt';
  record.previewFiles = [base + 'preview.png'];
  fs.mkdirSync(path.join(root, base), { recursive: true });
  for (const [name, value] of Object.entries({
    ...bytes,
    'cytv-theme.json': descriptor
  }))
    fs.writeFileSync(path.join(root, base, name), value);
  fs.writeFileSync(
    path.join(root, 'registry', keyFor(record.id) + '.json'),
    JSON.stringify(record)
  );
  return { record, manifest, base, bytes };
};
