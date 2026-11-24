'use strict';
// The routing preference is separate from the emergency-stop latch and profile.
// keepSource (Stay on input at power-on) is stored only while it is on, so the
// default record and older Helpers reading it are unchanged.
module.exports = function (fs, data, apply, visit) {
  var enabled = true,
    keepSource = false;
  try {
    var saved = JSON.parse(
      require('./state-permissions').readRecord(data, 'home-preference')
    );
    if (
      !saved ||
      typeof saved !== 'object' ||
      Array.isArray(saved) ||
      (saved.enabled !== undefined && typeof saved.enabled !== 'boolean') ||
      (saved.keepSource !== undefined && typeof saved.keepSource !== 'boolean')
    )
      throw Error('Expected Home preference object with enabled boolean');
    enabled = saved.enabled !== false;
    keepSource = saved.keepSource === true;
  } catch (e) {
    if (e.code !== 'ENOENT') throw e;
  }
  function save(nextEnabled, nextKeepSource) {
    var value = { enabled: nextEnabled };
    if (nextKeepSource) value.keepSource = true;
    require('./state-permissions').atomicRecord(
      data,
      'home-preference',
      JSON.stringify(value)
    );
  }
  return {
    enabled: function () {
      return enabled;
    },
    set: function (value) {
      if (typeof value !== 'boolean') throw Error('Expected enabled boolean');
      save(value, keepSource);
      enabled = value;
      apply(enabled);
      return { enabled: enabled };
    },
    keepSource: function () {
      return keepSource;
    },
    setKeepSource: function (value) {
      if (typeof value !== 'boolean')
        throw Error('Expected keepSource boolean');
      save(enabled, value);
      keepSource = value;
      return { keepSource: keepSource };
    },
    visit: function () {
      return visit();
    }
  };
};
