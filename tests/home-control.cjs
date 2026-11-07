const assert = require('node:assert/strict'),
  fs = require('fs'),
  os = require('os'),
  path = require('path');
const create = require('../native/app/home-control');
const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'cytv-home-'));
try {
  fs.writeFileSync(path.join(dir, 'profile.json'), 'keep');
  let applied = [],
    visits = 0;
  let c = create(
    fs,
    dir,
    (v) => applied.push(v),
    () => visits++
  );
  assert.equal(c.enabled(), true);
  c.visit();
  assert.equal(c.enabled(), true);
  assert.equal(visits, 1);
  c.set(false);
  assert.equal(c.enabled(), false);
  assert.deepEqual(applied, [false]);
  c = create(
    fs,
    dir,
    () => {},
    () => {}
  );
  assert.equal(c.enabled(), false);
  c.visit();
  assert.equal(c.enabled(), false);
  assert.equal(fs.readFileSync(path.join(dir, 'profile.json'), 'utf8'), 'keep');
  assert.throws(() => c.set('true'));
  c.set(true);
  assert.equal(
    create(
      fs,
      dir,
      () => {},
      () => {}
    ).enabled(),
    true
  );
  console.log(
    'PASS Home preference persists independently of stock-Home visits and user profile'
  );
} finally {
  fs.rmSync(dir, { recursive: true });
}
