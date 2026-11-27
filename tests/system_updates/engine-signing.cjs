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

// The new channel cannot be consumed by an old bootstrap, even with a valid signature.
const { signFeeds } = require('../../scripts/sign-release-feeds.cjs');
const policy = require('../../system-updater/policy');
const engine = require('../../system-updater/engine-policy');
const tileProduct = {};
const base = catalog.engine.url.slice(
  0,
  catalog.engine.url.lastIndexOf('/') + 1
);
for (const variant of Object.keys(releases)) {
  const edition = variant.startsWith('root') ? 'root' : 'no-root';
  const names =
    edition === 'root' ? ['root', 'root-infrastructure'] : ['home', 'helper'];
  const apps = {
    root: 'com.cleanyourtv.root.preview',
    home: 'com.gathin.tvhome',
    helper: 'com.local.nativehome'
  };
  const components = names.map((name) => {
    const common = { name, version: '1.0.0', sha256: 'a'.repeat(64), size: 11 };
    if (name === 'root-infrastructure')
      return {
        ...common,
        kind: 'infrastructure',
        url: base + 'root-infrastructure_1.0.0.tar.gz'
      };
    const hd = variant.endsWith('-720p') && name !== 'helper';
    return {
      ...common,
      application: apps[name],
      kind: 'ipk',
      url:
        base +
        apps[name] +
        '_1.0.0' +
        (hd ? '_720p' : '') +
        (name === 'helper' ? '_arm.ipk' : '_all.ipk')
    };
  });
  tileProduct[variant] = {
    schema: 2,
    supervisor: 2,
    release: 'v1.23.0',
    edition,
    notes: 'Update',
    components
  };
}
const tileCatalog = {
  ...catalog,
  schema: 2,
  releases: tileProduct,
  engine: { ...catalog.engine, bootstrap: 2 }
};
const tileInput = {
  productSchema: 2,
  system: tileProduct,
  bootstrap: tileCatalog
};
const tileFeeds = signFeeds(tileInput, privateKey, publicKey);
assert.deepEqual(
  Object.keys(tileFeeds).sort(),
  [
    'system-bootstrap-v2.json',
    ...Object.keys(releases).map((v) => 'system-update-v2-' + v + '.json')
  ].sort()
);
for (const variant of Object.keys(releases)) {
  const feed = tileFeeds['system-update-v2-' + variant + '.json'];
  assert.deepEqual(policy.verify(feed, publicKey, 2), tileProduct[variant]);
  assert.throws(() => policy.verify(feed, publicKey), /incompatible/);
}
assert.throws(
  () =>
    signBootstrap(
      { ...catalog, releases: tileProduct },
      tileProduct,
      privateKey,
      publicKey
    ),
  /legacy-channel/
);
const tileEnvelope = tileFeeds['system-bootstrap-v2.json'];
assert.deepEqual(engine.verify(tileEnvelope, publicKey, 2), tileCatalog);
assert.throws(() => engine.verify(tileEnvelope, publicKey), /catalog/);
assert.throws(() => engine.verify(envelope, publicKey, 2), /catalog/);
assert.throws(
  () => signFeeds({ ...tileInput, home: {} }, privateKey, publicKey),
  /legacy-feeds-forbidden/
);
const bad = structuredClone(tileInput);
bad.bootstrap.releases.root.components.push({
  ...bad.bootstrap.releases.root.components[0],
  name: 'root-updater'
});
assert.throws(() => signFeeds(bad, privateKey, publicKey), /incomplete/);
console.log(
  'PASS generation 2 signatures and exclusive channel names for all four edition/graphics sets'
);
