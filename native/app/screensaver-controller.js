'use strict';

// Trusted hooks for the existing Helper input/lifecycle owner. Construction is
// inert; integration must establish package and firmware capabilities first.
// The shared controller is supplied by packaging, not downloaded at runtime.
module.exports = function (options) {
  var controller = null;
  var lg = null;
  var enabled = false;
  var disposed = false;

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

  function launch(id, params, done) {
    var capability = context();
    if (
      !enabled ||
      disposed ||
      capability.ownerHealthy !== true ||
      capability.popupSupported !== true ||
      id !== 'com.cleanyourtv.screensaver'
    ) {
      done(false);
      return;
    }
    try {
      options.service.call(
        'luna://com.webos.applicationManager/launch',
        {
          id: 'com.cleanyourtv.screensaver',
          params: params
        },
        function (message) {
          done(
            !!(
              message &&
              message.payload &&
              message.payload.returnValue === true
            )
          );
        }
      );
    } catch (ignore) {
      done(false);
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
            return enabled && controller ? controller.startGlobal(done) : null;
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
        return true;
      } catch (ignore) {
        stop();
        return false;
      }
    },
    whenReady: function () {
      var current = controller;
      if (!enabled || disposed || !current) return Promise.resolve(false);
      return current.whenReady().then(function (ready) {
        return ready && enabled && !disposed && controller === current;
      });
    },
    preview: function () {
      return enabled && !disposed && controller ? controller.preview() : false;
    },
    eligible: function () {
      return enabled && !disposed && controller ? controller.eligible() : false;
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
    ownsPopup: function () {
      return !!(enabled && controller && controller.ownsPopup());
    }
  };
};
