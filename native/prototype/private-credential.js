'use strict';
// Check-only foundation, deliberately unwired. Private record: {key: string} at
// /cytv-helper-state/ssap-key.json. Never import shared SDK state or log results.
// Namespace/metadata checks do not establish app identity, code trust or reboot
// persistence. Endpoint consistency is not atomic openat confinement.
var directory = '/cytv-helper-state',
  file = directory + '/ssap-key.json',
  maximum = 65536;
function create(fs, actor) {
  return function readPrivateCredential() {
    var fds = [],
      result,
      refused = {},
      reason = 'unsafe',
      uid,
      gid,
      flags;
    function requireValue(value, code) {
      if (!value) {
        reason = code || 'unsafe';
        throw refused;
      }
    }
    function integer(v) {
      return (
        typeof v === 'number' &&
        isFinite(v) &&
        Math.floor(v) === v &&
        v >= 0 &&
        v <= 9007199254740991
      );
    }
    function identity(s) {
      return [s.dev, s.ino, s.uid, s.gid, s.mode];
    }
    function version(s) {
      return identity(s).concat([
        s.nlink,
        s.size,
        s.mtime.getTime(),
        s.ctime.getTime()
      ]);
    }
    function same(a, b) {
      return JSON.stringify(a) === JSON.stringify(b);
    }
    function open(path) {
      var fd = fs.openSync(
        path,
        flags.O_RDONLY | flags.O_NOFOLLOW | flags.O_NONBLOCK
      );
      fds.push(fd);
      return fd;
    }
    function owned(s, mode) {
      requireValue(
        integer(s.dev) &&
          integer(s.ino) &&
          s.ino > 0 &&
          s.uid === uid &&
          s.gid === gid &&
          (s.mode & 4095) === mode
      );
    }
    function checkDirectory(fd, path, mode, expected) {
      var descriptor = fs.fstatSync(fd),
        leaf = fs.lstatSync(path);
      requireValue(
        descriptor.isDirectory() && leaf.isDirectory() && !leaf.isSymbolicLink()
      );
      owned(descriptor, mode);
      owned(leaf, mode);
      requireValue(
        same(identity(descriptor), identity(leaf)) &&
          (!expected || same(identity(descriptor), expected))
      );
      return identity(descriptor);
    }
    function checkFile(fd, expected) {
      var descriptor = fs.fstatSync(fd),
        leaf = fs.lstatSync(file);
      requireValue(
        descriptor.isFile() && leaf.isFile() && !leaf.isSymbolicLink()
      );
      owned(descriptor, 384);
      owned(leaf, 384);
      requireValue(
        descriptor.nlink === 1 &&
          leaf.nlink === 1 &&
          integer(descriptor.size) &&
          descriptor.size > 0 &&
          descriptor.size <= maximum
      );
      requireValue(
        integer(descriptor.mtime.getTime()) &&
          integer(descriptor.ctime.getTime())
      );
      requireValue(
        same(version(descriptor), version(leaf)) &&
          (!expected || same(version(descriptor), expected))
      );
      return descriptor;
    }
    try {
      requireValue(
        actor &&
          typeof actor.getuid === 'function' &&
          typeof actor.getgid === 'function'
      );
      uid = actor.getuid();
      gid = actor.getgid();
      requireValue(
        integer(uid) &&
          uid > 0 &&
          uid < 4294967295 &&
          integer(gid) &&
          gid < 4294967295
      );
      flags = fs.constants || require('constants');
      requireValue(
        integer(flags.O_RDONLY) &&
          integer(flags.O_NOFOLLOW) &&
          flags.O_NOFOLLOW > 0 &&
          integer(flags.O_NONBLOCK) &&
          flags.O_NONBLOCK > 0,
        'unavailable'
      );
      var rootFd = open('/'),
        root = checkDirectory(rootFd, '/', 493),
        directoryFd = open(directory),
        parent = checkDirectory(directoryFd, directory, 448);
      checkDirectory(rootFd, '/', 493, root);
      var fd = open(file),
        before = checkFile(fd),
        pinned = version(before);
      checkDirectory(directoryFd, directory, 448, parent);
      checkDirectory(rootFd, '/', 493, root);
      var bytes = new Buffer(before.size),
        offset = 0;
      while (offset < bytes.length) {
        var n = fs.readSync(fd, bytes, offset, bytes.length - offset, offset);
        requireValue(integer(n) && n > 0 && n <= bytes.length - offset);
        offset += n;
      }
      checkFile(fd, pinned);
      checkDirectory(directoryFd, directory, 448, parent);
      checkDirectory(rootFd, '/', 493, root);
      requireValue(actor.getuid() === uid && actor.getgid() === gid);
      var text = bytes.toString('utf8'),
        record;
      requireValue(
        new Buffer(text, 'utf8').toString('base64') ===
          bytes.toString('base64'),
        'invalid-key'
      );
      try {
        record = JSON.parse(text);
      } catch (ignore) {
        requireValue(false, 'invalid-key');
      }
      requireValue(
        record &&
          typeof record === 'object' &&
          !Array.isArray(record) &&
          typeof record.key === 'string' &&
          record.key.length > 0,
        'invalid-key'
      );
      result = { ok: true, key: record.key };
    } catch (error) {
      result = {
        ok: false,
        reason:
          error === refused
            ? reason
            : error && error.code === 'ENOENT'
              ? 'missing'
              : error && error.code === 'ELOOP'
                ? 'unsafe'
                : 'unavailable'
      };
    } finally {
      while (fds.length) {
        try {
          fs.closeSync(fds.pop());
        } catch (ignoreClose) {
          result = { ok: false, reason: 'unavailable' };
        }
      }
    }
    return result;
  };
}
module.exports = create(require('fs'), process);
// Internal HOST fixture seam only; neither paths nor caller identity are inputs.
module.exports._createForTests = create;
