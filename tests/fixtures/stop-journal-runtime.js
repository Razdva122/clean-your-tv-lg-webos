// ES5 HOST typed-I/O fixtures; executes compiled production protocol.
'use strict';
var assert = require('assert'),
  path = require('path'),
  crypto = require('crypto');
var protocol = require(path.join(process.argv[2], 'stop-journal.js'));
function encoded(v) {
  var out = {};
  Object.keys(v)
    .sort()
    .forEach(function (k) {
      out[k] = v[k];
    });
  return JSON.stringify(out) + '\n';
}
function digest(raw) {
  return crypto.createHash('sha256').update(raw, 'utf8').digest('hex');
}
function id(n) {
  return ('00000000000000000000000000000000' + n.toString(16)).slice(-32);
}
function deferred() {
  var resolve,
    reject,
    promise = new Promise(function (a, b) {
      resolve = a;
      reject = b;
    });
  return { promise: promise, resolve: resolve, reject: reject };
}
function fixture() {
  var records = [
      {
        name: 'entry.0000.json',
        raw: encoded({
          v: 1,
          seq: 0,
          prev: null,
          phase: 'blocked',
          seen: [],
          consumed: [],
          intents: []
        })
      }
    ],
    stops = [],
    next = 100,
    held = false;
  var f = {
    records: records,
    stops: stops,
    calls: [],
    scanStatus: 'snapshot',
    loadStatus: 'snapshot',
    hook: function () {},
    readHook: function () {},
    publishHook: function () {},
    authCalls: 0
  };
  function boundary(label, action) {
    return Promise.resolve().then(function () {
      f.calls.push(label);
      action();
      return f.hook(label);
    });
  }
  var tx = {
    readJournal: function () {
      return boundary('load', function () {}).then(function () {
        return {
          status: f.loadStatus,
          records: f.records.map(function (v) {
            return { name: v.name, raw: v.raw };
          })
        };
      });
    },
    scanStops: function () {
      return boundary('scan', function () {}).then(function () {
        var v = { status: f.scanStatus, ids: f.stops.slice() };
        f.readHook(v);
        return v;
      });
    },
    appendPrivate: function (request) {
      var copy = { seq: request.seq, raw: request.raw, sha256: request.sha256 };
      return boundary('append.' + JSON.parse(copy.raw).phase, function () {
        f.records.push({
          name: 'entry.' + ('0000' + copy.seq).slice(-4) + '.json',
          raw: copy.raw
        });
      }).then(function () {
        return { status: 'durable', seq: copy.seq, sha256: copy.sha256 };
      });
    }
  };
  f.tx = tx;
  f.io = {
    withControllerTransaction: function (callback) {
      if (held) return Promise.reject(Error('busy'));
      held = true;
      return Promise.resolve()
        .then(function () {
          return callback(tx);
        })
        .then(
          function (v) {
            held = false;
            return v;
          },
          function (e) {
            held = false;
            throw e;
          }
        );
    },
    publishStop: function () {
      return Promise.resolve()
        .then(function () {
          if (f.scanStatus !== 'snapshot' || f.stops.length >= 16)
            throw Error('full or unknown');
          return f.publishHook();
        })
        .then(function () {
          var value = id(next++);
          f.stops.push(value);
          return { status: 'durable', id: value };
        });
    }
  };
  f.native = protocol._createForTests(f.io, function (request) {
    f.authCalls++;
    if (!request || request.testIntent === undefined)
      return Promise.reject(Error('HOST fixture auth refusal'));
    return request.testIntent;
  });
  f.start = function (n) {
    return f.native.requestHomeStart({ testIntent: id(n) });
  };
  f.publish = function () {
    return f.native.publishStop();
  };
  f.last = function () {
    return JSON.parse(f.records[f.records.length - 1].raw);
  };
  f.reopen = function () {
    held = false;
    return protocol._createForTests(f.io, function (request) {
      return request.testIntent;
    });
  };
  return f;
}
var cases = [];
function test(name, body) {
  cases.push({ name: name, body: body });
}
function blocked(value, adopted, durable) {
  assert.equal(value.blocked, true);
  assert.equal(value.private_adopted, adopted);
  assert.equal(value.durable_blocked, durable);
  assert.equal(value.physical_stop, 'UNTESTED');
  if (!adopted) assert.deepEqual(value.adopted_ids, []);
}

