'use strict';

// One bounded status command (2 s) plus one monitor interval (500 ms).
var STATUS_RETRY_WINDOW_MS = 2500;

// Fixed Home-only RPCs. Runtime snapshots attest the existing Root generation;
// no web payload can choose a generation, process, path or launch destination.
module.exports = function (service, options) {
  var settings = options.settings,
    now = options.now || options.controller.monotonic,
    schedule = options.setInterval || setInterval,
    unschedule = options.clearInterval || clearInterval,
    state = settings.normalize(),
    observation = null,
    expires = 0,
    refreshFailed = false,
    revision = 0,
    disposed = false,
    polling = false,
    queue = Promise.resolve(),
    monitor = null;
  var binding = null,
    personal = null,
    releaseHold = null;
  function personalSelected() {
    return (
      (state.mode === 'photo' || state.mode === 'video') &&
      state.assetId === 'personal-' + state.mode
    );
  }
  function personalUrl() {
    var value = owner();
    return personal &&
      value &&
      personal.generation === value.generation &&
      personal.mode === state.mode &&
      personal.assetId === state.assetId
      ? personal.url
      : '';
  }
  function globalMode() {
    return state.scope === 'global' && !personalSelected();
  }
  function owner() {
    return !disposed &&
      observation &&
      observation.popupInstalled === true &&
      (globalMode() ||
        (observation.foregroundOwn === true && observation.popupOwn !== true) ||
        (observation.popupOwn === true &&
          binding &&
          observation.owner &&
          binding.generation === observation.owner.generation &&
          now() < binding.expires)) &&
      !refreshFailed &&
      now() < expires
      ? observation.owner
      : null;
  }
  function adapterOwner() {
    var current = owner();
    if (
      current ||
      !globalMode() ||
      !state.enabled ||
      monitor === null ||
      !observation ||
      !observation.owner ||
      observation.popupInstalled !== true ||
      expires === 0 ||
      !(now() < expires + STATUS_RETRY_WINDOW_MS)
    )
      return current;
    // A missed read can keep the current popup connected for a bounded time.
    // The adapter requires fresh authority to launch or defer stock LG.
    return Object.assign({}, observation.owner, { stale: true });
  }
  function available() {
    var value = owner();
    return !!(
      value &&
      value.active === true &&
      value.healthy === true &&
      value.legacyHelperActive === false
    );
  }
  function canStart() {
    return (
      available() &&
      state.enabled === true &&
      (state.scope === 'cytv' || globalMode()) &&
      (state.mode === 'ambient' ||
        state.mode === 'clock' ||
        personalSelected() ||
        !!settings.background(state.mode, state.assetId))
    );
  }
  function localForeground() {
    return (
      canStart() &&
      observation.foregroundOwn === true &&
      observation.popupOwn !== true
    );
  }
  function foreignForeground() {
    return (
      canStart() &&
      globalMode() &&
      observation.foregroundForeign === true &&
      observation.popupOwn !== true
    );
  }
  var adapter = options.createAdapter({
    service: service,
    controller: options.controller,
    createLG: options.createLG,
    now: now,
    setInterval: schedule,
    clearInterval: unschedule,
    getOwner: adapterOwner,
    context: function (continuing) {
      return {
        popupSupported: continuing === true || canStart(),
        previewEligible: localForeground(),
        inAppEligible: localForeground(),
        globalTriggerVerified: globalMode(),
        globalEligible: foreignForeground(),
        idleTimeoutMs: state.idleTimeoutMs,
        clockOverlay: state.clockOverlay,
        clock: state.clock,
        quality: state.quality,
        mode: state.mode,
        assetId: state.assetId,
        personalMediaUrl: personalUrl()
      };
    },
    launch: function (id, params, done) {
      if (
        (!localForeground() && !foreignForeground()) ||
        id !== 'com.cleanyourtv.screensaver'
      )
        return done(false);
      var launchRevision = revision,
        launchPersonal = personal,
        settled = false;
      function completed(message) {
        if (settled) return;
        settled = true;
        var accepted = !!(
          message &&
          message.payload &&
          message.payload.returnValue === true
        );
        if (
          !accepted &&
          launchRevision === revision &&
          launchPersonal === personal
        )
          stop();
        done(accepted);
      }
      try {
        service.call(
          'luna://com.webos.applicationManager/launch',
          { id: id, params: params },
          completed
        );
      } catch (_) {
        completed(null);
      }
    }
  });
  function stop() {
    personal = null;
    if (monitor !== null) unschedule(monitor);
    monitor = null;
    if (releaseHold) releaseHold();
    releaseHold = null;
    var value = owner();
    if (value) adapter.stop(value.generation);
    binding = null;
    adapter.reconcile();
  }
  function invalidate(command) {
    if (
      command === 'status' &&
      globalMode() &&
      state.enabled &&
      monitor !== null
    )
      refreshFailed = true;
    else {
      stop();
      observation = null;
      expires = 0;
    }
    adapter.reconcile();
  }
  function apply(snapshot, began, expected) {
    if (disposed || expected !== revision) return false;
    var previous = observation && observation.owner;
    var previousExpires = expires;
    state = settings.normalize(snapshot && snapshot.state);
    observation = snapshot && typeof snapshot === 'object' ? snapshot : null;
    refreshFailed = false;
    if (
      personal &&
      (!observation ||
        !observation.owner ||
        observation.owner.generation !== personal.generation ||
        state.mode !== personal.mode ||
        state.assetId !== personal.assetId)
    )
      personal = null;
    var ttl = snapshot && snapshot.validForMs;
    var observedAt = snapshot && snapshot.observedAtMs;
    var received = now();
    expires =
      typeof observedAt === 'number' &&
      Math.floor(observedAt) === observedAt &&
      observedAt >= began &&
      observedAt <= received &&
      typeof ttl === 'number' &&
      isFinite(ttl) &&
      ttl > 0 &&
      ttl <= 1500
        ? observedAt + ttl
        : 0;
    if (expires > 0 && expires <= received) {
      // A reply that arrived expired cannot renew the retry window.
      var current = observation && observation.owner;
      expires =
        previous && current && previous.generation === current.generation
          ? Math.min(previousExpires, expires)
          : 0;
    }
    adapter.reconcile();
    if (globalMode() && state.enabled) {
      // Keep watching the saved opt-in even when boot or standby temporarily
      // prevents the runtime from attesting an owner.
      startMonitor();
      if (canStart()) adapter.enable(observation.owner.generation);
      else {
        personal = null;
        binding = null;
        adapter.reconcile();
      }
    } else if (!canStart()) stop();
    return true;
  }
  function execute(command, payload, expected) {
    var began;
    queue = queue
      .catch(function () {})
      .then(function () {
        if (disposed || expected !== revision) return null;
        began = now();
        return options.execute(command, payload);
      })
      .then(
        function (snapshot) {
          var retryable =
            command === 'status' &&
            snapshot &&
            snapshot.retryable === true &&
            snapshot.state &&
            snapshot.state.enabled === true &&
            snapshot.state.scope === 'global';
          if (snapshot && !retryable) {
            apply(snapshot, began, expected);
            return snapshot;
          }
          if (!disposed && expected === revision) invalidate(command);
          return null;
        },
        function () {
          if (!disposed && expected === revision) invalidate(command);
          return null;
        }
      );
    return queue;
  }
  function response(ok, started) {
    var result = {
      returnValue: ok,
      available: available(),
      state: settings.normalize(state)
    };
    if (started !== undefined) result.started = started;
    if (!result.available) result.reason = 'local-clock-owner-unavailable';
    return result;
  }
  function startMonitor() {
    if (monitor !== null) return;
    if (globalMode() && options.hold) releaseHold = options.hold();
    monitor = schedule(function () {
      if (binding) {
        var session = adapter.getSession();
        if (
          session &&
          session.generation === binding.generation &&
          session.visible === true &&
          session.focused === true &&
          typeof session.lastHeartbeatMs === 'number' &&
          now() >= session.lastHeartbeatMs &&
          now() - session.lastHeartbeatMs < 3000
        )
          binding.expires = Math.min(
            now() + 1500,
            session.lastHeartbeatMs + 3000
          );
      }
      adapter.reconcile();
      if (!canStart() && !(globalMode() && state.enabled)) {
        stop();
        return;
      }
      if (disposed || polling || !state.enabled) return;
      polling = true;
      execute('status', null, revision).then(function () {
        polling = false;
      });
    }, 500);
  }
  var methods = [
    'screensaverStatus',
    'screensaverConfigure',
    'screensaverPreview',
    'screensaverActivity',
    'screensaverEligible',
    'screensaverStop'
  ];
  methods.forEach(function (method) {
    service.register(method, function (message) {
      var caller;
      try {
        caller = message.ls2Message.applicationID();
      } catch (_) {}
      if (
        typeof caller !== 'string' ||
        caller.split(' ')[0] !== 'com.cleanyourtv.root.preview'
      ) {
        message.respond({
          returnValue: false,
          errorCode: 'caller-not-authorized'
        });
        return;
      }
      if (disposed) {
        message.respond(response(false, false));
        return;
      }
      var payload = message.payload || {},
        activation =
          method === 'screensaverPreview' || method === 'screensaverEligible',
        hasMedia = Object.prototype.hasOwnProperty.call(payload, 'mediaUrl');
      if (hasMedia && !activation) {
        revision += 1;
        stop();
        message.respond(response(false, false));
        return;
      }
      if (method === 'screensaverStop') {
        revision += 1;
        stop();
        message.respond(response(true));
        return;
      }
      var expected = revision,
        command = 'status';
      if (method === 'screensaverConfigure') {
        revision += 1;
        expected = revision;
        command = 'configure';
        stop();
        payload = settings.normalize(payload);
      }
      execute(command, command === 'configure' ? payload : null, expected).then(
        function (snapshot) {
          if (!snapshot || expected !== revision || disposed) {
            message.respond(response(false, false));
            return;
          }
          var value = owner();
          if (!activation && method !== 'screensaverActivity') {
            message.respond(response(true));
            return;
          }
          if (
            !localForeground() ||
            !value ||
            !adapter.enable(value.generation)
          ) {
            if (activation && !globalMode()) stop();
            message.respond(response(true, false));
            return;
          }
          startMonitor();
          if (!activation) {
            adapter.activity(value.generation);
            message.respond(response(true, false));
            return;
          }
          return adapter.whenReady(value.generation).then(function (ready) {
            var current = owner();
            if (
              !ready ||
              expected !== revision ||
              !localForeground() ||
              !current ||
              current.generation !== value.generation
            ) {
              message.respond(response(false, false));
              return;
            }
            personal = null;
            if (personalSelected()) {
              if (
                typeof settings.personalMediaUrl !== 'function' ||
                settings.personalMediaUrl(state.mode, payload.mediaUrl) !== true
              ) {
                stop();
                message.respond(response(false, false));
                return;
              }
              personal = {
                generation: value.generation,
                mode: state.mode,
                assetId: state.assetId,
                url: payload.mediaUrl
              };
            } else if (hasMedia) {
              stop();
              message.respond(response(false, false));
              return;
            }
            var started =
              method === 'screensaverPreview'
                ? adapter.preview(value.generation)
                : adapter.eligible(value.generation);
            if (started)
              binding = {
                generation: value.generation,
                expires: now() + 10000
              };
            else stop();
            message.respond(response(true, started));
          });
        }
      );
    });
  });
  return {
    resume: function () {
      return execute('status', null, revision);
    },
    dispose: function () {
      if (disposed) return;
      revision += 1;
      stop();
      disposed = true;
      adapter.dispose();
    }
  };
};
