'use strict';
var diagnostics = require('./diagnostics');
var screensaverMethods = [
  'screensaverStatus',
  'screensaverConfigure',
  'screensaverPreview',
  'screensaverActivity',
  'screensaverEligible',
  'screensaverStop'
];
function validScreensaver(method, payload, object) {
  if (!object) return false;
  if (method === 'screensaverPreview' || method === 'screensaverEligible') {
    var keys = Object.keys(payload);
    return (
      !keys.length ||
      (keys.length === 1 &&
        keys[0] === 'mediaUrl' &&
        typeof payload.mediaUrl === 'string' &&
        payload.mediaUrl.length <= 96 &&
        /^http:\/\/127\.0\.0\.1:[0-9]{1,5}\/[a-f0-9]{32}\/(?:4k\.mp4|1080p\.mp4|photo\.(?:jpg|png))$/.test(
          payload.mediaUrl
        ))
    );
  }
  if (method !== 'screensaverConfigure')
    return Object.keys(payload).length === 0;
  return (
    Object.keys(payload).every(function (key) {
      return (
        [
          'assetId',
          'enabled',
          'idleTimeoutMs',
          'mode',
          'scope',
          'clockOverlay',
          'clock',
          'quality'
        ].indexOf(key) >= 0
      );
    }) &&
    (!Object.prototype.hasOwnProperty.call(payload, 'quality') ||
      ['auto', '4k', '1080p', 'image'].indexOf(payload.quality) >= 0) &&
    (!Object.prototype.hasOwnProperty.call(payload, 'clock') ||
      (payload.clock &&
        typeof payload.clock === 'object' &&
        !Array.isArray(payload.clock) &&
        Object.keys(payload.clock).sort().join(',') === 'hour12,locale' &&
        typeof payload.clock.locale === 'string' &&
        /^[a-z]{2,3}(?:-[A-Z][a-z]{3}|-[A-Z]{2})?$/.test(
          payload.clock.locale
        ) &&
        typeof payload.clock.hour12 === 'boolean')) &&
    (!Object.prototype.hasOwnProperty.call(payload, 'clockOverlay') ||
      typeof payload.clockOverlay === 'boolean') &&
    typeof payload.enabled === 'boolean' &&
    ['cytv', 'global'].indexOf(payload.scope) !== -1 &&
    ['ambient', 'clock', 'photo', 'video'].indexOf(payload.mode) !== -1 &&
    typeof payload.assetId === 'string' &&
    /^[A-Za-z0-9_-]{0,128}$/.test(payload.assetId) &&
    typeof payload.idleTimeoutMs === 'number' &&
    Math.floor(payload.idleTimeoutMs) === payload.idleTimeoutMs &&
    payload.idleTimeoutMs >= 30000 &&
    payload.idleTimeoutMs <= 1800000
  );
}
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
            ].concat(screensaverMethods)
      ).indexOf(method) < 0 ||
      (screensaverMethods.indexOf(method) !== -1 &&
        !validScreensaver(method, payload, object)) ||
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
        if (method === 'screensaverConfigure') request.settings = payload;
        if (
          (method === 'screensaverPreview' ||
            method === 'screensaverEligible') &&
          payload.mediaUrl
        )
          request.mediaUrl = payload.mediaUrl;
        if (method === 'presentationDismissed') request.generation = generation;
        require('./state-permissions').atomicRecord(
          dir,
          prefix + '-request',
          JSON.stringify(request)
        );
      } catch (e) {
        var contract = e && e.contractEvents && e.contractEvents[0];
        var phase = e && (e.storagePhase || (contract && contract.phase));
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
          var raw = require('./state-permissions').readChannelRecord(
            dir,
            prefix + '-response'
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
