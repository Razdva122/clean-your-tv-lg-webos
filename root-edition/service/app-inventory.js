'use strict';
// Diagnostic categories only; never expose raw bus replies or child output.
function failure(message, reason, reply) {
  var error = Error(message),
    detail = { reason: reason };
  if (reply && reply.returnValue === false) {
    var text =
      typeof reply.errorText === 'string'
        ? reply.errorText.slice(0, 1024).toLowerCase()
        : '';
    if (/denied method|permission denied|access denied/.test(text))
      detail.reason = 'permission-denied';
    else if (/service does not exist|service is not registered/.test(text))
      detail.reason = 'service-missing';
    else if (/unknown method|method does not exist/.test(text))
      detail.reason = 'method-missing';
    var code = reply.errorCode;
    if (
      typeof code === 'number' &&
      Math.floor(code) === code &&
      code >= -2147483648 &&
      code <= 2147483647
    )
      detail.error_code = code;
  }
  error.inventory = detail;
  return error;
}

function clientReason(error) {
  if (error.code === 'ENOENT' || error.code === 'EACCES')
    return 'client-start-failed';
  if (
    error.code === 'ERR_CHILD_PROCESS_STDIO_MAXBUFFER' ||
    /^(stdout|stderr) maxBuffer/.test(error.message || '')
  )
    return 'oversized-reply';
  if (
    error.code === 'ETIMEDOUT' ||
    (error.killed === true && error.signal === 'SIGTERM')
  )
    return 'timeout';
  return 'client-error';
}

// Fixed read-only query. No caller-supplied commands, paths or launch parameters.
module.exports = function (execFile, getuid, priorityIds) {
  return new Promise(function (resolve, reject) {
    if (priorityIds === undefined) priorityIds = [];
    if (
      !Array.isArray(priorityIds) ||
      priorityIds.length > 200 ||
      priorityIds.some(function (id) {
        return typeof id !== 'string' || !id || id.length > 256;
      })
    ) {
      reject(Error('invalid-icon-priority'));
      return;
    }
    if ((getuid || process.getuid)() !== 0) {
      reject(failure('Root service required', 'root-required'));
      return;
    }
    (execFile || require('child_process').execFile)(
      '/usr/bin/luna-send',
      ['-n', '1', 'luna://com.webos.applicationManager/listApps', '{}'],
      { timeout: 8000, maxBuffer: 1024 * 1024 },
      function (error, stdout) {
        if (error) {
          reject(failure('inventory-unavailable', clientReason(error)));
          return;
        }
        try {
          var result = JSON.parse(stdout);
          if (result && result.returnValue === false)
            throw failure('inventory-unavailable', 'negative-reply', result);
          if (
            !result ||
            result.returnValue !== true ||
            !Array.isArray(result.apps)
          )
            throw Error('invalid-inventory');
          var fs = require('fs'),
            path = require('path'),
            iconBudget = 512 * 1024;
          var catalog = result.apps.slice(0, 200),
            apps = new Array(catalog.length);
          // Allocate bounded icon bytes in Home order, but retain catalog order
          // in the response. IDs select metadata only, never filesystem paths.
          catalog
            .map(function (a, index) {
              var rank = priorityIds.indexOf(a.id);
              return { app: a, index: index, rank: rank < 0 ? 200 : rank };
            })
            .sort(function (a, b) {
              return a.rank - b.rank || a.index - b.index;
            })
            .forEach(function (entry) {
              var a = entry.app;
              // The installed tuner can be invisible to LG Home; keep other system apps hidden.
              var hidden =
                  a.id !== 'com.webos.app.livetv' &&
                  (a.visible === false || a.hidden === true),
                icon = '';
              var variants = [
                'extraLargeIcon',
                'largeIcon',
                'mediumLargeIcon',
                'icon',
                'miniicon',
                'favicon'
              ];
              // Hidden catalog entries must not spend the visible-app icon budget.
              for (
                var variant = 0;
                !hidden && variant < variants.length;
                variant++
              ) {
                if (
                  typeof a[variants[variant]] !== 'string' ||
                  typeof a.folderPath !== 'string'
                )
                  continue;
                var file = path.resolve(a.folderPath, a[variants[variant]]);
                var allowed =
                  /^\/(usr\/palm|media\/(developer|cryptofs|system)\/apps\/usr\/palm|mnt\/otncabi\/usr\/palm)\/applications\//;
                if (allowed.test(file) && /\.(png|jpe?g|webp)$/i.test(file))
                  try {
                    var real = fs.realpathSync(file),
                      stat = fs.statSync(real);
                    if (
                      allowed.test(real) &&
                      stat.isFile() &&
                      stat.size > 0 &&
                      stat.size <= 32768 &&
                      stat.size <= iconBudget
                    ) {
                      var data = fs.readFileSync(real),
                        ext =
                          data.length >= 8 &&
                          data.slice(0, 8).toString('hex') ===
                            '89504e470d0a1a0a'
                            ? 'png'
                            : data.length >= 3 &&
                                data[0] === 255 &&
                                data[1] === 216 &&
                                data[2] === 255
                              ? 'jpeg'
                              : data.length >= 12 &&
                                  data.slice(0, 4).toString() === 'RIFF' &&
                                  data.slice(8, 12).toString() === 'WEBP'
                                ? 'webp'
                                : '';
                      if (!ext || data.length !== stat.size) continue;
                      iconBudget -= data.length;
                      icon =
                        'data:image/' +
                        ext +
                        ';base64,' +
                        data.toString('base64');
                      break;
                    }
                  } catch (_) {}
              }
              apps[entry.index] = {
                id: a.id,
                title: a.title,
                icon: icon,
                iconColor: a.iconColor || a.bgColor || '',
                hidden: hidden
              };
            });
          resolve(apps);
        } catch (error) {
          reject(
            error && error.inventory
              ? error
              : failure('invalid-inventory', 'malformed-reply')
          );
        }
      }
    );
  });
};

