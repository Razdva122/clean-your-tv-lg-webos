'use strict';
// Keep this root of trust independent of replaceable product signing keys.
var crypto = require('crypto');
function fields(value, names) {
  return (
    value &&
    typeof value === 'object' &&
    !Array.isArray(value) &&
    Object.keys(value).sort().join() === names.slice().sort().join()
  );
}
function bytes(value, limit) {
  if (typeof value !== 'string' || value.length > limit)
    throw Error('invalid-bootstrap-envelope');
  var raw = Buffer.from(value, 'base64');
  if (raw.toString('base64') !== value)
    throw Error('invalid-bootstrap-envelope');
  return raw;
}
function signed(raw, signature, key) {
  var verifier = crypto.createVerify('RSA-SHA256');
  verifier.update(raw);
  verifier.end();
  if (!verifier.verify(key, bytes(signature, 2048)))
    throw Error('invalid-engine-signature');
}
function delegationBytes(publicKey) {
  if (
    typeof publicKey !== 'string' ||
    publicKey.length > 4096 ||
    !/^-----BEGIN PUBLIC KEY-----\n[A-Za-z0-9+/=\n]+-----END PUBLIC KEY-----\n$/.test(
      publicKey
    )
  )
    throw Error('invalid-bootstrap-key');
  return Buffer.from('CYTV bootstrap key v1\n' + publicKey, 'utf8');
}
function verify(envelope, rootKey) {
  var withChain =
    envelope && Object.prototype.hasOwnProperty.call(envelope, 'keyChain');
  if (
    !fields(
      envelope,
      withChain
        ? ['payload', 'signature', 'keyChain']
        : ['payload', 'signature']
    )
  )
    throw Error('invalid-bootstrap-envelope');
  var chain = withChain ? envelope.keyChain : [];
  if (!Array.isArray(chain) || chain.length > 8)
    throw Error('invalid-bootstrap-key-chain');
  var key = rootKey,
    seen = {};
  chain.forEach(function (link) {
    if (!fields(link, ['publicKey', 'signature']))
      throw Error('invalid-bootstrap-key-chain');
    var raw = delegationBytes(link.publicKey),
      hash = crypto.createHash('sha256').update(raw).digest('hex');
    if (seen[hash]) throw Error('invalid-bootstrap-key-chain');
    signed(raw, link.signature, key);
    seen[hash] = true;
    key = link.publicKey;
  });
  var payload = bytes(envelope.payload, 262144);
  signed(payload, envelope.signature, key);
  return payload;
}
module.exports = { verify: verify, delegationBytes: delegationBytes };
