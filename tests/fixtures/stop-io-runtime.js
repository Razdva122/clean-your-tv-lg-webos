'use strict';
var assert = require('assert'),
  fs = require('fs'),
  path = require('path');
var crypto = require('crypto'),
  cp = require('child_process'),
  timed = require('./timeout-io'),
  heldTimed = require('./held-timeout-io');
var io = require('./stop-io'),
  denied = require('./denied-io'),
  missing = require('./missing-io');
var root = process.argv[2],
  journal = root + '/private/journal',
  raw =
    ' { "v":1, "seq":0, "prev":null, "phase":"blocked", "seen":[], "consumed":[], "intents":[] }\n';
var tests = [],
  count = 0,
  adapters = [];
function test(name, fn) {
  tests.push([name, fn]);
}
function adapter() {
  var a = io.create();
  adapters.push(a);
  return a;
}
function reject(p) {
  return p.then(
    function () {
      throw Error('expected rejection');
    },
    function (e) {
      return e;
    }
  );
}
function reset() {
  ['fault', 'hold-append', 'entered', 'release'].forEach(function (n) {
    try {
      fs.unlinkSync(root + '/' + n);
    } catch (e) {
      if (e.code !== 'ENOENT') throw e;
    }
  });
  fs.readdirSync(root + '/stop').forEach(function (n) {
    fs.unlinkSync(root + '/stop/' + n);
  });
  fs.readdirSync(journal).forEach(function (n) {
    fs.unlinkSync(journal + '/' + n);
  });
  fs.writeFileSync(journal + '/entry.0000.json', raw, { mode: 384 });
}
function check(v) {
  assert.strictEqual(v.status, 'snapshot');
  assert.strictEqual(v.records.length, 1);
  assert.strictEqual(v.records[0].name, 'entry.0000.json');
  assert.strictEqual(v.records[0].raw, raw);
}
function closeAll() {
  var list = adapters;
  adapters = [];
  return Promise.all(
    list.map(function (a) {
      return a.close();
    })
  );
}

