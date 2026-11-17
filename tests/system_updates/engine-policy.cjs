'use strict';
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const policy = require('../../system-updater/engine-policy');
const { privateKey, publicKey } = crypto.generateKeyPairSync('rsa', {
  modulusLength: 2048
});
const release = 'v1.23.0';
function catalog() {
  const releases = {};
  for (const variant of ['root', 'root-720p', 'no-root', 'no-root-720p']) {
    const edition = variant.replace(/-720p$/, '');
    releases[variant] = {
      edition,
      release,
      notes: 'Test',
      supervisor: 99,
      components: [
        { name: edition === 'root' ? 'root' : 'home', version: '1.0.0' }
      ]
    };
  }
  return {
    schema: 1,
    engine: {
      version: '1.2.11',
      bootstrap: 1,
      minimumPython: '3.9.0',
      minimumNode: 8,
      sha256: 'a'.repeat(64),
      size: 123,
      url:
        'https://github.com/Razdva122/clean-your-tv-lg-webos/releases/download/' +
        release +
        '/system-engine_1.2.11.tar.gz'
    },
    releases
  };
}
function signed(value) {
  const raw = Buffer.from(JSON.stringify(value));
  return {
    payload: raw.toString('base64'),
    signature: crypto.sign('RSA-SHA256', raw, privateKey).toString('base64')
  };
}
assert.equal(
  policy.verify(signed(catalog()), publicKey).releases.root.supervisor,
  99
);
for (const alter of [
  (c) => (c.engine.url += '?foreign'),
  (c) => (c.engine.bootstrap = 2),
  (c) => (c.engine.size = -1),
  (c) => delete c.releases.root,
  (c) => (c.releases.root.release = 'v9.0.0'),
  (c) => (c.engine.sha256 = 'x'),
  (c) => (c.engine.minimumPython = '3.9'),
  (c) => (c.extra = 'bad')
]) {
  const c = catalog();
  alter(c);
  assert.throws(() => policy.verify(signed(c), publicKey));
}
const bad = signed(catalog());
bad.signature = Buffer.alloc(256).toString('base64');
assert.throws(() => policy.verify(bad, publicKey));
console.log('System engine signed bootstrap policy passed');
