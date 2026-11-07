'use strict';
const fs = require('node:fs'),
  os = require('node:os'),
  path = require('node:path'),
  assert = require('node:assert/strict');
const { createLocalIO } = require('../renewal-service/local-io');
(async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'renew-test-'));
  try {
    const tokenFile = path.join(dir, 'token'),
      stateFile = path.join(dir, 'state.json');
    const io = createLocalIO({
      tokenFile,
      stateFile,
      request: () => {
        throw Error('no network');
      }
    });
    assert.deepEqual(await io.load(), {});
    fs.writeFileSync(tokenFile, 'Secret123\n');
    assert.equal(await io.readToken(), 'Secret123');
    fs.writeFileSync(stateFile + '.tmp', 'interrupted write');
    await io.save({
      status: 'healthy',
      checkedAt: 12,
      nextAt: 30,
      failures: 0,
      token: 'must-not-save'
    });
    assert.equal((await io.load()).nextAt, 30);
    assert.ok(!fs.readFileSync(stateFile, 'utf8').includes('must-not-save'));
    assert.equal(fs.statSync(stateFile).mode & 0o777, 0o600);
    assert.equal(fs.readFileSync(tokenFile, 'utf8'), 'Secret123\n');
    fs.writeFileSync(stateFile, 'bad-json');
    await assert.rejects(io.load());
    fs.writeFileSync(tokenFile, 'x'.repeat(4098));
    await assert.rejects(io.readToken());
    console.log(
      'local IO tests passed: private state, corruption, token read-only'
    );
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
