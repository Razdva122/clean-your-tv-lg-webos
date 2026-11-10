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
function fail() {
  throw Error('unsafe-storage');
}
function notice(log, target, warning) {
  try {
    if (log)
      log({
        event: warning
          ? 'state-permissions-warning'
          : 'state-permissions-error',
        target: target,
        reason: 'unsafe-storage',
        contract: events.normalize({
          schema: 1,
          component: 'storage',
          operation: 'prepare',
          phase: 'validate',
          field: target,
          expected: 'safe-storage',
          actual: { category: 'unsafe' },
          decision: warning ? 'retain' : 'refuse'
        })
      });
  } catch (ignore) {}
}
function session(directory, options, action) {
  options = options || {};
  var uid = process.getuid(),
    groups = process.getgroups(),
    parent,
    previous = process.cwd(),
    entered = false;
  if (groups.indexOf(process.getgid()) < 0) groups.push(process.getgid());
  if (
    typeof directory !== 'string' ||
    directory.charAt(0) !== '/' ||
    /\/\.\.?($|\/)/.test(directory)
  )
    fail();
  if (typeof c.O_NOFOLLOW !== 'number' || typeof c.O_DIRECTORY !== 'number')
    fail();
  directory = directory.replace(/\/+$/, '') || '/';
  function owned(s) {
    return s.uid === uid || (s.uid === 5999 && s.gid === 5000);
  }
  function ancestors() {
    for (var path = directory; ;) {
      var s = fs.lstatSync(path);
      if (!s.isDirectory() || s.isSymbolicLink()) fail();
      if (path === '/') break;
      path = path.slice(0, path.lastIndexOf('/')) || '/';
    }
  }
  function security(s) {
    var mode = s.mode & 4095,
      channel = options.role === 'channel';
    if (
      !owned(s) ||
      (options.role !== 'installer' && groups.indexOf(s.gid) < 0)
    )
      fail();
    if (
      channel
        ? mode !== 1528
        : mode & 3584 || (mode & 2 && !(options.legacy && mode === 511))
    )
      fail();
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
      fail();
    security(current);
  }
  function leaf(name, limit) {
    check();
    var s;
    try {
      s = fs.lstatSync(name);
    } catch (e) {
      if (e.code === 'ENOENT') return null;
      throw e;
    }
    if (!s.isFile() || s.nlink !== 1 || s.size > limit || s.mode & 3586) fail();
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
        if (n <= 0) fail();
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
  function write(name, bytes, mode, limit, preserve, original) {
    var initial = leaf(name, limit);
    if (preserve && initial) return;
    if (initial && groups.indexOf(initial.gid) < 0) fail();
    var path =
        (name === 'ssap-key.json' ? '.cytv-key-' : '.cytv-record-') +
        crypto.randomBytes(12).toString('hex'),
      fd,
      created = false,
      phase = 'write';
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
      if (
        !staged.isFile() ||
        staged.nlink !== 1 ||
        staged.uid !== uid ||
        !same(staged, fs.lstatSync(path))
      )
        fail();
      for (var offset = 0; offset < bytes.length;) {
        var n = fs.writeSync(fd, bytes, offset, bytes.length - offset);
        if (n <= 0) fail();
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
      throw error;
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
      fs.fchmodSync(parent, 504);
      before = fs.fstatSync(parent);
      check();
    }
    return action({
      uid: uid,
      groups: groups,
      owned: owned,
      read: read,
      leaf: leaf,
      write: write,
      check: check,
      stat: before
    });
  } finally {
    if (entered) process.chdir(previous);
    if (parent !== undefined) fs.closeSync(parent);
  }
}
function configuration(directory, options, repair) {
  options = options || {};
  return session(directory, { role: 'installer' }, function (s) {
    // Validate both configuration leaves before the first key mutation.
    var key = s.read('ssap-key.json', 65536),
      apps = s.read('apps.json', 16 * 1024 * 1024),
      replacing = false;
    if (apps && !s.owned(apps.stat)) fail();
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
          fail();
        replacing = true;
      } else if (mode & 7) {
        if (!repair || key.stat.uid !== s.uid || mode !== 509) fail();
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
            fail();
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
            fail();
          s.check();
        } finally {
          if (fd !== undefined) fs.closeSync(fd);
        }
      }
    }
    return true;
  });
}
function prepare(directory, log, initializeControl) {
  try {
    return session(directory, { legacy: true, normalize: true }, function (s) {
      if ((s.stat.mode & 4095) === 511) notice(log, 'directory', true);
      if (initializeControl)
        s.write('control.json', buffer('{}'), 432, Infinity, false);
      var ok = true;
      try {
        var key = s.read('ssap-key.json', 65536);
        if (key) {
          if (key.stat.gid !== s.stat.gid || s.groups.indexOf(key.stat.gid) < 0)
            fail();
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
                  fail();
                s.check();
                fs.fchmodSync(fd, 416);
                fs.fsyncSync(fd);
                if (
                  !same(key.stat, fs.lstatSync('ssap-key.json')) ||
                  (fs.fstatSync(fd).mode & 4095) !== 416
                )
                  fail();
              } catch (error) {
                // Preserve the existing runtime-only EPERM privacy repair.
                // Installer reclamation above still authenticates the exact hash.
                if (error.code !== 'EPERM' && error.code !== 'EACCES')
                  throw error;
                var adopted = JSON.parse(key.bytes.toString('utf8'));
                if (!adopted || typeof adopted.key !== 'string' || !adopted.key)
                  fail();
                s.write('ssap-key.json', key.bytes, 416, 65536, false, key);
              } finally {
                if (fd !== undefined) fs.closeSync(fd);
              }
            } else {
              var parsed;
              try {
                parsed = JSON.parse(key.bytes.toString('utf8'));
              } catch (ignore) {
                fail();
              }
              if (!parsed || typeof parsed.key !== 'string' || !parsed.key)
                fail();
              s.write('ssap-key.json', key.bytes, 416, 65536, false, key);
            }
          }
        }
      } catch (ignore) {
        ok = false;
        notice(log, 'ssap-key.json', false);
      }
      return initializeControl ? true : ok;
    });
  } catch (ignore) {
    notice(log, 'directory', false);
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
  return session(directory, { role: role }, function (s) {
    s.write(record[0], buffer(bytes), record[1], Infinity, false);
    return true;
  });
};
prepare.requestStop = function (directory, options) {
  return session(directory, { role: 'app' }, function (s) {
    s.leaf('blocked', Infinity);
    s.leaf('control.json', Infinity);
    s.write('blocked', buffer('stopped'), 436, Infinity, true);
    s.write('control.json', buffer('{"cmd":"stop"}'), 420, Infinity, false);
    return true;
  });
};
prepare.readConfiguration = function (directory, kind) {
  if (kind !== 'key' && kind !== 'apps') fail();
  return session(directory, { legacy: true }, function (s) {
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
      fail();
    return value.bytes.toString('utf8');
  });
};
module.exports = prepare;