test('defaults deny all requests without IO or auth', function () {
  return protocol
    .poll()
    .then(function (v) {
      blocked(v, false, false);
      return protocol.requestHomeStart({
        authorized: true,
        nativeHomeStart: true
      });
    })
    .then(function (v) {
      blocked(v, false, false);
      assert.equal(v.reason, 'authorization-unimplemented');
    });
});
test('known genesis is durably blocked', function () {
  var f = fixture();
  return f.native.poll().then(function (v) {
    blocked(v, true, true);
    assert.deepEqual(v.adopted_ids, []);
  });
});
test('publisher receipt never claims private adoption/physical stop', function () {
  var f = fixture();
  return f.publish().then(function (v) {
    assert.equal(v.durable_published, true);
    assert.equal(v.private_adopted, false);
    assert.equal(v.channel_status, 'NOT_RECHECKED');
    assert.equal(v.physical_stop, 'UNTESTED');
    assert.equal(f.calls.length, 0);
  });
});
test('fresh authorized intent commits observed Stop without deleting', function () {
  var f = fixture();
  f.stops.push(id(1));
  return f
    .start(2)
    .then(function (v) {
      assert.equal(v.blocked, false);
      assert.equal(v.private_adopted, false);
      assert.equal(v.durable_blocked, false);
      assert.deepEqual(f.last().consumed, [id(1)]);
      assert.deepEqual(f.stops, [id(1)]);
      return f.native.poll();
    })
    .then(function (v) {
      assert.equal(v.blocked, false);
    });
});
test('fresh Stop wins after committed Start', function () {
  var f = fixture();
  return f
    .start(1)
    .then(function () {
      f.stops.push(id(9));
      return f.native.mayAcquireInput();
    })
    .then(function (v) {
      blocked(v, true, true);
      assert.deepEqual(v.adopted_ids, [id(9)]);
      assert.deepEqual(f.last().consumed, []);
    });
});
test('used Start cannot clear a later Stop', function () {
  var f = fixture();
  return f
    .start(1)
    .then(function () {
      f.stops.push(id(2));
      return f.start(1);
    })
    .then(function (v) {
      blocked(v, false, true);
      assert.deepEqual(f.last().consumed, []);
      return f.native.poll();
    })
    .then(function (v) {
      blocked(v, true, true);
    });
});

