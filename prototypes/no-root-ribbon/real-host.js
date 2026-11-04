/* Native window shell only. Product service calls remain inside the locked mock. */
(function () {
  'use strict';
  var native = window.webOSSystem || window.PalmSystem;
  var nativeClose = window.close.bind(window);
  var mode = 'full', closed = false, timer, readyTimer;
  try {
    var params = native ? native.launchParams : {};
    if (typeof params === 'string') params = JSON.parse(params);
    if (params && !Array.isArray(params) && params.mode === 'overlay' || !native && location.search === '?mode=overlay') mode = 'overlay';
  } catch (_) { /* Missing or malformed context stays opaque. */ }
  function close() {
    if (closed) return;
    closed = true; clearTimeout(timer); clearInterval(readyTimer);
    if (window.HomeWallpaper) HomeWallpaper.suspend('no-root-lab');
    if (window.HomePresentationController) HomePresentationController.hide();
    nativeClose();
  }
  window.close = close;
  Object.defineProperty(window, 'RibbonLab', {value:Object.freeze({mode:mode}), writable:false, configurable:false});
  document.documentElement.setAttribute('data-lab-pending', 'true');
  timer = setTimeout(close, 60000);
  var started = Date.now(), activated = false;
  readyTimer = setInterval(function () {
    var controller = window.HomePresentationController;
    var ready = window.RootLauncherRendered === true && controller && controller.state().mode === mode;
    if (!ready && Date.now() - started < 10000) return;
    clearInterval(readyTimer);
    document.documentElement.removeAttribute('data-lab-pending');
    if (!closed && !activated && native && typeof native.activate === 'function') {
      activated = true; native.activate();
    }
  }, 50);
}());
