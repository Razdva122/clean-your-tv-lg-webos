'use strict';
// The routing preference is separate from the emergency-stop latch and profile.
module.exports = function (fs, data, apply, visit) {
  var path = data + '/home-control.json',
    enabled = true;
  try {
    enabled = JSON.parse(fs.readFileSync(path, 'utf8')).enabled !== false;
  } catch (e) {
    if (e.code !== 'ENOENT') throw e;
  }
  return {
    enabled: function () {
      return enabled;
    },
    set: function (value) {
      if (typeof value !== 'boolean') throw Error('Expected enabled boolean');
      require('./state-permissions').atomicRecord(
        data,
        'home-preference',
        JSON.stringify({ enabled: value })
      );
      enabled = value;
      apply(enabled);
      return { enabled: enabled };
    },
    visit: function () {
      return visit();
    }
  };
};
