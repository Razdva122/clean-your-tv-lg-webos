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
// The service's LS2 role deliberately does not grant compositor access.
// Use the existing Root broker pattern with a fixed command and bounded reply.
module.exports = function (execFile, uid) {
  return function () {
    return new Promise(function (resolve) {
      if (uid() !== 0) { resolve({content:null}); return; }
      try {
        execFile('/usr/bin/luna-send',
          ['-n', '1', 'luna://com.webos.surfacemanager/getForegroundAppInfo', '{}'],
          {timeout:1500, maxBuffer:65536}, function (error, stdout) {
            if (error || typeof stdout !== 'string' || stdout.length > 65536) {
              resolve({content:null}); return;
            }
            try { resolve({content:content(JSON.parse(stdout))}); }
            catch (_) { resolve({content:null}); }
          });
      } catch (_) { resolve({content:null}); }
    });
  };
};