test('unauthenticated boolean and SAM flags cannot Start with IO installed', function () {
  var f = fixture(),
    native = protocol._createForTests(f.io);
  return native
    .requestHomeStart({ authorized: true, nativeHomeStart: true })
    .then(function (v) {
      blocked(v, false, false);
      assert.equal(f.calls.length, 0);
    });
});
test('HOST authority must return an intent, not a boolean', function () {
  var f = fixture(),
    native = protocol._createForTests(f.io, function () {
      return true;
    });
  return native.requestHomeStart({ authorized: true }).then(function (v) {
    blocked(v, false, false);
    assert.equal(f.calls.length, 0);
  });
});
test('authority rejection never enters IO', function () {
  var f = fixture();
  return f.native.requestHomeStart({ authorized: true }).then(function (v) {
    blocked(v, false, false);
    assert.equal(f.calls.length, 0);
  });
});
test('missing transaction does not become a lease boolean', function () {
  return protocol
    ._createForTests({ lease: true })
    .poll()
    .then(function (v) {
      blocked(v, false, false);
    });
});
test('transaction returning true without callback denies', function () {
  return protocol
    ._createForTests({
      withControllerTransaction: function () {
        return true;
      }
    })
    .poll()
    .then(function (v) {
      blocked(v, false, false);
    });
});
test('boolean transaction capability denies without IO', function () {
  return protocol
    ._createForTests({
      withControllerTransaction: function (cb) {
        return cb(true);
      }
    })
    .poll()
    .then(function (v) {
      blocked(v, false, false);
    });
});
test('a callback after its transaction completed cannot run IO', function () {
  var callback,
    f = fixture(),
    native = protocol._createForTests({
      withControllerTransaction: function (cb) {
        callback = cb;
        return Promise.resolve(true);
      }
    });
  return native.poll().then(function (v) {
    blocked(v, false, false);
    assert.throws(function () {
      callback(f.tx);
    });
    assert.equal(f.calls.length, 0);
  });
});
test('busy native transaction never blocks independent Stop publication', function () {
  var f = fixture(),
    gate = deferred(),
    entered = deferred();
  f.hook = function (label) {
    if (label === 'load') {
      entered.resolve();
      return gate.promise;
    }
  };
  var active = f.native.poll();
  return entered.promise
    .then(function () {
      return f.native.poll();
    })
    .then(function (v) {
      blocked(v, false, false);
      assert.equal(v.reason, 'transaction-busy');
      return f.publish();
    })
    .then(function (v) {
      assert.equal(v.durable_published, true);
      f.hook = function () {};
      gate.resolve();
      return active;
    })
    .then(function (v) {
      blocked(v, true, true);
    });
});
test('failed checked controller lease denies before journal operations', function () {
  var f = fixture();
  f.io.withControllerTransaction = function () {
    return Promise.reject(Error('lease unavailable'));
  };
  return f.native.poll().then(function (v) {
    blocked(v, false, false);
    assert.equal(f.calls.length, 0);
  });
});
['overflow', 'pending', 'corrupt', 'unavailable'].forEach(function (status) {
  test(
    'typed ' +
      status +
      ' snapshot persists blocking but cannot acknowledge adoption',
    function () {
      var f = fixture();
      return f
        .start(1)
        .then(function () {
          f.scanStatus = status;
          return f.native.poll();
        })
        .then(function (v) {
          blocked(v, false, true);
          assert.equal(f.last().phase, 'blocked');
          return f.start(2);
        })
        .then(function (v) {
          blocked(v, false, true);
        });
    }
  );
});
[
  'empty',
  'too-many',
  'partial',
  'unknown-name',
  'wrong-seq',
  'wrong-prev',
  'unknown-phase',
  'wrong-schema',
  'over-bytes',
  'bad-ID',
  'duplicate-ID',
  'unsorted-ID',
  'unknown-consumption',
  'duplicate-intent'
].forEach(function (kind) {
  test(
    'private ' + kind + ' refuses without repairing or appending',
    function () {
      var f = fixture(),
        record = JSON.parse(f.records[0].raw);
      if (kind === 'empty') f.records.length = 0;
      else if (kind === 'too-many')
        for (var i = 0; i < 65; i++) f.records.push({ name: 'bad', raw: '{}' });
      else if (kind === 'partial') f.records[0].raw = '{';
      else if (kind === 'unknown-name') f.records[0].name = '.staging';
      else if (kind === 'over-bytes')
        f.records[0].raw = new Array(16386).join('x');
      else {
        if (kind === 'wrong-seq') record.seq = 3;
        if (kind === 'wrong-prev') record.prev = '0'.repeat(64);
        if (kind === 'unknown-phase') record.phase = 'enabled';
        if (kind === 'wrong-schema') record.extra = true;
        if (kind === 'bad-ID') record.seen = ['invalid'];
        if (kind === 'duplicate-ID') record.seen = [id(2), id(2)];
        if (kind === 'unsorted-ID') record.seen = [id(3), id(2)];
        if (kind === 'unknown-consumption') record.consumed = [id(2)];
        if (kind === 'duplicate-intent') record.intents = [id(2), id(2)];
        f.records[0].raw = encoded(record);
      }
      var before = JSON.stringify(f.records);
      return f.native.poll().then(function (v) {
        blocked(v, false, false);
        assert.equal(JSON.stringify(f.records), before);
      });
    }
  );
});
test('checked private read/sync unavailable cannot acknowledge durability', function () {
  var f = fixture();
  f.loadStatus = 'unavailable';
  return f.native.poll().then(function (v) {
    blocked(v, false, false);
    assert.equal(f.records.length, 1);
  });
});
test('missing previously observed Stop remains blocked without adoption', function () {
  var f = fixture();
  f.stops.push(id(2));
  return f
    .start(1)
    .then(function () {
      f.stops.length = 0;
      return f.native.poll();
    })
    .then(function (v) {
      blocked(v, false, true);
      assert.deepEqual(f.last().seen, [id(2)]);
      return f.start(3);
    })
    .then(function (v) {
      blocked(v, false, true);
    });
});
['prepare', 'commit'].forEach(function (phase) {
  test(
    'new Stop during asynchronous ' + phase + ' wins and is not consumed',
    function () {
      var f = fixture();
      f.hook = function (label) {
        if (label === 'append.' + phase) f.stops.push(id(9));
      };
      return f.start(1).then(function (v) {
        blocked(v, true, true);
        assert.deepEqual(v.adopted_ids, [id(9)]);
        assert.equal(f.last().consumed.indexOf(id(9)), -1);
      });
    }
  );
});
test('snapshot alias mutation cannot change observed private prepare/commit', function () {
  var f = fixture(),
    view;
  f.stops.push(id(2));
  f.readHook = function (v) {
    if (!view) view = v;
  };
  f.hook = function (label) {
    if (label === 'append.prepare') view.ids.push(id(9));
  };
  return f.start(1).then(function (v) {
    assert.equal(v.blocked, false);
    assert.deepEqual(f.last().seen, [id(2)]);
    assert.deepEqual(f.last().consumed, [id(2)]);
  });
});
test('oversized changed union preserves old15 and reports no adoption', function () {
  var f = fixture();
  for (var i = 1; i <= 15; i++) f.stops.push(id(i));
  var old = f.stops.slice();
  f.hook = function (label) {
    if (label === 'append.prepare') {
      f.stops.shift();
      f.stops.push(id(80), id(81));
    }
  };
  return f
    .start(50)
    .then(function (v) {
      blocked(v, false, true);
      assert.deepEqual(f.last().seen, old);
      return f.native.poll();
    })
    .then(function (v) {
      blocked(v, false, true);
      assert.deepEqual(f.last().seen, old);
    });
});
test('missing changed set below cap also reports no adoption', function () {
  var f = fixture();
  f.stops.push(id(2));
  f.hook = function (label) {
    if (label === 'append.prepare') f.stops.splice(0, 1, id(3));
  };
  return f.start(1).then(function (v) {
    blocked(v, false, true);
    assert.deepEqual(f.last().seen, [id(2)]);
  });
});
test('failed append ACK never authorizes Start and recovery blocks valid visible prepare', function () {
  var f = fixture(),
    original = f.tx.appendPrivate;
  f.tx.appendPrivate = function (v) {
    return original(v).then(function (ack) {
      ack.sha256 = 'bad';
      return ack;
    });
  };
  return f.start(1).then(function (v) {
    blocked(v, false, false);
    assert.notEqual(f.last().phase, 'commit');
  });
});
test('private capacity exhaustion blocks without deleting history', function () {
  var f = fixture(),
    chain = Promise.resolve();
  for (var i = 1; i < 35; i++)
    (function (n) {
      chain = chain.then(function () {
        return f.start(n);
      });
    })(i);
  return chain
    .then(function (v) {
      assert(v.blocked);
      assert(f.records.length <= 64);
      return f.native.poll();
    })
    .then(function (v) {
      blocked(v, false, true);
    });
});
test('full16 channel denies Start even if every ID was privately consumed', function () {
  var f = fixture(),
    previous = f.records[0].raw;
  for (var i = 1; i <= 16; i++) f.stops.push(id(i));
  ['prepare', 'commit'].forEach(function (phase, index) {
    var value = {
      v: 1,
      seq: index + 1,
      prev: digest(previous),
      phase: phase,
      seen: f.stops.slice(),
      consumed: index ? f.stops.slice() : [],
      intents: [id(40)]
    };
    previous = encoded(value);
    f.records.push({
      name: 'entry.000' + (index + 1) + '.json',
      raw: previous
    });
  });
  return f.native
    .poll()
    .then(function (v) {
      blocked(v, true, true);
      return f.start(41);
    })
    .then(function (v) {
      blocked(v, true, true);
      return f.publish();
    })
    .then(function (v) {
      assert.equal(v.durable_published, false);
      assert.equal(f.stops.length, 16);
    });
});
test('concurrent publisher own ACKs survive15 to17 and overflow denies native Start', function () {
  var f = fixture(),
    gate = deferred(),
    count = 0;
  for (var i = 1; i <= 15; i++) f.stops.push(id(i));
  f.publishHook = function () {
    if (++count === 2) gate.resolve();
    return gate.promise;
  };
  return Promise.all([f.publish(), f.publish()])
    .then(function (v) {
      assert(v[0].durable_published && v[1].durable_published);
      assert.notEqual(v[0].id, v[1].id);
      assert.equal(f.stops.length, 17);
      return f.start(1);
    })
    .then(function (v) {
      blocked(v, false, true);
    });
});
test('malformed publisher ACK is never a publication receipt', function () {
  var f = fixture();
  f.io.publishStop = function () {
    return Promise.resolve({ status: 'durable', id: 'invalid' });
  };
  return f.publish().then(function (v) {
    assert.equal(v.durable_published, false);
    assert.equal(v.private_adopted, false);
  });
});
['prepare', 'commit', 'blocked'].forEach(function (phase) {
  ['created', 'valid-unacknowledged'].forEach(function (stage) {
    test(
      'asynchronous process-state cut ' +
        phase +
        '/' +
        stage +
        ' recovers without replay',
      function () {
        var f = fixture(),
          cut = deferred(),
          never = deferred(),
          pending;
        f.stops.push(id(2));
        function begin() {
          f.hook = function (label) {
            if (label === 'append.' + phase) {
              if (stage === 'created') f.records[f.records.length - 1].raw = '';
              cut.resolve();
              return never.promise;
            }
          };
          pending = phase === 'blocked' ? f.native.poll() : f.start(1);
          return cut.promise;
        }
        return (
          phase === 'blocked'
            ? f.start(1).then(function () {
                f.stops.push(id(9));
                return begin();
              })
            : begin()
        )
          .then(function () {
            var reopened = f.reopen();
            f.hook = function () {};
            return reopened.poll();
          })
          .then(function (v) {
            var committed = phase === 'commit' && stage !== 'created';
            assert.equal(v.blocked, !committed);
            if (stage === 'created') assert.equal(v.durable_blocked, false);
            if (!committed && stage !== 'created')
              assert.equal(v.durable_blocked, true);
            if (stage !== 'created') {
              var reopened = f.reopen();
              return reopened
                .requestHomeStart({ testIntent: id(1) })
                .then(function (replay) {
                  assert(replay.blocked);
                });
            }
          });
      }
    );
  });
});
['created', 'valid-unacknowledged'].forEach(function (stage) {
  test(
    'publisher process-state cut ' + stage + ' never supplies durable ACK',
    function () {
      var f = fixture(),
        cut = deferred(),
        never = deferred();
      return f
        .start(1)
        .then(function () {
          f.io.publishStop = function () {
            f.stops.push(id(90));
            if (stage === 'created') f.scanStatus = 'pending';
            cut.resolve();
            return never.promise;
          };
          var pending = f.publish();
          return cut.promise;
        })
        .then(function () {
          return f.native.poll();
        })
        .then(function (v) {
          blocked(v, stage !== 'created', true);
          assert.equal(f.last().consumed.indexOf(id(90)), -1);
        });
    }
  );
});

