'use strict';
// A duplicate launch while cpcover finishes restoring the foreground app can
// disturb activation. Let an already restored launcher keep its current window.
module.exports = function (foreground) {
  return foreground !== 'com.gathin.tvhome';
};
// Input sources the TV can wake on: HDMI, Live TV and analog/external inputs.
// The opt-in Stay on input at power-on preference keeps these in front.
module.exports.source = function (foreground) {
  return /^com\.webos\.app\.(hdmi[0-9]+|livetv|av[0-9]*|comp[0-9]*|externalinput\.[a-z0-9]+)$/.test(
    foreground || ''
  );
};
