/* Application-owned inactivity only. Importing this factory observes nothing.
 * The owner must refresh() whenever playback or sensitive-modal eligibility
 * changes. There is no cross-app observation, playback inference or key filter.
 */
(function (root, factory) {
  'use strict';
  if (typeof module === 'object' && module.exports) module.exports = factory;
  else root.CYTVScreensaverIdle = factory;
})(typeof window !== 'undefined' ? window : this, function (options) {
  'use strict';
  var win = options.window,
    doc = options.document,
    now =
      options.now ||
      function () {
        return win.performance && win.performance.now
          ? win.performance.now()
          : Date.now();
      },
    schedule =
      options.setTimeout ||
      function (callback, delay) {
        return win.setTimeout(callback, delay);
      },
    unschedule =
      options.clearTimeout ||
      function (id) {
        win.clearTimeout(id);
      },
    idleMs = options.idleMs === undefined ? 60000 : options.idleMs,
    driftMs =
      options.maxTimerDriftMs === undefined ? 1000 : options.maxTimerDriftMs,
    enabled = false,
    destroyed = false,
    requested = false,
    epoch = 0,
    lastActivity = null,
    timer = null,
    inputEvents = [
      'keydown',
      'keyup',
      'pointerdown',
      'pointerup',
      'pointermove',
      'mousedown',
      'mouseup',
      'mousemove',
      'wheel',
      'touchstart',
      'touchmove',
      'touchend'
    ];
  if (
    typeof idleMs !== 'number' ||
    !isFinite(idleMs) ||
    idleMs <= 0 ||
    idleMs > 2147483647 ||
    typeof driftMs !== 'number' ||
    !isFinite(driftMs) ||
    driftMs < 0
  )
    throw new Error('Invalid screensaver idle interval');
  function time() {
    try {
      var value = now();
      return typeof value === 'number' && isFinite(value) && value >= 0
        ? value
        : null;
    } catch (ignore) {
      return null;
    }
  }
  function eligible() {
    try {
      return (
        doc.hidden === false &&
        doc.hasFocus() === true &&
        options.isEligible() === true
      );
    } catch (ignore) {
      return false;
    }
  }
  function cancelTimer() {
    if (!timer) return;
    var old = timer;
    timer = null;
    unschedule(old.id);
  }
  function arm(at, delay) {
    if (!enabled || destroyed || requested || timer) return;
    var current = { id: null, due: at + delay };
    timer = current;
    current.id = schedule(function () {
      if (!enabled || destroyed || timer !== current) return;
      timer = null;
      var currentTime = time();
      if (currentTime === null) return;
      // Timer suspension/clock jumps are not evidence of uninterrupted idle.
      if (
        currentTime < lastActivity ||
        currentTime < current.due ||
        currentTime - current.due > driftMs
      ) {
        activity();
        return;
      }
      if (!eligible() || !enabled || destroyed) return;
      var elapsed = currentTime - lastActivity;
      if (elapsed < idleMs) {
        arm(currentTime, idleMs - elapsed);
        return;
      }
      requested = true;
      try {
        options.onIdle({ epoch: epoch, idleMs: elapsed });
      } catch (ignore) {}
    }, delay);
  }
  function activity(event) {
    if (!enabled || destroyed) return;
    // Notify actual input before rechecking eligibility: the owner can cancel
    // an idle media preparation without adding a second input observer.
    if (event && inputEvents.indexOf(event.type) >= 0 && options.onInput)
      try {
        options.onInput(event);
      } catch (ignore) {}
    lastActivity = time();
    requested = false;
    epoch += 1;
    if (lastActivity === null || !eligible() || !enabled || destroyed) {
      cancelTimer();
      return;
    }
    try {
      if (options.onActivity) options.onActivity({ epoch: epoch });
    } catch (ignore) {}
    // Keep the existing timer across pointer motion. On expiry it rechecks the
    // latest activity time and schedules only the remaining idle interval.
    arm(lastActivity, idleMs);
  }
  function refresh() {
    cancelTimer();
    activity();
  }
  function listen(add) {
    var method = add ? 'addEventListener' : 'removeEventListener';
    inputEvents.forEach(function (type) {
      doc[method](type, activity, true);
    });
    doc[method]('visibilitychange', refresh, false);
    win[method]('focus', refresh, false);
    win[method]('blur', refresh, false);
  }
  function disable() {
    if (!enabled) return;
    enabled = false;
    requested = false;
    cancelTimer();
    listen(false);
  }
  return {
    enable: function () {
      if (enabled || destroyed) return;
      enabled = true;
      listen(true);
      activity();
    },
    disable: disable,
    refresh: refresh,
    destroy: function () {
      disable();
      destroyed = true;
    },
    status: function () {
      return { enabled: enabled, requested: requested, epoch: epoch };
    }
  };
});
