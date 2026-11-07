'use strict';
function pythonCommand() {
  return require('./python_boot').command(require('path').dirname(__dirname));
}

var Service = require('webos-service'),
  execFile = require('child_process').execFile;
var service = new Service('com.cleanyourtv.root.updater.service');
var dispatch = require('./updater/bridge')(function (method, payload) {
  return new Promise(function (resolve, reject) {
    if (process.getuid() !== 0) return reject(Error('root-service-required'));
    execFile(
      pythonCommand(),
      [__dirname + '/run-updater.py', method],
      { timeout: 100000, maxBuffer: 5 * 1024 * 1024 },
      function (error, stdout) {
        try {
          var value = JSON.parse(stdout);
          if (value.returnValue === true) return resolve(value.result);
          reject(Error(value.errorText || 'update-operation-failed'));
        } catch (_) {
          reject(
            Error(
              'Update state unavailable. Open Root Updater Recovery before retrying.'
            )
          );
        }
      }
    ).stdin.end(JSON.stringify(payload));
  });
});
require('./updater/bridge').methods.forEach(function (method) {
  service.register(method, function (message) {
    dispatch(message, method, message.payload || {}).then(
      function (result) {
        message.respond({ returnValue: true, result: result });
      },
      function (error) {
        message.respond({ returnValue: false, errorText: error.message });
      }
    );
  });
});

module.exports.pythonCommand = pythonCommand;
