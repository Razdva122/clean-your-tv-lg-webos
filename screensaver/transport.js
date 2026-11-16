'use strict';

var http = require('http');
var route = '/screensaver';
var host = '127.0.0.1';
var maxBytes = 2048;

function matches(session, token) {
  return !!(
    session &&
    /^[0-9a-f]{48}$/.test(token) &&
    session.sessionId === token
  );
}

function valid(event, session) {
  return (
    event &&
    event.schema === 1 &&
    event.sessionId === session.sessionId &&
    event.generation === session.generation &&
    typeof event.visible === 'boolean' &&
    typeof event.focused === 'boolean' &&
    ['loading', 'ready', 'error', 'closed'].indexOf(event.mediaState) !== -1
  );
}

function listen(current, receive, ready, serveMedia) {
  var server = http.createServer(function (req, res) {
    res.setHeader('Cache-Control', 'no-store');
    res.setHeader('Content-Type', 'application/json');
    res.setHeader('Access-Control-Allow-Origin', '*');
    function send(status, reply) {
      res.statusCode = status;
      res.end(JSON.stringify(reply || { close: true }));
    }
    var media = /^\/screensaver\/media\/([0-9a-f]{48})$/.exec(req.url);
    if (media) {
      var owned = current();
      if (!serveMedia || !matches(owned, media[1])) return send(404);
      try {
        if (serveMedia(owned, req, res)) return;
      } catch (_) {
        return req.connection.destroy();
      }
      return send(404);
    }
    if (req.url !== route) return send(404);
    if (req.method === 'OPTIONS') {
      res.setHeader('Access-Control-Allow-Methods', 'POST');
      res.setHeader(
        'Access-Control-Allow-Headers',
        'Content-Type, X-CYTV-Session'
      );
      res.statusCode = 204;
      return res.end();
    }
    if (req.method !== 'POST') return send(405);
    var token = req.headers['x-cytv-session'];
    if (!matches(current(), token)) return send(403);
    var body = '';
    var bytes = 0;
    var aborted = false;
    req.on('error', function () {
      aborted = true;
    });
    req.on('data', function (chunk) {
      if (aborted) return;
      bytes += chunk.length;
      if (bytes > maxBytes) {
        aborted = true;
        return req.connection.destroy();
      }
      body += String(chunk);
    });
    req.on('end', function () {
      if (aborted) return;
      var session = current();
      if (!matches(session, token)) return send(403);
      var payload;
      try {
        payload = JSON.parse(body);
      } catch (_) {
        return send(400);
      }
      if (!valid(payload, session)) return send(400);
      try {
        send(200, receive(payload));
      } catch (_) {
        send(500);
      }
    });
  });
  server.maxConnections = 8;
  server.setTimeout(2500);
  server.on('error', function (error) {
    if (!ready) return;
    var callback = ready;
    ready = null;
    callback(error);
  });
  server.listen(0, host, function () {
    var callback = ready;
    ready = null;
    if (!callback) return;
    callback(null, {
      endpoint: 'http://' + host + ':' + server.address().port + route,
      close: function () {
        server.close();
      }
    });
  });
}

exports.listen = listen;
