'use strict';
var fs = require('fs'),
  diagnostics = require('./diagnostics');
function readLimited(file, limit) {
  return new Promise(function (resolve, reject) {
    fs.open(file, 'r', function (error, fd) {
      if (error) {
        reject(error);
        return;
      }
      var buffer = Buffer.alloc(limit + 1);
      fs.read(fd, buffer, 0, limit + 1, 0, function (err, count) {
        fs.close(fd, function (closeError) {
          if (err || closeError || count > limit)
            reject(
              err ||
                closeError ||
                Object.assign(new Error('read-failed'), { code: 'TOO_LARGE' })
            );
          else resolve(buffer.slice(0, count).toString('utf8'));
        });
      });
    });
  });
}
function createLocalIO(options) {
  if (!options || !options.stateFile) throw new Error('stateFile required');
  var stateFile = options.stateFile;
  return {
    now: Date.now,
    request: options.request || require('./transport').createRequest(),
    readToken: function () {
      return readLimited(
        options.tokenFile || '/var/luna/preferences/devmode_enabled',
        4097
      ).then(function (s) {
        return s.trim();
      });
    },
    load: function () {
      return readLimited(stateFile, 4096).then(
        function (text) {
          try {
            var state = JSON.parse(text);
            if (
              !state ||
              typeof state !== 'object' ||
              !Number.isFinite(state.nextAt) ||
              !Number.isFinite(state.checkedAt) ||
              !Number.isFinite(state.failures)
            )
              throw { code: 'INVALID_STATE' };
            return state;
          } catch (error) {
            throw diagnostics.storage('renewal', 'parse', error);
          }
        },
        function (error) {
          if (error.code === 'ENOENT') return {};
          throw diagnostics.storage('renewal', 'read', error);
        }
      );
    },
    save: function (value) {
      // Fixed fields only: never persist arbitrary API responses or credentials.
      var clean = {
        status: value.status,
        checkedAt: value.checkedAt,
        nextAt: value.nextAt,
        failures: value.failures
      };
      if (typeof value.remainingSeconds === 'number')
        clean.remainingSeconds = value.remainingSeconds;
      return new Promise(function (resolve, reject) {
        var temp =
          stateFile +
          '.tmp-' +
          require('crypto').randomBytes(8).toString('hex');
        fs.writeFile(
          temp,
          JSON.stringify(clean) + '\n',
          { mode: 384, flag: 'wx' },
          function (error) {
            if (error) {
              reject(diagnostics.storage('renewal', 'write', error));
              return;
            }
            fs.rename(temp, stateFile, function (err) {
              if (err) {
                fs.unlink(temp, function () {
                  reject(diagnostics.storage('renewal', 'rename', err));
                });
              } else resolve();
            });
          }
        );
      });
    }
  };
}
module.exports = { createLocalIO: createLocalIO };
