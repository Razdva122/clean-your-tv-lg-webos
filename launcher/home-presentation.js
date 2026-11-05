/* Root presentation owns window transparency; themes only request a mode. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.HomePresentation = factory();
}(this, function () {
  'use strict';
  // A launch hint selects a request generation; only Helper's live reply can
  // establish content. Missing, stale or cross-generation facts stay unknown.
  function nativeContext(reply, expected, elapsed) {
    function generation(value) {
      return typeof value === 'number' && isFinite(value) && value >= 0 &&
        Math.floor(value) === value && value <= 9007199254740991;
    }
    if (elapsed === undefined) elapsed = 0;
    if (typeof elapsed !== 'number' || !isFinite(elapsed) || elapsed < 0 ||
        !generation(expected) || !reply || reply.returnValue !== true ||
        typeof reply.eligible !== 'boolean' || !generation(reply.generation) ||
        (reply.content !== null && typeof reply.content !== 'boolean') ||
        (reply.eligible && reply.content !== true) ||
        reply.generation !== expected || typeof reply.observedAgeMs !== 'number' ||
        !isFinite(reply.observedAgeMs) || reply.observedAgeMs < 0 || reply.observedAgeMs + elapsed > 2000) return null;
    return {eligible:reply.eligible, content:reply.content};
  }
  function create(options) {
    var generation = 0, launchGeneration = 0, visible = false, mode = 'closed', overlayTheme = false;
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
      // Native No-root still requires its ordinary typed Helper activation seam.
      if (!visible || !options.supported || !options.decoderContext && ((!overlayTheme && !options.queryFull) || startup || opaque)) return;
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
      activationUntil = 0;
      params = params || {};
      activation = params;
      startup = params.activateType === 'powerOn' || params.reason === 'boot' || params.reason === 'startup';
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
