'use strict';
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const trust = require('../../system-updater/bootstrap-trust');
const keys = Array.from({ length: 3 }, () =>
  crypto.generateKeyPairSync('rsa', { modulusLength: 2048 })
);
const pem = (key) => key.export({ type: 'spki', format: 'pem' });
const sign = (bytes, key) =>
  crypto.sign('RSA-SHA256', bytes, key).toString('base64');
const payload = Buffer.from('{"catalog":"future"}');
let chain = [],
  parent = keys[0];
for (const next of keys.slice(1)) {
  const publicKey = pem(next.publicKey);
  chain.push({
    publicKey,
    signature: sign(trust.delegationBytes(publicKey), parent.privateKey)
  });
  parent = next;
}
const envelope = {
  payload: payload.toString('base64'),
  signature: sign(payload, parent.privateKey),
  keyChain: chain
};
assert.deepEqual(trust.verify(envelope, keys[0].publicKey), payload);
assert.throws(
  () =>
    trust.verify({ ...envelope, keyChain: chain.slice(1) }, keys[0].publicKey),
  /signature/
);
assert.throws(
  () =>
    trust.verify(
      { ...envelope, keyChain: [...chain].reverse() },
      keys[0].publicKey
    ),
  /signature/
);
assert.throws(
  () =>
    trust.verify(
      { ...envelope, keyChain: Array(9).fill(chain[0]) },
      keys[0].publicKey
    ),
  /chain/
);
assert.throws(
  () =>
    trust.verify(
      { ...envelope, signature: sign(payload, keys[0].privateKey) },
      keys[0].publicKey
    ),
  /signature/
);
assert.throws(
  () =>
    trust.verify(
      { ...envelope, payload: Buffer.from('tampered').toString('base64') },
      keys[0].publicKey
    ),
  /signature/
);
assert.deepEqual(
  trust.verify(
    {
      payload: payload.toString('base64'),
      signature: sign(payload, keys[0].privateKey)
    },
    keys[0].publicKey
  ),
  payload
);
console.log(
  'PASS unchanged bootstrap trust follows authenticated rotation chain and rejects substitution'
);