test('default missing executable denies', function () {
  var entered = false;
  return reject(
    missing.withControllerTransaction(function () {
      entered = true;
      throw Error('must not enter');
    })
  ).then(function () {
    assert.strictEqual(entered, false);
    return missing.close();
  });
});
test('production missing binding denies', function () {
  var entered = false;
  return reject(
    denied.withControllerTransaction(function () {
      entered = true;
      throw Error('must not enter');
    })
  ).then(function () {
    assert.strictEqual(entered, false);
    return denied.close();
  });
});
test('actual child reads exact raw and rejects stale tx', function () {
  var a = adapter(),
    old;
  return a
    .withControllerTransaction(function (tx) {
      old = tx;
      return tx.readJournal().then(function (v) {
        check(v);
        return 'done';
      });
    })
    .then(function (v) {
      assert.strictEqual(v, 'done');
      return reject(old.readJournal());
    });
});
test('lease spans transactions and releases only after close', function () {
  var a = adapter(),
    b = adapter(),
    entered = false;
  return a
    .withControllerTransaction(function (tx) {
      return tx.readJournal();
    })
    .then(check)
    .then(function () {
      return reject(
        b.withControllerTransaction(function () {
          entered = true;
          throw Error('contender entered');
        })
      ).then(function (e) {
        assert.strictEqual(e.code, 'STOP_IO_NATIVE');
        assert.strictEqual(e.status, 2);
      });
    })
    .then(function () {
      assert.strictEqual(entered, false);
      return a.withControllerTransaction(function (tx) {
        return tx.readJournal();
      });
    })
    .then(check)
    .then(function () {
      return a.close();
    })
    .then(function () {
      var c = adapter();
      return c.withControllerTransaction(function (tx) {
        return tx.readJournal();
      });
    })
    .then(check);
});
test('overlapping transactions do not invoke second callback', function () {
  var a = adapter(),
    entered = false;
  return a
    .withControllerTransaction(function (tx) {
      return reject(
        a.withControllerTransaction(function () {
          entered = true;
          throw Error('nested callback');
        })
      ).then(function () {
        assert.strictEqual(entered, false);
        return tx.readJournal();
      });
    })
    .then(check);
});
test('one outstanding operation without a hidden queue', function () {
  var a = adapter();
  return a
    .withControllerTransaction(function (tx) {
      var first = tx.readJournal();
      return reject(tx.readJournal()).then(function () {
        return first;
      });
    })
    .then(check);
});
test('ordinary native read failure permits same-scope recovery', function () {
  var a = adapter();
  return a
    .withControllerTransaction(function (tx) {
      fs.unlinkSync(journal + '/entry.0000.json');
      return reject(tx.readJournal()).then(function (e) {
        assert.strictEqual(e.code, 'STOP_IO_NATIVE');
        fs.writeFileSync(journal + '/entry.0000.json', raw, { mode: 384 });
        return tx.readJournal();
      });
    })
    .then(check);
});
test('callback error ends transaction before reuse', function () {
  var a = adapter();
  return reject(
    a.withControllerTransaction(function (tx) {
      return tx.readJournal().then(function () {
        throw Error('callback failure');
      });
    })
  )
    .then(function () {
      return a.withControllerTransaction(function (tx) {
        return tx.readJournal();
      });
    })
    .then(check);
});
test('early callback completion drains then rejects', function () {
  var a = adapter(),
    pending,
    old;
  return reject(
    a.withControllerTransaction(function (tx) {
      old = tx;
      pending = tx.readJournal();
      return 'unsafe';
    })
  )
    .then(function (e) {
      assert.strictEqual(e.code, 'STOP_IO_EARLY_RETURN');
      return pending;
    })
    .then(check)
    .then(function () {
      return reject(old.readJournal());
    })
    .then(function () {
      return a.withControllerTransaction(function (tx) {
        return tx.readJournal();
      });
    })
    .then(check);
});
test('maximum bounded read preserves all raw bytes', function () {
  var spaces = new Array(16385).join(' ');
  for (var i = 0; i < 64; i++)
    fs.writeFileSync(
      journal + '/entry.' + ('0000' + i).slice(-4) + '.json',
      spaces,
      { mode: 384 }
    );
  var a = adapter();
  return a
    .withControllerTransaction(function (tx) {
      return tx.readJournal();
    })
    .then(function (v) {
      assert.strictEqual(v.records.length, 64);
      v.records.forEach(function (row, index) {
        assert.strictEqual(
          row.name,
          'entry.' + ('0000' + index).slice(-4) + '.json'
        );
        assert.strictEqual(row.raw, spaces);
      });
    });
});
test('unknown filename is not an empty snapshot', function () {
  var a = adapter();
  fs.writeFileSync(journal + '/foreign', 'x', { mode: 384 });
  return a
    .withControllerTransaction(function (tx) {
      return reject(tx.readJournal()).then(function () {
        fs.unlinkSync(journal + '/foreign');
        return tx.readJournal();
      });
    })
    .then(check);
});

test('cancel between BEGIN ACK and deferred callback prevents callback', function () {
  var cp = require('child_process'),
    spawn = cp.spawn,
    a = adapter(),
    called = false,
    cancelled = false,
    cancellation = null;
  cp.spawn = function () {
    var child = spawn.apply(cp, arguments),
      buffer = Buffer.alloc(0),
      scheduled = false;
    process.nextTick(function () {
      child.stdout.on('data', function (chunk) {
        if (scheduled) return;
        buffer = Buffer.concat([buffer, chunk]);
        while (buffer.length >= 16) {
          var len = buffer.readUInt32BE(12);
          if (buffer.length < 16 + len) return;
          var op = buffer[4];
          buffer = buffer.slice(16 + len);
          if (op === 1) {
            scheduled = true;
            Promise.resolve()
              .then(function () {})
              .then(function () {
                cancelled = true;
                cancellation = a.cancel();
              });
            return;
          }
        }
      });
    });
    return child;
  };
  var outer;
  try {
    outer = a.withControllerTransaction(function () {
      called = true;
      return 'must-not-run';
    });
  } finally {
    cp.spawn = spawn;
  }
  return reject(outer).then(function () {
    assert.strictEqual(cancelled, true);
    assert.strictEqual(called, false);
    return cancellation;
  });
});

