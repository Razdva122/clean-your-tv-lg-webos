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
      fs.writeFileSync(path + '.tmp', JSON.stringify({ enabled: value }), {
        mode: 432
      });
      fs.renameSync(path + '.tmp', path);
      enabled = value;
      apply(enabled);
      return { enabled: enabled };
    },
    visit: function () {
      return visit();
    }
  };
};
