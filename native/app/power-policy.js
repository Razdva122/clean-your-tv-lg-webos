'use strict';
module.exports = function () {
  var asleep = false;
  return {
    next: function (p) {
      if (p.state === 'Active Standby' || p.state === 'Suspend') {
        asleep = true;
        return false;
      }
      if (p.state === 'Active' && !p.processing && p.onOff !== 'off') {
        var resumed = asleep;
        asleep = false;
        return resumed;
      }
      return false;
    }
  };
};
