'use strict';
// The routing preference is separate from the emergency-stop latch and profile.
// Store optional preferences only when they differ from the historical defaults.
module.exports = function (fs, data, apply, visit) {
  var enabled = true,
    keepSource = false,
    longBackHome = true;
  try {
    var saved = JSON.parse(
      require('./state-permissions').readRecord(data, 'home-preference')
    );
    if (
      !saved ||
      typeof saved !== 'object' ||
      Array.isArray(saved) ||
      (saved.enabled !== undefined && typeof saved.enabled !== 'boolean') ||
      (saved.keepSource !== undefined &&
        typeof saved.keepSource !== 'boolean') ||
      (saved.longBackHome !== undefined &&
        typeof saved.longBackHome !== 'boolean')
    )
      throw Error('Expected Home preference object with enabled boolean');
    enabled = saved.enabled !== false;
    keepSource = saved.keepSource === true;
    longBackHome = saved.longBackHome !== false;
  } catch (e) {
    if (e.code !== 'ENOENT') throw e;
  }
  function save(nextEnabled, nextKeepSource, nextLongBackHome) {
    var value = { enabled: nextEnabled };
    if (nextKeepSource) value.keepSource = true;
    if (!nextLongBackHome) value.longBackHome = false;
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
      save(value, keepSource, longBackHome);
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
      save(enabled, value, longBackHome);
      keepSource = value;
      return { keepSource: keepSource };
    },
    longBackHome: function () {
      return longBackHome;
    },
    setLongBackHome: function (value) {
      if (typeof value !== 'boolean')
        throw Error('Expected longBackHome boolean');
      save(enabled, keepSource, value);
      longBackHome = value;
    },
    visit: function () {
      return visit();
    }
  };
};
