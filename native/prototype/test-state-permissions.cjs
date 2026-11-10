const a = require('node:assert/strict'),
  fs = require('fs'),
  os = require('os'),
  path = require('path');
const file = path.join(__dirname, '../app/state-permissions.js');
a.ok(fs.existsSync(file), 'runtime must restore state permissions after boot');
const secure = require(file),
  root = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'cytv-mode-')));
try {
  const state = path.join(root, 'state');
  fs.mkdirSync(state);
  for (const name of ['ssap-key.json', 'apps.json']) {
    fs.writeFileSync(path.join(state, name), 'preserved');
    fs.chmodSync(path.join(state, name), 0o775);
  }
  fs.chmodSync(state, 0o775);
  const before = fs.statSync(path.join(state, 'ssap-key.json'));
  a.equal(secure(state), true);
  a.equal(fs.statSync(state).mode & 0o777, 0o770);
  for (const [name, mode] of [
    ['ssap-key.json', 0o640],
    ['apps.json', 0o775]
  ]) {
    a.equal(fs.statSync(path.join(state, name)).mode & 0o777, mode);
    a.equal(fs.readFileSync(path.join(state, name), 'utf8'), 'preserved');
  }
  a.equal(fs.statSync(path.join(state, 'ssap-key.json')).uid, before.uid);
  a.equal(secure(state), true);
  fs.unlinkSync(path.join(state, 'apps.json'));
  a.equal(secure(state), true);
  fs.unlinkSync(path.join(state, 'ssap-key.json'));
  const target = path.join(root, 'outside');
  fs.writeFileSync(target, 'secret');
  fs.chmodSync(target, 0o775);
  fs.symlinkSync(target, path.join(state, 'ssap-key.json'));
  const errors = [];
  a.equal(
    secure(state, (x) => errors.push(x)),
    false
  );
  a.equal(fs.statSync(target).mode & 0o777, 0o775);
  a.ok(errors.length);
  a.ok(!JSON.stringify(errors).includes('secret'));
  fs.unlinkSync(path.join(state, 'ssap-key.json'));
  fs.mkdirSync(path.join(state, 'ssap-key.json'));
  a.equal(secure(state), false);
  fs.symlinkSync(state, path.join(root, 'linked'));
  a.equal(secure(path.join(root, 'linked')), false);
  a.equal(secure(path.join(root, 'missing')), false);
  // Isolate permission denial from the preceding unsafe-file type case.
  fs.rmdirSync(path.join(state, 'ssap-key.json'));
  fs.writeFileSync(path.join(state, 'ssap-key.json'), '{"key":"preserved"}');
  fs.chmodSync(path.join(state, 'ssap-key.json'), 0o775);
  const deniedKey = fs.statSync(path.join(state, 'ssap-key.json'));
  const vm = require('vm'),
    deniedModes = [],
    deniedEvents = [],
    sandbox = {
      module: { exports: {} },
      process,
      Buffer,
      require(name) {
        if (name === './contract-events') return events;
        if (name !== 'fs') return require(name);
        return Object.assign({}, fs, {
          fchmodSync(fd) {
            deniedModes.push(
              fs.fstatSync(fd).isDirectory() ? 'directory' : 'file'
            );
            const e = Error('denied');
            e.code = 'EPERM';
            throw e;
          }
        });
      }
    };
  const context = vm.createContext(sandbox);
  vm.runInContext(
    fs.readFileSync(require.resolve('../app/contract-events'), 'utf8'),
    context
  );
  const events = sandbox.module.exports;
  sandbox.module = { exports: {} };
  vm.runInContext(fs.readFileSync(file, 'utf8'), context);
  fs.chmodSync(state, 0o775);
  a.equal(
    sandbox.module.exports(state, (event) => deniedEvents.push(event)),
    false
  );
  a.deepEqual(deniedModes, ['directory', 'file', 'file']);
  a.ok(
    deniedEvents.some(
      (event) =>
        event.event === 'state-permissions-warning' &&
        event.contract.field === 'directory' &&
        event.contract.decision === 'retain'
    )
  );
  a.ok(
    deniedEvents.some(
      (event) =>
        event.event === 'state-permissions-error' &&
        event.contract.field === 'staging' &&
        event.contract.phase === 'chmod' &&
        event.contract.decision === 'refuse'
    )
  );
  const afterDenied = fs.statSync(path.join(state, 'ssap-key.json'));
  a.equal(afterDenied.ino, deniedKey.ino);
  a.equal(afterDenied.uid, deniedKey.uid);
  a.equal(afterDenied.mode & 0o777, 0o775);
  a.equal(
    fs.readFileSync(path.join(state, 'ssap-key.json'), 'utf8'),
    '{"key":"preserved"}'
  );
  a.deepEqual(fs.readdirSync(state), ['ssap-key.json']);
  a.equal(fs.statSync(state).mode & 0o777, 0o775);

  console.log(
    'PASS: boot modes, content/owner preservation, missing files, unsafe paths'
  );
} finally {
  fs.rmSync(root, { recursive: true, force: true });
}
