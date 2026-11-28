'use strict';
var crypto = require('crypto');
var id = 'io.github.razdva122.cytvhomepilot.service';
var manager = 'luna://com.palm.activitymanager/';
function activityId(n) {
  return (
    typeof n === 'number' &&
    n > 0 &&
    n <= 9007199254740991 &&
    Math.floor(n) === n
  );
}
function call(service, method, args) {
  return new Promise(function (resolve) {
    var timer = setTimeout(function () {
      resolve(null);
    }, 3500);
    try {
      service.call(manager + method, args, function (reply) {
        clearTimeout(timer);
        resolve(reply && reply.payload);
      });
    } catch (_) {
      clearTimeout(timer);
      resolve(null);
    }
  });
}
exports.clock = function () {
  var fs = require('fs');
  var boot = fs.readFileSync('/proc/sys/kernel/random/boot_id', 'utf8').trim();
  var epoch = /^btime ([0-9]{1,12})$/m.exec(
    fs.readFileSync('/proc/stat', 'utf8')
  );
  var at = Number(fs.readFileSync('/proc/uptime', 'utf8').split(' ')[0]);
  if (
    !/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/.test(boot) ||
    !epoch ||
    !isFinite(at) ||
    at < 0
  )
    throw Error('boot-clock-unavailable');
  return { boot: boot + ':' + epoch[1], at: Math.floor(at * 1000) };
};
exports.generation = function () {
  return crypto.randomBytes(16).toString('hex');
};
exports.create = function (service, generation, current) {
  var definition = {
    name: id + '.wake',
    description: 'Clean Your TV background wake',
    type: { foreground: true, persist: true },
    schedule: { interval: '10s', precise: true },
    callback: {
      method: 'luna://' + id + '/tick',
      params: { version: 1, generation: generation }
    }
  };
  function create(replace) {
    if (!current()) throw Error('cancelled');
    return call(service, 'create', {
      activity: definition,
      start: true,
      replace: replace,
      subscribe: false
    });
  }
  return create(false)
    .then(function (r) {
      // LG scopes a replace to this caller and activity name. A failed orphan
      // after an ordinary uninstall cannot prove liveness by delivering a tick.
      if (r && r.returnValue === false && r.errorCode === 17)
        return create(true);
      return r;
    })
    .then(function (r) {
      if (!r || r.returnValue !== true || !activityId(r.activityId))
        throw Error('activity-unavailable');
      return r.activityId;
    });
};
exports.cancel = function (service, n) {
  // A lost create acknowledgement can leave a real schedule without a saved ID.
  var target = activityId(n)
    ? { activityId: n }
    : { activityName: id + '.wake' };
  return call(service, 'cancel', target).then(function (r) {
    return !!(
      r &&
      (r.returnValue === true || (r.returnValue === false && r.errorCode === 2))
    );
  });
};
exports.delivery = function (message) {
  try {
    var sender = message.ls2Message.senderServiceName(),
      p = message.payload,
      a = p.$activity;
    if (
      (sender !== 'com.palm.activitymanager' &&
        sender !== 'com.webos.service.activitymanager') ||
      !a ||
      a !== message.activity ||
      a.name !== id + '.wake' ||
      !a.creator ||
      a.creator.serviceId !== id ||
      !activityId(a.activityId) ||
      !a.type ||
      a.type.continuous === true ||
      p.version !== 1 ||
      typeof p.generation !== 'string' ||
      !/^[a-f0-9]{32}$/.test(p.generation) ||
      typeof message.uniqueToken !== 'string' ||
      !message.uniqueToken ||
      message.uniqueToken.length > 256
    )
      return null;
    return {
      id: a.activityId,
      generation: p.generation,
      token: message.uniqueToken
    };
  } catch (_) {
    return null;
  }
};
