#!/usr/bin/env node
'use strict';

// Data only: never load modules, commands or HTML from a submitted repository.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const policy = require('../launcher/theme-policy.js');
const {
  imageInfo
} = require('../theme-api/compile.cjs');
const licenses = ['MIT', 'Apache-2.0', 'BSD-2-Clause', 'BSD-3-Clause', 'ISC', 'CC0-1.0', 'CC-BY-4.0', 'CC-BY-SA-4.0', 'MIT AND CC-BY-SA-3.0', 'LicenseRef-Personal-Fan-Theme'];
const tags = ['dark', 'light', 'minimal', 'colorful', 'photographic', 'high-contrast'];
const fields = ['schemaVersion', 'id', 'title', 'description', 'author', 'sourceRepository', 'sourceCommit', 'descriptorUrl', 'descriptorSha256', 'themeVersion', 'themeApiVersion', 'license', 'creditsFile', 'previewFiles', 'tags', 'addedAt', 'reviewedAt', 'evidence'];
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
function check(ok, message) {
  if (!ok) throw new Error(message);
}
function exact(o, keys) {
  check(o && typeof o === 'object' && !Array.isArray(o) && Object.keys(o).length === keys.length && keys.every(k => Object.hasOwn(o, k)), 'Unexpected or missing record fields');
}
function text(s, n) {
  check(typeof s === 'string' && s.length > 0 && s.length <= n && !/[<>\u0000-\u001f\u007f]/.test(s), 'Expected bounded plain text');
}
function relative(s) {
  check(typeof s === 'string' && s.length <= 240 && /^[A-Za-z0-9_-]+(?:[./-][A-Za-z0-9_-]+)*$/.test(s) && !s.split('/').some(x => x === '.' || x === '..'), 'Unsafe local path');
  return s;
}
function keyFor(id) {
  return id.slice(7).replace('/', '--').replace(':', '--');
}
function assetBase(r) {
  return 'assets/' + keyFor(r.id) + '/' + r.descriptorSha256 + '/';
}
function validateRecord(r) {
  exact(r, Object.hasOwn(r, 'availability') ? fields.concat('availability') : fields);
  if (r.availability !== undefined) check(['unavailable', 'removed'].includes(r.availability), 'Invalid moderation state');
  check(r.schemaVersion === 1 && r.themeApiVersion === policy.themeApiVersion, 'Unsupported schema/API');
  check(typeof r.id === 'string' && /^github:[a-z0-9][a-z0-9-]*\/[a-z0-9][a-z0-9._-]*:[a-z0-9][a-z0-9-]{0,63}$/.test(r.id), 'Invalid canonical theme ID');
  const repo = r.id.split(':')[1],
    owner = repo.split('/')[0];
  check(r.sourceRepository === 'https://github.com/' + repo, 'Source repository does not match identity');
  check(/^[a-f0-9]{40}$/.test(r.sourceCommit) && /^[a-f0-9]{64}$/.test(r.descriptorSha256), 'Commit/digest must be fixed lowercase hex');
  const rawPrefix = 'https://raw.githubusercontent.com/' + repo + '/';
  check(typeof r.descriptorUrl === 'string' && r.descriptorUrl.startsWith(rawPrefix), 'Descriptor must use the matching commit-pinned raw source');
  const distributionPath = r.descriptorUrl.slice(rawPrefix.length);
  check(/^[a-f0-9]{40}\//.test(distributionPath), 'Distribution commit must be fixed lowercase hex');
  const descriptorPath = relative(distributionPath.slice(41));
  check(descriptorPath.split('/').pop() === 'cytv-theme.json', 'Expected specific theme descriptor');
  exact(r.author, ['name', 'sourceProfile']);
  text(r.author.name, 100);
  check(r.author.sourceProfile === 'https://github.com/' + owner, 'Author profile must match source owner');
  text(r.title, 100);
  text(r.description, 1000);
  check(typeof r.themeVersion === 'string' && /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$/.test(r.themeVersion) && r.themeVersion.length <= 64, 'Invalid semantic version');
  check(licenses.includes(r.license), 'Unsupported redistribution license');
  const base = assetBase(r);
  relative(r.creditsFile);
  check(r.creditsFile.startsWith(base), 'Credits outside reviewed version');
  check(Array.isArray(r.previewFiles) && r.previewFiles.length >= 1 && r.previewFiles.length <= 4 && new Set(r.previewFiles).size === r.previewFiles.length, 'Expected one to four unique previews');
  r.previewFiles.forEach(p => {
    relative(p);
    check(p.startsWith(base) && /\.(png|jpe?g|webp)$/.test(p), 'Preview outside reviewed version');
  });
  check(Array.isArray(r.tags) && r.tags.length <= tags.length && new Set(r.tags).size === r.tags.length && r.tags.every(t => tags.includes(t)), 'Invalid controlled tags');
  for (const field of ['addedAt', 'reviewedAt']) check(typeof r[field] === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(r[field]) && new Date(r[field]).toISOString().slice(0, 10) === r[field], 'Invalid review date');
  check(r.addedAt <= r.reviewedAt, 'Review date precedes addition');
  check(Array.isArray(r.evidence) && r.evidence.length >= 1 && r.evidence.length <= 8, 'Expected review evidence');
  r.evidence.forEach(e => {
    exact(e, e.url === undefined ? ['kind', 'summary'] : ['kind', 'summary', 'url']);
    check(['browser', 'device'].includes(e.kind), 'Invalid evidence kind');
    text(e.summary, 1000);
    if (e.url !== undefined) check(typeof e.url === 'string' && /^https:\/\/github\.com\/[a-z0-9][a-z0-9-]*\/[a-z0-9][a-z0-9._-]*\/(?:issues|pull)\/\d+(?:#(?:issuecomment-\d+|discussion_r\d+))?$/.test(e.url), 'Unsafe evidence URL');
  });
  return r;
}
function readLocal(root, name, max) {
  relative(name);
  const base = fs.realpathSync(root),
    target = path.resolve(base, name);
  check(target.startsWith(base + path.sep), 'Path escaped root');
  // Reject symlinks at every level, including directories inside the review tree.
  let cursor = base;
  for (const part of name.split('/')) {
    cursor = path.join(cursor, part);
    check(!fs.lstatSync(cursor).isSymbolicLink(), 'Symlink in review assets');
  }
  const stat = fs.statSync(target);
  check(stat.isFile() && stat.size <= max, 'Asset missing or too large');
  return fs.readFileSync(target);
}
function validateFiles(r, root) {
  const base = assetBase(r),
    descriptor = readLocal(root, base + 'cytv-theme.json', 65536);
  check(hash(descriptor) === r.descriptorSha256, 'Descriptor digest mismatch');
  const m = policy.validateManifest(JSON.parse(descriptor.toString('utf8')));
  for (const [a, b] of [['id', 'id'], ['title', 'title'], ['description', 'description'], ['themeVersion', 'themeVersion'], ['themeApiVersion', 'themeApiVersion']]) check(r[a] === m[b], 'Registry/manifest mismatch: ' + a);
  check(m.source.repository === r.sourceRepository && m.source.commit === r.sourceCommit && m.author.name === r.author.name && m.author.url === r.author.sourceProfile && m.license.identifier === r.license, 'Manifest attribution/source mismatch');
  check(m.rules.path.endsWith('.json'), 'Rules must use a JSON path');
  m.documents.forEach(d => check(d.path.endsWith('.txt'), 'Public license and credits documents must use .txt paths'));
  m.assets.forEach(a => check({
    'image/png': /\.png$/,
    'image/jpeg': /\.jpe?g$/,
    'image/webp': /\.webp$/
  }[a.mediaType].test(a.path), 'Image extension/media type mismatch'));
  const verified = new Map();
  for (const f of [m.rules, ...m.assets, ...m.documents]) {
    const bytes = readLocal(root, base + f.path, f.size);
    check(bytes.length === f.size && hash(bytes) === f.sha256, 'Byte/hash mismatch: ' + f.path);
    verified.set(f.path, bytes);
  }
  m.assets.forEach(a => {
    const info = imageInfo(verified.get(a.path), a.mediaType, a.id === m.defaults.wallpaperAssetId);
    check(info.width === a.width && info.height === a.height, 'Image dimensions differ from manifest');
  });
  const rules = JSON.parse(verified.get(m.rules.path).toString('utf8'));
  policy.validateRules(rules);
  // The serializer also checks every referenced asset handle exists.
  policy.compileRules(rules, Object.fromEntries(m.assets.map(a => [a.id, 'data:' + a.mediaType + ';base64,' + verified.get(a.path).toString('base64')])));
  check(r.creditsFile === base + m.license.creditsPath, 'Credits must reference hashed manifest document');
  for (const p of r.previewFiles) {
    const a = m.assets.find(a => base + a.path === p);
    check(a && a.width <= 960 && a.height <= 540 && a.size <= 307200, 'Preview must be a bounded hashed manifest image');
    const b = verified.get(a.path);
    check(a.mediaType === 'image/png' && b.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])) || a.mediaType === 'image/jpeg' && b[0] === 255 && b[1] === 216 && b[2] === 255 || a.mediaType === 'image/webp' && b.toString('ascii', 0, 4) === 'RIFF' && b.toString('ascii', 8, 12) === 'WEBP', 'Invalid preview image signature');
  }
  return {
    record: r,
    manifest: m,
    base,
    files: ['cytv-theme.json', m.rules.path, ...m.assets.map(a => a.path), ...m.documents.map(d => d.path)]
  };
}
function loadRegistry(root = path.resolve(__dirname, '../showcase')) {
  const directory = path.join(root, 'registry'),
    seen = new Set(),
    keys = new Set(),
    result = [];
  for (const name of fs.readdirSync(directory).sort()) {
    if (name === '.gitkeep') continue;
    check(/^[a-z0-9][a-z0-9._-]*\.json$/.test(name), 'Unexpected registry file');
    const r = validateRecord(JSON.parse(readLocal(root, 'registry/' + name, 16384).toString('utf8')));
    check(name === keyFor(r.id) + '.json', 'Registry filename must match identity');
    check(!seen.has(r.id) && !keys.has(keyFor(r.id)), 'Duplicate theme identity or page-key collision');
    seen.add(r.id);
    keys.add(keyFor(r.id));
    result.push(validateFiles(r, root));
  }
  const orderPath = path.join(root, 'order.json');
  if (fs.existsSync(orderPath)) {
    const order = JSON.parse(readLocal(root, 'order.json', 16384).toString('utf8'));
    check(Array.isArray(order) && new Set(order).size === order.length && order.every(id => seen.has(id)), 'Invalid catalogue order');
    const rank = new Map(order.map((id, index) => [id, index]));
    result.sort((a, b) => (rank.has(a.record.id) ? rank.get(a.record.id) : order.length) - (rank.has(b.record.id) ? rank.get(b.record.id) : order.length));
  }
  return result;
}
async function verifyRemote(entries, fetcher = globalThis.fetch) {
  // Source commit and distribution commit differ when generated files are committed later.
  // Both are fixed; the descriptor digest binds the exact reviewed distribution bytes.
  // ponytail: 16 MiB per catalog check; shard review jobs when a larger catalog needs it.
  let total = 0;
  for (const entry of entries) {
    const r = validateRecord(entry.record);
    if (r.availability) continue;
    const baseUrl = r.descriptorUrl.slice(0, r.descriptorUrl.lastIndexOf('/') + 1);
    for (const name of entry.files) {
      relative(name);
      const url = name === 'cytv-theme.json' ? r.descriptorUrl : baseUrl + name;
      const expected = name === 'cytv-theme.json' ? r.descriptorSha256 : [entry.manifest.rules, ...entry.manifest.assets, ...entry.manifest.documents].find(f => f.path === name).sha256;
      const ceiling = name === 'cytv-theme.json' ? 65536 : [entry.manifest.rules, ...entry.manifest.assets, ...entry.manifest.documents].find(f => f.path === name).size;
      const response = await fetcher(url, {
        redirect: 'error',
        credentials: 'omit',
        signal: AbortSignal.timeout(15000),
        headers: {
          Accept: 'application/octet-stream'
        }
      });
      check(response.ok && !response.redirected, 'Pinned source unavailable');
      check(!response.headers.get('content-length') || Number(response.headers.get('content-length')) <= ceiling, 'Remote file too large');
      const chunks = [];
      let length = 0;
      for await (const chunk of response.body) {
        length += chunk.length;
        total += chunk.length;
        check(length <= ceiling && total <= 16 * 1024 * 1024, 'Remote download budget exceeded');
        chunks.push(Buffer.from(chunk));
      }
      check(hash(Buffer.concat(chunks)) === expected, 'Pinned remote byte/hash mismatch');
    }
  }
  return entries.length;
}
module.exports = {
  validateRecord,
  validateFiles,
  loadRegistry,
  keyFor,
  assetBase,
  hash,
  licenses,
  tags,
  readLocal,
  verifyRemote
};
if (require.main === module) (async () => {
  try {
    const args = process.argv.slice(2),
      entries = loadRegistry(args.find(a => a !== '--remote'));
    if (args.includes('--remote')) await verifyRemote(entries);
    console.log('Validated ' + entries.length + ' reviewed theme records' + (args.includes('--remote') ? ' and pinned remote bytes' : ''));
  } catch (e) {
    console.error(e.message);
    process.exitCode = 1;
  }
})();
