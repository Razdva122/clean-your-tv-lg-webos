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
      launchPoints = null;
    function finish(error, apps) {
      if (done) return;
      if (error && launchPoints) {
        error = null;
        apps = launchPoints;
      }
      done = true;
      clearTimeout(timer);
      clearTimeout(attemptTimer);
      if (socket)
        try {
          socket.terminate();
        } catch (_) {}
      if (error) reject(Error(error));
      else resolve(apps);
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
                launchPoints.some(function (a) {
                  return a && a.id === 'com.webos.app.livetv' && !a.hidden;
                })
              )
                finish(null, launchPoints);
              else
                send({
                  type: 'request',
                  id: 'tuner',
                  uri: 'ssap://com.webos.applicationManager/listApps',
                  payload: {}
                });
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
