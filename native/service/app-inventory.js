'use strict';
// Uses the existing pairing key and only the TV's own LAN address. Never pairs.
module.exports = function (options) {
  options = options || {};
  var inputs = options.inputs === true;
  function inputDevices(devices) {
    return devices.slice(0, 100).map(function (device) {
      if (
        !device ||
        typeof device !== 'object' ||
        Array.isArray(device) ||
        typeof device.appId !== 'string' ||
        !device.appId.trim()
      )
        throw Error('invalid-input');
      var result = {};
      ['appId', 'id', 'label', 'deviceName', 'spdProductDescription'].forEach(
        function (key) {
          if (typeof device[key] === 'string' && device[key].trim())
            result[key] = device[key].trim().slice(0, 256);
        }
      );
      result.connected =
        typeof device.connected === 'boolean' ? device.connected : null;
      return result;
    });
  }
  return new Promise(function (resolve, reject) {
    var socket,
      done = false,
      timer,
      attemptTimer,
      confirmationTimer,
      launchPoints = null,
      installedIds,
      deadline = Date.now() + (options.timeout || 8000);
    function finish(error, apps) {
      if (done) return;
      if (error && launchPoints) {
        error = null;
        apps = launchPoints;
      }
      done = true;
      clearTimeout(timer);
      clearTimeout(attemptTimer);
      clearTimeout(confirmationTimer);
      if (socket)
        try {
          socket.terminate();
        } catch (_) {}
      if (error) reject(Error(error));
      else if (options.details && !inputs) {
        icons(apps, hosts[index - 1], options, deadline).then(function (
          catalog
        ) {
          var result = { apps: catalog };
          if (installedIds) result.installedIds = installedIds;
          resolve(result);
        }, reject);
      } else resolve(apps);
    }
    function send(message) {
      try {
        socket.send(JSON.stringify(message));
      } catch (_) {
        finish('inventory-unavailable');
      }
    }
    try {
      var base =
        '/media/developer/apps/usr/palm/applications/com.local.nativehome';
      if (
        !options.readKey &&
        !require(base + '/state-permissions')(base + '/state')
      ) {
        finish('state-permissions');
        return;
      }
      var key = (
        options.readKey ||
        function () {
          return JSON.parse(
            require('fs').readFileSync(base + '/state/ssap-key.json', 'utf8')
          );
        }
      )();
      if (
        !key ||
        typeof key.key !== 'string' ||
        !key.key ||
        (inputs && key.key.length > 1024)
      ) {
        finish('missing-pairing');
        return;
      }
      var interfaces = (
          options.interfaces || require('os').networkInterfaces
        )(),
        hosts = [];
      Object.keys(interfaces).forEach(function (name) {
        interfaces[name].forEach(function (a) {
          if (
            !a.internal &&
            (a.family === 'IPv4' || a.family === 4) &&
            a.address.indexOf('169.254.') !== 0
          )
            hosts.push(a.address);
        });
      });
      if (!hosts.length) {
        finish('network-unavailable');
        return;
      }
      var WebSocket = options.WebSocket || require(base + '/websocket');
      var index = 0;
      timer = setTimeout(function () {
        finish('inventory-timeout');
      }, options.timeout || 8000);
      function connect() {
        if (done) return;
        if (index >= hosts.length) {
          finish('network-unavailable');
          return;
        }
        var current;
        try {
          current = new WebSocket('wss://' + hosts[index++] + ':3001', {
            rejectUnauthorized: false,
            handshakeTimeout: 2000,
            maxPayload: inputs ? 256 * 1024 : 1024 * 1024,
            perMessageDeflate: false
          });
        } catch (_) {
          connect();
          return;
        }
        socket = current;
        function retry() {
          if (done || socket !== current) return;
          if (launchPoints) {
            finish(null, launchPoints);
            return;
          }
          clearTimeout(attemptTimer);
          socket = null;
          try {
            current.terminate();
          } catch (_) {}
          connect();
        }
        attemptTimer = setTimeout(
          retry,
          Math.max(500, Math.floor((options.timeout || 8000) / hosts.length))
        );

        // Same full manifest as screen-watch.js: webOS 3.x stores the LAST registered
        // permission set per key, so a smaller request revokes the others.
        current.on('open', function () {
          if (done || socket !== current) return;
          send({
            type: 'register',
            id: 'register',
            payload: {
              forcePairing: false,
              pairingType: 'PROMPT',
              'client-key': key.key,
              manifest: {
                manifestVersion: 1,
                appVersion: '1.1',
                permissions: [
                  'READ_APP_STATUS',
                  'READ_RUNNING_APPS',
                  'READ_POWER_STATE',
                  'CONTROL_POWER',
                  'READ_INSTALLED_APPS',
                  'READ_INPUT_DEVICE_LIST'
                ]
              }
            }
          });
        });
        current.on('message', function (raw) {
          if (done || socket !== current) return;
          var message;
          try {
            message = JSON.parse(String(raw));
          } catch (_) {
            finish('invalid-response');
            return;
          }
          if (
            !message ||
            typeof message !== 'object' ||
            Array.isArray(message)
          ) {
            finish('invalid-response');
            return;
          }
          if (message.type === 'registered')
            send({
              type: 'request',
              id: inputs ? 'inputs' : 'apps',
              uri: inputs
                ? 'ssap://tv/getExternalInputList'
                : 'ssap://com.webos.applicationManager/listLaunchPoints',
              payload: {}
            });
          else if (message.payload && message.payload.pairingType)
            finish('pairing-required');
          else if (message.type === 'error') finish('inventory-denied');
          else if (message.id === 'tuner' && launchPoints) {
            var installed = message.payload;
            if (
              options.details &&
              installed &&
              installed.returnValue === true &&
              Array.isArray(installed.apps) &&
              installed.apps.length <= 300
            ) {
              var ids = installed.apps.map(function (a) {
                return a && a.id;
              });
              if (
                ids.every(function (id, i) {
                  return (
                    typeof id === 'string' &&
                    id.length > 0 &&
                    id.length <= 256 &&
                    ids.indexOf(id) === i
                  );
                }) &&
                launchPoints.every(function (a) {
                  return a && ids.indexOf(a.id) >= 0;
                })
              )
                installedIds = ids;
            }
            var tuner =
              installed &&
              installed.returnValue === true &&
              Array.isArray(installed.apps)
                ? installed.apps.filter(function (a) {
                    return (
                      a &&
                      a.id === 'com.webos.app.livetv' &&
                      typeof a.title === 'string' &&
                      a.title.length > 0 &&
                      a.title.length <= 256
                    );
                  })[0]
                : null;
            if (tuner) {
              // LG can omit its installed tuner from launch points and mark it invisible.
              // Only this discovered app is selectable; never synthesize a system ID.
              var entry = {};
              Object.keys(tuner).forEach(function (key) {
                entry[key] = tuner[key];
              });
              entry.hidden = false;
              finish(
                null,
                [entry].concat(
                  launchPoints.filter(function (a) {
                    return !a || a.id !== entry.id;
                  })
                )
              );
            } else finish(null, launchPoints);
          } else if (
            message.id === (inputs ? 'inputs' : 'apps') &&
            !launchPoints
          ) {
            var result = message.payload;
            if (
              !result ||
              (inputs
                ? result.returnValue !== true
                : result.returnValue === false) ||
              !Array.isArray(result[inputs ? 'devices' : 'launchPoints'])
            )
              finish('invalid-inventory');
            else if (inputs) {
              try {
                finish(null, inputDevices(result.devices));
              } catch (_) {
                finish('invalid-inventory');
              }
            } else {
              launchPoints = result.launchPoints.slice(0, 200);
              if (
                !options.details &&
                launchPoints.some(function (a) {
                  return a && a.id === 'com.webos.app.livetv' && !a.hidden;
                })
              )
                finish(null, launchPoints);
              else {
                // Confirmation is optional: leave time to resolve new app icons
                // even on firmware that never replies to listApps.
                if (options.details)
                  confirmationTimer = setTimeout(
                    function () {
                      finish(null, launchPoints);
                    },
                    Math.min(1000, Math.max(1, (deadline - Date.now()) / 2))
                  );
                send({
                  type: 'request',
                  id: 'tuner',
                  uri: 'ssap://com.webos.applicationManager/listApps',
                  payload: {}
                });
              }
            }
          }
        });
        current.on('error', retry);
        current.on('close', retry);
      }
      connect();
    } catch (_) {
      finish('inventory-unavailable');
    }
  });
};

