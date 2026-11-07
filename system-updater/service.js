'use strict';
function pythonCommand() {
  return require('./python_boot').command(require('path').dirname(__dirname));
}

var Service = require('webos-service'),
  execFile = require('child_process').execFile;
var SERVICE = 'com.cleanyourtv.system.updater.service';
var launchers = {
  'no-root': 'com.gathin.tvhome',
  root: 'com.cleanyourtv.root.preview'
};
var callers = [
  'com.gathin.tvhome',
  'com.cleanyourtv.root.preview',
  'com.cleanyourtv.updater',
  'com.cleanyourtv.root.updater'
];
var fields = {
  check: ['edition'],
  status: [],
  install: ['edition', 'release', 'profile'],
  restoreProfile: ['edition'],
  healthy: ['edition', 'transaction', 'version'],
  rollback: [],
  reconcile: []
};
function createDispatch(execute) {
  return async function (message, method, payload) {
    var id;
    try {
      id = message.ls2Message.applicationID().split(' ')[0];
    } catch (_) {
      throw Error('caller-not-authorized');
    }
    if (callers.indexOf(id) < 0) throw Error('caller-not-authorized');
    var allowed = fields[method];
    if (
      !allowed ||
      !payload ||
      typeof payload !== 'object' ||
      Array.isArray(payload) ||
      Object.keys(payload).length !== allowed.length ||
      Object.keys(payload).some(function (k) {
        return allowed.indexOf(k) < 0;
      })
    )
      throw Error('invalid-request');
    if (allowed.indexOf('edition') >= 0 && !launchers[payload.edition])
      throw Error('invalid-edition');
    if (
      ['install', 'restoreProfile', 'healthy'].indexOf(method) >= 0 &&
      id !== launchers[payload.edition]
    )
      throw Error('caller-not-authorized');
    if (
      allowed.indexOf('release') >= 0 &&
      (typeof payload.release !== 'string' ||
        !/^v(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})$/.test(
          payload.release
        ))
    )
      throw Error('invalid-release');
    if (
      allowed.indexOf('version') >= 0 &&
      (typeof payload.version !== 'string' ||
        !/^(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})$/.test(
          payload.version
        ))
    )
      throw Error('invalid-version');
    if (
      allowed.indexOf('transaction') >= 0 &&
      (typeof payload.transaction !== 'string' ||
        !/^([a-f0-9]{32})$/.test(payload.transaction))
    )
      throw Error('invalid-transaction');
    if (Buffer.byteLength(JSON.stringify(payload), 'utf8') > 4 * 1024 * 1024)
      throw Error('request-too-large');
    return execute(method, payload);
  };
}
module.exports = {
  createDispatch: createDispatch,
  methods: Object.keys(fields)
};
var service = new Service(SERVICE),
  dispatch = createDispatch(function (method, payload) {
    return new Promise(function (resolve, reject) {
      if (process.getuid() !== 0) return reject(Error('root-service-required'));
      var child = execFile(
        pythonCommand(),
        [__dirname + '/run-system-updater.py', method],
        { timeout: 100000, maxBuffer: 8 * 1024 * 1024 },
        function (error, stdout) {
          try {
            var value = JSON.parse(stdout);
            if (value.returnValue === true) return resolve(value.result);
            reject(Error(value.errorText || 'system-update-failed'));
          } catch (_) {
            reject(
              Error(
                'System update state unavailable. Open Recovery before retrying.'
              )
            );
          }
        }
      );
      child.stdin.end(JSON.stringify(payload));
    });
  });
Object.keys(fields).forEach(function (method) {
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
