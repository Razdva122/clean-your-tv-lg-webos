'use strict';
// Removing caller validation, resource bounds or completion fencing must break these cases.
var assert = require('assert'),
  fs = require('fs'),
  vm = require('vm');
var path = require('path'),
  EventEmitter = require('events').EventEmitter;
function exercise(filename, appId, entry) {
  var methods = {},
    calls = [],
    timers = [],
    held = 0,
    released = 0,
    clock = 1000;
  var tvProcess = Object.create(process);
  tvProcess.getuid = function () {
    return 1000;
  };
  function ClockDate(value) {
    return arguments.length ? new Date(value) : new Date(clock);
  }
  ClockDate.prototype = Date.prototype;
  ClockDate.UTC = Date.UTC;
  ClockDate.parse = Date.parse;
  ClockDate.now = function () {
    return clock;
  };
  var https = {
    request: function (options, callback) {
      var req = new EventEmitter();
      req.destroy = function () {
        req.destroyed = true;
      };
      req.end = function () {};
      calls.push({ options: options, callback: callback, req: req });
      return req;
    }
  };
  var service = {
    register: function (name, fn) {
      methods[name] = fn;
      return { on: function () {} };
    },
    activityManager: {
      create: function (name, callback) {
        held++;
        callback({ activityId: held });
      },
      complete: function (activity, callback) {
        released++;
        callback();
      }
    },
    call: function () {
      return { cancel: function () {} };
    }
  };
  function load(file) {
    var module = { exports: {} };
    var localRequire = function (name) {
      if (name === 'https') return https;
      if (name === 'webos-service')
        return function () {
          return service;
        };
      if (name === './weather')
        return load(path.resolve(path.dirname(file), 'weather.js'));
      if (name === '../../renewal-service/weather')
        return load(path.resolve('renewal-service/weather.js'));
      return name.charAt(0) === '.'
        ? require(path.resolve(path.dirname(file), name))
        : require(name);
    };
    try {
      vm.runInNewContext(
        fs.readFileSync(file, 'utf8'),
        {
          module: module,
          exports: module.exports,
          Buffer: Buffer,
          global: global,
          process: tvProcess,
          __dirname: path.dirname(path.resolve(file)),
          require: localRequire,
          Date: ClockDate,
          setTimeout: function (fn, ms) {
            assert.equal(ms, 12000);
            var t = { fn: fn };
            timers.push(t);
            return t;
          },
          clearTimeout: function (t) {
            if (t) t.cleared = true;
          }
        },
        { filename: file, displayErrors: false }
      );
    } catch (error) {
      throw new Error(file + ': ' + error.message);
    }
    return module.exports;
  }
  var api = load(filename);
  if (!entry)
    api(service, {
      appId: appId,
      https: https,
      hold: require('../../theme-receiver/register').activityHold(
        service,
        'weatherForecast'
      )
    });
  assert.equal(calls.length, 0, 'import/registration starts no network');
  function invoke(name, payload, caller) {
    var replies = [];
    methods[name]({
      payload: payload,
      ls2Message: {
        applicationID: function () {
          return caller === undefined ? appId + ' session' : caller;
        }
      },
      respond: function (r) {
        replies.push(r);
      }
    });
    return replies;
  }
  function forecast(id, extra, caller) {
    var p = { id: id, latitude: 12.345678, longitude: -45.678912 };
    Object.keys(extra || {}).forEach(function (k) {
      p[k] = extra[k];
    });
    return invoke('weatherForecast', p, caller);
  }
  function response(call, text, status) {
    var res = new EventEmitter();
    res.statusCode = status === undefined ? 200 : status;
    res.destroy = function () {
      res.destroyed = true;
    };
    call.callback(res);
    if (text !== undefined) {
      res.emit('data', Buffer.from ? Buffer.from(text) : new Buffer(text));
      res.emit('end');
    }
    return res;
  }
  assert.equal(typeof methods.weatherForecast, 'function');
  assert.equal(typeof methods.weatherForecastCancel, 'function');
  [
    ['foreign', {}],
    ['', {}],
    [appId, { url: 'https://evil/' }],
    [appId, { headers: {} }],
    [appId, { latitude: NaN }],
    [appId, { latitude: Infinity }],
    [appId, { id: '' }],
    [appId, { id: 123 }],
    [appId, { latitude: 91 }],
    [appId, { longitude: -181 }],
    [appId, { longitude: '2' }],
    [appId, { id: '../x' }],
    [appId, { id: new Array(66).join('a') }]
  ].forEach(function (item) {
    assert.equal(forecast('invalid', item[1], item[0])[0].returnValue, false);
  });
  assert.equal(calls.length, 0, 'reject before socket or hold');
  assert.equal(held, 0);
  var good = forecast('ok'),
    call = calls[0],
    options = call.options;
  assert.equal(options.hostname, 'api.met.no');
  assert.equal(options.port, 443);
  assert.equal(
    options.path,
    '/weatherapi/locationforecast/2.0/compact?lat=12.3457&lon=-45.6789'
  );
  assert.equal(options.method, 'GET');
  assert.equal(options.rejectUnauthorized, true);
  assert.equal(options.checkServerIdentity, undefined);
  assert.equal(options.agent, false);
  assert(/CleanYourTV.*github\.com/.test(options.headers['User-Agent']));
  assert.equal(
    options.ca,
    fs.readFileSync('renewal-service/ca-bundle.crt', 'utf8')
  );
  response(call, '{"properties":{"timeseries":[]}}');
  assert.equal(good[0].returnValue, true);
  assert(good[0].forecast.properties);
  response(call, '{}');
  call.req.emit('error', new Error('private URL/token'));
  assert.equal(good.length, 1);
  assert.equal(released, held);
  var a = forecast('a'),
    b = forecast('b');
  assert.equal(forecast('c')[0].errorCode, 'weather-busy');
  assert.equal(forecast('a')[0].errorCode, 'weather-busy');
  assert.equal(calls.length, 3);
  assert.equal(
    invoke('weatherForecastCancel', { id: 'a' }, 'foreign')[0].returnValue,
    false
  );
  assert.equal(
    invoke('weatherForecastCancel', { id: 'a', url: 'x' })[0].returnValue,
    false
  );
  assert.equal(
    invoke('weatherForecastCancel', { id: 'a' })[0].returnValue,
    true
  );
  assert.equal(a[0].errorCode, 'weather-cancelled');
  assert(calls[1].req.destroyed);
  response(calls[1], '{}');
  assert.equal(a.length, 1);
  timers[timers.length - 1].fn();
  assert.equal(b[0].errorCode, 'weather-timeout');
  assert.equal(released, held);
  invoke('weatherForecastCancel', { id: 'early' });
  var count = calls.length;
  assert.equal(forecast('early')[0].errorCode, 'weather-cancelled');
  assert.equal(calls.length, count);
  [
    ['bad-json', 'not json', 200, 'weather-invalid-response'],
    ['array', '[]', 200, 'weather-invalid-response'],
    ['null', 'null', 200, 'weather-invalid-response'],
    ['redirect', '{}', 302, 'weather-http-status'],
    ['large', new Array(262146).join('x'), 200, 'weather-response-too-large']
  ].forEach(function (c) {
    var replies = forecast(c[0]);
    response(calls[calls.length - 1], c[1], c[2]);
    assert.equal(replies[0].errorCode, c[3]);
    assert.equal(released, held);
  });
  ['error', 'aborted', 'close'].forEach(function (event) {
    var replies = forecast('res-' + event),
      res = response(calls[calls.length - 1]);
    res.emit(event, new Error('private response'));
    assert.equal(replies[0].errorCode, 'weather-network-error');
    assert.equal(released, held);
  });
  var error = forecast('req-error');
  calls[calls.length - 1].req.emit('error', new Error('private request'));
  assert.equal(
    JSON.stringify(error),
    '[{"returnValue":false,"errorCode":"weather-network-error"}]'
  );
  assert.equal(released, held);
  invoke('weatherForecastCancel', { id: 'expires' });
  clock += 12001;
  var expires = forecast('expires');
  response(calls[calls.length - 1], '{}');
  assert.equal(expires[0].returnValue, true);
  for (var i = 0; i < 65; i++)
    invoke('weatherForecastCancel', { id: 'bounded-' + i });
  var evicted = forecast('bounded-0');
  response(calls[calls.length - 1], '{}');
  assert.equal(evicted[0].returnValue, true);
  assert.equal(forecast('bounded-64')[0].errorCode, 'weather-cancelled');
  assert.equal(released, held);
  https.request = function () {
    throw new Error('private synchronous exception');
  };
  assert.equal(forecast('throw')[0].errorCode, 'weather-network-error');
  assert.equal(released, held);
  console.log('PASS trusted weather transport ' + filename);
}
if (!fs.existsSync('renewal-service/weather.js')) {
  assert.fail('weatherForecast trusted MET implementation is missing');
}
if (process.argv[2])
  exercise(
    process.argv[2],
    process.argv[3] || 'com.gathin.tvhome',
    process.argv[4] === 'entry'
  );
else {
  exercise('renewal-service/weather.js', 'com.gathin.tvhome');
  exercise('renewal-service/service.js', 'com.gathin.tvhome', true);
  exercise(
    'root-edition/service/service.js',
    'com.cleanyourtv.root.preview',
    true
  );
}
module.exports = exercise;
