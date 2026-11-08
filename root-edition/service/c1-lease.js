'use strict';
// The compositor receives only a short in-memory lease. This broker never writes
// recovery state and never runs a helper for an ordinary Root installation.
var ROOT = '/var/lib/clean-your-tv-root';
var BACKEND = 'c1-native-gate';
var ROUTING = 'compositor-keyfilter-v1';
var ALIAS = 'com.webos.cleanyourtv.root.lease';
var crypto = require('crypto');

function keys(value, expected) {
  return (
    !!value &&
    typeof value === 'object' &&
    !Array.isArray(value) &&
    Object.keys(value).sort().join(',') === expected.split(',').sort().join(',')
  );
}
function integer(value, min, max) {
  return (
    typeof value === 'number' &&
    isFinite(value) &&
    Math.floor(value) === value &&
    value >= min &&
    value < max
  );
}
function digest(value) {
  return typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
}
function admission(value, schema) {
  var version = /^\d{1,3}\.\d{1,3}\.\d{1,3}(?:-[A-Za-z0-9.]+)?$/;
  return (
    keys(value, 'model,firmware,webos,target_sha256,target') &&
    typeof value.model === 'string' &&
    (schema === 2
      ? /^OLED(?:48|55|65|77|83)C1[A-Z0-9]{2,12}$/
      : /^[A-Za-z0-9._-]{1,128}$/
    ).test(value.model) &&
    typeof value.firmware === 'string' &&
    version.test(value.firmware) &&
    typeof value.webos === 'string' &&
    version.test(value.webos) &&
    (schema !== 2 || value.webos.indexOf('6.') === 0) &&
    digest(value.target_sha256) &&
    keys(value.target, 'dev,ino,size,mtime_ns') &&
    integer(value.target.dev, 0, Math.pow(2, 63)) &&
    integer(value.target.ino, 1, Math.pow(2, 63)) &&
    integer(value.target.size, 52, Math.pow(2, 63)) &&
    integer(value.target.mtime_ns, 0, Math.pow(2, 63))
  );
}
function validNative(value) {
  return (
    keys(
      value,
      'returnValue,backend,routing,state,mounted,healthy,stock_verified,stopped,token,guardian_pid,reason,profiles'
    ) &&
    value.returnValue === true &&
    value.backend === BACKEND &&
    value.routing === ROUTING &&
    value.mounted === false &&
    value.stopped === false &&
    ((value.state === 'armed' &&
      value.healthy === true &&
      value.stock_verified === false &&
      value.guardian_pid > 0) ||
      (value.state === 'stock' &&
        value.healthy === false &&
        typeof value.stock_verified === 'boolean')) &&
    value.profiles === null &&
    typeof value.reason === 'string' &&
    typeof value.token === 'string' &&
    /^[a-f0-9]{32}$/.test(value.token) &&
    integer(value.guardian_pid, 0, 2147483648)
  );
}

