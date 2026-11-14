'use strict';
exports.expired = function (last, now) {
  return now - last > 2500;
};
exports.shouldBlock = function (code, signal) {
  return !!signal || code !== 25;
};
var events = require('./contract-events');
exports.classifyExit = function (s) {
  var code = s.code,
    signal = s.signal,
    reason = s.reportedReason;
  var d = {
    action: 'terminal',
    block: reason === 27 || exports.shouldBlock(code, signal),
    cleanup: !!(s.ready || signal),
    terminalUI: !!(code === 22 || code === 27 || reason === 27 || s.stop),
    code: code,
    signal: signal,
    reportedReason: reason,
    exitCode: reason === 27 ? 27 : code === 22 ? 0 : code || 0,
    diagnostics: []
  };
  var emergency = s.stop || s.blocked || (s.watchdog && !s.watchdogOwned);
  if (!emergency && reason !== 27 && s.tracked) {
    if (code === 33 && !signal && reason === 33 && s.ready && !s.watchdog) {
      d.block = d.cleanup = false;
    } else if (
      code === 32 &&
      !signal &&
      reason === 32 &&
      s.powerOffUntil &&
      s.now <= s.powerOffUntil &&
      !s.watchdog
    ) {
      d.action = 'wait-power';
      d.block = d.cleanup = false;
    } else if (
      (reason === undefined || reason === 20) &&
      ((code === 20 && !signal) ||
        (s.watchdogKill && signal === 'SIGKILL' && reason === undefined))
    ) {
      if (s.retryCount < 5) {
        d.action = 'retry-watchdog';
        d.block = false;
        d.cleanup = true;
      } else {
        d.retryLimit = true;
        d.exitCode = 20;
      }
    }
  }
  var known = [
    0, 10, 11, 12, 13, 14, 15, 16, 17, 18, 20, 22, 23, 24, 25, 26, 27, 28, 29,
    30, 31, 32, 33
  ];
  if (
    (reason !== undefined && reason !== code) ||
    (!signal && known.indexOf(code) < 0) ||
    (code === 32 && d.action !== 'wait-power') ||
    (code === 33 && d.block)
  ) {
    var actual = events.describe(code);
    actual.os_code = code;
    actual.reported_code = reason;
    actual.category =
      reason !== undefined && reason !== code ? 'mismatch' : 'unexpected';
    d.diagnostics.push(
      events.normalize({
        schema: 1,
        component: 'runtime',
        operation: 'relay-exit',
        phase: 'classify',
        field: 'exit',
        expected: 'tracked-relay-exit',
        actual: actual,
        decision: 'retain'
      })
    );
  }
  // Fixed Linux signal numbers describe known TV signals, never payload strings.
  var signals = { SIGKILL: 9, SIGTERM: 15, SIGINT: 2, SIGHUP: 1 };
  var signalCode =
    typeof signal === 'string' &&
    Object.prototype.hasOwnProperty.call(signals, signal)
      ? signals[signal]
      : undefined;
  if (signal && (d.diagnostics.length || signalCode === undefined)) {
    var signalActual = events.describe(signal);
    signalActual.code = signalCode;
    signalActual.category = signalCode === undefined ? 'unknown' : 'present';
    d.diagnostics.push(
      events.normalize({
        schema: 1,
        component: 'runtime',
        operation: 'relay-exit',
        phase: 'classify',
        field: 'signal',
        expected: 'relay-signal',
        actual: signalActual,
        decision: 'retain'
      })
    );
  }
  return d;
};
