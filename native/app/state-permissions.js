'use strict';
// Canonical synchronous storage operations. No installed-device source fallback.
var fs = require('fs'),
  c = fs.constants || require('constants'),
  crypto = require('crypto'),
  events = require('./contract-events');
function buffer(value) {
  return typeof Buffer.from === 'function'
    ? Buffer.from(value)
    : new Buffer(value);
}
function same(a, b) {
  return a.dev === b.dev && a.ino === b.ino;
}
function unchanged(a, b) {
  return (
    same(a, b) &&
    a.uid === b.uid &&
    a.gid === b.gid &&
    a.mode === b.mode &&
    a.nlink === b.nlink &&
    a.size === b.size &&
    a.mtime.getTime() === b.mtime.getTime() &&
    a.ctime.getTime() === b.ctime.getTime()
  );
}
function field(name) {
  var names = {
    directory: 'directory',
    'ssap-key.json': 'key',
    'apps.json': 'apps',
    'control.json': 'control',
    'controller.log': 'logger',
    'controller.log.previous': 'logger-previous',
    'controller.pid': 'pid',
    'home-control.json': 'home-preference',
    'startup-state.json': 'startup-state'
  };
  if (Object.prototype.hasOwnProperty.call(names, name)) return names[name];
  if (/^(home|input|catalog)-(request|response)\.json$/.test(name))
    return name.slice(0, -5);
  return name === 'blocked' ? 'blocked' : 'staging';
}
function actual(stat, limit) {
  var value = { category: 'unsafe' };
  if (stat) {
    value.uid = stat.uid;
    value.gid = stat.gid;
    value.mode = stat.mode & 4095;
    value.size = stat.size;
  }
  if (isFinite(limit)) value.limit = limit;
  return value;
}
function failure(error, target, rule, observed, operation, phase) {
  try {
    if (!error.contractEvents) {
      if (typeof error.errno === 'number')
        observed.errno = Math.abs(error.errno);
      error.contractEvents = [
        events.normalize({
          schema: 1,
          component: 'storage',
          operation: operation || 'prepare',
          phase: phase || 'validate',
          field: target || 'directory',
          expected: rule || 'storage-io',
          actual: observed || { category: 'unsafe' },
          decision: 'refuse'
        })
      ];
    }
  } catch (ignore) {}
  return error;
}
function fail(target, rule, observed, operation, phase) {
  throw failure(
    Error('unsafe-storage'),
    target,
    rule,
    observed || { category: 'unsafe' },
    operation,
    phase
  );
}
function notice(log, target, warning, error) {
  try {
    var event = events.normalize(
      error && error.contractEvents
        ? error.contractEvents[0]
        : {
            schema: 1,
            component: 'storage',
            operation: 'prepare',
            phase: 'validate',
            field: field(target),
            expected: 'safe-mode',
            actual: { category: 'unsafe' },
            decision: warning ? 'retain' : 'refuse'
          }
    );
    if (event && warning) event.decision = 'retain';
    if (log)
      log({
        event: warning
          ? 'state-permissions-warning'
          : 'state-permissions-error',
        target: target,
        reason: 'unsafe-storage',
        contract: event
      });
  } catch (ignore) {}
}
function session(directory, options, action) {
  options = options || {};
  var uid = process.getuid(),
    groups = process.getgroups(),
    parent,
    previous = process.cwd(),
    entered = false,
    target = 'directory',
    phase = 'validate',
    observed = { category: 'unsafe' };
  function fail(rule, stat, limit, name) {
    throw failure(
      Error('unsafe-storage'),
      name || target,
      rule || 'stable-inode',
      stat ? actual(stat, limit) : observed,
      options.operation || 'prepare',
      phase
    );
  }
  if (groups.indexOf(process.getgid()) < 0) groups.push(process.getgid());
  if (
    typeof directory !== 'string' ||
    directory.charAt(0) !== '/' ||
    /\/\.\.?($|\/)/.test(directory)
  )
    fail('absolute-directory');
  if (typeof c.O_NOFOLLOW !== 'number' || typeof c.O_DIRECTORY !== 'number')
    fail('nofollow-supported');
  directory = directory.replace(/\/+$/, '') || '/';
  function owned(s) {
    return s.uid === uid || (s.uid === 5999 && s.gid === 5000);
  }
  function ancestors() {
    for (var path = directory; ;) {
      var s = fs.lstatSync(path);
      if (!s.isDirectory() || s.isSymbolicLink())
        fail('directory-type', s, undefined, 'directory');
      if (path === '/') break;
      path = path.slice(0, path.lastIndexOf('/')) || '/';
    }
  }
  function security(s) {
    var mode = s.mode & 4095,
      channel = options.role === 'channel';
    if (!owned(s)) fail('trusted-owner', s, undefined, 'directory');
    if (options.role !== 'installer' && groups.indexOf(s.gid) < 0)
      fail('shared-group', s, undefined, 'directory');
    if (
      channel
        ? mode !== 1528
        : mode & 3584 || (mode & 2 && !(options.legacy && mode === 511))
    )
      fail('safe-mode', s, undefined, 'directory');
  }
  var before;
  function check() {
    ancestors();
    var current = fs.lstatSync(directory),
      opened = fs.fstatSync(parent);
    if (
      !same(before, current) ||
      !same(before, opened) ||
      current.uid !== before.uid ||
      current.gid !== before.gid ||
      current.mode !== before.mode ||
      opened.uid !== before.uid ||
      opened.gid !== before.gid ||
      opened.mode !== before.mode ||
      (entered && !same(before, fs.statSync('.')))
    )
      fail('stable-inode', current, undefined, 'directory');
    security(current);
  }
  function leaf(name, limit) {
    check();
    target = field(name);
    phase = 'read';
    observed = { category: 'unavailable' };
    var s;
    try {
      s = fs.lstatSync(name);
      observed = actual(s, limit);
    } catch (e) {
      if (e.code === 'ENOENT') return null;
      throw e;
    }
    if (!s.isFile() || s.nlink !== 1) fail('single-regular-file', s, limit);
    if (s.size > limit) fail('bounded-file', s, limit);
    if (s.mode & 3586) fail('safe-mode', s, limit);
    return s;
  }
  function read(name, limit) {
    var s = leaf(name, limit),
      fd;
    if (!s) return null;
    try {
      fd = fs.openSync(name, c.O_RDONLY | c.O_NOFOLLOW | c.O_NONBLOCK);
      if (!unchanged(s, fs.fstatSync(fd)) || !unchanged(s, fs.lstatSync(name)))
        fail();
      var bytes =
          typeof Buffer.alloc === 'function'
            ? Buffer.alloc(s.size)
            : new Buffer(s.size),
        offset = 0;
      while (offset < bytes.length) {
        var n = fs.readSync(fd, bytes, offset, bytes.length - offset, offset);
        if (n <= 0) fail('complete-io');
        offset += n;
      }
      if (!unchanged(s, fs.fstatSync(fd)) || !unchanged(s, fs.lstatSync(name)))
        fail();
      check();
      return { stat: s, bytes: bytes };
    } finally {
      if (fd !== undefined) fs.closeSync(fd);
    }
  }
  // Fixed runtime log only. Pin and compare the no-follow descriptor before
  // append; ordinary lines do not rewrite/fsync the bounded history.
  function appendLog(bytes, initial) {
    target = 'logger';
    phase = 'write';
    observed = actual(initial, 131072);
    var fd;
    try {
      check();
      fd = fs.openSync(
        'controller.log',
        c.O_WRONLY | c.O_APPEND | c.O_NOFOLLOW | c.O_NONBLOCK
      );
      if (
        !unchanged(initial, fs.fstatSync(fd)) ||
        !unchanged(initial, fs.lstatSync('controller.log'))
      )
        fail('stable-inode');
      for (var offset = 0; offset < bytes.length;) {
        var n = fs.writeSync(fd, bytes, offset, bytes.length - offset);
        if (n <= 0) fail('complete-io');
        offset += n;
      }
      var after = fs.fstatSync(fd);
      if (
        !same(initial, after) ||
        after.uid !== initial.uid ||
        after.gid !== initial.gid ||
        after.mode !== initial.mode ||
        after.nlink !== 1 ||
        after.size !== initial.size + bytes.length ||
        !unchanged(after, fs.lstatSync('controller.log'))
      )
        fail('stable-inode', after);
      check();
    } finally {
      if (fd !== undefined) fs.closeSync(fd);
    }
  }
  function write(name, bytes, mode, limit, preserve, original) {
    var initial = leaf(name, limit);
    if (preserve && initial) return;
    if (initial && groups.indexOf(initial.gid) < 0)
      fail('shared-group', initial);
    phase = 'write';
    var path =
        (name === 'ssap-key.json' ? '.cytv-key-' : '.cytv-record-') +
        crypto.randomBytes(12).toString('hex'),
      fd,
      created = false;
    phase = 'write';
    target = 'staging';
    observed = { category: 'unsafe', size: bytes.length };
    try {
      check();
      fd = fs.openSync(
        path,
        c.O_WRONLY | c.O_CREAT | c.O_EXCL | c.O_NOFOLLOW,
        384
      );
      created = true;
      // The pinned cwd prevents a path substitution from receiving private bytes.
      check();
      var staged = fs.fstatSync(fd);
      observed = actual(staged, limit);
      if (
        !staged.isFile() ||
        staged.nlink !== 1 ||
        staged.uid !== uid ||
        !same(staged, fs.lstatSync(path))
      )
        fail();
      for (var offset = 0; offset < bytes.length;) {
        var n = fs.writeSync(fd, bytes, offset, bytes.length - offset);
        if (n <= 0) fail('complete-io');
        offset += n;
      }
      phase = 'chmod';
      if (fs.fstatSync(fd).gid !== before.gid)
        fs.fchownSync(fd, uid, before.gid);
      fs.fchmodSync(fd, mode);
      fs.fsyncSync(fd);
      staged = fs.fstatSync(fd);
      if (
        staged.uid !== uid ||
        staged.gid !== before.gid ||
        (staged.mode & 4095) !== mode ||
        staged.nlink !== 1 ||
        !same(staged, fs.lstatSync(path))
      )
        fail();
      check();
      var current = leaf(name, limit);
      if (
        original &&
        (!current ||
          !unchanged(original.stat, current) ||
          read(name, limit).bytes.toString('hex') !==
            original.bytes.toString('hex'))
      )
        fail();
      if (
        !preserve &&
        (initial ? !current || !unchanged(initial, current) : current)
      )
        fail();
      phase = 'rename';
      if (preserve) {
        try {
          fs.linkSync(path, name);
        } catch (e) {
          if (e.code !== 'EEXIST') throw e;
          leaf(name, limit);
        }
      } else {
        fs.renameSync(path, name);
        created = false;
      }
      fs.fsyncSync(parent);
    } catch (error) {
      try {
        error.storagePhase = phase;
      } catch (ignore) {}
      throw failure(
        error,
        target,
        'storage-io',
        observed,
        options.operation || 'prepare',
        phase
      );
    } finally {
      if (fd !== undefined) fs.closeSync(fd);
      if (created) fs.unlinkSync(path);
    }
  }
  try {
    ancestors();
    parent = fs.openSync(directory, c.O_RDONLY | c.O_NOFOLLOW | c.O_DIRECTORY);
    before = fs.fstatSync(parent);
    security(before);
    check();
    process.chdir(directory);
    entered = true;
    check();
    if (
      options.normalize &&
      before.uid === uid &&
      options.role !== 'channel' &&
      (before.mode & 4095) !== 504
    ) {
      try {
        fs.fchmodSync(parent, 504);
        var normalized = fs.fstatSync(parent);
        if (
          !same(before, normalized) ||
          normalized.uid !== before.uid ||
          normalized.gid !== before.gid ||
          (normalized.mode & 4095) !== 504
        )
          fail();
        before = normalized;
      } catch (error) {
        if (error.code !== 'EPERM' && error.code !== 'EACCES') throw error;
        // Permission denial does not waive the original snapshot or policy.
        check();
        notice(
          options.log,
          'directory',
          true,
          failure(
            error,
            'directory',
            'safe-mode',
            actual(before),
            options.operation,
            'chmod'
          )
        );
      }
      check();
    }
    return action({
      uid: uid,
      groups: groups,
      owned: owned,
      read: read,
      appendLog: appendLog,
      leaf: leaf,
      write: write,
      check: check,
      stat: before
    });
  } catch (error) {
    throw failure(
      error,
      target,
      'storage-io',
      observed,
      options.operation || 'prepare',
      phase
    );
  } finally {
    if (entered) process.chdir(previous);
    if (parent !== undefined) fs.closeSync(parent);
  }
}
function configuration(directory, options, repair) {
  options = options || {};
  return session(
    directory,
    { role: 'installer', operation: repair ? 'prepare' : 'inspect' },
    function (s) {
      // Validate both configuration leaves before the first key mutation.
      var key = s.read('ssap-key.json', 65536),
        apps = s.read('apps.json', 16 * 1024 * 1024),
        replacing = false;
      if (apps && !s.owned(apps.stat))
        fail(
          'apps',
          'trusted-owner',
          actual(apps.stat),
          repair ? 'prepare' : 'inspect',
          'validate'
        );
      if (key) {
        var mode = key.stat.mode & 4095;
        if (!s.owned(key.stat)) {
          if (
            !repair ||
            !/^[a-f0-9]{64}$/.test(options.expectedHash || '') ||
            key.stat.gid !== s.stat.gid ||
            s.groups.indexOf(key.stat.gid) < 0 ||
            [416, 509].indexOf(mode) < 0 ||
            crypto.createHash('sha256').update(key.bytes).digest('hex') !==
              options.expectedHash
          )
            fail(
              'key',
              'authenticated-key',
              actual(key.stat),
              repair ? 'prepare' : 'inspect',
              'validate'
            );
          replacing = true;
        } else if (mode & 7) {
          if (!repair || key.stat.uid !== s.uid || mode !== 509)
            fail(
              'key',
              'private-key',
              actual(key.stat),
              repair ? 'prepare' : 'inspect',
              'validate'
            );
        }
        if (replacing)
          s.write('ssap-key.json', key.bytes, 416, 65536, false, key);
        else if (mode & 7) {
          var fd;
          try {
            fd = fs.openSync(
              'ssap-key.json',
              c.O_RDONLY | c.O_NOFOLLOW | c.O_NONBLOCK
            );
            if (
              !unchanged(key.stat, fs.fstatSync(fd)) ||
              !unchanged(key.stat, fs.lstatSync('ssap-key.json'))
            )
              fail(
                'key',
                'stable-inode',
                actual(key.stat),
                repair ? 'prepare' : 'inspect',
                'chmod'
              );
            s.check();
            fs.fchmodSync(fd, 416);
            fs.fsyncSync(fd);
            var after = fs.fstatSync(fd);
            if (
              !same(after, key.stat) ||
              after.uid !== key.stat.uid ||
              after.gid !== key.stat.gid ||
              after.nlink !== 1 ||
              (after.mode & 4095) !== 416 ||
              !same(after, fs.lstatSync('ssap-key.json'))
            )
              fail(
                'key',
                'stable-inode',
                actual(key.stat),
                repair ? 'prepare' : 'inspect',
                'chmod'
              );
            s.check();
          } catch (error) {
            throw failure(
              error,
              'key',
              'storage-io',
              actual(key.stat),
              repair ? 'prepare' : 'inspect',
              'chmod'
            );
          } finally {
            if (fd !== undefined) fs.closeSync(fd);
          }
        }
      }
      return true;
    }
  );
}
function prepare(directory, log, initializeControl) {
  var settings = { legacy: true, normalize: true, log: log };
  try {
    return session(directory, settings, function (s) {
      if ((s.stat.mode & 4095) === 511)
        notice(
          log,
          'directory',
          true,
          failure(
            Error('unsafe-storage'),
            'directory',
            'safe-mode',
            actual(s.stat)
          )
        );
      if (initializeControl)
        s.write('control.json', buffer('{}'), 432, Infinity, false);
      var ok = true;
      try {
        var key = s.read('ssap-key.json', 65536);
        if (key) {
          if (key.stat.gid !== s.stat.gid || s.groups.indexOf(key.stat.gid) < 0)
            fail(
              'key',
              'shared-group',
              actual(key.stat),
              'prepare',
              'validate'
            );
          if ((key.stat.mode & 4095) !== 416) {
            if (key.stat.uid === s.uid) {
              var fd;
              try {
                fd = fs.openSync(
                  'ssap-key.json',
                  c.O_RDONLY | c.O_NOFOLLOW | c.O_NONBLOCK
                );
                if (
                  !unchanged(key.stat, fs.fstatSync(fd)) ||
                  !unchanged(key.stat, fs.lstatSync('ssap-key.json'))
                )
                  fail(
                    'key',
                    'stable-inode',
                    actual(key.stat),
                    'prepare',
                    'chmod'
                  );
                s.check();
                fs.fchmodSync(fd, 416);
                fs.fsyncSync(fd);
                if (
                  !same(key.stat, fs.lstatSync('ssap-key.json')) ||
                  (fs.fstatSync(fd).mode & 4095) !== 416
                )
                  fail(
                    'key',
                    'valid-key',
                    actual(key.stat),
                    'prepare',
                    'validate'
                  );
              } catch (error) {
                // Preserve the existing runtime-only EPERM privacy repair.
                // Installer reclamation above still authenticates the exact hash.
                if (error.code !== 'EPERM' && error.code !== 'EACCES')
                  throw error;
                var adopted = JSON.parse(key.bytes.toString('utf8'));
                if (!adopted || typeof adopted.key !== 'string' || !adopted.key)
                  fail(
                    'key',
                    'valid-key',
                    actual(key.stat),
                    'prepare',
                    'validate'
                  );
                s.write('ssap-key.json', key.bytes, 416, 65536, false, key);
              } finally {
                if (fd !== undefined) fs.closeSync(fd);
              }
            } else {
              var parsed;
              try {
                parsed = JSON.parse(key.bytes.toString('utf8'));
              } catch (ignore) {
                fail(
                  'key',
                  'valid-key',
                  actual(key.stat),
                  'prepare',
                  'validate'
                );
              }
              if (!parsed || typeof parsed.key !== 'string' || !parsed.key)
                fail(
                  'key',
                  'valid-key',
                  actual(key.stat),
                  'prepare',
                  'validate'
                );
              s.write('ssap-key.json', key.bytes, 416, 65536, false, key);
            }
          }
        }
      } catch (ignore) {
        ok = false;
        notice(
          log,
          'ssap-key.json',
          false,
          failure(
            ignore,
            'key',
            'storage-io',
            key ? actual(key.stat) : { category: 'unsafe' },
            'prepare',
            'read'
          )
        );
      }
      return initializeControl ? true : ok;
    });
  } catch (ignore) {
    notice(log, 'directory', false, ignore);
    return false;
  }
}
// Fixed file classes only. Existing protocol payload bounds are retained; outputs
// with no historical bound are not given a new speculative cap.
var records = {
  control: ['control.json', 432, 'app'],
  'home-preference': ['home-control.json', 432, 'app'],
  'startup-state': ['startup-state.json', 420, 'service'],
  pid: ['controller.pid', 420, 'app'],
  logger: ['controller.log', 420, 'app']
};
['home', 'input', 'catalog'].forEach(function (prefix) {
  records[prefix + '-request'] = [prefix + '-request.json', 432, 'channel'];
  records[prefix + '-response'] = [prefix + '-response.json', 432, 'channel'];
});
prepare.inspectConfiguration = function (directory, options) {
  return configuration(directory, options, false);
};
prepare.prepareConfiguration = function (directory, options) {
  return configuration(directory, options, true);
};
prepare.atomicRecord = function (directory, kind, bytes, options) {
  if (
    !Object.prototype.hasOwnProperty.call(records, kind) ||
    (typeof bytes !== 'string' && !Buffer.isBuffer(bytes))
  )
    fail();
  var record = records[kind],
    role = record[2];
  if (options && options.role !== undefined) {
    if (role !== 'channel' || ['app', 'channel'].indexOf(options.role) < 0)
      fail();
    role = options.role;
  }
  var settings = {
    role: role,
    legacy: role !== 'channel',
    operation: 'record'
  };
  return session(directory, settings, function (s) {
    s.write(record[0], buffer(bytes), record[1], Infinity, false);
    return true;
  });
};
prepare.requestStop = function (directory, options) {
  return session(directory, { role: 'app', operation: 'stop' }, function (s) {
    s.leaf('blocked', Infinity);
    s.leaf('control.json', Infinity);
    s.write('blocked', buffer('stopped'), 436, Infinity, true);
    s.write('control.json', buffer('{"cmd":"stop"}'), 420, Infinity, false);
    return true;
  });
};
prepare.readConfiguration = function (directory, kind) {
  if (kind !== 'key' && kind !== 'apps')
    fail(
      'directory',
      'fixed-record',
      { category: 'invalid' },
      'read',
      'validate'
    );
  return session(directory, { legacy: true, operation: 'read' }, function (s) {
    var value = s.read(
      kind === 'key' ? 'ssap-key.json' : 'apps.json',
      kind === 'key' ? 65536 : 16 * 1024 * 1024
    );
    if (!value) {
      var error = Error('missing-configuration');
      error.code = 'ENOENT';
      throw error;
    }
    if (
      value.stat.gid !== s.stat.gid ||
      s.groups.indexOf(value.stat.gid) < 0 ||
      (kind === 'key' && (value.stat.mode & 4095) !== 416)
    )
      fail(
        kind,
        kind === 'key' ? 'private-key' : 'shared-group',
        actual(value.stat),
        'read',
        'validate'
      );
    return value.bytes.toString('utf8');
  });
};
// The sole log writer uses the same checked descriptors/staging as runtime
// records. Both fixed destinations are validated before any rotation mutation.
prepare.appendLog = function (directory, line) {
  if (typeof line !== 'string' || Buffer.byteLength(line, 'utf8') > 131071)
    fail('logger', 'bounded-file', { limit: 131071 }, 'logger', 'write');
  return session(
    directory,
    { legacy: true, operation: 'logger' },
    function (s) {
      var current = s.leaf('controller.log', 131072),
        previous = s.leaf('controller.log.previous', 131072),
        bytes = buffer(line + '\n');
      if (current && current.size + bytes.length > 131072) {
        s.write(
          'controller.log.previous',
          s.read('controller.log', 131072).bytes,
          420,
          131072,
          false
        );
        s.write('controller.log', bytes, 420, 131072, false);
      } else if (current) s.appendLog(bytes, current);
      else s.write('controller.log', bytes, 420, 131072, false);
      return true;
    }
  );
};
prepare.readLogEvents = function (directory) {
  var result = { schema: 1, telemetry: 'legacy', events: [] };
  try {
    return session(
      directory,
      { legacy: true, operation: 'collect' },
      function (s) {
        var recorder = events.create(),
          files = [
            s.read('controller.log.previous', 131072),
            s.read('controller.log', 131072)
          ];
        files.forEach(function (file) {
          if (!file) return;
          file.bytes
            .toString('utf8')
            .split('\n')
            .forEach(function (line) {
              if (line.length > 16480) return;
              try {
                var item = JSON.parse(line),
                  values = [];
                if (item.event === 'contract-event') values = [item.contract];
                if (
                  item.event === 'contract-snapshot' &&
                  item.contract &&
                  item.contract.schema === 1
                )
                  values = item.contract.events;
                else if (item.event !== 'contract-event') return;
                result.telemetry = 'read';
                events.exportEvents(values).forEach(function (event) {
                  var old = recorder.snapshot().events,
                    count = 0;
                  for (var i = 0; i < old.length; i++) {
                    var a = events.normalize(old[i]),
                      b = events.normalize(event);
                    count = a.count;
                    delete a.count;
                    delete b.count;
                    delete a.first;
                    delete b.first;
                    delete a.last;
                    delete b.last;
                    if (JSON.stringify(a) === JSON.stringify(b)) {
                      event.count = Math.max(0, event.count - count);
                      break;
                    }
                  }
                  if (event.count > 0) recorder.record(event);
                });
              } catch (ignore) {}
            });
        });
        result.events = events.exportEvents(recorder.snapshot());
        return result;
      }
    );
  } catch (ignore) {
    return { schema: 1, telemetry: 'unavailable', events: [] };
  }
};
module.exports = prepare;
