'use strict';
// The pilot follows the existing Helper's SSAP registration and launch-point
// exchange. This service owns a separate, inventory-only registration.
var appId = 'io.github.razdva122.cytvhomepilot';
function visibleApps(open, installed) {
  var seen = Object.create(null),
    result = [];
  open.forEach(function (a) {
    if (
      !a ||
      a.hidden ||
      a.visible === false ||
      a.id === appId ||
      !valid(a) ||
      seen[a.id]
    )
      return;
    seen[a.id] = true;
    result.push({ id: a.id, title: a.title });
  });
  // Some TVs omit the tuner from launch points. Only an actual installed tuner
  // can supply its title; no system application ID is synthesized for launch.
  if (installed && !seen['com.webos.app.livetv'])
    installed.some(function (a) {
      if (!valid(a) || a.id !== 'com.webos.app.livetv') return false;
      result.unshift({ id: a.id, title: a.title });
      return true;
    });
  return result;
}
function valid(a) {
  return (
    a &&
    typeof a.id === 'string' &&
    /^[a-zA-Z0-9][a-zA-Z0-9._-]{0,255}$/.test(a.id) &&
    typeof a.title === 'string' &&
    a.title.trim().length > 0 &&
    a.title.length <= 256
  );
}
module.exports = function inventory(saved, current, options) {
  options = options || {};
  return new Promise(function (resolve, reject) {
    var addresses = [],
      networks = (options.interfaces || require('os').networkInterfaces)();
    Object.keys(networks).forEach(function (k) {
      networks[k].forEach(function (n) {
        if (
          !n.internal &&
          (n.family === 'IPv4' || n.family === 4) &&
          require('net').isIPv4(n.address) &&
          n.address.indexOf('169.254.') !== 0 &&
          addresses.indexOf(n.address) < 0
        )
          addresses.push(n.address);
      });
    });
    var WebSocket = options.WebSocket || require('./websocket');
    var socket,
      attemptTimer,
      tunerTimer,
      opened = false,
      ended = false,
      asked = false,
      registered = false,
      issued,
      points = null,
      index = 0;
    var finalTimer = setTimeout(
      function () {
        done(!registered && !saved ? 'pairing-timeout' : 'network-unavailable');
      },
      saved ? 8000 : 65000
    );
    var stopTimer = setInterval(function () {
      if (!current()) done('cancelled');
    }, 150);
    function done(error, installed) {
      if (ended) return;
      ended = true;
      clearTimeout(finalTimer);
      clearInterval(stopTimer);
      clearTimeout(attemptTimer);
      clearTimeout(tunerTimer);
      if (socket) {
        try {
          socket.terminate();
        } catch (_) {}
      }
      if (!current()) error = 'cancelled';
      if (error) reject(Error(error));
      else resolve({ key: issued, apps: visibleApps(points, installed) });
    }
    function send(q) {
      try {
        socket.send(JSON.stringify(q));
      } catch (_) {
        done('network-unavailable');
      }
    }
    function connect() {
      if (!current()) {
        done('cancelled');
        return;
      }
      if (index >= addresses.length) {
        done('network-unavailable');
        return;
      }
      var host = addresses[index++],
        sock;
      try {
        sock = new WebSocket('wss://' + host + ':3001', {
          localAddress: host,
          rejectUnauthorized: false,
          handshakeTimeout: 2000,
          maxPayload: 1024 * 1024,
          perMessageDeflate: false
        });
      } catch (_) {
        connect();
        return;
      }
      socket = sock;
      function failed() {
        if (ended || socket !== sock) return;
        if (points) {
          done();
          return;
        }
        if (opened) {
          done('network-unavailable');
          return;
        }
        clearTimeout(attemptTimer);
        socket = null;
        try {
          sock.terminate();
        } catch (_) {}
        connect();
      }
      attemptTimer = setTimeout(failed, 2400);
      sock.on('error', failed);
      sock.on('close', failed);
      sock.on('open', function () {
        if (ended || socket !== sock) return;
        if (!current()) {
          done('cancelled');
          return;
        }
        clearTimeout(attemptTimer);
        opened = true;
        var payload = {
          forcePairing: false,
          manifest: {
            manifestVersion: 1,
            appVersion: '1.0',
            permissions: ['READ_INSTALLED_APPS']
          }
        };
        if (saved) payload['client-key'] = saved;
        else payload.pairingType = 'PROMPT';
        send({ id: 'register', type: 'register', payload: payload });
      });
      sock.on('message', function (raw) {
        if (ended || socket !== sock) return;
        if (!current()) {
          done('cancelled');
          return;
        }
        var m;
        try {
          m = JSON.parse(String(raw));
        } catch (_) {
          done('invalid-inventory');
          return;
        }
        if (!m || typeof m !== 'object') {
          done('invalid-inventory');
          return;
        }
        var p = m.payload || {};
        if (!registered) {
          if (m.id !== 'register') return;
          if (
            !saved &&
            m.type === 'response' &&
            p.returnValue === true &&
            p.pairingType === 'PROMPT'
          ) {
            asked = true;
            return;
          }
          issued = p['client-key'];
          if (
            m.type !== 'registered' ||
            p.returnValue === false ||
            typeof issued !== 'string' ||
            !issued ||
            Buffer.byteLength(issued) > 1024 ||
            (saved ? issued !== saved : !asked)
          ) {
            done(saved ? 'saved-pairing-rejected' : 'pairing-declined');
            return;
          }
          registered = true;
          send({
            id: 'apps',
            type: 'request',
            uri: 'ssap://com.webos.applicationManager/listLaunchPoints',
            payload: {}
          });
        } else if (m.id === 'apps' && !points) {
          if (
            m.type !== 'response' ||
            p.returnValue !== true ||
            !Array.isArray(p.launchPoints) ||
            p.launchPoints.length > 500
          ) {
            done('invalid-inventory');
            return;
          }
          points = p.launchPoints.slice(0, 200);
          if (
            !visibleApps(points, null).length &&
            points.some(function (a) {
              return !valid(a);
            })
          ) {
            done('invalid-inventory');
            return;
          }
          tunerTimer = setTimeout(function () {
            done();
          }, 750);
          send({
            id: 'tuner',
            type: 'request',
            uri: 'ssap://com.webos.applicationManager/listApps',
            payload: {}
          });
        } else if (m.id === 'tuner' && points) {
          done(
            null,
            m.type === 'response' &&
              p.returnValue === true &&
              Array.isArray(p.apps) &&
              p.apps.length <= 500
              ? p.apps
              : null
          );
        }
      });
    }
    connect();
  });
};
