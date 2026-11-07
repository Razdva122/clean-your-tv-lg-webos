'use strict';
const assert = require('assert/strict'),
  fs = require('fs'),
  path = require('path');
const policy = require('../../launcher/theme-policy.js'),
  data = require('../../launcher/theme-data.js');
function box(type, ...parts) {
  const body = Buffer.concat(parts),
    h = Buffer.alloc(8);
  h.writeUInt32BE(body.length + 8);
  h.write(type, 4);
  return Buffer.concat([h, body]);
}
function sps({
  width = 1920,
  height = 1080,
  profile = 66,
  chroma = 1,
  separate = 0,
  frameOnly = 1,
  scaling = false,
  poc = 0
} = {}) {
  let bits = '';
  const bit = (value) => (bits += value ? '1' : '0'),
    fixed = (value, size) => (bits += value.toString(2).padStart(size, '0')),
    ue = (value) => {
      const code = (value + 1).toString(2);
      bits += '0'.repeat(code.length - 1) + code;
    },
    se = (value) => ue(value <= 0 ? -2 * value : 2 * value - 1);
  fixed(profile, 8);
  fixed(0, 8);
  fixed(40, 8);
  ue(0);
  if (profile === 100) {
    ue(chroma);
    if (chroma === 3) bit(separate);
    ue(0);
    ue(0);
    bit(0);
    bit(scaling);
    if (scaling)
      for (let list = 0; list < (chroma === 3 ? 12 : 8); list++) {
        const present = scaling === 'all' || list === 0;
        bit(present);
        if (present) for (let j = 0; j < (list < 6 ? 16 : 64); j++) se(0);
      }
  }
  ue(0);
  ue(poc);
  if (poc === 0) ue(0);
  else if (poc === 1) {
    bit(0);
    se(0);
    se(0);
    ue(2);
    se(0);
    se(0);
  }
  ue(1);
  bit(0);
  const w = Math.ceil(width / 16),
    h = Math.ceil(height / (16 * (2 - frameOnly))),
    arrayType = separate ? 0 : chroma,
    cropY = (arrayType === 1 ? 2 : 1) * (2 - frameOnly),
    crop = (h * 16 * (2 - frameOnly) - height) / cropY;
  ue(w - 1);
  ue(h - 1);
  bit(frameOnly);
  if (!frameOnly) bit(0);
  bit(1);
  bit(crop !== 0);
  if (crop !== 0) {
    ue(0);
    ue(0);
    ue(0);
    ue(crop);
  }
  bit(0);
  bit(1);
  while (bits.length % 8) bit(0);
  const out = [103];
  let zeros = 0;
  for (let i = 0; i < bits.length; i += 8) {
    const byte = parseInt(bits.slice(i, i + 8), 2);
    if (zeros === 2 && byte <= 3) {
      out.push(3);
      zeros = 0;
    }
    out.push(byte);
    zeros = byte === 0 ? zeros + 1 : 0;
  }
  return Buffer.from(out);
}
function movie({
  width = 1920,
  height = 1080,
  duration = 2000,
  audio = false,
  codec = 'avc1',
  spsOptions = {},
  extraSps = [],
  spsBytes = null
} = {}) {
  const mvhd = Buffer.alloc(100);
  mvhd.writeUInt32BE(1000, 12);
  mvhd.writeUInt32BE(duration, 16);
  const tkhd = Buffer.alloc(84);
  tkhd.writeUInt32BE(width * 65536, 76);
  tkhd.writeUInt32BE(height * 65536, 80);
  const mdhd = Buffer.alloc(24);
  mdhd.writeUInt32BE(1000, 12);
  mdhd.writeUInt32BE(duration, 16);
  const hdlr = Buffer.alloc(24);
  hdlr.write(audio ? 'soun' : 'vide', 8);
  const avc1 = Buffer.alloc(78);
  avc1.writeUInt16BE(width, 24);
  avc1.writeUInt16BE(height, 26);
  const sequence = spsBytes || sps({ width, height, ...spsOptions }),
    sequences = [sequence, ...extraSps],
    nal = (bytes) => {
      const size = Buffer.alloc(2);
      size.writeUInt16BE(bytes.length);
      return Buffer.concat([size, bytes]);
    };
  const avcc = box(
    'avcC',
    Buffer.from([
      1,
      sequence[1],
      sequence[2],
      sequence[3],
      255,
      224 + sequences.length
    ]),
    ...sequences.map(nal),
    Buffer.from([1, 0, 2, 104, 0])
  );
  const sd = Buffer.alloc(8);
  sd.writeUInt32BE(1, 4);
  const stbl = box('stbl', box('stsd', sd, box(codec, avc1, avcc)));
  const mdia = box(
    'mdia',
    box('mdhd', mdhd),
    box('hdlr', hdlr),
    box('minf', stbl)
  );
  return Buffer.concat([
    box('ftyp', Buffer.from('isom\0\0\0\0isomavc1', 'binary')),
    box('moov', box('mvhd', mvhd), box('trak', box('tkhd', tkhd), mdia)),
    box('mdat', Buffer.from([0, 0, 0, 1, 101]))
  ]);
}
const fixture = require('./fixtures/valid-manifest.json');
function manifest() {
  const m = structuredClone(fixture);
  m.defaults.wallpaperAssetId = m.previewAssetId;
  m.requires.capabilities.push('video-wallpaper-v1');
  const bytes = movie();
  m.wallpaperVideo = {
    variants: [
      {
        quality: '1080p',
        path: 'wallpaper.mp4',
        mediaType: 'video/mp4',
        size: bytes.length,
        sha256: data.hash(bytes),
        width: 1920,
        height: 1080
      }
    ]
  };
  return m;
}
assert.equal(
  policy.validateManifest(manifest()).wallpaperVideo.variants[0].quality,
  '1080p'
);
for (const edit of [
  (m) => m.requires.capabilities.pop(),
  (m) => (m.defaults.wallpaperAssetId = null),
  (m) => m.wallpaperVideo.variants.push(m.wallpaperVideo.variants[0]),
  (m) => (m.wallpaperVideo.variants[0].size = 4194305),
  (m) => (m.wallpaperVideo.variants[0].width = 3840),
  (m) => (m.wallpaperVideo.variants[0].path = m.assets[0].path),
  (m) => (m.wallpaperVideo.variants = [])
]) {
  const m = manifest();
  edit(m);
  assert.throws(() => policy.validateManifest(m));
}
const ungated = structuredClone(fixture);
ungated.requires.capabilities.push('video-wallpaper-v1');
assert.throws(() => policy.validateManifest(ungated));
const actualVideo = fs.readFileSync(
  path.join(__dirname, 'fixtures/wallpaper-blue.mp4')
);
assert.deepEqual(data.videoInfo(actualVideo), {
  width: 1920,
  height: 1080,
  duration: 1
});
const spoof = Buffer.from(actualVideo),
  tk = spoof.indexOf(Buffer.from('tkhd')) + 4,
  av =
    spoof.indexOf(Buffer.from('avc1'), spoof.indexOf(Buffer.from('stsd'))) + 4;
