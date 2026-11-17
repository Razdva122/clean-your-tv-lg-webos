'use strict';
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const { signBootstrap } = require('../../scripts/sign-release-feeds.cjs');
const { verifyEngineRelease } = require('../../scripts/publish-release.cjs');
const { privateKey, publicKey } = crypto.generateKeyPairSync('rsa', {
  modulusLength: 2048
});
const raw = Buffer.from('exact engine archive');
const releases = Object.fromEntries(
  ['root', 'root-720p', 'no-root', 'no-root-720p'].map((variant) => [
    variant,
    {
      edition: variant.replace(/-720p$/, ''),
      release: 'v1.23.0',
      notes: 'Update',
      components: [
        { name: variant.startsWith('root') ? 'root' : 'home', version: '1.0.0' }
      ]
    }
  ])
);
const catalog = {
  schema: 1,
  engine: {
    version: '1.2.11',
    bootstrap: 1,
    minimumPython: '3.9.0',
    minimumNode: 8,
    size: raw.length,
    sha256: crypto.createHash('sha256').update(raw).digest('hex'),
    url: 'https://github.com/Razdva122/clean-your-tv-lg-webos/releases/download/v1.23.0/system-engine_1.2.11.tar.gz'
  },
  releases
};
const envelope = signBootstrap(catalog, releases, privateKey, publicKey);
const build = { tag: 'v1.23.0', system_engine: catalog.engine };
assert.deepEqual(
  verifyEngineRelease(envelope, build, raw, releases, publicKey),
  catalog
);
const next = crypto.generateKeyPairSync('rsa', { modulusLength: 2048 });
const nextPublic = next.publicKey.export({ type: 'spki', format: 'pem' });
const link = {
  publicKey: nextPublic,
  signature: crypto
    .sign(
      'RSA-SHA256',
      require('../../system-updater/bootstrap-trust').delegationBytes(
        nextPublic
      ),
      privateKey
    )
    .toString('base64')
};
const rotated = signBootstrap(catalog, releases, next.privateKey, publicKey, [
  link
]);
assert.deepEqual(
  verifyEngineRelease(rotated, build, raw, releases, publicKey),
  catalog
);
assert.throws(
  () => signBootstrap(catalog, releases, next.privateKey, publicKey),
  /signature/
);
assert.throws(
  () =>
    signBootstrap(
      catalog,
      { ...releases, root: { ...releases.root, notes: 'different' } },
      privateKey,
      publicKey
    ),
  /engine-product/
);
assert.throws(
  () =>
    verifyEngineRelease(
      envelope,
      build,
      Buffer.from('changed'),
      releases,
      publicKey
    ),
  /engine-package/
);
assert.throws(
  () =>
    verifyEngineRelease(
      envelope,
      { ...build, system_engine: { ...catalog.engine, version: '1.2.12' } },
      raw,
      releases,
      publicKey
    ),
  /engine-build/
);
assert.throws(
  () =>
    verifyEngineRelease(
      envelope,
      build,
      raw,
      { ...releases, root: { ...releases.root, notes: 'different' } },
      publicKey
    ),
  /engine-product/
);
console.log(
  'PASS engine signing binds exact four product manifests, build descriptor and archive bytes'
);
