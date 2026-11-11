'use strict';
// Host-bundled restart evidence. Never require an installed TV copy.
var fs = require('fs'),
  path = require('path'),
  c = require('constants');
var UUID = /^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/;
function fail(reason) {
  throw Error(reason || 'unsafe-path');
}
function same(a, b) {
  return a.dev === b.dev && a.ino === b.ino;
}
function exists(name) {
  try {
    return fs.lstatSync(name);
  } catch (error) {
    if (error.code === 'ENOENT') return null;
    throw error;
  }
}
function readKernel() {
  var kernel = fs
    .readFileSync('/proc/sys/kernel/random/boot_id', 'utf8')
    .trim();
  if (!UUID.test(kernel)) fail('invalid-boot-identity');
  return kernel;
}
function ancestry(name, uid) {
  for (;;) {
    var s = fs.lstatSync(name);
    if (
      !s.isDirectory() ||
      s.isSymbolicLink() ||
      [0, uid, 5999].indexOf(s.uid) < 0 ||
      (s.mode & 2 && !(s.uid === 0 && s.mode & 512))
    )
      fail();
    if (path.dirname(name) === name) return;
    name = path.dirname(name);
  }
}
function at(name, expected, fn) {
  var before = fs.lstatSync(name),
    fd = fs.openSync(name, c.O_RDONLY | c.O_DIRECTORY | c.O_NOFOLLOW);
  var prior = process.cwd(),
    priorStat = fs.statSync('.');
  try {
    if (
      !before.isDirectory() ||
      !same(before, fs.fstatSync(fd)) ||
      !same(before, expected)
    )
      fail();
    process.chdir(name);
    if (!same(before, fs.statSync('.'))) fail();
    return fn(fd);
  } finally {
    fs.closeSync(fd);
    process.chdir(prior);
    if (!same(priorStat, fs.statSync('.'))) fail();
  }
}
function validProof(proof, goal, kernelOnly) {
  var keys = kernelOnly
    ? 'goal,kernel,kind,schema'
    : 'dev,goal,ino,kernel,schema';
  if (
    !proof ||
    Object.keys(proof).sort().join(',') !== keys ||
    proof.schema !== (kernelOnly ? 2 : 1) ||
    proof.goal !== goal ||
    typeof proof.kernel !== 'string' ||
    !UUID.test(proof.kernel)
  )
    fail();
  if (kernelOnly) {
    if (proof.kind !== 'kernel-only') fail();
  } else if (
    [proof.dev, proof.ino].some(function (n) {
      return (
        typeof n !== 'number' ||
        n < 0 ||
        n > 9007199254740991 ||
        Math.floor(n) !== n
      );
    })
  )
    fail();
}
function run(input, context) {
  context = context || function () {};
  var uid = process.getuid(),
    kernel = readKernel(),
    bootRoot = '/tmp';
  var reply = { boot_id: kernel },
    proof = input.proof;
  context('boot-root');
  var parent = fs.lstatSync(bootRoot);
  context('boot-root', parent);
  ancestry(bootRoot, uid);
  if (
    parent.uid !== 0 ||
    typeof input.removal !== 'string' ||
    !/^[a-f0-9]{32}$/.test(input.removal) ||
    ['boot-create', 'boot-probe', 'boot-retire', 'boot-release'].indexOf(
      input.action
    ) < 0
  )
    fail();
  // Preserve the kind of every captured proof. An inaccessible schema-1 marker
  // is not permission to replace it with a weaker observation.
  var kernelOnly = proof && proof.schema === 2;
  if (
    input.action === 'boot-create' &&
    !proof &&
    input.connection !== 'root-ssh' &&
    (parent.mode & 4095) === 73
  ) {
    reply.boot_proof = {
      schema: 2,
      kind: 'kernel-only',
      goal: input.removal,
      kernel: kernel
    };
    return reply;
  }
  if (kernelOnly) {
    context('boot-proof', parent);
    validProof(proof, input.removal, true);
    if (input.connection === 'root-ssh' || input.action === 'boot-create')
      fail();
    reply.boot_restarted = proof.kernel !== kernel;
    if (input.action === 'boot-retire' && !reply.boot_restarted)
      fail('kernel-boot-unchanged');
    return reply;
  }
  if ((parent.mode & 4095) !== 1023) fail();
  var marker = 'cytv-removal-' + input.removal + '.boot',
    prefix = 'cytv-removal-v1:' + input.removal + ':';
  function markerStat(s) {
    if (
      !s.isFile() ||
      s.isSymbolicLink() ||
      s.uid !== uid ||
      (s.mode & 4095) !== 384 ||
      s.nlink !== 1 ||
      s.size !== prefix.length + 37
    )
      fail();
  }
  function markerRead(expected) {
    context('boot-read', parent);
    var s = exists(marker);
    if (!s) return null;
    markerStat(s);
    var fd = fs.openSync(marker, c.O_RDONLY | c.O_NOFOLLOW | c.O_NONBLOCK),
      b = new Buffer(s.size),
      offset = 0;
    try {
      var opened = fs.fstatSync(fd);
      markerStat(opened);
      if (!same(s, opened)) fail();
      while (offset < b.length) {
        var n = fs.readSync(fd, b, offset, b.length - offset, offset);
        if (n <= 0) fail();
        offset += n;
      }
      var after = fs.lstatSync(marker);
      markerStat(after);
      if (!same(s, after)) fail();
    } finally {
      fs.closeSync(fd);
    }
    var text = b.toString(),
      value = text.slice(prefix.length, -1);
    if (text !== prefix + value + '\n' || !UUID.test(value)) fail();
    if (expected && (!same(s, expected) || value !== expected.kernel)) fail();
    return { stat: s, kernel: value };
  }
  at(bootRoot, parent, function (directory) {
    function remove(item) {
      if (!same(item.stat, fs.lstatSync(marker))) fail();
      fs.unlinkSync(marker);
      fs.fsyncSync(directory);
    }
    context('boot-proof', parent);
    if (input.action !== 'boot-create') validProof(proof, input.removal, false);
    var item = markerRead(input.action === 'boot-create' ? null : proof);
    if (input.action === 'boot-create') {
      context('boot-create', parent);
      if (item && item.kernel !== kernel) {
        remove(item);
        item = null;
      }
      if (!item) {
        var out = fs.openSync(
            marker,
            c.O_WRONLY | c.O_CREAT | c.O_EXCL | c.O_NOFOLLOW,
            384
          ),
          bytes = new Buffer(prefix + kernel + '\n');
        try {
          var offset = 0;
          while (offset < bytes.length) {
            var n = fs.writeSync(
              out,
              bytes,
              offset,
              bytes.length - offset,
              offset
            );
            if (n <= 0) fail();
            offset += n;
          }
          fs.fsyncSync(out);
        } finally {
          fs.closeSync(out);
        }
        fs.fsyncSync(directory);
        item = markerRead(null);
      }
      reply.boot_proof = {
        schema: 1,
        goal: input.removal,
        kernel: item.kernel,
        dev: item.stat.dev,
        ino: item.stat.ino
      };
    } else {
      context(input.action, parent);
      reply.boot_restarted = !item || proof.kernel !== kernel;
      if (input.action === 'boot-retire') {
        if (!reply.boot_restarted) fail();
        if (item) remove(item);
      }
      if (input.action === 'boot-release' && item) remove(item);
    }
  });
  return reply;
}
exports.readKernel = readKernel;
exports.run = run;
