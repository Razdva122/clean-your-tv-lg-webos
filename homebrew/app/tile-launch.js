(function (root) {
  'use strict';
  var own = Object.prototype.hasOwnProperty;
  function debloatRequested(event) {
    if (root.CYTVTileEdition !== null) return false;
    try {
      var value = event
        ? event.detail
        : root.PalmSystem && root.PalmSystem.launchParams;
      for (var depth = 0; depth < 4; depth++) {
        if (typeof value === 'string') {
          if (value.length > 4096) return false;
          value = JSON.parse(value);
        }
        if (!value || typeof value !== 'object' || Array.isArray(value))
          return false;
        if (own.call(value, 'params')) value = value.params;
        else
          return (
            Object.keys(value).length === 1 &&
            own.call(value, 'cytvDebloat') &&
            value.cytvDebloat === true
          );
      }
    } catch (_) {}
    return false;
  }
  function openDebloat(event) {
    if (
      (!event && root.location.hash === '#openHome') ||
      !debloatRequested(event)
    )
      return false;
    root.location.replace('debloat.html');
    return true;
  }
  root.CYTVTileLaunch = {
    debloatRequested: debloatRequested,
    openDebloat: openDebloat
  };
})(window);
