'use strict';

var LG_RECONNECT_MS = 5000;

// Dormant adapter: the Root service must explicitly supply verified ownership,
// capability predicates and shared modules before enabling a generation. This
// module registers no service method, starts no input reader and touches no LG
// files. Root recovery/guardian ownership remains the caller's authority.
module.exports = function (options) {
  if (
    !options ||
    !options.controller ||
    typeof options.controller.create !== 'function' ||
    typeof options.createLG !== 'function' ||
    typeof options.getOwner !== 'function' ||
    typeof options.context !== 'function' ||
    typeof options.launch !== 'function'
  ) {
    throw new Error('Root screensaver dependencies are required');
  }
  var run = null;
  var lgDeferral = null;
  var disposed = false;
  var schedule = options.setInterval || setInterval;
  var unschedule = options.clearInterval || clearInterval;
  var now = options.now || options.controller.monotonic;

  function ownership() {
    var value;
    try {
      value = options.getOwner();
    } catch (_) {
      return null;
    }
    if (
      !value ||
      value.active !== true ||
      value.healthy !== true ||
      value.legacyHelperActive !== false ||
      typeof value.generation !== 'number' ||
      !isFinite(value.generation) ||
      value.generation < 0 ||
      value.generation > 9007199254740991 ||
      Math.floor(value.generation) !== value.generation
    )
      return null;
    return value;
  }

  function release() {
    var previous = run;
    run = null;
    if (!previous) return;
    if (previous.monitor !== null) unschedule(previous.monitor);
    // Remove LG deferral first. Renderer then sees close or its bounded
    // controller-loss timeout; no privileged closeByAppId is required.
    try {
      if (previous.lg) previous.lg.stop();
    } catch (_) {}
    try {
      if (previous.controller) previous.controller.dispose();
    } catch (_) {}
  }

  function maintains(active, current) {
    return (
      current &&
      current.generation === active.generation &&
      (current.stale !== true ||
        (active.controller && active.controller.ownsPopup()))
    );
  }

  function reconcile() {
    var current = disposed ? null : ownership();
    if (run && !maintains(run, current)) release();
    return current;
  }

  function matches(generation) {
    var current = reconcile();
    return !!(
      current &&
      current.stale !== true &&
      current.generation === generation
    );
  }

  function readSession(active) {
    if (!active || !active.controller) return null;
    var session = active.controller.getSession();
    // Rendering can outlive a poll deadline. Check freshness after reading it
    // so a deadline crossed during this read cannot defer the LG saver.
    return matches(active.generation) && run === active ? session : null;
  }

  function context(active) {
    var current = ownership();
    if (disposed || run !== active || !maintains(active, current))
      return { ownerHealthy: false, popupSupported: false };
    var supplied;
    try {
      supplied = options.context(current.stale === true) || {};
    } catch (_) {
      return { ownerHealthy: false, popupSupported: false };
    }
    var result = {};
    Object.keys(supplied).forEach(function (key) {
      result[key] = supplied[key];
    });
    result.ownerHealthy = true;
    result.ownerGeneration = active.generation;
    return result;
  }

  function startLG(active) {
    var time = now();
    if (time < active.nextLGStart || active.lg.status().running) return;
    // A failed LG reply closes the subscription. Retry on a fresh Root
    // status without replacing the controller or flooding an unavailable bus.
    active.nextLGStart = time + LG_RECONNECT_MS;
    active.lg.start();
  }

  function enable(generation) {
    if (!matches(generation)) return false;
    var available;
    try {
      available = (options.context() || {}).popupSupported === true;
    } catch (_) {
      available = false;
    }
    if (!available) {
      release();
      return false;
    }
    if (run) {
      startLG(run);
      return true;
    }
    // A fresh subscription for the same owner must still yield the next
    // request to LG after CYTV used the previous one.
    if (!lgDeferral || lgDeferral.generation !== generation)
      lgDeferral = { generation: generation, deferredGlobal: false };
    var active = {
      generation: generation,
      controller: null,
      lg: null,
      nextLGStart: 0,
      monitor: null
    };
    run = active;
    try {
      active.controller = options.controller.create({
        generation: generation,
        context: function () {
          return context(active);
        },
        now: now,
        listen: options.listen,
        setInterval: schedule,
        clearInterval: unschedule,
        acquireMedia: function () {
          if (
            !matches(generation) ||
            run !== active ||
            typeof options.acquireMedia !== 'function'
          )
            return null;
          return options.acquireMedia();
        },
        launch: function (id, params, callback) {
          if (
            id !== 'com.cleanyourtv.screensaver' ||
            !matches(generation) ||
            run !== active
          )
            return callback(false);
          options.launch(id, params, callback);
        }
      });
      active.lg = options.createLG({
        service: options.service,
        clientName: 'com.cleanyourtv.root.screensaver.' + generation,
        deferralState: lgDeferral,
        now: now,
        log: options.log,
        startGlobal: function (done) {
          if (!matches(generation) || run !== active) return null;
          return active.controller.startGlobal(done);
        },
        getSession: function () {
          return readSession(active);
        }
      });
      active.monitor = schedule(reconcile, 250);
      active.controller.enable();
      startLG(active);
      return true;
    } catch (_) {
      release();
      return false;
    }
  }

  function call(generation, method) {
    if (!matches(generation) || !run) return false;
    return run.controller[method]() !== false;
  }

  function stop(generation) {
    if (!matches(generation) || !run) return false;
    lgDeferral = null;
    release();
    return true;
  }

  return {
    enable: enable,
    whenReady: function (generation) {
      var active = run;
      if (!matches(generation) || !active) return Promise.resolve(false);
      return active.controller.whenReady().then(function (ready) {
        return ready && matches(generation) && run === active;
      });
    },
    preview: function (generation) {
      return call(generation, 'preview');
    },
    eligible: function (generation) {
      return call(generation, 'eligible');
    },
    activity: function (generation) {
      return call(generation, 'activity');
    },
    powerInactive: stop,
    stop: stop,
    getSession: function () {
      return readSession(run);
    },
    reconcile: reconcile,
    dispose: function () {
      disposed = true;
      release();
    }
  };
};
