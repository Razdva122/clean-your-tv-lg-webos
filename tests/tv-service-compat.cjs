// Packaged Home and Updater services run on the TV's own Node (0.12.2 on webOS 3.x).
// Compile them like Helper and load each service entry point on every available runtime
// (NODE010/NODE01025/NODE012 as in CI); uncompiled async functions failed to load there (#47).
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const cp = require('node:child_process');
const { compile } = require('../scripts/compile-helper.cjs');

function sources(directory, prefix = '') {
  const files = {};
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    if (entry.isFile())
      files[prefix + entry.name] = fs.readFileSync(
        path.join(directory, entry.name),
        'utf8'
      );
  }
  return files;
}
const services = {
  // Same layout as scripts/theme_receiver.py inject() for the No-root Home package.
  'renewal-service': {
    ...sources('renewal-service'),
    ...sources('theme-receiver', 'theme-receiver/'),
    'theme-receiver.js':
      "module.exports = require('./theme-receiver/register');\n"
  },
  'updater-service': {
    ...sources('updater-service'),
    'user-data.js': fs.readFileSync('launcher/user-data.js', 'utf8')
  }
};
const output = fs.mkdtempSync(path.join(os.tmpdir(), 'tv-service-compat-'));
try {
  // Minimal LS2 stand-in: loading must not depend on the TV bus being present.
  const stub = path.join(output, 'node_modules', 'webos-service');
  fs.mkdirSync(stub, { recursive: true });
  fs.writeFileSync(
    path.join(stub, 'index.js'),
    'function Service(){this.activityManager={create:function(){},complete:function(){}};}\n' +
      'Service.prototype.register=function(){return {on:function(){}};};Service.prototype.call=function(){};Service.prototype.subscribe=function(){return {on:function(){}};};\nmodule.exports=Service;\n'
  );
  for (const [name, files] of Object.entries(services)) {
    for (const [file, code] of Object.entries(compile(files))) {
      fs.mkdirSync(path.dirname(path.join(output, name, file)), {
        recursive: true
      });
      fs.writeFileSync(path.join(output, name, file), code);
    }
  }
  for (const runtime of new Set(
    [
      process.execPath,
      process.env.NODE010,
      process.env.NODE01025,
      process.env.NODE012
    ].filter(Boolean)
  )) {
    for (const name of Object.keys(services)) {
      const dir = path.join(output, name);
      const result = cp.spawnSync(
        runtime,
        [
          '-e',
          "require('./service.js');console.log('LOADED');process.exit(0);"
        ],
        {
          cwd: dir,
          encoding: 'utf8',
          timeout: 30000,
          env: { ...process.env, NODE_PATH: path.join(output, 'node_modules') }
        }
      );
      assert.equal(
        result.status,
        0,
        runtime + ' ' + name + '\n' + result.stdout + result.stderr
      );
      assert.match(result.stdout, /LOADED/, runtime + ' ' + name);
      if (name === 'updater-service') {
        const transport = cp.spawnSync(
          runtime,
          [path.resolve('tests/fixtures/tv-service-runtime.js'), dir],
          { encoding: 'utf8', timeout: 30000 }
        );
        assert.equal(
          transport.status,
          0,
          runtime +
            ' updater operations\n' +
            transport.stdout +
            transport.stderr
        );
        assert.match(transport.stdout, /PASS updater transport/);
      }
    }
  }
  console.log(
    'PASS compiled Home and Updater services load on ' +
      [
        process.version,
        process.env.NODE010 && 'NODE010',
        process.env.NODE01025 && 'NODE01025',
        process.env.NODE012 && 'NODE012'
      ]
        .filter(Boolean)
        .join(', ')
  );
} finally {
  fs.rmSync(output, { recursive: true, force: true });
}
