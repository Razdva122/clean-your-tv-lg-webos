'use strict';

var popupId = 'com.cleanyourtv.screensaver';
var applicationManager = 'luna://com.webos.applicationManager/';

// Trusted hooks for the existing Helper input/lifecycle owner. Construction is
// inert; integration must establish package and firmware capabilities first.
// The shared controller is supplied by packaging, not downloaded at runtime.
module.exports = function (options) {
  var controller = null;
  var lg = null;
  var enabled = false;
  var disposed = false;
  var activation = null;
  var closeReady = null;
  var closeVerified = null;

  function context() {
    var source;
    var value = {};
    try {
      source = options.context() || {};
      Object.keys(source).forEach(function (key) {
        value[key] = source[key];
      });
    } catch (ignore) {
      return {};
    }
    value.ownerHealthy = enabled && !disposed && source.ownerHealthy === true;
    return value;
  }

  function stop() {
    enabled = false;
    var oldLG = lg;
    var oldController = controller;
    lg = null;
    controller = null;
    // Clear registration even if controller cleanup or a provider throws.
    try {
      if (oldLG) oldLG.stop();
    } catch (ignore) {}
    try {
      if (oldController) oldController.dispose();
    } catch (ignore) {}
  }

  function reportUnverifiedClose() {
    if (options.log)
      options.log({ event: 'screensaver-popup-close-unverified' });
  }

  function closePopup(done) {
    function report(reply) {
      var closed =
        reply &&
        (reply.returnValue === true ||
          (reply.returnValue === false &&
            ((reply.errorCode === 40 &&
              reply.errorText === popupId + ' is not running') ||
              (reply.errorCode === 1 &&
                reply.errorText === 'app is not running'))));
      if (!closed) reportUnverifiedClose();
      done(!!closed);
    }
    try {
      options.service.call(
        applicationManager + 'closeByAppId',
        { id: popupId },
        function (message) {
          report(message && message.payload);
        }
      );
    } catch (ignore) {
      report(null);
    }
  }

  function checkClose() {
    if (closeReady) return;
    closeReady = new Promise(function (resolve) {
      var timer = setTimeout(function () {
        reportUnverifiedClose();
        finish(false);
      }, 3000);
      function finish(closed) {
        if (timer === null) {
          if (closed) closeVerified = true;
          return;
        }
        clearTimeout(timer);
        timer = null;
        closeVerified = closed;
        resolve();
      }
      // Clear a stale window and prove this Helper can remove its own popup.
      closePopup(finish);
    });
  }

  function canLaunch() {
    return (
      closeVerified === true &&
      !(activation && (activation.launching || activation.cancelled))
    );
  }

  function closeActivation(attempt) {
    if (attempt.closing) {
      attempt.closeAgain = true;
      return;
    }
    attempt.closing = true;
    var timer = setTimeout(function () {
      closeVerified = false;
      reportUnverifiedClose();
    }, 3000);
    closePopup(function (closed) {
      clearTimeout(timer);
      attempt.closing = false;
      closeVerified = closed;
      if (attempt.closeAgain || (!closed && !attempt.retried)) {
        attempt.retried = attempt.retried || !closed;
        attempt.closeAgain = false;
        closeActivation(attempt);
      } else if (!attempt.launching) activation = null;
    });
  }

  function cancelPopup(effect) {
    if (
      !activation ||
      activation.sessionId !== effect.sessionId ||
      activation.cancelled
    )
      return;
    activation.cancelled = true;
    closeActivation(activation);
  }

  function launch(id, params, done) {
    var capability = context();
    if (
      id !== popupId ||
      !canLaunch() ||
      capability.ownerHealthy !== true ||
      capability.popupSupported !== true
    )
      return done(false);
    var attempt = { sessionId: params.sessionId, launching: true };
    activation = attempt;
    function reported(ok) {
      attempt.launching = false;
      if (attempt.cancelled) {
        // An in-flight SAM launch may succeed after the first close request.
        if (ok) closeActivation(attempt);
        else if (!attempt.closing) activation = null;
        return;
      }
      done(ok);
    }
    try {
      options.service.call(
        applicationManager + 'launch',
        { id: popupId, params: params },
        function (message) {
          reported(
            !!(
              message &&
              message.payload &&
              message.payload.returnValue === true
            )
          );
        }
      );
    } catch (ignore) {
      reported(false);
    }
  }

  function getSession() {
    return enabled && !disposed && controller ? controller.getSession() : null;
  }

  function acquireMedia() {
    var owner = controller;
    var capability = context();
    if (
      !owner ||
      capability.ownerHealthy !== true ||
      capability.popupSupported !== true ||
      typeof options.acquireMedia !== 'function'
    )
      return null;
    var item = options.acquireMedia();
    capability = context();
    if (
      owner !== controller ||
      capability.ownerHealthy !== true ||
      capability.popupSupported !== true
    ) {
      try {
        if (item && item.lease && typeof item.lease.release === 'function')
          item.lease.release();
      } catch (ignore) {}
      return null;
    }
    return item;
  }

  return {
    enable: function () {
      if (disposed) return false;
      enabled = true;
      var capabilities = context();
      if (
        capabilities.popupSupported !== true ||
        capabilities.ownerHealthy !== true
      ) {
        stop();
        return false;
      }
      if (controller) return true;
      try {
        var shared = options.controller || require('./screensaver/controller');
        var createLG = options.createLG || require('./screensaver-lg');
        var now = options.now || shared.monotonic;
        controller = shared.create({
          generation: options.generation,
          context: context,
          launch: launch,
          closePopup: cancelPopup,
          acquireMedia: acquireMedia,
          now: now,
          listen: options.listen,
          setInterval: options.setInterval,
          clearInterval: options.clearInterval
        });
        lg = createLG({
          service: options.service,
          clientName: 'com.local.nativehome.screensaver',
          getSession: getSession,
          startGlobal: function (done) {
            return enabled && controller && canLaunch()
              ? controller.startGlobal(done)
              : null;
          },
          now: now,
          log: options.log
        });
        controller.enable();
        lg.start();
        if (lg.status && !lg.status().running) {
          stop();
          return false;
        }
        checkClose();
        return true;
      } catch (ignore) {
        stop();
        return false;
      }
    },
    whenReady: function () {
      var current = controller;
      if (!enabled || disposed || !current) return Promise.resolve(false);
      return Promise.all([current.whenReady(), closeReady]).then(
        function (ready) {
          return (
            ready[0] &&
            closeVerified === true &&
            enabled &&
            !disposed &&
            controller === current
          );
        }
      );
    },
    preview: function () {
      return enabled && !disposed && controller && canLaunch()
        ? controller.preview()
        : false;
    },
    eligible: function () {
      return enabled && !disposed && controller && canLaunch()
        ? controller.eligible()
        : false;
    },
    activity: function () {
      if (enabled && !disposed && controller) controller.activity();
    },
    powerInactive: function () {
      // A power transition invalidates ownership and registration together.
      // Only a new explicit enable from the existing owner can rearm it.
      stop();
    },
    stop: stop,
    dispose: function () {
      disposed = true;
      stop();
    },
    getSession: getSession,
    unavailable: function () {
      return closeVerified === false;
    },
    closePending: function () {
      return !!(activation && activation.cancelled);
    },
    ownsPopup: function () {
      return !!(enabled && controller && controller.ownsPopup());
    }
  };
};