// Read only icons on the already selected TV endpoint. No redirects, credentials,
// arbitrary filesystem reads or external hosts; bounds cover the entire refresh.
function icons(apps, host, options, deadline) {
  var url = require('url'),
    total = 512 * 1024,
    received = 0,
    active = [],
    next = 0,
    running = 0,
    stopped = false;
  apps = apps
    .filter(function (a) {
      return (
        a &&
        typeof a.id === 'string' &&
        a.id.length > 0 &&
        a.id.length <= 256 &&
        typeof a.title === 'string' &&
        a.title.length <= 256 &&
        (a.id === 'com.webos.app.livetv' || (!a.hidden && a.visible !== false))
      );
    })
    .slice(0, 200);
  var catalog = apps.map(function (a) {
    return {
      id: a.id,
      title: a.title,
      hidden: a.hidden,
      visible: a.visible,
      iconColor: a.iconColor || a.bgColor || '',
      icon: ''
    };
  });
  return new Promise(function (resolve) {
    var timer = setTimeout(finish, Math.max(0, deadline - Date.now()));
    function finish() {
      if (stopped) return;
      stopped = true;
      clearTimeout(timer);
      active.slice().forEach(function (cancel) {
        cancel();
      });
      resolve(catalog);
    }
    function pump() {
      if (stopped) return;
      if (Date.now() >= deadline || (!running && next === catalog.length)) {
        finish();
        return;
      }
      while (running < 4 && next < catalog.length) {
        var index = next++;
        running++;
        read(index, 0);
      }
    }
    var variants = [
      'extraLargeIcon',
      'largeIcon',
      'mediumLargeIcon',
      'icon',
      'miniicon',
      'favicon'
    ];
    function read(index, variant) {
      if (stopped) return;
      if (
        variant === variants.length ||
        total <= 0 ||
        received >= 2 * 1024 * 1024 ||
        Date.now() >= deadline
      ) {
        running--;
        pump();
        return;
      }
      var uri = apps[index][variants[variant]],
        parsed;
      try {
        if (typeof uri !== 'string' || uri.length > 4096)
          throw Error('invalid-icon');
        parsed = url.parse(uri);
        if (
          (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') ||
          parsed.hostname !== host ||
          parsed.auth ||
          (parsed.port &&
            ['80', '443', '3000', '3001'].indexOf(parsed.port) < 0)
        )
          throw Error('invalid-icon');
      } catch (_) {
        read(index, variant + 1);
        return;
      }
      var request,
        response,
        chunks = [],
        size = 0,
        complete = false;
      var requestTimer = setTimeout(
        function () {
          done();
        },
        Math.min(1000, Math.max(1, deadline - Date.now()))
      );
      function cancel() {
        done(true);
      }
      active.push(cancel);
      function done(cancelled, data) {
        if (complete) return;
        complete = true;
        clearTimeout(requestTimer);
        active.splice(active.indexOf(cancel), 1);
        if (response) response.destroy();
        if (request) request.abort();
        if (cancelled || stopped) return;
        var kind =
          data &&
          data.length >= 12 &&
          (data.slice(0, 8).toString('hex') === '89504e470d0a1a0a'
            ? 'png'
            : data[0] === 255 && data[1] === 216
              ? 'jpeg'
              : data.slice(0, 4).toString() === 'RIFF' &&
                  data.slice(8, 12).toString() === 'WEBP'
                ? 'webp'
                : '');
        if (kind && data.length <= total) {
          total -= data.length;
          catalog[index].icon =
            'data:image/' + kind + ';base64,' + data.toString('base64');
          running--;
          pump();
        } else read(index, variant + 1);
      }
      try {
        var get =
          options.get ||
          require(parsed.protocol === 'https:' ? 'https' : 'http').get;
        request = get(
          {
            protocol: parsed.protocol,
            hostname: parsed.hostname,
            port: parsed.port,
            path: parsed.path,
            rejectUnauthorized: false,
            agent: false
          },
          function (r) {
            response = r;
            r.on('error', function () {
              done();
            });
            r.on('aborted', function () {
              done();
            });
            if (complete) {
              r.destroy();
              return;
            }
            if (r.statusCode !== 200) {
              done();
              return;
            }
            r.on('data', function (chunk) {
              if (complete) return;
              size += chunk.length;
              received += chunk.length;
              if (
                size > 128 * 1024 ||
                size > total ||
                received > 2 * 1024 * 1024
              )
                done();
              else chunks.push(chunk);
            });
            r.on('end', function () {
              done(false, Buffer.concat(chunks));
            });
          }
        );
        request.on('error', function () {
          done();
        });
      } catch (_) {
        done();
      }
    }
    pump();
  });
}
module.exports.icons = icons;
