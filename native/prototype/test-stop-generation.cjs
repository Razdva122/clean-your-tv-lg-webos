const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const vm = require('vm');
const secure = require('../app/state-permissions');
const directory = fs.realpathSync(
  fs.mkdtempSync(path.join(os.tmpdir(), 'cytv-generation-'))
);
const filename = path.join(directory, 'stop-generation');
try {
  fs.chmodSync(directory, 0o770);
  assert.throws(() => secure.stopGeneration(directory));
  fs.writeFileSync(path.join(directory, 'blocked'), 'stopped');
  assert.equal(secure.stopGeneration(directory, 'setup'), null);
  assert.equal(fs.existsSync(filename), false);
  fs.unlinkSync(path.join(directory, 'blocked'));
  const initial = secure.stopGeneration(directory, true);
  assert.match(initial, /^I[a-f0-9]{32}$/);
  assert.equal(secure.stopGeneration(directory, true), initial);
  const stopped = secure.publishStopGeneration(directory);
  assert.match(stopped, /^S[a-f0-9]{32}$/);
  assert.notEqual(secure.publishStopGeneration(directory), stopped);
  assert.equal(fs.statSync(filename).mode & 0o777, 0o664);
  // A Stop that publishes after initialization's missing-file check wins.
  fs.unlinkSync(filename);
  const source = fs.readFileSync(
    require.resolve('../app/state-permissions'),
    'utf8'
  );
  const sandbox = {
    module: { exports: {} },
    Buffer,
    process,
    require(name) {
      if (name !== 'fs')
        return require(
          name === './contract-events' ? '../app/contract-events' : name
        );
      return Object.assign({}, fs, {
        linkSync(from, to) {
          const winner = secure.publishStopGeneration(directory);
          fs.linkSync(from, to);
          return winner;
        }
      });
    }
  };
  vm.runInNewContext(source, sandbox);
  assert.match(
    sandbox.module.exports.stopGeneration(directory, true),
    /^S[a-f0-9]{32}$/
  );
  // A publisher prepared before the baseline may finish after another Stop.
  // It must replace that generation with its own distinct cancellation token.
  let intermediate,
    once = false;
  const delayed = {
    module: { exports: {} },
    Buffer,
    process,
    require(name) {
      if (name !== 'fs')
        return require(
          name === './contract-events' ? '../app/contract-events' : name
        );
      return Object.assign({}, fs, {
        renameSync(from, to) {
          if (!once && to === 'stop-generation') {
            once = true;
            intermediate = secure.publishStopGeneration(directory);
          }
          return fs.renameSync(from, to);
        }
      });
    }
  };
  vm.runInNewContext(source, delayed);
  const late = delayed.module.exports.publishStopGeneration(directory);
  assert.notEqual(late, intermediate);
  assert.equal(secure.stopGeneration(directory), late);
  const readOnly = {
    module: { exports: {} },
    Buffer,
    process,
    require(name) {
      if (name === 'fs')
        return Object.assign({}, fs, {
          openSync(name, flags, mode) {
            if (name === 'stop-generation' && (flags & 3) === 2)
              throw Object.assign(Error('write ACL denied'), {
                code: 'EACCES'
              });
            return fs.openSync(name, flags, mode);
          }
        });
      return require(
        name === './contract-events' ? '../app/contract-events' : name
      );
    }
  };
  vm.runInNewContext(source, readOnly);
  assert.throws(() => readOnly.module.exports.stopGeneration(directory));
  assert.equal(
    fs.readFileSync(filename, 'utf8'),
    late,
    'write probe must not mutate a generation'
  );
  for (const fault of ['entropy', 'temporary-write']) {
    secure.requestStop(directory);
    const failing = {
      module: { exports: {} },
      Buffer,
      process,
      require(name) {
        if (name === 'crypto' && fault === 'entropy')
          return {
            randomBytes() {
              throw Error('entropy unavailable');
            }
          };
        if (name === 'fs' && fault === 'temporary-write')
          return Object.assign({}, fs, {
            openSync(name, flags, mode) {
              if (String(name).indexOf('.cytv-record-') === 0)
                throw Error('temporary write unavailable');
              return fs.openSync(name, flags, mode);
            }
          });
        return require(
          name === './contract-events' ? '../app/contract-events' : name
        );
      }
    };
    vm.runInNewContext(source, failing);
    assert.throws(() => failing.module.exports.requestStop(directory));
    assert.equal(
      fs.statSync(filename).size,
      0,
      fault + ' must invalidate the old baseline without randomness'
    );
    assert.throws(() => secure.stopGeneration(directory));
    assert.equal(
      fs.readFileSync(path.join(directory, 'blocked'), 'utf8'),
      'stopped'
    );
    if (fault === 'entropy') {
      // No new allocation is needed to retain an already initialized Stop command.
      assert.equal(
        JSON.parse(fs.readFileSync(path.join(directory, 'control.json'))).cmd,
        'stop'
      );
    }
    secure.publishStopGeneration(directory);
    fs.unlinkSync(filename);
    assert.throws(() =>
      failing.module.exports.publishStopGeneration(directory)
    );
    assert.equal(
      fs.statSync(filename).size,
      0,
      'failed first Stop must prevent fresh initialization'
    );
    assert.throws(() => secure.stopGeneration(directory, 'setup'));
    secure.publishStopGeneration(directory);
  }
  // An explicit Start can replace a fail-closed Stop sentinel with a new
  // cancellation baseline. An interrupted setup must still reject it.
  fs.writeFileSync(filename, '');
  assert.throws(() => secure.stopGeneration(directory, 'setup'));
  assert.match(secure.stopGeneration(directory, 'manual'), /^S[a-f0-9]{32}$/);
  const old = secure.stopGeneration(directory);
  fs.chmodSync(directory, 0o777);
  fs.chmodSync(filename, 0o777);
  assert.throws(() => secure.stopGeneration(directory));
  assert.throws(() => secure.stopGeneration(directory, 'setup'));
  const noEntropy = {
    module: { exports: {} },
    Buffer,
    process,
    require(name) {
      if (name === 'crypto')
        return {
          randomBytes() {
            throw Error('entropy unavailable');
          }
        };
      return require(
        name === './contract-events' ? '../app/contract-events' : name
      );
    }
  };
  vm.runInNewContext(source, noEntropy);
  assert.throws(() =>
    noEntropy.module.exports.stopGeneration(directory, 'install')
  );
  assert.equal(fs.statSync(directory).mode & 0o777, 0o777);
  assert.throws(() => secure.stopGeneration(directory));
  const repaired = secure.stopGeneration(directory, 'install');
  assert.match(repaired, /^S[a-f0-9]{32}$/);
  assert.notEqual(repaired, old, 'never adopt a token from expanded storage');
  assert.equal(fs.statSync(directory).mode & 0o777, 0o770);
  assert.equal(fs.statSync(filename).mode & 0o777, 0o664);
  assert.equal(secure.stopGeneration(directory), repaired);
  assert.notEqual(secure.publishStopGeneration(directory), repaired);
  const beforeBootstrap = secure.stopGeneration(directory);
  fs.chmodSync(directory, 0o777);
  assert.equal(secure(directory), true);
  assert.notEqual(secure.stopGeneration(directory), beforeBootstrap);
  assert.equal(fs.statSync(directory).mode & 0o777, 0o770);

  fs.writeFileSync(filename, '');
  let concurrentStop;
  const racingRepair = {
    module: { exports: {} },
    Buffer,
    process,
    require(name) {
      if (name === 'fs')
        return Object.assign({}, fs, {
          renameSync(from, to) {
            fs.renameSync(from, to);
            if (to === 'stop-generation' && !concurrentStop)
              concurrentStop = secure.publishStopGeneration(directory);
          }
        });
      return require(
        name === './contract-events' ? '../app/contract-events' : name
      );
    }
  };
  vm.runInNewContext(source, racingRepair);
  assert.throws(() =>
    racingRepair.module.exports.stopGeneration(directory, 'manual')
  );
  assert.equal(secure.stopGeneration(directory), concurrentStop);
  fs.chmodSync(directory, 0o777);
  const stopDuringChmod = {
    module: { exports: {} },
    Buffer,
    process,
    require(name) {
      if (name === 'fs')
        return Object.assign({}, fs, {
          fchmodSync(fd, mode) {
            fs.fchmodSync(fd, mode);
            if (mode === 0o770 && fs.fstatSync(fd).isDirectory())
              fs.truncateSync(filename, 0);
          }
        });
      return require(
        name === './contract-events' ? '../app/contract-events' : name
      );
    }
  };
  vm.runInNewContext(source, stopDuringChmod);
  assert.throws(() =>
    stopDuringChmod.module.exports.stopGeneration(directory, 'install')
  );
  assert.equal(fs.statSync(filename).size, 0);
  fs.writeFileSync(filename, 'bad');
  assert.throws(() => secure.stopGeneration(directory));
  assert.throws(() => secure.stopGeneration(directory, true));
  fs.unlinkSync(filename);
  fs.symlinkSync(path.join(directory, 'outside'), filename);
  assert.throws(() => secure.publishStopGeneration(directory));
  assert.throws(() => secure.requestStop(directory));
  assert.equal(
    fs.readFileSync(path.join(directory, 'blocked'), 'utf8'),
    'stopped'
  );
  assert.equal(
    JSON.parse(fs.readFileSync(path.join(directory, 'control.json'))).cmd,
    'stop'
  );
  console.log(
    'PASS: initialization, distinct Stops, racing initialization, malformed and indirect generation'
  );
} finally {
  fs.rmSync(directory, { recursive: true, force: true });
}
