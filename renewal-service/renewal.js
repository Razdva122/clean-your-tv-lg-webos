'use strict';
var diagnostics = require('./diagnostics');
var DAY = 86400000;
function parseRemaining(response) {
  if (
    !response ||
    response.result !== 'success' ||
    typeof response.errorMsg !== 'string'
  )
    return null;
  var m = /^(\d{1,6}):([0-5]\d):([0-5]\d)$/.exec(response.errorMsg);
  return m ? Number(m[1]) * 3600 + Number(m[2]) * 60 + Number(m[3]) : null;
}
function validToken(value) {
  return typeof value === 'string' && /^[a-zA-Z0-9]{1,4096}$/.test(value);
}
// One owner per state file. No global timers or application/remote-control actions.
function createRenewal(io, options) {
  options = options || {};
  var running = null;
  async function attempt() {
    if (!options.enabled) return { status: 'disabled' };
    var state,
      now = io.now();
    try {
      state = (await io.load()) || {};
    } catch (error) {
      return {
        status: 'storage-error',
        diagnostic: diagnostics.storage('renewal', 'read', error).diagnostic
      };
    }
    if (typeof state.nextAt === 'number' && now < state.nextAt)
      return { status: 'cooldown', nextAt: state.nextAt };
    var token;
    try {
      token = await io.readToken();
    } catch (_) {
      token = '';
    }
    if (!validToken(token)) return { status: 'unavailable' };
    var failures = Math.min(Math.max(Number(state.failures) || 0, 0), 3);
    var retryDelay = [15 * 60000, 60 * 60000, 6 * 3600000, DAY][failures];
    // Reserve before network: process death cannot cause an immediate retry loop.
    var result = {
      status: 'retry',
      checkedAt: now,
      nextAt: now + retryDelay,
      failures: failures + 1
    };
    try {
      await io.save(result);
    } catch (error) {
      return {
        status: 'storage-error',
        diagnostic: diagnostics.storage('renewal', 'write', error).diagnostic
      };
    }
    try {
      var before = parseRemaining(await io.request('check', token));
      if (before === null) result.status = 'unverified';
      else if (before === 0) {
        result.status = 'expired';
        result.nextAt = now + DAY;
      } else if (before > 7 * 86400) {
        result = {
          status: 'healthy',
          remainingSeconds: before,
          checkedAt: now,
          nextAt: now + DAY,
          failures: 0
        };
      } else if ((await io.readToken()) !== token)
        result.status = 'session-changed';
      else {
        var reset = await io.request('reset', token);
        if (!reset || reset.result !== 'success') result.status = 'unverified';
        else if ((await io.readToken()) !== token)
          result.status = 'session-changed';
        else {
          var after = parseRemaining(await io.request('check', token));
          if (after !== null && after > before + 60) {
            result = {
              status: 'renewed',
              remainingSeconds: after,
              checkedAt: now,
              nextAt: now + DAY,
              failures: 0
            };
          } else result.status = 'unverified';
        }
      }
    } catch (_) {
      result.status = 'retry';
    }
    try {
      await io.save(result);
    } catch (error) {
      return {
        status: 'storage-error',
        diagnostic: diagnostics.storage('renewal', 'write', error).diagnostic
      };
    }
    return result;
  }
  return {
    run: function () {
      if (!running)
        running = attempt().then(
          function (value) {
            running = null;
            return value;
          },
          function () {
            running = null;
            return { status: 'internal-error' };
          }
        );
      return running;
    }
  };
}
module.exports = {
  createRenewal: createRenewal,
  parseRemaining: parseRemaining,
  validToken: validToken
};
