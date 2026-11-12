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
// webOS can widen the mode of a retained Stop file. These are replacement
// inputs only; a generation that is read and used must still be mode 0664.
function expandedStopMode(stat) {
  var mode = stat.mode & 4095;
  return mode === 509 || mode === 511; // 0775 or 0777
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
  // Root SSH can use the packaged group without joining it; kernel I/O and
  // checked inode ownership/modes still have to succeed. Options grant nothing.
  function canAccessGroup(gid) {
    return uid === 0 || groups.indexOf(gid) >= 0;
  }
  function owned(s) {
    return s.uid === uid || (s.uid === 5999 && s.gid === 5000);
  }
  function ancestors() {
    for (var path = directory; ;) {
      var s = fs.lstatSync(path);
      if (!s.isDirectory() || s.isSymbolicLink())
        fail('directory-type', s, undefined, 'directory');
      if (options.channelParent && path === options.channelParent.path) {
        var outer = options.channelParent.stat;
        if (
          !same(outer, s) ||
          s.uid !== outer.uid ||
          s.gid !== outer.gid ||
          s.mode !== outer.mode
        )
          fail('stable-inode', s, undefined, 'directory');
      }
      if (path === '/') break;
      path = path.slice(0, path.lastIndexOf('/')) || '/';
    }
  }
  function security(s) {
    var mode = s.mode & 4095,
      channel = options.role === 'channel',
      channelParent = options.role === 'channel-parent';
    // The private child is created inside the checked package-owned directory.
    // Only its owner or the existing trusted group can create or replace it.
    if (
      options.channelParent
        ? s.gid !== options.channelParent.stat.gid
        : !owned(s)
    )
      fail('trusted-owner', s, undefined, 'directory');
    if (options.role !== 'installer' && !canAccessGroup(s.gid))
      fail('shared-group', s, undefined, 'directory');
    if (
      channel || channelParent
        ? mode !== 1528 && !(channelParent && mode === 509)
        : mode & 3584 || (mode & 2 && !(options.legacy && mode === 511))
    )
      fail('safe-mode', s, undefined, 'directory');
  }
  var before, bootSnapshot;
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
  function leaf(name, limit, replacingOutput) {
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
    if (
      s.mode & 3586 &&
      !(
        bootSnapshot &&
        bootSnapshot.name === name &&
        unchanged(bootSnapshot.stat, s) &&
        (s.mode & 4095) === 511
      ) &&
      !(
        replacingOutput &&
        (options.output === name ||
          (Array.isArray(options.output) &&
            options.output.indexOf(name) >= 0)) &&
        (s.mode & 4095) === 511 &&
        s.gid === before.gid &&
        canAccessGroup(s.gid)
      ) &&
      !(
        options.preserveStop &&
        name === 'blocked' &&
        (s.mode & 4095) === 511 &&
        s.gid === before.gid &&
        canAccessGroup(s.gid)
      )
    )
      fail('safe-mode', s, limit);
    return s;
  }
  function read(name, limit, writable) {
    var s = leaf(name, limit),
      fd;
    if (!s) return null;
    try {
      fd = fs.openSync(
        name,
        (writable ? c.O_RDWR : c.O_RDONLY) | c.O_NOFOLLOW | c.O_NONBLOCK
      );
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
  function invalidateGeneration() {
    var name = 'stop-generation',
      initial = leaf(name, 33),
      fd;
    try {
      if (!initial) {
        try {
          fd = fs.openSync(
            name,
            c.O_RDWR | c.O_CREAT | c.O_EXCL | c.O_NOFOLLOW | c.O_NONBLOCK,
            384
          );
        } catch (error) {
          if (error.code !== 'EEXIST') throw error;
          initial = leaf(name, 33);
        }
        if (fd !== undefined) {
          var created = fs.fstatSync(fd);
          if (
            !created.isFile() ||
            created.nlink !== 1 ||
            created.uid !== uid ||
            !same(created, fs.lstatSync(name))
          )
            fail('stable-inode');
          if (created.gid !== before.gid) fs.fchownSync(fd, uid, before.gid);
          fs.fchmodSync(fd, 436);
          fs.fsyncSync(fd);
          fs.fsyncSync(parent);
          check();
          return;
        }
      }
      if (
        !initial ||
        initial.gid !== before.gid ||
        (initial.mode & 4095) !== 436
      )
        fail('safe-mode', initial);
      fd = fs.openSync(name, c.O_RDWR | c.O_NOFOLLOW | c.O_NONBLOCK);
      if (
        !unchanged(initial, fs.fstatSync(fd)) ||
        !unchanged(initial, fs.lstatSync(name))
      )
        fail('stable-inode');
      check();
      fs.ftruncateSync(fd, 0);
      fs.fsyncSync(fd);
      if (!same(initial, fs.lstatSync(name))) fail('stable-inode');
      check();
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
  function write(name, bytes, mode, limit, preserve, original, concurrent) {
    var initial = leaf(name, limit, true);
    if (preserve && initial) return false;
    if (initial && !canAccessGroup(initial.gid)) fail('shared-group', initial);
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
      var current = leaf(name, limit, true);
      if (
        original &&
        (!current ||
          !unchanged(original.stat, current) ||
          (original.bytes &&
            read(name, limit).bytes.toString('hex') !==
              original.bytes.toString('hex')))
      )
        fail();
      if (
        !preserve &&
        !concurrent &&
        (initial ? !current || !unchanged(initial, current) : current)
      )
        fail();
      phase = 'rename';
      var published = true;
      if (preserve) {
        try {
          fs.linkSync(path, name);
        } catch (e) {
          if (e.code !== 'EEXIST') throw e;
          leaf(name, limit);
          published = false;
        }
        fs.unlinkSync(path);
        created = false;
      } else {
        fs.renameSync(path, name);
        created = false;
      }
      fs.fsyncSync(parent);
      return published;
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
  function installPauseGroupMatches() {
    if (typeof process.getegid === 'function')
      return process.getegid() === before.gid;
    // Legacy Node has no getegid. Check the group an exclusive create actually
    // receives in this directory before touching either Stop latch.
    var probe = '.cytv-record-' + crypto.randomBytes(12).toString('hex');
    check();
    var fd = fs.openSync(
      probe,
      c.O_WRONLY | c.O_CREAT | c.O_EXCL | c.O_NOFOLLOW,
      384
    );
    try {
      return fs.fstatSync(fd).gid === before.gid;
    } finally {
      fs.closeSync(fd);
      fs.unlinkSync(probe);
    }
  }
  function publishInstallPause(snapshot, pause) {
    var name = 'stop-generation';
    function publishExclusive() {
      // Legacy Stop writers reject a multi-link generation. Publish a single
      // inode with the final mode and group from the instant it is created.
      check();
      var fd,
        previousMask = process.umask(0);
      try {
        fd = fs.openSync(
          name,
          c.O_WRONLY | c.O_CREAT | c.O_EXCL | c.O_NOFOLLOW,
          436
        );
      } catch (error) {
        if (error.code === 'EEXIST') return false;
        throw error;
      } finally {
        process.umask(previousMask);
      }
      try {
        var opened = fs.fstatSync(fd);
        if (
          !opened.isFile() ||
          opened.nlink !== 1 ||
          opened.uid !== uid ||
          opened.gid !== before.gid ||
          (opened.mode & 4095) !== 436 ||
          !same(opened, leaf(name, 33) || {})
        )
          return false;
        var bytes = buffer(pause);
        if (fs.writeSync(fd, bytes, 0, bytes.length, 0) !== bytes.length)
          fail('complete-io');
        fs.fsyncSync(fd);
        fs.fsyncSync(parent);
        var current = read(name, 33);
        return (
          !!current &&
          same(opened, current.stat) &&
          current.bytes.toString('utf8') === pause
        );
      } finally {
        fs.closeSync(fd);
      }
    }
    if (!snapshot) return publishExclusive();
    // Capture the actual current inode atomically, then create exclusively.
    // An ordinary check followed by rename could overwrite a user Stop
    // published in between. A crash before publication retains the Stop latch.
    var saved = '.cytv-record-' + crypto.randomBytes(12).toString('hex'),
      moved = false,
      published = false;
    check();
    var fd = fs.openSync(
      saved,
      c.O_WRONLY | c.O_CREAT | c.O_EXCL | c.O_NOFOLLOW,
      384
    );
    fs.closeSync(fd);
    try {
      check();
      fs.renameSync(name, saved);
      moved = true;
      var captured = read(saved, 33, true);
      if (
        !captured ||
        !same(snapshot.stat, captured.stat) ||
        snapshot.stat.uid !== captured.stat.uid ||
        snapshot.stat.gid !== captured.stat.gid ||
        snapshot.stat.mode !== captured.stat.mode ||
        snapshot.bytes.toString('hex') !== captured.bytes.toString('hex')
      )
        fail('stable-inode', captured && captured.stat, 33, 'staging');
      published = publishExclusive();
      return published;
    } finally {
      try {
        if (moved && !published) {
          check();
          var retained = leaf(saved, 33);
          if (
            retained &&
            retained.gid === before.gid &&
            (retained.mode & 4095) === 436
          ) {
            try {
              fs.linkSync(saved, name);
              fs.fsyncSync(parent);
            } catch (error) {
              if (error.code !== 'EEXIST') throw error;
            }
          }
        }
      } finally {
        fs.unlinkSync(saved);
      }
    }
  }
  function replaceGeneration(previous) {
    var name = 'stop-generation';
    if (
      previous &&
      (previous.gid !== before.gid ||
        ((previous.mode & 4095) !== 436 && !expandedStopMode(previous)))
    )
      throw Error('Invalid Stop storage');
    var token = 'S' + crypto.randomBytes(16).toString('hex');
    write(
      name,
      buffer(token),
      436,
      33,
      !previous,
      previous && { stat: previous }
    );
    return token;
  }
  function expanded(name, limit, requireOwner) {
    check();
    var stat;
    try {
      stat = fs.lstatSync(name);
    } catch (error) {
      if (error.code === 'ENOENT') return null;
      throw error;
    }
    if ((stat.mode & 4095) !== 511) return null;
    if (
      (requireOwner && !owned(stat)) ||
      stat.gid !== before.gid ||
      !canAccessGroup(stat.gid)
    )
      fail('trusted-owner', stat, limit, field(name));
    bootSnapshot = { name: name, stat: stat };
    try {
      return read(name, limit);
    } finally {
      bootSnapshot = null;
    }
  }
  function replace(name, original, mode, limit) {
    if ((original.stat.mode & 4095) === 511)
      bootSnapshot = { name: name, stat: original.stat };
    try {
      write(name, original.bytes, mode, limit, false, original);
    } finally {
      bootSnapshot = null;
    }
  }
  function restrict(name, original, mode, limit) {
    target = field(name);
    phase = 'chmod';
    observed = actual(original.stat, limit);
    var fd;
    try {
      fd = fs.openSync(name, c.O_RDONLY | c.O_NOFOLLOW | c.O_NONBLOCK);
      if (
        !unchanged(original.stat, fs.fstatSync(fd)) ||
        !unchanged(original.stat, fs.lstatSync(name))
      )
        fail('stable-inode');
      check();
      fs.fchmodSync(fd, mode);
      fs.fsyncSync(fd);
      var current = read(name, limit);
      if (
        !current ||
        !same(original.stat, current.stat) ||
        original.stat.uid !== current.stat.uid ||
        original.stat.gid !== current.stat.gid ||
        (current.stat.mode & 4095) !== mode ||
        original.bytes.toString('hex') !== current.bytes.toString('hex')
      )
        fail('stable-inode');
    } finally {
      if (fd !== undefined) fs.closeSync(fd);
    }
  }
  function bootstrap() {
    // Only these retained values need a checked copy. A key is still just a
    // candidate credential until the TV's existing SSAP registration succeeds.
    var rules = [
        ['ssap-key.json', 416],
        ['home-control.json', 432],
        ['startup-state.json', 420]
      ],
      pending = [];
    rules.forEach(function (rule) {
      var original = expanded(rule[0], 65536, true);
      if (!original) return;
      var value = JSON.parse(original.bytes.toString('utf8'));
      if (
        !value ||
        typeof value !== 'object' ||
        Array.isArray(value) ||
        (rule[0] === 'ssap-key.json'
          ? typeof value.key !== 'string' || !value.key
          : typeof value.enabled !== 'boolean')
      )
        fail('valid-record', original.stat, 65536, field(rule[0]));
      pending.push([rule, original]);
    });
    pending.forEach(function (item) {
      replace(item[0][0], item[1], item[0][1], 65536);
    });
  }
  try {
    ancestors();
    parent = fs.openSync(directory, c.O_RDONLY | c.O_NOFOLLOW | c.O_DIRECTORY);
    before = fs.fstatSync(parent);
    if (options.expectedDirectory && !same(before, options.expectedDirectory))
      fail('stable-inode', before, undefined, 'directory');
    security(before);
    check();
    process.chdir(directory);
    entered = true;
    check();
    var expandedDirectory = (before.mode & 4095) === 511;
    if (
      options.requireStopEvidence &&
      expandedDirectory &&
      !(before.uid === 5999 && before.gid === 5000) &&
      !leaf('stop-generation', 33, true)
    )
      fail('safe-mode', before, undefined, 'directory');
    var repairedGeneration;
    if (
      (options.normalize || (options.repairGeneration && expandedDirectory)) &&
      (before.uid === uid ||
        (uid === 0 &&
          (options.role === 'installer' || options.repairGeneration))) &&
      options.role !== 'channel' &&
      (before.mode & 4095) !== 504
    ) {
      if (expandedDirectory) {
        var previousGeneration = leaf('stop-generation', 33, true);
        // Publish the replacement while setup readers still reject this
        // directory. A failed write must leave the expanded mode unchanged.
        if (options.repairGeneration || previousGeneration)
          repairedGeneration = replaceGeneration(previousGeneration);
      }
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
        if (options.role === 'installer') throw error;
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
      canAccessGroup: canAccessGroup,
      owned: owned,
      read: read,
      invalidateGeneration: invalidateGeneration,
      appendLog: appendLog,
      leaf: leaf,
      write: write,
      check: check,
      stat: before,
      repairedGeneration: repairedGeneration,
      replaceGeneration: replaceGeneration,
      publishInstallPause: publishInstallPause,
      installPauseGroupMatches: installPauseGroupMatches,
      bootstrap: bootstrap,
      expanded: expanded,
      replace: replace,
      restrict: restrict
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
    {
      role: 'installer',
      operation: repair ? 'prepare' : 'inspect',
      legacy: repair,
      normalize: repair,
      output: repair ? 'stop-generation' : undefined
    },
    function (s) {
      if (repair && s.stat.mode & 2)
        fail('safe-mode', s.stat, undefined, 'directory');
      // Validate both configuration leaves before the first key mutation.
      var key =
          (repair && s.expanded('ssap-key.json', 65536, false)) ||
          s.read('ssap-key.json', 65536),
        apps =
          (repair && s.expanded('apps.json', 16 * 1024 * 1024, true)) ||
          s.read('apps.json', 16 * 1024 * 1024),
        replacing = false;
      if (apps && !s.owned(apps.stat))
        fail(
          'apps',
          'trusted-owner',
          actual(apps.stat),
          repair ? 'prepare' : 'inspect',
          'validate'
        );
      // Root-origin repair keeps its original capsule proof even after the
      // adapter permanently becomes the packaged configuration owner.
      if (
        key &&
        options.requireHash &&
        (!repair ||
          !/^[a-f0-9]{64}$/.test(options.expectedHash || '') ||
          crypto.createHash('sha256').update(key.bytes).digest('hex') !==
            options.expectedHash)
      )
        fail('authenticated-key', key.stat, 65536, 'key');
      if (key) {
        var mode = key.stat.mode & 4095;
        // Trusted read ownership does not grant chmod authority over a
        // noncaller key; privacy repair must authenticate its original bytes.
        if (!s.owned(key.stat) || (key.stat.uid !== s.uid && mode & 7)) {
          if (
            !repair ||
            !/^[a-f0-9]{64}$/.test(options.expectedHash || '') ||
            key.stat.gid !== s.stat.gid ||
            !s.canAccessGroup(key.stat.gid) ||
            [416, 509, 511].indexOf(mode) < 0 ||
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
          if (!repair || key.stat.uid !== s.uid || [509, 511].indexOf(mode) < 0)
            fail(
              'key',
              'private-key',
              actual(key.stat),
              repair ? 'prepare' : 'inspect',
              'validate'
            );
        }
      }
      // A fresh private inode disconnects pre-repair writable descriptors.
      if (key && repair && (mode === 511 || (options.requireHash && mode & 7)))
        replacing = true;
      if (repair && apps && (apps.stat.mode & 4095) === 511)
        s.restrict('apps.json', apps, 420, 16 * 1024 * 1024);
      if (key) {
        if (replacing) s.replace('ssap-key.json', key, 416, 65536);
        else if (mode & 7) s.restrict('ssap-key.json', key, 416, 65536);
      }
      return true;
    }
  );
}
function prepare(directory, log, initializeControl) {
  var settings = {
    legacy: true,
    normalize: true,
    log: log,
    output: ['control.json', 'stop-generation']
  };
  try {
    return session(directory, settings, function (s) {
      s.bootstrap();
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
          if (key.stat.gid !== s.stat.gid || !s.canAccessGroup(key.stat.gid))
            fail(
              'key',
              'shared-group',
              actual(key.stat),
              'prepare',
              'validate'
            );
          if ((key.stat.mode & 4095) !== 416) {
            if (key.stat.uid === s.uid) {
              try {
                s.restrict('ssap-key.json', key, 416, 65536);
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
// The installed channel can be owned by a different UID. Under the known
// 0775 drift, use its group-writable namespace only to find a private child.
function channelSession(directory, settings, create, action) {
  var outerSettings = {
    role: 'channel-parent',
    operation: settings.operation,
    output: settings.output
  };
  return session(directory, outerSettings, function (outer) {
    if ((outer.stat.mode & 4095) === 1528) return action(outer);
    var name = '.private',
      fd;
    if (create) {
      outer.check();
      try {
        fs.mkdirSync(name, 448); // 0700 until the owner establishes the shared group.
      } catch (error) {
        if (error.code !== 'EEXIST') throw error;
      }
      var child = fs.lstatSync(name);
      if (
        child.isDirectory() &&
        child.uid === outer.uid &&
        (child.mode & 4095) === 448
      ) {
        try {
          fd = fs.openSync(name, c.O_RDONLY | c.O_NOFOLLOW | c.O_DIRECTORY);
          if (
            !same(child, fs.fstatSync(fd)) ||
            !same(child, fs.lstatSync(name))
          )
            fail('directory', 'stable-inode');
          outer.check();
          if (child.gid !== outer.stat.gid)
            fs.fchownSync(fd, child.uid, outer.stat.gid);
          fs.fchmodSync(fd, 1528);
        } finally {
          if (fd !== undefined) fs.closeSync(fd);
        }
      }
    }
    outer.check();
    settings.channelParent = { path: directory, stat: outer.stat };
    return session(directory + '/' + name, settings, action);
  });
}
prepare.readChannelRecord = function (directory, kind) {
  var record =
    Object.prototype.hasOwnProperty.call(records, kind) && records[kind];
  if (!record || record[2] !== 'channel') fail();
  return channelSession(
    directory,
    { role: 'channel', operation: 'record' },
    false,
    function (s) {
      var value = s.read(record[0], 2 * 1024 * 1024);
      if (!value) {
        var error = Error('channel record unavailable');
        error.code = 'ENOENT';
        throw error;
      }
      return value.bytes.toString('utf8');
    }
  );
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
    operation: 'record',
    output: record[0]
  };
  function write(s) {
    s.write(record[0], buffer(bytes), record[1], Infinity, false);
    return true;
  }
  return role === 'channel'
    ? channelSession(directory, settings, /-request$/.test(kind), write)
    : session(directory, settings, write);
};
function retainStop(s) {
  s.leaf('blocked', Infinity);
  s.write('blocked', buffer('stopped'), 436, Infinity, true);
}
prepare.retainStop = function (directory) {
  return session(
    directory,
    { role: 'app', operation: 'stop', legacy: true, preserveStop: true },
    retainStop
  );
};
prepare.requestStop = function (directory, options) {
  var legacyCleanup = options && options.legacyCleanup === true,
    forInstall = options && options.forInstall === true,
    generation,
    expectedDirectory =
      (options && options.expectedDirectory) || fs.lstatSync(directory);
  var publicationError;
  try {
    generation = prepare.publishStopGeneration(directory, {
      legacyCleanup: legacyCleanup,
      expectedDirectory: expectedDirectory,
      forInstall: forInstall
    });
  } catch (error) {
    if (forInstall) throw error;
    publicationError = error;
  }
  var result;
  try {
    result = session(
      directory,
      {
        role: 'app',
        operation: 'stop',
        output: ['control.json', 'stop-generation'],
        legacy: legacyCleanup,
        expectedDirectory: expectedDirectory,
        preserveStop: true
      },
      function (s) {
        s.leaf('blocked', Infinity);
        s.leaf('control.json', Infinity, true);
        var writeError;
        try {
          retainStop(s);
        } catch (error) {
          writeError = error;
        }
        try {
          s.write(
            'control.json',
            buffer('{"cmd":"stop"}'),
            420,
            Infinity,
            false
          );
        } catch (error) {
          if (!writeError) writeError = error;
        }
        if (writeError) throw writeError;
        return true;
      }
    );
  } catch (error) {
    throw publicationError || error;
  }
  if (publicationError) throw publicationError;
  return forInstall ? generation : result;
};
prepare.stopGeneration = function (directory, create) {
  var manual = create === 'manual',
    repair = manual || create === 'install',
    name = 'stop-generation';
  return session(
    directory,
    {
      role: 'app',
      operation: 'stop',
      legacy: repair,
      repairGeneration: repair,
      output: repair ? name : undefined
    },
    function (s) {
      if ((s.stat.mode & 4095) === 511) {
        // Explicit Start retains the published boot recovery path when the
        // runtime can use the directory but only the packaged owner can chmod it.
        // Setup always requires a checked generation in private storage.
        if (manual) return null;
        throw Error('Stop storage is not private');
      }
      if (s.uid !== 0 && !(s.stat.mode & (s.stat.uid === s.uid ? 128 : 16)))
        throw Error('Stop storage is not writable');
      var expected = s.repairedGeneration,
        previous = repair ? s.leaf(name, 33, true) : null;
      if (
        previous &&
        (previous.gid !== s.stat.gid ||
          ((previous.mode & 4095) !== 436 && !expandedStopMode(previous)))
      )
        throw Error('Invalid Stop storage');
      if (
        repair &&
        !expected &&
        previous &&
        (expandedStopMode(previous) || previous.size === 0)
      ) {
        // Never adopt expanded bytes or the failed-Stop sentinel. An S token
        // also prevents a pending fresh setup from adopting a new I token.
        expected = s.replaceGeneration(previous);
      }
      var value = s.read(name, 33, true);
      if (
        !value &&
        create === 'setup' &&
        (s.leaf('blocked', Infinity) || s.leaf('watchdog', Infinity))
      )
        return null;
      if (
        !value &&
        !expected &&
        (repair || create === true || create === 'setup')
      ) {
        var initial = 'I' + crypto.randomBytes(16).toString('hex');
        s.write(name, buffer(initial), 436, 33, true);
        if (repair) expected = initial;
        value = s.read(name, 33, true);
      }
      if (
        value &&
        (value.stat.gid !== s.stat.gid || (value.stat.mode & 4095) !== 436)
      )
        throw Error('Invalid Stop storage');
      var token = value && value.bytes.toString('utf8');
      if (
        !token ||
        !/^[IS][a-f0-9]{32}$/.test(token) ||
        (expected && token !== expected)
      )
        throw Error('Invalid Stop generation');
      return token;
    }
  );
};
prepare.publishStopGeneration = function (directory, options) {
  var legacyCleanup = options && options.legacyCleanup === true,
    forInstall = options && options.forInstall === true,
    expectedDirectory = options && options.expectedDirectory;
  try {
    return session(
      directory,
      {
        role: 'app',
        operation: 'stop',
        legacy: !forInstall,
        repairGeneration: !forInstall,
        expectedDirectory: expectedDirectory,
        requireStopEvidence: !legacyCleanup,
        output: 'stop-generation'
      },
      function (s) {
        if ((s.stat.mode & 4095) === 511 && legacyCleanup !== true)
          throw Error('Stop storage is not private');
        if (forInstall) {
          // Exclusive publication requires the final group from inode creation.
          // An unsupported SSH group must fall back before taking the latch.
          if (!s.installPauseGroupMatches())
            throw Error('Installer pause needs the shared effective group');
          // Pin the generation before looking at the latches. Exclusively
          // acquire blocked before changing it, so we cannot adopt an
          // existing safety latch or advance a generation we did not read.
          var snapshot = s.read('stop-generation', 33, true);
          if (
            snapshot &&
            (snapshot.stat.gid !== s.stat.gid ||
              (snapshot.stat.mode & 4095) !== 436 ||
              !/^[IS][a-f0-9]{32}$/.test(snapshot.bytes.toString('utf8')))
          )
            throw Error('Invalid Stop generation');
          if (
            s.leaf('watchdog', Infinity) ||
            !s.write('blocked', buffer('stopped'), 436, Infinity, true)
          )
            throw Error('Existing Stop prevents installer pause');
          var pause = 'S' + crypto.randomBytes(16).toString('hex');
          if (!s.publishInstallPause(snapshot, pause))
            throw Error('Stop changed during installer pause');
          return pause;
        }
        if (s.repairedGeneration) return s.repairedGeneration;
        var previous = s.leaf('stop-generation', 33, true);
        if (previous && expandedStopMode(previous))
          return s.replaceGeneration(previous);
        if (
          previous &&
          (previous.gid !== s.stat.gid || (previous.mode & 4095) !== 436)
        )
          throw Error('Invalid Stop storage');
        var token = 'S' + crypto.randomBytes(16).toString('hex');
        s.write(
          'stop-generation',
          buffer(token),
          436,
          33,
          false,
          undefined,
          true
        );
        return token;
      }
    );
  } catch (error) {
    if (forInstall) throw error;
    try {
      session(
        directory,
        {
          role: 'app',
          operation: 'stop',
          expectedDirectory: expectedDirectory
        },
        function (s) {
          s.invalidateGeneration();
        }
      );
    } catch (ignore) {}
    throw error;
  }
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
      !s.canAccessGroup(value.stat.gid) ||
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
    {
      legacy: true,
      operation: 'logger',
      output: ['controller.log', 'controller.log.previous']
    },
    function (s) {
      ['controller.log', 'controller.log.previous'].forEach(function (name) {
        var expanded = s.leaf(name, Infinity, true);
        if (expanded && (expanded.mode & 4095) === 511)
          s.write(name, buffer(''), 420, Infinity, false);
      });
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