// EIM denies the Root web/service identities on some firmware. Read once through
// the existing root CLI boundary; never accept a caller's URI or arguments.
module.exports.inputs = function (execFile, getuid) {
  return new Promise(function (resolve, reject) {
    if ((getuid || process.getuid)() !== 0) {
      reject(failure('input-status-unavailable', 'root-required'));
      return;
    }
    (execFile || require('child_process').execFile)(
      '/usr/bin/luna-send',
      ['-n', '1', 'luna://com.webos.service.eim/getAllInputStatus', '{}'],
      { timeout: 8000, maxBuffer: 256 * 1024 },
      function (error, stdout) {
        if (error) {
          reject(failure('input-status-unavailable', clientReason(error)));
          return;
        }
        try {
          var result = JSON.parse(stdout);
          if (result && result.returnValue === false)
            throw failure('input-status-unavailable', 'negative-reply', result);
          if (
            !result ||
            result.returnValue !== true ||
            !Array.isArray(result.devices)
          )
            throw Error('invalid-input-status');
          var fields = [
            'appId',
            'id',
            'label',
            'deviceName',
            'spdProductDescription'
          ];
          var devices = result.devices.slice(0, 100).map(function (device) {
            if (!device || typeof device !== 'object' || Array.isArray(device))
              throw Error('invalid-input-status');
            var clean = {};
            fields.forEach(function (key) {
              if (typeof device[key] === 'string')
                clean[key] = device[key].slice(0, 256);
            });
            clean.connected =
              typeof device.connected === 'boolean' ? device.connected : null;
            return clean;
          });
          resolve({ returnValue: true, devices: devices });
        } catch (error) {
          reject(
            error && error.inventory
              ? error
              : failure('input-status-unavailable', 'malformed-reply')
          );
        }
      }
    );
  });
};

module.exports.inputHandler = function (execFile, getuid) {
  var pending = null;
  return function (message) {
    function fail() {
      message.respond({
        returnValue: false,
        errorText: 'Input status unavailable'
      });
    }
    try {
      var caller = message.ls2Message.applicationID(),
        payload = message.payload;
      if (
        typeof caller !== 'string' ||
        caller.split(' ')[0] !== 'com.cleanyourtv.root.preview' ||
        !payload ||
        typeof payload !== 'object' ||
        Array.isArray(payload) ||
        Object.keys(payload).join(',') !== 'inputs' ||
        payload.inputs !== true ||
        (getuid || process.getuid)() !== 0
      ) {
        fail();
        return;
      }
    } catch (_) {
      fail();
      return;
    }
    if (!pending) pending = module.exports.inputs(execFile, getuid);
    var request = pending;
    request.then(
      function (result) {
        if (pending === request) pending = null;
        message.respond(result);
      },
      function () {
        if (pending === request) pending = null;
        fail();
      }
    );
  };
};
