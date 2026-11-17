'use strict';
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { signBootstrap } = require('./sign-release-feeds.cjs');
const enginePolicy = require('../system-updater/engine-policy');
const systemPolicy = require('../system-updater/policy');

function signSystemCandidate(folder, key, publicKey, chain = []) {
  const read = (name, limit = 64 * 1024 * 1024) => {
    if (!/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(name))
      throw Error('Invalid candidate asset name');
    const file = path.join(folder, name);
    const info = fs.lstatSync(file);
    if (!info.isFile() || info.nlink !== 1 || info.size > limit)
      throw Error('Invalid candidate asset');
    return fs.readFileSync(file);
  };
  const digest = (raw) => crypto.createHash('sha256').update(raw).digest('hex');
  const meta = JSON.parse(read('PROVENANCE.json', 65536));
  if (
    meta.schema !== 1 ||
    Object.hasOwn(meta, 'preliminary') ||
    Object.hasOwn(meta, 'direct_tv') ||
    !/^v\d{1,4}\.\d{1,4}\.\d{1,4}$/.test(meta.release) ||
    meta.release !== 'v' + meta.versions?.release ||
    !Number.isSafeInteger(meta.run_id) ||
    meta.run_id <= 0 ||
    !Number.isSafeInteger(meta.attempt) ||
    meta.attempt <= 0 ||
    !/^[a-f0-9]{40}$/.test(meta.source) ||
    !/^[a-f0-9]{64}$/.test(meta.artifact?.sha256) ||
    !Number.isSafeInteger(meta.artifact.id) ||
    meta.artifact.id <= 0 ||
    !Number.isSafeInteger(meta.artifact.size) ||
    meta.artifact.size <= 0
  )
    throw Error('Invalid system candidate provenance');

  const used = new Set(['PROVENANCE.json']);
  function verified(name, expected, size, limit) {
    const contents = read(name, limit);
    const hash = digest(contents);
    if (
      meta.files?.[name] !== hash ||
      (expected !== undefined && expected !== hash) ||
      (size !== undefined && size !== contents.length)
    ) {
      throw Error('Candidate asset hash or size mismatch');
    }
    used.add(name);
    return contents;
  }

  const catalog = enginePolicy.validate(
    JSON.parse(
      verified('system-bootstrap-manifest.json', undefined, undefined, 393216)
    )
  );
  const releases = JSON.parse(
    verified('system-manifests.json', undefined, undefined, 393216)
  );
  const notes =
    'Unpublished System QA only; source ' +
    meta.source +
    '; build ' +
    meta.run_id +
    ':' +
    meta.attempt +
    '; artifact ' +
    meta.artifact.sha256 +
    '.';
  for (const manifest of Object.values(catalog.releases)) {
    systemPolicy.validate(manifest);
    if (manifest.release !== meta.release || manifest.notes !== notes)
      throw Error('Candidate provenance differs from manifest');
    for (const item of manifest.components) {
      const version =
        { 'root-infrastructure': 'root', 'root-updater': 'updater' }[
          item.name
        ] || item.name;
      if (item.version !== meta.versions[version])
        throw Error('Candidate component version mismatch');
      verified(item.url.split('/').pop(), item.sha256, item.size);
    }
  }
  verified(
    catalog.engine.url.split('/').pop(),
    catalog.engine.sha256,
    catalog.engine.size
  );
  if (
    fs.readdirSync(folder).sort().join('\n') !== [...used].sort().join('\n') ||
    Object.keys(meta.files).sort().join('\n') !==
      [...used]
        .filter((item) => item !== 'PROVENANCE.json')
        .sort()
        .join('\n')
  ) {
    throw Error('Unexpected candidate asset inventory');
  }

  const envelope = signBootstrap(catalog, releases, key, publicKey, chain);
  fs.writeFileSync(
    path.join(folder, 'system-bootstrap-v1.json'),
    JSON.stringify(envelope, null, 2) + '\n',
    { flag: 'wx', mode: 0o600 }
  );
  return envelope;
}

module.exports = { signSystemCandidate };
if (require.main === module) {
  const key =
    process.env.BOOTSTRAP_SIGNING_PRIVATE_KEY ||
    process.env.UPDATE_SIGNING_PRIVATE_KEY;
  delete process.env.BOOTSTRAP_SIGNING_PRIVATE_KEY;
  delete process.env.UPDATE_SIGNING_PRIVATE_KEY;
  try {
    if (process.argv.length !== 3 || !key)
      throw Error('Missing candidate signing inputs');
    signSystemCandidate(
      process.argv[2],
      key,
      fs.readFileSync(
        path.join(__dirname, '../system-updater/bootstrap-public.pem')
      ),
      JSON.parse(process.env.BOOTSTRAP_SIGNING_KEY_CHAIN || '[]')
    );
    console.log('Verified and signed the unpublished System QA catalog.');
  } catch (_) {
    console.error('System candidate signing refused.');
    process.exitCode = 1;
  }
}
