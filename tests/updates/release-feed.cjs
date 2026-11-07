const assert = require('node:assert/strict'),
  crypto = require('node:crypto');
const {
  verifyRootRelease,
  verifyHomeRelease
} = require('../../scripts/publish-release.cjs');
const { privateKey, publicKey } = crypto.generateKeyPairSync('rsa', {
  modulusLength: 2048
});
const bytes = Buffer.from('release package');
const manifest = {
  schema: 1,
  edition: 'root',
  application: 'com.cleanyourtv.root.preview',
  release: 'v0.10.5',
  version: '0.1.6',
  runtime: 1,
  updater: 1,
  profile: 1,
  url: 'https://github.com/Razdva122/clean-your-tv-lg-webos/releases/download/v0.10.5/com.cleanyourtv.root.preview_0.1.6_all.ipk',
  sha256: crypto.createHash('sha256').update(bytes).digest('hex'),
  size: bytes.length,
  notes: 'Updates and recovery'
};
const payload = Buffer.from(JSON.stringify(manifest));
const feed = {
  payload: payload.toString('base64'),
  signature: crypto.sign('RSA-SHA256', payload, privateKey).toString('base64')
};
const build = { tag: 'v0.10.6', versions: { root: '0.1.6' } };
assert.equal(
  verifyRootRelease(feed, build, bytes, publicKey).version,
  '0.1.6',
  'unchanged Root feed may carry forward to a newer installer release'
);
assert.throws(
  () =>
    verifyRootRelease(
      feed,
      { ...build, versions: { root: '0.1.7' } },
      bytes,
      publicKey
    ),
  /stale-root-feed/
);
assert.throws(
  () =>
    verifyRootRelease(feed, build, Buffer.from('different package'), publicKey),
  /root-package-mismatch/
);
assert.throws(
  () =>
    verifyRootRelease(
      { ...feed, signature: Buffer.alloc(256).toString('base64') },
      build,
      bytes,
      publicKey
    ),
  /invalid-signature/
);
assert.throws(
  () => verifyRootRelease(feed, { tag: build.tag }, bytes, publicKey),
  /release-root-version-missing/
);
console.log(
  'PASS release publication rejects stale Root feeds, wrong package bytes, invalid signatures and missing version metadata'
);

const home = {
  schema: 1,
  release: 'v0.10.8',
  home: '1.3.3',
  helper: '0.6.16',
  url: 'https://github.com/Razdva122/clean-your-tv-lg-webos/releases/download/v0.10.8/com.gathin.tvhome_1.3.3_all.ipk',
  sha256: manifest.sha256,
  notes: 'Home updates'
};
function sign(m) {
  const b = Buffer.from(JSON.stringify(m));
  return {
    payload: b.toString('base64'),
    signature: crypto.sign('RSA-SHA256', b, privateKey).toString('base64')
  };
}
const priorHome = {
  ...home,
  home: '1.3.2',
  url: home.url.replace('1.3.3', '1.3.2')
};
const homeFeed = { ...sign(home), previous: sign(priorHome) },
  homeBuild = { versions: { home: '1.3.3', helper: '0.6.16' } };
assert.equal(
  verifyHomeRelease(homeFeed, homeBuild, bytes, publicKey).home,
  '1.3.3'
);
assert.throws(
  () =>
    verifyHomeRelease(
      homeFeed,
      { versions: { home: '1.3.4', helper: '0.6.16' } },
      bytes,
      publicKey
    ),
  /stale-home-feed/
);
assert.throws(
  () =>
    verifyHomeRelease(
      homeFeed,
      { versions: { home: '1.3.3', helper: '0.6.17' } },
      bytes,
      publicKey
    ),
  /helper-feed-mismatch/
);
assert.throws(
  () => verifyHomeRelease(homeFeed, homeBuild, Buffer.from('wrong'), publicKey),
  /home-package-mismatch/
);
console.log(
  'PASS No-root publication rejects outdated Home versions, wrong Helper requirements and package hashes'
);
assert.throws(
  () =>
    verifyHomeRelease(
      { ...homeFeed, previous: sign({ ...priorHome, helper: '0.6.15' }) },
      homeBuild,
      bytes,
      publicKey
    ),
  /incompatible-home-rollback/
);
