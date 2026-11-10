'use strict';
// Raw ES5: this exact host-owned source also runs on legacy TV Node.
var TYPES = [
  'null',
  'boolean',
  'number',
  'string',
  'array',
  'object',
  'undefined',
  'function',
  'unknown'
];
var CATEGORIES = [
  'unknown',
  'missing',
  'invalid',
  'unsafe',
  'unavailable',
  'mismatch',
  'oversized',
  'unexpected',
  'valid',
  'present',
  'absent',
  'denied',
  'busy',
  'stale'
];
var DECISIONS = ['refuse', 'wait', 'retry', 'retain', 'ignore', 'complete'];
var MAX = 2147483647;
function object(value) {
  return (
    value !== null &&
    typeof value === 'object' &&
    Object.getPrototypeOf(value) === Object.prototype
  );
}
function integer(value, low, high) {
  return (
    typeof value === 'number' &&
    isFinite(value) &&
    Math.floor(value) === value &&
    value >= low &&
    value <= high
  );
}
function describe(value) {
  try {
    if (value === null) return { type: 'null' };
    var type = typeof value;
    if (type === 'string') return { type: type, length: value.length };
    if (
      type === 'boolean' ||
      type === 'number' ||
      type === 'undefined' ||
      type === 'function'
    )
      return { type: type };
    if (
      Array.isArray(value) &&
      Object.getPrototypeOf(value) === Array.prototype
    )
      return { type: 'array', length: value.length };
    if (object(value))
      return { type: 'object', length: Object.keys(value).length };
  } catch (ignore) {}
  return { type: 'unknown' };
}
function normalize(event) {
  try {
    if (!object(event) || event.schema !== 1) return null;
    var result = { schema: 1 },
      keys = ['component', 'operation', 'phase', 'field', 'expected'],
      i,
      key,
      value;
    for (i = 0; i < keys.length; i++) {
      key = keys[i];
      value = event[key];
      if (
        typeof value !== 'string' ||
        value.length > (key === 'field' ? 64 : 32) ||
        !/^[A-Za-z][A-Za-z0-9_.-]*$/.test(value)
      )
        return null;
      result[key] = value;
    }
    var decision = event.decision;
    if (DECISIONS.indexOf(decision) < 0) return null;
    var safe = {},
      actual = event.actual;
    keys = [
      'type',
      'length',
      'uid',
      'gid',
      'mode',
      'size',
      'limit',
      'code',
      'errno',
      'os_code',
      'reported_code',
      'category'
    ];
    if (object(actual))
      for (i = 0; i < keys.length; i++) {
        key = keys[i];
        value = actual[key];
        if (key === 'type' || key === 'category') {
          if ((key === 'type' ? TYPES : CATEGORIES).indexOf(value) >= 0)
            safe[key] = value;
        } else if (
          integer(
            value,
            ['code', 'os_code', 'reported_code'].indexOf(key) >= 0
              ? -2147483648
              : 0,
            ['mode', 'errno'].indexOf(key) >= 0
              ? 4095
              : ['length', 'size', 'limit'].indexOf(key) >= 0
                ? 9007199254740991
                : MAX
          )
        )
          safe[key] = value;
      }
    result.actual = safe;
    result.decision = decision;
    value = event.count;
    result.count = integer(value, 1, MAX) ? value : 1;
    keys = ['first', 'last'];
    for (i = 0; i < keys.length; i++) {
      key = keys[i];
      value = event[key];
      if (integer(value, 0, 9007199254740991)) result[key] = value;
    }
    var count = result.count;
    result.count = MAX;
    if (JSON.stringify(result).length > 512) delete result.last;
    if (JSON.stringify(result).length > 512) delete result.first;
    var fits = JSON.stringify(result).length <= 512;
    result.count = count;
    return fits ? result : null;
  } catch (ignore) {
    return null;
  }
}
function safeEvents(envelope) {
  try {
    var values = Array.isArray(envelope)
      ? envelope
      : object(envelope) && envelope.schema === 1
        ? envelope.events
        : null;
    if (!Array.isArray(values)) return [];
    var result = [],
      i,
      clean;
    for (i = 0; i < Math.min(values.length, 32); i++) {
      clean = normalize(values[i]);
      if (clean) result.push(clean);
    }
    while (JSON.stringify(result).length > 16200) result.splice(1, 1);
    return result;
  } catch (ignore) {
    return [];
  }
}
function identity(event) {
  var copy = normalize(event);
  delete copy.count;
  delete copy.first;
  delete copy.last;
  return JSON.stringify(copy);
}
function create(emit, context) {
  var events = [],
    dropped = 0,
    suppressed = 0;
  return {
    record: function (event) {
      try {
        var merged = {},
          key,
          clean,
          i,
          keys = [
            'schema',
            'component',
            'operation',
            'phase',
            'field',
            'expected',
            'actual',
            'decision',
            'count',
            'first',
            'last'
          ];
        for (i = 0; i < keys.length; i++) {
          key = keys[i];
          if (
            object(context) &&
            Object.prototype.hasOwnProperty.call(context, key)
          )
            merged[key] = context[key];
          if (object(event) && Object.prototype.hasOwnProperty.call(event, key))
            merged[key] = event[key];
        }
        clean = normalize(merged);
        if (!clean) {
          suppressed = Math.min(MAX, suppressed + 1);
          return;
        }
        for (i = 0; i < events.length; i++)
          if (identity(events[i]) === identity(clean)) {
            events[i].count = Math.min(MAX, events[i].count + clean.count);
            if (clean.last !== undefined) events[i].last = clean.last;
            return;
          }
        if (events.length === 32) {
          events.splice(1, 1);
          dropped = Math.min(MAX, dropped + 1);
        }
        events.push(clean);
        while (JSON.stringify(events).length > 16200) {
          events.splice(1, 1);
          dropped = Math.min(MAX, dropped + 1);
        }
        if (typeof emit === 'function') emit(normalize(clean));
      } catch (ignore) {}
    },
    snapshot: function () {
      return {
        schema: 1,
        events: safeEvents(events),
        dropped: dropped,
        suppressed: suppressed
      };
    }
  };
}
module.exports = {
  describe: describe,
  normalize: normalize,
  safeEvents: safeEvents,
  create: create
};