function hash(s) {
  return crypto.createHash('sha256').update(s, 'utf8').digest('hex');
}
function event(seq, phase, prev, intents) {
  return (
    JSON.stringify({
      v: 1,
      seq: seq,
      prev: hash(prev),
      phase: phase,
      seen: [],
      consumed: [],
      intents: intents || []
    }) + '\n'
  );
}
function append(tx, body) {
  return tx.appendPrivate({ seq: 1, raw: body, sha256: hash(body) });
}
function delay(ms) {
  return new Promise(function (resolve) {
    setTimeout(resolve, ms);
  });
}
function fault(name) {
  fs.writeFileSync(root + '/fault', name);
}
function untilEntered() {
  var end = Date.now() + 5000;
  return new Promise(function (resolve, rejectFn) {
    function poll() {
      if (fs.existsSync(root + '/entered')) {
        resolve();
        return;
      }
      if (Date.now() > end) {
        rejectFn(Error('C hook not entered'));
        return;
      }
      setTimeout(poll, 5);
    }
    poll();
  });
}

test('actual append returns verified bytes hash and immutable intent', function () {
  var a = adapter(),
    body = event(1, 'blocked', raw);
  return a.withControllerTransaction(function (tx) {
    return tx
      .readJournal()
      .then(function () {
        var request = { seq: 1, raw: body, sha256: hash(body) },
          p = tx.appendPrivate(request);
        request.seq = 2;
        request.raw = 'corrupt';
        request.sha256 = 'bad';
        return p;
      })
      .then(function (r) {
        assert.strictEqual(r.status, 'durable');
        assert.strictEqual(r.seq, 1);
        assert.strictEqual(r.sha256, hash(body));
        return tx.readJournal();
      })
      .then(function (v) {
        assert.strictEqual(v.records[1].raw, body);
        v.records[0].raw = 'changed';
        v.records.length = 0;
        return tx.readJournal();
      })
      .then(function (v) {
        assert.strictEqual(v.records.length, 2);
        assert.strictEqual(v.records[0].raw, raw);
      });
  });
});
test('ordinary failed append leaves live recovery read', function () {
  var a = adapter(),
    body = event(1, 'prepare', raw, ['000000000000000000000000000000aa']);
  return a.withControllerTransaction(function (tx) {
    return tx
      .readJournal()
      .then(function () {
        fault('fail-append-sync');
        return reject(append(tx, body));
      })
      .then(function (e) {
        assert.strictEqual(e.code, 'STOP_IO_NATIVE');
        fs.unlinkSync(root + '/fault');
        return tx.readJournal();
      })
      .then(function (v) {
        assert.strictEqual(v.records.length, 2);
        assert.strictEqual(v.records[1].raw, body);
      });
  });
});
test('independent publisher bypasses held private transaction', function () {
  var a = adapter();
  return a.withControllerTransaction(function (tx) {
    return a.publishStop().then(function (r) {
      assert.strictEqual(r.status, 'durable');
      assert(/^[0-9a-f]{32}$/.test(r.id));
      return tx.scanStops().then(function (s) {
        assert.strictEqual(s.status, 'snapshot');
        assert.deepEqual(s.ids, [r.id]);
      });
    });
  });
});
['lock', 'journal', 'root'].forEach(function (target) {
  ['before', 'during'].forEach(function (boundary) {
    test(
      'SCAN rejects private ' +
        target +
        ' mode change ' +
        boundary +
        ' native scan',
      function () {
        var a = adapter(),
          p =
            target === 'root'
              ? root + '/private'
              : target === 'journal'
                ? journal
                : root + '/private/controller.lock',
          mode = target === 'lock' ? 384 : 448;
        return a.withControllerTransaction(function (tx) {
          return tx
            .readJournal()
            .then(function () {
              if (boundary === 'before')
                fs.chmodSync(p, target === 'lock' ? 420 : 493);
              else fault('scan-' + target + '-mode');
              return reject(tx.scanStops());
            })
            .then(
              function (e) {
                var changed = (fs.statSync(p).mode & 511) !== mode;
                fs.chmodSync(p, mode);
                assert.strictEqual(changed, true);
                assert.strictEqual(e.code, 'STOP_IO_NATIVE');
                assert.strictEqual(e.status, 1);
                return tx.readJournal();
              },
              function (e) {
                fs.chmodSync(p, mode);
                throw e;
              }
            )
            .then(check);
        });
      }
    );
  });
});
test('full Stop snapshot is explicit and publisher refuses full', function () {
  for (var i = 0; i < 16; i++) {
    var id = ('00000000000000000000000000000000' + i.toString(16)).slice(-32);
    fs.writeFileSync(
      root + '/stop/Stop.' + id,
      '{"id":"' + id + '","op":"stop","v":1}\n',
      { mode: 416 }
    );
  }
  var a = adapter();
  return a.withControllerTransaction(function (tx) {
    return tx.scanStops().then(function (v) {
      assert.strictEqual(v.ids.length, 16);
      return reject(a.publishStop());
    });
  });
});
test('full journal read cannot append', function () {
  for (var i = 1; i < 64; i++)
    fs.writeFileSync(
      journal + '/entry.' + ('0000' + i).slice(-4) + '.json',
      '{}\n',
      { mode: 384 }
    );
  var a = adapter();
  return a.withControllerTransaction(function (tx) {
    return tx.readJournal().then(function (v) {
      assert.strictEqual(v.records.length, 64);
      return reject(
        tx.appendPrivate({ seq: 63, raw: '{}', sha256: hash('{}') })
      )
        .then(function (e) {
          assert.strictEqual(e.code, 'STOP_IO_NATIVE');
          assert.strictEqual(e.status, 3);
          return tx.readJournal();
        })
        .then(function (v) {
          assert.strictEqual(v.records.length, 64);
        });
    });
  });
});
test('actual stdin backpressure drains before append receipt', function () {
  var a = adapter(),
    spawn = cp.spawn,
    appendPressure = false,
    appendDrained = false;
  cp.spawn = function () {
    var child = spawn.apply(cp, arguments),
      write = child.stdin.write;
    child.stdin._writableState.highWaterMark = 1;
    child.stdin.on('drain', function () {
      if (appendPressure) appendDrained = true;
    });
    child.stdin.write = function () {
      var isAppend = Buffer.isBuffer(arguments[0]) && arguments[0][4] === 4;
      // Modern Writable can synchronously drain even a one-byte high-water mark.
      // Cork the actual stream, not its return value. Node0.10 has no cork API;
      // its legacy Writable returns false for this bounded oversized write.
      var corked = isAppend && typeof child.stdin.cork === 'function';
      if (corked) child.stdin.cork();
      var ok;
      try {
        ok = write.apply(child.stdin, arguments);
      } finally {
        if (corked)
          process.nextTick(function () {
            child.stdin.uncork();
          });
      }
      if (isAppend && !ok) appendPressure = true;
      return ok;
    };
    return child;
  };
  var body = new Array(16385).join(' '),
    p;
  try {
    p = a.withControllerTransaction(function (tx) {
      return tx.readJournal().then(function () {
        return append(tx, body);
      });
    });
  } finally {
    cp.spawn = spawn;
  }
  return p.then(function (r) {
    assert.strictEqual(r.sha256, hash(body));
    assert.strictEqual(appendPressure, true);
    assert.strictEqual(appendDrained, true);
  });
});
test('split response chunks preserve exact read', function () {
  fault('split');
  var a = adapter();
  return a
    .withControllerTransaction(function (tx) {
      return tx.readJournal();
    })
    .then(check);
});
[
  'bad-magic',
  'old-id',
  'oversize',
  'partial',
  'bad-utf8',
  'nul',
  'trailing',
  'duplicate',
  'stdout-eof',
  'stderr-eof',
  'stderr-overflow'
].forEach(function (name) {
  test(
    'transport fault ' + name + ' closes scope without recovery',
    function () {
      var a = timed.create(),
        old;
      adapters.push(a);
      fault(name);
      return reject(
        a.withControllerTransaction(function (tx) {
          old = tx;
          return tx.readJournal().then(function () {
            return tx.readJournal();
          });
        })
      )
        .then(function () {
          return reject(old.readJournal());
        })
        .then(function () {
          if (fs.existsSync(root + '/fault')) fs.unlinkSync(root + '/fault');
          return reject(
            a.withControllerTransaction(function () {
              throw Error('must not restart');
            })
          );
        });
    }
  );
});
test('wrong append receipt never mints durability', function () {
  var a = adapter(),
    body = event(1, 'blocked', raw);
  return reject(
    a.withControllerTransaction(function (tx) {
      return tx.readJournal().then(function () {
        fault('wrong-receipt');
        return append(tx, body);
      });
    })
  ).then(function () {
    assert.strictEqual(
      fs.readFileSync(journal + '/entry.0001.json', 'utf8'),
      body
    );
  });
});
test('cancel blocked actual C append retains lease and independent Stop', function () {
  var a = adapter(),
    body = event(1, 'prepare', raw, ['000000000000000000000000000000ab']),
    settled = false,
    old;
  fs.writeFileSync(root + '/hold-append', '');
  var operation = a.withControllerTransaction(function (tx) {
    old = tx;
    return tx.readJournal().then(function () {
      return append(tx, body);
    });
  });
  var rejected = reject(operation).then(function (e) {
    settled = true;
    return e;
  });
  return untilEntered()
    .then(function () {
      a.cancel();
      return delay(50);
    })
    .then(function () {
      assert.strictEqual(settled, false);
      var b = adapter(),
        entered = false;
      return reject(
        b.withControllerTransaction(function () {
          entered = true;
        })
      ).then(function (e) {
        assert.strictEqual(e.code, 'STOP_IO_NATIVE');
        assert.strictEqual(e.status, 2);
        assert.strictEqual(entered, false);
        return a.publishStop();
      });
    })
    .then(function (r) {
      assert.strictEqual(r.status, 'durable');
      return reject(
        old.appendPrivate({ seq: 2, raw: '{}', sha256: hash('{}') })
      );
    })
    .then(function () {
      assert.strictEqual(settled, false);
      fs.writeFileSync(root + '/release', '');
      return rejected;
    })
    .then(function () {
      var c = adapter();
      return c.withControllerTransaction(function (tx) {
        return tx.readJournal();
      });
    })
    .then(function (v) {
      assert.strictEqual(v.records.length, 2);
      assert.strictEqual(v.records[1].raw, body);
    });
});
test('timeout is admission closure not proof of native release', function () {
  var a = heldTimed.create(),
    body = event(1, 'blocked', raw),
    settled = false;
  adapters.push(a);
  fs.writeFileSync(root + '/hold-append', '');
  var p = reject(
    a.withControllerTransaction(function (tx) {
      return tx.readJournal().then(function () {
        return append(tx, body);
      });
    })
  ).then(function (e) {
    settled = true;
    return e;
  });
  return untilEntered()
    .then(function () {
      heldTimed._expireTimeoutForTests();
      return delay(300);
    })
    .then(function () {
      assert.strictEqual(settled, false);
      var b = adapter();
      return reject(
        b.withControllerTransaction(function () {
          throw Error('contender entered');
        })
      );
    })
    .then(function () {
      fs.writeFileSync(root + '/release', '');
      return p;
    })
    .then(function (e) {
      assert.strictEqual(e.code, 'STOP_IO_TIMEOUT');
    });
});
test('durable unacknowledged prepare is read without replay', function () {
  var a = adapter(),
    body = event(1, 'prepare', raw, ['000000000000000000000000000000ac']);
  return reject(
    a.withControllerTransaction(function (tx) {
      return tx.readJournal().then(function () {
        fault('crash-append');
        return append(tx, body);
      });
    })
  )
    .then(function () {
      fs.unlinkSync(root + '/fault');
      var b = adapter();
      return b.withControllerTransaction(function (tx) {
        return tx.readJournal();
      });
    })
    .then(function (v) {
      assert.strictEqual(v.records.length, 2);
      assert.strictEqual(v.records[1].raw, body);
      assert.strictEqual(fs.readdirSync(journal).length, 2);
    });
});

