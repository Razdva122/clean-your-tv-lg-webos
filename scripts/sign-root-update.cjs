#!/usr/bin/env node
'use strict';
// Explicit local signing only. This command never publishes or searches for keys.
const fs = require('fs'),
  crypto = require('crypto'),
  policy = require('../root-edition/updater/fetch');
const [manifest, keyFile, output] = process.argv.slice(2);
if (!manifest || !keyFile || !output || process.argv.length !== 5)
  throw Error(
    'Usage: sign-root-update.cjs manifest.json private.pem root-update.json'
  );
const bytes = fs.readFileSync(manifest),
  privateKey = fs.readFileSync(keyFile);
const envelope = {
  payload: bytes.toString('base64'),
  signature: crypto.sign('RSA-SHA256', bytes, privateKey).toString('base64')
};
policy.verify(
  envelope,
  fs.readFileSync(__dirname + '/../updater-service/release-public.pem')
);
fs.writeFileSync(output, JSON.stringify(envelope, null, 2) + '\n', {
  flag: 'wx',
  mode: 0o644
});
