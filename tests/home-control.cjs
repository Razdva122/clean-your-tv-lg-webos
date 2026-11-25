const assert = require('node:assert/strict'),
  fs = require('fs'),
  os = require('os'),
  path = require('path');
const create = require('../native/app/home-control');
const dir = fs.realpathSync(
  fs.mkdtempSync(path.join(os.tmpdir(), 'cytv-home-'))
);
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
  fs.symlinkSync(
    path.join(dir, 'profile.json'),
    path.join(dir, 'home-control.json.tmp')
  );
  c.set(false);
  assert.equal(fs.readFileSync(path.join(dir, 'profile.json'), 'utf8'), 'keep');
  assert.equal(c.enabled(), false);
  assert.deepEqual(applied, [false]);
  fs.chmodSync(dir, 0o777);
  fs.chmodSync(path.join(dir, 'home-control.json'), 0o777);
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
  for (const value of [null, [], { enabled: 'false' }, { enabled: 1 }]) {
    const bytes = JSON.stringify(value);
    fs.writeFileSync(path.join(dir, 'home-control.json'), bytes);
    fs.chmodSync(path.join(dir, 'home-control.json'), 0o777);
    assert.throws(() =>
      create(
        fs,
        dir,
        () => {},
        () => {}
      )
    );
    assert.equal(
      fs.readFileSync(path.join(dir, 'home-control.json'), 'utf8'),
      bytes
    );
  }
  // Stay on input at power-on shares the record, defaults off and is written
  // only while on, so the original record shape and older readers are unchanged.
  fs.writeFileSync(path.join(dir, 'home-control.json'), '{"enabled":true}');
  applied = [];
  c = create(
    fs,
    dir,
    (v) => applied.push(v),
    () => {}
  );
  assert.equal(c.keepSource(), false);
  assert.throws(() => c.setKeepSource('true'));
  assert.deepEqual(c.setKeepSource(true), { keepSource: true });
  assert.deepEqual(applied, []);
  assert.equal(
    fs.readFileSync(path.join(dir, 'home-control.json'), 'utf8'),
    '{"enabled":true,"keepSource":true}'
  );
  c.set(false);
  c = create(
    fs,
    dir,
    () => {},
    () => {}
  );
  assert.equal(c.enabled(), false);
  assert.equal(c.keepSource(), true);
  c.setKeepSource(false);
  assert.equal(
    fs.readFileSync(path.join(dir, 'home-control.json'), 'utf8'),
    '{"enabled":false}'
  );
  // The long Back shortcut defaults on for old records and persists independently.
  assert.equal(c.longBackHome(), true);
  assert.throws(() => c.setLongBackHome('false'));
  c.setLongBackHome(false);
  c.setKeepSource(true);
  c.set(true);
  c = create(
    fs,
    dir,
    () => {},
    () => {}
  );
  assert.equal(c.longBackHome(), false);
  assert.equal(c.keepSource(), true);
  assert.equal(c.enabled(), true);
  c.setLongBackHome(true);
  assert.equal(
    fs.readFileSync(path.join(dir, 'home-control.json'), 'utf8'),
    '{"enabled":true,"keepSource":true}'
  );
  for (const value of [
    { keepSource: 'true' },
    { keepSource: 1 },
    { longBackHome: 'false' }
  ]) {
    fs.writeFileSync(
      path.join(dir, 'home-control.json'),
      JSON.stringify(value)
    );
    assert.throws(() =>
      create(
        fs,
        dir,
        () => {},
        () => {}
      )
    );
  }
  console.log(
    'PASS Home preference persists independently of stock-Home visits and user profile'
  );
} finally {
  fs.rmSync(dir, { recursive: true });
}