module.exports = function (service, options) {
  var opts = options || {};
  var fs = opts.fs || require('fs');
  var constants = fs.constants || require('constants');
  var execFile = opts.execFile || require('child_process').execFile;
  var getuid =
    opts.getuid ||
    function () {
      return process.getuid();
    };
  var later = opts.setTimeout || setTimeout;
  var clear = opts.clearTimeout || clearTimeout;
  var now =
    opts.now ||
    function () {
      var value = process.hrtime();
      return value[0] * 1000 + value[1] / 1000000;
    };
  var subscribers = Object.create(null),
    generation = 0,
    sequence = 0,
    token = '',
    everArmed = false;
  var pollTimer = null,
    deadline = null,
    child = null,
    homePending = null;

  function directory(path, privatePath) {
    var info = fs.lstatSync(path);
    if (
      !info.isDirectory() ||
      info.uid !== 0 ||
      info.mode & (privatePath ? 63 : 18)
    )
      throw Error('Unsafe lease directory');
  }
  function read(path, limit, executable) {
    var before = fs.lstatSync(path);
    var fd = fs.openSync(
      path,
      constants.O_RDONLY | constants.O_NOFOLLOW | constants.O_NONBLOCK
    );
    try {
      var info = fs.fstatSync(fd);
      if (
        !before.isFile() ||
        !info.isFile() ||
        before.ino !== info.ino ||
        before.dev !== info.dev ||
        info.uid !== 0 ||
        info.nlink !== 1 ||
        info.mode & 63 ||
        info.size > limit ||
        (executable && !(info.mode & 64))
      )
        throw Error('Unsafe lease file');
      // Node 0.12 cannot readFileSync(fd). Keep the authenticated descriptor
      // and bound reads to the verified size plus one byte to detect growth.
      var data = Buffer.alloc(info.size + 1);
      var offset = 0;
      while (offset < data.length) {
        var count = fs.readSync(fd, data, offset, data.length - offset, null);
        if (!count) break;
        offset += count;
      }
      if (offset !== info.size) throw Error('Lease file changed while reading');
      return data.slice(0, offset);
    } finally {
      fs.closeSync(fd);
    }
  }
  function authority() {
    if (getuid() !== 0) throw Error('Root lease broker required');
    ['/', '/var', '/var/lib', ROOT, ROOT + '/runtime'].forEach(function (path) {
      directory(path, false);
    });
    directory(ROOT + '/c1-keyfilter', true);
    var marker = JSON.parse(
      read(ROOT + '/home-backend.json', 8192, false).toString('utf8')
    );
    if (
      !keys(
        marker,
        'schema,backend,experimental,native_sha256,admission,routing'
      ) ||
      (marker.schema !== 2 && marker.schema !== 3) ||
      marker.backend !== BACKEND ||
      marker.routing !== ROUTING ||
      marker.experimental !== true ||
      !digest(marker.native_sha256) ||
      !admission(marker.admission, marker.schema)
    )
      throw Error('Unselected lease backend');
    var binary = read(ROOT + '/runtime/c1-keyfilter-guard', 16777216, true);
    if (
      crypto.createHash('sha256').update(binary).digest('hex') !==
      marker.native_sha256
    )
      throw Error('Changed lease helper');
  }
  function stop() {
    generation++;
    finishHome(false);
    if (pollTimer !== null) clear(pollTimer);
    if (deadline !== null) clear(deadline);
    pollTimer = null;
    deadline = null;
    var previous = child;
    child = null;
    if (previous) {
      try {
        previous.kill();
      } catch (_) {}
    }
    token = '';
    everArmed = false;
  }
  function respond(message, value) {
    try {
      return message.respond(value) !== false;
    } catch (_) {
      return false;
    }
  }
  function failed(message) {
    return respond(message, {
      returnValue: false,
      subscribed: false,
      backend: BACKEND,
      routing: ROUTING,
      healthy: false,
      token: token,
      sequence: sequence,
      errorText: 'C1 compositor lease unavailable'
    });
  }
  function revoke() {
    var previous = subscribers;
    subscribers = Object.create(null);
    Object.keys(previous).forEach(function (key) {
      failed(previous[key]);
      try {
        if (previous[key].cancel) previous[key].cancel();
      } catch (_) {}
    });
    stop();
  }
  function currentCaller(message) {
    try {
      return (
        message.ls2Message.senderServiceName() === 'com.webos.surfacemanager'
      );
    } catch (_) {
      return false;
    }
  }
  function fresh(start, limit) {
    var elapsed = now() - start;
    return (
      typeof elapsed === 'number' &&
      isFinite(elapsed) &&
      elapsed >= 0 &&
      elapsed < limit
    );
  }
  function finishHome(ok) {
    if (!homePending) return;
    var pending = homePending;
    homePending = null;
    clear(pending.timer);
    if (!ok && pending.child) {
      try {
        pending.child.kill();
      } catch (_) {}
    }
    return respond(pending.message, {
      returnValue: ok,
      backend: BACKEND,
      routing: ROUTING,
      token: pending.token
    });
  }
  function poll() {
    if (!Object.keys(subscribers).length) return stop();
    var current = generation;
    try {
      authority();
    } catch (_) {
      revoke();
      return;
    }
    var completed = false,
      started = now();
    deadline = later(function () {
      if (current !== generation || completed) return;
      completed = true;
      revoke();
    }, 350);
    // Fixed cadence and no overlapping children: the earlier deadline retires a
    // slow invocation before the next native broker pulse can start.
    pollTimer = later(function () {
      if (current === generation) poll();
    }, 400);
    try {
      child = execFile(
        ROOT + '/runtime/c1-keyfilter-guard',
        ['--lease'],
        { timeout: 350, maxBuffer: 8192 },
        function (error, stdout) {
          if (current !== generation || completed) return;
          completed = true;
          child = null;
          clear(deadline);
          deadline = null;
          var result;
          try {
            if (error || !fresh(started, 350))
              throw Error('Expired native lease reply');
            result = JSON.parse(stdout);
            if (
              !validNative(result) ||
              (everArmed && !result.healthy) ||
              (token && token !== result.token)
            )
              throw Error('Invalid native lease');
            // Recheck after the child: authority lost during execution cannot
            // produce a healthy reply from a once-authenticated executable.
            authority();
            if (!fresh(started, 350))
              throw Error('Expired native lease verification');
          } catch (_) {
            revoke();
            return;
          }
          token = result.token;
          if (result.healthy) everArmed = true;
          sequence++;
          Object.keys(subscribers).forEach(function (key) {
            if (
              !respond(subscribers[key], {
                returnValue: true,
                subscribed: true,
                backend: BACKEND,
                routing: ROUTING,
                healthy: result.healthy,
                token: token,
                sequence: sequence
              })
            )
              delete subscribers[key];
          });
          if (!Object.keys(subscribers).length) stop();
        }
      );
    } catch (_) {
      revoke();
    }
  }
  var leaseService;
  try {
    authority();
    // Service's documented second argument shares request activities and idle
    // lifetime with the primary service. The alias needs no activity grant.
    leaseService = opts.createService(ALIAS, service.activityManager, {
      noBuiltinMethods: true
    });
  } catch (_) {
    return false;
  }
  leaseService.register(
    'c1Lease',
    function (message) {
      // The hub-authenticated service name is independent of application metadata.
      if (
        !currentCaller(message) ||
        !message.isSubscription ||
        !keys(message.payload, 'subscribe') ||
        message.payload.subscribe !== true ||
        typeof message.uniqueToken !== 'string' ||
        !message.uniqueToken ||
        Object.keys(subscribers).length >= 2 ||
        subscribers[message.uniqueToken]
      ) {
        failed(message);
        return;
      }
      var first = !Object.keys(subscribers).length;
      subscribers[message.uniqueToken] = message;
      if (first) {
        generation++;
        token = '';
        poll();
      }
    },
    function (message) {
      delete subscribers[message.uniqueToken];
      if (!Object.keys(subscribers).length) stop();
    }
  );
  leaseService.register('c1Home', function (message) {
    if (
      !currentCaller(message) ||
      message.isSubscription ||
      !keys(message.payload, 'token') ||
      typeof message.payload.token !== 'string' ||
      !/^[a-f0-9]{32}$/.test(message.payload.token) ||
      !everArmed ||
      message.payload.token !== token ||
      homePending
    ) {
      respond(message, {
        returnValue: false,
        backend: BACKEND,
        routing: ROUTING,
        token: ''
      });
      return;
    }
    try {
      authority();
    } catch (_) {
      failed(message);
      revoke();
      return;
    }
    var pending = {
      message: message,
      token: token,
      generation: generation,
      started: now(),
      child: null,
      timer: null
    };
    homePending = pending;
    pending.timer = later(function () {
      if (homePending !== pending) return;
      finishHome(false);
      revoke();
    }, 2500);
    try {
      pending.child = execFile(
        ROOT + '/runtime/c1-keyfilter-guard',
        ['--home', pending.token],
        { timeout: 2400, maxBuffer: 8192 },
        function (error, stdout) {
          if (homePending !== pending) return;
          try {
            if (
              error ||
              pending.generation !== generation ||
              pending.token !== token ||
              !fresh(pending.started, 2500)
            )
              throw Error('Expired Home dispatch');
            var result = JSON.parse(stdout);
            if (
              !validNative(result) ||
              !result.healthy ||
              result.token !== pending.token
            )
              throw Error('Home dispatch failed');
            authority();
            if (!fresh(pending.started, 2500))
              throw Error('Expired Home dispatch verification');
          } catch (_) {
            finishHome(false);
            revoke();
            return;
          }
          if (!finishHome(true)) revoke();
        }
      );
    } catch (_) {
      finishHome(false);
      revoke();
    }
  });
};