spoof.writeUInt32BE(3840 * 65536, tk + 76);
spoof.writeUInt32BE(2160 * 65536, tk + 80);
spoof.writeUInt16BE(3840, av + 24);
spoof.writeUInt16BE(2160, av + 26);
assert.throws(
  () => data.videoInfo(spoof),
  /SPS|dimensions/,
  'FHD compressed stream cannot be advertised as UHD'
);
assert.deepEqual(data.videoInfo(movie()), {
  width: 1920,
  height: 1080,
  duration: 2
});
assert.deepEqual(data.videoInfo(movie({ width: 3840, height: 2160 })), {
  width: 3840,
  height: 2160,
  duration: 2
});
// Dimensions come from every compressed SPS, including chroma-specific cropping and bounded scaling lists.
for (const spsOptions of [
  { profile: 66 },
  { profile: 77 },
  { profile: 100 },
  { profile: 100, scaling: 'all' },
  { profile: 100, chroma: 0 },
  { profile: 100, chroma: 2 },
  { profile: 100, chroma: 3 },
  { profile: 100, chroma: 3, separate: 1, scaling: 'all' },
  { frameOnly: 0 },
  { poc: 1 },
  { poc: 2 }
])
  assert.deepEqual(data.videoInfo(movie({ spsOptions })), {
    width: 1920,
    height: 1080,
    duration: 2
  });
assert.throws(
  () => data.videoInfo(movie({ spsOptions: { width: 3840, height: 2160 } })),
  /SPS/
);
assert.throws(
  () =>
    data.videoInfo(movie({ extraSps: [sps({ width: 3840, height: 2160 })] })),
  /SPS/,
  'every SPS must agree with declared dimensions'
);
assert.throws(
  () => data.videoInfo(movie({ extraSps: [sps({ profile: 77 })] })),
  /SPS/,
  'SPS profile must agree with avcC'
);
for (const spsBytes of [
  Buffer.from([103, 66, 0, 40]),
  Buffer.from([103, 66, 0, 40, 0, 0, 3, 0, 0, 3, 0, 0, 3, 0, 0, 3, 0, 0]),
  Buffer.concat([sps(), Buffer.from([0, 0, 3, 4])]),
  Buffer.alloc(4097, 103)
])
  assert.throws(
    () => data.videoInfo(movie({ spsBytes })),
    /SPS/,
    'reject truncated, oversized, illegal escape and unbounded Golomb SPS'
  );
