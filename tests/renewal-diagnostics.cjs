'use strict';
const assert = require('node:assert/strict'),
  fs = require('node:fs'),
  os = require('node:os'),
  path = require('node:path'),
  vm = require('node:vm');
const createManager = require('../renewal-service/manager'),
  createHome = require('../renewal-service/home-control');
const { createLocalIO } = require('../renewal-service/local-io');
const { createRenewal } = require('../renewal-service/renewal');
const diagnostics = require('../renewal-service/diagnostics');
function failure(code) {
  return Object.assign(new Error('PRIVATE /path/token=secret'), { code });
}
function manager(overrides) {
  return createManager(
    Object.assign(
      {
        load: () => ({ enabled: false }),
        save() {},
        schedule: async () => ({ returnValue: true }),
        run: async () => ({ status: 'healthy' }),
        now: () => 1000
      },
      overrides
    )
  );
}
function service(overrides) {
  const methods = {},
    adapter = Object.assign(
      {
        readFileSync() {
          throw failure('ENOENT');
        },
        existsSync: () => false,
        mkdirSync() {},
        writeFileSync() {},
        renameSync() {}
      },
      overrides
    );
  function Service() {
    this.register = (name, fn) => {
      methods[name] = fn;
    };
    this.call = (uri, payload, done) =>
      done({ payload: { returnValue: true } });
  }
  vm.runInNewContext(fs.readFileSync('renewal-service/service.js', 'utf8'), {
    __dirname: '/unused',
    setTimeout,
    clearTimeout,
    require(name) {
      if (name === 'fs') return adapter;
      if (name === 'webos-service') return Service;
      if (name === './transport')
        return {
          createRequest: () => () => {
            throw Error('network forbidden');
          }
        };
      if (name === './renewal')
        return {
          createRenewal: () => ({ run: async () => ({ status: 'healthy' }) })
        };
      return require('../renewal-service/' + name.slice(2));
    }
  });
  return (method) =>
    new Promise((resolve) =>
      methods[method]({
        payload: {},
        respond: (r) => resolve(JSON.parse(JSON.stringify(r)))
      })
    );
}
(async () => {
  for (const operation of ['mkdir', 'write', 'rename']) {
    const name = {
      mkdir: 'mkdirSync',
      write: 'writeFileSync',
      rename: 'renameSync'
    }[operation];
    const call = service({
        [name]() {
          throw failure('EACCES');
        }
      }),
      result = await call('enable');
    assert.equal(
      result.version,
      require('../renewal-service/package.json').version
    );
    assert.deepEqual(result.state.diagnostic, {
      component: 'settings',
      operation,
      code: 'EACCES'
    });
  }
  for (const raw of ['{', 'null', '[]', 'true']) {
    const result = await service({ readFileSync: () => raw })('status');
    assert.equal(result.state.error, 'storage-error');
    assert.equal(result.state.diagnostic.operation, 'parse');
  }
  let m = manager({
    load() {
      throw failure('EACCES');
    }
  });
  assert.deepEqual(m.status().diagnostic, {
    component: 'settings',
    operation: 'read',
    code: 'EACCES'
  });
  assert.equal(m.status().error, 'storage-error');
  let failed = true,
    saved;
  m = manager({
    save(s) {
      if (failed) throw failure('ENOSPC');
      saved = JSON.parse(JSON.stringify(s));
    }
  });
  let reply = await m.enable();
  assert.equal(reply.error, 'storage-error');
  assert.deepEqual(reply.diagnostic, {
    component: 'settings',
    operation: 'write',
    code: 'ENOSPC'
  });
  failed = false;
  reply = await m.enable();
  assert.equal(reply.enabled, true);
  assert.equal(reply.diagnostic, undefined);
  assert.equal(
    saved.diagnostic,
    undefined,
    'diagnostics must not be persisted with preferences'
  );
  m = manager({
    schedule: async () => {
      throw failure('PRIVATE_ERROR');
    }
  });
  reply = await m.enable();
  assert.equal(
    reply.error,
    'internal-error',
    'non-storage failures must not pretend to be disk errors'
  );
  assert(!JSON.stringify(reply).includes('PRIVATE'));
  const directory = fs.mkdtempSync(
    path.join(os.tmpdir(), 'renewal-diagnostics-')
  );
  try {
    const stateFile = path.join(directory, 'renewal.json'),
      io = createLocalIO({
        stateFile,
        request() {
          throw Error('no network');
        }
      });
    fs.writeFileSync(stateFile, '{');
    await assert.rejects(io.load(), (error) => {
      assert.deepEqual(error.diagnostic, {
        component: 'renewal',
        operation: 'parse',
        code: 'INVALID_JSON'
      });
      return true;
    });
    const missing = createLocalIO({
      stateFile: path.join(directory, 'missing', 'renewal.json'),
      request() {}
    });
    await assert.rejects(missing.save({}), (error) => {
      assert.deepEqual(error.diagnostic, {
        component: 'renewal',
        operation: 'write',
        code: 'ENOENT'
      });
      return true;
    });
    const worker = createRenewal(
      { now: () => 1, load: io.load },
      { enabled: true }
    );
    assert.deepEqual((await worker.run()).diagnostic, {
      component: 'renewal',
      operation: 'parse',
      code: 'INVALID_JSON'
    });
    let workerSaved;
    const workerManager = manager({
      save: (s) => {
        workerSaved = JSON.parse(JSON.stringify(s));
      },
      run: worker.run
    });
    const workerReply = await workerManager.enable();
    assert.deepEqual(workerReply.diagnostic, {
      component: 'renewal',
      operation: 'parse',
      code: 'INVALID_JSON'
    });
    assert.equal(
      workerSaved.last.diagnostic,
      undefined,
      'worker diagnostics are transient too'
    );
    for (const operation of ['writeFileSync', 'chmodSync', 'renameSync']) {
      const adapter = Object.create(fs);
      adapter[operation] = () => {
        throw failure('EACCES');
      };
      const result = await createHome(adapter, directory)('homeStatus', {});
      assert.equal(result.returnValue, false);
      assert.deepEqual(result.diagnostic, {
        component: 'home',
        operation: {
          writeFileSync: 'write',
          chmodSync: 'chmod',
          renameSync: 'rename'
        }[operation],
        code: 'EACCES'
      });
      assert(!JSON.stringify(result).includes('PRIVATE'));
    }
    let now = 0,
      callback;
    const adapter = Object.create(fs);
    adapter.readFileSync = () => {
      throw failure('EACCES');
    };
    const send = createHome(adapter, directory, {
      now: () => now,
      later: (fn) => {
        callback = fn;
      }
    });
    const pending = send('homeStatus', {});
    now = 5001;
    callback();
    assert.deepEqual((await pending).diagnostic, {
      component: 'home',
      operation: 'read',
      code: 'EACCES'
    });
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
  for (const value of [
    { component: 'PRIVATE', operation: 'read', code: 'EIO' },
    { component: 'home', operation: 'read', code: 'PRIVATE' }
  ])
    assert.equal(diagnostics.sanitize(value), null);
  console.log(
    'PASS bounded storage/Home diagnostics, error classification, recovery, persistence and privacy'
  );
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
