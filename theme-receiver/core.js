'use strict';
var http = require('http');
var crypto = require('crypto');
var os = require('os');
var net = require('net');
var phonePage = require('./wallpaper-phone');
var heicWorker = require('./wallpaper-heic');
var CHUNK = 48 * 1024;
function error(code) {
  var e = new Error(code);
  e.code = code;
  return e;
}
function ipv4(address) {
  if (typeof address !== 'string') return '';
  if (address.indexOf('::ffff:') === 0) address = address.slice(7);
  return net.isIP(address) === 4 ? address : '';
}
function privateAddress(address) {
  address = ipv4(address);
  var p = address.split('.');
  return (
    !!address &&
    (p[0] === '10' ||
      p[0] === '127' ||
      (p[0] === '192' && p[1] === '168') ||
      (p[0] === '172' && +p[1] >= 16 && +p[1] <= 31))
  );
}
function addresses() {
  var result = [],
    interfaces = os.networkInterfaces();
  Object.keys(interfaces).forEach(function (name) {
    interfaces[name].forEach(function (item) {
      if (
        !item.internal &&
        privateAddress(item.address) &&
        item.address.indexOf('127.') !== 0 &&
        result.indexOf(item.address) < 0
      )
        result.push(item.address);
    });
  });
  return result;
}
function base64(value) {
  return (
    typeof value === 'string' &&
    value.length % 4 === 0 &&
    /^[A-Za-z0-9+/]*={0,2}$/.test(value)
  );
}
function envelope(buffer) {
  var v;
  try {
    v = JSON.parse(buffer.toString('utf8'));
  } catch (_) {
    return false;
  }
  if (
    !v ||
    Array.isArray(v) ||
    v.schemaVersion !== 1 ||
    !v.descriptor ||
    !base64(v.descriptor) ||
    !v.files ||
    typeof v.files !== 'object' ||
    Array.isArray(v.files)
  )
    return false;
  return Object.keys(v.files).every(function (key) {
    return base64(v.files[key]);
  });
}
// Transport validation; native image decode and MP4/SPS verification run in the TV before Apply.
function wallpaperEnvelope(buffer, browser) {
  var v;
  try {
    v = JSON.parse(buffer.toString('utf8'));
  } catch (_) {
    return false;
  }
  if (
    !v ||
    v.schemaVersion !== 1 ||
    v.kind !== 'wallpaper' ||
    ['phone', 'cytv'].indexOf(v.source) < 0 ||
    (browser && v.source !== 'phone') ||
    !Array.isArray(v.variants)
  )
    return false;
  var phone = v.source === 'phone',
    total = 0,
    qualities = {};
  function media(m, video) {
    if (
      !m ||
      typeof m !== 'object' ||
      typeof m.width !== 'number' ||
      typeof m.height !== 'number' ||
      m.width % 1 ||
      m.height % 1 ||
      m.width <= 0 ||
      m.height <= 0 ||
      !base64(m.data) ||
      typeof m.sha256 !== 'string' ||
      !/^[a-f0-9]{64}$/.test(m.sha256)
    )
      return false;
    var limit = 2 * 1024 * 1024,
      width = phone ? 1920 : 3840,
      height = phone ? 1080 : 2160;
    if (video) {
      if (
        phone ||
        ['4k', '1080p'].indexOf(m.quality) < 0 ||
        qualities[m.quality] ||
        m.mediaType !== 'video/mp4'
      )
        return false;
      qualities[m.quality] = true;
      width = m.quality === '4k' ? 3840 : 1920;
      height = m.quality === '4k' ? 2160 : 1080;
      limit = (m.quality === '4k' ? 12 : 4) * 1024 * 1024;
      if (m.width !== width || m.height !== height) return false;
    } else if (['image/jpeg', 'image/png'].indexOf(m.mediaType) < 0)
      return false;
    if (
      m.width > width ||
      m.height > height ||
      m.data.length > 4 * Math.ceil(limit / 3)
    )
      return false;
    var bytes = Buffer.from(m.data, 'base64');
    if (
      !bytes.length ||
      bytes.length > limit ||
      bytes.length !== m.size ||
      bytes.toString('base64') !== m.data ||
      crypto.createHash('sha256').update(bytes).digest('hex') !== m.sha256
    )
      return false;
    if (video) {
      total += bytes.length;
      if (bytes.length < 12 || bytes.toString('ascii', 4, 8) !== 'ftyp')
        return false;
    } else if (m.mediaType === 'image/png') {
      if (
        bytes.length < 24 ||
        bytes.slice(0, 8).toString('hex') !== '89504e470d0a1a0a' ||
        bytes.toString('ascii', 12, 16) !== 'IHDR' ||
        bytes.readUInt32BE(16) !== m.width ||
        bytes.readUInt32BE(20) !== m.height
      )
        return false;
    } else {
      if (bytes[0] !== 255 || bytes[1] !== 216) return false;
      var at = 2,
        found = false;
      while (at + 4 < bytes.length && bytes[at] === 255) {
        var marker = bytes[at + 1],
          length = bytes.readUInt16BE(at + 2);
        if (length < 2 || at + 2 + length > bytes.length) return false;
        if ([192, 193, 194].indexOf(marker) >= 0) {
          if (
            length < 8 ||
            bytes.readUInt16BE(at + 5) !== m.height ||
            bytes.readUInt16BE(at + 7) !== m.width
          )
            return false;
          found = true;
          break;
        }
        at += length + 2;
      }
      if (!found) return false;
    }
    return true;
  }
  return (
    v.variants.length <= 2 &&
    (!phone || v.variants.length === 0) &&
    media(v.image, false) &&
    v.variants.every(function (m) {
      return media(m, true);
    }) &&
    total <= 16 * 1024 * 1024
  );
}
exports.create = function (options) {
  options = options || {};
  var session = null,
    starting = false;
  var port = options.port === undefined ? 8879 : options.port;
  var ttl = options.ttlMs || 600000,
    deadline = options.requestTimeoutMs || 15000;
  var maxBytes = options.maxBytes || 33 * 1024 * 1024,
    maxWrong = options.maxWrongPins || 20;
  function closeListener(s) {
    if (!s.listening) return;
    s.listening = false;
    try {
      s.server.close();
    } catch (_) {}
  }
  function release(s) {
    var done = s.release;
    s.release = null;
    if (done)
      try {
        done();
      } catch (_) {}
  }
  function dispose(s) {
    clearTimeout(s.timer);
    release(s);
    s.buffer = null;
    closeListener(s);
    s.sockets.slice().forEach(function (socket) {
      socket.destroy();
    });
    if (session === s) session = null;
  }
  function current(id) {
    if (!session || typeof id !== 'string' || id !== session.id)
      throw error('invalid-session');
    if (Date.now() >= session.expiresAt) {
      dispose(session);
      throw error('session-expired');
    }
    return session;
  }
  function handle(s, req, res) {
    var socket = req.socket,
      local = ipv4(socket.localAddress);
    var chunks = [],
      size = 0,
      done = false,
      active = false,
      began = Date.now();
    function reset() {
      if (active && s.state === 'receiving') s.state = 'waiting';
      active = false;
      chunks = [];
    }
    function reply(code, payload, html, contentType) {
      if (done) return;
      done = true;
      clearTimeout(timer);
      reset();
      res.writeHead(code, {
        'Content-Type':
          contentType ||
          (html ? 'text/html; charset=utf-8' : 'application/json'),
        'Connection': 'close',
        'Cache-Control': 'no-store',
        'X-Content-Type-Options': 'nosniff',
        'Referrer-Policy': 'no-referrer',
        'Content-Security-Policy':
          "default-src 'none'; script-src 'unsafe-inline' 'wasm-unsafe-eval'; worker-src 'self'; style-src 'unsafe-inline'; img-src blob: data:; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
      });
      res.end(html || JSON.stringify(payload || { returnValue: code === 202 }));
      req.resume();
    }
    var timer = setTimeout(function () {
      reply(408);
      socket.destroy();
    }, deadline);
    res.on('close', function () {
      clearTimeout(timer);
      if (!done) {
        done = true;
        reset();
      }
    });
    req.on('aborted', function () {
      clearTimeout(timer);
      done = true;
      reset();
    });
    req.on('error', function () {
      clearTimeout(timer);
      done = true;
      reset();
    });
    if (session !== s || Date.now() >= s.expiresAt) {
      reply(410);
      return;
    }
    if (
      !privateAddress(local) ||
      !privateAddress(socket.remoteAddress) ||
      (local.indexOf('127.') !== 0 && s.addresses.indexOf(local) < 0) ||
      req.headers.host !== local + ':' + s.port
    ) {
      reply(403);
      return;
    }
    var browser = Object.prototype.hasOwnProperty.call(req.headers, 'origin');
    if (
      browser &&
      !(
        s.kind === 'wallpaper' &&
        req.headers.origin === 'http://' + req.headers.host &&
        ((req.method === 'POST' && req.url === '/v1/wallpaper') ||
          (req.method === 'GET' &&
            (req.url === '/wallpaper-heic-worker.js' ||
              req.url === '/wallpaper-heic-license.txt')))
      )
    ) {
      reply(403);
      return;
    }
    if (
      s.kind === 'wallpaper' &&
      req.method === 'GET' &&
      req.url === '/wallpaper'
    ) {
      reply(
        200,
        null,
        phonePage.replace('CYTV_SESSION_EXPIRES', String(s.expiresAt))
      );
      return;
    }
    if (
      s.kind === 'wallpaper' &&
      req.method === 'GET' &&
      req.url === '/wallpaper-heic-worker.js'
    ) {
      reply(200, null, heicWorker(), 'application/javascript; charset=utf-8');
      return;
    }
    if (
      s.kind === 'wallpaper' &&
      req.method === 'GET' &&
      req.url === '/wallpaper-heic-license.txt'
    ) {
      reply(200, null, heicWorker.license(), 'text/plain; charset=utf-8');
      return;
    }
    var capabilities =
      s.kind === 'wallpaper' &&
      req.method === 'GET' &&
      req.url === '/v1/wallpaper-capabilities';
    if (
      !capabilities &&
      (req.method !== 'POST' ||
        req.url !== (s.kind === 'wallpaper' ? '/v1/wallpaper' : '/v1/theme'))
    ) {
      reply(404);
      return;
    }
    if (req.headers['x-cytv-pin'] !== s.pin) {
      s.wrong += 1;
      if (s.wrong >= maxWrong)
        res.on('finish', function () {
          dispose(s);
        });
      reply(403);
      return;
    }
    if (capabilities) {
      require('./wallpaper-cache')
        .space(0)
        .then(function (storage) {
          reply(200, { wallpaperProtocol: 1, videoCacheStorage: storage });
        });
      return;
    }
    if (s.state !== 'waiting') {
      reply(409);
      return;
    }
    if (req.headers['content-type'] !== 'application/json') {
      reply(415);
      return;
    }
    if (
      req.headers['content-encoding'] ||
      (req.headers['content-length'] &&
        (!/^\d+$/.test(req.headers['content-length']) ||
          +req.headers['content-length'] > maxBytes))
    ) {
      reply(413);
      return;
    }
    s.state = 'receiving';
    active = true;
    req.on('data', function (chunk) {
      if (done) return;
      size += chunk.length;
      if (size > maxBytes) {
        reply(413);
        return;
      }
      chunks.push(chunk);
    });
    req.on('end', function () {
      if (done) return;
      var buffer = Buffer.concat(chunks, size);
      if (
        !(s.kind === 'wallpaper'
          ? wallpaperEnvelope(buffer, browser)
          : envelope(buffer))
      ) {
        reply(400);
        return;
      }
      // Old TV CPUs can spend noticeable time parsing a large envelope.
      if (Date.now() - began >= deadline) {
        reply(408);
        return;
      }
      if (Date.now() >= s.expiresAt) {
        reply(410);
        dispose(s);
        return;
      }
      s.buffer = buffer;
      s.state = 'received';
      active = false;
      res.on('finish', function () {
        closeListener(s);
        s.sockets.slice().forEach(function (other) {
          if (other !== socket) other.destroy();
        });
      });
      reply(202);
    });
  }
  return {
    start: function (request) {
      if (
        request &&
        request.kind !== undefined &&
        request.kind !== 'wallpaper' &&
        request.kind !== 'theme'
      )
        return Promise.reject(error('invalid-request'));
      if (session || starting) return Promise.reject(error('receiver-busy'));
      starting = true;
      return new Promise(function (resolve, reject) {
        var s = {
          id: crypto.randomBytes(24).toString('hex'),
          pin: (
            '000000' +
            (crypto.randomBytes(4).readUInt32BE(0) % 1000000)
          ).slice(-6),
          kind: request && request.kind === 'wallpaper' ? 'wallpaper' : 'theme',
          addresses: addresses(),
          wrong: 0,
          state: 'waiting',
          buffer: null,
          sockets: [],
          listening: false,
          release: typeof options.hold === 'function' ? options.hold() : null
        };
        s.server = http.createServer(function (req, res) {
          handle(s, req, res);
        });
        s.server.on('connection', function (socket) {
          s.sockets.push(socket);
          var timer = setTimeout(function () {
            socket.destroy();
          }, deadline);
          socket.on('close', function () {
            clearTimeout(timer);
            var i = s.sockets.indexOf(socket);
            if (i >= 0) s.sockets.splice(i, 1);
          });
        });
        s.server.on('error', function () {
          starting = false;
          release(s);
          if (session === s) dispose(s);
          reject(error('receiver-unavailable'));
        });
        s.server.listen(port, '0.0.0.0', function () {
          starting = false;
          s.listening = true;
          s.port = s.server.address().port;
          s.expiresAt = Date.now() + ttl;
          session = s;
          s.timer = setTimeout(function () {
            dispose(s);
          }, ttl);
          var response = {
            sessionId: s.id,
            pin: s.pin,
            addresses: s.addresses.slice(),
            expiresAt: s.expiresAt,
            port: s.port
          };
          if (s.kind === 'wallpaper') {
            response.kind = 'wallpaper';
            response.wallpaperProtocol = 1;
          }
          resolve(response);
        });
      });
    },
    status: function (id) {
      var s = current(id);
      return { state: s.state, size: s.buffer ? s.buffer.length : 0 };
    },
    read: function (id, offset) {
      var s = current(id);
      if (!s.buffer || s.state !== 'received') throw error('not-received');
      if (
        typeof offset !== 'number' ||
        offset < 0 ||
        offset % CHUNK !== 0 ||
        offset > s.buffer.length
      )
        throw error('invalid-offset');
      var end = Math.min(offset + CHUNK, s.buffer.length);
      return {
        offset: offset,
        data: s.buffer.slice(offset, end).toString('base64'),
        nextOffset: end,
        done: end === s.buffer.length
      };
    },
    stop: function (id) {
      try {
        dispose(current(id));
        return Promise.resolve({});
      } catch (e) {
        return Promise.reject(e);
      }
    }
  };
};
