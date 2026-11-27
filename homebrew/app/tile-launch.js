(function (root) {
  'use strict';
  var own = Object.prototype.hasOwnProperty;
  function requested(event, flag) {
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
            own.call(value, flag) &&
            value[flag] === true
          );
      }
    } catch (_) {}
    return false;
  }
  function debloatRequested(event) {
    return root.CYTVTileEdition === null && requested(event, 'cytvDebloat');
  }
  function maintenanceRequested(event) {
    return (
      (root.CYTVTileEdition === null || root.CYTVTileEdition === 'root') &&
      requested(event, 'cytvMaintenance')
    );
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
    openDebloat: openDebloat,
    maintenanceRequested: maintenanceRequested,
    openMaintenance: function (event) {
      if (
        (!event && root.location.hash === '#openHome') ||
        !maintenanceRequested(event)
      )
        return false;
      root.location.replace(
        root.CYTVTileEdition === null
          ? 'setup.html#maintenance'
          : 'recovery.html'
      );
      return true;
    }
  };
})(window);
