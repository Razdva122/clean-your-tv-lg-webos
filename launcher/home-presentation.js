/* Root presentation owns window transparency; themes only request a mode. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.HomePresentation = factory();
}(this, function () {
  'use strict';
  function create(options) {
    var generation = 0, visible = false, mode = 'closed', overlayTheme = false;
    var owners = Object.create(null), startup = false, blocked = false, activationUntil = 0;
    var now = options.now || Date.now;
    function isBlocked() { return Object.keys(owners).length > 0 || !!(options.blocked && options.blocked()); }
    function state() { return {mode:mode, visible:visible}; }
    function render() { if (options.render) options.render(state()); }
    function refresh() {
      var request = ++generation, settled = false;
      mode = visible ? 'full' : 'closed'; blocked = isBlocked(); render();
      if (!visible || !options.supported || !overlayTheme || startup || blocked) return;
      try {
        options.query(function (content) {
          if (settled || generation !== request || !visible) return;
          settled = true;
          mode = content === true && !isBlocked() ? 'overlay' : 'full'; render();
        });
      } catch (_) { /* Unknown platform context retains the opaque Home. */ }
    }
    function show(params) {
      activationUntil = 0;
      params = params || {};
      startup = params.activateType === 'powerOn' || params.reason === 'boot' || params.reason === 'startup';
      visible = true; refresh();
    }
    function hide() { activationUntil = 0; generation++; visible = false; mode = 'closed'; render(); }
    function dismiss() {
      if (!visible || mode !== 'overlay' || isBlocked()) return false;
      hide(); if (options.close) options.close(); return true;
    }
    return {
      state:state,
      token:function () { return generation; },
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
        if (activating || !dismiss()) show(params);
      },
      launched:function (token) {
        if (token !== generation || !options.supported || !visible || isBlocked()) return false;
        hide(); if (options.close) options.close(); return true;
      },
      setTheme:function (layout) { overlayTheme = !!layout && layout.presentation === 'overlay'; refresh(); },
      suspend:function (owner) { owners[owner] = true; refresh(); },
      resume:function (owner) { if (owners[owner]) { delete owners[owner]; refresh(); } },
      sync:function () { if (blocked !== isBlocked()) refresh(); }
    };
  }
  return {create:create};
}));
