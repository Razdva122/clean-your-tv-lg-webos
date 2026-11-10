'use strict';
var core = require('./core');
var wallpaperCache = require('./wallpaper-cache');
var texts = {
  'caller-not-authorized': 'Caller is not authorized',
  'invalid-session': 'Receiver session is unavailable',
  'session-expired': 'Receiver session expired',
  'receiver-busy': 'Receiver is already active',
  'receiver-unavailable': 'Receiver could not start',
  'not-received': 'No theme has been received',
  'invalid-offset': 'Invalid read offset',
  'invalid-request': 'Invalid receiver request'
};
// webos-service exits a standalone service five seconds after its last
// activity ends. The HTTP listener is not an activity, so a session holds one;
// otherwise the process exits while the TV still shows the PIN.
function activityHold(service, prefix) {
  var manager = service && service.activityManager,
    sequence = 0;
  if (
    !manager ||
    typeof manager.create !== 'function' ||
    typeof manager.complete !== 'function'
  )
    return null;
  return function () {
    var activity = null,
      released = false;
    function complete(a) {
      try {
        manager.complete(a, function () {});
      } catch (_) {}
    }
    try {
      manager.create(
        prefix ? prefix + '-' + ++sequence : 'themeReceiver',
        function (a) {
          if (!a || !a.activityId) return;
          if (released) complete(a);
          else activity = a;
        }
      );
    } catch (_) {}
    return function () {
      released = true;
      if (activity) {
        var a = activity;
        activity = null;
        complete(a);
      }
    };
  };
}
function register(service, options) {
  options = options || {};
  if (!options.appId || typeof options.appId !== 'string')
    throw new Error('appId required');
  var settings = {};
  Object.keys(options).forEach(function (key) {
    settings[key] = options[key];
  });
  if (typeof settings.hold !== 'function')
    settings.hold = activityHold(service);
  var receiver = core.create(settings);
  var methods = {
    themeReceiverStart: 'start',
    themeReceiverStatus: 'status',
    themeReceiverRead: 'read',
    themeReceiverStop: 'stop'
  };
  Object.keys(methods).forEach(function (method) {
    service.register(method, function (message) {
      function fail(code) {
        message.respond({
          returnValue: false,
          errorCode: code,
          errorText: texts[code] || 'Receiver request failed'
        });
      }
      var id;
      try {
        id = message.ls2Message.applicationID();
      } catch (_) {
        fail('caller-not-authorized');
        return;
      }
      if (typeof id !== 'string' || id.split(' ')[0] !== options.appId) {
        fail('caller-not-authorized');
        return;
      }
      var payload = message.payload || {},
        operation = methods[method],
        result;
      if (
        operation !== 'start' &&
        (typeof payload.sessionId !== 'string' ||
          payload.sessionId.length > 128)
      ) {
        fail('invalid-request');
        return;
      }
      try {
        result = receiver[operation](
          operation === 'start' ? payload : payload.sessionId,
          payload.offset
        );
      } catch (e) {
        fail(texts[e.code] ? e.code : 'invalid-request');
        return;
      }
      Promise.resolve(result).then(
        function (value) {
          var response = { returnValue: true };
          Object.keys(value || {}).forEach(function (key) {
            response[key] = value[key];
          });
          message.respond(response);
        },
        function (e) {
          fail(texts[e.code] ? e.code : 'receiver-unavailable');
        }
      );
    });
  });
  var cacheSettings = {};
  Object.keys(settings).forEach(function (key) {
    cacheSettings[key] = settings[key];
  });
  if (typeof options.hold !== 'function')
    cacheSettings.hold = activityHold(service, 'wallpaperMedia');
  var cache = wallpaperCache.create(cacheSettings);
  var cacheMethods = {
    wallpaperCacheStart: 'start',
    wallpaperCacheWrite: 'write',
    wallpaperCacheCommit: 'commit',
    wallpaperCacheKeepAlive: 'keepAlive',
    wallpaperCacheStop: 'stop'
  };
  Object.keys(cacheMethods).forEach(function (method) {
    service.register(method, function (message) {
      var caller;
      try {
        caller = message.ls2Message.applicationID();
      } catch (_) {}
      if (
        typeof caller !== 'string' ||
        caller.split(' ')[0] !== options.appId
      ) {
        message.respond({
          returnValue: false,
          errorCode: 'caller-not-authorized'
        });
        return;
      }
      Promise.resolve()
        .then(function () {
          return cache[cacheMethods[method]](message.payload || {});
        })
        .then(
          function (value) {
            var response = { returnValue: true };
            Object.keys(value || {}).forEach(function (key) {
              response[key] = value[key];
            });
            message.respond(response);
          },
          function (error) {
            var response = {
              returnValue: false,
              errorCode: 'wallpaper-cache-unavailable'
            };
            if (error && error.code === 'wallpaper-cache-storage-full') {
              response.errorCode = error.code;
              response.storage = error.storage;
            } else if (
              error &&
              (error.code === 'ENOSPC' || error.code === 'EDQUOT')
            )
              response.errorCode = 'wallpaper-cache-storage-full';
            message.respond(response);
          }
        );
    });
  });
  return receiver;
}
module.exports = register;
module.exports.register = register;
module.exports.activityHold = activityHold;
