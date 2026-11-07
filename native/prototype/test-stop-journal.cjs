// HOST only: compile through the real Helper compatibility path, then execute
// typed asynchronous I/O fixtures. No native lease, filesystem or TV admission.
const assert = require('node:assert/strict'),
  fs = require('node:fs'),
  os = require('node:os'),
  path = require('node:path'),
  cp = require('node:child_process');
const file = path.resolve('native/prototype/stop-journal.js');
assert(fs.existsSync(file), 'ES5 Stop journal module is required');
const { compile } = require('../../scripts/compile-helper.cjs'),
  directory = fs.mkdtempSync(path.join(os.tmpdir(), 'cytv-stop-journal-'));
try {
  const files = compile({ 'stop-journal.js': fs.readFileSync(file, 'utf8') });
  for (const [name, raw] of Object.entries(files))
    fs.writeFileSync(path.join(directory, name), raw);
  const runtimes = new Set(
    [
      process.execPath,
      process.env.NODE010,
      process.env.NODE01025,
      process.env.NODE012
    ].filter(Boolean)
  );
  for (const runtime of runtimes) {
    const r = cp.spawnSync(
      runtime,
      [path.resolve('tests/fixtures/stop-journal-runtime.js'), directory],
      { encoding: 'utf8', timeout: 30000 }
    );
    assert.equal(r.status, 0, runtime + '\n' + r.stdout + r.stderr);
    assert.match(r.stdout, /PASS Stop journal protocol/);
    console.log(r.stdout.trim());
  }
} finally {
  fs.rmSync(directory, { recursive: true, force: true });
}
