'use strict';
var ROOT = 'com.cleanyourtv.root.preview',
  RECOVERY = 'com.cleanyourtv.root.updater';
var fields = {
  check: [],
  status: [],
  install: ['version', 'profile'],
  restoreProfile: [],
  ready: ['transaction', 'version'],
  confirm: ['transaction', 'version'],
  reconcile: [],
  rollback: []
};
module.exports = function (execute) {
  return async function (message, method, payload) {
    var id;
    try {
      id = message.ls2Message.applicationID().split(' ')[0];
    } catch (_) {
      throw Error('caller-not-authorized');
    }
    if (
      [ROOT, RECOVERY].indexOf(id) < 0 ||
      (['install', 'ready', 'confirm', 'restoreProfile'].indexOf(method) >= 0 &&
        id !== ROOT)
    )
      throw Error('caller-not-authorized');
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
    if (
      allowed.indexOf('version') >= 0 &&
      (typeof payload.version !== 'string' ||
        !/^\d{1,4}\.\d{1,4}\.\d{1,4}$/.test(payload.version))
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
};
module.exports.methods = Object.keys(fields);
