'use strict';
exports.claim = function (state, boot, blocked) {
  if (
    blocked ||
    !state ||
    state.enabled !== true ||
    typeof boot !== 'string' ||
    !boot ||
    state.boot === boot
  )
    return null;
  return { enabled: true, boot: boot };
};
exports.identity = function (uuid, stat) {
  var m = /^btime (\d+)$/m.exec(stat);
  return uuid && m ? uuid + ':' + m[1] : '';
};
