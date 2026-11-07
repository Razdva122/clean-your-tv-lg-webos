'use strict';
const assert = require('assert/strict'),
  crypto = require('crypto');
const data = require('../../launcher/theme-data.js');
for (const value of ['', 'abc', 'Привет 🎨', 'x'.repeat(100000)])
  assert.equal(
    data.hash(data.encode(value)),
    crypto.createHash('sha256').update(value).digest('hex')
  );
assert.equal(data.decode(data.encode('Привет 🎨')), 'Привет 🎨');
assert.equal(
  data.source('https://github.com/Owner/Repo').repository,
  'https://github.com/owner/repo'
);
assert.equal(
  data.source(
    'https://raw.githubusercontent.com/owner/repo/' +
      'a'.repeat(40) +
      '/dist/cytv-theme.json'
  ).commit,
  'a'.repeat(40)
);
for (const url of [
  'http://github.com/a/b',
  'https://evil.test/a',
  'https://github.com/a/b?token=x',
  'https://raw.githubusercontent.com/a/b/main/cytv-theme.json',
  'https://raw.githubusercontent.com/a/b/' +
    'a'.repeat(40) +
    '/../cytv-theme.json',
  'https://github.com/user:secret@evil/a/b'
])
  assert.throws(() => data.source(url));
assert.throws(() => data.path('../outside'));
assert.throws(() => data.path('assets/%2e/x'));
assert.equal(data.path('assets/icon.png'), 'assets/icon.png');
assert.equal(data.versionAtLeast('1.5.1', '1.5.1'), true);
assert.equal(data.versionAtLeast('1.4.1', '1.5.1'), false);
assert.equal(data.versionAtLeast('1.5.1', '1.5.1-beta'), true);
assert.equal(data.versionAtLeast('1.5.2', '1.5.1-beta'), true);
assert.equal(data.versionAtLeast('1.5.1-beta.2', '1.5.1-beta.10'), false);
console.log(
  'Theme transport: SHA-256 vectors, UTF-8, canonical sources and traversal passed'
);

const fs = require('fs'),
  path = require('path'),
  registry =
    require('../../scripts/check-theme-submissions.cjs').loadRegistry();
const entry = registry.find((e) => e.record.title === 'Channel');
function pack() {
  const p = {
    descriptor: new Uint8Array(
      fs.readFileSync(path.resolve('showcase', entry.base, 'cytv-theme.json'))
    ),
    digest: entry.record.descriptorSha256,
    files: {}
  };
  for (const f of entry.files.filter((f) => f !== 'cytv-theme.json'))
    p.files[f] = new Uint8Array(
      fs.readFileSync(path.resolve('showcase', entry.base, f))
    );
  return p;
}
assert.equal(data.verify(pack(), '1.5.1').manifest.id, entry.record.id);
assert.throws(() => data.verify(pack(), '1.4.1'), /Update Home/);
let p = pack();
p.files[entry.manifest.rules.path][0] ^= 1;
assert.throws(() => data.verify(p, '1.5.1'), /hash mismatch/);
p = pack();
p.files['extra.js'] = new Uint8Array([1]);
assert.throws(() => data.verify(p, '1.5.1'), /Unexpected/);
p = pack();
p.descriptor[0] ^= 1;
assert.throws(() => data.verify(p, '1.5.1'), /Descriptor hash/);
assert.throws(() => data.imageInfo(new Uint8Array([1, 2, 3]), 'image/png'));
console.log(
  'Theme transport: real Channel bytes, wrong hashes, extra files and minimum version passed'
);

function chunk(kind, bytes) {
  const header = Buffer.alloc(8);
  header.write(kind);
  header.writeUInt32LE(bytes.length, 4);
  return Buffer.concat([header, bytes, Buffer.alloc(bytes.length % 2)]);
}
const canvas = Buffer.alloc(10);
canvas.writeUIntLE(1, 4, 3);
canvas.writeUIntLE(1, 7, 3);
const frame = Buffer.from([47, 1, 64, 0, 0]),
  body = Buffer.concat([
    Buffer.from('WEBP'),
    chunk('VP8X', canvas),
    chunk('VP8L', frame),
    chunk('EXIF', Buffer.from([0, 0]))
  ]),
  riff = Buffer.alloc(8);
riff.write('RIFF');
riff.writeUInt32LE(body.length, 4);
const webp = Buffer.concat([riff, body]);
assert.deepEqual(data.imageInfo(webp, 'image/webp'), { width: 2, height: 2 });
canvas.writeUIntLE(2, 4, 3);
const mismatchBody = Buffer.concat([
  Buffer.from('WEBP'),
  chunk('VP8X', canvas),
  chunk('VP8L', frame)
]);
riff.writeUInt32LE(mismatchBody.length, 4);
assert.throws(
  () => data.imageInfo(Buffer.concat([riff, mismatchBody]), 'image/webp'),
  /canvas/
);
console.log('Theme transport: extended WebP canvas/frame bounds passed');

// Native XHR dispatches abort synchronously: preserve the size-limit diagnosis.
const vm = require('vm');
class OversizedXHR {
  open() {}
  send() {
    this.onprogress({ loaded: 65537, lengthComputable: true, total: 65537 });
  }
  abort() {
    this.onabort();
  }
}
const bounded = { Promise, Uint8Array, XMLHttpRequest: OversizedXHR };
vm.runInNewContext(fs.readFileSync('launcher/theme-data.js', 'utf8'), bounded);
assert
  .rejects(
    bounded.ThemeData.request('https://api.github.com/test', 65536, false),
    /size limit/
  )
  .catch((e) => {
    console.error(e);
    process.exitCode = 1;
  });

// The decoder admits UHD only through an explicitly selected wallpaper slot.
const uhdHeader = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aE1sAAAAASUVORK5CYII=',
  'base64'
);
uhdHeader.writeUInt32BE(3840, 16);
uhdHeader.writeUInt32BE(2160, 20);
assert.throws(() => data.imageInfo(uhdHeader, 'image/png'), /dimensions/);
assert.deepEqual(data.imageInfo(uhdHeader, 'image/png', true), {
  width: 3840,
  height: 2160
});
uhdHeader.writeUInt32BE(3841, 16);
assert.throws(() => data.imageInfo(uhdHeader, 'image/png', true), /dimensions/);
