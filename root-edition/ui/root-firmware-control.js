(function (root, factory) {
  'use strict';
  if (typeof module === 'object' && module.exports) module.exports = factory;
  else root.createRootFirmwareControl = factory;
})(this, function (request) {
  'use strict';
  // Homebrew owns the preference and its boot-time hosts overlay. No new
  // privileged service, mount, reboot, firmware deletion or persisted CYTV flag.
  var busy = false;
  function failure(code) {
    var error = Error(code);
    error.firmwareCode = code;
    return error;
  }
  function reason(error) {
    if (
      error instanceof Error &&
      [
        'permission-denied',
        'service-unavailable',
        'not-root',
        'unsupported',
        'timeout',
        'unavailable'
      ].indexOf(error.firmwareCode) >= 0
    )
      return error.firmwareCode;
    var text = (error && (error.errorText || error.message)) || '';
    if (/denied|not permitted|permission/i.test(text))
      return 'permission-denied';
    if (
      /service[^\n]*(?:does not exist|not found|not registered|not running)|unknown service/i.test(
        text
      )
    )
      return 'service-unavailable';
    if (/timed out|timeout/i.test(text)) return 'timeout';
    if (/invalid service response/i.test(text)) return 'unsupported';
    return 'unavailable';
  }
  function call(method, payload) {
    return Promise.resolve()
      .then(function () {
        return request(
          'luna://org.webosbrew.hbchannel.service/' + method,
          payload,
          10000
        );
      })
      .then(function (reply) {
        if (!reply || reply.returnValue !== true) throw failure(reason(reply));
        if (
          typeof reply.blockUpdates !== 'boolean' ||
          (method === 'getConfiguration' && typeof reply.root !== 'boolean')
        )
          throw failure('unsupported');
        if (method === 'getConfiguration' && reply.root !== true)
          throw failure('not-root');
        return { returnValue: true, enabled: reply.blockUpdates };
      });
  }
  function status() {
    return call('getConfiguration', {});
  }
  return {
    get: function () {
      return status().catch(function (error) {
        return { returnValue: false, errorCode: reason(error) };
      });
    },
    set: async function (enabled, expectedEnabled) {
      if (typeof enabled !== 'boolean' || typeof expectedEnabled !== 'boolean')
        return { returnValue: false, errorCode: 'invalid' };
      if (busy) return { returnValue: false, errorCode: 'busy' };
      busy = true;
      var attempted = false;
      try {
        var before = await status();
        if (before.enabled !== expectedEnabled)
          return { returnValue: false, errorCode: 'changed', status: before };
        if (before.enabled === enabled) return before;
        attempted = true;
        await call('setConfiguration', { blockUpdates: enabled });
        var after = await status();
        if (after.enabled !== enabled)
          return {
            returnValue: false,
            errorCode: 'unconfirmed',
            status: after
          };
        return after;
      } catch (error) {
        var reply = {
          returnValue: false,
          errorCode: attempted ? 'unconfirmed' : reason(error)
        };
        if (attempted)
          try {
            reply.status = await status();
          } catch (_) {}
        return reply;
      } finally {
        busy = false;
      }
    }
  };
});
