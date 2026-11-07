const assert = require('node:assert/strict'),
  fs = require('node:fs'),
  os = require('node:os'),
  path = require('node:path');
assert(
  fs.existsSync('scripts/lib/update-permissions.cjs'),
  'permission installer required'
);
const setup = require('../../scripts/lib/update-permissions.cjs');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'cytv-perms-'));
let refreshes = 0;
const opts = {
  prefix: tmp,
  refresh: () => {
    refreshes++;
  },
  variant: 'lab'
};
try {
  const plan = setup.plan(opts);
  for (const f of plan.files)
    fs.mkdirSync(path.dirname(tmp + f.path), { recursive: true });
  setup.apply(opts);
  assert.equal(refreshes, 1);
  for (const f of plan.files)
    assert.equal(fs.readFileSync(tmp + f.path, 'utf8'), f.content);
  setup.apply(opts);
  assert.equal(refreshes, 2);
  const first = tmp + plan.files[0].path;
  fs.writeFileSync(first, 'foreign');
  assert.throws(() => setup.remove(opts), /changed/);
  assert(fs.existsSync(tmp + plan.files[2].path));
  fs.writeFileSync(first, plan.files[0].content);
  setup.remove(opts);
  for (const f of plan.files) assert(!fs.existsSync(tmp + f.path));
  fs.writeFileSync(first, 'existing');
  assert.throws(() => setup.apply(opts), /collision/);
  assert.equal(fs.readFileSync(first, 'utf8'), 'existing');
  fs.unlinkSync(first);
  fs.symlinkSync('/tmp', first);
  assert.throws(() => setup.apply(opts), /collision/);
  fs.unlinkSync(first);
  assert.throws(
    () =>
      setup.apply({
        ...opts,
        refresh: () => {
          throw Error('refresh failed');
        }
      }),
    /refresh failed/
  );
  assert(fs.existsSync(tmp + plan.files[2].path));
  setup.remove(opts);
  const legacy = JSON.parse(JSON.stringify(plan));
  for (const f of legacy.files) {
    f.content = f.content.replace(
      'com.cleanyourtv.updaterlab.service*',
      'com.cleanyourtv.updaterlab.service'
    );
    f.sha256 = require('crypto')
      .createHash('sha256')
      .update(f.content)
      .digest('hex');
    fs.writeFileSync(tmp + f.path, f.content);
  }
  fs.writeFileSync(
    tmp +
      '/var/luna-service2-dev/com.cleanyourtv.updaterlab.permissions.receipt.json',
    JSON.stringify({ schema: 1, files: legacy.files }) + '\n'
  );
  setup.remove(opts);
  for (const f of legacy.files) assert(!fs.existsSync(tmp + f.path));
  for (const exactService of [false, true]) {
    const prior = JSON.parse(JSON.stringify(plan));
    for (const f of prior.files) {
      let v = JSON.parse(f.content);
      delete v['com.cleanyourtv.updaterlab.renewalActivity'];
      delete v['com.cleanyourtv.updatetest.renewal*'];
      f.content = JSON.stringify(v, null, 2) + '\n';
      if (exactService)
        f.content = f.content.replace(
          'com.cleanyourtv.updaterlab.service*',
          'com.cleanyourtv.updaterlab.service'
        );
      f.sha256 = require('crypto')
        .createHash('sha256')
        .update(f.content)
        .digest('hex');
      fs.writeFileSync(tmp + f.path, f.content);
    }
    fs.writeFileSync(
      tmp +
        '/var/luna-service2-dev/com.cleanyourtv.updaterlab.permissions.receipt.json',
      JSON.stringify({ schema: 1, files: prior.files }) + '\n'
    );
    setup.remove(opts);
    for (const f of prior.files) assert(!fs.existsSync(tmp + f.path));
  }
  assert(!JSON.stringify(plan).includes('com.gathin.tvhome'));
  assert(!JSON.stringify(plan).includes('com.local.nativehome'));
  console.log(
    'PASS scoped permission apply/remove, collisions, symlinks, changed files and refresh failure'
  );
} finally {
  fs.rmSync(tmp, { recursive: true, force: true });
}
