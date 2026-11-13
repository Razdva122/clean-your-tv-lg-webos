"""Run the actual STATE_CHECK with real files and a modeled TV identity boundary."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from cytv.no_root_observer import STATE_CHECK


@unittest.skipIf(os.name == 'nt', 'TV storage requires POSIX inode and permission semantics')
class StateCheckIdentityTests(unittest.TestCase):
    def test_root_repair_authenticates_before_fixing_key_as_developer_without_upload(self):
        # Only identities and TV path translation are modeled. Contract source,
        # hashes, opens, inode replacement, file bytes and modes execute for real.
        harness = r'''
const fs = require('fs'), path = require('path'), vm = require('vm');
const assert = require('assert'), crypto = require('crypto');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const fixed = '/media/developer/apps/usr/palm/applications/com.local.nativehome/state';
const physical = input.root + fixed;
fs.mkdirSync(physical, {recursive: true, mode: 0o770});
fs.chmodSync(physical, 0o770);
const key = physical + '/ssap-key.json', apps = physical + '/apps.json';
const bytes = '{"key":"retained-pairing"}';
fs.writeFileSync(key, bytes, {mode: 0o640});
fs.writeFileSync(apps, '[]', {mode: 0o644});
fs.writeFileSync(physical + '/blocked', 'existing emergency stop');
const owners = {}, gids = {};
const stateInode = fs.statSync(physical).ino;
function execute(option, statusOverride) {
  let uid = 0, gid = 0, groups = [0], cwd = '/root-private', output = '', exitCode = 0;
  const events = [], hostFs = Object.assign({}, fs);
  function virtual(name) { return path.resolve(cwd, String(name)); }
  function translate(name) { return input.root + virtual(name); }
  function metadata(stat) {
    stat.uid = stat.isDirectory() ? (stat.ino === stateInode ? 5999 : 0) :
      (owners[stat.ino] === undefined ? 5999 : owners[stat.ino]);
    stat.gid = stat.isDirectory() ? (stat.ino === stateInode ? 5000 : 0) :
      (gids[stat.ino] === undefined ? 5000 : gids[stat.ino]);
    return stat;
  }
  ['lstatSync', 'statSync'].forEach(function(name) {
    hostFs[name] = function(target) { return metadata(fs[name](translate(target))); };
  });
  hostFs.fstatSync = function(fd) { return metadata(fs.fstatSync(fd)); };
  hostFs.openSync = function(target, flags, mode) {
    const name = virtual(target);
    events.push(['open', name, uid]);
    const fd = fs.openSync(translate(target), flags, mode);
    if (flags & require('constants').O_CREAT) {
      owners[fs.fstatSync(fd).ino] = uid;
      gids[fs.fstatSync(fd).ino] = gid;
    }
    return fd;
  };
  hostFs.fchownSync = function(fd, owner, group) {
    owners[fs.fstatSync(fd).ino] = owner;
    gids[fs.fstatSync(fd).ino] = group;
  };
  ['unlinkSync', 'chmodSync', 'readFileSync', 'readdirSync'].forEach(function(name) {
    hostFs[name] = function(target) {
      if (name === 'readFileSync' && target === '/proc/self/status') {
        if (statusOverride !== undefined && uid !== 0) return statusOverride;
        return 'Name:\tnode\nUid:\t' + [uid, uid, uid, uid].join('\t') +
          '\nGid:\t' + [gid, gid, gid, gid].join('\t') + '\n';
      }
      const args = Array.prototype.slice.call(arguments); args[0] = translate(target);
      return fs[name].apply(fs, args);
    };
  });
  ['renameSync', 'linkSync'].forEach(function(name) {
    hostFs[name] = function(from, to) { return fs[name](translate(from), translate(to)); };
  });
  const processBoundary = {
    argv: ['node', '-', option, fixed],
    getuid: function() { return uid; }, geteuid: function() { return uid; },
    getgid: function() { return gid; }, getegid: function() { return gid; },
    getgroups: function() { return groups.slice(); },
    setgroups: function(value) { assert.strictEqual(uid, 0); groups = value.slice(); events.push(['groups', groups]); },
    setgid: function(value) { assert.strictEqual(uid, 0); gid = value; events.push(['gid', gid]); },
    setuid: function(value) { assert.strictEqual(uid, 0); uid = value; events.push(['uid', uid]); },
    cwd: function() { return cwd; },
    chdir: function(value) {
      const next = path.resolve(cwd, value);
      if (uid !== 0 && next === '/root-private') throw Error('root-only SSH cwd');
      cwd = next; events.push(['cwd', cwd]);
    },
    stdout: {write: function(value) { output += value; }},
    exit: function(code) { exitCode = code; throw Error('adapter-exit'); }
  };
  if (input.legacy) {
    delete processBoundary.geteuid;
    delete processBoundary.getegid;
  }
  try {
    vm.runInNewContext(input.source, {
      require: function(name) { return name === 'fs' ? hostFs : require(name); },
      process: processBoundary, Buffer: Buffer, console: console
    });
  } catch (error) { if (error.message !== 'adapter-exit') throw error; }
  return {uid, gid, groups: Array.from(groups), cwd, events, output, exitCode};
}
const before = fs.statSync(key);
owners[before.ino] = 5999; gids[before.ino] = 5000;
const inspected = execute('inspect');
assert.strictEqual(inspected.exitCode, 0, inspected.output);
assert.strictEqual(inspected.output, 'CYTV_CONFIGURATION_PRIVATE');
assert.strictEqual(inspected.uid, 0);
assert.strictEqual(inspected.gid, 0);
assert.deepStrictEqual(inspected.groups, [0]);
assert.strictEqual(inspected.events.filter(e => ['uid', 'gid', 'groups'].includes(e[0])).length, 0);
assert.strictEqual(fs.statSync(key).ino, before.ino);
assert.strictEqual(fs.statSync(key).mode & 0o777, 0o640);
fs.chmodSync(key, 0o775); // Firmware-expanded key needs authenticated mode repair.
for (const option of ['repair-key-mode', 'repair-key-mode:' + '0'.repeat(64)]) {
  const refused = execute(option);
  assert.notStrictEqual(refused.exitCode, 0, option + ' must refuse without the original byte proof');
  assert(!refused.output.includes('CYTV_CONFIGURATION_PRIVATE'));
  assert.strictEqual(fs.statSync(key).ino, before.ino);
  assert.strictEqual(fs.statSync(key).mode & 0o777, 0o775);
  assert.strictEqual(owners[before.ino], 5999);
  assert.strictEqual(gids[before.ino], 5000);
  assert.strictEqual(fs.readFileSync(key, 'utf8'), bytes);
  if (option === 'repair-key-mode') assert.strictEqual(refused.uid, 0);
}
const digest = crypto.createHash('sha256').update(bytes).digest('hex');
if (input.legacy) {
  for (const status of [
    'Uid:\t5999\t5999\t5999\t5999\n', // Missing effective group.
    'Uid:\t5999\t0\t5999\t5999\nGid:\t5000\t5000\t5000\t5000\n',
    'Uid:\t5999\t5999\t5999\t5999\nGid:\t5000\t0\t5000\t5000\n'
  ]) {
    const refused = execute('repair-key-mode:' + digest, status);
    assert.notStrictEqual(refused.exitCode, 0);
    assert.strictEqual(refused.events.filter(e => e[0] === 'open').length, 0);
    assert.strictEqual(fs.statSync(key).ino, before.ino);
    assert.strictEqual(fs.statSync(key).mode & 0o777, 0o775);
  }
}
const repaired = execute('repair-key-mode:' + digest);
assert.strictEqual(repaired.exitCode, 0, repaired.output);
assert.strictEqual(repaired.output, 'CYTV_CONFIGURATION_PRIVATE');
assert.strictEqual(repaired.uid, 5999, 'Root repair must permanently become the packaged Helper identity');
assert.strictEqual(repaired.gid, 5000);
assert.deepStrictEqual(repaired.groups, []);
assert.strictEqual(repaired.cwd, '/', 'finalizer must not return to the Root-only SSH cwd');
assert(repaired.events.filter(e => e[0] === 'open').every(e => e[2] === 5999),
       'content and staging opens must happen after dropping privileges');
const after = fs.statSync(key);
assert.strictEqual(owners[after.ino], 5999, 'repair itself must leave a boot-readable owner; there is no upload step');
assert.strictEqual(gids[after.ino], 5000);
assert.strictEqual(after.mode & 0o777, 0o640);
assert.strictEqual(fs.readFileSync(key, 'utf8'), bytes);
assert.strictEqual(fs.readFileSync(apps, 'utf8'), '[]');
assert.strictEqual(fs.readFileSync(physical + '/blocked', 'utf8'), 'existing emergency stop');
assert.deepStrictEqual(fs.readdirSync(physical).sort(), ['apps.json', 'blocked', 'ssap-key.json']);
console.log('PASS: readonly Root inspect and permanent Developer identity repair without upload');
'''
        for legacy in (False, True):
            with self.subTest(legacy=legacy), tempfile.TemporaryDirectory() as temporary:
                result = subprocess.run([shutil.which('node'), '-e', harness],
                    input=json.dumps({'root': str(Path(temporary).resolve()), 'source': STATE_CHECK, 'legacy': legacy}),
                    text=True, capture_output=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
