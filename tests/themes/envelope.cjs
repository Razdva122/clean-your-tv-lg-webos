'use strict';
const assert = require('assert/strict'),
  fs = require('fs'),
  path = require('path');
const data = require('../../launcher/theme-data.js');
assert.equal(data.lanSource, undefined);
assert.equal(data.loadLan, undefined);
assert.throws(
  () => data.source('http://192.168.1.20:8879/123456/package.json'),
  'ordinary installs stay GitHub-only'
);
const entry = require('../../scripts/check-theme-submissions.cjs')
  .loadRegistry()
  .find((e) => e.record.title === 'Channel');
const descriptor = fs.readFileSync(
  path.resolve('showcase', entry.base, 'cytv-theme.json')
);
function envelope() {
  const files = {};
  for (const f of entry.files.filter((f) => f !== 'cytv-theme.json'))
    files[f] = fs
      .readFileSync(path.resolve('showcase', entry.base, f))
      .toString('base64');
  return { schemaVersion: 1, descriptor: descriptor.toString('base64'), files };
}
const p = data.unpackEnvelope(envelope(), '1.5.1');
assert.equal(p.digest, entry.record.descriptorSha256);
assert.equal(p.url, undefined, 'never store LAN address or PIN');
assert.equal(data.verify(p, '1.5.1').manifest.title, 'Channel');
assert.throws(() => data.unpackEnvelope(envelope(), '1.0.0'), /Update Home/);
let e = envelope();
e.files['extra.js'] = 'YQ==';
assert.throws(() => data.unpackEnvelope(e, '1.5.1'));
e = envelope();
e.files[entry.manifest.rules.path] = 'YQ==';
assert.throws(() => data.unpackEnvelope(e, '1.5.1'));
e = envelope();
e.descriptor = '!!!!';
assert.throws(() => data.unpackEnvelope(e, '1.5.1'));
e = envelope();
e.schemaVersion = 2;
assert.throws(() => data.unpackEnvelope(e, '1.5.1'));
e = envelope();
e.files[entry.manifest.rules.path] = 'A'.repeat(200000);
assert.throws(() => data.unpackEnvelope(e, '1.5.1'));
// Retired PC-hosted endpoints must be rejected before opening a connection.
let opened = 0;
global.XMLHttpRequest = class {
  constructor() {
    opened++;
  }
};
(async () => {
  for (const local of [false, undefined, 'lan'])
    await assert.rejects(
      data.request('http://192.168.1.20:8879/123456/package.json', 1024, local),
      /Unsupported theme host/
    );
  assert.equal(opened, 0);
  console.log(
    'PASS receiver envelope integrity and removal of PC-hosted download transport'
  );
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
