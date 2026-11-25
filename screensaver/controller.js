'use strict';

var crypto = require('crypto');
var policy = require('./policy');
var transport = require('./transport');
var settings = require('./settings');
var popupId = 'com.cleanyourtv.screensaver';

function monotonic() {
  var sample = process.hrtime();
  return sample[0] * 1000 + Math.floor(sample[1] / 1000000);
}

function create(options) {
  var now = options.now || monotonic;
  var set = options.setInterval || setInterval;
  var clear = options.clearInterval || clearInterval;
  var state = policy.createInitialState(options.generation);
  var wire,
    timer,
    disposed = false;
  var readiness, resolveReadiness, listenFailed;
  var media = null;
  var bundledFailed = null;
  var globalOffer = null;

  function releaseMedia() {
    var current = media;
    media = null;
    try {
      if (current) current.lease.release();
    } catch (_) {}
  }
  function ownsActivation(effect) {
    return (
      !disposed &&
      !!wire &&
      state.phase === 'starting' &&
      state.sessionId === effect.sessionId &&
      state.generation === effect.generation
    );
  }
  function acquireMedia(effect) {
    if (!options.acquireMedia) return;
    try {
      var item = options.acquireMedia();
      if (!item || !item.lease) return;
      var valid =
        (item.mode === 'video' && item.lease.contentType === 'video/mp4') ||
        (item.mode === 'photo' &&
          ['image/jpeg', 'image/png', 'image/webp'].indexOf(
            item.lease.contentType
          ) !== -1);
      if (
        !ownsActivation(effect) ||
        !valid ||
        typeof item.lease.serve !== 'function' ||
        typeof item.lease.release !== 'function'
      ) {
        if (typeof item.lease.release === 'function') item.lease.release();
        return;
      }
      media = { mode: item.mode, lease: item.lease };
    } catch (_) {}
  }

  function session() {
    return state.sessionId
      ? { sessionId: state.sessionId, generation: state.generation }
      : null;
  }
  function context() {
    var source = options.context() || {};
    var trusted = {};
    Object.keys(source).forEach(function (key) {
      trusted[key] = source[key];
    });
    trusted.ownerGeneration = options.generation;
    trusted.popupSupported =
      !!wire && !disposed && source.popupSupported === true;
    return trusted;
  }
  function event(type, identity) {
    var value = { type: type, generation: options.generation };
    if (identity) value.sessionId = identity.sessionId;
    return value;
  }
  function dispatch(message) {
    var result = policy.transition(state, message, context(), now());
    state = result.state;
    result.effects.forEach(function (effect) {
      if (effect.type === 'CLOSE' || effect.type === 'RELEASE') {
        releaseMedia();
        if (options.closePopup) options.closePopup(effect);
      }
      if (effect.type !== 'LAUNCH' || !ownsActivation(effect)) return;
      acquireMedia(effect);
      if (!ownsActivation(effect)) return;
      var params = {
        sessionId: effect.sessionId,
        generation: effect.generation,
        endpoint: wire.endpoint
      };
      function reported(ok) {
        if (ok !== true) dispatch(event('CLOSE', params));
      }
      try {
        options.launch(popupId, params, reported);
      } catch (_) {
        reported(false);
      }
    });
    if (globalOffer && state.phase !== 'starting') {
      var offer = globalOffer;
      globalOffer = null;
      offer.done(
        state.phase === 'visible' && state.sessionId === offer.sessionId
      );
    }
  }
  function update(payload) {
    var current = session();
    if (
      !current ||
      current.sessionId !== payload.sessionId ||
      current.generation !== payload.generation
    )
      return { close: true };
    var preference = context();
    var bundled =
      bundledFailed !== current.sessionId &&
      settings.background(preference.mode, preference.assetId);
    if (bundled && bundled.mode === 'video' && preference.quality === 'image')
      bundled = settings.background(
        'photo',
        bundled.id.replace(/-video$/, '-photo')
      );
    var personal =
      bundledFailed !== current.sessionId &&
      settings.personal(preference.mode, preference.assetId) &&
      settings.personalMediaUrl(preference.mode, preference.personalMediaUrl);
    payload = {
      schema: payload.schema,
      sessionId: payload.sessionId,
      generation: payload.generation,
      visible: payload.visible,
      focused: payload.focused,
      mediaState: payload.mediaState
    };
    if (payload.mediaState === 'closed') payload.type = 'CLOSED';
    else if (payload.mediaState === 'error') {
      if (state.phase === 'starting' && (media || bundled || personal)) {
        releaseMedia();
        bundledFailed = current.sessionId;
        bundled = null;
        personal = false;
      } else payload.type = 'CLOSE';
    } else if (state.phase === 'starting' && payload.mediaState === 'ready')
      payload.type = 'READY';
    else if (state.phase === 'visible') payload.type = 'HEARTBEAT';
    if (payload.type) dispatch(payload);
    current = session();
    if (
      !current ||
      current.sessionId !== payload.sessionId ||
      state.phase === 'closing' ||
      disposed
    )
      return { close: true };
    var content = media
      ? {
          mode: media.mode,
          url: wire.endpoint + '/media/' + current.sessionId,
          clockOverlay: preference.clockOverlay === true
        }
      : bundled
        ? {
            mode: bundled.mode,
            assetId: bundled.id,
            quality: preference.quality,
            clockOverlay: preference.clockOverlay === true
          }
        : personal
          ? {
              mode: /\.mp4$/.test(preference.personalMediaUrl)
                ? 'video'
                : 'photo',
              cacheUrl: preference.personalMediaUrl,
              clockOverlay: preference.clockOverlay === true
            }
          : preference.mode === 'clock'
            ? { mode: 'clock' }
            : {
                mode: 'ambient',
                clockOverlay: preference.clockOverlay === true
              };
    var clock = settings.clockPresentation(preference.clock);
    if (clock) content.clock = clock;
    return { close: false, content: content };
  }
  function maybeStart(type) {
    if (!wire || disposed) return false;
    var id;
    try {
      id = crypto.randomBytes(24).toString('hex');
    } catch (_) {
      return false;
    }
    dispatch(event(type, { sessionId: id }));
    return state.sessionId === id && state.phase === 'starting';
  }
  function tick() {
    if (state.sessionId) dispatch(event('DEADLINE', session()));
  }
  (options.listen || transport.listen)(
    session,
    update,
    function (error, channel) {
      if (error) {
        listenFailed = true;
        if (resolveReadiness) resolveReadiness(false);
        return;
      }
      if (disposed) return channel.close();
      wire = channel;
      timer = set(tick, 250);
      if (resolveReadiness) resolveReadiness(true);
    },
    function (identity, req, res) {
      if (
        !media ||
        disposed ||
        identity.sessionId !== state.sessionId ||
        identity.generation !== state.generation ||
        (state.phase !== 'starting' && state.phase !== 'visible')
      )
        return false;
      media.lease.serve(req, res);
      return true;
    }
  );

  return {
    whenReady: function () {
      if (disposed || listenFailed) return Promise.resolve(false);
      if (wire) return Promise.resolve(true);
      if (!readiness)
        readiness = new Promise(function (resolve) {
          resolveReadiness = resolve;
        });
      return readiness;
    },
    enable: function () {
      if (!disposed) dispatch(event('ENABLE'));
    },
    preview: function () {
      return maybeStart('PREVIEW');
    },
    eligible: function () {
      return maybeStart('ELIGIBLE');
    },
    startGlobal: function (done) {
      if (!maybeStart('GLOBAL')) return null;
      var identity = session();
      globalOffer = { sessionId: identity.sessionId, done: done };
      return function () {
        dispatch(event('CLOSE', identity));
      };
    },
    ownsPopup: function () {
      return state.phase === 'starting' || state.phase === 'visible';
    },
    activity: function () {
      dispatch(event('ACTIVITY', session()));
    },
    powerInactive: function () {
      dispatch(event('POWER_INACTIVE'));
    },
    stop: function () {
      dispatch(event('OWNER_STOP'));
    },
    dispose: function () {
      dispatch(event('OWNER_STOP'));
      disposed = true;
      if (resolveReadiness) resolveReadiness(false);
      if (timer !== undefined) clear(timer);
      if (wire) wire.close();
      wire = null;
    },
    getSession: function () {
      var capability = context();
      if (
        state.phase !== 'visible' ||
        capability.popupSupported !== true ||
        capability.ownerHealthy !== true
      )
        return null;
      return {
        state: 'visible',
        sessionId: state.sessionId,
        generation: state.generation,
        visible: state.visible,
        focused: state.focused,
        lastHeartbeatMs: state.heartbeatAtMs
      };
    }
  };
}

exports.create = create;
exports.monotonic = monotonic;