for (const options of [
  { audio: true },
  { duration: 0 },
  { duration: 61000 },
  { codec: 'hvc1' },
  { width: 1919 }
])
  assert.throws(() => data.videoInfo(movie(options)));
for (const bytes of [
  Buffer.alloc(0),
  movie().subarray(0, 100),
  Buffer.concat([movie(), Buffer.from([1])])
])
  assert.throws(() => data.videoInfo(bytes));
const bad = movie();
bad.writeUInt32BE(0, 0);
assert.throws(() => data.videoInfo(bad));
// Exercise the real external package through byte verification and receiver envelope assembly.
const entry = require('../../scripts/check-theme-submissions.cjs')
  .loadRegistry()
  .find((e) => e.record.title === 'Channel');
const pack = {
  descriptor: new Uint8Array(
    fs.readFileSync(path.resolve('showcase', entry.base, 'cytv-theme.json'))
  ),
  files: {}
};
for (const f of entry.files.filter((f) => f !== 'cytv-theme.json'))
  pack.files[f] = new Uint8Array(
    fs.readFileSync(path.resolve('showcase', entry.base, f))
  );
const m = JSON.parse(data.decode(pack.descriptor));
m.defaults.wallpaperAssetId = m.previewAssetId;
m.requires.capabilities.push('video-wallpaper-v1');
m.wallpaperVideo = manifest().wallpaperVideo;
function descriptor() {
  pack.descriptor = data.encode(JSON.stringify(m));
  pack.digest = data.hash(pack.descriptor);
}
pack.files['wallpaper.mp4'] = movie();
descriptor();
assert.equal(
  data.verify(pack, '99.0.0').manifest.wallpaperVideo.variants.length,
  1
);
const env = {
  schemaVersion: 1,
  descriptor: Buffer.from(pack.descriptor).toString('base64'),
  files: {}
};
for (const key of Object.keys(pack.files))
  env.files[key] = Buffer.from(pack.files[key]).toString('base64');
