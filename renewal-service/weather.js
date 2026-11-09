'use strict';
// The caller can choose coordinates, never a destination or TLS policy.
function createRequest(https) {
  https = https || require('https');
  return function (place, done) {
    var finished = false,
      request,
      response,
      timer;
    function finish(code, forecast) {
      if (finished) return;
      finished = true;
      clearTimeout(timer);
      if (code) {
        if (response && response.destroy) response.destroy();
        if (request) request.destroy();
      }
      done(code, forecast);
    }
    timer = setTimeout(function () {
      finish('weather-timeout');
    }, 12000);
    try {
      request = https.request(
        {
          hostname: 'api.met.no',
          port: 443,
          method: 'GET',
          path:
            '/weatherapi/locationforecast/2.0/compact?lat=' +
            String(Math.round(place.latitude * 10000) / 10000) +
            '&lon=' +
            String(Math.round(place.longitude * 10000) / 10000),
          rejectUnauthorized: true,
          agent: false,
          ca: require('fs').readFileSync(__dirname + '/ca-bundle.crt', 'utf8'),
          headers: {
            Accept: 'application/json',
            'User-Agent':
              'CleanYourTV (https://github.com/Razdva122/clean-your-tv-lg-webos)'
          }
        },
        function (res) {
          response = res;
          var chunks = [],
            size = 0;
          res.on('error', function () {
            finish('weather-network-error');
          });
          res.on('aborted', function () {
            finish('weather-network-error');
          });
          res.on('close', function () {
            finish('weather-network-error');
          });
          if (finished) {
            if (res.destroy) res.destroy();
            return;
          }
          if (res.statusCode !== 200) {
            finish('weather-http-status');
            return;
          }
          res.on('data', function (chunk) {
            if (finished) return;
            if (!Buffer.isBuffer(chunk)) chunk = new Buffer(chunk);
            size += chunk.length;
            if (size > 262144) {
              finish('weather-response-too-large');
              return;
            }
            chunks.push(chunk);
          });
          res.on('end', function () {
            if (finished) return;
            var body;
            try {
              body = JSON.parse(Buffer.concat(chunks).toString('utf8'));
            } catch (_) {
              finish('weather-invalid-response');
              return;
            }
            if (!body || typeof body !== 'object' || Array.isArray(body)) {
              finish('weather-invalid-response');
              return;
            }
            finish(null, body);
          });
        }
      );
      request.on('error', function () {
        finish('weather-network-error');
      });
      request.end();
    } catch (_) {
      finish('weather-network-error');
    }
    return {
      cancel: function () {
        finish('weather-cancelled');
      }
    };
  };
}
function valid(payload, forecast) {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload))
    return false;
  var keys = Object.keys(payload).sort().join(',');
  if (
    keys !== (forecast ? 'id,latitude,longitude' : 'id') ||
    typeof payload.id !== 'string' ||
    !/^[a-zA-Z0-9-]{1,64}$/.test(payload.id)
  )
    return false;
  return (
    !forecast ||
    (typeof payload.latitude === 'number' &&
      isFinite(payload.latitude) &&
      Math.abs(payload.latitude) <= 90 &&
      typeof payload.longitude === 'number' &&
      isFinite(payload.longitude) &&
      Math.abs(payload.longitude) <= 180)
  );
}
function register(service, options) {
  var pending = Object.create(null),
    cancelled = [],
    count = 0;
  var request = createRequest(options.https);
  function respond(message, code, forecast) {
    message.respond(
      code
        ? { returnValue: false, errorCode: code }
        : { returnValue: true, forecast: forecast }
    );
  }
  function authorized(message) {
    try {
      var id = message.ls2Message.applicationID();
      return typeof id === 'string' && id.split(' ')[0] === options.appId;
    } catch (_) {
      return false;
    }
  }
  function prune() {
    var now = Date.now();
    cancelled = cancelled.filter(function (entry) {
      return entry.until > now;
    });
  }
  function wasCancelled(id) {
    prune();
    return cancelled.some(function (entry) {
      return entry.id === id;
    });
  }
  function handler(forecast) {
    return function (message) {
      if (!authorized(message)) {
        respond(message, 'caller-not-authorized');
        return;
      }
      var payload = message.payload;
      if (!valid(payload, forecast)) {
        respond(message, 'invalid-request');
        return;
      }
      var id = payload.id;
      if (!forecast) {
        if (!wasCancelled(id))
          cancelled.push({ id: id, until: Date.now() + 12000 });
        if (cancelled.length > 64) cancelled.shift();
        if (pending[id]) pending[id].cancel();
        message.respond({ returnValue: true });
        return;
      }
      if (wasCancelled(id)) {
        respond(message, 'weather-cancelled');
        return;
      }
      if (count >= 2 || pending[id]) {
        respond(message, 'weather-busy');
        return;
      }
      var release = options.hold ? options.hold() : null,
        ended = false,
        operation;
      pending[id] = {
        cancel: function () {
          if (operation) operation.cancel();
        }
      };
      count++;
      operation = request(payload, function (code, body) {
        if (ended) return;
        ended = true;
        delete pending[id];
        count--;
        if (release) release();
        respond(message, code, body);
      });
    };
  }
  service.register('weatherForecast', handler(true));
  service.register('weatherForecastCancel', handler(false));
}
module.exports = register;