test('newline-suffixed intent is not a nonce', function () {
  var f = fixture(),
    native = protocol._createForTests(f.io, function () {
      return id(1) + '\n';
    });
  return native.requestHomeStart({}).then(function (v) {
    blocked(v, false, false);
    assert.equal(f.calls.length, 0);
  });
});
test('newline-suffixed Stop ID is unknown, never privately adopted', function () {
  var f = fixture();
  f.stops.push(id(2) + '\n');
  return f.native.poll().then(function (v) {
    blocked(v, false, true);
    assert.deepEqual(f.last().seen, []);
  });
});
test('newline-suffixed publication receipt ID is rejected', function () {
  var f = fixture();
  f.io.publishStop = function () {
    return Promise.resolve({ status: 'durable', id: id(1) + '\n' });
  };
  return f.publish().then(function (v) {
    assert.equal(v.durable_published, false);
  });
});

test('returned adopted IDs are bounded copies and never a global publication drain', function () {
  var f = fixture();
  f.stops.push(id(2));
  return f.native
    .poll()
    .then(function (v) {
      assert.deepEqual(v.adopted_ids, [id(2)]);
      v.adopted_ids.push(id(999));
      return f.publish().then(function (receipt) {
        assert.equal(v.adopted_ids.indexOf(receipt.id), -1);
        assert.deepEqual(f.last().seen, [id(2)]);
        return receipt;
      });
    })
    .then(function (receipt) {
      return f.native.poll().then(function (v) {
        assert(v.private_adopted);
        assert(v.adopted_ids.indexOf(receipt.id) >= 0);
        assert.equal(v.adopted_ids.indexOf(id(999)), -1);
        assert(v.adopted_ids.length <= 16);
      });
    });
});
test('unknown snapshot with failed durability reports neither confirmation until recovered', function () {
  var f = fixture();
  return f
    .start(1)
    .then(function () {
      f.scanStatus = 'corrupt';
      f.hook = function (label) {
        if (label === 'append.blocked') {
          f.loadStatus = 'unavailable';
          throw Error('synthetic fsync failure');
        }
      };
      return f.native.poll();
    })
    .then(function (v) {
      blocked(v, false, false);
      f.loadStatus = 'snapshot';
      f.hook = function () {};
      return f.native.poll();
    })
    .then(function (v) {
      blocked(v, false, true);
    });
});
test('private controller serialization spans separate native wrappers', function () {
  var f = fixture(),
    gate = deferred(),
    ready = deferred();
  var held = f.io.withControllerTransaction(function () {
    ready.resolve();
    return gate.promise;
  });
  var other = protocol._createForTests(f.io);
  return ready.promise
    .then(function () {
      return other.poll();
    })
    .then(function (v) {
      blocked(v, false, false);
      assert.equal(f.calls.length, 0);
      gate.resolve();
      return held;
    });
});

