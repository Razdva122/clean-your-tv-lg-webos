const assert = require('assert'),
  fs = require('fs'),
  os = require('os'),
  path = require('path');
const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'cytv-update-'));
try {
  const store = require('../../updater-service/storage')(
    path.join(dir, 'state')
  );
  assert.equal(store.read('profile'), null);
  store.write('profile', { schema: 1 });
  assert.deepEqual(store.read('profile'), { schema: 1 });
  assert.equal(
    fs.statSync(path.join(dir, 'state/profile.json')).mode & 0o777,
    0o600
  );
  assert.equal(fs.statSync(path.join(dir, 'state')).mode & 0o777, 0o700);
  assert.equal(fs.statSync(path.join(dir, 'state')).uid, process.getuid());
  const build = fs.readFileSync(
    path.join(__dirname, '../../scripts/build-updater.sh'),
    'utf8'
  );
  assert(!build.includes('fix-updater-data.py'));
  assert(!build.includes('state/.keep'));

  assert.throws(() => store.write('../outside', {}));
  fs.writeFileSync(path.join(dir, 'state/profile.json'), 'bad');
  assert.throws(() => store.read('profile'));
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
console.log('PASS private persistent updater state');
