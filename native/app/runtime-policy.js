'use strict';
exports.expired = function (last, now) {
  return now - last > 2500;
};
exports.shouldBlock = function (code, signal) {
  return !!signal || code !== 25;
};
