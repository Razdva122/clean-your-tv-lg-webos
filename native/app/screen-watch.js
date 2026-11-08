'use strict';
var fs = require('fs'),
  os = require('os'),
  WebSocket = require('./websocket');
// Local self-connection: the TV rejects loopback, but accepts its own LAN address.
// Never accepts a remote endpoint or launches anything itself.
module.exports = function (data, log, onForeground, onReset, onPower) {
  var closed = false,
    socket = null,
    retry = null,
    index = 0,
    cleanup = null,
    backoff = 10000,
    registered = false,
    pending = null,
    requestSequence = 0;
  function settle(value) {
    var request = pending;
    if (!request) return;
    pending = null;
    clearTimeout(request.timer);
    request.done(value);
  }
  function foreground(done) {
    if (typeof done !== 'function') return;
    if (
      closed ||
      !registered ||
      !socket ||
      pending ||
      requestSequence >= 9007199254740991
    ) {
      done(null);
      return;
    }
    var s = socket,
      request = {
        socket: s,
        id: 'cytv-foreground-' + ++requestSequence,
        done: done,
        timer: null
      };
    pending = request;
    request.timer = setTimeout(function () {
      if (pending === request) settle(null);
    }, 800);
    try {
      s.send(
        JSON.stringify({
          type: 'request',
          id: request.id,
          uri: 'ssap://com.webos.applicationManager/getForegroundAppInfo',
          payload: {}
        })
      );
    } catch (ignore) {
      if (pending === request) settle(null);
    }
  }
  function later() {
    if (!closed) {
      retry = setTimeout(connect, backoff);
      backoff = Math.min(backoff * 2, 60000);
    }
  }
  function connect() {
    if (closed) return;
    registered = false;
    socket = null;
    settle(null);
    onReset();
    if (!require('./state-permissions')(data, log)) {
      log({ event: 'screen-watch-unavailable', reason: 'state-permissions' });
      later();
      return;
    }
    var key,
      addresses = [];
    try {
      key = JSON.parse(fs.readFileSync(data + '/ssap-key.json', 'utf8')).key;
      if (typeof key !== 'string' || !key) throw Error('missing-key');
    } catch (e) {
      log({ event: 'screen-watch-unavailable', reason: 'missing-pairing-key' });
      return;
    }
    var interfaces = os.networkInterfaces();
    Object.keys(interfaces).forEach(function (name) {
      interfaces[name].forEach(function (a) {
        if (
          !a.internal &&
          (a.family === 'IPv4' || a.family === 4) &&
          a.address.indexOf('169.254.') !== 0
        )
          addresses.push(a.address);
      });
    });
    if (!addresses.length) {
      later();
      return;
    }
    var host = addresses[index++ % addresses.length],
      s;
    try {
      s = new WebSocket('wss://' + host + ':3001', {
        rejectUnauthorized: false,
        handshakeTimeout: 5000,
        maxPayload: 65536,
        perMessageDeflate: false
      });
    } catch (e) {
      later();
      return;
    }
    socket = s;
    var deadline = setTimeout(function () {
        s.terminate();
      }, 10000),
      pulse = null,
      alive = true;
    cleanup = function () {
      clearTimeout(deadline);
      clearInterval(pulse);
    };
    s.on('open', function () {
      if (closed || socket !== s) return;
      // Same full manifest as app-inventory.js: webOS 3.x stores the LAST registered
      // permission set per key, so a smaller request revokes the others.
      s.send(
        JSON.stringify({
          type: 'register',
          id: 'register',
          payload: {
            forcePairing: false,
            pairingType: 'PROMPT',
            'client-key': key,
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
        })
      );
    });
    s.on('pong', function () {
      if (!closed && socket === s) alive = true;
    });
    s.on('message', function (raw) {
      if (closed || socket !== s) return;
      var m;
      try {
        m = JSON.parse(String(raw));
      } catch (e) {
        settle(null);
        return;
      }
      if (!m || typeof m !== 'object' || Array.isArray(m)) {
        settle(null);
        return;
      }
      if (pending && pending.socket === s && m.id === pending.id) {
        var payload = m.payload,
          value =
            m.type === 'response' &&
            payload &&
            typeof payload === 'object' &&
            !Array.isArray(payload) &&
            (payload.returnValue === undefined ||
              payload.returnValue === true) &&
            !payload.pairingType &&
            typeof payload.appId === 'string' &&
            payload.appId.length > 0 &&
            payload.appId.indexOf('\x00') < 0
              ? payload.appId
              : null;
        settle(value);
        if (!(payload && payload.pairingType)) return;
      }
      if (m.type === 'registered') {
        registered = true;
        s.send(
          JSON.stringify({
            type: 'subscribe',
            id: 'foreground',
            uri: 'ssap://com.webos.applicationManager/getForegroundAppInfo',
            payload: {}
          })
        );
        if (onPower)
          s.send(
            JSON.stringify({
              type: 'subscribe',
              id: 'power',
              uri: 'ssap://com.webos.service.tvpower/power/getPowerState',
              payload: {}
            })
          );
      } else if (m.id === 'power') {
        if (m.type === 'error')
          log({ event: 'power-watch-error', error: String(m.error) });
        else if (
          m.payload &&
          m.payload.returnValue !== false &&
          typeof m.payload.state === 'string' &&
          onPower
        )
          onPower(m.payload);
      } else if (
        m.id === 'foreground' &&
        m.type !== 'error' &&
        m.payload &&
        typeof m.payload.appId === 'string'
      ) {
        if (!pulse) {
          backoff = 10000;
          clearTimeout(deadline);
          log({ event: 'screen-watch-connected' });
          pulse = setInterval(function () {
            if (!alive) {
              s.terminate();
              return;
            }
            alive = false;
            // ws throws from ping() unless the socket is OPEN. At power-off it
            // can be CLOSING before 'close' clears this interval; the callback
            // takes that error instead, and the next tick terminates.
            s.ping(function () {});
          }, 5000);
        }
        onForeground(m.payload.appId);
      } else if (m.type === 'error') {
        registered = false;
        settle(null);
        log({ event: 'screen-watch-error', error: String(m.error) });
        if (/^(400|401|403|404)\b/.test(String(m.error))) closed = true;
        s.terminate();
      } else if (m.payload && m.payload.pairingType) {
        // A revoked key must not leave an unattended pairing flow running.
        log({ event: 'screen-watch-unavailable', reason: 'pairing-required' });
        registered = false;
        closed = true;
        settle(null);
        s.terminate();
      }
    });
    s.on('error', function (e) {
      if (closed || socket !== s) return;
      registered = false;
      settle(null);
      log({ event: 'screen-watch-error', error: e.code || e.message });
    });
    s.on('close', function (code) {
      clearTimeout(deadline);
      clearInterval(pulse);
      if (socket !== s) return;
      registered = false;
      socket = null;
      settle(null);
      onReset();
      log({ event: 'screen-watch-disconnected', code: code });
      later();
    });
  }
  connect();
  return {
    foreground: foreground,
    close: function () {
      closed = true;
      registered = false;
      settle(null);
      clearTimeout(retry);
      if (cleanup) cleanup();
      onReset();
      if (socket) socket.terminate();
    }
  };
};
