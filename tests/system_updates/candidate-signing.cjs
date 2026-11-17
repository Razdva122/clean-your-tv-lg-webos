'use strict';
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {
  signSystemCandidate
} = require('../../scripts/sign-system-candidate.cjs');
const { verify } = require('../../system-updater/engine-policy');
const { privateKey, publicKey } = crypto.generateKeyPairSync('rsa', {
  modulusLength: 2048
});
const release = 'v1.23.0';
const base =
  'https://github.com/Razdva122/clean-your-tv-lg-webos/releases/download/' +
  release +
  '/';
const provenance = {
  schema: 1,
  release,
  source: 'a'.repeat(40),
  run_id: 123,
  attempt: 2,
  versions: {
    release: '1.23.0',
    home: '1.20.1',
    helper: '0.9.0',
    root: '0.21.1',
    updater: '0.6.1'
  },
  artifact: { id: 1234, size: 10, sha256: 'b'.repeat(64) },
  files: {}
};
const area = fs.mkdtempSync(
  path.join(os.tmpdir(), 'system-candidate-signing-')
);
const sha = (data) => crypto.createHash('sha256').update(data).digest('hex');
function write(name, data) {
  const raw = Buffer.isBuffer(data) ? data : Buffer.from(JSON.stringify(data));
  fs.writeFileSync(path.join(area, name), raw);
  provenance.files[name] = sha(raw);
  return { url: base + name, sha256: sha(raw), size: raw.length };
}
function saveProvenance() {
  fs.writeFileSync(
    path.join(area, 'PROVENANCE.json'),
    JSON.stringify(provenance)
  );
}
function component(name, application, version, suffix) {
  const kind = application ? 'ipk' : 'infrastructure';
  const file = application
    ? application + '_' + version + suffix + '_all.ipk'
    : 'root-infrastructure_' + version + suffix + '.tar.gz';
  return {
    name,
    version,
    kind,
    ...(application ? { application } : {}),
    ...write(file, Buffer.from(file))
  };
}
const notes =
  'Unpublished System QA only; source ' +
  provenance.source +
  '; build 123:2; artifact ' +
  provenance.artifact.sha256 +
  '.';
try {
  const releases = {};
  for (const suffix of ['', '-720p']) {
    for (const edition of ['root', 'no-root']) {
      const isRoot = edition === 'root';
      const appSuffix = suffix ? '_720p' : '';
      releases[edition + suffix] = {
        schema: 1,
        edition,
        release,
        notes,
        supervisor: 2,
        minimumSupervisorVersion: isRoot ? '1.2.10' : '1.2.11',
        components: isRoot
          ? [
              component(
                'root',
                'com.cleanyourtv.root.preview',
                '0.21.1',
                appSuffix
              ),
              component(
                'root-updater',
                'com.cleanyourtv.root.updater',
                '0.6.1',
                ''
              ),
              component('root-infrastructure', null, '0.21.1', appSuffix)
            ]
          : [
              component('home', 'com.gathin.tvhome', '1.20.1', appSuffix),
              component('helper', 'com.local.nativehome', '0.9.0', ''),
              component('updater', 'com.cleanyourtv.updater', '0.6.1', '')
            ]
      };
    }
  }
  const file = 'system-engine_1.2.11.tar.gz';
  const engine = {
    version: '1.2.11',
    bootstrap: 1,
    minimumNode: 8,
    minimumPython: '3.9.0',
    ...write(file, Buffer.from('exact engine'))
  };
  const catalog = { schema: 1, engine, releases };
  write('system-manifests.json', releases);
  write('system-bootstrap-manifest.json', catalog);
  saveProvenance();
  fs.writeFileSync(path.join(area, file), 'changed');
  assert.throws(
    () => signSystemCandidate(area, privateKey, publicKey),
    /asset/
  );
  assert.equal(
    fs.existsSync(path.join(area, 'system-bootstrap-v1.json')),
    false
  );
  write(file, Buffer.from('exact engine'));
  saveProvenance();
  provenance.preliminary = true;
  saveProvenance();
  assert.throws(
    () => signSystemCandidate(area, privateKey, publicKey),
    /provenance/
  );
  delete provenance.preliminary;
  saveProvenance();
  const envelope = signSystemCandidate(area, privateKey, publicKey);
  assert.deepEqual(verify(envelope, publicKey), catalog);
  assert.throws(() => signSystemCandidate(area, privateKey, publicKey));
} finally {
  fs.rmSync(area, { recursive: true, force: true });
}
console.log('PASS exact QA catalog signing and candidate provenance refusals');