[
  { nativeHomeStart: true },
  { nativeHomeAuto: true },
  { tile: true },
  true
].forEach(function (request, index) {
  test(
    'public legacy/automatic flag ' + index + ' has no Start authority',
    function () {
      var f = fixture(),
        native = protocol._createForTests(f.io);
      return native.requestHomeStart(request).then(function (v) {
        blocked(v, false, false);
        assert.equal(f.calls.length, 0);
      });
    }
  );
});
[
  'commit-without-prepare',
  'prepare-without-intent',
  'consumption-rollback',
  'intent-history-erased'
].forEach(function (kind) {
  test(
    'private transition ' + kind + ' is never adopted or repaired',
    function () {
      var f = fixture(),
        previous = f.records[0].raw;
      function add(phase, seen, consumed, intents) {
        var seq = f.records.length,
          raw = encoded({
            v: 1,
            seq: seq,
            prev: digest(previous),
            phase: phase,
            seen: seen,
            consumed: consumed,
            intents: intents
          });
        f.records.push({
          name: 'entry.' + ('0000' + seq).slice(-4) + '.json',
          raw: raw
        });
        previous = raw;
      }
      if (kind === 'commit-without-prepare') add('commit', [], [], []);
      else if (kind === 'prepare-without-intent') add('prepare', [], [], []);
      else {
        add('prepare', [id(1)], [], [id(2)]);
        add('commit', [id(1)], [id(1)], [id(2)]);
        if (kind === 'consumption-rollback')
          add('blocked', [id(1)], [], [id(2)]);
        else add('blocked', [id(1)], [id(1)], []);
      }
      var before = JSON.stringify(f.records);
      return f.native.poll().then(function (v) {
        blocked(v, false, false);
        assert.equal(JSON.stringify(f.records), before);
      });
    }
  );
});

