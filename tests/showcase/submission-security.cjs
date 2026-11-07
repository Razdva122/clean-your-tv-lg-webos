'use strict';
const assert = require('node:assert/strict'),
  fs = require('node:fs'),
  os = require('node:os'),
  path = require('node:path');
const {
    validateFiles,
    readLocal
  } = require('../../scripts/check-theme-submissions.cjs'),
  fixture = require('./fixture.cjs');
const root = fs.mkdtempSync(path.join(os.tmpdir(), 'cytv-security-'));
try {
  const { record, base } = fixture(root);
  const target = path.join(root, base, 'preview.png'),
    original = fs.readFileSync(target);
  fs.unlinkSync(target);
  fs.symlinkSync(path.join(root, base, 'LICENSE.txt'), target);
  assert.throws(() => validateFiles(record, root), /Symlink/);
  fs.unlinkSync(target);
  fs.writeFileSync(target, original);
  for (const name of [
    '../outside',
    'assets/%2e%2e/secret',
    'assets/a\\b',
    '/etc/passwd',
    'assets/a?x',
    'assets/a#x'
  ])
    assert.throws(() => readLocal(root, name, 100));
  fs.writeFileSync(
    path.join(root, 'malicious.cjs'),
    'throw new Error("author code executed")'
  );
  validateFiles(record, root); // An extra repository script is never imported or run.
  const descriptor = path.join(root, base, 'cytv-theme.json');
  fs.appendFileSync(descriptor, ' ');
  assert.throws(
    () => validateFiles(record, root),
    /Descriptor digest mismatch/
  );
  console.log(
    'Showcase submission security: traversal, symlinks, descriptor tampering and data-only validation passed'
  );
} finally {
  fs.rmSync(root, { recursive: true, force: true });
}
