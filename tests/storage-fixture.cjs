'use strict';
// Controller/LS2 tests substitute device I/O. Storage safety itself is exercised
// against real inodes by test_storage_contract.py and observer/Stop tests.
var fs = require('fs'),
  vm = require('vm'),
  path = require('path');
function create(io, prepare) {
  var result =
    prepare ||
    function () {
      return true;
    };
  result.atomicRecord = function (directory, kind, bytes) {
    var name =
      {
        control: 'control.json',
        pid: 'controller.pid',
        logger: 'controller.log',
        'home-preference': 'home-control.json',
        'startup-state': 'startup-state.json'
      }[kind] || kind + '.json';
    if (/-(request|response)$/.test(kind) && io.renameSync) {
      io.writeFileSync(directory + '/.fixture-record', bytes);
      io.renameSync(directory + '/.fixture-record', directory + '/' + name);
    } else io.writeFileSync(directory + '/' + name, bytes);
  };
  result.appendLog = function (directory, line) {
    io.appendFileSync(directory + '/controller.log', line + '\n');
  };
  result.readConfiguration = function (directory, kind) {
    return io.readFileSync(
      directory + '/' + (kind === 'key' ? 'ssap-key.json' : 'apps.json'),
      'utf8'
    );
  };
  result.stopGeneration = function (directory, initialize) {
    var name = directory + '/stop-generation',
      value;
    try {
      value = io.readFileSync(name, 'utf8');
    } catch (e) {
      if (!initialize || e.code !== 'ENOENT') throw e;
      value = 'I00000000000000000000000000000000';
      io.writeFileSync(name, value);
    }
    if (!/^[IS][a-f0-9]{32}$/.test(value)) throw Error('Invalid generation');
    return value;
  };
  result.publishStopGeneration = function (directory) {
    var token = 'S' + require('crypto').randomBytes(16).toString('hex');
    io.writeFileSync(directory + '/stop-generation', token);
    return token;
  };
  return result;
}
function load(file, storage) {
  var module = { exports: {} };
  vm.runInNewContext(fs.readFileSync(file, 'utf8'), {
    module: module,
    exports: module.exports,
    setTimeout: setTimeout,
    require: function (name) {
      return name === './state-permissions'
        ? storage
        : require(
            name.charAt(0) === '.'
              ? path.resolve(path.dirname(file), name)
              : name
          );
    }
  });
  return module.exports;
}
exports.create = create;
exports.homeControl = function (io, file) {
  return load(
    file || path.join(__dirname, '../native/app/home-control.js'),
    create(io)
  );
};
exports.load = load;
