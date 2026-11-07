'use strict';
const assert = require('assert'),
  fs = require('fs'),
  vm = require('vm'),
  path = require('path'),
  crypto = require('crypto');
const pin = '4a71641c8d5536175e404a961624e8656eba30e97b5026f6bd7dc31e4bbeaaea',
  executable = '/var/lib/clean-your-tv-python/' + pin + '/bin/python3.13';
const hash = (b) => crypto.createHash('sha256').update(b).digest('hex');
for (const kind of ['root', 'system']) {
  const state = '/var/lib/clean-your-tv-' + kind + '-updater',
    launcher = state + '/python-launcher',
    receipt = state + '/python-runtime.json',
    inventory = path.dirname(path.dirname(executable)) + '/.cytv-runtime.json';
  let data = {},
    modes = {},
    indirect = new Set();
  const fakefs = {
    lstatSync(name) {
      if (name in data)
        return {
          uid: 0,
          nlink: 1,
          size: data[name].length,
          mode: modes[name] || 0o100600,
          isFile: () => true,
          isDirectory: () => false,
          isSymbolicLink: () => indirect.has(name)
        };
      if ([launcher, receipt, inventory, executable].includes(name)) {
        let e = Error('missing');
        e.code = 'ENOENT';
        throw e;
      }
      return {
        uid: 0,
        nlink: 1,
        mode: 0o40755,
        isFile: () => false,
        isDirectory: () => true,
        isSymbolicLink: () => indirect.has(name)
      };
    },
    readFileSync(name, encoding) {
      return encoding ? data[name].toString() : data[name];
    },
    existsSync(name) {
      return name in data;
    }
  };
  let bindingModule;
  const sandbox = {
    module: { exports: {} },
    exports: {},
    __dirname: state + '/code',
    process: { getuid: () => 0 },
    Buffer,
    Promise,
    require(name) {
      if (name === 'fs') return fakefs;
      if (name === 'webos-service')
        return function () {
          this.register = () => {};
        };
      if (name === 'child_process')
        return {
          execFile() {
            throw Error('unexpected execution');
          }
        };
      if (name === './python_boot') return bindingModule;
      if (name === './updater/bridge') {
        let bridge = () => () => {};
        bridge.methods = [];
        return bridge;
      }
      return require(name);
    }
  };
  const helperSandbox = Object.assign({}, sandbox, { module: { exports: {} } });
  vm.runInNewContext(
    fs.readFileSync(
      path.join(process.cwd(), 'root-edition/python_boot.js'),
      'utf8'
    ),
    helperSandbox
  );
  bindingModule = helperSandbox.module.exports;
  const file = path.join(
    process.cwd(),
    kind === 'root'
      ? 'root-edition/updater/service.js'
      : 'system-updater/service.js'
  );
  vm.runInNewContext(fs.readFileSync(file, 'utf8'), sandbox);
  const select = sandbox.module.exports.pythonCommand;
  assert.equal(typeof select, 'function', 'binding selection must be testable');
  assert.equal(select(), '/usr/bin/python3');
  data[executable] = Buffer.from('verified executable');
  modes[executable] = 0o100755;
  data[inventory] = Buffer.from(
    JSON.stringify({
      schema: 1,
      archive_sha256: pin,
      files: { 'bin/python3.13': hash(data[executable]) }
    })
  );
  data[receipt] = Buffer.from(
    JSON.stringify({
      schema: 1,
      executable,
      archive_sha256: pin,
      inventory_sha256: hash(data[inventory])
    })
  );
  data[launcher] = Buffer.from(
    '#!/bin/sh\nunset PYTHONHOME PYTHONPATH\nexport PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1\nexec ' +
      executable +
      ' "$@"\n'
  );
  modes[launcher] = 0o100700;
  assert.equal(select(), launcher);
  const original = data[launcher];
  data[launcher] = Buffer.from('#!/bin/sh\nexec /tmp/foreign "$@"\n');
  assert.throws(select);
  data[launcher] = original;
  modes[launcher] = 0o100722;
  assert.throws(select);
  modes[launcher] = 0o100700;
  indirect.add('/var/lib');
  assert.throws(select);
  indirect.clear();
  data[executable] = Buffer.from('changed executable');
  assert.throws(select);
  data[executable] = Buffer.from('verified executable');
  const saved = data[receipt];
  delete data[receipt];
  assert.throws(select);
  data[receipt] = saved;
  assert.equal(select(), launcher);
}
console.log('Updater Python binding selection tests passed');
