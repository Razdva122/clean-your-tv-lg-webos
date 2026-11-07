const assert = require('node:assert/strict'),
  crypto = require('node:crypto');
const { signFeeds } = require('../../scripts/sign-release-feeds.cjs');
const { privateKey, publicKey } = crypto.generateKeyPairSync('rsa', {
  modulusLength: 2048
});
const rootPolicy = require('../../root-edition/updater/fetch'),
  homePolicy = require('../../updater-service/policy');
const base =
  'https://github.com/Razdva122/clean-your-tv-lg-webos/releases/download/v0.10.9/';
const manifests = {
  root: {
    schema: 1,
    edition: 'root',
    application: 'com.cleanyourtv.root.preview',
    release: 'v0.10.9',
    version: '0.1.9',
    runtime: 1,
    updater: 1,
    profile: 1,
    url: base + 'com.cleanyourtv.root.preview_0.1.9_all.ipk',
    sha256: 'a'.repeat(64),
    size: 123,
    notes: 'Root'
  },
  home: {
    schema: 1,
    release: 'v0.10.9',
    home: '1.3.5',
    helper: '0.6.16',
    url: base + 'com.gathin.tvhome_1.3.5_all.ipk',
    sha256: 'b'.repeat(64),
    notes: 'Home'
  },
  previous: {
    schema: 1,
    release: 'v0.10.9',
    home: '1.3.4',
    helper: '0.6.16',
    url: base + 'com.gathin.tvhome_1.3.4_all.ipk',
    sha256: 'c'.repeat(64),
    notes: 'Rollback'
  }
};
const feeds = signFeeds(manifests, privateKey, publicKey);
assert.deepEqual(
  rootPolicy.verify(feeds['root-update.json'], publicKey),
  manifests.root
);
assert.deepEqual(
  homePolicy.verify(feeds['update.json'], publicKey),
  manifests.home
);
assert.deepEqual(
  homePolicy.verify(feeds['previous-update.json'], publicKey),
  manifests.previous
);
assert.deepEqual(feeds['update.json'].previous, feeds['previous-update.json']);
assert.throws(
  () =>
    signFeeds(
      manifests,
      crypto.generateKeyPairSync('rsa', { modulusLength: 2048 }).privateKey,
      publicKey
    ),
  /invalid-signature/
);
assert.throws(
  () =>
    signFeeds(
      { ...manifests, previous: { ...manifests.previous, helper: '0.6.17' } },
      privateKey,
      publicKey
    ),
  /incompatible-home-rollback/
);
console.log(
  'PASS automatic signing produces both pinned feeds and matching rollback; wrong keys and incompatible rollback stop signing'
);
