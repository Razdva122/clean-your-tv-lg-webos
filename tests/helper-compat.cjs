// The build must load real Helper dependencies on the runtime from issue #47.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const cp = require('node:child_process');
const acorn = require('acorn');
const {compile} = require('../scripts/compile-helper.cjs');

function sources(directory, prefix = '') {
  const files = {};
  for (const entry of fs.readdirSync(directory, {withFileTypes: true})) {
    const name = prefix + entry.name;
    if (entry.isDirectory() && entry.name !== 'state') Object.assign(files, sources(path.join(directory, entry.name), name + '/'));
    else if (entry.isFile() && /\.(js|json)$/.test(name)) files[name] = fs.readFileSync(path.join(directory, entry.name), 'utf8');
  }
  return files;
}
const output = fs.mkdtempSync(path.join(os.tmpdir(), 'helper-compat-'));
try {
  const files = compile(sources('native/app'));
  const service = compile({...sources('native/service'), 'state-permissions.js': fs.readFileSync('native/app/state-permissions.js', 'utf8')});
  for (const [name, code] of Object.entries(service)) files['service/' + name] = code;
  for (const [name, code] of Object.entries(files)) {
    if (name.endsWith('.js')) acorn.parse(code, {ecmaVersion: 5});
    fs.mkdirSync(path.dirname(path.join(output, name)), {recursive: true});
    fs.writeFileSync(path.join(output, name), code);
  }
  cp.execFileSync('openssl', ['req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
    '-subj', '/CN=localhost', '-keyout', path.join(output, 'test-key.pem'),
    '-out', path.join(output, 'test-cert.pem')], {stdio: 'pipe'});
  for (const runtime of new Set([process.execPath, process.env.NODE010, process.env.NODE012].filter(Boolean))) {
    const result = cp.spawnSync(runtime, [path.resolve('tests/helper-runtime.js'), output], {encoding: 'utf8', timeout: 30000});
    assert.equal(result.status, 0, runtime + '\n' + result.stdout + result.stderr);
    assert.match(result.stdout, /PASS Helper runtime/);
    console.log(result.stdout.trim());
  }
  cp.execFileSync(process.execPath, ['--test', 'tests/controller-watchdog.cjs'], {env: {...process.env, HELPER_CONTROLLER_ROOT: output}, stdio: 'pipe'});
  console.log('PASS compiled Helper watchdog recovery and stop regressions');
} finally {
  fs.rmSync(output, {recursive: true, force: true});
}
