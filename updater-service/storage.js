'use strict';
var fs = require('fs'),
  path = require('path'),
  crypto = require('crypto');
module.exports = function (dir) {
  function file(name) {
    if (['transaction', 'profile'].indexOf(name) < 0)
      throw Error('invalid-state-name');
    return path.join(dir, name + '.json');
  }
  return {
    read: function (name) {
      try {
        var p = file(name);
        if (fs.statSync(p).size > 5 * 1024 * 1024)
          throw Error('state-too-large');
        return JSON.parse(fs.readFileSync(p, 'utf8'));
      } catch (e) {
        if (e.code === 'ENOENT') return null;
        throw Error('state-unreadable');
      }
    },
    write: function (name, value) {
      if (!fs.existsSync(dir)) fs.mkdirSync(dir, 448);
      var p = file(name),
        tmp = p + '.' + crypto.randomBytes(8).toString('hex');
      var bytes = JSON.stringify(value);
      if (bytes.length > 5 * 1024 * 1024) throw Error('state-too-large');
      var fd = fs.openSync(tmp, 'wx', 384);
      try {
        fs.writeFileSync(fd, bytes);
        fs.fsyncSync(fd);
      } finally {
        fs.closeSync(fd);
      }
      try {
        fs.renameSync(tmp, p);
        var parent = fs.openSync(dir, 'r');
        try {
          fs.fsyncSync(parent);
        } finally {
          fs.closeSync(parent);
        }
      } catch (e) {
        try {
          fs.unlinkSync(tmp);
        } catch (_) {}
        throw e;
      }
    }
  };
};
