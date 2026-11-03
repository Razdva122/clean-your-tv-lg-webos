'use strict';
// Only sanitized facts leave this fixed, read-only compositor query.
var excluded = ['com.cleanyourtv.root.preview', 'com.gathin.tvhome', 'com.local.nativehome',
  'com.webos.app.home', 'com.webos.app.fullhome', 'com.webos.app.homeconnect', 'com.webos.app.cpcover',
  'com.webos.app.screensaver', 'com.webos.app.systemui', 'com.palm.app.settings',
  'com.webos.app.settings', 'com.webos.app.inputpicker', 'com.webos.app.boot'];
function content(response) {
  if (!response || response.returnValue !== true || !Array.isArray(response.foregroundAppInfo) ||
      response.foregroundAppInfo.length > 128) return null;
  var surfaces = response.foregroundAppInfo;
  if (surfaces.some(function (surface) {
    return !surface || typeof surface.appId !== 'string' || !surface.appId || typeof surface.windowType !== 'string';
  })) return null;
  if (surfaces.some(function (surface) {
    if (surface.displayId !== undefined && surface.displayId !== 0) return false;
    return surface.pip === true || surface.multiview === true ||
      surface.viewType !== undefined && surface.viewType !== 'normal' ||
      surface.windowType !== '_WEBOS_WINDOW_TYPE_CARD' && surface.appId !== 'com.cleanyourtv.root.preview';
  })) return null;
  return surfaces.some(function (surface) {
    return (surface.displayId === undefined || surface.displayId === 0) &&
      surface.windowType === '_WEBOS_WINDOW_TYPE_CARD' && excluded.indexOf(surface.appId) < 0;
  });
}
module.exports = function (service, uid) {
  return function () {
    return new Promise(function (resolve) {
      if (uid() !== 0) { resolve({content:null}); return; }
      var done = false, request;
      function finish(value) {
        if (done) return;
        done = true;
        clearTimeout(timer);
        if (request && typeof request.cancel === 'function') { try { request.cancel(); } catch (_) {} }
        resolve({content:value});
      }
      var timer = setTimeout(function () { finish(null); }, 2000);
      try {
        request = service.call('luna://com.webos.surfacemanager/getForegroundAppInfo', {}, function (response) {
          finish(content(response && response.payload));
        });
      } catch (_) { finish(null); }
    });
  };
};
