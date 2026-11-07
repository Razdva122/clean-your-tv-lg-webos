const assert = require('assert'),
  crypto = require('crypto');
const policy = require('../../updater-service/policy');
const keys = crypto.generateKeyPairSync('rsa', { modulusLength: 2048 });
const manifest = {
  schema: 1,
  release: 'v0.8.0',
  home: '1.2.0',
  helper: '0.6.13',
  url: 'https://github.com/Razdva122/clean-your-tv-lg-webos/releases/download/v0.8.0/com.gathin.tvhome_1.2.0_all.ipk',
  sha256: 'a'.repeat(64),
  notes: 'Home update'
};
function envelope(m) {
  const payload = Buffer.from(JSON.stringify(m)).toString('base64');
  return {
    payload,
    signature: crypto
      .sign('RSA-SHA256', Buffer.from(payload, 'base64'), keys.privateKey)
      .toString('base64')
  };
}
const pub = keys.publicKey.export({ type: 'spki', format: 'pem' });
assert.equal(policy.verify(envelope(manifest), pub).home, '1.2.0');
assert.throws(() =>
  policy.verify({ ...envelope(manifest), signature: 'AAAA' }, pub)
);
for (const change of [
  { url: 'http://evil.invalid/a' },
  { url: manifest.url + '?x=1' },
  { helper: '*' },
  { home: '1.2.0; id' },
  { sha256: 'no' },
  { schema: 2 }
])
  assert.throws(() => policy.verify(envelope({ ...manifest, ...change }), pub));
assert.equal(policy.offer(manifest, '1.1.0', '0.6.13'), 'available');
assert.equal(policy.offer(manifest, '1.2.0', '0.6.13'), 'current');
assert.equal(policy.offer(manifest, '1.3.0', '0.6.13'), 'newer-installed');
assert.equal(
  policy.offer(manifest, '1.1.0', '0.6.12'),
  'helper-update-required'
);
console.log('PASS signed update policy');
