(function (root) {
  'use strict';
  var homes = {
    root: 'com.cleanyourtv.root.preview',
    'no-root': 'com.gathin.tvhome'
  };
  var storageKey = 'cytv.tile.home';
  var doc = root.document;
  var busy = false;
  var opened = false;
  var handoff;
  var returned;
  var currentBridge;
  var generation = 0;
  function saved(key) {
    try {
      return root.localStorage.getItem(key);
    } catch (_) {
      return null;
    }
  }
  function valid(value) {
    return value === 'root' || value === 'no-root';
  }
  function requestedRecovery(event) {
    try {
      var params = event && event.detail;
      if (!params) params = root.PalmSystem && root.PalmSystem.launchParams;
      if (params && params.params) params = params.params;
      if (typeof params === 'string') params = JSON.parse(params);
      if (params && params.params) params = params.params;
      return (
        params &&
        params.cytvRecovery === true &&
        root.location.hash !== '#openHome'
      );
    } catch (_) {
      return false;
    }
  }
  function open(event) {
    clearTimeout(returned);
    if (busy || doc.hidden) return;
    opened = true;
    var request = ++generation;
    var bound = root.CYTVTileEdition;
    var edition = valid(bound) ? bound : saved(storageKey);
    if (
      bound === null &&
      (saved('cytv.installer.operation') || !valid(edition))
    ) {
      root.location.replace('setup.html#open');
      return;
    }
    function recovery() {
      root.location.replace('recovery.html');
    }
    if ((!valid(bound) && bound !== null) || !valid(edition)) {
      recovery();
      return;
    }
    if (requestedRecovery(event)) {
      root.location.replace('recovery.html#status');
      return;
    }
    busy = true;
    var bridge;
    function finish(ok) {
      if (generation !== request || !busy) return;
      clearTimeout(handoff);
      if (bridge) {
        bridge.onservicecallback = function () {};
        try {
          bridge.cancel();
        } catch (_) {}
        currentBridge = null;
      }
      busy = false;
      if (!ok) {
        recovery();
        return;
      }
      // Remembering a daily launch grants no access to installation or routing.
      try {
        root.localStorage.setItem(storageKey, edition);
      } catch (_) {}
      if (!doc.hidden) {
        busy = true;
        handoff = setTimeout(function () {
          busy = false;
          if (!doc.hidden) recovery();
        }, 5000);
      }
    }
    try {
      handoff = setTimeout(function () {
        finish(false);
      }, 6000);
      currentBridge = bridge = new root.PalmServiceBridge();
      bridge.onservicecallback = function (raw) {
        try {
          finish(JSON.parse(raw).returnValue === true);
        } catch (_) {
          finish(false);
        }
      };
      bridge.call(
        'luna://com.webos.applicationManager/launch',
        JSON.stringify({ id: homes[edition] })
      );
    } catch (_) {
      finish(false);
    }
  }
  // A failed/crashed foreground application can return us to view without a
  // relaunch. Show recovery instead of starting the same Home in a loop.
  doc.addEventListener('visibilitychange', function () {
    if (doc.hidden) {
      clearTimeout(handoff);
      clearTimeout(returned);
      if (currentBridge) {
        try {
          currentBridge.cancel();
        } catch (_) {}
        currentBridge = null;
      }
      ++generation;
      busy = false;
    } else if (!busy) {
      // webOS can deliver visibilitychange just before webOSRelaunch. Give
      // deliberate relaunch its own turn instead of opening two destinations.
      returned = setTimeout(function () {
        if (busy || doc.hidden) return;
        if (!opened) open();
        else root.location.replace('recovery.html');
      }, 300);
    }
  });
  doc.addEventListener('webOSRelaunch', open);
  open();
})(window);
