'use strict';
// Preload before the firmware bootstrap. Never handle/suppress fatal exceptions.
var fs = require('fs'),
  path = require('path');
var state = path.dirname(__dirname),
  target = path.join(state, 'recovery-service.json');
var record = {
  schema: 1,
  pid: process.pid,
  attempt: process.pid + '-' + Date.now(),
  phase: 'starting'
};
function save() {
  var fd;
  try {
    for (var parent = state; ; parent = path.dirname(parent)) {
      var dir = fs.lstatSync(parent);
      if (
        !dir.isDirectory() ||
        dir.isSymbolicLink() ||
        dir.uid !== 0 ||
        dir.mode & 18
      )
        return;
      if (parent === path.dirname(parent)) break;
    }
    // Check before truncating: refuse symlinks, hard links and unsafe files.
    fd = fs.openSync(
      target,
      fs.constants.O_WRONLY |
        fs.constants.O_CREAT |
        fs.constants.O_NOFOLLOW |
        fs.constants.O_NONBLOCK,
      384
    );
    var info = fs.fstatSync(fd);
    if (!info.isFile() || info.uid !== 0 || info.nlink !== 1 || info.mode & 18)
      return;
    fs.fchmodSync(fd, 384);
    fs.ftruncateSync(fd, 0);
    fs.writeSync(fd, JSON.stringify(record) + '\n');
  } catch (_) {
    // Diagnostics must never stop recovery or replace the original failure.
  } finally {
    if (fd !== undefined) {
      try {
        fs.closeSync(fd);
      } catch (_) {}
    }
  }
}
save();
// Node 12.17+/13.7+ observes fatal exceptions without changing default exit behavior.
// Older supported Node versions still record normal/explicit/fatal exit codes.
process.on('uncaughtExceptionMonitor', function (error) {
  try {
    record.exception = {
      name: String((error && error.name) || '').slice(0, 64),
      code: String((error && error.code) || '').slice(0, 64),
      stack: String((error && error.stack) || '').slice(0, 4096)
    };
    save();
  } catch (_) {} // Even a throwing error getter must preserve the original exit.
});
process.on('exit', function (code) {
  record.phase = 'exited';
  record.exit_status = code;
  save();
});
