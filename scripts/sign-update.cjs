#!/usr/bin/env node
'use strict';
// Input manifest and prior envelope are reviewed local files; the private key is
// supplied explicitly and must never be committed or copied into an IPK.
const fs = require('fs'),
  crypto = require('crypto'),
  policy = require('../updater-service/policy');
const [manifest, keyFile, output, previous] = process.argv.slice(2);
if (!manifest || !keyFile || !output)
  throw Error(
    'Usage: sign-update.cjs manifest.json private.pem output.json [previous.json]'
  );
const key = fs.readFileSync(keyFile),
  publicKey = fs.readFileSync(
    __dirname + '/../updater-service/release-public.pem'
  );
const bytes = fs.readFileSync(manifest);
const envelope = {
  payload: bytes.toString('base64'),
  signature: crypto.sign('RSA-SHA256', bytes, key).toString('base64')
};
policy.verify(envelope, publicKey);
if (previous) {
  envelope.previous = JSON.parse(fs.readFileSync(previous));
  policy.verify(envelope.previous, publicKey);
  delete envelope.previous.previous;
}
fs.writeFileSync(output, JSON.stringify(envelope, null, 2) + '\n', {
  flag: 'wx',
  mode: 0o644
});
