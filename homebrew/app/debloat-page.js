(function (root) {
  'use strict';
  root.CYTVDebloatPage = true;
  root.document.addEventListener('webOSRelaunch', function (event) {
    if (!root.CYTVTileLaunch.debloatRequested(event))
      root.location.replace('index.html#openHome');
  });
})(window);
