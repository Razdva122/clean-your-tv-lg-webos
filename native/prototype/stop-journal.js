'use strict';
// Unwired protocol foundation. The future native adapter must verify fixed-path
// I/O and hold a checked controller lease for the entire callback. No filesystem,
// process, lease discovery, provisioning or Home authentication fallback exists.
var crypto = require('crypto'),
  nonce = /^[0-9a-f]{32}$/,
  maxStops = 16,
  maxEvents = 64,
  maxBytes = 16384;
function ensure(value) {
  if (!value) throw Error('stop-journal-unsafe');
}
function keys(value, expected) {
  ensure(
    value &&
      typeof value === 'object' &&
      !Array.isArray(value) &&
      Object.keys(value).sort().join(',') === expected
  );
}
function ids(value, max, sorted) {
  ensure(Array.isArray(value) && value.length <= max);
  var out = value.slice(),
    seen = Object.create(null);
  out.forEach(function (v) {
    ensure(typeof v === 'string' && nonce.test(v) && !seen[v]);
    seen[v] = true;
  });
  if (sorted)
    ensure(JSON.stringify(out) === JSON.stringify(out.slice().sort()));
  return out;
}
function includes(all, subset) {
  return subset.every(function (v) {
    return all.indexOf(v) >= 0;
  });
}
function equal(a, b) {
  return JSON.stringify(a) === JSON.stringify(b);
}
function digest(raw) {
  return crypto.createHash('sha256').update(raw, 'utf8').digest('hex');
}
function encode(value) {
  var out = {};
  Object.keys(value)
    .sort()
    .forEach(function (k) {
      out[k] = value[k];
    });
  return JSON.stringify(out) + '\n';
}
function decision(blocked, adopted, durable, reason, snapshot) {
  return {
    blocked: blocked,
    private_adopted: adopted,
    durable_blocked: durable,
    adopted_ids: adopted ? snapshot.slice() : [],
    reason: reason,
    physical_stop: 'UNTESTED',
    authorization: 'UNIMPLEMENTED'
  };
}
function unknown(reason) {
  return decision(true, false, false, reason || 'unsafe-or-unknown', []);
}
function create(io, hostAuthority) {
  var busy = false;
  function load(tx) {
    return Promise.resolve()
      .then(function () {
        return tx.readJournal();
      })
      .then(function (reply) {
        keys(reply, 'records,status');
        ensure(
          reply.status === 'snapshot' &&
            Array.isArray(reply.records) &&
            reply.records.length > 0 &&
            reply.records.length <= maxEvents
        );
        // Copy bounded primitive values before any later asynchronous operation.
        var rows = reply.records.map(function (row) {
          keys(row, 'name,raw');
          ensure(
            typeof row.name === 'string' &&
              typeof row.raw === 'string' &&
              row.raw.length > 0 &&
              Buffer.byteLength(row.raw, 'utf8') <= maxBytes
          );
          return { name: row.name, raw: row.raw };
        });
        var previous = null,
          hash = null;
        rows.forEach(function (row, index) {
          ensure(row.name === 'entry.' + ('0000' + index).slice(-4) + '.json');
          var state = JSON.parse(row.raw);
          keys(state, 'consumed,intents,phase,prev,seen,seq,v');
          ensure(
            state.v === 1 &&
              state.seq === index &&
              state.prev === hash &&
              ['blocked', 'prepare', 'commit'].indexOf(state.phase) >= 0
          );
          state.seen = ids(state.seen, maxStops, true);
          state.consumed = ids(state.consumed, maxStops, true);
          state.intents = ids(state.intents, maxEvents, false);
          ensure(includes(state.seen, state.consumed));
          if (!previous)
            ensure(
              state.phase === 'blocked' &&
                !state.seen.length &&
                !state.consumed.length &&
                !state.intents.length
            );
          else {
            ensure(
              includes(state.seen, previous.seen) &&
                includes(state.consumed, previous.consumed)
            );
            if (state.phase === 'prepare')
              ensure(
                equal(state.consumed, previous.consumed) &&
                  state.intents.length === previous.intents.length + 1 &&
                  equal(state.intents.slice(0, -1), previous.intents)
              );
            else if (state.phase === 'commit')
              ensure(
                previous.phase === 'prepare' &&
                  equal(state.seen, previous.seen) &&
                  equal(state.consumed, previous.seen) &&
                  equal(state.intents, previous.intents)
              );
            else
              ensure(
                equal(state.consumed, previous.consumed) &&
                  equal(state.intents, previous.intents)
              );
          }
          previous = state;
          hash = digest(row.raw);
        });
        return { state: previous, hash: hash };
      });
  }
  function scan(tx) {
    return Promise.resolve()
      .then(function () {
        return tx.scanStops();
      })
      .then(function (reply) {
        keys(reply, 'ids,status');
        ensure(reply.status === 'snapshot');
        return ids(reply.ids, maxStops, false).sort();
      });
  }
  function append(tx, loaded, phase, seen, consumed, intents) {
    var seq = loaded.state.seq + 1;
    ensure(seq < maxEvents);
    var value = {
      v: 1,
      seq: seq,
      prev: loaded.hash,
      phase: phase,
      seen: ids(seen, maxStops, false).sort(),
      consumed: ids(consumed, maxStops, false).sort(),
      intents: ids(intents, maxEvents, false)
    };
    ensure(includes(value.seen, value.consumed));
    var raw = encode(value),
      hash = digest(raw);
    ensure(Buffer.byteLength(raw, 'utf8') <= maxBytes);
    return Promise.resolve()
      .then(function () {
        return tx.appendPrivate({ seq: seq, raw: raw, sha256: hash });
      })
      .then(function (reply) {
        keys(reply, 'seq,sha256,status');
        ensure(
          reply.status === 'durable' &&
            reply.seq === seq &&
            reply.sha256 === hash
        );
        return { state: value, hash: hash };
      });
  }
  function block(tx, loaded, snapshot) {
    var adopted = snapshot !== undefined,
      seen = adopted ? snapshot.slice() : loaded.state.seen.slice();
    if (adopted) ensure(includes(seen, loaded.state.seen));
    if (loaded.state.phase === 'blocked' && equal(loaded.state.seen, seen))
      return Promise.resolve(
        decision(true, adopted, true, 'blocked-retained', seen)
      );
    return append(
      tx,
      loaded,
      'blocked',
      seen,
      loaded.state.consumed,
      loaded.state.intents
    ).then(function () {
      return decision(true, adopted, true, 'blocked-committed', seen);
    });
  }
  function operate(tx, intent) {
    return load(tx)
      .then(function (loaded) {
        ensure(loaded.state.seq < maxEvents - 1);
        return scan(tx).then(function (snapshot) {
          ensure(includes(snapshot, loaded.state.seen));
          if (snapshot.length === maxStops) return block(tx, loaded, snapshot);
          if (intent === undefined) {
            if (
              loaded.state.phase !== 'commit' ||
              !includes(loaded.state.consumed, snapshot)
            )
              return block(tx, loaded, snapshot);
            return decision(
              false,
              false,
              false,
              'committed-no-pending-stop',
              []
            );
          }
          ensure(
            typeof intent === 'string' &&
              nonce.test(intent) &&
              loaded.state.intents.indexOf(intent) < 0 &&
              loaded.state.seq + 3 < maxEvents
          );
          return append(
            tx,
            loaded,
            'prepare',
            snapshot,
            loaded.state.consumed,
            loaded.state.intents.concat([intent])
          ).then(function (prepared) {
            return scan(tx).then(function (current) {
              if (!equal(current, snapshot))
                return block(tx, prepared, current);
              return append(
                tx,
                prepared,
                'commit',
                snapshot,
                snapshot,
                prepared.state.intents
              ).then(function (committed) {
                return scan(tx).then(function (latest) {
                  if (!equal(latest, snapshot))
                    return block(tx, committed, latest);
                  return decision(
                    false,
                    false,
                    false,
                    'simulated-start-committed',
                    []
                  );
                });
              });
            });
          });
        });
      })
      .catch(function () {
        return load(tx).then(function (loaded) {
          return block(tx, loaded);
        });
      });
  }
  function run(intent) {
    if (busy) return Promise.resolve(unknown('transaction-busy'));
    if (!io || typeof io.withControllerTransaction !== 'function')
      return Promise.resolve(unknown('io-or-lease-unavailable'));
    busy = true;
    var entered = false,
      completed = false,
      live = true,
      answer;
    return Promise.resolve()
      .then(function () {
        return io.withControllerTransaction(function (tx) {
          ensure(live && !entered);
          entered = true;
          ensure(
            tx &&
              typeof tx.readJournal === 'function' &&
              typeof tx.scanStops === 'function' &&
              typeof tx.appendPrivate === 'function'
          );
          var scoped = {};
          ['readJournal', 'scanStops', 'appendPrivate'].forEach(
            function (name) {
              scoped[name] = function () {
                var args = arguments;
                return Promise.resolve()
                  .then(function () {
                    ensure(live);
                    return tx[name].apply(tx, args);
                  })
                  .then(function (value) {
                    ensure(live);
                    return value;
                  });
              };
            }
          );
          return operate(scoped, intent).then(function (value) {
            ensure(live);
            completed = true;
            answer = value;
            return value;
          });
        });
      })
      .then(function (value) {
        live = false;
        ensure(entered && completed && value === answer);
        return value;
      })
      .catch(function () {
        live = false;
        return unknown();
      })
      .then(function (value) {
        busy = false;
        return value;
      });
  }
  return {
    poll: function () {
      return run();
    },
    mayAcquireInput: function () {
      return run();
    },
    requestHomeStart: function (request) {
      if (typeof hostAuthority !== 'function')
        return Promise.resolve(unknown('authorization-unimplemented'));
      return Promise.resolve()
        .then(function () {
          return hostAuthority(request);
        })
        .then(function (intent) {
          ensure(typeof intent === 'string' && nonce.test(intent));
          return run(intent);
        })
        .catch(function () {
          return unknown('authorization-refused');
        });
    },
    publishStop: function () {
      if (!io || typeof io.publishStop !== 'function')
        return Promise.resolve({
          durable_published: false,
          private_adopted: false,
          durable_blocked: false,
          physical_stop: 'UNTESTED',
          reason: 'io-unavailable'
        });
      return Promise.resolve()
        .then(function () {
          return io.publishStop();
        })
        .then(function (reply) {
          keys(reply, 'id,status');
          ensure(
            reply.status === 'durable' &&
              typeof reply.id === 'string' &&
              nonce.test(reply.id)
          );
          return {
            id: reply.id,
            durable_published: true,
            private_adopted: false,
            durable_blocked: false,
            channel_status: 'NOT_RECHECKED',
            physical_stop: 'UNTESTED'
          };
        })
        .catch(function () {
          return {
            durable_published: false,
            private_adopted: false,
            durable_blocked: false,
            physical_stop: 'UNTESTED',
            reason: 'unsafe-or-unknown'
          };
        });
    }
  };
}
module.exports = create();
// Internal dependency seam for HOST models only. No real authorization is supplied.
module.exports._createForTests = create;
