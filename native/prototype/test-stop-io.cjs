'use strict';
const fs = require('node:fs'),
  path = require('node:path'),
  os = require('node:os'),
  cp = require('node:child_process');
const root = path.resolve(__dirname, '../..'),
  temp = fs.mkdtempSync(path.join(os.tmpdir(), 'cytv-stop-io-'));
const fixture = path.join(temp, 'fixture'),
  privateRoot = path.join(fixture, 'private'),
  stopRoot = path.join(fixture, 'stop'),
  out = path.join(temp, 'runtime');
function run(command, args, options = {}) {
  const r = cp.spawnSync(command, args, {
    cwd: root,
    encoding: 'utf8',
    timeout: 120000,
    ...options
  });
  if (r.error || r.status !== 0)
    throw Error((r.error || 'exit ' + r.status) + '\n' + r.stdout + r.stderr);
  return r.stdout;
}
function id(p) {
  const s = fs.lstatSync(p, { bigint: true });
  return '{' + s.dev + 'ULL,' + s.ino + 'ULL}';
}
function replaceOnce(source, pattern, replacement) {
  if ((source.match(pattern) || []).length !== 1)
    throw Error('expected exactly one fixture declaration: ' + pattern);
  return source.replace(pattern, replacement);
}
try {
  fs.mkdirSync(privateRoot, { recursive: true, mode: 0o700 });
  fs.mkdirSync(path.join(privateRoot, 'journal'), { mode: 0o700 });
  fs.writeFileSync(path.join(privateRoot, 'controller.lock'), '', {
    mode: 0o600
  });
  fs.mkdirSync(stopRoot, { mode: 0o770 });
  fs.chmodSync(stopRoot, 0o770);
  fs.mkdirSync(out);
  const header = path.join(temp, 'binding.h');
  fs.writeFileSync(
    header,
    'static const struct cytv_private_binding host_private={1,' +
      process.getuid() +
      ',' +
      process.getgid() +
      ',' +
      id(privateRoot) +
      ',' +
      id(path.join(privateRoot, 'journal')) +
      ',' +
      id(path.join(privateRoot, 'controller.lock')) +
      '};\n' +
      'static const struct cytv_stop_binding host_stop={1,' +
      fs.lstatSync(stopRoot, { bigint: true }).dev +
      'ULL,' +
      fs.lstatSync(stopRoot, { bigint: true }).ino +
      'ULL,' +
      process.getuid() +
      ',' +
      process.getgid() +
      ',1,{' +
      process.getuid() +
      '}};\n' +
      '#define CYTV_STOP_IO_HOOK_ROOT ' +
      JSON.stringify(fixture) +
      '\n#include ' +
      JSON.stringify(path.join(root, 'tests/fixtures/stop-io-host-hooks.h')) +
      '\n'
  );
  const sources = [
    'native/app/stop-io.c',
    'native/app/private-lease.c',
    'native/app/private-io.c',
    'native/app/stop-fs.c'
  ];
  const flags = ['-std=c11', '-Wall', '-Wextra', '-Werror'];
  const broker = path.join(temp, 'broker'),
    denied = path.join(temp, 'denied');
  run(process.env.CC || 'cc', [
    ...flags,
    '-DCYTV_STOP_IO_TEST_BUILD',
    '-DCYTV_PRIVATE_TEST_BUILD',
    '-DCYTV_STOP_TEST_BUILD',
    '-DCYTV_STOP_IO_BINDING_HEADER=' + JSON.stringify(header),
    '-DCYTV_PRIVATE_TEST_ROOT=' + JSON.stringify(privateRoot),
    '-DCYTV_STOP_TEST_PATH=' + JSON.stringify(stopRoot),
    ...sources,
    '-o',
    broker
  ]);
  run(process.env.CC || 'cc', [...flags, ...sources, '-o', denied]);
  const source = fs.readFileSync(
      path.join(root, 'native/prototype/stop-io.js'),
      'utf8'
    ),
    fixed =
      '/media/developer/apps/usr/palm/applications/com.local.nativehome/stop-io';
  if (source.split(fixed).length !== 2)
    throw Error('expected exactly one fixed executable literal');
  const files = {
    'stop-io.js': source.replace(fixed, broker),
    'denied-io.js': source.replace(fixed, denied),
    'missing-io.js': source,
    'timeout-io.js': source.replace(fixed, broker),
    // Expire this callback only after the native hold is observed. Transport
    // faults above keep the real deadline; a short startup budget is racy.
    'held-timeout-io.js': [
      "'use strict';",
      'var fixtureTimeout = null;',
      'function setTimeout(callback) { return (fixtureTimeout = {callback: callback}); }',
      'function clearTimeout(timer) { if (fixtureTimeout === timer) fixtureTimeout = null; }',
      source.replace(fixed, broker),
      'module.exports._expireTimeoutForTests = function () { if (!fixtureTimeout) throw Error("No pending fixture timeout"); var callback = fixtureTimeout.callback; fixtureTimeout = null; callback(); };'
    ].join('\n'),
    'exhausted-io.js': replaceOnce(
      source.replace(fixed, broker),
      /\bnextID\s*=\s*1\b/g,
      'nextID=4294967296'
    ),
    'runner.js': fs.readFileSync(
      path.join(root, 'tests/fixtures/stop-io-runtime.js'),
      'utf8'
    )
  };
  const protocol =
    process.env.CYTV_STOP_JOURNAL_FIXTURE ||
    (fs.existsSync(path.join(root, 'native/prototype/stop-journal.js'))
      ? path.join(root, 'native/prototype/stop-journal.js')
      : null);
  if (protocol) files['stop-journal.js'] = fs.readFileSync(protocol, 'utf8');
  const compiled = require('../../scripts/compile-helper.cjs').compile(files);
  for (const [name, content] of Object.entries(compiled))
    fs.writeFileSync(path.join(out, name), content);
  const runtimes = [
    process.execPath,
    process.env.NODE010,
    process.env.NODE01025,
    process.env.NODE012
  ].filter(Boolean);
  for (const node of runtimes)
    process.stdout.write(
      run(node, [
        path.join(out, 'runner.js'),
        fixture,
        broker,
        protocol ? 'protocol' : 'standalone'
      ])
    );
} finally {
  fs.rmSync(temp, { recursive: true, force: true });
}
