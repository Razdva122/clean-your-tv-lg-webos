'use strict';
// Public activation generations fence late replies; they are not credentials.
module.exports = function (options) {
  options = options || {};
  var now = options.now || Date.now,
    generation = options.seed,
    active = false,
    reason = null,
    content = null,
    observed = null;
  if (generation === undefined) {
    var bytes = require('crypto').randomBytes(6);
    generation = 0;
    for (var i = 0; i < bytes.length; i++)
      generation = generation * 256 + bytes[i];
  }
  function valid(n) {
    return (
      typeof n === 'number' &&
      isFinite(n) &&
      n >= 0 &&
      Math.floor(n) === n &&
      n <= 9007199254740991
    );
  }
  if (!valid(generation)) throw Error('Invalid presentation seed');
  function invalidate() {
    if (generation >= 9007199254740991)
      throw Error('Presentation generation exhausted');
    generation++;
    active = false;
    reason = null;
    content = null;
    observed = null;
  }
  return {
    generation: function () {
      return generation;
    },
    active: function () {
      return active;
    },
    begin: function (next, retain) {
      if (retain && active && reason === 'home' && next === 'home')
        return generation;
      invalidate();
      active = true;
      reason = next;
      return generation;
    },
    observe: function (n, id) {
      if (n !== generation || !active) return false;
      // Becoming foreground does not erase or renew the prelaunch underlay fact.
      if (id === 'com.gathin.tvhome') return true;
      content =
        typeof id === 'string' &&
        options.content &&
        options.content(id) === true
          ? true
          : null;
      observed = now();
      return true;
    },
    context: function () {
      var age = observed === null ? 0 : now() - observed,
        fresh = active && observed !== null && age >= 0 && age <= 2000;
      // Unknown is never evidence that the decoder is free.
      return {
        returnValue: true,
        eligible: fresh && reason === 'home' && content === true,
        content: fresh ? content : null,
        generation: generation,
        observedAgeMs: fresh ? age : 0
      };
    },
    dismiss: function (n) {
      if (!valid(n) || n !== generation) return false;
      invalidate();
      return true;
    },
    invalidate: invalidate
  };
};