assert.equal(data.unpackEnvelope(env, '99.0.0').digest, pack.digest);
pack.files['wallpaper.mp4'] = movie({ width: 3840, height: 2160 });
m.wallpaperVideo.variants[0].size = pack.files['wallpaper.mp4'].length;
m.wallpaperVideo.variants[0].sha256 = data.hash(pack.files['wallpaper.mp4']);
descriptor();
assert.throws(() => data.verify(pack, '99.0.0'), /dimensions/);
console.log(
  'PASS video policy, MP4 boundary validation and transport integrity'
);
module.exports = { movie, manifest };
// Media installation creates URLs without touching a native video decoder.
const vm = require('vm');
async function preparation() {
  const entry = require('../../scripts/check-theme-submissions.cjs')
    .loadRegistry()
    .find((e) => e.record.title === 'Channel');
  const m = JSON.parse(
      fs.readFileSync(
        path.resolve('showcase', entry.base, 'cytv-theme.json'),
        'utf8'
      )
    ),
    files = {};
  for (const f of entry.files.filter((f) => f !== 'cytv-theme.json'))
    files[f] = new Uint8Array(
      fs.readFileSync(path.resolve('showcase', entry.base, f))
    );
  m.defaults.wallpaperAssetId = m.previewAssetId;
  m.requires.capabilities.push('video-wallpaper-v1');
  m.wallpaperVideo = {
    variants: ['4k', '1080p'].map((quality) => {
      const width = quality === '4k' ? 3840 : 1920,
        height = quality === '4k' ? 2160 : 1080,
        bytes = movie({ width, height }),
        name = quality + '.mp4';
      files[name] = bytes;
      return {
        quality,
        path: name,
        mediaType: 'video/mp4',
        size: bytes.length,
        sha256: data.hash(bytes),
        width,
        height
      };
    })
  };
  const descriptor = data.encode(JSON.stringify(m)),
    pack = { descriptor, digest: data.hash(descriptor), files };
  let sequence = 0,
    cancel = false,
    mode = '',
    created = {},
    revoked = [],
    videoCount = 0;
  class FakeBlob {
    constructor(parts, options) {
      this.bytes = parts[0];
      this.type = options.type;
    }
  }
  class Image {
    set src(url) {
      const b = created[url],
        info = data.imageInfo(b.bytes, b.type, true);
      this.naturalWidth = info.width;
      this.naturalHeight = info.height;
      Promise.resolve().then(() => this.onload && this.onload());
    }
  }
  const context = {
    JSON,
    Uint8Array,
    ArrayBuffer,
    DataView,
    Int32Array,
    Promise,
    setTimeout,
    clearTimeout,
    ThemePolicy: policy,
    Blob: FakeBlob,
    Image,
    URL: {
      createObjectURL(blob) {
        if (blob.type === 'video/mp4') {
          videoCount++;
          if (mode === 'error' && videoCount === 2) throw Error('URL failed');
          if (mode === 'cancel') cancel = true;
        }
        const url = 'blob:verified-' + ++sequence;
        created[url] = blob;
        return url;
      },
      revokeObjectURL(url) {
        revoked.push(url);
      }
    }
  };
  vm.runInNewContext(
    fs.readFileSync('launcher/theme-data.js', 'utf8'),
    context
  );
  const ready = await context.ThemeData.prepare(pack, '99.0.0');
  assert.deepEqual(Object.keys(ready.videoHandles), ['4k', '1080p']);
  assert.equal(videoCount, 2);
  assert.equal(revoked.length, 0);
  context.ThemeData.dispose(ready.assetHandles, ready.videoHandles);
  assert.equal(revoked.length, Object.keys(created).length);
  for (const failure of ['error', 'cancel']) {
    created = {};
    revoked = [];
    mode = failure;
    cancel = false;
    videoCount = 0;
    await assert.rejects(
      context.ThemeData.prepare(pack, '99.0.0', () => cancel),
      failure === 'error' ? /URL failed/ : /Cancelled/
    );
    assert.equal(
      revoked.length,
      Object.keys(created).length,
      'release every image/video handle on ' + failure
    );
  }
  mode = '';
  cancel = false;
  let leaseDisposals = 0,
    cacheCalls = 0;
  context.WallpaperMediaCache = {
    prepare: async (manifest, received, isCancelled) => {
      cacheCalls++;
      assert.equal(received, pack);
      assert.equal(manifest.id, m.id);
      assert.equal(isCancelled(), false);
      return {
        handles: {
          '4k': 'file:///private/uhd.mp4',
          '1080p': 'file:///private/fhd.mp4'
        },
        dispose() {
          leaseDisposals++;
        }
      };
    }
  };
  const native = await context.ThemeData.prepare(pack, '99.0.0', () => false);
  assert.equal(cacheCalls, 1);
  assert.equal(native.videoHandles['4k'], 'file:///private/uhd.mp4');
  assert(native.videoLease);
  context.ThemeData.dispose(
    native.assetHandles,
    native.videoHandles,
    native.videoLease
  );
  assert.equal(leaseDisposals, 1);
  context.WallpaperMediaCache.prepare = async () => {
    cancel = true;
    return {
      handles: { '4k': 'file:///private/uhd.mp4' },
      dispose() {
        leaseDisposals++;
      }
    };
  };
  await assert.rejects(
    context.ThemeData.prepare(pack, '99.0.0', () => cancel),
    /Cancelled/
  );
  assert.equal(
    leaseDisposals,
    2,
    'cancelled native preparation releases lease'
  );
  console.log(
    'PASS video prepare ownership, no native decoder, failure/cancellation cleanup'
  );
}
preparation().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});

// Large real base64 payloads must reject malformed data without a regex stack overflow.
const largeBytes = Buffer.alloc(9 * 1024 * 1024, 1),
  largeManifest = manifest();
largeManifest.id = 'github:owner/repo:large';
largeManifest.source.repository = 'https://github.com/owner/repo';
largeManifest.wallpaperVideo.variants[0].quality = '4k';
largeManifest.wallpaperVideo.variants[0].width = 3840;
largeManifest.wallpaperVideo.variants[0].height = 2160;
largeManifest.wallpaperVideo.variants[0].size = largeBytes.length;
largeManifest.wallpaperVideo.variants[0].sha256 = data.hash(largeBytes);
const largeDescriptor = Buffer.from(JSON.stringify(largeManifest));
const largeEnvelope = {
  schemaVersion: 1,
  descriptor: largeDescriptor.toString('base64'),
  files: {}
};
for (const f of [
  largeManifest.rules,
  ...largeManifest.assets,
  ...largeManifest.documents
])
  largeEnvelope.files[f.path] = Buffer.alloc(f.size).toString('base64');
largeEnvelope.files[largeManifest.wallpaperVideo.variants[0].path] =
  largeBytes.toString('base64');
assert.throws(
  () => data.unpackEnvelope(largeEnvelope, '99.0.0'),
  (error) =>
    !(error instanceof RangeError) && /hash|MP4|signature/.test(error.message),
  'oversized regex repetition cannot exhaust stack before normal validation'
);
