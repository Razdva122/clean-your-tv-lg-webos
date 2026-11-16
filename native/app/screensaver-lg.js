'use strict';

// The C3 gives clients three seconds to answer. Leave time for LS2 delivery
// and let firmware proceed if the renderer still has not claimed the window.
var GLOBAL_READY_MS = 1500;

// Ordinary tvpower protocol. Only a fresh, visible and focused renderer may
// defer LG. A global owner can attempt to show one within the response budget.
module.exports = function (options) {
  var service = options.service,
    clientName = options.clientName,
    getSession = options.getSession,
    now =
      options.now ||
      function () {
        var time = process.hrtime();
        return time[0] * 1000 + time[1] / 1000000;
      },
    schedule = options.setTimeout || setTimeout,
    unschedule = options.clearTimeout || clearTimeout,
    current = null;
  if (typeof clientName !== 'string' || !clientName || clientName.length > 128)
    throw new Error('Invalid screensaver client name');

  function log(event, fields) {
    var record = fields || {};
    record.event = event;
    try {
      if (options.log) options.log(record);
    } catch (ignore) {}
  }
  function active(run) {
    return current === run && run.running;
  }
  function release(run, reason) {
    if (!active(run)) return;
    run.running = false;
    run.registered = false;
    if (run.offer) {
      unschedule(run.offer.timer);
      if (run.offer.cancel) run.offer.cancel();
      run.offer = null;
    }
    run.pending.forEach(function (request) {
      unschedule(request.timer);
      if (request.cancel) request.cancel();
    });
    run.pending = [];
    try {
      if (run.subscription) run.subscription.cancel();
    } catch (ignore) {}
    log('screensaver-lg-' + reason);
  }
  function timestampKey(value) {
    // Compare decimal request timestamps without coercing a 64-bit string to
    // Number. The original value, including its type, is always sent unchanged.
    if (typeof value === 'number') {
      if (
        !isFinite(value) ||
        value < 0 ||
        value > 9007199254740991 ||
        Math.floor(value) !== value
      )
        return null;
      return String(value);
    }
    if (typeof value !== 'string' || !/^[0-9]{1,32}$/.test(value)) return null;
    return value.replace(/^0+(?=[0-9])/, '');
  }
  function isNewer(key, previous) {
    return (
      previous === null ||
      key.length > previous.length ||
      (key.length === previous.length && key > previous)
    );
  }
  function healthy() {
    try {
      var session = getSession(),
        time = now();
      return !!(
        session &&
        typeof session.sessionId === 'string' &&
        session.sessionId &&
        typeof session.generation === 'number' &&
        isFinite(session.generation) &&
        session.generation >= 0 &&
        Math.floor(session.generation) === session.generation &&
        session.state === 'visible' &&
        session.visible === true &&
        session.focused === true &&
        typeof session.lastHeartbeatMs === 'number' &&
        isFinite(session.lastHeartbeatMs) &&
        typeof time === 'number' &&
        isFinite(time) &&
        time >= session.lastHeartbeatMs &&
        time - session.lastHeartbeatMs < 3000
      );
    } catch (ignore) {
      return false;
    }
  }
  function receive(run, message) {
    if (!active(run)) return;
    var payload = message && message.payload;
    if (
      !payload ||
      typeof payload !== 'object' ||
      Array.isArray(payload) ||
      payload.returnValue !== true
    ) {
      release(run, 'unavailable');
      return;
    }
    if (payload.timestamp === undefined) {
      if (payload.subscribed === true) run.registered = true;
      return;
    }
    var key = timestampKey(payload.timestamp);
    if (key === null) {
      release(run, 'invalid-request');
      return;
    }
    if (!isNewer(key, run.lastTimestamp)) return;
    run.lastTimestamp = key;
    if (run.offer) {
      run.offer.finish(false);
      return respond(run, payload, true);
    }
    var eligible =
      run.registered && run.pending.length === 0 && payload.state === 'Active';
    if (eligible && healthy()) return respond(run, payload, false);
    var deferral = options.deferralState || run;
    if (deferral.deferredGlobal) {
      deferral.deferredGlobal = false;
      return respond(run, payload, true);
    }
    if (!eligible || typeof options.startGlobal !== 'function')
      return respond(run, payload, true);

    var began = now();
    var offer = { timer: null, cancel: null, finish: finish };
    run.offer = offer;
    function finish(ready) {
      if (!active(run) || run.offer !== offer) return;
      run.offer = null;
      unschedule(offer.timer);
      var elapsed = now() - began;
      var shown =
        ready === true &&
        elapsed >= 0 &&
        elapsed < GLOBAL_READY_MS &&
        healthy();
      if (!shown && offer.cancel) offer.cancel();
      if (shown) deferral.deferredGlobal = true;
      respond(run, payload, !shown, shown ? offer.cancel : null);
    }
    offer.timer = schedule(function () {
      finish(false);
    }, GLOBAL_READY_MS);
    try {
      offer.cancel = options.startGlobal(finish);
      if (typeof offer.cancel !== 'function') finish(false);
    } catch (ignore) {
      finish(false);
    }
  }
  function respond(run, payload, ack, cancel) {
    // An owner callback may synchronously stop this registration.
    if (!active(run)) return;
    var request = { timer: null, cancel: cancel };
    run.pending.push(request);
    request.timer = schedule(function () {
      release(run, 'ack-timeout');
    }, 1000);
    log('screensaver-lg-response', { timestamp: payload.timestamp, ack: ack });
    try {
      service.call(
        'luna://com.webos.service.tvpower/power/responseScreenSaverRequest',
        {
          clientName: clientName,
          ack: ack,
          timestamp: payload.timestamp
        },
        function (reply) {
          if (!active(run)) return;
          var index = run.pending.indexOf(request);
          if (index < 0) return;
          unschedule(request.timer);
          run.pending.splice(index, 1);
          if (!reply || !reply.payload || reply.payload.returnValue !== true) {
            if (request.cancel) request.cancel();
            release(run, 'ack-failed');
          }
        }
      );
    } catch (ignore) {
      release(run, 'ack-failed');
    }
  }
  return {
    start: function () {
      if (current && current.running) return;
      var run = {
        running: true,
        registered: false,
        subscription: null,
        lastTimestamp: null,
        offer: null,
        deferredGlobal: false,
        pending: []
      };
      current = run;
      try {
        run.subscription = service.subscribe(
          'luna://com.webos.service.tvpower/power/registerScreenSaverRequest',
          {
            subscribe: true,
            clientName: clientName
          }
        );
        run.subscription.on('response', function (message) {
          receive(run, message);
        });
        run.subscription.on('cancel', function () {
          release(run, 'cancelled');
        });
        run.subscription.on('error', function () {
          release(run, 'unavailable');
        });
      } catch (ignore) {
        release(run, 'unavailable');
      }
    },
    stop: function () {
      if (current) release(current, 'stop');
    },
    status: function () {
      return {
        running: !!(current && current.running),
        registered: !!(current && current.registered)
      };
    }
  };
};
