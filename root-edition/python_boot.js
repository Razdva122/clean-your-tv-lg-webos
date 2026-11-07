'use strict';
// No target Python executes until its persisted binding has been checked.
function pythonCommand(state) {
  var fs = require('fs'),
    path = require('path'),
    crypto = require('crypto'),
    launcher = state + '/python-launcher',
    receipt = state + '/python-runtime.json';
  function present(name) {
    try {
      fs.lstatSync(name);
      return true;
    } catch (e) {
      if (e.code === 'ENOENT') return false;
      throw e;
    }
  }
  function owned(name, file) {
    var item = fs.lstatSync(name);
    if (
      item.uid !== 0 ||
      item.mode & 18 ||
      item.isSymbolicLink() ||
      (file ? !item.isFile() || item.nlink !== 1 : !item.isDirectory())
    )
      throw Error('unsafe-python-binding');
    for (var parent = path.dirname(name); ; parent = path.dirname(parent)) {
      item = fs.lstatSync(parent);
      if (
        !item.isDirectory() ||
        item.isSymbolicLink() ||
        item.uid !== 0 ||
        item.mode & 18
      )
        throw Error('unsafe-python-binding');
      if (parent === path.dirname(parent)) break;
    }
    return fs.lstatSync(name);
  }
  if (!present(launcher) && !present(receipt)) return '/usr/bin/python3';
  var pin = '4a71641c8d5536175e404a961624e8656eba30e97b5026f6bd7dc31e4bbeaaea',
    executable = '/var/lib/clean-your-tv-python/' + pin + '/bin/python3.13';
  if (
    (owned(launcher, true).mode & 511) !== 448 ||
    owned(receipt, true).size > 65536
  )
    throw Error('unsafe-python-binding');
  var binding = JSON.parse(fs.readFileSync(receipt, 'utf8'));
  if (
    Object.keys(binding).sort().join(',') !==
      'archive_sha256,executable,inventory_sha256,schema' ||
    binding.schema !== 1 ||
    binding.executable !== executable ||
    binding.archive_sha256 !== pin ||
    !/^[a-f0-9]{64}$/.test(binding.inventory_sha256)
  )
    throw Error('invalid-python-binding');
  if (
    fs.readFileSync(launcher, 'utf8') !==
    '#!/bin/sh\nunset PYTHONHOME PYTHONPATH\nexport PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1\nexec ' +
      executable +
      ' "$@"\n'
  )
    throw Error('invalid-python-launcher');
  var inventoryPath =
    path.dirname(path.dirname(executable)) + '/.cytv-runtime.json';
  if (
    owned(inventoryPath, true).size > 4 * 1024 * 1024 ||
    owned(executable, true).size > 256 * 1024 * 1024
  )
    throw Error('oversized-python-runtime');
  var raw = fs.readFileSync(inventoryPath),
    inventory = JSON.parse(raw);
  if (
    crypto.createHash('sha256').update(raw).digest('hex') !==
      binding.inventory_sha256 ||
    inventory.schema !== 1 ||
    inventory.archive_sha256 !== pin ||
    !inventory.files ||
    crypto
      .createHash('sha256')
      .update(fs.readFileSync(executable))
      .digest('hex') !== inventory.files['bin/python3.13']
  )
    throw Error('changed-python-runtime');
  return launcher;
}

function run(state, driver, args) {
  var path = require('path'),
    executable = pythonCommand(state);
  if (
    !path.isAbsolute(state) ||
    path.normalize(state) !== state ||
    !path.isAbsolute(driver) ||
    path.normalize(driver) !== driver ||
    driver.indexOf(state + '/') !== 0
  )
    throw Error('unsafe-python-binding-driver');
  var result = require('child_process').spawnSync(
    executable,
    [driver].concat(args),
    { stdio: 'inherit' }
  );
  if (result.error) throw result.error;
  if (result.status === null) throw Error('python-binding-child-failed');
  return result.status;
}
module.exports = { command: pythonCommand, run: run };
if (require.main === module) {
  try {
    if (process.argv.length < 5)
      throw Error('invalid-python-binding-arguments');
    process.exit(run(process.argv[2], process.argv[3], process.argv.slice(4)));
  } catch (error) {
    console.error('python-binding: ' + error.message);
    process.exit(1);
  }
}
