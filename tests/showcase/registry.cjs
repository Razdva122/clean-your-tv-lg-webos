'use strict';
const assert = require('node:assert/strict'),
  fs = require('node:fs'),
  os = require('node:os'),
  path = require('node:path');
const {
  validateRecord,
  loadRegistry,
  validateFiles
} = require('../../scripts/check-theme-submissions.cjs');
const fixture = require('./fixture.cjs'),
  root = fs.mkdtempSync(path.join(os.tmpdir(), 'cytv-registry-'));
try {
  const { record: r, base } = fixture(root);
  fixture(root, 'day');
  const cased = fixture(root, 'cased');
  cased.manifest.author.url = 'https://github.com/Owner';
  const rewriteAuthor = () => {
    const descriptor = Buffer.from(JSON.stringify(cased.manifest));
    cased.record.descriptorSha256 =
      require('../../scripts/check-theme-submissions.cjs').hash(descriptor);
    const next = require('../../scripts/check-theme-submissions.cjs').assetBase(
      cased.record
    );
    if (next !== cased.base) {
      fs.renameSync(path.join(root, cased.base), path.join(root, next));
      cased.base = next;
    }
    cased.record.creditsFile = next + 'CREDITS.txt';
    cased.record.previewFiles = [next + 'preview.png'];
    fs.writeFileSync(path.join(root, next, 'cytv-theme.json'), descriptor);
  };
  rewriteAuthor();
  assert.doesNotThrow(
    () => validateFiles(cased.record, root),
    'GitHub owner casing preserves source identity'
  );
  cased.manifest.author.url = 'https://github.com/Attacker';
  rewriteAuthor();
  assert.throws(
    () => validateFiles(cased.record, root),
    /attribution\/source/,
    'a different author remains rejected'
  );
  fs.rmSync(path.join(root, 'registry', 'owner--collection--cased.json'));
  fs.rmSync(path.join(root, cased.base), { recursive: true });

  const fork = {
    ...r,
    upstreamRepository: 'https://github.com/original/themes',
    author: { name: 'Original', sourceProfile: 'https://github.com/original' }
  };
  assert.doesNotThrow(() => validateRecord(fork));
  assert.throws(
    () =>
      validateRecord({
        ...fork,
        upstreamRepository: 'https://example.com/original/themes'
      }),
    /upstream/
  );
  assert.throws(
    () => validateRecord({ ...fork, upstreamRepository: r.sourceRepository }),
    /upstream/
  );
  validateRecord({ ...r, license: 'MIT AND CC-BY-SA-3.0' });
  validateRecord({ ...r, license: 'LicenseRef-Personal-Fan-Theme' });
  assert.throws(
    () => validateRecord({ ...r, license: 'MIT OR unknown' }),
    /license/
  );
  assert.equal(
    loadRegistry(root).length,
    2,
    'distinct themes in a collection retain distinct IDs'
  );
  const orderFile = path.join(root, 'order.json'),
    pinned = [r.id, 'github:owner/collection:day'];
  fs.writeFileSync(orderFile, JSON.stringify(pinned));
  assert.deepEqual(
    loadRegistry(root).map((e) => e.record.id),
    pinned,
    'curated order overrides filename order'
  );
  const newcomer = fixture(root, 'aaa');
  assert.deepEqual(
    loadRegistry(root).map((e) => e.record.id),
    [...pinned, newcomer.record.id],
    'new alphabetically earlier theme appends after existing themes'
  );
  fs.writeFileSync(orderFile, JSON.stringify([...pinned, r.id]));
  assert.throws(
    () => loadRegistry(root),
    /order/i,
    'duplicate ordered IDs are rejected'
  );
  fs.writeFileSync(
    orderFile,
    JSON.stringify([...pinned, 'github:owner/collection:missing'])
  );
  assert.throws(
    () => loadRegistry(root),
    /order/i,
    'unknown ordered IDs are rejected'
  );
  fs.writeFileSync(orderFile, JSON.stringify(pinned));
  for (const change of [
    { title: '<img src=x onerror=alert(1)>' },
    { descriptorUrl: r.descriptorUrl.replace(r.sourceCommit, 'main') },
    { descriptorUrl: r.descriptorUrl.replace('/owner/', '/attacker/') },
    { descriptorUrl: r.descriptorUrl.replace('/night/', '/../') },
    { descriptorUrl: r.descriptorUrl + '?raw=1' },
    { themeApiVersion: 2 },
    { license: 'All rights reserved' },
    { author: { name: 'Owner', sourceProfile: 'https://github.com/attacker' } },
    { creditsFile: '../secrets' },
    { previewFiles: ['https://evil.test/image.png'] },
    { previewFiles: [base + '../evil.png'] },
    { sourceCommit: 'a'.repeat(39) },
    { themeVersion: '01.0.0' },
    { tags: ['trending'] },
    { reviewedAt: '2026-02-30' },
    { approved: true },
    {
      evidence: [
        { kind: 'device', summary: 'test', url: 'javascript:alert(1)' }
      ]
    }
  ])
    assert.throws(
      () => validateRecord({ ...r, ...change }),
      JSON.stringify(change)
    );
  fs.writeFileSync(path.join(root, base, 'CREDITS.txt'), 'tampered');
  assert.throws(() => validateFiles(r, root), /Byte\/hash mismatch/);
  fs.writeFileSync(
    path.join(root, base, 'CREDITS.txt'),
    'Original test image\n'
  );
  fs.writeFileSync(
    path.join(root, 'registry', 'another.json'),
    JSON.stringify(r)
  );
  assert.throws(() => loadRegistry(root), /identity|Duplicate/);
  console.log(
    'Showcase registry: valid local byte hashes, multi-theme identity and 17 hostile records passed'
  );
} finally {
  fs.rmSync(root, { recursive: true, force: true });
}
