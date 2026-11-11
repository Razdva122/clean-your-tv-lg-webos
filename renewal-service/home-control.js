'use strict';
var diagnostics = require('./diagnostics');
// The service writes inside its own jail-visible package. The native controller
// reads this provisioned prisoner:jailer 2770 channel; request files stay 0660.
module.exports = function (fs, dir, options) {
  options = options || {};
  var busy = false,
    now = options.now || Date.now,
    later = options.later || setTimeout;
  var inputs = options.inputs === true,
    catalog = options.catalog === true,
    prefix = catalog ? 'catalog' : inputs ? 'input' : 'home';
  var nonce =
    options.nonce ||
    function () {
      return require('crypto').randomBytes(16).toString('hex');
    };
  return function (method, payload) {
    var object =
      payload && typeof payload === 'object' && !Array.isArray(payload);
    var generation =
      method === 'presentationDismissed' && object ? payload.generation : null;
    if (
      (catalog
        ? ['listApps']
        : inputs
          ? ['inputStatus']
          : [
              'homeStatus',
              'setHomeControl',
              'openLGHome',
              'presentationContext',
              'presentationDismissed'
            ]
      ).indexOf(method) < 0 ||
      (method === 'presentationContext' &&
        (!object || Object.keys(payload).length !== 0)) ||
      (method === 'presentationDismissed' &&
        (!object ||
          Object.keys(payload).length !== 1 ||
          Object.keys(payload)[0] !== 'generation' ||
          typeof generation !== 'number' ||
          !isFinite(generation) ||
          Math.floor(generation) !== generation ||
          generation < 0 ||
          generation > 9007199254740991)) ||
      ((method === 'inputStatus' || method === 'listApps') &&
        (!payload ||
          typeof payload !== 'object' ||
          Array.isArray(payload) ||
          Object.keys(payload).length !== 0)) ||
      (method === 'setHomeControl' &&
        (!payload || typeof payload.enabled !== 'boolean'))
    )
      return Promise.resolve({
        returnValue: false,
        errorText: 'Invalid Home request'
      });
    if (busy)
      return Promise.resolve({
        returnValue: false,
        errorText: 'Home control busy',
        diagnostic: diagnostics.describe('home', 'wait', { code: 'BUSY' })
      });
    busy = true;
    return new Promise(function (resolve) {
      var id = nonce(),
        deadline = now() + 5000,
        operation = 'write',
        lastFailure = null;
      function finish(r) {
        busy = false;
        resolve(r);
      }
      try {
        var request = { id: id, method: method, expires: deadline };
        if (method === 'setHomeControl') request.enabled = payload.enabled;
        if (method === 'presentationDismissed') request.generation = generation;
        require('./state-permissions').atomicRecord(
          dir,
          prefix + '-request',
          JSON.stringify(request)
        );
      } catch (e) {
        var phase = e && e.storagePhase;
        var contract = e && e.contractEvents && e.contractEvents[0];
        if (['write', 'chmod', 'rename'].indexOf(phase) >= 0) operation = phase;
        finish({
          returnValue: false,
          errorText: 'Home Helper data unavailable',
          diagnostic: diagnostics.describe(
            'home',
            operation,
            contract && contract.expected !== 'storage-io' && !e.code
              ? { code: 'INVALID_STATE' }
              : e
          ),
          channelMode:
            contract &&
            contract.field === 'directory' &&
            contract.expected === 'safe-mode' &&
            contract.actual
              ? contract.actual.mode
              : undefined
        });
        return;
      }
      function poll() {
        operation = 'read';
        try {
          var raw = fs.readFileSync(
            dir + '/' + prefix + '-response.json',
            'utf8'
          );
          operation = 'parse';
          var r = JSON.parse(raw);
          lastFailure = null;
          if (r.id === id) {
            finish(r);
            return;
          }
        } catch (e) {
          lastFailure = diagnostics.describe('home', operation, e);
        }
        if (now() >= deadline) {
          finish({
            returnValue: false,
            errorText: 'Home Helper did not respond',
            diagnostic:
              lastFailure ||
              diagnostics.describe('home', 'wait', { code: 'TIMEOUT' })
          });
          return;
        }
        later(poll, 100);
      }
      poll();
    });
  };
};