function requestFrame(op, id, len) {
  var b = Buffer.alloc(16);
  b.write('CYI1', 0, 'ascii');
  b[4] = op;
  b.writeUInt32BE(id, 8);
  b.writeUInt32BE(len || 0, 12);
  return b;
}
function rawBroker(bytes, expectedFrames) {
  return new Promise(function (resolve, rejectFn) {
    var child = cp.spawn(process.argv[3], ['controller'], {
        stdio: ['pipe', 'pipe', 'pipe']
      }),
      stdout = Buffer.alloc(0),
      sent = false;
    child.on('error', rejectFn);
    child.stdin.on('error', function () {});
    child.stderr.on('data', function () {});
    child.stdout.on('data', function (chunk) {
      stdout = Buffer.concat([stdout, chunk]);
      if (stdout.length > 64) {
        rejectFn(Error('unexpected raw response size'));
        child.stdin.end();
        return;
      }
      if (!sent && stdout.length >= 16) {
        sent = true;
        assert.strictEqual(stdout[4], 0);
        assert.strictEqual(stdout[5], 0);
        child.stdin.end(bytes);
      }
    });
    child.on('close', function (code) {
      try {
        assert.strictEqual(sent, true);
        assert.strictEqual(code, 2);
        assert.strictEqual(stdout.length, 16 * expectedFrames);
        resolve();
      } catch (e) {
        rejectFn(e);
      }
    });
  });
}
[
  ['unknown opcode', requestFrame(99, 1), 1],
  ['oversized request', requestFrame(4, 1, 2147483647), 1],
  ['partial header', requestFrame(1, 1).slice(0, 7), 1],
  [
    'partial payload',
    Buffer.concat([requestFrame(4, 1, 8), Buffer.alloc(4)]),
    1
  ],
  [
    'reused request ID',
    Buffer.concat([requestFrame(1, 1), requestFrame(2, 1)]),
    2
  ]
].forEach(function (row) {
  test('native rejects ' + row[0] + ' and releases lease', function () {
    return rawBroker(row[1], row[2])
      .then(function () {
        var a = adapter();
        return a.withControllerTransaction(function (tx) {
          return tx.readJournal();
        });
      })
      .then(check);
  });
});
test('request ID exhaustion never wraps or enters callback', function () {
  var exhausted = require('./exhausted-io'),
    a = exhausted.create(),
    entered = false;
  adapters.push(a);
  return reject(
    a.withControllerTransaction(function () {
      entered = true;
    })
  ).then(function (e) {
    assert.strictEqual(e.code, 'STOP_IO_ID_EXHAUSTED');
    assert.strictEqual(entered, false);
  });
});
if (process.argv[4] === 'protocol') {
  var protocol = require('./stop-journal');
  function committedFixture() {
    var intents = ['000000000000000000000000000000af'],
      prep = event(1, 'prepare', raw, intents),
      commit = event(2, 'commit', prep, intents);
    fs.writeFileSync(journal + '/entry.0001.json', prep, { mode: 384 });
    fs.writeFileSync(journal + '/entry.0002.json', commit, { mode: 384 });
  }
  function changePrivate(target, change) {
    var p =
        target === 'root'
          ? root + '/private'
          : target === 'journal'
            ? journal
            : root + '/private/controller.lock',
      directory = target !== 'lock',
      mode = directory ? 448 : 384;
    if (change === 'mode') {
      fs.chmodSync(p, directory ? 493 : 420);
      return function () {
        fs.chmodSync(p, mode);
      };
    }
    fs.renameSync(p, p + '.saved');
    if (change === 'replace') {
      if (directory) fs.mkdirSync(p, mode);
      else fs.writeFileSync(p, '', { mode: mode });
    }
    return function () {
      if (change === 'replace') {
        if (directory) fs.rmdirSync(p);
        else fs.unlinkSync(p);
      }
      fs.renameSync(p + '.saved', p);
    };
  }
  test('preserved ES5 committed fixture permits input with valid lease', function () {
    committedFixture();
    return protocol
      ._createForTests(adapter())
      .mayAcquireInput()
      .then(function (r) {
        assert.strictEqual(r.blocked, false);
      });
  });
  [2, 3].forEach(function (boundary) {
    ['lock', 'journal', 'root'].forEach(function (target) {
      ['mode', 'missing', 'replace'].forEach(function (change) {
        test(
          'preserved ES5 denies ' +
            target +
            ' ' +
            change +
            ' after ' +
            (boundary === 2 ? 'READ' : 'SCAN'),
          function () {
            committedFixture();
            var a = adapter(),
              spawn = cp.spawn,
              restore = null,
              changed = false;
            cp.spawn = function () {
              var child = spawn.apply(cp, arguments),
                buffer = Buffer.alloc(0);
              process.nextTick(function () {
                child.stdout.on('data', function (chunk) {
                  if (changed) return;
                  buffer = Buffer.concat([buffer, chunk]);
                  while (buffer.length >= 16) {
                    var len = buffer.readUInt32BE(12);
                    assert(len <= 1048576 + 4096);
                    if (buffer.length < 16 + len) return;
                    var op = buffer[4];
                    buffer = buffer.slice(16 + len);
                    if (op === boundary) {
                      restore = changePrivate(target, change);
                      changed = true;
                      return;
                    }
                  }
                });
              });
              return child;
            };
            function cleanup() {
              cp.spawn = spawn;
              if (restore) {
                restore();
                restore = null;
              }
            }
            return protocol
              ._createForTests(a)
              .mayAcquireInput()
              .then(
                function (r) {
                  cleanup();
                  assert.strictEqual(
                    changed,
                    true,
                    'fixture mutation must execute'
                  );
                  assert.strictEqual(
                    r.blocked,
                    true,
                    'unsafe lease must not permit input'
                  );
                },
                function (e) {
                  cleanup();
                  throw e;
                }
              );
          }
        );
      });
    });
  });
  test('preserved ES5 protocol adopts actual published Stop', function () {
    var a = adapter(),
      p = protocol._createForTests(a),
      id;
    return a
      .publishStop()
      .then(function (r) {
        id = r.id;
        return p.poll();
      })
      .then(function (r) {
        assert.strictEqual(r.blocked, true);
        assert.strictEqual(r.durable_blocked, true);
        assert.strictEqual(r.private_adopted, true);
        assert.deepEqual(r.adopted_ids, [id]);
        assert.strictEqual(r.physical_stop, 'UNTESTED');
        return p.requestHomeStart({ authorized: true, nativeHomeStart: true });
      })
      .then(function (r) {
        assert.strictEqual(r.blocked, true);
        assert.strictEqual(r.authorization, 'UNIMPLEMENTED');
      });
  });
  test('preserved ES5 protocol blocks actual unacknowledged prepare without commit', function () {
    var a = adapter(),
      body = event(1, 'prepare', raw, ['000000000000000000000000000000ad']);
    return reject(
      a.withControllerTransaction(function (tx) {
        return tx.readJournal().then(function () {
          fault('crash-append');
          return append(tx, body);
        });
      })
    )
      .then(function () {
        fs.unlinkSync(root + '/fault');
        var b = adapter();
        return protocol._createForTests(b).poll();
      })
      .then(function (r) {
        assert.strictEqual(r.blocked, true);
        assert.strictEqual(r.durable_blocked, true);
        assert.strictEqual(r.physical_stop, 'UNTESTED');
        var names = fs.readdirSync(journal).sort();
        assert.strictEqual(names.length, 3);
        names.forEach(function (name) {
          assert.notStrictEqual(
            JSON.parse(fs.readFileSync(journal + '/' + name, 'utf8')).phase,
            'commit'
          );
        });
        assert.strictEqual(
          JSON.parse(fs.readFileSync(journal + '/entry.0002.json', 'utf8'))
            .phase,
          'blocked'
        );
      });
  });
}

