/* Root presentation owns window transparency; themes only request a mode. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.HomePresentation = factory();
}(this, function () {
  'use strict';
  // A launch hint selects a request generation; only Helper's live reply can
  // establish content. Explicit decoder-only requests have no activation generation
  // and force opacity; missing, stale or cross-generation Home facts stay unknown.
  function nativeContext(reply, expected, elapsed, decoderOnly) {
    function generation(value) {
      return typeof value === 'number' && isFinite(value) && value >= 0 &&
        Math.floor(value) === value && value <= 9007199254740991;
    }
    if (elapsed === undefined) elapsed = 0;
    if (typeof elapsed !== 'number' || !isFinite(elapsed) || elapsed < 0 ||
        (decoderOnly === true ? expected !== null : !generation(expected)) ||
        !reply || reply.returnValue !== true ||
        typeof reply.eligible !== 'boolean' || !generation(reply.generation) ||
        (reply.content !== null && typeof reply.content !== 'boolean') ||
        (reply.eligible && reply.content !== true) ||
        (decoderOnly !== true && reply.generation !== expected) || typeof reply.observedAgeMs !== 'number' ||
        !isFinite(reply.observedAgeMs) || reply.observedAgeMs < 0 || reply.observedAgeMs + elapsed > 2000) return null;
    return {eligible:decoderOnly === true ? false : reply.eligible, content:reply.content};
  }
  function create(options) {
    var generation = 0, launchGeneration = 0, activationGeneration = 0, visible = false, mode = 'closed', overlayTheme = false;
    var owners = Object.create(null), startup = false, blocked = false, opaque = false, activationUntil = 0, content = null;
    var now = options.now || Date.now, activation = {};
    function isBlocked() { return Object.keys(owners).length > 0 || !!(options.blocked && options.blocked()); }
    function isOpaque() { return Object.keys(owners).length > 0 || !!(options.opaque ? options.opaque() : options.blocked && options.blocked()); }
    function state() { return {mode:mode, visible:visible, content:content}; }
    function render() { if (options.render) options.render(state()); }
    function refresh() {
      var request = ++generation, settled = false; launchGeneration++;
      content = null;
      mode = visible ? 'full' : 'closed'; blocked = isBlocked(); opaque = isOpaque(); render();
      // Root must query decoder context even while opaque or starting up.
      // No-root also queries while opaque; only typed fresh facts release its decoder.
      if (!visible || !options.supported || !options.decoderContext && !options.queryFull && (!overlayTheme || startup || opaque)) return;
      try {
        options.query(function (value) {
          if (settled || generation !== request || !visible) return;
          settled = true;
          var eligible = value === true;
          content = typeof value === 'boolean' ? value : null;
          if (options.queryFull && value && typeof value === 'object') {
            content = typeof value.content === 'boolean' ? value.content : null;
            eligible = value.eligible === true && content === true;
          }
          mode = eligible && overlayTheme && !startup && !isOpaque() ? 'overlay' : 'full'; render();
        }, activation);
      } catch (_) { /* Unknown platform context retains the opaque Home. */ }
    }
    function show(params) {
      activationGeneration++;
      activationUntil = 0;
      params = params || {};
      // Retain only activation primitives; caller mutation is not a new show.
      activation = {};
      if (typeof params.reason === 'string') activation.reason = params.reason;
      if (typeof params.activateType === 'string') activation.activateType = params.activateType;
      var hint = params.cytvHome;
      if (hint !== undefined || Object.prototype.hasOwnProperty.call(params, 'cytvHome')) {
        activation.cytvHome = hint && typeof hint === 'object' ? {
          reason: typeof hint.reason === 'string' ? hint.reason : null,
          generation: typeof hint.generation === 'number' ? hint.generation : null
        } : null;
      }
      startup = activation.activateType === 'powerOn' || activation.reason === 'boot' || activation.reason === 'startup';
      visible = true; refresh();
    }
    function hide() { activationUntil = 0; generation++; launchGeneration++; visible = false; content = null; mode = 'closed'; render(); }
    function dismiss(overlayOnly) {
      if (!visible || (mode !== 'overlay' && (overlayOnly || !options.dismissFull)) || isBlocked()) return false;
      hide(); if (options.close) options.close(); return true;
    }
    return {
      state:state,
      token:function () { return launchGeneration; },
      activationToken:function () { return activationGeneration; },
      show:show,
      hide:hide,
      dismiss:dismiss,
      visibility:function (shown, params) {
        if (!shown) { hide(); return; }
        if (!visible) {
          show(params);
          // Firmware can expose the window before delivering its activation relaunch.
          // Coalesce that short transition; a later Home is never permanently swallowed.
          activationUntil = now() + 500;
        }
      },
      relaunch:function (params, hidden) {
        var activating = hidden || now() < activationUntil;
        activationUntil = 0;
        if (activating || (options.toggle && !options.toggle(params)) || !dismiss(true)) show(params);
      },
      launched:function (token) {
        if (token !== launchGeneration || !options.supported || !visible || isBlocked()) return false;
        hide(); if (options.close) options.close(); return true;
      },
      setTheme:function (layout) { overlayTheme = !!layout && layout.presentation === 'overlay'; refresh(); },
      suspend:function (owner) { owners[owner] = true; refresh(); },
      resume:function (owner) { if (owners[owner]) { delete owners[owner]; refresh(); } },
      sync:function () {
        if (opaque !== isOpaque()) refresh();
        else if (blocked !== isBlocked()) { blocked = isBlocked(); launchGeneration++; }
      }
    };
  }
  return {create:create, nativeContext:nativeContext};
}));
