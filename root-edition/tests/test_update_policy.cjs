'use strict';
const assert = require('assert'),
  crypto = require('crypto');
const policy = require('../updater/fetch');
const keys = crypto.generateKeyPairSync('rsa', { modulusLength: 2048 });
const manifest = {
  schema: 1,
  edition: 'root',
  application: 'com.cleanyourtv.root.preview',
  release: 'v0.1.0',
  version: '0.1.0',
  runtime: 1,
  updater: 1,
  profile: 1,
  url: 'https://github.com/Razdva122/clean-your-tv-lg-webos/releases/download/v0.1.0/com.cleanyourtv.root.preview_0.1.0_all.ipk',
  sha256: 'a'.repeat(64),
  size: 12345,
  notes: 'Root update'
};
function signed(value) {
  const bytes = Buffer.from(JSON.stringify(value));
  return {
    payload: bytes.toString('base64'),
    signature: crypto
      .sign('RSA-SHA256', bytes, keys.privateKey)
      .toString('base64')
  };
}
assert.equal(policy.verify(signed(manifest), keys.publicKey).version, '0.1.0');
for (const [key, value] of [
  ['edition', 'no-root'],
  ['application', 'com.gathin.tvhome'],
  ['runtime', 2],
  ['profile', 2],
  ['size', -1],
  ['size', 34 * 1024 * 1024],
  ['url', 'https://example.com/app.ipk'],
  ['version', '1.2'],
  ['sha256', 'INVALID']
])
  assert.throws(
    () => policy.verify(signed({ ...manifest, [key]: value }), keys.publicKey),
    key
  );
const bad = signed(manifest);
bad.signature = Buffer.alloc(256).toString('base64');
assert.throws(() => policy.verify(bad, keys.publicKey));
assert.equal(policy.compare('0.10.0', '0.9.0'), 1);
assert(policy.allowed(manifest.url));
assert(
  !policy.allowed('https://github.com/else/project/releases/download/app.ipk')
);
assert(
  !policy.allowed(
    'https://user@github.com/Razdva122/clean-your-tv-lg-webos/releases/foo'
  )
);
assert.throws(() =>
  policy.verify({ ...signed(manifest), payload: '!bad' }, keys.publicKey)
);
console.log(
  'PASS Root signed policy rejects wrong edition, contracts, tampering and foreign URLs'
);