test('oversized caller raw is rejected before Buffer copy', function () {
  var a = adapter(),
    large = new Array(32769).join('x'),
    request = { seq: 1, raw: large, sha256: hash(large) };
  return a.withControllerTransaction(function (tx) {
    return tx
      .readJournal()
      .then(function () {
        var from = Buffer.from;
        Buffer.from = function (value) {
          if (typeof value === 'string' && value.length > 16384) {
            var e = Error('unbounded copy');
            e.code = 'TEST_UNBOUNDED_COPY';
            throw e;
          }
          return from.apply(Buffer, arguments);
        };
        var result;
        try {
          result = tx.appendPrivate(request);
        } finally {
          Buffer.from = from;
        }
        return reject(result);
      })
      .then(function (e) {
        assert.strictEqual(e.code, 'STOP_IO_REQUEST');
        return tx.readJournal();
      })
      .then(check);
  });
});

var chain = Promise.resolve();
tests.forEach(function (item) {
  chain = chain.then(function () {
    reset();
    return Promise.resolve()
      .then(item[1])
      .then(
        function () {
          count++;
          return closeAll();
        },
        function (e) {
          return closeAll().then(function () {
            throw Error(item[0] + ': ' + e.stack);
          });
        }
      );
  });
});
chain.then(
  function () {
    console.log('PASS ' + count + ' actual child cases on ' + process.version);
  },
  function (e) {
    console.error(e.stack);
    process.exitCode = 1;
  }
);
