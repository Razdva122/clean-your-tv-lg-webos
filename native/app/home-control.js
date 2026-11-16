'use strict';
// The routing preference is separate from the emergency-stop latch and profile.
module.exports = function (fs, data, apply, visit) {
  var enabled = true;
  try {
    var saved = JSON.parse(
      require('./state-permissions').readRecord(data, 'home-preference')
    );
    if (
      !saved ||
      typeof saved !== 'object' ||
      Array.isArray(saved) ||
      (saved.enabled !== undefined && typeof saved.enabled !== 'boolean')
    )
      throw Error('Expected Home preference object with enabled boolean');
    enabled = saved.enabled !== false;
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
