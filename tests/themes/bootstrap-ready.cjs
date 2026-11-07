// Both updater owners must wait for the shared UI presentation contract.
'use strict';
const assert = require('node:assert/strict'),
  fs = require('node:fs'),
  vm = require('node:vm'),
  path = require('node:path'),
  os = require('node:os'),
  { createRequire } = require('node:module'),
  { execFileSync } = require('node:child_process');
let staged;
const files = [
  'launcher/profile-bootstrap.js',
  'root-edition/ui/root-profile.js'
];
if (process.env.CYTV_BOOTSTRAP_READY_PATCH) {
  staged = fs.mkdtempSync(path.join(os.tmpdir(), 'cytv-bootstrap-ready-'));
  for (const file of files) {
    fs.mkdirSync(path.dirname(path.join(staged, file)), { recursive: true });
    fs.copyFileSync(file, path.join(staged, file));
  }
  execFileSync('patch', [
    '--batch',
    '-p1',
    '--directory',
    staged,
    '--input',
    path.resolve(process.env.CYTV_BOOTSTRAP_READY_PATCH)
  ]);
}
const localRequire = createRequire(
  path.resolve('tests/system_updates/profile.cjs')
);
const patchedFs = {
  ...fs,
  readFileSync(file, ...args) {
    const relative = path.relative(process.cwd(), path.resolve(String(file)));
    if (staged && files.includes(relative))
      return fs.readFileSync(path.join(staged, relative), ...args);
    return fs.readFileSync(file, ...args);
  }
};
const ctx = {
  require: (name) => (name === 'fs' ? patchedFs : localRequire(name)),
  setTimeout,
  clearTimeout,
  setImmediate,
  Promise,
  console
};
vm.runInNewContext(
  fs
    .readFileSync('tests/system_updates/profile.cjs', 'utf8')
    .split(/\(async\s*\(\s*\)\s*=>\s*\{/)[0] + ';this.fixture=harness;',
  ctx
);
const turn = () => new Promise((resolve) => setImmediate(resolve));
(async () => {
  try {
    for (const edition of ['no-root', 'root']) {
      let h = ctx.fixture(edition);
      await turn();
      let release;
      h.window.HomeUIReady = new Promise((resolve) => (release = resolve));
      h.window.RootLauncherRendered = false;
      h.scripts[0].onload();
      await turn();
      assert.equal(
        h.calls.some((call) => call[0] === 'healthy'),
        false,
        edition + ' cannot report healthy before presented UI'
      );
      assert.equal(
        h.errors.length,
        0,
        'pending presentation must not be treated as a failed render'
      );
      h.window.RootLauncherRendered = true;
      release();
      await turn();
      assert(
        h.calls.some((call) => call[0] === 'healthy'),
        edition +
          ' reports health after presentation and existing inventory checks'
      );
      h = ctx.fixture(edition);
      await turn();
      let reject;
      h.window.HomeUIReady = new Promise((resolve, fail) => (reject = fail));
      h.scripts[0].onload();
      reject(Error('presentation failed'));
      await turn();
      assert(!h.calls.some((call) => call[0] === 'healthy'));
      assert.equal(
        h.errors.length,
        1,
        edition + ' rejected presentation goes to Recovery'
      );
      h = ctx.fixture(edition, { tiles: ['wrong'] });
      await turn();
      h.window.HomeUIReady = Promise.resolve();
      h.window.RootLauncherRendered = true;
      h.scripts[0].onload();
      await turn();
      assert(
        !h.calls.some((call) => call[0] === 'healthy'),
        'waiting cannot weaken exact inventory validation'
      );
      console.log(
        'PASS ' +
          edition +
          ' pending/rejected/invalid UI readiness is fail-closed; healthy follows presented UI'
      );
    }
    const rootFile = path.resolve('root-edition/ui/test-profile.cjs'),
      rootRequire = createRequire(rootFile),
      rootCtx = {
        require: (name) => (name === 'fs' ? patchedFs : rootRequire(name)),
        __dirname: path.dirname(rootFile),
        setTimeout,
        clearTimeout,
        setImmediate,
        Promise,
        console
      };
    const rootSource = fs.readFileSync(rootFile, 'utf8'),
      rootFixture =
        rootSource.slice(
          0,
          rootSource.indexOf('assert.deepStrictEqual(data.validate(profile)')
        ) +
        rootSource.slice(
          rootSource.search(/const tick\s*=/),
          rootSource.search(/\(async\s*\(\s*\)\s*=>\s*\{/)
        );
    vm.runInNewContext(
      rootFixture + ';this.fixture=harness;this.snapshot=profile;',
      rootCtx
    );
    for (const fail of [false, true]) {
      const h = rootCtx.fixture({
        restore: {
          profile: rootCtx.snapshot,
          transaction: 'pending-ui',
          version: '0.0.1',
          phase: 'verifying'
        }
      });
      await turn();
      let release, reject;
      h.window.HomeUIReady = new Promise((resolve, no) => {
        release = resolve;
        reject = no;
      });
      h.scripts[0].onload();
      await turn();
      assert(
        !h.calls.some((call) => call[0] === 'ready' || call[0] === 'confirm')
      );
      if (fail) reject(Error('UI failed'));
      else {
        h.window.RootLauncherRendered = true;
        release();
      }
      await turn();
      assert.equal(
        h.calls.some((call) => call[0] === 'ready'),
        !fail
      );
      assert.equal(
        h.calls.some((call) => call[0] === 'confirm'),
        !fail
      );
      assert.equal(h.errors.length, fail ? 1 : 0);
    }
    console.log(
      'PASS legacy Root ready/confirm receipts wait for presentation and rejection enters Recovery'
    );
  } finally {
    if (staged) fs.rmSync(staged, { recursive: true, force: true });
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
