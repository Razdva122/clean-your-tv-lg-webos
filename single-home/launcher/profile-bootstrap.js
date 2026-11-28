/* Boot the product Home from its bundled service and origin-local layout. */
(function (root) {
  'use strict';
  var service = 'luna://io.github.razdva122.cytvhomepilot.service/';
  var pilot = {};
  root.PilotHome = pilot;
  function request(method, timeout, callback) {
    var bridge,
      finished = false;
    var timer = setTimeout(function () {
      finish(null);
    }, timeout);
    function finish(reply) {
      if (finished) return;
      finished = true;
      clearTimeout(timer);
      if (bridge) {
        try {
          bridge.cancel();
        } catch (_) {}
      }
      callback(reply);
    }
    try {
      bridge = new PalmServiceBridge();
      bridge.onservicecallback = function (raw) {
        var reply;
        try {
          reply = JSON.parse(raw);
        } catch (_) {}
        finish(reply);
      };
      bridge.call(service + method, '{}');
    } catch (_) {
      finish(null);
    }
  }
  function validId(id) {
    return (
      typeof id === 'string' &&
      /^[A-Za-z0-9_][A-Za-z0-9_.-]{0,255}$/.test(id) &&
      id !== 'io.github.razdva122.cytvhomepilot'
    );
  }
  pilot.installed = function (callback) {
    request('catalog', 12000, function (reply) {
      if (
        !reply ||
        reply.returnValue !== true ||
        !Array.isArray(reply.apps) ||
        reply.apps.length > 300 ||
        !reply.apps.every(function (app) {
          return (
            app &&
            validId(app.id) &&
            typeof app.title === 'string' &&
            app.title.length > 0 &&
            app.title.length <= 256
          );
        })
      ) {
        callback(null, null, reply && reply.errorCode);
        return;
      }
      callback(
        reply.apps,
        reply.apps.map(function (a) {
          return a.id;
        })
      );
    });
  };
  function previousSelection() {
    try {
      var ids = JSON.parse(localStorage.getItem('pilot.home.layout.v1'));
      if (Array.isArray(ids) && ids.length <= 300 && ids.every(validId))
        return ids;
    } catch (_) {}
    return null;
  }
  function boot(apps, ids) {
    var selected = previousSelection();
    root.TV_APPS = { apps: apps || [], inputs: [] };
    pilot.library = AppLibrary.create(
      localStorage,
      root.TV_APPS.apps,
      CONFIG,
      null,
      null,
      {
        initialIds: selected || ids,
        retainMissingIds: true
      }
    );
    if (
      apps &&
      (apps.length || selected || AppLibrary.readLayout(localStorage))
    ) {
      try {
        pilot.library.refresh(apps, ids);
      } catch (_) {
        // Keep the in-memory selection if origin storage is temporarily full.
      }
    }
    var script = document.createElement('script');
    script.src = 'app.js';
    document.body.appendChild(script);
  }
  function start() {
    var skip = /(?:^|[?&])skipSetup=1(?:&|$)/.test(location.search);
    try {
      skip =
        skip ||
        sessionStorage.getItem('cytv.home.skipSetup') === '1' ||
        localStorage.getItem('pilot.home.later') === '1';
    } catch (_) {}
    request('status', 4000, function (state) {
      if (
        !state ||
        state.returnValue !== true ||
        !state.paired ||
        state.storageReady !== true ||
        state.credentialsReady !== true
      ) {
        if (skip || (!state && AppLibrary.readLayout(localStorage))) boot(null);
        else location.replace('setup/index.html');
        return;
      }
      pilot.installed(function (apps, ids, error) {
        if (
          apps ||
          skip ||
          (error !== 'saved-pairing-rejected' &&
            AppLibrary.readLayout(localStorage))
        )
          boot(apps, ids);
        else
          location.replace(
            'setup/index.html?settings=1' +
              (error === 'saved-pairing-rejected'
                ? '&reason=saved-pairing-rejected'
                : '')
          );
      });
    });
  }
  if (root.HomeI18n) root.HomeI18n.ready(start);
  else start();
})(window);
