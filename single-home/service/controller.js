'use strict';
var boot = require('./boot');
var app = 'io.github.razdva122.cytvhomepilot';
var issues = [
  'invalid-request',
  'not-paired',
  'busy',
  'cancelled',
  'storage-unavailable',
  'storage-unverified',
  'activity-unavailable',
  'activity-cancel-unconfirmed',
  'boot-clock-unavailable',
  'pairing-declined',
  'pairing-timeout',
  'saved-pairing-rejected',
  'network-unavailable',
  'invalid-inventory'
];
function reject(code) {
  throw Error(code);
}
function safeStorageIssue(e) {
  var c = e && e.code;
  return typeof c === 'string' &&
    /^storage-(?:(?:db-(?:putKind|find|put)|keymanager-(?:generateKey|generate|begin|finish|abort))(?::-?[0-9]{1,10}|-(?:timeout|failed|unavailable))|invalid-(?:iv|handle|envelope|db-results|record|db-receipt|gcm-output|boot-state|credential)|canary-mismatch|credential-write-indeterminate|(?:write|credential)-not-confirmed)$/.test(
      c
    )
    ? c
    : 'storage-unavailable';
}
function respond(message, work) {
  Promise.resolve()
    .then(work)
    .then(
      function (result) {
        result.returnValue = true;
        message.respond(result);
      },
      function (error) {
        var code = error && error.message;
        var result = {
          returnValue: false,
          errorCode: issues.indexOf(code) >= 0 ? code : 'storage-unavailable'
        };
        if (result.errorCode === 'storage-unavailable')
          result.storageIssue = safeStorageIssue(error);
        message.respond(result);
      }
    );
}
module.exports = function (service, storage, inventory, clock) {
  var queue = Promise.resolve(),
    pairing = null,
    lastDelivery = null,
    epoch = 0,
    pairEpoch = 0;
  function serialized(task) {
    var result = queue.then(task);
    queue = result.then(
      function () {},
      function () {}
    );
    return result;
  }
  function writeBoot(s) {
    return storage.writeBoot(s);
  }
  function owner(method, fn) {
    service.register(method, function (m) {
      var sender;
      try {
        sender = m.ls2Message.applicationID();
      } catch (_) {}
      if (typeof sender !== 'string' || sender.split(' ')[0] !== app) {
        m.respond({ returnValue: false, errorCode: 'denied' });
        return;
      }
      var p = m.payload || {};
      if (
        Object.keys(p).some(function (k) {
          return k !== 'confirm' || (method !== 'pair' && method !== 'enable');
        })
      ) {
        m.respond({ returnValue: false, errorCode: 'invalid-request' });
        return;
      }
      // Invalidate pending network work at message receipt, ahead of queued DB work.
      if (method === 'disable') epoch++;
      if (method === 'disable' || method === 'cancelPair') {
        pairEpoch++;
        pairing = null;
      }
      var actionEpoch = method === 'pair' ? pairEpoch : epoch;
      var arrival;
      try {
        arrival = clock();
      } catch (_) {
        m.respond({ returnValue: false, errorCode: 'boot-clock-unavailable' });
        return;
      }
      var visit = serialized(function () {
        return storage.readBoot().then(function (s) {
          if (s.ownerVisit && s.ownerVisit.boot === arrival.boot) return;
          s.ownerVisit = arrival;
          return writeBoot(s);
        });
      });
      respond(m, function () {
        return visit.then(function () {
          if (
            (method === 'pair' && actionEpoch !== pairEpoch) ||
            (method === 'enable' && actionEpoch !== epoch)
          )
            reject('cancelled');
          return fn(p, arrival);
        });
      });
    });
  }
  function readiness() {
    return storage.probe().then(
      function (ok) {
        if (!ok) return { storageReady: false, credentialsReady: false };
        return storage.credentialsReady().then(
          function (ready) {
            return { storageReady: true, credentialsReady: ready === true };
          },
          function (e) {
            return {
              storageReady: true,
              credentialsReady: false,
              storageIssue: safeStorageIssue(e)
            };
          }
        );
      },
      function (e) {
        return {
          storageReady: false,
          credentialsReady: false,
          storageIssue: safeStorageIssue(e)
        };
      }
    );
  }
  function requireCredentials() {
    return storage.credentialsReady().then(
      function (ok) {
        if (!ok) reject('storage-unverified');
      },
      function () {
        reject('storage-unverified');
      }
    );
  }
  owner('probe', function () {
    return readiness().then(function (r) {
      if (!r.storageReady) return r;
      return storage.evidence().then(function (e) {
        if (e && /^[a-f0-9]{64}$/.test(e.canarySha256))
          r.canarySha256 = e.canarySha256;
        return r;
      });
    });
  });
  owner('status', function (p, arrival) {
    return readiness().then(function (r) {
      return serialized(function () {
        return storage.readBoot().then(function (s) {
          r.paired = s.paired === true;
          r.pairing = !!pairing;
          r.startup = s.startup;
          r.bootObserved = !!(
            s.startup === 'enabled' &&
            s.receipt &&
            s.receipt.boot === arrival.boot &&
            s.receipt.generation === s.generation &&
            s.receipt.early === true
          );
          if (r.bootObserved) {
            r.bootReceiptUptimeMs = s.receipt.at;
            r.firstOwnerUptimeMs = s.ownerVisit.at;
          }
          return r;
        });
      });
    });
  });
  owner('pair', function (p) {
    if (p.confirm !== true) reject('invalid-request');
    if (pairing) reject('busy');
    var session = { epoch: pairEpoch };
    pairing = session;
    function current() {
      return pairing === session && session.epoch === pairEpoch;
    }
    var result = requireCredentials()
      .then(function () {
        if (!current()) reject('cancelled');
        return inventory(null, current);
      })
      .then(function (profile) {
        if (!current()) reject('cancelled');
        return serialized(function () {
          return storage.read().then(function (s) {
            if (!current()) reject('cancelled');
            var before = s.key;
            s.key = profile.key;
            return storage.write(s).then(function () {
              if (current()) return { paired: true };
              s.key = before;
              return storage.write(s).then(function () {
                reject('cancelled');
              });
            });
          });
        });
      });
    return result.then(
      function (r) {
        if (pairing === session) pairing = null;
        return r;
      },
      function (e) {
        var cancelled = !current();
        if (pairing === session) pairing = null;
        if (
          cancelled &&
          (!e || e.code !== 'storage-credential-write-indeterminate')
        )
          reject('cancelled');
        throw e;
      }
    );
  });
  owner('cancelPair', function () {
    return { cancelled: true };
  });
  owner('catalog', function () {
    return requireCredentials()
      .then(function () {
        return serialized(function () {
          return storage.read();
        });
      })
      .then(function (s) {
        if (!s.key) reject('not-paired');
        return inventory(s.key, function () {
          return true;
        }).then(function (profile) {
          return { apps: profile.apps };
        });
      });
  });
  owner('enable', function (p) {
    if (p.confirm !== true) reject('invalid-request');
    var expected = epoch;
    return serialized(function () {
      return storage.readBoot().then(function (s) {
        if (expected !== epoch) reject('cancelled');
        if (
          s.startup === 'enabled' ||
          (s.startup === 'pending' && s.activityId)
        )
          return { startup: s.startup };
        s.generation = boot.generation();
        s.startup = 'pending';
        s.activityId = null;
        s.receipt = null;
        return writeBoot(s)
          .then(function () {
            if (expected !== epoch) reject('cancelled');
            return boot.create(service, s.generation, function () {
              return expected === epoch;
            });
          })
          .then(function (id) {
            s.activityId = id;
            return writeBoot(s).then(function () {
              if (expected !== epoch) reject('cancelled');
              return { startup: 'pending' };
            });
          });
      });
    });
  });
  owner('disable', function () {
    return serialized(function () {
      return storage.readBoot().then(function (s) {
        var old = s.activityId;
        s.startup = 'stopped';
        s.generation = boot.generation();
        s.receipt = null;
        lastDelivery = null;
        return writeBoot(s)
          .then(function () {
            return boot.cancel(service, old);
          })
          .then(function (cancelled) {
            if (!cancelled) reject('activity-cancel-unconfirmed');
            s.activityId = null;
            return writeBoot(s).then(function () {
              return { startup: 'stopped' };
            });
          });
      });
    });
  });
  service.register('tick', function (m) {
    var delivery = boot.delivery(m);
    if (!delivery) {
      m.respond({ returnValue: false, errorCode: 'denied' });
      return;
    }
    var received;
    try {
      received = clock();
    } catch (_) {
      m.respond({ returnValue: false, errorCode: 'boot-clock-unavailable' });
      return;
    }
    var expected = epoch;
    respond(m, function () {
      return serialized(function () {
        return storage.readBoot().then(function (s) {
          var match =
            (s.startup === 'pending' || s.startup === 'enabled') &&
            s.generation === delivery.generation &&
            s.activityId === delivery.id &&
            expected === epoch;
          if (!match) reject('cancelled');
          if (lastDelivery === delivery.token) reject('cancelled');
          lastDelivery = delivery.token;
          var receipt = s.receipt,
            changed = false;
          if (
            !receipt ||
            receipt.boot !== received.boot ||
            receipt.generation !== s.generation
          ) {
            s.receipt = {
              boot: received.boot,
              at: received.at,
              generation: s.generation,
              early: !s.ownerVisit || s.ownerVisit.boot !== received.boot
            };
            changed = true;
          } else if (
            s.startup === 'pending' &&
            received.at - receipt.at >= 4000
          ) {
            s.startup = 'enabled';
            changed = true;
          }
          return (changed ? writeBoot(s) : Promise.resolve()).then(function () {
            if (expected !== epoch) reject('cancelled');
            service.activityManager.complete(
              m.activity,
              { restart: true },
              function () {}
            );
            return { received: true };
          });
        });
      });
    });
  });
};
