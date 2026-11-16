(function (root, factory) {
  var policy = factory();
  if (typeof module === 'object' && module.exports) module.exports = policy;
  else root.CYTVScreensaverPolicy = policy;
})(this, function () {
  'use strict';

  function validGeneration(value) {
    return (
      typeof value === 'number' &&
      isFinite(value) &&
      value >= 0 &&
      value <= 9007199254740991 &&
      Math.floor(value) === value
    );
  }

  function createInitialState(generation) {
    if (!validGeneration(generation))
      throw new Error('Invalid owner generation');
    return {
      phase: 'disabled',
      enabled: false,
      generation: generation,
      sessionId: null,
      sequence: 0,
      lastActivityAtMs: null,
      requiresActivity: true,
      startedAtMs: null,
      heartbeatAtMs: null,
      closingAtMs: null,
      lastNowMs: null,
      visible: false,
      focused: false
    };
  }

  // Adapters supply monotonic time and authenticated observations. This module
  // performs no I/O and never controls another application's playback.
  function transition(previous, event, context, nowMs) {
    var state = {};
    var effects = [];
    var key;
    for (key in previous) {
      if (Object.prototype.hasOwnProperty.call(previous, key))
        state[key] = previous[key];
    }
    event = event || {};
    context = context || {};

    function result() {
      return { state: state, effects: effects };
    }
    function ownedEffect(type, reason) {
      var effect = {
        type: type,
        sessionId: state.sessionId,
        generation: state.generation
      };
      if (reason) effect.reason = reason;
      effects.push(effect);
    }
    function active() {
      return state.phase === 'starting' || state.phase === 'visible';
    }
    function duration(name, fallback) {
      var value = context[name];
      return typeof value === 'number' && isFinite(value) && value > 0
        ? value
        : fallback;
    }
    function finish() {
      if (state.sessionId) ownedEffect('RELEASE');
      state.phase = state.enabled ? 'armed' : 'disabled';
      state.sessionId = null;
      state.requiresActivity = true;
      state.lastActivityAtMs = null;
      state.startedAtMs = null;
      state.heartbeatAtMs = null;
      state.closingAtMs = null;
      state.visible = false;
      state.focused = false;
    }
    function close(reason) {
      if (!active()) return;
      ownedEffect('CLOSE', reason);
      state.phase = 'closing';
      state.closingAtMs = nowMs;
      state.visible = false;
      state.focused = false;
      state.requiresActivity = true;
    }
    function sameSession() {
      return (
        !!state.sessionId &&
        event.sessionId === state.sessionId &&
        event.generation === state.generation
      );
    }
    function supported() {
      return (
        context.popupSupported === true &&
        context.ownerHealthy === true &&
        context.ownerGeneration === state.generation
      );
    }
    function fresh() {
      return (
        state.heartbeatAtMs !== null &&
        nowMs >= state.heartbeatAtMs &&
        nowMs - state.heartbeatAtMs < duration('heartbeatTimeoutMs', 5000)
      );
    }
    function respondLG() {
      effects.push({
        type: 'RESPOND_LG',
        request: event.request,
        allow: !(
          state.phase === 'visible' &&
          state.visible &&
          state.focused &&
          supported() &&
          fresh()
        )
      });
    }

    if (
      validGeneration(context.ownerGeneration) &&
      context.ownerGeneration !== state.generation
    ) {
      close('owner-generation-changed');
      state.enabled = false;
      finish();
      state = createInitialState(context.ownerGeneration);
      if (event.type === 'LG_REQUEST') respondLG();
      return result();
    }

    // Late renderer/input messages cannot mutate a different activation.
    if (
      (event.type === 'READY' || event.type === 'HEARTBEAT') &&
      (event.schema !== 1 || !sameSession())
    )
      return result();
    if (
      (event.type === 'CLOSE' ||
        event.type === 'CLOSED' ||
        event.type === 'FOCUS_LOST') &&
      !sameSession()
    )
      return result();
    if (
      (event.type === 'ACTIVITY' || event.type === 'DEADLINE') &&
      ((event.generation !== undefined &&
        event.generation !== state.generation) ||
        (event.sessionId !== undefined && !sameSession()))
    )
      return result();

    if (
      typeof nowMs !== 'number' ||
      !isFinite(nowMs) ||
      nowMs < 0 ||
      (state.lastNowMs !== null && nowMs < state.lastNowMs)
    ) {
      // Retain a usable close deadline even when a caller's clock fails.
      nowMs = state.lastNowMs === null ? 0 : state.lastNowMs;
      close('invalid-clock');
      if (event.type === 'LG_REQUEST') respondLG();
      return result();
    }
    state.lastNowMs = nowMs;
    if (active() && !supported()) close('owner-unavailable');
    if (
      state.phase === 'starting' &&
      nowMs - state.startedAtMs >= duration('launchTimeoutMs', 10000)
    ) {
      close('launch-timeout');
    }
    if (state.phase === 'visible' && !fresh()) close('heartbeat-timeout');
    if (
      state.phase === 'closing' &&
      nowMs - state.closingAtMs >= duration('closeTimeoutMs', 2000)
    ) {
      finish();
    }

    switch (event.type) {
      case 'ENABLE':
        state.enabled = true;
        if (state.phase === 'disabled') state.phase = 'armed';
        break;
      case 'DISABLE':
        state.enabled = false;
        close('disabled');
        if (state.phase === 'armed') finish();
        break;
      case 'OWNER_STOP':
        state.enabled = false;
        close('owner-stop');
        finish();
        break;
      case 'POWER_INACTIVE':
        close('power-inactive');
        state.requiresActivity = true;
        state.lastActivityAtMs = null;
        break;
      case 'ACTIVITY':
        if (active()) close('activity');
        else if (state.phase === 'armed') {
          state.lastActivityAtMs = nowMs;
          state.requiresActivity = false;
        }
        break;
      case 'PREVIEW':
      case 'ELIGIBLE':
      case 'GLOBAL':
        if (
          state.phase !== 'armed' ||
          !supported() ||
          event.generation !== state.generation ||
          typeof event.sessionId !== 'string' ||
          !event.sessionId ||
          event.sessionId.length > 256
        )
          break;
        if (event.type === 'PREVIEW') {
          if (context.previewEligible !== true) break;
        } else if (event.type === 'GLOBAL') {
          if (context.globalEligible !== true) break;
        } else {
          if (
            context.inAppEligible !== true ||
            state.requiresActivity ||
            state.lastActivityAtMs === null ||
            nowMs - state.lastActivityAtMs < duration('idleTimeoutMs', 60000)
          )
            break;
        }
        state.phase = 'starting';
        state.sessionId = event.sessionId;
        state.sequence += 1;
        state.startedAtMs = nowMs;
        state.heartbeatAtMs = null;
        state.visible = false;
        state.focused = false;
        state.requiresActivity = true;
        ownedEffect('LAUNCH');
        break;
      case 'READY':
      case 'HEARTBEAT':
        if (
          !active() ||
          (event.type === 'HEARTBEAT' && state.phase !== 'visible')
        )
          break;
        if (
          event.visible !== true ||
          event.focused !== true ||
          event.mediaState !== 'ready'
        ) {
          close('renderer-unavailable');
          break;
        }
        state.phase = 'visible';
        state.visible = true;
        state.focused = true;
        state.heartbeatAtMs = nowMs;
        break;
      case 'FOCUS_LOST':
        close('focus-lost');
        break;
      case 'CLOSE':
        close('requested');
        break;
      case 'CLOSED':
        finish();
        break;
      case 'LG_REQUEST':
        respondLG();
        break;
    }
    return result();
  }

  return { createInitialState: createInitialState, transition: transition };
});