test('premature transaction completion cannot leave a late private commit', function () {
  var f = fixture();
  f.io.withControllerTransaction = function (callback) {
    callback(f.tx).catch(function () {});
    return Promise.resolve(true);
  };
  return f
    .start(1)
    .then(function (v) {
      blocked(v, false, false);
      return new Promise(function (resolve) {
        setTimeout(resolve, 0);
      });
    })
    .then(function () {
      assert.equal(
        f.records.length,
        1,
        'closed transaction must not append prepare/commit'
      );
    });
});
test('transaction loss while prepare ACK is pending cannot later commit', function () {
  var f = fixture(),
    outer = deferred(),
    ack = deferred(),
    paused = deferred();
  f.io.withControllerTransaction = function (callback) {
    callback(f.tx).catch(function () {});
    return outer.promise;
  };
  f.hook = function (label) {
    if (label === 'append.prepare') {
      paused.resolve();
      outer.reject(Error('checked native lease lost'));
      return ack.promise;
    }
  };
  var result = f.start(1);
  return paused.promise
    .then(function () {
      return result;
    })
    .then(function (v) {
      blocked(v, false, false);
      ack.resolve();
      return new Promise(function (resolve) {
        setTimeout(resolve, 0);
      });
    })
    .then(function () {
      assert.equal(
        f.records.length,
        2,
        'lease loss must not append a commit after visible prepare'
      );
      assert.equal(f.last().phase, 'prepare');
    });
});

test('private serialization compatibility matches V2 rather than shared Stop canonical bytes', function () {
  var f = fixture();
  f.records[0].raw = ' { "v":9, ' + f.records[0].raw.slice(1);
  return f.native
    .poll()
    .then(function (v) {
      blocked(v, true, true);
      return f.start(1);
    })
    .then(function (v) {
      assert.equal(v.blocked, false);
      assert.equal(f.last().prev, digest(f.records[f.records.length - 2].raw));
    });
});

Promise.resolve()
  .then(function () {
    return cases.reduce(function (chain, t) {
      return chain
        .then(function () {
          return t.body();
        })
        .catch(function (e) {
          e.message = t.name + ': ' + e.message;
          throw e;
        });
    }, Promise.resolve());
  })
  .then(
    function () {
      console.log(
        'PASS Stop journal protocol ' +
          cases.length +
          ' cases (' +
          process.version +
          '), asynchronous HOST typed IO only; no native/TV acceptance'
      );
    },
    function (e) {
      console.error(e.stack);
      process.exitCode = 1;
    }
  );
