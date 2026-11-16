'use strict';

// Only the existing authenticated Home-control consumer may call handle().
// Preferences are supplied by Home; capabilities and foreground are owner facts.
module.exports = function (options) {
  var settings = options.settings || require('./screensaver/settings');
  var createAdapter =
    options.createAdapter || require('./screensaver-controller');
  var now = options.now;
  var state = settings.normalize({});
  var installed = false;
  var foreground = null;
  var armed = false;
  var startingUntil = null;
  function globalMode() {
    return (
      state.scope === 'global' && !settings.personal(state.mode, state.assetId)
    );
  }
  var generation = options.generation;
  if (generation === undefined)
    generation = parseInt(require('crypto').randomBytes(6).toString('hex'), 16);
  if (options.loadSettings) {
    try {
      var saved = options.loadSettings();
      if (!validSettings(saved))
        throw new Error('Invalid saved screensaver settings');
      state = settings.normalize(saved);
    } catch (error) {
      if (error.code !== 'ENOENT') throw error;
    }
  }

  var personalMediaUrl = '';
  function healthy() {
    try {
      return options.healthy() === true;
    } catch (ignore) {
      return false;
    }
  }
  function available() {
    return (
      installed &&
      healthy() &&
      (state.scope === 'cytv' || globalMode()) &&
      (state.mode === 'ambient' ||
        state.mode === 'clock' ||
        !!settings.background(state.mode, state.assetId) ||
        settings.personal(state.mode, state.assetId))
    );
  }
  var adapter = createAdapter({
    generation: generation,
    service: options.service,
    now: now,
    log: options.log,
    context: function () {
      return {
        ownerHealthy: healthy(),
        popupSupported: available(),
        previewEligible: foreground === 'com.gathin.tvhome' && available(),
        inAppEligible: foreground === 'com.gathin.tvhome' && available(),
        globalEligible:
          state.enabled &&
          globalMode() &&
          available() &&
          typeof options.powerActive === 'function' &&
          options.powerActive() &&
          typeof foreground === 'string' &&
          !!foreground &&
          [
            'com.gathin.tvhome',
            'com.cleanyourtv.screensaver',
            'com.webos.app.screensaver',
            'com.webos.app.cpcover'
          ].indexOf(foreground) < 0,
        idleTimeoutMs: state.idleTimeoutMs,
        clockOverlay: state.clockOverlay,
        clock: state.clock,
        quality: state.quality,
        mode: state.mode,
        assetId: state.assetId,
        personalMediaUrl: personalMediaUrl
      };
    }
  });
  function stop() {
    armed = false;
    startingUntil = null;
    personalMediaUrl = '';
    adapter.stop();
  }
  function arm() {
    if (
      !state.enabled ||
      !available() ||
      (foreground !== 'com.gathin.tvhome' && !globalMode())
    )
      return false;
    if (!armed) armed = adapter.enable() === true;
    return armed;
  }
  function status(ok, started) {
    var reply = {
      returnValue: ok !== false,
      available: available(),
      state: settings.normalize(state)
    };
    if (started !== undefined) reply.started = started;
    if (!reply.available)
      reply.reason = !installed
        ? 'popup-unavailable'
        : !healthy()
          ? 'owner-unavailable'
          : state.scope !== 'cytv'
            ? 'global-media-unavailable'
            : 'media-unavailable';
    return reply;
  }
  function validSettings(value) {
    return !!(
      value &&
      typeof value === 'object' &&
      !Array.isArray(value) &&
      Object.keys(value).every(function (key) {
        return (
          [
            'assetId',
            'enabled',
            'idleTimeoutMs',
            'mode',
            'scope',
            'clockOverlay',
            'clock',
            'quality'
          ].indexOf(key) >= 0
        );
      }) &&
      (!Object.prototype.hasOwnProperty.call(value, 'clock') ||
        settings.clockPresentation(value.clock)) &&
      (!Object.prototype.hasOwnProperty.call(value, 'clockOverlay') ||
        typeof value.clockOverlay === 'boolean') &&
      (!Object.prototype.hasOwnProperty.call(value, 'quality') ||
        settings.qualities.indexOf(value.quality) >= 0) &&
      typeof value.enabled === 'boolean' &&
      (value.scope === 'cytv' || value.scope === 'global') &&
      ['ambient', 'clock', 'photo', 'video'].indexOf(value.mode) >= 0 &&
      typeof value.assetId === 'string' &&
      (!value.assetId || /^[A-Za-z0-9_-]{1,128}$/.test(value.assetId)) &&
      typeof value.idleTimeoutMs === 'number' &&
      isFinite(value.idleTimeoutMs)
    );
  }
  return {
    installed: function (ids) {
      installed =
        Array.isArray(ids) && ids.indexOf('com.cleanyourtv.screensaver') >= 0;
      if (!installed) stop();
      else if (globalMode()) arm();
    },
    foreground: function (id) {
      var previous = foreground;
      foreground = id;
      if (id === 'com.cleanyourtv.screensaver') {
        var session = adapter.getSession();
        if (!(
          armed &&
          ((adapter.ownsPopup && adapter.ownsPopup()) ||
            (session && session.generation === generation) ||
            (startingUntil !== null && now() < startingUntil))
        ))
          stop();
      } else if (globalMode()) {
        if (armed && !available()) stop();
        arm();
      } else if (
        id !== 'com.gathin.tvhome' ||
        previous === 'com.cleanyourtv.screensaver'
      )
        stop();
    },
    stop: stop,
    handle: function (method, payload, requestCurrent) {
      if (!healthy()) stop();
      if (method === 'screensaverStatus') return status(true);
      if (method === 'screensaverStop') {
        stop();
        return status(true);
      }
      if (method === 'screensaverConfigure') {
        if (!validSettings(payload)) return status(false);
        var nextState = settings.normalize(payload);
        try {
          if (options.saveSettings) options.saveSettings(nextState);
        } catch (ignore) {
          return status(false);
        }
        stop();
        state = nextState;
        arm();
        return status(true);
      }
      if (method === 'screensaverActivity') {
        if (foreground !== 'com.gathin.tvhome' || !arm()) return status(false);
        adapter.activity();
        return status(true);
      }
      if (method === 'screensaverPreview' || method === 'screensaverEligible') {
        var personal = settings.personal(state.mode, state.assetId);
        if (personal) {
          if (startingUntil !== null && now() < startingUntil)
            return status(true, false);
          if (
            !payload ||
            Object.keys(payload).join(',') !== 'mediaUrl' ||
            !settings.personalMediaUrl(state.mode, payload.mediaUrl)
          )
            return status(false);
        } else if (payload && Object.keys(payload).length) return status(false);
        if (foreground !== 'com.gathin.tvhome' || !arm())
          return status(true, false);
        return adapter.whenReady().then(function (ready) {
          if (
            !ready ||
            (requestCurrent && !requestCurrent()) ||
            !armed ||
            !available() ||
            foreground !== 'com.gathin.tvhome' ||
            (personal && startingUntil !== null && now() < startingUntil)
          )
            return status(true, false);
          personalMediaUrl = personal ? payload.mediaUrl : '';
          var started =
            (method === 'screensaverPreview'
              ? adapter.preview()
              : adapter.eligible()) === true;
          if (started) startingUntil = now() + 10000;
          else personalMediaUrl = '';
          return status(true, started);
        });
      }
      return status(false);
    }
  };
};
