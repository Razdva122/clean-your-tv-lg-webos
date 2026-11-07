'use strict';
// A duplicate launch while cpcover finishes restoring the foreground app can
// disturb activation. Let an already restored launcher keep its current window.
module.exports = function (foreground) {
  return foreground !== 'com.gathin.tvhome';
};
